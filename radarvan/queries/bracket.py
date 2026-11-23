"""Bracket read models - what the public may see of the active bracket.

Shared by `routes/bracket.py`, the bracket recap gate in `routes/commentary.py`
and `commentary.matchup_commentary`. The pre-reveal redaction lives here so a
non-HTTP caller can't build a prompt from placements the public can't see yet.
"""

from datetime import UTC, datetime
from typing import NamedTuple

from .. import bracket, tournament_membership
from ..api_types import (
    BracketMatchGames,
    BracketMatchOutput,
    BracketPlayerEntry,
    BracketTournamentOutput,
    LoserOfSource,
    MatchInfo,
    MatchSource,
    SeedSource,
    WinnerOfSource,
)
from ..cache import sorted_deduped_matches
from ..db import BracketMatchState, BracketTournament, Tournament
from ..db_utils import ReplayManager
from ..repositories import BracketRepo, TournamentRepo
from ..repositories.bracket import resolve_from_states


class BracketMatchNotFound(LookupError):
    """No active bracket, or no such match in it. ``str()`` is the 404 detail."""


class LoadedMatch(NamedTuple):
    """The active bracket, its raw rows, the resolution, and one match in it."""

    tournament: BracketTournament
    raw_states: dict[str, BracketMatchState]
    result: bracket.BracketResult
    resolved_match: bracket.ResolvedMatch


def load_match(repo: BracketRepo, match_id: str) -> LoadedMatch:
    """Resolve the active bracket and locate ``match_id`` in it."""
    tournament = repo.get_active()
    if tournament is None:
        raise BracketMatchNotFound("No active bracket tournament")
    if not bracket.is_valid_match_id(match_id, len(tournament.players)):
        raise BracketMatchNotFound("Unknown match id")
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
    """True once placements may be shown. Server clock only; ``allow_preview``
    must come from an authenticated tournament admin."""
    if allow_preview:
        return True
    return tournament.reveal_at is None or datetime.now(UTC) >= tournament.reveal_at


def _to_api_source(source: bracket.Source) -> MatchSource:
    if isinstance(source, bracket.Seed):
        return SeedSource(seed=source.seed)
    if isinstance(source, bracket.WinnerOf):
        return WinnerOfSource(match_id=source.match_id)
    return LoserOfSource(match_id=source.match_id)


def _redact(output: BracketTournamentOutput) -> BracketTournamentOutput:
    """Null out everything that says who is in which slot; the roster, bracket
    shape and scores stay visible."""
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


def build_output_from_states(
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


def build_output(
    tournament: BracketTournament, repo: BracketRepo, *, allow_preview: bool = False
) -> BracketTournamentOutput:
    return build_output_from_states(
        tournament, repo.get_match_states(tournament.id), allow_preview=allow_preview
    )


def active_bracket(
    repo: BracketRepo, *, allow_preview: bool
) -> BracketTournamentOutput | None:
    """The active bracket (redacted before reveal), or None if none exists."""
    tournament = repo.get_active()
    if tournament is None:
        return None
    return build_output(tournament, repo, allow_preview=allow_preview)


def tournament_for_bracket(
    tournament: BracketTournament, tournament_repo: TournamentRepo
) -> Tournament | None:
    """The durable Tournament row this bracket writes its game links to."""
    if tournament.tournament_id is None:
        return None
    return tournament_repo.get_tournament_by_id(tournament.tournament_id)


def match_games_response(
    match_id: str,
    resolved: bracket.ResolvedMatch,
    scheduled_at: datetime | None,
    parent: Tournament | None,
    all_matches: dict[int, MatchInfo],
    tournament_repo: TournamentRepo,
) -> BracketMatchGames:
    """Linked games for a bracket match, plus unconfirmed detector candidates.

    Linked games come from the link table, not the denormalized MatchInfo tag.
    Candidates are computed exactly as the backfill would link them.
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
        elsewhere = frozenset(
            link.match_id for link in all_links if link.stage != match_id
        )
        candidates = [
            m
            for m in tournament_membership.candidate_games(
                stage, all_matches.values(), elsewhere
            )
            if m.id not in spoken_for
        ]
    return BracketMatchGames(match_id=match_id, linked=linked, candidates=candidates)


def match_games(
    loaded: LoadedMatch,
    tournament_repo: TournamentRepo,
    replay_manager: ReplayManager,
    *,
    allow_preview: bool,
) -> BracketMatchGames:
    """The games played for one bracket match; empty before reveal, since they
    name the two players."""
    match_id = loaded.resolved_match.match_id
    if not is_revealed(loaded.tournament, allow_preview=allow_preview):
        return BracketMatchGames(match_id=match_id)
    parent = tournament_for_bracket(loaded.tournament, tournament_repo)
    raw = loaded.raw_states.get(match_id)
    return match_games_response(
        match_id,
        loaded.resolved_match,
        raw.scheduled_at if raw else None,
        parent,
        sorted_deduped_matches(replay_manager),
        tournament_repo,
    )
