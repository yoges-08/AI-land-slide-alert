import logging
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

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

async def fetch_live_weather(lat: float, lon: float):
    """
    Fetches live weather & rainfall data from Open-Meteo API for given lat/lon.
    Returns current weather, 24h accumulation, 7-day rainfall history, and 5-day forecast.
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
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            if response.status_code == 200:
                data = response.json()
                return parse_open_meteo_response(data, lat, lon)
    except Exception as e:
        logger.warning(f"Open-Meteo API fetch failed or timed out for ({lat}, {lon}): {e}. Using resilient fallback.")

    return get_fallback_weather(lat, lon)

def parse_open_meteo_response(data: dict, lat: float, lon: float):
    current = data.get("current", {})
    daily = data.get("daily", {})
    hourly = data.get("hourly", {})

    temp = current.get("temperature_2m", 22.0)
    humidity = current.get("relative_humidity_2m", 78)
    wind_speed = current.get("wind_speed_10m", 10.5)
    rainfall_1h = current.get("precipitation", 0.0)
    wmo_code = current.get("weather_code", 1)
    condition_text, icon_name = WMO_WEATHER_MAP.get(wmo_code, ("Variable", "Cloud"))

    # Calculate 24h rainfall (sum of last 24 hourly readings)
    hourly_precip = hourly.get("precipitation", [])
    rain_24h = sum(hourly_precip[-24:]) if len(hourly_precip) >= 24 else sum(hourly_precip)
    
    # 7-day rainfall trend data for chart
    daily_time = daily.get("time", [])
    daily_precip = daily.get("precipitation_sum", [])
    daily_codes = daily.get("weather_code", [])
    daily_max = daily.get("temperature_2m_max", [])
    daily_min = daily.get("temperature_2m_min", [])

    rainfall_trend_7d = []
    # Take past 7 days up to today
    for i in range(min(7, len(daily_time))):
        dt_str = daily_time[i]
        val = daily_precip[i] if i < len(daily_precip) and daily_precip[i] is not None else 0.0
        # Format date as 'Apr 21' or 'Sep 17'
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            label = dt.strftime("%b %d")
        except Exception:
            label = dt_str
        rainfall_trend_7d.append({"date": label, "rainfall_mm": round(val, 1)})

    # Next 5-Day Forecast
    forecast_5d = []
    start_idx = max(0, len(daily_time) - 5)
    for i in range(start_idx, len(daily_time)):
        dt_str = daily_time[i]
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            day_name = "Today" if i == start_idx else dt.strftime("%a")
        except Exception:
            day_name = f"Day {i}"

        code = daily_codes[i] if i < len(daily_codes) else 1
        cond, ic = WMO_WEATHER_MAP.get(code, ("Partly Cloudy", "CloudSun"))
        t_max = round(daily_max[i]) if i < len(daily_max) and daily_max[i] is not None else 25
        t_min = round(daily_min[i]) if i < len(daily_min) and daily_min[i] is not None else 18
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

    return {
        "temperature": round(temp, 1),
        "humidity": round(humidity),
        "wind_speed": round(wind_speed, 1),
        "rainfall_1h": round(rainfall_1h, 1),
        "rainfall_24h": round(rain_24h, 1),
        "rainfall_7d_cumulative": round(sum(d["rainfall_mm"] for d in rainfall_trend_7d), 1),
        "weather_code": wmo_code,
        "condition_text": condition_text,
        "icon_name": icon_name,
        "rainfall_trend_7d": rainfall_trend_7d,
        "forecast_5d": forecast_5d,
        "source": "Open-Meteo",
        "is_sample_data": False,
        "last_updated": datetime.utcnow().isoformat()
    }

def get_fallback_weather(lat: float, lon: float):
    """
    Returns realistic baseline weather for Northeast India if live Open-Meteo API is unreachable.
    """
    now = datetime.utcnow()
    days = [(now - timedelta(days=6 - i)).strftime("%b %d") for i in range(7)]
    # Default realistic values inspired by Gangtok/Sikkim monsoon conditions
    trend = [
        {"date": days[0], "rainfall_mm": 15.2},
        {"date": days[1], "rainfall_mm": 45.0},
        {"date": days[2], "rainfall_mm": 92.4},
        {"date": days[3], "rainfall_mm": 56.0},
        {"date": days[4], "rainfall_mm": 78.5},
        {"date": days[5], "rainfall_mm": 110.2},
        {"date": days[6], "rainfall_mm": 142.0},
    ]

    forecast = [
        {"day": "Today", "date": now.strftime("%Y-%m-%d"), "condition": "Light Rain", "icon": "CloudRain", "temp_max": 24, "temp_min": 18, "rainfall_mm": 42.0},
        {"day": "Tomorrow", "date": (now + timedelta(days=1)).strftime("%Y-%m-%d"), "condition": "Light Rain", "icon": "CloudRain", "temp_max": 26, "temp_min": 19, "rainfall_mm": 35.0},
        {"day": "Wed", "date": (now + timedelta(days=2)).strftime("%Y-%m-%d"), "condition": "Cloudy", "icon": "Cloud", "temp_max": 27, "temp_min": 20, "rainfall_mm": 12.0},
        {"day": "Thu", "date": (now + timedelta(days=3)).strftime("%Y-%m-%d"), "condition": "Mostly Cloudy", "icon": "CloudSun", "temp_max": 28, "temp_min": 21, "rainfall_mm": 8.0},
        {"day": "Fri", "date": (now + timedelta(days=4)).strftime("%Y-%m-%d"), "condition": "Partly Cloudy", "icon": "SunMedium", "temp_max": 29, "temp_min": 22, "rainfall_mm": 4.0},
    ]

    return {
        "temperature": 24.0,
        "humidity": 92,
        "wind_speed": 12.0,
        "rainfall_1h": 8.4,
        "rainfall_24h": 142.0,
        "rainfall_7d_cumulative": 539.3,
        "weather_code": 61,
        "condition_text": "Light Rain",
        "icon_name": "CloudRain",
        "rainfall_trend_7d": trend,
        "forecast_5d": forecast,
        "source": "Open-Meteo (Sample/Offline)",
        "is_sample_data": True,
        "last_updated": now.isoformat()
    }
