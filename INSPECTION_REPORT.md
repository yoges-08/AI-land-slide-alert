# LANDSAFE-NER — Codebase Audit & Inspection Report (Milestone 0)

**Project:** LANDSAFE Multi-Hazard Early Warning Platform  
**Audit Date:** September 19, 2026  
**Auditor:** Senior Geospatial / ML Backend Engineer  
**System Classification:** Academic / Non-Commercial Advisory Prototype  
**Official Authorities:** India Meteorological Department (IMD), National Disaster Management Authority (NDMA), National Center for Seismology (NCS).

---

## 1. Executive Summary

This audit assesses the state of the LANDSAFE codebase across `backend/`, `frontend/`, and `data/` directories. While the repository contains rich structural scaffolding, GIS vector boundaries, UI components, and API schemas, several core data and modeling pipelines currently rely on synthetic formulas, hardcoded fallbacks, and inverted array slices. 

To comply with the **Absolute Data Rules** (Real Data Only in Production, No Fabricated Observations, Explicit "NO DATA" Handling, Source Freshness Tracking), all synthetic and unverified generation paths must be excised or quarantined into dedicated demo modules prior to Milestone 1 (PostGIS Database Migration).

---

## 2. Defect Analysis & Verification Matrix

| ID | Component / File | Specific Lines | Severity | Impact | Remediation Plan (Milestone 0) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | `backend/app/services/satellite_service.py` | L63–L106 (`compute_satellite_indices`) | **Critical** | Fabricates NDSI, NDVI, BSI, and flood flags via heuristic formulas on elevation and slope rather than reading satellite band rasters. | Deprecate and isolate function into `demo_service.py`. Production path returns `None` / `"NO DATA"` until real Sentinel/MODIS/NISAR ingestion is active. |
| **DEF-02** | `backend/app/services/weather_service.py` | L141–L181 (`get_fallback_weather`) | **High** | Injects hardcoded numerical rainfall (142 mm), temperatures, and fake 7-day trends when Open-Meteo is unreachable. | Remove synthetic values. Replace with structured `"NO DATA"` response, `staleness="OFFLINE"`, and `last_successful_timestamp=None`. |
| **DEF-03** | `backend/app/services/weather_service.py` | L74–L75, L99–L100 (`parse_open_meteo_response`) | **High** | 1. `rain_24h` sums `hourly_precip[-24:]` (the *last 24 hours of the 6-day future forecast*) instead of past 24h.<br>2. 5-day forecast slice starts at `len(daily_time) - 5` (future days +2 to +6) but labels index 0 as "Today". | 1. Locate current hour index in `hourly["time"]` and slice `[curr_idx-24 : curr_idx]`.<br>2. Extract today's index (`past_days` offset) and slice days `0` to `+4` for forecast. |
| **DEF-04** | `backend/app/services/alert_service.py` | L4–L83 (`DEFAULT_ALERTS`) | **Medium** | Alerts are stored in a static in-memory Python list without persistence, deduplication, cooldown, or database backing. | Replace with SQLAlchemy/PostGIS database query layer in M1. For M0, wrap alert retrieval in a clean DB-ready service interface. |
| **DEF-05** | `backend/data/seed_locations.py` & `backend/data/ne_india_locations.json` | `seed_locations.py` (L50–L120) | **Medium** | Synthesizes monitoring locations using `random.uniform` and marks them as "field-validated" in README documentation. | Correct README documentation. Tag dataset as synthetic benchmark. Real district centroids and boundaries will be sourced from Survey of India / official OpenData. |
| **DEF-06** | `backend/ml/train_models.py` | L30–L110 (`generate_synthetic_landslide_dataset`) | **High** | ML models (XGBoost & RandomForest) are trained on formulaically generated target labels, producing ungrounded "confidence %" figures. | Transition to Susceptibility $\times$ Trigger physical hazard index (M6). Eliminate deceptive "Probability %" nomenclature in favor of categorized hazard indices. |
| **DEF-07** | `backend/app/core/database.py` & `backend/app/api/routes.py` | `routes.py` L24–L32 | **Medium** | SQLAlchemy models (`Location`, `WeatherRecord`, etc.) exist in `schema.py` but API routes bypass them entirely using `json.load()` on JSON files. CORS is `*` with credentials. | Build M1 PostGIS models and migrate all endpoint queries to SQLAlchemy Async sessions. Restrict CORS origins to configured environment variables. |
| **DEF-08** | `frontend/data/build_geo.py` | L6–L7, L320 | **Low** | Contained hardcoded Linux paths (`/home/claude/...`) and required external `india_districts.geojson`. | Updated to use `os.path` relative resolution and local `geo_data.json` outputs. |

---

## 3. Deep-Dive Code Inspection

### 3.1. Defect 1: Synthetic Satellite Index Calculation
- **Location:** `backend/app/services/satellite_service.py`, lines 63–106:
```python
def compute_satellite_indices(elevation: float, slope: float, lat: float, lon: float, is_monsoon: bool = True):
    # INVENTED FORMULAS:
    if elevation > 2500:
        snow_cover = min(92.0, (elevation - 2200) * 0.035 + (25.0 if lat > 27.5 else 10.0))
    bare_soil = round(min(75.0, max(8.0, slope * 0.95 + (15.0 if elevation < 1000 else 5.0))), 1)
    ndvi = round(max(0.15, min(0.88, 0.85 - (bare_soil / 100.0) * 0.5)), 2)
```
- **Violation:** Violates the Absolute Data Rule *"Never fill gaps with defaults or interpolated guesses shown as observations."*
- **Remediation:** In production mode (`LANDSAFE_MODE=production`), this endpoint must query the PostGIS `satellite_observations` table populated by Sentinel-2 / MODIS ingestion workers. If no raster scene exists within the validity window (e.g. 5 days for optical, 12 days for SAR), return `status: "NO DATA"`, `quality_flag: "NO_SCENE_AVAILABLE"`.

### 3.2. Defect 2 & 3: Open-Meteo Slice Inversion & Fake Fallback
- **Location:** `backend/app/services/weather_service.py`, lines 73–75:
```python
# DEFECT: hourly_precip contains 144 past hours + 24 today hours + 144 forecast hours = 312 hours.
# Slicing [-24:] selects the 6th day in the future!
hourly_precip = hourly.get("precipitation", [])
rain_24h = sum(hourly_precip[-24:])  # WRONG: sums Day +6 forecast rainfall
```
- **Remediation:**
```python
# Proper chronological alignment:
hourly_times = hourly.get("time", [])
# Find index closest to now (UTC+05:30)
now_iso = datetime.now().strftime("%Y-%m-%dT%H:00")
current_idx = hourly_times.index(now_iso) if now_iso in hourly_times else 144
rain_24h = sum(hourly_precip[max(0, current_idx - 23) : current_idx + 1])
```
- **Fallback Remediation:** Replace hardcoded `142.0 mm` with:
```python
def get_no_data_weather(lat: float, lon: float, error_msg: str):
    return {
        "status": "OFFLINE",
        "error": error_msg,
        "temperature": None,
        "rainfall_24h": None,
        "rainfall_trend_7d": [],
        "forecast_5d": [],
        "source": "Open-Meteo",
        "is_sample_data": False,
        "last_updated": None
    }
```

---

## 4. Frontend & Architecture Role Separation

1. **Canonical Frontend (`frontend/src/` - React 18 + Vite + Tailwind CSS)**:
   - Primary user-facing web application.
   - Communicates strictly with backend REST endpoints (`/api/v1/...`) and Server-Sent Events (`/api/v1/events`).
   - Displays real-time data freshness badges, source provenance tags, and official advisory disclaimers.

2. **Standalone Demonstration Dashboard (`frontend/landsafe-dashboard.html`)**:
   - Explicitly categorized as **DEMO ONLY / SIMULATOR**.
   - Contains a client-side meteorological and geotechnical simulation engine for offline demonstrations when external APIs or Docker clusters are unavailable.
   - Must prominently feature the **"DEMO MODE / SIMULATED DATA"** watermark to prevent confusion with production warning systems.

---

## 5. Milestone 0 Action Checklist

- [x] Comprehensive code audit completed (`INSPECTION_REPORT.md`).
- [ ] Fix `weather_service.py` Open-Meteo indexing bug (24h accumulation & 5-day forecast slice).
- [ ] Replace `weather_service.py` fake fallback with `NO DATA` payload.
- [ ] Quarantine synthetic `compute_satellite_indices()` into `backend/app/services/demo_service.py`.
- [ ] Create baseline unit tests (`pytest tests/test_weather.py tests/test_satellite.py tests/test_api.py`).
- [ ] Verify test suite passes with zero mock data leakage in production paths.
