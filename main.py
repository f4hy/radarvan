from datetime import datetime, UTC
from radarvan.api_types import Matches, MatchInfo, Player, General, Team
from typing import Union
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="radarvan", description="Stats for generals", version="0.1.0")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.get("/api/matches/{match_count}")
def get_matches(match_count: int) -> Matches:
    return Matches(
        matches=[
            MatchInfo(
                id=0,
                timestamp=datetime.now(),
                map="/maps/maps_tournament urban_tournament urban.webp",
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
                filename="/maps/maps_tournament urban_tournament urban.webp",
                incomplete="",
                notes="",
            ),
            MatchInfo(
                id=2,
                timestamp=datetime.now(),
                map="/maps/maps_tournament urban_tournament urban.webp",
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
                filename="/maps/maps_tournament urban_tournament urban.webp",
                incomplete="",
                notes="",
            ),
        ]
    )


app.mount("/", StaticFiles(directory="build", html=True), name="build")
