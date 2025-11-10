from sqlalchemy import create_engine, select, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, date
from db import (
    Base,
    ReplayFile,
    ParsedReplayJson,
    Match,
    MatchPlayer,
    GeneralModel,
    TeamModel,
    ObjectType,
    MatchPlayerAPM,
    MatchPlayerObject,
    MatchUpgradeEvent,
    MatchSpendingTimeline,
    MatchMoneyTimeline,
    MatchPlayerPower,
    General,
    Team,
    ProcessingStatus,
)
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, connection_string: str):
        """
        Initialize database connection.
        Example: DatabaseManager('postgresql://user:password@localhost:5432/cnc_stats')
        """
        con_str = connection_string.replace("postgres://", "postgresql://")
        self.engine = create_engine(con_str, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_all_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    def drop_all_tables(self):
        """Drop all tables - USE WITH CAUTION!"""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def initialize_lookup_tables(self):
        """Populate generals and teams lookup tables."""
        with self.get_session() as session:
            # Check if already populated
            if session.query(GeneralModel).count() > 0:
                return

            # Insert generals
            general_data = [
                (0, "USA", "USA"),
                (1, "AIR", "USA"),
                (2, "LASER", "USA"),
                (3, "SUPER", "USA"),
                (4, "CHINA", "CHINA"),
                (5, "NUKE", "CHINA"),
                (6, "TANK", "CHINA"),
                (7, "INFANTRY", "CHINA"),
                (8, "GLA", "GLA"),
                (9, "TOXIN", "GLA"),
                (10, "STEALTH", "GLA"),
                (11, "DEMO", "GLA"),
                (-1, "UNRECOGNIZED", "UNRECOGNIZED"),
            ]

            for gen_id, name, faction in general_data:
                session.add(GeneralModel(id=gen_id, name=name, faction=faction))

            # Insert teams
            team_data = [
                (0, "NONE"),
                (1, "ONE"),
                (2, "TWO"),
                (3, "THREE"),
                (4, "FOUR"),
                (-1, "OBSERVER"),
            ]

            for team_id, name in team_data:
                session.add(TeamModel(id=team_id, name=name))

    def refresh_materialized_views(self):
        """Refresh materialized views for aggregated stats."""
        with self.engine.connect() as conn:
            conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY player_general_stats")
            conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY map_stats_view")
            conn.commit()


class ReplayManager:
    """Repository for match-related operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_replay_file(self, url: str) -> ReplayFile | None:
        fetched = self.session.get(ReplayFile, url)
        return fetched

    def get_parsed_file(self, json_uri: str) -> ParsedReplayJson | None:
        fetched = self.session.get(ParsedReplayJson, json_uri)
        return fetched

    def register_replay(self, from_url: str, s3_uri: str) -> ReplayFile:
        """Register a new replay."""
        logger.info(f"Registering {from_url=} {s3_uri=}")
        prefix = "https://www.gentool.net/data/zh/"
        date_str = from_url.removeprefix(prefix).split("/")[0]
        date = datetime.strptime(date_str, "%Y_%m_%B")
        replay_file = ReplayFile(
            original_url=from_url,
            s3_uri=s3_uri,
            source_date=date,
        )
        self.session.add(replay_file)
        self.session.flush()
        self.session.commit()
        return replay_file

    def save_parsed_json(
        self,
        json_s3_uri: str,
        replay_id: int,
        original_replay_file_url: str,
        game_timestamp: datetime,
    ) -> ParsedReplayJson:
        """Save the result of parsing."""
        logger.info(
            f"Saving parsed json {replay_id=} {original_replay_file_url=} {json_s3_uri=} {game_timestamp=}"
        )
        game_date = (game_timestamp - timedelta(hours=5)).date()
        parsed_json = ParsedReplayJson(
            json_s3_uri=json_s3_uri,
            match_id=replay_id,
            replay_file_url=original_replay_file_url,
            game_timestamp=game_timestamp,
            game_date=game_date,
        )
        self.session.add(parsed_json)
        self.session.flush()
        replay_file = self.session.get(ReplayFile, original_replay_file_url)
        replay_file.status = ProcessingStatus.PARSED
        self.session.commit()
        return parsed_json

    def list_jsons(self, date: date | None = None) -> list[ParsedReplayJson]:
        """List all jsons or filter by date."""
        query = (
            self.session.query(ParsedReplayJson)
            .distinct(ParsedReplayJson.match_id)
            .order_by(ParsedReplayJson.match_id, ParsedReplayJson.game_timestamp)
        )
        if date:
            query.limit(ParsedReplayJson.game_date == date)
        return self.session.execute(query).scalars().all()

    def list_dates_with_games(self) -> list[date]:
        """Get the set of dates which have games."""

        stmt = select(ParsedReplayJson.game_date).distinct()
        unique_dates = self.session.execute(stmt).scalars().all()
        return unique_dates


class MatchRepository:
    """Repository for match-related operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_match(
        self,
        timestamp: datetime,
        map_name: str,
        winning_team: Team,
        duration_minutes: float,
        filename: str,
        incomplete: str = "",
        notes: str = "",
    ) -> Match:
        """Create a new match record."""
        match = Match(
            timestamp=timestamp,
            map=map_name,
            winning_team_id=winning_team.value,
            duration_minutes=duration_minutes,
            filename=filename,
            incomplete=incomplete,
            notes=notes,
        )
        self.session.add(match)
        self.session.flush()  # Get the match ID
        return match

    def add_player_to_match(
        self,
        match: Match,
        player_name: str,
        general: General,
        team: Team,
        color: str,
        is_winner: bool,
    ) -> MatchPlayer:
        """Add a player to a match."""
        player = MatchPlayer(
            match_id=match.id,
            player_name=player_name,
            general_id=general.value,
            team_id=team.value,
            color=color,
            is_winner=is_winner,
        )
        self.session.add(player)
        return player

    def add_apm_data(
        self,
        match: Match,
        player_name: str,
        action_count: int,
        minutes: float,
        apm: float,
    ):
        """Add APM data for a player in a match."""
        apm_record = MatchPlayerAPM(
            match_id=match.id,
            player_name=player_name,
            action_count=action_count,
            minutes=minutes,
            apm=apm,
        )
        self.session.add(apm_record)

    def get_or_create_object_type(self, name: str, category: str) -> ObjectType:
        """Get existing object type or create new one."""
        obj_type = self.session.query(ObjectType).filter_by(name=name).first()
        if not obj_type:
            obj_type = ObjectType(name=name, category=category)
            self.session.add(obj_type)
            self.session.flush()
        return obj_type

    def add_player_objects(
        self,
        match: Match,
        player_name: str,
        objects: Dict[str, Dict[str, int]],
        category: str,
    ):
        """Add built objects (units/buildings/upgrades) for a player."""
        for obj_name, stats in objects.items():
            obj_type = self.get_or_create_object_type(obj_name, category)
            record = MatchPlayerObject(
                match_id=match.id,
                player_name=player_name,
                object_type_id=obj_type.id,
                count=stats.get("Count", 0),
                total_spent=stats.get("TotalSpent", 0),
            )
            self.session.add(record)

    def add_upgrade_event(
        self,
        match: Match,
        player_name: str,
        upgrade_name: str,
        timecode: int,
        cost: int,
        at_minute: float,
    ):
        """Add an upgrade event."""
        event = MatchUpgradeEvent(
            match_id=match.id,
            player_name=player_name,
            upgrade_name=upgrade_name,
            timecode=timecode,
            cost=cost,
            at_minute=at_minute,
        )
        self.session.add(event)

    def add_spending_timeline(
        self,
        match: Match,
        player_name: str,
        at_minute: float,
        category: str,
        accumulated_cost: int,
    ):
        """Add spending timeline entry."""
        entry = MatchSpendingTimeline(
            match_id=match.id,
            player_name=player_name,
            at_minute=at_minute,
            category=category.upper(),
            accumulated_cost=accumulated_cost,
        )
        self.session.add(entry)

    def add_money_timeline(
        self,
        match: Match,
        timecode: int,
        player_name: str,
        money_value: int,
    ):
        """Add money timeline entry."""
        entry = MatchMoneyTimeline(
            match_id=match.id,
            timecode=timecode,
            player_name=player_name,
            money_value=money_value,
        )
        self.session.add(entry)

    def add_power_usage(
        self,
        match: Match,
        player_name: str,
        power_name: str,
        use_count: int,
    ):
        """Add power usage record."""
        power = MatchPlayerPower(
            match_id=match.id,
            player_name=player_name,
            power_name=power_name,
            use_count=use_count,
        )
        self.session.add(power)

    def get_match_by_id(self, match_id: int) -> Optional[Match]:
        """Get a match by ID with all related data."""
        return self.session.query(Match).filter_by(id=match_id).first()

    def get_recent_matches(self, limit: int = 10) -> List[Match]:
        """Get most recent matches."""
        return (
            self.session.query(Match)
            .order_by(Match.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_matches_by_player(self, player_name: str) -> List[Match]:
        """Get all matches for a specific player."""
        return (
            self.session.query(Match)
            .join(MatchPlayer)
            .filter(MatchPlayer.player_name == player_name)
            .order_by(Match.timestamp.desc())
            .all()
        )

    def get_matches_by_map(self, map_name: str) -> List[Match]:
        """Get all matches on a specific map."""
        return (
            self.session.query(Match)
            .filter(Match.map == map_name)
            .order_by(Match.timestamp.desc())
            .all()
        )


class StatsRepository:
    """Repository for statistics queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_player_stats(self, player_name: str) -> Dict:
        """Get comprehensive stats for a player."""
        # Win/Loss by general
        general_stats = (
            self.session.query(
                GeneralModel.name,
                func.count().filter(MatchPlayer.is_winner == True).label("wins"),
                func.count().filter(MatchPlayer.is_winner == False).label("losses"),
            )
            .join(MatchPlayer, GeneralModel.id == MatchPlayer.general_id)
            .filter(MatchPlayer.player_name == player_name)
            .group_by(GeneralModel.name)
            .all()
        )

        # Average APM
        avg_apm = (
            self.session.query(func.avg(MatchPlayerAPM.apm))
            .filter(MatchPlayerAPM.player_name == player_name)
            .scalar()
        )

        # Total games
        total_games = (
            self.session.query(func.count(MatchPlayer.id))
            .filter(MatchPlayer.player_name == player_name)
            .scalar()
        )

        return {
            "player_name": player_name,
            "total_games": total_games,
            "avg_apm": round(avg_apm, 2) if avg_apm else 0,
            "general_stats": [
                {
                    "general": name,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(wins / (wins + losses) * 100, 2)
                    if (wins + losses) > 0
                    else 0,
                }
                for name, wins, losses in general_stats
            ],
        }

    def get_leaderboard(self, min_games: int = 10) -> List[Dict]:
        """Get player leaderboard by win rate."""
        results = (
            self.session.query(
                MatchPlayer.player_name,
                func.count().filter(MatchPlayer.is_winner == True).label("wins"),
                func.count().filter(MatchPlayer.is_winner == False).label("losses"),
                func.count().label("total_games"),
                func.avg(MatchPlayerAPM.apm).label("avg_apm"),
            )
            .outerjoin(
                MatchPlayerAPM,
                and_(
                    MatchPlayer.match_id == MatchPlayerAPM.match_id,
                    MatchPlayer.player_name == MatchPlayerAPM.player_name,
                ),
            )
            .group_by(MatchPlayer.player_name)
            .having(func.count() >= min_games)
            .all()
        )

        leaderboard = []
        for player_name, wins, losses, total, avg_apm in results:
            win_rate = (wins / total * 100) if total > 0 else 0
            leaderboard.append(
                {
                    "player_name": player_name,
                    "wins": wins,
                    "losses": losses,
                    "total_games": total,
                    "win_rate": round(win_rate, 2),
                    "avg_apm": round(avg_apm, 2) if avg_apm else 0,
                }
            )

        return sorted(leaderboard, key=lambda x: x["win_rate"], reverse=True)

    def get_general_winrates(self) -> List[Dict]:
        """Get win rates for each general."""
        results = (
            self.session.query(
                GeneralModel.name,
                func.count().filter(MatchPlayer.is_winner == True).label("wins"),
                func.count().filter(MatchPlayer.is_winner == False).label("losses"),
            )
            .join(MatchPlayer, GeneralModel.id == MatchPlayer.general_id)
            .group_by(GeneralModel.name)
            .all()
        )

        return [
            {
                "general": name,
                "wins": wins,
                "losses": losses,
                "total_games": wins + losses,
                "win_rate": round(wins / (wins + losses) * 100, 2)
                if (wins + losses) > 0
                else 0,
            }
            for name, wins, losses in results
        ]

    def get_map_stats(self) -> List[Dict]:
        """Get statistics for each map."""
        results = (
            self.session.query(
                Match.map,
                func.count().label("games_played"),
                func.avg(Match.duration_minutes).label("avg_duration"),
            )
            .group_by(Match.map)
            .all()
        )

        return [
            {
                "map": map_name,
                "games_played": games,
                "avg_duration": round(duration, 2) if duration else 0,
            }
            for map_name, games, duration in results
        ]
