"""Tests for radarvan.stats_extraction, focused on the income_by_source breakdown.

Minimal replays are assembled directly from the model classes via
`model_construct` (see tests/test_apm.py) rather than a committed JSON fixture -
only the fields stats_data_from_replay actually reads are populated.
"""

from radarvan.cncstats_model.header import GeneralsHeader, Metadata
from radarvan.cncstats_model.zhreplay import (
    EnhancedReplayV2,
    EnrichedStats,
    GameInfoV2,
    PlayerSummaryV2,
)
from radarvan.cncstats_model.statsfile import (
    IncomeBySource,
    TimeSeries,
    TimeSeriesPlayer,
)
from radarvan.stats_extraction import stats_data_from_replay

FRAME_COUNT = 1800
DURATION_MINUTES = 10.0
SNAPSHOT_INTERVAL = 180  # one snapshot per minute at this frame_count/duration


def _header() -> GeneralsHeader:
    metadata = Metadata.model_construct(players=[])
    return GeneralsHeader.model_construct(
        frame_count=FRAME_COUNT,
        time_stamp_begin=0,
        time_stamp_end=int(DURATION_MINUTES * 60),
        metadata=metadata,
    )


def _summary(name: str, index: int) -> PlayerSummaryV2:
    return PlayerSummaryV2.model_construct(name=name, index=index)


def _ts_player(
    index: int,
    income: IncomeBySource | None,
    money: list[int] | None = None,
) -> TimeSeriesPlayer:
    money = money if money is not None else [1000, 2000]
    return TimeSeriesPlayer.model_construct(
        index=index,
        money=money,
        money_earned=money,
        money_spent=[0] * len(money),
        income_by_source=income,
    )


def _replay(ts_players: list[TimeSeriesPlayer]) -> EnhancedReplayV2:
    summaries = [_summary(f"P{p.index}", p.index) for p in ts_players]
    stats = EnrichedStats.model_construct(
        build_events=[],
        capture_events=[],
        battle_plan_events=[],
        death_events=[],
        energy_events=[],
        kill_events=[],
        radar_events=[],
        rank_events=[],
        science_points_events=[],
        skill_points_events=[],
        time_series=TimeSeries.model_construct(players=ts_players),
    )
    game_info = GameInfoV2.model_construct(snapshot_interval=SNAPSHOT_INTERVAL)
    return EnhancedReplayV2.model_construct(
        header=_header(), summary=summaries, stats=stats, game_info=game_info
    )


def test_income_by_source_extracted_per_player() -> None:
    p1_income = IncomeBySource.model_construct(
        black_market=[0, 100],
        bounty=[0, 0],
        crate=[0, 0],
        hacker=[0, 0],
        oil_derrick=[0, 50],
        other=[0, 0],
        salvage=[0, 0],
        supply=[0, 850],
        supply_drop=[0, 0],
        theft=[0, 0],
    )
    p2_income = IncomeBySource.model_construct(
        black_market=[0, 0],
        bounty=[0, 0],
        crate=[0, 0],
        hacker=[0, 200],
        oil_derrick=[0, 0],
        other=[0, 0],
        salvage=[0, 0],
        supply=[0, 800],
        supply_drop=[0, 0],
        theft=[0, 0],
    )
    replay = _replay([_ts_player(1, p1_income), _ts_player(2, p2_income)])

    result = stats_data_from_replay(replay)
    assert result is not None
    sd = result.stats_data

    # scale = DURATION_MINUTES / FRAME_COUNT; snap_idx=1 -> frame=SNAPSHOT_INTERVAL
    last_minute = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    assert sd.income_supply[last_minute] == {"P1": 850, "P2": 800}
    # Players that never earned from a source are pruned from that source's
    # snapshots (absent means zero) to keep the payload small.
    assert sd.income_black_market[last_minute] == {"P1": 100}
    assert sd.income_hacker[last_minute] == {"P2": 200}
    assert sd.income_oil_derrick[last_minute] == {"P1": 50}
    # A source nobody earned from is omitted entirely, not sent as zeros.
    assert sd.income_theft == {}


def test_income_by_source_sparsifies_unchanged_snapshots() -> None:
    """Only snapshots where a value changes (plus the one just before, so the
    plateau shape survives interpolation, plus the endpoints) are emitted."""
    income = IncomeBySource.model_construct(
        black_market=[0] * 6,
        bounty=[0] * 6,
        crate=[0] * 6,
        hacker=[0] * 6,
        oil_derrick=[0] * 6,
        other=[0] * 6,
        salvage=[0] * 6,
        # changes at snapshots 1 and 4; 2-3 are a plateau, 5 repeats.
        supply=[0, 100, 100, 100, 200, 200],
        supply_drop=[0] * 6,
        theft=[0] * 6,
    )
    replay = _replay([_ts_player(1, income, money=[0, 100, 100, 100, 200, 200])])

    result = stats_data_from_replay(replay)
    assert result is not None
    sd = result.stats_data

    minute_per_snap = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    # kept: 0 (endpoint + boundary), 1 (change), 3 (boundary), 4 (change),
    # 5 (endpoint); snapshot 2 (mid-plateau) is dropped.
    expected_snaps = [0, 1, 3, 4, 5]
    assert sorted(sd.income_supply) == [
        round(i * minute_per_snap, 3) for i in expected_snaps
    ]
    assert sd.income_supply[round(3 * minute_per_snap, 3)] == {"P1": 100}
    assert sd.income_supply[round(5 * minute_per_snap, 3)] == {"P1": 200}


def test_income_by_source_caps_snapshot_count() -> None:
    """A trickle source that changes on every snapshot must still come back
    with a bounded number of points (thinned grid), keeping the wire payload
    and chart render cost flat for long games - with the endpoints exact."""
    n = 1200
    supply = [i * 10 for i in range(n)]  # changes every snapshot
    income = IncomeBySource.model_construct(
        black_market=[0] * n,
        bounty=[0] * n,
        crate=[0] * n,
        hacker=[0] * n,
        oil_derrick=[0] * n,
        other=[0] * n,
        salvage=[0] * n,
        supply=supply,
        supply_drop=[0] * n,
        theft=[0] * n,
    )
    replay = _replay([_ts_player(1, income, money=supply)])

    result = stats_data_from_replay(replay)
    assert result is not None
    series = result.stats_data.income_supply

    assert len(series) <= 301
    minutes = sorted(series)
    assert series[minutes[0]] == {"P1": 0}
    assert series[minutes[-1]] == {"P1": (n - 1) * 10}


def test_income_by_source_absent_on_older_replays() -> None:
    """Older cncstats outputs don't populate incomeBySource at all; every
    income_<source> series must come back completely empty, not partially
    filled with zeros, so the frontend can hide the section entirely."""
    replay = _replay([_ts_player(1, None), _ts_player(2, None)])

    result = stats_data_from_replay(replay)
    assert result is not None
    sd = result.stats_data

    assert sd.income_supply == {}
    assert sd.income_black_market == {}
    assert sd.income_theft == {}
    # Unaffected series still populate as normal.
    last_minute = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    assert sd.money_earned[last_minute] == {"P1": 2000, "P2": 2000}
