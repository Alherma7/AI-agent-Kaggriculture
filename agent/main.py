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
LOOP_ORDER_HANDS = {
    (4, 4): (3, 4),
    (3, 4): (3, 3),
    (3, 3): (3, 2),
    (3, 2): (3, 1),
    (3, 1): (2, 1),
    (2, 1): (1, 1),
    (1, 1): (0, 1),
    (0, 1): (0, 0),
    (0, 0): (1, 0),
    (1, 0): (2, 0),
    (2, 0): (3, 0),
    (3, 0): (4, 0),
    (4, 0): (4, 1),
    (4, 1): (4, 2),
    (4, 2): (4, 3),
    (4, 3): (4, 4),
}
SPAWN_FEEDER = {(5, 4): (4, 4), (4, 5): (4, 4), (5, 5): (5, 4)}
HAND_ZONES = [
    {(0, 0): (1, 0), (1, 0): (1, 1), (1, 1): (0, 1), (0, 1): (0, 0)},  # hand 0: 2x2 block
    {(2, 0): (3, 0), (3, 0): (3, 1), (3, 1): (2, 1), (2, 1): (2, 0)},  # hand 1: 2x2 block
    {(4, 0): (4, 1), (4, 1): (4, 0)},  # hand 2: 2-tile ping-pong
    {(0, 1): (0, 2), (0, 2): (1, 2), (1, 2): (0, 2)},  # hand 3: settles on (0,2)<->(1,2), the LOOP_ORDER_HANDS gap
    {(4, 2): (4, 2)},  # hand 4: single tile, self-loop
]
GOOSE_TILE = (4, 2)
SHED_ADJACENT = {(4, 4), (5, 4), (4, 5), (5, 5)}
GOOSE_FEEDER = {(4, 4): (4, 3), (4, 3): (4, 2), (4, 2): (4, 2)}
PASTURE_TILE = (4, 1)
PASTURE_FEEDER = {(4, 4): (4, 3), (4, 3): (4, 2), (4, 2): (4, 1), (4, 1): (4, 1)}
CROP_INFO = {
    "WHEAT": {"ongoing": False, "max_yield_day": 4, "max_yield": 6},
    "MELON": {"ongoing": False, "max_yield_day": 12, "max_yield": 6},
    "STRAWBERRY": {"ongoing": True},
}
STRAWBERRY_TILE = (0, 1)


def _tile_action(tile, fallback, crop_seeds, crop_to_plant, obs):
    if tile is None and crop_seeds > 0:
        action = ["PLANT", crop_to_plant]
    elif tile is not None and tile.get("kind") == "PLANT":
        crop_age = obs["day"] - tile["planted_day"]
        ongoing_crop = CROP_INFO[tile["crop"]]["ongoing"]
        if ongoing_crop:
            if not tile.get("watered_today"):
                action = ["WATER"]
            elif tile.get("yield_units", 0) > 0:
                action = ["HARVEST"]
            else:
                action = fallback
        else:
            max_yield_day = CROP_INFO[tile["crop"]]["max_yield_day"]
            max_yield = CROP_INFO[tile["crop"]]["max_yield"]
            if crop_age >= max_yield_day or tile.get("yield_units", 0) >= max_yield:
                action = ["HARVEST"]
            elif not tile.get("watered_today"):
                action = ["WATER"]
            else:
                action = fallback
    else:
        action = fallback
    return action


def agent(obs):
    """melon_then_wheat_goose_cow_agent extended with STRAWBERRY, an
    ongoing crop, on a single fixed tile -- notebooks/15_leaderboard_agent.ipynb.
    See the module-level comment block just above CROP_INFO for the full
    account (the _tile_action refactor, the ongoing-crop mechanics, the
    watering-window regression and its Opus-diagnosed fix, and the
    STRAWBERRY_TILE placement rationale).
    """
    crop_to_plant = "MELON" if obs["day"] < 10 else "WHEAT"
    crop_seeds = obs["private"]["seeds"].get(crop_to_plant, 0)
    strawberry_seeds = obs["private"]["seeds"].get("STRAWBERRY", 0)

    market = []
    hands = []

    if obs["step"] == 0:
        market.append(["BUY_ANIMAL", "GOOSE", 1])
        market.append(["BUY_ANIMAL", "COW", 1])
        market.append(["BUY_SEED", "STRAWBERRY", 1])
    if obs["day"] < 13 and obs["private"]["shed"].get("WHEAT", 0) == 0:
        market.append(["BUY_PRODUCT", "WHEAT", 1])

    for i, (hx, hy) in enumerate(obs["farms"][obs["player"]]["hands"]):
        if i == 4:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **GOOSE_FEEDER}
        elif i == 2:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **PASTURE_FEEDER}
        else:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **HAND_ZONES[i % len(HAND_ZONES)]}
        target_x, target_y = hand_loop[(hx, hy)]
        if (target_x, target_y) == (hx, hy):
            move = ["PASS"]
        else:
            move = [DIRECTIONS[(target_x - hx, target_y - hy)]]

        hand_tile = obs["farms"][obs["player"]]["tiles"][hy][hx]

        if i == 4:
            hand_inventory = obs["private"]["inventories"][i + 1]

            if (hx, hy) == GOOSE_TILE:
                if hand_tile is None:
                    op = ["BUILD_COOP"]
                elif hand_tile.get("kind") == "COOP" and hand_tile.get("animal") != "GOOSE":
                    if hand_inventory.get("GOOSE", 0) > 0:
                        op = ["PLACE", "GOOSE", 1]
                    else:
                        op = ["PASS"]
                elif hand_inventory.get("WHEAT", 0) > 0 and not hand_tile.get("fed_today"):
                    op = ["FEED"]
                elif hand_tile.get("fertilizer_available"):
                    op = ["COLLECT_FERTILIZER"]
                elif not hand_tile.get("cared_today"):
                    op = ["CARE"]
                elif hand_tile.get("yield_units", 0) > 0:
                    op = ["HARVEST"]
                else:
                    op = ["PASS"]
                    egg_in_shed = obs["private"]["shed"].get("EGG", 0)
                    if egg_in_shed > 0:
                        market.append(["SELL", "EGG", egg_in_shed])
            else:
                if hand_tile == "LOCKED":
                    op = move
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("GOOSE", 0) == 0 and obs["private"]["shed"].get("GOOSE", 0) > 0:
                    op = ["PICKUP", "GOOSE", 1]
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("WHEAT", 0) == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
                    op = ["PICKUP", "WHEAT", 1]
                else:
                    op = _tile_action(hand_tile, move, crop_seeds, crop_to_plant, obs)
        elif i == 2:
            hand_inventory = obs["private"]["inventories"][i + 1]

            if (hx, hy) == PASTURE_TILE:
                if hand_tile is None:
                    op = ["BUILD_PASTURE"]
                elif hand_tile.get("kind") == "PASTURE" and hand_tile.get("animal") != "COW":
                    if hand_inventory.get("COW", 0) > 0:
                        op = ["PLACE", "COW", 1]
                    else:
                        op = ["PASS"]
                elif hand_inventory.get("WHEAT", 0) > 0 and not hand_tile.get("fed_today"):
                    op = ["FEED"]
                elif hand_tile.get("fertilizer_available"):
                    op = ["COLLECT_FERTILIZER"]
                elif not hand_tile.get("cared_today"):
                    op = ["CARE"]
                elif hand_tile.get("yield_units", 0) > 0:
                    op = ["HARVEST"]
                else:
                    op = ["PASS"]
            else:
                if hand_tile == "LOCKED":
                    op = move
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("COW", 0) == 0 and obs["private"]["shed"].get("COW", 0) > 0:
                    op = ["PICKUP", "COW", 1]
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("WHEAT", 0) == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
                    op = ["PICKUP", "WHEAT", 1]
                else:
                    op = _tile_action(hand_tile, move, crop_seeds, crop_to_plant, obs)
        elif hand_tile == "LOCKED" or (hx, hy) not in HAND_ZONES[i % len(HAND_ZONES)]:
            op = move
        else:
            if (hx, hy) == STRAWBERRY_TILE:
                op = _tile_action(hand_tile, move, strawberry_seeds, "STRAWBERRY", obs)
            else:
                op = _tile_action(hand_tile, move, crop_seeds, crop_to_plant, obs)
        hands.append(op)

    if len(obs["farms"][obs["player"]]["hands"]) < 5:
        market.append(["HIRE"])

    if obs["step"] == 0 or crop_seeds <= 5:
        market.append(["BUY_SEED", crop_to_plant, 6 - crop_seeds])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    target_x, target_y = LOOP_ORDER_12[(x, y)]
    direction = DIRECTIONS[(target_x - x, target_y - y)]

    tile = obs["farms"][obs["player"]]["tiles"][y][x]

    wheat_in_shed = obs["private"]["shed"].get("WHEAT", 0)
    melon_in_shed = obs["private"]["shed"].get("MELON", 0)
    fertilizer_in_shed = obs["private"]["shed"].get("FERTILIZER", 0)
    milk_in_shed = obs["private"]["shed"].get("MILK", 0)
    strawberry_in_shed = obs["private"]["shed"].get("STRAWBERRY", 0)
    if wheat_in_shed > 1:
        market.append(["SELL", "WHEAT", wheat_in_shed - 1])
    if melon_in_shed > 0:
        market.append(["SELL", "MELON", melon_in_shed])
    if fertilizer_in_shed > 0:
        market.append(["SELL", "FERTILIZER", fertilizer_in_shed])
    if milk_in_shed > 0:
        market.append(["SELL", "MILK", milk_in_shed])
    if strawberry_in_shed > 0:
        market.append(["SELL", "STRAWBERRY", strawberry_in_shed])

    farmer = _tile_action(tile, [direction], crop_seeds, crop_to_plant, obs)

    return {"farmer": farmer, "hands": hands, "market": market}
