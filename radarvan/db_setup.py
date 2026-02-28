import json
from db_utils import DatabaseManager, ReplayManager
import os
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Initialize database connection (do this once at application startup)
constring = os.getenv("DATABASE_URL")
print("!!", constring)
db_manager = DatabaseManager(constring)


def restore_replay_files() -> None:
    replay_dump_path = Path("./file_dump.json")
    if not replay_dump_path.exists():
        return
    parsed = json.loads(replay_dump_path.read_text())
    print(f"loaded {len(parsed)} from {replay_dump_path}")
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(session, auto_commit=False, notify=False)
        for r in tqdm(parsed):
            from_url = r["original_url"]
            s3_uri = r["s3_uri"]
            replay_manager.register_replay(
                from_url,
                s3_uri,
            )
        session.flush()
        session.commit()


def restore_jsons() -> None:
    replay_dump_path = Path("./replay_json_dump.json")
    if not replay_dump_path.exists():
        return
    parsed = json.loads(replay_dump_path.read_text())
    print(f"loaded {len(parsed)} from {replay_dump_path}")
    date_format = "%Y-%m-%dT%H:%M:%S"
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(session, auto_commit=False, notify=False)
        for r in tqdm(parsed):
            replay_manager.save_parsed_json(
                json_s3_uri=r["json_s3_uri"],
                replay_id=r["match_id"],
                original_replay_file_url=r["replay_file_url"],
                game_timestamp=datetime.strptime(r["game_timestamp"], date_format),
            )
        session.flush()
        session.commit()


def setup_database() -> None:
    """Run this once to set up your database."""

    # Drop all
    print("droping tables")
    db_manager.drop_all_tables()
    print("droped tables")
    # Create all tables
    db_manager.create_all_tables()
    print("created tables")

    restore_replay_files()
    restore_jsons()
    print("Database setup complete!")


if __name__ == "__main__":
    setup_database()
