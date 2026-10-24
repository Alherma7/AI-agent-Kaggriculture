# Resources

Every strategy/heuristic added to `src/kaggriculture_bot/strategies/` needs
an entry here (per `structuring-ml-projects` step 3) explaining why it
applies to this game specifically — a paper, a comparable bot-competition
writeup, or a Kaggle forum post. Cite the entry's short name in the
function's docstring.

## Official competition sources

- **Kaggriculture README.md** (competition kit; moved to `docs/GAME_RULES.md` on 2026-10-24)
  Why: authoritative game rules — object types, market price function,
  turn processing order, win condition. Ground truth for `config.py`.
- **Kaggriculture AGENTS.md** (competition kit, root of this repo)
  Why: agent function signature, observation/action format, local test
  harness (`kaggle_environments`), CLI submission workflow. Source of the
  first baseline (wheat-loop) example, graduated to
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_agent`
  (validated in `notebooks/03_baseline_wheat_loop.ipynb`, tested in
  `tests/test_baseline.py`). The graduated version follows the source's
  HARVEST-before-WATER priority exactly, but deviates on selling: 1
  unit/turn instead of dumping the whole shed, per the sell-all-vs-sell-one
  test logged in `PROGRESS.md` (2026-08-10).

- **Kaggriculture leaderboard replay `92035136.json`** (downloaded from
  kaggle.com, our v1 submission vs. `HechtJP`; analyzed 2026-08-13,
  logged in `PROGRESS.md`)
  Why: showed the concrete gap between `wheat_loop_agent` and a real
  winning opponent — a farmer that moves and tends multiple tiles beats
  one that camps a single tile, regardless of crop choice. Source for
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_2x2_agent`
  (validated in `notebooks/05_farmer_movement.ipynb`, tested in
  `tests/test_baseline.py`): reuses `wheat_loop_agent`'s own
  harvest > water > plant priority at each tile, adding "move to the next
  tile in a closed 2x2 loop" as the fallback once a tile needs nothing
  more today.
- **`README.md`'s `turnsPerDay` (24) and movement/action cost rules**
  Why: source for the ~12-tiles/day ceiling (24 turns / ~2 turns per new
  tile) that motivated
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_12_agent`
  (validated in `notebooks/06_farmer_movement_12_tile_loop.ipynb`, tested
  in `tests/test_baseline.py`): same design as `wheat_loop_2x2_agent`,
  with `LOOP_ORDER_2X2` swapped for a 12-tile closed loop
  (`LOOP_ORDER_12`) that pushes deliberately to that ceiling rather than
  an arbitrary size.

- **Kaggriculture leaderboard replays `92035136.json`/`94568249.json`**
  (our v1/v2 submissions vs. `HechtJP`/`Muhammed Ali Kul`; analyzed
  2026-08-13/2026-08-20, logged in `PROGRESS.md`) plus
  `kaggriculture.py::_do_hire`/`_hire_cost`/`_spawn_hand` (engine source,
  read directly, not assumed -- see `notebooks/07_farm_hands.ipynb`'s
  mini-tests)
  Why: both replays showed multiple farm hands as the single biggest gap
  vs. real opponents (up to 10 hands vs. our 0); the engine confirms
  hiring is effectively free (Fibonacci cost resets daily) and that hands
  spawn at the least-occupied shed corner, not always `(4,4)`. Source for
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_hands_agent`
  (validated in `notebooks/07_farm_hands.ipynb`, tested in
  `tests/test_baseline.py`): hires up to 5 hands/day and gives each
  `wheat_loop_12_agent`'s own harvest > water > plant > move priority
  against a second loop (`LOOP_ORDER_HANDS`), with a `"LOCKED"`-tile guard
  and `SPAWN_FEEDER` for hands that spawn off that loop.

- **Instrumented episode replays (own local runs) + the Muhammed Ali Kul
  leaderboard replay's overlap pattern** (analyzed 2026-08-21, logged in
  `PROGRESS.md`)
  Why: found that `wheat_loop_hands_agent`'s first graduated version had
  all 5 hands permanently merge onto one tile within a few turns of the
  day -- a one-turn tile collision became forever-identical behavior,
  since every hand's action was a pure function of its current tile with
  nothing distinguishing one hand from another. The real opponent replay
  showed transient overlaps that always resolved within 2 turns, which
  motivated the fix: `HAND_ZONES`, giving each hand index its own
  private, pairwise-disjoint loop, so a permanent merge is structurally
  impossible once a hand settles into its zone. Source for the current
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_hands_agent`
  (validated in `notebooks/07_farm_hands.ipynb`, tested in
  `tests/test_baseline.py`).

- **`kaggriculture.py::_apply_unit_action`/turn-processing loop** (engine
  source, read directly, not assumed -- see `notebooks/08_melon_hand.ipynb`)
  Why: explains a same-tile `PLANT` race that isn't documented in
  `README.md`/`AGENTS.md`: each turn, units apply in a fixed order
  (farmer, then hands by index), and `PLANT` re-checks the tile fresh for
  each unit -- so if two units share a tile, only the lowest-indexed one
  actually plants; the rest silently no-op. Separate from `AGENTS.md`'s
  documented "not enough seed for N simultaneous PLANT requests" rule.
  Source for the `in_own_zone` fix in
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_melon_agent`
  (validated in `notebooks/08_melon_hand.ipynb`, tested in
  `tests/test_baseline.py`): hand 4 (melon) always lost this race against
  lower-indexed wheat hands on shared `LOOP_ORDER_HANDS` transit tiles, so
  a hand now only tends a tile that's a key in its own `HAND_ZONES` entry.

- **Kaggriculture leaderboard replay `96612755.json`** (our v4 submission,
  `wheat_loop_melon_agent` 1-tile melon, vs. `Barathan Aslan`; analyzed
  2026-08-22, logged in `PROGRESS.md`)
  Why: showed only one NW tile is never planted the whole game --
  `(4,3)`, next to the respawn tile -- and that the farmer's own
  `LOOP_ORDER_12` never once visits it in 720 turns (daily reset to
  `(4,4)` means the loop rarely finishes a full lap, so its last tiles
  starve). A pre-existing gap in `LOOP_ORDER_12` (2026-08-19), only
  exposed once hands stopped opportunistically covering it. Source for
  `MELON_HAND_ZONES` in
  `src/kaggriculture_bot/strategies/baseline.py::wheat_loop_melon_agent`
  (validated in `notebooks/08_melon_hand.ipynb`, tested in
  `tests/test_baseline.py`): hand 4's zone grew from a single
  self-looping tile to the 2x2 block `(4,2)-(4,3)-(3,3)-(3,2)`, plugging
  the gap and quadrupling melon's tile capacity.

- **Kaggriculture leaderboard replay `96612755.json`, revisited** (opponent
  `Barathan Aslan` action log, analyzed 2026-08-22, logged in
  `PROGRESS.md`)
  Why: showed melon isn't a side crop for a real winning opponent — 220
  units sold for ~$25,594, **81% of their $31,477 final money**, starting
  exactly day 10 (`MELON`'s `first_yield_day`, a hard floor for both
  players since the market is shared). Source for
  `src/kaggriculture_bot/strategies/baseline.py::melon_rush_agent`
  (validated in `notebooks/09_melon_rush.ipynb`): every unit grows MELON
  from turn 0 instead of one hand, beats `wheat_loop_melon_agent` 20/20.
- **`kaggriculture.py::market_price`/`_town_consume`, read directly** (not
  assumed; a spike run 2026-08-22, logged in `PROGRESS.md`)
  Why: confirmed MELON's crashed price does *not* recover within a
  season — no shop buys MELON (only the town center does, draining ~140
  units over 720 turns, versus the ~150-200 units it takes to crash the
  price in the first place) — so a "dump then wait then dump again" cycle
  doesn't work, but a one-way switch away from MELON once its marginal
  price craters does. Source for
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_agent`
  (validated in `notebooks/10_melon_then_wheat.ipynb`, tested in
  `tests/test_baseline.py`): MELON for the first 10 days, WHEAT from day
  10 onward (a day cutoff instead of a price threshold, since MELON's
  `first_yield_day=10` already pins the timing precisely) — beats
  `melon_rush_agent` 20/20.

- **`kaggriculture.py`'s per-unit lockstep market loop, read directly**
  (not assumed; found 2026-08-22, logged in `PROGRESS.md`)
  Why: a single `SELL <crop> N` order is processed one unit at a time
  internally, re-quoting the price after each — so from a single
  player's own selling alone, dumping a full shed and trickling 1/turn
  are mathematically identical. But the market is shared, and episode
  96612755 showed the opponent sells a lot of melon too, so every turn
  spent holding shed inventory instead of selling is a turn where *their*
  selling can degrade the price first. Source for the sell-the-whole-shed
  change to
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_agent`
  (validated in `notebooks/10_melon_then_wheat.ipynb`, tested in
  `tests/test_baseline.py`) — reverses the 2026-08-10 sell-1-unit-per-turn
  choice, which was tested only for WHEAT against non-melon-selling
  baselines and found inconclusive there.

- **`kaggriculture.py::_spawn_hand`, read directly** (mini-test in
  `notebooks/12_buy_land_extra_hands.ipynb`, 2026-08-23) plus a
  grid-graph parity argument (own reasoning, not sourced)
  Why: confirmed a newly hired hand always spawns on the same 4
  shed-access corners regardless of how many quadrants are unlocked — no
  "5th NE corner" appears once NE is bought — so `SPAWN_FEEDER_NE` (reused
  from notebook 11) covers hands 5/6's spawn routing on its own, no NW
  merge needed. Separately: a closed cycle that visits every tile exactly
  once needs an even tile count, since grid adjacency is
  bipartite/checkerboard-colored (each step flips color, so returning to
  the start after visiting every tile requires an even number of steps) —
  this is why NE's 25 tiles can't split evenly between 2 hands' zones,
  forcing the one-tile gap in `ZONE_BOTTOM_NE`. Source for
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_extra_hands_agent`
  (validated in `notebooks/12_buy_land_extra_hands.ipynb`, tested in
  `tests/test_baseline.py`): hires 2 extra hands (indices 5, 6) dedicated
  to NE once bought, instead of relocating hands away from NW (the
  `notebooks/11_buy_land_ne.ipynb` approach that lost 20/20) — beats
  `melon_then_wheat_agent` decisively.

- **A local `kaggle_environments` simulation replay, watched directly**
  (own observation, 2026-08-23) plus the same `wheat_loop_12_agent`
  ~12-tiles/day ceiling cited above
  Why: showed the 2-hand NE version leaving real tiles untended for
  extended stretches — and the reason was quantifiable, not just visual:
  hand 6's zone (14 tiles, one hand) already exceeded the same
  ~12-tiles/day per-unit capacity ceiling `wheat_loop_12_agent` was
  originally sized against, a check that hadn't been re-applied when the
  NE zones were first built. Source for the 3-hand NE split in
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_extra_hands_agent`
  (`ZONE_LEFT_NE`/`ZONE_RIGHT_NE` replacing `ZONE_BOTTOM_NE`, tested in
  `tests/test_baseline.py`) — adopted on this capacity argument despite
  an inconclusive head-to-head `evaluate()` against the 2-hand version
  (contradictory across two independent runs), an explicit,
  project-owner-approved exception to this project's usual "must clear
  evaluate.py's gate" rule.

- **`kaggriculture.py`, read directly** (`_apply_unit_action`,
  `_is_shed_adjacent`, `_daily_refresh_animals`, `_commit_unit`'s
  `BUY_PRODUCT` branch, `_end_of_day`'s `_drop_inventories_to_shed`) —
  mini-tests and trace debugging in `notebooks/13_goose.ipynb`,
  2026-08-27
  Why: confirmed several mechanics not documented in `AGENTS.md`/`README.md`
  in enough detail to code against blind — standing on a `"LOCKED"` tile
  silently no-ops any non-move action (not just tile-tending ones);
  `PICKUP`/`DROP` require standing on one of the 4 shed-adjacent corners;
  a placed animal escapes after `consecutive_unfed >= 2`; `BUY_PRODUCT`
  (`WHEAT`/`FERTILIZER` only) deposits straight into the shed, not the
  buyer's inventory; and all held inventory is auto-dropped into the shed
  at `_end_of_day`, before positions/inventories reset. Source for
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_goose_agent`
  (validated in `notebooks/13_goose.ipynb`, tested in
  `tests/test_baseline.py`): folds a goose/egg income stream into hand 4
  of `melon_then_wheat_agent`, beating it decisively (`win_rate=1.0`
  across two independent `evaluate()` calls). Two prior attempts logged
  as negative results in the same notebook and in `PROGRESS.md` rather
  than discarded: a dedicated 9th hand on NE land (lost 0/10, placement
  delayed to day 14) and an early fold-in that starved the goose before
  day 10 (no `WHEAT` exists during the melon phase) and then, once fixed
  with a `BUY_PRODUCT` order, missed its own turn budget for reaching the
  coop at all (diagnosed by an Opus-run instrumented A/B, not guessed).

- **`kaggriculture.py`'s `PRODUCTS` list, read directly** (not assumed;
  checked this session, extends `notebooks/13_goose.ipynb`)
  Why: confirmed `"FERTILIZER"` is a normal sellable product key, same as
  `"WHEAT"`/`"MELON"`/`"EGG"` — `COLLECT_FERTILIZER` adds to the acting
  unit's inventory under that exact string, which auto-drops to
  `obs["private"]["shed"]["FERTILIZER"]` at day's end like any other
  product. An instrumented episode showed it accumulating to 27 units by
  turn ~710 and never selling, matching a Kaggle validation-replay
  screenshot noted in `PROGRESS.md` (2026-08-27). Source for the
  `SELL FERTILIZER` addition to
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_goose_agent`
  (validated in `notebooks/13_goose.ipynb`, tested in
  `tests/test_baseline.py`): checked every turn next to `WHEAT`/`MELON`
  (farmer-level, unconditional) rather than gated on hand 4 having nothing
  else to do (the `SELL EGG` pattern) — hand 4 is busy with
  `FEED`/`COLLECT_FERTILIZER`/`CARE`/`HARVEST` on some turns, so the
  EGG-style gate would delay (in the worst case, indefinitely block)
  selling. Beats the ungated version 10/10 across two independent
  `evaluate()` calls.

- **`kaggriculture.py`'s `ANIMALS` table and `_daily_refresh_animals`, read
  directly** (not assumed; extends `notebooks/14_cow.ipynb`, this session)
  Why: confirmed `_daily_refresh_animals` and the
  `FEED`/`COLLECT_FERTILIZER`/`CARE`/`HARVEST` action handlers are the
  *same* function for `COOP` and `PASTURE` -- only `interval`/
  `first_yield_day`/`max_held` differ per animal in the `ANIMALS` table,
  and the agent's own logic never reads those values directly (unlike crop
  harvest thresholds, hardcoded per crop in every wheat/melon agent so
  far). This meant a second animal (`COW`/`MILK`, structure `PASTURE`)
  could skip the isolated mini-test stage the goose needed and go straight
  to a hand inside `melon_then_wheat_goose_agent`. Source for
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_goose_cow_agent`
  (validated in `notebooks/14_cow.ipynb`, tested in
  `tests/test_baseline.py`): hand 2 repurposed for the cow (mirrors hand 4
  for the goose, no new hire), `HAND_ZONES[2]` sacrificed for
  `PASTURE_TILE` since all 13 free NW tiles were already claimed. Beats
  `melon_then_wheat_goose_agent` decisively (`win_rate=1.0` across two
  independent `evaluate()` calls both in the notebook and after
  graduation), confirmed via an instrumented episode (not just money): 31
  `HARVEST` actions, 11 `SELL MILK` orders totaling 33 units, shed `MILK`
  capping at `COW`'s `max_held=6` and never overflowing.

- **`notebooks/kaggriculture-getting-started.ipynb`** (bovard, official Kaggle
  starter kernel)
  Why: confirms `obs` supports both `.get()` and dotted attribute access;
  ships `CROPS` and other game constants directly importable from
  `kaggle_environments.envs.kaggriculture.kaggriculture` (source for
  `config.py`); "Melon Maxxer" is a working single-crop reference agent
  (reward 6099 vs. 0 against `"random"`) with its own weaknesses listed by
  Kaggle: no hands/land expansion, single crop only, no fertilizing, dumps
  full shed in one sell order (crashes its own price). Those weaknesses map
  directly onto Level 2 of our roadmap in `PROGRESS.md`.

- **Kaggriculture leaderboard replay `replays/103962387.json`** (`ringbearer`
  105735 vs `islet` 135063, both far above our prior best ~31-32k; analyzed
  2026-08-31, logged in `PROGRESS.md`) plus explicit chat scope decision to
  infer generalizable rules rather than clone the opponent's replay trace
  (see the `kaggriculture-hamburger.ipynb` entry below)
  Why: both seats' near-identical strategy revealed the next real gaps
  beyond `melon_then_wheat_goose_cow_agent` -- a 3rd/4th crop, land+more
  hands on a fixed day schedule, a 2nd `PASTURE` animal, `FERTILIZE`
  applied, and `DIG`. Source for starting the roadmap with `STRAWBERRY`
  (an `ongoing` crop, `first_yield_day=10`, mixed sparingly into hands'
  existing zones in the replay rather than a dedicated hand) in
  `notebooks/15_leaderboard_agent.ipynb`. Also source for extracting
  `_tile_action` in
  `src/kaggriculture_bot/strategies/baseline.py` (deduplicating the
  4x-copied per-tile `HARVEST`/`WATER`/`PLANT` block so each new roadmap
  item -- `STRAWBERRY` here, `FERTILIZE`/`DIG`/`CARROT` later -- changes
  in one place; re-validated as a behavior-neutral refactor, `win_rate=0.5`,
  before any new behavior) and for `STRAWBERRY_TILE`'s single-fixed-tile
  placement: an `ongoing` tile never clears after `HARVEST`, so once
  `STRAWBERRY`'s `max_yield=4` lifetime units are collected the tile is
  dead weight until `DIG` (roadmap step 5, not built yet) can reclaim it --
  deliberately minimal for that reason.

- **`kaggriculture.py`'s `CROPS` table, `_new_plant`, the `WATER`/`HARVEST`
  action handlers, `_daily_refresh_plants`, and `_decay_plants`/
  `max_lifespan_step`, all read directly** (not assumed; extends
  `notebooks/15_leaderboard_agent.ipynb`) plus an Opus-run instrumented,
  seeded A/B (10 fixed seeds, reproducible; project owner's explicit "use
  Opus" call for this diagnosis)
  Why: confirmed non-`ongoing` crops (`WHEAT`/`MELON`) get 1 free
  `yield_units` at planting plus a bonus per day watered inside an
  inclusive window `[(max_yield_day+1)//2, max_yield_day]`, capped at
  `max_yield`; `ongoing` crops (`STRAWBERRY`) instead accumulate on a
  fixed schedule via `_daily_refresh_plants`, and the tile never clears
  after `HARVEST`. A first attempt at capturing `WHEAT`/`MELON`'s bonus
  window (wait until `crop_age > max_yield_day` before harvesting)
  regressed hard: that threshold is the exact step `_decay_plants` starts
  converting the tile toward `WEED`
  (`max_lifespan_step = (planted_day + max_yield_day + 1) * turns_per_day`),
  and `_tile_action` had no `WEED` branch, so 20/25 tiles were lost
  permanently in one 10-seed comparison; a second-order bug (the longer
  `WHEAT` cycle delayed the first harvest past the `BUY_PRODUCT WHEAT`
  backstop's `day < 10` cutoff, starving and losing the cow) compounded
  it. Source for the fix in
  `src/kaggriculture_bot/strategies/baseline.py::melon_then_wheat_goose_cow_strawberry_agent`
  (validated in `notebooks/15_leaderboard_agent.ipynb`, tested in
  `tests/test_baseline.py`): harvest at `crop_age >= max_yield_day` (not
  `>`), and the `BUY_PRODUCT WHEAT` backstop extended to `day < 13`.
  Ruled out as the mechanism: market-price crashing from bursty sells
  (identical `WHEAT` sale prices between variants at every sell) and hand
  2/4's opportunistic transit-tile tending (the pure `_tile_action`
  refactor's exact bit-for-bit tie already showed that wiring unchanged).

## Papers

(none yet)

## Comparable projects / competitions

- **`notebooks/kaggriculture-hamburger.ipynb`** (community, high-voted) —
  reviewed but **not used as a code source**. It's not a normal strategy
  writeup: it's an experiment-automation notebook whose base policy is
  labeled "Fixed public [player] policy from episode [id]" — i.e. an
  opponent's exact move sequence reconstructed from a *public episode
  replay*, then lightly tweaked and re-tested. Noting this as a fact about
  the competition's meta, not a technique to reuse: since Kaggle simulation
  competitions publish every episode's replay, cloning a leaderboard
  opponent's behavior from replay data is a known possibility. Our own
  agent is built from the rules directly, not reverse-engineered from other
  players' matches.
- Worth searching Kaggle forums for past simulation competitions such as
  Lux AI, Kore, Halite once a baseline is running: turn-based
  resource/economy games share a lot of strategic structure with this one.
