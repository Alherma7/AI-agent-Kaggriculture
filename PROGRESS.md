# Progress

Living log for this project. Update as you go, not at the end — see
`structuring-ml-projects` skill: one bullet per validated change (win or
documented loss), plus a Next steps checklist that always reflects the
real state of `src/` and `agent/main.py`.

## Progress log

- 2026-08-05 — Project scaffolded. Competition kit (`README.md`,
  `AGENTS.md`) reviewed: 2-player turn-based farming sim, 720 turns/season,
  agent submitted as `main.py` via `kaggle-environments`. No training data —
  "evaluation metric" here is performance across simulated episodes
  (win rate / final money) against baseline and prior-version opponents.
- 2026-08-08 — `notebooks/01_explore_env.ipynb`: ran full 720-step
  random-vs-random and random-vs-starter episodes locally
  (`kaggle-environments` package, no Kaggle CLI needed). Findings:
  - `obs` / `farms` / `market` / `private` / `town` keys and tile dict
    shapes (`PLANT`, `WEED`, `COOP`/`PASTURE`, `LOCKED`, empty) all match
    `README.md` / `AGENTS.md` exactly — no drift to correct for.
  - `env.steps[-1][i]["reward"]` equals that player's final
    `farms[i]["money"]` (cross-checked directly) — `evaluate.py` can read
    `reward` off the last step instead of re-parsing the final `obs`.
  - `"random"` vs `"random"`: **both agents finish at $0** (random market
    orders bankrupt the farm — e.g. indiscriminate `BUY_LAND`/`BUY_SEED`
    with no matching sells). `"random"` vs `"starter"`: starter wins
    3503 vs 0. So `"starter"` is a real, non-trivial baseline to beat, and
    `"random"` alone is a weak lower bound (any agent that just avoids
    self-bankrupting should already clear it).
  - `env.toJSON()` round-trips through `json.dump`/`json.load` cleanly;
    replay saved to `replays/01_explore_random_vs_starter.json`.
  - Confirms `config.py`'s re-export from the installed
    `kaggle_environments` package (rather than hand-transcribing the
    README tables) is valid and importable end to end.
- 2026-08-10 — `notebooks/02_evaluate_harness.ipynb`: built and validated
  `score_episodes`/`run_episodes`/`evaluate` (ties count as 0.5 wins).
  Graduated to `src/kaggriculture_bot/evaluate.py` with unit tests on
  `score_episodes`'s aggregation logic in `tests/test_evaluate.py`
  (`pytest.ini` added so `tests/` can import the `src/` package). Ran the
  wheat-loop agent prototyped in `notebooks/prueba.ipynb` through the new
  harness (10 episodes each): **win_rate=1.0, avg_money=3891.2 vs
  "random"**; **win_rate=1.0, avg_money=3920.0 vs "starter"** — clears
  both baselines, so the harness itself is confirmed working end to end.
- 2026-08-10 — `notebooks/03_baseline_wheat_loop.ipynb`: took the
  wheat-loop agent from `00_inicio.ipynb` (renamed from `prueba.ipynb`)
  through `evaluate.py` to resolve its two open TODOs:
  - Fixed the `market` list being overwritten (assignment) instead of
    accumulated (`.append`) between the `BUY_SEED` and `SELL` blocks —
    validated against both baselines post-fix, still win_rate=1.0
    (avg_money=3902.9 vs "random", 3868.0 vs "starter"; small deltas vs.
    the pre-fix numbers are noise, not a behavior change, since buy/sell
    rarely land on the same turn with this loop's logic).
  - Tested selling the full `shed` in one `SELL` order per turn vs. the
    original 1-unit-per-turn, both vs `"starter"`: **negative/inconclusive
    result** — n=10 gave a 38-point avg_money gap (3906.0 vs 3868.0), but
    re-running the *same* matchup at n=10 swung by >100 points purely
    from episode randomness (weed-spawn chance). At n=20 the gap dropped
    to 14 points (3894.0 vs 3880.0 sell-one) — within that noise band, so
    not adopted; kept selling 1 unit/turn. `my_agent_v1` (sell-all) stays
    in the notebook, unused, in case a much larger n reopens the question.
- 2026-08-11 — Graduated `wheat_loop_agent` from
  `03_baseline_wheat_loop.ipynb` to
  `src/kaggriculture_bot/strategies/baseline.py`, with a docstring citing
  `AGENTS.md`'s "Example — Wheat Loop" and 10 unit tests in
  `tests/test_baseline.py` covering the buy/plant/harvest/water/sell
  branches (all passing). Resolved one open question in the process: the
  notebook version checked WATER before HARVEST when both applied on the
  same turn, diverging from the source example; confirmed with the source
  and switched to HARVEST-before-WATER to match `AGENTS.md` exactly. The
  sell-1-unit-per-turn behavior (vs. dumping the shed) was kept as-is,
  since that was already the validated choice from the 2026-08-10 entry
  above. `RESOURCES.md`'s `AGENTS.md` entry updated to point at the
  graduated function and note both decisions.

- 2026-08-13 — `scripts/build_agent.py` (TDD, 18 unit tests in
  `tests/test_build_agent.py`): statically parses (via `ast`, never
  executes) `src/kaggriculture_bot/strategies/baseline.py`, extracts
  `wheat_loop_agent`'s exact source, and rewrites it into `agent/main.py`
  with an `agent(obs)` entrypoint — no internal dependencies to flatten
  today, since `wheat_loop_agent` is self-contained. `agent/main.py` is
  now a generated artifact (regenerate via `python scripts/build_agent.py`
  after any strategy change); `test_agent_dir_matches_generated_output`
  guards against drift. Found and fixed one bug while regenerating: the
  notebook-prototyped `MAIN_HEADER` constant used `"""..."""` as its own
  Python delimiter, so its *value* excluded the triple quotes — the
  generated `agent/main.py` lost its enclosing docstring and became
  invalid Python. Fixed by delimiting with `'''...'''` and including the
  `"""` literally in the string. Also pinned `encoding="utf-8"` on all
  `read_text`/`write_text` calls, per the risk flagged in the prior
  session's notebook (Windows defaults to cp1252, which had already
  silently mis-encoded the em-dash in this same header once).

## Next steps

Roadmap in increasing agent complexity — each level only starts once the
previous one has cleared `evaluate.py`'s gate and been logged here.

### Level 0 — Foundations + evaluation harness

- [x] Notebook `01_explore_env.ipynb`: play random/starter episodes, inspect
      a raw `obs` dict and a `replay.json`
- [x] Transcribe the Object Types / Price Function tables from `README.md`
      into `src/kaggriculture_bot/config.py` as the single source of truth
      (done via re-export from the installed package instead of hand
      transcription — see 2026-08-08 log entry)
- [ ] Build `state.py` / `actions.py` helpers (parse `obs`, build valid
      action dicts)
- [x] Build `evaluate.py`: run N episodes vs. `"random"` and `"starter"`
      built-in agents, report win rate + average final money — this is the
      gate every later change must clear (`structuring-ml-projects` step 6)
- [ ] Join the competition on kaggle.com and download the kit data (blocked
      on CLI auth for now, see above — website works meanwhile)

### Level 1 — Baseline heuristic agent

- [x] Notebook `03_baseline_wheat_loop.ipynb`: validate the AGENTS.md
      wheat-loop example against `evaluate.py` (see 2026-08-10 log entry)
- [x] Graduate the validated wheat loop to
      `src/kaggriculture_bot/strategies/baseline.py` (named function,
      docstring, unit test) — see `structuring-ml-projects` graduation rule
- [x] Graduate to `agent/main.py` — inlined `wheat_loop_agent`'s body
      directly (2026-08-11) since Kaggle submissions must be a flat
      `main.py`/tar.gz, not a `src/`-style package import; kept in sync by
      hand with `src/kaggriculture_bot/strategies/baseline.py` for now
- [x] Deduplicate `agent/main.py` vs. `strategies/baseline.py`: added
      `scripts/build_agent.py`, which statically extracts the active
      strategy function (and recursively copies/rewrites any internal
      `kaggriculture_bot.*` imports as flat sibling files) into `agent/`.
      `agent/main.py` is now a generated artifact, never hand-edited.
      `tests/test_build_agent.py::test_agent_dir_matches_generated_output`
      guards against drift. See
      `docs/superpowers/specs/2026-08-12-build-agent-script-design.md`.
- [x] Submit v1 (`agent/main.py`, wheat-loop) to Kaggle — replay uploaded.
      Leaderboard result not logged yet.

### Level 2 — Resource management

- [ ] Per-tile crop choice by ROI (the Yield/tile/day column in README.md)
- [ ] Price-aware selling (avoid crashing premium goods to the $1 floor by
      dumping full inventory at once)
- [ ] Animals: coop/pasture, feed, care, fertilizer loop
- [ ] Hire farm hands / buy land only when projected ROI beats the cost
      (Fibonacci hire cost, $1k/$2k/$4k land cost)

### Level 3 — Turn-by-turn planning

- [ ] Score candidate actions per turn instead of fixed if/else rules
      (greedy scoring, or a short lookahead)

### Level 4 — Learning (optional, only if heuristics plateau)

- [ ] Self-play / RL against the local simulator (kaggle-environments
      exposes a Gym-like interface)
