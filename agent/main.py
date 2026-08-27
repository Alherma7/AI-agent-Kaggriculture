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


def agent(obs):
    """melon_then_wheat_agent extended with a goose/egg income stream on
    hand 4, instead of that hand's own single-tile crop zone. Motivated by
    the v5 replay (PROGRESS.md, 2026-08-23): the opponent ran COW/SHEEP
    and direct FERTILIZER sales, income streams we had none of. Goose
    chosen over cow/sheep as the first animal: cheapest to buy ($300 vs
    $400/$500), fastest first yield (day 4 vs day 8/6), and no
    every-N-days interval bookkeeping (eggs produce daily once fed).

    Built in notebooks/13_goose.ipynb, in three stages, two of them
    negative results kept for the record rather than silently discarded:

    1. **Isolated mini-test** (`_test_goose_agent`, farmer-only, a
       BUY_PRODUCT WHEAT shortcut standing in for real income): validated
       the full BUILD_COOP -> PICKUP -> PLACE -> FEED/COLLECT_FERTILIZER/
       CARE/HARVEST cycle against a real `obs`, finding and fixing several
       bugs a docs-only read would have missed -- a `tile` that's `None`
       before BUILD_COOP, `fed_today` vs. `coop_age` for the daily-care
       gate, `PICKUP` requiring shed-adjacency, and hands/inventories
       resetting to the shed every day.
    2. **First integration attempt**: a dedicated 9th hand, hired only
       after buying NE land, coop on NE's one unclaimed tile. Lost 0/10 to
       `melon_then_wheat_extra_hands_agent` -- a real negative result, not
       a bug (the mechanism itself worked). Root cause (found via replay
       trace): the goose wasn't placed until day 14 (land + hire + a
       couple of shed round-trips first), leaving too little season left,
       on top of a daily NE-border walk that produced nothing.
    3. **This version**: folds the goose into hand 4 of
       `melon_then_wheat_agent` directly -- no land purchase or dedicated
       hire needed, isolating the placement-delay problem from the NE-walk
       one. Three more real bugs found and fixed along the way, each
       confirmed by tracing hand 4's own position/tile/inventory turn by
       turn (not guessed):
       - Standing on a `"LOCKED"` tile silently no-ops *any* non-move
         action (confirmed reading `kaggriculture.py::_apply_unit_action`)
         -- without an explicit check, hand 4 got stuck forever retrying
         `PICKUP` from a locked spawn corner.
       - The `PICKUP WHEAT` condition needs the same
         `shed.get("WHEAT", 0) > 0` guard the `PICKUP GOOSE` one already
         had -- without it, hand 4 kept "trying" (and silently failing) to
         pick up wheat that didn't exist yet, permanently blocking the
         walk instead of falling through to tend/move.
       - The goose starves and escapes (`consecutive_unfed >= 2`, per
         `_daily_refresh_animals`) before day 10, since nobody -- including
         hand 4's own opportunistic tending -- grows WHEAT during the
         melon phase. Fixed with a `BUY_PRODUCT WHEAT` order whenever the
         shed is empty pre-day-10. That fix then caused a *second*
         regression -- hand 4 stopped reaching the coop at all, for the
         entire game -- diagnosed by comparing turns-per-node with and
         without the change: hand 4 only ever completes the 15-move
         `LOOP_ORDER_HANDS` walk with zero turns to spare (19 turns
         available, hired at hour 5), so the one extra `PICKUP WHEAT` this
         fix adds at `(4,4)` was exactly the turn that used to close the
         gap. Fixed with `GOOSE_FEEDER`, a direct 2-step route bypassing
         the shared loop entirely, plus ungating the whole coop cycle from
         holding WHEAT (only `FEED` needs it -- `COLLECT_FERTILIZER`/
         `CARE`/`HARVEST` don't, and were being skipped for nothing).

    Validated via `evaluate(melon_then_wheat_goose_agent,
    melon_then_wheat_agent, n=10)` across two independent calls:
    `win_rate=1.0` both times (`avg_money` 28871.0 and 29748.0), coop and
    goose placed on day 0 in the traced episode, all 30 days reached.
    """
    crop_to_plant = "MELON" if obs["day"] < 10 else "WHEAT"
    crop_seeds = obs["private"]["seeds"].get(crop_to_plant, 0)

    market = []
    hands = []

    if obs["step"] == 0:
        market.append(["BUY_ANIMAL", "GOOSE", 1])
    if obs["day"] < 10 and obs["private"]["shed"].get("WHEAT", 0) == 0:
        market.append(["BUY_PRODUCT", "WHEAT", 1])

    for i, (hx, hy) in enumerate(obs["farms"][obs["player"]]["hands"]):
        if i == 4:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **GOOSE_FEEDER}
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
                # At the coop.
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
                # Not at the coop yet: pickup priority (GOOSE, then
                # WHEAT), only possible while shed-adjacent; otherwise
                # tend whatever tile it's standing on, same as hands 0-3.
                if hand_tile == "LOCKED":
                    op = move
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("GOOSE", 0) == 0 and obs["private"]["shed"].get("GOOSE", 0) > 0:
                    op = ["PICKUP", "GOOSE", 1]
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("WHEAT", 0) == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
                    op = ["PICKUP", "WHEAT", 1]
                elif hand_tile is None and crop_seeds > 0:
                    op = ["PLANT", crop_to_plant]
                elif hand_tile is not None and hand_tile.get("kind") == "PLANT":
                    crop_age = obs["day"] - hand_tile["planted_day"]
                    threshold = 10 if hand_tile["crop"] == "MELON" else 2
                    if crop_age >= threshold:
                        op = ["HARVEST"]
                    elif not hand_tile.get("watered_today"):
                        op = ["WATER"]
                    else:
                        op = move
                else:
                    op = move
        elif hand_tile == "LOCKED" or (hx, hy) not in HAND_ZONES[i % len(HAND_ZONES)]:
            op = move
        elif hand_tile is None and crop_seeds > 0:
            op = ["PLANT", crop_to_plant]
        elif hand_tile is not None and hand_tile.get("kind") == "PLANT":
            crop_age = obs["day"] - hand_tile["planted_day"]
            threshold = 10 if hand_tile["crop"] == "MELON" else 2
            if crop_age >= threshold:
                op = ["HARVEST"]
            elif not hand_tile.get("watered_today"):
                op = ["WATER"]
            else:
                op = move
        else:
            op = move
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
    if wheat_in_shed > 1:
        market.append(["SELL", "WHEAT", wheat_in_shed - 1])
    if melon_in_shed > 0:
        market.append(["SELL", "MELON", melon_in_shed])

    if tile is None and crop_seeds > 0:
        farmer = ["PLANT", crop_to_plant]
    elif tile is not None and tile.get("kind") == "PLANT":
        crop_age = obs["day"] - tile["planted_day"]
        threshold = 10 if tile["crop"] == "MELON" else 2
        if crop_age >= threshold:
            farmer = ["HARVEST"]
        elif not tile.get("watered_today"):
            farmer = ["WATER"]
        else:
            farmer = [direction]
    else:
        farmer = [direction]

    return {"farmer": farmer, "hands": hands, "market": market}
