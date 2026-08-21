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
    """wheat_loop_12_agent extended with hired farm hands, each tending its
    own private zone.

    Motivated by both leaderboard replay analyses in PROGRESS.md
    (2026-08-13 HechtJP, 2026-08-20 Muhammed Ali Kul): both winning
    opponents used multiple farm hands as the single biggest lever we were
    missing (the latter held up to 10 hands vs. our 0). Hiring is cheap --
    the Fibonacci cost resets daily, so 5 hands in one day costs
    1+1+2+3+5=12 -- so this hires up to 5 hands on the first turn of every
    day and gives each the farmer's own harvest > water > plant > move
    priority.

    Things the notebook's mini-tests (not assumptions) surfaced:
    - Hands don't spawn at (4,4) -- they land on whichever of the 4
      shed-access corners is least occupied, and the other 3 are "LOCKED"
      (a string, not a tile dict) until that quadrant is bought. Each
      hand's tile is checked for "LOCKED" before `.get("kind")` is called,
      treated the same as the empty-tile "nothing to do, move on" branch;
      SPAWN_FEEDER routes a hand from a locked spawn corner one step into
      LOOP_ORDER_HANDS's entry point.
    - With up to 6 units (farmer + 5 hands) wanting to plant on the same
      turn, buying 1 seed at a time (like wheat_loop_12_agent) starves
      most of them -- seed is bought in a batch up to 6 in stock instead.
    - **Bug found after this agent first graduated** (2026-08-21, same
      notebook): with all 5 hands sharing LOOP_ORDER_HANDS, any two that
      land on the same tile (easy -- they all funnel through the shared
      entry point (4,4)) compute identical actions forever after, since a
      hand's action is a pure function of its current tile with nothing to
      tell two hands apart. Confirmed via instrumented episodes: hands
      glued together for the rest of a day, tending one tile instead of
      16. Fixed with HAND_ZONES: each hand index gets its own private,
      pairwise-disjoint loop it peels off into via `{**LOOP_ORDER_HANDS,
      **SPAWN_FEEDER, **HAND_ZONES[i]}` -- once settled into its zone, a
      hand can never land on a different-index hand's tile again.

    Validated in notebooks/07_farm_hands.ipynb via evaluate.py against the
    current best (this same agent, pre-HAND_ZONES): the un-zoned version
    loses 20/20 across three independent evaluate() runs (avg_money 6003.0,
    6524.0, 5856.0 for the losing, un-zoned version).
    """
    wheat_seeds = obs["private"]["seeds"].get("WHEAT", 0)

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
        if hand_tile == "LOCKED":
            op = move
        elif hand_tile is None and wheat_seeds > 0:
            op = ["PLANT", "WHEAT"]
        elif hand_tile is not None and hand_tile.get("kind") == "PLANT":
            crop_age = obs["day"] - hand_tile["planted_day"]
            if crop_age >= 2:
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

    if obs["step"] == 0 or wheat_seeds <= 5:
        market.append(["BUY_SEED", "WHEAT", 6 - wheat_seeds])

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

    return {"farmer": farmer, "hands": hands, "market": market}
