"""Query layer: what a request is asking about, separate from how it is served.

`routes/` owns HTTP - status codes, response models, auth. The modules here own
*selection*: which games, which players, which window. Handlers were carrying both,
and the selection half is the part that has to agree between endpoints.

Imports go one way: `routes` -> `queries` -> `cache`/`repositories`. Nothing here
may import from `routes`.
"""

from .games import (
    FORMAT_DESCRIPTION,
    MONTHS_BACK_DESCRIPTION,
    AllGames,
    CompetitiveGames,
    UnfilteredCompetitiveGames,
    WindowedCompetitiveGames,
    all_games,
    competitive_games,
)

__all__ = [
    "FORMAT_DESCRIPTION",
    "MONTHS_BACK_DESCRIPTION",
    "AllGames",
    "CompetitiveGames",
    "UnfilteredCompetitiveGames",
    "WindowedCompetitiveGames",
    "all_games",
    "competitive_games",
]
