"""Map-positioned replay-playback events (`MatchDetails.map_events`).

Exercises `match_details_from_replay` against the real cncstats fixture
`references/example_cncstats_output.json` when present; skipped otherwise.
"""

import json
from pathlib import Path

import pytest

from radarvan.api_types import MapEventOutput
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.match_details import match_details_from_replay

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "example_cncstats_output.json"
)

_skip_no_fixture = pytest.mark.skipif(
    not _FIXTURE.exists(),
    reason=f"replay fixture not available: {_FIXTURE}",
)


@pytest.fixture(scope="module")
def replay() -> EnhancedReplayV2:
    with _FIXTURE.open() as f:
        return EnhancedReplayV2.model_validate(json.load(f))


@_skip_no_fixture
def test_map_events_shape_and_ordering(replay: EnhancedReplayV2) -> None:
    details = match_details_from_replay(replay)
    assert details is not None
    events = details.map_events

    assert len(events) > 0
    assert all(isinstance(e, MapEventOutput) for e in events)
    # Sorted ascending by time so the front-end can stream them as the clock runs.
    times = [e.at_minute for e in events]
    assert times == sorted(times)

    names = {p.name for p in replay.summary}
    for e in events:
        assert e.kind in {"build", "capture"}
        assert e.player_name in names  # owner resolved from a real player index
        assert isinstance(e.name, str) and e.name
        assert isinstance(e.x, float) and isinstance(e.y, float)


@_skip_no_fixture
def test_map_events_only_structures_for_builds(replay: EnhancedReplayV2) -> None:
    details = match_details_from_replay(replay)
    assert details is not None
    builds = [e for e in details.map_events if e.kind == "build"]
    captures = [e for e in details.map_events if e.kind == "capture"]

    assert builds, "expected structure build events"
    assert captures, "expected capture events"
    # Builds are limited to structures: there are far more unit builds than
    # structures in the raw stream, so the count must match the structure subset.
    assert replay.stats is not None
    structure_builds = sum(
        1 for b in replay.stats.build_events if b.object_type == "structure"
    )
    assert len(builds) == structure_builds

    # Cleaned object names: no leading faction / variant prefix survives.
    assert any(b.name == "PowerPlant" for b in builds)
    assert all(not b.name.startswith(("America", "China", "GLA")) for b in builds)
