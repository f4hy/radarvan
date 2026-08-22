"""add game_night_summary_cache

Durable store of the once-a-night, LLM-written game-night recap, keyed on the
game-night date (US Eastern, 5am rollover - see utils.game_night_date). Unlike
the other commentary caches this one is never written on the read path: the
nightly scheduler job writes at most one row per run, so nights that predate
the feature simply have no row and never gain one.

Revision ID: b2c9e0a4d715
Revises: a1f4c7d92b30
Create Date: 2026-08-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c9e0a4d715"
down_revision: Union[str, Sequence[str], None] = "a1f4c7d92b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "game_night_summary_cache",
        sa.Column("night_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("night_date"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("game_night_summary_cache")
