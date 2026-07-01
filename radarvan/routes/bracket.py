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


def _resolve_from_states(
    tournament: BracketTournament, raw_states: dict[str, BracketMatchState]
) -> bracket.BracketResult:
    seed_to_name = {p.seed: p.player_name for p in tournament.players}
    match_states = {
        match_id: bracket.MatchState(
            best_of=row.best_of, score_a=row.score_a, score_b=row.score_b
        )
        for match_id, row in raw_states.items()
    }
    return bracket.resolve_bracket(seed_to_name, match_states)


def _resolve(
    tournament: BracketTournament, repo: BracketRepo
) -> tuple[bracket.BracketResult, dict[str, BracketMatchState]]:
    raw_states = repo.get_match_states(tournament.id)
    return _resolve_from_states(tournament, raw_states), raw_states


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
    """Set a match's scheduled date / best-of / score (admin only)."""
    _require_tournament_admin(user)
    tournament = repo.get_active()
    if tournament is None:
        raise HTTPException(status_code=404, detail="No active bracket tournament")
    if not bracket.is_valid_match_id(match_id, len(tournament.players)):
        raise HTTPException(status_code=404, detail="Unknown match id")

    # Fetched once and reused for both the pre-write validation resolve and
    # the post-write response, patched in place below instead of re-querying.
    raw_states = repo.get_match_states(tournament.id)

    if req.score_a is not None or req.score_b is not None:
        if req.best_of is None or req.score_a is None or req.score_b is None:
            raise HTTPException(
                status_code=400,
                detail="best_of, score_a, and score_b are all required together",
            )
        try:
            bracket.validate_score(req.best_of, req.score_a, req.score_b)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        result = _resolve_from_states(tournament, raw_states)
        match = next(m for m in result.matches if m.match_id == match_id)
        if match.player_a is None or match.player_b is None:
            raise HTTPException(
                status_code=400, detail="This match's players aren't determined yet"
            )

    raw_states[match_id] = repo.set_match(
        tournament.id,
        match_id,
        req.scheduled_date,
        req.best_of,
        req.score_a,
        req.score_b,
    )
    return _build_output_from_states(tournament, raw_states)
