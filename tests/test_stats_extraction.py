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
import numpy as np

from radarvan.stats_extraction import (
    _INCOME_CHART_HEIGHT_PX,
    _INCOME_TOLERANCE_PX,
    stats_data_from_replay,
)

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


def _income(n: int = 2, **overrides: list[int]) -> IncomeBySource:
    """An IncomeBySource with every source zeroed for `n` snapshots except
    the given overrides."""
    fields: dict[str, list[int]] = {src: [0] * n for src in IncomeBySource.model_fields}
    fields.update(overrides)
    return IncomeBySource.model_construct(**fields)


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
    p1_income = _income(supply=[0, 850], black_market=[0, 100], oil_derrick=[0, 50])
    p2_income = _income(supply=[0, 800], hacker=[0, 200])
    replay = _replay([_ts_player(1, p1_income), _ts_player(2, p2_income)])

    result = stats_data_from_replay(replay)
    assert result is not None
    income = result.income_by_source

    # scale = DURATION_MINUTES / FRAME_COUNT; snap_idx=1 -> frame=SNAPSHOT_INTERVAL
    last_minute = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    assert income["supply"][last_minute] == {"P1": 850, "P2": 800}
    # Players that never earned from a source are pruned from that source's
    # snapshots (absent means zero) to keep the payload small.
    assert income["black_market"][last_minute] == {"P1": 100}
    assert income["hacker"][last_minute] == {"P2": 200}
    assert income["oil_derrick"][last_minute] == {"P1": 50}
    # Sources nobody earned from are omitted entirely, not sent as zeros.
    assert sorted(income) == ["black_market", "hacker", "oil_derrick", "supply"]


def test_income_by_source_sparsifies_unchanged_snapshots() -> None:
    """A flat run keeps only its two ends; corners and endpoints survive."""
    # supply changes at snapshots 1 and 4; 2-3 are a plateau, 5 repeats.
    supply = [0, 100, 100, 100, 200, 200]
    replay = _replay([_ts_player(1, _income(n=6, supply=supply), money=supply)])

    result = stats_data_from_replay(replay)
    assert result is not None
    series = result.income_by_source["supply"]

    minute_per_snap = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    # kept: 0 (endpoint + boundary), 1 (change), 3 (boundary), 4 (change),
    # 5 (endpoint); snapshot 2 (mid-plateau) is dropped.
    expected_snaps = [0, 1, 3, 4, 5]
    assert sorted(series) == [round(i * minute_per_snap, 3) for i in expected_snaps]
    assert series[round(3 * minute_per_snap, 3)] == {"P1": 100}
    assert series[round(5 * minute_per_snap, 3)] == {"P1": 200}


def test_income_by_source_rows_are_per_player() -> None:
    """Each player has rows only at their own simplified points, with every
    source they earned from present there; another player's corners don't add
    rows for them."""
    supply = [0, 10, 20, 30, 40, 50]
    p1 = _income(n=6, supply=supply, salvage=[0, 50, 50, 50, 50, 50])
    p2 = _income(n=6, supply=[0, 0, 0, 100, 100, 100])
    replay = _replay([_ts_player(1, p1, money=supply), _ts_player(2, p2, money=supply)])

    result = stats_data_from_replay(replay)
    assert result is not None
    income = result.income_by_source

    minute_per_snap = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    m = [i * minute_per_snap for i in range(6)]
    # P1: supply is a straight line; the stacked salvage edge bends at 1.
    assert [t for t in income["supply"] if "P1" in income["supply"][t]] == [
        m[0],
        m[1],
        m[5],
    ]
    assert list(income["salvage"]) == [m[0], m[1], m[5]]
    assert income["supply"][m[1]]["P1"] == 10 and income["salvage"][m[1]] == {"P1": 50}
    # P2's step corners (2 and 3) are P2's alone.
    assert [t for t in income["supply"] if "P2" in income["supply"][t]] == [
        m[0],
        m[2],
        m[3],
        m[5],
    ]
    assert "P1" not in income["supply"][m[2]]


def test_income_by_source_stacked_edges_within_tolerance() -> None:
    """Every edge the stacked chart draws (cumulative sum of sources in the
    client's order) stays within half a pixel of the full-resolution one."""
    rng = np.random.default_rng(0)
    n = 1200
    cols = {
        "supply": np.cumsum(rng.integers(0, 40, n)),
        "oil_derrick": np.cumsum(rng.integers(0, 2, n) * 20),
        "black_market": np.cumsum((rng.random(n) < 0.01) * 500),
        "theft": np.cumsum((rng.random(n) < 0.002) * 3000),
    }
    p1 = _income(n=n, **{k: v.tolist() for k, v in cols.items()})
    replay = _replay([_ts_player(1, p1, money=[0] * n)])

    result = stats_data_from_replay(replay)
    assert result is not None
    income = result.income_by_source

    minute_per_snap = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    x = np.arange(n) * minute_per_snap
    kept_t = np.array(sorted(income["supply"]))
    assert len(kept_t) < n / 4
    total = sum(v[-1] for v in cols.values())
    tolerance = _INCOME_TOLERANCE_PX * total / _INCOME_CHART_HEIGHT_PX
    edge = np.zeros(n)
    kept_edge = np.zeros(len(kept_t))
    for src in ("supply", "oil_derrick", "black_market", "theft"):  # client order
        edge = edge + cols[src]
        kept_edge = kept_edge + np.array([income[src][t]["P1"] for t in kept_t])
        assert np.max(np.abs(np.interp(x, kept_t, kept_edge) - edge)) <= tolerance


def test_stats_straight_line_keeps_only_endpoints() -> None:
    n = 1200
    money = [i * 10 for i in range(n)]
    replay = _replay([_ts_player(1, None, money=money)])

    result = stats_data_from_replay(replay)
    assert result is not None
    series = result.stats_data.money

    minutes = list(series)
    assert minutes == sorted(minutes)
    assert [series[m] for m in minutes] == [{"P1": 0}, {"P1": (n - 1) * 10}]


def test_stats_jagged_line_capped_per_player_with_exact_endpoints() -> None:
    n = 1200
    money = [(i % 2) * 5000 + i for i in range(n)]  # never within tolerance
    replay = _replay([_ts_player(1, None, money=money)])

    result = stats_data_from_replay(replay)
    assert result is not None
    series = result.stats_data.money

    assert len(series) == 600
    minutes = list(series)
    assert series[minutes[0]] == {"P1": money[0]}
    assert series[minutes[-1]] == {"P1": money[-1]}


def test_stats_rows_sparse_but_first_and_last_complete() -> None:
    steady = [i * 10 for i in range(20)]
    spiky = [0, 5000] * 10
    replay = _replay(
        [_ts_player(1, None, money=steady), _ts_player(2, None, money=spiky)]
    )

    result = stats_data_from_replay(replay)
    assert result is not None
    series = result.stats_data.money

    minutes = list(series)
    assert series[minutes[0]] == {"P1": 0, "P2": 0}
    assert series[minutes[-1]] == {"P1": 190, "P2": 5000}
    # P1 is a straight line, so it appears only in the first and last rows.
    assert all(set(series[m]) == {"P2"} for m in minutes[1:-1])
    assert len(minutes) == 20


def test_income_by_source_absent_on_older_replays() -> None:
    """Older cncstats outputs don't populate incomeBySource at all; the
    breakdown must come back completely empty, not partially filled with
    zeros, so the frontend can hide the tab entirely."""
    replay = _replay([_ts_player(1, None), _ts_player(2, None)])

    result = stats_data_from_replay(replay)
    assert result is not None

    assert result.income_by_source == {}
    # Unaffected series still populate as normal.
    last_minute = SNAPSHOT_INTERVAL * DURATION_MINUTES / FRAME_COUNT
    assert result.stats_data.money_earned[last_minute] == {"P1": 2000, "P2": 2000}
