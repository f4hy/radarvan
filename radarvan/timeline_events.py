"""Per-player timeline markers for the match-details Event Chart.

Aggregates upgrades, rank ups, generals powers, superweapon builds and
activations, search & destroy activations, low-power transitions, player
eliminations, tech-building captures, and first-radar acquisitions into a
single chronological `list[TimelineEvent]`.
"""

from __future__ import annotations

from .api_types import TimelineEvent, Upgrades
from .cncstats_model.zhreplay import EnhancedReplayV2
from .replay_helpers import (
    FACTION_PREFIX_RE,
    clean_object_name,
    is_initial_seed_frame,
)
from .utils import minutess_per_step

# Substrings on the cleaned object name that identify a true superweapon
# structure (one of the three big base-bound powers).
_SUPERWEAPON_STRUCTURES = (
    "NuclearMissileLauncher",
    "ParticleCannonUplink",
    "ScudStorm",
)

# Substrings inside SpecialPower order names that mark a *base* superweapon
# launch (as opposed to a generals-panel power that the engine also tags
# "Superweapon*").
_SUPERWEAPON_ACTIVATION_KEYWORDS = (
    "NeutronMissile",
    "NuclearMissile",
    "ParticleCannon",
    "ScudStorm",
    "EMPPulse",
    "AnthraxBomb",
    "SpectreGunship",
)

_POWER_NAME_PREFIXES = ("SpecialAbility", "SpecialPower", "Superweapon")


def _clean_power_name(raw: str) -> str:
    """Strip per-general/faction prefixes and the SpecialPower/Superweapon tag.

    The faction strip runs twice: once in `clean_object_name` to handle a
    leading `China`/`America`/`GLA`, and again after the power-tag strip in
    case removing it exposes a faction prefix (e.g.
    ``Early_SuperweaponChinaCarpetBomb`` → ``ChinaCarpetBomb`` → ``CarpetBomb``).
    """
    cleaned = clean_object_name(raw)
    for prefix in _POWER_NAME_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    return FACTION_PREFIX_RE.sub("", cleaned)


def timeline_events_from_replay(
    replay: EnhancedReplayV2,
    upgrades_by_player: dict[str, Upgrades],
    name_by_idx: dict[int, str],
) -> list[TimelineEvent]:
    """Per-player markers for the timeline chart."""
    scale = minutess_per_step(replay)
    events: list[TimelineEvent] = []

    for player_name, ups in upgrades_by_player.items():
        for u in ups.upgrades:
            events.append(
                TimelineEvent(
                    player_name=player_name,
                    at_minute=u.at_minute,
                    event_name=clean_object_name(u.upgrade_name),
                    event_type="upgrade",
                    cost=u.cost,
                )
            )

    for chunk in replay.body:
        if chunk.order_name not in ("SpecialPowerAtLocation", "SpecialPowerAtObject"):
            continue
        details = chunk.details if isinstance(chunk.details, dict) else {}
        raw_name = details.get("Name") or details.get("name") or ""
        if not raw_name or raw_name.startswith("SpecialAbility"):
            # Unit abilities (capture-building, laser-guided missiles, etc.)
            # would flood the timeline; we only want generals powers and
            # superweapons here.
            continue
        if any(kw in raw_name for kw in _SUPERWEAPON_ACTIVATION_KEYWORDS):
            event_type = "superweapon_activated"
        else:
            event_type = "generals_power"
        events.append(
            TimelineEvent(
                player_name=chunk.player_name,
                at_minute=chunk.time_code * scale,
                event_name=_clean_power_name(raw_name) or raw_name,
                event_type=event_type,
                cost=0,
            )
        )

    if replay.stats is not None:
        seen_rank: set[tuple[str, int]] = set()
        for rev in sorted(replay.stats.rank_events, key=lambda e: e.frame):
            if rev.rank_level <= 1 or is_initial_seed_frame(rev.frame):
                continue
            name = name_by_idx.get(rev.player)
            if name is None:
                continue
            key = (name, rev.rank_level)
            if key in seen_rank:
                continue
            seen_rank.add(key)
            events.append(
                TimelineEvent(
                    player_name=name,
                    at_minute=rev.frame * scale,
                    event_name=f"Rank {rev.rank_level}",
                    event_type="rank_up",
                    cost=0,
                )
            )

        for bev in replay.stats.build_events:
            cleaned = clean_object_name(bev.object)
            if not any(sw in cleaned for sw in _SUPERWEAPON_STRUCTURES):
                continue
            name = name_by_idx.get(bev.player)
            if name is None:
                continue
            events.append(
                TimelineEvent(
                    player_name=name,
                    at_minute=bev.frame * scale,
                    event_name=cleaned,
                    event_type="superweapon_built",
                    cost=bev.cost,
                )
            )

        # Search & Destroy battle-plan activations: emit on every 0 → 1 flip.
        prev_sd: dict[int, int] = {}
        for bpev in sorted(replay.stats.battle_plan_events, key=lambda e: e.frame):
            prev = prev_sd.get(bpev.player, 0)
            prev_sd[bpev.player] = bpev.search_and_destroy
            if bpev.search_and_destroy <= 0 or prev > 0:
                continue
            name = name_by_idx.get(bpev.player)
            if name is None:
                continue
            events.append(
                TimelineEvent(
                    player_name=name,
                    at_minute=bpev.frame * scale,
                    event_name="Search and Destroy",
                    event_type="search_and_destroy",
                    cost=0,
                )
            )

        # Low-power transitions: emit when consumption first exceeds production.
        was_low: dict[int, bool] = {}
        for eev in sorted(replay.stats.energy_events, key=lambda e: e.frame):
            is_low_now = eev.consumption > eev.production
            prev_low = was_low.get(eev.player, False)
            was_low[eev.player] = is_low_now
            if not is_low_now or prev_low:
                continue
            name = name_by_idx.get(eev.player)
            if name is None:
                continue
            events.append(
                TimelineEvent(
                    player_name=name,
                    at_minute=eev.frame * scale,
                    event_name=f"Low Power ({eev.consumption} > {eev.production})",
                    event_type="low_power",
                    cost=0,
                )
            )

        # Player eliminations.
        for dev in replay.stats.death_events:
            if is_initial_seed_frame(dev.frame):
                continue
            name = name_by_idx.get(dev.player)
            if name is None:
                continue
            events.append(
                TimelineEvent(
                    player_name=name,
                    at_minute=dev.frame * scale,
                    event_name="Eliminated",
                    event_type="player_eliminated",
                    cost=0,
                )
            )

        # Tech-building captures (oil derricks, hospitals, comm centers, etc.).
        # Filtered to objects with a Tech prefix to skip the noisy unit
        # hijacks / base-building captures that share the same event stream.
        for cev in replay.stats.capture_events:
            if cev.new_owner <= 0 or not cev.object.startswith("Tech"):
                continue
            name = name_by_idx.get(cev.new_owner)
            if name is None:
                continue
            events.append(
                TimelineEvent(
                    player_name=name,
                    at_minute=cev.frame * scale,
                    event_name=cev.object.removeprefix("Tech"),
                    event_type="tech_capture",
                    cost=0,
                )
            )

        # First-radar-acquired per player; skip the frame-0 seed and any
        # repeat acquisitions (radar can flicker on/off with power).
        seen_radar: set[str] = set()
        for radev in sorted(replay.stats.radar_events, key=lambda e: e.frame):
            if is_initial_seed_frame(radev.frame) or not radev.has_radar:
                continue
            name = name_by_idx.get(radev.player)
            if name is None or name in seen_radar:
                continue
            seen_radar.add(name)
            events.append(
                TimelineEvent(
                    player_name=name,
                    at_minute=radev.frame * scale,
                    event_name="First Radar",
                    event_type="first_radar",
                    cost=0,
                )
            )

    events.sort(key=lambda e: (e.at_minute, e.player_name))
    return events
