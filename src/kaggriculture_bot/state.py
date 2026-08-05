"""Parse the raw `obs` dict (AGENTS.md Observation Format) into whatever
shape strategy functions find convenient (e.g. own farm vs. opponent farm,
tile lookups by type). Pure functions only — no side effects, so this is
straightforward to unit test in tests/test_state.py.
"""
