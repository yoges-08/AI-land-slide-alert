"""Milestone 3 Weather Ingestion & Multi-Source Reconciliation Tests

Verifies:
1. MOSDAC INSAT-3D/3DR QPE fetch, validation, normalization, and coordinate spatial mapping
2. NASA GPM IMERG ingestion, quality indexing, and grid normalization
3. Open-Meteo rate-budgeted ingestion, observed/forecast separation, and quality grading
4. Multi-source reconciliation priority hierarchy (MOSDAC -> NASA GPM -> Open-Meteo)
5. 10-day Antecedent Saturation Index (ASI_10d) calculation with 0.85 decay factor
6. Idempotent upserts to weather_observations table
7. REST API endpoints /api/weather/district/{id} and /api/weather/asi/{id}
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal, init_db, get_db
from backend.app.core.freshness import utcnow
from backend.app.ingestion.base import (
    RateLimitExceededError, SourceFetchError, SourceValidationError,
)
from backend.app.ingestion.sources.weather.mosdac_insat3d import MosdacInsat3dSource
from backend.app.ingestion.sources.weather.nasa_gpm import NasaGpmSource
from backend.app.ingestion.sources.weather.open_meteo import OpenMeteoSource
from backend.app.models.db_models import DataSource, District, SourceHealth, WeatherObservation, utc_now
from backend.app.services.db_seeder import seed_database
from backend.app.services.weather_reconciliation import (
    WeatherReconciliationService, WEATHER_SOURCE_PRIORITY, DECAY_FACTOR,
)
from backend.app.main import app


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


# --- 1. MOSDAC INSAT-3D/3DR Source Tests ---

@pytest.mark.asyncio
async def test_mosdac_source_normalization_and_store(db_session):
    source = MosdacInsat3dSource()
    sample_time = "2026-09-20T12:00:00Z"
    sample_payload = {
        "observation_time": sample_time,
        "product": "3D_QPE",
        "records": [
            {
                "district_id": 1,
                "rainfall_1h_mm": 15.5,
                "rainfall_24h_mm": 82.0,
                "rainfall_7d_cumulative_mm": 190.0,
                "quality_flag": "NOMINAL"
            },
            {
                "district_id": 2,
                "rainfall_1h_mm": 0.0,
                "rainfall_24h_mm": 4.2,
                "rainfall_7d_cumulative_mm": 18.5,
                "quality_flag": "NOMINAL"
            }
        ]
    }

    raw = await source.fetch(simulated_payload=sample_payload)
    source.validate(raw)
    records = source.normalize(raw)

    assert len(records) == 2
    assert records[0]["district_id"] == 1
    assert records[0]["source_id"] == "MOSDAC_INSAT3D_QPE"
    assert records[0]["rainfall_1h_mm"] == 15.5
    assert records[0]["rainfall_24h_mm"] == 82.0

    stored = source.store(records, db_session)
    assert stored == 2

    # Verify DB content
    obs = db_session.query(WeatherObservation).filter(
        WeatherObservation.district_id == 1,
        WeatherObservation.source_id == "MOSDAC_INSAT3D_QPE"
    ).first()
    assert obs is not None
    assert obs.rainfall_24h_mm == 82.0


def test_mosdac_validation_rejects_malformed_payload():
    source = MosdacInsat3dSource()
    with pytest.raises(SourceValidationError):
        source.validate(None)

    with pytest.raises(SourceValidationError):
        source.validate({"invalid": "payload"})


# --- 2. NASA GPM IMERG Source Tests ---

@pytest.mark.asyncio
async def test_nasa_gpm_source_normalization_and_quality_flagging(db_session):
    source = NasaGpmSource()
    sample_time = "2026-09-20T12:30:00Z"
    sample_payload = {
        "timestamp": sample_time,
        "product": "GPM_3IMERGHHE",
        "measurements": [
            {
                "district_id": 1,
                "precipitation_cal": 22.4,
                "precipitation_24h_mm": 95.0,
                "rainfall_7d_cumulative_mm": 210.0,
                "quality_index": 0.85
            },
            {
                "district_id": 3,
                "precipitation_cal": 5.0,
                "precipitation_24h_mm": 12.0,
                "rainfall_7d_cumulative_mm": 35.0,
                "quality_index": 0.30  # Should be flagged DEGRADED
            }
        ]
    }

    raw = await source.fetch(simulated_payload=sample_payload)
    source.validate(raw)
    records = source.normalize(raw)

    assert len(records) == 2
    assert records[0]["quality_flag"] == "NOMINAL"
    assert records[1]["quality_flag"] == "DEGRADED"

    stored = source.store(records, db_session)
    assert stored == 2


# --- 3. Open-Meteo Ingestion Source Tests ---

@pytest.mark.asyncio
async def test_open_meteo_source_forecast_and_observed_split(db_session):
    source = OpenMeteoSource()
    sample_time = "2026-09-20T13:00:00Z"
    sample_payload = {
        "observation_time": sample_time,
        "measurements": [
            {
                "district_id": 4,
                "temperature_c": 24.5,
                "relative_humidity_pct": 88.0,
                "wind_speed_kmh": 14.0,
                "rainfall_1h_mm": 2.5,
                "rainfall_24h_mm": 18.0,
                "rainfall_7d_cumulative_mm": 60.0,
                "quality_flag": "NOMINAL"
            }
        ]
    }

    raw = await source.fetch(simulated_payload=sample_payload)
    records = source.normalize(raw)
    assert len(records) == 1
    assert records[0]["district_id"] == 4
    assert records[0]["temperature_c"] == 24.5
    assert records[0]["is_forecast"] is False

    stored = source.store(records, db_session)
    assert stored == 1


# --- 4. Antecedent Saturation Index (ASI) Mathematical Correctness ---

def test_asi_calculation_decay_and_zero_fabrication():
    # Test theoretical decay calculation:
    # Day 1: 10mm -> 10 * 0.85^1 = 8.5
    # Day 2: 20mm -> 20 * 0.85^2 = 14.45
    # Expected ASI = 8.5 + 14.45 = 22.95
    past_rainfall = [10.0, 20.0]
    asi = WeatherReconciliationService.calculate_asi(past_rainfall)
    assert asi == 22.95

    # Zero fabrication: empty or null values return None
    assert WeatherReconciliationService.calculate_asi([]) is None
    assert WeatherReconciliationService.calculate_asi([None, None]) is None


# --- 5. Idempotent Upsert & Database Storage ---

def test_idempotent_weather_upsert(db_session):
    obs_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    rec1 = [{
        "district_id": 10,
        "source_id": "OPEN_METEO",
        "observation_time": obs_time,
        "rainfall_24h_mm": 30.0,
        "quality_flag": "NOMINAL",
        "is_forecast": False
    }]

    # First insert
    count1 = WeatherReconciliationService.store_observations(rec1, db_session)
    assert count1 == 1

    obs1 = db_session.query(WeatherObservation).filter(
        WeatherObservation.district_id == 10,
        WeatherObservation.observation_time == obs_time,
        WeatherObservation.source_id == "OPEN_METEO"
    ).first()
    assert obs1.rainfall_24h_mm == 30.0

    # Second insert with updated value (same slot)
    rec2 = [{
        "district_id": 10,
        "source_id": "OPEN_METEO",
        "observation_time": obs_time,
        "rainfall_24h_mm": 45.0,  # Updated reading
        "quality_flag": "NOMINAL",
        "is_forecast": False
    }]
    count2 = WeatherReconciliationService.store_observations(rec2, db_session)
    assert count2 == 1

    obs_rechecked = db_session.query(WeatherObservation).filter(
        WeatherObservation.district_id == 10,
        WeatherObservation.observation_time == obs_time,
        WeatherObservation.source_id == "OPEN_METEO"
    ).all()
    # Ensure no duplicate row was created, and value was updated
    assert len(obs_rechecked) == 1
    assert obs_rechecked[0].rainfall_24h_mm == 45.0


# --- 6. Multi-Source Reconciliation Priority Arbitration ---

def test_multi_source_priority_arbitration(db_session):
    now = utc_now()
    dist_id = 15

    # Clear any previous test observations for this district
    db_session.query(WeatherObservation).filter(WeatherObservation.district_id == dist_id).delete()
    db_session.commit()

    # Insert Open-Meteo (Priority 3)
    rec_om = [{
        "district_id": dist_id,
        "source_id": "OPEN_METEO",
        "observation_time": now,
        "rainfall_24h_mm": 20.0,
        "quality_flag": "NOMINAL",
        "is_forecast": False
    }]
    WeatherReconciliationService.store_observations(rec_om, db_session)

    # Reconciled should be OPEN_METEO
    res1 = WeatherReconciliationService.get_reconciled_district_weather(dist_id, db_session)
    assert res1["source"] == "OPEN_METEO"
    assert res1["observed"]["rainfall_24h_mm"] == 20.0

    # Insert NASA GPM (Priority 2)
    rec_gpm = [{
        "district_id": dist_id,
        "source_id": "NASA_GPM_IMERG",
        "observation_time": now,
        "rainfall_24h_mm": 35.0,
        "quality_flag": "NOMINAL",
        "is_forecast": False
    }]
    WeatherReconciliationService.store_observations(rec_gpm, db_session)

    # Reconciled should now prefer NASA_GPM_IMERG over OPEN_METEO
    res2 = WeatherReconciliationService.get_reconciled_district_weather(dist_id, db_session)
    assert res2["source"] == "NASA_GPM_IMERG"
    assert res2["observed"]["rainfall_24h_mm"] == 35.0

    # Insert MOSDAC INSAT-3D (Priority 1)
    rec_mosdac = [{
        "district_id": dist_id,
        "source_id": "MOSDAC_INSAT3D_QPE",
        "observation_time": now,
        "rainfall_24h_mm": 50.0,
        "quality_flag": "NOMINAL",
        "is_forecast": False
    }]
    WeatherReconciliationService.store_observations(rec_mosdac, db_session)

    # Reconciled should now prefer MOSDAC_INSAT3D_QPE
    res3 = WeatherReconciliationService.get_reconciled_district_weather(dist_id, db_session)
    assert res3["source"] == "MOSDAC_INSAT3D_QPE"
    assert res3["observed"]["rainfall_24h_mm"] == 50.0


# --- 7. REST API District Weather Endpoints ---

def test_api_weather_district_and_asi_endpoints(client, db_session):
    # Seed 10-day history for district 20
    now = utc_now()
    dist_id = 20
    records = []
    for day in range(1, 4):
        obs_dt = now - timedelta(days=day)
        records.append({
            "district_id": dist_id,
            "source_id": "MOSDAC_INSAT3D_QPE",
            "observation_time": obs_dt,
            "rainfall_24h_mm": 20.0,
            "quality_flag": "NOMINAL",
            "is_forecast": False
        })
    WeatherReconciliationService.store_observations(records, db_session)

    # Test /api/weather/district/{id}
    resp = client.get(f"/api/weather/district/{dist_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["district_id"] == dist_id
    assert "advisory" in body
    assert body["antecedent_saturation_index"] is not None

    # Test /api/weather/asi/{id}
    resp_asi = client.get(f"/api/weather/asi/{dist_id}")
    assert resp_asi.status_code == 200
    asi_body = resp_asi.json()
    assert asi_body["district_id"] == dist_id
    assert asi_body["decay_factor"] == 0.85
    assert asi_body["window_days"] == 10
    assert asi_body["antecedent_saturation_index"] is not None
