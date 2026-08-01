"""Purpose-built, pre-trimmed data for LLM-generated matchup commentary.

Built from ``PlayerProfile`` / ``HeadToHeadDetail`` but reduced to only the
fields ``commentary_prompts.GUIDELINES`` actually references, with generals
rendered by name (``STEALTH``) rather than the wire IntEnum index (``10``) -
an LLM reads names naturally and shouldn't have to hold the id-to-name table
in its head while writing.

Deliberately **not** rendered as JSON. ``render_player_data`` /
``render_head_to_head`` produce plain labeled text instead - JSON's
punctuation overhead (braces, quotes, commas) buys nothing here since
nothing downstream re-parses this content; it's read once, by the model,
and never round-tripped back through a JSON parser.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..api_types import (
    FavoriteObject,
    GeneralProfileStat,
    HeadToHeadDetail,
    HeadToHeadGeneralRecord,
    OpponentProfileStat,
    PlayerProfile,
    ProfileBadge,
    TeammateProfileStat,
)

_SLOTS = ConfigDict(slots=True)  # type: ignore[typeddict-unknown-key]

# "Last N matches" for the head-to-head recency data - just enough to spot a
# real 1v1 session and check the last-30-days window (guidelines caveat #5),
# not the complete history. Games are already sorted most-recent-first (see
# head_to_head.compute_head_to_head).
MAX_RECENT_MATCHES = 10


class HypeGeneralRecord(BaseModel):
    model_config = _SLOTS

    general: str
    games: int
    wins: int
    win_rate: float


class HypePlayerData(BaseModel):
    """Everything the hype-commentary guidelines use from one player's
    profile - see ``build_hype_player_data``."""

    model_config = _SLOTS

    player: str
    generals: list[HypeGeneralRecord]
    favorite_teammate: TeammateProfileStat | None
    nemesis: OpponentProfileStat | None
    avg_win_duration_minutes: float | None
    avg_loss_duration_minutes: float | None
    favorite_unit: FavoriteObject | None
    favorite_building: FavoriteObject | None
    favorite_upgrade: FavoriteObject | None
    favorite_power: FavoriteObject | None
    aversions: list[FavoriteObject]
    badges: list[ProfileBadge]


class HypeHeadToHeadGeneralRecord(BaseModel):
    model_config = _SLOTS

    general: str
    wins: int
    losses: int


class HypeMatchOutcome(BaseModel):
    model_config = _SLOTS

    date: str
    winner: str


class HypeHeadToHead(BaseModel):
    """Trimmed head-to-head payload - see ``build_hype_head_to_head``. Used
    for both the 1v1-only and unfiltered-all-formats pulls."""

    model_config = _SLOTS

    player1: str
    player2: str
    player1_wins: int
    player2_wins: int
    player1_by_general: list[HypeHeadToHeadGeneralRecord]
    player2_by_general: list[HypeHeadToHeadGeneralRecord]
    teammate_games: int
    teammate_wins: int
    recent_matches: list[HypeMatchOutcome]


def _hype_generals(generals: list[GeneralProfileStat]) -> list[HypeGeneralRecord]:
    return [
        HypeGeneralRecord(
            general=g.general.name, games=g.games, wins=g.wins, win_rate=g.win_rate
        )
        for g in generals
    ]


def build_hype_player_data(profile: PlayerProfile) -> HypePlayerData:
    computed = profile.computed
    return HypePlayerData(
        player=profile.player,
        generals=_hype_generals(profile.generals),
        favorite_teammate=profile.favorite_teammate,
        nemesis=profile.nemesis,
        avg_win_duration_minutes=profile.avg_win_duration_minutes,
        avg_loss_duration_minutes=profile.avg_loss_duration_minutes,
        favorite_unit=computed.favorite_unit if computed else None,
        favorite_building=computed.favorite_building if computed else None,
        favorite_upgrade=computed.favorite_upgrade if computed else None,
        favorite_power=computed.favorite_power if computed else None,
        aversions=computed.aversions if computed else [],
        badges=computed.badges if computed else [],
    )


def _hype_h2h_generals(
    records: list[HeadToHeadGeneralRecord],
) -> list[HypeHeadToHeadGeneralRecord]:
    return [
        HypeHeadToHeadGeneralRecord(
            general=r.general.name, wins=r.wins, losses=r.losses
        )
        for r in records
    ]


def build_hype_head_to_head(h2h: HeadToHeadDetail) -> HypeHeadToHead:
    recent = h2h.games[:MAX_RECENT_MATCHES]
    return HypeHeadToHead(
        player1=h2h.player1,
        player2=h2h.player2,
        player1_wins=h2h.player1_wins,
        player2_wins=h2h.player2_wins,
        player1_by_general=_hype_h2h_generals(h2h.player1_by_general),
        player2_by_general=_hype_h2h_generals(h2h.player2_by_general),
        teammate_games=h2h.teammate_games,
        teammate_wins=h2h.teammate_wins,
        recent_matches=[
            HypeMatchOutcome(
                date=g.date.isoformat(),
                winner=h2h.player1 if g.player1_won else h2h.player2,
            )
            for g in recent
        ],
    )


def _render_favorite(label: str, obj: FavoriteObject | None) -> str | None:
    if obj is None:
        return None
    return (
        f"{label}: {obj.name} ({obj.general.name}) - {obj.per_game:.2f}/game vs "
        f"peer {obj.peer_per_game:.2f}/game (score {obj.score:.2f})"
    )


def render_player_data(data: HypePlayerData) -> str:
    """Plain labeled text for one player - see the module docstring for why
    this isn't JSON."""
    lines = [f"Player: {data.player}", "", "Per-general record:"]
    lines.extend(
        f"- {g.general}: {g.games} games, {g.wins} wins ({g.win_rate:.1%})"
        for g in data.generals
    )

    lines.append("")
    if data.favorite_teammate is not None:
        t = data.favorite_teammate
        synergy = f", synergy {t.synergy:.2f}" if t.synergy is not None else ""
        lines.append(
            f"Favorite teammate: {t.name} ({t.games_together} games together, "
            f"{t.wins_together} wins{synergy})"
        )
    if data.nemesis is not None:
        n = data.nemesis
        lines.append(f"Nemesis: {n.name} ({n.wins} wins, {n.losses} losses)")
    if (
        data.avg_win_duration_minutes is not None
        or data.avg_loss_duration_minutes is not None
    ):
        win_d = (
            f"{data.avg_win_duration_minutes:.1f} min"
            if data.avg_win_duration_minutes is not None
            else "n/a"
        )
        loss_d = (
            f"{data.avg_loss_duration_minutes:.1f} min"
            if data.avg_loss_duration_minutes is not None
            else "n/a"
        )
        lines.append(f"Avg win duration: {win_d} | Avg loss duration: {loss_d}")

    lines.append("")
    for label, obj in (
        ("Favorite unit", data.favorite_unit),
        ("Favorite building", data.favorite_building),
        ("Favorite upgrade", data.favorite_upgrade),
        ("Favorite power", data.favorite_power),
    ):
        rendered = _render_favorite(label, obj)
        if rendered is not None:
            lines.append(rendered)

    if data.aversions:
        lines.append("")
        lines.append("Aversions (do not use, see guidelines):")
        lines.extend(
            f"- {a.name} ({a.general.name}) - score {a.score:.2f}"
            for a in data.aversions
        )

    if data.badges:
        lines.append("")
        lines.append("Badges:")
        lines.extend(
            f"- [{b.tier}] {b.label} (rank {b.rank} of {b.total_players}): "
            f"{b.description} (value {b.value})"
            for b in data.badges
        )

    return "\n".join(lines)


def render_head_to_head(h2h: HypeHeadToHead) -> str:
    """Plain labeled text for a head-to-head pull - see the module
    docstring for why this isn't JSON."""
    lines = [
        f"{h2h.player1} vs {h2h.player2}",
        f"Overall record: {h2h.player1} {h2h.player1_wins} - {h2h.player2_wins} {h2h.player2}",
        f"Teammate games together: {h2h.teammate_games} ({h2h.teammate_wins} {h2h.player1}/"
        f"{h2h.player2} wins combined)",
        "",
    ]

    lines.append(
        f"{h2h.player1}'s record by general (in these games against {h2h.player2}):"
    )
    if h2h.player1_by_general:
        lines.extend(
            f"- {g.general}: {g.wins} wins, {g.losses} losses"
            for g in h2h.player1_by_general
        )
    else:
        lines.append("- no games on record")

    lines.append(
        f"{h2h.player2}'s record by general (in these games against {h2h.player1}):"
    )
    if h2h.player2_by_general:
        lines.extend(
            f"- {g.general}: {g.wins} wins, {g.losses} losses"
            for g in h2h.player2_by_general
        )
    else:
        lines.append("- no games on record")

    lines.append("")
    if h2h.recent_matches:
        lines.append(f"Last {len(h2h.recent_matches)} matches (most recent first):")
        lines.extend(f"- {m.date}: {m.winner} won" for m in h2h.recent_matches)
    else:
        lines.append("No matches on record.")

    return "\n".join(lines)
