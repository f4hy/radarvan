"""add crc column to map_data

Stores the game map CRC (uppercase hex, matching the replay header MapCRC) so we
can register maps with / look them up on cncstats without a replay in hand.

Revision ID: b2c3d4e5f6a7
Revises: a8b9c0d1e2f3
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("map_data", sa.Column("crc", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("map_data", "crc")
