"""Submission entrypoint. Must define `agent(obs)` -> action dict.

This is the "production" pipeline: only strategies that graduated from
notebooks/ + evaluate.py (see RESOURCES.md, PROGRESS.md) get wired in here.
Packaged and submitted via `kaggle competitions submit kaggriculture -f ...`
(see AGENTS.md). No network/file I/O here at inference time — see
docs/RULES_SUMMARY.md (No Ingress or Egress).
"""

# TODO: import the validated strategy from kaggriculture_bot.strategies
# from kaggriculture_bot.strategies.baseline import wheat_loop_agent as agent


def agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}
