"""Generals-power identity: what a `PurchaseScience` order actually bought.

The replay body records a power *pick* as ``PurchaseScience`` with a single
bare integer argument (``14``, ``36``, ``62``) - no name, no faction. That
integer is the index of the entry in the game's ``Science.ini``, offset by one
(the engine's science list is 1-based; the file's first entry, ``SCIENCE_AMERICA``,
is id 1). `SCIENCES` below is that file, transcribed.

The offset was not assumed - it was verified against the corpus two ways, and
both agree on every entry that either one can see:

1. **Prerequisite chains.** ``SCIENCE_Paradrop2`` lists ``SCIENCE_Paradrop1`` as
   a prerequisite, so id 17 must never be bought without id 16 first. Sweeping
   ~580 matches, every multi-level family (Paradrop, A-10, Artillery Barrage,
   Cash Hack, Frenzy, Rebel Ambush, Cash Bounty, Emergency Repair, the Paradrop
   variants) shows exactly the chain the file predicts.
2. **`RequiredScience` links.** ``SpecialPower.ini`` names the science each
   power needs, so a power must never be *used* before its science is bought.
   Sixteen such pairs survive that test with zero violations across the corpus
   - id 14 -> Spy Drone, 16 -> Paradrop, 19 -> A-10, 27 -> Daisy Cutter,
   36 -> Artillery Barrage, 45 -> Cash Hack, 56 -> Rebel Ambush, 65 -> Anthrax
   Bomb, 66 -> Sneak Attack, 69 -> Emergency Repair, 72 -> Early Emergency
   Repair, 83 -> Tank Paradrop, 90 -> Infantry Paradrop, 94 -> Air Force A-10,
   and the Chem/Nuke variants.

Two classes of id are deliberately *not* in the table:

- **Unpurchasable sciences.** ``Science.ini`` marks several entries
  ``SciencePurchasePointCost = 0``, which its own comment explains means "not
  purchasable, NOT free" (Black Market Nuke, Crate Drop, the campaign-only
  strikes). They can never appear in a ``PurchaseScience`` order, so an id that
  lands on one means the mapping is wrong there rather than that someone bought
  a campaign science - see `UNIDENTIFIED` below.
- **Ids past the end of the file.** The corpus contains purchases at ids 75-77
  and 97-99, beyond the 96 entries stock Zero Hour ships. Ids 75-77 are a
  universal, rank-1, three-level chain that ~11% of players take as their very
  first pick, and buying 75 always precedes that player's first use of the
  power the stock file calls GPS Scrambler. Whatever the group's build adds
  there, guessing a name would be worse than admitting we don't know one.

`resolve` therefore returns None rather than a wrong name, and callers render
the bare id. It also refuses to name a science whose faction disagrees with the
player's: the tail of the file (the per-general blocks) is where a non-stock
build is most likely to diverge, and a China player "buying" an Air Force
science is the signature of exactly that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .api_types import General
from .replay_helpers import FACTION_PREFIX_RE, clean_object_name


@dataclass(frozen=True, slots=True)
class Science:
    """One purchasable entry of the game's science list."""

    key: str
    # Display name with the level and the per-general variant stripped, so the
    # three levels of Paradrop share one family and can be counted together.
    #
    # Taken from the *power the science grants*, not from the science's own key,
    # so a pick and its activations land on the same row: the science is
    # `SCIENCE_ChinaCarpetBomb` while the power is `SuperweaponChinaCarpetBomb`,
    # and naming each from its own key put "China Carpet Bomb (picked 70%)" and
    # "Carpet Bomb (18 uses)" on separate lines of the same table.
    family: str
    level: int
    # "America" / "China" / "GLA", or "" for the ones with no country
    # prerequisite (the Emergency Repair families).
    faction: str
    # Generals rank required to buy it: 1, 3 or 5.
    rank: int
    # "" for the base science, else the general it belongs to ("AirF", "Nuke",
    # "Infa", "Slth", "Chem", "Early", ...).
    variant: str
    # True when some SpecialPower names this science as its `RequiredScience` -
    # i.e. buying it puts a button on the generals panel. False for the ones
    # that unlock a *unit* instead (Paladin Tank, Red Guard Training, Marauder
    # Tank): still a generals point, but nothing to activate, so a page that
    # showed them alongside powers with a blank usage column would read as
    # broken rather than as a different kind of purchase.
    grants_power: bool = True

    @property
    def name(self) -> str:
        """Full display name: family, then level when the family has levels."""
        return f"{self.family} {self.level}" if self.level > 1 else self.family


_S = Science

SCIENCES: dict[int, Science] = {
    12: _S("SCIENCE_PaladinTank", "Paladin Tank", 1, "America", 1, "", False),
    13: _S("SCIENCE_StealthFighter", "Stealth Fighter", 1, "America", 1, "", False),
    14: _S("SCIENCE_SpyDrone", "Spy Drone", 1, "America", 1, "", True),
    15: _S("SCIENCE_Pathfinder", "Pathfinder", 1, "America", 3, "", False),
    16: _S("SCIENCE_Paradrop1", "Paradrop", 1, "America", 3, "", True),
    17: _S("SCIENCE_Paradrop2", "Paradrop", 2, "", 3, "", True),
    18: _S("SCIENCE_Paradrop3", "Paradrop", 3, "", 3, "", True),
    19: _S(
        "SCIENCE_A10ThunderboltMissileStrike1",
        "A10 Thunderbolt Missile Strike",
        1,
        "America",
        3,
        "",
        True,
    ),
    20: _S(
        "SCIENCE_A10ThunderboltMissileStrike2",
        "A10 Thunderbolt Missile Strike",
        2,
        "",
        3,
        "",
        True,
    ),
    21: _S(
        "SCIENCE_A10ThunderboltMissileStrike3",
        "A10 Thunderbolt Missile Strike",
        3,
        "",
        3,
        "",
        True,
    ),
    22: _S("SCIENCE_SpectreGunshipSolo", "Spectre Gunship", 1, "America", 5, "", True),
    23: _S("SCIENCE_SpectreGunship1", "Spectre Gunship", 1, "America", 3, "", True),
    24: _S("SCIENCE_SpectreGunship2", "Spectre Gunship", 2, "", 3, "", True),
    25: _S("SCIENCE_SpectreGunship3", "Spectre Gunship", 3, "", 5, "", True),
    26: _S("SCIENCE_AirF_CarpetBomb", "Carpet Bomb", 1, "America", 1, "AirF", True),
    27: _S("SCIENCE_DaisyCutter", "Daisy Cutter", 1, "America", 5, "", True),
    28: _S("SCIENCE_LeafletDrop", "Leaflet Drop", 1, "America", 5, "", True),
    29: _S("Early_SCIENCE_LeafletDrop", "Leaflet Drop", 1, "America", 3, "Early", True),
    31: _S("SCIENCE_RedGuardTraining", "Red Guard Training", 1, "China", 1, "", False),
    32: _S(
        "SCIENCE_BattlemasterTraining",
        "Battlemaster Training",
        1,
        "China",
        1,
        "",
        False,
    ),
    33: _S("SCIENCE_ClusterMines", "Cluster Mines", 1, "China", 3, "", True),
    34: _S("SCIENCE_ArtilleryTraining", "Artillery Training", 1, "China", 1, "", False),
    35: _S("SCIENCE_NukeLauncher", "Nuke Launcher", 1, "China", 1, "", False),
    36: _S("SCIENCE_ArtilleryBarrage1", "Artillery Barrage", 1, "China", 3, "", True),
    37: _S("SCIENCE_ArtilleryBarrage2", "Artillery Barrage", 2, "", 3, "", True),
    38: _S("SCIENCE_ArtilleryBarrage3", "Artillery Barrage", 3, "", 3, "", True),
    39: _S("SCIENCE_Frenzy1", "Frenzy", 1, "China", 3, "", True),
    40: _S("SCIENCE_Frenzy2", "Frenzy", 2, "", 3, "", True),
    41: _S("SCIENCE_Frenzy3", "Frenzy", 3, "", 3, "", True),
    42: _S("Early_SCIENCE_Frenzy1", "Frenzy", 1, "China", 1, "Early", True),
    43: _S("Early_SCIENCE_Frenzy2", "Frenzy", 2, "", 3, "Early", True),
    44: _S("Early_SCIENCE_Frenzy3", "Frenzy", 3, "", 3, "Early", True),
    45: _S("SCIENCE_CashHack1", "Cash Hack", 1, "China", 3, "", True),
    46: _S("SCIENCE_CashHack2", "Cash Hack", 2, "", 3, "", True),
    47: _S("SCIENCE_CashHack3", "Cash Hack", 3, "", 3, "", True),
    48: _S("SCIENCE_EMPPulse", "EMP Pulse", 1, "China", 5, "", True),
    49: _S("SCIENCE_ChinaCarpetBomb", "Carpet Bomb", 1, "China", 5, "", True),
    50: _S(
        "Early_SCIENCE_ChinaCarpetBomb", "Carpet Bomb", 1, "China", 3, "Early", True
    ),
    51: _S("Nuke_SCIENCE_ChinaCarpetBomb", "Carpet Bomb", 1, "China", 3, "Nuke", True),
    52: _S("SCIENCE_ScudLauncher", "Scud Launcher", 1, "GLA", 1, "", False),
    53: _S("SCIENCE_MarauderTank", "Marauder Tank", 1, "GLA", 1, "", False),
    54: _S("SCIENCE_TechnicalTraining", "Technical Training", 1, "GLA", 1, "", False),
    55: _S("SCIENCE_Hijacker", "Hijacker", 1, "GLA", 3, "", False),
    56: _S("SCIENCE_RebelAmbush1", "Rebel Ambush", 1, "GLA", 3, "", True),
    57: _S("SCIENCE_RebelAmbush2", "Rebel Ambush", 2, "", 3, "", True),
    58: _S("SCIENCE_RebelAmbush3", "Rebel Ambush", 3, "", 3, "", True),
    59: _S("Chem_SCIENCE_RebelAmbush1", "Rebel Ambush", 1, "GLA", 3, "Chem", True),
    60: _S("Chem_SCIENCE_RebelAmbush2", "Rebel Ambush", 2, "", 3, "Chem", True),
    61: _S("Chem_SCIENCE_RebelAmbush3", "Rebel Ambush", 3, "", 3, "Chem", True),
    62: _S("SCIENCE_CashBounty1", "Cash Bounty", 1, "GLA", 3, "", True),
    63: _S("SCIENCE_CashBounty2", "Cash Bounty", 2, "", 3, "", True),
    64: _S("SCIENCE_CashBounty3", "Cash Bounty", 3, "", 3, "", True),
    65: _S("SCIENCE_AnthraxBomb", "Anthrax Bomb", 1, "GLA", 5, "", True),
    66: _S("SCIENCE_SneakAttack", "Sneak Attack", 1, "GLA", 5, "", True),
    67: _S("SCIENCE_GPSScrambler", "GPS Scrambler", 1, "GLA", 5, "", True),
    68: _S("Slth_SCIENCE_GPSScrambler", "GPS Scrambler", 1, "GLA", 3, "Slth", True),
    69: _S("SCIENCE_EmergencyRepair1", "Emergency Repair", 1, "", 3, "", True),
    70: _S("SCIENCE_EmergencyRepair2", "Emergency Repair", 2, "", 3, "", True),
    71: _S("SCIENCE_EmergencyRepair3", "Emergency Repair", 3, "", 3, "", True),
    72: _S(
        "Early_SCIENCE_EmergencyRepair1", "Emergency Repair", 1, "", 1, "Early", True
    ),
    73: _S(
        "Early_SCIENCE_EmergencyRepair2", "Emergency Repair", 2, "", 3, "Early", True
    ),
    74: _S(
        "Early_SCIENCE_EmergencyRepair3", "Emergency Repair", 3, "", 3, "Early", True
    ),
    81: _S("SCIENCE_OverlordTraining", "Overlord Training", 1, "China", 1, "", False),
    82: _S(
        "SCIENCE_GattlingTankTraining",
        "Gattling Tank Training",
        1,
        "China",
        1,
        "",
        False,
    ),
    83: _S("SCIENCE_TankParadrop1", "Tank Paradrop", 1, "China", 3, "", True),
    84: _S("SCIENCE_TankParadrop2", "Tank Paradrop", 2, "", 3, "", True),
    85: _S("SCIENCE_TankParadrop3", "Tank Paradrop", 3, "", 3, "", True),
    86: _S(
        "Infa_SCIENCE_RedGuardTraining",
        "Red Guard Training",
        1,
        "China",
        1,
        "Infa",
        False,
    ),
    87: _S("SCIENCE_InfantryParadrop1", "Infantry Paradrop", 1, "China", 3, "", False),
    88: _S("SCIENCE_InfantryParadrop2", "Infantry Paradrop", 2, "", 3, "", False),
    89: _S("SCIENCE_InfantryParadrop3", "Infantry Paradrop", 3, "", 3, "", False),
    90: _S(
        "Infa_SCIENCE_InfantryParadrop1",
        "Infantry Paradrop",
        1,
        "China",
        3,
        "Infa",
        True,
    ),
    91: _S(
        "Infa_SCIENCE_InfantryParadrop2", "Infantry Paradrop", 2, "", 3, "Infa", True
    ),
    92: _S(
        "Infa_SCIENCE_InfantryParadrop3", "Infantry Paradrop", 3, "", 3, "Infa", True
    ),
    93: _S("Nuke_SCIENCE_NukeDrop", "Nuke Drop", 1, "China", 3, "Nuke", True),
    94: _S(
        "AirF_SCIENCE_A10ThunderboltMissileStrike1",
        "A10 Thunderbolt Missile Strike",
        1,
        "America",
        1,
        "AirF",
        True,
    ),
    95: _S(
        "AirF_SCIENCE_A10ThunderboltMissileStrike2",
        "A10 Thunderbolt Missile Strike",
        2,
        "",
        3,
        "AirF",
        True,
    ),
    96: _S(
        "AirF_SCIENCE_A10ThunderboltMissileStrike3",
        "A10 Thunderbolt Missile Strike",
        3,
        "",
        3,
        "AirF",
        True,
    ),
}


def faction_of(faction_string: str) -> str:
    """ "America" / "China" / "GLA" from a replay's `faction` string.

    The replay spells a player's general as `FactionAmericaLaserGeneral` /
    `FactionChina` / `FactionGLAToxinGeneral`; only the country half is a
    science prerequisite.
    """
    rest = faction_string.removeprefix("Faction")
    for country in ("America", "China", "GLA"):
        if rest.startswith(country):
            return country
    return ""


def resolve(science_id: int, faction_string: str) -> Science | None:
    """The science `science_id` names, or None when we can't be sure.

    `faction_string` is the buyer's replay faction. A science whose country
    prerequisite contradicts it is treated as unresolved rather than reported
    under the wrong name - see the module docstring.
    """
    science = SCIENCES.get(science_id)
    if science is None:
        return None
    country = faction_of(faction_string)
    if science.faction and country and science.faction != country:
        return None
    return science


def display_name(science_id: int, faction_string: str) -> str:
    """`resolve`'s name, or a stable placeholder naming the raw id."""
    science = resolve(science_id, faction_string)
    return science.name if science else f"Science #{science_id}"


_POWER_NAME_PREFIXES = ("SpecialAbility", "SpecialPower", "Superweapon")

_FACTION_SUFFIX_RE = re.compile(r"(China|America|GLA)$")

_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def clean_power_name(raw: str) -> str:
    """Strip per-general/faction prefixes and the SpecialPower/Superweapon tag.

    The faction strip runs twice: once in `clean_object_name` to handle a
    leading `China`/`America`/`GLA`, and again after the power-tag strip in
    case removing it exposes a faction prefix (e.g.
    ``Early_SuperweaponChinaCarpetBomb`` -> ``ChinaCarpetBomb`` -> ``CarpetBomb``).
    """
    cleaned = clean_object_name(raw)
    for prefix in _POWER_NAME_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    return FACTION_PREFIX_RE.sub("", cleaned)


def pretty_power_name(raw: str) -> str:
    """`clean_power_name` with the camel case split into words for display.

    Collapsing to the bare power name is deliberate: a general's own spelling
    of a power (``AirF_SuperweaponSpectreGunship``) is the same power as the
    base one to anyone comparing two players' habits, and keeping them apart
    would split one row into several.
    """
    cleaned = clean_power_name(raw)
    # A few powers carry the faction as a *suffix* rather than a prefix
    # (``SuperweaponParadropAmerica``). Dropping it keeps the power's name equal
    # to the science's ("Paradrop"), which is what lets a pick and its
    # activations line up in one row.
    cleaned = _FACTION_SUFFIX_RE.sub("", cleaned)
    return _WORD_BOUNDARY.sub(" ", cleaned) or raw


_GENERAL_BY_FACTION = {
    "FactionAmerica": General.USA,
    "FactionAmericaAirForceGeneral": General.AIR,
    "FactionAmericaLaserGeneral": General.LASER,
    "FactionAmericaSuperWeaponGeneral": General.SUPER,
    "FactionChina": General.CHINA,
    "FactionChinaInfantryGeneral": General.INFANTRY,
    "FactionChinaNukeGeneral": General.NUKE,
    "FactionChinaTankGeneral": General.TANK,
    "FactionGLA": General.GLA,
    "FactionGLADemolitionGeneral": General.DEMO,
    "FactionGLAStealthGeneral": General.STEALTH,
    "FactionGLAToxinGeneral": General.TOXIN,
}


def general_of(faction_string: str) -> General:
    """The `General` a replay's `faction` string names.

    Separate from `utils.side_to_general`, which reads the *summary* `side`
    field ("USA Lazr"); this reads `faction`, which is the only one of the two
    a `PlayerSummaryV2` carries alongside the powers.
    """
    return _GENERAL_BY_FACTION.get(faction_string, General.UNRECOGNIZED)


# The powers that answer "where is he / what is he doing" rather than dealing
# damage. Surfaced as their own rate because scouting cadence is the thing
# people actually compare, and it is split across two names for USA (the Spy
# Drone you drop and the Spy Satellite sweep) and a third for GLA.
RECON_POWERS = frozenset({"Spy Drone", "Spy Satellite", "Radar Van Scan"})
