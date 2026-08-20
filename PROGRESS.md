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
- 2026-08-13 — Analyzed the real Kaggle leaderboard replay for our v1
  submission (`92035136.json`, untracked in repo root — downloaded from
  kaggle.com, not yet moved to `replays/`): lost to `HechtJP`, 3343 vs
  34231. Extracted both players' `action` sequences directly from the
  replay's `steps` to compare behavior:
  - Our wheat-loop agent: `farmer` action is `PASS` on 660/720 turns
    (91.7%) — it only ever tends the single tile it starts on, never
    moves, never hires hands, only ever plants `WHEAT`.
  - `HechtJP`: farmer moves every day (`NORTH`/`SOUTH`/`EAST`/`WEST` sum
    to 427 of its own actions), hires ~3 farm hands *every single day*
    (89 `HIRE` orders ≈ 30 days × 3 — cheap, since Fibonacci hire cost
    resets daily: 3 hands costs $1+$1+$2=$4/day), and gives those hands
    the same tile-tending logic (hands' combined actions exceed 1800,
    dwarfing the farmer's own). Plants `WHEAT`/`CARROT`/`MELON`, not just
    wheat. Never issues `BUY_LAND` — stays in the free NW quadrant
    (5x5=25 tiles) the whole game, so land expansion isn't required to
    beat this bar.
  - Confirmed via `README.md`: farmer and hands spawn at the shed
    `(4,4)` at the start of every day (matches the replay's farmer
    position resetting to `(4,4)` exactly every 24 turns), and hands
    disappear at end-of-day (must be re-hired daily).
  - Revised Level 2 priority based on this: farmer movement first
    (single agent, multiple tiles), then hiring hands (same logic,
    parallelized) — ahead of per-tile crop ROI, since one agent tending
    one tile has a low ceiling regardless of which crop it grows.
- 2026-08-19 — `notebooks/05_farmer_movement.ipynb`: built and validated
  the first Level 2 increment — farmer movement over a closed 2x2 tile
  loop (`(4,4) → (4,3) → (3,3) → (3,4) → (4,4)`, the 4 tiles closest to
  the shed spawn point). Confirmed empirically (not assumed) that `NORTH`
  decrements `y` before writing the direction mapping. Two bugs found and
  fixed along the way, both via `evaluate.py` against `wheat_loop_agent`
  (not just random/starter, per the roadmap's step 4):
  - First working draft evaluated as a **loss**: `wheat_loop_agent` beat
    the movement version 20/20. Root cause (found via replay inspection,
    not guessed): once a tile held a growing crop, the "already
    watered today, nothing to do" case fell through to `PASS` instead of
    to the movement branch, so the farmer camped the first tile it moved
    to for its entire growth cycle (~20 turns/day of `PASS`) and never
    reached the other 3 tiles. Fix: that case now returns the same
    move-to-next-tile action as the empty/no-seed case.
  - After the fix: `wheat_loop_agent` loses 20/20
    (`evaluate(wheat_loop_agent, wheat_loop_2x2_agent, n=20)` →
    `win_rate=0.0` for the baseline). `avg_money`: baseline ~3300-3385
    across two independent `evaluate()` calls (fresh `env` each time) vs.
    ~4293 for the 2x2 loop version — roughly +29% money.
  - Harness note for future evaluations: within a single `evaluate()`/
    `run_episodes()` call, the `n` episodes reuse one `env` object and
    came back bit-for-bit identical every time in this matchup (no
    randomness triggered across the reused object's `.run()` calls);
    genuine variance only showed up **between** separate calls (fresh
    `env` via `make()` each time — consistent with the 2026-08-10 entry's
    "re-running the same matchup swung by >100 points"). For a
    trustworthy read, call `evaluate()` more than once rather than
    trusting a single call's `n`.
  - Known, deliberately deferred gap: on day 0 the farmer moves off
    `(4,4)` before it has a seed to plant (seed isn't available until the
    turn after `BUY_SEED` resolves), so that one tile isn't planted until
    the loop comes back around (~10 turns later) instead of on arrival.
    One-time startup cost, not fixed — see Next steps.
  - Graduated to
    `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_2x2_agent`
    (docstring cites this entry and the 2026-08-13 replay finding), with
    9 new unit tests in `tests/test_baseline.py` (loop-order structure,
    direction mapping, and a regression test for the `PASS`-trap bug).
    `RESOURCES.md` updated. **Not yet wired into `agent/main.py`** —
    `scripts/build_agent.py`'s `STRATEGY` constant still points at
    `wheat_loop_agent`; switching the submitted agent is a separate step.
- 2026-08-19 — `notebooks/06_farmer_movement_12_tile_loop.ipynb`: pushed
  the tile loop from 4 to 12 tiles, deliberately targeting the ~12
  tiles/day ceiling derived in the previous entry (24 turns/day, ~2
  turns per new tile) rather than an arbitrary size. Loop shape: the
  2-row rectangle spanning `y=3..4` (10 tiles, all of `x=0..4`) plus a
  2-tile detour into `y=2` between `(2,3)` and `(3,3)` — hand-built and
  verified adjacent/non-repeating the same way as the 2x2 loop, no new
  entries needed in `DIRECTIONS` (all 4 compass directions were already
  covered). Same stateless design as `wheat_loop_2x2_agent` (harvest >
  water > plant > move to next tile in the loop); the `PASS`-trap bug
  from the previous entry didn't recur since the fix was reused as-is.
  Validated against the **current best**, `wheat_loop_2x2_agent` — not
  the original 1-tile baseline, per this project's "recompute the
  baseline in the same run" rule (`structuring-ml-projects` step 4):
  `evaluate(wheat_loop_2x2_agent, wheat_loop_12_agent, n=20)` →
  `win_rate=0.0` for the 2x2 loop across two independent calls,
  `avg_money` 4301.0 and 4413.0 for the 2x2 loop (losing side) vs. more
  for the 12-tile version. Graduated to
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_12_agent`,
  7 new unit tests in `tests/test_baseline.py` (12-tile loop structure,
  behavior on the plain stretch and specifically on the 2-tile detour).
  `RESOURCES.md` updated. Same day-0 startup gap as `wheat_loop_2x2_agent`
  applies here too (now potentially delaying more tiles' first planting
  by a full lap) — still not fixed, see Next steps.
- 2026-08-19 — Wired `wheat_loop_12_agent` into `agent/main.py` for
  submission. Found and fixed a real gap in `scripts/build_agent.py`
  first: it only ever collected cross-module dependencies (things
  imported via `kaggriculture_bot.*`), never same-module top-level
  constants a strategy function references directly — irrelevant for
  `wheat_loop_agent` (fully self-contained) but `wheat_loop_2x2_agent`/
  `wheat_loop_12_agent` both read `LOOP_ORDER_*`/`DIRECTIONS` module
  constants, so generating without a fix would have shipped an
  `agent/main.py` that crashed with `NameError` on its first move. Added
  `_top_level_constants`/`_referenced_constant_block` (transitive, so a
  constant referencing another constant is still pulled in fully), 7 new
  unit tests in `tests/test_build_agent.py` (including one against the
  real `wheat_loop_2x2_agent` confirming only the constants it actually
  uses get included, not `LOOP_ORDER_12`). Regenerated `agent/main.py`
  via `python scripts/build_agent.py` after switching `STRATEGY` to
  `wheat_loop_12_agent`; `test_agent_dir_matches_generated_output` still
  passes. Ran the generated file standalone (imported exactly as Kaggle
  would run it, not via the `src/` package) through `evaluate.py` against
  `wheat_loop_2x2_agent` as an end-to-end check, not just a text diff:
  `win_rate=0.0` for the 2x2 loop, `avg_money=4480.0` — confirms the
  generated file behaves identically to the graduated `src/` version.
  **Not yet actually submitted to Kaggle** — that's a separate,
  externally-visible action, left for explicit confirmation.
- 2026-08-20 — Submitted v2 (`agent/main.py`, `wheat_loop_12_agent`) to
  Kaggle. Leaderboard score improved ~30 points over v1 (reported by
  project owner; exact leaderboard scoring formula not independently
  re-derived here). Analyzed the real leaderboard replay
  (`94568249.json`, saved to `replays/`, gitignored per `replays/*.json`
  — not in the repo) the same way the 2026-08-13 entry analyzed v1's:
  extracted both players' `action` sequences from `steps`. Still a loss,
  to `Muhammed Ali Kul`, 5737 vs 111496 — our money is up sharply from
  v1's 3343 (+72%), but the opponent's is over 3x HechtJP's 34231, so the
  gap widened, not narrowed.
  - Our agent: exactly the behavior `wheat_loop_12_agent` was validated
    for — 0 hands hired across all 720 turns, WHEAT-only, no land
    purchases, no animals. Farmer action counts: `WATER` 228, `PLANT`
    125, `HARVEST` 114, movement (`WEST`/`EAST`/`NORTH`/`SOUTH`) 252
    combined, `PASS` only 1 — confirms the 12-tile loop runs as designed
    (near-zero idle turns), so this loss is entirely about missing
    capabilities, not a bug in the loop itself.
  - Opponent: hired up to 10 hands (251 `HIRE` orders; held at 10 hands
    for 348/720 turns, the largest single bucket in the hand-count
    distribution), ran a full animal loop (`FEED` 162, `CARE` 30,
    `COLLECT_FERTILIZER` 19, `FERTILIZE` 3, `BUILD_PASTURE` 2,
    `BUY_ANIMAL` 10, `BUY_PRODUCT` 21), bought land twice, and
    diversified into `STRAWBERRY` alongside `WHEAT`.
  - Confirms the 2026-08-13 replay's priority call (farm hands first)
    still holds — 10 hands vs. our 0 is an even bigger gap than the ~3
    hands/day HechtJP used — and surfaces animals as a second lever of
    comparable size, not previously visible in the HechtJP replay (which
    had zero animal actions).

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
      Leaderboard result: lost to `HechtJP`, 3343 vs 34231 (episode
      92035136). See 2026-08-13 log entry for what that replay revealed.

### Level 2 — Resource management

- [x] **Farmer movement (first increment)** — 2x2 tile loop, graduated as
      `wheat_loop_2x2_agent` (see 2026-08-19 log entry). Beats
      `wheat_loop_agent` decisively (~+29% avg_money, 20/20 wins).
- [x] **Farmer movement (second increment)** — pushed to a 12-tile loop
      (the ~12-tile/day ceiling: 24 turns/day, ~2 turns/tile), graduated
      as `wheat_loop_12_agent` (see 2026-08-19 log entry). Beats
      `wheat_loop_2x2_agent` decisively, 20/20 across two runs.
- [ ] Fix the day-0 startup gap noted in the 2026-08-19 log entries
      (farmer moves off `(4,4)` before its first seed arrives, delaying
      that tile's first planting by a full lap — now potentially several
      tiles' worth with 12) — measure its actual cost first before
      adding the complexity.
- [x] Wired `wheat_loop_12_agent` into `scripts/build_agent.py`'s
      `STRATEGY` constant and regenerated `agent/main.py` (see 2026-08-19
      log entry — required a real fix to `build_agent.py` first, since it
      didn't handle same-module constants until now).
- [x] Submit `agent/main.py` (`wheat_loop_12_agent`) to Kaggle as v2.
      Leaderboard result: lost to `Muhammed Ali Kul`, 5737 vs 111496
      (episode 94568249). See 2026-08-20 log entry for what that replay
      revealed — confirms farm hands as the top-priority gap and surfaces
      animals as a second major lever.
- [ ] Hire farm hands daily (cheap — Fibonacci cost resets each day) and
      give each the same tile-tending logic as the farmer, once farmer
      movement (above) is validated — biggest single lever seen in both
      the HechtJP (2026-08-13) and Muhammed Ali Kul (2026-08-20) replays;
      the latter used up to 10 hands vs. our 0.
- [ ] Per-tile crop choice by ROI (the Yield/tile/day column in README.md)
      — diversify beyond wheat-only (HechtJP also grew CARROT/MELON)
- [ ] Price-aware selling (avoid crashing premium goods to the $1 floor by
      dumping full inventory at once)
- [ ] Animals: coop/pasture, feed, care, fertilizer loop
- [ ] Buy land only when projected ROI beats the cost ($1k/$2k/$4k) —
      note HechtJP never bought land in the replay we studied, stayed in
      the free NW quadrant the whole game

### Level 3 — Turn-by-turn planning

- [ ] Score candidate actions per turn instead of fixed if/else rules
      (greedy scoring, or a short lookahead)

### Level 4 — Learning (optional, only if heuristics plateau)

- [ ] Self-play / RL against the local simulator (kaggle-environments
      exposes a Gym-like interface)
