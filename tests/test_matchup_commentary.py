"""Matchup commentary: prompt assembly, availability gating, provider
dispatch, and the route's error-mapping - no real Anthropic/Gemini API
calls (mocked throughout)."""

from types import SimpleNamespace
from typing import cast

import pytest
from anthropic.types import TextBlock, Usage

from radarvan.api_types import (
    HeadToHeadDetail,
    PlayerProfile,
)
from radarvan.commentary import (
    anthropic_client,
    gemini_client,
    hype_data,
    matchup_commentary,
)
from radarvan.db_utils import ReplayManager
from radarvan.routes import commentary


def _profile(player: str) -> PlayerProfile:
    return PlayerProfile(player=player, games=10, wins=6, losses=4, generals=[])


class _StubReplayManager:
    """Minimal stand-in for the two ReplayManager methods the route calls -
    a cache-miss by default, recording any save_commentary call."""

    def __init__(self, cached: str | None = None) -> None:
        self.cached = cached
        self.saved: tuple[str, str, str, str, str] | None = None

    def get_cached_commentary(
        self, player1: str, player2: str, round_name: str
    ) -> str | None:
        return self.cached

    def save_commentary(
        self,
        player1: str,
        player2: str,
        round_name: str,
        commentary: str,
        provider: str,
    ) -> None:
        self.saved = (player1, player2, round_name, commentary, provider)


def _h2h(player1: str, player2: str) -> HeadToHeadDetail:
    return HeadToHeadDetail(
        player1=player1,
        player2=player2,
        player1_wins=3,
        player2_wins=1,
        games=[],
        player1_by_general=[],
        player2_by_general=[],
        by_map=[],
        teammate_games=2,
        teammate_wins=1,
    )


def test_build_user_message_includes_round_and_players() -> None:
    from radarvan.api_types import PlayerRatings

    ratings_context = hype_data.build_hype_ratings_context(
        [
            PlayerRatings(
                name="Alice", ordinal=20.0, mu=25.0, sigma=1.5, game_count=50
            ),
            PlayerRatings(name="Bob", ordinal=18.0, mu=23.0, sigma=1.7, game_count=40),
        ],
        "Alice",
        "Bob",
    )
    msg = matchup_commentary.build_user_message(
        "Winners Round 1",
        "Alice",
        "Bob",
        hype_data.build_hype_player_data(_profile("Alice")),
        hype_data.build_hype_player_data(_profile("Bob")),
        hype_data.build_hype_head_to_head(_h2h("Alice", "Bob")),
        hype_data.build_hype_head_to_head(_h2h("Alice", "Bob")),
        ratings_context,
    )
    assert "Winners Round 1" in msg
    assert "Alice vs Bob" in msg
    assert '<player1_profile player="Alice">' in msg
    assert '<player2_profile player="Bob">' in msg
    assert "<head_to_head_1v1>" in msg
    assert "<head_to_head_all_formats>" in msg
    assert "Teammate games together: 2" in msg
    assert "<team_game_ratings>" in msg
    assert "INTERNAL CALIBRATION ONLY" in msg
    assert "<- Alice (this matchup)" in msg
    assert "<- Bob (this matchup)" in msg
    # Not a JSON dump - no braces/quotes-as-syntax in the rendered payload.
    assert "{" not in msg


def test_anthropic_commentary_available_reflects_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(anthropic_client.API_KEY_ENV, raising=False)
    assert anthropic_client.commentary_available() is False
    monkeypatch.setenv(anthropic_client.API_KEY_ENV, "sk-ant-test")
    assert anthropic_client.commentary_available() is True


def test_gemini_commentary_available_reflects_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(gemini_client.API_KEY_ENV, raising=False)
    assert gemini_client.commentary_available() is False
    monkeypatch.setenv(gemini_client.API_KEY_ENV, "fake-gemini-key")
    assert gemini_client.commentary_available() is True


def test_commentary_available_dispatches_to_active_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """matchup_commentary.commentary_available() must check whichever
    provider COMMENTARY_PROVIDER selects - default is gemini."""
    monkeypatch.delenv(matchup_commentary.PROVIDER_ENV, raising=False)
    monkeypatch.setattr(gemini_client, "commentary_available", lambda: True)
    monkeypatch.setattr(anthropic_client, "commentary_available", lambda: False)
    assert matchup_commentary.commentary_available() is True

    monkeypatch.setenv(matchup_commentary.PROVIDER_ENV, "anthropic")
    monkeypatch.setattr(anthropic_client, "commentary_available", lambda: False)
    assert matchup_commentary.commentary_available() is False


def test_route_503_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: False)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        commentary.get_matchup_commentary(
            "Alice",
            "Bob",
            "Winners Round 1",
            replay_manager=cast(ReplayManager, _StubReplayManager()),
        )
    assert exc_info.value.status_code == 503


def test_route_200_returns_generated_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: True)
    monkeypatch.setattr(
        matchup_commentary,
        "generate_commentary",
        lambda replay_manager, player1, player2, round_name: "**Hype.**",
    )
    result = commentary.get_matchup_commentary(
        "Alice",
        "Bob",
        "Winners Round 1",
        replay_manager=cast(ReplayManager, _StubReplayManager()),
    )
    assert result.commentary == "**Hype.**"


def test_route_502_on_generation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: True)

    def _boom(
        replay_manager: object, player1: str, player2: str, round_name: str
    ) -> str:
        raise matchup_commentary.CommentaryGenerationError("boom")

    monkeypatch.setattr(matchup_commentary, "generate_commentary", _boom)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        commentary.get_matchup_commentary(
            "Alice",
            "Bob",
            "Winners Round 1",
            replay_manager=cast(ReplayManager, _StubReplayManager()),
        )
    assert exc_info.value.status_code == 502


def test_route_returns_cached_commentary_without_generating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cache hit must skip both the availability check and generation
    entirely - even an unavailable provider shouldn't block a cached read."""
    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: False)

    def _boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("generate_commentary should not be called on a cache hit")

    monkeypatch.setattr(matchup_commentary, "generate_commentary", _boom)
    stub = _StubReplayManager(cached="**Already hyped.**")
    result = commentary.get_matchup_commentary(
        "Alice", "Bob", "Winners Round 1", replay_manager=cast(ReplayManager, stub)
    )
    assert result.commentary == "**Already hyped.**"


def test_route_saves_commentary_after_generating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: True)
    monkeypatch.setattr(
        matchup_commentary,
        "generate_commentary",
        lambda replay_manager, player1, player2, round_name: "**Hype.**",
    )
    monkeypatch.setattr(matchup_commentary, "active_provider", lambda: "gemini")
    stub = _StubReplayManager()
    commentary.get_matchup_commentary(
        "Alice", "Bob", "Winners Round 1", replay_manager=cast(ReplayManager, stub)
    )
    assert stub.saved == ("Alice", "Bob", "Winners Round 1", "**Hype.**", "gemini")


def test_route_400_on_unknown_round_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route is a read-tier GET, so an arbitrary round_name would be an
    unbounded cache key - and every miss on a fresh key is a billed LLM
    call. Only names a real bracket produces are accepted."""

    def _boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("generate_commentary should not be called")

    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: True)
    monkeypatch.setattr(matchup_commentary, "generate_commentary", _boom)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        commentary.get_matchup_commentary(
            "Alice",
            "Bob",
            "Round of whatever I want",
            replay_manager=cast(ReplayManager, _StubReplayManager()),
        )
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("flag", ["bypass_cache", "force_refresh"])
def test_route_403_when_forcing_regeneration_without_write_key(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    """Both regenerate flags bill a fresh LLM call on every request, so a
    read-tier caller must not be able to set them."""

    def _boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("generate_commentary should not be called")

    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: True)
    monkeypatch.setattr(matchup_commentary, "generate_commentary", _boom)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        commentary.get_matchup_commentary(
            "Alice",
            "Bob",
            "Winners Round 1",
            write_access=False,
            replay_manager=cast(ReplayManager, _StubReplayManager(cached="cached")),
            **{flag: True},
        )
    assert exc_info.value.status_code == 403


def test_route_force_refresh_regenerates_with_write_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(matchup_commentary, "commentary_available", lambda: True)
    monkeypatch.setattr(
        matchup_commentary,
        "generate_commentary",
        lambda replay_manager, player1, player2, round_name: "**Fresh.**",
    )
    monkeypatch.setattr(matchup_commentary, "active_provider", lambda: "gemini")
    stub = _StubReplayManager(cached="**Stale.**")
    result = commentary.get_matchup_commentary(
        "Alice",
        "Bob",
        "Winners Round 1",
        force_refresh=True,
        write_access=True,
        replay_manager=cast(ReplayManager, stub),
    )
    assert result.commentary == "**Fresh.**"
    assert stub.saved is not None


def test_known_round_names_covers_every_bracket_round() -> None:
    """The commentary route rejects anything outside this set, so it must
    contain every name the bracket can actually hand the frontend."""
    from radarvan import bracket

    names = bracket.known_round_names()
    assert {
        "Winners Round 1",
        "Winners Round 2",
        "Winners Semifinal",
        "Winners Final",
        "Losers Final",
        "Grand Final",
        "Grand Final Reset",
    } <= names
    for n in range(bracket.MIN_PLAYERS, bracket.MAX_PLAYERS + 1):
        assert {m.round_name for m in bracket.build_topology(n).matches} <= names


def test_generate_with_anthropic_logs_usage_and_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_generate_with_anthropic must read response.usage/duration without
    raising (see the logger.info call) and still return the extracted text."""
    captured_kwargs: dict[str, object] = {}
    final_message = SimpleNamespace(
        content=[TextBlock(type="text", text="**Hype.**")],
        usage=Usage(input_tokens=123, output_tokens=45),
        stop_reason="end_turn",
    )

    class _StubStream:
        def __enter__(self) -> _StubStream:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def get_final_message(self) -> SimpleNamespace:
            return final_message

    class _StubMessages:
        def stream(self, **kwargs: object) -> _StubStream:
            captured_kwargs.update(kwargs)
            return _StubStream()

    class _StubClient:
        messages = _StubMessages()

    monkeypatch.setattr(anthropic_client, "anthropic_client", lambda: _StubClient())

    prompt = matchup_commentary.MatchupPrompt(system="sys", user_message="user")
    text = matchup_commentary._generate_with_anthropic(prompt, "Alice", "Bob")
    assert text == "**Hype.**"
    assert captured_kwargs["system"] == "sys"


def test_generate_with_gemini_logs_usage_and_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_generate_with_gemini must read interaction.usage/duration without
    raising and still return the extracted text."""
    captured_kwargs: dict[str, object] = {}
    stub_interaction = SimpleNamespace(
        output_text="**Hype.**",
        status="completed",
        usage=SimpleNamespace(
            total_input_tokens=123,
            total_output_tokens=45,
            total_thought_tokens=10,
        ),
    )

    class _StubInteractions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured_kwargs.update(kwargs)
            return stub_interaction

    class _StubClient:
        interactions = _StubInteractions()

    monkeypatch.setattr(gemini_client, "gemini_client", lambda: _StubClient())

    prompt = matchup_commentary.MatchupPrompt(system="sys", user_message="user")
    text = matchup_commentary._generate_with_gemini(prompt, "Alice", "Bob")
    assert text == "**Hype.**"
    assert captured_kwargs["system_instruction"] == "sys"
    assert captured_kwargs["input"] == "user"


def test_generate_with_gemini_raises_on_empty_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A budget-exhausted interaction (no output_text) must raise
    CommentaryGenerationError, not silently return an empty string."""
    stub_interaction = SimpleNamespace(
        output_text=None,
        status="budget_exceeded",
        usage=SimpleNamespace(
            total_input_tokens=123, total_output_tokens=16000, total_thought_tokens=16000
        ),
    )

    class _StubInteractions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            return stub_interaction

    class _StubClient:
        interactions = _StubInteractions()

    monkeypatch.setattr(gemini_client, "gemini_client", lambda: _StubClient())

    prompt = matchup_commentary.MatchupPrompt(system="sys", user_message="user")
    with pytest.raises(matchup_commentary.CommentaryGenerationError):
        matchup_commentary._generate_with_gemini(prompt, "Alice", "Bob")


def test_generate_commentary_dispatches_by_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matchup_commentary,
        "build_prompt",
        lambda replay_manager, player1, player2, round_name: matchup_commentary.MatchupPrompt(
            system="sys", user_message="user"
        ),
    )
    monkeypatch.setattr(
        matchup_commentary,
        "_generate_with_anthropic",
        lambda prompt, player1, player2: "anthropic-text",
    )
    monkeypatch.setattr(
        matchup_commentary,
        "_generate_with_gemini",
        lambda prompt, player1, player2: "gemini-text",
    )

    monkeypatch.delenv(matchup_commentary.PROVIDER_ENV, raising=False)
    assert (
        matchup_commentary.generate_commentary(
            cast(ReplayManager, None), "Alice", "Bob", "Winners Round 1"
        )
        == "gemini-text"
    )

    monkeypatch.setenv(matchup_commentary.PROVIDER_ENV, "anthropic")
    assert (
        matchup_commentary.generate_commentary(
            cast(ReplayManager, None), "Alice", "Bob", "Winners Round 1"
        )
        == "anthropic-text"
    )

    monkeypatch.setenv(matchup_commentary.PROVIDER_ENV, "gemini")
    assert (
        matchup_commentary.generate_commentary(
            cast(ReplayManager, None), "Alice", "Bob", "Winners Round 1"
        )
        == "gemini-text"
    )
