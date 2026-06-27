"""add map_votes table

Per-player-count map votes/vetoes cast by logged-in users. One row per
(user, player_count, map_name); `choice` is 'vote' or 'veto'.

Revision ID: a8b9c0d1e2f3
Revises: f7a1c2d3e4b5
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "f7a1c2d3e4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "map_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("player_count", sa.SmallInteger(), nullable=False),
        sa.Column("map_name", sa.String(), nullable=False),
        sa.Column("choice", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("choice in ('vote', 'veto')", name="check_vote_choice"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_map_votes_user_id", "map_votes", ["user_id"])
    op.create_index("ix_map_votes_player_count", "map_votes", ["player_count"])
    op.create_index(
        "idx_map_votes_user_count", "map_votes", ["user_id", "player_count"]
    )
    op.create_index(
        "uq_map_votes_user_count_map",
        "map_votes",
        ["user_id", "player_count", "map_name"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_map_votes_user_count_map", table_name="map_votes")
    op.drop_index("idx_map_votes_user_count", table_name="map_votes")
    op.drop_index("ix_map_votes_player_count", table_name="map_votes")
    op.drop_index("ix_map_votes_user_id", table_name="map_votes")
    op.drop_table("map_votes")
