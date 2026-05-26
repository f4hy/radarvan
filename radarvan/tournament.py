import statistics
from collections import Counter
import structlog
from itertools import combinations
from .player_ids import resolve_player_name
from datetime import date
from collections.abc import Sequence
from collections import defaultdict
from .api_types import (
    MatchDetails,
    MatchInfo,
    Matchup,
    Team,
    General,
    Tournament,
    MatchupResult,
    TournamentResult,
    WinLoss,
    TournamentReport,
    Statistic,
)

logger = structlog.get_logger(__name__)


def sorted_tuple(s: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(s))


TOURNAMENTS = [
    Tournament(
        name="2025_2v2_tournament",
        start_date=date(2025, 11, 1),
        end_date=date(2026, 1, 25),
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

    logger.info("getting overrides", tournament_id=tournament_id)
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
    if match_info.composition and not match_info.composition.is_team_game:
        return None
    gamedate = match_info.timestamp.date()
    team_map: defaultdict[Team, set[str]] = defaultdict(set)
    for p in match_info.players:
        if not p.is_real():
            continue
        team_map[p.team].add(resolve_player_name(p.name, p.color))

    teams = {sorted_tuple(list(t)) for t in team_map.values()}

    if len(team_map) != 2:
        return None

    for tournament in TOURNAMENTS:
        if gamedate > tournament.end_date or gamedate < tournament.start_date:
            continue
        if teams.issubset(set(tournament.teams)):
            return tournament.name
    return None


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


def winning_team(m: MatchInfo, tournament: Tournament) -> tuple[str, ...]:
    for p in m.players:
        if p.won:
            for team in tournament.teams:
                if resolve_player_name(p.name, p.color) in team:
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
                if not player.is_real():
                    continue
                if player.team not in teams_in_match:
                    teams_in_match[player.team] = set()
                teams_in_match[player.team].add(
                    resolve_player_name(player.name, player.color)
                )

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
                teams_in_match = {}
                player_won: dict[str, bool] = {}
                for player in match.players:
                    if not player.is_real():
                        continue
                    if player.team not in teams_in_match:
                        teams_in_match[player.team] = set()
                    name = resolve_player_name(player.name, player.color)
                    teams_in_match[player.team].add(name)
                    player_won[name] = player.won

                for team_enum, player_set in teams_in_match.items():
                    team_tuple = tuple(sorted(player_set))
                    if team_tuple not in team_records:
                        logger.warning(
                            "skipping unrecognized team in match",
                            match_id=match.id,
                            team=team_tuple,
                        )
                        continue
                    if any(player_won.get(name, False) for name in player_set):
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
        logger.debug(
            "all matchups",
            count=len(all_matchups),
            matchups=[(m.team1, m.team2) for m in all_matchups],
        )
        for i in all_matchups:
            logger.debug("matchup", matchup=i)

        for ms in all_matchups:
            found = False
            for m in matchups:
                logger.debug(
                    "comparing outcome",
                    outcome=set(m.outcome.keys()),
                    teams={ms.team1, ms.team2},
                )
                if set(m.outcome.keys()) == {ms.team1, ms.team2}:
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

        complete = (
            min(r.wins + r.losses for (_, r) in sorted_team_records)
            == tournament.total_games_played_per_team
        )

        result = TournamentResult(
            tournament=tournament,
            matchups=matchups,
            records=dict(sorted_team_records),
            complete=complete,
        )

        results.append(result)

    return results


def highest_apm(matches: list[MatchDetails], computed_at: date) -> Statistic:
    highest_apm_match = max(
        (m for m in matches if m.apms), key=lambda x: max(a.apm for a in x.apms)
    )
    highest_apm = max((a for a in highest_apm_match.apms), key=lambda x: x.apm)
    return Statistic(
        stat_name="Highest APM",
        value=round(highest_apm.apm, 2),
        player=resolve_player_name(highest_apm.player_name),
        match_id=highest_apm_match.match_id,
        date_computed=computed_at,
    )


def highest_ave_apm(matches: list[MatchDetails], computed_at: date) -> Statistic:
    player_apms: dict[str, list[float]] = defaultdict(list)
    for m in matches:
        if not m.apms:
            continue
        for a in m.apms:
            player_apms[resolve_player_name(a.player_name)].append(a.apm)

    averages = {p: statistics.mean(v) for p, v in player_apms.items()}
    player, max_ave = max(averages.items(), key=lambda x: x[1])
    return Statistic(
        stat_name="Highest Average APM",
        value=round(max_ave, 2),
        player=resolve_player_name(player),
        date_computed=computed_at,
    )


def faction_stats(matches: list[MatchInfo], computed_at: date) -> list[Statistic]:
    all_zeros = Counter({General(i): 0 for i in range(12)})
    generals_played = (
        Counter(p.general for m in matches for p in m.players if p.team > 0) + all_zeros
    )
    generals_won = (
        Counter(p.general for m in matches for p in m.players if p.won) + all_zeros
    )

    most_played, most_count = generals_played.most_common(1)[0]
    most_won, most_won_count = generals_won.most_common(1)[0]
    fewest_played, fewest_count = min(generals_played.items(), key=lambda x: x[1])
    fewest_won, fewest_won_count = min(generals_won.items(), key=lambda x: x[1])

    ratios = {k: generals_won[k] / (generals_played[k] or 1) for k in generals_played}

    highest_win_rate_gen, highest_win_rate = max(ratios.items(), key=lambda x: x[1])
    lowest_win_rate_gen, lowest_win_rate = min(ratios.items(), key=lambda x: x[1])

    return [
        Statistic(
            stat_name="Most played general",
            value=most_count,
            player=General(most_played).name,
            date_computed=computed_at,
        ),
        Statistic(
            stat_name="Least played general",
            value=fewest_count,
            player=General(fewest_played).name,
            date_computed=computed_at,
        ),
        Statistic(
            stat_name="General with most wins",
            value=most_won_count,
            player=General(most_won).name,
            date_computed=computed_at,
        ),
        Statistic(
            stat_name="General with fewest wins",
            value=fewest_won_count,
            player=General(fewest_won).name,
            date_computed=computed_at,
        ),
        Statistic(
            stat_name="General best win rate",
            value=round(highest_win_rate, 3),
            player=General(highest_win_rate_gen).name,
            date_computed=computed_at,
        ),
        Statistic(
            stat_name="General lowest win rate",
            value=round(lowest_win_rate, 3),
            player=General(lowest_win_rate_gen).name,
            date_computed=computed_at,
        ),
    ]


def unit_stats(matches: list[MatchDetails], computed_at: date) -> list[Statistic]:
    units_created = [s.UnitsCreated for m in matches for s in m.player_summary]
    mapped = [{c.split("_")[-1]: v.Count} for d in units_created for c, v in d.items()]
    unit_counts = sum((Counter(d) for d in mapped), Counter())

    return [
        Statistic(
            stat_name="Unit built",
            value=v,
            player=c,
            date_computed=computed_at,
        )
        for c, v in unit_counts.most_common()
    ]


def building_stats(matches: list[MatchDetails], computed_at: date) -> list[Statistic]:
    buildings_created = [s.BuildingsBuilt for m in matches for s in m.player_summary]
    mapped = [
        {c.split("_")[-1]: v.Count} for d in buildings_created for c, v in d.items()
    ]
    building_counts = sum((Counter(d) for d in mapped), Counter())

    return [
        Statistic(
            stat_name="Building built",
            value=v,
            player=c,
            date_computed=computed_at,
        )
        for c, v in building_counts.most_common()
    ]


def earlest_first_blood(matches: list[MatchDetails], computed_at: date) -> Statistic:
    earliest = min(
        (m for m in matches if m.first_blood),
        key=lambda x: x.first_blood.atMinute,  # type: ignore[union-attr]
    )
    if earliest.first_blood is None:
        raise RuntimeError(
            "earliest match has no first_blood despite being filtered for it"
        )
    return Statistic(
        stat_name="Earliest First Blood",
        value=f"{earliest.first_blood.atMinute:.2f}m",
        player=resolve_player_name(earliest.first_blood.attacker),
        match_id=earliest.match_id,
        date_computed=computed_at,
    )


def most_first_bloods(matches: list[MatchDetails], computed_at: date) -> Statistic:
    counter = Counter(
        resolve_player_name(m.first_blood.attacker) for m in matches if m.first_blood
    )
    most, count = counter.most_common(1)[0]
    return Statistic(
        stat_name="Most First Bloods",
        value=count,
        player=most,
        date_computed=computed_at,
    )


def last_val(d: dict[float, dict[str, int]]) -> dict[str, int]:
    last = next(reversed(d.values()))
    name_mapped = {resolve_player_name(k): v for k, v in last.items()}
    return name_mapped


def min_max_stats(matches: list[MatchDetails], computed_at: date) -> list[Statistic]:
    data_types = [
        "xp",
        "units_built",
        "units_lost",
        "buildings_built",
        "buildings_lost",
        "money_earned",
        "units_killed",
        "buildings_killed",
        "tech_buildings_captured",
        "faction_buildings_captured",
    ]
    stats: list[Statistic] = []
    for dt in data_types:
        counter = sum(
            (
                Counter(last_val(m.stats_data[dt]))
                for m in matches
                if m.stats_data and m.stats_data[dt]
            ),
            Counter(),
        )
        most, most_count = counter.most_common(1)[0]
        fewest, min_count = min(counter.items(), key=lambda x: x[1])
        txt = " ".join(dt.split("_")).title()
        stats.append(
            Statistic(
                stat_name=f"Most {txt}",
                value=most_count,
                player=most,
                date_computed=computed_at,
            )
        )
        stats.append(
            Statistic(
                stat_name=f"Fewest {txt}",
                value=min_count,
                player=fewest,
                date_computed=computed_at,
            )
        )
    return stats


def fastest_win(matches: list[MatchInfo], computed_at: date) -> Statistic:
    fastest = min((m for m in matches), key=lambda x: x.duration_minutes)
    winners = [resolve_player_name(p.name, p.color) for p in fastest.players if p.won]
    losers = [
        resolve_player_name(p.name, p.color)
        for p in fastest.players
        if not p.won and p.team > 0
    ]
    return Statistic(
        stat_name="Fastest win",
        value=f"{fastest.duration_minutes:.1f}m",
        player="✅" + "+".join(winners) + " vs " + "+".join(losers) + "❌",
        match_id=fastest.id,
        date_computed=computed_at,
    )


def slowest_win(matches: list[MatchInfo], computed_at: date) -> Statistic:
    slowest = max((m for m in matches), key=lambda x: x.duration_minutes)
    winners = [resolve_player_name(p.name, p.color) for p in slowest.players if p.won]
    losers = [
        resolve_player_name(p.name, p.color)
        for p in slowest.players
        if not p.won and p.team > 0
    ]
    return Statistic(
        stat_name="Slowest win",
        value=f"{slowest.duration_minutes:.1f}m",
        player="✅" + "+".join(winners) + " vs " + "+".join(losers) + "❌",
        match_id=slowest.id,
        date_computed=computed_at,
    )


def group_by_team(
    tournament_name: str, matches: list[MatchInfo]
) -> dict[tuple[str, ...], list[MatchInfo]]:
    teams = TOURNAMENT_MAP[tournament_name].teams
    grouped: dict[tuple[str, ...], list[MatchInfo]] = defaultdict(list)
    for m in matches:
        player_names = {
            resolve_player_name(p.name, p.color) for p in m.players if p.team > 0
        }
        for team in teams:
            if set(team).issubset(player_names):
                grouped[team].append(m)
    return grouped


def ave_times(
    tournament_name: str, matches: list[MatchInfo], computed_at: date
) -> list[Statistic]:
    grouped = group_by_team(tournament_name, matches)
    ret: list[Statistic] = []
    for players, matches in grouped.items():
        times = [m.duration_minutes for m in matches]
        ave = statistics.mean(times)

        ret.append(
            Statistic(
                stat_name="Average match duration",
                value=f"{ave:.1f}m",
                player="+".join(players),
                date_computed=computed_at,
            )
        )
    logger.debug("ave times", times=ret)
    return ret


def tournament_report(
    tournament_name: str,
    tournament_matches: list[MatchInfo],
    tournament_match_details: list[MatchDetails],
) -> TournamentReport:
    computed_at = date.today()
    details = tournament_match_details

    stats: list[Statistic] = [
        earlest_first_blood(details, computed_at),
        most_first_bloods(details, computed_at),
        *faction_stats(tournament_matches, computed_at),
        highest_apm(details, computed_at),
        highest_ave_apm(details, computed_at),
        fastest_win(tournament_matches, computed_at),
        slowest_win(tournament_matches, computed_at),
        *min_max_stats(details, computed_at),
        *ave_times(tournament_name, tournament_matches, computed_at),
        *unit_stats(details, computed_at),
        *building_stats(details, computed_at),
    ]

    return TournamentReport(name=tournament_name, stats=stats)
