"""add match_blurb_cache

Durable store of the LLM-written blurb for one interesting match, keyed on the
match id. Additive, so it is safe to apply while the old dynos still serve.

Revision ID: d4e7a19c3b62
Revises: b2c9e0a4d715
Create Date: 2026-09-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e7a19c3b62"
down_revision: Union[str, Sequence[str], None] = "b2c9e0a4d715"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "match_blurb_cache",
        sa.Column("match_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("blurb", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("match_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("match_blurb_cache")
