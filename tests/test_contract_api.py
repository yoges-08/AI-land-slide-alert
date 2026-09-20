"""M0 baseline contract suite.

Pins the *shape* of every route that existed before the upgrade: the path, the
status code, and the identity keys a consumer depends on. It deliberately does
NOT pin hazard values, because every one of those was fabricated at baseline and
M0 replaces them with NO DATA.

15 routes under /api plus / and /health. This file must stay green through M12.
"""
import pytest

pytestmark = pytest.mark.contract

PREDICT_BODY = {
    "latitude": 27.3389,
    "longitude": 88.6065,
    "elevation": 1650.0,
    "slope": 34.5,
    "rainfall_1h": 4.0,
    "rainfall_24h": 120.0,
    "rainfall_7d_cumulative": 400.0,
    "rainfall_intensity": 4.0,
    "distance_road": 91.0,
    "distance_river": 433.0,
    "historical_landslides": 3,
    "snow_cover_pct": 0.0,
    "snowmelt_rate": 0.0,
    "bare_soil_pct": 30.0,
    "vegetation_index": 0.47,
    "soil_type": "Loam",
    "land_cover": "Dense Forest",
    "geology": "Phyllite & Schist",
    "aspect": "W",
    "farm_change_flag": True,
}


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["system"] == "LANDSAFE-NER"
    assert body["api_prefix"] == "/api"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_locations(client):
    r = client.get("/api/locations")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) > 0
    for key in ("id", "name", "state", "district", "latitude", "longitude"):
        assert key in body[0]


@pytest.mark.parametrize("params", [
    {"state": "Sikkim"},
    {"district": "East Sikkim"},
    {"state": "Sikkim", "district": "East Sikkim"},
])
def test_locations_filters(client, params):
    r = client.get("/api/locations", params=params)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_hierarchy(client):
    r = client.get("/api/hierarchy")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) > 0
    for key in ("state", "districts", "total_locations", "hazard_monitoring_active"):
        assert key in body[0]


def test_location_detail(client, no_network):
    r = client.get("/api/location/1")
    assert r.status_code == 200
    body = r.json()
    for key in ("location", "weather", "satellite", "prediction", "disclaimer", "timestamp"):
        assert key in body


def test_location_detail_404(client):
    assert client.get("/api/location/999999").status_code == 404


def test_weather(client, no_network):
    r = client.get("/api/weather/27.3389/88.6065")
    assert r.status_code == 200
    assert "status" in r.json()


def test_risk(client, no_network):
    r = client.get("/api/risk/1")
    assert r.status_code == 200
    body = r.json()
    for key in ("location_id", "name", "state", "district"):
        assert key in body


def test_risk_404(client):
    assert client.get("/api/risk/999999").status_code == 404


def test_satellite(client):
    r = client.get("/api/satellite/1")
    assert r.status_code == 200
    body = r.json()
    assert body["location_id"] == 1
    assert "source" in body


def test_satellite_layers_info(client):
    r = client.get("/api/satellite/layers/info")
    assert r.status_code == 200
    assert "nasa_gibs_truecolor" in r.json()


def test_alerts_list(client):
    r = client.get("/api/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_history(client, no_network):
    r = client.get("/api/history/1")
    assert r.status_code == 200
    assert "location_id" in r.json()


def test_model_info(client):
    r = client.get("/api/model/info")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_export_report(client, no_network):
    r = client.get("/api/export/report/1")
    assert r.status_code == 200
    body = r.json()
    assert "title" in body and "generated_at" in body


def test_predict(client):
    r = client.post("/api/predict", json=PREDICT_BODY)
    assert r.status_code == 200
    assert "risk_category" in r.json()


def test_predict_requires_full_feature_vector(client):
    assert client.post("/api/predict", json={"slope": 30}).status_code == 422


def test_predict_flood(client):
    r = client.post("/api/predict/flood", json=PREDICT_BODY)
    assert r.status_code == 200
    assert "flood_risk_category" in r.json()


def test_simulation(client, no_network):
    r = client.post("/api/simulation", json={"location_id": 1, "rainfall_24h_delta": 100})
    assert r.status_code == 200
    for key in ("original_risk_category", "simulated_risk_category", "factor_changes"):
        assert key in r.json()


def test_alerts_post_route_still_exists(client):
    """POST /api/alerts must keep responding. M0 disables the write (503);
    M11 re-enables it behind auth. A 404 here would mean the route was lost."""
    r = client.post("/api/alerts", json={
        "location_id": 1, "location_name": "X", "state": "Sikkim",
        "title": "t", "message": "m",
    })
    assert r.status_code != 404
