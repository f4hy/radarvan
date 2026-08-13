"""Detect which played matches belong to which tournament.

The detection rules are pure functions over ``MatchInfo`` - no DB session, no
writes - so they're unit-testable in isolation. What they return are
*proposals*; the one persistence entry point at the bottom of this module
(``sync_links``) applies them, and ``TournamentRepo.link_match`` never lets an
``auto`` proposal overwrite an admin's ``manual`` link.

Two strategies, one per tournament format:

- **Round robin** reuses ``tournament.is_tournament_game`` unchanged - date
  range plus an exact match of both teams against the configured team list.
- **Bracket** matches a scheduled bracket slot against the 1v1s played on
  that game night by exactly those two people.

The bracket rule is the one that has to be careful about names. Bracket slots
hold canonical names (``Gorn``, ``OneThree111``) while ``MatchInfo`` players
hold raw in-game aliases (``Grn``, ``131``), so every comparison goes through
``resolve_player_name``. It also compares against ``human_participants``
rather than all players: a bracket entrant who sat one out as an observer
(e.g. ``Gorn.v.131`` spectating match 1931734) must not make that match look
like their game.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime

import structlog

from . import tournament
from .api_types import MatchInfo
from .db import BracketMatchState, BracketTournament, Tournament
from .repositories import BracketRepo, TournamentRepo
from .repositories.bracket import resolve_from_states
from .utils import game_night_date_of

logger = structlog.get_logger(__name__)

ROUND_ROBIN = "2v2_round_robin"
DOUBLE_ELIM = "1v1_double_elim"


@dataclass(frozen=True, slots=True)
class BracketStage:
    """One scheduled bracket slot to look for played games against.

    Built by the caller from ``BracketMatchState`` + the resolved bracket, so
    this module never touches bracket topology or the DB. Only slots with a
    ``scheduled_at`` and both players known can be matched at all.
    """

    stage: str
    round_name: str
    player_a: str
    player_b: str
    scheduled_at: datetime


@dataclass(frozen=True, slots=True)
class ProposedLink:
    """A match this module believes belongs to a tournament."""

    tournament_slug: str
    match_id: int
    stage: str | None = None
    round_name: str | None = None
    series_index: int | None = None


def _by_game_night(matches: Iterable[MatchInfo]) -> dict[date, list[MatchInfo]]:
    """Index the 1v1s worth considering by the night they were played.

    Every bracket slot only ever looks at one night, so indexing once turns a
    per-stage scan of the whole match table (~30 stages x thousands of
    matches) into a dict lookup over the ~20 games of that night.
    """
    index: defaultdict[date, list[MatchInfo]] = defaultdict(list)
    for m in matches:
        if not m.incomplete and m.composition is not None and m.composition.is_1v1:
            index[m.date].append(m)
    return index


def candidate_games(
    stage: BracketStage, matches: Iterable[MatchInfo]
) -> list[MatchInfo]:
    """The 1v1s that look like games of this bracket match, oldest first.

    Compared on ``MatchInfo.date`` (already the game-night date, Eastern with
    the 5am rollover) against the game night of ``scheduled_at`` - never on
    raw UTC calendar dates, which land a night early for anything after 8pm
    Eastern.

    Incomplete games (disconnect/desync/too-short) are left out: they'd
    inflate ``series_index`` for the real games of a best-of. An admin can
    still link one by hand if it counted.
    """
    return _candidates_from_index(stage, _by_game_night(matches))


def _candidates_from_index(
    stage: BracketStage, by_night: dict[date, list[MatchInfo]]
) -> list[MatchInfo]:
    """``candidate_games`` against an index the caller already built."""
    pair = frozenset({stage.player_a, stage.player_b})
    hits = [
        m
        for m in by_night.get(game_night_date_of(stage.scheduled_at), [])
        if m.roster().human_participant_names() == pair
    ]
    return sorted(hits, key=lambda m: m.timestamp)


def detect_bracket_links(
    slug: str, stages: list[BracketStage], matches: Iterable[MatchInfo]
) -> list[ProposedLink]:
    """Proposed links for every scheduled slot of a bracket tournament.

    A match that somehow matches two slots (the same pair scheduled twice on
    one night) is attributed to the first slot only - double-linking would
    violate the per-tournament unique index and silently reassign the game.
    """
    by_night = _by_game_night(matches)
    claimed: set[int] = set()
    links: list[ProposedLink] = []
    for stage in stages:
        found = _candidates_from_index(stage, by_night)
        contested = [m for m in found if m.id in claimed]
        if contested:
            logger.warning(
                "matches already claimed by an earlier bracket stage",
                match_ids=[m.id for m in contested],
                stage=stage.stage,
            )
        # Number what this stage keeps, not what it found. Today the two are
        # the same or the stage keeps nothing - candidates are keyed on night
        # + pairing, so two stages either see identical lists (the first takes
        # all of them) or disjoint ones. Numbering the survivors means a
        # partial overlap, if that keying ever widens, can't leave a hole that
        # makes the remaining game "game 2" of a series with no game 1.
        for index, match in enumerate(
            (m for m in found if m.id not in claimed), start=1
        ):
            claimed.add(match.id)
            links.append(
                ProposedLink(
                    tournament_slug=slug,
                    match_id=match.id,
                    stage=stage.stage,
                    round_name=stage.round_name,
                    series_index=index,
                )
            )
    return links


def detect_round_robin_links(matches: Iterable[MatchInfo]) -> list[ProposedLink]:
    """Proposed links for the configured round-robin tournaments.

    Membership is still ``tournament.is_tournament_game``; this only persists
    what that rule already decides. ``stage``/``round_name`` stay None - a
    round robin has no rounds, and ``series_index`` orders the whole
    tournament's games by time so reports have a stable sequence.
    """
    by_slug: defaultdict[str, list[MatchInfo]] = defaultdict(list)
    for match in matches:
        # Cheap date gate first: is_tournament_game builds a roster and
        # resolves every name before it checks the window, so without this
        # most of the match table pays for a lookup it can't pass.
        if not any(
            t.start_date <= match.timestamp.date() <= t.end_date
            for t in tournament.TOURNAMENTS
        ):
            continue
        slug = tournament.is_tournament_game(match)
        if slug:
            by_slug[slug].append(match)

    links: list[ProposedLink] = []
    for slug, group in by_slug.items():
        for index, match in enumerate(sorted(group, key=lambda m: m.timestamp), 1):
            links.append(
                ProposedLink(
                    tournament_slug=slug, match_id=match.id, series_index=index
                )
            )
    return links


# --- persistence entry point ---


def bracket_stages(
    bracket_tournament: BracketTournament,
    raw_states: dict[str, BracketMatchState],
) -> list[BracketStage]:
    """The bracket's scheduled, both-players-known slots.

    Resolves the bracket the same way the read endpoints do (topology and
    routing live in ``bracket.py`` and are derived fresh from seeds + scores
    on every call - nothing about who plays whom is stored). Slots without a
    ``scheduled_at`` are skipped: with no date there's no game night to look
    for games on.
    """
    result = resolve_from_states(bracket_tournament, raw_states)

    stages = []
    for match in result.matches:
        row = raw_states.get(match.match_id)
        if row is None or row.scheduled_at is None:
            continue
        if match.player_a is None or match.player_b is None:
            continue
        stages.append(
            BracketStage(
                stage=match.match_id,
                round_name=match.round_name,
                player_a=match.player_a,
                player_b=match.player_b,
                scheduled_at=row.scheduled_at,
            )
        )
    return stages


def sync_links(
    tournament_repo: TournamentRepo,
    bracket_repo: BracketRepo,
    matches: list[MatchInfo],
) -> dict[str, int]:
    """Register the known tournaments and persist every detected link.

    Idempotent: re-running only adds links for games that have since been
    played (and refreshes stage/series metadata on ``auto`` rows when a
    bracket is rescheduled). Manual links are left alone entirely.

    Callers must invalidate the match caches afterwards - ``MatchInfo`` is
    cached on ``latest_match_ts``, which doesn't move when a link is written
    for a match that already existed.
    """
    proposals: list[ProposedLink] = []
    # Each upsert already returns the row, so keep it: looking the tournament
    # back up per proposal is one query per linked game.
    id_by_slug: dict[str, int] = {}

    today = datetime.now(UTC).date()
    for config in tournament.TOURNAMENTS:
        row = tournament_repo.upsert_tournament(
            slug=config.name,
            name=config.name.replace("_", " "),
            tournament_format=ROUND_ROBIN,
            start_date=config.start_date,
            end_date=config.end_date,
            status="complete" if config.end_date < today else "active",
        )
        id_by_slug[row.slug] = row.id
    proposals.extend(detect_round_robin_links(matches))

    active = bracket_repo.get_active()
    if active is not None:
        bracket_row = (
            tournament_repo.get_tournament_by_id(active.tournament_id)
            if active.tournament_id
            else None
        )
        if bracket_row is None:
            bracket_row = _mint_bracket_tournament(tournament_repo, active)
            bracket_repo.set_tournament_id(active.id, bracket_row.id)
        id_by_slug[bracket_row.slug] = bracket_row.id
        raw_states = bracket_repo.get_match_states(active.id)
        proposals.extend(
            detect_bracket_links(
                bracket_row.slug, bracket_stages(active, raw_states), matches
            )
        )

    for proposal in proposals:
        tournament_repo.link_match(
            tournament_id=id_by_slug[proposal.tournament_slug],
            match_id=proposal.match_id,
            stage=proposal.stage,
            round_name=proposal.round_name,
            series_index=proposal.series_index,
            source="auto",
        )

    retracted = _retract_stale_links(tournament_repo, id_by_slug, proposals)
    excluded = _apply_known_exclusions(tournament_repo, id_by_slug)

    counts = {
        "tournaments": len(id_by_slug),
        "linked": len(proposals),
        "retracted": retracted,
        "excluded": excluded,
    }
    logger.info("synced tournament links", **counts)
    return counts


def _mint_bracket_tournament(
    tournament_repo: TournamentRepo, active: BracketTournament
) -> Tournament:
    """Create the registry row for a bracket nobody gave an identity.

    The slug is made unique rather than reused: creating/resetting a bracket
    leaves ``tournament_id`` NULL again, and reusing ``{year}_1v1_bracket``
    would re-point the *new* bracket at the *old* bracket's tournament - both
    brackets' games merging under one slug, with colliding stage ids. A
    second bracket in the same year gets ``_2``, and the finished one keeps
    its games. (Assigning identity at create time would be better still; see
    ``CreateBracketRequest``.)
    """
    year = active.created_at.year
    base = f"{year}_1v1_bracket"
    slug, suffix = base, 1
    while tournament_repo.get_tournament_by_slug(slug) is not None:
        suffix += 1
        slug = f"{base}_{suffix}"
    name = f"{year} 1v1 Bracket" if suffix == 1 else f"{year} 1v1 Bracket #{suffix}"
    return tournament_repo.upsert_tournament(
        slug=slug, name=name, tournament_format=DOUBLE_ELIM
    )


def _retract_stale_links(
    tournament_repo: TournamentRepo,
    id_by_slug: dict[str, int],
    proposals: list[ProposedLink],
) -> int:
    """Drop ``auto`` links the detector no longer proposes.

    Without this a reschedule is additive: move a bracket match to another
    night and the old night's games keep their stage rows alongside the new
    ones, so the match appears to have been played twice. Only tournaments
    synced in this run are touched - a finished bracket's tournament is never
    revisited, which is what keeps its games after the next bracket replaces
    it. ``manual`` links and tombstones are never retracted; an admin's
    judgement outranks the rule.
    """
    proposed_by_tournament: defaultdict[int, set[int]] = defaultdict(set)
    for proposal in proposals:
        proposed_by_tournament[id_by_slug[proposal.tournament_slug]].add(
            proposal.match_id
        )

    retracted = 0
    for tournament_id in id_by_slug.values():
        keep = proposed_by_tournament[tournament_id]
        for link in tournament_repo.list_links(tournament_id, include_excluded=True):
            if link.source == "auto" and link.match_id not in keep:
                tournament_repo.unlink_match(tournament_id, link.match_id)
                retracted += 1
    return retracted


def _apply_known_exclusions(
    tournament_repo: TournamentRepo, id_by_slug: dict[str, int]
) -> int:
    """Re-assert ``tournament.KNOWN_EXCLUSIONS`` as tombstones.

    These are permanent editorial decisions that live in code so a rebuilt
    database reaches the same answer; writing one by hand would only ever fix
    the database it was typed into.
    """
    excluded = 0
    for slug, match_ids in tournament.KNOWN_EXCLUSIONS.items():
        tournament_id = id_by_slug.get(slug)
        if tournament_id is None:
            continue
        for match_id in match_ids:
            tournament_repo.exclude_match(tournament_id, match_id)
            excluded += 1
    return excluded
