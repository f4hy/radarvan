"""add player_profiles

Durable, versioned per-player profile deep stats (favorites, aversions,
percentiles). One JSONB row per profiled player, recomputed as a batch.

Revision ID: d4e5f6a7b8c9
Revises: ec5e06c1753e
Create Date: 2026-07-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "ec5e06c1753e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "player_profiles",
        sa.Column("player", sa.String(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("player"),
    )
    op.create_index(
        "ix_player_profiles_version",
        "player_profiles",
        ["version"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_player_profiles_version",
        table_name="player_profiles",
    )
    op.drop_table("player_profiles")
