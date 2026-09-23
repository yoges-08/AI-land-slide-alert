"""The tests that matter: the fabrication paths must be closed.

Baseline behaviour these guard against, all measured on the original code:
  - /api/locations served rainfall_24h = 12.0 for all 304 sites
  - /api/locations served risk_probability from random.uniform
  - /api/risk/1 returned 0.0517 having been fed 0 mm of rainfall it never had
  - /api/location/1 returned 0.98 and a Critical alert quoting "142.0mm",
    a hardcoded fallback constant
  - /api/satellite/1 returned elevation-derived numbers labelled
    "NASA MODIS / Sentinel-2 & Sentinel-1"
"""
import json
from pathlib import Path

import pytest

from backend.app.services import alert_service

DATA_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "ne_india_locations.json"


# --- seed data (defect 5) --------------------------------------------------

def test_locations_do_not_serve_random_hazard_values(client):
    body = client.get("/api/locations").json()
    assert len(body) > 0
    for rec in body:
        assert rec["hazard_index"] is None
        assert rec["risk_category"] is None
        assert rec["rainfall_24h"] is None, "the 12.0 mm default is back"
        assert rec["vegetation_index"] is None
        assert rec["key_risk_factors"] is None


def test_locations_declare_their_provenance(client):
    body = client.get("/api/locations").json()
    assert {r["provenance"] for r in body} <= {"CURATED_SEED", "SYNTHETIC_SEED"}
    assert all(r["data_status"] == "NO_DATA" for r in body)


def test_synthetic_sector_sites_are_labelled_as_such(client):
    body = client.get("/api/locations").json()
    sectors = [r for r in body if "Sector-" in r["name"]]
    assert sectors, "fixture changed"
    assert all(r["provenance"] == "SYNTHETIC_SEED" for r in sectors)


def test_fabricated_fields_never_leave_the_loader():
    """Raw file still holds the random values; the loader must strip them."""
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert "risk_probability" in raw[0], "fixture changed"
    from backend.app.api.routes import get_all_cached_locations
    for rec in get_all_cached_locations():
        for field in ("risk_probability", "key_risk_factors", "is_sample_data",
                      "historical_landslides", "satellite_source"):
            assert field not in rec


# --- satellite (defect 1) --------------------------------------------------

def test_satellite_returns_no_data_not_derived_values(client):
    body = client.get("/api/satellite/1").json()
    if "copernicus" in body["source"].lower():
        # Live M4 ingestion is active
        if body["vegetation_index"] is not None:
            assert 0.0 <= body["vegetation_index"] <= 1.0
        if body["bare_soil_pct"] is not None:
            assert 0.0 <= body["bare_soil_pct"] <= 100.0
        if body["flood_extent_flag"] is not None:
            assert isinstance(body["flood_extent_flag"], bool)
        if body["snow_cover_pct"] is not None:
            assert 0.0 <= body["snow_cover_pct"] <= 100.0
    else:
        for field in ("snow_cover_pct", "snowmelt_rate", "farm_change_flag", "flood_extent_flag"):
            assert body[field] is None
        assert body["vegetation_index"] is None
        assert body["bare_soil_pct"] is None
        assert "pending" in body["source"].lower()


def test_satellite_does_not_claim_nasa_or_copernicus_provenance(client):
    body = client.get("/api/satellite/1").json()
    blob = json.dumps(body)
    assert "MODIS / Sentinel" not in blob
    assert "Near-real-time satellite indices" not in blob


def test_fake_satellite_module_is_not_importable_in_production():
    from backend.app.core.mode import DemoCodeInProductionError
    import importlib, sys
    sys.modules.pop("backend.demo.fake_satellite", None)
    with pytest.raises(DemoCodeInProductionError):
        importlib.import_module("backend.demo.fake_satellite")


def test_no_production_module_imports_the_demo_package():
    """Static check: backend/app must never reference backend.demo at module scope."""
    app_dir = Path(__file__).resolve().parent.parent / "backend" / "app"
    offenders = []
    for path in app_dir.rglob("*.py"):
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("import backend.demo", "from backend.demo")):
                indented = line[0] in " \t"     # function-scoped, gated by is_demo()
                if not indented:
                    offenders.append(f"{path.name}:{num}")
    assert not offenders, f"module-scope demo imports: {offenders}"


def test_esri_commercial_basemap_removed(client):
    layers = client.get("/api/satellite/layers/info").json()
    assert "esri_world_imagery" not in layers
    assert "arcgisonline" not in json.dumps(layers)


def test_bhuvan_layer_is_disabled_and_marked_pending(client):
    layers = client.get("/api/satellite/layers/info").json()
    bhuvan = layers["isro_bhuvan_wms"]
    assert bhuvan["status"] == "PENDING_VERIFICATION"
    assert bhuvan["enabled"] is False


# --- weather / risk join (defect 2, 3 and the /risk join) ------------------

def test_weather_offline_carries_no_values(client, no_network):
    body = client.get("/api/weather/27.3389/88.6065").json()
    assert body["status"] == "OFFLINE"
    assert body["rainfall_24h"] is None
    # last_success_at is omitted entirely when we have never had a success.
    assert body["data_status"].get("last_success_at") in (None,) or isinstance(
        body["data_status"]["last_success_at"], str)
    assert body["data_status"]["reason"]


def test_risk_endpoint_withholds_a_score_when_rainfall_is_missing(client, no_network):
    """Baseline returned 0.0517/Low here, computed from 0 mm it never had."""
    body = client.get("/api/risk/1").json()
    assert body["hazard_index"] is None
    assert body["risk_category"] is None
    assert body["status"] == "NO_DATA"


def test_location_detail_withholds_a_score_when_rainfall_is_missing(client, no_network):
    """Baseline returned 0.98/High built on the hardcoded 142 mm."""
    body = client.get("/api/location/1").json()
    assert body["prediction"]["status"] in ("NO_DATA", "DEGRADED")
    if body["prediction"]["status"] == "DEGRADED":
        assert "Weather unavailable" in body["prediction"]["reason"]
    else:
        assert body["prediction"]["hazard_index"] is None
    assert "142" not in json.dumps(body["weather"])


def test_no_alert_can_fire_without_an_observation(client, no_network):
    """The baseline emitted Critical / 'due to 142.0mm rainfall' right here."""
    body = client.get("/api/location/1").json()
    alert = body["threshold_alert"]
    assert alert["breach"] is False
    assert alert["evaluated"] is False


def test_threshold_evaluation_requires_observed_rainfall():
    result = alert_service.evaluate_threshold_breach(
        {"name": "Gangtok"},
        {"status": "OFFLINE", "observed": None},
        {"hazard_index": 0.95},
    )
    assert result["breach"] is False and result["evaluated"] is False


def test_threshold_evaluation_fires_on_a_real_observation():
    result = alert_service.evaluate_threshold_breach(
        {"name": "Gangtok"},
        {"status": "FRESH", "source": "Open-Meteo",
         "observed": {"rainfall_24h": 130.0, "observed_at": "2026-09-19T12:00:00+00:00"}},
        {"hazard_index": 0.82},
    )
    assert result["breach"] is True
    assert result["inputs"]["observed_rainfall_24h_mm"] == 130.0
    assert result["inputs"]["observed_at"] is not None


# --- alerts (defect 4) -----------------------------------------------------

def test_alert_feed_starts_empty(client):
    alert_service.reset_alerts()
    assert client.get("/api/alerts").json() == []


def test_hardcoded_alert_prose_is_gone():
    source = (Path(__file__).resolve().parent.parent / "backend" / "app" /
              "services" / "alert_service.py").read_text()
    assert "2 hours ago" not in source.replace('"2 hours ago"', "")
    assert "Disang Shale Saturation Alert" not in source
    assert "DEFAULT_ALERTS" not in source


def test_created_at_is_a_real_timestamp():
    from datetime import datetime
    alert_service.reset_alerts()
    alert = alert_service.create_alert(1, "Gangtok", "Sikkim", "Landslide",
                                       "High", "t", "m")
    parsed = datetime.fromisoformat(alert["created_at"])
    assert parsed.tzinfo is not None
    assert alert["advisory"].startswith("ADVISORY ONLY")


def test_unauthenticated_alert_write_is_refused(client):
    r = client.post("/api/alerts", json={
        "location_id": 1, "location_name": "X", "state": "Sikkim",
        "title": "t", "message": "m"})
    assert r.status_code == 503


# --- model wording (defect 6) ---------------------------------------------

def test_model_output_uses_index_not_probability(client):
    body = client.get("/api/model/info").json()
    assert body["calibration"] == "UNCALIBRATED"
    assert body["validated_against_observed_events"] is False
    assert "SYNTHETIC" in body["training_data"]


def test_predict_response_has_no_probability_field(client):
    from tests.test_contract_api import PREDICT_BODY
    body = client.post("/api/predict", json=PREDICT_BODY).json()
    assert "hazard_index" in body
    assert "risk_probability" not in body
    assert "flood_risk_probability" not in body


def test_predict_requires_rainfall_rather_than_defaulting_it(client):
    """Baseline defaulted rainfall_24h to 45.0 mm for coordinate-only calls."""
    r = client.post("/api/predict", json={
        "latitude": 27.3, "longitude": 88.6, "elevation": 1650, "slope": 34.5})
    assert r.status_code == 422
    missing = {e["loc"][-1] for e in r.json()["detail"]}
    assert "rainfall_24h" in missing


# --- advisory framing ------------------------------------------------------

@pytest.mark.parametrize("path", ["/", "/api/location/1", "/api/export/report/1"])
def test_advisory_notice_names_the_official_authorities(client, no_network, path):
    blob = json.dumps(client.get(path).json())
    for authority in ("IMD", "NDMA", "NCS"):
        assert authority in blob


def test_advisory_header_on_every_response(client):
    r = client.get("/health")
    assert "IMD, NDMA and NCS" in r.headers["X-LANDSAFE-Advisory"]
    assert r.headers["X-LANDSAFE-Mode"] == "production"


# --- CORS (defect 7) -------------------------------------------------------

def test_cors_is_not_a_wildcard():
    from backend.app.core.config import settings
    assert "*" not in settings.cors_origin_list
    assert settings.cors_origin_list


def test_no_wildcard_cors_in_source():
    src = (Path(__file__).resolve().parent.parent / "backend" / "app" / "main.py").read_text()
    code = [ln for ln in src.splitlines() if not ln.strip().startswith("#")]
    assert 'allow_origins=["*"]' not in "\n".join(code)


# --- mode isolation --------------------------------------------------------

def test_default_mode_is_production():
    from backend.app.core.config import settings
    assert settings.LANDSAFE_MODE == "production"
