"""Double-elimination bracket topology, entry, and prediction shapes."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    model_validator,
)
from datetime import datetime
from typing import Annotated, Literal
from .. import bracket as _bracket
from .common import PlayerName
from .matches import MatchInfo


class BracketMatchGames(BaseModel):
    """The games played for one bracket match, plus what else it could be.

    ``linked`` is what's persisted. ``candidates`` is what the detector would
    propose but nobody has confirmed - shown to tournament admins so they can
    link a game the automatic rule missed (a mismatched alias, a game played
    on a different night than scheduled).
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    match_id: str = Field(alias="matchId")
    linked: list[MatchInfo] = Field(default_factory=list)
    candidates: list[MatchInfo] = Field(default_factory=list)


class SetBracketGamesRequest(BaseModel):
    match_ids: list[int]


class BracketPlayerEntry(BaseModel):
    seed: int
    player_name: PlayerName


class CreateBracketRequest(BaseModel):
    players: list[BracketPlayerEntry]

    @model_validator(mode="after")
    def _validate_seeds(self) -> CreateBracketRequest:
        seeds = sorted(p.seed for p in self.players)
        n = len(seeds)
        if not (_bracket.MIN_PLAYERS <= n <= _bracket.MAX_PLAYERS):
            raise ValueError(
                f"players must number between {_bracket.MIN_PLAYERS} "
                f"and {_bracket.MAX_PLAYERS}"
            )
        if seeds != list(range(1, n + 1)):
            raise ValueError(f"players must have {n} unique seeds numbered 1-{n}")
        return self


class SetBracketMatchRequest(BaseModel):
    scheduled_at: datetime | None = None
    best_of: Literal[3, 5, 7, 9] | None = None
    score_a: int | None = None
    score_b: int | None = None


class BracketMatchPrediction(BaseModel):
    match_id: str
    # {player_name: vote_count}, only the two players in this match - total
    # prediction count is len(tally.values()) summed, derivable client-side.
    tally: dict[str, int] = Field(default_factory=dict)
    # The logged-in viewer's own pick (None if unset or logged out).
    my_pick: str | None = None
    # False once the match started (scheduled_at passed) or was scored -
    # predictions lock so nobody can "predict" after already knowing the
    # outcome.
    open: bool = True
    # Display names of users who predicted the actual winner - populated
    # only once the match is completed (None beforehand, so the frontend
    # can't accidentally leak a live result). Empty list means nobody called
    # it, not "not completed yet".
    correct_picks: list[str] | None = None


class BracketPredictionLeaderboardEntry(BaseModel):
    user_name: str
    correct: int
    total: int


class SetMatchPredictionRequest(BaseModel):
    # None clears the viewer's pick for this match.
    predicted_winner: str | None = None


class SetBracketRevealAtRequest(BaseModel):
    # When the bracket becomes publicly visible. None clears the gate (the
    # bracket is visible immediately, regardless of the server clock).
    reveal_at: datetime | None = None


class SeedSource(BaseModel):
    kind: Literal["seed"] = "seed"
    seed: int


class WinnerOfSource(BaseModel):
    kind: Literal["winner"] = "winner"
    match_id: str


class LoserOfSource(BaseModel):
    kind: Literal["loser"] = "loser"
    match_id: str


MatchSource = Annotated[
    SeedSource | WinnerOfSource | LoserOfSource, Field(discriminator="kind")
]


class BracketMatchOutput(BaseModel):
    match_id: str
    bracket: Literal["W", "L", "GF"]
    round_number: int
    round_name: str
    player_a: str | None = None
    player_b: str | None = None
    scheduled_at: datetime | None = None
    best_of: int | None = None
    score_a: int | None = None
    score_b: int | None = None
    winner: str | None = None
    status: Literal["pending", "ready", "completed", "not_applicable"]
    source_a: MatchSource
    source_b: MatchSource


class BracketTournamentOutput(BaseModel):
    # Alphabetical roster (names only, no seeding) - always populated,
    # regardless of `revealed`. Knowing who's *in* the tournament isn't a
    # spoiler; the bracket placement (`players`, `matches[*].player_a/b`,
    # `bye_advances`, `champion`/`runner_up`) is, so those are withheld
    # (empty list / null) until `revealed` is true.
    participant_names: list[str]
    players: list[BracketPlayerEntry]
    matches: list[BracketMatchOutput]
    bye_advances: list[BracketPlayerEntry]
    champion: str | None = None
    runner_up: str | None = None
    needs_reset: bool
    # Server-computed (never trust a client clock for this): true once
    # `reveal_at` has passed, or immediately if `reveal_at` is unset.
    revealed: bool
    reveal_at: datetime | None = None


class BracketSummaryResponse(BaseModel):
    """The AI-generated post-game recap of one completed bracket set.

    ``summary`` is null while the set isn't recappable yet - not finished, or
    finished but with fewer replays linked than games played. ``ready`` says
    which of those it is, so the UI can promise a recap that's coming instead
    of showing nothing.
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    match_id: str = Field(alias="matchId")
    ready: bool
    summary: str | None = None
