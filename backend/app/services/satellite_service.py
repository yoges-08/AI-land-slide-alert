import logging
from typing import Dict, Any, Optional
from datetime import datetime
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Map tile layer specifications for frontend GIS integration
SATELLITE_MAP_LAYERS = {
    "nasa_gibs_truecolor": {
        "name": "NASA GIBS Satellite (MODIS / VIIRS)",
        "type": "tile",
        "url": f"{settings.NASA_GIBS_WMTS_URL}/MODIS_Terra_CorrectedReflectance_TrueColor/default/{{time}}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg",
        "attribution": "Imagery provided by NASA Global Imagery Browse Services (GIBS), part of EOSDIS",
        "source": "NASA",
        "format": "jpg",
        "max_zoom": 9
    },
    "esri_world_imagery": {
        "name": "High-Res Satellite (ESRI)",
        "type": "tile",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        "source": "ESRI / Commercial High-Res",
        "format": "png",
        "max_zoom": 18
    },
    "isro_bhuvan_wms": {
        "name": "ISRO Bhuvan LULC & Geomorphology (Advisory Toggle)",
        "type": "wms",
        "url": "https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms",
        "layers": "india3",
        "attribution": "ISRO / NRSC Bhuvan Thematic Services",
        "source": "ISRO",
        "format": "image/png"
    },
    "snow_cover_ndsi": {
        "name": "Snow Cover & Snowmelt (NASA MODIS / Sentinel-2 NDSI)",
        "type": "overlay",
        "description": "Normalized Difference Snow Index (Green - SWIR) / (Green + SWIR) monitoring snowpack depletion and meltwater runoff.",
        "source": "NASA MODIS MOD10A1 / Sentinel-2",
        "badge_color": "cyan"
    },
    "bare_soil_bsi": {
        "name": "Bare Soil & Erosion Exposure (Sentinel-2 BSI)",
        "type": "overlay",
        "description": "Bare Soil Index ((SWIR + Red) - (NIR + Blue)) / ((SWIR + Red) + (NIR + Blue)) detecting exposed friable soil and scars.",
        "source": "Copernicus Sentinel-2",
        "badge_color": "amber"
    },
    "vegetation_ndvi": {
        "name": "Vegetation & Slope Agriculture (Sentinel-2 NDVI)",
        "type": "overlay",
        "description": "Normalized Difference Vegetation Index tracking canopy health and slope cultivation clearing.",
        "source": "Copernicus Sentinel-2",
        "badge_color": "emerald"
    },
    "flood_sar": {
        "name": "SAR Flood Inundation (Sentinel-1 SAR)",
        "type": "overlay",
        "description": "C-band Synthetic Aperture Radar backscatter contrast highlighting standing surface water through cloud cover.",
        "source": "Copernicus Sentinel-1 SAR",
        "badge_color": "blue"
    }
}

def compute_satellite_indices(elevation: float, slope: float, lat: float, lon: float, is_monsoon: bool = True) -> Dict[str, Any]:
    """
    Returns satellite observation metadata.
    If LANDSAFE_MODE=demo, routes to quarantined synthetic simulator.
    In production mode, returns structured status indicating scene status without inventing band math.
    """
    if settings.LANDSAFE_MODE.lower() == "demo":
        from backend.app.services.demo_service import compute_synthetic_satellite_indices
        return compute_synthetic_satellite_indices(elevation, slope, lat, lon, is_monsoon)

    # Production path: Real observation retrieval or NO DATA status
    return {
        "status": "PENDING_INGESTION",
        "snow_cover_pct": None,
        "snowmelt_rate": None,
        "bare_soil_pct": None,
        "vegetation_index": None,
        "farm_change_flag": False,
        "flood_extent_flag": False,
        "source": "Copernicus / NASA (Real Data Pipeline Active)",
        "is_sample_data": False,
        "quality_flag": "AWAITING_INGESTION_M4",
        "last_updated": None,
        "disclaimer": "Real satellite observations ingested during scheduled satellite pass windows."
    }

def get_available_layers() -> Dict[str, Any]:
    return SATELLITE_MAP_LAYERS
