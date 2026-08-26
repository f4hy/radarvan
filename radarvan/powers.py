"""Per-match generals-power picks and activations.

A projection of data already parsed, in the same spirit as `match_narrative`
and `durations`: nothing here reads the database or S3, and adding a field
costs no new derivation.

Two independent sources, because they fail independently:

- **Picks** come from the body's ``PurchaseScience`` orders, and are stored as
  the raw science id - `generals_powers` names them at read time, so the table
  can improve without invalidating a single cached match. Replays whose body
  stream cncstats dropped have no picks at all (`apm` has the same split).
- **Activations** come from ``summary[*].powersUsed``, which cncstats counts
  itself and which survives an empty body. The body is only consulted for the
  *first* activation's minute, so a body-less replay still gets counts.

Unit abilities (Ranger capture-building, laser-guided missiles, Colonel
Burton's charges) are excluded: they are a unit's button, not a generals point
spent, and they outnumber real power activations several to one.
"""

from __future__ import annotations

from collections import defaultdict

from .api_types import MatchPowers, PlayerPowers, PowerPick, PowerUse
from .cncstats_model.zhreplay import EnhancedReplayV2
from .game_composition import MatchRoster
from .player_ids import resolve_player_name
from .generals_powers import general_of, pretty_power_name
from .replay_helpers import is_initial_seed_frame
from .utils import duration_minutes, minutes_per_step

_POWER_ORDERS = ("SpecialPowerAtLocation", "SpecialPowerAtObject", "SpecialPower")


def is_generals_power(raw_name: str) -> bool:
    """True for a generals-panel power or superweapon, false for a unit ability.

    The general-specific spellings carry a prefix (``Demo_SpecialAbility...``),
    so the test has to run after that prefix is stripped rather than on the raw
    name - checking ``startswith("SpecialAbility")`` directly lets every
    prefixed unit ability through.
    """
    if not raw_name:
        return False
    tail = raw_name.split("_", 1)[1] if "_" in raw_name else raw_name
    return not tail.startswith("SpecialAbility")


def powers_from_replay(replay: EnhancedReplayV2) -> MatchPowers:
    """Picks and activations for every human who played."""
    scale = minutes_per_step(replay)
    roster = MatchRoster.from_header_players(replay.header.metadata.players)
    # `.humans`, not `.human_participants`: an FFA leaves every slot on team 0,
    # so the participants partition is empty there by design and the page would
    # silently lose every free-for-all. Powers are a per-player property, not a
    # team one. Observers and AI are still excluded - they aren't `.humans`.
    played = {slot.name: slot for slot in roster.humans}

    picks: dict[str, list[PowerPick]] = defaultdict(list)
    # A science can only be bought once, but the order stream can carry the
    # same purchase several times (the engine re-sends, and a player clicking
    # an already-bought button still emits the order). Counting those would
    # report someone taking Artillery Barrage three times.
    bought: dict[str, set[int]] = defaultdict(set)
    first_use: dict[str, dict[str, float]] = defaultdict(dict)

    for chunk in replay.body:
        if chunk.player_name not in played:
            continue
        if chunk.order_name == "PurchaseScience":
            if not chunk.arguments:
                continue
            science_id = chunk.arguments[0]
            if not isinstance(science_id, int):
                continue
            if science_id in bought[chunk.player_name]:
                continue
            bought[chunk.player_name].add(science_id)
            picks[chunk.player_name].append(
                PowerPick(at_minute=chunk.time_code * scale, science_id=science_id)
            )
        elif chunk.order_name in _POWER_ORDERS:
            details = chunk.details if isinstance(chunk.details, dict) else {}
            raw_name = details.get("Name") or details.get("name") or ""
            if not is_generals_power(raw_name):
                continue
            name = pretty_power_name(raw_name)
            seen = first_use[chunk.player_name]
            at_minute = chunk.time_code * scale
            if name not in seen or at_minute < seen[name]:
                seen[name] = at_minute

    match_minutes = duration_minutes(replay)
    eliminated_at = _elimination_minutes(replay, scale)

    players: list[PlayerPowers] = []
    for summary in replay.summary:
        if summary.name not in played:
            continue
        uses = [
            PowerUse(
                name=pretty_power_name(raw_name),
                count=count,
                first_minute=first_use[summary.name].get(pretty_power_name(raw_name)),
            )
            for raw_name, count in sorted((summary.powers_used or {}).items())
            if is_generals_power(raw_name) and count > 0
        ]
        players.append(
            PlayerPowers(
                player_name=resolve_player_name(
                    summary.name, played[summary.name].color
                ),
                faction=summary.faction,
                general=general_of(summary.faction),
                minutes=eliminated_at.get(summary.name, match_minutes),
                picks=sorted(picks[summary.name], key=lambda p: p.at_minute),
                uses=_merged(uses),
            )
        )
    return MatchPowers(players=players)


def _merged(uses: list[PowerUse]) -> list[PowerUse]:
    """Collapse the per-general spellings of one power into a single row.

    ``SuperweaponSpectreGunship`` and ``AirF_SuperweaponSpectreGunship`` are the
    same power to a reader comparing two players, and `pretty_power_name` maps
    both to "Spectre Gunship" - so two entries can land on one name.
    """
    by_name: dict[str, PowerUse] = {}
    for use in uses:
        existing = by_name.get(use.name)
        if existing is None:
            by_name[use.name] = use
            continue
        firsts = [m for m in (existing.first_minute, use.first_minute) if m is not None]
        by_name[use.name] = PowerUse(
            name=use.name,
            count=existing.count + use.count,
            first_minute=min(firsts) if firsts else None,
        )
    return sorted(by_name.values(), key=lambda u: (-u.count, u.name))


def _elimination_minutes(replay: EnhancedReplayV2, scale: float) -> dict[str, float]:
    """Minute each player was eliminated, for those who were.

    The denominator for a per-minute rate: someone knocked out at four minutes
    of a twenty-five minute game did not have twenty-five minutes of chances to
    fire a power, and averaging over the match length would rank them as
    passive when they were simply dead.
    """
    if replay.stats is None:
        return {}
    name_by_idx = {p.index: p.name for p in replay.summary}
    out: dict[str, float] = {}
    for death in replay.stats.death_events:
        if is_initial_seed_frame(death.frame):
            continue
        name = name_by_idx.get(death.player)
        if name is None:
            continue
        at_minute = death.frame * scale
        if name not in out or at_minute < out[name]:
            out[name] = at_minute
    return out
