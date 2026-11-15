"""add match_netstats

Per-match summary of the clients' netstats logs, keyed on the match id.
Additive, so it is safe to apply while the old dynos still serve.

Revision ID: c3e8a1f04b27
Revises: 98f1f5782ef6
Create Date: 2026-11-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3e8a1f04b27"
down_revision: Union[str, Sequence[str], None] = "98f1f5782ef6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "match_netstats",
        sa.Column("match_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("parser_version", sa.Integer(), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("match_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("match_netstats")
