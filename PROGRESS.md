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

## Next steps

Roadmap in increasing agent complexity — each level only starts once the
previous one has cleared `evaluate.py`'s gate and been logged here.

### Level 0 — Foundations + evaluation harness

- [ ] Notebook `01_explore_env.ipynb`: play random/starter episodes, inspect
      a raw `obs` dict and a `replay.json`
- [ ] Transcribe the Object Types / Price Function tables from `README.md`
      into `src/kaggriculture_bot/config.py` as the single source of truth
- [ ] Build `state.py` / `actions.py` helpers (parse `obs`, build valid
      action dicts)
- [ ] Build `evaluate.py`: run N episodes vs. `"random"` and `"starter"`
      built-in agents, report win rate + average final money — this is the
      gate every later change must clear (`structuring-ml-projects` step 6)
- [ ] Join the competition on kaggle.com and download the kit data (blocked
      on CLI auth for now, see above — website works meanwhile)

### Level 1 — Baseline heuristic agent

- [ ] Notebook `02_baseline_wheat_loop.ipynb`: validate the AGENTS.md
      wheat-loop example against `evaluate.py`
- [ ] Graduate to `agent/main.py`, submit v1, log the leaderboard result here

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
