"""add_lgd_administrative_columns

Revision ID: b7e29184c201
Revises: a6dacb25e406
Create Date: 2026-09-20 20:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e29184c201'
down_revision: Union[str, Sequence[str], None] = 'a6dacb25e406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with official LGD codes and geometry status if not present."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    # State columns
    state_cols = [c['name'] for c in insp.get_columns('states')] if insp.has_table('states') else []
    if 'lgd_code' not in state_cols:
        op.add_column('states', sa.Column('lgd_code', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_states_lgd_code'), 'states', ['lgd_code'], unique=True)
    if 'state_type' not in state_cols:
        op.add_column('states', sa.Column('state_type', sa.String(length=20), nullable=False, server_default='STATE'))

    # District columns
    dist_cols = [c['name'] for c in insp.get_columns('districts')] if insp.has_table('districts') else []
    if 'lgd_code' not in dist_cols:
        op.add_column('districts', sa.Column('lgd_code', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_districts_lgd_code'), 'districts', ['lgd_code'], unique=True)
    if 'lgd_state_code' not in dist_cols:
        op.add_column('districts', sa.Column('lgd_state_code', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_districts_lgd_state_code'), 'districts', ['lgd_state_code'], unique=False)
    if 'census_2011_code' not in dist_cols:
        op.add_column('districts', sa.Column('census_2011_code', sa.String(length=20), nullable=True))
        op.create_index(op.f('ix_districts_census_2011_code'), 'districts', ['census_2011_code'], unique=False)
    if 'geometry_status' not in dist_cols:
        op.add_column('districts', sa.Column('geometry_status', sa.String(length=30), nullable=False, server_default='AVAILABLE'))
    if 'terrain_provenance' not in dist_cols:
        op.add_column('districts', sa.Column('terrain_provenance', sa.String(length=150), nullable=False, server_default='ESTIMATED / HEURISTIC -- pending Copernicus GLO-30 DEM ingestion'))
    if 'headquarters' not in dist_cols:
        op.add_column('districts', sa.Column('headquarters', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_districts_census_2011_code'), table_name='districts')
    op.drop_index(op.f('ix_districts_lgd_state_code'), table_name='districts')
    op.drop_index(op.f('ix_districts_lgd_code'), table_name='districts')
    op.drop_column('districts', 'headquarters')
    op.drop_column('districts', 'terrain_provenance')
    op.drop_column('districts', 'geometry_status')
    op.drop_column('districts', 'census_2011_code')
    op.drop_column('districts', 'lgd_state_code')
    op.drop_column('districts', 'lgd_code')

    op.drop_index(op.f('ix_states_lgd_code'), table_name='states')
    op.drop_column('states', 'state_type')
    op.drop_column('states', 'lgd_code')
