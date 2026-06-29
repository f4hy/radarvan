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
    MatchInfo,
)


def _general_records(
    counts: dict[General, list[int]],
) -> list[HeadToHeadGeneralRecord]:
    return [
        HeadToHeadGeneralRecord(general=g, wins=wl[0], losses=wl[1])
        for g, wl in sorted(counts.items(), key=lambda kv: sum(kv[1]), reverse=True)
    ]


def compute_head_to_head(
    games: list[MatchInfo], player1: str, player2: str
) -> HeadToHeadDetail:
    """Head-to-head detail for ``player1`` vs ``player2`` over ``games``.

    Counts games where both played on *different* teams; the winner is the side
    whose team won. ``games`` may be in any order — the returned game list is
    sorted most-recent-first. ``player1``/``player2`` are expected to be already
    alias-resolved (equal names yield an empty record).
    """
    h2h_games: list[HeadToHeadGame] = []
    # [wins, losses] from each player's own perspective, keyed by their general.
    p1_by_general: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    p2_by_general: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    by_map: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    p1_wins = 0
    p2_wins = 0

    for game in games:
        # Resolve every roster name once, then reuse for lookup and team lists.
        roster = [
            (p, player_ids.resolve_player_name(p.name, p.color))
            for p in game.players
            if p.team > 0
        ]
        p1p = next((p for p, name in roster if name == player1), None)
        p2p = next((p for p, name in roster if name == player2), None)
        if p1p is None or p2p is None or p1p.team == p2p.team:
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
    )
