"""add upload source metadata to replay_files

Revision ID: d2e7b8a90f12
Revises: f1a2b3c4d5e6
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e7b8a90f12"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("replay_files", sa.Column("mac_id", sa.String(), nullable=True))
    op.add_column("replay_files", sa.Column("board_id", sa.String(), nullable=True))
    op.add_column("replay_files", sa.Column("uploader_name", sa.String(), nullable=True))
    op.add_column("replay_files", sa.Column("client_version", sa.String(), nullable=True))
    op.add_column("replay_files", sa.Column("source_tag", sa.String(), nullable=True))
    op.create_index("ix_replay_files_mac_id", "replay_files", ["mac_id"])
    op.create_index("ix_replay_files_board_id", "replay_files", ["board_id"])
    op.create_index(
        "ix_replay_files_uploader_name", "replay_files", ["uploader_name"]
    )


def downgrade() -> None:
    op.drop_index("ix_replay_files_uploader_name", table_name="replay_files")
    op.drop_index("ix_replay_files_board_id", table_name="replay_files")
    op.drop_index("ix_replay_files_mac_id", table_name="replay_files")
    op.drop_column("replay_files", "source_tag")
    op.drop_column("replay_files", "client_version")
    op.drop_column("replay_files", "uploader_name")
    op.drop_column("replay_files", "board_id")
    op.drop_column("replay_files", "mac_id")
