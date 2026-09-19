"""Quarantined Demonstration / Simulation Logic (DEMO MODE ONLY)

This module contains synthetic calculations and simulations used strictly when
LANDSAFE_MODE=demo. It is isolated from the production data ingestion pipeline.
"""
from datetime import datetime, timedelta
from typing import Dict, Any

def compute_synthetic_satellite_indices(elevation: float, slope: float, lat: float, lon: float, is_monsoon: bool = True) -> Dict[str, Any]:
    """
    Computes synthetic demonstration satellite indices.
    WARNING: Not derived from real band rasters. For offline demonstration only.
    """
    now = datetime.utcnow()
    last_updated_time = (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M UTC")

    if elevation > 2500:
        snow_cover = min(92.0, (elevation - 2200) * 0.035 + (25.0 if lat > 27.5 else 10.0))
        snowmelt_rate = round(snow_cover * 0.08, 2) if is_monsoon else 0.4
    elif elevation > 1800:
        snow_cover = round(max(0.0, (elevation - 1800) * 0.015), 1)
        snowmelt_rate = 0.2
    else:
        snow_cover = 0.0
        snowmelt_rate = 0.0

    bare_soil = round(min(75.0, max(8.0, slope * 0.95 + (15.0 if elevation < 1000 else 5.0))), 1)
    ndvi = round(max(0.15, min(0.88, 0.85 - (bare_soil / 100.0) * 0.5 - (0.2 if snow_cover > 30 else 0.0))), 2)
    farm_change = bool(slope > 20 and slope < 38 and bare_soil > 30 and ndvi > 0.45)
    flood_flag = bool(elevation < 150 and slope < 8 and (lat < 26.5 or "Assam" in str(lat)))

    return {
        "status": "DEMO_SIMULATION",
        "snow_cover_pct": snow_cover,
        "snowmelt_rate": snowmelt_rate,
        "bare_soil_pct": bare_soil,
        "vegetation_index": ndvi,
        "farm_change_flag": farm_change,
        "flood_extent_flag": flood_flag,
        "source": "DEMO SIMULATOR (Synthetic)",
        "is_sample_data": True,
        "quality_flag": "SYNTHETIC_DEMO",
        "last_updated": last_updated_time,
        "disclaimer": "DEMO DATA: Synthetic demonstration indices. Not from real satellite band rasters."
    }
