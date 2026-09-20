import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.db_models import (
    State, District, GridCell, DataSource, SourceHealth,
    WeatherObservation, SatelliteObservation, HazardEvent,
    ModelVersion, RiskAssessment, Prediction, Alert, Report, utc_now
)
from backend.app.services.db_seeder import seed_database

@pytest.fixture(scope="module")
def db_session():
    init_db()
    seed_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_states_seeded(db_session: Session):
    state_count = db_session.query(State).count()
    assert state_count >= 28, f"Expected at least 28 states, got {state_count}"
    
    sikkim = db_session.query(State).filter(State.name == "Sikkim").first()
    assert sikkim is not None
    assert sikkim.districts is not None
    assert len(sikkim.districts) > 0

def test_all_726_districts_seeded(db_session: Session):
    district_count = db_session.query(District).count()
    assert district_count == 726, f"Expected exactly 726 districts, got {district_count}"
    
    # Check sample district attributes
    aizawl = db_session.query(District).filter(District.name == "Aizawl").first()
    assert aizawl is not None
    assert aizawl.tier == 1
    assert aizawl.physiography_zone == "ne_hills"
    assert aizawl.is_1893_seismic_zone == 5
    assert aizawl.latitude > 20.0
    assert aizawl.longitude > 90.0

def test_data_sources_and_health(db_session: Session):
    sources = db_session.query(DataSource).all()
    source_ids = [s.id for s in sources]
    
    expected_sources = [
        "MOSDAC_INSAT3D_QPE",
        "NASA_GPM_IMERG",
        "OPEN_METEO",
        "COPERNICUS_S1_SAR",
        "COPERNICUS_S2_OPTICAL",
        "COPERNICUS_DEM_GLO30",
        "USGS_FDSN",
        "NASA_FIRMS",
        "NASA_COOLR"
    ]
    for exp in expected_sources:
        assert exp in source_ids, f"Missing data source: {exp}"
        health = db_session.query(SourceHealth).filter(SourceHealth.source_id == exp).first()
        assert health is not None
        assert health.status in ["FRESH", "RECENT", "AGING", "STALE", "OFFLINE"]

def test_model_versions_seeded(db_session: Session):
    models = db_session.query(ModelVersion).all()
    model_ids = [m.id for m in models]
    assert "LANDSAFE_PHYS_V1" in model_ids
    assert "LANDSAFE_SUSC_TRIG_V1" in model_ids

def test_insert_weather_observation(db_session: Session):
    district = db_session.query(District).first()
    obs_time = datetime.now(timezone.utc)
    
    weather_obs = WeatherObservation(
        district_id=district.id,
        source_id="OPEN_METEO",
        observation_time=obs_time,
        temperature_c=22.4,
        relative_humidity_pct=88.0,
        rainfall_1h_mm=4.5,
        rainfall_24h_mm=65.0,
        rainfall_7d_cumulative_mm=190.0,
        antecedent_saturation_index=0.72,
        quality_flag="NOMINAL",
        is_forecast=False
    )
    db_session.add(weather_obs)
    db_session.commit()
    
    retrieved = db_session.query(WeatherObservation).filter(
        WeatherObservation.district_id == district.id,
        WeatherObservation.observation_time == obs_time
    ).first()
    assert retrieved is not None
    assert retrieved.rainfall_24h_mm == 65.0
    assert retrieved.quality_flag == "NOMINAL"

def test_insert_risk_assessment_and_alert(db_session: Session):
    district = db_session.query(District).first()
    now = datetime.now(timezone.utc)
    
    # 1. Assessment
    assessment = RiskAssessment(
        district_id=district.id,
        model_version_id="LANDSAFE_SUSC_TRIG_V1",
        calculated_at=now,
        factor_of_safety=0.82,
        susceptibility_score=0.78,
        trigger_score=0.85,
        composite_hazard_index=0.66,
        hazard_level="HIGH",
        model_uncertainty=0.12,
        linear_shap_factors={"rainfall_24h": 0.35, "slope": 0.22, "geology": 0.15},
        glof_risk_level="LOW",
        flash_flood_level="MODERATE",
        input_quality_flag="NOMINAL"
    )
    db_session.add(assessment)
    
    # 2. Alert
    alert = Alert(
        district_id=district.id,
        hazard_type="Landslide",
        severity="WARNING",
        title=f"Landslide Warning: {district.name}",
        message_en=f"Critical rainfall trigger detected in {district.name}.",
        message_hi="भारी बारिश के कारण भूस्खलन की चेतावनी।",
        cap_identifier=f"IN-LS-{district.id}-{int(now.timestamp())}",
        is_active=True,
        issued_at=now,
        expires_at=now + timedelta(hours=12),
        cooldown_until=now + timedelta(hours=4)
    )
    db_session.add(alert)
    db_session.commit()
    
    retrieved_alert = db_session.query(Alert).filter(Alert.cap_identifier == alert.cap_identifier).first()
    assert retrieved_alert is not None
    assert retrieved_alert.severity == "WARNING"
    assert retrieved_alert.message_hi is not None
