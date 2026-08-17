"""LLM-generated matchup commentary."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class MatchupCommentaryResponse(BaseModel):
    commentary: str


class MatchupCommentaryPromptPreview(BaseModel):
    """The exact system + user content that would be sent to the active LLM
    provider, plus character counts - for inspecting/trimming payload size
    without spending a real API call. Shared by both dev-only preview
    endpoints (pre-game matchup, post-game recap); see routes/commentary.py.
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    system: str
    user_message: str = Field(alias="userMessage")
    system_chars: int = Field(alias="systemChars")
    user_message_chars: int = Field(alias="userMessageChars")
