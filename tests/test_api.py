import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_root_endpoint_disclaimer():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "academic_prototype_disclaimer" in data
    assert "IMD" in data["academic_prototype_disclaimer"] or "academic prototype" in data["academic_prototype_disclaimer"]

def test_get_locations_endpoint():
    response = client.get("/api/locations?state=Sikkim")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert data[0]["state"] == "Sikkim"

def test_hierarchy_endpoint():
    response = client.get("/api/hierarchy")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    states = [item["state"] for item in data]
    assert "Sikkim" in states or len(states) > 0

def test_alerts_endpoint():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_predict_endpoint():
    payload = {
        "latitude": 27.33,
        "longitude": 88.61,
        "elevation": 1650.0,
        "slope": 34.0,
        "rainfall_1h": 12.0,
        "rainfall_24h": 140.0,
        "rainfall_7d_cumulative": 380.0,
        "rainfall_intensity": 12.0,
        "soil_type": "Clay Loam",
        "geology": "Phyllite & Schist",
        "land_cover": "Degraded Forest",
        "aspect": "NE",
        "distance_road": 80.0,
        "distance_river": 300.0,
        "historical_landslides": 4,
        "snow_cover_pct": 0.0,
        "snowmelt_rate": 0.0,
        "bare_soil_pct": 35.0,
        "vegetation_index": 0.45,
        "farm_change_flag": True,
        "flood_extent_flag": False
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_probability" in data
    assert "risk_category" in data
    assert "top_factors" in data

def test_satellite_layer_metadata():
    response = client.get("/api/satellite/layers/info")
    assert response.status_code == 200
    data = response.json()
    assert "nasa_gibs_truecolor" in data
