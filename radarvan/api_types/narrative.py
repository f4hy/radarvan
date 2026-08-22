"""The deterministic per-match narrative: what happened, in order, in words.

A projection of ``MatchDetails`` - not a new derivation of the replay - so it
carries no version of its own and costs nothing to add: the route builds it
from the same cached details ``/api/details`` serves (see
``routes/matches.get_match_narrative``, which mirrors ``get_build_orders``).

Deliberately not LLM-generated. Every beat is a fact already in the details
(first blood, rank progression, a superweapon launch, a player going hunted),
rendered as a sentence; the ordering and the selection are the whole of the
editorial judgement. That keeps it free, instant, and identical on every
request - the LLM writing in this app is reserved for the bracket blurbs and
the once-a-night game-night summary.
"""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .common import Minute


class NarrativeBeat(BaseModel):
    """One sentence of the story, optionally pinned to a minute.

    ``kind`` groups beats for styling and is one of: "setup" (map, format,
    lineup - no minute), "first_blood", "milestone" (rank 5, search &
    destroy), "superweapon", "collapse" (went hunted, lost power), "economy",
    "damage", "tempo" (APM), "result". The frontend maps it to an icon; an
    unknown kind must render as a plain bullet rather than break the list.
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    kind: str
    text: str
    at_minute: Minute | None = Field(default=None, alias="atMinute")
    # The canonical player this beat is about, when it is about one player.
    # Lets the UI tint the row with that player's colour.
    player_name: str | None = Field(default=None, alias="playerName")


class MatchNarrative(BaseModel):
    """A match retold as an ordered list of beats.

    ``beats`` is empty when the match has no parsed details yet; ``headline``
    and the match metadata are still populated from the match row, so the UI
    always has something to show.
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    match_id: int = Field(alias="matchId")
    headline: str
    beats: list[NarrativeBeat] = Field(default_factory=list)
    # When the game started (UTC). Carried because a "game night" is a date
    # key, not a session: an evening can be two disjoint sittings, and only the
    # clock times show that.
    started_at: datetime | None = Field(default=None, alias="startedAt")
    # The tournament this game counted toward, as "slug" or "slug - Round
    # Name", or null for a casual game. A tournament link is the only
    # "played to win" signal in the data (see CLAUDE.md), so it changes how a
    # result should be read.
    tournament: str | None = None
