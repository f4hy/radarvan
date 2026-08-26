"""Corpus-wide generals-power habits: what each player picks, and how the group differs.

The read model behind `/api/power_stats/`. Selection lives here rather than in
the route for the usual reason (`routes` -> `queries` -> `cache`), and because
the group baseline and one player's rows have to be computed from the *same*
pass - a baseline built separately would disagree with the rows it is supposed
to explain the moment either side changed its filter.

Where the numbers come from:

- Per-match picks and activations are `MatchDetails.powers`, a projection
  written when a match's details are derived (`radarvan.powers`). Nothing here
  reads a replay.
- The whole corpus is folded into `PowerIndex` in one pass, and only the
  *counters* are kept. Holding every match's projection in memory instead would
  cost tens of megabytes on a 512MB dyno to save a fold that takes milliseconds.

A match whose details have not been derived yet simply contributes nothing;
the payload reports how many matches did contribute so a thin page is legible
rather than mysterious.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ..api_types import (
    General,
    GeneralPowers,
    MatchPowers,
    PlayerPowerProfile,
    PowerRow,
    PowerStats,
    UnusualPick,
)
from ..cache import competitive_matches
from ..db_utils import ReplayManager
from ..derived import CORPUS, derived
from .. import generals_powers, player_ids
from ..generals_powers import RECON_POWERS
from ..match_details import DETAILS_VERSION

# A general a player has barely touched says nothing about their habits, and a
# power seen a handful of times across the whole group has no baseline worth
# comparing against.
MIN_GAMES_ON_GENERAL = 3
MIN_GROUP_GAMES_ON_GENERAL = 5
# An "unusual" pick needs both enough of the player's own games to be a habit
# and enough group games for the baseline to mean anything.
MIN_GAMES_FOR_UNUSUAL = 5
MIN_GROUP_GAMES_FOR_UNUSUAL = 15
# Below this the gap is noise dressed up as a finding, however large the z.
MIN_RATE_GAP = 0.15
MAX_UNUSUAL = 12
# A row the player has never touched earns its place only by being something
# the rest of the group reaches for - "everyone else takes this and you don't"
# is a finding. Below that it is a blank line about a power nobody uses.
MIN_GROUP_RATE_TO_SHOW_UNTOUCHED = 0.25
# The same idea for a power nobody buys: the building-granted ones (Spy
# Satellite, Particle Cannon) have no pick rate at all, so "the group sweeps
# with the satellite and this player never does" can only show up as usage.
MIN_GROUP_USE_RATE_TO_SHOW_UNTOUCHED = 0.05


@dataclass(slots=True)
class Counts:
    """Counters for one (player, general) pair, folded over the corpus."""

    games: int = 0
    minutes: float = 0.0
    # Games in which the family was taken at all - the numerator of a pick
    # *rate*, so it counts once however many levels of it were bought.
    picked: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Levels bought, across those games. Artillery Barrage taken to 3 is three
    # generals points, and telling that apart from a single level is most of
    # what "how they spend points" means.
    levels: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Minute of the *first* level, summed over the games it was taken.
    pick_minute_total: dict[str, float] = field(
        default_factory=lambda: defaultdict(float)
    )
    uses: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add(self, other: Counts) -> None:
        self.games += other.games
        self.minutes += other.minutes
        for power, n in other.picked.items():
            self.picked[power] += n
        for power, n in other.levels.items():
            self.levels[power] += n
        for power, total in other.pick_minute_total.items():
            self.pick_minute_total[power] += total
        for power, n in other.uses.items():
            self.uses[power] += n

    def minus(self, other: Counts) -> Counts:
        """This minus `other`, for "the group except this player".

        Subtraction rather than a second fold because every figure here is a
        plain sum - which is also why the pick timing is carried as a total and
        a count rather than a median.
        """
        out = Counts(
            games=self.games - other.games, minutes=self.minutes - other.minutes
        )
        for power, n in self.picked.items():
            out.picked[power] = n - other.picked.get(power, 0)
        for power, n in self.levels.items():
            out.levels[power] = n - other.levels.get(power, 0)
        for power, total in self.pick_minute_total.items():
            out.pick_minute_total[power] = total - other.pick_minute_total.get(
                power, 0.0
            )
        for power, n in self.uses.items():
            out.uses[power] = n - other.uses.get(power, 0)
        return out


@dataclass(slots=True)
class PowerIndex:
    """Every player's power counters, plus which powers are ever bought.

    `purchasable` is observed, not assumed: a power that appears in the corpus
    only as an activation and never as a pick is one a *building* grants (Spy
    Satellite from the Strategy Center, Scud Storm from its own structure), and
    showing it a "0% pick rate" would read as a choice nobody makes rather than
    a choice nobody has.
    """

    by_player: dict[tuple[str, General], Counts] = field(default_factory=dict)
    by_general: dict[General, Counts] = field(default_factory=dict)
    purchasable: set[str] = field(default_factory=set)
    # Families that unlock a unit rather than a generals-panel power. Recorded
    # as "never seen granting one" rather than "seen not granting one": the
    # base and per-general spellings of Infantry Paradrop share a family name
    # and disagree, and the one that puts a button on the panel wins.
    grants_power: set[str] = field(default_factory=set)
    matches: int = 0

    @property
    def players(self) -> list[str]:
        """The roster the page offers, most games first.

        Restricted to `player_ids.HUMAN_NAMES` - the same canonical set
        `player_stats.most_common_colors` builds identity colors from, so the
        picker offers exactly the people the rest of the app treats as players.
        A one-off guest or an unresolved alias is not someone you compare
        habits for.

        The *baseline* is deliberately not restricted this way: "everyone else
        on this general" means everyone who played it, and dropping a guest's
        games would narrow the comparison without making it more honest.
        """
        games: Counter[str] = Counter()
        for (player, _), counts in self.by_player.items():
            if player in player_ids.HUMAN_NAMES:
                games[player] += counts.games
        # Most-played first, then alphabetical - a button set reads left to
        # right, and the regulars belong at the start of it.
        return sorted(games, key=lambda name: (-games[name], name))


def _fold(index: PowerIndex, powers: MatchPowers) -> None:
    for player in powers.players:
        if player.general is General.UNRECOGNIZED:
            continue
        one = Counts(games=1, minutes=player.minutes)
        # Group by *family*, not by the individual science: Paradrop 1/2/3 are
        # one habit, and splitting them would compare a player's level-2 rate
        # against a group rate diluted across three rows. Picks arrive in time
        # order, so the first sighting of a family is the minute it was opened.
        for pick in player.picks:
            science = generals_powers.resolve(pick.science_id, player.faction)
            family = science.family if science else f"Science #{pick.science_id}"
            if family not in one.picked:
                one.picked[family] = 1
                one.pick_minute_total[family] = pick.at_minute
            one.levels[family] += 1
            if science is not None:
                index.purchasable.add(family)
                if science.grants_power:
                    index.grants_power.add(family)
        for use in player.uses:
            one.uses[use.name] += use.count

        key = (player.player_name, player.general)
        index.by_player.setdefault(key, Counts()).add(one)
        index.by_general.setdefault(player.general, Counts()).add(one)


@derived(on=CORPUS, maxsize=3)
def power_index(replay_manager: ReplayManager, coverage: int) -> PowerIndex:
    """Fold every competitive match's powers projection into per-player counters.

    Takes a `ReplayManager` rather than a corpus so the derivation binds to the
    database-probed CORPUS token: this is one big query, and it should re-run
    when matches land, not once per distinct game-format filter.

    `coverage` is `count_cached_details(DETAILS_VERSION)` - the number of
    matches whose details have actually been derived. It is a key param, not
    decoration: CORPUS moves when *matches* change, and a cache warm changes
    the answer without changing the corpus. Without it, the first call after a
    DETAILS_VERSION bump (when the table is empty) would cache an empty index
    and serve it until somebody played a game. It stops moving once the warm
    finishes, so the steady state is a cache hit.
    """
    games = list(competitive_matches(replay_manager).values())
    rows = replay_manager.get_cached_powers_rows(
        [game.id for game in games], DETAILS_VERSION
    )
    index = PowerIndex()
    for raw in rows.values():
        _fold(index, MatchPowers.model_validate(raw))
        index.matches += 1
    return index


def _rate(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def _surprise(rate: float, group_rate: float, games: int) -> float:
    """Binomial z of `rate` against `group_rate` over `games` observations.

    Clamped away from a zero-variance baseline: a group rate of exactly 0 or 1
    would otherwise divide by zero and rank a single deviation infinitely
    surprising.
    """
    p = min(max(group_rate, 0.05), 0.95)
    return (rate - p) / math.sqrt(p * (1 - p) / games)


def _recon_rate(counts: Counts) -> float:
    return _rate(
        sum(n for power, n in counts.uses.items() if power in RECON_POWERS),
        counts.minutes,
    )


def _rows(mine: Counts, theirs: Counts, index: PowerIndex) -> list[PowerRow]:
    rows: list[PowerRow] = []
    every_power = (
        set(mine.picked) | set(mine.uses) | set(theirs.picked) | set(theirs.uses)
    )
    for power in sorted(every_power):
        picked = mine.picked.get(power, 0)
        group_picked = theirs.picked.get(power, 0)
        rows.append(
            PowerRow(
                power=power,
                purchasable=power in index.purchasable,
                unlocks_unit=(
                    power in index.purchasable and power not in index.grants_power
                ),
                games_picked=picked,
                pick_rate=_rate(picked, mine.games),
                group_pick_rate=_rate(group_picked, theirs.games),
                avg_pick_minute=(
                    mine.pick_minute_total[power] / picked if picked else None
                ),
                group_avg_pick_minute=(
                    theirs.pick_minute_total.get(power, 0.0) / group_picked
                    if group_picked
                    else None
                ),
                avg_levels=_rate(mine.levels.get(power, 0), picked),
                group_avg_levels=_rate(theirs.levels.get(power, 0), group_picked),
                uses=mine.uses.get(power, 0),
                uses_per_minute=_rate(mine.uses.get(power, 0), mine.minutes),
                group_uses_per_minute=_rate(theirs.uses.get(power, 0), theirs.minutes),
            )
        )
    rows = [
        row
        for row in rows
        if row.games_picked
        or row.uses
        or row.group_pick_rate >= MIN_GROUP_RATE_TO_SHOW_UNTOUCHED
        or row.group_uses_per_minute >= MIN_GROUP_USE_RATE_TO_SHOW_UNTOUCHED
    ]
    rows.sort(key=lambda r: (-r.pick_rate, -r.uses_per_minute, r.power))
    return rows


def profile_for(index: PowerIndex, player: str) -> PlayerPowerProfile:
    """One player's per-general breakdown and their stand-out picks."""
    generals: list[GeneralPowers] = []
    unusual: list[UnusualPick] = []
    total_games = 0

    for general in sorted(index.by_general, key=int):
        mine = index.by_player.get((player, general))
        if mine is None or mine.games < MIN_GAMES_ON_GENERAL:
            continue
        theirs = index.by_general[general].minus(mine)
        if theirs.games < MIN_GROUP_GAMES_ON_GENERAL:
            continue
        total_games += mine.games
        rows = _rows(mine, theirs, index)
        generals.append(
            GeneralPowers(
                general=general,
                games=mine.games,
                minutes=mine.minutes,
                group_games=theirs.games,
                recon_per_minute=_recon_rate(mine),
                group_recon_per_minute=_recon_rate(theirs),
                rows=rows,
            )
        )
        if (
            mine.games < MIN_GAMES_FOR_UNUSUAL
            or theirs.games < MIN_GROUP_GAMES_FOR_UNUSUAL
        ):
            continue
        for row in rows:
            if not row.purchasable:
                continue
            gap = row.pick_rate - row.group_pick_rate
            if abs(gap) < MIN_RATE_GAP:
                continue
            unusual.append(
                UnusualPick(
                    general=general,
                    power=row.power,
                    games=mine.games,
                    pick_rate=row.pick_rate,
                    group_pick_rate=row.group_pick_rate,
                    surprise=_surprise(row.pick_rate, row.group_pick_rate, mine.games),
                    direction="over" if gap > 0 else "under",
                )
            )

    generals.sort(key=lambda g: -g.games)
    unusual.sort(key=lambda u: -abs(u.surprise))
    return PlayerPowerProfile(
        player=player,
        games=total_games,
        generals=generals,
        unusual=unusual[:MAX_UNUSUAL],
    )


def power_stats(replay_manager: ReplayManager, player: str | None) -> PowerStats:
    """The powers page payload for `player` (or just the roster when None)."""
    index = power_index(
        replay_manager, replay_manager.count_cached_details(DETAILS_VERSION)
    )
    players = index.players
    profile = (
        profile_for(index, player) if player is not None and player in players else None
    )
    return PowerStats(players=players, matches=index.matches, profile=profile)
