"""add bracket_summary_cache

Durable cache of the AI-generated post-game recap of one bracket set, keyed
on (tournament_id, stage) - the durable Tournament the bracket links its
games to, plus the bracket match id. Generation is a real, billed LLM call;
once written, a row is served on every subsequent request for that set.

Revision ID: a1f4c7d92b30
Revises: c8e52d3f1b60
Create Date: 2026-08-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1f4c7d92b30"
down_revision: Union[str, Sequence[str], None] = "c8e52d3f1b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bracket_summary_cache",
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("tournament_id", "stage"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("bracket_summary_cache")
