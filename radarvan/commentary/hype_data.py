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
    BracketMatchOutput,
    BracketTournamentOutput,
    FavoriteObject,
    General,
    GeneralProfileStat,
    HeadToHeadDetail,
    HeadToHeadGeneralRecord,
    MatchInfo,
    OpponentProfileStat,
    PlayerProfile,
    PlayerRatings,
    ProfileBadge,
    TeammateProfileStat,
    UnitDamageStat,
)
from ..player_ids import resolve_player_name
from ..replay_files import map_basename

_SLOTS = ConfigDict(slots=True)  # type: ignore[typeddict-unknown-key]

# "Last N matches" for the head-to-head recency data - just enough to spot a
# real 1v1 session and check the last-30-days window (guidelines caveat #5),
# not the complete history. Games are already sorted most-recent-first (see
# head_to_head.compute_head_to_head).
MAX_RECENT_MATCHES = 10

# Below this, a peer-relative percentile stat isn't handed to the model at
# all - these percentiles have no meaningful "raw number only" form: an APM
# of 37 or a 11% first-blood rate says nothing without population context,
# and *with* that context a low value reads as "you're bad at this" in a way
# the guidelines' "never make an underdog feel bad" rule would forbid saying
# outright. So below-threshold stats are omitted entirely rather than
# reworded - the model only ever sees the flattering ones.
_MIN_NOTABLE_PERCENTILE = 75


class HypeGeneralRecord(BaseModel):
    model_config = _SLOTS

    general: str
    games: int
    wins: int
    win_rate: float


class HypeRatingEntry(BaseModel):
    model_config = _SLOTS

    player: str
    ordinal: float
    sigma: float


class HypeRatingsContext(BaseModel):
    """Team-game ordinal/sigma for the *whole* rated population, sorted
    best-to-worst - internal calibration context, not per-player narrative
    material (see ``build_hype_ratings_context`` / ``render_ratings_context``).

    Earlier iterations embedded just the two matchup players' own ordinals in
    their profile blocks. That still let the model quote a raw ordinal number
    in the output (meaningless/confusing to anyone reading the commentary -
    these are OpenSkill internals, never surfaced anywhere else in the app),
    and gave the model no sense of *scale*: is a 3-point gap huge or noise?
    Showing the full population with sigma (uncertainty) fixes both - the
    model can see where these two sit among everyone else and judge "close
    fight" vs "skill gap" without ever being handed the population rank
    (see the guideline against demoralizing an underdog with a raw ranking)
    or a number worth repeating verbatim.
    """

    model_config = _SLOTS

    player1: str
    player2: str
    entries: list[HypeRatingEntry]


class HypePlayerData(BaseModel):
    """Everything the hype-commentary guidelines use from one player's
    profile - see ``build_hype_player_data``."""

    model_config = _SLOTS

    player: str
    generals: list[HypeGeneralRecord]
    best_general: HypeGeneralRecord | None
    favorite_teammate: TeammateProfileStat | None
    nemesis: OpponentProfileStat | None
    avg_win_duration_minutes: float | None
    avg_loss_duration_minutes: float | None
    favorite_unit: FavoriteObject | None
    favorite_building: FavoriteObject | None
    favorite_upgrade: FavoriteObject | None
    favorite_power: FavoriteObject | None
    signature_damage_dealer: FavoriteObject | None
    top_damage_dealer: UnitDamageStat | None
    aversions: list[FavoriteObject]
    badges: list[ProfileBadge]
    # Wins/losses across this player's last (up to 10) rated team games,
    # oldest first (chronological) - same ordering as
    # routes.players.get_player_ratings' player_form. Plain W/L results, not
    # an internal rating number, so unlike HypeRatingsContext this is fine to
    # surface directly in the player's own block.
    recent_team_game_form: list[bool]
    avg_apm: float | None
    apm_percentile: float | None
    first_blood_rate: float | None
    first_blood_percentile: float | None
    avg_time_to_rank_5: float | None
    rank_5_percentile: float | None
    superweapons_built_per_game: float | None
    superweapon_percentile: float | None


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
    # Total value destroyed (build cost of everything killed - the
    # damage-dealt proxy) across all games between these two.
    player1_value_destroyed: int
    player2_value_destroyed: int
    recent_matches: list[HypeMatchOutcome]


def _hype_generals(generals: list[GeneralProfileStat]) -> list[HypeGeneralRecord]:
    return [
        HypeGeneralRecord(
            general=g.general.name, games=g.games, wins=g.wins, win_rate=g.win_rate
        )
        for g in generals
    ]


def build_hype_ratings_context(
    all_ratings: list[PlayerRatings], player1: str, player2: str
) -> HypeRatingsContext:
    """Whole rated population's ordinal/sigma, best-to-worst - see
    HypeRatingsContext's docstring for why this replaced per-player ordinals."""
    entries = sorted(
        (
            HypeRatingEntry(player=r.name, ordinal=r.ordinal, sigma=r.sigma)
            for r in all_ratings
        ),
        key=lambda e: e.ordinal,
        reverse=True,
    )
    return HypeRatingsContext(player1=player1, player2=player2, entries=entries)


def build_hype_player_data(
    profile: PlayerProfile, recent_team_game_form: list[bool] | None = None
) -> HypePlayerData:
    computed = profile.computed
    return HypePlayerData(
        player=profile.player,
        generals=_hype_generals(profile.generals),
        best_general=(
            _hype_generals([profile.best_general])[0] if profile.best_general else None
        ),
        favorite_teammate=profile.favorite_teammate,
        nemesis=profile.nemesis,
        avg_win_duration_minutes=profile.avg_win_duration_minutes,
        avg_loss_duration_minutes=profile.avg_loss_duration_minutes,
        favorite_unit=computed.favorite_unit if computed else None,
        favorite_building=computed.favorite_building if computed else None,
        favorite_upgrade=computed.favorite_upgrade if computed else None,
        favorite_power=computed.favorite_power if computed else None,
        signature_damage_dealer=computed.signature_damage_dealer if computed else None,
        top_damage_dealer=computed.top_damage_dealer if computed else None,
        aversions=computed.aversions if computed else [],
        badges=computed.badges if computed else [],
        recent_team_game_form=recent_team_game_form or [],
        avg_apm=computed.avg_apm if computed else None,
        apm_percentile=computed.apm_percentile if computed else None,
        first_blood_rate=computed.first_blood_rate if computed else None,
        first_blood_percentile=computed.first_blood_percentile if computed else None,
        avg_time_to_rank_5=computed.avg_time_to_rank_5 if computed else None,
        rank_5_percentile=computed.rank_5_percentile if computed else None,
        superweapons_built_per_game=(
            computed.superweapons_built_per_game if computed else None
        ),
        superweapon_percentile=computed.superweapon_percentile if computed else None,
    )


# --- Tournament-so-far context ---


class HypeTournamentGame(BaseModel):
    """One replay played inside the tournament, resolved to canonical names.

    ``winner_general == loser_general`` marks the mirror decider the rules
    call for when a set is level going into its last game - worth saying out
    loud, since a mirror is the one game where the draw gives neither player
    anything.
    """

    model_config = _SLOTS

    series_index: int | None
    map: str
    winner: str
    loser: str
    winner_general: str
    loser_general: str
    duration_minutes: float

    @property
    def is_mirror(self) -> bool:
        return self.winner_general == self.loser_general


class HypeReversePair(BaseModel):
    """The two games one draw produces under "random reverse for armies".

    The tournament randomizes the general matchup and then plays it twice
    with the players swapped, so a pair is the only place the data separates
    *player* from *draw*: taking both sides of the same matchup on the same
    map is a real result, while a 1-1 split says the draw decided those two
    games and neither player did. This is the one derived fact worth handing
    the model - it cannot reconstruct it from a flat game list without
    knowing the format.
    """

    model_config = _SLOTS

    map: str
    general_a: str
    general_b: str
    # None means the pair split 1-1.
    swept_by: str | None


class HypeTournamentSeries(BaseModel):
    """One bracket match (a best-of set) and whatever games it produced.

    ``games`` can be empty while ``score_a``/``score_b`` are set - an admin
    records the set result directly, and the replays only link once the
    detector has run (see ``tournament_membership.sync_links``).
    """

    model_config = _SLOTS

    stage: str
    round_name: str
    player_a: str
    player_b: str
    score_a: int | None
    score_b: int | None
    winner: str | None
    games: list[HypeTournamentGame]
    reverse_pairs: list[HypeReversePair]


class HypeTournamentRun(BaseModel):
    """One player's completed sets in this tournament, oldest first."""

    model_config = _SLOTS

    player: str
    series: list[HypeTournamentSeries]


class HypeTournamentContext(BaseModel):
    """What has already happened in the tournament these two are playing in.

    Sets where *both* of them played are pulled out into ``prior_meetings``
    rather than repeated in each run - a rematch is the single most
    interesting thing this block can surface, and duplicating it under both
    players buries that.
    """

    model_config = _SLOTS

    player1: str
    player2: str
    run1: HypeTournamentRun
    run2: HypeTournamentRun
    prior_meetings: list[HypeTournamentSeries]

    @property
    def is_empty(self) -> bool:
        return not (self.run1.series or self.run2.series or self.prior_meetings)


def tournament_game(match: MatchInfo) -> HypeTournamentGame | None:
    """One linked replay as a winner/loser pair, or None if it isn't one.

    Anything that isn't a clean two-human decided 1v1 is dropped rather than
    guessed at: a game with an unparsed general or no recorded winner would
    otherwise render as an authoritative-looking line the model would quote.
    """
    slots = [s for s in match.roster().human_participants if s.has_known_general]
    if len(slots) != 2:
        return None
    winners = [s for s in slots if s.won]
    losers = [s for s in slots if not s.won]
    if len(winners) != 1 or len(losers) != 1:
        return None
    won, lost = winners[0], losers[0]
    return HypeTournamentGame(
        series_index=match.tournament.series_index if match.tournament else None,
        map=map_basename(match.map),
        winner=resolve_player_name(won.name, won.color),
        loser=resolve_player_name(lost.name, lost.color),
        winner_general=General(won.general).name,
        loser_general=General(lost.general).name,
        duration_minutes=match.duration_minutes,
    )


def reverse_pairs(games: list[HypeTournamentGame]) -> list[HypeReversePair]:
    """Group a set's games into the reversed pairs the format produces.

    Two games pair up when they share a map and both players swapped
    generals between them. Mirrors are excluded - both players on one general
    cannot be "reversed", and the decider is already visible per-game.
    Anything that doesn't pair cleanly (an odd game, a map played more than
    twice) is simply left out; the flat game list still carries it.
    """
    by_draw: dict[tuple[str, frozenset[str]], list[HypeTournamentGame]] = {}
    order: list[tuple[str, frozenset[str]]] = []
    for game in games:
        if game.is_mirror:
            continue
        key = (game.map, frozenset({game.winner_general, game.loser_general}))
        if key not in by_draw:
            by_draw[key] = []
            order.append(key)
        by_draw[key].append(game)

    pairs = []
    for key in order:
        group = by_draw[key]
        if len(group) != 2:
            continue
        first, second = group
        generals_first = {
            first.winner: first.winner_general,
            first.loser: first.loser_general,
        }
        generals_second = {
            second.winner: second.winner_general,
            second.loser: second.loser_general,
        }
        if set(generals_first) != set(generals_second):
            continue
        if any(generals_first[p] == generals_second[p] for p in generals_first):
            # Same player kept the same general - the sides never reversed, so
            # this is two games of one draw, not a reversed pair.
            continue
        general_a, general_b = sorted(key[1])
        pairs.append(
            HypeReversePair(
                map=key[0],
                general_a=general_a,
                general_b=general_b,
                swept_by=first.winner if first.winner == second.winner else None,
            )
        )
    return pairs


def _series_for(
    match: BracketMatchOutput, games_by_stage: dict[str, list[MatchInfo]]
) -> HypeTournamentSeries | None:
    """A completed bracket match as a series, or None if it isn't usable.

    Only completed sets with both players known are kept: an unplayed or
    in-progress set has nothing to say about form, and a redacted
    (pre-reveal) bracket has no names to say it about.
    """
    if match.status != "completed" or match.winner is None:
        return None
    if match.player_a is None or match.player_b is None:
        return None
    games = [
        game
        for game in (
            tournament_game(m)
            for m in sorted(
                games_by_stage.get(match.match_id, []), key=lambda m: m.timestamp
            )
        )
        if game is not None
    ]
    return HypeTournamentSeries(
        stage=match.match_id,
        round_name=match.round_name,
        player_a=match.player_a,
        player_b=match.player_b,
        score_a=match.score_a,
        score_b=match.score_b,
        winner=match.winner,
        games=games,
        reverse_pairs=reverse_pairs(games),
    )


def build_hype_tournament_context(
    bracket_output: BracketTournamentOutput | None,
    tournament_games: list[MatchInfo],
    player1: str,
    player2: str,
) -> HypeTournamentContext:
    """Both players' tournament so far, from the resolved bracket + linked games.

    ``bracket_output`` is whatever ``routes.bracket.get_bracket`` returned, so
    a redacted pre-reveal bracket (player names nulled out) yields an empty
    context rather than leaking placements into generated text.
    """
    empty1 = HypeTournamentRun(player=player1, series=[])
    empty2 = HypeTournamentRun(player=player2, series=[])
    if bracket_output is None or not bracket_output.revealed:
        return HypeTournamentContext(
            player1=player1,
            player2=player2,
            run1=empty1,
            run2=empty2,
            prior_meetings=[],
        )

    games_by_stage: dict[str, list[MatchInfo]] = {}
    for match in tournament_games:
        stage = match.tournament.stage if match.tournament else None
        if stage is not None:
            games_by_stage.setdefault(stage, []).append(match)

    # Bracket order is already the order they were played in closely enough
    # for a narrative (round 1 before round 2); scheduled_at is not, since an
    # admin can schedule a later round earlier in wall-clock time.
    series = [
        s
        for s in (_series_for(m, games_by_stage) for m in bracket_output.matches)
        if s is not None
    ]

    def runs_for(player: str) -> list[HypeTournamentSeries]:
        return [
            s
            for s in series
            if player in (s.player_a, s.player_b)
            and {s.player_a, s.player_b} != {player1, player2}
        ]

    return HypeTournamentContext(
        player1=player1,
        player2=player2,
        run1=HypeTournamentRun(player=player1, series=runs_for(player1)),
        run2=HypeTournamentRun(player=player2, series=runs_for(player2)),
        prior_meetings=[
            s for s in series if {s.player_a, s.player_b} == {player1, player2}
        ],
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
        player1_value_destroyed=h2h.player1_value_destroyed,
        player2_value_destroyed=h2h.player2_value_destroyed,
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


def _render_top_damage_dealer(stat: UnitDamageStat | None) -> str | None:
    if stat is None:
        return None
    return (
        f"Top damage dealer (own best, not peer-compared): {stat.name} "
        f"({stat.general.name}) - {stat.per_game:.0f} value destroyed/game "
        f"({stat.kill_count} kills across {stat.games_on_general} games on general)"
    )


def _render_recent_form(recent_form: list[bool]) -> list[str]:
    if not recent_form:
        return []
    form = "-".join("W" if won else "L" for won in recent_form)
    return [f"Recent team-game form (oldest to most recent): {form}"]


def render_ratings_context(ctx: HypeRatingsContext) -> str:
    """Plain labeled text for the whole-population rating block - see
    HypeRatingsContext's docstring. The instruction not to quote these
    numbers lives here *and* in commentary_prompts.GUIDELINES (defense in
    depth: this text sits right next to the numbers, the guidelines catch it
    even if this block gets skimmed)."""
    lines = [
        "Team-game skill ratings (OpenSkill ordinal +/- sigma uncertainty) "
        "for every rated player, best to worst. INTERNAL CALIBRATION ONLY: "
        "these numbers are never shown to users anywhere in the app - do not "
        "state them, or any derived ranking/position, in the generated "
        "commentary. Use this purely to gauge, in your own judgment, whether "
        f"{ctx.player1} and {ctx.player2} (marked below) look closely matched "
        "or far apart in skill, then express that as hype language, not numbers.",
        "",
    ]
    for e in ctx.entries:
        marker = ""
        if e.player == ctx.player1:
            marker = f"  <- {ctx.player1} (this matchup)"
        elif e.player == ctx.player2:
            marker = f"  <- {ctx.player2} (this matchup)"
        lines.append(f"- {e.player}: {e.ordinal:.1f} +/- {e.sigma:.1f}{marker}")
    return "\n".join(lines)


def render_player_data(data: HypePlayerData) -> str:
    """Plain labeled text for one player - see the module docstring for why
    this isn't JSON."""
    lines = [f"Player: {data.player}", "", "Per-general record:"]
    lines.extend(
        f"- {g.general}: {g.games} games, {g.wins} wins ({g.win_rate:.1%})"
        for g in data.generals
    )
    if data.best_general is not None:
        bg = data.best_general
        lines.append(
            f"Best general (highest win rate): {bg.general} ({bg.games} games, "
            f"{bg.win_rate:.1%})"
        )

    lines.append("")
    lines.extend(_render_recent_form(data.recent_team_game_form))

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
        ("Signature damage dealer (peer-compared)", data.signature_damage_dealer),
    ):
        rendered = _render_favorite(label, obj)
        if rendered is not None:
            lines.append(rendered)
    top_damage = _render_top_damage_dealer(data.top_damage_dealer)
    if top_damage is not None:
        lines.append(top_damage)

    # *_percentile fields are already on a 0-100 scale (100 = best in the
    # population), not a 0-1 fraction - see player_profile._percentile. Only
    # top-quartile (>= _MIN_NOTABLE_PERCENTILE) stats are shown - see that
    # constant's comment for why below-threshold ones are dropped entirely
    # rather than shown without the percentile context.
    percentile_lines = []
    if (
        data.avg_apm is not None
        and data.apm_percentile is not None
        and data.apm_percentile >= _MIN_NOTABLE_PERCENTILE
    ):
        percentile_lines.append(
            f"APM: {data.avg_apm:.0f} avg ({data.apm_percentile:.0f}th percentile)"
        )
    if (
        data.first_blood_rate is not None
        and data.first_blood_percentile is not None
        and data.first_blood_percentile >= _MIN_NOTABLE_PERCENTILE
    ):
        percentile_lines.append(
            f"First blood rate: {data.first_blood_rate:.0%} "
            f"({data.first_blood_percentile:.0f}th percentile)"
        )
    if (
        data.avg_time_to_rank_5 is not None
        and data.rank_5_percentile is not None
        and data.rank_5_percentile >= _MIN_NOTABLE_PERCENTILE
    ):
        percentile_lines.append(
            f"Time to rank 5: {data.avg_time_to_rank_5:.1f} min avg "
            f"({data.rank_5_percentile:.0f}th percentile, higher = faster)"
        )
    if (
        data.superweapons_built_per_game is not None
        and data.superweapon_percentile is not None
        and data.superweapon_percentile >= _MIN_NOTABLE_PERCENTILE
    ):
        percentile_lines.append(
            f"Superweapons built: {data.superweapons_built_per_game:.2f}/game "
            f"({data.superweapon_percentile:.0f}th percentile)"
        )
    if percentile_lines:
        lines.append("")
        lines.append("Notable peer-relative percentiles (top quartile):")
        lines.extend(f"- {line}" for line in percentile_lines)

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


def _render_series(series: HypeTournamentSeries) -> list[str]:
    """One completed set: the headline score, then its games."""
    winner_is_a = series.winner == series.player_a
    loser = series.player_b if winner_is_a else series.player_a
    # Always written from the winner's side, so the first number is the
    # bigger one - "beat X 2-3" reads as a typo.
    if series.score_a is None or series.score_b is None:
        score = ""
    elif winner_is_a:
        score = f" {series.score_a}-{series.score_b}"
    else:
        score = f" {series.score_b}-{series.score_a}"
    lines = [f"- {series.round_name}: {series.winner} beat {loser}{score}"]

    for game in series.games:
        label = f"g{game.series_index}" if game.series_index else "game"
        mirror = (
            " [mirror decider - both on the same general]" if game.is_mirror else ""
        )
        lines.append(
            f"  - {label} on {game.map}: {game.winner} ({game.winner_general}) "
            f"beat {game.loser} ({game.loser_general}), "
            f"{game.duration_minutes:.1f} min{mirror}"
        )
    for pair in series.reverse_pairs:
        verdict = (
            f"{pair.swept_by} won both sides"
            if pair.swept_by
            else "split 1-1, each winning their turn on it"
        )
        lines.append(
            f"  - Reversed pair on {pair.map} ({pair.general_a} vs "
            f"{pair.general_b}): {verdict}"
        )
    if not series.games:
        lines.append("  - (result recorded; individual replays not linked)")
    return lines


def render_tournament_context(ctx: HypeTournamentContext) -> str:
    """Plain labeled text for what's already happened in this tournament.

    Returns "" when there's nothing to say, so the caller can drop the whole
    block rather than hand the model an empty section to reason about.
    """
    if ctx.is_empty:
        return ""

    lines = [
        "What has already happened in THIS tournament. Generals here are "
        "randomized and then played both ways (see the format note in your "
        "instructions), so treat a general as a draw, not a choice - the "
        "reversed-pair lines are where a result actually belongs to the "
        "player rather than the draw.",
        "",
    ]

    if ctx.prior_meetings:
        lines.append(
            f"{ctx.player1} and {ctx.player2} have ALREADY met in this tournament:"
        )
        for series in ctx.prior_meetings:
            lines.extend(_render_series(series))
        lines.append("")

    for run in (ctx.run1, ctx.run2):
        if run.series:
            lines.append(f"{run.player}'s run so far:")
            for series in run.series:
                lines.extend(_render_series(series))
        else:
            lines.append(
                f"{run.player} has not completed a match in this tournament yet."
            )
        lines.append("")

    return "\n".join(lines).rstrip()


def render_head_to_head(h2h: HypeHeadToHead) -> str:
    """Plain labeled text for a head-to-head pull - see the module
    docstring for why this isn't JSON."""
    lines = [
        f"{h2h.player1} vs {h2h.player2}",
        f"Overall record: {h2h.player1} {h2h.player1_wins} - {h2h.player2_wins} {h2h.player2}",
        f"Teammate games together: {h2h.teammate_games} ({h2h.teammate_wins} {h2h.player1}/"
        f"{h2h.player2} wins combined)",
    ]
    if h2h.player1_value_destroyed or h2h.player2_value_destroyed:
        lines.append(
            f"Value destroyed in these games: {h2h.player1} "
            f"{h2h.player1_value_destroyed} - {h2h.player2_value_destroyed} {h2h.player2}"
        )
    lines.append("")

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
