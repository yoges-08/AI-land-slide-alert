import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

OPEN_METEO_URL = f"{settings.OPEN_METEO_BASE_URL}/forecast"

# Mapping WMO Weather codes to readable descriptions & icons
WMO_WEATHER_MAP = {
    0: ("Clear sky", "Sun"),
    1: ("Mainly clear", "SunMedium"),
    2: ("Partly cloudy", "CloudSun"),
    3: ("Overcast", "Cloud"),
    45: ("Foggy", "CloudFog"),
    48: ("Depositing rime fog", "CloudFog"),
    51: ("Light drizzle", "CloudDrizzle"),
    53: ("Moderate drizzle", "CloudDrizzle"),
    55: ("Dense drizzle", "CloudDrizzle"),
    61: ("Slight rain", "CloudRain"),
    63: ("Moderate rain", "CloudRain"),
    65: ("Heavy rain", "CloudRainWind"),
    71: ("Slight snow", "CloudSnow"),
    73: ("Moderate snow", "CloudSnow"),
    75: ("Heavy snow", "Snowflake"),
    80: ("Slight rain showers", "CloudRain"),
    81: ("Moderate rain showers", "CloudRain"),
    82: ("Violent rain showers", "CloudRainWind"),
    95: ("Thunderstorm", "CloudLightning"),
    96: ("Thunderstorm with hail", "CloudLightning"),
    99: ("Heavy thunderstorm with hail", "CloudLightning"),
}

async def fetch_live_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches live weather & rainfall observations from Open-Meteo API for given lat/lon.
    Uses past_days=6 and forecast_days=6.
    Returns current observation, correct 24h past accumulation, 7-day history, and 5-day forecast.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "rain", "weather_code", "wind_speed_10m"],
        "hourly": ["precipitation", "rain"],
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "precipitation_probability_max"],
        "timezone": "Asia/Kolkata",
        "past_days": 6,
        "forecast_days": 6
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            if response.status_code == 200:
                data = response.json()
                return parse_open_meteo_response(data, lat, lon)
            else:
                logger.warning(f"Open-Meteo API responded with HTTP {response.status_code} for ({lat}, {lon})")
                return get_no_data_weather(lat, lon, f"HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"Open-Meteo API fetch failed or timed out for ({lat}, {lon}): {e}")
        return get_no_data_weather(lat, lon, str(e))

def parse_open_meteo_response(data: dict, lat: float, lon: float) -> Dict[str, Any]:
    current = data.get("current", {})
    daily = data.get("daily", {})
    hourly = data.get("hourly", {})

    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    wind_speed = current.get("wind_speed_10m")
    rainfall_1h = current.get("precipitation", 0.0)
    wmo_code = current.get("weather_code", 0)
    condition_text, icon_name = WMO_WEATHER_MAP.get(wmo_code, ("Variable", "Cloud"))

    # Correct 24h rainfall calculation:
    # Hourly data has past_days=6 (144 hrs) + today (24 hrs) + forecast_days=6 (144 hrs) = 312 hrs
    hourly_time = hourly.get("time", [])
    hourly_precip = hourly.get("precipitation", [])
    current_time_str = current.get("time", "")

    # Locate the hour corresponding to current time or fallback to end of past_days window
    curr_idx = -1
    if current_time_str and current_time_str in hourly_time:
        curr_idx = hourly_time.index(current_time_str)
    elif len(hourly_precip) >= 168:
        # Default to end of past 6 days + current day's first few hours
        curr_idx = 144

    if curr_idx >= 0 and len(hourly_precip) > 0:
        start_24h_idx = max(0, curr_idx - 23)
        past_24h_slice = [p for p in hourly_precip[start_24h_idx : curr_idx + 1] if p is not None]
        rain_24h = sum(past_24h_slice)
    else:
        rain_24h = rainfall_1h

    # 7-day rainfall trend data for chart (Past 6 days + Today = 7 days)
    daily_time = daily.get("time", [])
    daily_precip = daily.get("precipitation_sum", [])
    daily_codes = daily.get("weather_code", [])
    daily_max = daily.get("temperature_2m_max", [])
    daily_min = daily.get("temperature_2m_min", [])

    # Today is at index 6 when past_days=6
    today_idx = 6 if len(daily_time) > 6 else max(0, len(daily_time) - 1)

    rainfall_trend_7d = []
    trend_start = max(0, today_idx - 6)
    for i in range(trend_start, min(today_idx + 1, len(daily_time))):
        dt_str = daily_time[i]
        val = daily_precip[i] if i < len(daily_precip) and daily_precip[i] is not None else 0.0
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            label = "Today" if i == today_idx else dt.strftime("%b %d")
        except Exception:
            label = dt_str
        rainfall_trend_7d.append({"date": label, "rainfall_mm": round(val, 1)})

    # Next 5-Day Forecast (starts at Today / index today_idx, up to 5 days)
    forecast_5d = []
    for i in range(today_idx, min(today_idx + 5, len(daily_time))):
        dt_str = daily_time[i]
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            day_name = "Today" if i == today_idx else dt.strftime("%a")
        except Exception:
            day_name = f"Day {i - today_idx}"

        code = daily_codes[i] if i < len(daily_codes) and daily_codes[i] is not None else 1
        cond, ic = WMO_WEATHER_MAP.get(code, ("Partly Cloudy", "CloudSun"))
        t_max = round(daily_max[i]) if i < len(daily_max) and daily_max[i] is not None else None
        t_min = round(daily_min[i]) if i < len(daily_min) and daily_min[i] is not None else None
        p_sum = round(daily_precip[i], 1) if i < len(daily_precip) and daily_precip[i] is not None else 0.0

        forecast_5d.append({
            "day": day_name,
            "date": dt_str,
            "condition": cond,
            "icon": ic,
            "temp_max": t_max,
            "temp_min": t_min,
            "rainfall_mm": p_sum
        })

    cumulative_7d = sum(d["rainfall_mm"] for d in rainfall_trend_7d if d["rainfall_mm"] is not None)

    return {
        "status": "FRESH",
        "temperature": round(temp, 1) if temp is not None else None,
        "humidity": round(humidity) if humidity is not None else None,
        "wind_speed": round(wind_speed, 1) if wind_speed is not None else None,
        "rainfall_1h": round(rainfall_1h, 1) if rainfall_1h is not None else 0.0,
        "rainfall_24h": round(rain_24h, 1) if rain_24h is not None else 0.0,
        "rainfall_7d_cumulative": round(cumulative_7d, 1),
        "weather_code": wmo_code,
        "condition_text": condition_text,
        "icon_name": icon_name,
        "rainfall_trend_7d": rainfall_trend_7d,
        "forecast_5d": forecast_5d,
        "source": "Open-Meteo (Non-Commercial / Free Tier)",
        "is_sample_data": False,
        "quality_flag": "NOMINAL",
        "last_updated": current.get("time", datetime.utcnow().isoformat())
    }

def get_no_data_weather(lat: float, lon: float, error_msg: str = "Service Offline") -> Dict[str, Any]:
    """
    Returns structured NO DATA payload when live weather source is unreachable.
    Never fabricates or substitutes numerical observations.
    """
    return {
        "status": "OFFLINE",
        "error": error_msg,
        "temperature": None,
        "humidity": None,
        "wind_speed": None,
        "rainfall_1h": None,
        "rainfall_24h": None,
        "rainfall_7d_cumulative": None,
        "weather_code": None,
        "condition_text": "NO DATA / OFFLINE",
        "icon_name": "CloudOff",
        "rainfall_trend_7d": [],
        "forecast_5d": [],
        "source": "Open-Meteo",
        "is_sample_data": False,
        "quality_flag": "UNAVAILABLE",
        "last_updated": None
    }

def get_fallback_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Backward-compatible alias for get_no_data_weather.
    """
    return get_no_data_weather(lat, lon, "Fallback triggered - no cached observation available")
