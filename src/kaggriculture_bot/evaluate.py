"""This project's evaluation harness: run N episodes of a candidate agent
against fixed opponents (built-ins "random"/"starter", and previously
graduated versions of our own agent) and report win rate + average final
money. This is the gate every strategy change must clear before it's wired
into agent/main.py (structuring-ml-projects step 6) — recompute the
baseline in the same run, don't compare against a stale recorded number.

Validated in notebooks/02_evaluate_harness.ipynb against 10 episodes each
of a wheat-loop agent vs "random" (win_rate=1.0, avg_money=3891.2) and vs
"starter" (win_rate=1.0, avg_money=3920.0).
"""

from typing import Callable, Optional, Union

from kaggle_environments import make
from kaggle_environments.core import Environment

Agent = Union[str, Callable]


def score_episodes(
    episode_results: list[tuple[float, float]],
) -> dict[str, float]:
    """Aggregate (my_money, opponent_money) tuples into win_rate and avg_money.

    A tie counts as half a win (0.5) toward win_rate.
    """
    scores = []
    my_moneys = []
    for my_money, opponent_money in episode_results:
        my_moneys.append(my_money)
        if my_money > opponent_money:
            scores.append(1)
        elif my_money == opponent_money:
            scores.append(0.5)
        else:
            scores.append(0)

    return {
        "win_rate": sum(scores) / len(scores),
        "avg_money": sum(my_moneys) / len(my_moneys),
    }


def run_episodes(
    agent0: Agent,
    agent1: Agent,
    n: int = 10,
    env: Optional[Environment] = None,
) -> list[tuple[float, float]]:
    """Run n episodes of agent0 vs agent1.

    Returns each episode's final (agent0_money, agent1_money). Creates a
    fresh 720-step environment if none is passed in.
    """
    if env is None:
        env = make(
            "kaggriculture", configuration={"episodeSteps": 720}, debug=True
        )

    results = []
    for _ in range(n):
        steps = env.run([agent0, agent1])
        results.append((steps[-1][0]["reward"], steps[-1][1]["reward"]))
    return results


def evaluate(
    agent0: Agent,
    agent1: Agent,
    n: int = 10,
    env: Optional[Environment] = None,
) -> dict[str, float]:
    """Run n episodes of agent0 vs agent1, scoring agent0's performance."""
    return score_episodes(run_episodes(agent0, agent1, n, env))
