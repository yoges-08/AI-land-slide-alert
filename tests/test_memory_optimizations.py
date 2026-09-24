"""Tests for memory overflow fixes and memory diagnostics endpoint."""
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.weather_service import (
    _WEATHER_CACHE,
    _WEATHER_CACHE_MAX_SIZE,
    _evict_weather_cache,
    _get_weather_http_client,
    WEATHER_CACHE_TTL_SECONDS,
)
from backend.app.services.satellite_service import (
    _SAT_CACHE,
    _SAT_CACHE_MAX_SIZE,
    _evict_sat_cache,
    _get_sat_http_client,
    SAT_CACHE_TTL_SECONDS,
)
from backend.app.services.ml_service import _get_shap_explainer, load_ml_assets


@pytest.fixture
def client():
    return TestClient(app)


def test_weather_cache_eviction_and_bounding():
    """Verify weather cache purges expired entries and strictly respects MAX_SIZE."""
    now = time.time()
    _WEATHER_CACHE.clear()

    # 1. Add expired entries
    _WEATHER_CACHE[(10.0, 70.0)] = (now - WEATHER_CACHE_TTL_SECONDS - 100, {"data": "expired"})
    _WEATHER_CACHE[(11.0, 71.0)] = (now - 50, {"data": "fresh"})

    _evict_weather_cache()
    assert (10.0, 70.0) not in _WEATHER_CACHE
    assert (11.0, 71.0) in _WEATHER_CACHE

    # 2. Add more entries than MAX_SIZE
    for i in range(_WEATHER_CACHE_MAX_SIZE + 50):
        _WEATHER_CACHE[(round(10.0 + i * 0.1, 1), round(70.0 + i * 0.1, 1))] = (now + i, {"data": i})

    _evict_weather_cache()
    assert len(_WEATHER_CACHE) <= _WEATHER_CACHE_MAX_SIZE
    _WEATHER_CACHE.clear()


def test_satellite_cache_eviction_and_bounding():
    """Verify satellite cache purges expired entries and strictly respects MAX_SIZE."""
    now = time.time()
    _SAT_CACHE.clear()

    # 1. Add expired entry
    _SAT_CACHE[(27.1, 88.1)] = (now - SAT_CACHE_TTL_SECONDS - 100, {"status": "expired"})
    _SAT_CACHE[(27.2, 88.2)] = (now - 10, {"status": "fresh"})

    _evict_sat_cache()
    assert (27.1, 88.1) not in _SAT_CACHE
    assert (27.2, 88.2) in _SAT_CACHE

    # 2. Add more than MAX_SIZE
    for i in range(_SAT_CACHE_MAX_SIZE + 40):
        _SAT_CACHE[(round(20.0 + i * 0.1, 2), round(80.0 + i * 0.1, 2))] = (now + i, {"sat": i})

    _evict_sat_cache()
    assert len(_SAT_CACHE) <= _SAT_CACHE_MAX_SIZE
    _SAT_CACHE.clear()


@pytest.mark.asyncio
async def test_shared_http_clients_reused():
    """Verify weather and satellite HTTP clients are reused singletons."""
    c1 = await _get_weather_http_client()
    c2 = await _get_weather_http_client()
    assert c1 is c2

    s1 = await _get_sat_http_client()
    s2 = await _get_sat_http_client()
    assert s1 is s2


def test_lazy_shap_explainer():
    """Verify SHAP explainer is created lazily on first access."""
    load_ml_assets()
    explainer = _get_shap_explainer()
    assert explainer is not None
    # Subsequent access returns same instance
    assert _get_shap_explainer() is explainer


def test_debug_memory_endpoint(client):
    """Verify GET /api/debug/memory returns process RAM and cache diagnostics."""
    response = client.get("/api/debug/memory")
    assert response.status_code == 200
    data = response.json()

    assert "process_memory" in data
    assert "rss_mb" in data["process_memory"]
    assert "render_budget_mb" in data["process_memory"]
    assert data["process_memory"]["render_budget_mb"] == 512.0
    assert "caches" in data
    assert "weather_cache_entries" in data["caches"]
    assert "satellite_cache_entries" in data["caches"]
    assert "ml_status" in data


def test_simulation_endpoint_with_cache(client):
    """Verify POST /api/simulation executes cleanly using cached/live weather."""
    response = client.post(
        "/api/simulation",
        json={
            "location_id": 1,
            "rainfall_24h_delta": 25.0,
            "slope_override": 35.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "simulated_hazard_index" in data
    assert "simulated_risk_category" in data
