"""Submission entrypoint. Must define `agent(obs)` -> action dict.

GENERATED FILE -- do not edit by hand. Edit the strategy in
src/kaggriculture_bot/strategies/ and re-run the generator.

This is the "production" pipeline: only strategies that graduated from
notebooks/ + evaluate.py (see RESOURCES.md, PROGRESS.md) get wired in here.
Packaged and submitted via `kaggle competitions submit kaggriculture -f ...`
(see AGENTS.md). No network/file I/O here at inference time -- see
docs/RULES_SUMMARY.md (No Ingress or Egress).
"""


DIRECTIONS = {(0, -1): "NORTH", (0, 1): "SOUTH", (1, 0): "EAST", (-1, 0): "WEST"}
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


def agent(obs):
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
