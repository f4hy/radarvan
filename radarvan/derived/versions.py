"""Version tokens - the one vocabulary for "which generation of an input is this?".

A ``Dependency`` answers exactly one question: given a call, what token identifies
the generation of the input it derives from? ``registry.derived`` folds that token
into every cache key, so a stale entry becomes *unreachable* rather than something
somebody has to remember to clear.

Each dependency's token has two halves:

* **an epoch** - a process-local counter bumped by ``invalidate()``. This is what
  makes a ``WinnerOverride`` or a reparse invalidate correctly: both change match
  *content* without moving ``matches.created_at``, so a probe alone would miss them.
* **a probe** - a cheap DB read, refreshed on a short TTL, so a change made by
  something outside this process (a script, a second dyno, a manual SQL edit) still
  surfaces. What it catches depends on what it reads: ``MAPS`` sees any edit to
  ``map_data``, while ``CORPUS`` sees *newly arrived* matches only - an
  out-of-process reparse or override is not visible to it, and is covered by the
  epoch instead, which is why in-process writers must route through
  ``invalidate()``. The TTL here is a poll interval, which is the only kind of TTL
  this design keeps; derivations themselves have none.

Neither half is sufficient alone, which is why the token is the pair.

The durable projections are not managed by the registry, but the two that carry a
version string are listed at the bottom (``DURABLE_VERSIONS``) so one place
enumerates every version token in the system. ``matchup_commentary_cache`` has no
version at all, deliberately - see the note there.
"""

from __future__ import annotations

import functools
import hashlib
import threading
import time
from collections.abc import Callable, Hashable, Sequence
from typing import Any

from ..api_types import MatchInfo
from ..db_utils import ReplayManager

# How long a probe's value is reused before the DB is asked again. Only ever
# delays picking up an *out-of-process* change: anything this process does routes
# through invalidate(), which bumps the epoch and drops the probe immediately.
PROBE_TTL_SECONDS = 60.0

# Distinct from any value a probe can return, so "" (an empty match corpus) is a
# cached answer rather than a cache miss.
_UNPROBED = object()


class Dependency:
    """A named input whose generation can be identified by a token.

    Not a cache. Holds an epoch counter and, optionally, a probe whose result is
    memoized for ``PROBE_TTL_SECONDS``. Thread-safe: probes are read from sync
    endpoints running in uvicorn's threadpool.
    """

    def __init__(
        self,
        name: str,
        probe: Callable[..., Any],
        *,
        probe_param: str | None = None,
        value_param: str | None = None,
        value_revision: Callable[[Any], Hashable] | None = None,
    ) -> None:
        self.name = name
        self._probe = probe
        # probe_param/value_param name (not type) the parameter a call binds this
        # input through - probe_param for a function that reads the input itself
        # (a `replay_manager`), value_param for one handed the input directly (a
        # `list[MatchInfo]`, reduced via `value_revision`). By name so a FastAPI
        # dependency override or test stub isn't rejected by an isinstance check,
        # and so a rename fails at import time rather than on the first request.
        if (value_param is None) != (value_revision is None):
            raise ValueError(
                f"{name}: value_param and value_revision go together - a value "
                f"binding is a parameter plus the function that reduces it"
            )
        self.probe_param = probe_param
        self.value_param = value_param
        self._value_revision = value_revision
        self._lock = threading.Lock()
        self._epoch = 0
        # _UNPROBED rather than None: an empty database makes _corpus_probe return
        # "", and a falsy-or-None check would treat that as "never probed" and
        # re-query on every single derivation call.
        self._probed: Any = _UNPROBED
        self._probed_at = 0.0

    @property
    def epoch(self) -> int:
        with self._lock:
            return self._epoch

    def bump(self) -> int:
        """Mark this input as changed. Returns the new epoch.

        Also drops the memoized probe, so the next token reflects the DB
        immediately rather than up to ``PROBE_TTL_SECONDS`` later.
        """
        with self._lock:
            self._epoch += 1
            # No need to reset _probed_at: probe() only consults it once _probed
            # is something other than _UNPROBED.
            self._probed = _UNPROBED
            return self._epoch

    def probe(self, source: Any = None) -> Any:
        """The current probe value, re-read at most once per ``PROBE_TTL_SECONDS``."""
        now = time.monotonic()
        with self._lock:
            if (
                self._probed is not _UNPROBED
                and now - self._probed_at < PROBE_TTL_SECONDS
            ):
                return self._probed
        # Probing outside the lock: it is a DB round-trip, and holding a global
        # lock across it would serialize every derivation in the process. A race
        # here costs a duplicate query, never a wrong answer - both callers read
        # the same row and store the same value.
        value = self._probe() if self.probe_param is None else self._probe(source)
        with self._lock:
            self._probed = value
            self._probed_at = time.monotonic()
        return value

    # The two token functions below differ only in how the second half is
    # obtained, and WHICH ONE APPLIES IS A PROPERTY OF THE CALL, not of the
    # dependency: CORPUS declares both bindings, and `sorted_deduped_matches`
    # uses the probe while `compute_player_ratings` uses the value. `registry`
    # picks one at decoration time, from the signature. There is deliberately no
    # `token()` that guesses between them - that guess was a bug.

    def token_from_probe(self, source: Any = None) -> tuple[int, Any]:
        """``(epoch, probe)``, for a call that reads this input from the database."""
        return (self.epoch, self.probe(source))

    def token_from_value(self, value: Any) -> tuple[int, Any]:
        """``(epoch, revision(value))``, for a call handed this input directly.

        No probe: the caller already answered the question a probe would ask.
        """
        if self._value_revision is None:
            raise TypeError(f"{self.name} has no value binding to reduce")
        return (self.epoch, self._value_revision(value))

    def __repr__(self) -> str:
        return f"<Dependency {self.name} epoch={self.epoch}>"


def _corpus_probe(replay_manager: ReplayManager) -> str:
    """Latest match creation time, as a string. Moves when a match is registered."""
    ts = replay_manager.latest_match_created_at()
    return ts.isoformat() if ts else ""


def _maps_probe(replay_manager: ReplayManager) -> str:
    """Revision of the map registry: row count plus newest ``updated_at``.

    ``MapData.updated_at`` carries ``onupdate=func.now()``, so this is a real
    revision rather than a timer - re-parsing a map's geometry moves it.
    """
    rev = replay_manager.map_registry_revision()
    return f"{rev.rows}:{rev.updated_at.isoformat() if rev.updated_at else ''}"


@functools.cache
def _model_probe() -> str:
    """Fingerprint of the ONNX ensemble directory: filenames, sizes, mtimes.

    Cached for the life of the process rather than re-globbed on the usual poll:
    the ensemble is loaded once into lru_cached ONNX sessions, so a file changing
    underneath us would not change any answer this process gives. Swapping the
    ensemble means a deploy, and a deploy means a new process. (Measured at
    ~376us per run over a 30-model ensemble - small, but paid for nothing.)

    The import is function-local on purpose. `ml/` puts this repo on PYTHONPATH
    and imports `player_rating`, which reaches this module, so a module-scope
    import of `ml_inference` would drag onnxruntime into the 3.13 training venv.
    """
    from ..ml_inference import ENSEMBLE_DIR

    parts = []
    for path in sorted(ENSEMBLE_DIR.glob("model-*.onnx")):
        try:
            stat = path.stat()
        except OSError:
            continue
        parts.append(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
    # Digested rather than joined: a 30-model ensemble makes a ~2 KB string, and
    # this ends up inside every key of a 256-entry cache.
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


# The matches in the database, and everything that reads like a match: winners,
# rosters, durations, overrides. Bumped by cache.invalidate_match_caches().
def _match_ids(games: Sequence[MatchInfo]) -> frozenset[int]:
    """Revision of a corpus handed over by value: the set of ids in it.

    The ids alone are not a sufficient token, which is why `Dependency.token`
    pairs this with the epoch: a reparse or a `WinnerOverride` changes a match's
    content while leaving its id untouched.
    """
    return frozenset(g.id for g in games)


CORPUS = Dependency(
    "corpus",
    _corpus_probe,
    probe_param="replay_manager",
    value_param="games",
    value_revision=_match_ids,
)

# Stored map geometry (the map_data table). Bumped alongside CORPUS, because the
# same operations that land matches also fetch the maps they were played on.
MAPS = Dependency("maps", _maps_probe, probe_param="replay_manager")

# The ONNX ensemble on disk. Cannot change within a process (the sessions are
# lru_cached), so this exists to keep model-derived results from surviving a
# deploy that swaps the ensemble.
MODEL = Dependency("model", _model_probe)

DEPENDENCIES: tuple[Dependency, ...] = (CORPUS, MAPS, MODEL)


# Version strings owned by the durable projection tables. Listed here so one place
# enumerates every version token in the system, but the registry does not manage
# them: each has its own load/save path with semantics the in-memory decorator does
# not model (bulk loads with a session per thread for details; real API spend for
# commentary). See derived_registry_plan.md section 4.
#
# Both are "<hand-bumped logic version>-<hash of the model's JSON schema>", so a
# schema change invalidates automatically and a derivation-logic change needs the
# constant bumped by hand. tests/test_derived_registry.py asserts these still exist.
DURABLE_VERSIONS: tuple[str, ...] = (
    "match_details.DETAILS_VERSION",
    "player_profile.PROFILE_VERSION",
)

# matchup_commentary_cache is deliberately absent: it has no version column at all.
# Rows are keyed on (player1, player2, round_name) and kept forever, because
# regenerating one is a billed LLM call - a version bump there would silently spend
# money on every cached matchup. Prompt changes are handled by deleting rows by hand.
