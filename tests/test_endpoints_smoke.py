"""Executes every GET endpoint against a stubbed data layer.

The route handlers hold real logic (corpus selection, filtering, serialization)
that no other test reaches, because the only way to call them is an HTTP request.
This module supplies that call: each GET route runs against an in-memory corpus,
and the response must be a 200 that validates against the route's declared
response model.

Two properties are worth keeping:

* **Nothing here may touch a real database.** ``DATABASE_URL`` commonly points at
  *production* in a developer shell (see CLAUDE.md), so ``db_manager`` is patched
  to raise. A handler that reaches past its injected dependency fails loudly
  instead of quietly querying prod.
* **Coverage can only shrink deliberately.** A new GET route enrols in the run
  automatically and has to pass, so the one way to lose coverage is to excuse an
  endpoint in ``NOT_EXERCISED`` - which ``test_excused_list_does_not_grow``
  turns into a visible decision rather than a quiet one.

Of the 105 ``/api`` routes: 43 GETs run here, 25 are excused with a reason, and
the rest are mutating (checked for a usable response model, not executed).
"""

import os

# dependencies.py builds the engine at import time, so point it somewhere inert
# before that happens - a developer shell's DATABASE_URL is usually *production*.
# This only helps when this module is imported first; the guarantee that nothing
# reaches a real database is _forbid_db below, which holds either way.
os.environ["DATABASE_URL"] = "postgresql://stub:stub@127.0.0.1:1/stub-not-used"

import logging
from datetime import datetime

import pytest
import structlog
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from radarvan import derived, dependencies as deps, matches as matches_mod
from radarvan.main import app
from radarvan.repositories.maps import MapRegistryRevision

import corpus

# The app's global exception handler renders a rich traceback for every 500.
# Left enabled, a single failing route buries the assertion message in megabytes
# of console output and the module takes a minute to run.
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
    logger_factory=structlog.ReturnLoggerFactory(),
    cache_logger_on_first_use=True,
)

# --- routes ------------------------------------------------------------------


def _walk(routes: object) -> list[APIRoute]:
    """Flatten the route tree.

    ``include_router`` wraps each router in a ``_IncludedRouter`` whose real
    routes hang off ``original_router``, so ``app.routes`` alone shows only the
    handful declared directly on the app.
    """
    found: list[APIRoute] = []
    for route in routes:  # type: ignore[attr-defined]
        if isinstance(route, APIRoute):
            found.append(route)
        included = getattr(route, "original_router", None)
        if included is not None:
            found.extend(_walk(included.routes))
        elif not isinstance(route, APIRoute):
            found.extend(_walk(getattr(route, "routes", []) or []))
    return found


ALL_ROUTES = _walk(app.routes)

# Values substituted into path templates and required query params.
PATH_VALUES = {
    "match_id": str(corpus.A_MATCH.id),
    "map_name": corpus.A_MAP,
    "date": corpus.A_MATCH.date.isoformat(),
    "player_count": "4",
    "team_size": "2",
    "tournament_name": "spring-cup",
    "slug": "spring-cup",
}

QUERY_VALUES = {
    "/api/player_head_to_head/": {
        "player1": corpus.A_PLAYER,
        "player2": corpus.AN_OPPONENT,
    },
    "/api/player_profile/": {"player": corpus.A_PLAYER},
    "/api/player_ratings/daily_changes/": {"for_date": corpus.A_MATCH.date.isoformat()},
    "/api/predict/faction_matchup": {
        "player1": corpus.A_PLAYER,
        "player2": corpus.AN_OPPONENT,
        "map_name": corpus.A_MAP,
    },
    "/api/files_for_match": {"match_id": corpus.A_MATCH.id},
    "/api/presigned_urls_for_match": {"match_id": corpus.A_MATCH.id},
}

# Routes this module deliberately does not execute. Every entry needs a reason;
# the coverage test below refuses to let the list grow silently.
NOT_EXERCISED = {
    "/api/auth/discord/login": "redirects to Discord; needs real OAuth config",
    "/api/auth/discord/callback": "requires a signed OAuth state from Discord",
    "/api/matchup_commentary/": "a cache miss bills a real LLM call (see CLAUDE.md)",
    "/api/matchup_commentary/prompt_preview": "needs match details loaded from S3",
    "/api/replay": "fetches a replay over HTTP from an external URL",
    "/api/details/{match_id}": "reads the multi-MB raw replay from S3",
    "/api/build_orders/{match_id}": "reads the raw replay from S3",
    "/api/replay_url/{match_id}": "needs a real S3 object to presign",
    "/api/debug/json_url/{match_id}": "needs a real S3 object to presign",
    "/api/debug/match/{match_id}": "returns raw parsed JSON read from S3",
    "/api/map_image/{map_name}": "streams a webp from S3",
    "/api/map_data/{map_name}": "needs stored map geometry, not match data",
    "/api/predict/match/{match_id}": "ONNX inference over details loaded from S3",
    "/api/predict/over_time/{match_id}": "ONNX inference over details loaded from S3",
    "/api/bracket_summary/{match_id}": "LLM-backed summary",
    "/api/bracket_summary_preview/{match_id}": "LLM-backed summary",
    "/api/bracket_games/{match_id}": "needs a persisted bracket tournament",
    "/api/tournaments/{slug}/games": "needs a persisted tournament",
    "/api/tournament_report/{tournament_name}": "needs a persisted tournament report",
    "/api/is_tournament_game/{match_id}": "needs persisted tournament links",
    # These reach past the repository for a raw SQLAlchemy session, so a stub
    # repo is not enough to run them.
    "/api/missing_maps": "queries through a raw SQLAlchemy session",
    "/api/map_reparse_status": "queries through a raw SQLAlchemy session",
    "/api/tournaments": "queries through a raw SQLAlchemy session",
    "/api/files_for_match": "needs replay-file rows and their S3 objects",
    "/api/presigned_urls_for_match": "needs replay-file rows and their S3 objects",
}

GET_ROUTES = sorted(
    {
        r.path: r
        for r in ALL_ROUTES
        if "GET" in r.methods
        and r.path.startswith("/api")
        and r.path not in NOT_EXERCISED
    }.values(),
    key=lambda r: r.path,
)


# --- stub data layer ---------------------------------------------------------


class _StubRepo:
    """Returns an empty result for any repository method a handler calls.

    Empty is a valid answer for every list/lookup endpoint, so handlers still run
    end to end and their responses still have to satisfy the response model - the
    point is to exercise the handler, not to assert on data.
    """

    _EMPTY: dict[str, object] = {}

    def latest_match_created_at(self) -> datetime:
        return corpus.LATEST

    def get_overrides(self) -> dict[int, object]:
        return {}

    def get_active(self) -> None:
        return None

    def get_player_profile(self, player: str, version: str) -> None:
        # None is the real "not computed at this PROFILE_VERSION yet" answer;
        # the catch-all below would hand back a list and fail response validation.
        return None

    def list_maps_by_player_count(self) -> dict[int, list[str]]:
        return {len(corpus.CORPUS[0].players): list(corpus.MAPS)}

    def list_map_names(self) -> list[str]:
        return list(corpus.MAPS)

    def map_registry_revision(self) -> MapRegistryRevision:
        # Backs derived.MAPS. Fixed, so the map derivations key stably across the
        # module rather than re-deriving per request.
        return MapRegistryRevision(rows=len(corpus.MAPS), updated_at=corpus.LATEST)

    @property
    def session(self):
        raise AssertionError(
            "this endpoint queries through a raw SQLAlchemy session; it belongs "
            "in NOT_EXERCISED rather than being served by a stub repository"
        )

    def __getattr__(self, name: str):
        # Anything not spelled out above answers with an empty sequence. Handlers
        # that need richer data belong in NOT_EXERCISED, not in a growing stub.
        def _empty(*args: object, **kwargs: object) -> list[object]:
            return []

        return _empty


def _forbid_db(*args: object, **kwargs: object):
    raise AssertionError(
        "a handler reached radarvan.dependencies.db_manager directly; "
        "smoke tests must never open a real database session"
    )


@pytest.fixture(scope="module")
def client() -> TestClient:
    stub = _StubRepo()
    app.dependency_overrides[deps.get_replay_manager] = lambda: stub
    app.dependency_overrides[deps.get_db_session] = lambda: None
    for provider in (
        deps.get_user_repo,
        deps.get_map_vote_repo,
        deps.get_bracket_repo,
        deps.get_bracket_prediction_repo,
    ):
        app.dependency_overrides[provider] = lambda: stub

    real_get_match_infos = matches_mod.get_match_infos
    real_db_manager_get = deps.db_manager.get_replay_manager
    real_session_local = deps.db_manager.SessionLocal
    matches_mod.get_match_infos = lambda replay_manager: list(corpus.CORPUS)
    deps.db_manager.get_replay_manager = _forbid_db
    deps.db_manager.SessionLocal = _forbid_db
    _clear_caches()

    # Not a context-managed TestClient: that would run the lifespan, which starts
    # the scheduler and warms caches against a real database.
    yield TestClient(app, raise_server_exceptions=False)

    matches_mod.get_match_infos = real_get_match_infos
    deps.db_manager.get_replay_manager = real_db_manager_get
    deps.db_manager.SessionLocal = real_session_local
    app.dependency_overrides.clear()
    _clear_caches()


def _clear_caches() -> None:
    """Empty every registered derivation.

    ``derived.clear_all()`` rather than ``cache.invalidate_match_caches()``: the
    latter kicks the background warm thread, which opens its own session against
    the real database. This used to enumerate six caches by name and so missed
    the ten declared in other modules - which is the problem the registry exists
    to remove, so it would be a poor place to keep reproducing it.
    """
    derived.clear_all()


# --- tests -------------------------------------------------------------------


def _url(route: APIRoute) -> str:
    path = route.path
    for name, value in PATH_VALUES.items():
        path = path.replace(f"{{{name}}}", value)
    assert "{" not in path, f"no fixture value for a path param in {route.path}"
    return path


@pytest.mark.parametrize("route", GET_ROUTES, ids=lambda r: r.path)
def test_get_endpoint_returns_a_valid_response(
    route: APIRoute, client: TestClient
) -> None:
    response = client.get(_url(route), params=QUERY_VALUES.get(route.path))
    assert response.status_code == 200, (
        f"{route.path} -> {response.status_code}: {response.text[:300]}"
    )
    if route.response_model is not None:
        TypeAdapter(route.response_model).validate_python(response.json())


# A new GET route enrols in the smoke run automatically, so the only way to
# lose coverage is to add an entry to NOT_EXERCISED. This ceiling is what makes
# that a deliberate act: lower it as endpoints become testable, and treat raising
# it as a change worth justifying in review.
MAX_EXCUSED = 25


def test_excused_list_does_not_grow() -> None:
    """Silencing a failing endpoint by excusing it has to be a visible decision."""
    assert len(NOT_EXERCISED) <= MAX_EXCUSED, (
        f"NOT_EXERCISED grew to {len(NOT_EXERCISED)} (ceiling {MAX_EXCUSED}). "
        "Prefer making the endpoint testable over excusing it."
    )


def test_mutating_routes_declare_a_resolvable_response_type() -> None:
    """Mutating endpoints aren't executed, but their contract is still checked.

    Running a POST/DELETE against a stub would assert nothing about real
    behaviour, so instead every one has to expose a response type that pydantic
    can actually build a schema for - which catches a broken or renamed
    annotation without touching any data.
    """
    broken: list[str] = []
    for route in ALL_ROUTES:
        if route.methods <= {"GET", "HEAD"} or not route.path.startswith("/api"):
            continue
        model = route.response_model
        if model is None:
            continue
        try:
            TypeAdapter(model).json_schema(ref_template="#/components/schemas/{model}")
        except Exception as exc:  # pragma: no cover - only on a real breakage
            broken.append(f"{route.path}: {exc}")
    assert not broken, "mutating endpoints with an unusable response model: " + str(
        broken
    )


def test_all_api_routes_fall_into_exactly_one_bucket() -> None:
    """Every /api route is exercised, excused, or mutating - and only one."""
    exercised = {r.path for r in GET_ROUTES}
    excused = set(NOT_EXERCISED)
    mutating = {
        r.path
        for r in ALL_ROUTES
        if r.path.startswith("/api") and not r.methods <= {"GET", "HEAD"}
    }
    api_paths = {r.path for r in ALL_ROUTES if r.path.startswith("/api")}
    assert exercised & excused == set(), "a route is both exercised and excused"
    assert api_paths == exercised | excused | mutating, (
        f"unbucketed routes: {sorted(api_paths - (exercised | excused | mutating))}"
    )


def test_excused_routes_still_exist() -> None:
    """Keeps NOT_EXERCISED from accumulating entries for deleted endpoints."""
    live = {r.path for r in ALL_ROUTES}
    stale = sorted(set(NOT_EXERCISED) - live)
    assert not stale, f"NOT_EXERCISED names routes that no longer exist: {stale}"
