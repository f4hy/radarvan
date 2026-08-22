"""The deterministic game-night recap and the once-a-night LLM prompt.

The recap is the free half of the page, so it is the half with rules worth
pinning: which games the records are computed over, that a streak is a run
within the night rather than across the corpus, and that the highlights never
surface a rating level (only a win probability, which is allowed - see the
ratings note in CLAUDE.md).
"""

from datetime import date

from radarvan import game_night, match_narrative
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
                    event_name="Scud Storm",
                    event_type="superweapon_activated",
                )
            ],
        ),
    }
    recap = _recap(games, details=details)
    kinds = {h.kind: h for h in recap.highlights}
    assert kinds["first_blood"].detail == "CoreDawg at 1.5 min"
    assert kinds["first_blood"].match_id == 2
    assert "Scud Storm" in kinds["superweapon"].detail
    assert kinds["hunted"].detail == "Syn went hunted at 20.0 min"


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
