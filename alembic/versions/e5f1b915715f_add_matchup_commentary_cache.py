"""add matchup_commentary_cache

Durable cache of AI-generated pre-game matchup commentary, keyed on
(player1, player2, round_name). Generation is a real, billed LLM call; once
written, a row is served on every subsequent request for the same triple.

Revision ID: e5f1b915715f
Revises: 1711cb99f87a
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f1b915715f"
down_revision: Union[str, Sequence[str], None] = "1711cb99f87a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "matchup_commentary_cache",
        sa.Column("player1", sa.String(), nullable=False),
        sa.Column("player2", sa.String(), nullable=False),
        sa.Column("round_name", sa.String(), nullable=False),
        sa.Column("commentary", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("player1", "player2", "round_name"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("matchup_commentary_cache")
