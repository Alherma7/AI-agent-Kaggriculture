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


LOOP_ORDER_2X2 = {
    (4, 4): (4, 3),
    (4, 3): (3, 3),
    (3, 3): (3, 4),
    (3, 4): (4, 4),
}
DIRECTIONS = {(0, -1): "NORTH", (0, 1): "SOUTH", (1, 0): "EAST", (-1, 0): "WEST"}

# 12-tile closed loop within the NW quadrant (x,y in [0,4]): the 2-row
# rectangle spanning y=3..4 (10 tiles) plus a 2-tile detour into y=2,
# reaching the ~12 tiles/day ceiling (24 turns/day, ~2 turns/tile) without
# exceeding it. See notebooks/06_farmer_movement_12_tile_loop.ipynb.
LOOP_ORDER_12 = {
    (4, 4): (3, 4),
    (3, 4): (2, 4),
    (2, 4): (1, 4),
    (1, 4): (0, 4),
    (0, 4): (0, 3),
    (0, 3): (1, 3),
    (1, 3): (2, 3),
    (2, 3): (2, 2),
    (2, 2): (3, 2),
    (3, 2): (3, 3),
    (3, 3): (4, 3),
    (4, 3): (4, 4),
}


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


def wheat_loop_2x2_agent(obs):
    """wheat_loop_agent extended with farmer movement over a 2x2 tile loop.

    Motivated by the leaderboard replay analysis in PROGRESS.md
    (2026-08-13): wheat_loop_agent's farmer never moves, so it only ever
    tends its single starting tile, while the opponent that beat it moves
    every day and tends multiple tiles. This is the first Level 2
    increment (see PROGRESS.md roadmap): the farmer cycles through the
    4 tiles closest to the shed spawn point (4,4) -- (4,4), (4,3), (3,3),
    (3,4), forming a closed loop -- instead of one. At each tile it
    applies wheat_loop_agent's own harvest > water > plant priority, and
    only moves to the next tile in the loop once there is nothing left to
    do at the current one today (matching AGENTS.md's HARVEST-before-WATER
    order, same as wheat_loop_agent).

    Validated in notebooks/05_farmer_movement.ipynb via evaluate.py: beats
    wheat_loop_agent (win_rate=0.0 for the 1-tile baseline across two
    independent evaluate() runs; baseline avg_money ~3300-3385 vs. this
    agent's ~4293).
    """
    market = []
    wheat_seeds = obs["private"]["seeds"].get("WHEAT", 0)
    if obs["step"] == 0 or wheat_seeds <= 0:
        market.append(["BUY_SEED", "WHEAT", 1])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    target_x, target_y = LOOP_ORDER_2X2[(x, y)]
    direction = DIRECTIONS[(target_x - x, target_y - y)]

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
            farmer = [direction]
    else:
        farmer = [direction]

    return {"farmer": farmer, "hands": [], "market": market}


def wheat_loop_12_agent(obs):
    """wheat_loop_2x2_agent's design, extended to a 12-tile loop.

    Same priority and same stateless "look up the next tile from my
    current position" mechanism as wheat_loop_2x2_agent -- only
    LOOP_ORDER_2X2 is swapped for LOOP_ORDER_12, a 12-tile closed loop
    (see the constant's comment for its shape). 12 tiles was picked
    deliberately, not arbitrarily: with turnsPerDay=24 and ~1 move + ~1
    tend action per new tile, a single farmer can service roughly
    24 / 2 ~= 12 tiles/day at most, so this pushes to that ceiling
    rather than picking a round number.

    Validated in notebooks/06_farmer_movement_12_tile_loop.ipynb via
    evaluate.py against the current best (wheat_loop_2x2_agent, not the
    original 1-tile baseline, per the project's "compare against current
    state" rule): wheat_loop_2x2_agent loses 20/20 across two independent
    evaluate() runs, avg_money ~4301-4413 for the 2x2 loop vs. more for
    this agent.
    """
    market = []
    wheat_seeds = obs["private"]["seeds"].get("WHEAT", 0)
    if obs["step"] == 0 or wheat_seeds <= 0:
        market.append(["BUY_SEED", "WHEAT", 1])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    target_x, target_y = LOOP_ORDER_12[(x, y)]
    direction = DIRECTIONS[(target_x - x, target_y - y)]

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
            farmer = [direction]
    else:
        farmer = [direction]

    return {"farmer": farmer, "hands": [], "market": market}
