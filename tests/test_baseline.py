"""Unit tests for kaggriculture_bot.strategies.baseline's wheat_loop_agent
and wheat_loop_2x2_agent — plumbing (which action each picks for a given
obs), not agent quality; that's what evaluate.py's harness is for.
"""

from kaggriculture_bot.strategies.baseline import (
    DIRECTIONS,
    LOOP_ORDER_2X2,
    LOOP_ORDER_12,
    wheat_loop_agent,
    wheat_loop_2x2_agent,
    wheat_loop_12_agent,
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
