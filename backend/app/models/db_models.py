"""SQLAlchemy & GeoAlchemy2 Database Models for LANDSAFE-NER (Milestone 1)

Defines all spatial and relational models required by the multi-hazard platform:
1. states & districts (Admin boundaries, terrain, lithology, IS 1893 seismic zones)
2. grid_cells (High-resolution raster mesh)
3. data_sources & source_health (Source registry & freshness tracking)
4. weather_observations (Precipitation & meteorological time series)
5. satellite_observations (Sentinel-1/2, MODIS, NISAR raster features)
6. hazard_events (Seismic, historical landslide inventory, GLOF events)
7. model_versions (Physics & ML model catalog)
8. risk_assessments (Geotechnical FoS, Susceptibility x Trigger, SHAP)
9. predictions (Inference archive)
10. alerts (CAP-compliant multilingual warning records)
11. reports (Automated state/district advisory summaries)
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, BigInteger, SmallInteger, Float, String, Boolean,
    DateTime, ForeignKey, Text, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

from backend.app.core.config import settings

if settings.DATABASE_URL.startswith("postgresql"):
    from geoalchemy2 import Geometry
    HAS_GEOALCHEMY = True
else:
    HAS_GEOALCHEMY = False
    Geometry = lambda *args, **kwargs: Text()

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# 1. Administrative Boundaries & Terrain Registry (Authoritative LGD - MoPR)
# ---------------------------------------------------------------------------
class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    lgd_code = Column(Integer, unique=True, nullable=True, index=True)  # Official LGD State Code
    iso_code = Column(String(10), unique=True, nullable=True)
    state_type = Column(String(20), nullable=False, default="STATE")  # "STATE" or "UNION_TERRITORY"
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    districts = relationship("District", back_populates="state", cascade="all, delete-orphan")


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, ForeignKey("states.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    lgd_code = Column(Integer, nullable=True, index=True)  # Official LGD District Code
    lgd_state_code = Column(Integer, nullable=True, index=True)
    census_2011_code = Column(String(20), nullable=True, index=True)
    tier = Column(SmallInteger, nullable=False, default=1)  # 1: Full Monitoring, 2: Screening, 3: Plains
    physiography_zone = Column(String(50), nullable=False, default="ne_hills")
    mean_elevation_m = Column(Float, nullable=False, default=1000.0)
    mean_slope_deg = Column(Float, nullable=False, default=25.0)
    dominant_lithology = Column(String(50), nullable=False, default="lesser_himalaya")
    is_1893_seismic_zone = Column(SmallInteger, nullable=False, default=5)  # Zone 2, 3, 4, or 5
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry_status = Column(String(30), nullable=False, default="AVAILABLE")  # AVAILABLE or PENDING_BOUNDARY
    terrain_provenance = Column(
        String(150),
        nullable=False,
        default="ESTIMATED / HEURISTIC — pending Copernicus GLO-30 DEM ingestion (see ARCHITECTURE.md)"
    )
    headquarters = Column(String(100), nullable=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    centroid = Column(Geometry("POINT", srid=4326), nullable=True)
    boundary_source = Column(String(100), default="Local Government Directory (LGD) / Survey of India")
    licence = Column(String(100), default="Open Government Data (OGD) India")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    state = relationship("State", back_populates="districts")
    grid_cells = relationship("GridCell", back_populates="district", cascade="all, delete-orphan")
    weather_observations = relationship("WeatherObservation", back_populates="district", cascade="all, delete-orphan")
    satellite_observations = relationship("SatelliteObservation", back_populates="district", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="district", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="district", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="district", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_district_state_name", "state_id", "name"),
        Index("idx_district_tier", "tier"),
        Index("idx_district_lgd_code", "lgd_code"),
    )


class GridCell(Base):
    __tablename__ = "grid_cells"

    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True)
    cell_code = Column(String(50), unique=True, nullable=False, index=True)
    resolution_m = Column(Float, default=1000.0)
    elevation_m = Column(Float, nullable=True)
    slope_deg = Column(Float, nullable=True)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=True)

    district = relationship("District", back_populates="grid_cells")


# ---------------------------------------------------------------------------
# 2. Source Provenance & Freshness Registry
# ---------------------------------------------------------------------------
class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(50), primary_key=True)  # e.g., 'MOSDAC_INSAT3D_QPE', 'NASA_GPM_IMERG', 'OPEN_METEO'
    name = Column(String(150), nullable=False)
    provider = Column(String(100), nullable=False)  # e.g., 'ISRO/MOSDAC', 'NASA', 'Copernicus'
    cadence_minutes = Column(Integer, nullable=False)  # e.g., 30 for INSAT, 30 for GPM, 60 for Open-Meteo
    licence = Column(String(100), nullable=False)
    api_endpoint = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    health = relationship("SourceHealth", back_populates="data_source", uselist=False, cascade="all, delete-orphan")


class SourceHealth(Base):
    __tablename__ = "source_health"

    source_id = Column(String(50), ForeignKey("data_sources.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(20), nullable=False, default="FRESH")  # FRESH, RECENT, AGING, STALE, OFFLINE
    last_successful_fetch = Column(DateTime(timezone=True), nullable=True)
    last_attempt_status = Column(String(50), nullable=True)
    consecutive_failures = Column(Integer, default=0)
    average_latency_ms = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    data_source = relationship("DataSource", back_populates="health")


# ---------------------------------------------------------------------------
# 3. Weather & Satellite Observations (Time-Series)
# ---------------------------------------------------------------------------
class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(50), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    observation_time = Column(DateTime(timezone=True), nullable=False, index=True)
    ingestion_time = Column(DateTime(timezone=True), default=utc_now)
    temperature_c = Column(Float, nullable=True)
    relative_humidity_pct = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)
    rainfall_1h_mm = Column(Float, nullable=True)
    rainfall_24h_mm = Column(Float, nullable=True)
    rainfall_7d_cumulative_mm = Column(Float, nullable=True)
    antecedent_saturation_index = Column(Float, nullable=True)
    quality_flag = Column(String(20), default="NOMINAL")  # NOMINAL, DEGRADED, ESTIMATED, UNAVAILABLE
    is_forecast = Column(Boolean, default=False)

    district = relationship("District", back_populates="weather_observations")

    __table_args__ = (
        Index("idx_weather_district_obs_time", "district_id", "observation_time"),
        UniqueConstraint("district_id", "source_id", "observation_time", "is_forecast", name="uq_district_weather_slot"),
    )


class SatelliteObservation(Base):
    __tablename__ = "satellite_observations"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(50), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    granule_id = Column(String(150), nullable=False)
    capture_time = Column(DateTime(timezone=True), nullable=False, index=True)
    snow_cover_fraction = Column(Float, nullable=True)
    snowmelt_mm_day = Column(Float, nullable=True)
    bare_soil_index = Column(Float, nullable=True)
    ndvi = Column(Float, nullable=True)
    sar_inundation_km2 = Column(Float, nullable=True)
    cloud_cover_pct = Column(Float, nullable=True)
    raster_s3_path = Column(String(255), nullable=True)
    quality_flag = Column(String(20), default="NOMINAL")

    district = relationship("District", back_populates="satellite_observations")

    __table_args__ = (
        Index("idx_satellite_district_capture_time", "district_id", "capture_time"),
    )


# ---------------------------------------------------------------------------
# 4. Natural Hazards, Seismic Events, & Model Registry
# ---------------------------------------------------------------------------
class HazardEvent(Base):
    __tablename__ = "hazard_events"

    id = Column(String(50), primary_key=True)  # e.g., USGS event id 'us7000xxxx' or 'COOLR_12345'
    hazard_type = Column(String(50), nullable=False)  # 'EARTHQUAKE', 'HISTORICAL_LANDSLIDE', 'GLOF'
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    magnitude = Column(Float, nullable=True)
    depth_km = Column(Float, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    epicenter = Column(Geometry("POINT", srid=4326), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    pga_estimate_g = Column(Float, nullable=True)
    source = Column(String(50), nullable=False)  # 'USGS_FDSN', 'NASA_COOLR', 'SDMA'
    disclosure = Column(String(255), nullable=True)  # "Validation only; carries media-reporting bias"


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(50), primary_key=True)  # 'LANDSAFE_PHYS_V1', 'XGBOOST_LANDSLIDE_V1'
    name = Column(String(100), nullable=False)
    hazard_type = Column(String(50), nullable=False)  # 'Landslide', 'Flood', 'GLOF'
    description = Column(Text, nullable=True)
    trained_at = Column(DateTime(timezone=True), default=utc_now)
    features_used = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)


# ---------------------------------------------------------------------------
# 5. Risk Assessments, Predictions, Alerts, and Reports
# ---------------------------------------------------------------------------
class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version_id = Column(String(50), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False)
    calculated_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    factor_of_safety = Column(Float, nullable=True)
    susceptibility_score = Column(Float, nullable=True)
    trigger_score = Column(Float, nullable=True)
    composite_hazard_index = Column(Float, nullable=False)
    hazard_level = Column(String(20), nullable=False)  # LOW, MODERATE, HIGH, SEVERE, EXTREME
    model_uncertainty = Column(Float, nullable=True)
    linear_shap_factors = Column(JSON, nullable=True)
    glof_risk_level = Column(String(20), nullable=True)
    flash_flood_level = Column(String(20), nullable=True)
    input_quality_flag = Column(String(20), default="NOMINAL")

    district = relationship("District", back_populates="risk_assessments")

    __table_args__ = (
        Index("idx_risk_district_calculated_at", "district_id", "calculated_at"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version_id = Column(String(50), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False)
    predicted_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    landslide_probability = Column(Float, nullable=True)
    risk_category = Column(String(50), nullable=False)
    flood_probability = Column(Float, nullable=True)
    flood_category = Column(String(50), nullable=True)
    top_factors = Column(JSON, nullable=True)
    is_simulated = Column(Boolean, default=False)

    district = relationship("District", back_populates="predictions")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True)
    hazard_type = Column(String(50), nullable=False)  # 'Landslide', 'Flash Flood', 'GLOF'
    severity = Column(String(20), nullable=False)  # 'INFO', 'WATCH', 'WARNING', 'CRITICAL'
    title = Column(String(200), nullable=False)
    message_en = Column(Text, nullable=False)
    message_hi = Column(Text, nullable=True)
    message_bn = Column(Text, nullable=True)
    message_as = Column(Text, nullable=True)
    message_ml = Column(Text, nullable=True)
    cap_identifier = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    issued_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    cooldown_until = Column(DateTime(timezone=True), nullable=False)

    district = relationship("District", back_populates="alerts")


class Report(Base):
    __tablename__ = "reports"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    scope = Column(String(20), nullable=False)  # 'NATIONAL', 'STATE', 'DISTRICT'
    scope_id = Column(Integer, nullable=True)  # district_id or state_id
    title = Column(String(200), nullable=False)
    generated_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    report_data = Column(JSON, nullable=False)
    pdf_path = Column(String(255), nullable=True)
    disclaimer = Column(Text, nullable=False)
