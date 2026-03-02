"""add date_computed to tournament_stats

Revision ID: c3d8a1f92e05
Revises: b7e9f3a24c81
Create Date: 2026-03-02 00:01:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d8a1f92e05"
down_revision: Union[str, Sequence[str], None] = "b7e9f3a24c81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "tournament_stats", sa.Column("date_computed", sa.Date(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tournament_stats", "date_computed")
