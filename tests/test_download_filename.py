"""The name a downloaded .rep is saved under."""

from datetime import UTC, datetime

from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.replay_files import download_filename

import corpus


def test_names_the_date_format_sides_map_and_id() -> None:
    match = corpus.match(1, day=7, map_name="maps/Tournament Desert/desert.map")
    assert (
        download_filename(match)
        == "2026-01-07-2v2-CoreDawg-Skip-vs-Pancake-Syn-desert-1.rep"
    )


def test_observers_do_not_appear() -> None:
    match = corpus.match(2, day=7, extra_players=(corpus.observer(),))
    assert download_filename(match) == download_filename(corpus.match(2, day=7))


def test_aliases_resolve_to_canonical_names() -> None:
    match = corpus.match(3, day=7, team_one=("skp", "CoreDawg"))
    assert download_filename(match).startswith("2026-01-07-2v2-CoreDawg-Skip-vs-")


def test_teamless_1v1_players_are_separate_sides() -> None:
    # A 1v1 that never went through parse_replay.reassign_1v1_teams: both
    # competitors sit on team 0, and joining them would lose the "vs".
    match = MatchInfo(
        id=4,
        timestamp=datetime(2026, 1, 7, 12, 0, tzinfo=UTC),
        date=datetime(2026, 1, 7, 12, 0, tzinfo=UTC).date(),
        map="Bitter Winter",
        winning_team=Team.NONE,
        players=[
            Player(name="Skip", general=General(1), team=Team.NONE, color="red"),
            Player(name="Syn", general=General(2), team=Team.NONE, color="blue"),
        ],
        duration_minutes=9.0,
        filename="4.rep",
    )
    # No composition either, so the format falls back to the side sizes.
    assert download_filename(match) == "2026-01-07-1v1-Skip-vs-Syn-Bitter_Winter-4.rep"


def test_unsafe_characters_are_collapsed() -> None:
    match = corpus.match(5, day=7, map_name="[Fan] Snow? Storm!.map")
    assert download_filename(match).endswith("-Fan_Snow_Storm-5.rep")
