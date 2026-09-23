"""ISRO MOSDAC INSAT-3D/3DR QPE Ingestion Source (Milestone 3 - Priority 1)

Ingests Quantitative Precipitation Estimation (QPE) and Hydro-Estimator / IMSRA
half-hourly satellite precipitation products covering the Indian subcontinent:
Bounds: 6.0°N to 38.0°N, 68.0°E to 98.0°E.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.freshness import utcnow
from backend.app.ingestion.base import (
    BaseSource, IngestionError, SourceFetchError, SourceValidationError,
)

logger = logging.getLogger(__name__)


class MosdacInsat3dSource(BaseSource):
    """ISRO MOSDAC INSAT-3D/3DR QPE Precipitation Ingestor."""

    source_id = "MOSDAC_INSAT3D_QPE"
    name = "INSAT-3D/3DR Quantitative Precipitation Estimation (QPE & IMSRA)"
    provider = "ISRO / SAC / MOSDAC"
    cadence_minutes = 30
    licence = "Open Government Data (OGD) / Research Non-Commercial"
    api_endpoint = os.getenv("MOSDAC_API_ENDPOINT", "https://mosdac.gov.in/catalog/search")
    max_retries = 3
    retry_backoff_base_s = 0.5

    def __init__(self):
        super().__init__()
        self.auth_token = getattr(settings, "MOSDAC_AUTH_TOKEN", "") or os.getenv("MOSDAC_AUTH_TOKEN", "")

    async def fetch(self, **kwargs) -> Dict[str, Any]:
        """Fetch half-hourly QPE raster or grid metadata from MOSDAC API.
        
        Allows passing simulated_payload for offline/simulation testing or
        fetches directly from MOSDAC API using HTTPS with token auth.
        """
        simulated_payload = kwargs.get("simulated_payload")
        if simulated_payload is not None:
            return simulated_payload

        # Guard: skip if no working auth token and no login credentials
        if not self.auth_token and not (os.getenv("MOSDAC_USERNAME") and os.getenv("MOSDAC_PASSWORD")):
            raise SourceFetchError(
                "MOSDAC_AUTH_TOKEN is empty. Skipping fetch. "
                "Login to mosdac.gov.in to obtain a bearer token."
            )

        # Live network fetch
        headers = {
            "Accept": "application/json",
            "User-Agent": "LANDSAFE-NER/1.0 (Disaster-Early-Warning-Research)",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif os.getenv("MOSDAC_USERNAME") and os.getenv("MOSDAC_PASSWORD"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as auth_client:
                    login_resp = await auth_client.post(
                        "https://mosdac.gov.in/api/v1/auth/login",
                        json={
                            "username": os.getenv("MOSDAC_USERNAME"),
                            "password": os.getenv("MOSDAC_PASSWORD"),
                        }
                    )
                    if login_resp.status_code == 200:
                        token = login_resp.json().get("token") or login_resp.json().get("access_token")
                        if token:
                            self.auth_token = token
                            headers["Authorization"] = f"Bearer {token}"
            except Exception as exc:
                logger.debug("MOSDAC auto-login skipped: %s", exc)

        params = kwargs.get("params", {
            "satellite": "3DIMG",
            "sensor": "IMAGER",
            "product": "QPE",
            "level": "L2",
            "format": "json",
            "limit": 1,
            "sort": "-datetime",
        })

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.api_endpoint, headers=headers, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (401, 403):
                    raise SourceFetchError(f"MOSDAC authentication required (HTTP {response.status_code}): Access token pending or expired.")
                else:
                    raise SourceFetchError(f"MOSDAC server returned HTTP {response.status_code}")
        except Exception as exc:
            if isinstance(exc, SourceFetchError):
                raise
            raise SourceFetchError(f"MOSDAC connection failed: {type(exc).__name__} - {str(exc)}") from exc

    def validate(self, raw_data: Any) -> bool:
        """Validate MOSDAC QPE payload structure and coordinate integrity."""
        super().validate(raw_data)
        if not isinstance(raw_data, dict):
            raise SourceValidationError("[MOSDAC_INSAT3D_QPE] Root payload must be a JSON dictionary")

        if "records" not in raw_data and "measurements" not in raw_data and "grid" not in raw_data:
            raise SourceValidationError("[MOSDAC_INSAT3D_QPE] Payload missing precipitation data collections ('records' or 'measurements')")

        obs_time = raw_data.get("observation_time") or raw_data.get("timestamp")
        if not obs_time:
            raise SourceValidationError("[MOSDAC_INSAT3D_QPE] Missing observation timestamp")

        return True

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Transform raw MOSDAC observations into standardized internal format."""
        self.validate(raw_data)
        obs_time_str = raw_data.get("observation_time") or raw_data.get("timestamp")
        try:
            obs_time = datetime.fromisoformat(obs_time_str.replace("Z", "+00:00"))
        except Exception:
            obs_time = utcnow()

        items = raw_data.get("records") or raw_data.get("measurements") or []
        normalized_records = []

        for item in items:
            district_id = item.get("district_id")
            if district_id is None:
                continue

            r_1h = item.get("rainfall_1h_mm") or item.get("rain_rate_mmh") or item.get("qpe_val")
            r_24h = item.get("rainfall_24h_mm") or item.get("rain_24h_sum")

            # Zero-fabrication: Never invent numbers. Ensure float or None.
            r_1h_val = float(r_1h) if r_1h is not None else None
            r_24h_val = float(r_24h) if r_24h is not None else None

            normalized_records.append({
                "district_id": int(district_id),
                "source_id": self.source_id,
                "observation_time": obs_time,
                "rainfall_1h_mm": r_1h_val,
                "rainfall_24h_mm": r_24h_val,
                "rainfall_7d_cumulative_mm": float(item["rainfall_7d_cumulative_mm"]) if item.get("rainfall_7d_cumulative_mm") is not None else None,
                "quality_flag": item.get("quality_flag", "NOMINAL"),
                "is_forecast": False,
            })

        return normalized_records

    def store(self, records: List[Dict[str, Any]], db: Session) -> int:
        """Store normalized records into weather_observations table idempotently."""
        from backend.app.services.weather_reconciliation import WeatherReconciliationService
        return WeatherReconciliationService.store_observations(records, db)
