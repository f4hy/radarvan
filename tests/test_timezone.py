"""Timezone handling for match timestamps and 'game night' grouping.

Guards two invariants introduced when fixing the matches-page time display:

1. Match timestamps are tz-aware UTC end-to-end, so the API serializes an
   offset and clients render in the viewer's local zone (not a hard-coded one).
2. ``game_night_date`` groups a match onto the *evening it was played* in US
   Eastern, rolling the day boundary forward ~5am local so late-night sessions
   (running past midnight into the early morning) stay on the prior night.
"""

import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from radarvan import matches
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.utils import duration_minutes, game_night_date, game_night_date_of

EASTERN = ZoneInfo("America/New_York")
REPO_ROOT = Path(__file__).parent.parent
EXAMPLE_REPLAY = REPO_ROOT / "references" / "example_cncstats_output.json"

# The reference replay's time_stamp_begin (a POSIX/UTC epoch) and the instant it
# represents. 03:21 UTC is still the *previous evening* (23:21) in US Eastern.
EXAMPLE_TS_BEGIN = 1779938463
EXAMPLE_UTC = datetime.datetime(2026, 5, 28, 3, 21, 3, tzinfo=datetime.UTC)
EXAMPLE_GAME_NIGHT = datetime.date(2026, 5, 27)


def _eastern_epoch(year: int, month: int, day: int, hour: int, minute: int = 0) -> float:
    """POSIX (UTC) epoch for a given US Eastern wall-clock time."""
    return datetime.datetime(
        year, month, day, hour, minute, tzinfo=EASTERN
    ).timestamp()


class TestGameNightDate:
    def test_evening_games_stay_on_their_day(self) -> None:
        # Saturday 2026-06-06 evening (EDT).
        assert game_night_date(_eastern_epoch(2026, 6, 6, 20, 0)) == datetime.date(
            2026, 6, 6
        )
        assert game_night_date(_eastern_epoch(2026, 6, 6, 23, 59)) == datetime.date(
            2026, 6, 6
        )

    @pytest.mark.parametrize("hour, minute", [(0, 1), (1, 0), (2, 30), (4, 59)])
    def test_after_midnight_rolls_back_to_prior_night(
        self, hour: int, minute: int
    ) -> None:
        # Early Sunday 2026-06-07 morning still counts as the Saturday night.
        ts = _eastern_epoch(2026, 6, 7, hour, minute)
        assert game_night_date(ts) == datetime.date(2026, 6, 6)

    def test_rollover_boundary_is_5am_local(self) -> None:
        assert game_night_date(_eastern_epoch(2026, 6, 7, 4, 59)) == datetime.date(
            2026, 6, 6
        )
        assert game_night_date(_eastern_epoch(2026, 6, 7, 5, 0)) == datetime.date(
            2026, 6, 7
        )

    def test_daytime_game_is_on_its_own_day(self) -> None:
        assert game_night_date(_eastern_epoch(2026, 6, 7, 13, 0)) == datetime.date(
            2026, 6, 7
        )

    def test_winter_est_late_night(self) -> None:
        # January = EST (UTC-5). Saturday night and early Sunday.
        assert game_night_date(_eastern_epoch(2026, 1, 10, 23, 0)) == datetime.date(
            2026, 1, 10
        )
        assert game_night_date(_eastern_epoch(2026, 1, 11, 1, 30)) == datetime.date(
            2026, 1, 10
        )

    def test_grouping_uses_eastern_not_utc(self) -> None:
        # 2026-05-28T03:21:03Z is May 27 *evening* (23:21) in Eastern — grouping
        # on the raw UTC date would wrongly land it on the 28th.
        assert game_night_date(EXAMPLE_UTC.timestamp()) == EXAMPLE_GAME_NIGHT

    def test_accepts_int_and_float(self) -> None:
        ts = _eastern_epoch(2026, 6, 6, 20, 0)
        assert game_night_date(int(ts)) == game_night_date(float(ts))

    def test_returns_a_plain_date(self) -> None:
        result = game_night_date(_eastern_epoch(2026, 6, 6, 20, 0))
        assert type(result) is datetime.date


class TestGameNightDateOf:
    """game_night_date_of is what the bracket exposes to the frontend so a
    match popup can look up the games actually played for it - the raw UTC
    date of scheduled_at is the wrong day for any evening start."""

    def test_evening_start_is_the_previous_utc_day(self) -> None:
        # A real case: WB1 scheduled 2026-08-08T00:05Z is 8:05pm Eastern on
        # the 7th, and its games are stored under the 7th.
        when = datetime.datetime(2026, 8, 8, 0, 5, tzinfo=datetime.UTC)
        assert when.date() == datetime.date(2026, 8, 8), "precondition"
        assert game_night_date_of(when) == datetime.date(2026, 8, 7)

    def test_naive_input_is_read_as_utc(self) -> None:
        aware = datetime.datetime(2026, 8, 8, 0, 5, tzinfo=datetime.UTC)
        naive = datetime.datetime(2026, 8, 8, 0, 5)
        assert game_night_date_of(naive) == game_night_date_of(aware)

    def test_matches_game_night_date_for_the_same_instant(self) -> None:
        when = datetime.datetime(2026, 1, 11, 1, 30, tzinfo=datetime.UTC)
        assert game_night_date_of(when) == game_night_date(when.timestamp())

    def test_afternoon_start_stays_on_its_own_day(self) -> None:
        when = datetime.datetime(2026, 6, 7, 13, 0, tzinfo=EASTERN)
        assert game_night_date_of(when) == datetime.date(2026, 6, 7)


@pytest.fixture
def example_replay() -> EnhancedReplayV2:
    return EnhancedReplayV2.model_validate(json.loads(EXAMPLE_REPLAY.read_text()))


class TestMatchTimestampsAreAwareUtc:
    def test_match_from_replay_timestamp_is_aware_utc(
        self, example_replay: EnhancedReplayV2
    ) -> None:
        mi = matches.match_from_replay(example_replay, filter_short=False)
        assert mi is not None
        assert mi.timestamp.tzinfo is not None, "timestamp must be tz-aware"
        assert mi.timestamp.utcoffset() == datetime.timedelta(0), "must be UTC"
        assert mi.timestamp == EXAMPLE_UTC

    def test_match_from_replay_date_is_game_night(
        self, example_replay: EnhancedReplayV2
    ) -> None:
        mi = matches.match_from_replay(example_replay, filter_short=False)
        assert mi is not None
        assert mi.date == game_night_date(EXAMPLE_TS_BEGIN) == EXAMPLE_GAME_NIGHT

    def test_db_match_timestamp_is_aware_utc(
        self, example_replay: EnhancedReplayV2
    ) -> None:
        db_match = matches.replay_to_db_match(example_replay, "s3://test/x.json")
        assert db_match.timestamp.tzinfo is not None
        assert db_match.timestamp.utcoffset() == datetime.timedelta(0)
        assert db_match.timestamp == EXAMPLE_UTC


def test_duration_is_timezone_independent(
    example_replay: EnhancedReplayV2,
) -> None:
    # Duration is a delta of two epochs, so it must not depend on any zone.
    assert duration_minutes(example_replay) > 0
