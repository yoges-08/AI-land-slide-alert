"""initial_schema_m1

Revision ID: a6dacb25e406
Revises: 
Create Date: 2026-09-19 22:48:49.250389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6dacb25e406'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. states
    op.create_table(
        'states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('iso_code', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iso_code')
    )
    op.create_index(op.f('ix_states_id'), 'states', ['id'], unique=False)
    op.create_index(op.f('ix_states_name'), 'states', ['name'], unique=True)

    # 2. districts
    op.create_table(
        'districts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('state_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('tier', sa.SmallInteger(), nullable=False, server_default='1'),
        sa.Column('physiography_zone', sa.String(length=50), nullable=False, server_default='ne_hills'),
        sa.Column('mean_elevation_m', sa.Float(), nullable=False, server_default='1000.0'),
        sa.Column('mean_slope_deg', sa.Float(), nullable=False, server_default='25.0'),
        sa.Column('dominant_lithology', sa.String(length=50), nullable=False, server_default='lesser_himalaya'),
        sa.Column('is_1893_seismic_zone', sa.SmallInteger(), nullable=False, server_default='5'),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('boundary_source', sa.String(length=100), nullable=True),
        sa.Column('licence', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['state_id'], ['states.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_districts_id'), 'districts', ['id'], unique=False)
    op.create_index(op.f('ix_districts_name'), 'districts', ['name'], unique=False)
    op.create_index(op.f('ix_districts_state_id'), 'districts', ['state_id'], unique=False)
    op.create_index('idx_district_state_name', 'districts', ['state_id', 'name'], unique=False)
    op.create_index('idx_district_tier', 'districts', ['tier'], unique=False)

    # 3. data_sources
    op.create_table(
        'data_sources',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('cadence_minutes', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('licence', sa.String(length=200), nullable=True),
        sa.Column('api_endpoint', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. source_health
    op.create_table(
        'source_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='UNKNOWN'),
        sa.Column('last_successful_fetch', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_attempt_status', sa.String(length=50), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_latency_ms', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )
    op.create_index(op.f('ix_source_health_id'), 'source_health', ['id'], unique=False)

    # 5. model_versions
    op.create_table(
        'model_versions',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('version_tag', sa.String(length=50), nullable=False),
        sa.Column('algorithm', sa.String(length=100), nullable=False),
        sa.Column('weights_path', sa.String(length=255), nullable=True),
        sa.Column('input_features', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('trained_on_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_production', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. weather_observations
    op.create_table(
        'weather_observations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('observation_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('relative_humidity_pct', sa.Float(), nullable=True),
        sa.Column('wind_speed_kmh', sa.Float(), nullable=True),
        sa.Column('rainfall_1h_mm', sa.Float(), nullable=True),
        sa.Column('rainfall_24h_mm', sa.Float(), nullable=True),
        sa.Column('rainfall_7d_cumulative_mm', sa.Float(), nullable=True),
        sa.Column('quality_flag', sa.String(length=20), nullable=True),
        sa.Column('is_forecast', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_weather_district_obs_time', 'weather_observations', ['district_id', 'observation_time'], unique=False)
    op.create_index(op.f('ix_weather_observations_district_id'), 'weather_observations', ['district_id'], unique=False)
    op.create_index(op.f('ix_weather_observations_observation_time'), 'weather_observations', ['observation_time'], unique=False)

    # 7. satellite_observations
    op.create_table(
        'satellite_observations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False),
        sa.Column('granule_id', sa.String(length=150), nullable=False),
        sa.Column('capture_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('snow_cover_fraction', sa.Float(), nullable=True),
        sa.Column('snowmelt_mm_day', sa.Float(), nullable=True),
        sa.Column('bare_soil_index', sa.Float(), nullable=True),
        sa.Column('ndvi', sa.Float(), nullable=True),
        sa.Column('sar_inundation_km2', sa.Float(), nullable=True),
        sa.Column('cloud_cover_pct', sa.Float(), nullable=True),
        sa.Column('raster_s3_path', sa.String(length=255), nullable=True),
        sa.Column('quality_flag', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_satellite_district_capture_time', 'satellite_observations', ['district_id', 'capture_time'], unique=False)
    op.create_index(op.f('ix_satellite_observations_capture_time'), 'satellite_observations', ['capture_time'], unique=False)
    op.create_index(op.f('ix_satellite_observations_district_id'), 'satellite_observations', ['district_id'], unique=False)

    # 8. hazard_events
    op.create_table(
        'hazard_events',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('hazard_type', sa.String(length=50), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('magnitude', sa.Float(), nullable=True),
        sa.Column('depth_km', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('epicenter', sa.Text(), nullable=True),
        sa.Column('district_id', sa.Integer(), nullable=True),
        sa.Column('pga_estimate_g', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('disclosure', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hazard_events_event_time'), 'hazard_events', ['event_time'], unique=False)

    # 9. risk_assessments
    op.create_table(
        'risk_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('model_version_id', sa.String(length=50), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('factor_of_safety', sa.Float(), nullable=True),
        sa.Column('susceptibility_score', sa.Float(), nullable=True),
        sa.Column('trigger_score', sa.Float(), nullable=True),
        sa.Column('composite_hazard_index', sa.Float(), nullable=False),
        sa.Column('hazard_level', sa.String(length=20), nullable=False),
        sa.Column('model_uncertainty', sa.Float(), nullable=True),
        sa.Column('linear_shap_factors', sa.JSON(), nullable=True),
        sa.Column('glof_risk_level', sa.String(length=20), nullable=True),
        sa.Column('flash_flood_level', sa.String(length=20), nullable=True),
        sa.Column('input_quality_flag', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_risk_district_calculated_at', 'risk_assessments', ['district_id', 'calculated_at'], unique=False)
    op.create_index(op.f('ix_risk_assessments_calculated_at'), 'risk_assessments', ['calculated_at'], unique=False)
    op.create_index(op.f('ix_risk_assessments_district_id'), 'risk_assessments', ['district_id'], unique=False)

    # 10. predictions
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('model_version_id', sa.String(length=50), nullable=False),
        sa.Column('predicted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('landslide_probability', sa.Float(), nullable=True),
        sa.Column('risk_category', sa.String(length=50), nullable=False),
        sa.Column('flood_probability', sa.Float(), nullable=True),
        sa.Column('flood_category', sa.String(length=50), nullable=True),
        sa.Column('top_factors', sa.JSON(), nullable=True),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_predictions_district_id'), 'predictions', ['district_id'], unique=False)
    op.create_index(op.f('ix_predictions_predicted_at'), 'predictions', ['predicted_at'], unique=False)

    # 11. alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_id', sa.Integer(), nullable=False),
        sa.Column('hazard_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message_en', sa.Text(), nullable=False),
        sa.Column('message_hi', sa.Text(), nullable=True),
        sa.Column('message_bn', sa.Text(), nullable=True),
        sa.Column('message_as', sa.Text(), nullable=True),
        sa.Column('message_ml', sa.Text(), nullable=True),
        sa.Column('cap_identifier', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_cap_identifier'), 'alerts', ['cap_identifier'], unique=True)
    op.create_index(op.f('ix_alerts_district_id'), 'alerts', ['district_id'], unique=False)
    op.create_index(op.f('ix_alerts_is_active'), 'alerts', ['is_active'], unique=False)
    op.create_index(op.f('ix_alerts_issued_at'), 'alerts', ['issued_at'], unique=False)


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('predictions')
    op.drop_table('risk_assessments')
    op.drop_table('hazard_events')
    op.drop_table('satellite_observations')
    op.drop_table('weather_observations')
    op.drop_table('model_versions')
    op.drop_table('source_health')
    op.drop_table('data_sources')
    op.drop_table('districts')
    op.drop_table('states')
