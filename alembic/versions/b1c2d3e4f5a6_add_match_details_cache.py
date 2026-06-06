"""add match_details_cache

Durable, versioned cache of the derived MatchDetails wire shape. The raw
cncstats JSON stays in S3; only the small owned projection is persisted here.

Revision ID: b1c2d3e4f5a6
Revises: e3f4a5b6c7d8
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "match_details_cache",
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("match_id"),
    )
    op.create_index(
        "ix_match_details_cache_version",
        "match_details_cache",
        ["version"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_match_details_cache_version",
        table_name="match_details_cache",
    )
    op.drop_table("match_details_cache")
