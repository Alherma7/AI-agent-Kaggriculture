# Resources

Every strategy/heuristic added to `src/kaggriculture_bot/strategies/` needs
an entry here (per `structuring-ml-projects` step 3) explaining why it
applies to this game specifically — a paper, a comparable bot-competition
writeup, or a Kaggle forum post. Cite the entry's short name in the
function's docstring.

## Official competition sources

- **Kaggriculture README.md** (competition kit, root of this repo)
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
