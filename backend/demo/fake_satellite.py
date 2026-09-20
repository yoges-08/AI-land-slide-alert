"""QUARANTINED — demo only. Never import from backend/app/.

This is the original satellite_service.compute_satellite_indices(), moved here
verbatim in M0 (confirmed defect 1). It derives snow cover, NDVI, bare soil and
flood extent from elevation and slope via hand-tuned formulas. No satellite band
data is involved at any point, and the baseline labelled its output
"NASA MODIS / Sentinel-2 & Sentinel-1".

Kept only so LANDSAFE_MODE=demo can still render a populated screen. Real values
arrive in M4 (NISAR -> Sentinel-1 for SAR, Resourcesat -> Sentinel-2 for
vegetation), gated on Bhoonidhi account approval.
"""
from datetime import timedelta
from typing import Any, Dict

from backend.app.core.freshness import utcnow
from backend.app.core.mode import DEMO_LABEL, require_demo_mode

require_demo_mode("backend.demo.fake_satellite")


def compute_satellite_indices(elevation: float, slope: float, lat: float, lon: float,
                              is_monsoon: bool = True) -> Dict[str, Any]:
    now = utcnow()

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
    ndvi = round(max(0.15, min(0.88, 0.85 - (bare_soil / 100.0) * 0.5
                               - (0.2 if snow_cover > 30 else 0.0))), 2)
    farm_change = bool(20 < slope < 38 and bare_soil > 30 and ndvi > 0.45)
    # Baseline also had `or "Assam" in str(lat)` here — a string test against a
    # float, always False. Dropped rather than carried into the demo.
    flood_flag = bool(elevation < 150 and slope < 8 and lat < 26.5)

    return {
        "data_mode": DEMO_LABEL,
        "snow_cover_pct": snow_cover,
        "snowmelt_rate": snowmelt_rate,
        "bare_soil_pct": bare_soil,
        "vegetation_index": ndvi,
        "farm_change_flag": farm_change,
        "flood_extent_flag": flood_flag,
        "source": f"{DEMO_LABEL} — synthetic, derived from elevation/slope only",
        "last_updated": (now - timedelta(hours=4)).isoformat(),
        "disclaimer": f"{DEMO_LABEL}. Not derived from any satellite observation.",
    }
