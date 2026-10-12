"""drop duplicate indexes, add matches.json_s3_uri index

Every dropped index is a twin of a primary key / unique index on the same
columns, or a leading-column prefix of one, so no query loses its access path.
Safe to apply while the old dynos still serve: nothing references index names.

Revision ID: 98f1f5782ef6
Revises: d4e7a19c3b62
Create Date: 2026-10-12 00:11:54.752356

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "98f1f5782ef6"
down_revision: Union[str, Sequence[str], None] = "d4e7a19c3b62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_matches_json_s3_uri", "matches", ["json_s3_uri"])
    op.drop_index("ix_replay_files_original_url", table_name="replay_files")
    op.drop_constraint("uq_replay_files_file_hash", "replay_files", type_="unique")
    op.drop_index("ix_users_discord_id", table_name="users")
    op.drop_index("ix_users_player_name", table_name="users")
    op.drop_index("ix_map_votes_user_id", table_name="map_votes")
    op.drop_index("idx_map_votes_user_count", table_name="map_votes")
    op.drop_index("ix_tournament_games_tournament_id", table_name="tournament_games")
    op.drop_index("ix_bracket_players_tournament_id", table_name="bracket_players")
    op.drop_index(
        "ix_bracket_predictions_tournament_id", table_name="bracket_predictions"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(
        "ix_bracket_predictions_tournament_id", "bracket_predictions", ["tournament_id"]
    )
    op.create_index(
        "ix_bracket_players_tournament_id", "bracket_players", ["tournament_id"]
    )
    op.create_index(
        "ix_tournament_games_tournament_id", "tournament_games", ["tournament_id"]
    )
    op.create_index(
        "idx_map_votes_user_count", "map_votes", ["user_id", "player_count"]
    )
    op.create_index("ix_map_votes_user_id", "map_votes", ["user_id"])
    op.create_index("ix_users_player_name", "users", ["player_name"])
    op.create_index("ix_users_discord_id", "users", ["discord_id"])
    op.create_unique_constraint(
        "uq_replay_files_file_hash", "replay_files", ["file_hash"]
    )
    op.create_index(
        "ix_replay_files_original_url", "replay_files", ["original_url"], unique=True
    )
    op.drop_index("ix_matches_json_s3_uri", table_name="matches")
