"""Satellite layer metadata and (pending) satellite observations.

M0, confirmed defect 1: compute_satellite_indices() fabricated snow/NDVI/bare
soil/flood values from elevation and slope, then labelled them
"NASA MODIS / Sentinel-2 & Sentinel-1". It has been moved to
backend/demo/fake_satellite.py and is unreachable in production.

Until M4 ingestion lands, satellite observations are NO DATA with the pending
source named. The SatelliteFeature table shape is fine and is kept; only the
population function was fake.
"""
from __future__ import annotations

from typing import Any, Dict

from backend.app.core.freshness import no_data
from backend.app.core.mode import is_demo

# Tile layers actually available to us, free at the tier used.
# Removed in M0: ESRI World Imagery (arcgisonline) — a commercial service,
# outside the zero-budget rule and never a decided basemap.
SATELLITE_MAP_LAYERS: Dict[str, Dict[str, Any]] = {
    "nasa_gibs_truecolor": {
        "name": "NASA GIBS True Colour (MODIS Terra)",
        "type": "wmts",
        # {time} is substituted server-side per request date. Leaflet cannot
        # fill it, which is why the baseline URL could never have worked as a
        # plain TileLayer.
        "url_template": ("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
                         "MODIS_Terra_CorrectedReflectance_TrueColor/default/"
                         "{time}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"),
        "time_dimension": "required",
        "attribution": "NASA Global Imagery Browse Services (GIBS), EOSDIS",
        "source": "NASA GIBS",
        "licence": "NASA open data",
        "format": "jpg",
        "max_zoom": 9,
        "status": "VERIFIED",
    },
    "isro_bhuvan_wms": {
        "name": "ISRO Bhuvan LULC (india3)",
        "type": "wms",
        "url": "https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms",
        "layers": "india3",
        "attribution": "ISRO / NRSC Bhuvan",
        "source": "ISRO Bhuvan",
        "licence": "UNCONFIRMED for the india3 layer",
        "format": "image/png",
        "status": "PENDING_VERIFICATION",
        "enabled": False,
        "note": ("Toggle only, disabled by default. Licence for the india3 layer "
                 "is unconfirmed and it must be served as a WMS request, not a "
                 "slippy TileLayer."),
    },
}

# Derived index layers. These describe products we intend to ingest; none of
# them is populated yet. They are listed so the frontend can render an honest
# 'source pending' state rather than an empty panel.
PENDING_INDEX_LAYERS: Dict[str, Dict[str, Any]] = {
    "soil_moisture_flood_sar": {
        "name": "SAR soil moisture / flood extent",
        "primary": "NISAR S-SAR (Bhoonidhi)", "fallback": "Copernicus Sentinel-1",
        "status": "PENDING", "milestone": "M4",
        "blocker": "Bhoonidhi account approval",
    },
    "vegetation": {
        "name": "Vegetation / land cover",
        "primary": "Resourcesat LISS-3/4 (Bhoonidhi)", "fallback": "Copernicus Sentinel-2",
        "status": "PENDING", "milestone": "M4",
        "blocker": "Bhoonidhi account approval",
    },
    "rainfall_qpe": {
        "name": "Satellite rainfall (QPE)",
        "primary": "INSAT-3D/3DR IMSRA (MOSDAC)", "fallback": "NASA GPM IMERG",
        "status": "PENDING", "milestone": "M3/M4",
        "blocker": "MOSDAC account",
    },
    "fire_hotspots": {
        "name": "Active fire hotspots",
        "primary": "NASA FIRMS", "fallback": None,
        "status": "PENDING", "milestone": "M4", "blocker": "FIRMS MAP_KEY",
    },
}

_PENDING_REASON = (
    "Satellite indices are not yet ingested. The baseline values were derived "
    "from elevation and slope, not from any satellite band, and were removed in M0."
)


def get_satellite_observation(location: dict) -> Dict[str, Any]:
    """Return real satellite observations, or NO DATA. Never derived values."""
    if is_demo():
        from backend.demo.fake_satellite import compute_satellite_indices
        return compute_satellite_indices(
            location.get("elevation", 0.0), location.get("slope", 0.0),
            location.get("latitude", 0.0), location.get("longitude", 0.0),
        )

    status = no_data(
        "nisar_ssar",
        reason=_PENDING_REASON,
        pending="M4 ingestion: FIRMS -> INSAT-3D/3DR -> NISAR -> Resourcesat",
    )
    return {
        "data_status": status,
        "status": "NO_DATA",
        "source": "pending — NISAR / Sentinel-1 / Resourcesat / Sentinel-2 (M4)",
        "snow_cover_pct": None,
        "snowmelt_rate": None,
        "bare_soil_pct": None,
        "vegetation_index": None,
        "farm_change_flag": None,
        "flood_extent_flag": None,
        "last_updated": None,
        "pending_sources": PENDING_INDEX_LAYERS,
    }


def get_available_layers() -> Dict[str, Any]:
    return {
        **SATELLITE_MAP_LAYERS,
        "_pending_index_layers": PENDING_INDEX_LAYERS,
    }
