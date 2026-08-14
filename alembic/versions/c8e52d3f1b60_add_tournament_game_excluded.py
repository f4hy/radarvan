"""add tournament_games.excluded tombstone flag

Deleting a link can't express "this match is not a tournament game" - the
detector would recreate it on the next run. An excluded row is a manual
row that reads skip, replacing the hard-coded warmup match id that used to
live in tournament.tournament_games().

Revision ID: c8e52d3f1b60
Revises: b7d41c2e9a58
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8e52d3f1b60"
down_revision: Union[str, Sequence[str], None] = "b7d41c2e9a58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "tournament_games",
        sa.Column(
            "excluded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tournament_games", "excluded")
