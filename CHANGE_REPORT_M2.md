# Milestone 2 Audit & Completion Report: Ingestion Framework & Scheduler

**Project:** LANDSAFE-NER (Multi-Hazard Early Warning System)  
**Milestone:** M2 — Ingestion Framework & Multi-Source Scheduling  
**Date:** September 20, 2026  
**Status:** Completed & 100% Verified (81/81 Tests Passing)

---

## 1. Executive Summary

Milestone 2 establishes the autonomous, resilient data ingestion backbone for the LANDSAFE platform. In accordance with the system architecture and academic non-commercial licensing requirements, this framework ensures:
1. **Rate Limiting & Quota Guards:** Strict token-bucket rate limiting preventing provider bans across free tiers (e.g. Open-Meteo <10,000 calls/day, NASA FIRMS, USGS FDSN).
2. **Standardized Ingestion Lifecycle:** The `BaseSource` pipeline (`fetch` $\rightarrow$ `validate` $\rightarrow$ `normalize` $\rightarrow$ `store` $\rightarrow$ `update_health`) with exponential backoff retry mechanics.
3. **Verification Gating (`PENDING_VERIFICATION`):** Unverified providers (such as NISAR S-SAR or Resourcesat LISS) are strictly blocked from scheduling and execution until credentials and API schemas are confirmed.
4. **Resilient Periodic Scheduling:** Integrated APScheduler `AsyncIOScheduler` executing background ingestion jobs aligned with provider cadences while isolating job failures.
5. **Real-time Observability API:** REST endpoints (`/api/sources`, `/api/sources/{id}/health`, `/api/sources/{id}/trigger`) exposing live health status, latency moving averages, and quota counters.

---

## 2. Deliverables & Architectural Components

### 2.1 Per-Source Rate Limiting (`backend/app/ingestion/rate_limiter.py`)
- Client-side burst control with minimum call interval spacing.
- Daily budget tracking with automatic UTC midnight rollover.
- Asynchronous acquisition (`acquire_async`) avoiding event-loop thread blocking.
- Configured defaults:
  - `OPEN_METEO`: 10,000 calls/day (5 req/sec burst limit)
  - `USGS_FDSN`: 50,000 calls/day (2 req/sec burst limit)
  - `NASA_GPM_IMERG`: 20,000 calls/day (5 req/sec burst limit)
  - `NASA_FIRMS`: 10,000 calls/day (1 req/sec burst limit)
  - `MOSDAC_INSAT3D_QPE`: 10,000 calls/day (2 req/sec burst limit)
  - `COPERNICUS_S1_SAR` / `COPERNICUS_S2_OPTICAL`: 5,000 calls/day (1 req/sec)

### 2.2 Standard Ingestion Base Class (`backend/app/ingestion/base.py`)
- Abstract base class `BaseSource` defining contract methods:
  - `async fetch(**kwargs) -> Any`: Provider network request with retry and exponential backoff.
  - `validate(raw_data) -> bool`: Structural integrity validation; rejects null/empty/corrupt payloads.
  - `normalize(raw_data) -> List[Dict[str, Any]]`: Transformation to internal database schemas.
  - `store(records, db) -> int`: Persists records to database tables.
  - `update_health(...) -> SourceHealth`: Updates DB health record (`FRESH`, `DEGRADED`, `OFFLINE`).
  - `async run_cycle(...) -> Dict[str, Any]`: Orchestrates full cycle with rate-limit check, latency measurement, and health tracking.

### 2.3 Provider Registry & Verification Gating (`backend/app/ingestion/registry.py`)
- Case-insensitive source lookup and registration.
- Active source filtering enforcing `PENDING_VERIFICATION` gating.
- Prevents unverified sources (e.g. NISAR S-SAR, Resourcesat LISS) from executing automated jobs.

### 2.4 Ingestion Scheduler (`backend/app/ingestion/scheduler.py`)
- Wraps APScheduler `AsyncIOScheduler` in UTC timezone.
- Maps each active source to its interval cadence (in minutes).
- Provides administrative controls: `start()`, `shutdown()`, `pause_source()`, `resume_source()`, `trigger_now()`, and `get_jobs_status()`.
- Integrated cleanly into FastAPI `lifespan` in `backend/app/main.py` gated by `settings.SCHEDULER_AUTOSTART`.

### 2.5 Monitoring REST Endpoints (`backend/app/api/routes.py`)
- `GET /api/sources`: Returns all 9 registered sources with database health, cadence, provider details, and quota status.
- `GET /api/sources/{source_id}/health`: Detailed health, consecutive failure count, latency average, and rate limit counters for a single source.
- `POST /api/sources/{source_id}/trigger`: On-demand manual ingestion cycle trigger with execution feedback.

---

## 3. Verification & Test Suite Results

The comprehensive test suite in `tests/test_ingestion_framework.py` verifies all components:

| Test Case | Component | Verification Objective | Result |
| :--- | :--- | :--- | :--- |
| `test_rate_limiter_quota_and_burst` | RateLimiter | Enforces daily budget cap and burst throttling | **PASSED** |
| `test_rate_limiter_async_acquire` | RateLimiter | Async quota acquisition without event loop block | **PASSED** |
| `test_rate_limiter_rollover` | RateLimiter | Daily rollover resets usage at UTC midnight | **PASSED** |
| `test_base_source_successful_cycle` | BaseSource | Nominal pipeline run & DB health status -> `FRESH` | **PASSED** |
| `test_base_source_failing_cycle_retries_and_health_transition` | BaseSource | Exponential backoff retry & transition to `OFFLINE` | **PASSED** |
| `test_base_source_rate_limit_exceeded` | BaseSource | Rate limit check returns `RATE_LIMITED` gracefully | **PASSED** |
| `test_registry_registration_and_verification_gating` | SourceRegistry | Gating blocks unverified sources in `PENDING_VERIFICATION` | **PASSED** |
| `test_scheduler_lifecycle_and_trigger` | IngestionScheduler | Scheduler start, job addition, pause/resume, and trigger | **PASSED** |
| `test_scheduler_blocks_unverified_trigger` | IngestionScheduler | Blocks manual trigger on unverified source | **PASSED** |
| `test_api_sources_list` | REST API | `GET /api/sources` returns all data sources and health | **PASSED** |
| `test_api_source_health_detail` | REST API | `GET /api/sources/OPEN_METEO/health` returns quota | **PASSED** |
| `test_api_source_health_404` | REST API | `GET /api/sources/INVALID/health` returns 404 | **PASSED** |
| `test_api_source_trigger_endpoint` | REST API | `POST /api/sources/{id}/trigger` runs cycle | **PASSED** |

### Complete Test Run Status
```
======================= 81 passed, 6 warnings in 29.20s =======================
```
- Total test cases: **81**
- Passed: **81 (100% green)**
- Regressions / Breakages: **0**
- Contract stability: **All 15 `/api` endpoints verified**

---

## 4. Next Milestone Transition (M3: Weather Ingestion)

With M2 successfully verified and committed, the ingestion framework is ready to onboard live weather data ingestors in Milestone 3:
- **Priority 1:** MOSDAC INSAT-3D/3DR QPE rainfall half-hourly raster fetcher.
- **Priority 2:** NASA GPM IMERG half-hourly precipitation fetcher.
- **Priority 3:** Open-Meteo 24h observed rainfall and 5-day forecast fetcher.
- Persisting incoming time-series into `weather_observations` table with spatial foreign key mapping to `districts`.
