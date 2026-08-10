"""Unit tests for kaggriculture_bot.evaluate's scoring/aggregation logic
(win-rate and average-money computation from a list of episode results) —
not model/agent quality, that's what evaluate.py's harness itself is for.
"""

from kaggriculture_bot.evaluate import score_episodes


def test_score_episodes_all_wins():
    result = score_episodes([(100, 50), (200, 10)])
    assert result == {"win_rate": 1.0, "avg_money": 150.0}


def test_score_episodes_all_losses():
    result = score_episodes([(10, 100), (0, 5)])
    assert result == {"win_rate": 0.0, "avg_money": 5.0}


def test_score_episodes_counts_tie_as_half_win():
    result = score_episodes([(100, 50), (200, 10), (50, 50)])
    assert result == {
        "win_rate": 0.8333333333333334,
        "avg_money": 116.66666666666667,
    }


def test_score_episodes_single_episode():
    result = score_episodes([(3000, 0)])
    assert result == {"win_rate": 1.0, "avg_money": 3000.0}
