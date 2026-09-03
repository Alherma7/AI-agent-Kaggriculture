"""Submission entrypoint. Must define `agent(obs)` -> action dict.

EXPERIMENTAL SNAPSHOT -- hand-generated from notebooks/15_leaderboard_agent.ipynb
(strawberry_agent), NOT via scripts/build_agent.py, because that strategy
hasn't graduated to src/kaggriculture_bot/strategies/baseline.py yet (still
being validated -- see the notebook's Status cell). Regenerate from the
notebook, don't hand-edit. Once strawberry_agent graduates, switch
scripts/build_agent.py's STRATEGY back to it and use the normal generator.

No network/file I/O at inference time -- see docs/RULES_SUMMARY.md.
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
    {(2, 0): (2, 1), (2, 1): (2, 0)},  # hand 1: shrunk from a 2x2 block -- (3,0)/(3,1) now belong to CHAIN_NW
    {(4, 0): (4, 1), (4, 1): (4, 0)},  # hand 2: 2-tile ping-pong
    {(0, 1): (0, 2), (0, 2): (1, 2), (1, 2): (0, 2)},  # hand 3: settles on (0,2)<->(1,2), the LOOP_ORDER_HANDS gap
    {(4, 2): (4, 2)},  # hand 4: single tile, self-loop
]
LOOP_ORDER_HANDS_NE = {
    (5, 4): (6, 4), (6, 4): (7, 4), (7, 4): (8, 4), (8, 4): (9, 4),
    (9, 4): (9, 3), (9, 3): (9, 2), (9, 2): (9, 1), (9, 1): (9, 0),
    (9, 0): (8, 0), (8, 0): (7, 0), (7, 0): (6, 0), (6, 0): (5, 0),
    (5, 0): (5, 1), (5, 1): (5, 2), (5, 2): (5, 3), (5, 3): (5, 4),
}
SPAWN_FEEDER_NE = {(4, 4): (5, 4), (4, 5): (4, 4), (5, 5): (5, 4)}
ZONE_TOP_NE = {
    (5, 0): (6, 0), (6, 0): (7, 0), (7, 0): (8, 0), (8, 0): (9, 0),
    (9, 0): (9, 1), (9, 1): (8, 1), (8, 1): (7, 1), (7, 1): (6, 1),
    (6, 1): (5, 1), (5, 1): (5, 0),
}
ZONE_LEFT_NE = {
    (5, 2): (6, 2), (6, 2): (6, 3), (6, 3): (6, 4),
    (6, 4): (5, 4), (5, 4): (5, 3), (5, 3): (5, 2),
}
ZONE_RIGHT_NE = {
    (7, 2): (8, 2), (8, 2): (9, 2), (9, 2): (9, 3), (9, 3): (9, 4),
    (9, 4): (8, 4), (8, 4): (7, 4), (7, 4): (7, 3), (7, 3): (7, 2),
}
# SW crop zones (EXPERIMENT, 2026-09-03): 3 real strong replays
# (103962387/105046178/105002288) all own SW and grow STRAWBERRY across
# nearly all of it (38 tiles across NW+NE+SW in one traced replay), not
# just the fixed tile + ZONE_RIGHT_NE we have. Built by shifting
# LOOP_ORDER_HANDS/SPAWN_FEEDER/ZONE_*_NE (y+5, and x-5,y+5 for the
# sub-zones) -- SW's x-range (0-4) matches NW's, not NE's, so the NW
# loop shape transfers directly with a y shift.
LOOP_ORDER_HANDS_SW = {(x, y + 5): (x2, y2 + 5) for (x, y), (x2, y2) in LOOP_ORDER_HANDS.items()}
SPAWN_FEEDER_SW = {(4, 4): (4, 5), (5, 4): (4, 5), (5, 5): (4, 5)}
ZONE_TOP_SW = {(x - 5, y + 5): (x2 - 5, y2 + 5) for (x, y), (x2, y2) in ZONE_TOP_NE.items()}
ZONE_LEFT_SW = {(x - 5, y + 5): (x2 - 5, y2 + 5) for (x, y), (x2, y2) in ZONE_LEFT_NE.items()}
ZONE_RIGHT_SW = {(x - 5, y + 5): (x2 - 5, y2 + 5) for (x, y), (x2, y2) in ZONE_RIGHT_NE.items()}
GOOSE_TILE = (4, 2)
SHED_ADJACENT = {(4, 4), (5, 4), (4, 5), (5, 5)}
PASTURE_TILE = (4, 1)

# Chain hands (Opus diagnosis, 2026-09-03): generalizes the old
# hand-2/hand-4 single-tile dedicated-pasture model to a multi-tile
# closed loop, matching the pasture layout measured in 3 independent
# strong Kaggle replays (103962387/105002288/105046178: a 14-tile
# contiguous block around spawn, none left uncultivated). See the
# chain-hand paragraph in the docstring for why a *roaming* pool could
# not sustain this (it could, in principle, reach any of these tiles --
# it just could never carry enough WHEAT in one trip to feed more than
# one animal).
CHAIN_H4 = [(4, 2), (4, 3), (3, 3), (3, 2)]
CHAIN_H4_NEXT = {(4, 2): (4, 3), (4, 3): (3, 3), (3, 3): (3, 2), (3, 2): (4, 2)}
CHAIN_NW = [(4, 1), (4, 0), (3, 0), (3, 1)]
CHAIN_NW_NEXT = {(4, 1): (4, 0), (4, 0): (3, 0), (3, 0): (3, 1), (3, 1): (4, 1)}

CROP_INFO = {
    "WHEAT": {"ongoing": False, "max_yield_day": 4, "max_yield": 6, "first_yield_day": 2},
    "MELON": {"ongoing": False, "max_yield_day": 12, "max_yield": 6, "first_yield_day": 10},
    "STRAWBERRY": {"ongoing": True, "first_yield_day": 10},
    "CARROT": {"ongoing": False, "max_yield_day": 3, "max_yield": 4, "first_yield_day": 2},
}
STRAWBERRY_TILE = (0,1)

def _tile_action(tile, fallback, seed_budget, crop_to_plant, obs):
    # DIG reclaims a WEED tile back to empty (roadmap step 5) -- cheap,
    # isolated: any tile-tending caller (farmer, wheat/melon/strawberry
    # hands, NE hands) benefits without extra wiring.
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        return ["DIG"]

    if tile is None and seed_budget[0] > 0:
        # Decremented here, not read-only: `seed_budget` is shared across
        # every unit's call this turn (see its construction in `agent`).
        # The engine's PLANT validation is atomic per crop -- if the
        # season's total PLANT requests for a crop exceed the seeds on
        # hand, it drops ALL of them, not just the overflow
        # (kaggriculture.py's `interpreter`, `blocked = {crop for crop, n
        # in plant_demand.items() if n > seeds.get(crop, 0)}`). Handing
        # every unit the same un-decremented seed count let N units all
        # see "seeds > 0" and all request PLANT off a 1-seed budget, so
        # the engine blocked every one of them and none of the N tiles
        # ever got planted -- confirmed on seed 1, day 0: melon_seeds
        # flat at 1 for 5+ turns straight while 4 units re-requested
        # PLANT MELON each turn. Decrementing here caps this turn's
        # requests at the real seed count, so the ones beyond budget
        # fall through to `fallback` instead of piling into the same
        # doomed request.
        action = ["PLANT", crop_to_plant]
        seed_budget[0] -= 1
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
            first_yield_day = CROP_INFO[tile["crop"]]["first_yield_day"]
            # The engine silently rejects HARVEST before first_yield_day
            # (kaggriculture.py:390-407), so a tile that hits max_yield
            # early -- MELON does, at age 8 with fertilizer -- would
            # HARVEST-deadlock here for two days. Falling through to
            # WATER keeps it from weeding out while it matures.
            if (crop_age >= max_yield_day or tile.get("yield_units",0) >= max_yield) and crop_age >= first_yield_day:
                action = ["HARVEST"]
            elif not tile.get("watered_today"):
                action = ["WATER"]
            else: 
                action = fallback
    else:
        action = fallback
    return action

PLACE_RADIUS = 2


def _nearest_free_tile(obs, player, from_pos):
    """Brute-force nearest free (`None`, not `"LOCKED"`) tile to
    `from_pos`, by Manhattan distance -- no pathfinding needed here (chat
    decision): this grid has no obstacles blocking movement within an
    unlocked quadrant, so straight-line distance already matches real
    walking distance. Returns the `(x, y)` of the nearest free tile, or
    `None` if there isn't one.

    Bounded to PLACE_RADIUS of `from_pos` (Opus diagnosis, 2026-09-03):
    unbounded, a carrying pool hand walks to whatever empty tile exists
    anywhere on the board once near-shed ground is taken, and an animal
    placed there can't complete a daily fetch-wheat/feed round trip --
    it starves in ~3 days, gets rebought, and repeats. Returning `None`
    when nothing qualifies is not a deadlock: the caller's `roam_op`
    falls back to `["PASS"]`, the carried animal is flushed to the shed
    at day-end, and `unplaced_animals > 0` already throttles further
    `BUY_ANIMAL` orders.
    """
    tiles = obs["farms"][player]["tiles"]
    best_dist, best_pos = None, None

    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if tile is not None:
                continue
            dist = abs(x - from_pos[0]) + abs(y - from_pos[1])
            if dist > PLACE_RADIUS:
                continue
            if best_dist is None or dist < best_dist:
                best_dist, best_pos = dist, (x, y)
    return best_pos

def _move_toward(hx, hy, target_x, target_y):
    if target_x > hx:
        op = ["EAST"]
    elif target_x < hx:
        op = ["WEST"]
    elif target_y > hy:
        op = ["SOUTH"]
    elif target_y < hy:
        op = ["NORTH"]
    else:
        op = ["PASS"]

    return op

def _nearest_needs_care_tile(obs, player, from_pos):
    """Nearest PASTURE/COOP tile with a placed animal that needs
    attention this turn (FEED/COLLECT_FERTILIZER/CARE/HARVEST) --
    same brute-force Manhattan-distance approach as
    `_nearest_free_tile`, for the shared-hands design (chat decision):
    the replay reaches 13 animals with only 9 hands total by day 9, so
    a dedicated hand per animal (what hands 8-18 did before) is not how
    it's done -- a small pool of hands must roam between existing
    animals needing care AND building new ones, not camp one each.
    """
    tiles = obs["farms"][player]["tiles"]
    best_dist, best_pos = None, None
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or "animal" not in tile:
                continue
            needs_care = (
                not tile.get("fed_today")
                or tile.get("fertilizer_available")
                or not tile.get("cared_today")
                or tile.get("yield_units", 0) > 0
            )
            if not needs_care:
                continue
            dist = abs(x - from_pos[0]) + abs(y - from_pos[1])
            if best_dist is None or dist < best_dist:
                best_dist, best_pos = dist, (x, y)
    return best_pos

def _chain_hand_op(obs, chain, hand_idx, hx, hy, hand_tile, move, placed_counts):
    """Generalizes hand 2/4's single-tile dedicated-pasture pattern to a
    multi-tile chain (Opus diagnosis, 2026-09-03). Bulk-picks WHEAT for
    the whole chain in one shed trip instead of one unit at a time --
    confirmed against a real strong replay (105046178.json) that three
    dedicated hands bulk-pick 4-6 WHEAT each and feed 14 animals/day
    between them, while our old one-at-a-time PICKUP capped care at one
    animal fed per shed trip regardless of hand or tile count. `chain`
    is this hand's own list of tile coordinates; `move` is the
    loop-computed fallback when nothing on/off the chain needs doing.
    """
    ANCHOR_LOCAL = (4, 4)
    hand_inventory = obs["private"]["inventories"][hand_idx + 1]
    wheat_held = hand_inventory.get("WHEAT", 0)
    carrying = "COW" if hand_inventory.get("COW", 0) > 0 else ("SHEEP" if hand_inventory.get("SHEEP", 0) > 0 else None)
    tiles = obs["farms"][obs["player"]]["tiles"]

    if hand_tile == "LOCKED":
        return move

    chain_needs_animal = any(
        tiles[y][x] is None
        or (isinstance(tiles[y][x], dict) and tiles[y][x].get("kind") == "PASTURE" and tiles[y][x].get("animal") is None)
        for (x, y) in chain
    )

    # Shed errands are checked before "am I on one of my own chain
    # tiles" -- CHAIN_NE's (5,4) is BOTH a chain tile and shed-adjacent,
    # and checking chain-membership first meant hand 6 cycled its own 6
    # pastures forever and never once detoured for an animal (confirmed
    # on seed 1: shed sat at 1 unplaced COW the entire game, 6 of
    # CHAIN_NE's pastures stayed empty from day 10 to day 29).
    if (hx, hy) in SHED_ADJACENT:
        if wheat_held == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
            return ["PICKUP", "WHEAT", len(chain)]
        if (
            carrying is None
            and chain_needs_animal
            and (obs["private"]["shed"].get("COW", 0) > 0 or obs["private"]["shed"].get("SHEEP", 0) > 0)
        ):
            waiting = [a for a in ("COW", "SHEEP") if obs["private"]["shed"].get(a, 0) > 0]
            pickup = min(waiting, key=lambda a: (placed_counts[a], -obs["private"]["shed"].get(a, 0)))
            return ["PICKUP", pickup, 1]

    if (hx, hy) in chain:
        if hand_tile is None:
            return ["BUILD_PASTURE"]
        if hand_tile.get("kind") in ("PLANT", "WEED"):
            # The farmer's LOOP_ORDER_12 (CHAIN_H4 only -- CHAIN_NW isn't
            # on it) can plant here before this tile is claimed as
            # pasture. DIG reclaims it; a one-turn race, once per tile.
            return ["DIG"]
        if hand_tile.get("kind") == "PASTURE" and hand_tile.get("animal") is None:
            return ["PLACE", carrying, 1] if carrying else move
        if wheat_held > 0 and not hand_tile.get("fed_today"):
            return ["FEED"]
        if hand_tile.get("fertilizer_available"):
            return ["COLLECT_FERTILIZER"]
        if not hand_tile.get("cared_today"):
            return ["CARE"]
        if hand_tile.get("yield_units", 0) > 0:
            return ["HARVEST"]
        if wheat_held == 0 and not hand_tile.get("fed_today"):
            return _move_toward(hx, hy, ANCHOR_LOCAL[0], ANCHOR_LOCAL[1])
        # This tile is fully serviced for today -- advance to the next
        # tile in the chain rather than parking (the bug that capped
        # this design at 2-3 pastures the first time it was measured:
        # a hand that stopped here forever never got back to
        # WEED-spawning/farmer-planted tiles elsewhere in its own chain).
        return move

    if wheat_held == 0:
        return ["PASS"] if (hx, hy) == ANCHOR_LOCAL else _move_toward(hx, hy, ANCHOR_LOCAL[0], ANCHOR_LOCAL[1])
    return move

def agent(obs):
    """Crop selection (from the replay's real market orders, not
    day<10/>=10): BUY_SEED MELON fires ONCE at step 0 (12 units) and is
    never replenished; BUY_SEED WHEAT tops up on-goingly. BUY_SEED
    STRAWBERRY/CARROT fire once at day 4 (matching the replay's real
    first purchases of both that day), not step 0/day 20. crop_to_plant
    picks MELON while any melon seed remains, then CARROT while any
    carrot seed remains, then WHEAT.

    Hire cap: 5 -> 8 (day>=6, NE hands 5/6/7) -> 10 (day>=6, hands 8/9,
    the shared animal-care pool below).

    BUY_LAND bug (chat, found via an instrumented episode -- the same
    class of bug as the day==6/>=6 HIRE fix earlier in this notebook,
    just never applied here too): the trigger was `day == 6`, a strict
    one-shot. If money isn't actually >= $1000 that exact day (it
    usually isn't -- confirmed: ~$200 on day 6 in a real episode, way
    short), the order fails silently in the engine and, since day==6
    never matches again, NE stays locked *for the entire rest of the
    game*. Fixed: `day >= 6`, so it keeps retrying every day until
    affordable. Verified: NE unlocks around day 11 in a real episode.

    GOOSE/COOP dropped (chat decision): not a real income pillar in the
    replay, and was broken (transit collision with hand 2) in every
    prior graduated agent that carried it.

    SHEEP (1st, hand 4) / COW (hand 2) WHEAT restock bug (chat, found via
    an instrumented episode): both hands only ever picked up WHEAT while
    still walking to their PASTURE/COOP the *first* time -- once settled
    (self-looping on their own tile forever), they never returned to the
    shed. The animal ran unfed for 2 consecutive days and escaped
    (confirmed in the engine: `consecutive_unfed >= 2` -> "Animal
    escapes; structure remains"). Fixed in two parts, both needed:
    1. Once the animal is confirmed already placed, if the hand's own
       WHEAT inventory hits 0, it overrides its fixed
       GOOSE_FEEDER/PASTURE_FEEDER route (one-way, toward the tile --
       just following it bounces the hand right back) with
       `_move_toward` aimed at the shed `(4, 4)` until it picks more up.
    2. The `BUY_PRODUCT WHEAT` backstop used to stop at `day < 13` --
       with more animals now competing for WHEAT, the shed was
       genuinely empty when the hand got there (not a routing bug), so
       part 1 alone just oscillated waiting for stock that never came.
       Backstop is now unconditional (buy 1 whenever the shed is empty),
       not just early-game insurance.
    Verified via an instrumented episode: SHEEP stays placed the whole
    game post-fix (previously escaped ~day 15 every time).

    Animal-hijacking bug (chat, found right after the BUY_LAND fix above
    -- fixing that exposed this one, it was masked before since NE never
    unlocked and hands 8/9 never had a tile to build on regardless):
    hand 2/4's transit branch still had its *original* "pick up my own
    animal on the way to my structure" check (`SHEEP/COW == 0 in my
    inventory and shed has one -> PICKUP`), and it's checked *before*
    the WHEAT-pickup check. Once hand 2/4's own animal is already placed,
    that check should never fire again -- but it still did, every time
    hand 2/4 detoured to the shed for a WHEAT restock (see the bug
    above): if hands 8/9 had just bought a *replacement* COW/SHEEP and
    left it in the shed, hand 2/4 grabbed it first (lower index, and its
    own inventory genuinely reads 0 for that animal since it doesn't
    carry the one already placed). Hand 2/4 has nowhere to put a second
    animal, so it just sat in their inventory until the daily reset
    dropped it back to the shed -- where it would get hijacked again the
    next day. Confirmed via an instrumented episode: shed COW/SHEEP was
    always exactly 0 whenever hands 8/9 checked. Fixed: that pickup is
    now gated on `not sheep_already_placed`/`not cow_already_placed`.

    Staged BUY_ANIMAL bug (chat -- the *third* instance of the same
    one-shot-trigger class as the HIRE and BUY_LAND fixes above): the
    replay's real re-buy schedule (COW +1 day 2, +1 day 3, +2 day 7, +1
    day 9; SHEEP +2 day 6, +2 day 8, on top of the COW x2 / SHEEP x2
    bought at step 0) was encoded as `if obs["day"] == X: BUY_ANIMAL
    ...` -- fires on that exact day and never again. Money is extremely
    tight through this stretch (it hits $0 by day 4 in a real episode),
    so an unaffordable order just doesn't execute in the engine (no
    error, `_commit_unit` returns False and the order is dropped) and,
    with a `==` trigger, is never retried. Confirmed via an instrumented
    episode tracking `obs["private"]["shed"]` and every
    `obs["private"]["inventories"][i]` from day 12 to day 20: shed COW
    and SHEEP were *both* exactly 0 the whole time and no hand carried
    one either -- the extra animals were simply never bought.

    `==` -> `>=` is not the fix here (unlike HIRE/BUY_LAND) because each
    of these orders carries a quantity: `day >= X` would re-fire every
    single turn from day X on and overbuy without bound. Fixed as a
    *cumulative-target retry* instead: ANIMAL_TARGETS holds how many of
    each animal we should own in total by each checkpoint day (COW
    2/3/4/6/7 at days 0/2/3/7/9; SHEEP 2/4/6 at days 0/6/8 -- the same
    schedule, re-expressed cumulatively). Each turn we take the latest
    checkpoint <= today, count how many we *actually* own everywhere
    (shed + every inventory + every tile whose `animal` matches), and
    queue a BUY_ANIMAL for just the shortfall. The engine commits
    multi-unit orders one unit at a time (`_process_market`'s per-unit
    lockstep loop), so a partly-affordable order still buys what it can.
    That makes the schedule self-correcting whichever day the money
    shows up, and it stops on its own the moment the target is met -- it
    also re-buys automatically if an animal is lost. The step-0 COW x2 /
    SHEEP x2 / MELON x12 orders stay as one-shots: money is high enough
    at step 0 that those do reliably land, and the day-2 checkpoint
    would cover them anyway if they didn't. Verified via an instrumented
    episode: shed COW/SHEEP goes from a flat 0/0 all game to a stocked
    5/5 from day 12 on.

    LOCKED-tile trap, hands 8/9 (chat, found by monkeypatching the
    engine's `_apply_unit_action` to log what it actually receives and
    what it does with it -- fixing the BUY_ANIMAL bug above exposed
    this, because before it there was never an animal in the shed for a
    stuck hand to fail at picking up). The engine short-circuits *every*
    non-move op on a LOCKED tile, and does so before dispatching the op
    at all:
        tile = farm["tiles"][fy][fx]
        if tile == "LOCKED": return          # kaggriculture.py:323-325
    `_spawn_hand` deliberately spawns new hands onto shed-access tiles
    even when they're locked ("blocking movement would strand it
    there"), and two of the four shed-access tiles -- `(4, 5)` (SW) and
    `(5, 5)` (SE) -- sit in quadrants this agent never buys. Meanwhile
    this branch's PICKUP checks only looked at position and shed stock,
    never at the tile itself, so a hand spawned on `(4, 5)` matched the
    "shed-adjacent, shed has a COW -> PICKUP" check and re-issued that
    PICKUP *every single turn, forever*, with the engine discarding it
    every time. The `elif hand_tile == "LOCKED": op = ["PASS"]` branch
    sat below the PICKUP checks so it was never even reached -- and PASS
    would have been just as permanent a dead end anyway. Confirmed via
    the patched engine: hand 9 at `(4, 5)`, `shed_adjacent=True`,
    `board=10`, `before shed=4 inv={}` / `after shed=4 inv={}` on every
    step from 298 onward, while hand 8 at `(4, 4)` in the *same* step
    picked up fine (`shed 5->4`). A standalone repro confirms the same
    PICKUP succeeds at `(4, 5)` when that tile isn't LOCKED, so it is
    the LOCKED guard and not shed-adjacency. Fixed: the LOCKED case is
    checked *first* and folded into the ordinary fall-through -- it
    resolves to the same `_move_toward(target)` every other
    "nothing-to-do-here" case uses, never to PASS, so the hand always
    walks off the locked tile toward wherever it was actually headed.
    (Movement itself is legal on LOCKED tiles: the engine's move
    dispatch sits above that guard.)

    Animal-carrier deadlock, hands 8/9 (chat, found in the same trace):
    the branch order tested "am I standing on a PASTURE that has an
    animal -> tend it" *before* "am I carrying an unplaced animal -> go
    build somewhere". Once that tile's animal was fed/cared/harvested
    the tend branch resolved to PASS, so a hand that happened to walk
    over an already-placed animal on its way to a free tile parked there
    for the rest of the day with a live COW in its pocket. Confirmed:
    `h8 pos(4, 2) inv{'COW': 1, 'WHEAT': 1} op ['PASS']`, repeating --
    `(4, 2)` is GOOSE_TILE, hand 4's SHEEP. It only ever got a second
    COW placed on the days its route happened to go WEST first and miss
    that tile. Fixed: carrying is resolved before maintenance --
    BUILD_PASTURE / PLACE if the tile underneath can take the animal,
    otherwise keep moving toward `_nearest_free_tile`; the tend branch
    is only reachable when not carrying. A carrier does now walk past
    animals needing FEED/CARE without stopping, but nothing is lost by
    that: hand 2/4 tend their own tiles unconditionally, and any pool
    hand that isn't carrying still routes to the hungry/care targets
    below, so such a tile is picked up a turn or two later rather than
    skipped -- and an animal only escapes after two *consecutive* unfed
    days, far more slack than that deferral needs.

    Pickup priority: WHEAT before animal (chat -- the fix for the
    starvation loop the two fixes above exposed). Once hands 8/9 could
    finally place animals, an instrumented episode showed them placing
    animals and then letting every one starve: across days 11-29 the
    pool issued BUILD_PASTURE / PLACE / CARE / moves / PASS and **zero
    FEED, zero PICKUP WHEAT** -- every day's pool pickups were literally
    `{'COW': 2}`. Cause: the animal-PICKUP check sat above the
    WHEAT-PICKUP check, and shed COW is never 0 (2-4 every day, since
    escaped cows are immediately re-bought by the cumulative-target
    retry above). So a pool hand at the shed always grabbed another COW
    and never any WHEAT -- and FEED requires WHEAT in the hand's *own*
    inventory, so it could never fire. Every pool-placed COW cycled
    `consecutive_unfed` 0 -> 1 -> escape and the retry bought another:
    35 COW acquired, 28 escaped, 4 alive at the end, ~$14k burned.
    Priority direction was settled against the replay itself rather than
    guessed (`replays/103962387.json`, both seats): `PICKUP WHEAT`
    occurs 86-102 times per game and `FEED` 266-326, while `PICKUP COW`
    and `PICKUP SHEEP` occur only 5-9 times each -- roughly once per
    animal ever bought. Fetching WHEAT is the frequent recurring errand;
    fetching an animal is a near one-off. Fixed by swapping the two
    checks: at the shed a pool hand tops up WHEAT first, and the elif
    ordering then means it only reaches for an animal when it already
    holds WHEAT (or the shed has none to take) -- so it arrives at the
    new pasture able to FEED what it just placed, on the same trip.

    Fair COW/SHEEP pickup choice (chat, the other half of the same
    starvation trace): the choice was `"COW" if shed COW > 0 else
    "SHEEP"`, so while any COW sat in the shed -- which was always,
    given the escape/re-buy loop -- SHEEP was never picked at all. Shed
    SHEEP stayed pinned at exactly 5, untouched, from day 11 to the end
    of the game, and SHEEP_placed never left 1. Fixed: among the animals
    actually waiting in the shed, take whichever has *fewer* currently
    placed on the farm, ties broken toward the larger shed backlog. That
    self-balances the two herds instead of letting the first-listed one
    monopolise every trip, and it reuses `placed_counts`, now computed
    once per turn and shared with the ANIMAL_TARGETS owned-count above
    (one tile scan per turn instead of two).

    Feed before expand (chat, the last piece -- the WHEAT-first reorder
    alone was necessary but not sufficient). With WHEAT ahead of animal
    in the pickup order, FEED finally started firing, but only 1-2 times
    a day against 5-7 pool-placed animals, and escapes stayed high
    (26 animals lost, money 12.9k). The trace showed why: every day both
    pool hands spent their entire 24 turns on one *expansion* round-trip
    each -- pickups were exactly `{'WHEAT': 2, <animal>: 2}` per day --
    and only fed the animal they happened to place at the end of it.
    `roam_target = ANCHOR` fires whenever the shed holds any animal, and
    the shed always holds animals while the retry above is topping up,
    so `_nearest_needs_care_tile` roaming effectively never ran. Fixed
    by making hunger outrank fetching: a pool hand carrying WHEAT walks
    to the nearest *unfed* placed animal, and the shed animal-pickup is
    gated on there being no unfed animal anywhere. Unfed is the only
    state that actually kills (`consecutive_unfed >= 2`), so it is the
    right thing to gate on -- gating on `_nearest_needs_care_tile`
    instead was tried first and is too strong: something always needs
    CARE or HARVEST, so expansion stopped dead (2 COW / 1 SHEEP, 10
    animals left in the shed, money 26.7k). Gating on hunger alone keeps
    both: escapes fell 26 -> 3, SHEEP got placed at last, and money went
    12.9k -> **36.1k**, the best of this whole thread.

    Buy only what the pool can place (chat, closing the last gap in this
    thread: ~$4k of bought animals sitting idle in the shed). Measured
    the pool's real care capacity with an instrumented episode first,
    rather than guessing a cap: from day 14 to the end of the game the
    farm sits in an exact steady state of **4 placed / 4 fed / 0 hungry
    / 9 unplaced**, every single day, with the pool landing exactly
    2.0 FEED per day (one per pool hand) on top of hand 2/4 feeding
    their own. So sustainable capacity is 4 animals, while
    ANIMAL_TARGETS was chasing the replay's 13 -- the other 9 were
    bought and then parked in the shed for the rest of the game.
    Adding pool hands to cover them was rejected on the numbers already
    established above (cumulative Fibonacci `_hire_cost`, charged again
    every single day), so the fix is to stop over-buying instead: a
    BUY_ANIMAL is only queued when *nothing* is currently unplaced
    (shed + every inventory), and it queues 1 unit rather than the whole
    shortfall. That needs no magic capacity constant -- purchasing now
    follows placement, and placement is already hunger-gated by the
    paragraph above, so the schedule self-throttles to whatever the pool
    can really sustain and resumes on its own if capacity ever grows.
    Verified properly, because single-episode money swings ~5k run to
    run here (the market is shared with the opponent, so our own orders
    move their outcome too) and one sample per variant proves nothing:
    an 8-seed *paired* A/B, same seeds for both variants, gives mean
    33,469 -> **36,778** (+9.9%), median 33,280 -> 36,498, and post-cap
    is ahead on **all 8 of 8 seeds** individually. Animals acquired
    drops 16 -> 9 and idle shed stock 9 -> 1. (A per-species variant --
    one COW *and* one SHEEP in flight -- was tried and not carried
    forward: two in flight is already more than the pool clears. It was
    only ever single-sampled, so treat that comparison as indicative,
    not measured.)

    DIG: built into `_tile_action` itself.

    FERTILIZE: farmer-only, picks up FERTILIZER when shed-adjacent and
    applies it to its own PLANT tile ahead of water/harvest.
    `BUY_PRODUCT FERTILIZER` also queued once at day 6 (qty 2, matching
    the replay's real first purchase), on top of what's collected from
    animals.

    DROP (chat, closing a compliance gap against the replay -- an
    efficiency gap, not a rule violation): the farmer's own harvests go
    into its own inventory (`_inv_add` on HARVEST, confirmed in the
    engine), only flushed to the shed automatically once per day
    (`_drop_inventories_to_shed`, at the daily reset). The farmer now
    drops everything except a held FERTILIZER (reserved for FERTILIZE)
    whenever it's shed-adjacent and carrying something. Hands still rely
    on the daily flush; only the farmer got this so far.

    Shared-hands animal care, hands 8/9 (chat decision, replacing the
    earlier "one dedicated hand per animal" design): instrumented the
    replay directly and found it reaches 13 total animals (7 COW + 6
    SHEEP by day 9) with only 9 hands *total* -- nowhere near a 1:1
    dedicated-hand-per-animal ratio. Tried that ratio first (hands 8-18,
    cap 19) and it was a real dead end, not a bug: hands reset to 0
    every day, and the per-day hire cost is cumulative Fibonacci
    (`_hire_cost`) -- hiring up to 19 in one day costs $10,945 in that
    day alone, repeated every day for the rest of the game. Confirmed
    via `evaluate()`: money crashed to near-$0 and stayed there.

    So hands 8/9 are a small *shared* pool instead. Priority each turn,
    in order: standing on a LOCKED tile -> walk off it toward the
    current target; carrying an unplaced animal -> BUILD_PASTURE / PLACE
    here if this tile can take it, else keep walking to the nearest free
    tile (searched from the fixed anchor (4,4) so the target doesn't
    flip mid-walk); standing on a placed animal needing
    FEED/COLLECT_FERTILIZER/CARE/HARVEST -> do it; shed-adjacent and out
    of WHEAT -> PICKUP WHEAT; shed-adjacent holding WHEAT with nothing
    hungry and an animal waiting -> PICKUP that animal; otherwise walk
    to the nearest hungry animal if carrying WHEAT, else to the shed if
    an animal is waiting, else to whatever needs care next. Market
    orders below queue the replay's full real schedule (7 COW/6 SHEEP
    total by day 9).

    Hand 2/4 shed ping-pong (chat, found by tracing hand 4 turn by turn
    through day 1 of a real instrumented episode -- the leftover of the
    WHEAT-restock fix above, which got the hand *to* the shed but never
    said what to do once it was standing there). With the animal placed
    and the hand's own WHEAT at 0, the restock branch is gated on
    `(hx, hy) != ANCHOR`, so it only fires while the hand is *away* from
    the shed. On ANCHOR with an empty shed that branch is skipped, the
    `PICKUP WHEAT` branch above it needs stock the shed hasn't got, and
    the fall-through is `move` -- which for hand 4 is
    `GOOSE_FEEDER[(4, 4)] = (4, 3)`, one step NORTH. Next turn it's off
    ANCHOR again, the restock branch fires, and walks it back SOUTH.
    Confirmed on seed 1, day 1: hand 4 alternates `(4, 4)` -> `(4, 3)`
    -> `(4, 4)` from step 30 to step 47, 18 turns for zero net progress,
    and those are the only 9 SOUTH ops it issues in the entire game.
    Hand 2's COW branch has the identical 2-cycle. Fixed by moving the
    position test out of the guard and into the body: off ANCHOR, walk
    toward it as before; *on* ANCHOR, `PASS` and wait for a restock
    instead of stepping off. Strictly better rather than merely tidier,
    because the shed is exactly where WHEAT appears -- a bouncing hand
    is one tile away half the time and misses the turn stock lands.

    Why the shed is empty, though, is not what the ping-pong makes it
    look like, and that correction is the point of tracing instead of
    assuming. On day 1 the shed holds exactly 1 WHEAT; hand 2 is hired
    earlier so it reaches the shed first and takes it at step 29. The
    unconditional `BUY_PRODUCT WHEAT` backstop then fires on all 18
    remaining turns of that day and is rejected on all 18 -- WHEAT
    quotes at $28 and the farm is down to $16 after the morning's five
    hires and the `BUY_SEED WHEAT` top-up. Day 2 the farm has $2 and
    manages only 3 hires, so **hand 4 does not exist at all**: the
    SHEEP's second consecutive unfed day, and its escape at the day-3
    rollover, are a money problem, not a routing one. The COW repeats it
    one day behind ($0, 2 hands, escape at day 4). So this fix deletes
    real wasted turns but is *not* the escape mechanism, and it measures
    exactly that way: a paired 8-seed A/B comes back identical to the
    digit on all 8 seeds (mean 36,818 both arms, 23 escapes both arms).
    Kept anyway -- a dead 2-cycle is worth removing and it costs nothing
    -- but logged as outcome-neutral, not as a win.

    Scaling the shed WHEAT reserve was the obvious money-side follow-up
    and is **rejected on the numbers**. Selling down to 1
    (`wheat_in_shed > 1`) while four hands each want a WHEAT a day looks
    like the culprit, so the SELL floor and the `BUY_PRODUCT` target
    were both scaled to `1 + placed animals`. Paired 8-seed A/B: mean
    36,818 -> **34,928** (-5.1%), ahead on **0 of 8 seeds**, escapes
    23 -> 24. Buying WHEAT back at $28 a unit drains more than the
    reserve saves, and it does nothing for the days 1-4 window where the
    escapes actually happen, because in that window there is no money to
    buy anything at any reserve level.

    NE hands walking a quadrant we haven't bought yet (chat -- the
    project owner spotted this one in a real Kaggle replay first,
    "agentes van a zonas que todavia no se han comprado", and it
    reproduces locally). Hiring and land share the same `day >= 6`
    trigger, but `BUY_LAND` additionally has to *afford* $1000 and
    doesn't for a long while: confirmed in a real episode, NE unlocks on
    **day 11**, a five-day gap. Hands 5/6/7 are hired from day 6 and
    routed straight into `LOOP_ORDER_HANDS_NE` / `SPAWN_FEEDER_NE` /
    their own `ZONE_TOP_NE`/`ZONE_LEFT_NE`/`ZONE_RIGHT_NE`. Moving onto
    LOCKED tiles is legal (the move dispatch sits above the LOCKED
    guard, the same mechanic as the LOCKED-tile trap above), so nothing
    crashes -- they simply walk. Measured on seed 1: across days 6-10
    hands 5/6/7 spend **173 of 174 hand-turns standing on LOCKED tiles
    and issue zero tile ops**, while being re-hired and paid on every
    one of those days.

    Fixed in the routing, not in the hiring, and both were built and
    measured rather than argued. Delaying the 5->8 hire tier until NE is
    really unlocked is worth almost nothing (paired 8-seed A/B: mean
    +62, ahead on 4 of 8 seeds) -- the cumulative Fibonacci hire cost
    for hands 6/7/8 across the whole locked window is only ~$120, so
    what was lost was never the money, it was the work those hands
    didn't do. Letting them fall through to the ordinary NW routing
    (`HAND_ZONES[i % 5]`, the same branch every non-special hand uses)
    while `"NE" not in unlocked_quadrants` is the winner: **mean
    36,818 -> 38,797 (+5.4%), median 36,549 -> 38,775, ahead on 8 of 8
    seeds**, escapes 23 -> 16. Two other shapes were tried and are
    worse: roaming the full `LOOP_ORDER_HANDS` circuit untethered
    (+1,206, 6 of 8) and folding them into the hands-8/9 animal pool for
    the locked window (+577, 7 of 8). The fix is one expression --
    `ne_zone_by_index` is empty until NE is ours -- so nothing after day
    11 changes; confirmed in the trace, days 11-29 are the same routing
    and the same per-day tile-op counts as before. It also leaves the
    earlier "hire NE hands rather than relocate NW hands" decision
    standing: they are still hired on day 6, and still take up their NE
    zones the moment the land is bought.

    **This is the first change in this thread that flips the
    head-to-head.** `melon_then_wheat_goose_cow_agent` used to take 7 of
    8 paired seeds; post-fix we win **8 of 8**.

    ------------------------------------------------------------------
    Audit follow-up (chat): the replay's calendar was copied, its money
    efficiency was not. Every one of the roadmap's day triggers --
    `BUY_LAND` day 6, `BUY_SEED STRAWBERRY/CARROT` day 4 -- was lifted
    straight off `replays/103962387.json`, but the replay's agent could
    *afford* those days and this one could not, so our copies of the
    exact triggers were quietly failing. Five fixes below, measured in
    sequence with a paired 8-seed A/B (seeds 1-8, `episodeSteps` 720, vs
    `melon_then_wheat_goose_cow_agent`) at every step, starting from
    38,797.

    Routing-lookup crash guard (chat -- pure insurance, applied first so
    the rest could be measured at all). `hand_loop[(hx, hy)]` was an
    unguarded dict lookup. Once NE unlocks, hands 5/6/7 get the merged
    `LOOP_ORDER_HANDS_NE`/`SPAWN_FEEDER_NE`/zone dict, which has no key
    for any NW tile except `(4, 4)` -- so a hand standing anywhere else
    in NW at the exact moment `BUY_LAND` resolves raises `KeyError` and
    forfeits the episode. Not hypothetical: it killed 3 of the 5
    variants built while measuring the fixes below, precisely *because*
    each of them shifts the money curve and therefore the day the land
    lands on. Fixed by falling back to `_move_toward(ANCHOR)` when the
    key is missing, and by replacing the `DIRECTIONS[(dx, dy)]` lookup
    with `_move_toward` in the same spot (identical op for the adjacent
    targets these dicts actually hold, but it cannot raise on a
    non-adjacent one -- a `KeyError: (-3, 0)` from `DIRECTIONS` showed
    up in one experiment too). The farmer's `LOOP_ORDER_12` lookup got
    the same guard for the same reason, though the farmer respawns onto
    `(4, 4)` every day and has never actually left the loop. Measured on
    its own: **identical to the digit on all 8 seeds** -- which is
    exactly what insurance that does not fire should look like.

    HARVEST before `first_yield_day` (chat, confirmed against the engine
    and then in a trace). `_tile_action` chose HARVEST on
    `crop_age >= max_yield_day or yield_units >= max_yield` alone, but
    `kaggriculture.py:390-407` silently drops a HARVEST while
    `day - planted_day < CROPS[crop]["first_yield_day"]`. MELON reaches
    its `max_yield` of 6 at age 8 when the tile has been fertilized, and
    its `first_yield_day` is 10 -- so the unit stood on the tile
    re-issuing a rejected HARVEST for two whole days. Confirmed: 37
    rejected HARVESTs in one game, and the farmer visiting only 2 of its
    12 loop tiles on days 8-9 instead of the usual 8-11, with 4 melons
    weeding out at full yield. Fixed by adding the real `first_yield_day`
    to `CROP_INFO` (read off the installed package's `CROPS` dict, not
    assumed: WHEAT 2, CARROT 2, STRAWBERRY 10, MELON 10) and requiring
    `crop_age >= first_yield_day` as well. Falling through to WATER
    rather than to the move matters -- it keeps the immature plant from
    weeding while it finishes. Measured alone: **38,797 -> 40,808
    (+2,011), ahead on 8 of 8 seeds.**

    One HIRE per turn (chat -- the single biggest effect in this
    thread). The hire-cap block was an `if/elif/elif` chain, so at most
    **one** `["HIRE"]` was ever queued per turn and the roster did not
    fill until about hour 10 of each day: 45 hand-turns lost per day,
    ~18.75% of all hand labour, every day of the game. There was no
    reason for the pacing -- `_process_market` walks the whole market
    list and dispatches each order at its own index, so several HIREs in
    one list all land in the same turn, and `_hire_cost` charges the
    same cumulative Fibonacci total either way (it counts
    `hires_today`, not turns). Fixed by queuing the whole shortfall, up
    to 4 per turn, which keeps the list clear of
    `maxMarketOrdersPerTurn` (10, overflow **silently dropped**) --
    verified in a traced episode rather than argued: the longest market
    list this build ever produces is 9 orders and no turn on any of the
    8 seeds exceeds the cap. The two old `elif` tiers collapse into one
    `hire_cap` expression. Measured on top of the guard: **40,808 ->
    47,925 (+7,117), ahead on 8 of 8 seeds.**

    Step-0 animal overcommit (chat). The step-0 order bought
    `BUY_ANIMAL COW 2` + `SHEEP 2`, but only two animals are placeable
    that early -- hand 2 builds one COW pasture, hand 4 one SHEEP
    pasture, and hands 8/9, which could place more, do not exist until
    day 6 and need NE land that does not unlock until day 11 on the old
    build. So $900 of livestock sat in the shed through exactly the days
    the farm was cash-starved: day 1 money $16 against a $28 WHEAT quote
    (so the `BUY_PRODUCT WHEAT` backstop failed on all 19 remaining
    turns), day 2 $2 with only 3 hands hired, day 3 $0. The SHEEP
    escaped on day 3 and the COW on day 4 -- because their keeper hands
    could not be afforded, not because of any routing bug. Fixed by
    buying one of each at step 0; the cumulative `ANIMAL_TARGETS` retry
    already re-buys the second of each the moment it is both affordable
    and placeable, so nothing is given up long-run. Measured on top:
    **47,925 -> 50,419 (+2,494), ahead on 8 of 8 seeds.** Phase total so
    far: 38,797 -> 50,419, **+30.0%**, 8 of 8.

    Sell before buy, i.e. market-order *position* is a price (chat --
    the second-biggest effect, and the one that had to be re-measured
    from scratch because an earlier audit pass had it as a regression).
    `_process_market` walks both players' queues in lockstep **by order
    index**: at index i it quotes that index's unit for both players
    against the market inventory *as it stands at that index*, then
    commits. `_commit_unit`'s SELL bumps `market["inventory"][item]`,
    and price falls as inventory rises -- so whoever's SELL sits at the
    lower index is quoted before the other player's sales have glutted
    the book. This agent appended its SELLs last, behind up to nine
    buys, while `melon_then_wheat_goose_cow_agent` sells from index ~3;
    on day 11, when the first melon crop is dumped, that gap is worth
    thousands. Fixed with a stable sort putting SELLs at the front of
    the list. The mechanism was confirmed, not inferred: with the sort
    the traced episode sells the **identical** number of units of every
    single product (WHEAT 578, FERTILIZER 97, MILK 87, MELON 72, WOOL
    30, CARROT 6, STRAWBERRY 4), hires the identical hands on the
    identical days, and buys the land on the same day -- the entire gap
    is one step change of +$6,934 on day 11, i.e. price realised, not
    production. Measured on top: **50,419 -> 57,669 (+7,250), ahead on 8
    of 8 seeds.** Checked against three further opponents to make sure
    it is not an artifact of one opponent's queue shape rather than a
    real edge: +7,350 (8 of 8) vs `melon_then_wheat_goose_agent`,
    +8,004 (8 of 8) vs `melon_then_wheat_goose_cow_strawberry_agent`,
    and +2,524 (8 of 8) against a copy of our own pre-audit build.

    STRAWBERRY: a real retry, and the audit premise that turned out to
    be already fixed (chat). Going in, `if obs["day"] == 4: BUY_SEED
    STRAWBERRY` was the same one-shot class as the HIRE/BUY_LAND/staged
    BUY_ANIMAL bugs above, and on the pre-audit build it failed exactly
    that way -- $0 on all 24 turns of day 4, the seed never bought all
    game, and `STRAWBERRY_TILE = (0, 1)` sitting `None` for all 719
    steps. A strategy named after a crop it never planted. **That is no
    longer true after the four fixes above, and the trace says so before
    any change to this trigger**: on all 8 seeds the day-4 buy now lands
    on day 4 (the replay's own day), the tile is planted on day 4 (the
    replay plants day 5) and holds STRAWBERRY for 605 of 719 steps. The
    money fixes fixed the trigger. Made it a retry anyway -- `day >= 4`,
    gated on the seed being absent **and** the tile not already carrying
    a strawberry, so it neither re-buys behind a planted tile nor
    depends on one specific day's balance ever again -- and it is not
    the no-op it was expected to be: it also replants after the tile
    weeds out. Measured on top: **57,669 -> 60,285 (+2,616), ahead on 8
    of 8 seeds**, and it removes the one bad seed in the set (seed 4,
    47,119 -> 59,827).

    CARROT left exactly as it is (chat, argued from the trace rather
    than patched). The concern was that `crop_to_plant`'s
    `elif carrot_seeds > 0` branch routes *all* planting to CARROT the
    moment any carrot seed exists, ahead of WHEAT, and CARROT is a much
    worse continuous-replant crop (`max_yield` 4 against WHEAT's 6). On
    the pre-audit build that was real and a `day == 4` -> `day >= 4`
    change measured -5,644, 0 of 8. On this build it is not: the day-4
    order is `BUY_SEED CARROT 3`, a one-shot batch of three, and the
    trace shows exactly 3 CARROT plantings against 234 WHEAT and 49
    MELON across the whole game -- bounded, and about as marginal as the
    replay itself makes CARROT (1-4 plantings per hand, first planted
    day 21-25). Dropping CARROT entirely was built and measured on the
    finished build and is **not** an improvement: -1,071, ahead on only
    1 of 8 seeds. So it stays, on the numbers.

    **Rejected on the numbers, all three re-measured on the finished
    build rather than carried over from the audit's earlier build:**
    - Bounding the day-6 FERTILIZER purchase
      (`day >= 6 and shed < 2 -> BUY_PRODUCT FERTILIZER 1`, and a
      day-6-only variant of the same): **-22,642 and -23,344, ahead on
      0 of 8 seeds.** Worth writing down because the mechanism is a
      trap, not noise, and it also settles a Phase-2 question: dropping
      that one order shortens the day-6 market list by one, which slides
      `BUY_LAND` from index 3 to index 2 -- early enough that the
      morning's `SELL WHEAT 18` proceeds are still in hand when it is
      quoted, so it succeeds. The land is then bought on **day 6, the
      replay's own day**, and it is a disaster: the $1,000 comes out of
      exactly the cash that funds the 5 -> 10 hire ramp, and the farm
      runs days 6-10 on 0-4 hands instead of 10 (MELON sold 36 vs 72,
      MILK 43 vs 87). So we deliberately do *not* chase the replay's
      day-6 land milestone -- the replay's agent could afford land and
      hands on the same day and this one cannot. Day 7 (down from day
      11) is where this build should be.
    - The missing NE tile. `ZONE_TOP_NE` (10) + `ZONE_LEFT_NE` (6) +
      `ZONE_RIGHT_NE` (8) is 24 of the quadrant's 25 tiles, and `(8, 3)`
      is genuinely dead -- LOCKED, then `None`, never tended. It cannot
      be fixed by adding it to a zone, and that is a parity fact rather
      than a lack of imagination: a zone dict maps each tile to exactly
      one successor, so a zone is a closed walk, and a closed walk on
      unit steps alternates tile colours, so every zone must have an
      even tile count -- three even numbers cannot sum to 25. The best
      available shape (an 8-cycle each for LEFT and RIGHT, overlapping
      on `(7, 3)`, which does cover all 25) measures **-811, ahead on 2
      of 8 seeds**. One dead tile is cheaper than the disruption.
    - An unconditional `SELL WOOL` alongside the MILK/MELON/WHEAT sells,
      instead of only from hand 4's idle branch: **-1,213, ahead on 2 of
      8 seeds.** It adds an order to a list already at 9 of the 10-order
      cap, and the position effect above cuts both ways.

    **Where this leaves the numbers**: paired 8-seed A/B against
    `melon_then_wheat_goose_cow_agent`, pre-audit build vs this one, same
    seeds both arms -- mean **38,797 -> 60,285 (+55.4%)**, median 38,775
    -> 60,242, ahead on **8 of 8 seeds** individually (+19,122 to
    +24,296), head-to-head **8 of 8**. `BUY_LAND` resolves on day 7 on
    every seed (was day 11), STRAWBERRY seed on day 4 on every seed (was
    never).

    ------------------------------------------------------------------
    2026-09-03 session: chain hands, then SW reconsidered. Three real
    replays (`103962387`, `105002288` -- a real Kaggle loss, 47,259 vs
    "edteoh"'s 167,058 -- and `105046178`) all converge on the same
    14-tile pasture block hugging the spawn row, none uncultivated.
    Tracing real actions found why our 2-pool-hand model couldn't match
    it: strong agents bulk-pick 4-6 WHEAT per shed trip and tend a
    circuit of pastures; we picked up 1 unit at a time, capping care at
    one animal fed per trip regardless of hand or tile count. Replaced
    hand 2/4's single-tile dedicated-pasture model, plus hand 6
    (formerly a `ZONE_LEFT_NE` crop hand), with `_chain_hand_op`: bulk
    `PICKUP WHEAT len(chain)`, `DIG` anything the farmer plants on a
    chain tile first, then the same BUILD/PLACE/FEED/CARE/HARVEST
    priority per tile. Wheat reserve now scales `1 + 3*(placed animals)`
    instead of a flat 1, plus a feed floor and `hire_cap` 10 -> 9 (the
    10th hand's fee no longer earns its keep once 3 hands do animal
    care). Two real bugs found verifying this against the 8-seed A/B:
    a "nothing left to do" fallback of `PASS` instead of `move` parked a
    chain hand on its first tile forever (3 pastures, not 14, until
    fixed); and `CHAIN_NE`'s `(5,4)` tile being *both* a chain tile and
    shed-adjacent meant hand 6 never once detoured to fetch an animal
    until shed errands were checked before chain-tile membership.
    Measured: **64,159 -> 102,303 (+59.5%), 8 of 8 seeds.**

    SW land was re-tried on top of this and this time it holds: with
    the 14-pasture chain economy already fixed, the earlier SW rejection
    (this same session, before chain hands existed) no longer applies.
    Re-enabled `BUY_LAND` up to 3 quadrants, added 3 new STRAWBERRY
    zones in SW (`ZONE_TOP_SW`/`LEFT_SW`/`RIGHT_SW`, built by shifting
    the NE zone shapes -- SW's x-range matches NW's, not NE's) for 3 new
    hands, and `hire_cap` 9 -> 12 once SW is unlocked. Also converted
    `ZONE_TOP_NE` (hand 5) to STRAWBERRY -- rejected earlier this same
    session under the pre-chain economy, positive now for the same
    reason as SW. Measured in sequence: **102,303 -> 109,340 (SW) ->
    111,603 (+ ZONE_TOP_NE), 8 of 8 seeds both steps.**

    edteoh's crop mix investigated, and the WHEAT-tightness worry above
    turned out to be unfounded. edteoh actually grows WHEAT on **41**
    tiles (vs 13 STRAWBERRY, all in SW) -- the opposite emphasis from
    this build -- so the working hypothesis was "we need more WHEAT, not
    more STRAWBERRY." Tested directly: reverting any of the SW/NE
    STRAWBERRY zones back to `crop_to_plant` **always loses**, and it's
    monotonic -- the more reverted, the worse:
    - All 3 SW zones back to WHEAT: **-8,853**
    - 2 of 3 SW zones back to WHEAT: **-3,157 to -5,121**
    - SW all-WHEAT + `ZONE_TOP_NE` also reverted: **-11,920**

    Also tested and confirmed **not** the bottleneck: raising the
    `BUY_PRODUCT WHEAT` per-turn cap from 5 to 15 changes nothing
    (+1) -- the cap was never binding, so the low WHEAT-sold figure is
    a sign of an efficiently-spent surplus, not a starved one. So more
    STRAWBERRY remains correct for this build; edteoh's wheat-heavy mix
    doesn't transfer, most likely because its payoff depends on
    something structural we haven't replicated (see below) rather than
    the crop ratio itself.

    Three more edteoh-motivated ideas built and rejected, all measured
    the same way:
    - **A 15th pasture** (a 4th chain, `CHAIN_2 = [(1,4),(2,3),(2,4),
      (3,4)]`, mirroring 4 of edteoh's extra tiles, hand 12,
      `hire_cap` 13): **-5,845**. Consistent with the 4th-chain/3rd-pool
      -hand rejections earlier in this file -- going past 14 still
      doesn't pay under this build's economy.
    - **Raising `ANIMAL_TARGETS`' final checkpoint to 14** (COW 7->8 or
      SHEEP 6->7), to actually fill the 14th pasture tile (`(6,4)` was
      confirmed, on 3 separate seeds, to sit built-but-permanently-empty
      -- `ANIMAL_TARGETS` caps at COW 7 + SHEEP 6 = 13, one short of the
      14 chain slots this build actually has): **-6,200 either way**,
      and the herd still doesn't stabilize at 14 -- it re-buys
      repeatedly without holding the extra animal. The empty 14th tile
      is real and understood, but is not free money to fix.
    - **Growing `crop_to_plant` on a chain tile while waiting for an
      animal**, instead of an eager `BUILD_PASTURE` the moment the tile
      is reached (prompted directly by watching the replay: several
      chain tiles sat as empty, unusable PASTURE for days before an
      animal was available to fill them -- true, but expensive to fix
      this way): **-30,093, the worst result measured in this entire
      file.** Once an animal *is* ready, converting a cropped tile back
      takes 3 separate loop passes (`DIG` the crop, `BUILD_PASTURE`,
      `PLACE`) instead of 1, which delays herd establishment by several
      days across up to 6 tiles per chain; and because animals are
      bought throughout days ~2-9 (see `ANIMAL_TARGETS`), most tiles'
      waiting window is too short for the crop grown there to mature
      before being dug up, so the seed spend is usually a pure loss. The
      early empty-pasture "waste" this was meant to fix is cheaper than
      the fix.
    - **Tapering `hire_cap` down in the last 4 days** (day>=26: 12->9,
      dropping hands 9/10/11, the SW-STRAWBERRY hands, on the theory
      that new plantings that late can't mature before day 30 anyway):
      **-3,385**. Doesn't apply here -- STRAWBERRY is an *ongoing* crop,
      so those hands are still harvesting already-established plants
      right up to the end, not waiting on anything new to mature. This
      specific objection would need to target a genuine one-shot
      late-planting waste (WHEAT/MELON/CARROT past a day where they
      cannot reach `first_yield_day` before day 30) to have a shot --
      not measured, reasoned only: WHEAT's `first_yield_day` is 2, so
      even a day-29 planting gets a partial harvest, and MELON hasn't
      been bought fresh since step 0, so the plausible waste here is
      small either way.

    **Still open**: `edteoh`'s replay (105002288.json) still beats this
    build (167,058 vs this build's local-benchmark 111,603 -- not
    directly comparable, different opponent) with **17** pastures/
    animals against our 14 and noticeably higher FERTILIZER (460) and
    WOOL (285) volumes. Every direct attempt to close this gap so far
    (more WHEAT, a 15th pasture, filling the 14th, cultivating chain
    tiles pre-animal, tapering late hires) has measured negative -- the
    mechanism behind edteoh's extra capacity is still unidentified, not
    just unbuilt.
    """
    melon_seeds = obs["private"]["seeds"].get("MELON", 0)
    wheat_seeds = obs["private"]["seeds"].get("WHEAT", 0)
    carrot_seeds = obs["private"]["seeds"].get("CARROT", 0)
    if melon_seeds > 0:
        crop_to_plant, crop_seeds = "MELON", melon_seeds
    elif carrot_seeds > 0:
        crop_to_plant, crop_seeds = "CARROT", carrot_seeds
    else:
        crop_to_plant, crop_seeds = "WHEAT", wheat_seeds
    # Shared across every `_tile_action` call this turn for crop_to_plant
    # (hands and farmer alike) so the agent never requests more PLANTs
    # for one crop than it has seeds -- see the seed-budget paragraph in
    # `_tile_action`.
    crop_seed_budget = [crop_seeds]

    # STRAWBERRY_TILE is the original single plant; ZONE_RIGHT_NE (hand
    # 7's 8 tiles, already-owned NE land, no extra hires) adds 8 more
    # once NE is bought -- see the strawberry-acreage paragraph. SW land
    # and a dedicated SW-strawberry hand were tried and rejected (Opus
    # diagnosis, 2026-09-03): SW's $2,000 never earns back inside a
    # 29-day game, and a 3rd animal-pool hand loses money independent of
    # land, because the real cap on the pool was never hand count -- it
    # was near-shed tiles (only 4 exist), and a 3rd hand just walks
    # animals to distant tiles they can't reach daily to feed. Do not
    # re-add SW/hire_cap>10/a 3rd pool hand without a new mechanism for
    # the near-shed-tile constraint.
    strawberry_seeds = obs["private"]["seeds"].get("STRAWBERRY", 0)
    sw_unlocked = "SW" in obs["farms"][obs["player"]]["unlocked_quadrants"]
    ne_unlocked = "NE" in obs["farms"][obs["player"]]["unlocked_quadrants"]
    strawberry_target_tiles = (
        [STRAWBERRY_TILE]
        + (list(ZONE_TOP_NE) + list(ZONE_RIGHT_NE) if ne_unlocked else [])
        + (list(ZONE_TOP_SW) + list(ZONE_LEFT_SW) + list(ZONE_RIGHT_SW) if sw_unlocked else [])
    )
    strawberry_unplanted = sum(
        1
        for (tx, ty) in strawberry_target_tiles
        if not (
            isinstance(obs["farms"][obs["player"]]["tiles"][ty][tx], dict)
            and obs["farms"][obs["player"]]["tiles"][ty][tx].get("crop") == "STRAWBERRY"
        )
    )
    # Shared across every STRAWBERRY `_tile_action` call this turn (the
    # fixed tile and, once unlocked, the SW zone) for the same reason as
    # crop_seed_budget above: several tiles wanting to plant the same
    # turn must not jointly out-request the atomic per-crop PLANT cap.
    strawberry_seed_budget = [strawberry_seeds]

    market = []
    hands = []

    if obs["step"] == 0:
        market.append(["BUY_ANIMAL", "COW", 1])
        market.append(["BUY_ANIMAL", "SHEEP", 1])
        market.append(["BUY_SEED", "MELON", 12])
    if obs["day"] >= 4 and strawberry_unplanted > strawberry_seeds:
        market.append(["BUY_SEED", "STRAWBERRY", strawberry_unplanted - strawberry_seeds])
    if obs["day"] == 4 and carrot_seeds == 0:
        market.append(["BUY_SEED", "CARROT", 3])
    if obs["day"] == 6:
        market.append(["BUY_PRODUCT", "FERTILIZER", 2])

    # One tile scan per turn, shared by the ANIMAL_TARGETS owned-count
    # below and the pool's COW/SHEEP pickup choice further down.
    placed_counts = {"COW": 0, "SHEEP": 0}
    for row in obs["farms"][obs["player"]]["tiles"]:
        for animal_tile in row:
            if isinstance(animal_tile, dict) and animal_tile.get("animal") in placed_counts:
                placed_counts[animal_tile["animal"]] += 1

    # Never buy another animal while one is still waiting to be placed --
    # see "Buy only what the pool can place" in the docstring.
    unplaced_animals = 0
    for species in ("COW", "SHEEP"):
        unplaced_animals += obs["private"]["shed"].get(species, 0)
        for inventory in obs["private"]["inventories"]:
            unplaced_animals += inventory.get(species, 0)

    # Cumulative animal targets by checkpoint day -- see the "Staged
    # BUY_ANIMAL bug" paragraph in the docstring. Day 0 (COW 2 / SHEEP 2)
    # is the step-0 order above; every later checkpoint is a retrying
    # top-up to the cumulative total, not a one-shot on that exact day.
    ANIMAL_TARGETS = {"COW": {2: 3, 3: 4, 7: 6, 9: 7}, "SHEEP": {6: 4, 8: 6}}
    for animal, checkpoints in ANIMAL_TARGETS.items():
        reached = [d for d in checkpoints if d <= obs["day"]]
        if not reached:
            continue
        target = checkpoints[max(reached)]
        owned = obs["private"]["shed"].get(animal, 0) + placed_counts[animal]
        for inventory in obs["private"]["inventories"]:
            owned += inventory.get(animal, 0)
        if owned < target and unplaced_animals == 0:
            market.append(["BUY_ANIMAL", animal, 1])

    # Feed floor, not a bare "shed is empty" backstop (Opus diagnosis,
    # 2026-09-03): with chain hands feeding a real herd, running the
    # shed down to 0 before buying starves whichever hand's trip lands
    # on an empty shed. Buys up to 5 at a time toward keeping at least
    # one WHEAT per placed animal in reserve.
    feed_floor = max(1, placed_counts["COW"] + placed_counts["SHEEP"])
    wheat_now = obs["private"]["shed"].get("WHEAT", 0)
    if wheat_now < feed_floor:
        market.append(["BUY_PRODUCT", "WHEAT", min(5, feed_floor - wheat_now)])
    # EXPERIMENT, 2026-09-03: SW ($2,000) re-enabled. Previously rejected
    # (2026-09-03 earlier) on the pre-chain-hand economy, where the herd
    # was capped near 4 animals and a 3rd pool hand lost money outright
    # -- that conclusion no longer holds against the current chain-hand
    # build (14 pastures, bulk WHEAT). Re-measuring on the numbers, not
    # assuming the old rejection still applies.
    if obs["day"] >= 6 and len(obs["farms"][obs["player"]]["unlocked_quadrants"]) < 3:
        market.append(["BUY_LAND"])

    # Hands 5/6/7 only take up their NE zones once NE is actually ours.
    # Hiring is gated on day >= 6 but BUY_LAND also has to afford $1000,
    # which doesn't land until ~day 11; empty here means they fall
    # through to the ordinary NW routing below instead of walking a
    # locked quadrant -- see the NE-hands paragraph in the docstring.
    ne_zone_by_index = (
        {5: ZONE_TOP_NE, 6: ZONE_LEFT_NE, 7: ZONE_RIGHT_NE}
        if "NE" in obs["farms"][obs["player"]]["unlocked_quadrants"]
        else {}
    )
    # EXPERIMENT, 2026-09-03: hands 9/10/11 (new once hire_cap allows SW)
    # grow STRAWBERRY across most of SW, mirroring what all 3 real strong
    # replays actually do with their 3rd quadrant -- see the SW zone
    # constants above.
    sw_zone_by_index = (
        {9: ZONE_TOP_SW, 10: ZONE_LEFT_SW, 11: ZONE_RIGHT_SW} if sw_unlocked else {}
    )
    ANCHOR = (4, 4)

    for i, (hx, hy) in enumerate(obs["farms"][obs["player"]]["hands"]):
        if i >= 8 and i not in sw_zone_by_index:
            # Shared animal-care pool -- see docstring for the priority
            # order and why it's not one dedicated hand per animal.
            hand_inventory = obs["private"]["inventories"][i + 1]
            hand_tile = obs["farms"][obs["player"]]["tiles"][hy][hx]
            carrying = "COW" if hand_inventory.get("COW", 0) > 0 else ("SHEEP" if hand_inventory.get("SHEEP", 0) > 0 else None)

            # Nearest placed animal that hasn't eaten today. Unfed is the
            # only state that actually kills one (consecutive_unfed >= 2
            # in the engine), so it outranks fetching another animal --
            # see "Feed before expand" in the docstring.
            hungry_target, hungry_dist = None, None
            if carrying is None:
                for ty, trow in enumerate(obs["farms"][obs["player"]]["tiles"]):
                    for tx, t in enumerate(trow):
                        if not isinstance(t, dict) or "animal" not in t or t.get("fed_today"):
                            continue
                        dist = abs(tx - hx) + abs(ty - hy)
                        if hungry_dist is None or dist < hungry_dist:
                            hungry_dist, hungry_target = dist, (tx, ty)

            # Where this hand is headed whenever nothing actionable
            # applies where it stands. Computed up front because the
            # LOCKED case needs it too: on a LOCKED tile every non-move
            # op is a silent no-op in the engine, so walking is the only
            # way out (see the LOCKED-tile trap in the docstring).
            if carrying is not None:
                roam_target = _nearest_free_tile(obs, obs["player"], ANCHOR)
            elif hungry_target is not None and hand_inventory.get("WHEAT", 0) > 0:
                roam_target = hungry_target
            elif obs["private"]["shed"].get("COW", 0) > 0 or obs["private"]["shed"].get("SHEEP", 0) > 0:
                roam_target = ANCHOR
            else:
                roam_target = _nearest_needs_care_tile(obs, obs["player"], (hx, hy))
            roam_op = ["PASS"] if roam_target is None else _move_toward(hx, hy, roam_target[0], roam_target[1])

            if hand_tile == "LOCKED":
                op = roam_op
            elif hand_tile is None and carrying is not None:
                op = ["BUILD_PASTURE"]
            elif isinstance(hand_tile, dict) and hand_tile.get("kind") == "PASTURE" and "animal" not in hand_tile and carrying is not None:
                op = ["PLACE", carrying, 1]
            elif carrying is not None:
                # Carrying an animal this tile can't take -- keep walking
                # to a free one, never divert into maintenance here (see
                # the carrier deadlock in the docstring).
                op = roam_op
            elif isinstance(hand_tile, dict) and hand_tile.get("kind") == "PASTURE" and "animal" in hand_tile:
                animal = hand_tile["animal"]
                product = "MILK" if animal == "COW" else "WOOL"
                if hand_inventory.get("WHEAT", 0) > 0 and not hand_tile.get("fed_today"):
                    op = ["FEED"]
                elif hand_tile.get("fertilizer_available"):
                    op = ["COLLECT_FERTILIZER"]
                elif not hand_tile.get("cared_today"):
                    op = ["CARE"]
                elif hand_tile.get("yield_units", 0) > 0:
                    op = ["HARVEST"]
                else:
                    # Move on rather than park (Opus diagnosis,
                    # 2026-09-03): with bulk WHEAT above, a pool hand can
                    # carry enough to feed several animals in one trip --
                    # PASS-ing here as soon as *this* tile is done wastes
                    # the rest of that WHEAT instead of carrying it to the
                    # next hungry one.
                    op = roam_op
                    product_in_shed = obs["private"]["shed"].get(product, 0)
                    if product_in_shed > 0:
                        market.append(["SELL", product, product_in_shed])
            elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("WHEAT", 0) == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
                # WHEAT first: FEED needs it in this hand's own
                # inventory, and it's the frequent errand in the replay
                # (see the pickup-priority paragraph in the docstring).
                # Bulk 5, not 1 (Opus diagnosis, 2026-09-03): a real
                # strong replay bulk-picks 4-6 WHEAT per shed trip and
                # tends several animals on the same trip; picking up 1
                # at a time capped this pool at one FEED per trip.
                op = ["PICKUP", "WHEAT", 5]
            elif (
                (hx, hy) in SHED_ADJACENT
                and hungry_target is None
                and (obs["private"]["shed"].get("COW", 0) > 0 or obs["private"]["shed"].get("SHEEP", 0) > 0)
            ):
                # Only expand once nothing is hungry, and only once this
                # hand already holds WHEAT (the check above would have
                # fired otherwise), so it can feed what it places.
                # Take whichever animal has fewer placed, ties to the
                # bigger shed backlog: COW used to starve SHEEP out.
                waiting = [a for a in ("COW", "SHEEP") if obs["private"]["shed"].get(a, 0) > 0]
                pickup = min(waiting, key=lambda a: (placed_counts[a], -obs["private"]["shed"].get(a, 0)))
                op = ["PICKUP", pickup, 1]
            else:
                op = roam_op
            hands.append(op)
            continue

        if i == 4:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **CHAIN_H4_NEXT}
        elif i == 2:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **CHAIN_NW_NEXT}
        elif i in ne_zone_by_index:
            hand_loop = {**LOOP_ORDER_HANDS_NE, **SPAWN_FEEDER_NE, **ne_zone_by_index[i]}
        elif i in sw_zone_by_index:
            hand_loop = {**LOOP_ORDER_HANDS_SW, **SPAWN_FEEDER_SW, **sw_zone_by_index[i]}
        else:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **HAND_ZONES[i % len(HAND_ZONES)]}
        # Unguarded, this used to be a KeyError -> forfeited episode
        # whenever a hand stood somewhere its own merged loop doesn't
        # cover (see the routing-lookup paragraph in the docstring).
        # `_move_toward` also replaces the DIRECTIONS lookup: for the
        # adjacent targets these dicts hold it returns exactly the same
        # op, and it can't raise on a non-adjacent one.
        if (hx, hy) in hand_loop:
            target_x, target_y = hand_loop[(hx, hy)]
        else:
            target_x, target_y = ANCHOR
        move = _move_toward(hx, hy, target_x, target_y)

        hand_tile = obs["farms"][obs["player"]]["tiles"][hy][hx]

        if i == 4:
            op = _chain_hand_op(obs, CHAIN_H4, i, hx, hy, hand_tile, move, placed_counts)
        elif i == 2:
            op = _chain_hand_op(obs, CHAIN_NW, i, hx, hy, hand_tile, move, placed_counts)
        elif i in ne_zone_by_index:
            if i == 6:
                # ZONE_LEFT_NE's tiles doubled as a chain instead of a
                # crop zone (Opus diagnosis, 2026-09-03): the same tile
                # set as CHAIN_NE, chosen because 3 independent strong
                # replays converge on a 14-tile pasture block (CHAIN_NW +
                # CHAIN_H4 + this one) around spawn, none uncultivated.
                # Bypasses the own_zone/LOCKED gate below --
                # _chain_hand_op needs shed access (off-zone) for bulk
                # WHEAT/animal pickups, which the old "off my zone -> just
                # move" shortcut would have blocked entirely.
                op = _chain_hand_op(obs, list(ZONE_LEFT_NE), i, hx, hy, hand_tile, move, placed_counts)
            elif hand_tile == "LOCKED" or (hx, hy) not in ne_zone_by_index[i]:
                op = move
            elif i in (5, 7):
                # ZONE_TOP_NE (5) + ZONE_RIGHT_NE (7) all-STRAWBERRY
                # instead of crop_to_plant. RIGHT was already converted
                # (Opus diagnosis, 2026-09-03: +4,470 on its own).
                # EXPERIMENT, 2026-09-03 (re-test): TOP measured negative
                # for STRAWBERRY under the pre-chain-hand economy -- the
                # same "no longer holds" caveat as SW's reversal above.
                # ZONE_LEFT_NE (hand 6) is NOT converted: it's CHAIN_NE,
                # a pasture chain now, not a crop zone.
                op = _tile_action(hand_tile, move, strawberry_seed_budget, "STRAWBERRY", obs)
            else:
                op = _tile_action(hand_tile, move, crop_seed_budget, crop_to_plant, obs)

        elif i in sw_zone_by_index:
            # EXPERIMENT, 2026-09-03: all-STRAWBERRY, same rationale as
            # ZONE_RIGHT_NE above -- see the SW zone constants paragraph.
            if hand_tile == "LOCKED" or (hx, hy) not in sw_zone_by_index[i]:
                op = move
            else:
                op = _tile_action(hand_tile, move, strawberry_seed_budget, "STRAWBERRY", obs)

        elif hand_tile == "LOCKED" or (hx, hy) not in HAND_ZONES[i % len(HAND_ZONES)]:
            op = move
        else:
            if (hx, hy) == STRAWBERRY_TILE:
                op = _tile_action(hand_tile, move, strawberry_seed_budget, "STRAWBERRY", obs)
            else:
                op = _tile_action(hand_tile, move, crop_seed_budget, crop_to_plant, obs)
        hands.append(op)

    # Batch the hires: the engine dispatches every order in one turn's
    # market list, so several HIREs in the same list all land, at the
    # same cumulative Fibonacci cost as spreading them over the day.
    # Capped at 4 per turn to leave room inside maxMarketOrdersPerTurn
    # (10) for the SELL orders -- see the hire-ramp paragraph.
    # Capped at 10 (not the reference replay's 12-13): a 3rd hand added
    # to the animal-care pool measured net negative independent of land,
    # because near-shed pasture tiles -- not hand count -- are what caps
    # the pool (Opus diagnosis, 2026-09-03; see the strawberry-acreage
    # paragraph above).
    # 9, not 10 (Opus diagnosis, 2026-09-03): ten hands were sized for a
    # 2-hand roaming pool; with hands 2/4/6 doing chain-based animal care
    # instead, the 10th hand's daily Fibonacci hire fee outweighs it.
    # Measured: hire_cap 8 loses badly (-46,340) by starving the pool's
    # remaining WOOL/MILK sales -- don't go below 9.
    # EXPERIMENT, 2026-09-03: 12 once SW is unlocked (3 more hands for
    # the new STRAWBERRY zones above), matching what all 3 real strong
    # replays actually run once they own SW.
    hire_cap = 12 if sw_unlocked else (9 if obs["day"] >= 6 else 5)
    hire_shortfall = hire_cap - len(obs["farms"][obs["player"]]["hands"])
    for _ in range(max(0, min(hire_shortfall, 4))):
        market.append(["HIRE"])

    if obs["step"] == 0 or wheat_seeds <= 5:
        market.append(["BUY_SEED", "WHEAT", 6 - wheat_seeds])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    if (x, y) in LOOP_ORDER_12:
        target_x, target_y = LOOP_ORDER_12[(x, y)]
    else:
        target_x, target_y = ANCHOR
    direction = _move_toward(x, y, target_x, target_y)[0]

    tile = obs["farms"][obs["player"]]["tiles"][y][x]
    farmer_inventory = obs["private"]["inventories"][0]

    wheat_in_shed = obs["private"]["shed"].get("WHEAT", 0)
    melon_in_shed = obs["private"]["shed"].get("MELON", 0)
    fertilizer_in_shed = obs["private"]["shed"].get("FERTILIZER", 0)
    milk_in_shed = obs["private"]["shed"].get("MILK", 0)
    strawberry_in_shed = obs["private"]["shed"].get("STRAWBERRY", 0)
    carrot_in_shed = obs["private"]["shed"].get("CARROT", 0)
    # Scales with herd size, not a flat 1 (Opus diagnosis, 2026-09-03):
    # selling down to 1 starved the chain hands' bulk pickups the moment
    # there was more than one animal to feed. A flat reserve was tried at
    # several multiples without a herd behind it and measured negative
    # every time (see the docstring) -- it only pays once chain hands
    # exist to spend it.
    wheat_reserve = 1 + 3 * (placed_counts["COW"] + placed_counts["SHEEP"])
    if wheat_in_shed > wheat_reserve:
        market.append(["SELL", "WHEAT", wheat_in_shed - wheat_reserve])
    if melon_in_shed > 0:
        market.append(["SELL", "MELON", melon_in_shed])
    if fertilizer_in_shed > 1:
        market.append(["SELL", "FERTILIZER", fertilizer_in_shed - 1])
    if milk_in_shed > 0:
        market.append(["SELL", "MILK", milk_in_shed])
    wool_in_shed = obs["private"]["shed"].get("WOOL", 0)
    if wool_in_shed > 0:
        # Explicit and unconditional (Opus diagnosis, 2026-09-03): the
        # only unconditional WOOL seller used to live in hand 4's bespoke
        # idle branch, deleted along with it when hand 4 became a chain
        # hand. Measured close to outcome-neutral on its own (+500, 5/8)
        # but removes a real fragility: without it, WOOL sales depend on
        # a pool hand happening to idle on a serviced pasture, which is
        # exactly the dependency that made hire_cap=8 collapse.
        market.append(["SELL", "WOOL", wool_in_shed])
    if strawberry_in_shed > 0:
            market.append(["SELL", "STRAWBERRY", strawberry_in_shed])
    if carrot_in_shed > 0:
        market.append(["SELL", "CARROT", carrot_in_shed])

    inventory_has_other_items = any(k != "FERTILIZER" and v > 0 for k, v in farmer_inventory.items())
    if (x, y) in SHED_ADJACENT and inventory_has_other_items:
        farmer = ["DROP"]
    elif (x, y) in SHED_ADJACENT and farmer_inventory.get("FERTILIZER", 0) == 0 and fertilizer_in_shed > 0:
        farmer = ["PICKUP", "FERTILIZER", 1]
    elif (
        isinstance(tile, dict)
        and tile.get("kind") == "PLANT"
        and farmer_inventory.get("FERTILIZER", 0) > 0
        and tile.get("fertilized_until_day", -1) < obs["day"]
    ):
        farmer = ["FERTILIZE"]
    else:
        farmer = _tile_action(tile, [direction], crop_seed_budget, crop_to_plant, obs)

    # SELLs go to the front of the turn's market list. The engine walks
    # both players' queues in lockstep by order *index*, quoting each
    # unit against the market inventory as it stands at that index, so
    # an order's position decides the price it gets -- see the
    # sell-before-buy paragraph in the docstring. Stable sort: the
    # relative order inside each group is untouched.
    market.sort(key=lambda order: 0 if order[0] == "SELL" else 1)
    return {"farmer": farmer, "hands": hands, "market": market}
