# LANDSAFE-NER — Remaining Issues & Solutions (23 September 2026)

> **For AI Agent:** These are the remaining issues in the LANDSAFE-NER project. Fix each one in order. Each issue has the exact file, the problem, and the solution code. Do NOT modify anything that is already working.

---

## Status of Previously Reported Issues

| # | Issue | Status |
|---|---|---|
| ✅ | Satellite data returns NULL | **FIXED** — Now returns real NDVI & bare soil from Sentinel-2 |
| ✅ | Scheduler disabled | **FIXED** — `SCHEDULER_AUTOSTART = True` |
| ✅ | Frontend rainfall D3 bug | **FIXED** — Now uses timestamp-based windowing |
| ✅ | Source health misleading | **FIXED** — Shows `CREDENTIALS_OK` for configured sources |
| ✅ | Keep-alive self-ping | **FIXED** — `_keep_alive()` pings every 10 min |
| ✅ | Cache TTL too short | **FIXED** — Now 30 minutes |
| ✅ | Throttling missing | **FIXED** — Semaphore + min interval added |
| ❌ | Open-Meteo rate-limited (429) | **STILL BROKEN** — weather returns all null |
| ❌ | ML prediction fails | **STILL BROKEN** — no weather → no prediction |
| ⚠️ | Frontend still fabricates risk | **PARTIALLY FIXED** — better formula but still client-side |

---

## Issue 1 (CRITICAL): Open-Meteo Returns HTTP 429 — All Weather Data is NULL

**File:** `backend/app/services/weather_service.py`  
**Live evidence:** `/api/weather/26.1445/91.7362` returns `{"status":"OFFLINE","reason":"Open-Meteo unreachable (HTTP 429)","temperature":null}`

### Problem

Open-Meteo free tier is permanently rate-limiting the backend. The 30-min cache and semaphore help but are not enough — the backend is still making too many calls. Every user clicking a location triggers a separate Open-Meteo request even if a nearby location was just fetched. With 788 locations and the scheduler now running, the daily quota gets exhausted quickly.

### Root Cause

1. The cache key uses exact `(lat, lon)` coordinates rounded to 4 decimals. Two locations 1 km apart generate separate API calls even though Open-Meteo gives the same data at ~11 km resolution.
2. The 10-min keep-alive self-ping wakes the server, which may trigger scheduler ingestion cycles that each call Open-Meteo for multiple locations.
3. No 429-specific backoff — when a 429 is received, the code still retries immediately with just `0.5 * 2^attempt` seconds delay, which counts against the rate limit.

### Solution

**Step A:** Add geographic bucketing — round coordinates to 1 decimal (~11 km) for cache lookup since Open-Meteo resolution is ~11 km anyway.

In `backend/app/services/weather_service.py`, change the cache key logic at line 91:

```python
# BEFORE (line 91):
cache_key = (round(lat, 4), round(lon, 4))

# AFTER — bucket to ~11 km grid (matches Open-Meteo resolution):
cache_key = (round(lat, 1), round(lon, 1))
```

**Step B:** Add 429-specific exponential backoff with much longer wait. After the retry loop (around line 129), add special handling for 429:

```python
# REPLACE lines 124-133 with:
                if response.status_code == 200:
                    parsed = parse_open_meteo_response(response.json(), lat, lon)
                    _LAST_SUCCESS[cache_key] = parsed["data_status"]["observed_at"] or utcnow().isoformat()
                    _WEATHER_CACHE[cache_key] = (time.time(), parsed)
                    return parsed
                elif response.status_code == 429:
                    # Rate limited — back off significantly and stop retrying
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Open-Meteo 429 rate-limit; backing off %ds", retry_after)
                    # Cache a "rate limited" marker to prevent further calls for this period
                    _WEATHER_CACHE[cache_key] = (time.time(), None)
                    await asyncio.sleep(min(retry_after, 120))
                    break  # Don't retry on 429
                last_error = f"HTTP {response.status_code}"
```

**Step C:** Skip API call entirely if a recent 429 was received. Add this right after the existing cache check (after line 96):

```python
    # If we recently got a 429, don't even try for 5 minutes
    RATE_LIMIT_COOLDOWN_S = 300.0  # 5 minutes
    if cache_key in _WEATHER_CACHE:
        cached_time, cached_val = _WEATHER_CACHE[cache_key]
        if cached_val is None and (now_ts - cached_time) < RATE_LIMIT_COOLDOWN_S:
            logger.debug("Skipping Open-Meteo call — still in 429 cooldown for (%s, %s)", lat, lon)
            return unavailable(lat, lon, "Rate-limited (cooldown active)")
```

---

## Issue 2 (CRITICAL): ML Prediction Returns NO_DATA When Weather Is Down

**File:** `backend/app/api/routes.py`  
**Live evidence:** `/api/location/1` returns `"prediction":{"hazard_index":null,"status":"NO_DATA","reason":"No observed rainfall available"}`

### Problem

The ML prediction requires `rainfall_24h` from weather. When Open-Meteo is rate-limited, `rainfall_24h` is `null`, and the model refuses to predict. But the frontend already fetches weather directly from Open-Meteo as a fallback — this fallback weather should also trigger the ML model on the backend.

### Solution

The frontend at `frontend/src/services/api.js` line 184 already has this fallback logic — when backend weather is OFFLINE, it fetches from Open-Meteo directly and calls `/api/predict`. This works correctly.

The issue is the **backend-side** — when Open-Meteo is rate-limited, the backend should also try the frontend's direct approach. Add a fallback in `backend/app/api/routes.py` in the location detail handler.

Find the section where weather and prediction are assembled (around lines 240-260) and add a second attempt using the Sentinel-2 data:

```python
# After getting weather and prediction, if prediction failed but satellite has data,
# compute a terrain-only risk estimate using satellite vegetation data:

if prediction.get("status") == "NO_DATA" and satellite.get("status") == "FRESH":
    sat_veg = satellite.get("vegetation_index")
    sat_bare = satellite.get("bare_soil_pct")
    sat_fire = satellite.get("fire_detected")
    terrain_slope = loc.get("slope", 0)
    terrain_elev = loc.get("elevation", 0)
    
    if sat_veg is not None:
        # Compute satellite-enhanced terrain risk
        slope_score = min(1.0, max(0.0, (terrain_slope - 5.0) / 40.0))
        veg_risk = max(0.0, 1.0 - sat_veg)  # Low NDVI = higher risk
        bare_risk = (sat_bare or 0) / 100.0
        fire_boost = 0.15 if sat_fire else 0.0
        
        sat_hazard = min(0.95, (slope_score * 0.40) + (veg_risk * 0.25) + (bare_risk * 0.20) + fire_boost)
        sat_hazard = round(sat_hazard, 3)
        
        if sat_hazard >= 0.60:
            sat_risk_cat = "High"
        elif sat_hazard >= 0.35:
            sat_risk_cat = "Moderate"
        else:
            sat_risk_cat = "Low"
        
        prediction = {
            **prediction,
            "hazard_index": sat_hazard,
            "risk_category": sat_risk_cat,
            "status": "DEGRADED",
            "reason": "Weather unavailable (429). Risk estimated from satellite + terrain only. Less reliable than full model.",
            "inputs": {
                "weather": prediction.get("inputs", {}).get("weather", {}),
                "satellite": {"status": "FRESH", "source": satellite.get("source", "Sentinel-2")},
            },
            "top_factors": {
                "slope": round(slope_score, 3),
                "low_vegetation": round(veg_risk, 3),
                "bare_soil": round(bare_risk, 3),
                "fire_detected": sat_fire or False,
            },
        }
```

---

## Issue 3 (HIGH): Sources Show OFFLINE with calls_today=0 — Scheduler Not Actually Fetching

**File:** `backend/app/ingestion/scheduler.py`, `backend/app/ingestion/registry.py`  
**Live evidence:** `/api/sources` shows all sources have `"calls_today":0` and `"last_successful_fetch":null` despite `SCHEDULER_AUTOSTART=True`

### Problem

The scheduler is enabled (`SCHEDULER_AUTOSTART=True`) and `ingestion_scheduler.start()` runs in `main.py`. However:

1. `init_default_sources()` in `registry.py` only registers 3 sources (MOSDAC, GPM, Open-Meteo). The other 6 sources (Sentinel-1/2, USGS, FIRMS, COOLR, DEM) have no ingestion source classes, so they never get scheduled.
2. Even the 3 registered sources may not be running because `is_verified()` might be blocking them via `PENDING_VERIFICATION` list in config.
3. The MOSDAC source has an empty auth token so its fetch will fail silently.

### Solution

**Step A:** Check `PENDING_VERIFICATION` in `backend/app/core/config.py`. Find the `PENDING_VERIFICATION` list and remove any sources that now have working credentials:

```python
# Find PENDING_VERIFICATION and update it:
# BEFORE (if it blocks MOSDAC, GPM etc.):
PENDING_VERIFICATION = ["nisar_ssar", "resourcesat_liss"]

# AFTER — only block sources that truly don't have credentials:
PENDING_VERIFICATION = ["nisar_ssar", "resourcesat_liss"]
# Make sure MOSDAC_INSAT3D_QPE, NASA_GPM_IMERG, OPEN_METEO are NOT in this list
```

**Step B:** The ingestion `fetch()` methods for MOSDAC and NASA GPM point to placeholder API endpoints that may not exist. Verify and update:

In `backend/app/ingestion/sources/weather/mosdac_insat3d.py` line 31:
```python
# CHECK: Is this a real endpoint?
api_endpoint = os.getenv("MOSDAC_API_ENDPOINT", "https://www.mosdac.gov.in/api/v1/qpe")
# If this endpoint doesn't exist, update to the real MOSDAC data access URL.
# The actual MOSDAC data portal may use a different URL format.
```

In `backend/app/ingestion/sources/weather/nasa_gpm.py` line 31:
```python
# CHECK: Is this a real endpoint?
api_endpoint = os.getenv("NASA_GPM_API_ENDPOINT", "https://gpm.nasa.gov/api/v1/imerg")
# The real NASA GPM IMERG data is accessed via GES DISC:
# https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary
# Update to the correct OPeNDAP or HTTP endpoint
```

**Step C:** Add a startup log to confirm what the scheduler actually registered. In `backend/app/main.py` after `ingestion_scheduler.start()`:

```python
    if settings.SCHEDULER_AUTOSTART:
        ingestion_scheduler.start()
        jobs = ingestion_scheduler.get_jobs_status()
        logger.info("[LANDSAFE-NER] Ingestion scheduler started with %d jobs: %s",
                     len(jobs), [j["name"] for j in jobs])
```

---

## Issue 4 (HIGH): Sentinel-1 SAR Data Missing — snow_cover, flood_extent, snowmelt Are NULL

**File:** `backend/app/services/satellite_service.py`  
**Live evidence:** `snow_cover_pct=null, snowmelt_rate=null, flood_extent_flag=null` for all locations

### Problem

The current satellite service fetches NDVI and bare soil from Sentinel-2 (optical), but Sentinel-1 SAR data (for soil moisture, flood extent, snow cover) is not being fetched. The CDSE credentials are available.

### Solution

Add a Sentinel-1 SAR fetch function to `satellite_service.py`. Sentinel-1 provides C-band SAR backscatter which can detect:
- **Flood extent** — water has very low backscatter in VV polarization
- **Snow cover** — wet snow has distinct backscatter signature
- **Soil moisture** — backscatter correlates with surface moisture

```python
async def _fetch_sentinel1_sar(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch flood/snow/moisture indicators from Copernicus Sentinel-1 SAR."""
    if not settings.CDSE_CLIENT_ID or not settings.CDSE_CLIENT_SECRET:
        return None
    
    try:
        # Get CDSE access token (reuse from Sentinel-2 if already cached)
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
                return None
            access_token = token_resp.json().get("access_token")
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=12)  # Sentinel-1 revisit = 6-12 days
        bbox_delta = 0.05
        
        # Evalscript for VV/VH backscatter analysis
        evalscript = '''
        //VERSION=3
        function setup() {
            return { input: ["VV", "VH"], output: { bands: 3, sampleType: "FLOAT32" } };
        }
        function evaluatePixel(sample) {
            let vv_db = 10 * Math.log10(Math.max(sample.VV, 1e-10));
            let vh_db = 10 * Math.log10(Math.max(sample.VH, 1e-10));
            let ratio = sample.VH / Math.max(sample.VV, 1e-10);
            return [vv_db, vh_db, ratio];
        }
        '''
        
        stat_payload = {
            "input": {
                "bounds": {
                    "bbox": [lon - bbox_delta, lat - bbox_delta, lon + bbox_delta, lat + bbox_delta],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                        },
                        "acquisitionMode": "IW"
                    }
                }]
            },
            "aggregation": {
                "timeRange": {
                    "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                    "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                },
                "aggregationInterval": {"of": "P12D"},
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
                return None
            
            result = resp.json()
            intervals = result.get("data", [])
            if not intervals:
                return None
            
            latest = intervals[-1]
            outputs = latest.get("outputs", {}).get("data", {}).get("bands", {})
            vv_stats = outputs.get("B0", {}).get("stats", {})
            vh_stats = outputs.get("B1", {}).get("stats", {})
            
            vv_mean = vv_stats.get("mean")  # VV backscatter in dB
            vh_mean = vh_stats.get("mean")  # VH backscatter in dB
            
            if vv_mean is None:
                return None
            
            # Interpretation thresholds (empirical from ESA documentation):
            # VV < -18 dB typically indicates standing water (flood)
            # VV < -12 dB with VH/VV ratio change indicates wet snow
            flood_flag = vv_mean < -18.0
            snow_pct = None
            if vv_mean < -12.0 and vh_mean is not None and vh_mean < -22.0:
                # Rough wet snow indicator for high-altitude locations
                snow_pct = min(100.0, max(0.0, (-12.0 - vv_mean) * 15.0))
            
            return {
                "flood_extent_flag": flood_flag,
                "snow_cover_pct": round(snow_pct, 1) if snow_pct is not None else None,
                "snowmelt_rate": None,  # Needs time-series comparison (future)
                "vv_backscatter_db": round(vv_mean, 2),
                "vh_backscatter_db": round(vh_mean, 2) if vh_mean else None,
                "source": "Copernicus Sentinel-1 GRD (IW)",
                "observed_at": latest.get("interval", {}).get("to"),
            }
    
    except Exception as exc:
        logger.warning("Sentinel-1 SAR fetch failed: %s", exc)
        return None
```

Then update the main `get_satellite_observation()` function to call both Sentinel-2 AND Sentinel-1:

```python
async def get_satellite_observation(location: dict) -> Dict[str, Any]:
    # ... existing demo mode check ...
    # ... existing cache check ...
    
    # Fetch from both satellites concurrently
    sentinel2, sentinel1, fire = await asyncio.gather(
        _fetch_sentinel2_indices(lat, lon),
        _fetch_sentinel1_sar(lat, lon),
        _fetch_nasa_firms_fire(lat, lon),
        return_exceptions=True,
    )
    
    # Handle exceptions from gather
    if isinstance(sentinel2, Exception): sentinel2 = None
    if isinstance(sentinel1, Exception): sentinel1 = None
    if isinstance(fire, Exception): fire = None
    
    if sentinel2 or sentinel1 or fire is not None:
        result = {
            "status": "FRESH",
            "source": "Copernicus Sentinel-2 L2A + Sentinel-1 GRD",
            "vegetation_index": (sentinel2 or {}).get("vegetation_index"),
            "bare_soil_pct": (sentinel2 or {}).get("bare_soil_pct"),
            "snow_cover_pct": (sentinel1 or {}).get("snow_cover_pct"),
            "snowmelt_rate": (sentinel1 or {}).get("snowmelt_rate"),
            "flood_extent_flag": (sentinel1 or {}).get("flood_extent_flag"),
            "farm_change_flag": None,  # Needs time-series NDVI comparison (future)
            "fire_detected": fire if not isinstance(fire, Exception) else None,
            "last_updated": (sentinel2 or sentinel1 or {}).get("observed_at") or utcnow().isoformat(),
        }
        _SAT_CACHE[cache_key] = (now_ts, result)
        return result
    
    # ... existing no_data fallback ...
```

Add `import asyncio` at the top of the file if not already present.

---

## Issue 5 (MEDIUM): Frontend Still Computes Risk Client-Side — Not Using Real Model

**File:** `frontend/src/App.jsx` lines 77–107  
**Problem:** The dashboard map risk levels are computed client-side using a terrain susceptibility formula. While improved from the old hardcoded values (now uses GSI-style LSI), it still does NOT use the ML model or satellite data. Users see "High" risk on the map but it's only from slope/elevation.

### Solution

Add a `risk_source` label so users know the source. Update lines 102-107:

```javascript
// AFTER line 100 (inside the else branch, after computing riskCat):
        return {
          ...l,
          risk_category: riskCat,
          hazard_index: hazIdx,
          risk_source: 'TERRAIN_SUSCEPTIBILITY',  // Label clearly
          risk_note: 'Based on terrain slope/elevation only. Click for full model prediction.',
        };
```

Then in the UI where risk badges are displayed, show the source label. Search for where `risk_category` is rendered (likely in a badge or chip component) and append:

```jsx
{loc.risk_source === 'TERRAIN_SUSCEPTIBILITY' && (
  <span className="text-xs text-gray-400 ml-1">(Terrain)</span>
)}
```

---

## Issue 6 (MEDIUM): CORS_ORIGINS Missing Vercel Production URL

**File:** Render environment variable  
**Current value:** `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

### Problem

The Render env only has localhost URLs. The production Vercel URL is missing. The code has a regex fallback (`allow_origin_regex=r"https://.*\.vercel\.app"`) which covers it, but explicit is better.

### Solution

Update `CORS_ORIGINS` on Render to:
```
http://localhost:5173,http://127.0.0.1:5173,https://ai-land-slide-alert.vercel.app
```

This is a **Render dashboard change**, not a code change.

---

## Issue 7 (MEDIUM): ML Model Trained on Synthetic Data — Not Validated

**File:** `backend/app/services/ml_service.py`, `backend/ml/train_models.py`  
**Problem:** The XGBoost model was trained on synthetic formula-derived labels, never validated against real landslide events. The code explicitly says `"UNCALIBRATED"`.

### Solution

This is a long-term fix. For now, add a disclaimer to the API response. Find where the prediction response is built and ensure the status/note fields include:

```python
"calibration": "UNCALIBRATED",
"training_data": "SYNTHETIC",
"confidence_note": "This hazard index has not been validated against observed landslides. Use IMD/NDMA guidance as the authoritative source."
```

For a future milestone: retrain using NASA COOLR (Cooperative Open Online Landslide Repository) real landslide event data + historical weather at event locations.

---

## Issue 8 (LOW): MOSDAC and NASA GPM Ingestion Sources Use Placeholder API URLs

**File:** `backend/app/ingestion/sources/weather/mosdac_insat3d.py` line 31, `backend/app/ingestion/sources/weather/nasa_gpm.py` line 31  
**Problem:** The API endpoints `https://www.mosdac.gov.in/api/v1/qpe` and `https://gpm.nasa.gov/api/v1/imerg` are likely placeholder URLs that don't exist. Even with credentials, the fetch will fail.

### Solution

Update to real data access endpoints:

**MOSDAC:** The actual MOSDAC data portal uses:
```python
# In mosdac_insat3d.py:
api_endpoint = os.getenv("MOSDAC_API_ENDPOINT", "https://mosdac.gov.in/data/web/data_products_info/QPE")
```

**NASA GPM IMERG:** The real data is accessed via NASA GES DISC:
```python
# In nasa_gpm.py:
api_endpoint = os.getenv("NASA_GPM_API_ENDPOINT", 
    "https://disc.gsfc.nasa.gov/api/data/GPM_3IMERGHH_07")
```

However, these APIs require specific request formats. The `fetch()` methods need to be tested and adjusted for the actual API response format.

---

## Execution Order

| Priority | Issue | Impact |
|---|---|---|
| 🥇 **1** | Issue 1: Fix Open-Meteo 429 handling | Restores weather data for entire site |
| 🥇 **2** | Issue 2: Add satellite-based fallback prediction | Shows risk even when weather is down |
| 🥈 **3** | Issue 4: Add Sentinel-1 SAR for flood/snow | Fills remaining null satellite fields |
| 🥈 **4** | Issue 3: Fix scheduler to actually run ingestion | Enables background data collection |
| 🥉 **5** | Issue 5: Label frontend risk source | Transparency for users |
| 🥉 **6** | Issue 6: Fix CORS on Render | Security best practice |
| 🥉 **7** | Issue 7: Add ML model disclaimer | User safety |
| 🥉 **8** | Issue 8: Fix ingestion API URLs | Enables MOSDAC/GPM data flow |

---

## Verification After Fixes

After implementing all fixes, verify:

1. `GET /api/weather/26.1445/91.7362` → should return temperature, humidity, rainfall (not null)
2. `GET /api/satellite/1` → should return NDVI, bare_soil, snow_cover, flood_extent (not all null)
3. `GET /api/location/1` → prediction should have a hazard_index (not null)
4. `GET /api/sources` → at least Open-Meteo should show `calls_today > 0`
5. Frontend map should show risk labels with "(Terrain)" suffix for non-model predictions

---

*Report generated 23 September 2026. No code was modified.*
