"""Replacement operations publish all rows together or preserve the previous set."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import event

from radarvan.api_types import SetBracketGamesRequest, Statistic
from radarvan.db import (
    BracketMatchState,
    BracketPlayer,
    BracketTournament,
    ComputedStatistic,
    Tournament,
    TournamentGame,
    User,
)
from radarvan.db_utils import DatabaseManager, ReplayManager
from radarvan.repositories.bracket import BracketRepo
from radarvan.repositories.stats import StatsRepo
from radarvan.repositories.tournaments import TournamentRepo


@pytest.fixture
def manager(tmp_path: Path) -> Iterator[DatabaseManager]:
    # A file gives the observing session its own connection and transaction.
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'replacements.db'}")
    for table in (ComputedStatistic, Tournament, TournamentGame):
        table.__table__.create(manager.engine)
    yield manager
    manager.engine.dispose()


def _stat(name: str, value: float | str | None = None) -> Statistic:
    return Statistic(stat_name=name, value=value, date_computed=date(2026, 9, 13))


def _stats(manager: DatabaseManager) -> list[Statistic]:
    with manager.get_session() as session:
        return StatsRepo(session).get_computed_stats()


@pytest.mark.parametrize("auto_commit", [True, False])
@pytest.mark.parametrize(
    "replacement", [[], [_stat("new", 42), _stat("text", "value")]]
)
def test_stats_publish_only_the_complete_replacement(
    manager: DatabaseManager, auto_commit: bool, replacement: list[Statistic]
) -> None:
    previous = [_stat("old", 1)]
    with manager.get_session() as session:
        StatsRepo(session).replace_computed_stats(previous)

    with manager.get_session() as session:

        @event.listens_for(session, "after_flush_postexec")
        def before_publish(*_: object) -> None:
            assert _stats(manager) == previous

        StatsRepo(session, auto_commit=auto_commit).replace_computed_stats(replacement)
        if not auto_commit:
            assert _stats(manager) == previous

    assert _stats(manager) == replacement


@pytest.mark.parametrize("auto_commit", [True, False])
@pytest.mark.parametrize("failure_event", ["after_flush_postexec", "before_commit"])
def test_failed_stats_replacement_preserves_previous_snapshot(
    manager: DatabaseManager, auto_commit: bool, failure_event: str
) -> None:
    previous = [_stat("old", 1), _stat("old text", "retained")]
    with manager.get_session() as session:
        StatsRepo(session).replace_computed_stats(previous)

    with (
        pytest.raises(RuntimeError, match="publication failed"),
        manager.get_session() as session,
    ):

        @event.listens_for(session, failure_event)
        def fail(*_: object) -> None:
            raise RuntimeError("publication failed")

        StatsRepo(session, auto_commit=auto_commit).replace_computed_stats(
            [_stat("new", 99)]
        )

    assert _stats(manager) == previous


@pytest.fixture
def tournament_id(manager: DatabaseManager) -> int:
    with manager.get_session() as session:
        repo = TournamentRepo(session, auto_commit=False)
        tournament = repo.upsert_tournament("cup", "Cup", "double_elimination")
        for match_id, stage, index in [
            (1, "WB1-1", 1),
            (2, "WB1-1", 2),
            (9, "LB1-1", 1),
        ]:
            repo.link_match(
                tournament.id,
                match_id,
                stage=stage,
                round_name="Original",
                series_index=index,
            )
        return tournament.id


def _links(
    manager: DatabaseManager, tournament_id: int
) -> dict[int, tuple[str | None, str | None, int | None, str, bool]]:
    with manager.get_session() as session:
        return {
            row.match_id: (
                row.stage,
                row.round_name,
                row.series_index,
                row.source,
                row.excluded,
            )
            for row in TournamentRepo(session).list_links(
                tournament_id, include_excluded=True
            )
        }


@pytest.mark.parametrize("auto_commit", [True, False])
def test_stage_replacement_publishes_links_and_tombstones_together(
    manager: DatabaseManager, tournament_id: int, auto_commit: bool
) -> None:
    previous = _links(manager, tournament_id)
    with manager.get_session() as session:

        @event.listens_for(session, "after_flush_postexec")
        def before_publish(*_: object) -> None:
            assert _links(manager, tournament_id) == previous

        TournamentRepo(session, auto_commit=auto_commit).replace_stage_links(
            tournament_id, "WB1-1", "Winners Round 1", [4, 2, 3, 2]
        )
        if not auto_commit:
            assert _links(manager, tournament_id) == previous

    assert _links(manager, tournament_id) == {
        1: ("WB1-1", "Original", 1, "manual", True),
        2: ("WB1-1", "Winners Round 1", 2, "manual", False),
        3: ("WB1-1", "Winners Round 1", 3, "manual", False),
        4: ("WB1-1", "Winners Round 1", 1, "manual", False),
        9: previous[9],
    }


@pytest.mark.parametrize("auto_commit", [True, False])
@pytest.mark.parametrize("failure_event", ["after_flush_postexec", "before_commit"])
def test_failed_stage_replacement_restores_exclusions_and_additions(
    manager: DatabaseManager, tournament_id: int, auto_commit: bool, failure_event: str
) -> None:
    previous = _links(manager, tournament_id)
    calls = 0
    with (
        pytest.raises(RuntimeError, match="publication failed"),
        manager.get_session() as session,
    ):

        @event.listens_for(session, failure_event)
        def fail(*_: object) -> None:
            nonlocal calls
            calls += 1
            # Fail after an exclusion and an insert have reached the DB.
            if failure_event == "before_commit" or calls == 2:
                raise RuntimeError("publication failed")

        TournamentRepo(session, auto_commit=auto_commit).replace_stage_links(
            tournament_id, "WB1-1", "Winners Round 1", [4, 2, 3]
        )

    assert _links(manager, tournament_id) == previous


def test_empty_stage_replacement_keeps_tombstones_and_can_reinstate_links(
    manager: DatabaseManager, tournament_id: int
) -> None:
    with manager.get_session() as session:
        repo = TournamentRepo(session)
        repo.replace_stage_links(tournament_id, "WB1-1", "Winners Round 1", [])
        assert repo.list_links(tournament_id, stage="WB1-1") == []
        assert {
            row.match_id
            for row in repo.list_links(tournament_id, include_excluded=True)
        } == {1, 2, 9}
        repo.link_match(tournament_id, 1, stage="WB1-1", source="auto")
        assert repo.list_links(tournament_id, stage="WB1-1") == []
        repo.replace_stage_links(tournament_id, "WB1-1", "Winners Round 1", [2])

    links = _links(manager, tournament_id)
    assert links[1][-1] is True
    assert links[2] == ("WB1-1", "Winners Round 1", 1, "manual", False)
    assert links[9][-1] is False


def test_replacements_can_participate_in_one_outer_transaction(
    manager: DatabaseManager, tournament_id: int
) -> None:
    previous_links = _links(manager, tournament_id)
    with manager.get_session() as session:
        StatsRepo(session).replace_computed_stats([_stat("old")])

    with (
        pytest.raises(RuntimeError, match="later work failed"),
        manager.get_session() as session,
    ):
        StatsRepo(session, auto_commit=False).replace_computed_stats([_stat("new")])
        TournamentRepo(session, auto_commit=False).replace_stage_links(
            tournament_id, "WB1-1", "Winners Round 1", [4]
        )
        raise RuntimeError("later work failed")

    assert _stats(manager) == [_stat("old")]
    assert _links(manager, tournament_id) == previous_links


@pytest.mark.parametrize("fail_commit", [False, True])
def test_bracket_route_invalidates_only_after_successful_publication(
    manager: DatabaseManager,
    tournament_id: int,
    monkeypatch: pytest.MonkeyPatch,
    fail_commit: bool,
) -> None:
    from radarvan.routes import bracket
    import corpus

    for table in (BracketTournament, BracketPlayer, BracketMatchState):
        table.__table__.create(manager.engine)
    with manager.get_session() as session:
        repo = BracketRepo(session, auto_commit=False)
        active = repo.create([(seed, f"Player {seed}") for seed in range(1, 10)])
        repo.set_tournament_id(active.id, tournament_id)

    games = {i: corpus.match(i, day=i) for i in range(1, 4)}
    monkeypatch.setattr(bracket, "sorted_deduped_matches", lambda _: games)
    monkeypatch.setattr(bracket.player_ids, "is_tournament_admin", lambda _: True)
    previous = _links(manager, tournament_id)
    invalidations = []

    def invalidate() -> None:
        # A different connection must see the new links before a warmer can run.
        links = _links(manager, tournament_id)
        assert links[1][-1] is True
        assert links[2][-1] is False
        assert links[3][-1] is False
        invalidations.append(True)

    monkeypatch.setattr(bracket, "invalidate_match_caches", invalidate)

    def update() -> None:
        with manager.get_session() as session:
            if fail_commit:

                @event.listens_for(session, "before_commit")
                def fail(*_: object) -> None:
                    raise RuntimeError("publication failed")

            result = bracket.set_bracket_games(
                "WB1-1",
                SetBracketGamesRequest(match_ids=[3, 2, 2]),
                user=User(id=1, discord_id="admin"),
                repo=BracketRepo(session),
                tournament_repo=TournamentRepo(session),
                replay_manager=ReplayManager(session),
            )
            assert [game.id for game in result.linked] == [2, 3]

    if fail_commit:
        with pytest.raises(RuntimeError, match="publication failed"):
            update()
        assert _links(manager, tournament_id) == previous
        assert invalidations == []
    else:
        update()
        assert invalidations == [True]
