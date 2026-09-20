"""D2 and D3 regression tests.

The fixture is the same one that exposed the baseline bug: 100 mm fell in the
24 hours ending now, and 500 mm is forecast for the final day of the horizon.
Baseline reported 500. Anything other than 100 here is a regression.
"""
from datetime import datetime, timedelta

import pytest

from backend.app.services import weather_service as ws


NOW = datetime(2026, 9, 19, 12, 0)          # Asia/Kolkata local, as Open-Meteo returns
PAST_DAYS, FORECAST_DAYS = 6, 6


def build_response(observed_24h_mm=100.0, final_forecast_day_mm=500.0):
    """Mirror a real past_days=6 / forecast_days=6 payload."""
    start = (NOW - timedelta(days=PAST_DAYS)).replace(hour=0, minute=0)
    total_hours = (PAST_DAYS + FORECAST_DAYS + 1) * 24
    times, precip = [], []
    for i in range(total_hours):
        ts = start + timedelta(hours=i)
        times.append(ts.strftime("%Y-%m-%dT%H:%M"))
        if NOW - timedelta(hours=24) < ts <= NOW:
            precip.append(observed_24h_mm / 24)          # the real observation
        elif ts > NOW + timedelta(days=5):
            precip.append(final_forecast_day_mm / 24)     # the trap
        else:
            precip.append(0.0)

    daily_dates = [(start + timedelta(days=d)).strftime("%Y-%m-%d")
                   for d in range(PAST_DAYS + FORECAST_DAYS + 1)]
    n = len(daily_dates)
    return {
        "current": {
            "time": NOW.strftime("%Y-%m-%dT%H:%M"),
            "temperature_2m": 21.4, "relative_humidity_2m": 90,
            "precipitation": 2.0, "weather_code": 61, "wind_speed_10m": 9.2,
        },
        "hourly": {"time": times, "precipitation": precip, "rain": precip},
        "daily": {
            "time": daily_dates,
            "precipitation_sum": [10.0] * n,
            "weather_code": [61] * n,
            "temperature_2m_max": [25.0] * n,
            "temperature_2m_min": [18.0] * n,
        },
    }


def test_rainfall_24h_uses_the_window_ending_now_not_the_forecast_tail():
    """D3: baseline returned 500.0 here. The true observed total is 100.0."""
    parsed = ws.parse_open_meteo_response(build_response(), 27.0, 88.0)
    assert parsed["observed"]["rainfall_24h"] == pytest.approx(100.0, abs=0.5)
    assert parsed["observed"]["rainfall_24h"] != pytest.approx(500.0, abs=1.0)
    assert parsed["observed"]["rainfall_24h_hours_counted"] == 24


def test_rainfall_24h_ignores_future_hours_entirely():
    """Changing only the forecast must not change the observed total."""
    a = ws.parse_open_meteo_response(build_response(final_forecast_day_mm=0.0), 27.0, 88.0)
    b = ws.parse_open_meteo_response(build_response(final_forecast_day_mm=900.0), 27.0, 88.0)
    assert a["observed"]["rainfall_24h"] == b["observed"]["rainfall_24h"]


def test_forecast_starts_today_not_day_plus_two():
    """D3 second half: baseline labelled 2026-09-21 as 'Today'."""
    parsed = ws.parse_open_meteo_response(build_response(), 27.0, 88.0)
    first = parsed["forecast_5d"][0]
    assert first["day"] == "Today"
    assert first["date"] == NOW.strftime("%Y-%m-%d")
    assert first["is_forecast"] is False


def test_forecast_block_contains_only_future_days():
    parsed = ws.parse_open_meteo_response(build_response(), 27.0, 88.0)
    assert all(d["is_forecast"] for d in parsed["forecast"]["days"])
    assert all(d["date"] > NOW.strftime("%Y-%m-%d") for d in parsed["forecast"]["days"])


def test_observed_trend_ends_today():
    parsed = ws.parse_open_meteo_response(build_response(), 27.0, 88.0)
    assert parsed["rainfall_trend_7d"][-1]["iso_date"] == NOW.strftime("%Y-%m-%d")
    assert len(parsed["rainfall_trend_7d"]) == 7


def test_partial_window_is_flagged_degraded_not_filled():
    """A short history must degrade the quality flag, never fabricate hours."""
    data = build_response()
    keep = 6
    idx = [i for i, t in enumerate(data["hourly"]["time"])
           if datetime.fromisoformat(t) <= NOW][-keep:]
    data["hourly"]["time"] = [data["hourly"]["time"][i] for i in idx]
    data["hourly"]["precipitation"] = [data["hourly"]["precipitation"][i] for i in idx]
    parsed = ws.parse_open_meteo_response(data, 27.0, 88.0)
    assert parsed["observed"]["rainfall_24h_hours_counted"] == keep
    assert parsed["data_status"]["provenance"]["quality_flag"] == "DEGRADED"


def test_no_hourly_data_yields_none_not_zero():
    """Absence must not render as 0.0 mm, which reads as 'it did not rain'."""
    data = build_response()
    data["hourly"] = {"time": [], "precipitation": []}
    parsed = ws.parse_open_meteo_response(data, 27.0, 88.0)
    assert parsed["observed"]["rainfall_24h"] is None


def test_fallback_weather_is_gone():
    """D2: the hardcoded-values function must not exist at all."""
    assert not hasattr(ws, "get_fallback_weather")


@pytest.mark.asyncio
async def test_unreachable_source_returns_no_values(monkeypatch):
    """D2: every observed field is null and the payload is marked OFFLINE."""
    import httpx

    async def boom(*a, **k):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(httpx.AsyncClient, "get", boom)
    monkeypatch.setattr(ws.settings, "OPEN_METEO_RETRIES", 0)

    result = await ws.fetch_live_weather(27.3389, 88.6065)
    assert result["status"] == "OFFLINE"
    assert result["data_status"]["status"] == "OFFLINE"
    for field in ("temperature", "humidity", "rainfall_1h",
                  "rainfall_24h", "rainfall_7d_cumulative"):
        assert result[field] is None, f"{field} was substituted with a value"
    assert result["rainfall_trend_7d"] == []
    assert "142" not in str(result)          # the baseline fallback constant
