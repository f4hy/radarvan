# Architecture review

A read of the whole repo — ~50k lines of Python across 151 modules, ~25k lines of
TypeScript across 80 files, 61 test files, 115 API routes, 2,291 matches over 412
game nights in production.

The baseline is high, and that matters for calibration: the layering (`routes/` →
`queries/` → `repositories/`), the `@derived` registry, the versioned durable
caches, the auth tiers, the deploy-config tests and the 3.13/3.14 parse guard are
all better than this size of project usually gets. None of what follows is
"adopt a pattern you're missing." Every finding is a place where a pattern this
repo *already chose* was not applied, or where a choice that was right at 2k
matches has a horizon worth naming.

Ordered by how much future work each unlocks.

---

## 1. `stat_name` is six things at once

`Statistic` (`api_types/tournaments.py:86`) carries `stat_name: str`. That one
string is simultaneously:

- the record's **identity** in `computed_statistics`
- the **display label**, emoji included — `"🔥 Longest Win Streak"`
- the **namespace**, via `__`-prefix convention (`general_stats.GENERAL_VALUE_STAT_PREFIX`,
  `opening_book.OPENING_STAT_PREFIX`)
- the **UI category key**, by substring match (`Superlatives.tsx:CATEGORY_ORDER`)
- the **React list key** (`Superlatives.tsx:136`)
- a **data carrier** — `f"🔥 Longest Win Streak ({streak.start} to {streak.end})"`,
  `f"🤝 Best Duo ({best[0]} & {best[1]})"`, `f"🌙 Best Game Night ({night})"`

There are 44 `stat_name=` sites in `superlatives.py` and more in `tournament.py`.

What this costs, concretely:

**The Records page groups stats by substring-matching English.** The comment at
`Superlatives.tsx:22-26` documents the failure mode already found in the wild —
"Efficiency" sat below "Money" in `CATEGORY_ORDER`, every `"… to Win"` record
matched `"Money"` first, and an entire section silently never rendered. Nothing
catches that: no type, no test, no build step. Renaming a label in Python
re-buckets or orphans a card in React, with no error anywhere.

**A record's identity changes when its data changes.** `"🔥 Longest Win Streak
(2025-03-04 to 2025-04-11)"` becomes a different `stat_name` the moment someone
extends the streak. You cannot ask "who has held the longest-streak record over
time", diff two nightly runs, or reference a record from anywhere stable.

**Three unrelated features share one table**, separated by `__` prefixes that
`routes/superlatives.py:34-39` filters out by hand, and one of them stores a
`General` enum in the column named `player`: `player=str(int(general))`
(`routes/superlatives.py:88`).

### What to do

Split the string into the three facts it's carrying:

```python
class Statistic(BaseModel):
    key: str              # "longest_win_streak" — stable, the row identity
    label: str            # "🔥 Longest Win Streak" — display only
    category: StatCategory  # StrEnum → OpenAPI → a TS union
    detail: str | None    # "2025-03-04 to 2025-04-11" — the data that was in the name
    value: float | str | None
    player: str | None
    match_id: int | None
```

`ComputedStatistic` gains `stat_key` and a `kind` column; the `__` prefixes
become `kind` values and the hand-rolled prefix filters disappear. `general_value`
rows stop abusing `player` and get their own `general` column or their own table.

The payoff is on the React side: grouping becomes `Record<StatCategory, Stat[]>`
over a generated union, so adding a category in Python is a *TypeScript
compile error* until the page handles it — instead of a card quietly falling into
"Other". This is the change with the highest ratio of future-mistakes-prevented
to lines-touched in the repo.

---

## 2. Bracket is the one feature the architecture never reached

Every other domain got the documented split. `queries/__init__.py` states it:
"`routes/` owns HTTP… the modules here own *selection*." There are `queries/`
modules for games, game nights, players and powers. There is no `queries/bracket.py`.

So `routes/bracket.py` is 743 lines — the largest route file by 150 lines — and
holds the domain logic the query layer exists to hold: reveal gating
(`is_revealed`), redaction (`_redact`), output construction (`_build_output`,
`_build_output_from_states`), prediction resolution (`_resolved_predictions`),
leaderboard scoring, and map records. Compare `routes/players.py`: 363 lines, zero
private helpers, pure delegation.

The frontend mirrors it exactly. `Bracket.tsx` is 2,457 lines and 35 components —
the largest file in the repo, and its lazy chunk is 260 KB, second only to the
charting library.

And inside it, one live tournament is hardcoded as module constants
(`Bracket.tsx:101-153`):

```ts
const DEFAULT_SEEDS = ["Modus", "Tytan", "WildCard", …]
const TOURNAMENT_BANNER_TITLE = "The Third Gamerz Rule 1v1 Tournament"
const TOURNAMENT_RULES: string[] = [ … 8 rules, one naming a specific admin … ]
const TOURNAMENT_MAP_LIST: string[] = [ … 11 maps … ]
```

Meanwhile `db.Tournament` exists, `TournamentRepo` exists, and its docstring says
it's "the durable identity every tournament game hangs off." Running the *fourth*
tournament means editing TypeScript and shipping a deploy, for content that is
already modelled as data one table over. An admin cannot do it; the ops control
panel (`AdminPanel.tsx`, whose tasks are commendably data-not-JSX) can't reach it.

### What to do

- Add `queries/bracket.py` and move reveal/redaction/output-shaping and prediction
  scoring out of the route file. That is the same move already made for game night
  and powers, so there is a worked example.
- Move rules, map pool, banner title and default seeds onto the `Tournament` row
  (explicit columns, or one `config: JSONB` if the shape is still moving), served
  by the existing endpoint and edited from the admin panel.
- Split `Bracket.tsx` into `features/bracket/` — tree rendering, the match editor,
  predictions, the matchup popup, the rules/map panels.

---

## 3. `src/` is 80 files in one flat directory

No subdirectories except the generated `api/` and the thin `clients/`. Nothing
distinguishes a page from a shared component from a hook from a helper, and the
top five files hold 122 components between them.

The consequence shows up as pages importing each other:

```
Superlatives  ← Matches          (for DisplayMatchInfo)
DebugData     ← Matches
Tournaments   ← Matches
Bracket       ← Matches, Agenda
HeadToHead    ← ShowMatchDetails
PlayerRatings ← PlayerSynergy
Draft         ← BalanceTeams
```

`routes.tsx` lazily splits every page, which is right — but opening Records pulls
in the entire 944-line Matches page to render one match card. The import graph
says these are shared components; the file layout says they're pages.

### What to do

```
src/
  features/   bracket/ matches/ players/ maps/ game-night/ admin/ …
  components/ PlayerChip WinRateChip WinRateRadar QueryState Page
              GameMap FormatToggle MatchCard …
  lib/        utils links apiError useUrlState queryClient theme
  api/        (generated — unchanged)
```

Start by extracting `DisplayMatchInfo` out of `Matches.tsx` into
`components/MatchCard.tsx`; that alone removes four page-to-page edges and
shrinks four lazy chunks. The rest can be moved file by file — it is pure
mechanical churn with a typechecker holding the rope.

---

## 4. The "legacy" facade the cache layer makes mandatory

`db_utils.py` says: "New code should prefer instantiating the specific repo it
needs over taking a fat ReplayManager dependency. ReplayManager remains for
backwards compatibility." CLAUDE.md repeats it.

The counts go the other way. 38 modules import `ReplayManager`; 13 import a
specific repo. That is not slow drift toward the goal — the goal is
structurally unreachable, and the `@derived` layer is why.

`versions.CORPUS` and `versions.MAPS` bind their probe **by parameter name**:
`probe_param="replay_manager"`. `registry._resolve_binding` raises `TypeError` at
import time if the decorated function has no parameter with that name. Of the 13
derivations in the codebase, eight take `replay_manager`; four take the corpus by
value as `games`; one binds nothing. Any new cached derivation that needs a DB
probe *must* take the eight-way-multiple-inheritance facade. There is no way to
write `@derived(on=MAPS)` over a `MapRepo`.

This isn't a bug — the name-binding is deliberate and well argued
(`versions.py:71-76`), and the facade has no MRO ambiguity. The problem is that
the repo carries documented intent its own design forbids, in two files, which is
worse than either choice made cleanly.

### What to do

Pick one:

- **Narrow the binding.** Declare the probe against a `Protocol`
  (`class CorpusProbe(Protocol): def latest_match_created_at(self) -> datetime | None`)
  and let `probe_param` accept any parameter satisfying it. Then a derivation can
  take `MapRepo` and the guidance becomes true.
- **Or accept the facade** and delete the "prefer the specific repo" line from
  both `db_utils.py` and CLAUDE.md. `ReplayManager` is a coherent unit-of-work
  object; there is nothing shameful about saying so.

Either is fine. The current state — advice that the decorator rejects — is not.

---

## 5. Four spellings of "which map is this"

| Where | Behaviour |
|---|---|
| `repositories/maps.py:normalize_map_name` | strip whitespace, lowercase |
| `map_stats.py:_normalize_map_name` | **byte-identical private duplicate** |
| `replay_files.py:map_key` | + strip path, strip `.map` |
| `src/bracketApi.ts:mapKey` | hand-written TS twin of `map_key` |
| `src/utils.ts:displayMapName` | strip path + `.map`, keep case |

`bracketApi.ts:44` is honest about it: *"TS twin of radarvan/replay_files.py's
map_key — the two must agree for a pool map name to line up with the map recorded
on a match."* Nothing enforces that they agree. And `src/CLAUDE.md:47` records
that this exact class of thing — hand-written twins of backend logic — was
deliberately eliminated during the generated-client migration. This one survived.

### What to do

- Delete `map_stats._normalize_map_name`; import the one in `repositories/maps.py`.
- The backend already returns `mapKey` on `MapPlayerRecords`. Put the canonical key
  on the wire everywhere the frontend needs to join on it, and delete the TS copy.
- If a TS copy genuinely must remain, pin it with a vitest fed from a
  Python-generated fixture of tricky names, so divergence is a red test rather
  than a silently empty map record.

---

## 6. Lint and type-check see only `radarvan/`

`make check` is `ruff check radarvan/` + `mypy radarvan/`. Unchecked: 14,656 lines
of tests, ~4,000 lines across the two ML packages, `scripts/`, `tools/`, and the
root-level scripts.

Running ruff over them: **1,668 findings.** Most are noise that should simply be
configured away — 1,565 `S101` (asserts in tests) and 25 `T201` (prints in
scripts). What's left is not noise:

- **25 `DTZ001`** — naive `datetime()` construction, in a codebase whose game-night
  correctness rests entirely on US-Eastern with a 5am rollover, and whose
  production code is DTZ-clean because the rule is on there. Test fixtures can
  currently build timestamps production would never produce.
- 31 `PERF401`, 7 `B905` (`zip` without `strict=`), 1 `B006` (mutable default).

And because `mypy` never sees `tests/`, a fixture can construct a `MatchInfo`
the API would reject — which is precisely the failure the e2e suite already
learned to prevent on the TypeScript side (`e2e/fixtures.ts` is typed against
`src/api` for exactly this reason).

### What to do

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]
"scripts/**" = ["T201"]
"ml/**" = ["T201"]
```

Point the Makefile targets at `radarvan tests ml ml_win_prediction_over_time
scripts tools`, fix the ~65 real findings, and add `mypy tests/`. This is an
afternoon, and it closes the gap between "the rules this project believes in" and
"the code those rules actually run on."

---

## 7. The corpus snapshot makes the app single-dyno — say so

Today: 2,291 matches, 412 nights. `sorted_deduped_matches` holds the whole corpus
in process — roughly 20 MB of `MatchInfo` on a 512 MB dyno, per
`derived/registry.py:248` — and the warm pass is about 10 seconds. At ~420 matches
a year that's roughly +4 MB/year. Memory is not the near-term problem.

The binding constraint is correctness, not size. `invalidate()` bumps a
**process-local** epoch, and `versions.py:16-19` states the limit plainly: the
CORPUS probe "sees *newly arrived* matches only — an out-of-process reparse or
override is not visible to it, and is covered by the epoch instead, which is why
in-process writers must route through `invalidate()`."

Put a second dyno behind the load balancer and dyno B keeps serving the old
winner after dyno A applies a `WinnerOverride`, for as long as its LRU holds the
entry. No error, no log line, just a wrong answer on half the requests.
Rate limiting degrades gracefully by design (`rate_limit.py:52-56`); the corpus
does not. `Procfile` runs `fastapi run` — one worker — so this is correct today
and invisible tomorrow.

### What to do

- **Now, free:** write it down as an invariant, next to the auth and migration
  invariants in CLAUDE.md. "This app runs as exactly one process. Scaling out
  requires a shared corpus revision first."
- **When it's needed:** make the CORPUS probe read a `corpus_revision` row that
  every write path bumps — the same operations that call `invalidate_match_caches()`
  today. The epoch then becomes redundant, the probe becomes authoritative for
  out-of-process writes too, and every one of the 13 derivations scales out
  unchanged because none of them names a cache. That is a genuinely small change,
  and it is the difference between "single dyno forever" and "scales the day it
  has to."

The `@derived` design already earned this: because invalidation names no cache,
the fix is one probe function, not thirteen call sites.

---

## 8. `mapparse` — a 3.2 MB binary with no source

At the repo root: a statically-linked x86-64 Linux Go executable, not stripped,
tracked in git, and a production dependency —
`missing_maps.MAPPARSE_BIN = os.environ.get("MAPPARSE_BIN", "./mapparse")`.

`MapData.mapparse_bin_hash` exists specifically to find rows that predate a
*rebuild* of this binary, so it does get rebuilt — from source that isn't in the
repo. Nothing records where it came from, how to build it, or what version it is.
The whole map-geometry pipeline has a bus factor of one and no recovery path.

### What to do

Vendor the source (or add it as a submodule with a build step). Failing that,
record provenance in the README — upstream repo, commit, build command, target
triple, checksum — and pin the expected SHA-256 in a test so a swapped binary is
a red build rather than a silent geometry change.

---

## 9. Two ML packages built by copy-and-modify

`ml/` and `ml_win_prediction_over_time/` share ten identically-named modules:
`config`, `dataset`, `export`, `features`, `model`, `predict`, `snapshot`,
`split`, `train`, `baselines`. The bodies differ — this is parallel evolution, not
copy-paste — but `train.py` alone has 134 lines in common, and the shared shape is
substantial: gzip-JSONL snapshot I/O, temporal train/dev split, the training loop
with early stopping, ONNX export, vocab/stats freezing from train only.

Two consequences already visible: the 3.13-parseability trap had to be fixed
twice (`tests/test_ml_venv_imports.py:60-70` records `ruff format` breaking the
second package after the first was pinned), and `ml_ensemble/` carries 30 `.onnx`
files plus a 160 KB `vocab.json` in git.

### What to do

A small `mltools/` for the plumbing both packages genuinely share, leaving each
package to own only its features, model and objective. Move model weights to S3
with a fetch step at deploy — or keep them in git deliberately and write down why.

---

## 10. Smaller things

**`derived_registry_plan.md` doesn't exist.** It is cited by
`derived/__init__.py:28`, `derived/versions.py:234` and
`tests/test_derived_registry.py:14`. Either restore it or drop the references.

**`api_types/` is a full barrel with fan-in 71 and fan-out 24.** Importing any one
wire type pulls all 24 submodules. The docstring says the re-export exists so
`from .api_types import X` keeps working for every name, which is a fair call —
but it makes the package the single highest-coupling node in the backend, and new
code should import from the submodule (`from .api_types.matches import MatchInfo`)
so the barrel shrinks to a compatibility shim over time.

**`src/CLAUDE.md` is 74 bullets of excellent content in the wrong place.** Facts
like "`MatchActivityCalendar`'s two nested `<g>`s are load-bearing" and "the
generated types lie about dates inside dict-valued fields" are read by whoever
opens `src/CLAUDE.md` — not by whoever opens `MatchActivityCalendar.tsx`. The test
for where a note belongs: *would the person about to break this see it?* Repo-wide
rules stay in CLAUDE.md; per-file traps belong in a three-line comment at the top
of the file they constrain. Several already are; the rest should follow them.

**`_safe_compute(fn, *args)`** (`superlatives.py:1334`) is the one untyped
function in the strict-mypy backend, carrying `# type: ignore[no-untyped-def]`. If
the 25 stat producers shared a `Protocol` signature — which finding 1 would make
natural anyway — it types cleanly and the dispatcher in `get_superlatives` becomes
a list of producers instead of three hand-maintained argument-shape groups.

---

## Suggested order

| | Work | Unlocks |
|---|---|---|
| 1 | Lint/typecheck the whole repo (§6) | Independent, an afternoon, makes everything after it safer |
| 2 | `mapparse` provenance (§8) | Removes the only single-point-of-failure with no recovery path |
| 3 | Collapse the map-key functions (§5) | Small, self-contained, deletes a live correctness risk |
| 4 | Typed `Statistic` (§1) | Biggest ratio of mistakes-prevented to lines-touched; also fixes `_safe_compute` |
| 5 | `src/` layout + extract `MatchCard` (§3) | Mechanical, typechecker-guided; prerequisite for §2 |
| 6 | `queries/bracket.py`, tournament content to DB, split `Bracket.tsx` (§2) | Turns "ship a deploy per tournament" into an admin form |
| 7 | Resolve the `ReplayManager` contradiction (§4) | Either direction; just stop documenting the impossible one |
| 8 | Write down the single-dyno invariant now; `corpus_revision` when scaling (§7) | Free today, cheap later, because `@derived` names no caches |
| 9 | `mltools/` (§9) | Lowest urgency — the duplication is stable and guarded by tests |
