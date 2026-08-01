"""Detailed head-to-head record between two players.

Companion to the all-pairs matrix in ``routes/players.get_head_to_head``: given
two players, distil the competitive games where they were on opposite teams into
an overall record plus by-general and by-map breakdowns and the full game list.
Kept as a module (not inline in the route) so it can be unit-tested on a plain
``list[MatchInfo]``, matching the ``player_stats`` / ``player_rating`` convention.
"""

from __future__ import annotations

from collections import defaultdict

from . import player_ids
from .api_types import (
    General,
    HeadToHeadDetail,
    HeadToHeadGame,
    HeadToHeadGeneralRecord,
    HeadToHeadMapRecord,
    KillEventOutput,
    MatchInfo,
    PlayerSummary,
)


def _general_records(
    counts: dict[General, list[int]],
) -> list[HeadToHeadGeneralRecord]:
    return [
        HeadToHeadGeneralRecord(general=g, wins=wl[0], losses=wl[1])
        for g, wl in sorted(counts.items(), key=lambda kv: sum(kv[1]), reverse=True)
    ]


def value_destroyed_by_match(
    kill_data_by_match: dict[int, tuple[list[KillEventOutput], list[PlayerSummary]]],
    player1: str,
    player2: str,
) -> dict[int, tuple[int, int]]:
    """For each match, the value `player1` destroyed of `player2`'s stuff and
    vice versa (build cost of kills - the damage-dealt proxy, since replays
    don't carry raw HP).

    Kill events carry each match's *raw* in-game names (not alias-resolved -
    see match_details.py's name_by_idx), so each match is resolved
    independently via its own player_summary color map, same as
    superlatives.py does. Takes the (kill_events, player_summary) pairs from
    match_details.load_many_kill_data rather than full MatchDetails - across
    a whole head-to-head history that can be hundreds of matches, and full
    MatchDetails validation (build_orders/apm_over_time/etc.) is far more than
    this needs.
    """
    result: dict[int, tuple[int, int]] = {}
    for match_id, (kill_events, player_summary) in kill_data_by_match.items():
        color_map = {ps.Name: ps.Color for ps in player_summary}
        p1_destroyed = 0
        p2_destroyed = 0
        for k in kill_events:
            killer = player_ids.resolve_player_name(
                k.killer_player, color_map.get(k.killer_player, "")
            )
            victim = player_ids.resolve_player_name(
                k.victim_player, color_map.get(k.victim_player, "")
            )
            if killer == player1 and victim == player2:
                p1_destroyed += k.value
            elif killer == player2 and victim == player1:
                p2_destroyed += k.value
        if p1_destroyed or p2_destroyed:
            result[match_id] = (p1_destroyed, p2_destroyed)
    return result


def compute_head_to_head(
    games: list[MatchInfo],
    player1: str,
    player2: str,
    value_by_match: dict[int, tuple[int, int]] | None = None,
) -> HeadToHeadDetail:
    """Head-to-head detail for ``player1`` vs ``player2`` over ``games``.

    The by-general/by-map breakdowns and game list only cover games where both
    played on *different* teams (the winner is the side whose team won); games
    where they were teammates instead are tallied separately into
    ``teammate_games``/``teammate_wins`` rather than mixed into the opposite-team
    stats. ``games`` may be in any order - the returned game list is sorted
    most-recent-first. ``player1``/``player2`` are expected to be already
    alias-resolved (equal names yield an empty record).

    ``value_by_match`` (from ``value_destroyed_by_match``) is optional so this
    stays testable on plain ``MatchInfo`` alone; omitted entries default to
    (0, 0).
    """
    value_by_match = value_by_match or {}
    h2h_games: list[HeadToHeadGame] = []
    # [wins, losses] from each player's own perspective, keyed by their general.
    p1_by_general: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    p2_by_general: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    by_map: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    p1_wins = 0
    p2_wins = 0
    p1_value_destroyed = 0
    p2_value_destroyed = 0
    teammate_games = 0
    teammate_wins = 0

    for game in games:
        # Resolve every roster name once, then reuse for lookup and team lists.
        roster = [
            (p, player_ids.resolve_player_name(p.name, p.color))
            for p in game.players
            if p.team > 0
        ]
        p1p = next((p for p, name in roster if name == player1), None)
        p2p = next((p for p, name in roster if name == player2), None)
        if p1p is None or p2p is None:
            continue
        if p1p.team == p2p.team:
            teammate_games += 1
            if p1p.won:
                teammate_wins += 1
            continue
        if p1p.won == p2p.won:
            continue  # no decisive opposite-team result

        p1_won = p1p.won
        if p1_won:
            p1_wins += 1
        else:
            p2_wins += 1
        p1_by_general[p1p.general][0 if p1_won else 1] += 1
        p2_by_general[p2p.general][1 if p1_won else 0] += 1
        by_map[game.map][0 if p1_won else 1] += 1
        p1d, p2d = value_by_match.get(game.id, (0, 0))
        p1_value_destroyed += p1d
        p2_value_destroyed += p2d

        h2h_games.append(
            HeadToHeadGame(
                match_id=game.id,
                timestamp=game.timestamp,
                date=game.date,
                map=game.map,
                duration_minutes=game.duration_minutes,
                game_format=game.composition.category if game.composition else None,
                player1_general=p1p.general,
                player2_general=p2p.general,
                player1_won=p1_won,
                player1_team=[name for p, name in roster if p.team == p1p.team],
                player2_team=[name for p, name in roster if p.team == p2p.team],
                player1_value_destroyed=p1d,
                player2_value_destroyed=p2d,
            )
        )

    h2h_games.sort(key=lambda g: g.timestamp, reverse=True)
    return HeadToHeadDetail(
        player1=player1,
        player2=player2,
        player1_wins=p1_wins,
        player2_wins=p2_wins,
        games=h2h_games,
        player1_by_general=_general_records(p1_by_general),
        player2_by_general=_general_records(p2_by_general),
        by_map=[
            HeadToHeadMapRecord(map=m, player1_wins=wl[0], player2_wins=wl[1])
            for m, wl in sorted(by_map.items(), key=lambda kv: sum(kv[1]), reverse=True)
        ],
        teammate_games=teammate_games,
        teammate_wins=teammate_wins,
        player1_value_destroyed=p1_value_destroyed,
        player2_value_destroyed=p2_value_destroyed,
    )
