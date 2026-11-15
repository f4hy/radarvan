from datetime import UTC, datetime

from test_netstats import SEED, _log, _zip

from radarvan import netstats_sync
from radarvan.netstats import PARSER_VERSION
from radarvan.repositories.netstats import NO_LOGS, OK, PARSE_ERROR


class _Repo:
    def __init__(self, to_fetch: list[int], stale: tuple[int, ...] = ()) -> None:
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

    def attempts(self, match_id):
        return self.rows[match_id][3] if match_id in self.rows else 0

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
    repo, store = _Repo([SEED, 7]), _Store()
    result = netstats_sync.sync_netstats(repo, _Client({SEED: GOOD}), store, NOW)

    status, version, summary, attempts = repo.rows[SEED]
    assert (status, version, attempts) == (OK, PARSER_VERSION, 1)
    assert [s.name for s in summary.roster] == ["Ann", "Bob"]
    assert store.objects[netstats_sync.netstats_s3_uri(SEED)] == GOOD
    assert repo.rows[7][0] == NO_LOGS
    assert (result.fetched, result.no_logs) == (1, 1)


def test_s3_copy_is_used_once_cncstats_no_longer_has_the_logs():
    store = _Store({netstats_sync.netstats_s3_uri(SEED): GOOD})
    repo = _Repo([], stale=(SEED,))
    repo.rows[SEED] = (OK, PARSER_VERSION - 1, None, 8)
    result = netstats_sync.sync_netstats(repo, _Client({}), store, NOW)

    assert repo.rows[SEED][:2] == (OK, PARSER_VERSION)
    assert repo.rows[SEED][3] == 8
    assert result.rederived == 1


def test_unparseable_logs_are_marked_not_raised():
    repo = _Repo([SEED])
    netstats_sync.sync_netstats(repo, _Client({SEED: b"not a zip"}), _Store(), NOW)
    assert repo.rows[SEED][0] == PARSE_ERROR
