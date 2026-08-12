# Design: `scripts/build_agent.py` — dedupe `agent/main.py`

## Problem

`agent/main.py` and `src/kaggriculture_bot/strategies/baseline.py` currently
hold two hand-maintained copies of the same agent function. This already
caused one real desync (main.py edited by hand, separately from the
graduated `src/` version), and PROGRESS.md's Level 1 checklist flags it as
unresolved:

> Deduplicate `agent/main.py` vs. `strategies/baseline.py` (e.g. a
> build/packaging script that generates the flat submission file from the
> single source of truth)

## Goal

`agent/main.py` stops being edited by hand. It becomes a generated artifact,
produced from the graduated strategy function in `src/`, via a build script.

## Non-goals (YAGNI)

- Circular-import detection. Resolution is recursive (a copied module's own
  internal imports are followed too), but nothing guards against a cycle
  (`a.py` imports `b.py` imports `a.py`) — not a shape that exists in the
  repo today, and if introduced it would just infinite-loop loudly rather
  than fail cleanly.
- Relative imports (`from . import x`) — nothing in the repo uses them today.
- Bundling non-Python assets (`model_weights.pkl`-style binaries) —
  `AGENTS.md`'s multi-file tar.gz format supports it, but no strategy needs
  it yet.
- A CLI flag for selecting the active strategy — a single hardcoded constant
  is enough for the current one-strategy-at-a-time workflow.

## Background: multi-file submissions are officially supported

`AGENTS.md` (treated as ground truth per `RESOURCES.md`) documents both
submission shapes explicitly:

```
**Single file agent:**
kaggle competitions submit kaggriculture -f main.py -m "Wheat loop v1"

**Multi-file agent** — bundle into a tar.gz with `main.py` at the root:
tar -czf submission.tar.gz main.py helper.py model_weights.pkl
kaggle competitions submit kaggriculture -f submission.tar.gz -m "Multi-file agent v1"
```

(`AGENTS.md:191-204`). The current v1 submission used the single-file form
only (`wheat_loop_agent` has no internal imports, so no helper files are
needed yet). The multi-file tar.gz path is trusted on the strength of this
documented source, consistent with how the rest of the project already
treats `AGENTS.md` as authoritative (action format, obs shape, etc.) without
requiring a separate live probe for each documented claim. If it turns out
to behave differently in practice once a strategy actually needs a helper
file, that's a fast, cheap thing to discover and fix at that point — it does
not block this design.

## Design

### `scripts/build_agent.py`

```python
STRATEGY = "kaggriculture_bot.strategies.baseline:wheat_loop_agent"
```

One constant, edited by hand when the active strategy changes. Format:
`"<dotted.module.path>:<function_name>"`.

**`generate_files(strategy_path: str) -> dict[str, str]`** — pure function,
no disk I/O beyond reading `src/`. Returns a mapping of
`{relative_path_under_agent: file_content}`, e.g.
`{"main.py": "...", "config.py": "..."}`.

Steps:
1. Split `strategy_path` into module + function name; locate the module's
   source file under `src/kaggriculture_bot/`.
2. Parse the module with `ast` and collect its top-level `import` /
   `from ... import ...` statements.
3. For each import whose module path starts with `kaggriculture_bot.`:
   copy the referenced file's full source verbatim into the output dict
   under its bare filename (e.g. `kaggriculture_bot.config` →
   `config.py`), and rewrite the import statement (for the generated
   `main.py`) to the flat form (`from kaggriculture_bot.config import X`
   → `from config import X`). Recurse into the copied module's own
   top-level imports the same way, so a two-level chain
   (`baseline.py` → `config.py` → `another_helper.py`) resolves correctly.
   A copied module is only ever emitted once even if referenced from
   multiple places.
4. Any import that does *not* start with `kaggriculture_bot.` (stdlib or
   third-party, e.g. `kaggle_environments`) is left untouched in the
   generated file — assumed available in the Kaggle sandbox, same
   assumption `config.py` already makes today.
5. Extract the strategy function's body via `inspect.getsource`, rename it
   to `agent`, and assemble `main.py`'s content as: the fixed entrypoint
   docstring (the one `agent/main.py` already carries — submission
   contract, "no network/file I/O" note) + the flat-rewritten import lines
   from step 3 + the renamed function.

**`main()`** — CLI entrypoint: calls `generate_files(STRATEGY)`, writes each
entry to `agent/<relative_path>`, overwriting existing content.

### Error handling

- `strategy_path` that doesn't resolve to a real module/function → raise
  immediately with a clear message (bad constant is a programmer error,
  not a runtime condition to recover from).
- An internal-looking import (`kaggriculture_bot.X`) whose file can't be
  found, or a relative import (`from . import x`) → raise loudly rather
  than emitting a `main.py` that will fail on Kaggle with no local signal.
- `generate_files` must be deterministic and idempotent: calling it twice
  with the same `STRATEGY` produces byte-identical output. This is required
  for the sync test below to be meaningful.

### `agent/main.py` header

Changes from "keep this in sync by hand" to noting the file is generated —
edits should go in `src/kaggriculture_bot/strategies/` and
`scripts/build_agent.py` re-run, not in `agent/main.py` directly.

### Testing

- **`tests/test_build_agent.py`**
  - Sync check: `generate_files(STRATEGY)` compared against the actual
    on-disk content of `agent/main.py` (and any copied files it currently
    produces) — fails if they differ. Catches exactly the kind of drift
    that motivated this change.
  - Import-rewrite coverage: `wheat_loop_agent` has no imports today, so
    that branch of `generate_files` has no real-world exerciser yet. Add a
    small synthetic fixture (a throwaway module + function with one
    `kaggriculture_bot.X`-style import, created under `tests/` or generated
    in-memory for the test) purely to exercise the copy-and-rewrite path,
    so it isn't shipped untested.
  - Error-path coverage: bad `strategy_path`, and an unresolvable internal
    import, each raise as designed.

## Open questions

None outstanding — resolved through the brainstorming session above
(scope of import handling, strategy-selection mechanism, sync-check
requirement, and trust in `AGENTS.md` for the multi-file format).
