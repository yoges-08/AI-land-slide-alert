# LANDSAFE-NER — National Landslide & Multi-Hazard Watch

An AI-based landslide and multi-hazard monitoring platform covering all **788 districts** of India (28 States + 8 UTs), aligned with the canonical Local Government Directory (LGD) maintained by the Ministry of Panchayati Raj.

> **Disclaimer**: LANDSAFE-NER is an academic, non-commercial monitoring aid and research prototype. Official early warnings and evacuation instructions are issued exclusively by the India Meteorological Department (IMD), National Disaster Management Authority (NDMA), and National Center for Seismology (NCS).

---

## Architecture Overview

```
├── backend/
│   ├── app/
│   │   ├── api/routes.py            FastAPI endpoints with validation & provenance
│   │   ├── core/                    Database engine, config, freshness & security
│   │   ├── ingestion/               Multi-source scheduler, registry & rate limiters
│   │   ├── models/                  SQLAlchemy ORM models & Pydantic response schemas
│   │   └── services/                Physics models, ML inference, weather reconciliation
│   └── data/
│       ├── lgd_administrative_units.json  788 official LGD districts & state hierarchy
│       └── ne_india_locations.json        Curated landmark sites & benchmark sectors
├── frontend/
│   ├── src/                         Vite + React interactive dashboard & Leaflet GIS
│   └── data/
│       └── geo_data.json            Client-side LGD geospatial coordinates & terrain metadata
├── alembic/                         Database schema migrations for PostgreSQL/PostGIS & SQLite
└── tests/                           Automated unit, integration, and contract tests (pytest)
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Initialize database & seed authoritative LGD boundaries
python -m backend.app.services.db_seeder

# Run backend API server (runs at http://127.0.0.1:8000)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Dashboard opens at http://localhost:5173
```

### 4. Running Tests
```bash
# Run isolated test suite
python -m pytest tests/ -v
```

---

## Multi-Source Ingestion & Hydrological Physics

1. **Precipitation Reconciliation (Priority Arbitration)**:
   - Priority 1: ISRO MOSDAC INSAT-3D/3DR QPE & IMSRA
   - Priority 2: NASA GPM IMERG Half-Hourly Early/Late Run
   - Priority 3: Open-Meteo Numerical Weather Forecast Model

2. **10-Day Antecedent Saturation Index (ASI)**:
   $$ASI_{10d} = \sum_{k=1}^{10} (0.85)^k \cdot R_k$$

3. **Geotechnical Factor of Safety (FoS)**:
   - Infinite-slope geotechnical equilibrium incorporating pore water pressure, friction angles, and IS 1893 pseudo-static seismic acceleration.
