"""hype_data: profile/head-to-head -> trimmed Hype* types -> plain-text
render. No network calls - pure data transformation."""

from datetime import UTC, date, datetime

from radarvan.api_types import (
    BracketMatchOutput,
    BracketTournamentOutput,
    FavoriteObject,
    General,
    GeneralProfileStat,
    HeadToHeadDetail,
    HeadToHeadGame,
    HeadToHeadGeneralRecord,
    MatchInfo,
    OpponentProfileStat,
    Player,
    PlayerProfile,
    PlayerProfileComputed,
    ProfileBadge,
    SeedSource,
    Team,
    TeammateProfileStat,
    TournamentTag,
)
from radarvan.player_role import PlayerRole
from radarvan.commentary import hype_data


def _game(date_: date, player1_won: bool) -> HeadToHeadGame:
    return HeadToHeadGame(
        match_id=1,
        timestamp=f"{date_.isoformat()}T00:00:00Z",  # type: ignore[arg-type]
        date=date_,
        map="some map",
        duration_minutes=10.0,
        player1_general=General.GLA,
        player2_general=General.INFANTRY,
        player1_won=player1_won,
        player1_team=["Alice"],
        player2_team=["Bob"],
    )


def _full_profile(player: str) -> PlayerProfile:
    return PlayerProfile(
        player=player,
        games=40,
        wins=25,
        losses=15,
        generals=[
            GeneralProfileStat(general=General.STEALTH, games=17, wins=11, losses=6, win_rate=0.647),
            GeneralProfileStat(general=General.GLA, games=23, wins=10, losses=13, win_rate=0.303),
        ],
        favorite_teammate=TeammateProfileStat(
            name="Carol", games_together=42, wins_together=30, synergy=1.2
        ),
        nemesis=OpponentProfileStat(name="Dave", wins=3, losses=9),
        avg_win_duration_minutes=8.4,
        avg_loss_duration_minutes=11.2,
        computed=PlayerProfileComputed(
            favorite_unit=FavoriteObject(
                name="Vehicle Bomb Truck",
                general=General.STEALTH,
                per_game=0.82,
                peer_per_game=0.03,
                score=27.33,
                games_on_general=17,
                total_count=14,
            ),
            aversions=[
                FavoriteObject(
                    name="Speaker Tower",
                    general=General.CHINA,
                    per_game=0.01,
                    peer_per_game=0.5,
                    score=0.02,
                    games_on_general=5,
                    total_count=1,
                )
            ],
            badges=[
                ProfileBadge(
                    key="first_blood",
                    label="Sharpshooter",
                    description="Draws first blood constantly",
                    value=0.75,
                    rank=1,
                    tier="gold",
                    total_players=45,
                )
            ],
            games_analyzed=40,
            computed_at=date(2026, 1, 1),
        ),
    )


def test_build_hype_player_data_uses_general_names_not_indices() -> None:
    data = hype_data.build_hype_player_data(_full_profile("Gorn"))
    assert data.generals[0].general == "STEALTH"
    assert data.generals[1].general == "GLA"
    assert all(not g.general.isdigit() for g in data.generals)


def test_render_player_data_is_not_json_and_has_key_sections() -> None:
    data = hype_data.build_hype_player_data(_full_profile("Gorn"))
    rendered = hype_data.render_player_data(data)

    # Not a JSON dump.
    assert "{" not in rendered
    assert '"' not in rendered

    assert "Player: Gorn" in rendered
    assert "STEALTH: 17 games, 11 wins (64.7%)" in rendered
    assert "Favorite teammate: Carol (42 games together, 30 wins, synergy 1.20)" in rendered
    assert "Nemesis: Dave (3 wins, 9 losses)" in rendered
    assert "Avg win duration: 8.4 min | Avg loss duration: 11.2 min" in rendered
    assert "Favorite unit: Vehicle Bomb Truck (STEALTH)" in rendered
    assert "score 27.33" in rendered
    assert "Aversions (do not use, see guidelines):" in rendered
    assert "Speaker Tower (CHINA)" in rendered
    assert "[gold] Sharpshooter (rank 1 of 45)" in rendered


def test_render_player_data_omits_absent_optional_fields() -> None:
    profile = PlayerProfile(player="NewPlayer", games=1, wins=1, losses=0, generals=[])
    data = hype_data.build_hype_player_data(profile)
    rendered = hype_data.render_player_data(data)
    assert "Favorite teammate" not in rendered
    assert "Nemesis" not in rendered
    assert "Badges" not in rendered


def test_build_hype_head_to_head_caps_recent_matches_and_maps_winner() -> None:
    games = [_game(date(2026, 1, i), player1_won=(i % 2 == 0)) for i in range(1, 25)]
    h2h = HeadToHeadDetail(
        player1="Alice",
        player2="Bob",
        player1_wins=12,
        player2_wins=12,
        games=games,
        player1_by_general=[HeadToHeadGeneralRecord(general=General.GLA, wins=5, losses=3)],
        player2_by_general=[HeadToHeadGeneralRecord(general=General.INFANTRY, wins=3, losses=5)],
        by_map=[],
        teammate_games=10,
        teammate_wins=6,
    )
    data = hype_data.build_hype_head_to_head(h2h)
    assert len(data.recent_matches) == hype_data.MAX_RECENT_MATCHES == 10
    assert data.recent_matches[0].winner in ("Alice", "Bob")
    # player1_won=True (even day) -> Alice; False -> Bob.
    assert data.recent_matches[0].winner == ("Alice" if games[0].player1_won else "Bob")


def test_render_head_to_head_handles_no_games() -> None:
    h2h = HeadToHeadDetail(
        player1="Alice",
        player2="Bob",
        player1_wins=0,
        player2_wins=0,
        games=[],
        player1_by_general=[],
        player2_by_general=[],
        by_map=[],
        teammate_games=0,
        teammate_wins=0,
    )
    data = hype_data.build_hype_head_to_head(h2h)
    rendered = hype_data.render_head_to_head(data)
    assert "{" not in rendered
    assert "- no games on record" in rendered
    assert "No matches on record." in rendered


# --- Tournament-so-far context ---
#
# The fixtures below mirror the real bracket's format: a randomized general
# draw played both ways on one map ("random reverse for armies"), and a
# same-general mirror when a set is level going into its last game.


def _match(
    match_id: int,
    stage: str,
    series_index: int,
    map_name: str,
    winner: tuple[str, General],
    loser: tuple[str, General],
    minutes: float = 10.0,
) -> MatchInfo:
    winner_name, winner_general = winner
    loser_name, loser_general = loser
    return MatchInfo(
        id=match_id,
        timestamp=datetime(2026, 8, 8, 1, series_index, tzinfo=UTC),
        date=date(2026, 8, 7),
        map=f"userdata/maps/{map_name}",
        winning_team=Team.ONE,
        players=[
            Player(
                name=winner_name,
                general=winner_general,
                team=Team.ONE,
                color="green",
                won=True,
                role=PlayerRole.HUMAN,
            ),
            Player(
                name=loser_name,
                general=loser_general,
                team=Team.TWO,
                color="orange",
                won=False,
                role=PlayerRole.HUMAN,
            ),
        ],
        duration_minutes=minutes,
        filename=f"upload:{match_id}",
        tournament=TournamentTag(
            slug="2026_1v1_bracket",
            stage=stage,
            round_name="Winners Round 1",
            series_index=series_index,
        ),
    )


def _bracket_match(
    match_id: str,
    round_name: str,
    player_a: str,
    player_b: str,
    score_a: int | None = None,
    score_b: int | None = None,
    winner: str | None = None,
    status: str = "completed",
) -> BracketMatchOutput:
    return BracketMatchOutput(
        match_id=match_id,
        bracket="W",
        round_number=1,
        round_name=round_name,
        player_a=player_a,
        player_b=player_b,
        score_a=score_a,
        score_b=score_b,
        winner=winner,
        status=status,  # type: ignore[arg-type]
        source_a=SeedSource(seed=1),
        source_b=SeedSource(seed=2),
    )


def _bracket(
    matches: list[BracketMatchOutput], revealed: bool = True
) -> BracketTournamentOutput:
    return BracketTournamentOutput(
        participant_names=["Gorn", "Neo", "Skip", "Syn"],
        players=[],
        matches=matches,
        bye_advances=[],
        needs_reset=False,
        revealed=revealed,
    )


def test_reverse_pair_swept_when_one_player_wins_both_sides() -> None:
    games = [
        _match(
            1, "WB1-1", 1, "nobugscars", ("Neo", General.DEMO), ("Syn", General.GLA)
        ),
        _match(
            2, "WB1-1", 2, "nobugscars", ("Neo", General.GLA), ("Syn", General.DEMO)
        ),
    ]
    ctx = hype_data.build_hype_tournament_context(
        _bracket(
            [_bracket_match("WB1-1", "Winners Round 1", "Neo", "Syn", 3, 0, "Neo")]
        ),
        games,
        "Neo",
        "Modus",
    )
    (series,) = ctx.run1.series
    (pair,) = series.reverse_pairs
    assert pair.swept_by == "Neo"
    assert (pair.general_a, pair.general_b) == ("DEMO", "GLA")


def test_reverse_pair_split_when_each_takes_one_side() -> None:
    games = [
        _match(
            1, "WB1-2", 1, "vendetta", ("Pancake", General.GLA), ("Skip", General.TOXIN)
        ),
        _match(
            2, "WB1-2", 2, "vendetta", ("Skip", General.GLA), ("Pancake", General.TOXIN)
        ),
    ]
    ctx = hype_data.build_hype_tournament_context(
        _bracket(
            [
                _bracket_match(
                    "WB1-2", "Winners Round 1", "Pancake", "Skip", 3, 2, "Pancake"
                )
            ]
        ),
        games,
        "Pancake",
        "Tytan",
    )
    (pair,) = ctx.run1.series[0].reverse_pairs
    assert pair.swept_by is None


def test_same_general_kept_across_two_games_is_not_a_reverse_pair() -> None:
    # Same map, same draw, but nobody swapped - not the reversed pair the
    # format produces, so it must not be reported as one.
    games = [
        _match(1, "WB1-1", 1, "vendetta", ("Neo", General.GLA), ("Syn", General.TOXIN)),
        _match(2, "WB1-1", 2, "vendetta", ("Neo", General.GLA), ("Syn", General.TOXIN)),
    ]
    ctx = hype_data.build_hype_tournament_context(
        _bracket(
            [_bracket_match("WB1-1", "Winners Round 1", "Neo", "Syn", 3, 0, "Neo")]
        ),
        games,
        "Neo",
        "Modus",
    )
    assert ctx.run1.series[0].reverse_pairs == []


def test_mirror_decider_is_flagged_and_never_paired() -> None:
    games = [
        _match(
            1, "WB1-2", 5, "badlands", ("Pancake", General.NUKE), ("Skip", General.NUKE)
        ),
    ]
    ctx = hype_data.build_hype_tournament_context(
        _bracket(
            [
                _bracket_match(
                    "WB1-2", "Winners Round 1", "Pancake", "Skip", 3, 2, "Pancake"
                )
            ]
        ),
        games,
        "Pancake",
        "Tytan",
    )
    series = ctx.run1.series[0]
    assert series.games[0].is_mirror
    assert series.reverse_pairs == []
    assert "mirror decider" in hype_data.render_tournament_context(ctx)


def test_prior_meeting_is_pulled_out_of_both_runs() -> None:
    bracket = _bracket(
        [
            _bracket_match("WB1-1", "Winners Round 1", "Neo", "Syn", 3, 0, "Neo"),
            _bracket_match("WB2-1", "Winners Round 2", "Modus", "Neo", 3, 0, "Modus"),
        ]
    )
    ctx = hype_data.build_hype_tournament_context(bracket, [], "Modus", "Neo")
    assert [s.stage for s in ctx.prior_meetings] == ["WB2-1"]
    assert ctx.run1.series == []
    assert [s.stage for s in ctx.run2.series] == ["WB1-1"]
    rendered = hype_data.render_tournament_context(ctx)
    assert "have ALREADY met in this tournament" in rendered
    assert rendered.count("Winners Round 2") == 1


def test_unplayed_and_pending_matches_are_excluded() -> None:
    bracket = _bracket(
        [
            _bracket_match(
                "WB2-3", "Winners Round 2", "Tytan", "Pancake", status="ready"
            ),
            _bracket_match(
                "WB3-2", "Winners Semifinal", "Tytan", "Neo", status="pending"
            ),
        ]
    )
    ctx = hype_data.build_hype_tournament_context(bracket, [], "Tytan", "Pancake")
    assert ctx.is_empty
    assert hype_data.render_tournament_context(ctx) == ""


def test_unrevealed_bracket_yields_nothing() -> None:
    bracket = _bracket(
        [_bracket_match("WB1-1", "Winners Round 1", "Neo", "Syn", 3, 0, "Neo")],
        revealed=False,
    )
    ctx = hype_data.build_hype_tournament_context(bracket, [], "Neo", "Modus")
    assert ctx.is_empty


def test_missing_bracket_yields_nothing() -> None:
    ctx = hype_data.build_hype_tournament_context(None, [], "Neo", "Modus")
    assert ctx.is_empty
    assert hype_data.render_tournament_context(ctx) == ""


def test_series_with_no_linked_replays_still_reports_the_score() -> None:
    ctx = hype_data.build_hype_tournament_context(
        _bracket(
            [
                _bracket_match(
                    "LB1-2",
                    "Losers Round 1",
                    "Skip",
                    "OneThree111",
                    0,
                    3,
                    "OneThree111",
                )
            ]
        ),
        [],
        "OneThree111",
        "Tytan",
    )
    rendered = hype_data.render_tournament_context(ctx)
    assert "OneThree111 beat Skip 3-0" in rendered
    assert "individual replays not linked" in rendered


def test_render_is_plain_text_and_names_the_format() -> None:
    games = [
        _match(
            1,
            "WB1-1",
            1,
            "nobugscars",
            ("Neo", General.DEMO),
            ("Syn", General.GLA),
            11.3,
        ),
        _match(
            2,
            "WB1-1",
            2,
            "nobugscars",
            ("Neo", General.GLA),
            ("Syn", General.DEMO),
            18.7,
        ),
    ]
    ctx = hype_data.build_hype_tournament_context(
        _bracket(
            [_bracket_match("WB1-1", "Winners Round 1", "Neo", "Syn", 3, 0, "Neo")]
        ),
        games,
        "Neo",
        "Modus",
    )
    rendered = hype_data.render_tournament_context(ctx)
    assert "{" not in rendered
    assert "Winners Round 1: Neo beat Syn 3-0" in rendered
    assert "g1 on nobugscars: Neo (DEMO) beat Syn (GLA), 11.3 min" in rendered
    assert "Neo won both sides" in rendered
    # The player with no completed sets is stated, not silently absent.
    assert "Modus has not completed a match in this tournament yet." in rendered


def test_aliases_in_replays_resolve_to_bracket_names() -> None:
    # Linked replays carry in-game aliases; the bracket carries canonical
    # names. Without resolution the games would attach to nobody.
    games = [
        _match(
            1, "WB2-2", 1, "canyon", ("Grn", General.CHINA), ("131", General.STEALTH)
        )
    ]
    ctx = hype_data.build_hype_tournament_context(
        _bracket(
            [
                _bracket_match(
                    "WB2-2", "Winners Round 2", "Gorn", "OneThree111", 3, 1, "Gorn"
                )
            ]
        ),
        games,
        "Gorn",
        "Modus",
    )
    game = ctx.run1.series[0].games[0]
    assert (game.winner, game.loser) == ("Gorn", "OneThree111")
