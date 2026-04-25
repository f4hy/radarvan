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

NAME_MAPPING = {
    "skip": "Skip",
    "skp": "Skip",
    "sk": "Skip",
    "skippy": "Skip",
    "mod": "Modus",
    "modus": "Modus",
    "131": "OneThree111",
    "onethree111": "OneThree111",
    "neo": "Neo",
    "pan": "Pancake",
    "cake": "Pancake",
    "pc": "Pancake",
    "pancake": "Pancake",
    "w": "WildCard",
    "wld": "WildCard",
    "wild": "WildCard",
    "wildcard": "WildCard",
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
    "cpu": "HardArmy",
    "pcaps": "pcap",
    "pcap": "pcap",
    "g.c": "pcap",
    "gc": "pcap",
    "shift": "Shifty",
    "shifty": "Shifty",
    # "domi": "DoMiNaToR",
    # "-dominator-": "DoMiNaToR",
    # "dominator": "DoMiNaToR",
    # "[ooe]excal^": "[OoE]Excal^",
}

PLAYER_NAMES = set(NAME_MAPPING.values())


def resolve_player_name(name: str, color: str = "") -> str:
    """Resolve a player name from their in-game name and optional color."""
    if name.lower() == "pc":
        if color.lower() == "purple":
            return "pcap"
        if color.lower() == "pink" or color == "":
            return "Pancake"
        return "pcap"
    return NAME_MAPPING.get(name.lower(), name)
