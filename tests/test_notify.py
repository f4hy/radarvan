import httpx2
import pytest

from radarvan import notify


class _RecordingClient:
    def __init__(self, status: int) -> None:
        self.status = status
        self.sent: list[dict[str, str]] = []

    def post(self, url: str, json: dict[str, str]) -> httpx2.Response:
        self.sent.append(json)
        return httpx2.Response(self.status, request=httpx2.Request("POST", url))


def test_notify_truncates_to_discord_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _RecordingClient(204)
    monkeypatch.setattr(notify, "WEB_HOOK", "https://example.invalid/hook")
    monkeypatch.setattr(notify, "client", lambda: fake)
    notify.notify("x" * 5000)
    assert len(fake.sent[0]["content"]) == notify.DISCORD_CONTENT_LIMIT
    assert fake.sent[0]["content"].endswith("…")


def test_notify_leaves_short_message_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _RecordingClient(204)
    monkeypatch.setattr(notify, "WEB_HOOK", "https://example.invalid/hook")
    monkeypatch.setattr(notify, "client", lambda: fake)
    notify.notify("hello")
    assert fake.sent == [{"content": "hello"}]


def test_notify_swallows_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _RecordingClient(400)
    monkeypatch.setattr(notify, "WEB_HOOK", "https://example.invalid/hook")
    monkeypatch.setattr(notify, "client", lambda: fake)
    notify.notify("hello")
    assert len(fake.sent) == 1
