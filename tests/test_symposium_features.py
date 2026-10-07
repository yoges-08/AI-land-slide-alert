import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_interactive_simulate_endpoint():
    payload = {
        "rainfall_intensity": 120.0,
        "soil_moisture": 75.0,
        "slope": 35.0,
        "earthquake_magnitude": 2.5,
        "vegetation_cover": 30.0,
        "duration": 24.0
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "probability" in data
    assert "hazard_index" in data
    assert "risk_level" in data
    assert "shap_values" in data
    assert "contributions" in data
    assert len(data["contributions"]) == 6
    assert data["probability"] > 0.0


def test_notification_subscription_and_log():
    # 1. Subscribe phone
    sub_payload = {
        "phone_number": "+91 99999 11111",
        "district": "Wayanad",
        "name": "Disaster Relief Officer"
    }
    sub_res = client.post("/api/notifications/subscribe", json=sub_payload)
    assert sub_res.status_code == 200
    assert sub_res.json()["success"] is True

    # 2. Test alert dispatch
    test_payload = {
        "phone_number": "+91 99999 11111",
        "district": "Wayanad"
    }
    test_res = client.post("/api/notifications/test", json=test_payload)
    assert test_res.status_code == 200
    assert test_res.json()["success"] is True

    # 3. Check notification log
    log_res = client.get("/api/notifications/log")
    assert log_res.status_code == 200
    log_data = log_res.json()
    assert "notifications" in log_data
    assert len(log_data["notifications"]) >= 1


def test_evacuation_endpoint():
    response = client.get("/api/evacuation/Wayanad")
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "target_shelter" in data
    assert "primary_route" in data
    assert "alternative_route" in data
    assert len(data["primary_route"]["coordinates"]) > 0
    assert "whatsapp_share_text" in data
