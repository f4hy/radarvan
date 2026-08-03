"""add discord_event_id to bracket_match_state

Revision ID: e2f21c15866b
Revises: 9417f9aa55dc
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f21c15866b"
down_revision: Union[str, Sequence[str], None] = "9417f9aa55dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "bracket_match_state",
        sa.Column("discord_event_id", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("bracket_match_state", "discord_event_id")
