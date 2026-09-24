# LANDSAFE-NER — Memory Overflow Issue Report & Fix Instructions

> **For AI Agent:** The Render free tier server crashed with "exceeded its memory limit". This report explains WHY it happened, HOW to fix it, and HOW to prevent it in the future. Fix all issues in order.

---

## The Problem

Render sent this email:
> **"Web Service AI-land-slide-alert exceeded its memory limit"**
> An instance of your Web Service exceeded its memory limit, which triggered an automatic restart. While restarting, the instance was temporarily unavailable.

**Render free tier limit: 512 MB RAM**

---

## Root Cause Analysis — 5 Memory Leaks Found

### Leak 1: Unbounded In-Memory Caches (BIGGEST PROBLEM)

**Files:** `backend/app/services/weather_service.py` line 59, `backend/app/services/satellite_service.py` line 23

The weather and satellite caches are Python dicts that **grow forever** — old entries are never evicted:

```python
# weather_service.py line 59:
_WEATHER_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}

# satellite_service.py line 23:
_SAT_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
```

**Why this causes OOM:**
- With 788 locations, each weather response is ~5-10 KB → weather cache alone = ~8 MB
- Each satellite response is ~3 KB → satellite cache = ~2.4 MB
- The `_LAST_SUCCESS` dict (line 55) also grows unbounded
- Expired entries stay in memory forever (TTL only controls refetch, NOT eviction)
- Over hours/days of operation, cache accumulates all unique lat/lon queries
- With `round(lat, 4)` precision, every tiny coordinate difference creates a new entry

**Fix — Add cache eviction with max size:**

In `backend/app/services/weather_service.py`, replace lines 57-60:

```python
# BEFORE:
# 30-minute in-memory TTL cache: (round(lat, 4), round(lon, 4)) -> (timestamp, parsed_data)
import time
_WEATHER_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
WEATHER_CACHE_TTL_SECONDS: float = 30.0 * 60.0  # 30 minutes

# AFTER — Bounded LRU-style cache with eviction:
import time
_WEATHER_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
WEATHER_CACHE_TTL_SECONDS: float = 30.0 * 60.0  # 30 minutes
_WEATHER_CACHE_MAX_SIZE: int = 200  # Max 200 entries (~2 MB)

def _evict_weather_cache() -> None:
    """Remove expired entries and enforce max size."""
    now = time.time()
    # Remove expired
    expired = [k for k, (ts, _) in _WEATHER_CACHE.items() if (now - ts) > WEATHER_CACHE_TTL_SECONDS]
    for k in expired:
        del _WEATHER_CACHE[k]
    # If still too large, remove oldest
    if len(_WEATHER_CACHE) > _WEATHER_CACHE_MAX_SIZE:
        sorted_keys = sorted(_WEATHER_CACHE.keys(), key=lambda k: _WEATHER_CACHE[k][0])
        for k in sorted_keys[:len(_WEATHER_CACHE) - _WEATHER_CACHE_MAX_SIZE]:
            del _WEATHER_CACHE[k]
```

Then in `fetch_live_weather()`, call `_evict_weather_cache()` at the START of the function (before the cache check at line 93):

```python
async def fetch_live_weather(lat: float, lon: float) -> dict[str, Any]:
    global _LAST_REQUEST_TIME
    _evict_weather_cache()  # <-- ADD THIS LINE
    cache_key = (round(lat, 1), round(lon, 1))  # Also change from 4 to 1 decimal
    # ... rest unchanged ...
```

**Do the same for satellite cache** in `backend/app/services/satellite_service.py`. Replace line 22-24:

```python
# BEFORE:
_SAT_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
SAT_CACHE_TTL_SECONDS: float = 30.0 * 60.0

# AFTER:
_SAT_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
SAT_CACHE_TTL_SECONDS: float = 30.0 * 60.0
_SAT_CACHE_MAX_SIZE: int = 150

def _evict_sat_cache() -> None:
    """Remove expired entries and enforce max size."""
    now = time.time()
    expired = [k for k, (ts, _) in _SAT_CACHE.items() if (now - ts) > SAT_CACHE_TTL_SECONDS]
    for k in expired:
        del _SAT_CACHE[k]
    if len(_SAT_CACHE) > _SAT_CACHE_MAX_SIZE:
        sorted_keys = sorted(_SAT_CACHE.keys(), key=lambda k: _SAT_CACHE[k][0])
        for k in sorted_keys[:len(_SAT_CACHE) - _SAT_CACHE_MAX_SIZE]:
            del _SAT_CACHE[k]
```

Call `_evict_sat_cache()` at the start of `get_satellite_observation()` (before line 346).

Also add eviction for `_LAST_SUCCESS` dict in weather_service.py (line 55) — cap it at 200 entries.

---

### Leak 2: Creating New httpx.AsyncClient For EVERY Request (11 Instances)

**Files:** `satellite_service.py` lines 96, 162, 203, 269, 323; `weather_service.py` line 122; `mosdac_insat3d.py` lines 58, 81; `nasa_gpm.py` line 59

Every API call creates `async with httpx.AsyncClient(...) as client:` — this allocates a new SSL context, connection pool, and buffers each time. With concurrent requests, this can spike memory to 100+ MB.

**The satellite service is the worst offender** — `get_satellite_observation()` calls 3 functions concurrently via `asyncio.gather()`, each creating its own httpx client. The Sentinel-2 function creates TWO clients (one for token, one for data). That's **5 httpx clients created per satellite request**.

**Fix — Use a shared reusable httpx client:**

Add a module-level shared client in `backend/app/services/satellite_service.py`. Add after line 20:

```python
# Shared HTTP client — reused across all satellite requests to save memory
_SHARED_HTTP_CLIENT: Optional[httpx.AsyncClient] = None

async def _get_http_client() -> httpx.AsyncClient:
    """Get or create a shared HTTP client."""
    global _SHARED_HTTP_CLIENT
    if _SHARED_HTTP_CLIENT is None or _SHARED_HTTP_CLIENT.is_closed:
        _SHARED_HTTP_CLIENT = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
        )
    return _SHARED_HTTP_CLIENT
```

Then replace ALL `async with httpx.AsyncClient(timeout=...) as client:` blocks in the file with:

```python
client = await _get_http_client()
# Use client directly without 'async with' — it stays open
```

Do the same in `backend/app/services/weather_service.py` — add a shared client and reuse it.

---

### Leak 3: SHAP TreeExplainer Loads Entire Model Copy Into Memory

**File:** `backend/app/services/ml_service.py` lines 49-53

```python
_SHAP_EXPLAINER = shap.TreeExplainer(_LANDSLIDE_MODEL)
```

`shap.TreeExplainer` creates an internal copy of the XGBoost model's tree structure. Combined with the model itself:

| Component | Size on Disk | Approx. RAM |
|---|---|---|
| `best_landslide_model.joblib` | 0.6 MB | ~2-5 MB |
| `flood_model.joblib` | 3.7 MB | ~15-30 MB |
| `preprocessor.joblib` | 7 KB | ~0.1 MB |
| SHAP TreeExplainer (copy of landslide model) | — | ~5-10 MB |
| numpy/pandas/shap/xgboost libraries | — | ~100-150 MB |

**Total ML overhead: ~130-200 MB** out of 512 MB budget.

**Fix — Make SHAP explainer lazy (only create when needed):**

```python
# BEFORE (line 49-53):
            try:
                _SHAP_EXPLAINER = shap.TreeExplainer(_LANDSLIDE_MODEL)
            except Exception as e:
                print(f"Warning initializing SHAP explainer: {e}")

# AFTER — lazy initialization:
            # Don't create SHAP explainer at startup — it duplicates the model in memory.
            # It will be created on first use in predict_risk().
            _SHAP_EXPLAINER = None  # Lazy — created on first SHAP request
```

Then in the function that uses `_SHAP_EXPLAINER` (likely `predict_risk()`), add lazy init:

```python
def _get_shap_explainer():
    global _SHAP_EXPLAINER
    if _SHAP_EXPLAINER is None and _LANDSLIDE_MODEL is not None:
        try:
            _SHAP_EXPLAINER = shap.TreeExplainer(_LANDSLIDE_MODEL)
        except Exception:
            pass
    return _SHAP_EXPLAINER
```

---

### Leak 4: Simulation Endpoint Creates 40+ Concurrent API Calls

**File:** `backend/app/api/routes.py` lines 446-479

The logs showed **40+ consecutive** `/api/simulation` calls in 2 minutes. Each simulation call:
1. Calls `fetch_live_weather()` → creates new httpx client → Open-Meteo request
2. Weather returns 429 → creates error response object
3. Total: 40 httpx clients + 40 weather response dicts + 40 satellite cache lookups

**Fix — Cache simulation weather and add request debouncing:**

Replace lines 459 in `backend/app/api/routes.py`:

```python
# BEFORE (line 459):
    weather = await fetch_live_weather(loc["latitude"], loc["longitude"])

# AFTER — use cached weather, don't fetch fresh for simulation:
    # Simulation uses cached weather only — never triggers new API calls
    cache_key = (round(loc["latitude"], 1), round(loc["longitude"], 1))
    now_ts = time.time()
    from backend.app.services.weather_service import _WEATHER_CACHE, WEATHER_CACHE_TTL_SECONDS
    if cache_key in _WEATHER_CACHE:
        cached_time, cached_val = _WEATHER_CACHE[cache_key]
        if (now_ts - cached_time) < WEATHER_CACHE_TTL_SECONDS * 2:  # Use wider window for simulation
            weather = cached_val
        else:
            weather = await fetch_live_weather(loc["latitude"], loc["longitude"])
    else:
        weather = await fetch_live_weather(loc["latitude"], loc["longitude"])
```

Add `import time` at the top of routes.py if not already present.

---

### Leak 5: Scheduler Ingestion Cycles Accumulate Failed Retries In Memory

**Files:** `backend/app/ingestion/base.py` line 201, scheduler runs every 30 min

The scheduler fires MOSDAC and NASA GPM every 30 minutes. Each cycle:
- Creates 3 httpx clients per source (3 retries)
- MOSDAC → 3 retries × 404 response = wasted connections
- NASA GPM → 3 retries × 404 response = wasted connections
- Open-Meteo → 2 retries × 429 response = wasted connections

**That's 8 httpx clients created every 30 minutes that ALL fail.**

**Fix — Disable the broken ingestion sources until URLs are fixed:**

In `backend/app/ingestion/sources/weather/mosdac_insat3d.py`, add at the start of `fetch()`:

```python
    async def fetch(self, **kwargs) -> Dict[str, Any]:
        simulated_payload = kwargs.get("simulated_payload")
        if simulated_payload is not None:
            return simulated_payload

        # Guard: skip if no auth token (prevents repeated 404 error spam)
        if not self.auth_token:
            raise SourceFetchError(
                "MOSDAC_AUTH_TOKEN is empty. Skipping fetch to conserve memory and prevent error spam. "
                "Set MOSDAC_AUTH_TOKEN in environment to enable."
            )
        
        # ... rest of existing fetch code ...
```

In `backend/app/ingestion/sources/weather/nasa_gpm.py`, add the same guard:

```python
    async def fetch(self, **kwargs) -> Dict[str, Any]:
        simulated_payload = kwargs.get("simulated_payload")
        if simulated_payload is not None:
            return simulated_payload

        # Guard: API endpoint is a placeholder. Skip until real URL is configured.
        if "gpm.nasa.gov/api/v1/imerg" in self.api_endpoint:
            raise SourceFetchError(
                "NASA GPM API endpoint is a placeholder URL (returns 404). "
                "Update NASA_GPM_API_ENDPOINT to the real GES DISC endpoint."
            )
        
        # ... rest of existing fetch code ...
```

---

## Memory Budget After Fixes

| Component | Before Fix | After Fix |
|---|---|---|
| Python + FastAPI + uvicorn | ~80 MB | ~80 MB (unchanged) |
| numpy/pandas/xgboost/shap imports | ~120 MB | ~120 MB (unchanged) |
| ML models (landslide + flood) | ~35 MB | ~35 MB (unchanged) |
| SHAP explainer | ~10 MB at startup | **0 MB** (lazy) |
| Weather cache (unbounded) | ~10-50 MB (grows) | **~2 MB** (capped at 200) |
| Satellite cache (unbounded) | ~5-20 MB (grows) | **~1 MB** (capped at 150) |
| httpx clients (per request) | ~5-20 MB (spikes) | **~2 MB** (shared client) |
| Scheduler failed retries | ~5 MB (every 30 min) | **~0 MB** (guarded) |
| **TOTAL** | **~270-375 MB** (grows to 512+) | **~240 MB** (stable) |

---

## How To Prevent This In The Future

### Rule 1: Never Use Unbounded Dicts as Caches
Always add a max size and eviction policy. Use `functools.lru_cache` or a bounded dict.

### Rule 2: Never Create httpx.AsyncClient Inside Loops
Create ONE shared client at module level and reuse it. Each client allocates ~2-5 MB.

### Rule 3: Don't Retry Failed API Calls That Will Always Fail
If MOSDAC returns 404 (URL doesn't exist), retrying 3 times every 30 minutes forever wastes memory. Add circuit breakers.

### Rule 4: Lazy-Load Heavy Libraries
Don't initialize SHAP explainer at startup. Create it on first use.

### Rule 5: Add Memory Monitoring
Add a `/debug/memory` endpoint to track memory usage:

```python
# Add to routes.py:
import resource
import sys

@router.get("/debug/memory")
async def memory_usage():
    """Report current memory usage for debugging."""
    import psutil
    process = psutil.Process()
    mem = process.memory_info()
    return {
        "rss_mb": round(mem.rss / 1024 / 1024, 1),
        "vms_mb": round(mem.vms / 1024 / 1024, 1),
        "weather_cache_entries": len(_WEATHER_CACHE),
        "satellite_cache_entries": len(_SAT_CACHE),
    }
```

Add `psutil` to `requirements.txt`.

---

## Fix Priority (Do In This Order)

| # | Fix | Memory Saved | Effort |
|---|---|---|---|
| 🥇 **1** | Add cache eviction + max size (Leak 1) | ~20-50 MB | Change 2 files, ~30 lines |
| 🥇 **2** | Use shared httpx client (Leak 2) | ~10-20 MB | Change 2 files, ~20 lines |
| 🥇 **3** | Guard broken ingestion sources (Leak 5) | ~5 MB + stops error spam | Change 2 files, ~10 lines |
| 🥈 **4** | Make SHAP explainer lazy (Leak 3) | ~10 MB | Change 1 file, ~10 lines |
| 🥈 **5** | Cache-only weather for simulation (Leak 4) | ~5-10 MB during spikes | Change 1 file, ~10 lines |
| 🥉 **6** | Add memory monitoring endpoint | 0 MB (diagnostic) | Add 1 endpoint |

---

## Quick Verification After Fixes

After implementing all fixes, verify:

1. Deploy to Render
2. Wait 30 min — check logs for no more MOSDAC/GPM 404 errors
3. Open the website, click through 10+ locations
4. Check memory: `GET /debug/memory` — should be under 300 MB
5. Wait 2 hours — memory should stay stable, not grow
6. No more "exceeded memory limit" emails from Render

---

*Report generated 25 September 2026. Root cause: unbounded in-memory caches + new httpx client per request + broken scheduler retries.*
