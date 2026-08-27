"""Unit tests for kaggriculture_bot.strategies.baseline's wheat_loop_agent
and wheat_loop_2x2_agent — plumbing (which action each picks for a given
obs), not agent quality; that's what evaluate.py's harness is for.
"""

from kaggriculture_bot.strategies.baseline import (
    DIRECTIONS,
    LOOP_ORDER_2X2,
    LOOP_ORDER_12,
    LOOP_ORDER_HANDS,
    SPAWN_FEEDER,
    HAND_ZONES,
    wheat_loop_agent,
    wheat_loop_2x2_agent,
    wheat_loop_12_agent,
    wheat_loop_hands_agent,
    wheat_loop_melon_agent,
    MELON_HAND_ZONES,
    melon_rush_agent,
    melon_then_wheat_agent,
    LOOP_ORDER_HANDS_NE,
    SPAWN_FEEDER_NE,
    ZONE_TOP_NE,
    ZONE_LEFT_NE,
    ZONE_RIGHT_NE,
    melon_then_wheat_extra_hands_agent,
    GOOSE_TILE,
    GOOSE_FEEDER,
    melon_then_wheat_goose_agent,
)


def make_obs(*, step=5, day=0, seeds=0, shed=0, tile=None):
    """Build a minimal 1x1-farm obs with the farmer standing on `tile`."""
    return {
        "player": 0,
        "step": step,
        "day": day,
        "farms": [{"farmer": [0, 0], "tiles": [[tile]]}],
        "private": {"seeds": {"WHEAT": seeds}, "shed": {"WHEAT": shed}},
    }


def test_buys_seed_on_step_zero_even_with_stock():
    obs = make_obs(step=0, seeds=3)
    action = wheat_loop_agent(obs)
    assert ["BUY_SEED", "WHEAT", 1] in action["market"]


def test_buys_seed_when_out_of_stock_mid_game():
    obs = make_obs(step=100, seeds=0)
    action = wheat_loop_agent(obs)
    assert ["BUY_SEED", "WHEAT", 1] in action["market"]


def test_does_not_buy_seed_when_stocked_past_step_zero():
    obs = make_obs(step=100, seeds=2)
    action = wheat_loop_agent(obs)
    assert ["BUY_SEED", "WHEAT", 1] not in action["market"]


def test_plants_on_empty_tile_with_seed_in_hand():
    obs = make_obs(step=5, seeds=1, tile=None)
    action = wheat_loop_agent(obs)
    assert action["farmer"] == ["PLANT", "WHEAT"]


def test_does_not_plant_on_empty_tile_without_seed():
    obs = make_obs(step=5, seeds=0, tile=None)
    action = wheat_loop_agent(obs)
    assert action["farmer"] == ["PASS"]


def test_harvests_before_watering_when_both_are_possible():
    # AGENTS.md's own priority: harvest as soon as the crop is ready, even
    # if it also hasn't been watered today.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": False}
    obs = make_obs(day=2, tile=tile)
    action = wheat_loop_agent(obs)
    assert action["farmer"] == ["HARVEST"]


def test_waters_when_not_yet_ready_to_harvest_and_unwatered():
    tile = {"kind": "PLANT", "planted_day": 1, "watered_today": False}
    obs = make_obs(day=2, tile=tile)
    action = wheat_loop_agent(obs)
    assert action["farmer"] == ["WATER"]


def test_passes_when_already_watered_and_not_ready_to_harvest():
    tile = {"kind": "PLANT", "planted_day": 1, "watered_today": True}
    obs = make_obs(day=2, tile=tile)
    action = wheat_loop_agent(obs)
    assert action["farmer"] == ["PASS"]


def test_sells_one_unit_regardless_of_shed_size():
    # Validated choice (PROGRESS.md, 2026-08-10): sell 1/turn, not the
    # whole shed at once.
    obs = make_obs(shed=5)
    action = wheat_loop_agent(obs)
    assert ["SELL", "WHEAT", 1] in action["market"]
    assert ["SELL", "WHEAT", 5] not in action["market"]


def test_does_not_sell_when_shed_is_empty():
    obs = make_obs(shed=0)
    action = wheat_loop_agent(obs)
    assert not any(order[0] == "SELL" for order in action["market"])


def make_loop_obs(*, step=5, day=0, seeds=0, shed=0, farmer=(4, 4), tiles=None):
    """Build a 5x5-tile obs covering the 2x2 loop corner, farmer at `farmer`."""
    board = [[None] * 5 for _ in range(5)]
    for (x, y), tile in (tiles or {}).items():
        board[y][x] = tile
    return {
        "player": 0,
        "step": step,
        "day": day,
        "farms": [{"farmer": list(farmer), "tiles": board}],
        "private": {"seeds": {"WHEAT": seeds}, "shed": {"WHEAT": shed}},
    }


def assert_is_closed_adjacent_cycle(loop_order):
    """Every tile's target is orthogonally adjacent, and following targets
    from any starting tile visits each tile exactly once before closing
    back on the start."""
    n = len(loop_order)
    start = next(iter(loop_order))
    pos = start
    visited = set()
    for _ in range(n):
        visited.add(pos)
        (x, y), (nx, ny) = pos, loop_order[pos]
        assert abs(nx - x) + abs(ny - y) == 1  # orthogonally adjacent
        pos = (nx, ny)
    assert pos == start  # closes the loop after exactly n steps
    assert visited == set(loop_order)  # no tile repeated or skipped


def test_loop_order_2x2_is_a_single_closed_cycle_of_adjacent_tiles():
    assert len(LOOP_ORDER_2X2) == 4
    assert_is_closed_adjacent_cycle(LOOP_ORDER_2X2)


def test_loop_order_12_is_a_single_closed_cycle_of_adjacent_tiles():
    assert len(LOOP_ORDER_12) == 12
    assert_is_closed_adjacent_cycle(LOOP_ORDER_12)


def test_every_loop_transition_has_a_direction():
    for loop_order in (LOOP_ORDER_2X2, LOOP_ORDER_12):
        for (x, y), (nx, ny) in loop_order.items():
            assert (nx - x, ny - y) in DIRECTIONS


def test_2x2_plants_on_empty_tile_with_seed_in_hand():
    obs = make_loop_obs(seeds=1, farmer=(4, 4), tiles={(4, 4): None})
    action = wheat_loop_2x2_agent(obs)
    assert action["farmer"] == ["PLANT", "WHEAT"]


def test_2x2_harvests_before_watering_when_both_are_possible():
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": False}
    obs = make_loop_obs(day=2, farmer=(4, 3), tiles={(4, 3): tile})
    action = wheat_loop_2x2_agent(obs)
    assert action["farmer"] == ["HARVEST"]


def test_2x2_waters_when_not_yet_ready_to_harvest_and_unwatered():
    tile = {"kind": "PLANT", "planted_day": 1, "watered_today": False}
    obs = make_loop_obs(day=2, farmer=(3, 3), tiles={(3, 3): tile})
    action = wheat_loop_2x2_agent(obs)
    assert action["farmer"] == ["WATER"]


def test_2x2_moves_toward_next_loop_tile_when_current_tile_already_watered():
    # (4,4) -> (4,3) is a NORTH move (see notebooks/05_farmer_movement.ipynb
    # direction check: NORTH decrements y).
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_loop_obs(day=0, farmer=(4, 4), tiles={(4, 4): tile})
    action = wheat_loop_2x2_agent(obs)
    assert action["farmer"] == ["NORTH"]


def test_2x2_moves_toward_next_loop_tile_when_empty_and_out_of_seed():
    # Regression check for the bug logged in PROGRESS.md: a tile with a
    # live crop must not fall through to PASS once watered -- it has to
    # advance to the next tile in LOOP_ORDER_2X2 like the empty-tile case.
    obs = make_loop_obs(seeds=0, farmer=(3, 4), tiles={(3, 4): None})
    action = wheat_loop_2x2_agent(obs)
    assert action["farmer"] == ["EAST"]


def test_2x2_sells_one_unit_regardless_of_shed_size():
    obs = make_loop_obs(shed=5, farmer=(4, 4), tiles={(4, 4): None})
    action = wheat_loop_2x2_agent(obs)
    assert ["SELL", "WHEAT", 1] in action["market"]
    assert ["SELL", "WHEAT", 5] not in action["market"]


def test_12_plants_on_empty_tile_with_seed_in_hand():
    obs = make_loop_obs(seeds=1, farmer=(1, 3), tiles={(1, 3): None})
    action = wheat_loop_12_agent(obs)
    assert action["farmer"] == ["PLANT", "WHEAT"]


def test_12_harvests_before_watering_when_both_are_possible():
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": False}
    obs = make_loop_obs(day=2, farmer=(0, 4), tiles={(0, 4): tile})
    action = wheat_loop_12_agent(obs)
    assert action["farmer"] == ["HARVEST"]


def test_12_moves_along_the_straight_stretch_when_already_watered():
    # (1,4) -> (0,4) is WEST -- part of the plain bottom-row stretch.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_loop_obs(day=0, farmer=(1, 4), tiles={(1, 4): tile})
    action = wheat_loop_12_agent(obs)
    assert action["farmer"] == ["WEST"]


def test_12_moves_into_the_detour_when_already_watered():
    # (2,3) -> (2,2) is NORTH -- the start of the 2-tile detour into y=2
    # that takes the loop from 10 to 12 tiles.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_loop_obs(day=0, farmer=(2, 3), tiles={(2, 3): tile})
    action = wheat_loop_12_agent(obs)
    assert action["farmer"] == ["NORTH"]


def test_12_moves_out_of_the_detour_when_empty_and_out_of_seed():
    # (3,2) -> (3,3) is SOUTH -- leaving the detour and rejoining y=3.
    # Regression check for the PASS-trap bug logged in PROGRESS.md
    # (2026-08-19): "nothing to do here" must move, never PASS.
    obs = make_loop_obs(seeds=0, farmer=(3, 2), tiles={(3, 2): None})
    action = wheat_loop_12_agent(obs)
    assert action["farmer"] == ["SOUTH"]


def test_12_sells_one_unit_regardless_of_shed_size():
    obs = make_loop_obs(shed=5, farmer=(4, 4), tiles={(4, 4): None})
    action = wheat_loop_12_agent(obs)
    assert ["SELL", "WHEAT", 1] in action["market"]
    assert ["SELL", "WHEAT", 5] not in action["market"]


def test_loop_order_hands_is_a_single_closed_cycle_of_adjacent_tiles():
    assert len(LOOP_ORDER_HANDS) == 16
    assert_is_closed_adjacent_cycle(LOOP_ORDER_HANDS)


def test_spawn_feeder_routes_each_locked_corner_one_step_toward_the_loop():
    # Every SPAWN_FEEDER entry must be orthogonally adjacent to its target,
    # and eventually reach LOOP_ORDER_HANDS's entry point (4,4).
    for pos, nxt in SPAWN_FEEDER.items():
        assert abs(nxt[0] - pos[0]) + abs(nxt[1] - pos[1]) == 1
        assert nxt == (4, 4) or nxt in SPAWN_FEEDER


def make_hands_obs(
    *,
    step=5,
    day=0,
    seeds=0,
    shed=0,
    melon_seeds=0,
    melon_shed=0,
    farmer=(4, 4),
    hands=(),
    tiles=None,
    money=3000,
    unlocked_quadrants=("NW",),
):
    """Build a 6x6-tile obs (covers LOOP_ORDER_HANDS + the SE spawn corner)
    with a farmer and a list of hands at given positions."""
    board = [[None] * 6 for _ in range(6)]
    for (x, y), tile in (tiles or {}).items():
        board[y][x] = tile
    return {
        "player": 0,
        "step": step,
        "day": day,
        "farms": [
            {
                "farmer": list(farmer),
                "hands": [list(h) for h in hands],
                "tiles": board,
                "money": money,
                "unlocked_quadrants": list(unlocked_quadrants),
            }
        ],
        "private": {
            "seeds": {"WHEAT": seeds, "MELON": melon_seeds},
            "shed": {"WHEAT": shed, "MELON": melon_shed},
        },
    }


def test_hands_hires_while_under_five():
    obs = make_hands_obs(hands=[(4, 4), (3, 4)])
    action = wheat_loop_hands_agent(obs)
    assert ["HIRE"] in action["market"]


def test_hands_does_not_hire_at_five():
    obs = make_hands_obs(hands=[(4, 4), (3, 4), (3, 3), (3, 2), (3, 1)])
    action = wheat_loop_hands_agent(obs)
    assert ["HIRE"] not in action["market"]


def test_hands_buys_seed_in_batch_up_to_six():
    obs = make_hands_obs(seeds=2)
    action = wheat_loop_hands_agent(obs)
    assert ["BUY_SEED", "WHEAT", 4] in action["market"]


def test_hands_does_not_buy_seed_when_stocked_past_six():
    obs = make_hands_obs(step=100, seeds=6)
    action = wheat_loop_hands_agent(obs)
    assert not any(order[0] == "BUY_SEED" for order in action["market"])


def test_hand_on_locked_spawn_corner_moves_via_spawn_feeder_instead_of_crashing():
    # (5,5) is "LOCKED" (unbought quadrant) -- SPAWN_FEEDER routes it toward
    # (5,4), a NORTH move. Regression check for the AttributeError bug
    # logged in notebooks/07_farm_hands.ipynb: "LOCKED" is a string, not a
    # tile dict, and must be guarded before .get("kind") is called.
    obs = make_hands_obs(hands=[(5, 5)], tiles={(5, 5): "LOCKED"})
    action = wheat_loop_hands_agent(obs)
    assert action["hands"] == [["NORTH"]]


def test_hand_plants_on_empty_tile_with_seed_in_hand():
    obs = make_hands_obs(seeds=1, hands=[(3, 1)], tiles={(3, 1): None})
    action = wheat_loop_hands_agent(obs)
    assert action["hands"] == [["PLANT", "WHEAT"]]


def test_hand_harvests_before_watering_when_both_are_possible():
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": False}
    obs = make_hands_obs(day=2, hands=[(1, 1)], tiles={(1, 1): tile})
    action = wheat_loop_hands_agent(obs)
    assert action["hands"] == [["HARVEST"]]


def test_hand_moves_toward_next_loop_tile_when_already_watered():
    # (3,4) -> (3,3) is NORTH, per LOOP_ORDER_HANDS (NORTH decrements y).
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_hands_obs(day=0, hands=[(3, 4)], tiles={(3, 4): tile})
    action = wheat_loop_hands_agent(obs)
    assert action["hands"] == [["NORTH"]]


def test_hand_zones_are_pairwise_disjoint_and_valid_cycles():
    steady_state = [
        {(0, 0), (1, 0), (1, 1), (0, 1)},
        {(2, 0), (3, 0), (3, 1), (2, 1)},
        {(4, 0), (4, 1)},
        {(0, 2), (1, 2)},
        {(4, 2)},
    ]
    for i, a in enumerate(steady_state):
        for j, b in enumerate(steady_state):
            if i < j:
                assert not (a & b)
    for zone, tiles in zip(HAND_ZONES, steady_state):
        home_only = {k: v for k, v in zone.items() if k in tiles}
        if len(home_only) == 1:
            ((tile, target),) = home_only.items()
            assert tile == target
        else:
            assert_is_closed_adjacent_cycle(home_only)


def test_two_hands_on_the_same_tile_diverge_by_index_instead_of_merging_forever():
    # Regression check for the permanent-merge bug logged in PROGRESS.md
    # (2026-08-21): before HAND_ZONES, every hand computed the same action
    # from the same tile, so a collision became permanent. Hand 0 and hand
    # 1 both standing on (2,1) must now move in different directions.
    obs = make_hands_obs(day=0, hands=[(2, 1), (2, 1)], tiles={(2, 1): None})
    action = wheat_loop_hands_agent(obs)
    assert action["hands"][0] != action["hands"][1]


def test_hand_four_passes_instead_of_moving_once_its_single_tile_is_tended():
    # Hand index 4's zone is a single self-looping tile -- once tended and
    # watered, there's nowhere to move to, so it must PASS, not crash on a
    # zero-length DIRECTIONS lookup.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_hands_obs(
        day=0,
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (4, 2)],
        tiles={(4, 2): tile},
    )
    action = wheat_loop_hands_agent(obs)
    assert action["hands"][4] == ["PASS"]


def test_hands_farmer_still_follows_loop_order_12():
    # Farmer logic is unchanged from wheat_loop_12_agent -- same tile,
    # same next move.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_hands_obs(day=0, farmer=(1, 4), tiles={(1, 4): tile})
    action = wheat_loop_hands_agent(obs)
    assert action["farmer"] == ["WEST"]


# -- wheat_loop_melon_agent ---------------------------------------------
#
# Regression check for the interference bug logged in PROGRESS.md
# (2026-08-22, notebooks/08_melon_hand.ipynb): the engine applies each
# turn's PLANT actions in unit order (farmer, then hands by index) and
# silently drops any PLANT that lands on a tile another unit already
# claimed that same turn (kaggriculture.py's _apply_unit_action). Since
# hand 4 (melon) is always last, it lost every such race while hands
# opportunistically tended any empty tile they passed through on shared
# LOOP_ORDER_HANDS transit -- so melon seed stock never dropped, ever.
# Fix: a hand only tends (PLANT/WATER/HARVEST) a tile that's a key in its
# *own* HAND_ZONES entry; elsewhere it just moves through.


def test_melon_hand_buys_melon_seed_when_below_buffer():
    obs = make_hands_obs(melon_seeds=1)
    action = wheat_loop_melon_agent(obs)
    assert ["BUY_SEED", "MELON", 1] in action["market"]


def test_melon_hand_does_not_buy_melon_seed_when_stocked():
    obs = make_hands_obs(step=100, melon_seeds=2)
    action = wheat_loop_melon_agent(obs)
    assert not any(
        order[:2] == ["BUY_SEED", "MELON"] for order in action["market"]
    )


def test_melon_hand_plants_melon_on_its_own_empty_tile():
    obs = make_hands_obs(
        melon_seeds=1,
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (4, 2)],
        tiles={(4, 2): None},
    )
    action = wheat_loop_melon_agent(obs)
    assert action["hands"][4] == ["PLANT", "MELON"]


def test_melon_hand_does_not_harvest_at_the_wheat_threshold_age():
    # crop_age=2 would harvest a WHEAT tile, but hand 4's threshold is 10.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_hands_obs(
        day=2,
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (4, 2)],
        tiles={(4, 2): tile},
    )
    action = wheat_loop_melon_agent(obs)
    # Already watered and not ready to harvest -> move on to the zone's
    # next tile, (4,3) (SOUTH), per MELON_HAND_ZONES's 2x2 block.
    assert action["hands"][4] == ["SOUTH"]


def test_melon_hand_harvests_at_its_own_threshold_age():
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": False}
    obs = make_hands_obs(
        day=10,
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (4, 2)],
        tiles={(4, 2): tile},
    )
    action = wheat_loop_melon_agent(obs)
    assert action["hands"][4] == ["HARVEST"]


def test_melon_hand_sells_melon_when_in_shed():
    obs = make_hands_obs(melon_shed=3)
    action = wheat_loop_melon_agent(obs)
    assert ["SELL", "MELON", 1] in action["market"]


def test_other_hands_still_plant_wheat_on_their_own_zone_tile():
    obs = make_hands_obs(
        seeds=1,
        hands=[(0, 0), (3, 4), (3, 3), (3, 2), (5, 4)],
        tiles={(0, 0): None},
    )
    action = wheat_loop_melon_agent(obs)
    assert action["hands"][0] == ["PLANT", "WHEAT"]


def test_hand_does_not_tend_a_shared_transit_tile_outside_its_own_zone():
    # (3,4) is a shared LOOP_ORDER_HANDS node but not in HAND_ZONES[0] --
    # hand 0 must move through it (NORTH, per LOOP_ORDER_HANDS), never
    # plant there, even though the tile is empty and seed is in stock.
    obs = make_hands_obs(
        seeds=1,
        hands=[(3, 4), (4, 4), (3, 3), (3, 2), (3, 1)],
        tiles={(3, 4): None},
    )
    action = wheat_loop_melon_agent(obs)
    assert action["hands"][0] == ["NORTH"]


def test_melon_hand_does_not_tend_a_shared_transit_tile_either():
    # Same fix, melon side: hand 4 must not plant on a non-(4,2) tile it's
    # merely passing through, even with melon seed in stock.
    obs = make_hands_obs(
        melon_seeds=1,
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (3, 4)],
        tiles={(3, 4): None},
    )
    action = wheat_loop_melon_agent(obs)
    assert action["hands"][4] == ["NORTH"]


def test_melon_farmer_still_follows_loop_order_12():
    # Farmer logic is unchanged -- still wheat-only, same as
    # wheat_loop_hands_agent.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_hands_obs(day=0, farmer=(1, 4), tiles={(1, 4): tile})
    action = wheat_loop_melon_agent(obs)
    assert action["farmer"] == ["WEST"]


# -- MELON_HAND_ZONES[4] expansion (2026-08-22) ---------------------------
#
# Regression check for the orphaned-tile bug found in the real Kaggle
# replay (episode 96612755, logged in PROGRESS.md): the farmer's own
# LOOP_ORDER_12 never once reached (4,3) in 720 turns (resets to (4,4)
# daily, rarely finishes a full lap). Fix: hand 4's zone grew from a
# single self-looping tile to the 2x2 block (4,2)-(4,3)-(3,3)-(3,2).


def test_melon_hand_zones_are_pairwise_disjoint():
    # Only compare each zone's *home* tiles (steady-state), same caveat as
    # HAND_ZONES: zone 3's (0,1) key is a shared entry point, not a home
    # tile, and zone 0 legitimately owns (0,1) as a home tile.
    steady_state = [
        {(0, 0), (1, 0), (1, 1), (0, 1)},
        {(2, 0), (3, 0), (3, 1), (2, 1)},
        {(4, 0), (4, 1)},
        {(0, 2), (1, 2)},
        {(4, 2), (4, 3), (3, 3), (3, 2)},
    ]
    for i, a in enumerate(steady_state):
        for j, b in enumerate(steady_state):
            if i < j:
                assert not (a & b)


def test_melon_hand_zone_four_is_a_closed_adjacent_cycle():
    zone4 = MELON_HAND_ZONES[4]
    assert len(zone4) == 4
    assert_is_closed_adjacent_cycle(zone4)


def test_melon_hand_tends_the_new_zone_tiles_not_just_the_original_one():
    # Hands 0-3 parked off to the side (irrelevant to this check) so their
    # positions never collide with hand 4's tile under test.
    for tile_pos in [(4, 3), (3, 3), (3, 2)]:
        obs = make_hands_obs(
            melon_seeds=1,
            hands=[(5, 4), (5, 4), (5, 4), (5, 4), tile_pos],
            tiles={tile_pos: None},
        )
        action = wheat_loop_melon_agent(obs)
        assert action["hands"][4] == ["PLANT", "MELON"], tile_pos


# -- melon_rush_agent -------------------------------------------------------
#
# All-in melon experiment (PROGRESS.md, 2026-08-22): every unit grows MELON,
# reusing wheat_loop_hands_agent's structure (LOOP_ORDER_12 / HAND_ZONES)
# with WHEAT -> MELON and threshold 2 -> 10 everywhere.


def test_rush_hires_while_under_five():
    obs = make_hands_obs(hands=[(4, 4), (3, 4)])
    action = melon_rush_agent(obs)
    assert ["HIRE"] in action["market"]


def test_rush_buys_melon_seed_in_batch_up_to_six():
    obs = make_hands_obs(melon_seeds=2)
    action = melon_rush_agent(obs)
    assert ["BUY_SEED", "MELON", 4] in action["market"]


def test_rush_does_not_buy_seed_when_stocked_past_six():
    obs = make_hands_obs(step=100, melon_seeds=6)
    action = melon_rush_agent(obs)
    assert not any(order[0] == "BUY_SEED" for order in action["market"])


def test_rush_hand_plants_melon_on_its_own_empty_tile():
    obs = make_hands_obs(melon_seeds=1, hands=[(0, 0)], tiles={(0, 0): None})
    action = melon_rush_agent(obs)
    assert action["hands"] == [["PLANT", "MELON"]]


def test_rush_hand_does_not_harvest_at_the_wheat_threshold_age():
    # crop_age=2 would harvest a WHEAT tile everywhere else in this file,
    # but melon_rush_agent's threshold is 10 for every hand.
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": True}
    obs = make_hands_obs(day=2, hands=[(0, 0)], tiles={(0, 0): tile})
    action = melon_rush_agent(obs)
    assert action["hands"] == [["EAST"]]  # zone move, not HARVEST


def test_rush_hand_harvests_at_the_melon_threshold_age():
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": False}
    obs = make_hands_obs(day=10, hands=[(0, 0)], tiles={(0, 0): tile})
    action = melon_rush_agent(obs)
    assert action["hands"] == [["HARVEST"]]


def test_rush_hand_does_not_tend_a_shared_transit_tile_outside_its_own_zone():
    obs = make_hands_obs(
        melon_seeds=1,
        hands=[(3, 4)],
        tiles={(3, 4): None},
    )
    action = melon_rush_agent(obs)
    assert action["hands"] == [["NORTH"]]


def test_rush_sells_melon_when_in_shed():
    obs = make_hands_obs(melon_shed=3)
    action = melon_rush_agent(obs)
    assert ["SELL", "MELON", 1] in action["market"]


def test_rush_does_not_sell_wheat_ever():
    obs = make_hands_obs(shed=5)  # WHEAT in shed, should be irrelevant
    action = melon_rush_agent(obs)
    assert not any(order[:2] == ["SELL", "WHEAT"] for order in action["market"])


def test_rush_farmer_plants_melon_not_wheat():
    obs = make_hands_obs(melon_seeds=1, farmer=(4, 4), tiles={(4, 4): None})
    action = melon_rush_agent(obs)
    assert action["farmer"] == ["PLANT", "MELON"]


def test_rush_farmer_harvests_at_the_melon_threshold_age():
    tile = {"kind": "PLANT", "planted_day": 0, "watered_today": False}
    obs = make_hands_obs(day=10, farmer=(1, 4), tiles={(1, 4): tile})
    action = melon_rush_agent(obs)
    assert action["farmer"] == ["HARVEST"]


# -- melon_then_wheat_agent ---------------------------------------------
#
# One-way day-based crop switch (PROGRESS.md, 2026-08-22): MELON for the
# first 10 days, WHEAT from day 10 onward. Harvest threshold always comes
# from the tile's own crop, not the current phase, since MELON planted
# before the switch keeps growing after it.


def test_switch_hand_plants_melon_before_day_10():
    obs = make_hands_obs(day=5, melon_seeds=1, hands=[(0, 0)], tiles={(0, 0): None})
    action = melon_then_wheat_agent(obs)
    assert action["hands"] == [["PLANT", "MELON"]]


def test_switch_hand_plants_wheat_from_day_10():
    obs = make_hands_obs(day=10, seeds=1, hands=[(0, 0)], tiles={(0, 0): None})
    action = melon_then_wheat_agent(obs)
    assert action["hands"] == [["PLANT", "WHEAT"]]


def test_switch_buys_melon_seed_before_day_10():
    obs = make_hands_obs(day=5, melon_seeds=2)
    action = melon_then_wheat_agent(obs)
    assert ["BUY_SEED", "MELON", 4] in action["market"]


def test_switch_buys_wheat_seed_from_day_10():
    obs = make_hands_obs(day=10, seeds=2)
    action = melon_then_wheat_agent(obs)
    assert ["BUY_SEED", "WHEAT", 4] in action["market"]


def test_switch_does_not_buy_melon_seed_once_in_wheat_phase():
    obs = make_hands_obs(step=100, day=10, melon_seeds=0)
    action = melon_then_wheat_agent(obs)
    assert not any(order[:2] == ["BUY_SEED", "MELON"] for order in action["market"])


def test_switch_harvest_threshold_uses_the_tiles_own_crop_not_the_phase():
    # A MELON planted on day 8 (before the switch) is still growing on
    # day 12 (after it) -- must wait for its own day 18, not jump to the
    # WHEAT-phase threshold of 2. crop_age=4 < 10 and already watered ->
    # move to the zone's next tile (EAST from (0,0), per HAND_ZONES[0]).
    tile = {"kind": "PLANT", "crop": "MELON", "planted_day": 8, "watered_today": True}
    obs = make_hands_obs(day=12, hands=[(0, 0)], tiles={(0, 0): tile})
    action = melon_then_wheat_agent(obs)
    assert action["hands"] == [["EAST"]]


def test_switch_harvests_a_wheat_tile_at_its_own_threshold_after_the_switch():
    tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 10, "watered_today": False}
    obs = make_hands_obs(day=12, hands=[(0, 0)], tiles={(0, 0): tile})
    action = melon_then_wheat_agent(obs)
    assert action["hands"] == [["HARVEST"]]


def test_switch_sells_the_full_melon_shed_not_one_unit_at_a_time():
    # Dumping the whole shed at once beats 1/turn when the market is
    # shared with an opponent also selling melon (PROGRESS.md, 2026-08-22)
    # -- every unit sells at the same price either way (checked directly
    # in the engine's per-unit lockstep market loop), but trickling gives
    # the opponent's own sales more turns to degrade the price first.
    obs = make_hands_obs(day=15, melon_shed=3)
    action = melon_then_wheat_agent(obs)
    assert ["SELL", "MELON", 3] in action["market"]


def test_switch_sells_the_full_wheat_shed_not_one_unit_at_a_time():
    obs = make_hands_obs(day=15, shed=2)
    action = melon_then_wheat_agent(obs)
    assert ["SELL", "WHEAT", 2] in action["market"]


def test_switch_farmer_plants_melon_before_day_10():
    obs = make_hands_obs(day=5, melon_seeds=1, farmer=(4, 4), tiles={(4, 4): None})
    action = melon_then_wheat_agent(obs)
    assert action["farmer"] == ["PLANT", "MELON"]


def test_switch_farmer_plants_wheat_from_day_10():
    obs = make_hands_obs(day=10, seeds=1, farmer=(4, 4), tiles={(4, 4): None})
    action = melon_then_wheat_agent(obs)
    assert action["farmer"] == ["PLANT", "WHEAT"]


# -- melon_then_wheat_extra_hands_agent ----------------------------------
#
# Extends melon_then_wheat_agent with 2 extra hands (indices 5, 6)
# dedicated to NE, hired only once NE is bought (PROGRESS.md, 2026-08-23;
# notebooks/12_buy_land_extra_hands.ipynb). NW (hands 0-4) is unchanged.


def make_ne_obs(
    *,
    step=5,
    day=0,
    seeds=0,
    shed=0,
    melon_seeds=0,
    melon_shed=0,
    farmer=(4, 4),
    hands=(),
    tiles=None,
    money=3000,
    unlocked_quadrants=("NW",),
):
    """Same shape as make_hands_obs, but a 10x10 board -- large enough to
    also cover NE (x=5..9, y=0..4)."""
    board = [[None] * 10 for _ in range(10)]
    for (x, y), tile in (tiles or {}).items():
        board[y][x] = tile
    return {
        "player": 0,
        "step": step,
        "day": day,
        "farms": [
            {
                "farmer": list(farmer),
                "hands": [list(h) for h in hands],
                "tiles": board,
                "money": money,
                "unlocked_quadrants": list(unlocked_quadrants),
            }
        ],
        "private": {
            "seeds": {"WHEAT": seeds, "MELON": melon_seeds},
            "shed": {"WHEAT": shed, "MELON": melon_shed},
        },
    }


def test_loop_order_hands_ne_is_a_single_closed_cycle_of_adjacent_tiles():
    assert len(LOOP_ORDER_HANDS_NE) == 16
    assert_is_closed_adjacent_cycle(LOOP_ORDER_HANDS_NE)


def test_zone_top_ne_is_a_single_closed_cycle_of_adjacent_tiles():
    assert len(ZONE_TOP_NE) == 10
    assert_is_closed_adjacent_cycle(ZONE_TOP_NE)


def test_zone_left_ne_is_a_single_closed_cycle_of_adjacent_tiles():
    assert len(ZONE_LEFT_NE) == 6
    assert_is_closed_adjacent_cycle(ZONE_LEFT_NE)


def test_zone_right_ne_is_a_single_closed_cycle_of_adjacent_tiles():
    # 15 tiles in the y=2-4 block minus (8,3), split into ZONE_LEFT_NE (6)
    # and ZONE_RIGHT_NE (8) -- a single closed loop can't visit all 15 in
    # one piece (grid adjacency is bipartite, so a cycle needs an even
    # tile count), and this split also keeps each hand under the
    # ~12-tiles/day ceiling wheat_loop_12_agent was sized against.
    assert len(ZONE_RIGHT_NE) == 8
    assert (8, 3) not in ZONE_RIGHT_NE
    assert_is_closed_adjacent_cycle(ZONE_RIGHT_NE)


def test_ne_zones_are_pairwise_disjoint():
    zones = [ZONE_TOP_NE, ZONE_LEFT_NE, ZONE_RIGHT_NE]
    for i, a in enumerate(zones):
        for j, b in enumerate(zones):
            if i < j:
                assert not (set(a) & set(b))


def test_spawn_feeder_ne_routes_each_corner_toward_the_loop_entry():
    for pos, nxt in SPAWN_FEEDER_NE.items():
        assert abs(nxt[0] - pos[0]) + abs(nxt[1] - pos[1]) == 1
        assert nxt == (5, 4) or nxt in SPAWN_FEEDER_NE


def test_extra_hands_hires_while_under_five_regardless_of_quadrants():
    obs = make_ne_obs(hands=[(4, 4), (3, 4)], unlocked_quadrants=("NW",))
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["HIRE"] in action["market"]


def test_extra_hands_does_not_hire_past_five_before_ne_unlocked():
    obs = make_ne_obs(
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (4, 2)],
        unlocked_quadrants=("NW",),
    )
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["HIRE"] not in action["market"]


def test_extra_hands_hires_up_to_eight_once_ne_unlocked():
    obs = make_ne_obs(
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (4, 2)],
        unlocked_quadrants=("NW", "NE"),
    )
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["HIRE"] in action["market"]


def test_extra_hands_does_not_hire_past_eight_even_with_ne_unlocked():
    obs = make_ne_obs(
        hands=[(4, 4), (3, 4), (3, 3), (3, 2), (4, 2), (5, 4), (5, 0), (7, 2)],
        unlocked_quadrants=("NW", "NE"),
    )
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["HIRE"] not in action["market"]


def test_extra_hands_buys_seed_in_batch_up_to_nine():
    # Up to 9 units can now want to plant at once (farmer + up to 8 hands),
    # vs. the 6 melon_then_wheat_agent's seed buffer was tuned for.
    obs = make_ne_obs(day=10, seeds=2)
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["BUY_SEED", "WHEAT", 7] in action["market"]


def test_extra_hands_buys_land_once_affordable_in_wheat_phase():
    obs = make_ne_obs(day=10, money=1000, unlocked_quadrants=("NW",))
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["BUY_LAND"] in action["market"]


def test_extra_hands_does_not_buy_land_before_wheat_phase_even_if_affordable():
    # Regression check: starting money ($3000) already clears the $1000
    # threshold on turn 0, day 0 (melon phase) -- BUY_LAND must wait for
    # crop_to_plant == "WHEAT" (day >= 10), not fire immediately.
    obs = make_ne_obs(day=5, money=3000, unlocked_quadrants=("NW",))
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["BUY_LAND"] not in action["market"]


def test_extra_hands_does_not_buy_land_once_already_unlocked():
    obs = make_ne_obs(day=10, money=5000, unlocked_quadrants=("NW", "NE"))
    action = melon_then_wheat_extra_hands_agent(obs)
    assert ["BUY_LAND"] not in action["market"]


def test_hand_five_plants_wheat_on_its_own_ne_zone_tile():
    # (6,1) is only a ZONE_TOP_NE tile (not in ZONE_LEFT_NE, ZONE_RIGHT_NE,
    # or the shared LOOP_ORDER_HANDS_NE ring) -- a regression check that
    # hand 5 really uses ZONE_TOP_NE (own_zone assignment bug).
    obs = make_ne_obs(
        day=10,
        seeds=1,
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), (3, 4), (6, 1)],
        tiles={(6, 1): None},
        unlocked_quadrants=("NW", "NE"),
    )
    action = melon_then_wheat_extra_hands_agent(obs)
    assert action["hands"][5] == ["PLANT", "WHEAT"]


def test_hand_six_plants_wheat_on_its_own_ne_zone_tile():
    # (6,3) is only a ZONE_LEFT_NE tile (interior, not in ZONE_TOP_NE,
    # ZONE_RIGHT_NE, or the shared ring) -- same regression check, hand 6.
    obs = make_ne_obs(
        day=10,
        seeds=1,
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), (3, 4), (5, 0), (6, 3)],
        tiles={(6, 3): None},
        unlocked_quadrants=("NW", "NE"),
    )
    action = melon_then_wheat_extra_hands_agent(obs)
    assert action["hands"][6] == ["PLANT", "WHEAT"]


def test_hand_seven_plants_wheat_on_its_own_ne_zone_tile():
    # (8,2) is only a ZONE_RIGHT_NE tile (not in ZONE_TOP_NE, ZONE_LEFT_NE,
    # or the shared ring) -- same regression check, for hand 7.
    obs = make_ne_obs(
        day=10,
        seeds=1,
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), (3, 4), (5, 0), (5, 2), (8, 2)],
        tiles={(8, 2): None},
        unlocked_quadrants=("NW", "NE"),
    )
    action = melon_then_wheat_extra_hands_agent(obs)
    assert action["hands"][7] == ["PLANT", "WHEAT"]


def test_hand_five_does_not_tend_a_shared_ring_tile_outside_its_own_zone():
    # (9,4) is a LOOP_ORDER_HANDS_NE ring tile and a ZONE_RIGHT_NE tile,
    # but not in ZONE_TOP_NE -- hand 5 must move through it (NORTH, per
    # LOOP_ORDER_HANDS_NE), never plant there, even with seed in stock.
    obs = make_ne_obs(
        day=10,
        seeds=1,
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), (3, 4), (9, 4)],
        tiles={(9, 4): None},
        unlocked_quadrants=("NW", "NE"),
    )
    action = melon_then_wheat_extra_hands_agent(obs)
    assert action["hands"][5] == ["NORTH"]


def test_extra_hands_farmer_still_follows_loop_order_12():
    # Farmer logic is unchanged from melon_then_wheat_agent -- NE is hands
    # 5/6/7 only. crop_age=0 < threshold and already watered -> move on to
    # the next LOOP_ORDER_12 tile, (0,4), a WEST move.
    tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0, "watered_today": True}
    obs = make_ne_obs(day=0, farmer=(1, 4), tiles={(1, 4): tile})
    action = melon_then_wheat_extra_hands_agent(obs)
    assert action["farmer"] == ["WEST"]
def make_goose_obs(
    *,
    step=5,
    day=0,
    seeds=0,
    shed=0,
    melon_seeds=0,
    melon_shed=0,
    goose_shed=0,
    egg_shed=0,
    farmer=(4, 4),
    hands=(),
    tiles=None,
    money=3000,
    unlocked_quadrants=("NW",),
    inventories=None,
):
    """Like make_hands_obs, but adds private.inventories (hand 4's own
    inventory in melon_then_wheat_goose_agent lives at inventories[5]) and
    GOOSE/EGG shed keys."""
    board = [[None] * 6 for _ in range(6)]
    for (x, y), tile in (tiles or {}).items():
        board[y][x] = tile
    if inventories is None:
        inventories = [{} for _ in range(len(hands) + 1)]
    return {
        "player": 0,
        "step": step,
        "day": day,
        "farms": [
            {
                "farmer": list(farmer),
                "hands": [list(h) for h in hands],
                "tiles": board,
                "money": money,
                "unlocked_quadrants": list(unlocked_quadrants),
            }
        ],
        "private": {
            "seeds": {"WHEAT": seeds, "MELON": melon_seeds},
            "shed": {"WHEAT": shed, "MELON": melon_shed, "GOOSE": goose_shed, "EGG": egg_shed},
            "inventories": inventories,
        },
    }


def test_goose_buys_goose_on_step_zero():
    obs = make_goose_obs(step=0, hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)])
    action = melon_then_wheat_goose_agent(obs)
    assert ["BUY_ANIMAL", "GOOSE", 1] in action["market"]


def test_goose_buys_wheat_product_during_melon_phase_when_shed_empty():
    obs = make_goose_obs(day=5, shed=0, hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)])
    action = melon_then_wheat_goose_agent(obs)
    assert ["BUY_PRODUCT", "WHEAT", 1] in action["market"]


def test_goose_does_not_buy_wheat_product_once_shed_has_some():
    obs = make_goose_obs(day=5, shed=1, hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)])
    action = melon_then_wheat_goose_agent(obs)
    assert ["BUY_PRODUCT", "WHEAT", 1] not in action["market"]


def test_goose_does_not_buy_wheat_product_after_day_ten():
    # Regression: this must stop once real WHEAT growing starts, otherwise
    # it's needless spend on top of the harvested supply.
    obs = make_goose_obs(day=10, shed=0, hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)])
    action = melon_then_wheat_goose_agent(obs)
    assert ["BUY_PRODUCT", "WHEAT", 1] not in action["market"]


def test_goose_hand_uses_direct_feeder_route_not_shared_loop():
    # LOOP_ORDER_HANDS would send (4,4) -> (3,4) (WEST). GOOSE_FEEDER sends
    # it -> (4,3) (NORTH) instead -- the whole point of the direct route
    # (see the function docstring: hand 4 has zero turns of slack for the
    # full 15-move shared loop).
    obs = make_goose_obs(hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)])
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["NORTH"]


def test_goose_hand_picks_up_goose_when_shed_has_one():
    obs = make_goose_obs(goose_shed=1, hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)])
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["PICKUP", "GOOSE", 1]


def test_goose_hand_picks_up_wheat_once_carrying_goose_and_shed_has_wheat():
    obs = make_goose_obs(
        shed=1,
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)],
        inventories=[{}, {}, {}, {}, {}, {"GOOSE": 1}],
    )
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["PICKUP", "WHEAT", 1]


def test_goose_hand_does_not_stall_trying_to_pick_up_wheat_that_does_not_exist():
    # Regression for the real bug found in notebooks/13_animals.ipynb:
    # without the shed.get("WHEAT", 0) > 0 guard, this condition stayed
    # true forever (shed always 0 during the melon phase), permanently
    # blocking hand 4 at (4,4) instead of falling through to tend/move.
    tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0, "watered_today": False}
    obs = make_goose_obs(
        shed=0,
        tiles={(4, 4): tile},
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 4)],
    )
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["WATER"]


def test_goose_hand_moves_off_locked_spawn_corner():
    obs = make_goose_obs(hands=[(3, 4), (3, 4), (3, 4), (3, 4), (5, 4)], tiles={(5, 4): "LOCKED"})
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["WEST"]


def test_goose_hand_tends_a_transit_tile_opportunistically():
    # (4,3) is on the way to GOOSE_TILE but not GOOSE_TILE itself, and not
    # shed-adjacent -- the whole point of folding the goose into hand 4
    # instead of a dedicated hand: this used to be pure wasted transit.
    obs = make_goose_obs(
        day=0,
        melon_seeds=1,
        tiles={(4, 3): None},
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), (4, 3)],
    )
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["PLANT", "MELON"]


def test_goose_hand_builds_coop_on_empty_goose_tile():
    obs = make_goose_obs(hands=[(3, 4), (3, 4), (3, 4), (3, 4), GOOSE_TILE], tiles={GOOSE_TILE: None})
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["BUILD_COOP"]


def test_goose_hand_places_goose_when_carrying_one_on_empty_coop():
    obs = make_goose_obs(
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), GOOSE_TILE],
        tiles={GOOSE_TILE: {"kind": "COOP"}},
        inventories=[{}, {}, {}, {}, {}, {"GOOSE": 1}],
    )
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["PLACE", "GOOSE", 1]


def test_goose_hand_feeds_when_carrying_wheat_and_not_fed_today():
    tile = {
        "kind": "COOP",
        "animal": "GOOSE",
        "fed_today": False,
        "cared_today": False,
        "fertilizer_available": False,
        "yield_units": 0,
    }
    obs = make_goose_obs(
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), GOOSE_TILE],
        tiles={GOOSE_TILE: tile},
        inventories=[{}, {}, {}, {}, {}, {"WHEAT": 1}],
    )
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["FEED"]


def test_goose_hand_still_cares_without_wheat_in_hand():
    # Regression for the second real bug found: the old
    # `if wheat == 0: PASS` gate at the top of this branch skipped
    # COLLECT_FERTILIZER/CARE/HARVEST too, not just FEED, even on days
    # hand 4 wasn't carrying wheat -- eggs never got harvested as a result.
    tile = {
        "kind": "COOP",
        "animal": "GOOSE",
        "fed_today": True,
        "cared_today": False,
        "fertilizer_available": False,
        "yield_units": 0,
    }
    obs = make_goose_obs(
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), GOOSE_TILE],
        tiles={GOOSE_TILE: tile},
        inventories=[{}, {}, {}, {}, {}, {}],
    )
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["CARE"]


def test_goose_hand_sells_eggs_when_nothing_left_to_do_that_day():
    tile = {
        "kind": "COOP",
        "animal": "GOOSE",
        "fed_today": True,
        "cared_today": True,
        "fertilizer_available": False,
        "yield_units": 0,
    }
    obs = make_goose_obs(
        egg_shed=2,
        hands=[(3, 4), (3, 4), (3, 4), (3, 4), GOOSE_TILE],
        tiles={GOOSE_TILE: tile},
    )
    action = melon_then_wheat_goose_agent(obs)
    assert action["hands"][4] == ["PASS"]
    assert ["SELL", "EGG", 2] in action["market"]


def test_goose_feeder_is_a_closed_two_step_route_to_goose_tile():
    assert GOOSE_FEEDER[(4, 4)] == (4, 3)
    assert GOOSE_FEEDER[(4, 3)] == GOOSE_TILE
    assert GOOSE_FEEDER[GOOSE_TILE] == GOOSE_TILE
