# LANDSAFE-NER — Issue Report for AI Implementation

> **Instructions for AI:** Fix each issue below in order. Do NOT skip any. Each issue has the exact file path, the current broken code, and what to replace it with. After fixing all issues, run the backend and verify the fixes work.

---

## Issue 1: `satellite_service.py` Is Hardcoded to Return NULL — Must Call Real APIs

**File:** `backend/app/services/satellite_service.py`  
**Problem:** The function `get_satellite_observation()` always returns `null` for every satellite value in production mode. It never calls any satellite API. The Copernicus CDSE credentials (`CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`), NASA FIRMS key (`NASA_FIRMS_MAP_KEY`), and NASA Earthdata credentials (`EARTHDATA_TOKEN`) are already configured in the environment but the code never uses them.

**What to do:** Rewrite the entire `backend/app/services/satellite_service.py` file. The new version must:

1. Make `get_satellite_observation()` an `async` function
2. Fetch **NDVI** and **bare soil %** from Copernicus Sentinel-2 L2A using the CDSE Statistical API (`https://sh.dataspace.copernicus.eu/api/v1/statistics`) with OAuth2 client credentials from `settings.CDSE_CLIENT_ID` and `settings.CDSE_CLIENT_SECRET`
3. Fetch **active fire hotspots** from NASA FIRMS API (`https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/...`) using `settings.NASA_FIRMS_MAP_KEY`
4. Keep a 30-minute in-memory TTL cache keyed by `(round(lat,3), round(lon,3))` to avoid excessive API calls
5. If all satellite APIs fail, return the existing `no_data(...)` fallback with all values as `None`
6. Keep the existing `is_demo()` branch unchanged
7. Keep `SATELLITE_MAP_LAYERS` and `PENDING_INDEX_LAYERS` dicts unchanged
8. Keep `get_available_layers()` function unchanged
9. For snow_cover_pct, snowmelt_rate, flood_extent_flag, farm_change_flag — leave as `None` with a comment saying these require Sentinel-1 SAR (future work)

**Important:** Since the function becomes `async`, you must also update every call site in `backend/app/api/routes.py`:
- Line 244: `satellite = get_satellite_observation(loc)` → `satellite = await get_satellite_observation(loc)`
- Line 324: `satellite = get_satellite_observation(loc)` → `satellite = await get_satellite_observation(loc)`
- Line 354: `sat = get_satellite_observation(loc)` → `sat = await get_satellite_observation(loc)`
- Line 450: `satellite = get_satellite_observation(loc)` → `satellite = await get_satellite_observation(loc)`

Also in `backend/app/models/schema.py`, the `SatelliteInfoResponse` model may need a `fire_detected` field added (Optional[bool]).

---

## Issue 2: Ingestion Scheduler Is Disabled — Add `SCHEDULER_AUTOSTART` to Render

**File:** `backend/app/core/config.py` line 45  
**Problem:** `SCHEDULER_AUTOSTART: bool = False` — the background scheduler that fetches data from MOSDAC, NASA GPM, USGS etc. never starts. The env var `SCHEDULER_AUTOSTART` is also missing from Render environment.

**What to do:**  
Change line 45 in `backend/app/core/config.py`:

```python
# BEFORE:
SCHEDULER_AUTOSTART: bool = False

# AFTER:
SCHEDULER_AUTOSTART: bool = os.getenv("SCHEDULER_AUTOSTART", "false").lower() in ("true", "1", "yes")
```

Add `import os` at the top if not already present.  
This lets the Render environment variable `SCHEDULER_AUTOSTART=true` control it without hardcoding.

---

## Issue 3: Open-Meteo Gets Rate-Limited (HTTP 429) — Add Throttling

**File:** `backend/app/services/weather_service.py`  
**Problem:** Open-Meteo free tier returns HTTP 429 (Too Many Requests). When weather fails, ML predictions also fail because `rainfall_24h` is mandatory.

**What to do:**

1. Increase cache TTL from 15 minutes to 30 minutes:

```python
# BEFORE (line 60):
WEATHER_CACHE_TTL_SECONDS: float = 15.0 * 60.0  # 15 minutes

# AFTER:
WEATHER_CACHE_TTL_SECONDS: float = 30.0 * 60.0  # 30 minutes
```

2. Add a global asyncio semaphore and minimum request interval right after the cache dict (around line 60):

```python
import asyncio as _asyncio
_OPEN_METEO_SEMAPHORE = _asyncio.Semaphore(2)  # Max 2 concurrent Open-Meteo requests
_LAST_OM_REQUEST_TS: float = 0.0
_MIN_OM_INTERVAL_S: float = 1.0  # At least 1 second between requests
```

3. Wrap the HTTP request section inside `fetch_live_weather()` with the semaphore and delay:

```python
async def fetch_live_weather(lat: float, lon: float) -> dict[str, Any]:
    # ... existing cache check code stays the same ...

    global _LAST_OM_REQUEST_TS
    async with _OPEN_METEO_SEMAPHORE:
        now_mono = time.monotonic()
        wait = _MIN_OM_INTERVAL_S - (now_mono - _LAST_OM_REQUEST_TS)
        if wait > 0:
            await asyncio.sleep(wait)
        _LAST_OM_REQUEST_TS = time.monotonic()

        # ... existing retry loop and HTTP fetch code ...
```

---

## Issue 4: Frontend Fallback Has D3 Rainfall Bug — Overstates 24h Rainfall

**File:** `frontend/src/services/api.js` lines 69–72  
**Problem:** When the Render backend is sleeping, the frontend fetches weather directly from Open-Meteo. It uses position-based array slicing (`hourlyPrecip.slice(-24)`) which includes FUTURE forecast hours, overstating rainfall by 2–5x. The backend fixed this (D3 fix) but the frontend fallback was never fixed.

**What to do:** Replace lines 69–72 in `frontend/src/services/api.js`:

```javascript
// BEFORE (BUGGY):
// 24h rainfall sum from recent 24 hourly records
const hourlyPrecip = hourly.precipitation || [];
const recent24 = hourlyPrecip.slice(Math.max(0, hourlyPrecip.length - 24));
const rainfall24h = Math.round((recent24.reduce((a, b) => a + (Number(b) || 0), 0)) * 10) / 10;

// AFTER (FIXED — timestamp-based windowing matching backend D3 fix):
// 24h rainfall sum using timestamp comparison (D3 fix)
const hourlyTimes = hourly.time || [];
const hourlyPrecip = hourly.precipitation || [];
const nowDt = new Date(current.time || Date.now());
const past24hDt = new Date(nowDt.getTime() - 24 * 60 * 60 * 1000);
let rainfall24h = 0;
for (let i = 0; i < hourlyTimes.length; i++) {
  const t = new Date(hourlyTimes[i]);
  if (t > past24hDt && t <= nowDt && hourlyPrecip[i] != null) {
    rainfall24h += Number(hourlyPrecip[i]) || 0;
  }
}
rainfall24h = Math.round(rainfall24h * 10) / 10;
```

---

## Issue 5: Frontend Fabricates Risk Categories on Map — Hardcoded Constants

**File:** `frontend/src/App.jsx` lines 75–98  
**Problem:** The dashboard map shows High/Moderate/Low risk pins with hardcoded hazard indices (0.78, 0.44, 0.12) fabricated from slope/elevation. Users see these and think they're real model predictions.

**What to do:** Replace lines 75–98 in `frontend/src/App.jsx`:

```javascript
// BEFORE (FABRICATED):
const enrichedLocs = (locs || []).map((l) => {
  let riskCat = l.risk_category;
  let hazIdx = l.hazard_index;
  if (!riskCat) {
    const slope = Number(l.slope) || 0;
    const elev = Number(l.elevation) || 0;
    if (slope >= 30 && elev >= 1000) {
      riskCat = 'High';
      hazIdx = 0.78;
    } else if (slope >= 15 || elev >= 450) {
      riskCat = 'Moderate';
      hazIdx = 0.44;
    } else {
      riskCat = 'Low';
      hazIdx = 0.12;
    }
  }
  return {
    ...l,
    risk_category: riskCat,
    hazard_index: hazIdx,
  };
});

// AFTER (HONEST — terrain-based estimate clearly labelled):
const enrichedLocs = (locs || []).map((l) => {
  let riskCat = l.risk_category;
  let hazIdx = l.hazard_index;
  let riskSource = l.risk_source || 'MODEL';
  if (!riskCat) {
    const slope = Number(l.slope) || 0;
    const elev = Number(l.elevation) || 0;
    if (slope >= 30 && elev >= 1000) {
      riskCat = 'High';
    } else if (slope >= 15 || elev >= 450) {
      riskCat = 'Moderate';
    } else {
      riskCat = 'Low';
    }
    hazIdx = null;  // No fake index — null means "not computed by model"
    riskSource = 'TERRAIN_ESTIMATE';
  }
  return {
    ...l,
    risk_category: riskCat,
    hazard_index: hazIdx,
    risk_source: riskSource,
  };
});
```

---

## Issue 6: DB Seeder Shows `AWAITING_CREDENTIALS` Even When Keys Exist

**File:** `backend/app/services/db_seeder.py` lines 128–138  
**Problem:** The seeder hardcodes `status="OFFLINE"` and `last_attempt_status="AWAITING_CREDENTIALS"` for all non-Open-Meteo sources, regardless of whether actual credentials are configured. This is misleading.

**What to do:** Replace lines 128–138 in `backend/app/services/db_seeder.py`:

```python
# BEFORE:
is_open_meteo = (src.id == "OPEN_METEO")
health = SourceHealth(
    source_id=src.id,
    status="FRESH" if is_open_meteo else "OFFLINE",
    last_successful_fetch=utc_now() if is_open_meteo else None,
    last_attempt_status="INITIALIZED" if is_open_meteo else "AWAITING_CREDENTIALS",
    consecutive_failures=0,
    average_latency_ms=85.0 if is_open_meteo else 0.0
)

# AFTER:
is_open_meteo = (src.id == "OPEN_METEO")
# Check if credentials are actually configured for this source
has_creds = is_open_meteo  # Open-Meteo needs no credentials
if src.id == "MOSDAC_INSAT3D_QPE":
    has_creds = bool(os.getenv("MOSDAC_AUTH_TOKEN", ""))
elif src.id == "NASA_GPM_IMERG":
    has_creds = bool(os.getenv("EARTHDATA_TOKEN", ""))
elif src.id in ("COPERNICUS_S1_SAR", "COPERNICUS_S2_OPTICAL", "COPERNICUS_DEM_GLO30"):
    has_creds = bool(os.getenv("CDSE_CLIENT_ID", ""))
elif src.id == "NASA_FIRMS":
    has_creds = bool(os.getenv("NASA_FIRMS_MAP_KEY", ""))
elif src.id == "USGS_FDSN":
    has_creds = True  # USGS is public, no auth needed
elif src.id == "NASA_COOLR":
    has_creds = bool(os.getenv("EARTHDATA_TOKEN", ""))

health = SourceHealth(
    source_id=src.id,
    status="FRESH" if is_open_meteo else ("STANDBY" if has_creds else "OFFLINE"),
    last_successful_fetch=utc_now() if is_open_meteo else None,
    last_attempt_status="INITIALIZED" if is_open_meteo else ("CREDENTIALS_OK" if has_creds else "AWAITING_CREDENTIALS"),
    consecutive_failures=0,
    average_latency_ms=85.0 if is_open_meteo else 0.0
)
```

Add `import os` at the top of the file if not already present.

---

## Issue 7: `MOSDAC_AUTH_TOKEN` Is Empty — Cannot Fetch INSAT-3D Data

**File:** `.env` line 22 and Render environment  
**Problem:** `MOSDAC_AUTH_TOKEN=` is empty. MOSDAC username/password are set but the bearer token is blank. The MOSDAC API ingestion code checks for this token.

**What to do:** The code in `backend/app/ingestion/sources/weather/mosdac_insat3d.py` line 37 reads:
```python
self.auth_token = getattr(settings, "MOSDAC_AUTH_TOKEN", "") or os.getenv("MOSDAC_AUTH_TOKEN", "")
```

If MOSDAC supports username/password login to get a token, add auto-login in the `fetch()` method. Replace the auth header section in `mosdac_insat3d.py` (around lines 49–55):

```python
# BEFORE:
headers = {
    "Accept": "application/json",
    "User-Agent": "LANDSAFE-NER/1.0 (Disaster-Early-Warning-Research)",
}
if self.auth_token:
    headers["Authorization"] = f"Bearer {self.auth_token}"

# AFTER:
headers = {
    "Accept": "application/json",
    "User-Agent": "LANDSAFE-NER/1.0 (Disaster-Early-Warning-Research)",
}
if self.auth_token:
    headers["Authorization"] = f"Bearer {self.auth_token}"
elif os.getenv("MOSDAC_USERNAME") and os.getenv("MOSDAC_PASSWORD"):
    # Auto-login to get token if not provided
    try:
        async with httpx.AsyncClient(timeout=10.0) as auth_client:
            login_resp = await auth_client.post(
                "https://www.mosdac.gov.in/api/v1/auth/login",
                json={
                    "username": os.getenv("MOSDAC_USERNAME"),
                    "password": os.getenv("MOSDAC_PASSWORD"),
                }
            )
            if login_resp.status_code == 200:
                token = login_resp.json().get("token") or login_resp.json().get("access_token")
                if token:
                    self.auth_token = token
                    headers["Authorization"] = f"Bearer {token}"
    except Exception as exc:
        logger.warning("MOSDAC auto-login failed: %s", exc)
```

---

## Issue 8: Render Free Tier Puts Server to Sleep — Backend Goes Offline

**File:** `backend/app/main.py`  
**Problem:** Render free tier sleeps the server after 15 minutes of inactivity. Cold start takes 30–60 seconds, during which all API calls fail.

**What to do:** Add a self-ping keep-alive task in `backend/app/main.py`. Add this inside the `lifespan()` function:

```python
import asyncio
import httpx

async def _keep_alive_ping():
    """Prevent Render free tier from sleeping by self-pinging every 12 minutes."""
    await asyncio.sleep(60)  # Wait 1 min after startup
    while True:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.get("https://ai-land-slide-alert.onrender.com/health")
            logger.debug("[KeepAlive] Self-ping successful")
        except Exception:
            pass
        await asyncio.sleep(720)  # Ping every 12 minutes (under 15-min sleep threshold)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[LANDSAFE-NER] starting in %s mode", settings.LANDSAFE_MODE)
    if is_demo():
        logger.warning("[LANDSAFE-NER] DEMO MODE — every response carries %s", DEMO_LABEL)
    load_ml_assets()
    logger.info("[LANDSAFE-NER] model and SHAP explainer loaded (UNCALIBRATED, synthetic training data)")
    if settings.SCHEDULER_AUTOSTART:
        ingestion_scheduler.start()
        logger.info("[LANDSAFE-NER] Ingestion scheduler started")
    
    # Start keep-alive background task
    keep_alive_task = asyncio.create_task(_keep_alive_ping())
    
    yield
    
    keep_alive_task.cancel()
    if ingestion_scheduler.is_running:
        ingestion_scheduler.shutdown()
        logger.info("[LANDSAFE-NER] Ingestion scheduler stopped")
    logger.info("[LANDSAFE-NER] shutting down")
```

---

## Issue 9: CORS_ORIGINS on Render Missing Vercel Domain

**File:** Render environment variable `CORS_ORIGINS`  
**Problem:** The Render env has `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` — this is the local dev value. The production Vercel frontend URL `https://ai-land-slide-alert.vercel.app` is missing. The code has a regex fallback (`allow_origin_regex=r"https://.*\.vercel\.app"`) which may cover it, but it's better to be explicit.

**What to do:** Update the `CORS_ORIGINS` environment variable on Render to:

```
http://localhost:5173,http://127.0.0.1:5173,https://ai-land-slide-alert.vercel.app
```

This is a Render dashboard change, not a code change. But if you want to hardcode the fix in code, update `backend/app/core/config.py` line 35:

```python
# BEFORE:
CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://ai-land-slide-alert.vercel.app"

# This is already correct in the code. Just update the Render env var.
```

---

## Issue 10: Frontend `api.js` — 7-Day Trend Takes Wrong Days

**File:** `frontend/src/services/api.js` lines 76–87  
**Problem:** The 7-day rainfall trend always takes the FIRST 7 days from the daily array. With `past_days=6, forecast_days=6`, that's days -6 to 0 (correct). But the backend version uses today's index to compute the range. The frontend version happens to be correct by coincidence but should be made explicit.

**What to do:** Replace lines 76–87:

```javascript
// BEFORE:
const rainfallTrend7d = [];
for (let i = 0; i < Math.min(7, dailyTimes.length); i++) {
  ...
}

// AFTER (explicit past-7-days logic):
const rainfallTrend7d = [];
const todayStr = new Date().toISOString().slice(0, 10);
const todayIdx = dailyTimes.findIndex(d => d === todayStr);
const startIdx = Math.max(0, (todayIdx >= 0 ? todayIdx : 6) - 6);
const endIdx = todayIdx >= 0 ? todayIdx + 1 : 7;
for (let i = startIdx; i < Math.min(endIdx, dailyTimes.length); i++) {
  const dtStr = dailyTimes[i];
  const d = new Date(dtStr);
  const formattedDate = !isNaN(d.getTime()) ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : dtStr;
  rainfallTrend7d.push({
    date: formattedDate,
    iso_date: dtStr,
    rainfall_mm: dailyPrecip[i] != null ? Math.round(dailyPrecip[i] * 10) / 10 : 0,
  });
}
```

---

## Execution Order

Fix in this exact order:

1. **Issue 2** — Enable scheduler (small config change, enables everything else)
2. **Issue 1** — Rewrite satellite_service.py (biggest impact — enables satellite data)
3. **Issue 3** — Add Open-Meteo throttling (fixes weather downtime)
4. **Issue 4** — Fix frontend rainfall bug (prevents wrong data)
5. **Issue 5** — Fix frontend risk labels (stops showing fake risk)
6. **Issue 8** — Add keep-alive ping (prevents Render sleep)
7. **Issue 6** — Fix db_seeder credential detection
8. **Issue 7** — Add MOSDAC auto-login
9. **Issue 9** — Fix CORS origins on Render
10. **Issue 10** — Fix frontend 7-day trend

## After All Fixes

1. Run `pip install -r backend/requirements.txt` to ensure all dependencies are installed
2. Test locally: `python -m uvicorn backend.app.main:app --reload`
3. Hit `http://localhost:8000/api/satellite/1` — should return real NDVI/bare_soil values
4. Hit `http://localhost:8000/api/location/1` — should return weather + satellite + prediction
5. Git commit and push to trigger Render redeploy
6. Add `SCHEDULER_AUTOSTART=true` to Render environment variables
7. Verify on live site: https://ai-land-slide-alert.vercel.app/

---

*This report contains all information needed to fix the issues. No additional research required.*
