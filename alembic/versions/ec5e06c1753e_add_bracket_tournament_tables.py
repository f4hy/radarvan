"""add bracket tournament tables

Revision ID: ec5e06c1753e
Revises: c3d4e5f6a7b8
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ec5e06c1753e"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bracket_tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bracket_players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("seed", sa.SmallInteger(), nullable=False),
        sa.Column("player_name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["bracket_tournaments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bracket_players_tournament_id"),
        "bracket_players",
        ["tournament_id"],
    )
    op.create_index(
        "uq_bracket_players_tournament_seed",
        "bracket_players",
        ["tournament_id", "seed"],
        unique=True,
    )
    op.create_table(
        "bracket_match_state",
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=16), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("best_of", sa.SmallInteger(), nullable=True),
        sa.Column("score_a", sa.SmallInteger(), nullable=True),
        sa.Column("score_b", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["bracket_tournaments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("tournament_id", "match_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("bracket_match_state")
    op.drop_index(
        "uq_bracket_players_tournament_seed", table_name="bracket_players"
    )
    op.drop_index(
        op.f("ix_bracket_players_tournament_id"), table_name="bracket_players"
    )
    op.drop_table("bracket_players")
    op.drop_table("bracket_tournaments")
