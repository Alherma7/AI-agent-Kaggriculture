"""This project's evaluation harness: run N episodes of a candidate agent
against fixed opponents (built-ins "random"/"starter", and previously
graduated versions of our own agent) and report win rate + average final
money. This is the gate every strategy change must clear before it's wired
into agent/main.py (structuring-ml-projects step 6) — recompute the
baseline in the same run, don't compare against a stale recorded number.
"""
