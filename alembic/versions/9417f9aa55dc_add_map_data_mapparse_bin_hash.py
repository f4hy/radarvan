"""add map_data.mapparse_bin_hash

Revision ID: 9417f9aa55dc
Revises: 0e560dd853fe
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9417f9aa55dc"
down_revision: Union[str, Sequence[str], None] = "0e560dd853fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "map_data",
        sa.Column("mapparse_bin_hash", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("map_data", "mapparse_bin_hash")
