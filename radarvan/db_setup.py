"""(Re)create the database tables and seed them from a local replay JSON dump.

Run as a script (``python -m radarvan.db_setup``) to create all tables and, if
``replay_json_dump.json`` is present, restore parsed-replay records from it.
"""

import json
from .db_utils import DatabaseManager, ReplayManager
import os
from pathlib import Path
from datetime import datetime

import structlog
from tqdm import tqdm

logger = structlog.get_logger(__name__)

# Initialize database connection (do this once at application startup)
constring = os.getenv("DATABASE_URL")
if constring is None:
    raise RuntimeError("DATABASE_URL environment variable is not set")
db_manager = DatabaseManager(constring)


def restore_jsons() -> None:
    replay_dump_path = Path("./replay_json_dump.json")
    if not replay_dump_path.exists():
        return
    parsed = json.loads(replay_dump_path.read_text())
    logger.info("loaded replay dump", count=len(parsed), path=str(replay_dump_path))
    date_format = "%Y-%m-%dT%H:%M:%S"
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(session, auto_commit=False, notify=False)
        for r in tqdm(parsed):
            replay_manager.save_parsed_json(  # type: ignore[call-arg]  # see mypy_errors.md
                json_s3_uri=r["json_s3_uri"],
                replay_id=r["match_id"],
                original_replay_file_url=r["replay_file_url"],
                # game_timestamp is a naive `DateTime` column by design (db.py); keep it naive.
                game_timestamp=datetime.strptime(  # noqa: DTZ007
                    r["game_timestamp"], date_format
                ),
            )
        session.flush()
        session.commit()


def setup_database() -> None:
    """Run this once to set up your database."""

    # Drop all
    # print("droping tables")
    # db_manager.drop_all_tables()
    logger.info("dropped tables")
    # Create all tables
    db_manager.create_all_tables()
    logger.info("created tables")

    restore_jsons()
    logger.info("Database setup complete!")


if __name__ == "__main__":
    setup_database()
