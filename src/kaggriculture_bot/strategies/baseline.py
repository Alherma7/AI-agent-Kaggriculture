"""Baseline heuristic agent(s).

wheat_loop_agent follows the "Example — Wheat Loop" from AGENTS.md
(competition kit, root of this repo): buy wheat seed if out of stock,
plant on an empty tile, harvest as soon as the crop is ready (checked
before watering, matching AGENTS.md's own priority order), otherwise
water. Sells wheat one unit per turn rather than dumping the whole shed
at once — validated as the better choice in
notebooks/03_baseline_wheat_loop.ipynb (see 2026-08-10 entry in
PROGRESS.md: selling the full shed per turn showed no consistent
improvement over n=10/n=20 runs vs "starter").

Validated in notebooks/03_baseline_wheat_loop.ipynb via evaluate.py:
win_rate=1.0 vs both "random" and "starter" built-in agents.
"""


def wheat_loop_agent(obs):
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
