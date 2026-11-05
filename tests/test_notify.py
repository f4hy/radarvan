import threading

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


def _drain() -> None:
    notify._executor.submit(lambda: None).result(timeout=5)


def test_notify_truncates_to_discord_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _RecordingClient(204)
    monkeypatch.setattr(notify, "WEB_HOOK", "https://example.invalid/hook")
    monkeypatch.setattr(notify, "client", lambda: fake)
    notify.notify("x" * 5000)
    _drain()
    assert len(fake.sent[0]["content"]) == notify.DISCORD_CONTENT_LIMIT
    assert fake.sent[0]["content"].endswith("…")


def test_notify_leaves_short_message_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _RecordingClient(204)
    monkeypatch.setattr(notify, "WEB_HOOK", "https://example.invalid/hook")
    monkeypatch.setattr(notify, "client", lambda: fake)
    notify.notify("hello")
    _drain()
    assert fake.sent == [{"content": "hello"}]


def test_notify_swallows_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _RecordingClient(400)
    monkeypatch.setattr(notify, "WEB_HOOK", "https://example.invalid/hook")
    monkeypatch.setattr(notify, "client", lambda: fake)
    notify.notify("hello")
    _drain()
    assert len(fake.sent) == 1


def test_notify_does_not_wait_for_the_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()
    fake = _RecordingClient(204)

    def slow_client() -> _RecordingClient:
        release.wait(timeout=5)
        return fake

    monkeypatch.setattr(notify, "WEB_HOOK", "https://example.invalid/hook")
    monkeypatch.setattr(notify, "client", slow_client)
    notify.notify("hello")
    assert fake.sent == []
    release.set()
    _drain()
    assert fake.sent == [{"content": "hello"}]
