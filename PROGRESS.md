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
- 2026-08-21 — `notebooks/07_farm_hands.ipynb`: built and validated the
  first hands increment — hire up to 5 hands daily (batched on the first
  turn of each day) and give each `wheat_loop_12_agent`'s own
  harvest > water > plant > move priority against a second, 16-tile loop
  (`LOOP_ORDER_HANDS`). Two real findings from mini-tests against a real
  `obs` (not assumed):
  - Hands don't spawn at `(4,4)` — `kaggriculture.py::_spawn_hand` places
    each new hand at the least-occupied of the 4 shed-access corners, and
    since the farmer permanently occupies `(4,4)`, new hands mostly land
    on the other 3, which are `"LOCKED"` (a string, not a tile dict) until
    that quadrant is bought. Without a guard, `.get("kind")` on a
    `"LOCKED"` tile raises `AttributeError` — 4 of 5 hands would have
    crashed on their first turn. Fixed with an explicit `"LOCKED"` check
    (treated like the empty-tile "nothing to do, move on" branch) plus
    `SPAWN_FEEDER`, routing a hand from a locked spawn corner one step
    into `LOOP_ORDER_HANDS`'s entry point.
  - With up to 6 units (farmer + 5 hands) all wanting to plant, buying 1
    seed/turn (like `wheat_loop_12_agent`) starves most of them — switched
    to buying up to 6 in stock at once.
  - Validated against the current best,
    `evaluate(wheat_loop_12_agent, wheat_loop_hands_agent, n=20)` →
    `win_rate=0.0` for `wheat_loop_12_agent` across two independent calls
    (`avg_money` 4775.0 and 4685.0 for the losing baseline). Graduated to
    `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_hands_agent`,
    12 new unit tests in `tests/test_baseline.py`. `RESOURCES.md` updated.
  - Known, deliberately deferred gaps: `(0,2)`/`(1,2)` still uncovered by
    either loop; the day-0 startup gap noted for `wheat_loop_12_agent`
    applies here too, now for up to 6 units.
- 2026-08-21 — Bug found in `wheat_loop_hands_agent` after the entry
  above: instrumented a full local episode and found all 5 hands
  permanently merge onto a single tile a few turns into day 0 and stay
  glued together for the rest of the day. Root cause: every hand's action
  was a pure function of its current tile — nothing distinguished one
  hand from another, so the moment two hands landed on the same tile
  (easy, since they all funnel through the shared entry point `(4,4)`),
  they computed identical actions forever after. Cross-checked against
  the real `Muhammed Ali Kul` replay (`replays/94568249.json`): their
  hands also overlap occasionally (473/720 turns with ≥2 units sharing a
  tile) but never stay merged more than 2 consecutive turns — confirming
  this was a real behavioral bug, not just normal traffic.
  - Fix: `HAND_ZONES`, splitting the 13 free NW tiles into 5
    pairwise-disjoint private loops, one per hand index (the hands list's
    order is stable turn to turn — confirmed empirically — so list
    position works as a de facto ID). Each hand still approaches via the
    shared `LOOP_ORDER_HANDS`/`SPAWN_FEEDER` path; its zone only
    overrides the tile(s) where it should peel off into its own loop
    instead of continuing on the shared one. Bonus: also finally covers
    `(0,2)`/`(1,2)`, the gap noted as untended in the previous entry.
  - Validated in `notebooks/07_farm_hands.ipynb` against the current best
    (`wheat_loop_hands_agent` pre-fix): the un-zoned version loses 20/20
    across **three** independent `evaluate()` runs (`avg_money` 6003.0,
    6524.0, 5856.0 for the losing, un-zoned version). Graduated the fix
    into `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_hands_agent`
    in place (same function name, new `HAND_ZONES`-based hands logic), 3
    new unit tests in `tests/test_baseline.py` (zone disjointness/cycle
    validity, two hands on one tile diverging instead of merging, and the
    single-tile zone's `PASS` fallback). `RESOURCES.md` updated.
  - Regenerated `agent/main.py` via `scripts/build_agent.py` (`STRATEGY`
    unchanged, still `wheat_loop_hands_agent` — only its body changed).
- 2026-08-22 — `notebooks/08_melon_hand.ipynb`: first increment on the
  "Per-tile crop choice by ROI" roadmap item — deliberately not the ROI
  logic itself (needs melon's sell-price behavior, not yet explored),
  just proving the multi-crop mechanism works. One fixed hand (index 4,
  the single-tile `(4,2)` zone in `HAND_ZONES`) grows `MELON` instead of
  `WHEAT`; farmer and hands 0-3 unchanged.
  - Read `CROPS` off the installed `kaggle_environments` package (not
    transcribed): `MELON` costs $80/seed vs. $10 for `WHEAT`, isn't
    `ongoing` (one harvest per planting), and `first_yield_day` is 10 vs.
    2 — so the harvest threshold had to branch per hand instead of the
    hardcoded `crop_age >= 2` every prior agent used.
  - **Bug found via instrumented episode, not assumed**: the first working
    draft printed nothing when logging `tile(4,2)`'s state over a full
    episode — `melon_seeds` never dropped below 2 across 3 full days, and
    hands 0/2/4 stayed permanently glued to one shared tile all day.
    Root cause, confirmed by reading the installed engine source
    (`kaggriculture.py::_apply_unit_action`): each turn's `PLANT` actions
    apply in a fixed unit order (farmer, then hands by index), and a
    `PLANT` silently no-ops if the tile is no longer empty by the time
    that unit's turn comes — so on any tile shared with a lower-indexed
    hand, hand 4 (melon) lost the plant race every single time. This is
    separate from `AGENTS.md`'s documented "not enough seed for N
    simultaneous PLANT requests" rule. Every hand (0-3 too) previously
    tended *any* empty tile it merely passed through on the shared
    `LOOP_ORDER_HANDS` transit path — harmless when every hand wants the
    same crop, not once one hand wants something different.
  - Fix: `in_own_zone` check — a hand now only tends
    (`PLANT`/`WATER`/`HARVEST`) a tile that's a key in its own
    `HAND_ZONES` entry; elsewhere it just moves through. This also
    removes hands 0-3's previous opportunistic tending of shared transit
    tiles, so the validation below compares two changes at once (melon
    hand + zone-restricted tending) rather than isolating attribution,
    consistent with this project's "compare against current best as a
    whole" convention. `RESOURCES.md` updated with the engine-source
    finding.
  - Validated against the current best,
    `evaluate(wheat_loop_hands_agent, wheat_loop_melon_agent, n=20)` →
    `win_rate=0.0` for `wheat_loop_hands_agent` across two independent
    calls (`avg_money` 5857.0 and 6488.0 for the losing baseline).
    Graduated to
    `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_melon_agent`,
    11 new unit tests in `tests/test_baseline.py` (melon seed buy/no-buy,
    plant/harvest at melon's own threshold vs. wheat's, sell, and two
    regression tests for the `in_own_zone` fix — a wheat hand and the
    melon hand both refusing to tend a shared transit tile outside their
    own zone).
  - Regenerated `agent/main.py` via `scripts/build_agent.py` (switched
    `STRATEGY` to `wheat_loop_melon_agent`), validated standalone against
    `wheat_loop_hands_agent` the same way as the 2026-08-19/2026-08-21
    entries: `win_rate=0.0`, `avg_money=6136.0` — confirms the generated
    file behaves identically to the graduated `src/` version. **Not yet
    submitted to Kaggle.**
- 2026-08-22 — Submitted v4 (`agent/main.py`, `wheat_loop_melon_agent`,
  1-tile melon hand) to Kaggle. Lost to `Barathan Aslan`, 6698 vs 31477
  (episode 96612755, saved to `replays/`). Analyzed the same way as prior
  submissions:
  - Confirms the 1-tile melon design worked exactly as built: only 3
    `PLANT MELON` orders across the whole game (vs. 194 `PLANT WHEAT`) —
    one tile, one ~10-day cycle, ~3 harvests possible in a 30-day season.
  - **New finding**: of the 25 NW tiles, exactly one is never planted the
    entire game — `(4,3)`, right next to the respawn tile `(4,4)`.
    Tracking the farmer's own position turn by turn (not assumed) showed
    it never visits `(4,3)` even once in 720 turns: early `LOOP_ORDER_12`
    tiles get visited on almost every one of the 30 days (~89 times
    each), but the count drops off fast toward the loop's end — `(3,3)`
    only 2 times, `(4,3)` zero. Root cause: the farmer resets to `(4,4)`
    every day (game rule) and a full 12-tile lap plus harvest/water
    rarely fits in the ~24-turn day budget, so the last tiles before
    wrapping around are systematically starved. This is a gap in
    `LOOP_ORDER_12` itself, present since 2026-08-19 — it was hidden
    until now because hands used to opportunistically tend `(3,3)`/`(4,3)`
    while passing through on shared `LOOP_ORDER_HANDS` transit (both are
    nodes in that graph too); the `in_own_zone` fix logged above removed
    that accidental coverage and exposed the real gap.
  - Fix (`notebooks/08_melon_hand.ipynb`, same day): `MELON_HAND_ZONES`,
    a new constant (not a `HAND_ZONES` mutation — `wheat_loop_hands_agent`
    stays untouched, same reasoning as keeping `LOOP_ORDER_2X2` separate
    from `LOOP_ORDER_12`). Hand 4's zone grows from a single self-looping
    tile to the closed 2x2 block `(4,2)-(4,3)-(3,3)-(3,2)`, plugging the
    farmer-loop gap as a real own-zone tile and quadrupling melon's tile
    capacity in the same change. `RESOURCES.md` updated.
  - Validated against the current best (`wheat_loop_melon_agent`, 1-tile):
    `win_rate=0.0` across two independent `evaluate()` calls (`avg_money`
    8350.0 and 8553.0 for the losing, 1-tile side). Graduated in place
    into `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_melon_agent`
    (same function name, now built on `MELON_HAND_ZONES`), 3 new unit
    tests in `tests/test_baseline.py` (zone disjointness/cycle validity,
    tending all 4 zone tiles not just the original one) plus one existing
    test updated (hand 4 now moves within its zone instead of `PASS`ing
    on a single tile). Regenerated `agent/main.py` (`STRATEGY` unchanged).
    **Not yet submitted to Kaggle.**
- 2026-08-22 — Revisited the episode 96612755 replay (opponent
  `Barathan Aslan`, our v4 submission) to check the opponent's own
  `PLANT`/`SELL` actions, not just ours: they planted `MELON` 45 times
  and sold 220 units for **~$25,594 — 81% of their $31,477 final money**
  (first sale day 10, 12 units at full $250 base price). Melon isn't a
  side crop for this opponent, it's the majority of their win. Our own
  4-tile melon hand is far too small to compete at that scale.
  - `notebooks/09_melon_rush.ipynb`: tested the other extreme —
    `melon_rush_agent`, every unit (farmer + up to 5 hands) grows MELON
    exclusively, reusing `wheat_loop_hands_agent`'s structure with
    `WHEAT` -> `MELON` and threshold `2` -> `10` everywhere (not just one
    hand). Beats `wheat_loop_melon_agent` 20/20 across two independent
    `evaluate()` calls (`avg_money` 16219.0 and 15216.0 for the losing
    side). Real risk confirmed via an instrumented episode, not assumed:
    money drops to **$68** by day 11 (no income before day 10) before
    exploding to $17,068 by day 14 as the first melon harvests sell.
    Graduated to
    `src/kaggriculture_bot/strategies/baseline.py::melon_rush_agent`, 10
    new unit tests in `tests/test_baseline.py`. `RESOURCES.md` updated.
  - Spike (same day, before designing further): read `market_price`/
    `_town_consume` directly from the installed engine rather than
    simulate a full episode. Confirmed MELON's price does **not**
    recover within a season once crashed — no shop buys MELON (only
    `TOWN_CENTER_PRODUCTS`, draining ~140 units over 720 turns), while
    the price already hits the $1 floor around 150-200 cumulative units
    sold. Simulated selling sequentially: 24 units nets $5,958 (avg
    $248/unit), 100 units nets $21,721 (avg $217/unit), 200 units only
    $26,527 total (avg $133/unit, floor hit at unit #158) — so a
    "dump-wait-dump again" cycle doesn't work, but permanently switching
    new plantings away from MELON once it's no longer worth it does.
  - `notebooks/10_melon_then_wheat.ipynb`: `melon_then_wheat_agent` —
    MELON for the first 10 days (matches `first_yield_day`, a hard floor
    for everyone), WHEAT from day 10 onward, applied uniformly to every
    unit. Harvest threshold reads each tile's own `crop` field rather
    than the current phase, so MELON planted before the switch still
    matures on its own schedule; seed purchases and shed sales are
    tracked for both crops independently, so nothing goes to waste and
    nothing gets missed during the transition. Beats `melon_rush_agent`
    20/20 across two independent `evaluate()` calls (`avg_money` 16711.0
    both times — confirmed as two genuinely separate runs, not a
    duplicated paste). Graduated to
    `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_agent`,
    12 new unit tests in `tests/test_baseline.py` (crop/seed/threshold/sell
    switching correctly by day, and the tile-crop-not-phase harvest
    regression). `RESOURCES.md` updated.
  - **Extended same day**: noticed the agent still sells 1 unit/turn
    (inherited from `wheat_loop_agent`'s 2026-08-10 convention). Read the
    engine's per-unit lockstep market loop directly: a `SELL <crop> N`
    order is processed one unit at a time internally regardless of N, so
    from a single player's own selling alone, dumping the full shed and
    trickling 1/turn give identical revenue — but since the market is
    shared and episode 96612755 showed the opponent sells a lot of melon
    too, every turn spent holding inventory is a turn where *their*
    selling can degrade price first. Switched both `SELL WHEAT`/
    `SELL MELON` to dump the full shed amount instead of 1. Re-validated
    against the then-current best (this same agent, 1-unit-per-turn):
    `win_rate=0.0` across two independent `evaluate()` calls (`avg_money`
    13514.0 and 13751.0 for the losing side). Graduated in place (same
    function name), 2 existing tests updated to expect the full shed
    amount instead of 1. `RESOURCES.md` updated. Regenerated
    `agent/main.py` (`STRATEGY` unchanged, only the body changed).
    **Not yet submitted to Kaggle.**
- 2026-08-22 — `notebooks/11_buy_land_ne.ipynb`: explored `BUY_LAND` (no
  hard cap on hands in the engine either -- `_do_hire` only checks
  affordability, confirmed reading `kaggriculture.py` directly -- filed
  as a separate idea below). Bought NE (`LAND_ORDER = ["NE","SW","SE"]`,
  `LAND_PRICES = [1000,2000,4000]`) once `crop_to_plant == "WHEAT" and
  money >= 1000` (gating on the phase, not just the raw threshold --
  starting money is already $3000, so a bare `money >= 1000` check would
  fire on turn 0), then relocated hands 3 and 4 from their small NW
  zones to a freshly-designed NE loop/zones (not a coordinate mirror of
  `LOOP_ORDER_HANDS` -- that broke, see below).
  - **Bug found and fixed**: first attempt mirrored `LOOP_ORDER_HANDS`
    into NE by shifting `x + 5`. Crashed with `KeyError: (5, 4)`.
    Root cause: `LOOP_ORDER_HANDS` only covers tiles the *hands* need,
    deliberately excluding what the farmer's own `LOOP_ORDER_12` already
    covers in NW -- its "entry" key `(4,4)` is NW's innermost corner,
    which shifts to `(9,4)`, NE's *farthest* corner, not the near one;
    `(5,4)` (NE's real near corner) was never a key in the shifted dict
    at all. Fixed by designing NE's loop directly instead of mirroring:
    a 16-tile loop around the NE block's border, entering at `(5,4)`,
    with hands 3/4 peeling into their own private 2x2 zones
    (`ZONE_3_NE`/`ZONE_4_NE`) -- verified directly (closed-cycle checks,
    disjointness, reachability from all 4 spawn corners), not just by
    construction. Also added a merged NW+NE fallback for the one-turn
    edge case where NE unlocks mid-day while a hand is still physically
    in NW territory.
  - **Result: lost 20/20** to `melon_then_wheat_agent` (`win_rate=1.0`
    for the baseline). Diagnosed with a real replay-diff, not guessed:
    replaying the land-agent's actual observations through the baseline
    function turn by turn found **zero divergence** in the melon phase
    (days 0-9) -- confirms no code bug, the loss is economic. Money
    trajectory from an instrumented episode: gap is $1160 right after
    buying NE (day 12) but narrows to just $141 by day 29 -- NE's wheat
    *is* profitable, but land is only affordable this late (~day 12,
    once melon money arrives) and doesn't have enough of the ~18
    remaining days to fully repay the $1000 outlay from just 2 hands'
    worth of low-value WHEAT before the season ends.
  - **Follow-up idea, not yet built**: since hiring has no hard cap,
    hire 2 *extra* hands (indices 5/6) dedicated to NE instead of
    relocating hands 3/4 away from NW -- NW keeps its current coverage
    entirely, NE becomes pure upside minus the incremental Fibonacci
    hiring cost (cheap: hands 6/7 cost 8+13=21/day extra, vs. the $1000
    land cost itself). Paused here for the day; `melon_then_wheat_agent`
    (without land) is the version being submitted next, not the land
    variant. Geometry (`LOOP_ORDER_HANDS_NE`/`ZONE_3_NE`/`ZONE_4_NE`/
    `SPAWN_FEEDER_NE`) is already built and validated in the notebook,
    reusable for the extra-hands version.
- 2026-08-23 — `notebooks/12_buy_land_extra_hands.ipynb`: built the
  follow-up idea queued in the entry above — hire 2 *extra* hands
  (indices 5, 6) dedicated to NE once it's bought, instead of relocating
  hands away from NW. Hands 0-4 (NW) stay exactly as in
  `melon_then_wheat_agent`; NE becomes pure upside.
  - Mini-test finding (real obs, not assumed): a newly hired hand always
    spawns on one of the same 4 shed-access corners
    (`(4,4)`,`(5,4)`,`(4,5)`,`(5,5)`), whether or not NE is unlocked — no
    "5th NE corner" appears. Those 3 non-`(5,4)` corners are exactly
    `SPAWN_FEEDER_NE`'s keys (reused as-is from notebook 11), so hands 5/6
    route straight into NE without needing NW's own `SPAWN_FEEDER` merged
    in — simpler than notebook 11's relocated-hands case, since 5/6 are
    only ever hired *after* NE is already unlocked.
  - New finding: a single closed loop can't cover NE's 25 tiles split
    between only 2 hands as two even halves, because a closed cycle
    visiting every tile exactly once needs an even tile count (grid
    adjacency is bipartite/checkerboard — each step flips color). Split
    by rows instead: `ZONE_TOP_NE` (`y=0-1`, 10 tiles, no interior tile so
    its border alone is a valid cycle) and `ZONE_BOTTOM_NE` (`y=2-4`, 15
    tiles minus `(8,3)` = 14, the interior tile with no entry-point role
    dropped to reach an even count). NE ends up with 24/25 tiles tended,
    one deliberate gap.
  - Several real bugs found and fixed while writing the agent (not just
    typos — logic errors that would have silently broken the feature):
    two independent `HIRE` conditions that could both fire the same turn
    once NE was unlocked (double-hiring); the raised hire cap nested
    inside `BUY_LAND`'s `unlocked_quadrants == 1` condition, made
    unreachable by a second, contradictory `> 1` check on the same
    nesting; `BUY_LAND` missing the `crop_to_plant == "WHEAT"` gate
    (would fire turn 0, spending the starting $3000 before any melon
    income); zone assignment using `i == 3` inside a branch already
    restricted to `i in (5, 6)` (both hands would have used
    `ZONE_BOTTOM_NE`, leaving `ZONE_TOP_NE` completely uncovered);
    `in_own_zone` still checking `HAND_ZONES` instead of the branch's own
    `own_zone` variable; and the seed-purchase buffer left at 6 (tuned for
    farmer + 5 hands) despite the hire cap now reaching farmer + 7.
  - Validated via `evaluate.py` against the current best,
    `melon_then_wheat_agent`: `win_rate=0.0` for the baseline across two
    independent `evaluate()` calls (`avg_money` 14569.0 and 14403.0 for
    the losing side) — beats even `melon_then_wheat_land_agent`'s
    relocated-hands approach, which lost outright. Graduated to
    `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_extra_hands_agent`,
    17 new unit tests in `tests/test_baseline.py`. `RESOURCES.md` updated.
    Wired into `agent/main.py` (`STRATEGY` switched to
    `melon_then_wheat_extra_hands_agent`). **Not yet submitted to Kaggle.**
- 2026-08-23 — Watched a local `kaggle_environments` simulation of the
  2-hand NE version above and found real NE tiles going untended for
  extended stretches — confirmed quantifiable, not just visual: hand 6's
  zone (the old `ZONE_BOTTOM_NE`, 14 tiles) already exceeded the
  ~12-tiles/day per-unit ceiling `wheat_loop_12_agent` was originally
  sized against (24 turns/day, ~2 turns/tile) — that check just hadn't
  been applied to the new NE zones when they were first built. Added a
  3rd NE hand (index 7) and split `ZONE_BOTTOM_NE`'s 14 tiles by column
  instead of leaving them to one hand: `ZONE_LEFT_NE` (`x=5-6`, 6 tiles,
  a 2-column block with no interior, same shape as `ZONE_TOP_NE`) and
  `ZONE_RIGHT_NE` (`x=7-9` minus `(8,3)`, 8 tiles — turns out to be
  exactly the border ring of a 3x3 block around the `(8,3)` gap, also
  interior-free, so no detour needed for either piece). Hire cap raised
  5→8 (from 5→7); seed buffer raised 8→9 (farmer + up to 8 hands).
  - **Explicit exception to the "must clear evaluate.py's gate" rule**:
    head-to-head `evaluate()` against the 2-hand version came back
    contradictory across two independent runs (`win_rate=1.0` for the
    2-hand version, then `win_rate=0.0` — `avg_money` 20153.0/20882.0) —
    inconclusive, not a clean win either way, the first time in this
    project a graduated change didn't clear that gate. Adopted anyway, by
    explicit project-owner decision, on the capacity-ceiling argument
    above rather than the metric. Flagged here and in the function's
    docstring rather than silently overriding the usual rule.
  - Graduated in place into
    `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_extra_hands_agent`
    (same function name, `ZONE_BOTTOM_NE` replaced by
    `ZONE_LEFT_NE`/`ZONE_RIGHT_NE`), tests in `tests/test_baseline.py`
    updated/extended for the 3rd hand (own-zone regression checks for
    hands 5/6/7, hire cap up to 8, seed buffer up to 9).
    `RESOURCES.md` updated. Regenerated `agent/main.py` (`STRATEGY`
    unchanged, only the body changed). **Not yet submitted to Kaggle.**

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
- [x] Hire farm hands daily (cheap — Fibonacci cost resets each day) and
      give each the same tile-tending logic as the farmer — biggest single
      lever seen in both the HechtJP (2026-08-13) and Muhammed Ali Kul
      (2026-08-20) replays. Graduated as `wheat_loop_hands_agent`, wired
      into `agent/main.py`. Found and fixed a real bug the same day
      (2026-08-21 log entries): hands were permanently merging onto one
      tile; fixed with `HAND_ZONES` (per-hand disjoint private loops) —
      beats the un-zoned version decisively, 20/20 across three runs.
- [x] **Per-tile crop choice (first increment)** — one fixed hand (index
      4) grows MELON instead of WHEAT, no ROI comparison yet, graduated
      as `wheat_loop_melon_agent` (see 2026-08-22 log entry). Beats
      `wheat_loop_hands_agent` decisively, 20/20 across two runs. Wired
      into `agent/main.py`, submitted as v4 — lost to `Barathan Aslan`
      (episode 96612755), replay analysis revealed and fixed a real gap
      in `LOOP_ORDER_12` (see next bullet).
- [x] **Per-tile crop choice (second increment)** — extended hand 4 from
      a single melon tile to a 2x2 zone (`MELON_HAND_ZONES`), which also
      plugs the `(4,3)` farmer-loop gap found in the v4 replay. Beats the
      1-tile version decisively, 20/20 across two runs. Regenerated
      `agent/main.py`, not yet submitted to Kaggle.
- [x] **Melon rush (third increment)** — every unit grows MELON from turn
      0 instead of one hand, motivated by a real opponent replay showing
      melon as 81% of their winning money. Graduated as `melon_rush_agent`
      (see 2026-08-22 log entry). Beats `wheat_loop_melon_agent`
      decisively, 20/20 across two runs.
- [x] **Melon then wheat (fourth increment)** — one-way day-based switch
      (MELON days 0-9, WHEAT from day 10) instead of pure rush, since a
      spike confirmed MELON's crashed price never recovers within a
      season. Graduated as `melon_then_wheat_agent` (see 2026-08-22 log
      entry). Beats `melon_rush_agent` decisively, 20/20 across two runs.
      Extended same day: sell the full shed at once instead of 1/turn
      (matters against a shared market with a melon-selling opponent).
      Wired into `agent/main.py`, not yet submitted to Kaggle.
- [x] **Buy land (NE)** — first attempt (relocating hands 3/4 to NE) lost
      20/20 to `melon_then_wheat_agent`, economic not a bug: land only
      affordable ~day 12, too few days to repay $1000 from 2 hands' WHEAT
      (2026-08-22 log entry). Follow-up idea — hire 2 *extra* hands
      (indices 5, 6) dedicated to NE instead of relocating, so NW coverage
      never drops — built and validated 2026-08-23:
      `melon_then_wheat_extra_hands_agent` beats `melon_then_wheat_agent`
      decisively, 20/20 across two runs (see 2026-08-23 log entry for the
      real bugs found and fixed along the way, plus the checkerboard
      parity finding behind `ZONE_TOP_NE`/`ZONE_BOTTOM_NE`'s tile split).
      Extended same day to a 3rd NE hand after watching a local replay
      show real coverage gaps, traced to hand 6's zone exceeding the
      ~12-tiles/day per-unit ceiling — `ZONE_BOTTOM_NE` split into
      `ZONE_LEFT_NE`/`ZONE_RIGHT_NE`. Adopted despite an inconclusive
      head-to-head `evaluate()` against the 2-hand version (contradictory
      across two runs), an explicit exception to the usual validation
      gate — see the second 2026-08-23 log entry. Wired into
      `agent/main.py`. **Not yet submitted to Kaggle.**
- [ ] Per-tile crop choice by ROI (the Yield/tile/day column in README.md)
      — actually compare $/tile/day across crops (needs melon's — and
      other crops' — sell-price behavior, not yet explored) instead of a
      fixed hand-to-crop assignment; extend beyond MELON to
      CARROT/TOMATO/STRAWBERRY
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
