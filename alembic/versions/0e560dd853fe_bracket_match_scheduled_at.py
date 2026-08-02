"""replace bracket_match_state.scheduled_date with scheduled_at

Revision ID: 0e560dd853fe
Revises: e5f1b915715f
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0e560dd853fe"
down_revision: Union[str, Sequence[str], None] = "e5f1b915715f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "bracket_match_state",
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Preserve any dates admins already entered, as midnight UTC on that date.
    op.execute(
        "UPDATE bracket_match_state "
        "SET scheduled_at = scheduled_date::timestamp AT TIME ZONE 'UTC' "
        "WHERE scheduled_date IS NOT NULL"
    )
    op.drop_column("bracket_match_state", "scheduled_date")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "bracket_match_state",
        sa.Column("scheduled_date", sa.Date(), nullable=True),
    )
    op.execute(
        "UPDATE bracket_match_state "
        "SET scheduled_date = (scheduled_at AT TIME ZONE 'UTC')::date "
        "WHERE scheduled_at IS NOT NULL"
    )
    op.drop_column("bracket_match_state", "scheduled_at")
