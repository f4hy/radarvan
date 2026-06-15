from collections.abc import Iterable
from typing import Protocol

PLAYERS = {
    "wild": "A1AF434A9790",
    "modus": "09BAC013F91C",
    "Mod": "4046F3C8B32E",  # new laptop
    "bill": "5211058E5C33",
    "neo": "872FB64BC80D",
    "Skip": "7E00462DFB0F",
    "Tytan": "BE3C6996A715",
    "Pancake": "0F581CE73940",
    "Syn": "AABC3F9C1BD7",
    "Gorn": "E590BC7EC80D",
    "CoreDog": "528B373177B5",
    "Fer": "C6D491FD7F19",
}


PLAYER_NAME_MAPPING = {
    "skip": "Skip",
    "skp": "Skip",
    "sk": "Skip",
    "skippy": "Skip",
    "skippy1999": "Skip",
    "mod": "Modus",
    "modus": "Modus",
    "131": "OneThree111",
    "onethree111": "OneThree111",
    "onethree111_2": "OneThree111",
    "neo": "Neo",
    "pan": "Pancake",
    "cake": "Pancake",
    "pc": "Pancake",
    "pancake": "Pancake",
    "w": "WildCard",
    "wld": "WildCard",
    "wild": "WildCard",
    "wildcard": "WildCard",
    "ktkelly16": "WildCard",
    "cd": "CoreDawg",
    "coredawg": "CoreDawg",
    "c": "CoreDawg",
    "cor": "CoreDawg",
    "cb": "CoreDawg",
    "cd@wg": "CoreDawg",
    "cdawg": "CoreDawg",
    "cdog": "CoreDawg",
    "cdg": "CoreDawg",
    "cdwg": "CoreDawg",
    "syn": "Syn",
    "stm": "STM",
    "ty": "Tytan",
    "tytan": "Tytan",
    "tyt": "Tytan",
    "t": "Tytan",
    "grn": "Gorn",
    "gorn": "Gorn",
    "go": "Gorn",
    "scottagorn": "Gorn",
    "fer": "EnragedFerret",
    "ferret": "EnragedFerret",
    "enragedferret": "EnragedFerret",
    "pcaps": "pcap",
    "pcap": "pcap",
    "g.c": "pcap",
    "gc": "pcap",
    "shft": "Shifty",
    "shift": "Shifty",
    "shifty": "Shifty",
    "wilywolf": "WilyWolf",
}

CPU_NAME_MAPPING = {
    "cpu": "HardArmy",
    "hardarmy": "HardArmy",
    "hard army": "HardArmy",
    "mediumarmy": "MediumArmy",
    "medium army": "MediumArmy",
    "easyarmy": "EasyArmy",
    "easy army": "EasyArmy",
    "tacticalai": "TacticalAI",
    "tactical ai": "TacticalAI",
}

NAME_MAPPING = PLAYER_NAME_MAPPING | CPU_NAME_MAPPING

PLAYER_NAMES = set(NAME_MAPPING.values())

# Players (by claimed in-game name) with admin privileges. Hard-coded for now;
# add names here to grant admin.
ADMIN_PLAYERS: set[str] = {"Modus", "OneThree111"}


def is_admin(player_name: str | None) -> bool:
    """True if the given claimed in-game name is an admin."""
    return player_name is not None and player_name in ADMIN_PLAYERS


def resolve_player_name(name: str, color: str = "") -> str:
    """Resolve a player name from their in-game name and optional color."""
    if name.lower() == "pc":
        if color.lower() == "purple":
            return "pcap"
        if color.lower() == "pink" or color == "":
            return "Pancake"
        return "pcap"
    return NAME_MAPPING.get(name.lower(), name)


class _Player(Protocol):
    @property
    def team(self) -> int: ...
    @property
    def name(self) -> str: ...
    @property
    def color(self) -> str: ...


def all_teams_have_group_player(players: Iterable[_Player]) -> bool:
    """Return True if every team (team > 0) has at least one player from PLAYER_NAMES."""
    teams: dict[int, bool] = {}
    for p in players:
        if p.team <= 0:
            continue
        name = resolve_player_name(p.name, p.color)
        if p.team not in teams:
            teams[p.team] = False
        if name in PLAYER_NAMES:
            teams[p.team] = True
    return bool(teams) and all(teams.values())
