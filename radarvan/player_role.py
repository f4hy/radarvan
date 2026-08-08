"""What kind of slot a player occupies: human, CPU, or observer.

This is deliberately a leaf module (it imports only ``player_ids`` and the
generated header model, neither of which import anything internal) so that
every layer can share one definition: ``db`` persists it, ``game_composition``
partitions on it, ``api_types`` puts it on the wire, and ``utils`` derives it
from the replay header.

The replay header is the authority. ``header.metadata.players[*].type`` is
"C" for every AI slot, and a spectator is a type-"H" slot with
``playerTemplate`` -2. Both facts were previously discarded on the way into
the DB and then re-guessed from the player's *name* against a hard-coded
list, which is why AI slots named outside that list (Tactical AI, EasyArmy,
MediumArmy - 417 matches) were counted as humans.
"""

from enum import IntEnum

from .cncstats_model.header import Player as HeaderPlayer
from .player_ids import is_cpu_name

# SAGE marks a spectator slot with playerTemplate -2 (the summary side is
# "Observer", and utils.cncstats_faction_to_general maps -2 to UNRECOGNIZED).
OBSERVER_PLAYER_TEMPLATE = "-2"


class PlayerRole(IntEnum):
    """The kind of slot a player occupied.

    HUMAN and CPU are both *competitors* - they play the game and belong to a
    team. OBSERVER covers spectators and any slot the header doesn't report as
    human or computer (empty/disconnected slots).
    """

    HUMAN = 0
    CPU = 1
    OBSERVER = 2


def role_from_header(player_header: HeaderPlayer) -> PlayerRole:
    """Classify a raw replay-header slot.

    Order matters: spectators come through with type "H" like everyone else
    and are only distinguishable by playerTemplate, so the observer test has
    to run before the human one.
    """
    if player_header.type not in ("H", "C"):
        return PlayerRole.OBSERVER
    if player_header.player_template.strip() == OBSERVER_PLAYER_TEMPLATE:
        return PlayerRole.OBSERVER
    if player_header.type == "C":
        return PlayerRole.CPU
    return PlayerRole.HUMAN


def resolve_role(
    role: int | None, name: str, color: str = "", is_observer: bool = False
) -> PlayerRole:
    """The recorded role if there is one, else a name-based guess.

    The single place the "un-backfilled row" fallback is applied - both
    ``api_types.Player`` and ``game_composition.MatchRoster`` go through here
    so they can't drift apart.
    """
    if role is not None:
        return PlayerRole(role)
    return role_from_name(name, color, is_observer=is_observer)


def role_from_name(name: str, color: str = "", is_observer: bool = False) -> PlayerRole:
    """Best-effort role for a slot whose header classification wasn't recorded.

    The fallback for ``match_players`` rows written before the ``role`` column
    existed. Weaker than ``role_from_header`` - it can only recognize AI slots
    whose (resolved) name is a known CPU name - so it must never be used when
    a stored role is available.
    """
    if is_observer:
        return PlayerRole.OBSERVER
    if is_cpu_name(name, color):
        return PlayerRole.CPU
    return PlayerRole.HUMAN
