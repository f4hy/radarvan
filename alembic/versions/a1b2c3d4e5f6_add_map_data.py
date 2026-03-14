"""add map_data table

Revision ID: a1b2c3d4e5f6
Revises: 8da58256e2e7
Create Date: 2026-03-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8da58256e2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'map_data',
        sa.Column('map_name', sa.String(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('map_name'),
    )


def downgrade() -> None:
    op.drop_table('map_data')
