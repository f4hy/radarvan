"""`matches.matches_differ` field-by-field comparison.

`matches_differ` only reads plain attributes off the two match objects and off
each player in `.players` (see `radarvan/matches.py`), so lightweight
`SimpleNamespace` stand-ins are sufficient (mirrors `tests/test_rating_upsets`).
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from radarvan.cncstats_model import body, header
from radarvan.cncstats_model.statsfile import DeathEvent
from radarvan.cncstats_model.zhreplay import (
    EnhancedReplayV2,
    EnrichedBuildEvent,
    EnrichedStats,
    PlayerSummaryV2,
)
from radarvan.matches import filter_by_months_back, is_incomplete, matches_differ
from radarvan.player_role import PlayerRole


def _header_player(name: str, team: str) -> header.Player:
    # player_template is read by utils.is_competitor on is_incomplete's
    # no-winner path; "2" is an ordinary competitor (-2 would be a spectator).
    return header.Player.model_construct(
        name=name, team=team, type="H", starting_position="0", player_template="2"
    )


def _summary_player(index: int, name: str, team: int, win: bool) -> PlayerSummaryV2:
    return PlayerSummaryV2.model_construct(index=index, name=name, team=team, win=win)


def _replay(
    teams: list[str],
    player_discons: list[bool],
    wins: list[bool],
    desync: bool = False,
    stats: EnrichedStats | None = None,
    body_chunks: list[body.BodyChunk] | None = None,
) -> EnhancedReplayV2:
    names = [f"P{i}" for i in range(len(teams))]
    metadata = header.Metadata.model_construct(
        # seed is the match id, which the mismatch paths log.
        seed=42,
        players=[_header_player(n, t) for n, t in zip(names, teams)],
    )
    head = header.GeneralsHeader.model_construct(
        desync=desync,
        quit_early=False,
        player_discons=player_discons,
        metadata=metadata,
        time_stamp_begin=0,
        time_stamp_end=600,
    )
    # Summary teams are the header's 0-based team + 1, matching
    # player_role.team_from_header.
    summary = [
        _summary_player(i + 1, n, int(t) + 1, w)
        for i, (n, t, w) in enumerate(zip(names, teams, wins))
    ]
    return EnhancedReplayV2.model_construct(
        header=head, stats=stats, summary=summary, body=body_chunks or []
    )


def test_disconnect_with_a_surviving_teammate_is_not_flagged() -> None:
    # 3v3: one member of team "0" disconnects, but two teammates remain and
    # the team still won - should not read as "Disconnect".
    replay = _replay(
        teams=["0", "0", "0", "1", "1", "1"],
        player_discons=[True, False, False, False, False, False],
        wins=[True, True, True, False, False, False],
    )
    assert is_incomplete(replay) == ""


def test_disconnect_of_a_solo_slot_with_a_winner_is_not_flagged() -> None:
    # 1v1 (each side is a "team" of one) - a disconnect on a slot with no
    # teammate doesn't invalidate the match as long as a winner was decided.
    replay = _replay(
        teams=["0", "1"], player_discons=[True, False], wins=[True, False]
    )
    assert is_incomplete(replay) == ""


def test_whole_team_disconnecting_is_still_flagged() -> None:
    # Both members of team "0" disconnect - the team was wiped out purely by
    # disconnection, so this still counts as a match-ending "Disconnect".
    replay = _replay(
        teams=["0", "0", "1", "1"],
        player_discons=[True, True, False, False],
        wins=[False, False, True, True],
    )
    assert is_incomplete(replay) == "Disconnect"


def _checksum(frame: int, player_id: int, value: int) -> body.BodyChunk:
    return body.BodyChunk.model_construct(
        order_name="Checksum", time_code=frame, player_id=player_id, arguments=[value]
    )


def _build(player: int) -> EnrichedBuildEvent:
    return EnrichedBuildEvent.model_construct(player=player, frame=100, cost=0)


def _mismatch_replay(
    decided_at: int | None,
    diverged_at: int | None,
    unlisted_death_at: int | None = None,
    unlisted_alive: bool = False,
) -> EnhancedReplayV2:
    """A 2v2 that desynced, parameterized on when each thing happened.

    Team "1" (summary indices 3 and 4) is wiped out at `decided_at`; two of the
    four clients report a different checksum at `diverged_at`. Either may be
    None to leave that evidence out entirely.

    `unlisted_death_at` / `unlisted_alive` add a fifth competitor that built
    something but has no summary entry - the cncstats slot-dropping bug - to
    exercise the guard that refuses to call a game decided while a slot whose
    side is unknown might still be playing.
    """
    deaths = (
        []
        if decided_at is None
        else [
            DeathEvent(frame=decided_at - 30, player=3),
            DeathEvent(frame=decided_at, player=4),
        ]
    )
    builds = [_build(i) for i in (1, 2, 3, 4)]
    if unlisted_death_at is not None or unlisted_alive:
        builds.append(_build(5))
    if unlisted_death_at is not None:
        deaths.append(DeathEvent(frame=unlisted_death_at, player=5))
    chunks = (
        []
        if diverged_at is None
        else [
            _checksum(diverged_at, player_id, 111 if player_id < 4 else 222)
            for player_id in (2, 3, 4, 5)
        ]
    )
    return _replay(
        teams=["0", "0", "1", "1"],
        player_discons=[False] * 4,
        wins=[True, True, False, False],
        desync=True,
        stats=EnrichedStats.model_construct(
            build_events=builds, kill_events=[], death_events=deaths
        ),
        body_chunks=chunks,
    )


def test_mismatch_after_the_last_player_died_is_not_flagged() -> None:
    # The losing team was gone 60 frames before the clients diverged, so every
    # checksum covering the game that decided the result agreed (603038953).
    assert is_incomplete(_mismatch_replay(decided_at=1000, diverged_at=1060)) == ""


def test_mismatch_before_the_result_is_still_flagged() -> None:
    # Divergence first: everything recorded afterwards - including who died -
    # came out of simulations that no longer agreed.
    replay = _mismatch_replay(decided_at=1000, diverged_at=940)
    assert is_incomplete(replay) == "Replay header Mismatch"


def test_mismatch_with_no_checksums_to_date_it_is_still_flagged() -> None:
    # An empty body leaves nothing to place the divergence in time, so the
    # match stays flagged rather than being cleared on an assumption.
    replay = _mismatch_replay(decided_at=1000, diverged_at=None)
    assert is_incomplete(replay) == "Replay header Mismatch"


def test_mismatch_with_no_team_wiped_out_is_still_flagged() -> None:
    # Nobody was eliminated, so the game never reached a result the divergence
    # could have come after.
    replay = _mismatch_replay(decided_at=None, diverged_at=1060)
    assert is_incomplete(replay) == "Replay header Mismatch"


def test_undescribed_slot_still_playing_keeps_the_flag() -> None:
    # A competitor cncstats dropped from the header is alive at the end. It
    # could have been the losing side's last player, so the listed teams dying
    # does not prove the game was over before the divergence.
    replay = _mismatch_replay(decided_at=1000, diverged_at=1060, unlisted_alive=True)
    assert is_incomplete(replay) == "Replay header Mismatch"


def test_undescribed_slot_pushes_the_decision_point_out_to_its_death() -> None:
    # It died after the last listed player, so the game cannot have been
    # decided before then - which is still before the divergence here.
    replay = _mismatch_replay(
        decided_at=1000, diverged_at=1100, unlisted_death_at=1050
    )
    assert is_incomplete(replay) == ""

    # Same match, but the clients diverge between the listed players dying and
    # the unlisted one - the flag has to stand (603038953's shape, had its AI
    # outlived the mismatch).
    replay = _mismatch_replay(
        decided_at=1000, diverged_at=1020, unlisted_death_at=1050
    )
    assert is_incomplete(replay) == "Replay header Mismatch"


def _player(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "player_name": "Skip",
        "general_id": 3,
        "team_id": 1,
        "color": "red",
        "is_winner": True,
        "starting_position": 0,
        "role": PlayerRole.HUMAN,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _match(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "map": "Tournament Desert",
        "winning_team_id": 1,
        "duration_minutes": 12.5,
        "incomplete": "",
        "game_version": "Version 1.04",
        "players": [
            _player(),
            _player(
                player_name="131",
                general_id=5,
                team_id=2,
                color="blue",
                is_winner=False,
                starting_position=1,
            ),
        ],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_identical_matches_do_not_differ() -> None:
    assert matches_differ(_match(), _match()) is False


def test_player_order_does_not_matter() -> None:
    # matches_differ sorts players before comparing, so a different ordering of
    # the same players must still compare equal.
    m1 = _match()
    m2 = _match(players=list(reversed(m1.players)))
    assert matches_differ(m1, m2) is False


def test_duration_difference_within_rounding_is_ignored() -> None:
    # Durations are compared rounded to 2 decimals.
    assert (
        matches_differ(_match(duration_minutes=12.5), _match(duration_minutes=12.501))
        is False
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("map", "Other Map"),
        ("winning_team_id", 2),
        ("duration_minutes", 13.0),
        ("incomplete", "disconnect"),
        ("game_version", "Version 1.05"),
    ],
)
def test_top_level_field_difference_is_detected(field: str, value: object) -> None:
    assert matches_differ(_match(), _match(**{field: value})) is True


@pytest.mark.parametrize(
    "field, value",
    [
        ("player_name", "Renamed"),
        ("general_id", 99),
        ("team_id", 7),
        ("color", "green"),
        ("is_winner", False),
        ("starting_position", 4),
        # An un-backfilled row must compare unequal to a classified one so the
        # reparse paths pick the role up.
        ("role", None),
        ("role", PlayerRole.CPU),
    ],
)
def test_player_field_difference_is_detected(field: str, value: object) -> None:
    new_players = [_player(**{field: value}), _match().players[1]]
    assert matches_differ(_match(), _match(players=new_players)) is True


def _game_on(d: date) -> SimpleNamespace:
    return SimpleNamespace(date=d)


def test_filter_by_months_back_none_returns_unchanged() -> None:
    games = [_game_on(date(2020, 1, 1))]
    assert filter_by_months_back(games, None) == games


def test_filter_by_months_back_drops_older_games() -> None:
    today = date(2026, 6, 30)
    recent = _game_on(date(2026, 6, 1))  # within the last month
    old = _game_on(date(2025, 1, 1))  # well over a year ago
    result = filter_by_months_back([recent, old], 1, today=today)
    assert result == [recent]


def test_filter_by_months_back_boundary_is_inclusive() -> None:
    today = date(2026, 6, 30)
    cutoff_day = _game_on(today - timedelta(days=30))
    result = filter_by_months_back([cutoff_day], 1, today=today)
    assert result == [cutoff_day]
