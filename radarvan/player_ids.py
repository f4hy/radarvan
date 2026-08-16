"""Player identity helpers - the known-player ID/alias tables, ``resolve_player_name``
for canonicalizing in-game aliases, and ``is_admin`` admin checks."""

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

# Canonical (resolved) names on each side of the mapping. Built once at import:
# `is_cpu_name` sits under `role_from_name`, which runs per player per match
# across the whole corpus, so rebuilding the set per call showed up in the
# rating/stats passes.
CPU_NAMES: frozenset[str] = frozenset(CPU_NAME_MAPPING.values())
HUMAN_NAMES: frozenset[str] = frozenset(PLAYER_NAME_MAPPING.values())

# Players (by claimed in-game name) with admin privileges. Hard-coded for now;
# add names here to grant admin.
ADMIN_PLAYERS: set[str] = {"Modus", "OneThree111"}


def is_admin(player_name: str | None) -> bool:
    """True if the given claimed in-game name is an admin."""
    return player_name is not None and player_name in ADMIN_PLAYERS


# Directory names on gentool.net to skip during scraping even though they
# match a known player ID substring - e.g. some other player's client happens
# to share Skip's ID (7E00462DFB0F), so scraping by ID alone would also pull
# in their unrelated games. Match against the full directory name, not just
# the player name, since we can't rely on name/alias matching here.
BLOCKED_SCRAPE_DIRS: set[str] = {"akram_7E00462DFB0F", "DESKTOP-CQM9_7E00462DFB0F"}


# Admins for the 1v1 double-elimination bracket feature specifically - a
# separate, narrower set from ADMIN_PLAYERS so granting bracket admin doesn't
# also grant access to unrelated admin features (debug page, backfills, …).
TOURNAMENT_ADMINS: set[str] = {"Modus", "Gorn"}


def is_tournament_admin(player_name: str | None) -> bool:
    """True if the given claimed in-game name can administer the 1v1 bracket."""
    return player_name is not None and player_name in TOURNAMENT_ADMINS


def resolve_player_name(name: str, color: str = "") -> str:
    """Resolve a player name from their in-game name and optional color."""
    if name.lower() == "pc":
        if color.lower() == "purple":
            return "pcap"
        if color.lower() == "pink" or color == "":
            return "Pancake"
        return "pcap"
    return NAME_MAPPING.get(name.lower(), name)


def is_cpu_name(name: str, color: str = "") -> bool:
    """True if the resolved name is a known CPU/AI opponent (any CPU_NAME_MAPPING side)."""
    return resolve_player_name(name, color) in CPU_NAMES
