"""The ``@derived`` decorator and the registry of everything wearing it.

Every in-process derivation in this codebase goes through here. The decorator
exists to make four properties impossible to omit rather than merely
conventional:

* **bounded** - ``maxsize`` is a required argument with no default. An unbounded
  cache cannot be declared.
* **locked** - the lock is created by the decorator. There is no way to skip it.
* **versioned** - ``on=`` is required, and the dependency's token is folded into
  every key. A stale entry becomes unreachable rather than something a
  maintainer has to remember to clear.
* **keyed** - the per-call key is derived from the signature, so a derivation
  cannot silently collapse distinct arguments onto one entry.

That last one is why ``@derived(on=X, maxsize=N)`` is the whole vocabulary: the
dependency knows which parameter carries its input (see ``versions.Dependency``),
and everything else in the signature is the key - never passed by hand, since a
caller who forgot ``key=`` would get *wrong* answers, not merely stale ones.

The registry itself is what makes those properties testable: ``REGISTRY`` holds a
record per derivation, and ``tests/test_derived_registry.py`` walks it. It also
means invalidation is ``invalidate(CORPUS)`` - one token, no cache named - instead
of a hand-maintained list of ``cache_clear()`` calls that ten of the sixteen
original caches were never on.

There is deliberately no ``ttl=`` parameter. A TTL is a guess at how long a version
token stays valid, and the registry has the real token. The only TTLs left in the
system are the DB-poll intervals inside ``versions.Dependency``.
"""

from __future__ import annotations

import inspect
import threading
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from typing import Any, cast

import structlog
from cachetools import LRUCache, cached

from .versions import Dependency

logger = structlog.get_logger(__name__)

# Distinct from any value a caller could pass, so "argument omitted" is
# distinguishable from "argument passed as None" when building a key.
_MISSING = object()


@dataclass(frozen=True, slots=True)
class Parameter:
    """One key-carrying parameter of a derivation, resolved at decoration time.

    Holds the position as well as the name so the key can be built by index
    lookup on every call - ``inspect`` runs once, when the decorator is applied,
    never per request.
    """

    name: str
    index: int
    default: Any

    def extract(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        if self.name in kwargs:
            return kwargs[self.name]
        if self.index < len(args):
            return args[self.index]
        # A required parameter that is genuinely absent still reaches the wrapped
        # function, which raises the normal TypeError. Keying it as _MISSING just
        # keeps that call from colliding with a real one in the meantime.
        return self.default


@dataclass(frozen=True, slots=True)
class Derivation:
    """One registered derivation, as the enforcement tests see it."""

    name: str
    module: str
    dependency: Dependency
    # The parameter the dependency binds to observe its generation, or None if it
    # binds nothing (MODEL). Which of the dependency's two bindings this is
    # decides whether the token is a per-generation singleton (probe) or varies
    # with the argument (value).
    bound_param: str | None
    # The parameters that make up the per-call key: everything the dependency
    # does not bind. Empty for the many derivations that take only a manager.
    key_params: tuple[Parameter, ...]
    lock: threading.Lock = field(compare=False)
    cache_clear: Callable[[], None] = field(compare=False)
    cache: LRUCache[Any, Any] = field(compare=False)

    @property
    def qualified_name(self) -> str:
        return f"{self.module}.{self.name}"

    @property
    def maxsize(self) -> int:
        # cachetools types maxsize as float (it allows inf for a getsizeof cache);
        # every cache here is built with an int.
        return int(self.cache.maxsize)


REGISTRY: list[Derivation] = []
_registry_lock = threading.Lock()


def _resolve_binding(
    func: Callable[..., Any], on: Dependency
) -> tuple[Parameter | None, tuple[Parameter, ...]]:
    """Split a signature into (the parameter the dependency binds, the rest).

    Runs once, when the decorator is applied, so a renamed parameter fails on
    import rather than on the first request that reaches the endpoint.
    """
    where = f"{func.__module__}.{func.__name__}"
    parameters = list(inspect.signature(func).parameters.values())
    for p in parameters:
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            raise TypeError(
                f"{where} takes *args/**kwargs, which cannot be keyed by "
                f"position. Give it explicit parameters."
            )

    names = [p.name for p in parameters]
    bound_names = [n for n in (on.probe_param, on.value_param) if n is not None]
    present = [n for n in bound_names if n in names]

    if bound_names and not present:
        raise TypeError(
            f"{where} derives from {on.name!r}, which is observed through a "
            f"{' or '.join(repr(n) for n in bound_names)} argument, but its "
            f"parameters are {names}. Rename the parameter to match."
        )
    if len(present) > 1:
        raise TypeError(
            f"{where} has both {present} in its signature; {on.name!r} cannot "
            f"tell which one carries its input. Keep exactly one."
        )

    bound = present[0] if present else None
    resolved = [
        Parameter(
            name=p.name,
            index=i,
            default=_MISSING if p.default is p.empty else p.default,
        )
        for i, p in enumerate(parameters)
    ]
    binding = next((p for p in resolved if p.name == bound), None)
    key_params = tuple(p for p in resolved if p.name != bound)
    return binding, key_params


def derived[F: Callable[..., Any]](*, on: Dependency, maxsize: int) -> Callable[[F], F]:
    """Declare a memoized derivation over a versioned input.

    ``on`` names the input this derives from. Its token is folded into every cache
    key, so entries computed against an older generation can never be read back,
    and it also says how the generation is observed for a given call - either by
    probing the database through a ``replay_manager`` parameter, or by reading the
    ``list[MatchInfo]`` the function was handed. Which one applies is decided by
    the signature; see ``versions.Dependency``.

    Everything else in the signature is the per-call key: the match id for
    per-match details, the tuning parameters for synergy. Nothing to declare, and
    nothing to forget.

    The effective key is ``(dependency token, remaining arguments)``.
    """
    if maxsize < 1:
        raise ValueError(f"maxsize must be at least 1, got {maxsize}")

    def decorate(func: F) -> F:
        cache_obj: LRUCache[Any, Any] = LRUCache(maxsize=maxsize)
        lock = threading.Lock()
        binding, key_params = _resolve_binding(func, on)
        # Which half of the token this call supplies is decided here, once, from
        # the signature - CORPUS offers both, and asking it to guess per call is
        # how `sorted_deduped_matches(replay_manager)` ended up trying to iterate
        # a ReplayManager as if it were the corpus.
        token_of = (
            on.token_from_value
            if binding is not None and binding.name == on.value_param
            else on.token_from_probe
        )

        def full_key(*args: Any, **kwargs: Any) -> Hashable:
            source = binding.extract(args, kwargs) if binding is not None else None
            return (
                token_of(source),
                tuple(p.extract(args, kwargs) for p in key_params),
            )

        # condition= selects cachetools' single-flight wrapper: concurrent misses
        # of the same key wait for the first computation instead of each running
        # it. invalidate() sweeps and pokes the warm thread in the same call, so
        # the warm thread and the request that triggered it race for exactly the
        # same key by construction - and one of these is a multi-second recompute
        # on a one-core dyno. The key is still computed outside the lock, which
        # matters because computing it can hit the database.
        wrapper = cached(
            cache=cache_obj,
            key=full_key,
            lock=lock,
            condition=threading.Condition(lock),
        )(func)

        with _registry_lock:
            if any(
                d.name == func.__name__ and d.module == func.__module__
                for d in REGISTRY
            ):
                raise RuntimeError(
                    f"derivation {func.__module__}.{func.__name__} registered twice"
                )
            REGISTRY.append(
                Derivation(
                    name=func.__name__,
                    module=func.__module__,
                    dependency=on,
                    bound_param=binding.name if binding is not None else None,
                    key_params=key_params,
                    lock=lock,
                    cache_clear=wrapper.cache_clear,
                    cache=cache_obj,
                )
            )
        return cast(F, wrapper)

    return decorate


def invalidate(*dependencies: Dependency) -> None:
    """Mark inputs as changed. Every derivation over them re-derives on next read.

    Two things happen, for two different reasons:

    * **the epoch is bumped**, which is what makes this *correct*. Every key
      carries the token, so entries from the previous generation stop being
      addressable - including in a derivation added tomorrow that nobody thought
      to mention here.
    * **the derivations over that dependency are emptied**, which is only about
      *memory*. Bumping alone leaves the superseded generation resident until the
      LRU happens to evict it, and these entries are not small: one generation of
      `sorted_deduped_matches` is roughly 20 MB of `MatchInfo` on a 512 MB dyno.
      Sweeping caps it at one live generation. It buys no speed - the warm after
      an invalidate was measured at the same ~10s with and without this sweep;
      that cost is the recompute itself, which is the price of no longer serving
      a stale answer.

    No cache is named in either step - the registry is walked. Adding a new
    derivation still requires no change here, which is the whole point.
    """
    for dependency in dependencies:
        epoch = dependency.bump()
        swept = 0
        for derivation in REGISTRY:
            if derivation.dependency is dependency:
                derivation.cache_clear()
                swept += 1
        logger.debug(
            "invalidated", dependency=dependency.name, epoch=epoch, swept=swept
        )


def clear_all() -> None:
    """Empty every registered cache outright. Tests only.

    Production invalidation is ``invalidate()``: it is scoped to the input that
    actually changed, and it bumps the epoch, which is what makes the result
    correct rather than merely empty. This exists so a test can assert on
    recomputation without depending on LRU eviction order.
    """
    for derivation in REGISTRY:
        derivation.cache_clear()


def describe() -> list[str]:
    """One line per derivation. For debugging and the registry tests' failure output."""
    return [
        f"{d.qualified_name} on={d.dependency.name} maxsize={d.maxsize} "
        f"key={[p.name for p in d.key_params]} size={len(d.cache)}"
        for d in sorted(REGISTRY, key=lambda d: d.qualified_name)
    ]
