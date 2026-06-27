"""Per-player-count vote/veto limits and mutual exclusivity."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan.db import MapVote, User
from radarvan.repositories.votes import (
    VETO_LIMIT,
    VOTE_LIMIT,
    MapVoteRepo,
    VoteLimitExceeded,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    MapVote.__table__.create(engine)
    with Session(engine) as s:
        user = User(discord_id="u1", discord_username="u1")
        s.add(user)
        s.flush()
        yield s


def _repo(session: Session) -> MapVoteRepo:
    return MapVoteRepo(session, auto_commit=False)


def test_vote_limit_enforced(session: Session) -> None:
    repo = _repo(session)
    for i in range(VOTE_LIMIT):
        repo.set_choice(1, 4, f"map{i}", "vote")
    assert len(repo.get_choices(1, 4)) == VOTE_LIMIT
    with pytest.raises(VoteLimitExceeded):
        repo.set_choice(1, 4, "one_too_many", "vote")


def test_veto_limit_enforced(session: Session) -> None:
    repo = _repo(session)
    for i in range(VETO_LIMIT):
        repo.set_choice(1, 4, f"map{i}", "veto")
    with pytest.raises(VoteLimitExceeded):
        repo.set_choice(1, 4, "one_too_many", "veto")


def test_vote_and_veto_are_mutually_exclusive(session: Session) -> None:
    repo = _repo(session)
    repo.set_choice(1, 4, "tournament_desert", "vote")
    # Switching to veto replaces the vote (does not create a second row).
    choices = repo.set_choice(1, 4, "tournament_desert", "veto")
    assert choices == {"tournament_desert": "veto"}
    rows = session.query(MapVote).filter_by(map_name="tournament_desert").all()
    assert len(rows) == 1


def test_clearing_removes_the_pick(session: Session) -> None:
    repo = _repo(session)
    repo.set_choice(1, 4, "map", "vote")
    assert repo.set_choice(1, 4, "map", None) == {}


def test_limits_are_per_player_count(session: Session) -> None:
    repo = _repo(session)
    for i in range(VOTE_LIMIT):
        repo.set_choice(1, 2, f"map{i}", "vote")
    # A different player count has its own independent allowance.
    repo.set_choice(1, 4, "other_map", "vote")
    assert repo.get_choices(1, 4) == {"other_map": "vote"}


def test_tally_filters_to_given_users(session: Session) -> None:
    # Two users vote for different maps at the same player count.
    other = User(discord_id="u2", discord_username="u2")
    session.add(other)
    session.flush()
    repo = _repo(session)
    repo.set_choice(1, 4, "alpha", "vote")  # user 1
    repo.set_choice(other.id, 4, "beta", "vote")  # user 2

    assert repo.tally(4) == {"alpha": (1, 0), "beta": (1, 0)}
    # Restricting to user 1 drops user 2's vote.
    assert repo.tally(4, user_ids=[1]) == {"alpha": (1, 0)}
    # An empty participant set yields nothing.
    assert repo.tally(4, user_ids=[]) == {}


def test_played_map_without_mapdata_appears_by_observed_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from radarvan.routes import votes

    # A map with games but no MapData geometry still shows, grouped by the
    # real-player count observed in its games.
    monkeypatch.setattr(
        votes,
        "_match_map_index",
        lambda rm: {"k": votes._MapAgg("coastline wold", game_count=3, counts={4})},
    )
    monkeypatch.setattr(votes, "maps_by_player_count", lambda rm: {})

    page4 = votes._build_page(4, object(), None, None)  # type: ignore[arg-type]
    assert [o.map_name for o in page4.maps] == ["coastline wold"]
    # Not a 2-player map (only ever played 4-player).
    assert votes._build_page(2, object(), None, None).maps == []  # type: ignore[arg-type]


def test_mapdata_overlay_adds_capacity_and_canonical_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from radarvan.routes import votes

    # MapData with no games contributes capacity 8 and a canonical name.
    monkeypatch.setattr(votes, "_match_map_index", lambda rm: {})
    monkeypatch.setattr(votes, "maps_by_player_count", lambda rm: {8: ["Big Map"]})

    page = votes._build_page(8, object(), None, None)  # type: ignore[arg-type]
    assert [o.map_name for o in page.maps] == ["Big Map"]
    assert page.maps[0].game_count == 0


def test_choose_map_request_resolves_aliases_at_validation() -> None:
    from radarvan.api_types import ChooseMapRequest

    # The PlayerName annotated type resolves each name when the model is built.
    req = ChooseMapRequest(players=["skp", "wild", "Skip"])
    assert req.players == ["Skip", "WildCard", "Skip"]


def test_choose_map_resolves_player_aliases(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from radarvan.api_types import ChooseMapRequest
    from radarvan.repositories import UserRepo
    from radarvan.routes import votes as votes_module
    from radarvan.routes.votes import choose_map

    user = session.get(User, 1)
    assert user is not None
    user.player_name = "Skip"
    session.flush()
    vote_repo = _repo(session)
    vote_repo.set_choice(1, 4, "tournament_desert", "vote")
    user_repo = UserRepo(session, auto_commit=False)

    # Recency needs match history; this test is about alias resolution, so stub it.
    monkeypatch.setattr(votes_module, "_recently_played_maps", lambda rm: set())

    # The chosen map has no stored geometry/CRC here; stub the CRC lookup.
    class _NoCrc:
        def get_map_crc(self, name: str) -> None:
            return None

    rm = _NoCrc()

    # "skp" is an alias of "Skip" (PLAYER_NAME_MAPPING) and must resolve to it.
    result = choose_map(4, ChooseMapRequest(players=["skp"]), rm, vote_repo, user_repo)  # type: ignore[arg-type]
    assert result.chosen_map == "tournament_desert"
    assert result.chosen_map_crc is None

    # An unknown name resolves to itself, matches no account -> no eligible maps.
    empty = choose_map(4, ChooseMapRequest(players=["nobody"]), rm, vote_repo, user_repo)  # type: ignore[arg-type]
    assert empty.chosen_map is None


def test_resetting_same_choice_is_idempotent(session: Session) -> None:
    repo = _repo(session)
    repo.set_choice(1, 4, "map", "vote")
    # Re-voting the same map must not count against the limit again.
    assert repo.set_choice(1, 4, "map", "vote") == {"map": "vote"}
