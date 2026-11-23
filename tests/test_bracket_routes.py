"""Bracket write routes: tournament-admin gate, PATCH semantics, the 409
reroute guard, reveal redaction and prediction locking."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from radarvan import bracket, discord_events, player_ids
from radarvan import dependencies as deps
from radarvan.db import (
    BracketMatchState,
    BracketPlayer,
    BracketPrediction,
    BracketTournament,
    Tournament,
    User,
)
from radarvan.repositories import BracketPredictionRepo
from radarvan.routes import bracket as bracket_routes

ADMIN_DISCORD_ID = "admin-1"
NAMES = {i: f"P{i}" for i in range(1, 10)}


class FakeBracketRepo:
    # In-memory stand-in: SQLite would drop tzinfo and break the route's
    # scheduled_at comparisons, which real Postgres keeps.
    def __init__(self) -> None:
        self.tournament: BracketTournament | None = None
        self.states: dict[str, BracketMatchState] = {}
        self.event_ids: list[tuple[str, str | None]] = []

    def get_active(self) -> BracketTournament | None:
        return self.tournament

    def create(
        self, players: list[tuple[int, str]], reveal_at: datetime | None = None
    ) -> BracketTournament:
        t = BracketTournament(id=1, reveal_at=reveal_at)
        t.players = [BracketPlayer(seed=s, player_name=n) for s, n in players]
        self.tournament = t
        self.states = {}
        return t

    def set_reveal_at(
        self, tournament_id: int, reveal_at: datetime | None
    ) -> BracketTournament:
        assert self.tournament is not None
        self.tournament.reveal_at = reveal_at
        return self.tournament

    def get_match_states(self, tournament_id: int) -> dict[str, BracketMatchState]:
        return dict(self.states)

    def set_match(
        self,
        tournament_id: int,
        match_id: str,
        scheduled_at: datetime | None,
        best_of: int | None,
        score_a: int | None,
        score_b: int | None,
    ) -> BracketMatchState:
        row = self.states.get(match_id) or BracketMatchState(
            tournament_id=tournament_id, match_id=match_id
        )
        row.scheduled_at = scheduled_at
        row.best_of = best_of
        row.score_a = score_a
        row.score_b = score_b
        self.states[match_id] = row
        return row

    def set_discord_event_id(
        self, tournament_id: int, match_id: str, discord_event_id: str | None
    ) -> None:
        self.event_ids.append((match_id, discord_event_id))
        self.states[match_id].discord_event_id = discord_event_id


class Harness:
    def __init__(self, client: TestClient, repo: FakeBracketRepo) -> None:
        self.client = client
        self.repo = repo
        self.user: User | None = None
        self.discord_calls: list[datetime | None] = []

    def login(
        self, discord_id: str, user_id: int = 1, player_name: str | None = None
    ) -> None:
        self.user = User(
            id=user_id,
            discord_id=discord_id,
            discord_username=f"u{user_id}",
            player_name=player_name,
        )

    def score(self, match_id: str, a: int, b: int, best_of: int = 3) -> None:
        resp = self.client.post(
            f"/api/bracket/{match_id}",
            json={"best_of": best_of, "score_a": a, "score_b": b},
        )
        assert resp.status_code == 200, resp.text


@pytest.fixture
def session() -> Iterator[Session]:
    # Sync route handlers run on a threadpool, so the connection must be shared.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Tournament, BracketTournament, BracketPrediction):
        model.__table__.create(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def h(monkeypatch: pytest.MonkeyPatch, session: Session) -> Iterator[Harness]:
    monkeypatch.setattr(
        player_ids, "TOURNAMENT_ADMIN_DISCORD_IDS", frozenset({ADMIN_DISCORD_ID})
    )
    repo = FakeBracketRepo()
    repo.create(list(NAMES.items()))
    app = FastAPI()
    app.include_router(bracket_routes.router)
    harness = Harness(TestClient(app), repo)

    def fake_sync(
        *, existing_event_id: str | None, scheduled_at: datetime | None, name: str
    ) -> str | None:
        harness.discord_calls.append(scheduled_at)
        return None if scheduled_at is None else f"evt-{len(harness.discord_calls)}"

    monkeypatch.setattr(discord_events, "sync_match_event", fake_sync)

    def current_user() -> User | None:
        return harness.user

    def required_user() -> User:
        assert harness.user is not None, "test forgot to log in"
        return harness.user

    app.dependency_overrides[deps.get_bracket_repo] = lambda: repo
    app.dependency_overrides[deps.get_bracket_prediction_repo] = lambda: (
        BracketPredictionRepo(session, auto_commit=False)
    )
    app.dependency_overrides[deps.get_current_user] = current_user
    app.dependency_overrides[deps.require_current_user] = required_user
    harness.login(ADMIN_DISCORD_ID)
    yield harness


def _match(body: dict, match_id: str) -> dict:
    return next(m for m in body["matches"] if m["match_id"] == match_id)


# --- rerouted_scored_matches (pure) ---


def test_reroute_flags_only_scored_downstream_matches() -> None:
    states = {
        "WB1-1": bracket.MatchState(3, 2, 0),
        "WB2-1": bracket.MatchState(3, 2, 0),
    }
    before = bracket.resolve_bracket(NAMES, states)
    flipped = {**states, "WB1-1": bracket.MatchState(3, 0, 2)}
    after = bracket.resolve_bracket(NAMES, flipped)
    # LB1-1 also changes players (the WB1-1 loser) but has no score, so it's fine.
    assert bracket.rerouted_scored_matches(
        before, after, states, edited_match_id="WB1-1"
    ) == ["WB2-1"]


def test_reroute_ignores_same_winner_score_change() -> None:
    states = {
        "WB1-1": bracket.MatchState(3, 2, 0),
        "WB2-1": bracket.MatchState(3, 2, 0),
    }
    before = bracket.resolve_bracket(NAMES, states)
    after = bracket.resolve_bracket(
        NAMES, {**states, "WB1-1": bracket.MatchState(3, 2, 1)}
    )
    assert (
        bracket.rerouted_scored_matches(before, after, states, edited_match_id="WB1-1")
        == []
    )


# --- tier enforcement ---


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/bracket/WB1-1", {"best_of": 3, "score_a": 2, "score_b": 0}),
        ("post", "/api/bracket/reveal_at", {"reveal_at": None}),
        (
            "post",
            "/api/bracket",
            {"players": [{"seed": s, "player_name": n} for s, n in NAMES.items()]},
        ),
    ],
)
def test_bracket_writes_require_a_tournament_admin(
    h: Harness, method: str, path: str, body: dict
) -> None:
    # A plain logged-in user - even one claiming an admin's player name - is refused.
    h.login("someone-else", user_id=2, player_name="P1")
    resp = getattr(h.client, method)(path, json=body)
    assert resp.status_code == 403
    assert h.repo.states == {}


# --- PATCH semantics ---


def test_score_then_schedule_keeps_the_score(h: Harness) -> None:
    h.score("WB1-1", 2, 0)
    when = datetime(2026, 12, 1, 1, 0, tzinfo=UTC)
    resp = h.client.post("/api/bracket/WB1-1", json={"scheduled_at": when.isoformat()})
    assert resp.status_code == 200
    m = _match(resp.json(), "WB1-1")
    assert (m["best_of"], m["score_a"], m["score_b"]) == (3, 2, 0)
    assert m["winner"] == "P8"
    assert datetime.fromisoformat(m["scheduled_at"]) == when


def test_explicit_null_clears_but_omission_keeps(h: Harness) -> None:
    when = datetime(2026, 12, 1, 1, 0, tzinfo=UTC)
    h.client.post(
        "/api/bracket/WB1-1",
        json={
            "scheduled_at": when.isoformat(),
            "best_of": 3,
            "score_a": 2,
            "score_b": 1,
        },
    )
    resp = h.client.post("/api/bracket/WB1-1", json={"score_a": None, "score_b": None})
    assert resp.status_code == 200
    m = _match(resp.json(), "WB1-1")
    assert (m["score_a"], m["score_b"], m["winner"]) == (None, None, None)
    assert m["best_of"] == 3
    assert m["status"] == "ready"
    assert m["scheduled_at"] is not None


@pytest.mark.parametrize(
    "body",
    [
        {"score_a": 2, "score_b": 0},  # no best_of stored or sent
        {"best_of": 3, "score_a": 2},  # score_b missing
        {"best_of": 3, "score_a": 1, "score_b": 1},  # nobody reached 2
        {"best_of": 3, "score_a": 3, "score_b": 0},  # past the threshold
    ],
)
def test_invalid_scores_are_rejected(h: Harness, body: dict) -> None:
    resp = h.client.post("/api/bracket/WB1-1", json=body)
    assert resp.status_code == 400
    assert h.repo.states == {}


def test_cannot_score_a_match_whose_players_are_undetermined(h: Harness) -> None:
    # WB2-1 waits on WB1-1's winner.
    resp = h.client.post(
        "/api/bracket/WB2-1", json={"best_of": 3, "score_a": 2, "score_b": 0}
    )
    assert resp.status_code == 400
    assert "aren't determined" in resp.json()["detail"]


def test_unknown_match_id_is_404(h: Harness) -> None:
    # WB1-2 exists in a 16-player bracket but not a 9-player one.
    resp = h.client.post("/api/bracket/WB1-2", json={"best_of": 3})
    assert resp.status_code == 404


# --- reroute guard ---


def test_flipping_an_upstream_result_under_a_scored_match_is_409(h: Harness) -> None:
    h.score("WB1-1", 2, 0)  # P8 advances
    h.score("WB2-1", 2, 0)  # P1 beats P8
    resp = h.client.post("/api/bracket/WB1-1", json={"score_a": 0, "score_b": 2})
    assert resp.status_code == 409
    assert "WB2-1" in resp.json()["detail"]
    assert h.repo.states["WB1-1"].score_a == 2  # nothing written


def test_flip_succeeds_once_downstream_result_is_cleared(h: Harness) -> None:
    h.score("WB1-1", 2, 0)
    h.score("WB2-1", 2, 0)
    cleared = h.client.post(
        "/api/bracket/WB2-1", json={"score_a": None, "score_b": None}
    )
    assert cleared.status_code == 200
    resp = h.client.post("/api/bracket/WB1-1", json={"score_a": 0, "score_b": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert _match(body, "WB2-1")["player_b"] == "P9"
    assert _match(body, "LB1-1")["player_a"] == "P8"


def test_same_winner_score_correction_is_allowed(h: Harness) -> None:
    h.score("WB1-1", 2, 0)
    h.score("WB2-1", 2, 0)
    resp = h.client.post("/api/bracket/WB1-1", json={"score_a": 2, "score_b": 1})
    assert resp.status_code == 200


# --- Discord event sync ---


def test_discord_sync_runs_only_when_scheduled_at_changes(h: Harness) -> None:
    when = datetime(2026, 12, 1, 1, 0, tzinfo=UTC)
    h.client.post("/api/bracket/WB1-1", json={"scheduled_at": when.isoformat()})
    assert h.discord_calls == [when]
    assert h.repo.states["WB1-1"].discord_event_id == "evt-1"

    h.score("WB1-1", 2, 0)
    h.client.post("/api/bracket/WB1-1", json={"scheduled_at": when.isoformat()})
    assert len(h.discord_calls) == 1

    h.client.post("/api/bracket/WB1-1", json={"scheduled_at": None})
    assert h.discord_calls == [when, None]
    assert h.repo.states["WB1-1"].discord_event_id is None


# --- reveal gate ---


def test_unrevealed_bracket_hides_placements_but_not_the_roster(h: Harness) -> None:
    h.score("WB1-1", 2, 0)
    future = datetime.now(UTC) + timedelta(days=1)
    h.client.post("/api/bracket/reveal_at", json={"reveal_at": future.isoformat()})

    h.login("visitor", user_id=2)
    body = h.client.get("/api/bracket").json()
    assert body["revealed"] is False
    assert body["participant_names"] == sorted(NAMES.values())
    assert body["players"] == [] and body["bye_advances"] == []
    assert all(
        m["player_a"] is None and m["player_b"] is None and m["winner"] is None
        for m in body["matches"]
    )
    # preview is only honoured for a tournament admin.
    assert h.client.get("/api/bracket?preview=true").json()["revealed"] is False
    h.login(ADMIN_DISCORD_ID)
    preview = h.client.get("/api/bracket?preview=true").json()
    assert preview["revealed"] is True
    assert _match(preview, "WB1-1")["winner"] == "P8"


def test_predictions_are_withheld_before_reveal(h: Harness) -> None:
    future = datetime.now(UTC) + timedelta(days=1)
    h.client.post("/api/bracket/reveal_at", json={"reveal_at": future.isoformat()})
    assert h.client.get("/api/bracket_predictions").json() == []
    assert h.client.get("/api/bracket_prediction_leaderboard").json() == []


# --- predictions ---


def test_prediction_must_name_one_of_the_players(h: Harness) -> None:
    resp = h.client.post(
        "/api/bracket_predictions/WB1-1", json={"predicted_winner": "P1"}
    )
    assert resp.status_code == 400


def test_predictions_lock_once_scheduled_time_passes(h: Harness) -> None:
    past = datetime.now(UTC) - timedelta(minutes=1)
    h.client.post("/api/bracket/WB1-1", json={"scheduled_at": past.isoformat()})
    resp = h.client.post(
        "/api/bracket_predictions/WB1-1", json={"predicted_winner": "P8"}
    )
    assert resp.status_code == 409


def test_predictions_lock_once_scored(h: Harness) -> None:
    h.score("WB1-1", 2, 0)
    resp = h.client.post(
        "/api/bracket_predictions/WB1-1", json={"predicted_winner": "P8"}
    )
    assert resp.status_code == 409


def test_leaderboard_counts_only_completed_matches(
    h: Harness, session: Session
) -> None:
    for uid, name in ((1, ADMIN_DISCORD_ID), (2, "fan")):
        session.add(User(id=uid, discord_id=name, discord_username=name))
    session.flush()

    h.login(ADMIN_DISCORD_ID, user_id=1)
    assert (
        h.client.post(
            "/api/bracket_predictions/WB1-1", json={"predicted_winner": "P8"}
        ).status_code
        == 200
    )
    h.client.post("/api/bracket_predictions/WB2-2", json={"predicted_winner": "P4"})
    h.login("fan", user_id=2)
    h.client.post("/api/bracket_predictions/WB1-1", json={"predicted_winner": "P9"})

    h.login(ADMIN_DISCORD_ID, user_id=1)
    h.score("WB1-1", 2, 0)  # P8 wins; WB2-2 still unplayed

    board = h.client.get("/api/bracket_prediction_leaderboard").json()
    assert board == [
        {"user_name": ADMIN_DISCORD_ID, "correct": 1, "total": 1},
        {"user_name": "fan", "correct": 0, "total": 1},
    ]
    preds = {p["match_id"]: p for p in h.client.get("/api/bracket_predictions").json()}
    assert preds["WB1-1"]["correct_picks"] == [ADMIN_DISCORD_ID]
    assert preds["WB1-1"]["open"] is False
    assert preds["WB2-2"]["correct_picks"] is None
    assert preds["WB2-2"]["my_pick"] == "P4"
    assert preds["WB2-2"]["open"] is True
