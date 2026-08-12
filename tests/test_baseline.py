"""Unit tests for kaggriculture_bot.strategies.baseline's wheat_loop_agent —
plumbing (which action it picks for a given obs), not agent quality; that's
what evaluate.py's harness is for.
"""

from kaggriculture_bot.strategies.baseline import wheat_loop_agent


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
