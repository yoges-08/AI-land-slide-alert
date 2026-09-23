"""Open-Meteo ingestion.

M0 changes, against the two confirmed defects:

  D3  rainfall_24h summed hourly_precip[-24:], which with past_days=6 /
      forecast_days=6 is the LAST 24 FORECAST hours — roughly six days in the
      future. Measured error on a fixture: 500 mm reported for a true 100 mm.
      Now sliced by hourly["time"] against the response's own current time.
      The 5-day forecast started at day +2 and labelled it "Today"; now keyed
      to the real current date.

  D2  get_fallback_weather() returned hardcoded values on any exception.
      Deleted. An unreachable source now returns a DataStatus with no values.

Observed and forecast are separate blocks in the payload so they cannot be
summed together by accident. Open-Meteo is a ground-model cross-check, not a
satellite source, and is labelled as such.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from backend.app.core.config import settings
from backend.app.core.freshness import (
    Provenance, freshness_tier, liveness, no_data, utcnow,
)

logger = logging.getLogger(__name__)

OPEN_METEO_URL = f"{settings.OPEN_METEO_BASE_URL}/forecast"
SOURCE_KEY = "open_meteo"
PRODUCT_ID = "open-meteo/forecast/v1"

WMO_WEATHER_MAP = {
    0: ("Clear sky", "Sun"), 1: ("Mainly clear", "SunMedium"),
    2: ("Partly cloudy", "CloudSun"), 3: ("Overcast", "Cloud"),
    45: ("Foggy", "CloudFog"), 48: ("Depositing rime fog", "CloudFog"),
    51: ("Light drizzle", "CloudDrizzle"), 53: ("Moderate drizzle", "CloudDrizzle"),
    55: ("Dense drizzle", "CloudDrizzle"), 61: ("Slight rain", "CloudRain"),
    63: ("Moderate rain", "CloudRain"), 65: ("Heavy rain", "CloudRainWind"),
    71: ("Slight snow", "CloudSnow"), 73: ("Moderate snow", "CloudSnow"),
    75: ("Heavy snow", "Snowflake"), 80: ("Slight rain showers", "CloudRain"),
    81: ("Moderate rain showers", "CloudRain"), 82: ("Violent rain showers", "CloudRainWind"),
    95: ("Thunderstorm", "CloudLightning"), 96: ("Thunderstorm with hail", "CloudLightning"),
    99: ("Heavy thunderstorm with hail", "CloudLightning"),
}

# Last successful fetch per (lat, lon), so an OFFLINE response can state when we
# last actually had data. In-memory for M0; moves to source_health in M2.
_LAST_SUCCESS: dict[tuple[float, float], str] = {}

# 30-minute in-memory TTL cache: (round(lat, 4), round(lon, 4)) -> (timestamp, parsed_data)
import time
_WEATHER_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
WEATHER_CACHE_TTL_SECONDS: float = 30.0 * 60.0  # 30 minutes

_OPEN_METEO_SEMAPHORE = asyncio.Semaphore(3)
_LAST_REQUEST_TIME: float = 0.0
_MIN_REQUEST_INTERVAL_S: float = 0.4


IST = timezone(timedelta(hours=5, minutes=30))


def _parse_iso(value: str) -> Optional[datetime]:
    """Open-Meteo returns local naive ISO strings under the requested timezone (Asia/Kolkata)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


async def fetch_live_weather(lat: float, lon: float) -> dict[str, Any]:
    """Fetch observed + forecast weather, or return NO DATA. Uses 30-min TTL cache, 11km grid, and rate throttling."""
    global _LAST_REQUEST_TIME
    cache_key = (round(lat, 1), round(lon, 1))
    now_ts = time.time()
    RATE_LIMIT_COOLDOWN_S = 300.0  # 5 minutes

    if cache_key in _WEATHER_CACHE:
        cached_time, cached_val = _WEATHER_CACHE[cache_key]
        if cached_val is not None and (now_ts - cached_time) < WEATHER_CACHE_TTL_SECONDS:
            return cached_val
        if cached_val is None and (now_ts - cached_time) < RATE_LIMIT_COOLDOWN_S:
            logger.debug("Skipping Open-Meteo call — still in 429 cooldown for (%s, %s)", lat, lon)
            return unavailable(lat, lon, "Rate-limited (cooldown active)")

    params = {
        "latitude": lat, "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "precipitation",
                    "rain", "weather_code", "wind_speed_10m"],
        "hourly": ["precipitation", "rain"],
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min",
                    "precipitation_sum", "precipitation_probability_max"],
        "timezone": "Asia/Kolkata",
        "past_days": 6,
        "forecast_days": 6,
    }
    headers = {
        "User-Agent": "LANDSAFE-NER/1.0 (academic-monitoring; contact: yoges0302)"
    }

    last_error = None
    async with _OPEN_METEO_SEMAPHORE:
        elapsed = time.time() - _LAST_REQUEST_TIME
        if elapsed < _MIN_REQUEST_INTERVAL_S:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL_S - elapsed)
        _LAST_REQUEST_TIME = time.time()

        for attempt in range(settings.OPEN_METEO_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.OPEN_METEO_TIMEOUT_S) as client:
                    response = await client.get(OPEN_METEO_URL, params=params, headers=headers)
                if response.status_code == 200:
                    parsed = parse_open_meteo_response(response.json(), lat, lon)
                    _LAST_SUCCESS[cache_key] = parsed["data_status"]["observed_at"] or utcnow().isoformat()
                    _WEATHER_CACHE[cache_key] = (now_ts, parsed)
                    return parsed
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Open-Meteo 429 rate-limit; backing off %ds for key %s", retry_after, cache_key)
                    _WEATHER_CACHE[cache_key] = (time.time(), None)
                    await asyncio.sleep(min(retry_after, 120))
                    last_error = f"HTTP 429 (Rate-limited, retry after {retry_after}s)"
                    break
                last_error = f"HTTP {response.status_code}"
            except Exception as exc:  # noqa: BLE001 - any transport failure is NO DATA
                last_error = f"{type(exc).__name__}: {exc}"
            if attempt < settings.OPEN_METEO_RETRIES:
                await asyncio.sleep(0.5 * (2 ** attempt))

    logger.warning("Open-Meteo unavailable for (%s, %s): %s", lat, lon, last_error)
    return unavailable(lat, lon, last_error or "unknown error")


def unavailable(lat: float, lon: float, reason: str) -> dict[str, Any]:
    """The replacement for get_fallback_weather(). Carries no values."""
    cache_key = (round(lat, 1), round(lon, 1))
    return {
        "data_status": no_data(
            SOURCE_KEY,
            reason=f"Open-Meteo unreachable ({reason})",
            last_success_at=_LAST_SUCCESS.get(cache_key) or _LAST_SUCCESS.get((lat, lon)),
            offline=True,
        ),
        "status": "OFFLINE",
        "source": "Open-Meteo",
        "observed": None,
        "forecast": None,
        # Legacy top-level keys kept so existing consumers do not KeyError.
        # Explicitly null: no observation is available.
        "temperature": None, "humidity": None, "wind_speed": None,
        "rainfall_1h": None, "rainfall_24h": None, "rainfall_7d_cumulative": None,
        "weather_code": None, "condition_text": None, "icon_name": None,
        "rainfall_trend_7d": [], "forecast_5d": [],
        "last_updated": None,
    }


def _observed_window_sum(hourly_times: list[str], values: list, now: datetime,
                         hours: int) -> tuple[Optional[float], int]:
    """Sum the `hours` hours ENDING NOW. Forecast hours are excluded by time.

    This is the D3 fix. Position-based slicing cannot distinguish past from
    future; timestamp comparison can.
    """
    if not hourly_times or not values:
        return None, 0
    window_start = now - timedelta(hours=hours)
    total, count = 0.0, 0
    for ts_str, val in zip(hourly_times, values):
        ts = _parse_iso(ts_str)
        if ts is None or val is None:
            continue
        if window_start < ts <= now:          # strictly past-or-present only
            total += float(val)
            count += 1
    if count == 0:
        return None, 0
    return round(total, 1), count


def parse_open_meteo_response(data: dict, lat: float, lon: float) -> dict[str, Any]:
    current = data.get("current", {}) or {}
    daily = data.get("daily", {}) or {}
    hourly = data.get("hourly", {}) or {}

    now = _parse_iso(current.get("time", "")) or datetime.now()
    received_at = utcnow()

    wmo_code = current.get("weather_code")
    condition_text, icon_name = WMO_WEATHER_MAP.get(wmo_code, (None, None))

    hourly_times = hourly.get("time", []) or []
    hourly_precip = hourly.get("precipitation", []) or []

    # D3 FIX: the 24 hours ending now, not the last 24 array entries.
    rain_24h, hours_counted = _observed_window_sum(hourly_times, hourly_precip, now, 24)

    daily_time = daily.get("time", []) or []
    daily_precip = daily.get("precipitation_sum", []) or []
    daily_codes = daily.get("weather_code", []) or []
    daily_max = daily.get("temperature_2m_max", []) or []
    daily_min = daily.get("temperature_2m_min", []) or []

    today = now.date()
    today_idx = next((i for i, d in enumerate(daily_time)
                      if _parse_iso(d) and _parse_iso(d).date() == today), None)

    # Observed rainfall trend: past days up to and including today.
    rainfall_trend_7d = []
    if today_idx is not None:
        for i in range(max(0, today_idx - 6), today_idx + 1):
            dt = _parse_iso(daily_time[i])
            val = daily_precip[i] if i < len(daily_precip) else None
            rainfall_trend_7d.append({
                "date": dt.strftime("%b %d") if dt else daily_time[i],
                "iso_date": daily_time[i],
                "rainfall_mm": round(float(val), 1) if val is not None else None,
            })

    rain_7d = None
    observed_days = [d["rainfall_mm"] for d in rainfall_trend_7d if d["rainfall_mm"] is not None]
    if observed_days:
        rain_7d = round(sum(observed_days), 1)

    # D3 FIX (second half): the forecast starts at TODAY, not today + 2.
    forecast_5d = []
    if today_idx is not None:
        for i in range(today_idx, min(today_idx + 5, len(daily_time))):
            dt = _parse_iso(daily_time[i])
            offset = i - today_idx
            day_name = "Today" if offset == 0 else ("Tomorrow" if offset == 1
                                                    else (dt.strftime("%a") if dt else f"+{offset}d"))
            code = daily_codes[i] if i < len(daily_codes) else None
            cond, ic = WMO_WEATHER_MAP.get(code, (None, None))
            forecast_5d.append({
                "day": day_name,
                "date": daily_time[i],
                "is_forecast": offset > 0,
                "condition": cond, "icon": ic,
                "temp_max": daily_max[i] if i < len(daily_max) else None,
                "temp_min": daily_min[i] if i < len(daily_min) else None,
                "rainfall_mm": (round(float(daily_precip[i]), 1)
                                if i < len(daily_precip) and daily_precip[i] is not None else None),
            })

    observed_at_utc = _to_utc(now)
    tier = freshness_tier(SOURCE_KEY, observed_at_utc)

    # A partial 24 h window is real but incomplete -> DEGRADED, not silently filled.
    quality = "GOOD" if hours_counted >= 24 else ("DEGRADED" if hours_counted > 0 else "SUSPECT")

    provenance = Provenance(
        source="Open-Meteo",
        dataset_product_id=PRODUCT_ID,
        observed_at=observed_at_utc.isoformat(),
        received_at=received_at.isoformat(),
        processed_at=utcnow().isoformat(),
        spatial_resolution="~11 km (ground model, not satellite)",
        temporal_resolution="hourly",
        licence="Open-Meteo free tier, non-commercial",
        quality_flag=quality,
    )

    return {
        "data_status": {
            "status": tier,
            "source": SOURCE_KEY,
            "liveness": liveness(SOURCE_KEY),
            "observed_at": observed_at_utc.isoformat(),
            "provenance": provenance.__dict__,
        },
        "status": tier,
        "source": "Open-Meteo",
        "source_note": "Ground forecast model, cross-check only. Not a satellite source.",
        "observed": {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "rainfall_1h": current.get("precipitation"),
            "rainfall_24h": rain_24h,
            "rainfall_24h_hours_counted": hours_counted,
            "rainfall_7d_cumulative": rain_7d,
            "weather_code": wmo_code,
            "condition_text": condition_text,
            "observed_at": observed_at_utc.isoformat(),
        },
        "forecast": {
            "issued_at": received_at.isoformat(),
            "days": [f for f in forecast_5d if f["is_forecast"]],
        },
        # Legacy flat keys, observed values only.
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed": current.get("wind_speed_10m"),
        "rainfall_1h": current.get("precipitation"),
        "rainfall_24h": rain_24h,
        "rainfall_7d_cumulative": rain_7d,
        "weather_code": wmo_code,
        "condition_text": condition_text,
        "icon_name": icon_name,
        "rainfall_trend_7d": rainfall_trend_7d,
        "forecast_5d": forecast_5d,
        "last_updated": observed_at_utc.isoformat(),
    }
