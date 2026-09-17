# LANDSAFE-NER
### Landslide & Multi-Hazard Risk Monitoring System for Northeast India
**B.Tech AI & Data Science Academic Prototype**

---

## 0. Prototype Disclaimer
> **"LANDSAFE-NER is a B.Tech AI & Data Science academic prototype. It is NOT an official government disaster-warning system. Risk levels are based on prototype thresholds for demonstration purposes only. Do not use for real-world emergency decisions."**

---

## 1. Project Overview

LANDSAFE-NER is an early-warning and terrain intelligence monitoring system engineered specifically for the 8 states of **Northeast India** (Sikkim, Arunachal Pradesh, Assam, Meghalaya, Nagaland, Manipur, Mizoram, Tripura).

The platform addresses steep-terrain geotechnical hazards by combining:
1. **Live 24/7 Weather Ingestion**: Continuous rainfall accumulation and intensity tracking via the Open-Meteo API.
2. **Static Geomorphological Data**: Elevation, slope, aspect, soil type, lithology (Disang shale, Phyllite, etc.), and distance to infrastructure from Bhuvan/SRTM DEM.
3. **Satellite Terrain Intelligence**:
   - **Snow Cover (NDSI) & Snowmelt Rate**: NASA MODIS MOD10A1 / Sentinel-2 NDSI.
   - **Bare Soil Exposure (BSI)**: Copernicus Sentinel-2 Bare Soil Index.
   - **Vegetation Health & Slope Agriculture (NDVI)**: Sentinel-2 NDVI time series tracking jhum/farm clearing on steep slopes.
   - **Multi-Hazard SAR Flood Extent**: Sentinel-1 Synthetic Aperture Radar backscatter contrast.
4. **Machine Learning & SHAP Explainability**: XGBoost, Random Forest, and Logistic Regression with real-time TreeExplainer feature contribution breakdown.

---

## 2. System Architecture

```
┌────────────────────┐   ┌──────────────────────────┐   ┌───────────────────────────┐
│  Open-Meteo (live)  │   │  NASA GIBS / GPM / MODIS │   │  ISRO Bhuvan / MOSDAC /    │
│  weather + rainfall │   │  Sentinel-1 / Sentinel-2 │   │  NRSC Landslide Atlas      │
└──────────┬──────────┘   └────────────┬─────────────┘   └─────────────┬─────────────┘
           │                            │                                │
           ▼                            ▼                                ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │                         DATA INGESTION LAYER                             │
   │   weather_service   |   satellite_service   |   static_data_loader       │
   └──────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
                          ┌──────────────────────┐
                          │  Feature Pipeline      │
                          │  (weather + terrain +  │
                          │   snow/soil/veg/flood) │
                          └──────────┬─────────────┘
                                     ▼
                    ┌───────────────────────────────┐
                    │        ML Prediction Layer     │
                    │  Landslide model (XGBoost/RF)  │
                    │  Flood model (rule-based/LogReg)│
                    └───────┬─────────────┬───────────┘
                            ▼             ▼
                     Risk Probability   SHAP Explanation
                            └─────┬───────┘
                                  ▼
                         ┌─────────────────┐
                         │  FastAPI Backend │ (Port 8000)
                         └────────┬─────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │ SQLite / PostgreSQL DB   │
                    └────────────┬──────────────┘
                                 ▼
                        ┌──────────────────┐
                        │ React Dashboard  │ (Port 5173)
                        │ (Leaflet GIS UI) │
                        └──────────────────┘
```

---

## 3. Quick Start & Execution

### Prerequisites
- Python 3.9+
- Node.js 18+ and npm

### One-Click Launch
```bash
python run_system.py
```
- **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Manual Startup (Individual Services)

#### 1. Backend
```bash
# In project root:
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend
```bash
cd frontend
npm run dev
```

---

## 4. Machine Learning & Feature Engineering

### Trained Models
1. **XGBoost Classifier (Deployed Best)**: `ROC-AUC: ~0.833 | Accuracy: ~78%`
2. **Random Forest Classifier**: `ROC-AUC: ~0.835 | Accuracy: ~79%`
3. **Logistic Regression (Baseline)**: `ROC-AUC: ~0.846 | Accuracy: ~79%`
4. **Multi-Hazard Flood Model**: `ROC-AUC: ~0.925 | Accuracy: ~89%`

### Feature Set
- `rainfall_1h`, `rainfall_24h`, `rainfall_7d_cumulative`, `rainfall_intensity`
- `slope`, `elevation`, `aspect`, `soil_type`, `geology`, `land_cover`
- `distance_road`, `distance_river`, `historical_landslides`
- `snow_cover_pct`, `snowmelt_rate`, `bare_soil_pct`, `vegetation_index`, `farm_change_flag`, `flood_extent_flag`

---

## 5. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/locations` | List 250 monitored locations with risk category |
| `GET` | `/api/location/{id}` | Detailed location stats, live weather, satellite indices, and ML risk |
| `GET` | `/api/weather/{lat}/{lon}` | Live Open-Meteo weather and 5-day forecast |
| `POST` | `/api/predict` | Custom landslide prediction with SHAP log-odds |
| `POST` | `/api/predict/flood` | Multi-hazard flood risk prediction |
| `GET` | `/api/risk/{id}` | Risk score breakdown and key risk factors |
| `GET` | `/api/satellite/{id}` | Satellite indices with data source tags & timestamps |
| `GET` | `/api/satellite/layers/info`| NASA GIBS and ISRO layer configurations |
| `GET` | `/api/alerts` | Active threshold early warnings |
| `POST` | `/api/simulation` | What-If simulation engine with slider overrides |
| `GET` | `/api/model/info` | ML benchmark comparisons and feature importances |
| `GET` | `/api/export/report/{id}` | Academic prototype PDF/JSON hazard report |

---

## 6. Academic & Viva Highlights
- **Satellite Terrain Intelligence Integration**: NDSI snowmelt rate and Sentinel-2 BSI (Bare Soil Index) detect slope destabilization days before failure.
- **Explainable AI**: Every prediction contains a real-time SHAP decomposition showing physical drivers (e.g. 24h rainfall vs slope angle vs Disang shale lithology).
- **Data Provenance Transparency**: Every metric renders a `DataSourceTag` (`NASA GIBS`, `ISRO Bhuvan`, `Open-Meteo`, `SAMPLE DATA`) ensuring zero fabricated data presentation.
