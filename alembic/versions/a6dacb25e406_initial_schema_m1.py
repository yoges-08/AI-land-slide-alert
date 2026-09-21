"""initial_schema_m1

Revision ID: a6dacb25e406
Revises: 
Create Date: 2026-09-19 22:48:49.250389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from backend.app.models.db_models import Base


# revision identifiers, used by Alembic.
revision: str = 'a6dacb25e406'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all core domain tables on clean database."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
