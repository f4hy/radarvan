import logging
from itertools import combinations, permutations
from player_ids import player_name_map
from datetime import date
from pydantic import BaseModel
from typing import DefaultDict, Sequence
from collections import defaultdict
from api_types import (
    MatchInfo,
    Matchup,
    Team,
    Player,
    Tournament,
    MatchupResult,
    TournamentResult,
    WinLoss,
)

logger = logging.getLogger(__name__)


def sorted_tuple(s: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(s))


TOURNAMENTS = [
    Tournament(
        name="2025_2v2_tournament",
        start_date=date(2025, 11, 1),
        end_date=date(2026, 2, 1),
        teams=[
            sorted_tuple(["Syn", "WildCard"]),
            sorted_tuple(["OneThree111", "Pancake"]),
            sorted_tuple(["Neo", "CoreDawg"]),
            sorted_tuple(["STM", "Skip"]),
            sorted_tuple(["WildCard", "Syn"]),
            sorted_tuple(["Gorn", "EnragedFerret"]),
            sorted_tuple(["Modus", "Tytan"]),
        ],
        total_games_played_per_team=30,
    )
]

TOURNAMENT_MAP = {t.name: t for t in TOURNAMENTS}


def overrides_for_tournament(tournament_id: str) -> list[MatchupResult]:
    """Overrides in case matchupes were not recorred, e.g. missing from gentool uploade."""

    logger.info(f"Getting overrides for {tournament_id}")
    if tournament_id == "2025_2v2_tournament":
        logger.warning("pancake+131 vs Neo and Coredawg was not uploaded to gentool")
        return [
            # MatchupResult(
            #     tournament_name="205_2v2_tournament",
            #     matches=[],  # missing
            #     outcome={
            #         sorted_tuple(["OneThree111", "Pancake"]): WinLoss(wins=4, losses=2),
            #         sorted_tuple(["Neo", "CoreDawg"]): WinLoss(wins=2, losses=4),
            #     },
            #     override="Matches not uploaded to gentool results manually added",
            # )
        ]
    return []


def is_tournament_game(match_info: MatchInfo) -> str | None:
    if match_info.incomplete:
        return None
    gamedate = match_info.timestamp.date()
    team_map: DefaultDict[Team, set[str]] = defaultdict(set)
    for p in match_info.players:
        if p.team == Team.OBSERVER:
            continue
        team_map[p.team].add(player_name_map(p.name))

    teams = {sorted_tuple(t) for t in team_map.values()}

    if len(team_map) != 2:
        return None

    for tournament in TOURNAMENTS:
        if gamedate > tournament.end_date or gamedate < tournament.start_date:
            continue
        if teams.issubset(set(tournament.teams)):
            return tournament.name


def tournament_games(matches: list[MatchInfo]) -> dict[str, list[MatchInfo]]:
    """For each tournament return the list of matches in that tournament."""

    games: dict[str, list[MatchInfo]] = defaultdict(list)
    for m in matches:
        # if m.id != 1619771421:
        #     continue
        if m.id == 437356734:
            logger.warning("Skipping wanmup game")
            continue
        tournament = is_tournament_game(m)
        if tournament:
            games[tournament].append(m)
    return games


def winning_team(m: MatchInfo, tournament: Tournament) -> frozenset[str]:
    for p in m.players:
        if p.team == m.winning_team:
            for team in tournament.teams:
                if player_name_map(p.name) in team:
                    return team
    raise ValueError("Winner not in tournament")


def create_tournament_results(
    tournament_matches: dict[str, list[MatchInfo]],
) -> list[TournamentResult]:
    """
    Convert a dictionary of tournament matches to TournamentResult objects.
    """
    results = []

    for tournament_name, matches in tournament_matches.items():
        if tournament_name not in TOURNAMENT_MAP:
            continue

        tournament = TOURNAMENT_MAP[tournament_name]

        # Build team records
        team_records: dict[tuple[str, ...], WinLoss] = {}

        # Initialize records for all tournament teams
        for team in tournament.teams:
            team_records[team] = WinLoss(wins=0, losses=0)

        # Group matches by team matchup
        matchup_dict: dict[frozenset[tuple[str, ...]], list[MatchInfo]] = {}

        for match in matches:
            # Group players by team
            teams_in_match: dict[Team, set[str]] = {}
            for player in match.players:
                if player.team == Team.OBSERVER:
                    continue
                if player.team not in teams_in_match:
                    teams_in_match[player.team] = set()
                teams_in_match[player.team].add(player_name_map(player.name))

            # Convert to sorted tuples
            team_tuples = [
                tuple(sorted(players)) for players in teams_in_match.values()
            ]

            # Create matchup key (frozenset of team tuples)
            matchup_key = frozenset(team_tuples)

            if matchup_key not in matchup_dict:
                matchup_dict[matchup_key] = []
            matchup_dict[matchup_key].append(match)

        # Create MatchupResult objects
        matchups = []
        for matchup_teams, matchup_matches in matchup_dict.items():
            # Calculate outcome for each team in this matchup
            outcome: dict[tuple[str, ...], WinLoss] = {}

            for team in matchup_teams:
                outcome[team] = WinLoss(wins=0, losses=0)

            # Count wins/losses for each team in this specific matchup
            for match in matchup_matches:
                teams_in_match: dict[Team, set[str]] = {}
                for player in match.players:
                    if player.team == Team.OBSERVER:
                        continue
                    if player.team not in teams_in_match:
                        teams_in_match[player.team] = set()
                    teams_in_match[player.team].add(player_name_map(player.name))

                for team_enum, player_set in teams_in_match.items():
                    team_tuple = tuple(sorted(player_set))
                    if team_enum == match.winning_team:
                        outcome[team_tuple].wins += 1
                        team_records[team_tuple].wins += 1
                    else:
                        outcome[team_tuple].losses += 1
                        team_records[team_tuple].losses += 1

            matchup_result = MatchupResult(
                tournament_name=tournament_name,
                matches=matchup_matches,
                outcome=outcome,
            )
            matchups.append(matchup_result)

        overrides = overrides_for_tournament(tournament.name)
        if overrides:
            matchups.extend(overrides)
            for m in overrides:
                for team, wl in m.outcome.items():
                    team_records[team].wins += wl.wins
                    team_records[team].losses += wl.losses

        all_matchups = [
            Matchup(team1=i, team2=j, played=False)
            for i, j in combinations(tournament.teams, 2)
            if i != j
        ]
        logger.info(
            f"all matchesup {len(all_matchups)} {[(m.team1, m.team2) for m in all_matchups]}"
        )
        for i in all_matchups:
            logger.info(f"M {i}")

        for ms in all_matchups:
            found = False
            for m in matchups:
                logger.info(
                    f" outcome {set(m.outcome.keys())} compared to {set([ms.team1, ms.team2])}"
                )
                if set(m.outcome.keys()) == set([ms.team1, ms.team2]):
                    found = True
            if not found:
                matchups.append(
                    MatchupResult(
                        tournament_name=tournament_name,
                        matches=[],
                        outcome={
                            ms.team1: WinLoss(wins=0, losses=0),
                            ms.team2: WinLoss(wins=0, losses=0),
                        },
                        override="not played yet",
                    )
                )

        sorted_team_records = sorted(
            team_records.items(), key=lambda item: item[1].wins, reverse=True
        )

        result = TournamentResult(
            tournament=tournament,
            matchups=matchups,
            records=dict(sorted_team_records),
        )

        results.append(result)

    return results
