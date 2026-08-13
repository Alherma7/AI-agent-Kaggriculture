import ast
from pathlib import Path


PACKAGE = "kaggriculture_bot"
SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
AGENT_DIR = Path(__file__).resolve().parent.parent / "agent" 
STRATEGY = "kaggriculture_bot.strategies.baseline:wheat_loop_agent"
MAIN_HEADER = '''"""Submission entrypoint. Must define `agent(obs)` -> action dict.

GENERATED FILE -- do not edit by hand. Edit the strategy in
src/kaggriculture_bot/strategies/ and re-run the generator.

This is the "production" pipeline: only strategies that graduated from
notebooks/ + evaluate.py (see RESOURCES.md, PROGRESS.md) get wired in here.
Packaged and submitted via `kaggle competitions submit kaggriculture -f ...`
(see AGENTS.md). No network/file I/O here at inference time -- see
docs/RULES_SUMMARY.md (No Ingress or Egress).
"""'''

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


def _flat_name(module_name):
    return module_name.rsplit(".", 1)[-1] + ".py"


def _collect_internal_modules(module_name, src_root, collected):
    if module_name in collected:
        return
    source = _module_to_path(module_name, src_root).read_text(encoding="utf-8")
    collected[module_name] = _rewrite_internal_imports(source)
    tree = ast.parse(source)
    for node in _internal_import_nodes(tree):
        _collect_internal_modules(node.module, src_root, collected)


def generate_files(strategy_path, src_root=SRC_ROOT):
    module_name, func_name = strategy_path.split(":")
    module_source = _module_to_path(module_name, src_root).read_text(encoding="utf-8")
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
        (AGENT_DIR / name).write_text(content, encoding="utf-8")
        print(f"wrote agent/{name}")


if __name__ == "__main__":
    main()
