# LANDSAFE-NER — Data Audit Report

## Why No Satellite Data & No Live Data Is Shown on the Website

**Audit Date:** 22 September 2026  
**Website:** https://ai-land-slide-alert.vercel.app/  
**Backend:** https://ai-land-slide-alert.onrender.com  
**Repository:** https://github.com/yoges-08/AI-land-slide-alert.git

---

## 1. Summary of the Problem

The website **does NOT show any real satellite data**. When a user opens any location, all satellite-derived values are `null`:

```
snow_cover_pct     → null
snowmelt_rate      → null
bare_soil_pct      → null
vegetation_index   → null
farm_change_flag   → null
flood_extent_flag  → null
```

The only "live" data visible on the website is **weather data from Open-Meteo** — which is a **ground-based forecast model**, NOT a satellite source.

---

## 2. Root Cause: Why No Satellite Data Is Shown

### Reason 1: Fake Satellite Data Was Removed (Correctly)

In the original baseline code, there was a function called `compute_satellite_indices()` that **fabricated** satellite values from elevation and slope using a formula. It labelled these as "NASA MODIS / Sentinel-2 & Sentinel-1" even though **no satellite was ever contacted**.

This was identified as **Defect 1** and removed in Milestone M0. The code now says:

```
File: backend/app/services/satellite_service.py (line 3-10)

"M0, confirmed defect 1: compute_satellite_indices() fabricated snow/NDVI/bare
soil/flood values from elevation and slope, then labelled them
'NASA MODIS / Sentinel-2 & Sentinel-1'. It has been moved to
backend/demo/fake_satellite.py and is unreachable in production."
```

**This removal was correct** — showing fake numbers as satellite data is worse than showing nothing.

### Reason 2: No Real Satellite API Is Connected

The code has **ingestion source classes** written for satellite providers, but **none of them are actually fetching data** because:

| Satellite Source | File | Why It's Not Working |
|---|---|---|
| **ISRO MOSDAC INSAT-3D/3DR** | `backend/app/ingestion/sources/weather/mosdac_insat3d.py` | `MOSDAC_AUTH_TOKEN` is empty — no credentials configured |
| **NASA GPM IMERG** | `backend/app/ingestion/sources/weather/nasa_gpm.py` | `EARTHDATA_TOKEN` is empty — no credentials configured |
| **Copernicus Sentinel-1 (SAR)** | Not implemented yet | `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` are empty |
| **Copernicus Sentinel-2 (Optical)** | Not implemented yet | `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` are empty |
| **NISAR S-SAR (Bhoonidhi)** | Not implemented yet | Bhoonidhi account approval pending |
| **Resourcesat LISS-3/4** | Not implemented yet | Bhoonidhi account approval pending |
| **NASA FIRMS (Fire)** | Not implemented yet | `NASA_FIRMS_MAP_KEY` is empty |
| **USGS Earthquake** | Not implemented yet | Code structure exists but no fetch logic |
| **NASA COOLR (Landslide DB)** | Not implemented yet | Code structure exists but no fetch logic |

**Evidence from `.env.example`:**

```
NASA_FIRMS_MAP_KEY=your_nasa_firms_map_key_here
EARTHDATA_USERNAME=your_earthdata_username
EARTHDATA_PASSWORD=your_earthdata_password
EARTHDATA_TOKEN=your_earthdata_token_or_leave_empty
CDSE_CLIENT_ID=your_cdse_client_id
CDSE_CLIENT_SECRET=your_cdse_client_secret
MOSDAC_USERNAME=your_mosdac_user
MOSDAC_PASSWORD=your_mosdac_password
BHOONIDHI_API_KEY=pending_manual_nrsc_approval
```

All values are placeholder strings — **no real API keys have been configured**.

### Reason 3: The Ingestion Scheduler Is Disabled

Even if API keys were configured, the background scheduler that would periodically fetch data is **turned off**:

```
File: backend/app/core/config.py (line 45)

SCHEDULER_AUTOSTART: bool = False
```

And in `main.py` (line 22-23):

```python
if settings.SCHEDULER_AUTOSTART:
    ingestion_scheduler.start()
```

Since `SCHEDULER_AUTOSTART = False`, the scheduler **never starts**. No background data fetching happens.

### Reason 4: The satellite_service.py Returns Empty Data by Design

In production mode, the satellite service function explicitly returns `NO_DATA`:

```python
# File: backend/app/services/satellite_service.py (line 92-118)

def get_satellite_observation(location: dict):
    """Return real satellite observations, or NO DATA. Never derived values."""
    if is_demo():
        # Only in demo mode, return fake data
        from backend.demo.fake_satellite import compute_satellite_indices
        return compute_satellite_indices(...)

    # In production: return NO DATA
    return {
        "data_status": status,
        "status": "NO_DATA",
        "source": "pending — NISAR / Sentinel-1 / Resourcesat / Sentinel-2 (M4)",
        "snow_cover_pct": None,
        "snowmelt_rate": None,
        "bare_soil_pct": None,
        "vegetation_index": None,
        "farm_change_flag": None,
        "flood_extent_flag": None,
        "last_updated": None,
    }
```

The system is running in `production` mode (not `demo`), so it returns all `null` values.

---

## 3. Root Cause: Why No Live Data Is Shown for Most Sources

### The `/api/sources` Endpoint Is Misleading

When you call `https://ai-land-slide-alert.onrender.com/api/sources`, it shows **all 9 sources as "FRESH"**:

```json
{
  "id": "MOSDAC_INSAT3D_QPE",
  "health": {
    "status": "FRESH",
    "last_attempt_status": "INITIALIZED",
    "calls_today": 0,
    "consecutive_failures": 0
  }
}
```

**This is fake freshness.** The evidence:

1. `"last_attempt_status": "INITIALIZED"` — means the record was created by the database seeder (`db_seeder.py`), NOT by an actual data fetch
2. `"calls_today": 0` — **zero API calls** made to any source today
3. The seeder code (`backend/app/services/db_seeder.py`, line 129-136) creates health records with `status="FRESH"` and a fake `last_successful_fetch` timestamp at seed time

```python
# File: backend/app/services/db_seeder.py (line 128-136)
health = SourceHealth(
    source_id=src.id,
    status="FRESH",                        # ← Set to FRESH without any actual fetch
    last_successful_fetch=utc_now(),        # ← Timestamp of seeding, not real fetch
    last_attempt_status="INITIALIZED",      # ← Never actually attempted
    consecutive_failures=0,
    average_latency_ms=120.0               # ← Hardcoded fake latency
)
```

### Only Open-Meteo Actually Works

The **only** source that actually fetches live data is **Open-Meteo**, and it works through a different path — not via the ingestion scheduler, but via on-demand API calls in `weather_service.py` when a user opens a location.

---

## 4. What Data the Website Actually Shows

### Data That IS Real and Live

| Data | Source | How It Works |
|---|---|---|
| Temperature | Open-Meteo API | Backend calls `api.open-meteo.com` on each location request |
| Humidity | Open-Meteo API | Same as above |
| Wind Speed | Open-Meteo API | Same as above |
| Rainfall (1h, 24h, 7d) | Open-Meteo API | Computed from hourly/daily data |
| 5-Day Weather Forecast | Open-Meteo API | Daily forecast from Open-Meteo |
| 7-Day Rainfall Trend Chart | Open-Meteo API | Daily historical rainfall |
| Map Satellite Tiles | NASA GIBS | MODIS Terra true-colour imagery tiles |

### Data That IS NOT Real

| Data | What's Actually Happening |
|---|---|
| Risk categories on map (High/Moderate/Low) | **Fabricated by frontend** using slope + elevation formula |
| Hazard index on map pins (0.78/0.44/0.12) | **Hardcoded constants** in `App.jsx` |
| Source health "FRESH" status | **Seeder artefact** — no real fetch ever happened |
| Satellite indices (NDVI, snow, flood, soil) | **All null** — no satellite connected |
| MOSDAC INSAT-3D rainfall | **Never fetched** — no API token |
| NASA GPM IMERG rainfall | **Never fetched** — no Earthdata token |
| USGS Earthquake data | **Never fetched** — no implementation |
| NASA FIRMS fire hotspots | **Never fetched** — no MAP_KEY |
| Alerts | **Static/empty** — alert creation disabled |

### Frontend Risk Fabrication (Detail)

When locations load, the backend returns **no risk category** (stripped in M0). The frontend then invents one:

```javascript
// File: frontend/src/App.jsx (line 75-98)
if (!riskCat) {
  const slope = Number(l.slope) || 0;
  const elev = Number(l.elevation) || 0;
  if (slope >= 30 && elev >= 1000) {
    riskCat = 'High';    hazIdx = 0.78;   // ← Hardcoded
  } else if (slope >= 15 || elev >= 450) {
    riskCat = 'Moderate'; hazIdx = 0.44;   // ← Hardcoded
  } else {
    riskCat = 'Low';     hazIdx = 0.12;   // ← Hardcoded
  }
}
```

This is **not from any model, satellite, or live observation** — just a simple if/else on static terrain values.

---

## 5. The Render Free Tier Problem

The backend is deployed on **Render free tier**, which:

1. **Puts the server to sleep** after 15 minutes of inactivity
2. **Cold start takes 30-60 seconds** — during this time, API calls timeout
3. When the backend is asleep, the frontend falls back to **direct Open-Meteo calls from the browser**

This fallback has a **known rainfall bug (D3)**: it uses position-based array slicing instead of timestamp-based windowing, which can include future forecast hours in the "24h rainfall" calculation, **overstating rainfall by 2-5x**.

```javascript
// File: frontend/src/services/api.js (line 70-72)
// BUG: This takes the last 24 entries, which may include FUTURE forecast hours
const hourlyPrecip = hourly.precipitation || [];
const recent24 = hourlyPrecip.slice(Math.max(0, hourlyPrecip.length - 24));
const rainfall24h = Math.round((recent24.reduce((a, b) => a + (Number(b) || 0), 0)) * 10) / 10;
```

The backend version of this calculation (`weather_service.py`) was **fixed** to use timestamp comparison, but the frontend fallback was not.

---

## 6. Complete Data Flow Diagram

```
User Opens Website
        │
        ▼
Frontend (Vercel) loads 788 districts from /api/locations
        │
        ▼
Backend returns locations with NO risk data
        │
        ▼
Frontend FABRICATES risk labels from slope + elevation
        │
        ▼
User clicks a specific location
        │
        ▼
Frontend calls /api/location/{id}
        │
        ├──► Backend calls Open-Meteo API ──► Returns LIVE weather ✅
        │
        ├──► Backend calls get_satellite_observation() ──► Returns ALL NULL ❌
        │
        └──► Backend runs predict_risk() with weather + terrain
                    │
                    ▼
              ML Model (XGBoost) ──► Returns hazard_index
              (Trained on SYNTHETIC data, UNCALIBRATED) ⚠️

If Backend is asleep (Render free tier):
        │
        ▼
Frontend calls Open-Meteo directly from browser
        │
        ▼
Rainfall 24h may be OVERSTATED (D3 bug still present) ❌
```

---

## 7. Why This Happened — Timeline

| Milestone | What Happened |
|---|---|
| **Baseline** | Fake satellite data was generated from formulas and mislabelled as MODIS/Sentinel |
| **M0** | Fake data correctly removed; production now returns `null` for all satellite indices |
| **M1** | Database schema and seeder created; health records seeded as "FRESH" without real fetches |
| **M2** | Ingestion framework (BaseSource, scheduler, registry, rate limiter) built but scheduler disabled |
| **M3** | Weather reconciliation and MOSDAC/GPM source classes written but no API keys configured |
| **M4** | Satellite index ingestion (NISAR, Sentinel, Resourcesat) — **NOT YET IMPLEMENTED** |
| **M6** | ML model retrain on real data — **NOT YET DONE** |

---

## 8. What Needs to Happen to Show Real Satellite Data

1. **Register and obtain API keys** for:
   - ISRO MOSDAC: https://www.mosdac.gov.in/ (for INSAT-3D/3DR satellite rainfall)
   - NASA Earthdata: https://urs.earthdata.nasa.gov/ (for GPM IMERG, FIRMS, COOLR)
   - Copernicus CDSE: https://dataspace.copernicus.eu/ (for Sentinel-1 SAR, Sentinel-2 optical)
   - ISRO Bhoonidhi: contact bhoonidhi@nrsc.gov.in (for NISAR, Resourcesat)

2. **Add real API keys** to the `.env` file on Render

3. **Set `SCHEDULER_AUTOSTART=True`** in the Render environment to enable background data ingestion

4. **Complete M4 milestone** — implement the actual satellite index extraction code for NDVI, soil moisture, snow cover, and flood extent from Sentinel-1/2 and NISAR data

5. **Upgrade from Render free tier** to avoid cold-start timeouts and keep the scheduler running

6. **Fix the frontend fallback rainfall bug** in `frontend/src/services/api.js` (line 70-72) to use timestamp-based windowing like the backend does

---

## 9. Conclusion

| Question | Answer |
|---|---|
| Does the website show live satellite data? | **NO** — All satellite indices are `null` |
| Does the website show any live data at all? | **YES** — Weather from Open-Meteo (ground model, not satellite) |
| Why no satellite data? | No API keys configured, scheduler disabled, M4 code not written |
| Are the risk labels on the map real? | **NO** — Fabricated by frontend from static slope/elevation |
| Is the ML prediction real? | Partially — it runs live but is trained on synthetic data |
| Is the source health dashboard accurate? | **NO** — Shows "FRESH" for sources that never fetched data |

**The website is fundamentally a weather dashboard powered by Open-Meteo, with a non-functional satellite layer and an uncalibrated risk model. No real satellite scientific data flows into the system.**

---

*Report generated by automated code audit. No code was modified.*
