"""API Pydantic Schemas for LANDSAFE-NER.

Every observed quantity is nullable with no default, so absence renders as
NO DATA.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(from_attributes=True)


class StateDistrictHierarchyItem(BaseModel):
    state: str
    districts: List[str]
    total_locations: int
    hazard_monitoring_active: bool


class PredictRequest(BaseModel):
    """Rainfall is required, not defaulted."""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation: float = Field(..., ge=-500.0, le=9000.0)
    slope: float = Field(..., ge=0.0, le=90.0)
    rainfall_1h: float = Field(..., ge=0.0)
    rainfall_24h: float = Field(..., ge=0.0)
    rainfall_7d_cumulative: float = Field(..., ge=0.0)
    rainfall_intensity: float = Field(..., ge=0.0)
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
