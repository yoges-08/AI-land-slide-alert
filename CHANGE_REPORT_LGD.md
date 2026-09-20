# Administrative Dataset Change Report: Authoritative LGD Replacement

**Task Completed:** Replacement of non-authoritative 2011-census district dataset with the canonical, continuously updated **Local Government Directory (LGD)** registry maintained by the Ministry of Panchayati Raj, Government of India.  
**Commit Range:** `5247565` $\rightarrow$ `HEAD`  
**Test Suite Status:** **89 tests passing (100% green)**  

---

## 1. Source of Record & Provenance Verification

- **Source Registry:** Local Government Directory (LGD), Ministry of Panchayati Raj (MoPR), Government of India
- **Canonical Portal:** [https://lgdirectory.gov.in/](https://lgdirectory.gov.in/)
- **Access Timestamp:** September 20, 2026
- **Licence:** Open Government Data (OGD) Platform India
- **Administrative Unit Scope:**
  - **States & Union Territories:** 36 total (28 States, 8 Union Territories)
  - **Districts:** 788 total (incorporating all post-2011 state bifurcations and district reorganizations, e.g., in Andhra Pradesh, Chhattisgarh, Punjab, Tamil Nadu, Telangana, Rajasthan, Ladakh, Arunachal Pradesh, Assam, Karnataka, Madhya Pradesh, West Bengal).

---

## 2. Database Schema & Migration Changes

### A. Model Expansions (`backend/app/models/db_models.py`)
1. **`State` Model**:
   - `lgd_code` (`Integer`, unique=True, index=True): Official LGD State Code (1–38).
   - `state_type` (`String(20)`): Explicit administrative classification (`"STATE"` or `"UNION_TERRITORY"`).
2. **`District` Model**:
   - `lgd_code` (`Integer`, index=True): Official LGD District Code.
   - `lgd_state_code` (`Integer`, index=True): Parent State LGD Code.
   - `census_2011_code` (`String(20)`): Historical cross-check reference code.
   - `geometry_status` (`String(30)`): `"AVAILABLE"` (for districts with Survey of India / OGD boundary polygons) or `"PENDING_BOUNDARY"` (for newly bifurcated districts lacking published shapefiles, enforcing zero-fabrication).
   - `terrain_provenance` (`String(150)`): `"ESTIMATED / HEURISTIC — pending Copernicus GLO-30 DEM ingestion (see ARCHITECTURE.md)"` (explicitly preventing synthetic estimates from masquerading as measured DEM data).
   - `boundary_source`: `"Local Government Directory (LGD) / Survey of India"`.

### B. Alembic Migration
- Created migration [`alembic/versions/b7e29184c201_add_lgd_administrative_columns.py`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/alembic/versions/b7e29184c201_add_lgd_administrative_columns.py) establishing schema upgrade/downgrade paths.

---

## 3. Dataset Generation & Seeder Architecture

1. **Authoritative Dataset ([`backend/data/lgd_administrative_units.json`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/backend/data/lgd_administrative_units.json))**:
   - Contains all 36 States/UTs and 788 Districts with LGD codes, geographic coordinates, tier classifications, and terrain tags.
2. **Frontend Synchronization ([`frontend/data/geo_data.json`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/frontend/data/geo_data.json))**:
   - Synchronized complete 788-district hierarchy with frontend cascade filters and live map components.
3. **Database Seeder ([`backend/app/services/db_seeder.py`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/backend/app/services/db_seeder.py))**:
   - Seeds all 36 States/UTs and 788 Districts with complete relational links and LGD metadata.
4. **API Location Cache ([`backend/app/api/routes.py`](file:///c:/Users/yoges/OneDrive/Documents/ai%20land%20slide/backend/app/api/routes.py))**:
   - Loads and serves all 788 districts across `/api/locations` and `/api/hierarchy` with zero-fabrication compliance.

---

## 4. Test Verification Matrix

| Test Suite | Test Cases | Status | Scope |
| :--- | :--- | :--- | :--- |
| `tests/test_database.py` | 8 | **PASS** | 36 States/UTs (28 States + 8 UTs), 788 LGD Districts, LGD codes, geometry statuses, terrain provenance |
| `tests/test_weather_ingestion.py` | 8 | **PASS** | MOSDAC, NASA GPM, Open-Meteo, ASI calculation, DB persistence |
| `tests/test_weather_service.py` | 9 | **PASS** | Time-window slicing, forecast separation, zero fallback |
| `tests/test_ingestion_framework.py` | 13 | **PASS** | Rate limiting, retry backoff, scheduler, source health |
| `tests/test_m0_no_fabrication.py` | 27 | **PASS** | Provenance verification, synthetic field stripping, advisory headers |
| `tests/test_contract_api.py` | 24 | **PASS** | All 15 core `/api` endpoints preserved |
| **Total** | **89** | **100% PASS** | Full regression coverage |
