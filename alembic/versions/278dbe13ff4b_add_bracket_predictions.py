"""add bracket_predictions table

Revision ID: 278dbe13ff4b
Revises: e2f21c15866b
Create Date: 2026-08-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "278dbe13ff4b"
down_revision: Union[str, Sequence[str], None] = "e2f21c15866b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bracket_predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("predicted_winner", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["bracket_tournaments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bracket_predictions_tournament_id"),
        "bracket_predictions",
        ["tournament_id"],
    )
    op.create_index(
        op.f("ix_bracket_predictions_user_id"),
        "bracket_predictions",
        ["user_id"],
    )
    op.create_index(
        "uq_bracket_predictions_tournament_match_user",
        "bracket_predictions",
        ["tournament_id", "match_id", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_bracket_predictions_tournament_match_user",
        table_name="bracket_predictions",
    )
    op.drop_index(
        op.f("ix_bracket_predictions_user_id"), table_name="bracket_predictions"
    )
    op.drop_index(
        op.f("ix_bracket_predictions_tournament_id"), table_name="bracket_predictions"
    )
    op.drop_table("bracket_predictions")
