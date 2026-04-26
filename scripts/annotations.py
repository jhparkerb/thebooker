"""Type annotation coverage — per file and overall. Excludes test files."""

import ast
import pathlib
import sys

files = sorted(pathlib.Path(".").rglob("*.py"))
files = [f for f in files if "__pycache__" not in str(f)
         and not f.name.startswith("test_")]

total_params = total_annotated = total_returns = total_fns = 0

print(f"{'File':<45} {'Params':>8} {'Returns':>8} {'Overall':>8}")
print("-" * 75)

for f in files:
    try:
        tree = ast.parse(f.read_text())
    except SyntaxError:
        continue

    params = annotated = returns = fns = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fns += 1
        args = node.args
        all_args = args.args + args.posonlyargs + args.kwonlyargs
        if args.vararg:  all_args.append(args.vararg)
        if args.kwarg:   all_args.append(args.kwarg)
        # skip 'self' / 'cls'
        all_args = [a for a in all_args if a.arg not in ("self", "cls")]
        params    += len(all_args)
        annotated += sum(1 for a in all_args if a.annotation)
        returns   += 1 if node.returns else 0

    if fns == 0:
        continue

    param_pct  = 100 * annotated / params if params else 100.0
    return_pct = 100 * returns   / fns
    overall    = 100 * (annotated + returns) / (params + fns) if (params + fns) else 100.0
    print(f"{str(f):<45} {param_pct:>7.0f}%  {return_pct:>7.0f}%  {overall:>7.0f}%")

    total_params    += params
    total_annotated += annotated
    total_returns   += returns
    total_fns       += fns

print("-" * 75)
op = 100 * total_annotated / total_params if total_params else 100.0
or_ = 100 * total_returns / total_fns if total_fns else 100.0
ov = 100 * (total_annotated + total_returns) / (total_params + total_fns) if (total_params + total_fns) else 100.0
print(f"{'TOTAL':<45} {op:>7.0f}%  {or_:>7.0f}%  {ov:>7.0f}%")
