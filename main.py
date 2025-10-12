from datetime import datetime, UTC
from radarvan.api_types import Matches, MatchInfo, Player, General, Team
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/matches/{match_count}")
def get_matches(match_count: int) -> Matches:
    return Matches(
        matches=[
            MatchInfo(
                id=0,
                timestamp=datetime.now(),
                map="test",
                winning_team=1,
                players=[
                    Player(name="Modus", general=General.AIR, team=Team.THREE),
                    Player(name="Bill", general=General.AIR, team=Team.ONE),
                    Player(name="Cake", general=General.AIR, team=Team.THREE),
                    Player(name="Wild", general=General.AIR, team=Team.ONE),
                    Player(name="Joe", general=General.AIR, team=Team.THREE),
                    Player(name="Skip", general=General.AIR, team=Team.ONE),
                ],
                duration_minutes=1.0,
                filename="test",
                incomplete="",
                notes="",
            ),
            MatchInfo(
                id=2,
                timestamp=datetime.now(),
                map="test",
                winning_team=1,
                players=[
                    Player(name="Modus", general=General.AIR, team=Team.THREE),
                    Player(name="Bill", general=General.AIR, team=Team.ONE),
                    Player(name="Cake", general=General.AIR, team=Team.THREE),
                    Player(name="Wild", general=General.AIR, team=Team.ONE),
                    Player(name="Joe", general=General.AIR, team=Team.THREE),
                    Player(name="Skip", general=General.AIR, team=Team.ONE),
                    Player(name="ty", general=General.AIR, team=Team.THREE),
                    Player(name="neo", general=General.AIR, team=Team.ONE),
                ],
                duration_minutes=1.0,
                filename="test",
                incomplete="",
                notes="",
            ),
        ]
    )
