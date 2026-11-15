from datetime import UTC, datetime

from test_netstats import SEED, _log, _zip

from radarvan import netstats_sync
from radarvan.db import NetstatsStatus
from radarvan.netstats import PARSER_VERSION
from radarvan.repositories.netstats import NetstatsWork


class _Repo:
    def __init__(
        self, to_fetch: list[NetstatsWork], stale: tuple[NetstatsWork, ...] = ()
    ) -> None:
        self.to_fetch = to_fetch
        self.stale = list(stale)
        self.rows: dict[int, tuple] = {}
        self.session = self

    def rollback(self) -> None:
        pass

    def matches_to_fetch(self, since, max_attempts, limit):
        return self.to_fetch

    def stale_rows(self, parser_version, limit):
        return self.stale

    def save(self, match_id, status, parser_version, summary, attempts):
        self.rows[match_id] = (status, parser_version, summary, attempts)


class _Client:
    def __init__(self, logs: dict[int, bytes]) -> None:
        self.logs = logs

    def get_logs_zip(self, seed: int) -> bytes | None:
        return self.logs.get(seed)


class _Store:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = objects or {}

    def write_bytes(self, uri: str, data: bytes) -> None:
        self.objects[uri] = data

    def read_bytes(self, uri: str) -> bytes:
        if uri not in self.objects:
            raise FileNotFoundError(uri)
        return self.objects[uri]


GOOD = _zip({"Ann/ReleaseLog.txt.gz": _log(0, SEED, peers="0:1/1", stall_on=1)})
NOW = datetime(2026, 11, 15, tzinfo=UTC)


def test_found_logs_are_stored_and_copied_to_s3():
    repo, store = _Repo([NetstatsWork(SEED, 0), NetstatsWork(7, 2)]), _Store()
    result = netstats_sync.sync_netstats(repo, _Client({SEED: GOOD}), store, NOW)

    status, version, summary, attempts = repo.rows[SEED]
    # Bob uploaded nothing yet, so the match stays due for another fetch.
    assert (status, version, attempts) == (NetstatsStatus.OK, PARSER_VERSION, 1)
    assert [s.name for s in summary.roster] == ["Ann", "Bob"]
    assert store.objects[netstats_sync.netstats_s3_uri(SEED)] == GOOD
    assert repo.rows[7][0] == NetstatsStatus.NO_LOGS and repo.rows[7][3] == 3
    assert result == {"ok": 1, "no_logs": 1}


def test_fetching_stops_once_every_player_has_uploaded():
    both = _zip(
        {
            "Ann/ReleaseLog.txt.gz": _log(0, SEED, peers="0:1/1", stall_on=1),
            "Bob/ReleaseLog.txt.gz": _log(1, SEED, peers="", stall_on=0),
        }
    )
    repo = _Repo([NetstatsWork(SEED, 0)])
    netstats_sync.sync_netstats(repo, _Client({SEED: both}), _Store(), NOW)
    assert repo.rows[SEED][3] == netstats_sync.MAX_ATTEMPTS


def test_rederive_reads_the_s3_copy_without_refetching():
    store = _Store({netstats_sync.netstats_s3_uri(SEED): GOOD})
    repo = _Repo([], stale=(NetstatsWork(SEED, 5),))
    result = netstats_sync.sync_netstats(repo, _Client({}), store, NOW)

    assert repo.rows[SEED][:2] == (NetstatsStatus.OK, PARSER_VERSION)
    assert repo.rows[SEED][3] == 5
    assert result["rederived"] == 1


def test_rederive_with_nothing_archived_keeps_the_old_row():
    repo = _Repo([], stale=(NetstatsWork(SEED, 5),))
    netstats_sync.sync_netstats(repo, _Client({SEED: GOOD}), _Store(), NOW)
    assert SEED not in repo.rows


def test_unparseable_logs_are_marked_not_raised():
    repo = _Repo([NetstatsWork(SEED, 0)])
    netstats_sync.sync_netstats(repo, _Client({SEED: b"not a zip"}), _Store(), NOW)
    assert repo.rows[SEED][0] == NetstatsStatus.PARSE_ERROR
