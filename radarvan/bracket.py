"""Double-elimination bracket for 9-16 entrants: topology generation + pure resolution.

The bracket size is always fixed at 16 (never shrinks for smaller fields) —
a 9-11 player tournament is "effectively a 16-person bracket with more byes",
not a smaller bracket. Standard bracket-size-16 seeding (``seed_order(16)``)
assigns byes to whichever seeds' round-1 opponent would exceed the actual
entrant count; every round after round 1 is a clean power-of-two single
elimination (8→4→2→1), regardless of how many byes there were.

The losers bracket is the genuinely tricky part: round 1's bye count shrinks
the population of first-round losers relative to a full 16-bracket, so the
survivor count arriving at each subsequent "meet the newly-dropped losers"
stage doesn't line up 1:1 without reconciliation. ``build_topology`` handles
this generically via two primitives — ``_reduce_to`` (repeated self-pairing
to shrink a population down to a target size, tolerating an odd population
by carrying one entrant through untested each round) and ``_merge_wave``
(levels two populations to the same size via ``_reduce_to`` before pairing
them 1:1) — verified by hand for every bye count 0-7 (equivalently 16-9
entrants) via loss-accounting: every match produces exactly one loss, and a
double-elim bracket for N entrants needs exactly 2*(N-1) losses (or
2*(N-1)+1 with a grand-final reset) to reach a champion. The old fixed-12
topology (byes=4) is a special case of this and collapses onto exactly the
same match structure.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

BracketType = Literal["W", "L", "GF"]
MatchStatus = Literal["pending", "ready", "completed", "not_applicable"]

MIN_PLAYERS = 9
MAX_PLAYERS = 16


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


@dataclass
class Topology:
    matches: list[MatchDef]
    bye_seeds: list[int]


def seed_order(n: int) -> list[int]:
    """Standard recursive tournament seeding order for a bracket of size n.

    E.g. seed_order(16) == [1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11] — the
    textbook seeding so that top seeds meet as late as possible.
    """
    if n == 1:
        return [1]
    prev = seed_order(n // 2)
    result: list[int] = []
    for s in prev:
        result.append(s)
        result.append(n + 1 - s)
    return result


_SEED_ORDER_16 = seed_order(16)


def _reduce_to(
    pool: list[Source], target: int, round_counter: list[int]
) -> tuple[list[Source], list[MatchDef]]:
    """Repeatedly self-pair ``pool`` down to exactly ``target`` (0+ rounds).

    Each round pairs off just enough entrants to reach `target` in one more
    round (``ceil(len/2)``, clamped at ``target``), leaving the rest to carry
    through untouched — so an odd `pool` never gets stuck.
    """
    all_matches: list[MatchDef] = []
    while len(pool) > target:
        length = len(pool)
        new_len = max(target, -(-length // 2))  # ceil(length / 2)
        k = length - new_len
        round_counter[0] += 1
        rnum = round_counter[0]
        matches = [
            MatchDef(
                f"LB{rnum}-{i + 1}",
                "L",
                rnum,
                f"Losers Round {rnum}",
                pool[2 * i],
                pool[2 * i + 1],
            )
            for i in range(k)
        ]
        leftover = pool[2 * k :]
        pool = [WinnerOf(m.match_id) for m in matches] + leftover
        all_matches += matches
    return pool, all_matches


def _pair_round(
    sources: list[Source], round_number: int, round_name: str, id_prefix: str
) -> tuple[list[Source], list[MatchDef]]:
    """Pair up consecutive `sources` into one clean (bye-free) winners-bracket
    round — shared by rounds 2, 3, and the final, which only ever differ in
    round number/name and id prefix."""
    matches = [
        MatchDef(f"{id_prefix}-{i}", "W", round_number, round_name, a, b)
        for i, (a, b) in enumerate(zip(sources[0::2], sources[1::2]), start=1)
    ]
    return [WinnerOf(m.match_id) for m in matches], matches


def _merge_wave(
    existing: list[Source],
    incoming: list[Source],
    round_counter: list[int],
    final_round_name: str | None = None,
) -> tuple[list[Source], list[MatchDef]]:
    """Level ``existing`` (current LB survivors) and ``incoming`` (a fresh
    wave of winners-bracket droppers) to the same size via ``_reduce_to``,
    then pair them 1:1."""
    matches: list[MatchDef] = []
    if len(existing) > len(incoming):
        existing, ms = _reduce_to(existing, len(incoming), round_counter)
        matches += ms
    elif len(incoming) > len(existing):
        incoming, ms = _reduce_to(incoming, len(existing), round_counter)
        matches += ms
    round_counter[0] += 1
    rnum = round_counter[0]
    name = final_round_name or f"Losers Round {rnum}"
    merge_matches = [
        MatchDef(f"LB{rnum}-{i + 1}", "L", rnum, name, a, b)
        for i, (a, b) in enumerate(zip(existing, incoming))
    ]
    matches += merge_matches
    return [WinnerOf(m.match_id) for m in merge_matches], matches


@lru_cache(maxsize=8)
def build_topology(num_players: int) -> Topology:
    """Build the full WB/LB/GF match topology for a fixed 16-slot bracket
    with ``num_players`` real entrants (9-16); the rest bye through round 1.
    """
    if not (MIN_PLAYERS <= num_players <= MAX_PLAYERS):
        raise ValueError(
            f"num_players must be between {MIN_PLAYERS} and {MAX_PLAYERS}, "
            f"got {num_players}"
        )

    matches: list[MatchDef] = []
    bye_seeds: list[int] = []

    # Winners bracket round 1: byes go to whichever seed's seed_order(16)
    # partner exceeds num_players (always the *lower* of the pair, since
    # seed_order always orders each pair low-then-high and the low half of
    # any pair is always <= 8 <= MIN_PLAYERS <= num_players).
    pairs = list(zip(_SEED_ORDER_16[0::2], _SEED_ORDER_16[1::2]))
    round1_sources: list[Source] = []
    wb1_ids: list[str] = []
    for x, y in pairs:
        if y > num_players:
            bye_seeds.append(x)
            round1_sources.append(Seed(x))
        else:
            match_id = f"WB1-{len(wb1_ids) + 1}"
            matches.append(
                MatchDef(match_id, "W", 1, "Winners Round 1", Seed(x), Seed(y))
            )
            wb1_ids.append(match_id)
            round1_sources.append(WinnerOf(match_id))

    # Winners bracket round 2 (always a clean 8 -> 4, no more byes ever),
    # semifinals (4 -> 2), and final (2 -> 1) — three rounds of the same
    # bye-free pairing, just with a different round number/name/id prefix.
    round2_sources, wb2_matches = _pair_round(
        round1_sources, 2, "Winners Round 2", "WB2"
    )
    matches += wb2_matches
    round3_sources, wb3_matches = _pair_round(
        round2_sources, 3, "Winners Semifinal", "WB3"
    )
    matches += wb3_matches
    _, wb4_matches = _pair_round(round3_sources, 4, "Winners Final", "WB4")
    matches += wb4_matches
    wb_final_id = wb4_matches[0].match_id

    # Losers bracket: process each winners-bracket round's droppers as a wave.
    d1: list[Source] = [LoserOf(mid) for mid in wb1_ids]
    d2: list[Source] = [LoserOf(m.match_id) for m in wb2_matches]
    d3: list[Source] = [LoserOf(m.match_id) for m in wb3_matches]
    d4: list[Source] = [LoserOf(wb_final_id)]

    round_counter = [0]
    # Wave 1 is `_reduce_to`'s single-round case (target = ceil(len/2)): pure
    # self-pairing with no incoming wave to level against yet.
    survivors, m1 = _reduce_to(d1, -(-len(d1) // 2), round_counter)
    matches += m1
    survivors, m2 = _merge_wave(survivors, d2, round_counter)
    matches += m2
    survivors, m3 = _merge_wave(survivors, d3, round_counter)
    matches += m3
    survivors, m4 = _merge_wave(
        survivors, d4, round_counter, final_round_name="Losers Final"
    )
    matches += m4
    # The final merge_wave always reduces to exactly one survivor: the
    # losers-bracket champion.
    lb_champion_source = survivors[0]

    # Grand final; GF-2 (bracket reset) only applies if the losers-bracket
    # entrant (slot_b) wins GF-1.
    matches.append(
        MatchDef(
            "GF-1", "GF", 1, "Grand Final", WinnerOf(wb_final_id), lb_champion_source
        )
    )
    matches.append(
        MatchDef(
            "GF-2",
            "GF",
            2,
            "Grand Final Reset",
            WinnerOf(wb_final_id),
            lb_champion_source,
        )
    )

    return Topology(matches=matches, bye_seeds=bye_seeds)


def is_valid_match_id(match_id: str, num_players: int) -> bool:
    return any(m.match_id == match_id for m in build_topology(num_players).matches)


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
    source_a: Source = field(repr=False)
    source_b: Source = field(repr=False)


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


def rerouted_scored_matches(
    before: BracketResult,
    after: BracketResult,
    states: dict[str, MatchState],
    edited_match_id: str,
) -> list[str]:
    """Match ids whose resolved players differ between ``before`` and ``after``
    while they already have a recorded score in ``states``.

    Editing an upstream result re-routes players through the bracket; any
    downstream match with a stored score would silently attribute that score
    to the new players. Callers should reject an edit that returns a non-empty
    list. The edited match itself is exempt (its own players don't move).
    """
    before_by_id = {m.match_id: m for m in before.matches}
    conflicts: list[str] = []
    for m_after in after.matches:
        if m_after.match_id == edited_match_id:
            continue
        state = states.get(m_after.match_id)
        if state is None or state.score_a is None or state.score_b is None:
            continue
        m_before = before_by_id[m_after.match_id]
        if (m_before.player_a, m_before.player_b) != (
            m_after.player_a,
            m_after.player_b,
        ):
            conflicts.append(m_after.match_id)
    return conflicts


def resolve_bracket(
    seed_to_name: dict[int, str],
    match_states: dict[str, MatchState],
) -> BracketResult:
    """Build the topology for this player count and derive every match's
    players/winner/status.

    ``match_states`` holds only what's persisted (best_of + scores) per match
    id; everything else — who plays whom, whether a match is playable yet,
    who the champion is — is derived fresh each call.
    """
    topology = build_topology(len(seed_to_name))
    winners: dict[str, str] = {}
    losers: dict[str, str] = {}
    resolved: dict[str, ResolvedMatch] = {}

    def resolve_source(src: Source) -> str | None:
        if isinstance(src, Seed):
            return seed_to_name.get(src.seed)
        if isinstance(src, WinnerOf):
            return winners.get(src.match_id)
        return losers.get(src.match_id)

    for m in topology.matches:
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
                    source_a=m.slot_a,
                    source_b=m.slot_b,
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
            source_a=m.slot_a,
            source_b=m.slot_b,
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

    bye_advances = [
        (s, seed_to_name[s]) for s in topology.bye_seeds if s in seed_to_name
    ]

    return BracketResult(
        matches=list(resolved.values()),
        bye_advances=bye_advances,
        champion=champion,
        runner_up=runner_up,
        needs_reset=needs_reset,
    )
