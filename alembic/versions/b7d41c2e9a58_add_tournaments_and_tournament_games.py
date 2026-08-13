"""add tournaments registry and tournament_games link table

Persists which matches counted as tournament games, replacing the derived
date+player-set filter (2v2) and the frontend's per-render date+name guess
(1v1 bracket). Anchored to a durable `tournaments` row rather than
`bracket_tournaments`, whose reset cascades everything away.

Revision ID: b7d41c2e9a58
Revises: a3c9f21b7e04
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d41c2e9a58"
down_revision: Union[str, Sequence[str], None] = "a3c9f21b7e04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # match_id intentionally has no FK to matches: reset_match deletes and a
    # reparse re-inserts the row under the same id, so CASCADE would destroy
    # curated links and RESTRICT would break the reset.
    op.create_table(
        "tournament_games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=True),
        sa.Column("round_name", sa.String(length=64), nullable=True),
        sa.Column("series_index", sa.SmallInteger(), nullable=True),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("source in ('auto', 'manual')", name="check_link_source"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tournament_games_tournament_id"),
        "tournament_games",
        ["tournament_id"],
    )
    op.create_index(
        op.f("ix_tournament_games_match_id"), "tournament_games", ["match_id"]
    )
    op.create_index(
        "uq_tournament_games_tournament_match",
        "tournament_games",
        ["tournament_id", "match_id"],
        unique=True,
    )

    op.add_column(
        "bracket_tournaments", sa.Column("tournament_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_bracket_tournaments_tournament_id",
        "bracket_tournaments",
        "tournaments",
        ["tournament_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_bracket_tournaments_tournament_id",
        "bracket_tournaments",
        type_="foreignkey",
    )
    op.drop_column("bracket_tournaments", "tournament_id")
    op.drop_index(
        "uq_tournament_games_tournament_match", table_name="tournament_games"
    )
    op.drop_index(op.f("ix_tournament_games_match_id"), table_name="tournament_games")
    op.drop_index(
        op.f("ix_tournament_games_tournament_id"), table_name="tournament_games"
    )
    op.drop_table("tournament_games")
    op.drop_table("tournaments")
