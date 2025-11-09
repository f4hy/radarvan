from typing import List, Dict, Optional
from datetime import datetime, timedelta
from db_utils import DatabaseManager, MatchRepository, StatsRepository
from db import General, Team, Match
import os

# Initialize database connection (do this once at application startup)
constring = os.getenv("DATABASE_URL")
print("!!", constring)
db_manager = DatabaseManager(constring)


def setup_database():
    """Run this once to set up your database."""

    # Drop all
    db_manager.drop_all_tables()
    # Create all tables
    db_manager.create_all_tables()

    # Initialize lookup tables (generals, teams)
    db_manager.initialize_lookup_tables()

    print("Database setup complete!")


if __name__ == "__main__":
    setup_database()
