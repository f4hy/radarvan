"""Persisted tournament-game membership: the link repo and the detector.

The alias cases are the point of these tests. Bracket slots hold canonical
names while replays hold in-game aliases, and the frontend's old date+name
guess compared the two directly - so `Grn` never matched `Gorn` and a whole
bracket round showed "no games found".
"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan import tournament, tournament_membership
from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.db import (
    BracketMatchState,
    BracketPlayer,
    BracketTournament,
    Tournament,
    TournamentGame,
)
from radarvan.game_composition import GameComposition
from radarvan.player_role import PlayerRole
from radarvan.repositories.tournaments import TournamentRepo
from radarvan.tournament_membership import BracketStage


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    Tournament.__table__.create(engine)
    TournamentGame.__table__.create(engine)
    with Session(engine) as s:
        yield s


def _repo(session: Session) -> TournamentRepo:
    return TournamentRepo(session, auto_commit=False)


def _tournament(session: Session, slug: str = "test_cup") -> Tournament:
    return _repo(session).upsert_tournament(
        slug=slug, name="Test Cup", tournament_format=tournament_membership.DOUBLE_ELIM
    )


def _comp(category: str = "1v1", **overrides: object) -> GameComposition:
    base: dict[str, object] = {
        "category": category,
        "is_comp_stomp": False,
        "is_ffa": False,
        "num_teams": 2,
        "team_sizes": [1, 1],
        "total_players": 2,
        "num_humans": 2,
        "num_computers": 0,
        "is_balanced": True,
        "is_1v1": category == "1v1",
        "is_team_game": True,
    }
    base.update(overrides)
    return GameComposition(**base)  # type: ignore[arg-type]


def _player(
    name: str,
    team: Team,
    *,
    color: str = "red",
    general: General = General.USA,
    role: PlayerRole = PlayerRole.HUMAN,
    won: bool = False,
) -> Player:
    return Player(
        name=name, general=general, team=team, color=color, won=won, role=role
    )


def _match(
    match_id: int,
    players: list[Player],
    *,
    when: datetime = datetime(2026, 8, 9, 5, 47, 44),
    night: date = date(2026, 8, 8),
    comp: GameComposition | None = None,
    incomplete: str = "",
) -> MatchInfo:
    return MatchInfo(
        id=match_id,
        timestamp=when,
        date=night,
        map="some_map",
        winning_team=Team.ONE,
        players=players,
        duration_minutes=10.0,
        filename=f"game_{match_id}.rep",
        incomplete=incomplete,
        composition=comp if comp is not None else _comp(),
    )


def _1v1(match_id: int, a: str, b: str, **kwargs: object) -> MatchInfo:
    return _match(
        match_id,
        [_player(a, Team.ONE, won=True), _player(b, Team.TWO, color="blue")],
        **kwargs,  # type: ignore[arg-type]
    )


# --- repo ---


def test_link_and_unlink_round_trip(session: Session) -> None:
    repo = _repo(session)
    t = _tournament(session)

    repo.link_match(t.id, 1931734, stage="WB2-2", round_name="Winners Round 2")
    assert list(repo.links_by_match()) == [1931734]

    assert repo.unlink_match(t.id, 1931734) is True
    assert repo.links_by_match() == {}
    assert repo.unlink_match(t.id, 1931734) is False


def test_relinking_updates_in_place(session: Session) -> None:
    """The unique index is per (tournament, match) - a second link is an update."""
    repo = _repo(session)
    t = _tournament(session)

    repo.link_match(t.id, 42, stage="WB1-1", series_index=1)
    repo.link_match(t.id, 42, stage="WB1-1", series_index=2)

    links = repo.list_links(t.id)
    assert len(links) == 1
    assert links[0].series_index == 2


def test_auto_never_overwrites_manual(session: Session) -> None:
    """An admin's correction must survive every later detector run."""
    repo = _repo(session)
    t = _tournament(session)

    repo.link_match(t.id, 42, stage="LB1-1", source="manual")
    repo.link_match(t.id, 42, stage="WB9-9", source="auto")

    link = repo.list_links(t.id)[0]
    assert link.source == "manual"
    assert link.stage == "LB1-1"


def test_manual_may_overwrite_auto(session: Session) -> None:
    repo = _repo(session)
    t = _tournament(session)

    repo.link_match(t.id, 42, stage="WB9-9", source="auto")
    repo.link_match(t.id, 42, stage="LB1-1", source="manual")

    link = repo.list_links(t.id)[0]
    assert link.source == "manual"
    assert link.stage == "LB1-1"


def test_invalid_source_rejected(session: Session) -> None:
    repo = _repo(session)
    t = _tournament(session)
    with pytest.raises(ValueError):
        repo.link_match(t.id, 42, source="guessed")


def test_upsert_tournament_keeps_id_and_links(session: Session) -> None:
    """Correcting a tournament's metadata must not orphan its games."""
    repo = _repo(session)
    t = _repo(session).upsert_tournament(
        slug="cup", name="Cup", tournament_format=tournament_membership.DOUBLE_ELIM
    )
    repo.link_match(t.id, 7)

    again = repo.upsert_tournament(
        slug="cup", name="Renamed Cup", tournament_format=tournament_membership.DOUBLE_ELIM
    )
    assert again.id == t.id
    assert again.name == "Renamed Cup"
    assert list(repo.links_by_match()) == [7]


def test_excluded_match_is_not_a_link(session: Session) -> None:
    """A tombstone is not a game - it's the record that one doesn't count."""
    repo = _repo(session)
    t = _tournament(session)

    repo.link_match(t.id, 437356734)
    repo.exclude_match(t.id, 437356734)

    assert repo.links_by_match() == {}
    assert repo.list_links(t.id) == []
    assert [link.match_id for link in repo.list_links(t.id, include_excluded=True)] == [
        437356734
    ]


def test_exclusion_survives_the_detector(session: Session) -> None:
    """Unlinking wouldn't hold - the next auto run would re-add the match."""
    repo = _repo(session)
    t = _tournament(session)

    repo.exclude_match(t.id, 437356734)
    repo.link_match(t.id, 437356734, source="auto")

    assert repo.links_by_match() == {}


def test_admin_can_reinstate_an_excluded_match(session: Session) -> None:
    repo = _repo(session)
    t = _tournament(session)

    repo.exclude_match(t.id, 437356734)
    repo.link_match(t.id, 437356734, source="manual")

    assert list(repo.links_by_match()) == [437356734]


def test_list_links_filters_by_stage(session: Session) -> None:
    repo = _repo(session)
    t = _tournament(session)
    repo.link_match(t.id, 1, stage="WB2-2")
    repo.link_match(t.id, 2, stage="WB2-2")
    repo.link_match(t.id, 3, stage="LB1-1")

    assert {link.match_id for link in repo.list_links(t.id, stage="WB2-2")} == {1, 2}


def test_links_survive_a_bracket_reset(session: Session) -> None:
    """The reason links hang off Tournament and not BracketTournament.

    Creating/resetting a bracket deletes the BracketTournament row and
    cascades its players, match states and predictions away. The record that
    those games were played must not go with it.
    """
    BracketTournament.__table__.create(session.get_bind())
    BracketPlayer.__table__.create(session.get_bind())
    # The delete below cascades through every child relationship.
    BracketMatchState.__table__.create(session.get_bind())

    repo = _repo(session)
    t = _tournament(session)
    repo.link_match(t.id, 1931734, stage="WB2-2")

    old_bracket = BracketTournament(tournament_id=t.id)
    old_bracket.players = [BracketPlayer(seed=1, player_name="Gorn")]
    session.add(old_bracket)
    session.flush()

    # What BracketRepo.create does before inserting the replacement.
    session.delete(old_bracket)
    session.flush()

    assert session.get(Tournament, t.id) is not None
    assert [link.match_id for link in repo.list_links(t.id)] == [1931734]


# --- detector: bracket ---


_WB2_2 = BracketStage(
    stage="WB2-2",
    round_name="Winners Round 2",
    player_a="Gorn",
    player_b="OneThree111",
    # 9:30pm Eastern on the 8th, which is already the 9th in UTC.
    scheduled_at=datetime(2026, 8, 9, 1, 30),
)


def test_aliases_resolve_to_bracket_names() -> None:
    """The regression: `Grn`/`131` in the replay are `Gorn`/`OneThree111`."""
    match = _1v1(1931734, "Grn", "131")
    links = tournament_membership.detect_bracket_links("cup", [_WB2_2], [match])

    assert len(links) == 1
    assert links[0].match_id == 1931734
    assert links[0].stage == "WB2-2"
    assert links[0].round_name == "Winners Round 2"
    assert links[0].series_index == 1


def test_observer_does_not_make_a_game_count() -> None:
    """A bracket entrant spectating someone else's 1v1 isn't playing it."""
    match = _match(
        555,
        [
            _player("Gorn.v.131", Team.OBSERVER, role=PlayerRole.OBSERVER, general=-1),
            _player("Grn", Team.ONE, won=True),
            _player("Neo", Team.TWO, color="blue"),
        ],
    )
    assert tournament_membership.detect_bracket_links("cup", [_WB2_2], [match]) == []


def test_observing_entrant_alongside_the_real_pair_still_links() -> None:
    """Match 1931734's actual shape: the two players plus an observer slot."""
    match = _match(
        1931734,
        [
            _player("Gorn.v.131", Team.OBSERVER, role=PlayerRole.OBSERVER, general=-1),
            _player("131", Team.ONE, won=True),
            _player("Grn", Team.TWO, color="blue"),
        ],
    )
    links = tournament_membership.detect_bracket_links("cup", [_WB2_2], [match])
    assert [link.match_id for link in links] == [1931734]


def test_series_index_orders_by_time() -> None:
    matches = [
        _1v1(3445000, "Grn", "131", when=datetime(2026, 8, 9, 6, 10, 48)),
        _1v1(1376000, "Grn", "131", when=datetime(2026, 8, 9, 5, 37, 5)),
        _1v1(4070187, "Grn", "131", when=datetime(2026, 8, 9, 6, 20, 11)),
        _1v1(1931734, "Grn", "131", when=datetime(2026, 8, 9, 5, 47, 44)),
    ]
    links = tournament_membership.detect_bracket_links("cup", [_WB2_2], matches)

    assert [(link.match_id, link.series_index) for link in links] == [
        (1376000, 1),
        (1931734, 2),
        (3445000, 3),
        (4070187, 4),
    ]


def test_other_night_is_not_linked() -> None:
    match = _1v1(99, "Grn", "131", night=date(2026, 8, 1))
    assert tournament_membership.detect_bracket_links("cup", [_WB2_2], [match]) == []


def test_wrong_pairing_is_not_linked() -> None:
    match = _1v1(99, "Grn", "Neo")
    assert tournament_membership.detect_bracket_links("cup", [_WB2_2], [match]) == []


def test_team_game_is_not_linked() -> None:
    """Both entrants in the same 2v2 that night is not a bracket game."""
    match = _match(
        99,
        [
            _player("Grn", Team.ONE, won=True),
            _player("Neo", Team.ONE, won=True),
            _player("131", Team.TWO, color="blue"),
            _player("Syn", Team.TWO, color="green"),
        ],
        comp=_comp("2v2", team_sizes=[2, 2], total_players=4, num_humans=4),
    )
    assert tournament_membership.detect_bracket_links("cup", [_WB2_2], [match]) == []


def test_incomplete_game_is_not_linked() -> None:
    match = _1v1(99, "Grn", "131", incomplete="Too Short")
    assert tournament_membership.detect_bracket_links("cup", [_WB2_2], [match]) == []


_DUPLICATE_STAGE = BracketStage(
    stage="LB1-1",
    round_name="Losers Round 1",
    player_a="Gorn",
    player_b="OneThree111",
    scheduled_at=datetime(2026, 8, 9, 1, 30),
)


def test_match_is_claimed_by_only_one_stage() -> None:
    match = _1v1(1931734, "Grn", "131")
    links = tournament_membership.detect_bracket_links(
        "cup", [_WB2_2, _DUPLICATE_STAGE], [match]
    )
    assert [link.stage for link in links] == ["WB2-2"]


def test_series_index_is_contiguous_per_stage() -> None:
    """Whatever a stage keeps is numbered 1..n with no gaps.

    Two stages sharing a night and a pairing see the *same* candidate list
    (candidates are keyed on exactly those two things), so the first claims
    all of them and the second proposes nothing - the numbering can't be left
    with a hole. The generator in `detect_bracket_links` numbers what survives
    rather than what was found, so that stays true if the keying ever widens.
    """
    first = _1v1(1, "Grn", "131", when=datetime(2026, 8, 9, 5, 0))
    second = _1v1(2, "Grn", "131", when=datetime(2026, 8, 9, 6, 0))
    links = tournament_membership.detect_bracket_links(
        "cup", [_WB2_2, _DUPLICATE_STAGE], [first, second]
    )

    by_stage: dict[str | None, list[int | None]] = {}
    for link in links:
        by_stage.setdefault(link.stage, []).append(link.series_index)
    assert by_stage == {"WB2-2": [1, 2]}


def test_exclusion_keeps_round_and_series(session: Session) -> None:
    """The admin view has to be able to say where an excluded game was."""
    repo = _repo(session)
    t = _tournament(session)
    repo.link_match(
        t.id, 42, stage="WB2-2", round_name="Winners Round 2", series_index=3
    )

    repo.exclude_match(t.id, 42)

    tombstone = repo.list_links(t.id, include_excluded=True)[0]
    assert tombstone.excluded is True
    assert tombstone.stage == "WB2-2"
    assert tombstone.round_name == "Winners Round 2"
    assert tombstone.series_index == 3


# --- detector: round robin ---


def _2v2(match_id: int, team_one: list[str], team_two: list[str], **kw: object) -> MatchInfo:
    players = [_player(n, Team.ONE, won=True) for n in team_one]
    players += [_player(n, Team.TWO, color="blue") for n in team_two]
    return _match(
        match_id,
        players,
        comp=_comp("2v2", team_sizes=[2, 2], total_players=4, num_humans=4),
        **kw,  # type: ignore[arg-type]
    )


def test_round_robin_detection_matches_the_existing_rule() -> None:
    """The persisted links must be exactly what the old filter decided."""
    inside = _2v2(
        1,
        ["Syn", "WildCard"],
        ["OneThree111", "Pancake"],
        when=datetime(2025, 12, 1, 20, 0),
        night=date(2025, 12, 1),
    )
    # Same teams, but after the tournament's end_date.
    outside = _2v2(
        2,
        ["Syn", "WildCard"],
        ["OneThree111", "Pancake"],
        when=datetime(2026, 6, 1, 20, 0),
        night=date(2026, 6, 1),
    )
    matches = [inside, outside]

    links = tournament_membership.detect_round_robin_links(matches)
    expected = {m.id for m in matches if tournament.is_tournament_game(m)}

    assert {link.match_id for link in links} == expected == {1}
    assert links[0].tournament_slug == "2025_2v2_tournament"
    assert links[0].stage is None
