"""Function length report — lines per function, descending. Excludes test files."""

import ast
import pathlib
import sys

TOP_N = int(sys.argv[1]) if len(sys.argv) > 1 else 20

files = sorted(pathlib.Path(".").rglob("*.py"))
files = [f for f in files if "__pycache__" not in str(f)
         and not f.name.startswith("test_")]

rows: list[tuple[int, str, str, int]] = []
for f in files:
    try:
        tree = ast.parse(f.read_text())
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = node.end_lineno - node.lineno + 1
            rows.append((length, node.name, str(f), node.lineno))

rows.sort(reverse=True)

print(f"{'Lines':>6}  {'Function':<35} File")
print("-" * 75)
for length, name, path, lineno in rows[:TOP_N]:
    print(f"{length:>6}  {name:<35} {path}:{lineno}")
