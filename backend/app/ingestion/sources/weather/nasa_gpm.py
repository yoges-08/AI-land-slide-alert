"""NASA GPM IMERG Ingestion Source (Milestone 3 - Priority 2)

Ingests NASA Global Precipitation Measurement (GPM) Integrated Multi-satellitE
Retrievals for GPM (IMERG) half-hourly Early and Late precipitation estimates
on a 0.1° x 0.1° (~10 km) grid.
"""
import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.freshness import utcnow
from backend.app.ingestion.base import (
    BaseSource, IngestionError, SourceFetchError, SourceValidationError,
)

logger = logging.getLogger(__name__)


class NasaGpmSource(BaseSource):
    """NASA GPM IMERG Half-Hourly Precipitation Ingestor."""

    source_id = "NASA_GPM_IMERG"
    name = "NASA Global Precipitation Measurement (GPM IMERG Early/Late Run)"
    provider = "NASA Earthdata / GSFC"
    cadence_minutes = 30
    licence = "NASA Open Data Policy (Free / Unrestricted)"
    api_endpoint = os.getenv("NASA_GPM_API_ENDPOINT", "https://cmr.earthdata.nasa.gov/search/granules.json")
    max_retries = 3
    retry_backoff_base_s = 0.5

    def __init__(self):
        super().__init__()
        self.earthdata_token = getattr(settings, "EARTHDATA_TOKEN", "") or os.getenv("EARTHDATA_TOKEN", "")

    async def fetch(self, **kwargs) -> Dict[str, Any]:
        """Fetch half-hourly IMERG data from NASA Earthdata / GES DISC CMR API."""
        simulated_payload = kwargs.get("simulated_payload")
        if simulated_payload is not None:
            return simulated_payload

        # Guard: skip if no Earthdata token and no username/password configured
        if not self.earthdata_token and not (os.getenv("EARTHDATA_USERNAME") and os.getenv("EARTHDATA_PASSWORD")):
            raise SourceFetchError(
                "EARTHDATA_TOKEN is empty. Skipping NASA GPM fetch to conserve memory. "
                "Configure EARTHDATA_TOKEN in environment to enable."
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": "LANDSAFE-NER/1.0 (Academic-Disaster-Watch)",
        }
        if self.earthdata_token:
            headers["Authorization"] = f"Bearer {self.earthdata_token}"
        elif os.getenv("EARTHDATA_USERNAME") and os.getenv("EARTHDATA_PASSWORD"):
            username = os.getenv("EARTHDATA_USERNAME", "")
            password = os.getenv("EARTHDATA_PASSWORD", "")
            creds = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"

        params = kwargs.get("params", {
            "collection_concept_id": "C2723754864-GES_DISC",
            "temporal": f"{(datetime.now(timezone.utc) - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%SZ')},",
            "bounding_box": "68,6,98,38",
            "sort_key": "-start_date",
            "page_size": 1,
        })

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.api_endpoint, headers=headers, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (401, 403):
                    raise SourceFetchError(f"NASA Earthdata authentication error (HTTP {response.status_code})")
                else:
                    raise SourceFetchError(f"NASA GPM server returned HTTP {response.status_code}")
        except Exception as exc:
            if isinstance(exc, SourceFetchError):
                raise
            raise SourceFetchError(f"NASA GPM connection failed: {type(exc).__name__} - {str(exc)}") from exc

    def validate(self, raw_data: Any) -> bool:
        """Validate NASA GPM payload structure and values."""
        super().validate(raw_data)
        if not isinstance(raw_data, dict):
            raise SourceValidationError("[NASA_GPM_IMERG] Root payload must be a JSON dictionary")

        if "granules" not in raw_data and "measurements" not in raw_data and "records" not in raw_data:
            raise SourceValidationError("[NASA_GPM_IMERG] Payload missing precipitation data items")

        obs_time = raw_data.get("observation_time") or raw_data.get("timestamp")
        if not obs_time:
            raise SourceValidationError("[NASA_GPM_IMERG] Missing observation timestamp")

        return True

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Transform raw NASA GPM observations into standardized internal format."""
        self.validate(raw_data)
        obs_time_str = raw_data.get("observation_time") or raw_data.get("timestamp")
        try:
            obs_time = datetime.fromisoformat(obs_time_str.replace("Z", "+00:00"))
        except Exception:
            obs_time = utcnow()

        items = raw_data.get("granules") or raw_data.get("measurements") or raw_data.get("records") or []
        normalized_records = []

        for item in items:
            district_id = item.get("district_id")
            if district_id is None:
                continue

            precip_cal = item.get("precipitation_cal") or item.get("precipitation_1h_mm") or item.get("rainfall_1h_mm")
            precip_24h = item.get("precipitation_24h_mm") or item.get("rainfall_24h_mm")
            quality_idx = item.get("quality_index", 1.0)

            r_1h_val = float(precip_cal) if precip_cal is not None else None
            r_24h_val = float(precip_24h) if precip_24h is not None else None

            # Quality flag based on GPM quality index
            quality_flag = "NOMINAL"
            if quality_idx is not None and float(quality_idx) < 0.5:
                quality_flag = "DEGRADED"

            normalized_records.append({
                "district_id": int(district_id),
                "source_id": self.source_id,
                "observation_time": obs_time,
                "rainfall_1h_mm": r_1h_val,
                "rainfall_24h_mm": r_24h_val,
                "rainfall_7d_cumulative_mm": float(item["rainfall_7d_cumulative_mm"]) if item.get("rainfall_7d_cumulative_mm") is not None else None,
                "quality_flag": quality_flag,
                "is_forecast": False,
            })

        return normalized_records

    def store(self, records: List[Dict[str, Any]], db: Session) -> int:
        """Store normalized records into weather_observations table idempotently."""
        from backend.app.services.weather_reconciliation import WeatherReconciliationService
        return WeatherReconciliationService.store_observations(records, db)
