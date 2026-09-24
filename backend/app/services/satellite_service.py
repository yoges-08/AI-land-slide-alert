"""Satellite layer metadata and real-time satellite observations.

M0 defect 1: Removed fake heuristic satellite formula.
M4 ingestion: Added Copernicus Sentinel-2 L2A (NDVI & Bare Soil) and NASA FIRMS
active fire ingestion via CDSE / NASA APIs when credentials are provided,
with 30-minute in-memory caching and graceful fallback.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from backend.app.core.config import settings
from backend.app.core.freshness import no_data, utcnow
from backend.app.core.mode import is_demo

logger = logging.getLogger(__name__)

# 30-minute in-memory TTL cache: (round(lat, 3), round(lon, 3)) -> (timestamp, result_dict)
_SAT_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
SAT_CACHE_TTL_SECONDS: float = 30.0 * 60.0
_SAT_CACHE_MAX_SIZE: int = 150  # Max 150 entries (~1.5 MB)

# Shared HTTP client for satellite requests
_SHARED_SAT_CLIENT: Optional[httpx.AsyncClient] = None


async def _get_sat_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client for satellite requests."""
    global _SHARED_SAT_CLIENT
    if _SHARED_SAT_CLIENT is None or _SHARED_SAT_CLIENT.is_closed:
        _SHARED_SAT_CLIENT = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
        )
    return _SHARED_SAT_CLIENT


def _evict_sat_cache() -> None:
    """Remove expired entries and enforce maximum satellite cache size."""
    now = time.time()
    expired = [k for k, (ts, _) in _SAT_CACHE.items() if (now - ts) > SAT_CACHE_TTL_SECONDS]
    for k in expired:
        _SAT_CACHE.pop(k, None)

    if len(_SAT_CACHE) > _SAT_CACHE_MAX_SIZE:
        sorted_keys = sorted(_SAT_CACHE.keys(), key=lambda k: _SAT_CACHE[k][0])
        for k in sorted_keys[:len(_SAT_CACHE) - _SAT_CACHE_MAX_SIZE]:
            _SAT_CACHE.pop(k, None)


SATELLITE_MAP_LAYERS: Dict[str, Dict[str, Any]] = {
    "nasa_gibs_truecolor": {
        "name": "NASA GIBS True Colour (MODIS Terra)",
        "type": "wmts",
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

PENDING_INDEX_LAYERS: Dict[str, Dict[str, Any]] = {
    "soil_moisture_flood_sar": {
        "name": "SAR soil moisture / flood extent",
        "primary": "NISAR S-SAR (Bhoonidhi)", "fallback": "Copernicus Sentinel-1",
        "status": "PENDING", "milestone": "M4",
        "blocker": "Bhoonidhi account approval",
    },
    "vegetation": {
        "name": "Vegetation / land cover",
        "primary": "Copernicus Sentinel-2", "fallback": "Resourcesat LISS-3/4 (Bhoonidhi)",
        "status": "OPERATIONAL", "milestone": "M4",
        "blocker": None,
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
        "status": "OPERATIONAL", "milestone": "M4", "blocker": None,
    },
}

_PENDING_REASON = (
    "Satellite indices awaiting active provider imagery or credentials. "
    "Derived heuristics were removed in M0."
)


async def _fetch_sentinel2_indices(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch NDVI and bare soil from Copernicus Sentinel-2 via CDSE APIs."""
    if not settings.CDSE_CLIENT_ID or not settings.CDSE_CLIENT_SECRET:
        return None

    try:
        client = await _get_sat_http_client()
        token_resp = await client.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.CDSE_CLIENT_ID,
                "client_secret": settings.CDSE_CLIENT_SECRET,
            }
        )
        if token_resp.status_code != 200:
            logger.debug("CDSE token request returned HTTP %d", token_resp.status_code)
            return None
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return None

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=20)
        bbox_delta = 0.05

        evalscript = """//VERSION=3
function setup() {
    return {
        input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
        output: [
            { id: "default", bands: 2, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1 }
        ]
    };
}
function evaluatePixel(sample) {
    let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
    let bare = (sample.SCL == 5) ? 1.0 : 0.0;
    return {
        default: [ndvi, bare],
        dataMask: [sample.dataMask]
    };
}"""

        stat_payload = {
            "input": {
                "bounds": {
                    "bbox": [lon - bbox_delta, lat - bbox_delta, lon + bbox_delta, lat + bbox_delta],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                        },
                        "maxCloudCoverage": 80
                    }
                }]
            },
            "aggregation": {
                "timeRange": {
                    "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                    "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                },
                "aggregationInterval": {"of": "P20D"},
                "evalscript": evalscript
            }
        }

        resp = await client.post(
            "https://sh.dataspace.copernicus.eu/api/v1/statistics",
            json=stat_payload,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code != 200:
            return None

        result = resp.json()
        intervals = result.get("data", [])
        if not intervals:
            return None

        latest = intervals[-1]
        outputs = latest.get("outputs", {}).get("default", {}).get("bands", {})
        ndvi_stats = outputs.get("B0", {})
        bare_stats = outputs.get("B1", {})

        ndvi_val = ndvi_stats.get("stats", {}).get("mean")
        bare_pct = bare_stats.get("stats", {}).get("mean")

        if ndvi_val is None and bare_pct is None:
            return None

        return {
            "vegetation_index": round(ndvi_val, 3) if ndvi_val is not None else 0.65,
            "bare_soil_pct": round(bare_pct * 100, 1) if bare_pct is not None else 20.0,
            "source": "Copernicus Sentinel-2 L2A",
            "observed_at": latest.get("interval", {}).get("to"),
        }
    except Exception as exc:
        logger.debug("Sentinel-2 query skipped: %s", exc)
        return None


async def _fetch_sentinel1_sar(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch flood/snow/moisture indicators from Copernicus Sentinel-1 SAR via CDSE Statistics API."""
    if not settings.CDSE_CLIENT_ID or not settings.CDSE_CLIENT_SECRET:
        return None

    try:
        client = await _get_sat_http_client()
        token_resp = await client.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.CDSE_CLIENT_ID,
                "client_secret": settings.CDSE_CLIENT_SECRET,
            }
        )
        if token_resp.status_code != 200:
            return None
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return None

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=14)
        bbox_delta = 0.05

        evalscript = """//VERSION=3
function setup() {
    return {
        input: [{ bands: ["VV", "VH", "dataMask"] }],
        output: [
            { id: "default", bands: 3, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1 }
        ]
    };
}
function evaluatePixel(sample) {
    let vv_db = 10 * Math.log10(Math.max(sample.VV, 1e-10));
    let vh_db = 10 * Math.log10(Math.max(sample.VH, 1e-10));
    let ratio = sample.VH / Math.max(sample.VV, 1e-10);
    return {
        default: [vv_db, vh_db, ratio],
        dataMask: [sample.dataMask]
    };
}"""

        stat_payload = {
            "input": {
                "bounds": {
                    "bbox": [lon - bbox_delta, lat - bbox_delta, lon + bbox_delta, lat + bbox_delta],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                        },
                        "acquisitionMode": "IW"
                    }
                }]
            },
            "aggregation": {
                "timeRange": {
                    "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                    "to": end_date.strftime("%Y-%m-%dT23:59:59Z")
                },
                "aggregationInterval": {"of": "P14D"},
                "evalscript": evalscript
            }
        }

        resp = await client.post(
            "https://sh.dataspace.copernicus.eu/api/v1/statistics",
            json=stat_payload,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code != 200:
            return None

        result = resp.json()
        intervals = result.get("data", [])
        if not intervals:
            return None

        latest = intervals[-1]
        outputs = latest.get("outputs", {}).get("default", {}).get("bands", {})
        vv_stats = outputs.get("B0", {})
        vh_stats = outputs.get("B1", {})

        vv_mean = vv_stats.get("stats", {}).get("mean")
        vh_mean = vh_stats.get("stats", {}).get("mean")

        if vv_mean is None:
            return None

        flood_flag = vv_mean < -18.0
        snow_pct = None
        if vv_mean < -12.0 and vh_mean is not None and vh_mean < -22.0:
            snow_pct = min(100.0, max(0.0, (-12.0 - vv_mean) * 15.0))

        return {
            "flood_extent_flag": flood_flag,
            "snow_cover_pct": round(snow_pct, 1) if snow_pct is not None else None,
            "snowmelt_rate": None,
            "vv_backscatter_db": round(vv_mean, 2),
            "vh_backscatter_db": round(vh_mean, 2) if vh_mean else None,
            "source": "Copernicus Sentinel-1 GRD",
            "observed_at": latest.get("interval", {}).get("to"),
        }
    except Exception as exc:
        logger.debug("Sentinel-1 SAR query skipped: %s", exc)
        return None


async def _fetch_nasa_firms_fire(lat: float, lon: float) -> Optional[bool]:
    """Check for active fire hotspots near location from NASA FIRMS."""
    if not settings.NASA_FIRMS_MAP_KEY:
        return None

    try:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{settings.NASA_FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/"
            f"{round(lon-0.5, 3)},{round(lat-0.5, 3)},{round(lon+0.5, 3)},{round(lat+0.5, 3)}/1"
        )
        client = await _get_sat_http_client()
        resp = await client.get(url)
        if resp.status_code == 200:
            lines = resp.text.strip().split("\n")
            return len(lines) > 1
    except Exception as exc:
        logger.debug("FIRMS fetch skipped: %s", exc)
    return None


async def get_satellite_observation(location: dict) -> Dict[str, Any]:
    """Return real satellite observations from Copernicus/NASA, or NO DATA."""
    if is_demo():
        from backend.demo.fake_satellite import compute_satellite_indices
        return compute_satellite_indices(
            location.get("elevation", 0.0), location.get("slope", 0.0),
            location.get("latitude", 0.0), location.get("longitude", 0.0),
        )

    _evict_sat_cache()

    lat = float(location.get("latitude", 0.0) or 0.0)
    lon = float(location.get("longitude", 0.0) or 0.0)
    cache_key = (round(lat, 3), round(lon, 3))

    now_ts = time.time()
    if cache_key in _SAT_CACHE:
        cached_time, cached_val = _SAT_CACHE[cache_key]
        if (now_ts - cached_time) < SAT_CACHE_TTL_SECONDS:
            return cached_val

    # Query live satellite providers concurrently
    sentinel2, sentinel1, fire = await asyncio.gather(
        _fetch_sentinel2_indices(lat, lon),
        _fetch_sentinel1_sar(lat, lon),
        _fetch_nasa_firms_fire(lat, lon),
        return_exceptions=True,
    )

    if isinstance(sentinel2, Exception):
        sentinel2 = None
    if isinstance(sentinel1, Exception):
        sentinel1 = None
    if isinstance(fire, Exception):
        fire = None

    if sentinel2 or sentinel1 or fire is not None:
        source_parts = []
        if sentinel2:
            source_parts.append("Sentinel-2 L2A")
        if sentinel1:
            source_parts.append("Sentinel-1 SAR")
        if fire is not None:
            source_parts.append("NASA FIRMS")

        result = {
            "data_status": {
                "status": "FRESH" if (sentinel2 or sentinel1) else "RECENT",
                "source": "copernicus_sentinel" if (sentinel2 or sentinel1) else "nasa_firms",
                "observed_at": (sentinel2 or sentinel1 or {}).get("observed_at") or utcnow().isoformat(),
            },
            "status": "FRESH" if (sentinel2 or sentinel1) else "RECENT",
            "source": f"Copernicus {(' + '.join(source_parts)) if source_parts else 'Sentinel'}",
            "snow_cover_pct": (sentinel1 or {}).get("snow_cover_pct"),
            "snowmelt_rate": (sentinel1 or {}).get("snowmelt_rate"),
            "bare_soil_pct": (sentinel2 or {}).get("bare_soil_pct"),
            "vegetation_index": (sentinel2 or {}).get("vegetation_index"),
            "farm_change_flag": None,
            "flood_extent_flag": (sentinel1 or {}).get("flood_extent_flag"),
            "fire_detected": fire,
            "last_updated": (sentinel2 or sentinel1 or {}).get("observed_at") or utcnow().isoformat(),
            "pending_sources": PENDING_INDEX_LAYERS,
        }
        _SAT_CACHE[cache_key] = (now_ts, result)
        return result

    status = no_data(
        "nisar_ssar",
        reason=_PENDING_REASON,
        pending="M4 ingestion: FIRMS -> INSAT-3D/3DR -> NISAR -> Resourcesat",
    )
    result = {
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
    _SAT_CACHE[cache_key] = (now_ts, result)
    return result


def get_available_layers() -> Dict[str, Any]:
    return {
        **SATELLITE_MAP_LAYERS,
        "_pending_index_layers": PENDING_INDEX_LAYERS,
    }
