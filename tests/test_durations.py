"""The game-length histogram.

The bucketing rules are the whole feature: an empty bar has to survive so the
client can draw a continuous axis, the last bar has to absorb the long tail, and
a mis-parsed near-zero duration must not become a spike in the first bar.
"""

from radarvan import durations

import corpus


def test_buckets_cover_the_range_including_empty_bars() -> None:
    buckets = durations.bucket_durations([1.0, 1.5], bucket_minutes=2.0, max_minutes=10.0)
    # Five 2-minute bars plus the overflow bin.
    assert len(buckets) == 6
    assert buckets[0].count == 2
    assert [b.count for b in buckets[1:]] == [0, 0, 0, 0, 0]
    assert buckets[0].start_minutes == 0.0
    assert buckets[0].end_minutes == 2.0


def test_final_bucket_is_an_open_ended_overflow_bin() -> None:
    """One marathon widens the tail label rather than the whole axis."""
    buckets = durations.bucket_durations(
        [5.0, 240.0], bucket_minutes=2.0, max_minutes=10.0
    )
    assert buckets[-1].end_minutes is None
    assert buckets[-1].count == 1
    assert buckets[-1].start_minutes == 10.0


def test_a_value_exactly_on_a_boundary_lands_in_the_upper_bucket() -> None:
    buckets = durations.bucket_durations([2.0], bucket_minutes=2.0, max_minutes=10.0)
    assert buckets[0].count == 0
    assert buckets[1].count == 1


def test_near_zero_durations_are_dropped_as_misparses() -> None:
    games = [
        corpus.match(1, day=5, duration_minutes=0.0),
        corpus.match(2, day=5, duration_minutes=0.2),
        corpus.match(3, day=5, duration_minutes=12.0),
    ]
    assert durations.playable_durations(games) == [12.0]
    assert durations.duration_distribution(games).stats.count == 1


def test_summary_statistics_are_ordered_and_interpolated() -> None:
    stats = durations.summarize([10.0, 20.0, 30.0, 40.0])
    assert stats.count == 4
    assert stats.shortest_minutes == 10.0
    assert stats.longest_minutes == 40.0
    assert stats.median_minutes == 25.0
    assert stats.total_minutes == 100.0
    assert stats.mean_minutes == 25.0


def test_summary_of_nothing_is_empty_rather_than_an_error() -> None:
    stats = durations.summarize([])
    assert stats.count == 0
    assert stats.median_minutes is None
    assert stats.total_minutes == 0


def test_by_format_splits_the_corpus_and_orders_by_popularity() -> None:
    games = [
        corpus.match(1, day=5, duration_minutes=10.0),
        corpus.match(2, day=5, duration_minutes=20.0),
        corpus.match(
            3,
            day=5,
            team_one=corpus.TEAM_ONE[:1],
            team_two=corpus.TEAM_TWO[:1],
            duration_minutes=6.0,
        ),
    ]
    result = durations.duration_distribution(games)
    assert list(result.by_format) == ["2v2", "1v1"]
    assert result.by_format["2v2"].count == 2
    assert result.by_format["1v1"].median_minutes == 6.0
    # Every format's games are also in the overall stats, counted once.
    assert result.stats.count == 3


def test_an_observer_does_not_change_the_distribution() -> None:
    """Adding a spectator must be a no-op - see CLAUDE.md."""
    plain = corpus.match(1, day=5, duration_minutes=14.0)
    watched = corpus.match(
        1, day=5, duration_minutes=14.0, extra_players=(corpus.observer(),)
    )
    assert durations.duration_distribution([plain]) == durations.duration_distribution(
        [watched]
    )
