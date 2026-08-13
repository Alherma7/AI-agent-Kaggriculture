"""Unit tests for scripts/build_agent.py's plumbing (path resolution,
source extraction, import rewriting) -- not agent quality; that's what
evaluate.py's harness is for.
"""
from pathlib import Path

import pytest

from build_agent import (
    _function_source,
    _module_to_path,
    _rewrite_internal_imports,
    _top_level_import_block,
)


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


def test_rewrite_internal_imports_flattens_internal_import():
    source = "from kaggriculture_bot.config import CROPS\n\nX = CROPS\n"
    result = _rewrite_internal_imports(source)
    assert result == "from config import CROPS\n\nX = CROPS\n"


def test_rewrite_internal_imports_leaves_external_imports_untouched():
    source = (
        "from kaggle_environments.envs.kaggriculture.kaggriculture import (\n"
        "    CROPS,\n"
        "    ANIMALS,\n"
        ")\n"
        "import random\n"
    )
    assert _rewrite_internal_imports(source) == source


def test_rewrite_internal_imports_rejects_multiline_internal_import():
    source = (
        "from kaggriculture_bot.config import (\n"
        "    CROPS,\n"
        ")\n"
    )
    with pytest.raises(ValueError, match="multi-line internal import"):
        _rewrite_internal_imports(source)


def test_top_level_import_block_collects_only_top_level_imports_in_order():
    source = (
        "import random\n"
        "from kaggriculture_bot.config import CROPS\n"
        "\n"
        "\n"
        "def agent(obs):\n"
        "    import os\n"
        "    return CROPS\n"
    )
    result = _top_level_import_block(source)
    assert result == "import random\nfrom config import CROPS\n"


def test_top_level_import_block_empty_when_no_imports():
    assert _top_level_import_block("def agent(obs):\n    return obs\n") == ""
