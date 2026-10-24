"""Usage beacons the app sends about itself."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PageView(BaseModel):
    path: str = Field(max_length=512)
    query: str = Field(default="", max_length=1024)
    # The in-app page the visitor came from; None on the first page of a visit.
    referrer: str | None = Field(default=None, max_length=512)
