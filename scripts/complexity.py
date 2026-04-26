"""Cyclomatic complexity report for all non-test Python files."""

import ast
import pathlib
import sys

TOP_N = int(sys.argv[1]) if len(sys.argv) > 1 else 25


def cc(path: pathlib.Path) -> list[tuple[int, str, int]]:
    tree = ast.parse(path.read_text())
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        n = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                  ast.With, ast.Assert, ast.comprehension)):
                n += 1
            elif isinstance(child, ast.BoolOp):
                n += len(child.values) - 1
        results.append((n, node.name, node.lineno))
    return results


files = sorted(pathlib.Path(".").rglob("*.py"))
files = [f for f in files if "__pycache__" not in str(f)
         and not f.name.startswith("test_")]

rows: list[tuple[int, str, str, int]] = []
for f in files:
    try:
        for n, name, lineno in cc(f):
            rows.append((n, name, str(f), lineno))
    except SyntaxError as e:
        print(f"  [skip] {f}: {e}", file=sys.stderr)

rows.sort(reverse=True)

print(f"{'CC':>4}  {'Function':<35} File")
print("-" * 75)
for n, name, path, lineno in rows[:TOP_N]:
    print(f"{n:>4}  {name:<35} {path}:{lineno}")
