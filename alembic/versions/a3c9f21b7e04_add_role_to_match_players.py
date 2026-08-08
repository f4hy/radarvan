"""add role to match_players

Nullable on purpose: existing rows are backfilled from the stored replay JSON
(POST /api/backfill_player_roles/) rather than in this migration, and readers
fall back to a name-based guess while role IS NULL. Tighten to NOT NULL in a
follow-up once the backfill has drained.

Revision ID: a3c9f21b7e04
Revises: 278dbe13ff4b
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c9f21b7e04'
down_revision: Union[str, Sequence[str], None] = '278dbe13ff4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('match_players', sa.Column('role', sa.SmallInteger(), nullable=True))
    # The backfill walks rows with role IS NULL; without this it's a seq scan
    # over every match_player on each batch.
    op.create_index(
        'ix_match_players_role_null',
        'match_players',
        ['match_id'],
        postgresql_where=sa.text('role IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_match_players_role_null', table_name='match_players')
    op.drop_column('match_players', 'role')
