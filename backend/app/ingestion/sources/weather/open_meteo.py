"""Open-Meteo Ingestion Source (Milestone 3 - Priority 3)

Ground numerical forecast model cross-check providing observed and forecast
meteorological parameters (temperature, relative humidity, wind speed, precipitation).
Adheres strictly to the <10,000 requests/day non-commercial rate limit budget.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.freshness import utcnow
from backend.app.ingestion.base import (
    BaseSource, IngestionError, RateLimitExceededError, SourceFetchError, SourceValidationError,
)
from backend.app.services.weather_service import (
    OPEN_METEO_URL, parse_open_meteo_response, _parse_iso,
)

logger = logging.getLogger(__name__)


class OpenMeteoSource(BaseSource):
    """Open-Meteo Ground Model Ingestor with token-bucket rate limiter."""

    source_id = "OPEN_METEO"
    name = "Open-Meteo Weather API (Ground-Model Cross-Check)"
    provider = "Open-Meteo"
    cadence_minutes = 60
    licence = "Non-Commercial / Free Tier (<10k calls/day)"
    api_endpoint = f"{settings.OPEN_METEO_BASE_URL}/forecast"
    max_retries = 2
    retry_backoff_base_s = 0.5

    async def fetch(self, **kwargs) -> Dict[str, Any]:
        """Fetch weather for coordinates with rate limiting."""
        simulated_payload = kwargs.get("simulated_payload")
        if simulated_payload is not None:
            return simulated_payload

        lat = kwargs.get("latitude")
        lon = kwargs.get("longitude")
        district_id = kwargs.get("district_id", 1)

        if lat is None or lon is None:
            # Default to primary Tier-1 benchmark (Gangtok) for automated scheduled cycles
            lat = 27.3389
            lon = 88.6065
            district_id = 1

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation",
                        "rain", "weather_code", "wind_speed_10m"],
            "hourly": ["precipitation", "rain"],
            "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min",
                      "precipitation_sum", "precipitation_probability_max"],
            "timezone": "Asia/Kolkata",
            "past_days": 6,
            "forecast_days": 6,
        }

        # Check if already in live weather cache to conserve quota and avoid 429
        from backend.app.services.weather_service import fetch_live_weather
        live = await fetch_live_weather(lat, lon)
        if live.get("status") == "LIVE":
            return {
                "latitude": lat,
                "longitude": lon,
                "current": {
                    "temperature_2m": live.get("temperature"),
                    "relative_humidity_2m": live.get("humidity"),
                    "precipitation": live.get("rainfall_1h"),
                    "wind_speed_10m": live.get("wind_speed"),
                },
                "hourly": {
                    "precipitation": [live.get("rainfall_1h", 0.0)],
                },
                "_meta": {"district_id": district_id, "lat": lat, "lon": lon},
            }

        try:
            async with httpx.AsyncClient(timeout=settings.OPEN_METEO_TIMEOUT_S) as client:
                response = await client.get(self.api_endpoint, params=params)
                if response.status_code == 200:
                    data = response.json()
                    data["_meta"] = {"district_id": district_id, "lat": lat, "lon": lon}
                    return data
                elif response.status_code == 429:
                    raise RateLimitExceededError("Open-Meteo daily request quota or burst rate limit exceeded (429)")
                else:
                    raise SourceFetchError(f"Open-Meteo returned HTTP {response.status_code}")
        except Exception as exc:
            if isinstance(exc, IngestionError):
                raise
            raise SourceFetchError(f"Open-Meteo request failed: {type(exc).__name__} - {str(exc)}") from exc

    def validate(self, raw_data: Any) -> bool:
        """Validate Open-Meteo payload structure."""
        super().validate(raw_data)
        if not isinstance(raw_data, dict):
            raise SourceValidationError("[OPEN_METEO] Payload must be a dictionary")
        if "current" not in raw_data and "hourly" not in raw_data and "measurements" not in raw_data:
            raise SourceValidationError("[OPEN_METEO] Missing 'current' or 'hourly' weather blocks")
        return True

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Normalize Open-Meteo payload into weather observations and forecasts."""
        self.validate(raw_data)

        # If payload was already prepared as a batch list of measurements
        if "measurements" in raw_data:
            obs_time_str = raw_data.get("observation_time", utcnow().isoformat())
            obs_time = datetime.fromisoformat(obs_time_str.replace("Z", "+00:00")) if isinstance(obs_time_str, str) else obs_time_str
            records = []
            for item in raw_data["measurements"]:
                records.append({
                    "district_id": int(item["district_id"]),
                    "source_id": self.source_id,
                    "observation_time": obs_time,
                    "temperature_c": item.get("temperature_c"),
                    "relative_humidity_pct": item.get("relative_humidity_pct"),
                    "wind_speed_kmh": item.get("wind_speed_kmh"),
                    "rainfall_1h_mm": float(item["rainfall_1h_mm"]) if item.get("rainfall_1h_mm") is not None else None,
                    "rainfall_24h_mm": float(item["rainfall_24h_mm"]) if item.get("rainfall_24h_mm") is not None else None,
                    "rainfall_7d_cumulative_mm": float(item["rainfall_7d_cumulative_mm"]) if item.get("rainfall_7d_cumulative_mm") is not None else None,
                    "quality_flag": item.get("quality_flag", "NOMINAL"),
                    "is_forecast": False,
                })
            return records

        meta = raw_data.get("_meta", {})
        district_id = meta.get("district_id", 1)
        lat = meta.get("lat", raw_data.get("latitude", 0.0))
        lon = meta.get("lon", raw_data.get("longitude", 0.0))

        parsed = parse_open_meteo_response(raw_data, lat, lon)
        obs = parsed.get("observed") or {}
        forecast_block = parsed.get("forecast") or {}

        records = []
        if obs:
            obs_time_str = obs.get("observed_at")
            obs_time = datetime.fromisoformat(obs_time_str) if obs_time_str else utcnow()
            records.append({
                "district_id": int(district_id),
                "source_id": self.source_id,
                "observation_time": obs_time,
                "temperature_c": obs.get("temperature"),
                "relative_humidity_pct": obs.get("humidity"),
                "wind_speed_kmh": obs.get("wind_speed"),
                "rainfall_1h_mm": float(obs["rainfall_1h"]) if obs.get("rainfall_1h") is not None else None,
                "rainfall_24h_mm": float(obs["rainfall_24h"]) if obs.get("rainfall_24h") is not None else None,
                "rainfall_7d_cumulative_mm": float(obs["rainfall_7d_cumulative"]) if obs.get("rainfall_7d_cumulative") is not None else None,
                "quality_flag": parsed.get("data_status", {}).get("provenance", {}).get("quality_flag", "NOMINAL"),
                "is_forecast": False,
            })

        # Process future forecast days
        forecast_days = forecast_block.get("days", [])
        for fday in forecast_days:
            fdate_str = fday.get("date")
            if not fdate_str:
                continue
            ftime = datetime.fromisoformat(fdate_str).replace(tzinfo=timezone.utc)
            records.append({
                "district_id": int(district_id),
                "source_id": self.source_id,
                "observation_time": ftime,
                "temperature_c": fday.get("temp_max"),
                "relative_humidity_pct": None,
                "wind_speed_kmh": None,
                "rainfall_1h_mm": None,
                "rainfall_24h_mm": float(fday["rainfall_mm"]) if fday.get("rainfall_mm") is not None else None,
                "rainfall_7d_cumulative_mm": None,
                "quality_flag": "ESTIMATED",
                "is_forecast": True,
            })

        return records

    def store(self, records: List[Dict[str, Any]], db: Session) -> int:
        """Store normalized records into weather_observations table idempotently."""
        from backend.app.services.weather_reconciliation import WeatherReconciliationService
        return WeatherReconciliationService.store_observations(records, db)
