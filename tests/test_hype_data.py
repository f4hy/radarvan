"""hype_data: profile/head-to-head -> trimmed Hype* types -> plain-text
render. No network calls - pure data transformation."""

from datetime import date

from radarvan.api_types import (
    FavoriteObject,
    General,
    GeneralProfileStat,
    HeadToHeadDetail,
    HeadToHeadGame,
    HeadToHeadGeneralRecord,
    OpponentProfileStat,
    PlayerProfile,
    PlayerProfileComputed,
    ProfileBadge,
    TeammateProfileStat,
)
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
