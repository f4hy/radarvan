"""add file_hash to replay_files

Revision ID: f1a2b3c4d5e6
Revises: aedc02025d51
Create Date: 2026-04-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'aedc02025d51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('replay_files', sa.Column('file_hash', sa.String(64), nullable=True))
    op.create_unique_constraint('uq_replay_files_file_hash', 'replay_files', ['file_hash'])
    op.create_index('ix_replay_files_file_hash', 'replay_files', ['file_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_replay_files_file_hash', table_name='replay_files')
    op.drop_constraint('uq_replay_files_file_hash', 'replay_files', type_='unique')
    op.drop_column('replay_files', 'file_hash')
