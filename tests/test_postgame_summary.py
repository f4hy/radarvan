"""Post-game set recap: per-game data reduction, the plain-text render, and
the route's readiness gate. No LLM calls (the generator is stubbed or never
reached)."""

from datetime import UTC, date, datetime
from typing import cast

import pytest

from radarvan.api_types import (
    APM,
    BracketMatchGames,
    BracketMatchOutput,
    BracketTournamentOutput,
    BuildOrder,
    BuildOrderEntry,
    FirstBlood,
    General,
    KillEventOutput,
    MatchDetails,
    MatchInfo,
    ObjectSummary,
    Player,
    PlayerSummary,
    SeedSource,
    Team,
    TimelineEvent,
    TournamentTag,
)
from radarvan.commentary import postgame_summary, summary_data
from radarvan.db_utils import ReplayManager
from radarvan.player_role import PlayerRole
from radarvan.repositories import BracketRepo, BracketSummaryRepo, TournamentRepo
from radarvan.routes import commentary


def _match(
    match_id: int,
    series_index: int,
    map_name: str,
    winner: tuple[str, General],
    loser: tuple[str, General],
    minutes: float = 10.0,
) -> MatchInfo:
    winner_name, winner_general = winner
    loser_name, loser_general = loser
    return MatchInfo(
        id=match_id,
        timestamp=datetime(2026, 8, 8, 1, series_index, tzinfo=UTC),
        date=date(2026, 8, 7),
        map=f"userdata/maps/{map_name}",
        winning_team=Team.ONE,
        players=[
            Player(
                name=winner_name,
                general=winner_general,
                team=Team.ONE,
                color="green",
                won=True,
                role=PlayerRole.HUMAN,
            ),
            Player(
                name=loser_name,
                general=loser_general,
                team=Team.TWO,
                color="orange",
                won=False,
                role=PlayerRole.HUMAN,
            ),
            # An observer in every game - the recap must never mention them
            # or count them as a competitor (see CLAUDE.md).
            Player(
                name="Caster",
                general=General.UNRECOGNIZED,
                team=Team.OBSERVER,
                color="grey",
                won=False,
                role=PlayerRole.OBSERVER,
            ),
        ],
        duration_minutes=minutes,
        filename=f"upload:{match_id}",
        tournament=TournamentTag(
            slug="2026_1v1_bracket",
            stage="WB1-1",
            round_name="Winners Round 1",
            series_index=series_index,
        ),
    )


def _details(match_id: int, winner: str, loser: str) -> MatchDetails:
    return MatchDetails(
        match_id=match_id,
        costs=[],
        apms=[
            APM(player_name=winner, action_count=400, minutes=10.0, apm=40.0),
            APM(player_name=loser, action_count=300, minutes=10.0, apm=30.0),
        ],
        upgrade_events={},
        stats_data={},
        first_blood=FirstBlood(attacker=winner, victim=loser, atMinute=1.5),
        player_summary=[
            PlayerSummary(
                Name=winner,
                Side="GLA",
                Team=1,
                Win=True,
                Color="green",
                UnitsCreated={},
                BuildingsBuilt={},
                UpgradesBuilt={},
                PowersUsed={"SpecialPowerGLAScudStorm": 1},
                UnitsDestroyed={"Quad": ObjectSummary(Count=10, TotalSpent=8000)},
                BuildingsDestroyed={"Stash": ObjectSummary(Count=2, TotalSpent=3000)},
                UnitsLost={"Rebel": ObjectSummary(Count=4, TotalSpent=800)},
                BuildingsLost={},
            ),
            PlayerSummary(
                Name=loser,
                Side="China",
                Team=2,
                Win=False,
                Color="orange",
                UnitsCreated={},
                BuildingsBuilt={},
                UpgradesBuilt={},
                PowersUsed={},
                UnitsDestroyed={"Tank": ObjectSummary(Count=4, TotalSpent=800)},
                BuildingsDestroyed={},
                UnitsLost={"Quad": ObjectSummary(Count=10, TotalSpent=8000)},
                BuildingsLost={"Stash": ObjectSummary(Count=2, TotalSpent=3000)},
            ),
        ],
        kill_events=[
            KillEventOutput(
                at_minute=2.0,
                killer_player=winner,
                victim_player=loser,
                x=0.0,
                y=0.0,
                killer="Chem_GLAVehicleQuadCannon",
                victim="ChinaTankBattleMaster",
                damage_type="EXPLOSION",
                value=900,
            )
        ],
        player_money_spent={winner: 50000, loser: 40000},
        player_money_collected={winner: 52000, loser: 38000},
        time_to_rank_5={winner: 9.0},
        build_orders={
            winner: BuildOrder(
                buildings=[
                    BuildOrderEntry(at_minute=0.5, name="Barracks", cost=500),
                    BuildOrderEntry(
                        at_minute=0.7, name="SupplyStash", cost=1500, count=2
                    ),
                ],
                units=[],
                # The literal "dummy" upgrade cncstats emits for unnamed
                # upgrades must not reach the prompt.
                upgrades=[BuildOrderEntry(at_minute=1.0, name="dummy", cost=0)],
            )
        },
        timeline_events=[
            TimelineEvent(
                player_name=winner,
                at_minute=8.0,
                event_name="ScudStorm",
                event_type="superweapon_built",
            ),
            TimelineEvent(
                player_name=winner,
                at_minute=9.5,
                event_name="ScudStorm",
                event_type="superweapon_activated",
            ),
            TimelineEvent(
                player_name=winner,
                at_minute=6.0,
                event_name="Rank 4",
                event_type="rank_up",
            ),
        ],
    )


def _bracket_match(
    score_a: int = 3, score_b: int = 1, status: str = "completed"
) -> BracketMatchOutput:
    return BracketMatchOutput(
        match_id="WB1-1",
        bracket="W",
        round_number=1,
        round_name="Winners Round 1",
        player_a="Gorn",
        player_b="Neo",
        best_of=5,
        score_a=score_a,
        score_b=score_b,
        winner="Gorn" if score_a > score_b else "Neo",
        status=status,  # type: ignore[arg-type]
        source_a=SeedSource(seed=1),
        source_b=SeedSource(seed=2),
    )


def _summary_set(games: int = 4) -> summary_data.SummarySet:
    built = []
    for index in range(1, games + 1):
        # Games come in reversed pairs: same map, same two generals, players
        # swapped - which is how the tournament is actually played, and what
        # reverse-pair detection needs to see.
        winner, loser = ("Gorn", "Neo") if index % 2 else ("Neo", "Gorn")
        match = _match(
            match_id=index,
            series_index=index,
            map_name="tournament desert" if index <= 2 else "canyon of the dead",
            # Winner alternates while the generals stay put, so each player
            # takes both sides of the same draw - that is the swap.
            winner=(winner, General.GLA if index <= 2 else General.LASER),
            loser=(loser, General.NUKE if index <= 2 else General.TOXIN),
        )
        game = summary_data.build_summary_game(match, _details(index, winner, loser))
        assert game is not None
        built.append(game)
    return summary_data.build_summary_set(_bracket_match(), built)


def test_build_summary_game_ignores_observers() -> None:
    match = _match(
        1, 1, "tournament desert", ("Gorn", General.GLA), ("Neo", General.NUKE)
    )
    game = summary_data.build_summary_game(match, _details(1, "Gorn", "Neo"))
    assert game is not None
    assert [p.player for p in game.players] == ["Gorn", "Neo"]


def test_build_summary_game_puts_the_winner_first() -> None:
    match = _match(
        1, 1, "tournament desert", ("Neo", General.NUKE), ("Gorn", General.GLA)
    )
    game = summary_data.build_summary_game(match, _details(1, "Neo", "Gorn"))
    assert game is not None
    assert game.players[0].player == "Neo"
    assert game.players[0].won is True
    assert game.players[1].won is False


def test_build_summary_game_without_details_keeps_the_result_line() -> None:
    """A game whose replay details can't be loaded still happened - dropping
    it would make the set look shorter than it was."""
    match = _match(
        1, 1, "tournament desert", ("Gorn", General.GLA), ("Neo", General.NUKE)
    )
    game = summary_data.build_summary_game(match, None)
    assert game is not None
    assert game.players == []
    assert game.outcome.winner == "Gorn"


def test_player_ledger_is_derived_from_details() -> None:
    match = _match(
        1, 1, "tournament desert", ("Gorn", General.GLA), ("Neo", General.NUKE)
    )
    game = summary_data.build_summary_game(match, _details(1, "Gorn", "Neo"))
    assert game is not None
    winner = game.players[0]
    assert winner.apm == 40.0
    assert winner.money_collected == 52000
    assert winner.value_destroyed == 11000
    assert winner.value_lost == 800
    assert winner.units_destroyed == 10
    assert winner.buildings_destroyed == 2
    assert winner.highest_rank == 4
    assert winner.rank_5_minute == 9.0
    assert winner.superweapons_built == ["ScudStorm @ 8.0min"]
    assert winner.superweapons_fired == ["ScudStorm @ 9.5min"]
    # Killer unit names arrive with general/faction prefixes on them.
    assert winner.top_killers[0].name == "VehicleQuadCannon"
    assert winner.powers_used == ["ScudStorm x1"]
    # The "dummy" placeholder upgrade is dropped entirely.
    assert winner.upgrades == []
    assert winner.opening_buildings == [
        "Barracks @ 0.5min",
        "SupplyStash x2 @ 0.7min",
    ]


def test_render_summary_set_is_not_json_and_covers_every_game() -> None:
    rendered = summary_data.render_summary_set(_summary_set(games=4))
    assert "{" not in rendered
    assert "Winners Round 1 (best of 5): Gorn beat Neo 3-1" in rendered
    for index, map_name in enumerate(
        [
            "tournament desert",
            "tournament desert",
            "canyon of the dead",
            "canyon of the dead",
        ],
        start=1,
    ):
        assert f"Game {index} on {map_name}" in rendered
    assert "First blood:" in rendered
    assert "Reversed pairs" in rendered
    assert "Caster" not in rendered


def test_render_summary_set_writes_the_score_from_the_winners_side() -> None:
    """ "beat X 1-3" reads as a typo - the winner's number comes first even
    when the winner is player B."""
    summary = summary_data.build_summary_set(_bracket_match(score_a=1, score_b=3), [])
    assert summary.winner == "Neo"
    assert "Neo beat Gorn 3-1" in summary_data.render_summary_set(summary)


def test_missing_games_note_only_when_replays_are_missing() -> None:
    assert summary_data.missing_games_note(_summary_set(games=4)) == ""
    partial = _summary_set(games=2)
    note = summary_data.missing_games_note(partial)
    assert "only 2 of the 4 games" in note


def test_build_user_message_carries_the_ask_and_the_set() -> None:
    message = postgame_summary.build_user_message(_summary_set(games=4))
    assert "Write the post-game recap for Winners Round 1: Gorn vs Neo." in message
    assert "<set_result>" in message
    assert "Game 4 on canyon of the dead" in message


def test_build_summary_set_rejects_an_unfinished_match() -> None:
    unfinished = _bracket_match().model_copy(update={"winner": None})
    with pytest.raises(ValueError):
        summary_data.build_summary_set(unfinished, [])


# --- route readiness gate ---


class _StubBracketRoutes:
    """Stands in for the two bracket route handlers _recappable_set calls."""

    def __init__(self, match: BracketMatchOutput, linked: list[MatchInfo]) -> None:
        self.match = match
        self.linked = linked

    def bracket(self) -> BracketTournamentOutput:
        return BracketTournamentOutput(
            participant_names=["Gorn", "Neo"],
            players=[],
            matches=[self.match],
            bye_advances=[],
            needs_reset=False,
            revealed=True,
        )

    def games(self) -> BracketMatchGames:
        return BracketMatchGames(match_id=self.match.match_id, linked=self.linked)


def _patch_bracket_routes(
    monkeypatch: pytest.MonkeyPatch,
    match: BracketMatchOutput,
    linked: list[MatchInfo],
) -> None:
    stub = _StubBracketRoutes(match, linked)
    monkeypatch.setattr(
        commentary.bracket_routes,
        "load_match",
        lambda repo, match_id: (object(), {}, object(), object()),
    )
    monkeypatch.setattr(
        commentary.bracket_routes,
        "tournament_for_bracket",
        lambda tournament, tournament_repo: type("T", (), {"id": 7})(),
    )
    monkeypatch.setattr(
        commentary.bracket_routes,
        "get_bracket",
        lambda preview, user, repo: stub.bracket(),
    )
    monkeypatch.setattr(
        commentary.bracket_routes,
        "get_bracket_games",
        lambda match_id, user, repo, tournament_repo, replay_manager: stub.games(),
    )


class _StubSummaryRepo:
    def __init__(self, cached: str | None = None) -> None:
        self.cached = cached
        self.saved: tuple[int, str, str, str] | None = None

    def get_cached_summary(self, tournament_id: int, stage: str) -> str | None:
        return self.cached

    def save_summary(
        self, tournament_id: int, stage: str, summary: str, provider: str
    ) -> None:
        self.saved = (tournament_id, stage, summary, provider)


def _call(
    summary_repo: _StubSummaryRepo, **kwargs: object
) -> commentary.BracketSummaryResponse:
    return commentary.get_bracket_summary(
        "WB1-1",
        repo=cast(BracketRepo, None),
        tournament_repo=cast(TournamentRepo, None),
        summary_repo=cast(BracketSummaryRepo, summary_repo),
        replay_manager=cast(ReplayManager, None),
        **kwargs,  # type: ignore[arg-type]
    )


def _linked(count: int) -> list[MatchInfo]:
    return [
        _match(i, i, "tournament desert", ("Gorn", General.GLA), ("Neo", General.NUKE))
        for i in range(1, count + 1)
    ]


def test_route_not_ready_when_games_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of the gate: a 4-game set with 2 replays on record
    must not be recapped as a 2-0."""
    _patch_bracket_routes(monkeypatch, _bracket_match(), _linked(2))

    def _boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("generate_summary must not be called")

    monkeypatch.setattr(postgame_summary, "generate_summary", _boom)
    result = _call(_StubSummaryRepo())
    assert result.ready is False
    assert result.summary is None


def test_route_not_ready_while_the_set_is_unfinished(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unfinished = _bracket_match(status="ready")
    _patch_bracket_routes(monkeypatch, unfinished, _linked(4))

    def _boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("generate_summary must not be called")

    monkeypatch.setattr(postgame_summary, "generate_summary", _boom)
    assert _call(_StubSummaryRepo()).ready is False


def test_route_returns_cached_summary_without_generating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bracket_routes(monkeypatch, _bracket_match(), _linked(4))

    def _boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("generate_summary must not be called on a cache hit")

    monkeypatch.setattr(postgame_summary, "generate_summary", _boom)
    result = _call(_StubSummaryRepo(cached="**Recap.**"))
    assert result.summary == "**Recap.**"
    assert result.ready is True


def test_route_generates_and_saves_on_a_cache_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_bracket_routes(monkeypatch, _bracket_match(), _linked(4))
    monkeypatch.setattr(
        commentary.matchup_commentary, "commentary_available", lambda: True
    )
    monkeypatch.setattr(
        commentary.matchup_commentary, "active_provider", lambda: "gemini"
    )
    monkeypatch.setattr(
        postgame_summary,
        "generate_summary",
        lambda replay_manager, match, games: "**Fresh recap.**",
    )
    repo = _StubSummaryRepo()
    result = _call(repo)
    assert result.summary == "**Fresh recap.**"
    assert repo.saved == (7, "WB1-1", "**Fresh recap.**", "gemini")


def test_route_403_when_forcing_regeneration_without_admin_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """force_refresh bills a fresh LLM call on every request."""
    from fastapi import HTTPException

    _patch_bracket_routes(monkeypatch, _bracket_match(), _linked(4))
    with pytest.raises(HTTPException) as exc_info:
        _call(_StubSummaryRepo(cached="cached"), force_refresh=True, admin_access=False)
    assert exc_info.value.status_code == 403


def test_route_502_on_generation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    _patch_bracket_routes(monkeypatch, _bracket_match(), _linked(4))
    monkeypatch.setattr(
        commentary.matchup_commentary, "commentary_available", lambda: True
    )

    def _boom(replay_manager: object, match: object, games: object) -> str:
        raise commentary.matchup_commentary.CommentaryGenerationError("boom")

    monkeypatch.setattr(postgame_summary, "generate_summary", _boom)
    with pytest.raises(HTTPException) as exc_info:
        _call(_StubSummaryRepo())
    assert exc_info.value.status_code == 502
