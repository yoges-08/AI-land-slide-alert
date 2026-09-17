import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.models.schema import (
    LocationResponse, PredictRequest, PredictResponse,
    SimulationRequest, SimulationResponse, AlertItem,
    SatelliteInfoResponse, StateDistrictHierarchyItem
)
from backend.app.services.weather_service import fetch_live_weather, get_fallback_weather
from backend.app.services.satellite_service import compute_satellite_indices, get_available_layers
from backend.app.services.ml_service import predict_risk, simulate_scenario, get_model_info
from backend.app.services.alert_service import get_recent_alerts, create_alert, evaluate_threshold_breach

router = APIRouter()

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ne_india_locations.json"
LOCATIONS_CACHE = []

def get_all_cached_locations():
    global LOCATIONS_CACHE
    if not LOCATIONS_CACHE:
        if DATA_PATH.exists():
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                LOCATIONS_CACHE = json.load(f)
        else:
            LOCATIONS_CACHE = []
    return LOCATIONS_CACHE

@router.get("/locations", response_model=List[LocationResponse])
async def get_locations(
    state: Optional[str] = None,
    district: Optional[str] = None,
    risk: Optional[str] = None
):
    """
    Returns list of locations across India. Supports State, District, and Risk filtering.
    """
    locs = get_all_cached_locations()
    if state:
        locs = [l for l in locs if l.get("state", "").lower() == state.lower()]
    if district:
        locs = [l for l in locs if l.get("district", "").lower() == district.lower()]
    if risk:
        locs = [l for l in locs if risk.lower() in l.get("risk_category", "").lower()]
    return locs

@router.get("/hierarchy", response_model=List[StateDistrictHierarchyItem])
async def get_state_district_hierarchy():
    """
    Returns all Indian States, their constituent districts, and whether active hazard monitoring is enabled.
    """
    locs = get_all_cached_locations()
    state_map = {}

    for loc in locs:
        st = loc.get("state", "Unknown")
        dist = loc.get("district", st)
        tier = loc.get("coverage_tier", "FULL_HAZARD_MONITORING")

        if st not in state_map:
            state_map[st] = {
                "state": st,
                "districts": set(),
                "total_locations": 0,
                "hazard_monitoring_active": False
            }

        state_map[st]["districts"].add(dist)
        state_map[st]["total_locations"] += 1
        if tier == "FULL_HAZARD_MONITORING":
            state_map[st]["hazard_monitoring_active"] = True

    hierarchy = []
    for st, data in sorted(state_map.items()):
        hierarchy.append(StateDistrictHierarchyItem(
            state=st,
            districts=sorted(list(data["districts"])),
            total_locations=data["total_locations"],
            hazard_monitoring_active=data["hazard_monitoring_active"]
        ))

    return hierarchy

@router.get("/location/{loc_id}")
async def get_location_detail(loc_id: int):
    """
    Returns full details for a location with State and District taxonomy, live weather, and ML risk scores.
    """
    locs = get_all_cached_locations()
    loc = next((l for l in locs if l["id"] == loc_id), None)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location ID {loc_id} not found.")

    weather = await fetch_live_weather(loc["latitude"], loc["longitude"])
    satellite = compute_satellite_indices(loc["elevation"], loc["slope"], loc["latitude"], loc["longitude"])

    combined_features = dict(loc)
    combined_features.update({
        "rainfall_1h": weather.get("rainfall_1h", 0.0),
        "rainfall_24h": weather.get("rainfall_24h", loc.get("rainfall_24h", 25.0)),
        "rainfall_7d_cumulative": weather.get("rainfall_7d_cumulative", 120.0),
        "rainfall_intensity": weather.get("rainfall_1h", 0.0),
        "snow_cover_pct": satellite.get("snow_cover_pct", loc.get("snow_cover_pct", 0.0)),
        "snowmelt_rate": satellite.get("snowmelt_rate", loc.get("snowmelt_rate", 0.0)),
        "bare_soil_pct": satellite.get("bare_soil_pct", loc.get("bare_soil_pct", 20.0)),
        "vegetation_index": satellite.get("vegetation_index", loc.get("vegetation_index", 0.65)),
        "farm_change_flag": satellite.get("farm_change_flag", loc.get("farm_change_flag", False)),
        "flood_extent_flag": satellite.get("flood_extent_flag", loc.get("flood_extent_flag", False))
    })

    if loc.get("has_prediction", True):
        ml_result = predict_risk(combined_features)
    else:
        ml_result = {
            "risk_probability": 0.05,
            "risk_category": "Insufficient data (Plain/Low Hazard)",
            "flood_risk_probability": 0.10 if loc["elevation"] < 100 else 0.02,
            "flood_risk_category": "Low",
            "key_risk_factors": {"heavy_rainfall": 10, "steep_slope": 5, "land_cover_change": 10, "historical_landslide": 0},
            "top_factors": {"slope": -1.2, "elevation": -0.8},
            "shap_values": {"slope": -1.2, "elevation": -0.8},
            "model_version": "LANDSAFE-XGBoost-v1.0 (Plain Zone Notice)"
        }

    threshold_eval = evaluate_threshold_breach(loc, weather, ml_result)

    return {
        "location": loc,
        "weather": weather,
        "satellite": satellite,
        "prediction": ml_result,
        "threshold_alert": threshold_eval,
        "disclaimer": settings.PROTOTYPE_DISCLAIMER,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/weather/{lat}/{lon}")
async def get_weather(lat: float, lon: float):
    weather_data = await fetch_live_weather(lat, lon)
    return weather_data

@router.post("/predict", response_model=PredictResponse)
async def predict_custom_landslide(payload: PredictRequest):
    result = predict_risk(payload.model_dump())
    return PredictResponse(
        risk_probability=result["risk_probability"],
        risk_category=result["risk_category"],
        flood_risk_probability=result["flood_risk_probability"],
        flood_risk_category=result["flood_risk_category"],
        top_factors=result["top_factors"],
        shap_values=result["shap_values"],
        disclaimer=settings.PROTOTYPE_DISCLAIMER,
        timestamp=datetime.utcnow().isoformat()
    )

@router.post("/predict/flood")
async def predict_custom_flood(payload: PredictRequest):
    result = predict_risk(payload.model_dump())
    return {
        "flood_risk_probability": result["flood_risk_probability"],
        "flood_risk_category": result["flood_risk_category"],
        "disclaimer": settings.PROTOTYPE_DISCLAIMER,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/risk/{loc_id}")
async def get_location_risk(loc_id: int):
    locs = get_all_cached_locations()
    loc = next((l for l in locs if l["id"] == loc_id), None)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location {loc_id} not found.")

    res = predict_risk(loc)
    return {
        "location_id": loc_id,
        "name": loc["name"],
        "state": loc["state"],
        "district": loc.get("district", loc["state"]),
        "risk_probability": res["risk_probability"],
        "risk_category": res["risk_category"],
        "key_risk_factors": res["key_risk_factors"],
        "top_factors": res["top_factors"],
        "disclaimer": settings.PROTOTYPE_DISCLAIMER
    }

@router.get("/satellite/{loc_id}", response_model=SatelliteInfoResponse)
async def get_satellite_info(loc_id: int):
    locs = get_all_cached_locations()
    loc = next((l for l in locs if l["id"] == loc_id), None)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location {loc_id} not found.")

    sat_data = compute_satellite_indices(loc["elevation"], loc["slope"], loc["latitude"], loc["longitude"])
    return SatelliteInfoResponse(
        location_id=loc_id,
        location_name=loc["name"],
        district=loc.get("district", loc["state"]),
        state=loc.get("state"),
        snow_cover_pct=sat_data["snow_cover_pct"],
        snowmelt_rate=sat_data["snowmelt_rate"],
        bare_soil_pct=sat_data["bare_soil_pct"],
        vegetation_index=sat_data["vegetation_index"],
        farm_change_flag=sat_data["farm_change_flag"],
        flood_extent_flag=sat_data["flood_extent_flag"],
        source=sat_data["source"],
        last_updated=sat_data["last_updated"],
        disclaimer=sat_data["disclaimer"]
    )

@router.get("/satellite/layers/info")
async def get_satellite_layer_metadata():
    return get_available_layers()

@router.get("/alerts")
async def list_alerts(limit: int = 10):
    return get_recent_alerts(limit)

@router.post("/alerts")
async def create_new_alert(
    location_id: int = Body(...),
    location_name: str = Body(...),
    state: str = Body(...),
    hazard_type: str = Body("Landslide"),
    severity: str = Body("High"),
    title: str = Body(...),
    message: str = Body(...)
):
    alert = create_alert(location_id, location_name, state, hazard_type, severity, title, message)
    return alert

@router.get("/history/{loc_id}")
async def get_history(loc_id: int):
    locs = get_all_cached_locations()
    loc = next((l for l in locs if l["id"] == loc_id), None)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location {loc_id} not found.")

    weather = await fetch_live_weather(loc["latitude"], loc["longitude"])
    return {
        "location_id": loc_id,
        "name": loc["name"],
        "rainfall_trend_7d": weather.get("rainfall_trend_7d", []),
        "disclaimer": settings.PROTOTYPE_DISCLAIMER
    }

@router.post("/simulation", response_model=SimulationResponse)
async def run_simulation(payload: SimulationRequest):
    locs = get_all_cached_locations()
    loc_id = payload.location_id or 1
    loc = next((l for l in locs if l["id"] == loc_id), locs[0] if locs else None)
    if not loc:
        raise HTTPException(status_code=404, detail="No locations available for simulation.")

    sim_res = simulate_scenario(loc, payload.model_dump())
    return SimulationResponse(
        original_risk_probability=sim_res["original_risk_probability"],
        simulated_risk_probability=sim_res["simulated_risk_probability"],
        original_risk_category=sim_res["original_risk_category"],
        simulated_risk_category=sim_res["simulated_risk_category"],
        delta_risk=sim_res["delta_risk"],
        simulated_flood_probability=sim_res["simulated_flood_probability"],
        simulated_flood_category=sim_res["simulated_flood_category"],
        factor_changes=sim_res["factor_changes"],
        disclaimer=settings.PROTOTYPE_DISCLAIMER
    )

@router.get("/model/info")
async def get_ml_model_info():
    info = get_model_info()
    return info

@router.get("/export/report/{loc_id}")
async def export_risk_report(loc_id: int):
    locs = get_all_cached_locations()
    loc = next((l for l in locs if l["id"] == loc_id), None)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    weather = await fetch_live_weather(loc["latitude"], loc["longitude"])
    satellite = compute_satellite_indices(loc["elevation"], loc["slope"], loc["latitude"], loc["longitude"])
    risk = predict_risk(loc)

    report = {
        "title": f"LANDSAFE-NER Hazard Assessment Report — {loc['name']}, {loc.get('district', '')}, {loc['state']}",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "academic_disclaimer": settings.PROTOTYPE_DISCLAIMER,
        "location_metadata": loc,
        "live_weather": {
            "temperature_c": weather.get("temperature"),
            "rainfall_24h_mm": weather.get("rainfall_24h"),
            "rainfall_7d_cumulative_mm": weather.get("rainfall_7d_cumulative"),
            "condition": weather.get("condition_text")
        },
        "satellite_terrain_intelligence": satellite,
        "hazard_prediction": {
            "landslide_risk_probability": f"{int(risk['risk_probability'] * 100)}%",
            "landslide_risk_category": risk["risk_category"],
            "flood_risk_probability": f"{int(risk['flood_risk_probability'] * 100)}%",
            "flood_risk_category": risk["flood_risk_category"],
            "top_contributing_factors": risk["top_factors"],
            "shap_explanation": risk["shap_values"]
        }
    }
    return report
