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
