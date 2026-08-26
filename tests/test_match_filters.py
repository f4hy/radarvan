"""The Matches page's player/map/format filters (``matches.filter_matches``).

Each of the three is independent and optional. The interesting cases are the
two the page would get subtly wrong on its own: a spectator is not a player of
the match, and an in-game alias is not a different person.
"""

from radarvan.api_types import Team
from radarvan.matches import filter_matches

import corpus


def _games():
    return [
        corpus.match(1, day=5, map_name="maps/defcon6"),
        corpus.match(2, day=6, map_name="maps/tournament island"),
        corpus.match(
            3,
            day=7,
            map_name="maps/defcon6",
            team_one=("Skip",),
            team_two=("Syn",),
            comp=corpus.composition(
                category="1v1",
                team_sizes=[1, 1],
                total_players=2,
                num_humans=2,
            ),
        ),
    ]


def test_no_filters_returns_everything() -> None:
    games = _games()
    assert filter_matches(games) == games


def test_each_filter_narrows_independently() -> None:
    games = _games()
    assert [g.id for g in filter_matches(games, map_name="maps/defcon6")] == [1, 3]
    assert [g.id for g in filter_matches(games, game_format="1v1")] == [3]
    assert [g.id for g in filter_matches(games, player="Pancake")] == [1, 2]


def test_filters_compose() -> None:
    games = _games()
    assert [
        g.id
        for g in filter_matches(games, player="Skip", map_name="maps/defcon6")
    ] == [1, 3]
    assert (
        filter_matches(
            games, player="Pancake", map_name="maps/defcon6", game_format="1v1"
        )
        == []
    )


def test_map_filter_matches_the_stored_string_not_a_display_name() -> None:
    # The picker sends back what /api/map_match_counts gave it, which is the
    # stored path. A basename would silently match nothing.
    games = _games()
    assert filter_matches(games, map_name="defcon6") == []


def test_an_unknown_player_matches_nothing() -> None:
    assert filter_matches(_games(), player="Nobody") == []


def test_a_spectator_is_not_a_player_of_the_match() -> None:
    """Filtering by a name only finds games that name actually played.

    An observer changing an answer about a match is the failure this codebase
    has hit twice (see CLAUDE.md); here it would put a night in someone's
    history because they watched it.
    """
    watched = corpus.match(4, day=8, extra_players=(corpus.observer("Gorn"),))
    played = corpus.match(
        5, day=9, team_one=("Gorn", "CoreDawg"), team_two=corpus.TEAM_TWO
    )
    assert [g.id for g in filter_matches([watched, played], player="Gorn")] == [5]


def test_an_alias_finds_the_player_it_resolves_to() -> None:
    """Clients send in-game aliases; the roster answers in canonical names.

    The route types the query param as ``PlayerName`` so this resolution
    happens at validation - the check here is that the two ends agree once it
    has, which is what makes "Scottagorn" show up under "Gorn".
    """
    from radarvan.player_ids import resolve_player_name

    games = [
        corpus.match(6, day=10, team_one=("Gorn", "CoreDawg"), team_two=corpus.TEAM_TWO)
    ]
    assert filter_matches(games, player=resolve_player_name("scottagorn")) == games


def test_a_filtered_out_match_keeps_its_neighbours_intact() -> None:
    # filter_matches must not mutate its input (CLAUDE.md: never mutate inputs).
    games = _games()
    before = list(games)
    filter_matches(games, player="Skip", game_format="1v1")
    assert games == before


def test_incomplete_and_observer_slots_do_not_affect_the_format_filter() -> None:
    game = corpus.match(
        7,
        day=11,
        winner=Team.ONE,
        extra_players=(corpus.observer("Gorn"),),
    )
    assert filter_matches([game], game_format="2v2") == [game]
