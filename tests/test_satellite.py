import pytest
from backend.app.core.config import settings
from backend.app.services.satellite_service import compute_satellite_indices, get_available_layers
from backend.app.services.demo_service import compute_synthetic_satellite_indices

def test_production_satellite_service_no_fake_math(monkeypatch):
    # Ensure production mode
    monkeypatch.setattr(settings, "LANDSAFE_MODE", "production")
    result = compute_satellite_indices(elevation=3200, slope=35, lat=27.5, lon=88.5)
    
    assert result["status"] == "PENDING_INGESTION"
    assert result["snow_cover_pct"] is None
    assert result["bare_soil_pct"] is None
    assert result["vegetation_index"] is None
    assert result["is_sample_data"] is False
    assert result["quality_flag"] == "AWAITING_INGESTION_M4"

def test_demo_satellite_simulator(monkeypatch):
    monkeypatch.setattr(settings, "LANDSAFE_MODE", "demo")
    result = compute_satellite_indices(elevation=3200, slope=35, lat=27.5, lon=88.5)
    
    assert result["status"] == "DEMO_SIMULATION"
    assert result["is_sample_data"] is True
    assert "DEMO DATA" in result["disclaimer"]
    assert isinstance(result["snow_cover_pct"], (int, float))

def test_satellite_layers_metadata():
    layers = get_available_layers()
    assert "nasa_gibs_truecolor" in layers
    assert "snow_cover_ndsi" in layers
    assert "flood_sar" in layers
