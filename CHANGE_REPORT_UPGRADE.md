# LANDSAFE-NER — Upgrade & Change Report

## Integration: ISRO NRSC Bhoonidhi Satellite Ingestion (Option 2)

### Summary of Changes:
1. **Bhoonidhi Authentication & In-Memory Token Caching** (`backend/app/services/satellite_service.py`):
   - Implemented `_fetch_bhoonidhi_token()` using `BHOONIDHI_USER_ID` and `BHOONIDHI_PASSWORD` configuration.
   - Cached JWT tokens with expiry timestamps to eliminate redundant auth handshakes.
2. **STAC/OpenSearch Multi-Hazard EO Scene Querying** (`backend/app/services/satellite_service.py`):
   - Added `_fetch_bhoonidhi_scenes(lat, lon)` bounding box query against Bhoonidhi's STAC catalog for Resourcesat-2A, Cartosat, and NISAR observations.
   - Parsed platform, sensor/instrument (LISS-4/LISS-3/S-SAR), acquisition timestamp, and cloud coverage percentage.
3. **Resilient Provider Concurrency & Zero-Fabrication Fallback** (`backend/app/services/satellite_service.py`):
   - Concurrently queries Copernicus Sentinel-2 L2A, Sentinel-1 SAR, NASA FIRMS, and ISRO Bhoonidhi.
   - If credentials are unset or the provider is temporarily unreachable, cleanly reports `NO_DATA` or fallback Copernicus observations without crashes or synthetic data fabrication.
4. **Schema & API Updates** (`backend/app/models/schema.py`, `backend/app/api/routes.py`):
   - Extended `SatelliteInfoResponse` to carry optional `bhoonidhi_scene` and `fire_detected` metadata.

---

### Deployment & Verification Checklist:
To test this on the deployed Render instance:
- [ ] Add `BHOONIDHI_USER_ID` and `BHOONIDHI_PASSWORD` environment variables in your Render Dashboard settings (or leave empty to test graceful fallback).
- [ ] Deploy the latest commit to Render.
- [ ] Visit `/api/satellite/1` (e.g. `https://<your-render-app>.onrender.com/api/satellite/1`).
- [ ] Verify HTTP 200 response:
  - If Bhoonidhi credentials are provided: Verify `bhoonidhi_scene` contains platform details (e.g. Resourcesat/LISS-4) and `source` notes Bhoonidhi.
  - If Bhoonidhi credentials are empty: Verify `source` gracefully reports Copernicus/NASA or pending M4 status with `"status": "NO_DATA"` and zero fabrication.
- [ ] Visit `/api/satellite/layers/info` to confirm verified layer registry metadata.
