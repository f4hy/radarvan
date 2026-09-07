"""The game-night recap: one evening of games, reduced to a page.

Two layers, and the split is the point. Everything except ``ai_summary`` is
**deterministic** - recomputed from the night's matches on every request, free,
and available for every night back to the start of the corpus.
``ai_summary`` is a real, billed LLM call, so it is generated **once**, by the
nightly scheduler job, for a night that has just closed; it is never generated
to serve a request and old nights are never backfilled. A night without one
returns null there and the page simply omits that section.
"""

from __future__ import annotations

from datetime import date as date_type, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GameNightPlayerLine(BaseModel):
    """One player's night: their record and what they played.

    Computed over the night's *decided competitive* games only, so it agrees
    with every other W/L surface in the app (see the "two match sets" note in
    CLAUDE.md). Observers never appear - a spectator slot is not a game
    played.
    """

    model_config = ConfigDict(populate_by_name=True)

    player: str
    wins: int
    losses: int
    games: int
    # Generals this player was handed over the night, most-played first.
    # Generals are randomized per match, so this is flavour, not a choice.
    generals: list[str] = Field(default_factory=list)
    # Longest run of wins within the night, in the order the games were played.
    best_streak: int = Field(default=0, alias="bestStreak")
    # Best single-game APM of the night, when APM could be derived.
    best_apm: float | None = Field(default=None, alias="bestApm")


class GameNightHighlight(BaseModel):
    """One notable thing that happened, ready to render as a card.

    ``kind`` is a stable slug ("longest_game", "upset", "first_blood", ...)
    the frontend maps to an icon; ``title`` and ``detail`` are already
    human-readable, so an unrecognised kind still renders correctly.
    """

    model_config = ConfigDict(populate_by_name=True)

    kind: str
    title: str
    detail: str
    match_id: int | None = Field(default=None, alias="matchId")
    # Winner's win-prob sparkline, for the "momentum" highlight only.
    points: list[float] | None = Field(default=None)


class GameNightRecap(BaseModel):
    """Everything the recap page shows for one game night.

    ``match_count`` counts every match played that night; ``counted_matches``
    is the decided-competitive subset the player lines and most highlights are
    computed over. The two differ when the night included comp-stomps,
    unfinished games, or games with an unknown player.
    """

    model_config = ConfigDict(populate_by_name=True)

    date: date_type
    match_count: int = Field(alias="matchCount")
    counted_matches: int = Field(alias="countedMatches")
    total_minutes: float = Field(alias="totalMinutes")
    median_minutes: float | None = Field(default=None, alias="medianMinutes")
    # Wall-clock span of the night, from the first game's start to the last
    # game's start plus its duration. Null when nothing was played.
    started_at: datetime | None = Field(default=None, alias="startedAt")
    ended_at: datetime | None = Field(default=None, alias="endedAt")
    # {"2v2": 6, "3v3": 2}, over every match of the night.
    formats: dict[str, int] = Field(default_factory=dict)
    # {map name: games played}, most-played first.
    maps: dict[str, int] = Field(default_factory=dict)
    players: list[GameNightPlayerLine] = Field(default_factory=list)
    highlights: list[GameNightHighlight] = Field(default_factory=list)
    # Generated once by the nightly job; null for every night that predates
    # the feature and for a night still in progress. Never generated to serve
    # a request - see the module docstring.
    ai_summary: str | None = Field(default=None, alias="aiSummary")
    ai_summary_provider: str | None = Field(default=None, alias="aiSummaryProvider")
    ai_summary_computed_at: datetime | None = Field(
        default=None, alias="aiSummaryComputedAt"
    )


class GameNightSummaryStatus(BaseModel):
    """Whether a night's LLM summary exists, without shipping its text.

    Used by the ops panel to see what the nightly job has and hasn't written.
    """

    model_config = ConfigDict(populate_by_name=True)

    date: date_type
    has_summary: bool = Field(alias="hasSummary")
    provider: str | None = None
    computed_at: datetime | None = Field(default=None, alias="computedAt")


# generated: a real LLM call was spent and a row written.
# already_summarized: a stored recap existed; the backfill never overwrites.
# too_few_games: below the floor a night has to clear to be worth a call.
# not_attempted: eligible, but this run's max_to_update was already used up.
# failed: the provider errored on this night, which stops the run.
GameNightBackfillOutcome = Literal[
    "generated",
    "already_summarized",
    "too_few_games",
    "not_attempted",
    "failed",
]


class GameNightBackfillNight(BaseModel):
    """What the backfill did about one night in the window, and why.

    Every night considered gets a row, including the ones left alone - the
    point of the report is to show what a run *would* have spent on, so the
    operator can widen the budget deliberately rather than by rerunning
    blind.
    """

    model_config = ConfigDict(populate_by_name=True)

    date: date_type
    # Games played that night (all of them, matching GameNightRecap.matchCount).
    matches: int
    outcome: GameNightBackfillOutcome


class GameNightBackfill(BaseModel):
    """The result of one backfill run over the last N game nights."""

    model_config = ConfigDict(populate_by_name=True)

    days: int
    # Nights written this run - i.e. how many LLM calls this run billed.
    generated: int
    # Eligible nights left unwritten (budget exhausted, or the run stopped on
    # an error). Re-run to pick them up.
    remaining: int
    nights: list[GameNightBackfillNight] = Field(default_factory=list)
