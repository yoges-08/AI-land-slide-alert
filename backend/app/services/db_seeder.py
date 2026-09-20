"""Database Seeder for LANDSAFE-NER (Milestone 1)

Populates initial administrative boundaries (States & 726 Districts),
data source registry with health tracking, and model versions from geo_data.json.
"""
import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.db_models import (
    State, District, DataSource, SourceHealth, ModelVersion, utc_now
)

logger = logging.getLogger(__name__)

GEO_DATA_PATH = Path(__file__).resolve().parents[3] / "frontend" / "data" / "geo_data.json"

DATA_SOURCES_INITIAL = [
    {
        "id": "MOSDAC_INSAT3D_QPE",
        "name": "INSAT-3D/3DR Quantitative Precipitation Estimation (QPE & IMSRA)",
        "provider": "ISRO / SAC / MOSDAC",
        "cadence_minutes": 30,
        "licence": "Open Government Data (OGD) / Research Non-Commercial",
        "api_endpoint": "https://www.mosdac.gov.in"
    },
    {
        "id": "NASA_GPM_IMERG",
        "name": "NASA Global Precipitation Measurement (GPM IMERG Early/Late Run)",
        "provider": "NASA Earthdata / GSFC",
        "cadence_minutes": 30,
        "licence": "NASA Open Data Policy (Free / Unrestricted)",
        "api_endpoint": "https://gpm.nasa.gov"
    },
    {
        "id": "OPEN_METEO",
        "name": "Open-Meteo Weather API (Ground-Model Cross-Check)",
        "provider": "Open-Meteo",
        "cadence_minutes": 60,
        "licence": "Non-Commercial / Free Tier (<10k calls/day)",
        "api_endpoint": "https://api.open-meteo.com/v1"
    },
    {
        "id": "COPERNICUS_S1_SAR",
        "name": "Sentinel-1 Synthetic Aperture Radar (SAR Ground Moisture / Flood Inundation)",
        "provider": "European Space Agency (ESA) / Copernicus CDSE",
        "cadence_minutes": 8640,  # 6-12 day revisit
        "licence": "Copernicus Open Access Policy",
        "api_endpoint": "https://catalogue.dataspace.copernicus.eu"
    },
    {
        "id": "COPERNICUS_S2_OPTICAL",
        "name": "Sentinel-2 MultiSpectral Instrument (NDVI & Bare Soil Exposure)",
        "provider": "European Space Agency (ESA) / Copernicus CDSE",
        "cadence_minutes": 7200,  # 5 day revisit
        "licence": "Copernicus Open Access Policy",
        "api_endpoint": "https://catalogue.dataspace.copernicus.eu"
    },
    {
        "id": "COPERNICUS_DEM_GLO30",
        "name": "Copernicus Digital Elevation Model (GLO-30 30m Global Grid)",
        "provider": "ESA / Airbus",
        "cadence_minutes": 525600,  # Static terrain base
        "licence": "Copernicus Open Access Policy",
        "api_endpoint": "https://registry.opendata.aws/copernicus-dem"
    },
    {
        "id": "USGS_FDSN",
        "name": "USGS Earthquake Hazards Program FDSN Real-Time Feed",
        "provider": "USGS",
        "cadence_minutes": 15,
        "licence": "US Public Domain (Free)",
        "api_endpoint": "https://earthquake.usgs.gov/fdsnws/event/1"
    },
    {
        "id": "NASA_FIRMS",
        "name": "NASA Fire Information for Resource Management System (FIRMS Near-Real-Time)",
        "provider": "NASA LANCE / FIRMS",
        "cadence_minutes": 60,
        "licence": "NASA Open Data Policy (MAP_KEY)",
        "api_endpoint": "https://firms.modaps.eosdis.nasa.gov"
    },
    {
        "id": "NASA_COOLR",
        "name": "NASA Cooperative Open Online Landslide Repository (COOLR / GLC)",
        "provider": "NASA GSFC",
        "cadence_minutes": 43200,
        "licence": "NASA Open Data Policy (Research / Media-Reporting Bias Disclosed)",
        "api_endpoint": "https://maps.nccs.nasa.gov"
    }
]

MODEL_VERSIONS_INITIAL = [
    {
        "id": "LANDSAFE_PHYS_V1",
        "name": "Infinite-Slope Geotechnical Safety Model (FoS + IS 1893 Seismicity)",
        "hazard_type": "Landslide",
        "description": "Deterministic infinite-slope factor of safety calculation incorporating dynamic pore water pressure, root cohesion, and pseudo-static seismic acceleration.",
        "features_used": ["slope_deg", "lithology", "effective_cohesion", "friction_angle", "soil_saturation", "seismic_zone_kh"]
    },
    {
        "id": "LANDSAFE_SUSC_TRIG_V1",
        "name": "Terrain Susceptibility x Dynamic Meteorological Trigger Model",
        "hazard_type": "Landslide",
        "description": "Multiplicative interaction model combining static geological susceptibility with dynamic 24h rainfall, 10-day antecedent saturation, and snowmelt triggers with Linear-SHAP attribution.",
        "features_used": ["slope_deg", "elevation", "lithology", "rainfall_24h", "asi_10d", "snowmelt_rate", "road_cut_distance"]
    }
]

def seed_database(db: Session = None):
    """Seed states, districts, sources, and models into database."""
    own_session = False
    if db is None:
        init_db()
        db = SessionLocal()
        own_session = True

    try:
        # 1. Seed Data Sources & Health
        for src_data in DATA_SOURCES_INITIAL:
            existing = db.query(DataSource).filter(DataSource.id == src_data["id"]).first()
            if not existing:
                src = DataSource(**src_data)
                db.add(src)
                db.flush()
                # Create initial health record
                health = SourceHealth(
                    source_id=src.id,
                    status="FRESH",
                    last_successful_fetch=utc_now(),
                    last_attempt_status="INITIALIZED",
                    consecutive_failures=0,
                    average_latency_ms=120.0
                )
                db.add(health)

        # 2. Seed Model Versions
        for model_data in MODEL_VERSIONS_INITIAL:
            existing_model = db.query(ModelVersion).filter(ModelVersion.id == model_data["id"]).first()
            if not existing_model:
                m = ModelVersion(**model_data)
                db.add(m)

        # 3. Seed States & 726 Districts from geo_data.json
        if GEO_DATA_PATH.exists():
            with open(GEO_DATA_PATH, "r", encoding="utf-8") as f:
                geo = json.load(f)

            states_raw = geo.get("states", {})
            states_dict = {}
            if isinstance(states_raw, dict):
                for s_name, s_meta in states_raw.items():
                    state_obj = db.query(State).filter(State.name == s_name).first()
                    if not state_obj:
                        iso_val = s_meta.get("iso") if isinstance(s_meta, dict) else None
                        state_obj = State(name=s_name, iso_code=iso_val)
                        db.add(state_obj)
                        db.flush()
                    states_dict[s_name] = state_obj.id
            elif isinstance(states_raw, list):
                for s_info in states_raw:
                    s_name = s_info.get("name") if isinstance(s_info, dict) else str(s_info)
                    if not s_name:
                        continue
                    state_obj = db.query(State).filter(State.name == s_name).first()
                    if not state_obj:
                        iso_val = s_info.get("iso") if isinstance(s_info, dict) else None
                        state_obj = State(name=s_name, iso_code=iso_val)
                        db.add(state_obj)
                        db.flush()
                    states_dict[s_name] = state_obj.id

            for idx, d in enumerate(geo.get("districts", [])):
                d_name = d.get("n")
                s_name = d.get("s")
                state_id = states_dict.get(s_name)
                if not state_id:
                    state_obj = db.query(State).filter(State.name == s_name).first()
                    if not state_obj:
                        state_obj = State(name=s_name)
                        db.add(state_obj)
                        db.flush()
                    states_dict[s_name] = state_obj.id
                    state_id = state_obj.id

                d_id = idx + 1
                existing_district = db.query(District).filter(District.id == d_id).first()
                if not existing_district:
                    ll = d.get("ll", [20.0, 78.0])
                    sz = 5 if s_name in ["Assam", "Nagaland", "Manipur", "Mizoram", "Tripura", "Arunachal Pradesh", "Meghalaya"] else (4 if s_name in ["Sikkim", "Uttarakhand", "Himachal Pradesh", "Jammu and Kashmir", "Ladakh"] else 3)
                    dist = District(
                        id=d_id,
                        state_id=state_id,
                        name=d_name,
                        tier=d.get("tier", 1),
                        physiography_zone=d.get("z", "plateau"),
                        mean_elevation_m=float(d.get("e", 500)),
                        mean_slope_deg=float(d.get("sl", 10)),
                        dominant_lithology=d.get("z", "plateau"),
                        is_1893_seismic_zone=sz,
                        latitude=float(ll[0]),
                        longitude=float(ll[1]),
                        boundary_source="Survey of India / OpenData",
                        licence="Open Government Data (OGD) India"
                    )
                    db.add(dist)

        db.commit()
        logger.info("[Database] Seeding completed successfully.")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"[Database] Seeding error: {e}")
        raise
    finally:
        if own_session:
            db.close()

if __name__ == "__main__":
    seed_database()
    print("Database seeding completed successfully.")
