"""Base Ingestion Framework Class & Lifecycle Management (Milestone 2)

Provides:
1. Standardized pipeline: Rate Limit -> Fetch -> Validate -> Normalize -> Store -> Update Health
2. Exponential backoff and retry handling on network errors
3. Robust error classification and DB health state transitions (FRESH, DEGRADED, OFFLINE)
4. Audit-proof execution reporting with zero synthetic fallbacks
"""
import abc
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.core.freshness import freshness_tier
from backend.app.ingestion.rate_limiter import RateLimiter, get_rate_limiter
from backend.app.models.db_models import DataSource, SourceHealth, utc_now

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Base exception for all ingestion lifecycle errors."""
    pass


class RateLimitExceededError(IngestionError):
    """Raised when rate limiter daily quota or burst limit is exhausted."""
    pass


class SourceValidationError(IngestionError):
    """Raised when provider payload fails structural or integrity validation."""
    pass


class SourceFetchError(IngestionError):
    """Raised when network fetch fails after all retry attempts."""
    pass


class BaseSource(abc.ABC):
    """Abstract Base Class for all external data provider ingestors."""

    source_id: str
    name: str
    provider: str
    cadence_minutes: int
    licence: str
    api_endpoint: Optional[str] = None
    is_active: bool = True
    pass_based: bool = False
    max_retries: int = 3
    retry_backoff_base_s: float = 0.5  # Base seconds for exponential backoff

    def __init__(self):
        if not hasattr(self, "source_id") or not self.source_id:
            raise ValueError("BaseSource subclass must define a non-empty `source_id`")
        self.rate_limiter: RateLimiter = get_rate_limiter(self.source_id)

    @abc.abstractmethod
    async def fetch(self, **kwargs) -> Any:
        """Perform provider network request with authentication and parameters.
        Must raise an exception if network or HTTP request fails.
        """
        pass

    def validate(self, raw_data: Any) -> bool:
        """Validate raw incoming payload. Returns True if valid, raises SourceValidationError otherwise."""
        if raw_data is None:
            raise SourceValidationError(f"[{self.source_id}] Payload is null/empty")
        if isinstance(raw_data, (list, dict)) and len(raw_data) == 0:
            raise SourceValidationError(f"[{self.source_id}] Payload collection is empty")
        return True

    @abc.abstractmethod
    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Transform raw provider data into internal model-ready dictionaries."""
        pass

    def store(self, records: List[Dict[str, Any]], db: Session) -> int:
        """Persist normalized records to the database. Override in specific ingestors if custom upserts are needed."""
        # Default pass-through (e.g. for sub-services that handle their own direct inserts)
        return len(records)

    def update_health(
        self,
        db: Session,
        is_success: bool,
        latency_ms: float,
        last_attempt_status: str,
        target_status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> SourceHealth:
        """Update source health record in database with execution outcome."""
        health = db.query(SourceHealth).filter(SourceHealth.source_id == self.source_id).first()
        if not health:
            # Check if DataSource exists, if not create DataSource record first to satisfy foreign key
            ds = db.query(DataSource).filter(DataSource.id == self.source_id).first()
            if not ds:
                ds = DataSource(
                    id=self.source_id,
                    name=getattr(self, "name", self.source_id),
                    provider=getattr(self, "provider", "Unknown"),
                    cadence_minutes=getattr(self, "cadence_minutes", 60),
                    licence=getattr(self, "licence", "Open Data"),
                    api_endpoint=getattr(self, "api_endpoint", None),
                    is_active=self.is_active
                )
                db.add(ds)
                db.flush()

            health = SourceHealth(
                source_id=self.source_id,
                status="FRESH" if is_success else "OFFLINE",
                last_successful_fetch=utc_now() if is_success else None,
                last_attempt_status=last_attempt_status,
                consecutive_failures=0 if is_success else 1,
                average_latency_ms=latency_ms
            )
            db.add(health)
        else:
            if is_success:
                health.status = target_status or "FRESH"
                health.last_successful_fetch = utc_now()
                health.consecutive_failures = 0
                health.last_attempt_status = last_attempt_status or "SUCCESS"
                # Exponential moving average for latency
                if health.average_latency_ms and health.average_latency_ms > 0:
                    health.average_latency_ms = round(health.average_latency_ms * 0.7 + latency_ms * 0.3, 2)
                else:
                    health.average_latency_ms = round(latency_ms, 2)
            else:
                health.consecutive_failures = (health.consecutive_failures or 0) + 1
                health.status = target_status or ("DEGRADED" if health.consecutive_failures < 3 else "OFFLINE")
                health.last_attempt_status = f"FAILED: {error_message or last_attempt_status}"
                health.average_latency_ms = round(latency_ms, 2)

        health.updated_at = utc_now()
        db.commit()
        db.refresh(health)
        return health

    async def run_cycle(self, db: Optional[Session] = None, **kwargs) -> Dict[str, Any]:
        """Execute a full ingestion cycle with rate limiting, retries, validation, and health recording."""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        start_time = time.perf_counter()
        cycle_result: Dict[str, Any] = {
            "source_id": self.source_id,
            "success": False,
            "records_count": 0,
            "latency_ms": 0.0,
            "status": "UNKNOWN",
            "error": None
        }

        try:
            # 1. Rate Limiting Check
            if not await self.rate_limiter.acquire_async(1):
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                cycle_result["latency_ms"] = round(latency_ms, 2)
                cycle_result["status"] = "RATE_LIMITED"
                cycle_result["error"] = f"Rate limit / daily budget exhausted for {self.source_id}"
                logger.warning("[Ingestion:%s] Rate limit quota exhausted", self.source_id)
                self.update_health(
                    db=db,
                    is_success=False,
                    latency_ms=latency_ms,
                    last_attempt_status="RATE_LIMIT_EXCEEDED",
                    target_status="DEGRADED",
                    error_message=cycle_result["error"]
                )
                return cycle_result

            # 2. Fetch with Retries & Exponential Backoff
            raw_data = None
            last_fetch_error = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug("[Ingestion:%s] Fetch attempt %d/%d", self.source_id, attempt, self.max_retries)
                    raw_data = await self.fetch(**kwargs)
                    break
                except Exception as ex:
                    last_fetch_error = ex
                    logger.warning(
                        "[Ingestion:%s] Fetch attempt %d/%d failed: %s",
                        self.source_id, attempt, self.max_retries, str(ex)
                    )
                    if attempt < self.max_retries:
                        backoff = self.retry_backoff_base_s * (2 ** (attempt - 1))
                        await asyncio.sleep(backoff)

            if raw_data is None and last_fetch_error is not None:
                raise SourceFetchError(f"Failed after {self.max_retries} attempts: {str(last_fetch_error)}")

            # 3. Validation
            self.validate(raw_data)

            # 4. Normalization
            records = self.normalize(raw_data)

            # 5. DB Persistence
            stored_count = self.store(records, db)

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            cycle_result["success"] = True
            cycle_result["records_count"] = stored_count
            cycle_result["latency_ms"] = round(latency_ms, 2)
            cycle_result["status"] = "FRESH"

            # 6. Update Health in DB
            self.update_health(
                db=db,
                is_success=True,
                latency_ms=latency_ms,
                last_attempt_status="SUCCESS",
                target_status="FRESH"
            )
            logger.info(
                "[Ingestion:%s] Successfully ingested %d records in %.1fms",
                self.source_id, stored_count, latency_ms
            )

        except Exception as err:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = str(err)
            cycle_result["success"] = False
            cycle_result["latency_ms"] = round(latency_ms, 2)
            cycle_result["error"] = error_msg
            cycle_result["status"] = "OFFLINE"

            logger.error("[Ingestion:%s] Cycle failed: %s", self.source_id, error_msg, exc_info=True)
            self.update_health(
                db=db,
                is_success=False,
                latency_ms=latency_ms,
                last_attempt_status="FAILED",
                error_message=error_msg
            )
        finally:
            if should_close_db:
                db.close()

        return cycle_result
