"""Milestone 2 Ingestion Framework & Scheduler Verification Tests

Verifies:
1. Per-source rate limiting, burst controls, and quota exhaustion
2. BaseSource fetch retry with exponential backoff and health transitions
3. Registry enforcement of PENDING_VERIFICATION gating
4. IngestionScheduler lifecycle and manual trigger execution
5. REST API contract for source monitoring (/api/sources and health)
"""
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import PENDING_VERIFICATION, settings
from backend.app.core.database import SessionLocal, init_db, get_db
from backend.app.models.db_models import Base, DataSource, SourceHealth, utc_now
from backend.app.ingestion.base import (
    BaseSource,
    IngestionError,
    RateLimitExceededError,
    SourceFetchError,
    SourceValidationError,
)
from backend.app.ingestion.rate_limiter import RateLimiter, get_rate_limiter
from backend.app.ingestion.registry import SourceRegistry, source_registry
from backend.app.ingestion.scheduler import IngestionScheduler, ingestion_scheduler
from backend.app.main import app
from backend.app.services.db_seeder import seed_database

# --- Test DB Setup Fixtures ---

@pytest.fixture(scope="module")
def db_session():
    init_db()
    seed_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- Mock Source Implementations ---

class DummyWorkingSource(BaseSource):
    source_id = "DUMMY_WORKING"
    name = "Dummy Working Provider"
    provider = "LANDSAFE Test"
    cadence_minutes = 15
    licence = "Test Licence"
    api_endpoint = "https://test.landsafe.internal"

    def __init__(self, fetch_count: int = 5):
        super().__init__()
        self.fetch_count = fetch_count
        self.fetch_calls = 0

    async def fetch(self, **kwargs) -> Any:
        self.fetch_calls += 1
        return [{"reading_id": i, "val": 10.0 + i} for i in range(self.fetch_count)]

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        return [{"id": item["reading_id"], "value": item["val"]} for item in raw_data]


class DummyFailingSource(BaseSource):
    source_id = "DUMMY_FAILING"
    name = "Dummy Failing Provider"
    provider = "LANDSAFE Test"
    cadence_minutes = 30
    licence = "Test Licence"
    max_retries = 2
    retry_backoff_base_s = 0.05

    def __init__(self):
        super().__init__()
        self.fetch_attempts = 0

    async def fetch(self, **kwargs) -> Any:
        self.fetch_attempts += 1
        raise ConnectionResetError("Simulated socket connection reset")

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        return []


# --- 1. Rate Limiter Tests ---

def test_rate_limiter_quota_and_burst():
    limiter = RateLimiter("test_burst", daily_budget=5, max_calls_per_second=50.0)
    assert limiter.can_call(1) is True
    assert limiter.acquire(1) is True
    assert limiter.acquire(2) is True
    assert limiter.acquire(2) is True
    # Quota reached (5/5)
    assert limiter.can_call(1) is False
    assert limiter.acquire(1) is False
    status = limiter.get_status()
    assert status["quota_exceeded"] is True
    assert status["remaining_budget"] == 0


@pytest.mark.asyncio
async def test_rate_limiter_async_acquire():
    limiter = RateLimiter("test_async", daily_budget=3, max_calls_per_second=100.0)
    assert await limiter.acquire_async(2) is True
    assert await limiter.acquire_async(1) is True
    assert await limiter.acquire_async(1) is False


def test_rate_limiter_rollover():
    limiter = RateLimiter("test_rollover", daily_budget=2)
    limiter.acquire(2)
    assert limiter.can_call(1) is False
    # Simulate past date
    limiter.reset_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    limiter._check_day_rollover()
    assert limiter.can_call(1) is True
    assert limiter.calls_today == 0


# --- 2. BaseSource Ingestion Cycle Tests ---

@pytest.mark.asyncio
async def test_base_source_successful_cycle(db_session):
    source = DummyWorkingSource(fetch_count=3)
    result = await source.run_cycle(db=db_session)
    assert result["success"] is True
    assert result["records_count"] == 3
    assert result["status"] == "FRESH"
    assert result["latency_ms"] >= 0.0

    # Verify DB health record
    health = db_session.query(SourceHealth).filter(SourceHealth.source_id == "DUMMY_WORKING").first()
    assert health is not None
    assert health.status == "FRESH"
    assert health.consecutive_failures == 0
    assert health.last_attempt_status == "SUCCESS"
    assert health.last_successful_fetch is not None


@pytest.mark.asyncio
async def test_base_source_failing_cycle_retries_and_health_transition(db_session):
    # Ensure clean state for test
    db_session.query(SourceHealth).filter(SourceHealth.source_id == "DUMMY_FAILING").delete()
    db_session.query(DataSource).filter(DataSource.id == "DUMMY_FAILING").delete()
    db_session.commit()

    source = DummyFailingSource()
    result = await source.run_cycle(db=db_session)
    assert result["success"] is False
    assert result["status"] == "OFFLINE"
    assert "Simulated socket connection reset" in result["error"]
    assert source.fetch_attempts == 2  # max_retries = 2

    # Check DB health degraded / failure count
    health = db_session.query(SourceHealth).filter(SourceHealth.source_id == "DUMMY_FAILING").first()
    assert health is not None
    assert health.consecutive_failures == 1
    assert "FAILED" in health.last_attempt_status


class DummyExhaustedSource(BaseSource):
    source_id = "DUMMY_EXHAUSTED"
    name = "Dummy Exhausted Provider"
    provider = "LANDSAFE Test"
    cadence_minutes = 15
    licence = "Test Licence"

    def __init__(self):
        super().__init__()
        self.rate_limiter.daily_budget = 0  # Exhaust quota immediately

    async def fetch(self, **kwargs) -> Any:
        return []

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        return []


@pytest.mark.asyncio
async def test_base_source_rate_limit_exceeded(db_session):
    source = DummyExhaustedSource()
    result = await source.run_cycle(db=db_session)
    assert result["success"] is False
    assert result["status"] == "RATE_LIMITED"


# --- 3. Registry & Verification Gating Tests ---

def test_registry_registration_and_verification_gating():
    reg = SourceRegistry()
    src = DummyWorkingSource()
    reg.register(src)

    assert reg.get("DUMMY_WORKING") is src
    assert reg.get("dummy_working") is src
    assert reg.is_verified("DUMMY_WORKING") is True

    # Check that PENDING_VERIFICATION sources are flagged unverified
    for blocked_id in PENDING_VERIFICATION:
        assert reg.is_verified(blocked_id) is False

    unverified = reg.get_unverified_sources()
    assert "nisar_ssar" in unverified or "resourcesat_liss" in unverified


# --- 4. Scheduler Tests ---

@pytest.mark.asyncio
async def test_scheduler_lifecycle_and_trigger(db_session):
    scheduler = IngestionScheduler()
    source = DummyWorkingSource()
    source_registry.register(source)

    scheduler.start(autoconfigure_jobs=False)
    assert scheduler.is_running is True

    # Add job
    added = scheduler.add_source_job(source)
    assert added is True
    jobs = scheduler.get_jobs_status()
    assert any(j["job_id"] == "ingest_dummy_working" for j in jobs)

    # Pause and Resume
    assert scheduler.pause_source("dummy_working") is True
    assert scheduler.resume_source("dummy_working") is True

    # Manual Trigger
    trigger_result = await scheduler.trigger_now("dummy_working")
    assert trigger_result["success"] is True

    # Remove job and shutdown
    assert scheduler.remove_source_job("dummy_working") is True
    scheduler.shutdown(wait=False)
    assert scheduler.is_running is False


@pytest.mark.asyncio
async def test_scheduler_blocks_unverified_trigger():
    class UnverifiedNISAR(BaseSource):
        source_id = "nisar_ssar"
        name = "NISAR SAR"
        provider = "ISRO"
        cadence_minutes = 17280
        licence = "Space Policy 2023"
        async def fetch(self, **kwargs): return []
        def normalize(self, raw_data): return []

    source_registry.register(UnverifiedNISAR())
    result = await ingestion_scheduler.trigger_now("nisar_ssar")
    assert result["success"] is False
    assert result["status"] == "BLOCKED"
    assert "PENDING_VERIFICATION" in result["error"]


# --- 5. API Endpoints Tests ---

def test_api_sources_list(client):
    res = client.get("/api/sources")
    assert res.status_code == 200
    data = res.json()
    assert "sources" in data
    assert data["total_sources"] >= 9
    # Verify advisory header and envelope
    assert "advisory" in data
    assert "X-LANDSAFE-Advisory" in res.headers

    # Verify key providers present
    source_ids = [s["id"] for s in data["sources"]]
    assert "OPEN_METEO" in source_ids
    assert "MOSDAC_INSAT3D_QPE" in source_ids


def test_api_source_health_detail(client):
    res = client.get("/api/sources/OPEN_METEO/health")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "OPEN_METEO"
    assert "health" in data
    assert "rate_limit" in data
    assert data["rate_limit"]["daily_budget"] == 10000


def test_api_source_health_404(client):
    res = client.get("/api/sources/NON_EXISTENT_SOURCE/health")
    assert res.status_code == 404


def test_api_source_trigger_endpoint(client):
    # Register dummy source in global registry
    dummy = DummyWorkingSource()
    source_registry.register(dummy)

    res = client.post("/api/sources/dummy_working/trigger")
    assert res.status_code == 200
    data = res.json()
    assert data["source_id"] == "DUMMY_WORKING"
    assert data["success"] is True
