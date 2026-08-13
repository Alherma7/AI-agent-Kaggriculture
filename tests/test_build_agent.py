"""Unit tests for scripts/build_agent.py's plumbing (path resolution,
source extraction, import rewriting) -- not agent quality; that's what
evaluate.py's harness is for.
"""
from pathlib import Path

import pytest

from build_agent import _function_source, _module_to_path


def test_module_to_path_resolves_dotted_module():
    src_root = Path("/repo/src")
    result = _module_to_path("kaggriculture_bot.strategies.baseline", src_root)
    assert result == src_root / "kaggriculture_bot" / "strategies" / "baseline.py"


def test_module_to_path_resolves_top_level_module():
    src_root = Path("/repo/src")
    result = _module_to_path("kaggriculture_bot.config", src_root)
    assert result == src_root / "kaggriculture_bot" / "config.py"


def test_module_to_path_rejects_non_internal_module():
    with pytest.raises(ValueError, match="not an internal module"):
        _module_to_path("kaggle_environments.envs.kaggriculture", Path("/repo/src"))


def test_function_source_extracts_exact_function_text():
    source = (
        "CONST = 1\n"
        "\n"
        "\n"
        "def wheat_loop_agent(obs):\n"
        "    return obs\n"
        "\n"
        "\n"
        "def other(obs):\n"
        "    return None\n"
    )
    result = _function_source(source, "wheat_loop_agent")
    assert result == "def wheat_loop_agent(obs):\n    return obs\n"


def test_function_source_raises_if_not_found():
    with pytest.raises(ValueError, match="not found"):
        _function_source("def other(obs):\n    return None\n", "wheat_loop_agent")
