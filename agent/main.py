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


def agent(obs):
    """melon_rush_agent extended with a one-way day-based crop switch:
    MELON for the first 10 days, WHEAT from day 10 onward.

    Motivated by two things found while validating melon_rush_agent
    (PROGRESS.md, 2026-08-22): (1) it goes as low as $68 in the early game
    (no income until MELON's first_yield_day=10) and (2) it keeps
    replanting MELON forever even once the shared market is crashed,
    while WHEAT's own market barely reacts to oversupply
    (above_target=0.20/log vs. MELON's 3.60/sq) -- so switching new
    plantings to WHEAT once the first MELON wave is in flight both adds a
    steadier income source and stops feeding a market that no longer pays
    well. A day cutoff, not a market-price threshold: MELON's
    first_yield_day is exactly 10, so day 10 is precisely when the first
    wave becomes sellable and anything planted after would only mature
    very late in the season anyway.

    Same structure as melon_rush_agent (LOOP_ORDER_12 for the farmer,
    HAND_ZONES for hands) with three changes, applied uniformly to every
    unit rather than duplicating the whole if/elif chain:
    - What to plant on an empty tile: `crop_to_plant = "MELON" if
      obs["day"] < 10 else "WHEAT"`.
    - What seed to buy: only `crop_to_plant`'s seed stock -- never buys
      MELON seed once day 10 hits, so nothing goes to waste unused.
    - How to tend what's already planted: the harvest threshold is read
      from the tile's own `crop` field, not from the current phase -- a
      MELON planted on day 8 still needs its own day 18 before
      harvesting, even once new plantings have already switched to WHEAT.
      Selling checks WHEAT and MELON shed stock independently (not just
      `crop_to_plant`), since both may be present during the transition.

    First validated in notebooks/10_melon_then_wheat.ipynb via evaluate.py
    against the then-current best, melon_rush_agent: win_rate=0.0 for the
    baseline across two independent evaluate() calls (avg_money 16711.0
    both times -- unusually exact agreement, confirmed as two genuinely
    separate runs, not a duplicated paste).

    **Extended same day (2026-08-22)**: sold 1 unit/turn at first
    (inherited from wheat_loop_agent's original convention). Checked
    directly in the installed engine (kaggriculture.py's per-unit
    lockstep market loop): a single `SELL <crop> N` order is processed
    one unit at a time internally regardless of N, re-quoting the price
    after each -- so from our own selling alone, dumping the whole shed
    at once and trickling 1/turn give identical revenue. But the market
    is shared, and episode 96612755 showed the opponent also sells a lot
    of melon -- every turn spent holding shed inventory is a turn where
    *their* selling can degrade the price before ours goes through. Fixed
    by selling the full shed (`SELL <crop> <shed_amount>`) the moment
    it's available, instead of capping at 1/turn, for both WHEAT and
    MELON. Re-validated in notebooks/10_melon_then_wheat.ipynb against the
    then-current best (this same agent, 1-unit-per-turn selling):
    win_rate=0.0 across two independent evaluate() calls (avg_money
    13514.0 and 13751.0 for the losing, 1-unit-per-turn side).
    """
    crop_to_plant = "MELON" if obs["day"] < 10 else "WHEAT"
    crop_seeds = obs["private"]["seeds"].get(crop_to_plant, 0)

    market = []
    hands = []

    for i, (hx, hy) in enumerate(obs["farms"][obs["player"]]["hands"]):
        hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **HAND_ZONES[i % len(HAND_ZONES)]}
        target_x, target_y = hand_loop[(hx, hy)]
        if (target_x, target_y) == (hx, hy):
            move = ["PASS"]
        else:
            move = [DIRECTIONS[(target_x - hx, target_y - hy)]]

        hand_tile = obs["farms"][obs["player"]]["tiles"][hy][hx]
        in_own_zone = (hx, hy) in HAND_ZONES[i % len(HAND_ZONES)]
        if hand_tile == "LOCKED" or not in_own_zone:
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
    if wheat_in_shed > 0:
        market.append(["SELL", "WHEAT", wheat_in_shed])
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
