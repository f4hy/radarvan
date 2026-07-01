"""Fixed 12-entrant double-elimination bracket: static topology + pure resolution.

The topology below is hand-derived and verified (not a generic N-player
algorithm — this bracket is always exactly 12 seeded entrants). Standard
bracket-size-16 seeding gives winners-bracket round 1 four real matches
(8v9, 5v12, 7v10, 6v11) with seeds 1-4 byeing straight to round 2; every
round after that is a clean power-of-two single elimination. The losers
bracket has an inherent sizing mismatch after round 1 (only 4 winners-bracket
round-1 losers vs. round 2's 4 losers, since byes mean round 1 dropped fewer
losers than a full bracket would) — LB round 2 is split into a "2a" round
that lets the fresh round-2 droppers play each other and a "2b" round that
merges them with round 1's survivors, which is the standard way real
bracket generators reconcile this. Verified by loss-accounting: every match
produces exactly one loss, and a double-elim bracket for N entrants needs
exactly 2*(N-1) losses (here 22) to reach a champion, or 2*(N-1)+1 (23) if
the grand final goes to a reset — this topology sums to exactly that.
"""

from dataclasses import dataclass
from typing import Literal

BracketType = Literal["W", "L", "GF"]
MatchStatus = Literal["pending", "ready", "completed", "not_applicable"]


@dataclass(frozen=True)
class Seed:
    seed: int


@dataclass(frozen=True)
class WinnerOf:
    match_id: str


@dataclass(frozen=True)
class LoserOf:
    match_id: str


Source = Seed | WinnerOf | LoserOf


@dataclass(frozen=True)
class MatchDef:
    match_id: str
    bracket: BracketType
    round_number: int
    round_name: str
    slot_a: Source
    slot_b: Source


# Seeds that bye straight through winners-bracket round 1 to round 2.
BYE_SEEDS: tuple[int, ...] = (1, 2, 3, 4)

TOPOLOGY: list[MatchDef] = [
    # Winners bracket round 1 (4 real matches; seeds 1-4 bye to round 2).
    MatchDef("WB1-1", "W", 1, "Winners Round 1", Seed(8), Seed(9)),
    MatchDef("WB1-2", "W", 1, "Winners Round 1", Seed(5), Seed(12)),
    MatchDef("WB1-3", "W", 1, "Winners Round 1", Seed(7), Seed(10)),
    MatchDef("WB1-4", "W", 1, "Winners Round 1", Seed(6), Seed(11)),
    # Winners bracket round 2.
    MatchDef("WB2-1", "W", 2, "Winners Round 2", Seed(1), WinnerOf("WB1-1")),
    MatchDef("WB2-2", "W", 2, "Winners Round 2", Seed(4), WinnerOf("WB1-2")),
    MatchDef("WB2-3", "W", 2, "Winners Round 2", Seed(2), WinnerOf("WB1-3")),
    MatchDef("WB2-4", "W", 2, "Winners Round 2", Seed(3), WinnerOf("WB1-4")),
    # Winners bracket semifinals.
    MatchDef(
        "WB3-1", "W", 3, "Winners Semifinal", WinnerOf("WB2-1"), WinnerOf("WB2-2")
    ),
    MatchDef(
        "WB3-2", "W", 3, "Winners Semifinal", WinnerOf("WB2-3"), WinnerOf("WB2-4")
    ),
    # Winners bracket final.
    MatchDef("WB4-1", "W", 4, "Winners Final", WinnerOf("WB3-1"), WinnerOf("WB3-2")),
    # Losers bracket round 1: pair winners-round-1 losers among themselves.
    MatchDef("LB1-1", "L", 1, "Losers Round 1", LoserOf("WB1-1"), LoserOf("WB1-2")),
    MatchDef("LB1-2", "L", 1, "Losers Round 1", LoserOf("WB1-3"), LoserOf("WB1-4")),
    # Losers bracket round 2a: pair winners-round-2 losers among themselves
    # (reconciles LB1's 2 survivors against WB2's 4 fresh droppers).
    MatchDef("LB2a-1", "L", 2, "Losers Round 2a", LoserOf("WB2-1"), LoserOf("WB2-2")),
    MatchDef("LB2a-2", "L", 2, "Losers Round 2a", LoserOf("WB2-3"), LoserOf("WB2-4")),
    # Losers bracket round 2b: LB1 survivors vs LB2a survivors.
    MatchDef(
        "LB2b-1", "L", 2, "Losers Round 2b", WinnerOf("LB1-1"), WinnerOf("LB2a-1")
    ),
    MatchDef(
        "LB2b-2", "L", 2, "Losers Round 2b", WinnerOf("LB1-2"), WinnerOf("LB2a-2")
    ),
    # Losers bracket round 3: LB2b survivors vs winners-semifinal losers.
    MatchDef("LB3-1", "L", 3, "Losers Round 3", WinnerOf("LB2b-1"), LoserOf("WB3-1")),
    MatchDef("LB3-2", "L", 3, "Losers Round 3", WinnerOf("LB2b-2"), LoserOf("WB3-2")),
    # Losers bracket round 4: pair LB3 survivors.
    MatchDef("LB4-1", "L", 4, "Losers Round 4", WinnerOf("LB3-1"), WinnerOf("LB3-2")),
    # Losers bracket round 5: LB4 survivor vs winners-final loser -> LB champion.
    MatchDef("LB5-1", "L", 5, "Losers Final", WinnerOf("LB4-1"), LoserOf("WB4-1")),
    # Grand final; GF-2 (bracket reset) only applies if the losers-bracket
    # entrant (slot_b) wins GF-1.
    MatchDef("GF-1", "GF", 1, "Grand Final", WinnerOf("WB4-1"), WinnerOf("LB5-1")),
    MatchDef(
        "GF-2", "GF", 2, "Grand Final Reset", WinnerOf("WB4-1"), WinnerOf("LB5-1")
    ),
]

_BY_ID: dict[str, MatchDef] = {m.match_id: m for m in TOPOLOGY}


def is_valid_match_id(match_id: str) -> bool:
    return match_id in _BY_ID


@dataclass
class MatchState:
    """Mutable, persisted per-match state (everything else is derived)."""

    best_of: int | None = None
    score_a: int | None = None
    score_b: int | None = None


@dataclass
class ResolvedMatch:
    match_id: str
    bracket: BracketType
    round_number: int
    round_name: str
    player_a: str | None
    player_b: str | None
    winner: str | None
    loser: str | None
    status: MatchStatus


@dataclass
class BracketResult:
    matches: list[ResolvedMatch]
    bye_advances: list[tuple[int, str]]
    champion: str | None
    runner_up: str | None
    needs_reset: bool


def win_threshold(best_of: int) -> int:
    """Wins needed to take a best-of-N match."""
    return best_of // 2 + 1


def validate_score(best_of: int, score_a: int, score_b: int) -> None:
    """Raise ValueError if this score is not a valid best-of-N result."""
    if best_of not in (3, 5, 7, 9):
        raise ValueError(f"invalid best_of {best_of}")
    if score_a < 0 or score_b < 0:
        raise ValueError("scores must be non-negative")
    threshold = win_threshold(best_of)
    hi, lo = max(score_a, score_b), min(score_a, score_b)
    if hi != threshold:
        raise ValueError(
            f"winning score must be exactly {threshold} for best of {best_of}"
        )
    if lo >= threshold:
        raise ValueError("scores cannot both reach the winning threshold")


def resolve_bracket(
    seed_to_name: dict[int, str],
    match_states: dict[str, MatchState],
) -> BracketResult:
    """Walk the static topology and derive every match's players/winner/status.

    ``match_states`` holds only what's persisted (best_of + scores) per match
    id; everything else — who plays whom, whether a match is playable yet,
    who the champion is — is derived fresh each call.
    """
    winners: dict[str, str] = {}
    losers: dict[str, str] = {}
    resolved: dict[str, ResolvedMatch] = {}

    def resolve_source(src: Source) -> str | None:
        if isinstance(src, Seed):
            return seed_to_name.get(src.seed)
        if isinstance(src, WinnerOf):
            return winners.get(src.match_id)
        return losers.get(src.match_id)

    for m in TOPOLOGY:
        player_a = resolve_source(m.slot_a)
        player_b = resolve_source(m.slot_b)

        if m.match_id == "GF-2":
            gf1 = resolved["GF-1"]
            applicable = gf1.status == "completed" and gf1.winner == player_b
            if not applicable:
                resolved[m.match_id] = ResolvedMatch(
                    match_id=m.match_id,
                    bracket=m.bracket,
                    round_number=m.round_number,
                    round_name=m.round_name,
                    player_a=player_a,
                    player_b=player_b,
                    winner=None,
                    loser=None,
                    status="not_applicable",
                )
                continue

        state = match_states.get(m.match_id)
        winner: str | None = None
        loser: str | None = None
        status: MatchStatus
        if player_a is None or player_b is None:
            status = "pending"
        elif (
            state is None
            or state.best_of is None
            or state.score_a is None
            or state.score_b is None
            or state.score_a == state.score_b
        ):
            status = "ready"
        else:
            if state.score_a > state.score_b:
                winner, loser = player_a, player_b
            else:
                winner, loser = player_b, player_a
            status = "completed"

        resolved[m.match_id] = ResolvedMatch(
            match_id=m.match_id,
            bracket=m.bracket,
            round_number=m.round_number,
            round_name=m.round_name,
            player_a=player_a,
            player_b=player_b,
            winner=winner,
            loser=loser,
            status=status,
        )
        if winner is not None:
            winners[m.match_id] = winner
        if loser is not None:
            losers[m.match_id] = loser

    gf1 = resolved["GF-1"]
    gf2 = resolved["GF-2"]
    needs_reset = gf2.status != "not_applicable"
    if needs_reset:
        champion, runner_up = gf2.winner, gf2.loser
    else:
        champion, runner_up = gf1.winner, gf1.loser

    bye_advances = [(s, seed_to_name[s]) for s in BYE_SEEDS if s in seed_to_name]

    return BracketResult(
        matches=list(resolved.values()),
        bye_advances=bye_advances,
        champion=champion,
        runner_up=runner_up,
        needs_reset=needs_reset,
    )
