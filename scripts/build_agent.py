import ast
from pathlib import Path


PACKAGE = "kaggriculture_bot"
SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
AGENT_DIR = Path(__file__).resolve().parent.parent / "agent" 
STRATEGY = "kaggriculture_bot.strategies.baseline:wheat_loop_agent"
MAIN_HEADER = """Submission entrypoint. Must define `agent(obs)` -> action dict.

GENERATED FILE -- do not edit by hand. Edit the strategy in
src/kaggriculture_bot/strategies/ and re-run the generator.

This is the "production" pipeline: only strategies that graduated from
notebooks/ + evaluate.py (see RESOURCES.md, PROGRESS.md) get wired in here.
Packaged and submitted via `kaggle competitions submit kaggriculture -f ...`
(see AGENTS.md). No network/file I/O here at inference time — see
docs/RULES_SUMMARY.md (No Ingress or Egress).
"""

def _module_to_path(module_name, src_root):
    if not module_name.startswith(PACKAGE + "."):
        raise ValueError(f"not an internal module: {module_name!r}")
    module_name_path = module_name.replace(".", "/") + ".py"
    module_source = (src_root / module_name_path)
    return module_source

def _function_source(source, func_name):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.splitlines(keepends=True)
            return "".join(lines[node.lineno - 1 : node.end_lineno])
    raise ValueError(f"function {func_name!r} not found")


def _internal_import_nodes(tree):
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith(PACKAGE + ".")
        ):
            yield node


def _rewrite_internal_imports(source):
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
    rewritten = _rewrite_internal_imports(source)
    tree = ast.parse(source)
    lines = rewritten.splitlines(keepends=True)
    chunks = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            chunks.append("".join(lines[node.lineno - 1 : node.end_lineno]))
    return "".join(chunks)
