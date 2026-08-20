"""Derived values: one registry for every in-process derivation in the system.

Before this package, caching *was* the architecture and it had never been designed
- sixteen independent inventions across eleven modules, three strategies, four
invalidation models. ``invalidate_match_caches()`` cleared six caches by name; the
other ten were correct only because their keys happened to derive from match
identity, with nothing enforcing that.

A derivation now declares what it depends on, and that is all:

    @derived(on=CORPUS, maxsize=1)
    def sorted_deduped_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
        ...

That is the entire vocabulary. The decorator supplies the bound and the lock
(neither is optional), folds the dependency's version token into every key, and
reads the per-call key off the signature - so there is no way to declare a
derivation that silently collapses distinct arguments onto one entry.
Invalidation is ``invalidate(CORPUS)``: one token, no cache named, nothing to
remember when a seventeenth derivation arrives.

``tests/test_derived_registry.py`` holds the line - it walks ``REGISTRY`` for shape,
asserts the invalidation property directly, and fails the suite if a bare
``cachetools`` cache appears anywhere outside the documented allow-list.

Scope: this is the in-memory tier. The durable projections (``match_details_cache``,
``player_profiles``) keep their own versioned load/save paths - see
``versions.DURABLE_VERSIONS`` and section 4 of ``derived_registry_plan.md``.
"""

from .registry import REGISTRY, Derivation, clear_all, derived, describe, invalidate
from .versions import CORPUS, DEPENDENCIES, DURABLE_VERSIONS, MAPS, MODEL, Dependency

__all__ = [
    "CORPUS",
    "DEPENDENCIES",
    "DURABLE_VERSIONS",
    "MAPS",
    "MODEL",
    "REGISTRY",
    "Dependency",
    "Derivation",
    "clear_all",
    "derived",
    "describe",
    "invalidate",
]
