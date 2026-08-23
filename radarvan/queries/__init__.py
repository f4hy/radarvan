"""Query layer: what a request is asking about, separate from how it is served.

`routes/` owns HTTP - status codes, response models, auth. The modules here own
*selection*: which games, which players, which window. Handlers were carrying both,
and the selection half is the part that has to agree between endpoints.

Imports go one way: `routes` -> `queries` -> `cache`/`repositories`. Nothing here
may import from `routes`.
"""

from .game_night import (
    NightGames,
    build_night_recap,
    closed_nights_within,
    latest_closed_night,
    night_narratives,
    on_night,
)
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
    "NightGames",
    "UnfilteredCompetitiveGames",
    "WindowedCompetitiveGames",
    "all_games",
    "build_night_recap",
    "closed_nights_within",
    "competitive_games",
    "latest_closed_night",
    "night_narratives",
    "on_night",
]
