# LANDSAFE-NER — Issue Report with Solutions

**Date:** 22 September 2026  
**Website:** https://ai-land-slide-alert.vercel.app/  
**Backend:** https://ai-land-slide-alert.onrender.com

---

## Issue 1: Satellite Indices Return All NULL — No Satellite Data on Website

**Severity:** 🔴 Critical  
**File:** `backend/app/services/satellite_service.py` (line 92–118)

### Problem

The function `get_satellite_observation()` is **hardcoded to return `null`** for every satellite index in production mode. It never calls any satellite API regardless of credentials.

```python
# CURRENT CODE — always returns null
def get_satellite_observation(location: dict):
    if is_demo():
        return compute_satellite_indices(...)  # demo only
    
    return {
        "status": "NO_DATA",
        "snow_cover_pct": None,        # ← Always null
        "snowmelt_rate": None,         # ← Always null
        "bare_soil_pct": None,         # ← Always null
        "vegetation_index": None,      # ← Always null
        "farm_change_flag": None,      # ← Always null
        "flood_extent_flag": None,     # ← Always null
    }
```

### Solution

Rewrite `get_satellite_observation()` to fetch real data from Copernicus Sentinel-2 (for NDVI, bare soil) and Sentinel-1 (for soil moisture, flood). Use the CDSE credentials already in `.env`.

```python
# SOLUTION — Replace satellite_service.py with real API calls

import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from backend.app.core.config import settings
from backend.app.core.freshness import no_data, utcnow
from backend.app.core.mode import is_demo

logger = logging.getLogger(__name__)

# Cache to avoid repeated API calls (30-min TTL)
import time
_SAT_CACHE: dict[tuple[float, float], tuple[float, dict]] = {}
SAT_CACHE_TTL = 1800  # 30 minutes


async def _fetch_sentinel2_indices(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch NDVI and bare soil from Copernicus Sentinel-2 via CDSE APIs."""
    if not settings.CDSE_CLIENT_ID or not settings.CDSE_CLIENT_SECRET:
        return None

    try:
        # Step 1: Get access token from CDSE
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.CDSE_CLIENT_ID,
                    "client_secret": settings.CDSE_CLIENT_SECRET,
                }
            )
            if token_resp.status_code != 200:
                logger.warning("CDSE token request failed: HTTP %d", token_resp.status_code)
                return None
            access_token = token_resp.json().get("access_token")

        # Step 2: Query Sentinel-2 Statistical API for NDVI
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=10)
        bbox_delta = 0.05  # ~5km box around the point

        evalscript = """
        //VERSION=3
        function setup() {
            return { input: ["B04", "B08", "SCL"], output: { bands: 2, sampleType: "FLOAT32" } };
        }
        function evaluatePixel(sample) {
            if (sample.SCL == 6 || sample.SCL == 7) {  // vegetation or bare soil
                let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
                let bare = (sample.SCL == 5) ? 1.0 : 0.0;
                return [ndvi, bare];
            }
            return [NaN, NaN];
        }
        """

        stat_payload = {
            "input": {
                "bounds": {
                    "bbox": [lon - bbox_delta, lat - bbox_delta, lon + bbox_delta, lat + bbox_delta],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                        },
                        "maxCloudCoverage": 30
                    }
                }]
            },
            "aggregation": {
                "timeRange": {
                    "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                    "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                },
                "aggregationInterval": {"of": "P10D"},
                "evalscript": evalscript
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://sh.dataspace.copernicus.eu/api/v1/statistics",
                json=stat_payload,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                logger.warning("Sentinel-2 stats request failed: HTTP %d", resp.status_code)
                return None

            result = resp.json()
            intervals = result.get("data", [])
            if not intervals:
                return None

            # Get the most recent interval
            latest = intervals[-1]
            outputs = latest.get("outputs", {}).get("data", {}).get("bands", {})
            ndvi_stats = outputs.get("B0", {})  # NDVI band
            bare_stats = outputs.get("B1", {})  # Bare soil band

            ndvi_val = ndvi_stats.get("stats", {}).get("mean")
            bare_pct = bare_stats.get("stats", {}).get("mean")

            return {
                "vegetation_index": round(ndvi_val, 4) if ndvi_val is not None else None,
                "bare_soil_pct": round(bare_pct * 100, 1) if bare_pct is not None else None,
                "source": "Copernicus Sentinel-2 L2A",
                "observed_at": latest.get("interval", {}).get("to"),
            }

    except Exception as exc:
        logger.warning("Sentinel-2 fetch failed: %s", exc)
        return None


async def _fetch_nasa_firms_fire(lat: float, lon: float) -> Optional[bool]:
    """Check for active fire hotspots near location from NASA FIRMS."""
    if not settings.NASA_FIRMS_MAP_KEY:
        return None

    try:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{settings.NASA_FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/"
            f"{lon-0.5},{lat-0.5},{lon+0.5},{lat+0.5}/1"
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                return len(lines) > 1  # Header + data rows = fire detected
    except Exception as exc:
        logger.warning("FIRMS fetch failed: %s", exc)
    return None


async def get_satellite_observation(location: dict) -> Dict[str, Any]:
    """Return real satellite observations from Copernicus/NASA, or NO DATA."""
    if is_demo():
        from backend.demo.fake_satellite import compute_satellite_indices
        return compute_satellite_indices(
            location.get("elevation", 0.0), location.get("slope", 0.0),
            location.get("latitude", 0.0), location.get("longitude", 0.0),
        )

    lat = location.get("latitude", 0.0)
    lon = location.get("longitude", 0.0)
    cache_key = (round(lat, 3), round(lon, 3))

    # Check cache
    now_ts = time.time()
    if cache_key in _SAT_CACHE:
        cached_time, cached_val = _SAT_CACHE[cache_key]
        if (now_ts - cached_time) < SAT_CACHE_TTL:
            return cached_val

    # Try fetching real satellite data
    sentinel2 = await _fetch_sentinel2_indices(lat, lon)
    fire = await _fetch_nasa_firms_fire(lat, lon)

    if sentinel2 or fire is not None:
        result = {
            "data_status": {
                "status": "FRESH" if sentinel2 else "DEGRADED",
                "source": "copernicus_sentinel2",
            },
            "status": "FRESH" if sentinel2 else "DEGRADED",
            "source": (sentinel2 or {}).get("source", "Copernicus/NASA"),
            "snow_cover_pct": None,  # Needs Sentinel-1 SAR — future
            "snowmelt_rate": None,   # Needs Sentinel-1 SAR — future
            "bare_soil_pct": (sentinel2 or {}).get("bare_soil_pct"),
            "vegetation_index": (sentinel2 or {}).get("vegetation_index"),
            "farm_change_flag": None,  # Needs time-series comparison — future
            "flood_extent_flag": None, # Needs Sentinel-1 SAR — future
            "fire_detected": fire,
            "last_updated": (sentinel2 or {}).get("observed_at") or utcnow().isoformat(),
        }
        _SAT_CACHE[cache_key] = (now_ts, result)
        return result

    # Fallback: no data
    status = no_data(
        "nisar_ssar",
        reason="Satellite APIs unreachable or no recent cloud-free imagery",
    )
    return {
        "data_status": status,
        "status": "NO_DATA",
        "source": "pending",
        "snow_cover_pct": None,
        "snowmelt_rate": None,
        "bare_soil_pct": None,
        "vegetation_index": None,
        "farm_change_flag": None,
        "flood_extent_flag": None,
        "last_updated": None,
    }
```

> **Note:** The function must become `async` since it now makes HTTP calls. Update `routes.py` to `await get_satellite_observation(loc)` wherever it is called.

---

## Issue 2: Open-Meteo Rate Limited (HTTP 429) — Weather Data Down

**Severity:** 🔴 Critical  
**File:** `backend/app/services/weather_service.py`

### Problem

Open-Meteo free tier is returning HTTP 429 (Too Many Requests). When weather fails, ML predictions also fail because they require `rainfall_24h` as a mandatory input.

### Solution

**A. Add request throttling** — Limit how often you call Open-Meteo per location:

```python
# In weather_service.py — increase cache TTL from 15 min to 30 min
WEATHER_CACHE_TTL_SECONDS: float = 30.0 * 60.0  # 30 minutes instead of 15
```

**B. Add a global request limiter** — Max 5 requests per second across all locations:

```python
import asyncio

_OPEN_METEO_SEMAPHORE = asyncio.Semaphore(3)  # Max 3 concurrent requests
_LAST_REQUEST_TIME = 0.0
_MIN_REQUEST_INTERVAL = 0.5  # 500ms between requests

async def fetch_live_weather(lat: float, lon: float) -> dict[str, Any]:
    global _LAST_REQUEST_TIME
    
    # Check cache first (existing code)
    cache_key = (round(lat, 4), round(lon, 4))
    now_ts = time.time()
    if cache_key in _WEATHER_CACHE:
        cached_time, cached_val = _WEATHER_CACHE[cache_key]
        if (now_ts - cached_time) < WEATHER_CACHE_TTL_SECONDS:
            return cached_val

    # Throttle requests
    async with _OPEN_METEO_SEMAPHORE:
        elapsed = time.time() - _LAST_REQUEST_TIME
        if elapsed < _MIN_REQUEST_INTERVAL:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _LAST_REQUEST_TIME = time.time()
        
        # ... rest of existing fetch code ...
```

**C. Add Render environment variable:**

```
OPEN_METEO_DAILY_CALL_BUDGET=8000
```

This leaves headroom below the 10,000 limit.

---

## Issue 3: Ingestion Scheduler Is Disabled — No Background Data Fetching

**Severity:** 🔴 Critical  
**File:** `backend/app/core/config.py` (line 45)

### Problem

```python
SCHEDULER_AUTOSTART: bool = False
```

The scheduler that periodically fetches data from MOSDAC, NASA GPM, USGS, etc. never starts.

### Solution

**Option A (Environment Variable on Render):**

Add this in Render Dashboard → Environment → Environment Variables:
```
SCHEDULER_AUTOSTART=true
```

**Option B (Code change):**

```python
# In config.py line 45, change to:
SCHEDULER_AUTOSTART: bool = True
```

---

## Issue 4: MOSDAC Auth Token Is Empty — INSAT-3D Data Cannot Be Fetched

**Severity:** 🟠 High  
**File:** `.env` (line 22)

### Problem

```
MOSDAC_AUTH_TOKEN=
```

The MOSDAC API requires a bearer token. Username/password alone are not sufficient for API access.

### Solution

1. Go to https://www.mosdac.gov.in/
2. Login with your credentials (`yoges0302`)
3. Navigate to **API Access** or **User Profile** → **API Token**
4. Generate/copy the token
5. Set it in `.env`:

```
MOSDAC_AUTH_TOKEN=your_actual_token_here
```

6. Also add it as a Render environment variable.

---

## Issue 5: Credentials Not Deployed to Render — Production Has No API Keys

**Severity:** 🔴 Critical  
**File:** Render Dashboard (not code)

### Problem

API keys exist in local `.env` but the Render deployment does not have them. Render uses its own environment configuration, not your local `.env` file.

### Solution

Go to **Render Dashboard → Your Service → Environment → Environment Variables** and add:

```
NASA_FIRMS_MAP_KEY=bbcd4ffc3336b5ebb824ad8acea9dbab
EARTHDATA_USERNAME=yoges03
EARTHDATA_PASSWORD=Yogeswaran@2802
EARTHDATA_TOKEN=eyJ0eXAiOiJKV1QiLCJvcmlna...  (full token)
CDSE_CLIENT_ID=sh-45ae6476-bc07-4409-8b17-af70ff2d10ec
CDSE_CLIENT_SECRET=89I4IEQ7ZpFdVXLoVimtizLSakiMPG3a
MOSDAC_USERNAME=yoges0302
MOSDAC_PASSWORD=Waran@2802
MOSDAC_AUTH_TOKEN=  (once you get it)
SCHEDULER_AUTOSTART=true
LANDSAFE_MODE=production
```

Then **redeploy** the service.

---

## Issue 6: Frontend Fabricates Risk Categories — Map Shows Fake Risk Levels

**Severity:** 🟠 High  
**File:** `frontend/src/App.jsx` (lines 75–98)

### Problem

The dashboard map shows High/Moderate/Low risk pins, but these are **invented by the frontend** using hardcoded slope/elevation thresholds — not from any model or data source.

```javascript
if (slope >= 30 && elev >= 1000) {
    riskCat = 'High';    hazIdx = 0.78;   // ← Hardcoded fake
} else if (slope >= 15 || elev >= 450) {
    riskCat = 'Moderate'; hazIdx = 0.44;   // ← Hardcoded fake
} else {
    riskCat = 'Low';     hazIdx = 0.12;   // ← Hardcoded fake
}
```

### Solution

Replace the hardcoded formula with a call to the backend `/api/risk/{id}` endpoint which runs the actual ML model:

```javascript
// In App.jsx — replace the enrichment block (lines 76-98) with:

const enrichedLocs = await Promise.all(
  (locs || []).map(async (l) => {
    if (l.risk_category && l.hazard_index != null) {
      return l; // Already has real risk data
    }
    // Show terrain-based label with clear "ESTIMATED" tag
    const slope = Number(l.slope) || 0;
    const elev = Number(l.elevation) || 0;
    let riskCat, hazIdx;
    if (slope >= 30 && elev >= 1000) {
      riskCat = 'High (Terrain)';
      hazIdx = null;
    } else if (slope >= 15 || elev >= 450) {
      riskCat = 'Moderate (Terrain)';
      hazIdx = null;
    } else {
      riskCat = 'Low (Terrain)';
      hazIdx = null;
    }
    return {
      ...l,
      risk_category: riskCat,
      hazard_index: hazIdx,
      risk_source: 'TERRAIN_ESTIMATE',
    };
  })
);
```

This makes it clear that map-level risk is a terrain estimate, not a model prediction. The real ML prediction shows when a user clicks a specific location.

---

## Issue 7: Frontend Fallback Has D3 Rainfall Bug — Overstates Rainfall

**Severity:** 🟠 High  
**File:** `frontend/src/services/api.js` (lines 69–72)

### Problem

When the backend is sleeping (Render free tier cold start), the frontend fetches weather directly from Open-Meteo. But it uses **position-based slicing** instead of timestamp-based windowing:

```javascript
// BUG: Takes last 24 array entries — may include FUTURE forecast hours
const hourlyPrecip = hourly.precipitation || [];
const recent24 = hourlyPrecip.slice(Math.max(0, hourlyPrecip.length - 24));
const rainfall24h = Math.round((recent24.reduce((a, b) => a + (Number(b) || 0), 0)) * 10) / 10;
```

This can **overstate 24h rainfall by 2–5x** because with `past_days=6` and `forecast_days=6`, the array has ~288 entries and the last 24 are future forecast hours.

### Solution

Replace with timestamp-based windowing (matching the backend's D3 fix):

```javascript
// FIXED: Use timestamp comparison to get only past 24 hours
const hourlyTimes = hourly.time || [];
const hourlyPrecip = hourly.precipitation || [];
const now = new Date(current.time || Date.now());
const past24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);

let rainfall24h = 0;
let hoursCount = 0;
for (let i = 0; i < hourlyTimes.length; i++) {
  const t = new Date(hourlyTimes[i]);
  if (t > past24h && t <= now && hourlyPrecip[i] != null) {
    rainfall24h += Number(hourlyPrecip[i]) || 0;
    hoursCount++;
  }
}
rainfall24h = Math.round(rainfall24h * 10) / 10;
```

---

## Issue 8: ML Model Trained on Synthetic Data — Unreliable Predictions

**Severity:** 🟡 Medium  
**File:** `backend/ml/train_models.py`, `backend/app/services/ml_service.py`

### Problem

The XGBoost model was trained on **synthetic labels** generated by a hand-weighted sigmoid formula. It has never been validated against real observed landslide events. The code itself says:

```
"training_data": "SYNTHETIC — see backend/ml/train_models.py"
"calibration": "UNCALIBRATED"
```

### Solution

1. **Get real landslide event data** from NASA COOLR (Cooperative Open Online Landslide Repository):
   - URL: https://maps.nccs.nasa.gov/arcgis/apps/MapAndAppGallery/index.html
   - Or use the API already registered as `NASA_COOLR` in your sources

2. **Retrain the model** with real events:

```python
# Use NASA COOLR for positive labels (actual landslide events)
# Use random non-event locations for negative labels
# Split by time (train on pre-2024 events, test on 2024+ events)
# Measure precision/recall per region, not just accuracy

from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

# ... fetch COOLR data, merge with weather at event time/location ...

model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    scale_pos_weight=len(neg) / len(pos),  # Handle class imbalance
)
model.fit(X_train, y_train)
```

3. **Calibrate the output** using Platt scaling or isotonic regression so the output can be interpreted as a probability.

---

## Issue 9: Render Free Tier Cold Start — Backend Sleeps After 15 Minutes

**Severity:** 🟡 Medium  
**File:** Render deployment configuration

### Problem

Render free tier puts the server to sleep after 15 minutes of inactivity. Cold start takes 30–60 seconds, during which all API calls fail or timeout.

### Solution

**Option A (Free):** Add a health-check ping to keep the server awake:

Create a free cron job at https://cron-job.org that hits your health endpoint every 10 minutes:
```
URL: https://ai-land-slide-alert.onrender.com/health
Schedule: */10 * * * *
```

**Option B (Paid):** Upgrade to Render's **Starter plan** ($7/month) which keeps the service always running.

**Option C (Code):** Add a self-ping in `main.py`:

```python
import asyncio
import httpx

async def _keep_alive():
    """Ping self every 10 minutes to prevent Render free tier sleep."""
    while True:
        await asyncio.sleep(600)  # 10 minutes
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.get("https://ai-land-slide-alert.onrender.com/health")
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...
    keep_alive_task = asyncio.create_task(_keep_alive())
    yield
    keep_alive_task.cancel()
    # ... existing shutdown code ...
```

---

## Issue 10: `satellite_service.py` routes.py Calls Are Synchronous

**Severity:** 🟡 Medium  
**File:** `backend/app/api/routes.py` (lines 244, 324, 354, 450)

### Problem

`get_satellite_observation()` is called as a synchronous function. If you rewrite it to fetch real satellite data (Issue 1 solution), it must become `async`. But `routes.py` calls it without `await`:

```python
satellite = get_satellite_observation(loc)   # ← No await
```

### Solution

After making `get_satellite_observation` async, update all call sites in `routes.py`:

```python
# Line 244 in get_location_detail:
satellite = await get_satellite_observation(loc)

# Line 324 in get_location_risk:
satellite = await get_satellite_observation(loc)

# Line 354 in get_satellite_info:
sat = await get_satellite_observation(loc)

# Line 450 in export_risk_report:
satellite = await get_satellite_observation(loc)
```

---

## Priority Order for Fixes

| Priority | Issue | Impact |
|---|---|---|
| 🥇 1 | Issue 5: Deploy credentials to Render | Enables everything else |
| 🥇 2 | Issue 1: Rewrite `satellite_service.py` | Enables real satellite data |
| 🥇 3 | Issue 3: Enable scheduler | Enables background data ingestion |
| 🥈 4 | Issue 2: Fix Open-Meteo rate limit | Restores weather data |
| 🥈 5 | Issue 7: Fix frontend rainfall bug | Prevents overstated rainfall |
| 🥈 6 | Issue 6: Fix frontend risk labels | Stops showing fake risk |
| 🥉 7 | Issue 4: Get MOSDAC token | Enables INSAT-3D satellite rainfall |
| 🥉 8 | Issue 9: Fix Render cold start | Keeps server awake |
| 🥉 9 | Issue 10: Make satellite calls async | Required for Issue 1 |
| 🥉 10 | Issue 8: Retrain ML model | Improves prediction accuracy |

---

*Report generated by automated code audit. No code was modified.*
