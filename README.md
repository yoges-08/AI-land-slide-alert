# LANDSAFE-NER
### National Landslide & Multi-Hazard Risk Monitoring System
**All-India State & District Hierarchical Coverage**
*B.Tech AI & Data Science Academic Prototype*

---

## 0. Prototype Disclaimer
> **"LANDSAFE-NER is a B.Tech AI & Data Science academic prototype. It is NOT an official government disaster-warning system. Risk levels are based on prototype thresholds for demonstration purposes only. Do not use for real-world emergency decisions."**

---

## 1. Project Overview & Coverage Scope

LANDSAFE-NER provides early-warning and terrain intelligence hazard monitoring across **all 28 States and 8 Union Territories of India**, organized hierarchically as **State → District**.

### Data Coverage Transparency (Tier 1 vs. Tier 2)

| Tier | Region / States | Data Coverage Level | Description |
|---|---|---|---|
| **Tier 1: Full Hazard Monitoring** | **Northeast India** (Sikkim, Arunachal Pradesh, Assam, Meghalaya, Nagaland, Manipur, Mizoram, Tripura)<br>**Himalayan Corridor** (Uttarakhand, Himachal Pradesh, Jammu & Kashmir, Ladakh)<br>**Western Ghats & Coastal Slopes** (Kerala: Wayanad, Idukki; Maharashtra: Raigad, Pune hills; Karnataka: Kodagu, Chikmagalur; Tamil Nadu: Nilgiris; West Bengal: Darjeeling/Kalimpong) | **Full ML + Satellite + Live Weather** | Real-time Open-Meteo rainfall, high-resolution DEM slope/aspect, lithology, NASA MODIS Snow cover/melt, Sentinel-2 BSI (bare soil) & NDVI, and XGBoost/SHAP landslide predictions. |
| **Tier 2: Plain / Non-Mountainous Districts** | **Remaining States & UTs** (e.g. Punjab, Haryana, Rajasthan, Uttar Pradesh plains, Bihar, Gujarat, Madhya Pradesh, Odisha, Andhra Pradesh, Telangana, Delhi, etc.) | **Terrain & Live Weather Only (Low Hazard Zone)** | Non-mountainous flat/undulating terrain lacking geotechnical slope instability or historical ground truth. **Marked transparently as "Insufficient Data for Prediction (Plain / Low Hazard Zone)"** rather than fabricating uncalibrated risk scores. |

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

### One-Click Launch
```bash
python run_system.py
```
- **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Manual Startup

#### 1. Backend Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Development Server
```bash
cd frontend
npm run dev
```

---

## 4. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/locations` | List locations with State, District, and Risk filters |
| `GET` | `/api/hierarchy` | List all Indian States, their districts, and monitoring tiers |
| `GET` | `/api/location/{id}` | Detailed location stats, live weather, satellite indices, and ML risk |
| `GET` | `/api/weather/{lat}/{lon}` | Live Open-Meteo weather and 5-day forecast |
| `POST` | `/api/predict` | Custom landslide prediction with SHAP log-odds |
| `POST` | `/api/predict/flood` | Multi-hazard flood risk prediction |
| `GET` | `/api/risk/{id}` | Risk score breakdown and key risk factors |
| `GET` | `/api/satellite/{id}` | Satellite indices with data source tags & timestamps |
| `GET` | `/api/alerts` | Active threshold early warnings |
| `POST` | `/api/simulation` | What-If simulation engine with slider overrides |
| `GET` | `/api/model/info` | ML benchmark comparisons and feature importances |
| `GET` | `/api/export/report/{id}` | Academic prototype PDF/JSON hazard report |
