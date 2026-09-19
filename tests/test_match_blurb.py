"""Which matches get an LLM caption, what the model is shown, and what it costs.

Most of what is pinned here is a refusal: below the bar nothing is picked, a
picked match that already has a blurb is not paid for twice, and a provider
error keeps what was already written. Every test replaces ``llm.generate``, so
none can reach a provider.
"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan import game_night, match_narrative, queries
from radarvan.api_types import GameNightHighlight
from radarvan.commentary import llm, match_blurb
from radarvan.db import MatchBlurbCache
from radarvan.match_interest import MIN_INTEREST_FOR_BLURB, Interest
from radarvan.repositories import MatchBlurbRepo

import corpus
from corpus import BACK_AND_FORTH, STOMP

NIGHT = corpus.match(1, day=5).date


def _night(curves: dict[int, list[float]]) -> queries.NightGames:
    games = [corpus.match(i, day=5) for i in curves]
    details = {i: corpus.curve_details(i, probs) for i, probs in curves.items()}
    return queries.NightGames(
        recap=game_night.build_recap(NIGHT, games, games, details, []),
        played=games,
        counted=games,
        details_by_id=details,
    )


@pytest.fixture
def repo():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite://")
    MatchBlurbCache.__table__.create(engine)
    with Session(engine) as session:
        yield MatchBlurbRepo(session)


class _FakeProvider:
    """Stands in for ``llm.generate``; records every prompt it is handed."""

    def __init__(self) -> None:
        self.prompts: list[llm.Prompt] = []
        self.fail_on_call: int | None = None

    def __call__(self, prompt: llm.Prompt, *, kind: str, label: str) -> str:
        self.prompts.append(prompt)
        if len(self.prompts) == self.fail_on_call:
            raise llm.CommentaryGenerationError("provider down")
        return f"Caption {len(self.prompts)}."


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> _FakeProvider:
    fake = _FakeProvider()
    monkeypatch.setattr(llm, "generate", fake)
    monkeypatch.setattr(llm, "active_provider", lambda: "test")
    return fake


# --- who gets a blurb ---------------------------------------------------------


def test_a_lively_game_is_picked_and_a_stomp_beside_it_is_not() -> None:
    picks = match_blurb.pick_candidates(_night({1: STOMP, 2: BACK_AND_FORTH}))
    assert [p.match.id for p in picks] == [2]
    assert picks[0].interest.score >= MIN_INTEREST_FOR_BLURB


def test_a_night_can_never_cost_more_than_the_cap() -> None:
    picks = match_blurb.pick_candidates(
        _night(dict.fromkeys(range(1, 9), BACK_AND_FORTH))
    )
    assert len(picks) == match_blurb.MAX_BLURBS_PER_NIGHT


def test_a_game_without_parsed_details_is_never_picked() -> None:
    unparsed = _night({1: BACK_AND_FORTH})._replace(details_by_id={})
    assert match_blurb.pick_candidates(unparsed) == []


# --- what the model is shown --------------------------------------------------


def _prompt_for(curve: list[float]) -> llm.Prompt:
    pick = match_blurb.pick_candidates(_night({1: curve}))[0]
    narrative = match_narrative.build_narrative(pick.match, pick.details)
    return match_blurb.build_prompt(narrative, pick.interest)


def test_the_prompt_carries_the_game_its_timeline_and_why_it_was_picked() -> None:
    message = _prompt_for(BACK_AND_FORTH).user_message
    assert "Skip & CoreDawg beat Syn & Pancake" in message
    assert "LINEUP" in message
    assert "Turning point" in message
    why = message.split("WHY THIS GAME")[1]
    assert "the lead changed hands 3 times" in why
    assert '"they" = the winners' in why


def test_the_result_beat_is_not_repeated_after_the_headline() -> None:
    assert "took it at" not in _prompt_for(BACK_AND_FORTH).user_message


def test_the_system_prompt_holds_the_rules_the_nightly_recap_holds() -> None:
    system = match_blurb.SYSTEM_PROMPT
    assert "Never state, imply, or invent a player's skill rating" in system
    assert "never as objective odds" in system
    assert "Never invent a detail" in system
    assert "randomized" in system


def test_a_tournament_game_is_flagged_in_the_prompt() -> None:
    narrative = match_narrative.build_narrative(
        corpus.match(1, day=5), corpus.curve_details(1, BACK_AND_FORTH)
    ).model_copy(update={"tournament": "spring-cup - Winners Final"})
    prompt = match_blurb.build_prompt(narrative, Interest(0.7, ["a reason"]))
    assert "[TOURNAMENT: spring-cup - Winners Final]" in prompt.user_message


# --- what it costs ------------------------------------------------------------


def test_each_pick_is_captioned_and_stored(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    night = _night({1: BACK_AND_FORTH, 2: BACK_AND_FORTH})
    run = asyncio.run(match_blurb.generate_night_blurbs(night, repo))
    assert run.date == NIGHT
    assert sorted(run.generated) == sorted(run.picked) == [1, 2]
    assert len(provider.prompts) == 2
    assert set(repo.get_blurbs([1, 2]).values()) == {"Caption 1.", "Caption 2."}


def test_running_a_captioned_night_again_spends_nothing(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    night = _night({1: BACK_AND_FORTH})
    asyncio.run(match_blurb.generate_night_blurbs(night, repo))
    again = asyncio.run(match_blurb.generate_night_blurbs(night, repo))
    assert again.generated == []
    assert again.picked == [1]
    assert len(provider.prompts) == 1


def test_force_pays_again_and_replaces_the_blurb(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    night = _night({1: BACK_AND_FORTH})
    asyncio.run(match_blurb.generate_night_blurbs(night, repo))
    asyncio.run(match_blurb.generate_night_blurbs(night, repo, force=True))
    assert len(provider.prompts) == 2
    assert repo.get_blurbs([1]) == {1: "Caption 2."}


def test_a_provider_error_keeps_what_was_already_paid_for(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    provider.fail_on_call = 2
    night = _night({1: BACK_AND_FORTH, 2: BACK_AND_FORTH, 3: BACK_AND_FORTH})
    with pytest.raises(llm.CommentaryGenerationError):
        asyncio.run(match_blurb.generate_night_blurbs(night, repo))
    assert len(provider.prompts) == 2  # stopped rather than retrying the third
    assert len(repo.get_blurbs([1, 2, 3])) == 1


def test_a_night_of_stomps_picks_nothing_and_makes_no_call(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    run = asyncio.run(match_blurb.generate_night_blurbs(_night({1: STOMP, 2: STOMP}), repo))
    assert run.picked == [] and run.generated == []
    assert provider.prompts == []


# --- attaching a stored blurb --------------------------------------------------


def _card(kind: str, match_id: int) -> GameNightHighlight:
    return GameNightHighlight(kind=kind, title="t", detail="d", match_id=match_id)


def test_only_the_match_of_the_night_card_carries_the_blurb(repo: MatchBlurbRepo) -> None:
    repo.save_blurb(5, "A caption.", "test")
    cards = [
        _card(game_night.MATCH_OF_THE_NIGHT, 5),
        _card("momentum", 5),
        _card("apm", 6),
    ]
    assert [c.blurb for c in queries.with_blurbs(cards, repo)] == ["A caption.", None, None]


def test_attaching_blurbs_does_not_mutate_its_input(repo: MatchBlurbRepo) -> None:
    repo.save_blurb(5, "A caption.", "test")
    cards = [_card(game_night.MATCH_OF_THE_NIGHT, 5)]
    queries.with_blurbs(cards, repo)
    assert cards[0].blurb is None


# --- backfill -----------------------------------------------------------------


def _night_on(day: int, ids: range) -> queries.NightGames:
    games = [corpus.match(i, day=day) for i in ids]
    details = {i: corpus.curve_details(i, BACK_AND_FORTH) for i in ids}
    return queries.NightGames(
        recap=game_night.build_recap(games[0].date, games, games, details, []),
        played=games,
        counted=games,
        details_by_id=details,
    )


def test_a_zero_budget_reports_what_would_be_spent_and_calls_nothing(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    result = asyncio.run(match_blurb.caption_night(_night_on(5, range(1, 4)), repo, 0))
    assert (result.report.picked, result.report.generated, result.report.pending) == (3, 0, 3)
    assert not result.failed
    assert provider.prompts == []


def test_the_budget_stops_a_night_part_way(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    report = asyncio.run(match_blurb.caption_night(_night_on(5, range(1, 4)), repo, 2)).report
    assert (report.generated, report.pending) == (2, 1)
    assert len(provider.prompts) == 2


def test_a_provider_error_still_reports_what_was_written_before_it(
    provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    provider.fail_on_call = 2
    result = asyncio.run(match_blurb.caption_night(_night_on(5, range(1, 4)), repo, 3))
    assert result.failed
    assert (result.report.generated, result.report.pending) == (1, 2)


def _backfill(
    monkeypatch: pytest.MonkeyPatch, repo: MatchBlurbRepo, nights: dict, **kwargs: object
):  # type: ignore[no-untyped-def]
    from radarvan.routes.game_night import backfill_match_blurbs

    async def build(night, all_games, competitive, db_manager):  # type: ignore[no-untyped-def]
        return nights[night]

    monkeypatch.setattr(queries, "build_night_recap", build)
    all_games = [g for n in nights.values() for g in n.played]
    return asyncio.run(
        backfill_match_blurbs(all_games, [], blurbs=repo, **{"days": 400, **kwargs})  # type: ignore[arg-type]
    )


def test_the_backfill_shares_one_budget_across_nights_newest_first(
    monkeypatch: pytest.MonkeyPatch, provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    older, newer = _night_on(5, range(1, 4)), _night_on(6, range(11, 13))
    report = _backfill(
        monkeypatch, repo, {older.recap.date: older, newer.recap.date: newer}, max_to_update=4
    )
    assert [n.date for n in report.nights] == [newer.recap.date, older.recap.date]
    assert [n.generated for n in report.nights] == [2, 2]
    assert (report.generated, report.pending, report.stopped) == (4, 1, False)
    assert len(provider.prompts) == 4


def test_a_dry_run_backfill_spends_nothing_and_needs_no_provider(
    monkeypatch: pytest.MonkeyPatch, provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    monkeypatch.setattr(llm, "commentary_available", lambda: False)
    night = _night_on(5, range(1, 4))
    report = _backfill(monkeypatch, repo, {night.recap.date: night}, max_to_update=0)
    assert (report.generated, report.pending) == (0, 3)
    assert provider.prompts == []


def test_the_backfill_never_overwrites_and_a_rerun_spends_nothing(
    monkeypatch: pytest.MonkeyPatch, provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    night = _night_on(5, range(1, 4))
    nights = {night.recap.date: night}
    _backfill(monkeypatch, repo, nights, max_to_update=10)
    again = _backfill(monkeypatch, repo, nights, max_to_update=10)
    assert (again.generated, again.pending) == (0, 0)
    assert len(provider.prompts) == 3


def test_a_provider_error_stops_the_backfill_and_hides_later_nights(
    monkeypatch: pytest.MonkeyPatch, provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    provider.fail_on_call = 1
    older, newer = _night_on(5, range(1, 4)), _night_on(6, range(11, 14))
    report = _backfill(
        monkeypatch, repo, {older.recap.date: older, newer.recap.date: newer}, max_to_update=9
    )
    assert report.stopped
    assert [n.date for n in report.nights] == [newer.recap.date]


def test_the_backfill_refuses_bad_input_and_a_busy_generator(
    monkeypatch: pytest.MonkeyPatch, provider: _FakeProvider, repo: MatchBlurbRepo
) -> None:
    from fastapi import HTTPException

    night = _night_on(5, range(1, 4))
    nights = {night.recap.date: night}
    for bad in ({"days": 0}, {"max_to_update": -1}):
        with pytest.raises(HTTPException) as bad_input:
            _backfill(monkeypatch, repo, nights, **bad)
        assert bad_input.value.status_code == 400

    monkeypatch.setattr(llm, "commentary_available", lambda: False)
    with pytest.raises(HTTPException) as no_provider:
        _backfill(monkeypatch, repo, nights, max_to_update=3)
    assert no_provider.value.status_code == 503

    held = asyncio.Lock()
    asyncio.run(held.acquire())
    monkeypatch.setattr(match_blurb, "generation_lock", held)
    with pytest.raises(HTTPException) as busy:
        _backfill(monkeypatch, repo, nights, max_to_update=0)
    assert busy.value.status_code == 409
    assert provider.prompts == []
