import pytest
from datetime import datetime, timedelta
from backend.app.services.weather_service import parse_open_meteo_response, get_no_data_weather

def test_parse_open_meteo_response_24h_rainfall():
    # Build simulated Open-Meteo payload with 312 hourly slots (144 past + 24 today + 144 future)
    hourly_times = []
    hourly_precip = []
    base_time = datetime(2026, 9, 13, 0, 0)
    for i in range(312):
        t = base_time + timedelta(hours=i)
        hourly_times.append(t.strftime("%Y-%m-%dT%H:00"))
        # Set 2.0 mm rain only during the 24 hours of today (indices 144 to 167)
        if 144 <= i <= 167:
            hourly_precip.append(2.0)
        elif i > 167:
            hourly_precip.append(10.0) # Future rain on day +6
        else:
            hourly_precip.append(0.0)

    # Current time is today at hour 23 (index 167)
    curr_time_str = hourly_times[167]

    daily_times = []
    daily_precip = []
    daily_codes = []
    for d in range(13):
        dt = (base_time + timedelta(days=d)).strftime("%Y-%m-%d")
        daily_times.append(dt)
        daily_precip.append(48.0 if d == 6 else 0.0)
        daily_codes.append(61)

    mock_payload = {
        "current": {
            "time": curr_time_str,
            "temperature_2m": 21.5,
            "relative_humidity_2m": 85,
            "wind_speed_10m": 8.0,
            "precipitation": 2.0,
            "weather_code": 61
        },
        "hourly": {
            "time": hourly_times,
            "precipitation": hourly_precip
        },
        "daily": {
            "time": daily_times,
            "precipitation_sum": daily_precip,
            "weather_code": daily_codes,
            "temperature_2m_max": [25] * 13,
            "temperature_2m_min": [18] * 13
        }
    }

    parsed = parse_open_meteo_response(mock_payload, 27.33, 88.61)

    # Verify 24h rainfall sums the past 24h (24 * 2.0 = 48.0 mm), NOT the future day 6 (24 * 10 = 240 mm)
    assert parsed["rainfall_24h"] == 48.0
    assert parsed["status"] == "FRESH"
    assert parsed["is_sample_data"] is False
    assert len(parsed["forecast_5d"]) == 5
    assert parsed["forecast_5d"][0]["day"] == "Today"
    assert len(parsed["rainfall_trend_7d"]) == 7
    assert parsed["rainfall_trend_7d"][-1]["date"] == "Today"

def test_get_no_data_weather():
    fallback = get_no_data_weather(27.33, 88.61, "Test Network Failure")
    assert fallback["status"] == "OFFLINE"
    assert fallback["temperature"] is None
    assert fallback["rainfall_24h"] is None
    assert fallback["rainfall_7d_cumulative"] is None
    assert fallback["is_sample_data"] is False
    assert fallback["quality_flag"] == "UNAVAILABLE"
    assert fallback["last_updated"] is None
