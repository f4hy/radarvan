"""1v1 double-elimination bracket tournament endpoints.

Public reads; admin-gated writes (create/reset the bracket, set a match's
date/best-of/score). "Admin" here is the tournament-specific set
(``player_ids.TOURNAMENT_ADMINS``), not the global ``ADMIN_PLAYERS`` used by
other admin features.

``/api/bracket_eligible_players`` is deliberately a separate top-level path
rather than nested under ``/api/bracket`` — the OpenAPI client generator can
silently merge a static path with a parameterized sibling that shares a
prefix (see CLAUDE.md gotcha re: ``/api/map_data/by_player_count`` vs.
``/api/map_data/{map_name}``).
"""

import structlog

from fastapi import APIRouter, Depends, HTTPException

from .. import bracket, player_ids
from ..api_types import (
    BracketMatchOutput,
    BracketPlayerEntry,
    BracketTournamentOutput,
    CreateBracketRequest,
    LoserOfSource,
    MatchSource,
    SeedSource,
    SetBracketMatchRequest,
    WinnerOfSource,
)
from ..db import BracketMatchState, BracketTournament, User
from ..dependencies import get_bracket_repo, require_current_user
from ..repositories import BracketRepo

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["bracket"])


def _require_tournament_admin(user: User) -> None:
    if not player_ids.is_tournament_admin(user.player_name):
        raise HTTPException(status_code=403, detail="Forbidden")


def _to_api_source(source: bracket.Source) -> MatchSource:
    if isinstance(source, bracket.Seed):
        return SeedSource(seed=source.seed)
    if isinstance(source, bracket.WinnerOf):
        return WinnerOfSource(match_id=source.match_id)
    return LoserOfSource(match_id=source.match_id)


def _states_from_rows(
    raw_states: dict[str, BracketMatchState],
) -> dict[str, bracket.MatchState]:
    return {
        match_id: bracket.MatchState(
            best_of=row.best_of, score_a=row.score_a, score_b=row.score_b
        )
        for match_id, row in raw_states.items()
    }


def _seed_to_name(tournament: BracketTournament) -> dict[int, str]:
    return {p.seed: p.player_name for p in tournament.players}


def _resolve_from_states(
    tournament: BracketTournament, raw_states: dict[str, BracketMatchState]
) -> bracket.BracketResult:
    return bracket.resolve_bracket(
        _seed_to_name(tournament), _states_from_rows(raw_states)
    )


def _build_output_from_states(
    tournament: BracketTournament, raw_states: dict[str, BracketMatchState]
) -> BracketTournamentOutput:
    result = _resolve_from_states(tournament, raw_states)

    matches = []
    for m in result.matches:
        raw = raw_states.get(m.match_id)
        matches.append(
            BracketMatchOutput(
                match_id=m.match_id,
                bracket=m.bracket,
                round_number=m.round_number,
                round_name=m.round_name,
                player_a=m.player_a,
                player_b=m.player_b,
                scheduled_date=raw.scheduled_date if raw else None,
                best_of=raw.best_of if raw else None,
                score_a=raw.score_a if raw else None,
                score_b=raw.score_b if raw else None,
                winner=m.winner,
                status=m.status,
                source_a=_to_api_source(m.source_a),
                source_b=_to_api_source(m.source_b),
            )
        )

    return BracketTournamentOutput(
        players=[
            BracketPlayerEntry(seed=p.seed, player_name=p.player_name)
            for p in sorted(tournament.players, key=lambda p: p.seed)
        ],
        matches=matches,
        bye_advances=[
            BracketPlayerEntry(seed=seed, player_name=name)
            for seed, name in result.bye_advances
        ],
        champion=result.champion,
        runner_up=result.runner_up,
        needs_reset=result.needs_reset,
    )


def _build_output(
    tournament: BracketTournament, repo: BracketRepo
) -> BracketTournamentOutput:
    return _build_output_from_states(tournament, repo.get_match_states(tournament.id))


@router.get("/api/bracket")
def get_bracket(
    repo: BracketRepo = Depends(get_bracket_repo),
) -> BracketTournamentOutput | None:
    """The current bracket tournament, or None if none has been created yet."""
    tournament = repo.get_active()
    if tournament is None:
        return None
    return _build_output(tournament, repo)


@router.get("/api/bracket_eligible_players")
def eligible_players() -> list[str]:
    """Known player names — the pool admins pick the 9-16 entrants from."""
    return sorted(player_ids.PLAYER_NAMES)


@router.post("/api/bracket")
def create_bracket(
    req: CreateBracketRequest,
    user: User = Depends(require_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
) -> BracketTournamentOutput:
    """Create (or replace) the bracket with these 9-16 seeded entrants."""
    _require_tournament_admin(user)
    tournament = repo.create([(p.seed, p.player_name) for p in req.players])
    logger.info(
        "bracket created", user_id=user.id, players=[p.player_name for p in req.players]
    )
    return _build_output(tournament, repo)


@router.post("/api/bracket/{match_id}")
def set_bracket_match(
    match_id: str,
    req: SetBracketMatchRequest,
    user: User = Depends(require_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
) -> BracketTournamentOutput:
    """Update a match's scheduled date / best-of / score (admin only).

    PATCH semantics: only fields present in the request body change; omitted
    fields keep their stored values, and an explicit null clears a field.
    """
    _require_tournament_admin(user)
    tournament = repo.get_active()
    if tournament is None:
        raise HTTPException(status_code=404, detail="No active bracket tournament")
    if not bracket.is_valid_match_id(match_id, len(tournament.players)):
        raise HTTPException(status_code=404, detail="Unknown match id")

    # Fetched once and reused for both the pre-write validation resolve and
    # the post-write response, patched in place below instead of re-querying.
    raw_states = repo.get_match_states(tournament.id)
    existing = raw_states.get(match_id)

    def merged[T](field: str, current: T) -> T:
        value: T = getattr(req, field)
        return value if field in req.model_fields_set else current

    scheduled_date = merged(
        "scheduled_date", existing.scheduled_date if existing else None
    )
    best_of = merged("best_of", existing.best_of if existing else None)
    score_a = merged("score_a", existing.score_a if existing else None)
    score_b = merged("score_b", existing.score_b if existing else None)

    seed_to_name = _seed_to_name(tournament)
    states = _states_from_rows(raw_states)
    before = bracket.resolve_bracket(seed_to_name, states)

    if score_a is not None or score_b is not None:
        if best_of is None or score_a is None or score_b is None:
            raise HTTPException(
                status_code=400,
                detail="best_of, score_a, and score_b are all required together",
            )
        try:
            bracket.validate_score(best_of, score_a, score_b)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        match = next(m for m in before.matches if m.match_id == match_id)
        if match.player_a is None or match.player_b is None:
            raise HTTPException(
                status_code=400, detail="This match's players aren't determined yet"
            )

    # Refuse edits that would re-route players through matches that already
    # have a recorded score — their stored result would silently be attributed
    # to different players. The admin must clear the downstream result first.
    new_states = dict(states)
    new_states[match_id] = bracket.MatchState(
        best_of=best_of, score_a=score_a, score_b=score_b
    )
    after = bracket.resolve_bracket(seed_to_name, new_states)
    conflicts = bracket.rerouted_scored_matches(
        before, after, states, edited_match_id=match_id
    )
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This change would alter the players of {', '.join(conflicts)}, "
                "which already have a recorded score. Clear those results first."
            ),
        )

    raw_states[match_id] = repo.set_match(
        tournament.id,
        match_id,
        scheduled_date,
        best_of,
        score_a,
        score_b,
    )
    return _build_output_from_states(tournament, raw_states)
