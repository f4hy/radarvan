# Architecture refactor checklist

Sequence steps from the architecture review. Full findings, evidence, and diagrams:
<https://claude.ai/code/artifact/3f4740cd-9178-4031-8f82-0879c2b01734>

Reviewed at `d374eea` (`perf/reduce-initial-bundle`, tree-identical to `origin/main` @ `1e5f99c`).
Ordered so each step makes the next one cheaper. Nothing here is a rewrite; no step blocks feature work.

- [x] **01** — Split `api_types.py` into a package, re-export from `__init__` _(an afternoon · no risk)_
      → 19 context modules + `__init__` re-exporting 170 names; OpenAPI spec unchanged.
- [ ] **02** — Move `warm_caches()` off the boot path _(an hour · low risk)_
- [ ] **03** — Parametrized smoke test across all 111 endpoints _(half a day · no risk)_
- [ ] **04** — `derived/` registry; migrate the 16 caches one at a time _(3–5 days · medium risk)_
- [ ] **05** — `queries/` layer; move logic out of handlers as you touch them _(incremental · low risk)_
- [ ] **06** — Narrow `Depends` providers; freeze `ReplayManager` _(incremental · low risk)_
- [ ] **07** — Fixture coverage for `ffa_stats`, `general_stats`, `team_stats`, `create_teams` _(a day · no risk)_
- [ ] **08** — TanStack Query, then React Router over the existing lazy boundaries _(2–3 days · medium risk)_
- [ ] **09** — `require_dev` on the endpoints that shouldn't exist in prod _(an hour · no risk)_
- [ ] **10** — Import-linter rule enforcing layer direction in `make check` _(an hour · no risk)_
