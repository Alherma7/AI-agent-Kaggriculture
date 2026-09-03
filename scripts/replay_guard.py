"""Diagnostic guard: detect silent action failures, calibrated and
cross-checked against the reference top-leaderboard replay
(`replays/103962387.json`) instead of assumed from reading the engine
source alone.

Two independent checks:

1. Silent-failure detection. For every market order / unit op an agent
   issues in a local episode, checks whether it had the effect the
   engine is supposed to give it (money/shed/seeds/tile/inventory
   deltas). A streak of consecutive failed attempts at the same thing
   raises one warning instead of staying silent forever -- this is
   exactly the shape every bug found by hand so far in this project has
   had: `BUY_PRODUCT WHEAT` failing 19 turns straight (day 1-4 money
   starvation), the `day == 4` CARROT/STRAWBERRY one-shot never landing,
   `HIRE`/`BUY_LAND`/staged `BUY_ANIMAL` one-shots silently not firing.
   `calibrate_from_reference_replay()` runs these same checkers against
   the real reference replay first, so the "expected effect" rules are
   validated against real engine behaviour, not just read off the source
   once and trusted.

2. Milestone comparison. Extracts each action type's first-occurrence
   day from the reference replay (both seats) and compares it against a
   traced local episode of any agent, flagging milestones we reach
   meaningfully later, or never.

Usage:
    python scripts/replay_guard.py                       # audits agent/main.py
    python scripts/replay_guard.py --seed 3               # a specific seed
    python scripts/replay_guard.py --calibrate-only        # just run check #1's self-test

This is a read-only diagnostic tool. It never edits the notebook, `agent/main.py`,
or any other project file -- it only runs local episodes and reports.
"""
import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_REPLAY = ROOT / "replays" / "103962387.json"
DEFAULT_AGENT = ROOT / "agent" / "main.py"

STUCK_THRESHOLD = 3  # consecutive failed attempts at the same order/op before warning


# ---------------------------------------------------------------------------
# Expected-effect checkers. Each one answers "given this op was issued and
# its precondition looked satisfiable from `obs`, did it actually do what
# the engine (kaggriculture.py) says it should?" Read directly from the
# engine source (not guessed), and cross-checked against the reference
# replay by `calibrate_from_reference_replay()` below.
# ---------------------------------------------------------------------------

def market_order_succeeded(order, pre_farm, post_farm, pre_private, post_private):
    """order = e.g. ["BUY_LAND"], ["BUY_SEED","WHEAT",6], ["SELL","MELON",4]."""
    op = order[0]
    item = order[1] if len(order) > 1 else None

    if op == "HIRE":
        return len(post_farm["hands"]) > len(pre_farm["hands"])
    if op == "BUY_LAND":
        return len(post_farm["unlocked_quadrants"]) > len(pre_farm["unlocked_quadrants"])
    if op == "BUY_SEED":
        return post_private["seeds"].get(item, 0) > pre_private["seeds"].get(item, 0)
    if op == "BUY_PRODUCT":
        return post_private["shed"].get(item, 0) > pre_private["shed"].get(item, 0)
    if op == "BUY_ANIMAL":
        return post_private["shed"].get(item, 0) > pre_private["shed"].get(item, 0)
    if op == "SELL":
        return post_private["shed"].get(item, 0) < pre_private["shed"].get(item, 0)
    return None  # unknown order type -- not checked


MOVE_OPS = {"NORTH", "SOUTH", "EAST", "WEST"}
_TILE_MUTATING_OPS = {
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
    "BUILD_PASTURE", "PLACE", "PICKUP", "DROP", "FEED", "CARE",
    "COLLECT_FERTILIZER",
}


def unit_op_succeeded(op_list, pre_pos, post_pos, pre_tile, post_tile, pre_inv, post_inv):
    """op_list = the unit's own action, e.g. ["WATER"], ["PICKUP","WHEAT",1].
    pre_tile/post_tile are the tile at pre_pos (the unit's position BEFORE
    this turn -- tile ops act on the tile the unit starts the turn on, not
    where it ends up if the op were a move instead)."""
    if not op_list:
        return None
    op = op_list[0]
    item = op_list[1] if len(op_list) > 1 else None

    if op in MOVE_OPS:
        return pre_pos != post_pos
    if op == "PASS":
        return None  # no expected effect

    def tile_dict(t):
        return t if isinstance(t, dict) else {}

    pre_t, post_t = tile_dict(pre_tile), tile_dict(post_tile)

    if op == "PLANT":
        return pre_tile is None and isinstance(post_tile, dict) and post_tile.get("kind") == "PLANT"
    if op == "WATER":
        if not (isinstance(pre_tile, dict) and pre_tile.get("kind") == "PLANT"):
            return None  # precondition not met -- not this checker's business
        if pre_t.get("watered_today"):
            return None  # already watered -- correctly a no-op, not a failure
        return post_t.get("watered_today") is True
    if op == "HARVEST":
        if pre_t.get("yield_units", 0) <= 0:
            return None
        return post_t.get("yield_units", 0) < pre_t.get("yield_units", 0)
    if op == "FERTILIZE":
        return post_inv.get("FERTILIZER", 0) < pre_inv.get("FERTILIZER", 0)
    if op == "DIG":
        if pre_tile is None or (isinstance(pre_tile, dict) and "animal" in pre_tile):
            return None  # precondition not met
        return post_tile is None
    if op in ("BUILD_COOP", "BUILD_PASTURE"):
        if pre_tile is not None:
            return None
        want_kind = "COOP" if op == "BUILD_COOP" else "PASTURE"
        return isinstance(post_tile, dict) and post_tile.get("kind") == want_kind
    if op == "PLACE":
        # Two distinct engine paths: place an animal on a matching empty
        # structure, or drop an item at the shed. Distinguish by the tile.
        if isinstance(pre_tile, dict) and pre_tile.get("kind") in ("COOP", "PASTURE") and "animal" not in pre_tile:
            return isinstance(post_tile, dict) and post_tile.get("animal") == item
        return post_inv.get(item, 0) < pre_inv.get(item, 0)
    if op == "PICKUP":
        return post_inv.get(item, 0) > pre_inv.get(item, 0)
    if op == "DROP":
        pre_total = sum(pre_inv.values())
        if pre_total == 0:
            return None
        return sum(post_inv.values()) < pre_total
    if op == "FEED":
        if not (isinstance(pre_tile, dict) and "animal" in pre_tile) or pre_t.get("fed_today"):
            return None
        return post_t.get("fed_today") is True
    if op == "CARE":
        if not (isinstance(pre_tile, dict) and "animal" in pre_tile) or pre_t.get("cared_today"):
            return None
        return post_t.get("cared_today") is True
    if op == "COLLECT_FERTILIZER":
        if not (isinstance(pre_tile, dict) and "animal" in pre_tile) or not pre_t.get("fertilizer_available"):
            return None
        return post_inv.get("FERTILIZER", 0) > pre_inv.get("FERTILIZER", 0)
    return None


# ---------------------------------------------------------------------------
# Calibration: run the checkers against the real reference replay to
# confirm they match actual engine behaviour, not just the source read.
# ---------------------------------------------------------------------------

def calibrate_from_reference_replay(replay_path=REFERENCE_REPLAY, verbose=True):
    with open(replay_path, encoding="utf-8") as f:
        replay = json.load(f)
    steps = replay["steps"]
    n_players = len(steps[0])

    market_stats = defaultdict(lambda: [0, 0])  # (op,item) -> [succeeded, failed]
    unit_stats = defaultdict(lambda: [0, 0])    # op -> [succeeded, failed]

    for player in range(n_players):
        for t in range(1, len(steps)):
            # Confirmed empirically (not assumed) against this replay: the
            # action recorded AT index t was computed from the observation
            # at (t-1), and its effect is what's visible in the observation
            # AT index t -- i.e. steps[t]["observation"] is a post-state,
            # not the input the agent saw. A naive same-index pre/post pair
            # (obs[t] vs obs[t+1]) makes every check fail near-universally.
            action = steps[t][player].get("action") or {}
            obs = steps[t - 1][player]["observation"]
            obs_next = steps[t][player]["observation"]
            farm, farm_next = obs["farms"][player], obs_next["farms"][player]
            priv, priv_next = obs["private"], obs_next["private"]

            for order in action.get("market", []) or []:
                if not order:
                    continue
                result = market_order_succeeded(order, farm, farm_next, priv, priv_next)
                if result is None:
                    continue
                key = (order[0], order[1] if len(order) > 1 else None)
                market_stats[key][0 if result else 1] += 1

            units = [("farmer", action.get("farmer"), 0)]
            for i, op_list in enumerate(action.get("hands", []) or []):
                units.append((f"hand{i}", op_list, i + 1))
            for _, op_list, inv_idx in units:
                if not op_list:
                    continue
                pos = farm["farmer"] if inv_idx == 0 else (
                    farm["hands"][inv_idx - 1] if inv_idx - 1 < len(farm["hands"]) else None
                )
                pos_next = farm_next["farmer"] if inv_idx == 0 else (
                    farm_next["hands"][inv_idx - 1] if inv_idx - 1 < len(farm_next["hands"]) else None
                )
                if pos is None or pos_next is None:
                    continue
                fx, fy = pos
                tile = farm["tiles"][fy][fx] if farm["tiles"][fy][fx] != "LOCKED" else "LOCKED"
                tile_next = farm_next["tiles"][fy][fx] if farm_next["tiles"][fy][fx] != "LOCKED" else "LOCKED"
                pre_inv = priv["inventories"][inv_idx] if inv_idx < len(priv["inventories"]) else {}
                post_inv = priv_next["inventories"][inv_idx] if inv_idx < len(priv_next["inventories"]) else {}
                if tile == "LOCKED":
                    continue  # engine no-ops everything here; not informative
                result = unit_op_succeeded(op_list, tuple(pos), tuple(pos_next), tile, tile_next, pre_inv, post_inv)
                if result is None:
                    continue
                unit_stats[op_list[0]][0 if result else 1] += 1

    if verbose:
        print("=== Calibration against replays/103962387.json ===")
        print("(succeeded / failed, per order/op type -- 'failed' here just means the")
        print(" engine's own precondition wasn't met that turn, e.g. no money; a checker")
        print(" is suspect only if it disagrees with what a human reading the trace would say)")
        print("\n-- market orders --")
        for key, (ok, bad) in sorted(market_stats.items()):
            print(f"  {key}: {ok} ok / {bad} no-effect")
        print("\n-- unit ops --")
        for key, (ok, bad) in sorted(unit_stats.items()):
            print(f"  {key}: {ok} ok / {bad} no-effect")
    return market_stats, unit_stats


# ---------------------------------------------------------------------------
# Milestone extraction + comparison.
# ---------------------------------------------------------------------------

MILESTONE_ORDER_TYPES = {
    "market": ["HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"],
    "unit": ["PLANT", "HARVEST", "DIG", "FERTILIZE", "FEED", "BUILD_COOP", "BUILD_PASTURE", "PLACE"],
}


def _milestone_key(kind, order):
    if kind == "market" and order[0] in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL") and len(order) > 1:
        return f"{order[0]} {order[1]}"
    if kind == "unit" and order[0] == "PLANT" and len(order) > 1:
        return f"PLANT {order[1]}"
    return order[0]


def extract_milestones(replay_path=REFERENCE_REPLAY):
    """First day each interesting order type appears, per seat, from a real
    replay JSON (same format `evaluate.py`/local episodes produce)."""
    with open(replay_path, encoding="utf-8") as f:
        replay = json.load(f)
    steps = replay["steps"]
    n_players = len(steps[0])
    first_day = defaultdict(lambda: [None] * n_players)

    for player in range(n_players):
        for t in range(1, len(steps)):
            # Same pre/post convention as calibrate_from_reference_replay:
            # action[t] was decided from obs[t-1], so that's the day it was
            # actually issued on.
            action = steps[t][player].get("action") or {}
            obs = steps[t - 1][player]["observation"]
            day = obs["day"]
            for order in action.get("market", []) or []:
                if not order:
                    continue
                key = _milestone_key("market", order)
                if first_day[key][player] is None:
                    first_day[key][player] = day
            for op_list in [action.get("farmer")] + list(action.get("hands", []) or []):
                if not op_list:
                    continue
                if op_list[0] not in MILESTONE_ORDER_TYPES["unit"]:
                    continue
                key = _milestone_key("unit", op_list)
                if first_day[key][player] is None:
                    first_day[key][player] = day
    return dict(first_day)


def trace_local_episode(agent, opponent, seed=1, episode_steps=720):
    """Run one local episode and return the same first-day-per-milestone
    shape as `extract_milestones`, for player 0 (our agent) only."""
    sys.path.insert(0, str(ROOT / "src"))
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": episode_steps, "seed": seed}, debug=True)
    env.reset()
    env.run([agent, opponent])

    first_day = {}
    for t in range(1, len(env.steps)):
        # Same pre/post convention as guard_episode: the day the order was
        # actually decided on is obs[t-1]'s day.
        action = env.steps[t][0].get("action") or {}
        obs = env.steps[t - 1][0]["observation"]
        day = obs["day"]
        for order in action.get("market", []) or []:
            if not order:
                continue
            key = _milestone_key("market", order)
            first_day.setdefault(key, day)
        for op_list in [action.get("farmer")] + list(action.get("hands", []) or []):
            if not op_list or op_list[0] not in MILESTONE_ORDER_TYPES["unit"]:
                continue
            key = _milestone_key("unit", op_list)
            first_day.setdefault(key, day)
    return first_day, env


def compare_milestones(reference_milestones, our_milestones, behind_threshold=2):
    print("\n=== Milestone comparison vs replays/103962387.json ===")
    all_keys = sorted(reference_milestones.keys())
    for key in all_keys:
        ref_days = [d for d in reference_milestones[key] if d is not None]
        ref_day = min(ref_days) if ref_days else None
        our_day = our_milestones.get(key)
        if ref_day is None:
            continue
        if our_day is None:
            print(f"  NEVER REACHED: {key} (replay reaches it by day {ref_day})")
        elif our_day - ref_day >= behind_threshold:
            print(f"  BEHIND: {key} -- us day {our_day}, replay day {ref_day} (+{our_day - ref_day})")
        else:
            print(f"  ok: {key} -- us day {our_day}, replay day {ref_day}")


# ---------------------------------------------------------------------------
# Silent-failure detection over a local episode.
# ---------------------------------------------------------------------------

def guard_episode(agent, opponent, seed=1, episode_steps=720, stuck_threshold=STUCK_THRESHOLD):
    sys.path.insert(0, str(ROOT / "src"))
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": episode_steps, "seed": seed}, debug=True)
    env.reset()
    env.run([agent, opponent])

    market_streak = defaultdict(int)
    unit_streak = defaultdict(int)
    warnings = []

    for t in range(1, len(env.steps)):
        # Same pre/post convention confirmed in calibrate_from_reference_replay:
        # action[t] was decided from obs[t-1] and its effect lands in obs[t].
        action = env.steps[t][0].get("action") or {}
        obs = env.steps[t - 1][0]["observation"]
        obs_next = env.steps[t][0]["observation"]
        farm, farm_next = obs["farms"][0], obs_next["farms"][0]
        priv, priv_next = obs["private"], obs_next["private"]
        day = obs["day"]

        for order in action.get("market", []) or []:
            if not order:
                continue
            result = market_order_succeeded(order, farm, farm_next, priv, priv_next)
            if result is None:
                continue
            key = (order[0], order[1] if len(order) > 1 else None)
            if result:
                market_streak[key] = 0
            else:
                market_streak[key] += 1
                if market_streak[key] == stuck_threshold:
                    warnings.append(
                        f"step {t} (day {day}): market order {key} failed "
                        f"{stuck_threshold}+ turns in a row (money=${farm['money']:.0f})"
                    )

        units = [("farmer", action.get("farmer"), 0)]
        for i, op_list in enumerate(action.get("hands", []) or []):
            units.append((f"hand{i}", op_list, i + 1))
        for unit_name, op_list, inv_idx in units:
            if not op_list:
                continue
            pos = farm["farmer"] if inv_idx == 0 else (
                farm["hands"][inv_idx - 1] if inv_idx - 1 < len(farm["hands"]) else None
            )
            pos_next = farm_next["farmer"] if inv_idx == 0 else (
                farm_next["hands"][inv_idx - 1] if inv_idx - 1 < len(farm_next["hands"]) else None
            )
            if pos is None or pos_next is None:
                continue
            fx, fy = pos
            tile = farm["tiles"][fy][fx]
            tile_next = farm_next["tiles"][fy][fx]
            pre_inv = priv["inventories"][inv_idx] if inv_idx < len(priv["inventories"]) else {}
            post_inv = priv_next["inventories"][inv_idx] if inv_idx < len(priv_next["inventories"]) else {}
            key = (unit_name, op_list[0])
            if tile == "LOCKED":
                unit_streak[key] = 0
                continue
            result = unit_op_succeeded(op_list, tuple(pos), tuple(pos_next), tile, tile_next, pre_inv, post_inv)
            if result is None:
                unit_streak[key] = 0
                continue
            if result:
                unit_streak[key] = 0
            else:
                unit_streak[key] += 1
                if unit_streak[key] == stuck_threshold:
                    warnings.append(
                        f"step {t} (day {day}): {key} failed {stuck_threshold}+ turns "
                        f"in a row at {pos}"
                    )
    return warnings, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default=str(DEFAULT_AGENT), help="path to an agent.py with an agent(obs) function")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--calibrate-only", action="store_true")
    args = parser.parse_args()

    calibrate_from_reference_replay()

    if args.calibrate_only:
        return

    sys.path.insert(0, str(ROOT / "src"))
    from kaggriculture_bot.strategies.baseline import melon_then_wheat_goose_cow_agent

    spec = importlib.util.spec_from_file_location("audited_agent", args.agent)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    agent = module.agent

    print(f"\n=== Silent-failure guard: {args.agent}, seed {args.seed} ===")
    warnings, _ = guard_episode(agent, melon_then_wheat_goose_cow_agent, seed=args.seed)
    if not warnings:
        print("  none")
    for w in warnings:
        print(f"  {w}")

    print(f"\n=== Tracing our agent for milestone comparison, seed {args.seed} ===")
    reference = extract_milestones()
    ours, _ = trace_local_episode(agent, melon_then_wheat_goose_cow_agent, seed=args.seed)
    compare_milestones(reference, ours)


if __name__ == "__main__":
    main()
