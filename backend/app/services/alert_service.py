from datetime import datetime, timedelta
from typing import List, Dict, Any

DEFAULT_ALERTS = [
    {
        "id": 1,
        "location_id": 1,
        "location_name": "Gangtok",
        "state": "Sikkim",
        "hazard_type": "Landslide",
        "severity": "High",
        "title": "High Risk Detected",
        "message": "Heavy 24h precipitation (142 mm) exceeding critical pore-pressure threshold on steep 34° slopes.",
        "created_at": "2 hours ago",
        "is_active": True,
        "is_read": False
    },
    {
        "id": 2,
        "location_id": 21,
        "location_name": "Tawang",
        "state": "Arunachal Pradesh",
        "hazard_type": "Landslide",
        "severity": "High",
        "title": "Snowmelt Runoff Advisory",
        "message": "Elevated spring snowmelt rate (6.8 mm/day) combined with active slope road-cut destabilization.",
        "created_at": "4 hours ago",
        "is_active": True,
        "is_read": False
    },
    {
        "id": 3,
        "location_id": 41,
        "location_name": "Shillong",
        "state": "Meghalaya",
        "hazard_type": "Landslide",
        "severity": "Moderate",
        "title": "Moderate Risk Warning",
        "message": "Continuous monsoon rainfall accumulation reaching 78 mm over weathered quartzite slopes.",
        "created_at": "6 hours ago",
        "is_active": True,
        "is_read": True
    },
    {
        "id": 4,
        "location_id": 81,
        "location_name": "Haflong (Dima Hasao)",
        "state": "Assam",
        "hazard_type": "Landslide",
        "severity": "High",
        "title": "Disang Shale Saturation Alert",
        "message": "Critical water saturation in weathered Disang shale formation along NH-27 hill corridor.",
        "created_at": "7 hours ago",
        "is_active": True,
        "is_read": False
    },
    {
        "id": 5,
        "location_id": 71,
        "location_name": "Aizawl",
        "state": "Mizoram",
        "hazard_type": "Landslide",
        "severity": "Moderate",
        "title": "Risk Stable / Under Observation",
        "message": "Rainfall eased; groundwater drainage monitoring active along eastern anticlinal slope ridge.",
        "created_at": "8 hours ago",
        "is_active": False,
        "is_read": True
    },
    {
        "id": 6,
        "location_id": 95,
        "location_name": "Silchar (Barak Basin)",
        "state": "Assam",
        "hazard_type": "Flood",
        "severity": "High",
        "title": "Sentinel-1 SAR Inundation Alert",
        "message": "Synthetic Aperture Radar detects flood extent encroachment across low-lying riverbanks.",
        "created_at": "9 hours ago",
        "is_active": True,
        "is_read": False
    }
]

def get_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    return DEFAULT_ALERTS[:limit]

def create_alert(location_id: int, location_name: str, state: str, hazard_type: str, severity: str, title: str, message: str) -> Dict[str, Any]:
    new_alert = {
        "id": len(DEFAULT_ALERTS) + 1,
        "location_id": location_id,
        "location_name": location_name,
        "state": state,
        "hazard_type": hazard_type,
        "severity": severity,
        "title": title,
        "message": message,
        "created_at": "Just now",
        "is_active": True,
        "is_read": False
    }
    DEFAULT_ALERTS.insert(0, new_alert)
    return new_alert

def evaluate_threshold_breach(location: dict, live_weather: dict, risk_result: dict):
    """
    Evaluates if current conditions breach prototype early warning thresholds.
    """
    risk_prob = risk_result.get("risk_probability", 0.0)
    rainfall_24h = live_weather.get("rainfall_24h", 0.0)
    
    if risk_prob >= 0.70:
        return {
            "breach": True,
            "severity": "Critical" if risk_prob >= 0.85 else "High",
            "title": f"High Landslide Risk: {location.get('name')}",
            "message": f"Risk probability calculated at {int(risk_prob*100)}% due to {rainfall_24h}mm rainfall and steep terrain."
        }
    elif risk_prob >= 0.40 and rainfall_24h > 60:
        return {
            "breach": True,
            "severity": "Moderate",
            "title": f"Precipitation Warning: {location.get('name')}",
            "message": f"Cumulative 24h rainfall reached {rainfall_24h}mm under elevated slope susceptibility."
        }
    return {"breach": False}
