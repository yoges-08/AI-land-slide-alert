from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from backend.app.core.database import Base

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
    snow_cover_pct = Column(Float, default=0.0)
    snowmelt_rate = Column(Float, default=0.0)
    bare_soil_pct = Column(Float, default=15.0)
    vegetation_index = Column(Float, default=0.65)
    farm_change_flag = Column(Boolean, default=False)
    flood_extent_flag = Column(Boolean, default=False)
    source = Column(String(50), default="NASA/Copernicus")
    last_updated = Column(DateTime, default=datetime.utcnow)

    location = relationship("Location", back_populates="satellite_features")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float, default=22.0)
    humidity = Column(Float, default=75.0)
    wind_speed = Column(Float, default=12.0)
    rainfall_1h = Column(Float, default=0.0)
    rainfall_24h = Column(Float, default=0.0)
    rainfall_7d_cumulative = Column(Float, default=0.0)
    rainfall_intensity = Column(Float, default=0.0)
    weather_code = Column(Integer, default=1)
    condition_text = Column(String(50), default="Clear")
    source = Column(String(50), default="Open-Meteo")

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
    heavy_rainfall: int = 50
    steep_slope: int = 40
    land_cover_change: int = 30
    historical_landslide: int = 20

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
    risk_probability: Optional[float] = 0.25
    risk_category: str = "Low"
    flood_risk_category: str = "Low"
    snow_cover_pct: float = 0.0
    snowmelt_rate: float = 0.0
    bare_soil_pct: float = 15.0
    vegetation_index: float = 0.65
    farm_change_flag: bool = False
    flood_extent_flag: bool = False
    rainfall_24h: float = 12.0
    key_risk_factors: KeyRiskFactors
    satellite_source: str = "NASA/Copernicus"
    is_sample_data: bool = False

    class Config:
        from_attributes = True

class StateDistrictHierarchyItem(BaseModel):
    state: str
    districts: List[str]
    total_locations: int
    hazard_monitoring_active: bool

class PredictRequest(BaseModel):
    latitude: float
    longitude: float
    elevation: float
    slope: float
    rainfall_1h: float = 5.0
    rainfall_24h: float = 45.0
    rainfall_7d_cumulative: float = 120.0
    rainfall_intensity: float = 5.0
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
    risk_probability: float
    risk_category: str
    flood_risk_probability: float
    flood_risk_category: str
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
    original_risk_probability: float
    simulated_risk_probability: float
    original_risk_category: str
    simulated_risk_category: str
    delta_risk: float
    simulated_flood_probability: float
    simulated_flood_category: str
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
    location_id: int
    location_name: str
    district: Optional[str] = None
    state: Optional[str] = None
    status: Optional[str] = "NOMINAL"
    snow_cover_pct: Optional[float] = None
    snowmelt_rate: Optional[float] = None
    bare_soil_pct: Optional[float] = None
    vegetation_index: Optional[float] = None
    farm_change_flag: Optional[bool] = False
    flood_extent_flag: Optional[bool] = False
    source: str = "Copernicus / NASA"
    quality_flag: Optional[str] = "NOMINAL"
    last_updated: Optional[str] = None
    disclaimer: str = "Advisory satellite data layer."
