"""add users table

Discord-authenticated community members. `discord_id` is the login identity;
`player_name` (nullable, unique) is the in-game name claimed on first login.

Revision ID: f7a1c2d3e4b5
Revises: b1c2d3e4f5a6
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a1c2d3e4b5"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discord_id", sa.String(), nullable=False),
        sa.Column("discord_username", sa.String(), nullable=False),
        sa.Column("discord_avatar", sa.String(), nullable=True),
        sa.Column("player_name", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discord_id"),
        sa.UniqueConstraint("player_name"),
    )
    op.create_index("ix_users_discord_id", "users", ["discord_id"])
    op.create_index("ix_users_player_name", "users", ["player_name"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_player_name", table_name="users")
    op.drop_index("ix_users_discord_id", table_name="users")
    op.drop_table("users")
