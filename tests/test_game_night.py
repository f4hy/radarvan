"""The deterministic game-night recap and the once-a-night LLM prompt.

The recap is the free half of the page, so it is the half with rules worth
pinning: which games the records are computed over, that a streak is a run
within the night rather than across the corpus, and that the highlights never
surface a rating level (only a win probability, which is allowed - see the
ratings note in CLAUDE.md).
"""

from datetime import UTC, date, datetime, timedelta

from radarvan import game_night, match_narrative, queries, schedule, utils
from radarvan.api_types import APM, FirstBlood, MatchDetails, Team, TimelineEvent
from radarvan.commentary import night_summary
from radarvan.player_rating import GameUpset

import corpus

NIGHT = date(2026, 1, 5)


def _details(match_id: int, **overrides: object) -> MatchDetails:
    base: dict[str, object] = {
        "match_id": match_id,
        "costs": [],
        "apms": [],
        "upgrade_events": {},
        "stats_data": {},
        "player_summary": [],
    }
    base.update(overrides)
    return MatchDetails(**base)  # type: ignore[arg-type]


def _recap(
    all_matches: list[object],
    counted: list[object] | None = None,
    details: dict[int, MatchDetails] | None = None,
    upsets: list[GameUpset] | None = None,
) -> object:
    return game_night.build_recap(
        NIGHT,
        all_matches,  # type: ignore[arg-type]
        counted if counted is not None else all_matches,  # type: ignore[arg-type]
        details or {},
        upsets or [],
    )


def test_an_empty_night_is_a_zeroed_recap_not_an_error() -> None:
    recap = _recap([])
    assert recap.match_count == 0
    assert recap.players == []
    assert recap.started_at is None
    assert recap.ai_summary is None


def test_match_count_is_every_game_but_records_use_the_counted_set() -> None:
    """A comp-stomp night shows games played and no W-L table."""
    played = [corpus.match(i, day=5) for i in (1, 2, 3)]
    recap = _recap(played, counted=played[:1])
    assert recap.match_count == 3
    assert recap.counted_matches == 1
    assert sum(line.games for line in recap.players) == 4  # one 2v2


def test_undecided_games_are_dropped_from_the_records() -> None:
    decided = corpus.match(1, day=5)
    undecided = corpus.match(2, day=5, winner=Team.NONE)
    recap = _recap([decided, undecided])
    assert recap.match_count == 2
    assert recap.counted_matches == 1


def test_standings_are_ordered_by_wins_then_losses() -> None:
    recap = _recap([corpus.match(i, day=5) for i in (1, 2, 3)])
    assert [line.player for line in recap.players[:2]] == ["CoreDawg", "Skip"]
    assert recap.players[0].wins == 3
    assert recap.players[0].losses == 0
    assert recap.players[-1].wins == 0


def test_best_streak_is_a_run_within_the_night_in_play_order() -> None:
    games = [
        corpus.match(1, day=5, winner=Team.ONE),
        corpus.match(2, day=5, winner=Team.TWO),
        corpus.match(3, day=5, winner=Team.ONE),
        corpus.match(4, day=5, winner=Team.ONE),
    ]
    recap = _recap(games)
    skip = next(line for line in recap.players if line.player == "Skip")
    assert skip.wins == 3
    assert skip.best_streak == 2


def test_best_apm_comes_from_the_night_and_is_absent_without_details() -> None:
    game = corpus.match(1, day=5)
    without = _recap([game])
    assert all(line.best_apm is None for line in without.players)

    with_apm = _recap(
        [game],
        details={
            1: _details(
                1,
                apms=[APM(player_name="Skip", action_count=1, minutes=1.0, apm=140.0)],
            )
        },
    )
    skip = next(line for line in with_apm.players if line.player == "Skip")
    assert skip.best_apm == 140.0


def test_an_observer_changes_nothing_about_the_night() -> None:
    """Adding a spectator must be a no-op - see CLAUDE.md."""
    plain = _recap([corpus.match(1, day=5)])
    watched = _recap([corpus.match(1, day=5, extra_players=(corpus.observer(),))])
    assert plain == watched
    assert "Gorn" not in {line.player for line in watched.players}


def test_formats_and_maps_are_counted_over_every_game() -> None:
    games = [
        corpus.match(1, day=5, map_name="Bitter Winter"),
        corpus.match(2, day=5, map_name="Bitter Winter"),
        corpus.match(
            3,
            day=5,
            map_name="Tournament Desert",
            team_one=corpus.TEAM_ONE[:1],
            team_two=corpus.TEAM_TWO[:1],
        ),
    ]
    recap = _recap(games)
    assert recap.formats == {"2v2": 2, "1v1": 1}
    assert list(recap.maps) == ["Bitter Winter", "Tournament Desert"]


def test_upsets_are_narrowed_to_this_night_and_shown_as_a_probability() -> None:
    tonight = corpus.match(1, day=5)
    upsets = [
        GameUpset(
            match_id=999,
            at_date=NIGHT,
            favored_team=1,
            favored_win_prob=0.99,
            favored_players=["Elsewhere"],
            winning_team=2,
            winner_win_prob=0.01,
            winner_players=["Nobody"],
        ),
        GameUpset(
            match_id=1,
            at_date=NIGHT,
            favored_team=2,
            favored_win_prob=0.80,
            favored_players=["Syn", "Pancake"],
            winning_team=1,
            winner_win_prob=0.20,
            winner_players=["Skip", "CoreDawg"],
        ),
    ]
    recap = _recap([tonight], upsets=upsets)
    upset = next(h for h in recap.highlights if h.kind == "upset")
    # The bigger surprise belongs to another night's match and must not win.
    assert upset.match_id == 1
    assert "20% to win" in upset.detail
    # Attributed to the model rather than stated as fact - it is a pre-game
    # estimate from a rating system fitted to this group, not observed odds.
    assert "our model projected" in upset.detail


def test_highlights_report_no_rating_level_only_probabilities() -> None:
    """A level would defeat the admin gate on the ratings page - CLAUDE.md."""
    recap = _recap(
        [corpus.match(1, day=5)],
        upsets=[
            GameUpset(
                match_id=1,
                at_date=NIGHT,
                favored_team=2,
                favored_win_prob=0.7,
                favored_players=["Syn"],
                winning_team=1,
                winner_win_prob=0.3,
                winner_players=["Skip"],
            )
        ],
    )
    rendered = " ".join(h.detail for h in recap.highlights).lower()
    for banned in ("ordinal", "rating", "mu", "rank #"):
        assert banned not in rendered


def test_detail_highlights_come_from_the_parsed_replay() -> None:
    games = [corpus.match(1, day=5), corpus.match(2, day=5)]
    details = {
        1: _details(
            1,
            first_blood=FirstBlood(attacker="Skip", victim="Syn", atMinute=4.0),
            time_to_hunted={"Syn": 20.0},
        ),
        2: _details(
            2,
            first_blood=FirstBlood(attacker="CoreDawg", victim="Pancake", atMinute=1.5),
            timeline_events=[
                TimelineEvent(
                    player_name="Skip",
                    at_minute=25.0,
                    event_name="ScudStorm",
                    event_type="superweapon_activated",
                )
            ],
        ),
    }
    recap = _recap(games, details=details)
    kinds = {h.kind: h for h in recap.highlights}
    assert kinds["first_blood"].detail == "CoreDawg at 1.5 min"
    assert kinds["first_blood"].match_id == 2
    assert "ScudStorm" in kinds["superweapon"].detail
    assert kinds["hunted"].detail == "Syn went hunted at 20.0 min"


def _activation(player: str, name: str, minute: float) -> TimelineEvent:
    return TimelineEvent(
        player_name=player,
        at_minute=minute,
        event_name=name,
        event_type="superweapon_activated",
    )


def test_generals_powers_are_counted_apart_from_superweapons() -> None:
    """A Spectre Gunship must never be reported as a superweapon launch.

    The engine tags several generals-panel powers ``Superweapon*``, so the
    highlight has to narrow to ``BASE_SUPERWEAPON_LAUNCHES`` the way
    ``superlatives`` does - see CLAUDE.md.
    """
    games = [corpus.match(1, day=5)]
    recap = _recap(
        games,
        details={
            1: _details(
                1,
                timeline_events=[
                    _activation("Skip", "SpectreGunship", 9.9),
                    _activation("Skip", "SpectreGunship", 14.0),
                    _activation("Syn", "ScudStorm", 22.0),
                ],
            )
        },
    )
    kinds = {h.kind: h for h in recap.highlights}
    # The first *superweapon* is the Scud Storm at 22 min, not the 9.9 gunship.
    assert "ScudStorm" in kinds["superweapon"].detail
    assert "22.0 min" in kinds["superweapon"].detail
    assert "SpectreGunship" not in kinds["superweapon"].detail
    assert kinds["power"].detail == "Skip called in 2"


def test_a_night_of_only_generals_powers_reports_no_superweapon() -> None:
    recap = _recap(
        [corpus.match(1, day=5)],
        details={
            1: _details(
                1,
                timeline_events=[
                    _activation("Skip", "SpectreGunship", 9.9),
                    _activation("Skip", "EMPPulse", 12.0),
                ],
            )
        },
    )
    assert not [h for h in recap.highlights if h.kind == "superweapon"]


def test_record_cards_need_a_meaningful_sample() -> None:
    """A 1-0 is not the best record of the night."""
    recap = _recap([corpus.match(1, day=5)])
    assert not [h for h in recap.highlights if h.kind == "best_record"]

    many = [corpus.match(i, day=5) for i in range(1, 4)]
    recap = _recap(many)
    best = next(h for h in recap.highlights if h.kind == "best_record")
    assert "3-0" in best.detail


# --- the LLM prompt ----------------------------------------------------------


def test_the_prompt_renders_the_night_without_calling_a_provider() -> None:
    games = [corpus.match(1, day=5), corpus.match(2, day=5)]
    recap = _recap(games)
    narratives = [match_narrative.build_narrative(game, None) for game in games]
    prompt = night_summary.build_prompt(recap, narratives)
    assert "never seen" not in prompt.system  # sanity: it's the night guidelines
    assert "game night" in prompt.system.lower()
    assert "<game_night>" in prompt.user_message
    assert "STANDINGS" in prompt.user_message
    assert "Skip: 2-0" in prompt.user_message


def test_the_prompt_forbids_rating_levels() -> None:
    """The one rule this feature cannot get wrong - see CLAUDE.md."""
    lowered = night_summary.SYSTEM_PROMPT.lower()
    assert "never state, imply, or invent a player's skill rating" in lowered.replace(
        "**", ""
    )


def test_rendered_games_are_capped() -> None:
    games = [corpus.match(i, day=5) for i in range(1, 40)]
    recap = _recap(games)
    narratives = [match_narrative.build_narrative(g, None) for g in games]
    rendered = night_summary.render_night(recap, narratives)
    assert rendered.count("Game ") <= night_summary.MAX_GAMES_RENDERED + 1


# --- which night the nightly job picks ---------------------------------------


def test_latest_closed_night_never_picks_the_night_in_progress() -> None:
    """The row is permanent, so summarizing a live evening would freeze it."""
    from datetime import UTC, datetime

    from radarvan import utils
    from radarvan.queries import latest_closed_night

    tonight = utils.game_night_date_of(datetime.now(UTC))
    games = [
        corpus.match(1, day=5),
        corpus.match(2, day=5).model_copy(update={"date": tonight}),
    ]
    assert latest_closed_night(games) == corpus.match(1, day=5).date
    assert latest_closed_night(games) < tonight


def test_latest_closed_night_is_none_when_only_tonight_has_games() -> None:
    from datetime import UTC, datetime

    from radarvan import utils
    from radarvan.queries import latest_closed_night

    tonight = utils.game_night_date_of(datetime.now(UTC))
    games = [corpus.match(1, day=5).model_copy(update={"date": tonight})]
    assert latest_closed_night(games) is None


def test_the_prompt_stamps_every_game_with_its_start_time() -> None:
    """Two disjoint sittings on one date are only visible from the clock."""
    games = [corpus.match(1, day=5), corpus.match(2, day=5)]
    recap = _recap(games)
    narratives = [match_narrative.build_narrative(g, None) for g in games]
    # Scoped to the per-game section: the night's summary line carries the
    # same clock time, and counting the whole document would pass on that.
    per_game = night_summary.render_night(recap, narratives).split("GAME BY GAME")[1]
    # corpus builds every match at 12:00 UTC = 7am US Eastern (EST in January).
    assert per_game.count("7:00am") == len(games)


def test_the_prompt_renders_times_in_the_groups_own_timezone() -> None:
    """UTC would put an evening on the wrong side of midnight."""
    recap = _recap([corpus.match(1, day=5)])
    assert recap.started_at is not None
    # 12:00 UTC is 07:00 America/New_York, not 12:00.
    assert "7:00am" in night_summary._local(recap.started_at)


def test_a_tournament_game_is_flagged_in_the_prompt() -> None:
    from radarvan.api_types import TournamentTag

    casual = corpus.match(1, day=5)
    tournament = corpus.match(2, day=5).model_copy(
        update={
            "tournament": TournamentTag(
                slug="spring-cup", stage="WB1-1", round_name="Winners Round 1"
            )
        }
    )
    games = [casual, tournament]
    recap = _recap(games)
    narratives = [match_narrative.build_narrative(g, None) for g in games]
    rendered = night_summary.render_night(recap, narratives)
    assert rendered.count("[TOURNAMENT: spring-cup - Winners Round 1]") == 1


def test_a_night_of_casual_games_carries_no_tournament_marker() -> None:
    games = [corpus.match(i, day=5) for i in (1, 2)]
    recap = _recap(games)
    narratives = [match_narrative.build_narrative(g, None) for g in games]
    assert "TOURNAMENT" not in night_summary.render_night(recap, narratives)


def test_the_prompt_separates_superweapons_from_generals_powers() -> None:
    """The rule this feature got wrong first time round."""
    lowered = night_summary.SYSTEM_PROMPT.lower()
    assert "never call a gunship a superweapon" in lowered


def test_the_prompt_warns_that_a_night_may_be_two_sittings() -> None:
    assert "not necessarily one sitting" in night_summary.SYSTEM_PROMPT


def test_the_prompt_frames_win_probability_as_a_model_projection() -> None:
    """It is our own (imperfect) rating model, not objective odds."""
    assert "not a fact" in night_summary.SYSTEM_PROMPT
    assert "never as objective odds" in night_summary.SYSTEM_PROMPT


def _night(match_id: int, night: date) -> object:
    """A corpus match keyed to a given game night."""
    return corpus.match(match_id, day=5).model_copy(update={"date": night})


def test_the_backfill_window_never_includes_the_live_night() -> None:
    """The same rule the nightly job follows: a stored recap is permanent, so
    an evening still being played must stay out of reach of the backfill."""
    tonight = utils.game_night_date_of(datetime.now(UTC))
    games = [_night(1, tonight), _night(2, tonight - timedelta(days=1))]
    assert queries.closed_nights_within(games, 7) == [tonight - timedelta(days=1)]  # type: ignore[arg-type]


def test_the_backfill_window_is_counted_in_game_night_keys() -> None:
    """``days`` back from tonight, inclusive at the far end, newest first."""
    tonight = utils.game_night_date_of(datetime.now(UTC))
    inside = [tonight - timedelta(days=n) for n in (1, 3, 7)]
    outside = tonight - timedelta(days=8)
    games = [_night(i, night) for i, night in enumerate([*inside, outside])]
    assert queries.closed_nights_within(games, 7) == inside  # type: ignore[arg-type]


def test_one_stray_upload_is_not_a_game_night_for_either_caller() -> None:
    """The floor lives with the generator so the job and the backfill share it."""
    assert night_summary.MIN_MATCHES_FOR_SUMMARY > 1
    assert schedule.MIN_MATCHES_FOR_SUMMARY == night_summary.MIN_MATCHES_FOR_SUMMARY
