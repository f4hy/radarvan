"""1v1 double-elimination bracket tournament endpoints.

Public reads; tournament-admin-gated writes (create/reset the bracket, set a
match's date/best-of/score). Privilege follows the authenticated Discord ID,
not the user-selectable player association.

``/api/bracket_eligible_players`` is deliberately a separate top-level path
rather than nested under ``/api/bracket`` - the OpenAPI client generator can
silently merge a static path with a parameterized sibling that shares a
prefix (see CLAUDE.md gotcha re: ``/api/map_data/by_player_count`` vs.
``/api/map_data/{map_name}``).
"""

from datetime import UTC, datetime
from typing import NamedTuple

import structlog

from fastapi import APIRouter, Depends, HTTPException

from .. import bracket, discord_events, map_stats, player_ids, tournament_membership
from ..api_types import (
    BracketMatchGames,
    BracketMatchOutput,
    BracketPlayerEntry,
    BracketPredictionLeaderboardEntry,
    BracketTournamentOutput,
    CreateBracketRequest,
    LoserOfSource,
    MatchInfo,
    BracketMatchPrediction,
    MapPlayerRecords,
    MatchSource,
    SeedSource,
    SetBracketGamesRequest,
    SetBracketMatchRequest,
    SetBracketRevealAtRequest,
    SetMatchPredictionRequest,
    WinnerOfSource,
)
from ..cache import invalidate_match_caches, sorted_deduped_matches
from ..db import BracketMatchState, BracketTournament, Tournament, User
from ..db_utils import ReplayManager
from ..dependencies import (
    get_bracket_prediction_repo,
    get_bracket_repo,
    get_current_user,
    get_replay_manager,
    get_tournament_repo,
    require_current_user,
)
from ..repositories import BracketPredictionRepo, BracketRepo, TournamentRepo
from ..repositories.bracket import (
    resolve_from_states,
    seed_to_name,
    states_from_rows,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["bracket"])


def _require_tournament_admin(user: User) -> None:
    if not player_ids.is_tournament_admin(user.discord_id):
        raise HTTPException(status_code=403, detail="Forbidden")


def _to_api_source(source: bracket.Source) -> MatchSource:
    if isinstance(source, bracket.Seed):
        return SeedSource(seed=source.seed)
    if isinstance(source, bracket.WinnerOf):
        return WinnerOfSource(match_id=source.match_id)
    return LoserOfSource(match_id=source.match_id)


class LoadedMatch(NamedTuple):
    """The active bracket, its raw rows, the resolution, and one match in it."""

    tournament: BracketTournament
    raw_states: dict[str, BracketMatchState]
    result: bracket.BracketResult
    resolved_match: bracket.ResolvedMatch


def load_match(repo: BracketRepo, match_id: str) -> LoadedMatch:
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
    result = resolve_from_states(tournament, raw_states)
    resolved_match = next(m for m in result.matches if m.match_id == match_id)
    return LoadedMatch(
        tournament=tournament,
        raw_states=raw_states,
        result=result,
        resolved_match=resolved_match,
    )


def is_revealed(tournament: BracketTournament, *, allow_preview: bool) -> bool:
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
    result = resolve_from_states(tournament, raw_states)

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
        revealed=is_revealed(tournament, allow_preview=allow_preview),
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
        preview and user is not None and player_ids.is_tournament_admin(user.discord_id)
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
    tournament, raw_states, before, resolved_match = load_match(repo, match_id)
    existing = raw_states.get(match_id)

    def merged[T](field: str, current: T) -> T:
        value: T = getattr(req, field)
        return value if field in req.model_fields_set else current

    scheduled_at = merged("scheduled_at", existing.scheduled_at if existing else None)
    best_of = merged("best_of", existing.best_of if existing else None)
    score_a = merged("score_a", existing.score_a if existing else None)
    score_b = merged("score_b", existing.score_b if existing else None)

    names_by_seed = seed_to_name(tournament)
    states = states_from_rows(raw_states)

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
        after = bracket.resolve_bracket(names_by_seed, new_states)
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

    scheduled_at_changed = scheduled_at != (existing.scheduled_at if existing else None)

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


def tournament_for_bracket(
    tournament: BracketTournament, tournament_repo: TournamentRepo
) -> Tournament | None:
    """The durable Tournament row this bracket writes its game links to."""
    if tournament.tournament_id is None:
        return None
    return tournament_repo.get_tournament_by_id(tournament.tournament_id)


def _games_response(
    match_id: str,
    resolved: bracket.ResolvedMatch,
    scheduled_at: datetime | None,
    parent: Tournament | None,
    all_matches: dict[int, MatchInfo],
    tournament_repo: TournamentRepo,
) -> BracketMatchGames:
    """Linked games for a bracket match, plus unconfirmed detector candidates.

    Linked games come from the indexed link table, not from scanning every
    MatchInfo for a matching tag - the tag is a denormalized copy, and reading
    the rows keeps this endpoint agreeing with the writes below it.

    Candidates are computed the same way the backfill does, so what an admin
    sees offered here is exactly what an automatic run would have linked.
    """
    if parent is None:
        return BracketMatchGames(match_id=match_id)

    # Every link of this tournament, not just this stage's: a game already
    # linked elsewhere must not be offered as a candidate here. Adding it
    # would rewrite that row's stage (the unique key is (tournament, match))
    # and silently take the game off the other match - the same collision
    # `detect_bracket_links` guards against with its `claimed` set.
    all_links = tournament_repo.list_links(parent.id)
    spoken_for = {link.match_id for link in all_links}
    linked = sorted(
        (
            all_matches[link.match_id]
            for link in all_links
            if link.stage == match_id and link.match_id in all_matches
        ),
        key=lambda m: m.timestamp,
    )

    candidates: list[MatchInfo] = []
    if scheduled_at is not None and resolved.player_a and resolved.player_b:
        stage = tournament_membership.BracketStage(
            stage=match_id,
            round_name=resolved.round_name,
            player_a=resolved.player_a,
            player_b=resolved.player_b,
            scheduled_at=scheduled_at,
        )
        candidates = [
            m
            for m in tournament_membership.candidate_games(stage, all_matches.values())
            if m.id not in spoken_for
        ]
    return BracketMatchGames(match_id=match_id, linked=linked, candidates=candidates)


@router.get("/api/bracket_games/{match_id}")
def get_bracket_games(
    match_id: str,
    user: User | None = Depends(get_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
    tournament_repo: TournamentRepo = Depends(get_tournament_repo),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> BracketMatchGames:
    """The games actually played for one bracket match.

    A distinct top-level path rather than ``/api/bracket/{match_id}/games``
    for the same reason ``/api/bracket_eligible_players`` is - the OpenAPI
    generator merges sibling paths sharing a parameterized prefix.

    Readable without an account once the bracket is revealed - which games
    were played is what the Matches page already shows. Before ``reveal_at``
    it returns nothing: both the linked MatchInfos and the detector
    candidates name the two players, which is exactly what ``_redact``
    withholds from ``GET /api/bracket``. Editing is admin-gated below.
    """
    tournament_row, raw_states, _result, resolved = load_match(repo, match_id)
    is_admin = user is not None and player_ids.is_tournament_admin(user.discord_id)
    if not is_revealed(tournament_row, allow_preview=is_admin):
        return BracketMatchGames(match_id=match_id)
    parent = tournament_for_bracket(tournament_row, tournament_repo)
    raw = raw_states.get(match_id)
    return _games_response(
        match_id,
        resolved,
        raw.scheduled_at if raw else None,
        parent,
        sorted_deduped_matches(replay_manager),
        tournament_repo,
    )


@router.post("/api/bracket_games/{match_id}")
def set_bracket_games(
    match_id: str,
    req: SetBracketGamesRequest,
    user: User = Depends(require_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
    tournament_repo: TournamentRepo = Depends(get_tournament_repo),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> BracketMatchGames:
    """Link matches to this bracket match (admin only).

    Written as ``manual`` links, which the auto-detector will never overwrite
    or remove. Replaces the full set for this stage: anything previously
    linked and not in ``match_ids`` is excluded rather than deleted, so a
    later detector run doesn't just put it back.
    """
    _require_tournament_admin(user)
    tournament_row, raw_states, _result, resolved = load_match(repo, match_id)
    parent = tournament_for_bracket(tournament_row, tournament_repo)
    if parent is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This bracket isn't registered as a tournament yet - run "
                "POST /api/backfill/tournament_games first."
            ),
        )

    wanted = set(req.match_ids)
    known = sorted_deduped_matches(replay_manager)
    unknown = sorted(wanted - set(known))
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown match ids: {unknown}")

    existing = {
        link.match_id for link in tournament_repo.list_links(parent.id, stage=match_id)
    }
    for match_id_to_drop in existing - wanted:
        tournament_repo.exclude_match(parent.id, match_id_to_drop, stage=match_id)
    for index, linked_id in enumerate(
        sorted(wanted, key=lambda m: known[m].timestamp), start=1
    ):
        tournament_repo.link_match(
            tournament_id=parent.id,
            match_id=linked_id,
            stage=match_id,
            round_name=resolved.round_name,
            series_index=index,
            source="manual",
        )

    logger.info(
        "bracket games set", user_id=user.id, match_id=match_id, games=sorted(wanted)
    )
    raw = raw_states.get(match_id)
    response = _games_response(
        match_id,
        resolved,
        raw.scheduled_at if raw else None,
        parent,
        known,
        tournament_repo,
    )
    # Last, and after the response is built off `known`: MatchInfo is cached on
    # the corpus probe, which doesn't move when a link is written for a match
    # that already existed, so the tags need dropping - but invalidating first
    # would make the response build re-derive every MatchInfo in the DB.
    invalidate_match_caches()
    return response


@router.get("/api/bracket_map_records")
def get_bracket_map_records(
    user: User | None = Depends(get_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
    tournament_repo: TournamentRepo = Depends(get_tournament_repo),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MapPlayerRecords]:
    """Each map's per-player records across every game linked to the bracket.

    Derived from the same persisted links ``/api/bracket_games`` reads, so an
    admin's manual link or exclusion is reflected here too. Empty before
    ``reveal_at`` for the same reason ``get_bracket_games`` is: the records
    name who played whom.
    """
    tournament_row = repo.get_active()
    if tournament_row is None:
        return []
    is_admin = user is not None and player_ids.is_tournament_admin(user.discord_id)
    if not is_revealed(tournament_row, allow_preview=is_admin):
        return []
    parent = tournament_for_bracket(tournament_row, tournament_repo)
    if parent is None:
        return []
    known = sorted_deduped_matches(replay_manager)
    games = [
        known[link.match_id]
        for link in tournament_repo.list_links(parent.id)
        if link.match_id in known
    ]
    return map_stats.map_player_records(games)


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
    if tournament is None or not is_revealed(tournament, allow_preview=False):
        return []

    raw_states = repo.get_match_states(tournament.id)
    result = resolve_from_states(tournament, raw_states)
    tallies = prediction_repo.tally_all(tournament.id)
    my_picks = prediction_repo.get_user_picks(tournament.id, user.id) if user else {}
    now = datetime.now(UTC)

    correct_names_by_match = _resolved_predictions(
        prediction_repo, tournament, result
    ).correct_by_match

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
                correct_picks=correct_names_by_match.get(m.match_id)
                if m.status == "completed"
                else None,
            )
        )
    return predictions


class ResolvedPredictions(NamedTuple):
    """Per-match "who called it" name lists, plus the overall leaderboard."""

    correct_by_match: dict[str, list[str]]
    leaderboard: list[BracketPredictionLeaderboardEntry]


def _resolved_predictions(
    prediction_repo: BracketPredictionRepo,
    tournament: BracketTournament,
    result: bracket.BracketResult,
) -> ResolvedPredictions:
    """Walks every prediction once and derives both per-match "who called
    it" name lists and the overall per-user leaderboard, restricted to
    matches that have completed (winners come from the already-resolved
    bracket - bracket.py owns that logic, not stored on the prediction
    rows). Shared so ``get_bracket_predictions`` and the leaderboard
    endpoint agree on exactly the same notion of "correct".
    """
    winners = {
        m.match_id: m.winner
        for m in result.matches
        if m.status == "completed" and m.winner is not None
    }
    correct_by_match: dict[str, list[str]] = {}
    tallies: dict[str, dict[str, int]] = {}
    for (
        match_id,
        predicted_winner,
        display_name,
    ) in prediction_repo.all_picks_with_names(tournament.id):
        winner = winners.get(match_id)
        if winner is None:
            continue
        entry = tallies.setdefault(display_name, {"correct": 0, "total": 0})
        entry["total"] += 1
        if predicted_winner == winner:
            entry["correct"] += 1
            correct_by_match.setdefault(match_id, []).append(display_name)

    leaderboard = [
        BracketPredictionLeaderboardEntry(
            user_name=name, correct=counts["correct"], total=counts["total"]
        )
        for name, counts in tallies.items()
    ]
    leaderboard.sort(key=lambda e: (-e.correct, -e.total, e.user_name))
    return ResolvedPredictions(
        correct_by_match=correct_by_match, leaderboard=leaderboard
    )


@router.get("/api/bracket_prediction_leaderboard")
def get_bracket_prediction_leaderboard(
    repo: BracketRepo = Depends(get_bracket_repo),
    prediction_repo: BracketPredictionRepo = Depends(get_bracket_prediction_repo),
) -> list[BracketPredictionLeaderboardEntry]:
    """Ranked "who's called the most winners" standings for the active
    tournament - only counts predictions against matches that have
    completed, so an unfinished bracket's leaderboard only grows, it never
    reshuffles into an incomplete-looking mid-guess state. Empty (not 404)
    before a tournament exists or before it's revealed, same as
    ``get_bracket_predictions``.
    """
    tournament = repo.get_active()
    if tournament is None or not is_revealed(tournament, allow_preview=False):
        return []

    raw_states = repo.get_match_states(tournament.id)
    result = resolve_from_states(tournament, raw_states)
    return _resolved_predictions(prediction_repo, tournament, result).leaderboard


@router.post("/api/bracket_predictions/{match_id}")
def set_bracket_prediction(
    match_id: str,
    req: SetMatchPredictionRequest,
    user: User = Depends(require_current_user),
    repo: BracketRepo = Depends(get_bracket_repo),
    prediction_repo: BracketPredictionRepo = Depends(get_bracket_prediction_repo),
) -> BracketMatchPrediction:
    """Set (or clear, with null) the caller's prediction for a match."""
    tournament, raw_states, _result, m = load_match(repo, match_id)
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
