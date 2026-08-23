"""Ordering guarantees in the /api/upload_replay handler.

A replay under two minutes is not a match. Every read path already agrees
(get_match_infos lists with a 2.0 minute floor), but the handler used to
register the match first and validate afterwards, which left short games
reachable through /api/details while invisible in /api/matches/by_date.
"""

from io import BytesIO
from typing import Any

import pytest
from fastapi import HTTPException

from radarvan import matches, replay_files
from radarvan.replay_files import ParsedReplayResult
from radarvan.routes import files as files_route


class _FakeUpload:
    """Stand-in for fastapi's UploadFile: the handler only reads .file."""

    def __init__(self, data: bytes) -> None:
        self.file = BytesIO(data)


class _FakeReplayManager:
    """Records the writes the handler attempts."""

    def __init__(self) -> None:
        self.registered: list[Any] = []
        self.compositions: list[int] = []

    def get_replay_by_hash(self, file_hash: str) -> None:
        return None

    def register_match(self, db_match: Any) -> tuple[Any, bool]:
        self.registered.append(db_match)
        return db_match, True

    def compute_and_save_composition(self, match_id: int) -> None:
        self.compositions.append(match_id)


class _StubMatch:
    match_id = 4242


@pytest.fixture
def wiring(monkeypatch: pytest.MonkeyPatch) -> _FakeReplayManager:
    """Stub out S3/parse/cache so only the handler's ordering is under test."""
    manager = _FakeReplayManager()
    parsed = ParsedReplayResult(replay=object(), json_path="s3://bucket/x.json")

    monkeypatch.setattr(replay_files, "compute_hash", lambda data: "deadbeef")
    monkeypatch.setattr(replay_files, "upload_and_parse", lambda *a, **k: parsed)
    monkeypatch.setattr(replay_files, "is_dev_build", lambda build: False)
    monkeypatch.setattr(matches, "replay_to_db_match", lambda *a, **k: _StubMatch())
    monkeypatch.setattr(files_route, "invalidate_match_caches", lambda: None)
    return manager


def test_short_replay_registers_nothing(
    wiring: _FakeReplayManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(matches, "match_from_replay", lambda replay: None)

    with pytest.raises(HTTPException) as raised:
        files_route.upload_replay(file=_FakeUpload(b"rep"), replay_manager=wiring)

    assert raised.value.status_code == 422
    # The whole point: a rejected upload leaves no match behind.
    assert wiring.registered == []
    assert wiring.compositions == []


def test_normal_replay_still_registers(
    wiring: _FakeReplayManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = object()
    monkeypatch.setattr(matches, "match_from_replay", lambda replay: sentinel)
    monkeypatch.setattr(
        files_route.ml_inference, "predict_and_notify", lambda info: None
    )

    result = files_route.upload_replay(file=_FakeUpload(b"rep"), replay_manager=wiring)

    assert result is sentinel
    assert len(wiring.registered) == 1
    assert wiring.compositions == [_StubMatch.match_id]
