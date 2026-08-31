"""LLM-generated matchup commentary."""

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

    model_config = ConfigDict(populate_by_name=True)

    system: str
    user_message: str = Field(alias="userMessage")
    system_chars: int = Field(alias="systemChars")
    user_message_chars: int = Field(alias="userMessageChars")
