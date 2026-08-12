"""Submission entrypoint. Must define `agent(obs)` -> action dict.

This is the "production" pipeline: only strategies that graduated from
notebooks/ + evaluate.py (see RESOURCES.md, PROGRESS.md) get wired in here.
Packaged and submitted via `kaggle competitions submit kaggriculture -f ...`
(see AGENTS.md). No network/file I/O here at inference time — see
docs/RULES_SUMMARY.md (No Ingress or Egress).
"""

# Inlined copy of kaggriculture_bot.strategies.baseline.wheat_loop_agent.
# Kaggle submissions must be flat (main.py [+ flat helper files], no
# src/-style package) — see AGENTS.md "Submit Your Agent". Keep this in
# sync by hand with src/kaggriculture_bot/strategies/baseline.py until a
# build step generates it automatically (tracked in PROGRESS.md).


def agent(obs):
    market = []
    wheat_seeds = obs["private"]["seeds"].get("WHEAT", 0)
    if obs["step"] == 0 or wheat_seeds <= 0:
        market.append(["BUY_SEED", "WHEAT", 1])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    tile = obs["farms"][obs["player"]]["tiles"][y][x]

    wheat_in_shed = obs["private"]["shed"].get("WHEAT", 0)
    if wheat_in_shed > 0:
        market.append(["SELL", "WHEAT", 1])

    if tile is None and wheat_seeds > 0:
        farmer = ["PLANT", "WHEAT"]
    elif tile is not None and tile.get("kind") == "PLANT":
        crop_age = obs["day"] - tile["planted_day"]
        if crop_age >= 2:
            farmer = ["HARVEST"]
        elif not tile.get("watered_today"):
            farmer = ["WATER"]
        else:
            farmer = ["PASS"]
    else:
        farmer = ["PASS"]

    return {"farmer": farmer, "hands": [], "market": market}
