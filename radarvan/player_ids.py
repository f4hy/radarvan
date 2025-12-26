PLAYERS = {
    "wild": "A1AF434A9790",
    "modus": "09BAC013F91C",
    "bill": "5211058E5C33",
    "neo": "872FB64BC80D",
    "Skip": "7E00462DFB0F",
    "Tytan": "BE3C6996A715",
    "Pancake": "0F581CE73940",
    "Syn": "AABC3F9C1BD7",
    "Gorn": "E590BC7EC80D",
    "CoreDog": "528B373177B5",
}


def player_name_map(name: str) -> str:
    """Map all aliases"""

    mapping = {
        "skip": "Skip",
        "mod": "Modus",
        "131": "OneThree111",
        "neo": "Neo",
        "pan": "Pancake",
        "pc": "Pancake",
        "wld": "WildCard",
        "wild": "WildCard",
        "wildcard": "WildCard",
        "cd": "CoreDawg",
        "cd@wg": "CoreDawg",
        "syn": "Syn",
        "stm": "STM",
        "ty": "Tytan",
        "tyt": "Tytan",
        "pcap": "pcap",
        "grn": "Gorn",
        "fer": "EnragedFerret",
    }
    return mapping.get(name.lower(), name)
