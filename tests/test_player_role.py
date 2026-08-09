"""Role classification (``radarvan.player_role``) and the ``MatchRoster``
partitioning built on it.

The replay header is authoritative: ``type`` is "C" for every AI slot and a
spectator is a type-"H" slot with playerTemplate -2. Both facts used to be
dropped on the way into the DB and re-guessed from the player's name, which
misclassified AI slots named outside a hard-coded five-entry list.
"""

from types import SimpleNamespace

import pytest

from radarvan.api_types import General, Player, Team
from radarvan.cncstats_model.header import Player as HeaderPlayer
from radarvan.game_composition import MatchRoster, RosterSlot
from radarvan.player_role import (
    PlayerRole,
    resolve_role,
    role_from_header,
    role_from_name,
)


def _header(
    name: str, player_template: str, ptype: str = "H", team: str = "-1"
) -> HeaderPlayer:
    return HeaderPlayer.model_construct(
        name=name, team=team, type=ptype, player_template=player_template
    )


def _db_player(
    name: str,
    team: int = 1,
    general: int = 3,
    color: str = "red",
    role: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        player_name=name,
        color=color,
        team_id=team,
        general_id=general,
        is_winner=False,
        role=role,
        starting_position=None,
    )


class TestRoleFromHeader:
    def test_human(self) -> None:
        assert role_from_header(_header("Syn", "2")) == PlayerRole.HUMAN

    def test_cpu_is_read_from_type_not_name(self) -> None:
        # The AI slot in match 258514171: header name is empty, type is "C",
        # and the display name ("Tactical AI") only exists in `summary`. The
        # name is therefore useless for classification; the type is not.
        assert role_from_header(_header("", "10", ptype="C")) == PlayerRole.CPU

    def test_spectator_beats_the_human_type(self) -> None:
        # Spectators arrive as type "H"; only playerTemplate distinguishes them.
        assert role_from_header(_header("Watcher", "-2")) == PlayerRole.OBSERVER

    def test_unknown_slot_type_is_an_observer(self) -> None:
        assert role_from_header(_header("Slot", "2", ptype="X")) == PlayerRole.OBSERVER


class TestRoleFallback:
    def test_stored_role_wins_over_the_name_guess(self) -> None:
        # "Skip" is a human name, but a recorded CPU role must not be second-
        # guessed - the header knew better than the name ever can.
        assert resolve_role(PlayerRole.CPU, "Skip") == PlayerRole.CPU

    def test_falls_back_to_the_name_when_unset(self) -> None:
        assert resolve_role(None, "Tactical AI") == PlayerRole.CPU
        assert resolve_role(None, "Skip") == PlayerRole.HUMAN

    @pytest.mark.parametrize("name", ["Tactical AI", "TacticalAI", "EasyArmy", "CPU"])
    def test_known_ai_names_guess_cpu(self, name: str) -> None:
        # These are exactly the names the old five-entry _CPU_NAMES list missed.
        assert role_from_name(name) == PlayerRole.CPU

    def test_observer_flag_overrides_the_name(self) -> None:
        assert role_from_name("Skip", is_observer=True) == PlayerRole.OBSERVER


class TestMatchRoster:
    def test_partitions_observers_out_of_competitors(self) -> None:
        roster = MatchRoster(
            [
                RosterSlot("Watcher", "-1", -1, -1, PlayerRole.OBSERVER),
                RosterSlot("Syn", "grey", 1, 0, PlayerRole.HUMAN),
                RosterSlot("Neo", "orange", 2, 5, PlayerRole.HUMAN),
            ]
        )
        assert [s.name for s in roster.observers] == ["Watcher"]
        assert [s.name for s in roster.competitors] == ["Syn", "Neo"]
        assert len(roster.slots) == 3

    def test_teamless_competitors_are_not_observers(self) -> None:
        # The distinction the old `team > 0` checks collapsed: a 1v1 that never
        # went through reassign_1v1_teams has two teamless *competitors*.
        roster = MatchRoster(
            [
                RosterSlot("Syn", "grey", 0, 0, PlayerRole.HUMAN),
                RosterSlot("Neo", "orange", 0, 5, PlayerRole.HUMAN),
            ]
        )
        assert len(roster.competitors) == 2
        assert roster.observers == ()
        assert roster.participants == ()

    def test_humans_and_cpus_split(self) -> None:
        roster = MatchRoster(
            [
                RosterSlot("Skip", "red", 1, 3, PlayerRole.HUMAN),
                RosterSlot("Tactical AI", "-1", 2, 5, PlayerRole.CPU),
                RosterSlot("Watcher", "-1", -1, -1, PlayerRole.OBSERVER),
            ]
        )
        assert [s.name for s in roster.humans] == ["Skip"]
        assert [s.name for s in roster.cpus] == ["Tactical AI"]

    def test_from_db_players_uses_stored_role(self) -> None:
        roster = MatchRoster.from_db_players(
            [
                _db_player("Skip", team=1, role=PlayerRole.HUMAN),
                # Recorded as a CPU despite a name no heuristic would catch.
                _db_player("Mystery Bot", team=2, role=PlayerRole.CPU),
            ]
        )
        assert [s.name for s in roster.cpus] == ["Mystery Bot"]

    def test_from_db_players_guesses_when_role_is_null(self) -> None:
        # Un-backfilled rows: the name is all we have.
        roster = MatchRoster.from_db_players(
            [
                _db_player("Skip", team=1, role=None),
                _db_player("Tactical AI", team=2, role=None),
            ]
        )
        assert [s.name for s in roster.cpus] == ["Tactical AI"]

    def test_from_players_reads_api_player_shape(self) -> None:
        roster = MatchRoster.from_players(
            [
                Player(
                    name="Watcher",
                    general=General.UNRECOGNIZED,
                    team=Team.OBSERVER,
                    color="-1",
                    role=PlayerRole.OBSERVER,
                ),
                Player(
                    name="Syn",
                    general=General.USA,
                    team=Team.TWO,
                    color="grey",
                    role=PlayerRole.HUMAN,
                ),
            ]
        )
        assert [s.name for s in roster.observers] == ["Watcher"]
        assert [s.name for s in roster.humans] == ["Syn"]


class TestRosterComposition:
    def test_ai_slot_is_counted_as_a_computer(self) -> None:
        # Match 258514171: five humans and one AI in a 3v3. The old name-based
        # detector read "Tactical AI" as a human and reported numComputers 0.
        roster = MatchRoster.from_db_players(
            [
                _db_player("Mod", team=1, role=PlayerRole.HUMAN),
                _db_player("131", team=1, role=PlayerRole.HUMAN),
                _db_player("Tactical AI", team=1, role=PlayerRole.CPU),
                _db_player("Tytan", team=2, role=PlayerRole.HUMAN),
                _db_player("Pancake", team=2, role=PlayerRole.HUMAN),
                _db_player("Wld", team=2, role=PlayerRole.HUMAN),
            ]
        )
        comp = roster.composition()
        assert comp.category == "3v3"
        assert comp.num_computers == 1
        assert comp.num_humans == 5
        assert comp.is_comp_stomp is False

    def test_observers_count_toward_total_but_not_humans(self) -> None:
        roster = MatchRoster.from_db_players(
            [
                _db_player("Watcher", team=-1, general=-1, role=PlayerRole.OBSERVER),
                _db_player("Syn", team=1, role=PlayerRole.HUMAN),
                _db_player("Neo", team=2, role=PlayerRole.HUMAN),
            ]
        )
        comp = roster.composition()
        assert comp.category == "1v1"
        assert comp.total_players == 3
        assert comp.num_humans == 2
        assert comp.num_computers == 0

    def test_comp_stomp_still_detected(self) -> None:
        roster = MatchRoster.from_db_players(
            [
                _db_player("Skip", team=1, role=PlayerRole.HUMAN),
                _db_player("Neo", team=1, role=PlayerRole.HUMAN),
                _db_player("HardArmy", team=2, role=PlayerRole.CPU),
                _db_player("EasyArmy", team=2, role=PlayerRole.CPU),
            ]
        )
        comp = roster.composition()
        assert comp.category == "2v2"
        assert comp.is_comp_stomp is True
