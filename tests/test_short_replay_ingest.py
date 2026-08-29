"""A replay under the duration floor must never leave a match row behind.

Both ingest paths - `POST /api/upload_replay` and the gentool scrape's
`register_matches` - used to build the match, register it, compute its
composition, and only *then* ask whether the replay was long enough. The row was
already committed by that point (`register_match` commits on its own, so the
request-scoped rollback never sees it), which left short games half-present:
present in `matches`, absent from every listing, and counted by anything
reconciling this database against cncstats.

Four things are pinned here:

1. **One floor.** Registration and listing agree at the boundary. They used to
   disagree: `match_from_replay` rejected `< 2` while `list_matches` filtered
   `> 2.0`, so a replay of exactly 2.0 minutes registered a row that no listing
   would ever show.
2. **Declining writes nothing.** No match row, no composition.
3. **Declining is remembered.** The ReplayFile goes SKIPPED, so the scrape does
   not re-read and re-validate that JSON from S3 on every run forever.
4. **The ratchet.** A source scan asserting `register_match` is called from
   exactly one place, so a third ingest path cannot reintroduce the bug by
   forgetting a check. Point 4 is why the first three stay true.
"""

import ast
import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan import matches, utils
from radarvan.api_types import MatchInfo
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.db import (
    Match,
    MatchPlayer,
    ParsedReplayJson,
    ProcessingStatus,
    ReplayFile,
)
from radarvan.utils import MIN_MATCH_MINUTES
from radarvan.repositories.matches import RegisteredMatch
from radarvan.repositories.replays import ReplayRepo

TESTS_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = TESTS_DIR.parent / "radarvan"

JSON_URI = "s3://generals-stats/radarvan/dev/uploads/deadbeef.json"


@pytest.fixture(scope="module")
def base_replay() -> EnhancedReplayV2:
    data = json.loads((TESTS_DIR / "new_cncstats_output.json").read_text())
    return EnhancedReplayV2.model_validate(data)


def replay_lasting(base: EnhancedReplayV2, minutes: float) -> EnhancedReplayV2:
    """A copy of `base` whose header says the game ran for `minutes`."""
    replay = base.model_copy(deep=True)
    header = replay.header
    assert header is not None
    header.time_stamp_end = (header.time_stamp_begin or 0) + round(minutes * 60)
    return replay


class FakeReplayManager:
    """Records every write `register_parsed_replay` attempts."""

    def __init__(self) -> None:
        self.registered: list[Any] = []
        self.compositions: list[int] = []
        self.marked_not_a_match: list[str] = []

    def register_match(self, db_match: Any) -> RegisteredMatch:
        self.registered.append(db_match)
        return RegisteredMatch(match=db_match, created=True)

    def compute_and_save_composition(self, match_id: int) -> None:
        self.compositions.append(match_id)

    def mark_not_a_match(self, json_s3_uri: str) -> bool:
        self.marked_not_a_match.append(json_s3_uri)
        return True


# --- 1. One floor -----------------------------------------------------------


def listing_would_show(minutes: float) -> bool:
    """`MatchRepo.list_matches`' predicate, which every match listing goes through."""
    return minutes > MIN_MATCH_MINUTES


@pytest.mark.parametrize(
    "minutes",
    [0.0, 0.5, 1.0, 1.9, 1.99, MIN_MATCH_MINUTES, 2.01, 2.5, 10.0, 45.0],
)
def test_nothing_registers_that_a_listing_would_hide(
    base_replay: EnhancedReplayV2, minutes: float
) -> None:
    """The registration floor and the listing floor are the same floor.

    Asserted as an equivalence rather than against fixed expected values, so it
    keeps holding if MIN_MATCH_MINUTES ever moves.
    """
    replay = replay_lasting(base_replay, minutes)
    shown = listing_would_show(minutes)
    assert (matches.match_from_replay(replay) is not None) is shown
    # The predicate itself, at the boundary the old spellings disagreed about.
    assert utils.is_long_enough(replay) is shown


def test_too_short_is_the_incomplete_reason(base_replay: EnhancedReplayV2) -> None:
    """`incomplete_reason` reads the same floor, not its own copy of the number."""
    assert matches.is_incomplete(replay_lasting(base_replay, 1.0)) == "Too Short"
    assert matches.is_incomplete(replay_lasting(base_replay, 10.0)) != "Too Short"


# --- 2 & 3. Declining writes nothing, and is remembered ----------------------


def test_short_replay_writes_no_match_row(base_replay: EnhancedReplayV2) -> None:
    manager = FakeReplayManager()

    outcome = matches.register_parsed_replay(
        replay_lasting(base_replay, 0.5), JSON_URI, manager
    )

    assert outcome.match_info is None
    assert outcome.created is False
    # The whole point: a declined replay leaves no match behind.
    assert manager.registered == []
    assert manager.compositions == []
    # And the decline is remembered, or the scrape re-reads that JSON forever.
    assert manager.marked_not_a_match == [JSON_URI]


def test_long_replay_registers(base_replay: EnhancedReplayV2) -> None:
    manager = FakeReplayManager()

    outcome = matches.register_parsed_replay(
        replay_lasting(base_replay, 12.0), JSON_URI, manager
    )

    assert isinstance(outcome.match_info, MatchInfo)
    assert outcome.created is True
    assert len(manager.registered) == 1
    assert manager.compositions == [outcome.match_info.id]
    assert manager.registered[0].json_s3_uri == JSON_URI
    # A real match is not marked as "we looked and it isn't one".
    assert manager.marked_not_a_match == []


# --- 3 (continued). What "remembered" means in the database ------------------


@pytest.fixture
def replay_repo() -> ReplayRepo:
    """A ReplayRepo over the three tables the scrape queue touches.

    SQLite, like `test_match_repo_race`, so this runs in CI. It cannot hold
    `match_compostion` or `match_details_cache` (ARRAY and JSONB are
    Postgres-only).
    """
    engine = create_engine("sqlite://")
    for model in (ReplayFile, ParsedReplayJson, Match, MatchPlayer):
        model.__table__.create(engine)
    return ReplayRepo(Session(engine), auto_commit=True)


def add_parsed_replay(repo: ReplayRepo, url: str, json_uri: str, match_id: int) -> None:
    repo.session.add(
        ReplayFile(
            original_url=url,
            s3_uri=f"s3://bucket/{match_id}.rep",
            status=ProcessingStatus.PARSED,
            player_id="someone",
            source_date=date(2026, 8, 21),
        )
    )
    repo.session.add(
        ParsedReplayJson(
            json_s3_uri=json_uri,
            match_id=match_id,
            replay_file_url=url,
            game_timestamp=datetime(2026, 8, 21, tzinfo=UTC),
        )
    )
    repo.session.commit()


def test_a_parsed_replay_with_no_match_is_queued_for_registration(
    replay_repo: ReplayRepo,
) -> None:
    add_parsed_replay(replay_repo, "upload:aaa", "s3://bucket/aaa.json", match_id=1)

    queued = replay_repo.list_jsons_awaiting_registration()

    assert [j.match_id for j in queued] == [1]


def test_declined_replay_leaves_the_registration_queue(
    replay_repo: ReplayRepo,
) -> None:
    """The reason `mark_not_a_match` exists.

    `list_jsons_awaiting_registration` selects parsed JSONs that have no match row, and
    a declined replay never gets one - so without a terminal marker the scrape
    would re-read and re-validate its JSON from S3 on every run, forever, for a
    set that only grows.
    """
    add_parsed_replay(replay_repo, "upload:aaa", "s3://bucket/aaa.json", match_id=1)

    assert replay_repo.mark_not_a_match("s3://bucket/aaa.json") is True

    assert replay_repo.list_jsons_awaiting_registration() == []
    replay_file = replay_repo.get_replay_file("upload:aaa")
    assert replay_file is not None
    assert replay_file.status is ProcessingStatus.SKIPPED


def test_declining_one_replay_does_not_dequeue_the_others(
    replay_repo: ReplayRepo,
) -> None:
    add_parsed_replay(replay_repo, "upload:aaa", "s3://bucket/aaa.json", match_id=1)
    add_parsed_replay(replay_repo, "upload:bbb", "s3://bucket/bbb.json", match_id=2)

    replay_repo.mark_not_a_match("s3://bucket/aaa.json")

    assert [j.match_id for j in replay_repo.list_jsons_awaiting_registration()] == [2]


def test_marking_an_unknown_json_is_a_no_op(replay_repo: ReplayRepo) -> None:
    assert replay_repo.mark_not_a_match("s3://bucket/nope.json") is False


# --- The scrape loop's bookkeeping ------------------------------------------


class FakeQueuedJson:
    """Stand-in for a ParsedReplayJson row in the scrape's registration queue.

    `replay_file` is always present: it is a non-null FK, and the queue query
    inner-joins it to filter on status.
    """

    def __init__(self, match_id: int, tag: str) -> None:
        self.match_id = match_id
        self.json_s3_uri = f"s3://bucket/{tag}.json"
        self.replay_file_url = f"upload:{tag}"
        self.replay_file = SimpleNamespace(is_dev=False)


class FakeScrapeManager(FakeReplayManager):
    def __init__(self, queue: list[FakeQueuedJson]) -> None:
        super().__init__()
        self.queue = queue

    def list_jsons_awaiting_registration(self) -> list[FakeQueuedJson]:
        return self.queue


@pytest.fixture
def scraped(
    base_replay: EnhancedReplayV2, monkeypatch: pytest.MonkeyPatch
) -> dict[str, EnhancedReplayV2]:
    """Map each queued replay's URL to the replay `parse_replay` should return."""
    by_url: dict[str, EnhancedReplayV2] = {}
    monkeypatch.setattr(
        matches.replay_files, "parse_replay", lambda url, manager: by_url[url]
    )
    return by_url


def test_scrape_declines_short_replays_without_registering(
    base_replay: EnhancedReplayV2, scraped: dict[str, EnhancedReplayV2]
) -> None:
    queue = [FakeQueuedJson(1, "short"), FakeQueuedJson(2, "real")]
    scraped["upload:short"] = replay_lasting(base_replay, 0.5)
    scraped["upload:real"] = replay_lasting(base_replay, 12.0)
    manager = FakeScrapeManager(queue)

    outcome = matches.register_matches(manager)

    assert outcome.registered == 1
    assert len(manager.registered) == 1
    assert manager.marked_not_a_match == ["s3://bucket/short.json"]


def test_every_copy_of_a_declined_game_gets_marked(
    base_replay: EnhancedReplayV2, scraped: dict[str, EnhancedReplayV2]
) -> None:
    """Both players upload the same game and gentool has a copy too.

    Each is its own ParsedReplayJson row, and each needs its own SKIPPED mark:
    marking one and skipping the rest by match_id would leave the others in the
    queue, re-read from S3 on every scrape.
    """
    queue = [FakeQueuedJson(7, "copy-a"), FakeQueuedJson(7, "copy-b")]
    for job in queue:
        scraped[job.replay_file_url] = replay_lasting(base_replay, 0.5)
    manager = FakeScrapeManager(queue)

    matches.register_matches(manager)

    assert manager.marked_not_a_match == [
        "s3://bucket/copy-a.json",
        "s3://bucket/copy-b.json",
    ]


def test_a_registered_game_is_only_registered_once(
    base_replay: EnhancedReplayV2, scraped: dict[str, EnhancedReplayV2]
) -> None:
    """The other half of that: a real game's second copy must not re-register."""
    queue = [FakeQueuedJson(7, "copy-a"), FakeQueuedJson(7, "copy-b")]
    for job in queue:
        scraped[job.replay_file_url] = replay_lasting(base_replay, 12.0)
    manager = FakeScrapeManager(queue)

    assert matches.register_matches(manager).registered == 1
    assert len(manager.registered) == 1


def test_declines_consume_the_work_budget(
    base_replay: EnhancedReplayV2, scraped: dict[str, EnhancedReplayV2]
) -> None:
    """`max_to_update` bounds S3 reads, not just rows written.

    Counting only registrations would let a capped ops call walk an unbounded
    queue of short replays, reading and validating every one.
    """
    queue = [FakeQueuedJson(i, f"short-{i}") for i in range(10)]
    for job in queue:
        scraped[job.replay_file_url] = replay_lasting(base_replay, 0.5)
    manager = FakeScrapeManager(queue)

    assert matches.register_matches(manager, max_to_update=3).registered == 0
    assert len(manager.marked_not_a_match) == 3


# --- 4. The ratchet ---------------------------------------------------------


def register_match_call_sites() -> list[str]:
    """Every module containing a `<something>.register_match(...)` call.

    One pass over each file: nesting a walk per function would attribute a call
    inside a closure to both enclosing defs, and miss one outside any def.
    """
    return sorted(
        {
            str(path.relative_to(PACKAGE_ROOT))
            for path in PACKAGE_ROOT.rglob("*.py")
            for node in ast.walk(ast.parse(path.read_text(), filename=str(path)))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "register_match"
        }
    )


def test_only_one_place_creates_a_match_from_a_replay() -> None:
    """A new ingest path has to go through the floor, not around it.

    `register_parsed_replay` is the single writer, so adding a caller cannot
    reintroduce register-then-validate the way upload and the scrape each had
    it. If this fails because you added a legitimate second writer, move the
    duration decision with it rather than widening the list.
    """
    assert register_match_call_sites() == ["matches.py"]
