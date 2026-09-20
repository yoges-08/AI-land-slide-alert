"""ORM and API schemas.

M0: defect 2 extends into this file. Observed quantities carried column-level
defaults (WeatherRecord.temperature=22.0, humidity=75.0;
SatelliteFeature.bare_soil_pct=15.0, vegetation_index=0.65) and Pydantic
response defaults (LocationResponse.rainfall_24h=12.0, is_sample_data=False).
Those defaults are a fabrication mechanism: the baseline served 12.0 mm of rain
for all 304 sites because the JSON had no such field.

Every observed quantity is now nullable with no default, so absence renders as
NO DATA. Table shapes are otherwise kept and extended, per the project
decisions; M1 migrates them to PostgreSQL + PostGIS and adds the provenance
columns.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel, Field

Base = declarative_base()

# --- SQLAlchemy ORM Models ---

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    coverage_tier = Column(String(50), default="FULL_HAZARD_MONITORING")
    has_prediction = Column(Boolean, default=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, nullable=False)
    slope = Column(Float, nullable=False)
    aspect = Column(String(20), default="N")
    soil_type = Column(String(50), default="Loam")
    geology = Column(String(100), default="Phyllite & Schist")
    land_cover = Column(String(50), default="Dense Forest")
    distance_road = Column(Float, default=200.0)
    distance_river = Column(Float, default=500.0)
    historical_landslides = Column(Integer, default=0)
    image_url = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    weather_records = relationship("WeatherRecord", back_populates="location", cascade="all, delete-orphan")
    satellite_features = relationship("SatelliteFeature", back_populates="location", cascade="all, delete-orphan")
    predictions = relationship("PredictionRecord", back_populates="location", cascade="all, delete-orphan")
    alerts = relationship("AlertRecord", back_populates="location", cascade="all, delete-orphan")


class SatelliteFeature(Base):
    __tablename__ = "satellite_features"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    capture_date = Column(DateTime, default=datetime.utcnow)
    snow_cover_pct = Column(Float, nullable=True)
    snowmelt_rate = Column(Float, nullable=True)
    bare_soil_pct = Column(Float, nullable=True)
    vegetation_index = Column(Float, nullable=True)
    farm_change_flag = Column(Boolean, nullable=True)
    flood_extent_flag = Column(Boolean, nullable=True)
    source = Column(String(100), nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)

    location = relationship("Location", back_populates="satellite_features")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    rainfall_1h = Column(Float, nullable=True)
    rainfall_24h = Column(Float, nullable=True)
    rainfall_7d_cumulative = Column(Float, nullable=True)
    rainfall_intensity = Column(Float, nullable=True)
    weather_code = Column(Integer, nullable=True)
    condition_text = Column(String(50), nullable=True)
    source = Column(String(100), nullable=False)

    location = relationship("Location", back_populates="weather_records")


class PredictionRecord(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    predicted_at = Column(DateTime, default=datetime.utcnow)
    risk_probability = Column(Float, nullable=False)
    risk_category = Column(String(50), nullable=False)
    flood_risk_probability = Column(Float, default=0.0)
    flood_risk_category = Column(String(20), default="Low")
    top_factors = Column(Text, nullable=True)
    is_simulated = Column(Boolean, default=False)

    location = relationship("Location", back_populates="predictions")


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    hazard_type = Column(String(30), default="Landslide")
    severity = Column(String(20), default="High")
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_read = Column(Boolean, default=False)

    location = relationship("Location", back_populates="alerts")


# --- Pydantic Schemas ---

class KeyRiskFactors(BaseModel):
    """None where the driving input was not supplied. Never a default number."""
    heavy_rainfall: Optional[int] = None
    steep_slope: Optional[int] = None
    land_cover_change: Optional[int] = None
    historical_landslide: Optional[int] = None

class LocationBase(BaseModel):
    name: str
    state: str
    district: Optional[str] = None
    coverage_tier: Optional[str] = "FULL_HAZARD_MONITORING"
    has_prediction: Optional[bool] = True
    latitude: float
    longitude: float
    elevation: float
    slope: float
    aspect: Optional[str] = "N"
    soil_type: Optional[str] = "Loam"
    geology: Optional[str] = "Phyllite & Schist"
    land_cover: Optional[str] = "Dense Forest"
    distance_road: Optional[float] = 200.0
    distance_river: Optional[float] = 500.0
    historical_landslides: Optional[int] = 0
    image_url: Optional[str] = None

class LocationResponse(LocationBase):
    id: int
    # Hazard attributes were generated with random.uniform at seed time
    # (defect 5). They are withheld until M1 replaces the seed data.
    hazard_index: Optional[float] = None
    risk_category: Optional[str] = None
    flood_risk_category: Optional[str] = None
    snow_cover_pct: Optional[float] = None
    snowmelt_rate: Optional[float] = None
    bare_soil_pct: Optional[float] = None
    vegetation_index: Optional[float] = None
    farm_change_flag: Optional[bool] = None
    flood_extent_flag: Optional[bool] = None
    rainfall_24h: Optional[float] = None
    key_risk_factors: Optional[KeyRiskFactors] = None
    satellite_source: Optional[str] = None
    data_status: str = "NO_DATA"
    provenance: str = "UNVERIFIED_SEED"

    class Config:
        from_attributes = True

class StateDistrictHierarchyItem(BaseModel):
    state: str
    districts: List[str]
    total_locations: int
    hazard_monitoring_active: bool

class PredictRequest(BaseModel):
    """Rainfall is required, not defaulted.

    The baseline defaulted rainfall_24h to 45.0 mm, so a caller who supplied
    only coordinates received a hazard score computed from rainfall that was
    never observed anywhere. An inference needs its inputs stated.
    """
    latitude: float
    longitude: float
    elevation: float
    slope: float
    rainfall_1h: float
    rainfall_24h: float
    rainfall_7d_cumulative: float
    rainfall_intensity: float
    soil_type: str = "Loam"
    geology: str = "Phyllite & Schist"
    land_cover: str = "Dense Forest"
    aspect: str = "N"
    distance_road: float = 150.0
    distance_river: float = 400.0
    historical_landslides: int = 2
    snow_cover_pct: float = 0.0
    snowmelt_rate: float = 0.0
    bare_soil_pct: float = 20.0
    vegetation_index: float = 0.60
    farm_change_flag: bool = False
    flood_extent_flag: bool = False

class PredictResponse(BaseModel):
    """Field names changed in M0: *_probability -> *_index. The model was
    trained on synthetic labels and its output is not a probability."""
    hazard_index: float
    risk_category: str
    flood_index: Optional[float] = None
    flood_risk_category: Optional[str] = None
    top_factors: Dict[str, float]
    shap_values: Optional[Dict[str, float]] = None
    disclaimer: str
    timestamp: str

class SimulationRequest(BaseModel):
    location_id: Optional[int] = None
    rainfall_24h_delta: float = 0.0
    slope_override: Optional[float] = None
    snowmelt_rate_override: Optional[float] = None
    bare_soil_pct_override: Optional[float] = None
    farm_change_flag_override: Optional[bool] = None

class SimulationResponse(BaseModel):
    original_hazard_index: float
    simulated_hazard_index: float
    original_risk_category: str
    simulated_risk_category: str
    delta_index: float
    simulated_flood_index: Optional[float] = None
    simulated_flood_category: Optional[str] = None
    factor_changes: Dict[str, Any]
    disclaimer: str

class AlertItem(BaseModel):
    id: int
    location_id: int
    location_name: str
    state: str
    district: Optional[str] = None
    hazard_type: str
    severity: str
    title: str
    message: str
    created_at: str
    is_active: bool
    is_read: bool

class SatelliteInfoResponse(BaseModel):
    """All index fields nullable: no satellite ingestion exists yet (M4)."""
    location_id: int
    location_name: str
    district: Optional[str] = None
    state: Optional[str] = None
    snow_cover_pct: Optional[float] = None
    snowmelt_rate: Optional[float] = None
    bare_soil_pct: Optional[float] = None
    vegetation_index: Optional[float] = None
    farm_change_flag: Optional[bool] = None
    flood_extent_flag: Optional[bool] = None
    source: str
    last_updated: Optional[str] = None
    disclaimer: str

# Rebuild all models to resolve forward annotations
LocationBase.model_rebuild()
LocationResponse.model_rebuild()
StateDistrictHierarchyItem.model_rebuild()
PredictRequest.model_rebuild()
PredictResponse.model_rebuild()
SimulationRequest.model_rebuild()
SimulationResponse.model_rebuild()
AlertItem.model_rebuild()
SatelliteInfoResponse.model_rebuild()

