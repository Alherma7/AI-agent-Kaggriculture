# build_agent.py Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note for this project specifically:** the project owner has asked to
> write this code themselves (mentor-not-implementer). Treat this plan as a
> guide for a human to follow task-by-task, not as authorization for an
> agent to execute it unattended.

**Goal:** Replace the hand-maintained duplicate of `wheat_loop_agent` in
`agent/main.py` with a generated file, produced by `scripts/build_agent.py`
from the graduated strategy in `src/kaggriculture_bot/strategies/`.

**Architecture:** A pure function `generate_files(strategy_path, src_root)`
statically parses (via `ast`, never executes) the strategy module's source,
extracts the target function's exact text, and recursively collects any
`kaggriculture_bot.*` modules it imports — rewriting those import lines to
their flat form and returning each as a `{filename: content}` entry. A thin
`main()` writes that dict to `agent/`. A sync-check test guards against the
generated files drifting from what's actually committed.

**Tech Stack:** Python stdlib only (`ast`, `pathlib`) — no new dependencies.

## Global Constraints

- Static analysis only — the strategy module's source is **never executed**
  during generation (parsed with `ast`, not imported/`exec`'d). This keeps
  the build script safe to run on untrusted-ish strategy code and makes
  tests fully hermetic (no need for a fixture module's imports to actually
  resolve).
- `agent/main.py` becomes a generated artifact from this point forward —
  never hand-edited again. Real changes go in
  `src/kaggriculture_bot/strategies/` (+ `STRATEGY` in
  `scripts/build_agent.py` if the active strategy itself changes), then
  `python scripts/build_agent.py` regenerates `agent/`.
- Follows `docs/superpowers/specs/2026-08-12-build-agent-script-design.md`.
  One deviation from that spec, decided during planning: function
  extraction uses static `ast` parsing instead of
  `inspect.getsource`-after-`exec`, for the safety/testability reasons
  above. Everything else in the spec (constant-based strategy selection,
  flat-sibling-file copying, recursive import resolution, sync-check test)
  is unchanged.

---

## Task 1: Path resolution + function extraction

**Files:**
- Create: `scripts/build_agent.py`
- Modify: `pytest.ini` (add `scripts` to `pythonpath` so tests can `import
  build_agent`)
- Test: `tests/test_build_agent.py`

**Interfaces:**
- Produces: `_module_to_path(module_name: str, src_root: Path) -> Path`,
  `_function_source(source: str, func_name: str) -> str`, module-level
  constants `PACKAGE = "kaggriculture_bot"`, `SRC_ROOT`, `AGENT_DIR`,
  `STRATEGY`, `MAIN_HEADER`.

- [ ] **Step 1: Add `scripts` to pytest's import path**

Edit `pytest.ini`:

```ini
[pytest]
pythonpath = src scripts
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_build_agent.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_build_agent.py -v`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'build_agent'`
(the module doesn't exist yet).

- [ ] **Step 4: Write the minimal implementation**

Create `scripts/build_agent.py`:

```python
"""Generates agent/main.py (and flat sibling files for any internal
kaggriculture_bot imports) from the graduated strategy function in
src/kaggriculture_bot/strategies/. agent/main.py is a build artifact --
never edit it by hand. To change the active strategy or pick up changes
made in src/, update STRATEGY below if needed and run:

    python scripts/build_agent.py

See docs/superpowers/specs/2026-08-12-build-agent-script-design.md.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
AGENT_DIR = REPO_ROOT / "agent"
PACKAGE = "kaggriculture_bot"

STRATEGY = "kaggriculture_bot.strategies.baseline:wheat_loop_agent"

MAIN_HEADER = '''"""Submission entrypoint. Must define `agent(obs)` -> action dict.

GENERATED FILE -- do not edit by hand. Edit the strategy in
src/kaggriculture_bot/strategies/ and, if needed, the STRATEGY constant in
scripts/build_agent.py, then re-run: python scripts/build_agent.py

This is the "production" pipeline: only strategies that graduated from
notebooks/ + evaluate.py (see RESOURCES.md, PROGRESS.md) get wired in here.
Packaged and submitted via `kaggle competitions submit kaggriculture -f ...`
(see AGENTS.md). No network/file I/O here at inference time -- see
docs/RULES_SUMMARY.md (No Ingress or Egress).
"""'''


def _module_to_path(module_name, src_root):
    if not module_name.startswith(PACKAGE + "."):
        raise ValueError(f"not an internal module: {module_name!r}")
    relative = module_name[len(PACKAGE) + 1 :].replace(".", "/")
    return src_root / PACKAGE / f"{relative}.py"


def _function_source(source, func_name):
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.splitlines(keepends=True)
            return "".join(lines[node.lineno - 1 : node.end_lineno])
    raise ValueError(f"function {func_name!r} not found")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_build_agent.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add pytest.ini scripts/build_agent.py tests/test_build_agent.py
git commit -m "Add build_agent.py path resolution + function extraction"
```

---

## Task 2: Import rewriting

**Files:**
- Modify: `scripts/build_agent.py`
- Test: `tests/test_build_agent.py`

**Interfaces:**
- Consumes: `PACKAGE` constant from Task 1.
- Produces: `_internal_import_nodes(tree: ast.Module) -> Iterator[ast.ImportFrom]`,
  `_rewrite_internal_imports(source: str) -> str`,
  `_top_level_import_block(source: str) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_agent.py`:

```python
from build_agent import (
    _rewrite_internal_imports,
    _top_level_import_block,
)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_build_agent.py -v`
Expected: FAIL — `ImportError: cannot import name '_rewrite_internal_imports'`

- [ ] **Step 3: Write the minimal implementation**

Add to `scripts/build_agent.py` (below `_function_source`):

```python
def _internal_import_nodes(tree):
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith(PACKAGE + ".")
        ):
            yield node


def _rewrite_internal_imports(source):
    """Rewrite `from kaggriculture_bot.x import y` lines to the flat
    `from x import y` form. Every other line (including external,
    possibly multi-line imports) is left untouched. Raises if an internal
    import itself spans multiple lines (not supported -- none exist in
    this repo today).
    """
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    for node in _internal_import_nodes(tree):
        if node.lineno != node.end_lineno:
            raise ValueError(
                f"multi-line internal import not supported: {node.module}"
            )
        flat_module = node.module.rsplit(".", 1)[-1]
        lines[node.lineno - 1] = lines[node.lineno - 1].replace(
            f"from {node.module} import", f"from {flat_module} import"
        )
    return "".join(lines)


def _top_level_import_block(source):
    """Exact source text (already flat-rewritten) of every top-level
    import statement in source, in original order. Rewriting only ever
    replaces text within a line, so line numbers from the original parse
    still line up with the rewritten text.
    """
    rewritten = _rewrite_internal_imports(source)
    tree = ast.parse(source)
    lines = rewritten.splitlines(keepends=True)
    chunks = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            chunks.append("".join(lines[node.lineno - 1 : node.end_lineno]))
    return "".join(chunks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_build_agent.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/build_agent.py tests/test_build_agent.py
git commit -m "Add internal-import rewriting to build_agent.py"
```

---

## Task 3: Recursive dependency collection

**Files:**
- Modify: `scripts/build_agent.py`
- Test: `tests/test_build_agent.py`

**Interfaces:**
- Consumes: `_module_to_path`, `_rewrite_internal_imports`,
  `_internal_import_nodes` from Tasks 1-2.
- Produces: `_flat_name(module_name: str) -> str`,
  `_collect_internal_modules(module_name: str, src_root: Path, collected: dict[str, str]) -> None`
  (mutates `collected` in place).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_agent.py`:

```python
from build_agent import _collect_internal_modules, _flat_name


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_build_agent.py -v`
Expected: FAIL — `ImportError: cannot import name '_collect_internal_modules'`

- [ ] **Step 3: Write the minimal implementation**

Add to `scripts/build_agent.py`:

```python
def _flat_name(module_name):
    return module_name.rsplit(".", 1)[-1] + ".py"


def _collect_internal_modules(module_name, src_root, collected):
    """Recursively fill collected[module_name] = flat-rewritten source,
    for module_name and every kaggriculture_bot.* module it imports,
    directly or transitively. Idempotent -- already-collected modules are
    skipped.
    """
    if module_name in collected:
        return
    source = _module_to_path(module_name, src_root).read_text()
    collected[module_name] = _rewrite_internal_imports(source)
    tree = ast.parse(source)
    for node in _internal_import_nodes(tree):
        _collect_internal_modules(node.module, src_root, collected)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_build_agent.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/build_agent.py tests/test_build_agent.py
git commit -m "Add recursive internal-dependency collection to build_agent.py"
```

---

## Task 4: `generate_files` + CLI, regenerate `agent/main.py`

**Files:**
- Modify: `scripts/build_agent.py`
- Modify: `agent/main.py` (regenerated, no longer hand-edited — this is
  the last hand-touch it ever gets)
- Test: `tests/test_build_agent.py`

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: `generate_files(strategy_path: str, src_root: Path = SRC_ROOT) -> dict[str, str]`,
  `main() -> None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_agent.py`:

```python
from build_agent import generate_files


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_build_agent.py -v`
Expected: FAIL — `ImportError: cannot import name 'generate_files'`

- [ ] **Step 3: Write the minimal implementation**

Add to `scripts/build_agent.py`:

```python
def generate_files(strategy_path, src_root=SRC_ROOT):
    """Build agent/main.py (+ any flat sibling modules) from a
    "module.path:function_name" strategy reference. Returns
    {relative_filename: file_content}. Pure -- reads src_root, never
    touches agent/.
    """
    module_name, func_name = strategy_path.split(":")
    module_source = _module_to_path(module_name, src_root).read_text()
    func_source = _function_source(module_source, func_name)
    func_source = func_source.replace(f"def {func_name}(", "def agent(", 1)

    deps = {}
    tree = ast.parse(module_source)
    for node in _internal_import_nodes(tree):
        _collect_internal_modules(node.module, src_root, deps)

    flat_names = [_flat_name(name) for name in deps]
    if len(flat_names) != len(set(flat_names)):
        raise ValueError("flat filename collision among internal dependencies")

    import_block = _top_level_import_block(module_source)
    main_body = MAIN_HEADER + "\n\n\n"
    if import_block:
        main_body += import_block + "\n\n"
    main_body += func_source

    files = {"main.py": main_body}
    for dep_name, source in deps.items():
        files[_flat_name(dep_name)] = source
    return files


def main():
    files = generate_files(STRATEGY)
    AGENT_DIR.mkdir(exist_ok=True)
    for name, content in files.items():
        (AGENT_DIR / name).write_text(content)
        print(f"wrote agent/{name}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_build_agent.py -v`
Expected: 17 passed

- [ ] **Step 5: Regenerate `agent/main.py` and review the diff**

Run: `python scripts/build_agent.py`
Then: `git diff agent/main.py`

Expected: only the docstring/header changed (now says "GENERATED FILE --
do not edit by hand" instead of the old "keep this in sync by hand"
comment); the `agent` function body is unchanged, since
`wheat_loop_agent` has no dependencies today. Read the diff to confirm
before moving on — this is the file that gets submitted to Kaggle.

- [ ] **Step 6: Run the full test suite (including `evaluate.py`'s gate) to confirm the regenerated agent still behaves identically**

Run: `pytest -q`
Expected: all passing (same count as before this task, plus the new
`test_build_agent.py` tests)

- [ ] **Step 7: Commit**

```bash
git add scripts/build_agent.py tests/test_build_agent.py agent/main.py
git commit -m "Generate agent/main.py via build_agent.py instead of hand-editing"
```

---

## Task 5: Sync-check test + docs

**Files:**
- Test: `tests/test_build_agent.py`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `generate_files`, `STRATEGY`, `AGENT_DIR` from Task 4.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_build_agent.py`:

```python
from build_agent import AGENT_DIR, STRATEGY


def test_agent_dir_matches_generated_output():
    """Guards against exactly the bug that motivated this script: someone
    edits src/kaggriculture_bot/strategies/ (or agent/main.py directly)
    and forgets to keep the other in sync. Run
    `python scripts/build_agent.py` and commit the result if this fails.
    """
    expected = generate_files(STRATEGY)
    actual = {
        path.name: path.read_text()
        for path in AGENT_DIR.iterdir()
        if path.suffix == ".py"
    }
    assert actual == expected
```

(`generate_files` is already imported earlier in this file from Task 4.)

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_build_agent.py::test_agent_dir_matches_generated_output -v`
Expected: PASS (Task 4 already regenerated and committed `agent/main.py`,
so this should be in sync from the start)

- [ ] **Step 3: Update `PROGRESS.md`**

In the Level 1 checklist, change:

```markdown
- [ ] Deduplicate `agent/main.py` vs. `strategies/baseline.py` (e.g. a
      build/packaging script that generates the flat submission file from
      the single source of truth) — deferred until actually needed again
```

to:

```markdown
- [x] Deduplicate `agent/main.py` vs. `strategies/baseline.py`: added
      `scripts/build_agent.py`, which statically extracts the active
      strategy function (and recursively copies/rewrites any internal
      `kaggriculture_bot.*` imports as flat sibling files) into `agent/`.
      `agent/main.py` is now a generated artifact, never hand-edited.
      `tests/test_build_agent.py::test_agent_dir_matches_generated_output`
      guards against drift. See
      `docs/superpowers/specs/2026-08-12-build-agent-script-design.md`.
```

Add a dated entry to the Progress log (adjust the date if you run this on
a different day) describing what shipped, mirroring the style of the
existing entries above it.

- [ ] **Step 4: Run the full suite one more time**

Run: `pytest -q`
Expected: all passing

- [ ] **Step 5: Commit**

```bash
git add tests/test_build_agent.py PROGRESS.md
git commit -m "Add build_agent.py sync-check test, update PROGRESS.md"
```
