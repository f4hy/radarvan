"""The derived-value registry, and the rule that nothing may sidestep it.

Four things are pinned here:

1. **Shape** - every registered derivation is bounded, locked, and versioned.
   These are properties the decorator supplies, so this is really a test that
   nobody has bypassed the decorator while still landing in the registry.
2. **Invalidation** - bumping a dependency's epoch makes derivations over it
   recompute, and *not* bumping it makes them not recompute. Asserted as a
   property with a call counter rather than against a fixed expected value.
3. **Content-change staleness** - a derivation that takes the corpus by value
   re-derives when match *contents* change but the ids do not. This is the
   reparse/override bug the epoch exists to close; see
   `derived_registry_plan.md` section 2(a).
4. **The ratchet** - a source scan asserting no module outside `radarvan/derived`
   builds a bare cachetools cache, except for a short allow-list where each entry
   carries a reason. This is what makes the seventeenth cache correct by
   construction instead of correct if reviewed carefully.

Point 4 is the reason the other three are worth writing down.
"""

import ast
import itertools
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from radarvan import derived
from radarvan.derived import CORPUS, MAPS, MODEL, versions
from radarvan.derived.registry import Derivation

from corpus import CORPUS as MATCH_CORPUS
from corpus import match

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "radarvan"

# threading.Lock is a factory, not a class, so the type has to come from an instance.
_LOCK_TYPE = type(threading.Lock())


# --------------------------------------------------------------------------
# 1. shape
# --------------------------------------------------------------------------


def _registered() -> list[Derivation]:
    # Importing the app pulls in every module that declares a derivation. Without
    # this the registry reflects only whatever this test file happened to import.
    import radarvan.main  # noqa: F401

    return list(derived.REGISTRY)


def test_registry_is_populated() -> None:
    assert _registered(), (
        "no derivations registered - either radarvan.main stopped importing the "
        "modules that declare them, or @derived is no longer being used"
    )


def test_every_derivation_is_bounded_locked_and_versioned() -> None:
    registry = "\n  ".join(derived.describe())
    for d in _registered():
        assert d.maxsize >= 1, f"{d.qualified_name} declares maxsize={d.maxsize}"
        assert isinstance(d.lock, _LOCK_TYPE), (
            f"{d.qualified_name} carries {d.lock!r} instead of a lock, so "
            f"concurrent access from uvicorn's threadpool is unguarded"
        )
        assert d.dependency in versions.DEPENDENCIES, (
            f"{d.qualified_name} depends on {d.dependency!r}, which is not one of "
            f"the declared dependencies {[x.name for x in versions.DEPENDENCIES]}"
            f"\n  {registry}"
        )


def test_derivation_names_are_unique() -> None:
    names = [d.qualified_name for d in _registered()]
    assert len(names) == len(set(names)), f"duplicate derivations: {sorted(names)}"


def test_maxsize_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="maxsize must be at least 1"):

        @derived.derived(on=CORPUS, maxsize=0)
        def _unbounded() -> int:
            return 0


def test_key_is_every_parameter_the_dependency_does_not_bind() -> None:
    """The per-call key is read off the signature, so it cannot be forgotten.

    A derivation that omitted a hand-written `key=` used to serve its first
    result for every argument - wrong answers, not stale ones. Nothing is
    declared now, so this pins the derivation rule instead.
    """
    by_name = {d.qualified_name: d for d in _registered()}

    details = by_name["radarvan.cache.details_from_id"]
    assert [p.name for p in details.key_params] == ["match_id"], (
        "details_from_id must key on match_id; `replay_manager` is bound by CORPUS"
    )

    synergy = by_name["radarvan.player_synergy.compute_player_synergy"]
    assert [p.name for p in synergy.key_params] == [
        "lambda_pair",
        "lambda_main",
        "min_games_together",
    ], "synergy must key on its tuning params; `games` is bound by CORPUS"

    grid = by_name["radarvan.routes.predict._faction_grid"]
    assert [p.name for p in grid.key_params] == ["map_name", "player1", "player2"], (
        "MODEL binds no parameter, so every argument of _faction_grid is key"
    )

    for name in ("radarvan.cache.sorted_deduped_matches", "radarvan.cache.map_name_index"):
        assert by_name[name].key_params == (), (
            f"{name} takes only a manager, so its key should be the token alone"
        )


def test_probe_bound_derivations_with_no_key_hold_one_entry() -> None:
    """A derivation whose whole key is a probe token has no use for a second slot.

    A probe answers the same thing for every caller within a generation, so with
    no key parameters there is exactly one live key - and since invalidate()
    sweeps, slot two could only ever hold a generation already superseded. One
    generation of the match corpus is ~20 MB on a 512 MB dyno.

    Value-bound derivations are deliberately exempt: their token carries the ids
    of the list they were handed, so distinct corpora (all matches vs
    competitive vs a format filter) are distinct live keys.
    """
    for d in _registered():
        probe_bound = d.bound_param is not None and d.bound_param == d.dependency.probe_param
        if probe_bound and not d.key_params:
            assert d.maxsize == 1, (
                f"{d.qualified_name} keys on a probe token alone but declares "
                f"maxsize={d.maxsize}; the extra slots can only retain "
                f"superseded generations"
            )


# --------------------------------------------------------------------------
# 2. invalidation
# --------------------------------------------------------------------------


class _Counter:
    """Stands in for an expensive derivation; counts how often it really ran."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        return self.calls


@pytest.fixture
def probe_dependency() -> versions.Dependency:
    """A dependency with a probe we control, isolated from the real ones."""
    value = itertools.count()
    return versions.Dependency("test-probe", lambda: next(value))


def test_invalidate_forces_recompute_and_nothing_else_does() -> None:
    counter = _Counter()

    # A constant probe, so the epoch is the only thing that can move the token -
    # which is exactly what invalidate() bumps.
    dep = versions.Dependency("test-constant", lambda: "fixed")

    @derived.derived(on=dep, maxsize=4)
    def probe() -> int:
        return counter()

    assert probe() == 1
    assert probe() == 1, "a repeat call re-derived; the cache is not being read"
    assert counter.calls == 1

    derived.invalidate(dep)
    assert probe() == 2, "invalidate() did not make the derivation re-derive"
    assert probe() == 2
    assert counter.calls == 2

    # Registered under a throwaway dependency; drop it so it does not leak into
    # the shape tests, which check every registration against DEPENDENCIES.
    _unregister(probe.__name__)


def test_concurrent_misses_of_one_key_compute_once() -> None:
    """The expensive case is guaranteed, not incidental.

    `invalidate_match_caches()` sweeps and pokes the warm thread in the same
    call, so the warm thread and the request that triggered it race for exactly
    the same key by construction - and that key is a multi-second recompute on a
    one-core dyno. cachetools' plain locked wrapper calls the function outside
    the lock, so every racer would compute and all but one result be discarded.
    """
    counter = _Counter()
    dep = versions.Dependency("test-single-flight", lambda: "fixed")

    @derived.derived(on=dep, maxsize=4)
    def slow() -> int:
        value = counter()
        time.sleep(0.2)
        return value

    threads = [threading.Thread(target=slow) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter.calls == 1, (
        f"{counter.calls} threads computed the same key concurrently; the "
        f"derivation is not single-flighted"
    )
    _unregister(slow.__name__)


def test_bump_drops_the_memoized_probe(probe_dependency: versions.Dependency) -> None:
    """A bump must re-read the probe immediately, not wait out PROBE_TTL_SECONDS."""
    first = probe_dependency.probe()
    assert probe_dependency.probe() == first, "probe is not memoized within its TTL"

    probe_dependency.bump()
    assert probe_dependency.probe() != first, (
        "bump() left the previous probe value memoized, so an out-of-process "
        "change made just before the bump would be missed for up to a minute"
    )


def test_token_combines_epoch_and_probe(
    probe_dependency: versions.Dependency,
) -> None:
    epoch, _ = probe_dependency.token_from_probe()
    assert epoch == 0
    probe_dependency.bump()
    bumped_epoch, _ = probe_dependency.token_from_probe()
    assert bumped_epoch == 1


def test_a_dependency_offering_both_bindings_picks_by_signature() -> None:
    """CORPUS is read by probe or by value depending on the derivation.

    Both live on the same Dependency object, so the choice has to come from the
    signature. Getting it from the dependency instead means every manager-taking
    derivation tries to iterate its ReplayManager.
    """
    by_name = {d.qualified_name: d for d in _registered()}
    assert by_name["radarvan.cache.sorted_deduped_matches"].bound_param == "replay_manager"
    assert by_name["radarvan.player_rating.compute_player_ratings"].bound_param == "games"
    assert by_name["radarvan.routes.predict._faction_grid"].bound_param is None


def test_a_derivation_missing_the_probe_parameter_fails_at_decoration() -> None:
    """The failure must land on import, not on the first request to the endpoint."""
    with pytest.raises(TypeError, match="Rename the parameter"):

        @derived.derived(on=CORPUS, maxsize=4)
        def _no_manager(some_other_argument: int) -> int:
            return some_other_argument


def test_a_derivation_offering_both_bindings_fails_at_decoration() -> None:
    """CORPUS can be observed by probe or by value, never both in one call."""
    with pytest.raises(TypeError, match=r"cannot\s+tell which one"):

        @derived.derived(on=CORPUS, maxsize=4)
        def _ambiguous(games: list, replay_manager: object) -> int:
            return 0


def test_star_args_are_rejected_at_decoration() -> None:
    """*args cannot be keyed by position, so it must not be silently dropped."""
    with pytest.raises(TypeError, match=r"\*args"):

        @derived.derived(on=MODEL, maxsize=4)
        def _varargs(*args: int) -> int:
            return 0


def test_probe_input_binds_from_a_keyword_argument() -> None:
    """Handlers call these positionally, but nothing stops a keyword call."""
    seen: list[object] = []
    dep = versions.Dependency("test-kwarg", lambda rm: seen.append(rm) or "v",
                              probe_param="replay_manager")

    @derived.derived(on=dep, maxsize=2)
    def probe(replay_manager: object) -> int:
        return 1

    sentinel = object()
    probe(replay_manager=sentinel)
    assert seen == [sentinel], "the probe did not receive the keyword argument"
    _unregister(probe.__name__)


# --------------------------------------------------------------------------
# 3. content-change staleness (the reparse / override bug)
# --------------------------------------------------------------------------


def test_corpus_taking_derivation_sees_a_content_change_at_the_same_ids() -> None:
    """A reparse changes a match's contents but not its id.

    The ids alone would hash identically before and after, so a derivation
    over `list[MatchInfo]` would serve the pre-reparse answer forever. The epoch
    is what closes that, and this asserts it end to end.
    """
    counter = _Counter()
    dep = versions.Dependency(
        "test-corpus-by-value",
        lambda: "fixed",
        value_param="games",
        value_revision=versions._match_ids,
    )

    @derived.derived(on=dep, maxsize=4)
    def winners(games: list) -> tuple[int, ...]:
        counter()
        return tuple(g.winning_team for g in games)

    before = list(MATCH_CORPUS[:3])
    assert winners(before) == tuple(g.winning_team for g in before)
    assert counter.calls == 1

    # Same ids and same days, opposite winner - exactly what an override does.
    after = [
        match(g.id, day=g.timestamp.day, winner=(2 if g.winning_team == 1 else 1))
        for g in before
    ]
    assert versions._match_ids(after) == versions._match_ids(before), (
        "fixture problem: the two lists must share ids for this test to mean anything"
    )

    assert winners(after) == tuple(g.winning_team for g in before), (
        "without an invalidation the stale answer is expected - the ids match"
    )

    derived.invalidate(dep)
    assert winners(after) == tuple(g.winning_team for g in after), (
        "after invalidate() the derivation still returned the pre-change answer: "
        "a reparse or WinnerOverride would serve stale ratings"
    )

    _unregister(winners.__name__)


def test_a_corpus_by_value_derivation_never_probes() -> None:
    """When the input arrives by value, asking the database is redundant work."""
    probes = _Counter()
    dep = versions.Dependency(
        "test-no-probe",
        lambda: probes(),
        value_param="games",
        value_revision=versions._match_ids,
    )

    @derived.derived(on=dep, maxsize=2)
    def winners(games: list) -> int:
        return len(games)

    winners(list(MATCH_CORPUS[:2]))
    assert probes.calls == 0, (
        "a derivation handed the corpus directly still hit the probe; the caller "
        "already answered the question the probe asks"
    )
    _unregister(winners.__name__)


# --------------------------------------------------------------------------
# 4. the ratchet
# --------------------------------------------------------------------------


# Modules allowed to build a cachetools cache without going through @derived.
# Every entry needs a reason. Prefer making the thing a derivation over adding a
# line here - a cache that is not in the registry is a cache that invalidation
# does not know about, which is the exact problem the registry exists to remove.
CACHE_ALLOWLIST: dict[str, str] = {
    "derived/registry.py": "the registry itself - this is where the cache is built",
    "routes/draft.py": (
        "an idempotency cache over a deliberately random result. Version-keying it "
        "would re-randomize a draft mid-game-night, which is the opposite of what "
        "it is for."
    ),
    "scrape_games.py": (
        "an async HTTP response cache over gentool. Derives from an external site, "
        "not from the corpus, and cachetools_async is a different decorator."
    ),
    "routes/players.py": (
        "the six-hour hold on /api/balance_teams/. The numbers underneath are a "
        "derivation and track the corpus; this deliberately freezes an answer for "
        "a game night, which is a wall clock and cannot be a version token."
    ),
}

_CACHETOOLS_CACHE_NAMES = {"LRUCache", "TTLCache", "LFUCache", "Cache", "TLRUCache"}
_CACHE_DECORATORS = {"cached", "cachedmethod", "locked_cached"}

# functools.lru_cache/cache over a function that TAKES ARGUMENTS is the same bug
# shape as a bare cachetools cache: a keyed, unversioned, process-global memo. Over
# a nullary function it is just a singleton (a client, a model handle), which is
# fine and extremely common here - so the detector keys on the parameter list, not
# the decorator name. This gap was live: migrating `player_rating.get_model` from
# `@cached(cache={})` to `@lru_cache(maxsize=1)` moved it out of the scan entirely.
_FUNCTOOLS_DECORATORS = {"lru_cache", "cache"}

FUNCTOOLS_ALLOWLIST: dict[str, str] = {
    "bracket.build_topology": (
        "a pure function of one int (the entrant count). Nothing versions it "
        "because nothing can change it - see bracket.py's module docstring."
    ),
}


def _python_files() -> Iterator[Path]:
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _relative(path: Path) -> str:
    return str(path.relative_to(PACKAGE_ROOT))


def _builds_a_cache(tree: ast.AST) -> bool:
    """True if this module constructs a cachetools cache or applies its decorator."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name in _CACHETOOLS_CACHE_NAMES or name in _CACHE_DECORATORS:
                return True
    return False


def test_no_module_builds_a_cache_outside_the_registry() -> None:
    offenders = {
        _relative(path)
        for path in _python_files()
        if _builds_a_cache(ast.parse(path.read_text()))
    }
    unexpected = offenders - CACHE_ALLOWLIST.keys()
    assert not unexpected, (
        "these modules build a cachetools cache directly:\n  "
        + "\n  ".join(sorted(unexpected))
        + "\n\nDeclare it with @derived(on=..., maxsize=...) instead - that supplies "
        "the bound and the lock and puts it under invalidation. If it genuinely is "
        "not a derivation, add it to CACHE_ALLOWLIST with a reason."
    )


def _functools_cached_with_arguments(tree: ast.AST, module: str) -> set[str]:
    """Qualified names of functions in this module memoized by functools *and*
    taking arguments - i.e. keyed memos that no version token reaches."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = node.args
        if not (args.posonlyargs or args.args or args.kwonlyargs):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            name = (
                target.id
                if isinstance(target, ast.Name)
                else target.attr
                if isinstance(target, ast.Attribute)
                else None
            )
            if name in _FUNCTOOLS_DECORATORS:
                found.add(f"{module}.{node.name}")
    return found


def test_no_functools_memo_over_a_keyed_function() -> None:
    offenders: set[str] = set()
    for path in _python_files():
        module = _relative(path).removesuffix(".py").replace("/", ".")
        offenders |= _functools_cached_with_arguments(ast.parse(path.read_text()), module)
    unexpected = offenders - FUNCTOOLS_ALLOWLIST.keys()
    assert not unexpected, (
        "these functions are memoized by functools but take arguments:\n  "
        + "\n  ".join(sorted(unexpected))
        + "\n\nThat is a keyed process-global cache no version token reaches - the "
        "exact shape @derived exists to replace. Declare it with "
        "@derived(on=..., maxsize=...), or add it to FUNCTOOLS_ALLOWLIST with a "
        "reason if it is a pure function of its arguments."
    )


def test_functools_allowlist_entries_still_exist() -> None:
    import importlib

    for dotted in FUNCTOOLS_ALLOWLIST:
        module_name, _, attr = dotted.rpartition(".")
        module = importlib.import_module(f"radarvan.{module_name}")
        assert hasattr(module, attr), (
            f"{dotted} is allow-listed but no longer exists"
        )


def test_allowlist_entries_still_exist_and_still_cache() -> None:
    """A stale exemption is worse than no exemption - it hides the next one."""
    for name in CACHE_ALLOWLIST:
        path = PACKAGE_ROOT / name
        assert path.exists(), f"{name} is allow-listed but no longer exists"
        assert _builds_a_cache(ast.parse(path.read_text())), (
            f"{name} no longer builds a cache; drop it from CACHE_ALLOWLIST"
        )


def test_allowlist_stays_small() -> None:
    assert len(CACHE_ALLOWLIST) <= 4, (
        f"CACHE_ALLOWLIST grew to {len(CACHE_ALLOWLIST)}. Prefer making the cache a "
        "derivation over exempting it. Every entry here is a wall clock chosen on "
        "purpose - if a new one is really 'this derives from the corpus', it "
        "belongs in the registry instead."
    )


def test_locked_cached_helper_is_gone() -> None:
    """`utils.locked_cached` existed so a lock could not be forgotten, but nothing
    forced anyone to call it - and a cache was still declared without it (#119).
    The registry closes that gap; keeping both would leave it open."""
    from radarvan import utils

    assert not hasattr(utils, "locked_cached"), (
        "utils.locked_cached is back. @derived supplies the lock and the bound "
        "together; a second, optional way to get only the lock is the gap that "
        "produced the unbounded synergy cache."
    )


# --------------------------------------------------------------------------
# consistency between the registry and the things it describes
# --------------------------------------------------------------------------


def test_versions_does_not_import_ml_inference_at_module_scope() -> None:
    """`_model_probe` shares `ml_inference.ENSEMBLE_DIR` via a function-local
    import. It has to stay local: `ml/` puts this repo on PYTHONPATH and imports
    `player_rating`, which reaches `derived`, and onnxruntime has no wheel for the
    3.13 training venv."""
    source = (PACKAGE_ROOT / "derived" / "versions.py").read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = ast.unparse(node)
            assert "ml_inference" not in names, (
                f"derived/versions.py imports ml_inference at module scope "
                f"({names}), which drags onnxruntime into the ml/ training venv"
            )


def test_durable_versions_still_exist() -> None:
    """The durable projections are outside the registry but listed in it, so the
    one place that enumerates version tokens stays accurate."""
    import importlib

    for dotted in versions.DURABLE_VERSIONS:
        module_name, _, attr = dotted.rpartition(".")
        module = importlib.import_module(f"radarvan.{module_name}")
        assert hasattr(module, attr), (
            f"{dotted} is listed in DURABLE_VERSIONS but no longer exists"
        )


def test_dependencies_are_distinct_objects() -> None:
    assert len({id(d) for d in versions.DEPENDENCIES}) == len(versions.DEPENDENCIES)
    assert {d.name for d in versions.DEPENDENCIES} == {"corpus", "maps", "model"}
    assert (CORPUS, MAPS, MODEL) == versions.DEPENDENCIES


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _unregister(name: str) -> None:
    """Drop a test-local derivation from the process-global registry."""
    derived.REGISTRY[:] = [d for d in derived.REGISTRY if d.name != name]
