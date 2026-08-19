"""Unit tests for scripts/build_agent.py's plumbing (path resolution,
source extraction, import rewriting) -- not agent quality; that's what
evaluate.py's harness is for.
"""
from pathlib import Path

import pytest

from build_agent import (
    AGENT_DIR,
    STRATEGY,
    _collect_internal_modules,
    _flat_name,
    _function_source,
    _module_to_path,
    _referenced_constant_block,
    _rewrite_internal_imports,
    _top_level_constants,
    _top_level_import_block,
    generate_files,
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


def test_top_level_constants_collects_simple_module_level_assignments():
    source = (
        "A = {1: 2}\n"
        "B = 'x'\n"
        "\n"
        "def agent(obs):\n"
        "    local = 1\n"
        "    return A\n"
    )
    constants = _top_level_constants(source)
    assert constants == {"A": "A = {1: 2}\n", "B": "B = 'x'\n"}
    assert "local" not in constants  # not top-level, not collected


def test_referenced_constant_block_includes_only_names_the_function_uses():
    module_source = "A = {1: 2}\nB = {3: 4}\n"
    func_source = "def agent(obs):\n    return B\n"
    assert _referenced_constant_block(module_source, func_source) == "B = {3: 4}\n"


def test_referenced_constant_block_empty_when_function_uses_no_constants():
    module_source = "A = {1: 2}\n"
    func_source = "def agent(obs):\n    return obs\n"
    assert _referenced_constant_block(module_source, func_source) == ""


def test_referenced_constant_block_follows_transitive_references_in_declaration_order():
    # B references A; a function that only names B must still pull in A.
    module_source = "A = {1: 2}\nB = A\nC = {5: 6}\n"
    func_source = "def agent(obs):\n    return B\n"
    assert _referenced_constant_block(module_source, func_source) == "A = {1: 2}\nB = A\n"


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


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_flat_name_uses_last_component():
    assert _flat_name("kaggriculture_bot.strategies.baseline") == "baseline.py"
    assert _flat_name("kaggriculture_bot.config") == "config.py"


def test_collect_internal_modules_single_dependency(tmp_path):
    pkg = tmp_path / "kaggriculture_bot"
    _write(pkg / "config.py", "CROPS = ['WHEAT']\n")

    collected = {}
    _collect_internal_modules("kaggriculture_bot.config", tmp_path, collected)

    assert collected == {"kaggriculture_bot.config": "CROPS = ['WHEAT']\n"}


def test_collect_internal_modules_recurses_transitively(tmp_path):
    pkg = tmp_path / "kaggriculture_bot"
    _write(pkg / "a.py", "from kaggriculture_bot.b import VALUE\n")
    _write(pkg / "b.py", "VALUE = 1\n")

    collected = {}
    _collect_internal_modules("kaggriculture_bot.a", tmp_path, collected)

    assert collected == {
        "kaggriculture_bot.a": "from b import VALUE\n",
        "kaggriculture_bot.b": "VALUE = 1\n",
    }


def test_collect_internal_modules_visits_each_module_once(tmp_path):
    pkg = tmp_path / "kaggriculture_bot"
    _write(pkg / "a.py", "from kaggriculture_bot.shared import X\n")
    _write(pkg / "b.py", "from kaggriculture_bot.shared import Y\n")
    _write(pkg / "shared.py", "X = 1\nY = 2\n")

    collected = {}
    _collect_internal_modules("kaggriculture_bot.a", tmp_path, collected)
    _collect_internal_modules("kaggriculture_bot.b", tmp_path, collected)

    assert set(collected) == {
        "kaggriculture_bot.a",
        "kaggriculture_bot.b",
        "kaggriculture_bot.shared",
    }


def test_generate_files_real_baseline_has_no_dependencies():
    files = generate_files("kaggriculture_bot.strategies.baseline:wheat_loop_agent")
    assert set(files) == {"main.py"}
    assert "def agent(obs):" in files["main.py"]
    assert "GENERATED FILE" in files["main.py"]
    assert 'market.append(["BUY_SEED", "WHEAT", 1])' in files["main.py"]


def test_generate_files_copies_and_rewrites_one_dependency(tmp_path):
    pkg = tmp_path / "kaggriculture_bot" / "strategies"
    _write(
        pkg / "foo.py",
        "from kaggriculture_bot.helper import VALUE\n"
        "\n"
        "\n"
        "def foo_agent(obs):\n"
        "    return VALUE\n",
    )
    _write(tmp_path / "kaggriculture_bot" / "helper.py", "VALUE = 42\n")

    files = generate_files("kaggriculture_bot.strategies.foo:foo_agent", src_root=tmp_path)

    assert set(files) == {"main.py", "helper.py"}
    assert files["helper.py"] == "VALUE = 42\n"
    assert "from helper import VALUE" in files["main.py"]
    assert "def agent(obs):\n    return VALUE\n" in files["main.py"]


def test_generate_files_includes_referenced_module_level_constant(tmp_path):
    pkg = tmp_path / "kaggriculture_bot" / "strategies"
    _write(
        pkg / "foo.py",
        "UNUSED = {9: 9}\n"
        "TABLE = {1: 2}\n"
        "\n"
        "\n"
        "def foo_agent(obs):\n"
        "    return TABLE[1]\n",
    )

    files = generate_files("kaggriculture_bot.strategies.foo:foo_agent", src_root=tmp_path)

    assert set(files) == {"main.py"}
    assert "TABLE = {1: 2}" in files["main.py"]
    assert "UNUSED" not in files["main.py"]  # not referenced, must not leak in


def test_generate_files_real_2x2_agent_includes_its_constants():
    files = generate_files("kaggriculture_bot.strategies.baseline:wheat_loop_2x2_agent")
    assert set(files) == {"main.py"}
    assert "LOOP_ORDER_2X2 = {" in files["main.py"]
    assert "DIRECTIONS = {" in files["main.py"]
    assert "LOOP_ORDER_12" not in files["main.py"]  # not used by this agent


def test_generate_files_raises_on_flat_name_collision(tmp_path):
    strat = tmp_path / "kaggriculture_bot" / "strategies"
    _write(
        strat / "foo.py",
        "from kaggriculture_bot.a.helper import X\n"
        "from kaggriculture_bot.b.helper import Y\n"
        "\n"
        "\n"
        "def foo_agent(obs):\n"
        "    return X + Y\n",
    )
    _write(tmp_path / "kaggriculture_bot" / "a" / "helper.py", "X = 1\n")
    _write(tmp_path / "kaggriculture_bot" / "b" / "helper.py", "Y = 2\n")

    with pytest.raises(ValueError, match="collision"):
        generate_files("kaggriculture_bot.strategies.foo:foo_agent", src_root=tmp_path)


def test_agent_dir_matches_generated_output():
    """Guards against exactly the bug that motivated this script: someone
    edits src/kaggriculture_bot/strategies/ (or agent/main.py directly)
    and forgets to keep the other in sync. Run
    `python scripts/build_agent.py` and commit the result if this fails.
    """
    expected = generate_files(STRATEGY)
    actual = {
        path.name: path.read_text(encoding="utf-8")
        for path in AGENT_DIR.iterdir()
        if path.suffix == ".py"
    }
    assert actual == expected
