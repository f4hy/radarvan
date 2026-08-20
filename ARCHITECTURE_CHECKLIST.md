# Architecture refactor checklist

Sequence steps from the architecture review. Full findings, evidence, and diagrams:
<https://claude.ai/code/artifact/3f4740cd-9178-4031-8f82-0879c2b01734>

Reviewed at `d374eea` (`perf/reduce-initial-bundle`, tree-identical to `origin/main` @ `1e5f99c`).
Ordered so each step makes the next one cheaper. Nothing here is a rewrite; no step blocks feature work.

- [x] **01** — Split `api_types.py` into a package, re-export from `__init__` _(an afternoon · no risk)_
      → 19 context modules + `__init__` re-exporting 170 names; OpenAPI spec unchanged.
- [x] **02** — ~~Move `warm_caches()` off the boot path~~ — **won't do.** Blocking boot is the
      intended behaviour: better to wait for the dyno to be ready than to serve cold. Measured
      3.68s cold (local → prod DB), so there is ample headroom against Heroku's 60s boot timeout.
      Revisit only if warm time approaches ~30s.
- [x] **03** — Parametrized smoke test across all 111 endpoints _(half a day · no risk)_
      → `tests/test_endpoints_smoke.py` runs 43 GETs against `tests/corpus.py`; 25 excused with
      reasons behind a ceiling; mutating routes checked for a usable response model. +64 tests, 7s.
- [x] **04** — `derived/` registry; migrate the 16 caches one at a time _(3–5 days · medium risk)_
      → 12 derivations, every one of them just `@derived(on=…, maxsize=…)` — the per-call key is
      read off the signature, so it can't be forgotten. `invalidate_match_caches()` collapsed to
      `invalidate(CORPUS, MAPS)`, naming no cache. Closed three staleness bugs: 10 of the 16 caches
      were never on the old clear list, reparse/override left ratings-skill-synergy serving
      pre-correction results, and `balance_teams` ran on 12h-stale ratings (the 6h hold that behaviour
      accidentally provided is now explicit at the route). `utils.locked_cached`
      deleted; a ratchet test fails any new bare cachetools cache *or* `functools` memo over a
      keyed function. Derivations are single-flighted now (8 racing threads → 1 computation).
      Boot warm unchanged (3.1s).
- [ ] **05** — `queries/` layer; move logic out of handlers as you touch them _(incremental · low risk)_
- [ ] **06** — Narrow `Depends` providers; freeze `ReplayManager` _(incremental · low risk)_
- [ ] **07** — Fixture coverage for `ffa_stats`, `general_stats`, `team_stats`, `create_teams` _(a day · no risk)_
- [ ] **08** — TanStack Query, then React Router over the existing lazy boundaries _(2–3 days · medium risk)_
- [ ] **09** — `require_dev` on the endpoints that shouldn't exist in prod _(an hour · no risk)_
- [ ] **10** — Import-linter rule enforcing layer direction in `make check` _(an hour · no risk)_
