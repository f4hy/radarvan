"""add zulu_build and is_dev flags

Revision ID: e3f4a5b6c7d8
Revises: d2e7b8a90f12
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e7b8a90f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("replay_files", sa.Column("zulu_build", sa.String(), nullable=True))
    op.add_column(
        "replay_files",
        sa.Column(
            "is_dev",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_replay_files_is_dev", "replay_files", ["is_dev"])
    op.add_column(
        "matches",
        sa.Column(
            "is_dev",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_matches_is_dev", "matches", ["is_dev"])


def downgrade() -> None:
    op.drop_index("ix_matches_is_dev", table_name="matches")
    op.drop_column("matches", "is_dev")
    op.drop_index("ix_replay_files_is_dev", table_name="replay_files")
    op.drop_column("replay_files", "is_dev")
    op.drop_column("replay_files", "zulu_build")
