"""The deterministic per-match narrative.

Two things are pinned: that every beat comes from data actually present (a
missing field produces no beat rather than an invented one), and the selection
rules that stop an 8-player game becoming a log - first-to-reach only for the
shared milestones, but every collapse.
"""

import pytest

from radarvan import match_narrative
from radarvan.api_types import (
    APM,
    FirstBlood,
    MatchDetails,
    TimelineEvent,
)

import corpus


def _details(**overrides: object) -> MatchDetails:
    base: dict[str, object] = {
        "match_id": 1,
        "costs": [],
        "apms": [],
        "upgrade_events": {},
        "stats_data": {},
        "player_summary": [],
    }
    base.update(overrides)
    return MatchDetails(**base)  # type: ignore[arg-type]


def _kinds(narrative: match_narrative.MatchNarrative) -> list[str]:
    return [beat.kind for beat in narrative.beats]


def test_a_match_with_no_details_still_has_a_headline() -> None:
    narrative = match_narrative.build_narrative(corpus.A_MATCH, None)
    assert narrative.beats == []
    assert "beat" in narrative.headline
    assert corpus.A_MATCH.map in narrative.headline


def test_headline_names_winners_losers_map_and_length() -> None:
    match = corpus.match(1, day=5, duration_minutes=23.0, map_name="Bitter Winter")
    narrative = match_narrative.build_narrative(match, None)
    assert "Skip & CoreDawg beat Syn & Pancake" in narrative.headline
    assert "Bitter Winter" in narrative.headline
    assert "23 min" in narrative.headline


def test_an_undecided_match_says_so_rather_than_naming_a_winner() -> None:
    from radarvan.api_types import Team

    match = corpus.match(1, day=5, winner=Team.NONE, incomplete="no winner recorded")
    narrative = match_narrative.build_narrative(match, _details())
    assert "beat" not in narrative.headline
    assert "no winner recorded" in narrative.headline
    assert _kinds(narrative)[-1] == "result"


def test_empty_details_yield_only_setup_and_result() -> None:
    """Nothing is invented for a match whose details carry no events."""
    narrative = match_narrative.build_narrative(corpus.A_MATCH, _details())
    assert _kinds(narrative) == ["setup", "result"]


def test_beats_are_ordered_by_minute_between_setup_and_result() -> None:
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(
            time_to_hunted={"Syn": 18.0},
            first_blood=FirstBlood(attacker="Skip", victim="Syn", atMinute=2.0),
            time_to_rank_5={"CoreDawg": 9.0, "Pancake": 11.0},
        ),
    )
    kinds = _kinds(narrative)
    assert kinds[0] == "setup"
    assert kinds[-1] == "result"
    timed = [b for b in narrative.beats if b.at_minute is not None]
    assert [b.at_minute for b in timed] == sorted(b.at_minute for b in timed)
    assert [b.kind for b in timed] == ["first_blood", "milestone", "collapse"]


def test_only_the_first_player_to_a_milestone_is_named() -> None:
    """Eight rank-5 lines is a log, not a story."""
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(time_to_rank_5={"Skip": 12.0, "CoreDawg": 9.0, "Syn": 14.0}),
    )
    milestones = [b for b in narrative.beats if b.kind == "milestone"]
    assert len(milestones) == 1
    assert milestones[0].player_name == "CoreDawg"
    assert milestones[0].at_minute == 9.0


def test_every_collapse_is_named_not_just_the_first() -> None:
    """Which teammate went hunted is the story in a team game."""
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH, _details(time_to_hunted={"Syn": 18.0, "Pancake": 22.0})
    )
    collapses = [b for b in narrative.beats if b.kind == "collapse"]
    assert [b.player_name for b in collapses] == ["Syn", "Pancake"]


def _activation(player: str, name: str, minute: float) -> TimelineEvent:
    return TimelineEvent(
        player_name=player,
        at_minute=minute,
        event_name=name,
        event_type="superweapon_activated",
    )


def test_a_generals_power_is_not_reported_as_a_superweapon() -> None:
    """A Spectre Gunship is a generals-panel star power, not a Scud Storm.

    The engine tags several panel powers ``Superweapon*``, so ``event_type``
    alone is far wider than "a superweapon fired" - see
    ``timeline_events.BASE_SUPERWEAPON_LAUNCHES``.
    """
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(timeline_events=[_activation("Skip", "SpectreGunship", 9.9)]),
    )
    assert not [b for b in narrative.beats if b.kind == "superweapon"]
    power = next(b for b in narrative.beats if b.kind == "power")
    assert power.text == "Skip called in the SpectreGunship generals power."


def test_the_two_are_reported_side_by_side_not_merged() -> None:
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(
            timeline_events=[
                _activation("Skip", "SpectreGunship", 9.9),
                _activation("Syn", "ScudStorm", 20.0),
                _activation("CoreDawg", "EMPPulse", 12.0),
                _activation("Pancake", "NeutronMissile", 22.0),
            ]
        ),
    )
    assert {b.player_name for b in narrative.beats if b.kind == "superweapon"} == {
        "Syn",
        "Pancake",
    }
    assert {b.player_name for b in narrative.beats if b.kind == "power"} == {
        "Skip",
        "CoreDawg",
    }


@pytest.mark.parametrize("name", match_narrative.BASE_SUPERWEAPON_LAUNCHES)
def test_every_base_superweapon_is_recognised(name: str) -> None:
    assert match_narrative.is_base_superweapon(name)


def test_repeated_launches_of_one_weapon_collapse_to_a_single_beat() -> None:
    """A Spectre Gunship called in six times is one habit, not six beats."""
    events = [
        _activation("Skip", "SpectreGunship", minute) for minute in (14.0, 7.2, 10.8)
    ]
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH, _details(timeline_events=events)
    )
    powers = [b for b in narrative.beats if b.kind == "power"]
    assert len(powers) == 1
    assert powers[0].at_minute == 7.2
    assert "(x3)" in powers[0].text


def test_a_single_launch_is_not_annotated_with_a_count() -> None:
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(timeline_events=[_activation("Skip", "ScudStorm", 20.0)]),
    )
    launch = next(b for b in narrative.beats if b.kind == "superweapon")
    assert launch.text == "Skip launched the ScudStorm superweapon."


def test_superweapon_launches_are_capped_and_time_ordered() -> None:
    events = [
        _activation("Skip", f"ScudStorm {i}", float(30 - i))
        for i in range(match_narrative.MAX_SUPERWEAPON_BEATS + 4)
    ]
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH, _details(timeline_events=events)
    )
    launches = [b for b in narrative.beats if b.kind == "superweapon"]
    assert len(launches) == match_narrative.MAX_SUPERWEAPON_BEATS
    assert launches == sorted(launches, key=lambda b: b.at_minute or 0.0)


def test_superweapon_builds_are_not_reported_as_launches() -> None:
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(
            timeline_events=[
                TimelineEvent(
                    player_name="Skip",
                    at_minute=12.0,
                    event_name="Nuke Silo",
                    event_type="superweapon_built",
                )
            ]
        ),
    )
    assert not [b for b in narrative.beats if b.kind == "superweapon"]


_kill = corpus.kill


def test_a_cheap_kill_is_not_called_out_as_the_priciest() -> None:
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(kill_events=[_kill(match_narrative.BIG_KILL_MIN_VALUE - 1)]),
    )
    assert not [b for b in narrative.beats if "Priciest" in b.text]


def test_the_priciest_kill_names_both_units_cleaned() -> None:
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH, _details(kill_events=[_kill(4000)])
    )
    beat = next(b for b in narrative.beats if "Priciest" in b.text)
    # clean_object_name strips the faction prefix.
    assert "Crusader" in beat.text and "AmericaVehicle" not in beat.text
    assert "Overlord" in beat.text
    assert "$4,000" in beat.text


def test_ledger_beats_name_the_leader_of_each_column() -> None:
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH,
        _details(
            player_money_collected={"Skip": 40000, "Syn": 25000},
            kill_events=[_kill(4000, killer="Syn"), _kill(2000, killer="Skip")],
            apms=[
                APM(player_name="Skip", action_count=100, minutes=10.0, apm=80.0),
                APM(player_name="Syn", action_count=100, minutes=10.0, apm=120.0),
            ],
        ),
    )
    by_kind = {b.kind: b for b in narrative.beats if b.kind in {"economy", "tempo"}}
    assert by_kind["economy"].player_name == "Skip"
    assert by_kind["tempo"].player_name == "Syn"
    damage = next(b for b in narrative.beats if b.text.endswith("destroyed."))
    assert damage.player_name == "Syn"


def test_a_zero_ledger_produces_no_beat() -> None:
    """A leader of nothing is not a leader."""
    narrative = match_narrative.build_narrative(
        corpus.A_MATCH, _details(player_money_collected={"Skip": 0, "Syn": 0})
    )
    assert not [b for b in narrative.beats if b.kind == "economy"]


def test_observers_do_not_appear_in_the_lineup() -> None:
    """Adding a spectator must not change the story - see CLAUDE.md."""
    plain = match_narrative.build_narrative(corpus.match(1, day=5), _details())
    watched = match_narrative.build_narrative(
        corpus.match(1, day=5, extra_players=(corpus.observer(name="Gorn"),)),
        _details(),
    )
    assert plain == watched
    assert "Gorn" not in watched.headline


# --- shapes that aren't two teams --------------------------------------------


def test_an_ffa_names_every_player_as_their_own_side() -> None:
    """FFA slots are all team 0, so `participants` is empty - see CLAUDE.md."""
    match = corpus.ffa_match(1, day=5, winner_index=1)
    narrative = match_narrative.build_narrative(match, _details())
    names = corpus.FFA_NAMES[:4]
    assert names[1] in narrative.headline
    assert "beat" in narrative.headline
    for name in names:
        assert name in narrative.beats[0].text
    assert narrative.beats[-1].text.startswith(f"{names[1]} took it")


def test_the_map_is_shown_as_a_name_not_a_stored_path() -> None:
    match = corpus.match(1, day=5, map_name="userdata/maps/bitter winter/bitter winter.map")
    narrative = match_narrative.build_narrative(match, _details())
    assert "bitter winter" in narrative.headline
    assert "userdata/maps" not in narrative.headline
    assert "userdata/maps" not in narrative.beats[0].text
    assert ".map" not in narrative.headline


# --- match metadata carried for the recap prompt ------------------------------


def test_the_narrative_carries_the_wall_clock_start() -> None:
    """A game night is a date key, not a sitting - only the clock shows a gap."""
    match = corpus.match(1, day=5)
    narrative = match_narrative.build_narrative(match, _details())
    assert narrative.started_at == match.timestamp


def test_a_casual_game_has_no_tournament_label() -> None:
    assert match_narrative.build_narrative(corpus.A_MATCH, None).tournament is None


def test_a_tournament_game_names_its_round() -> None:
    from radarvan.api_types import TournamentTag

    match = corpus.A_MATCH.model_copy(
        update={
            "tournament": TournamentTag(
                slug="spring-cup", stage="WB2-1", round_name="Winners Semifinal"
            )
        }
    )
    narrative = match_narrative.build_narrative(match, None)
    assert narrative.tournament == "spring-cup - Winners Semifinal"


def test_a_round_robin_tournament_game_still_names_the_tournament() -> None:
    from radarvan.api_types import TournamentTag

    match = corpus.A_MATCH.model_copy(
        update={"tournament": TournamentTag(slug="spring-cup")}
    )
    assert match_narrative.build_narrative(match, None).tournament == "spring-cup"


# --- turning point ------------------------------------------------------------

SKIP_WINS = corpus.match(1, day=5)

# Rises 25% -> 90% between 1.5 and 3.0 min, the winners starting behind.
COMEBACK = [0.5, 0.3, 0.25, 0.6, 0.85, 0.9]
# Rises 55% -> 90% with the winners never behind.
WIRE_TO_WIRE = [0.55, 0.6, 0.6, 0.65, 0.9, 0.95]
# 49% -> 92%: a big rise, but from level, not from behind.
LEVEL_START = [0.49, 0.5, 0.55, 0.8, 0.92, 0.95]


def _turning_point(probs: list[float] | None, **overrides: object) -> str | None:
    """The turning-point beat text for ``SKIP_WINS`` (Skip & CoreDawg are team A)."""
    curve = corpus.win_prob_over_time(probs) if probs is not None else None
    narrative = match_narrative.build_narrative(
        SKIP_WINS, _details(win_prob_over_time=curve, **overrides)
    )
    beats = [b for b in narrative.beats if b.kind == "turning_point"]
    return beats[0].text if beats else None


def test_the_turning_point_names_the_window_the_odds_and_what_was_destroyed() -> None:
    text = _turning_point(
        COMEBACK,
        kill_events=[
            _kill(3000, "Skip", "Syn", at_minute=2.0),
            _kill(500, "Syn", "Skip", at_minute=2.5),
        ],
    )
    assert text is not None
    assert text.startswith("Turning point:")
    assert "odds for Skip & CoreDawg went from 25% to 90%" in text
    assert "between 1.5 and 3.0 min" in text
    assert "they destroyed $3,000 and lost $500" in text


def test_kills_outside_the_window_are_not_attributed_to_it() -> None:
    text = _turning_point(
        COMEBACK,
        kill_events=[
            _kill(3000, "Skip", "Syn", at_minute=2.0),
            _kill(99_000, "Skip", "Syn", at_minute=20.0),
        ],
    )
    assert text is not None and "$3,000" in text and "99,000" not in text


def test_only_a_swing_from_clearly_behind_is_a_turning_point() -> None:
    kills = [_kill(3000, "Skip", "Syn", at_minute=2.0)]
    assert (_turning_point(COMEBACK, kill_events=kills) or "").startswith(
        "Turning point:"
    )
    for level in (WIRE_TO_WIRE, LEVEL_START):
        assert (_turning_point(level, kill_events=kills) or "").startswith(
            "Decisive stretch:"
        )


def test_a_swing_with_nothing_under_it_is_not_a_moment() -> None:
    """The model catching up to a game that had already been decided."""
    assert _turning_point(COMEBACK) is None


def test_cheap_trades_alone_do_not_explain_a_swing() -> None:
    cheap = _kill(match_narrative.TURNING_POINT_MIN_VALUE - 1, at_minute=2.0)
    assert _turning_point(COMEBACK, kill_events=[cheap]) is None


def test_a_launch_inside_the_window_explains_it_and_one_outside_does_not() -> None:
    text = _turning_point(
        COMEBACK,
        timeline_events=[
            _activation("Skip", "ScudStorm", 2.5),
            _activation("Syn", "NuclearMissile", 20.0),
        ],
    )
    assert text is not None
    assert "Skip launched the ScudStorm superweapon" in text
    assert "NuclearMissile" not in text


def test_a_player_going_hunted_inside_the_window_is_named() -> None:
    text = _turning_point(COMEBACK, time_to_hunted={"Syn": 2.2})
    assert text is not None and "Syn went hunted" in text


def test_no_curve_means_no_turning_point() -> None:
    assert _turning_point(None, kill_events=[_kill(3000, at_minute=2.0)]) is None
