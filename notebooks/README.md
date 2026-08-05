# Notebooks

Numbered, one per exploration/validation round (see `structuring-ml-projects`
skill). A finding only graduates to `src/kaggriculture_bot/` once it's a
named function with a cited docstring, validated against `evaluate.py`'s
win-rate/score harness, showed a win, and has a unit test.

Planned:

- `01_explore_env.ipynb` — play with `kaggle_environments.make("kaggriculture")`,
  inspect a raw `obs` dict, render a random-vs-random game
- `02_baseline_wheat_loop.ipynb` — validate the AGENTS.md wheat-loop example
  against `"random"` and `"starter"` opponents
- `NN_<idea>.ipynb` — one per new strategy under test
