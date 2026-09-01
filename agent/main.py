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
    {(2, 0): (3, 0), (3, 0): (3, 1), (3, 1): (2, 1), (2, 1): (2, 0)},  # hand 1: 2x2 block
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
GOOSE_TILE = (4, 2)
SHED_ADJACENT = {(4, 4), (5, 4), (4, 5), (5, 5)}
GOOSE_FEEDER = {(4, 4): (4, 3), (4, 3): (4, 2), (4, 2): (4, 2)}
PASTURE_TILE = (4, 1)
PASTURE_FEEDER = {(4, 4): (4, 3), (4, 3): (4, 2), (4, 2): (4, 1), (4, 1): (4, 1)}

CROP_INFO = {
    "WHEAT": {"ongoing": False, "max_yield_day": 4, "max_yield": 6},
    "MELON": {"ongoing": False, "max_yield_day": 12, "max_yield": 6},
    "STRAWBERRY": {"ongoing": True},
    "CARROT": {"ongoing": False, "max_yield_day": 3, "max_yield": 4},
}
STRAWBERRY_TILE = (0,1)

def _tile_action(tile, fallback, crop_seeds, crop_to_plant, obs):
    # DIG reclaims a WEED tile back to empty (roadmap step 5) -- cheap,
    # isolated: any tile-tending caller (farmer, wheat/melon/strawberry
    # hands, NE hands) benefits without extra wiring.
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        return ["DIG"]

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
            if crop_age >= max_yield_day or tile.get("yield_units",0) >= max_yield:
                action = ["HARVEST"]
            elif not tile.get("watered_today"):
                action = ["WATER"]
            else: 
                action = fallback
    else:
        action = fallback
    return action

def _nearest_free_tile(obs, player, from_pos):
    """Brute-force nearest free (`None`, not `"LOCKED"`) tile to
    `from_pos`, by Manhattan distance -- no pathfinding needed here (chat
    decision): this grid has no obstacles blocking movement within an
    unlocked quadrant, so straight-line distance already matches real
    walking distance. Returns the `(x, y)` of the nearest free tile, or
    `None` if there isn't one.

    TODO: iterate obs["farms"][player]["tiles"] (a 2D list indexed
    tiles[y][x]), skip "LOCKED" and any non-None tile, track the minimum
    Manhattan distance to from_pos among what's left.
    """
    # TODO
    tiles = obs["farms"][player]["tiles"]
    best_dist, best_pos = None, None
    
    for y, row in enumerate(tiles): 
        for x, tile in enumerate(row):
            if tile is not None:
                continue
            else:
                
                dist = abs(x - from_pos[0]) + abs(y - from_pos[1])
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

    **Still open**: only 4 animals stay alive against the replay's 13 --
    two pool hands cap the sustainable herd. `SW` land (the replay buys
    it too) and more/better-allocated care hands are the next levers.
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
    strawberry_seeds = obs["private"]["seeds"].get("STRAWBERRY", 0)

    market = []
    hands = []

    if obs["step"] == 0:
        market.append(["BUY_ANIMAL", "COW", 2])
        market.append(["BUY_ANIMAL", "SHEEP", 2])
        market.append(["BUY_SEED", "MELON", 12])
    if obs["day"] == 4 and strawberry_seeds == 0:
        market.append(["BUY_SEED", "STRAWBERRY", 1])
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

    if obs["private"]["shed"].get("WHEAT", 0) == 0:
        market.append(["BUY_PRODUCT", "WHEAT", 1])
    if obs["day"] >= 6 and len(obs["farms"][obs["player"]]["unlocked_quadrants"]) == 1:
        market.append(["BUY_LAND"])

    ne_zone_by_index = {5: ZONE_TOP_NE, 6: ZONE_LEFT_NE, 7: ZONE_RIGHT_NE}
    ANCHOR = (4, 4)

    goose_tile_now = obs["farms"][obs["player"]]["tiles"][GOOSE_TILE[1]][GOOSE_TILE[0]]
    sheep_already_placed = isinstance(goose_tile_now, dict) and goose_tile_now.get("animal") == "SHEEP"
    pasture_tile_now = obs["farms"][obs["player"]]["tiles"][PASTURE_TILE[1]][PASTURE_TILE[0]]
    cow_already_placed = isinstance(pasture_tile_now, dict) and pasture_tile_now.get("animal") == "COW"

    for i, (hx, hy) in enumerate(obs["farms"][obs["player"]]["hands"]):
        if i >= 8:
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
                    op = ["PASS"]
                    product_in_shed = obs["private"]["shed"].get(product, 0)
                    if product_in_shed > 0:
                        market.append(["SELL", product, product_in_shed])
            elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("WHEAT", 0) == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
                # WHEAT first: FEED needs it in this hand's own
                # inventory, and it's the frequent errand in the replay
                # (see the pickup-priority paragraph in the docstring).
                op = ["PICKUP", "WHEAT", 1]
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
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **GOOSE_FEEDER}
        elif i == 2:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **PASTURE_FEEDER}
        elif i in ne_zone_by_index:
            hand_loop = {**LOOP_ORDER_HANDS_NE, **SPAWN_FEEDER_NE, **ne_zone_by_index[i]}
        else:
            hand_loop = {**LOOP_ORDER_HANDS, **SPAWN_FEEDER, **HAND_ZONES[i % len(HAND_ZONES)]}
        target_x, target_y = hand_loop[(hx, hy)]
        if (target_x, target_y) == (hx, hy):
            move = ["PASS"]
        else:
            move = [DIRECTIONS[(target_x - hx, target_y - hy)]]

        hand_tile = obs["farms"][obs["player"]]["tiles"][hy][hx]

        if i == 4:
            # SHEEP, on the tile/route the goose used to use.
            hand_inventory = obs["private"]["inventories"][i + 1]

            if (hx, hy) == GOOSE_TILE:
                if hand_tile is None:
                    op = ["BUILD_PASTURE"]
                elif hand_tile.get("kind") == "PASTURE" and hand_tile.get("animal") != "SHEEP":
                    if hand_inventory.get("SHEEP", 0) > 0:
                        op = ["PLACE", "SHEEP", 1]
                    else:
                        op = ["PASS"]
                elif hand_inventory.get("WHEAT", 0) > 0 and not hand_tile.get("fed_today"):
                    op = ["FEED"]
                elif hand_inventory.get("WHEAT", 0) == 0 and not hand_tile.get("fed_today"):
                    # Out of WHEAT, animal still needs feeding -- go
                    # restock (see docstring).
                    op = _move_toward(hx, hy, ANCHOR[0], ANCHOR[1])
                elif hand_tile.get("fertilizer_available"):
                    op = ["COLLECT_FERTILIZER"]
                elif not hand_tile.get("cared_today"):
                    op = ["CARE"]
                elif hand_tile.get("yield_units", 0) > 0:
                    op = ["HARVEST"]
                else:
                    op = ["PASS"]
                    wool_in_shed = obs["private"]["shed"].get("WOOL", 0)
                    if wool_in_shed > 0:
                        market.append(["SELL", "WOOL", wool_in_shed])
            else:
                if hand_tile == "LOCKED":
                    op = move
                elif not sheep_already_placed and (hx, hy) in SHED_ADJACENT and hand_inventory.get("SHEEP", 0) == 0 and obs["private"]["shed"].get("SHEEP", 0) > 0:
                    op = ["PICKUP", "SHEEP", 1]
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("WHEAT", 0) == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
                    op = ["PICKUP", "WHEAT", 1]
                elif sheep_already_placed and hand_inventory.get("WHEAT", 0) == 0 and (hx, hy) != ANCHOR:
                    # Mid-restock-trip: GOOSE_FEEDER only maps forward
                    # (toward the coop), so just following `move` here
                    # would bounce the hand straight back without ever
                    # reaching the shed.
                    op = _move_toward(hx, hy, ANCHOR[0], ANCHOR[1])
                else:
                    op = move
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
                elif hand_inventory.get("WHEAT", 0) == 0 and not hand_tile.get("fed_today"):
                    op = _move_toward(hx, hy, ANCHOR[0], ANCHOR[1])
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
                elif not cow_already_placed and (hx, hy) in SHED_ADJACENT and hand_inventory.get("COW", 0) == 0 and obs["private"]["shed"].get("COW", 0) > 0:
                    op = ["PICKUP", "COW", 1]
                elif (hx, hy) in SHED_ADJACENT and hand_inventory.get("WHEAT", 0) == 0 and obs["private"]["shed"].get("WHEAT", 0) > 0:
                    op = ["PICKUP", "WHEAT", 1]
                elif cow_already_placed and hand_inventory.get("WHEAT", 0) == 0 and (hx, hy) != ANCHOR:
                    op = _move_toward(hx, hy, ANCHOR[0], ANCHOR[1])
                else:
                    op = move
        elif i in ne_zone_by_index:
            own_zone = ne_zone_by_index[i]
            if hand_tile == "LOCKED" or (hx, hy) not in own_zone:
                op = move
            else:
                op = _tile_action(hand_tile, move, crop_seeds, crop_to_plant, obs)

        elif hand_tile == "LOCKED" or (hx, hy) not in HAND_ZONES[i % len(HAND_ZONES)]:
            op = move
        else:
            if (hx, hy) == STRAWBERRY_TILE:
                op = _tile_action(hand_tile, move, strawberry_seeds,"STRAWBERRY", obs)
            else:
                op = _tile_action(hand_tile, move, crop_seeds, crop_to_plant, obs)
        hands.append(op)

    if len(obs["farms"][obs["player"]]["hands"]) < 5:
        market.append(["HIRE"])

    elif len(obs["farms"][obs["player"]]["hands"]) < 8 and obs["day"] >= 6:
        market.append(["HIRE"])

    elif len(obs["farms"][obs["player"]]["hands"]) < 10 and obs["day"] >= 6:
        market.append(["HIRE"])

    if obs["step"] == 0 or wheat_seeds <= 5:
        market.append(["BUY_SEED", "WHEAT", 6 - wheat_seeds])

    farmer_pos = obs["farms"][obs["player"]]["farmer"]
    x, y = farmer_pos
    target_x, target_y = LOOP_ORDER_12[(x, y)]
    direction = DIRECTIONS[(target_x - x, target_y - y)]

    tile = obs["farms"][obs["player"]]["tiles"][y][x]
    farmer_inventory = obs["private"]["inventories"][0]

    wheat_in_shed = obs["private"]["shed"].get("WHEAT", 0)
    melon_in_shed = obs["private"]["shed"].get("MELON", 0)
    fertilizer_in_shed = obs["private"]["shed"].get("FERTILIZER", 0)
    milk_in_shed = obs["private"]["shed"].get("MILK", 0)
    strawberry_in_shed = obs["private"]["shed"].get("STRAWBERRY", 0)
    carrot_in_shed = obs["private"]["shed"].get("CARROT", 0)
    if wheat_in_shed > 1:
        market.append(["SELL", "WHEAT", wheat_in_shed - 1])
    if melon_in_shed > 0:
        market.append(["SELL", "MELON", melon_in_shed])
    if fertilizer_in_shed > 1:
        market.append(["SELL", "FERTILIZER", fertilizer_in_shed - 1])
    if milk_in_shed > 0:
        market.append(["SELL", "MILK", milk_in_shed])
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
        farmer = _tile_action(tile, [direction], crop_seeds, crop_to_plant, obs)

    return {"farmer": farmer, "hands": hands, "market": market}
