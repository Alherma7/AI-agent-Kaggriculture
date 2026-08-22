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

# A second, 16-tile closed loop for the hired hands to share, covering 11 of
# the 13 NW tiles LOOP_ORDER_12 doesn't reach ((0,2)/(1,2) still uncovered --
# known gap, see notebooks/07_farm_hands.ipynb). Shares 5 tiles with
# LOOP_ORDER_12 as pure transit, which is harmless -- units can co-occupy a
# tile. Entry point is (4,4), same as LOOP_ORDER_12.
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

# A newly hired hand spawns at whichever of the 4 shed-access corners is
# least occupied (kaggriculture.py::_spawn_hand), tie-broken NWSE -- not
# always (4,4), since the farmer's permanent presence there gives it a head
# start. The other 3 corners are "LOCKED" tiles until that quadrant is
# bought, so a hand landing on one needs a valid first move even though it
# isn't in LOOP_ORDER_HANDS. Each entry routes one step toward (4,4), the
# loop's entry point (see notebooks/07_farm_hands.ipynb for the mini-test
# that confirmed spawn placement and tile lock state).
SPAWN_FEEDER = {(5, 4): (4, 4), (4, 5): (4, 4), (5, 5): (5, 4)}

# Per-hand-index private zones, carved out of the same 13 free NW tiles as
# LOOP_ORDER_HANDS (pairwise disjoint -- see notebooks/07_farm_hands.ipynb's
# "Fix: split the loop into 5 disjoint zones" section for the full
# derivation). A hand still reaches its zone via the shared
# LOOP_ORDER_HANDS/SPAWN_FEEDER path; each zone dict only overrides the one
# or two tiles where that hand should peel off into its own private loop
# instead of continuing on the shared path -- so once a hand settles into
# its zone, landing on the same tile as a different-index hand again is
# structurally impossible (their zones share no tiles). Hand 4's zone is a
# single tile with nowhere to move to (a self-loop); the agent below treats
# that as PASS instead of a direction lookup.
HAND_ZONES = [
    {(0, 0): (1, 0), (1, 0): (1, 1), (1, 1): (0, 1), (0, 1): (0, 0)},  # hand 0: 2x2 block
    {(2, 0): (3, 0), (3, 0): (3, 1), (3, 1): (2, 1), (2, 1): (2, 0)},  # hand 1: 2x2 block
    {(4, 0): (4, 1), (4, 1): (4, 0)},  # hand 2: 2-tile ping-pong
    {(0, 1): (0, 2), (0, 2): (1, 2), (1, 2): (0, 2)},  # hand 3: settles on (0,2)<->(1,2), the LOOP_ORDER_HANDS gap
    {(4, 2): (4, 2)},  # hand 4: single tile, self-loop
]

# Zones for wheat_loop_melon_agent specifically -- a separate constant, not a
# HAND_ZONES mutation, so wheat_loop_hands_agent (already graduated and
# validated) is unaffected, same as LOOP_ORDER_2X2 staying untouched when
# LOOP_ORDER_12 was introduced. Only hand 4 differs from HAND_ZONES: a real
# Kaggle leaderboard replay (episode 96612755, analyzed 2026-08-22, logged in
# PROGRESS.md) showed the farmer's own LOOP_ORDER_12 never once reaches
# (4,3) in a full 720-turn game -- the loop resets to (4,4) daily and rarely
# finishes a full lap before the day ends, so the last tiles before the
# wrap-around ((3,3), (4,3)) are starved. Extending hand 4's zone from a
# single self-looping tile to the 2x2 block (4,2)-(4,3)-(3,3)-(3,2) plugs
# that gap (a genuine "own zone" tile now, not opportunistic transit tending)
# while also giving melon 4x the tile capacity.
MELON_HAND_ZONES = [
    HAND_ZONES[0],
    HAND_ZONES[1],
    HAND_ZONES[2],
    HAND_ZONES[3],
    {(4, 2): (4, 3), (4, 3): (3, 3), (3, 3): (3, 2), (3, 2): (4, 2)},  # hand 4: 2x2 block (was 1 tile)
]


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


def wheat_loop_hands_agent(obs):
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


def wheat_loop_melon_agent(obs):
    """wheat_loop_hands_agent extended with one hand growing MELON instead
    of WHEAT: hand index 4 (the single-tile (4,2) zone in HAND_ZONES).

    First increment on the PROGRESS.md Level 2 item "Per-tile crop choice
    by ROI" -- deliberately not the ROI logic itself (that needs melon's
    sell-price behavior, not yet explored), just proving the multi-crop
    mechanism works. The farmer and hands 0-3 are unchanged.

    Per-hand behavior is parameterized by index instead of duplicating the
    if/elif chain: hand 4 uses MELON's seed stock, crop name, and harvest
    threshold (`first_yield_day` = 10, vs. 2 for WHEAT); every other hand
    keeps the WHEAT values.

    Real bug found and fixed in notebooks/08_melon_hand.ipynb (2026-08-22):
    the engine applies each turn's PLANT actions in unit order (farmer,
    then hands by index) and silently drops any PLANT landing on a tile
    another unit already claimed that same turn
    (kaggle_environments' kaggriculture.py::_apply_unit_action -- separate
    from the "not enough seed for N simultaneous PLANT requests" rule in
    AGENTS.md). Hand 4 is always last, so it lost every such race against
    a lower-indexed hand -- and since all hands used to tend *any* empty
    tile they passed through on the shared LOOP_ORDER_HANDS transit path
    (harmless when every hand wants the same crop, not once one hand wants
    something else), melon seed stock never dropped, ever, confirmed via
    an instrumented episode. Fixed with an `in_own_zone` check: a hand now
    only tends (PLANT/WATER/HARVEST) a tile that's a key in its *own*
    HAND_ZONES entry; elsewhere it just moves through without touching the
    tile. This also removes hands 0-3's previous opportunistic tending of
    shared transit tiles, so the validation below compares two changes at
    once (melon hand + zone-restricted tending), consistent with this
    project's "compare against current best as a whole" convention rather
    than isolating attribution.

    First validated in notebooks/08_melon_hand.ipynb via evaluate.py
    against the then-current best, wheat_loop_hands_agent: win_rate=0.0
    for the baseline across two independent evaluate() calls (avg_money
    5697.0 and 5834.0 for the losing side).

    **Extended same day (2026-08-22)**: a real Kaggle leaderboard replay
    (episode 96612755, this agent's own first submission) showed the
    farmer's LOOP_ORDER_12 never once reaches (4,3) in a full 720-turn
    game -- the farmer/hands reset to (4,4) every day and rarely finish a
    full lap before the day ends, so the loop's last tiles before
    wrapping ((3,3), (4,3)) are starved (visited 2 and 0 times in 30
    days). This predates melon; it was simply masked before by hands'
    now-removed opportunistic tending of shared transit tiles. Fixed by
    giving hand 4 a proper 2x2 zone, MELON_HAND_ZONES (was a single
    self-looping tile) -- (4,2)-(4,3)-(3,3)-(3,2) -- which both plugs the
    farmer-loop gap and gives melon 4x the tile capacity. Re-validated in
    notebooks/08_melon_hand.ipynb against the then-current best (this same
    agent, pre-zone-expansion): win_rate=0.0 across two independent
    evaluate() calls (avg_money 8350.0 and 8553.0 for the losing,
    1-tile-melon side).
    """
    wheat_seeds = obs["private"]["seeds"].get("WHEAT", 0)
    melon_seeds = obs["private"]["seeds"].get("MELON", 0)
    market = []
    hands = []

    for i, (hx, hy) in enumerate(obs["farms"][obs["player"]]["hands"]):
        hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **MELON_HAND_ZONES[i % len(MELON_HAND_ZONES)]}
        target_x, target_y = hand_loop[(hx, hy)]
        if (target_x, target_y) == (hx, hy):
            move = ["PASS"]
        else:
            move = [DIRECTIONS[(target_x - hx, target_y - hy)]]

        if i == 4:
            seeds = melon_seeds
            crop = "MELON"
            threshold = 10
        else:
            seeds = wheat_seeds
            crop = "WHEAT"
            threshold = 2

        hand_tile = obs["farms"][obs["player"]]["tiles"][hy][hx]
        in_own_zone = (hx, hy) in MELON_HAND_ZONES[i % len(MELON_HAND_ZONES)]
        if hand_tile == "LOCKED" or not in_own_zone:
            op = move
        elif hand_tile is None and seeds > 0:
            op = ["PLANT", crop]
        elif hand_tile is not None and hand_tile.get("kind") == "PLANT":
            crop_age = obs["day"] - hand_tile["planted_day"]
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

    if obs["step"] == 0 or wheat_seeds <= 5:
        market.append(["BUY_SEED", "WHEAT", 6 - wheat_seeds])

    if obs["step"] == 0 or melon_seeds <= 1:
        market.append(["BUY_SEED", "MELON", 2 - melon_seeds])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    target_x, target_y = LOOP_ORDER_12[(x, y)]
    direction = DIRECTIONS[(target_x - x, target_y - y)]

    tile = obs["farms"][obs["player"]]["tiles"][y][x]

    wheat_in_shed = obs["private"]["shed"].get("WHEAT", 0)
    melon_in_shed = obs["private"]["shed"].get("MELON", 0)
    if wheat_in_shed > 0:
        market.append(["SELL", "WHEAT", 1])
    if melon_in_shed > 0:
        market.append(["SELL", "MELON", 1])

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


def melon_rush_agent(obs):
    """All units (farmer + up to 5 hands) grow MELON exclusively, no WHEAT
    at all -- an experiment, not (yet) a refinement of wheat_loop_melon_agent.

    Motivated by a real finding in the episode 96612755 replay analysis
    (PROGRESS.md, 2026-08-22): the winning opponent's melon sales alone
    were $25,594 -- 81% of their $31,477 final money, from 220 units sold
    starting day 10 (melon's first_yield_day, a hard floor -- nobody can
    sell melon before that, us or them, since the shared market is the
    same instance for both players). wheat_loop_melon_agent's single
    4-tile hand is far too small to compete at that scale (45 PLANT MELON
    orders for the opponent vs. our 3). This tests the other extreme:
    maximum melon production from turn 0, reusing wheat_loop_hands_agent's
    exact structure (LOOP_ORDER_12 for the farmer, HAND_ZONES for hands)
    with WHEAT swapped for MELON and the harvest threshold changed from 2
    to 10 (MELON's first_yield_day) everywhere, not just for one hand.

    Deliberately no wheat/phase-switching logic yet -- isolates the raw
    effect of all-in melon production before adding that complexity.
    Real risk, to be judged by evaluate.py rather than assumed: no income
    at all until day 10, against seed ($80/unit) and hire costs from the
    $3000 starting money.
    """
    melon_seeds = obs["private"]["seeds"].get("MELON", 0)

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
        elif hand_tile is None and melon_seeds > 0:
            op = ["PLANT", "MELON"]
        elif hand_tile is not None and hand_tile.get("kind") == "PLANT":
            crop_age = obs["day"] - hand_tile["planted_day"]
            if crop_age >= 10:
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

    if obs["step"] == 0 or melon_seeds <= 5:
        market.append(["BUY_SEED", "MELON", 6 - melon_seeds])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    target_x, target_y = LOOP_ORDER_12[(x, y)]
    direction = DIRECTIONS[(target_x - x, target_y - y)]

    tile = obs["farms"][obs["player"]]["tiles"][y][x]

    melon_in_shed = obs["private"]["shed"].get("MELON", 0)
    if melon_in_shed > 0:
        market.append(["SELL", "MELON", 1])

    if tile is None and melon_seeds > 0:
        farmer = ["PLANT", "MELON"]
    elif tile is not None and tile.get("kind") == "PLANT":
        crop_age = obs["day"] - tile["planted_day"]
        if crop_age >= 10:
            farmer = ["HARVEST"]
        elif not tile.get("watered_today"):
            farmer = ["WATER"]
        else:
            farmer = [direction]
    else:
        farmer = [direction]

    return {"farmer": farmer, "hands": hands, "market": market}


def melon_then_wheat_agent(obs):
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
