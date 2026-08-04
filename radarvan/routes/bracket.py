"""1v1 double-elimination bracket tournament endpoints.

Public reads; admin-gated writes (create/reset the bracket, set a match's
date/best-of/score). "Admin" here is the tournament-specific set
(``player_ids.TOURNAMENT_ADMINS``), not the global ``ADMIN_PLAYERS`` used by
other admin features.

``/api/bracket_eligible_players`` is deliberately a separate top-level path
rather than nested under ``/api/bracket`` - the OpenAPI client generator can
silently merge a static path with a parameterized sibling that shares a
prefix (see CLAUDE.md gotcha re: ``/api/map_data/by_player_count`` vs.
``/api/map_data/{map_name}``).
"""

from datetime import UTC, datetime

import structlog

from fastapi import APIRouter, Depends, HTTPException

from .. import bracket, discord_events, player_ids
from ..api_types import (
    BracketMatchOutput,
    BracketPlayerEntry,
    BracketTournamentOutput,
    CreateBracketRequest,
    LoserOfSource,
    BracketMatchPrediction,
    MatchSource,
    SeedSource,
    SetBracketMatchRequest,
    SetBracketRevealAtRequest,
    SetMatchPredictionRequest,
    WinnerOfSource,
)
from ..db import BracketMatchState, BracketTournament, User
from ..dependencies import (
    get_bracket_prediction_repo,
    get_bracket_repo,
    get_current_user,
    require_current_user,
)
from ..repositories import BracketPredictionRepo, BracketRepo

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


def _load_match(
    repo: BracketRepo, match_id: str
) -> tuple[
    BracketTournament,
    dict[str, BracketMatchState],
    bracket.BracketResult,
    bracket.ResolvedMatch,
]:
    """Shared preamble for every single-match bracket write/read: fetch the
    active tournament, validate ``match_id``, resolve the whole bracket, and
    locate that match within it. 404s on no active tournament or an unknown
    match_id - the two checks every caller needs before touching one match.
    """
    tournament = repo.get_active()
    if tournament is None:
        raise HTTPException(status_code=404, detail="No active bracket tournament")
    if not bracket.is_valid_match_id(match_id, len(tournament.players)):
        raise HTTPException(status_code=404, detail="Unknown match id")
    raw_states = repo.get_match_states(tournament.id)
    result = _resolve_from_states(tournament, raw_states)
    resolved_match = next(m for m in result.matches if m.match_id == match_id)
    return tournament, raw_states, result, resolved_match


def _is_revealed(tournament: BracketTournament, *, allow_preview: bool) -> bool:
    """True once the bracket's placements/matchups may be shown.

    ``reveal_at`` is compared against the server clock only - a client can
    never push this true early except via an authenticated admin preview
    (see ``get_bracket``'s ``preview`` param).
    """
    if allow_preview:
        return True
    return tournament.reveal_at is None or datetime.now(UTC) >= tournament.reveal_at


def _redact(output: BracketTournamentOutput) -> BracketTournamentOutput:
    """Strip player placements before reveal_at.

    Only ``participant_names`` (the always-visible roster), the bracket
    shape (match ids/sources/status), and scores stay visible - everything
    that would reveal *who* is in *which* slot is nulled out.
    """
    return output.model_copy(
        update={
            "players": [],
            "matches": [
                m.model_copy(
                    update={"player_a": None, "player_b": None, "winner": None}
                )
                for m in output.matches
            ],
            "bye_advances": [],
            "champion": None,
            "runner_up": None,
        }
    )


def _build_output_from_states(
    tournament: BracketTournament,
    raw_states: dict[str, BracketMatchState],
    *,
    allow_preview: bool = False,
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
                scheduled_at=raw.scheduled_at if raw else None,
                best_of=raw.best_of if raw else None,
                score_a=raw.score_a if raw else None,
                score_b=raw.score_b if raw else None,
                winner=m.winner,
                status=m.status,
                source_a=_to_api_source(m.source_a),
                source_b=_to_api_source(m.source_b),
            )
        )

    output = BracketTournamentOutput(
        participant_names=sorted(p.player_name for p in tournament.players),
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
        revealed=_is_revealed(tournament, allow_preview=allow_preview),
        reveal_at=tournament.reveal_at,
    )
    return output if output.revealed else _redact(output)


def _build_output(
    tournament: BracketTournament, repo: BracketRepo, *, allow_preview: bool = False
) -> BracketTournamentOutput:
    return _build_output_from_states(
        tournament, repo.get_match_states(tournament.id), allow_preview=allow_preview
    )


@router.get("/api/bracket")
def get_bracket(
    preview: bool = False,
    user: User | None = Depends(get_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
) -> BracketTournamentOutput | None:
    """The current bracket tournament, or None if none has been created yet.

    Before ``reveal_at``, player placements are withheld from the response
    (see ``_build_output_from_states``) - only the roster and blank bracket
    shape are visible. ``preview=true`` bypasses that gate, but only for a
    logged-in tournament admin; it's a per-request opt-in (an admin's own
    "peek early" button), not a way to reveal the bracket for everyone.
    """
    tournament = repo.get_active()
    if tournament is None:
        return None
    allow_preview = (
        preview
        and user is not None
        and player_ids.is_tournament_admin(user.player_name)
    )
    return _build_output(tournament, repo, allow_preview=allow_preview)


@router.get("/api/bracket_eligible_players")
def eligible_players() -> list[str]:
    """Known player names - the pool admins pick the 9-16 entrants from."""
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
    return _build_output(tournament, repo, allow_preview=True)


@router.post("/api/bracket/reveal_at")
def set_bracket_reveal_at(
    req: SetBracketRevealAtRequest,
    user: User = Depends(require_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
) -> BracketTournamentOutput:
    """Set (or clear, with null) when the bracket becomes publicly visible."""
    _require_tournament_admin(user)
    tournament = repo.get_active()
    if tournament is None:
        raise HTTPException(status_code=404, detail="No active bracket tournament")
    tournament = repo.set_reveal_at(tournament.id, req.reveal_at)
    logger.info("bracket reveal_at set", user_id=user.id, reveal_at=req.reveal_at)
    return _build_output(tournament, repo, allow_preview=True)


@router.post("/api/bracket/{match_id}")
def set_bracket_match(
    match_id: str,
    req: SetBracketMatchRequest,
    user: User = Depends(require_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
) -> BracketTournamentOutput:
    """Update a match's scheduled date/time / best-of / score (admin only).

    PATCH semantics: only fields present in the request body change; omitted
    fields keep their stored values, and an explicit null clears a field.
    ``scheduled_at`` can be set (or cleared) independently of best_of/scores -
    e.g. an admin scheduling a match ahead of time, before it's been played.
    """
    _require_tournament_admin(user)
    # raw_states is fetched once here and reused for both the pre-write
    # validation resolve and the post-write response, patched in place below
    # instead of re-querying.
    tournament, raw_states, before, resolved_match = _load_match(repo, match_id)
    existing = raw_states.get(match_id)

    def merged[T](field: str, current: T) -> T:
        value: T = getattr(req, field)
        return value if field in req.model_fields_set else current

    scheduled_at = merged("scheduled_at", existing.scheduled_at if existing else None)
    best_of = merged("best_of", existing.best_of if existing else None)
    score_a = merged("score_a", existing.score_a if existing else None)
    score_b = merged("score_b", existing.score_b if existing else None)

    seed_to_name = _seed_to_name(tournament)
    states = _states_from_rows(raw_states)

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

        if resolved_match.player_a is None or resolved_match.player_b is None:
            raise HTTPException(
                status_code=400, detail="This match's players aren't determined yet"
            )

    # Refuse edits that would re-route players through matches that already
    # have a recorded score - their stored result would silently be attributed
    # to different players. The admin must clear the downstream result first.
    # A pure scheduled_at edit (the Agenda tab's primary use case) can't
    # possibly re-route anyone - best_of/score_a/score_b, the only fields
    # that feed routing, are unchanged - so skip the second resolve_bracket
    # and the reroute diff entirely in that case.
    scores_unchanged = (
        best_of == (existing.best_of if existing else None)
        and score_a == (existing.score_a if existing else None)
        and score_b == (existing.score_b if existing else None)
    )
    if not scores_unchanged:
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

    scheduled_at_changed = scheduled_at != (
        existing.scheduled_at if existing else None
    )

    row = repo.set_match(
        tournament.id,
        match_id,
        scheduled_at,
        best_of,
        score_a,
        score_b,
    )
    raw_states[match_id] = row

    # Best-effort: keep the Discord scheduled event in sync with
    # scheduled_at, but only bother calling out when it actually changed -
    # a pure best_of/score edit shouldn't touch Discord.
    if scheduled_at_changed:
        event_name = (
            f"{resolved_match.player_a or 'TBD'} vs {resolved_match.player_b or 'TBD'} "
            f"({resolved_match.round_name})"
        )
        new_event_id = discord_events.sync_match_event(
            existing_event_id=row.discord_event_id,
            scheduled_at=scheduled_at,
            name=event_name,
        )
        if new_event_id != row.discord_event_id:
            repo.set_discord_event_id(tournament.id, match_id, new_event_id)
            row.discord_event_id = new_event_id

    return _build_output_from_states(tournament, raw_states, allow_preview=True)


def _prediction_is_open(
    status: str, scheduled_at: datetime | None, now: datetime
) -> bool:
    """Predictions stay open while a match is unplayed and, if scheduled,
    hasn't started yet - once the scheduled time passes (or it's scored),
    nobody should be able to "predict" after already knowing the outcome.
    """
    return status == "ready" and (scheduled_at is None or scheduled_at > now)


@router.get("/api/bracket_predictions")
def get_bracket_predictions(
    user: User | None = Depends(get_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
    prediction_repo: BracketPredictionRepo = Depends(get_bracket_prediction_repo),
) -> list[BracketMatchPrediction]:
    """Community "who wins this match" prediction tallies for every match
    with both players known - a hype feature, not authoritative (the real
    result lives in BracketMatchState via resolve_bracket). Reads are open;
    casting (POST) requires login. Withheld entirely before the bracket is
    revealed, same as player placements.
    """
    tournament = repo.get_active()
    if tournament is None or not _is_revealed(tournament, allow_preview=False):
        return []

    raw_states = repo.get_match_states(tournament.id)
    result = _resolve_from_states(tournament, raw_states)
    tallies = prediction_repo.tally_all(tournament.id)
    my_picks = prediction_repo.get_user_picks(tournament.id, user.id) if user else {}
    now = datetime.now(UTC)

    predictions = []
    for m in result.matches:
        if m.player_a is None or m.player_b is None:
            continue
        raw = raw_states.get(m.match_id)
        tally = tallies.get(m.match_id, {})
        predictions.append(
            BracketMatchPrediction(
                match_id=m.match_id,
                tally=tally,
                my_pick=my_picks.get(m.match_id),
                open=_prediction_is_open(
                    m.status, raw.scheduled_at if raw else None, now
                ),
            )
        )
    return predictions


@router.post("/api/bracket_predictions/{match_id}")
def set_bracket_prediction(
    match_id: str,
    req: SetMatchPredictionRequest,
    user: User = Depends(require_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
    prediction_repo: BracketPredictionRepo = Depends(get_bracket_prediction_repo),
) -> BracketMatchPrediction:
    """Set (or clear, with null) the caller's prediction for a match."""
    tournament, raw_states, _result, m = _load_match(repo, match_id)
    if m.player_a is None or m.player_b is None:
        raise HTTPException(
            status_code=400, detail="This match's players aren't determined yet"
        )

    raw = raw_states.get(match_id)
    is_open = _prediction_is_open(
        m.status, raw.scheduled_at if raw else None, datetime.now(UTC)
    )
    if not is_open:
        raise HTTPException(
            status_code=409, detail="Predictions are closed for this match"
        )
    if req.predicted_winner is not None and req.predicted_winner not in (
        m.player_a,
        m.player_b,
    ):
        raise HTTPException(
            status_code=400,
            detail="predicted_winner must be one of this match's players",
        )

    prediction_repo.set_pick(tournament.id, match_id, user.id, req.predicted_winner)
    tally = prediction_repo.tally(tournament.id, match_id)
    return BracketMatchPrediction(
        match_id=match_id,
        tally=tally,
        my_pick=req.predicted_winner,
        open=is_open,
    )
