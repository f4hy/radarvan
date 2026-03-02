"""add computed statistics table

Revision ID: b7e9f3a24c81
Revises: 097c42609dea
Create Date: 2026-03-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7e9f3a24c81"
down_revision: Union[str, Sequence[str], None] = "097c42609dea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "computed_statistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stat_name", sa.String(), nullable=False),
        sa.Column("value_float", sa.Float(), nullable=True),
        sa.Column("value_str", sa.String(), nullable=True),
        sa.Column("player", sa.String(), nullable=True),
        sa.Column("match_id", sa.Integer(), nullable=True),
        sa.Column("date_computed", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_computed_statistics_date_computed",
        "computed_statistics",
        ["date_computed"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_computed_statistics_date_computed", table_name="computed_statistics"
    )
    op.drop_table("computed_statistics")
