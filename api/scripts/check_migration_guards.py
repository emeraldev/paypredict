"""Static enforcement of the destructive-migration guard convention.

Scans every file under `alembic/versions/` and, for each `upgrade()`
and `downgrade()` function that contains a destructive operation,
requires one of:

  1. A call to `require_upgrade_ack` / `require_downgrade_ack` /
     `require_downgrade_precondition` inside the same function.
  2. An override comment `# migration-guard: ok — <reason>` on any
     line of the function body. The `— <reason>` suffix is
     mandatory; a bare `# migration-guard: ok` is rejected because
     the reason is exactly what a reviewer needs to sanity-check.

Destructive operations recognised:

  - `op.drop_column(...)`
  - `op.drop_table(...)`
  - `op.execute(<sql>)` where the SQL string (or f-string prefix)
    contains DELETE FROM / TRUNCATE / DROP TABLE / DROP COLUMN /
    ALTER TABLE ... DROP.

Deliberately NOT flagged:

  - `sa.Enum(name=...).drop(...)` — drops a type, not data.
  - `op.execute("DROP TYPE ...")` — same.
  - `op.execute("UPDATE ...")` — modifies rows but doesn't destroy
    them structurally. Anything that renames values in place is a
    conscious data change, not a class of accident this check is
    designed to prevent.
  - `op.alter_column(...)` type changes — the failure mode is
    "cast fails at runtime", which is the domain of
    `require_downgrade_precondition`. Callers who need it will
    reach for it; we don't force it here.

Exit code: 0 if every destructive function is guarded or acknowledged;
1 otherwise. Prints a list of offenders with the exact function and
what needs to be added.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


_API_ROOT = Path(__file__).resolve().parent.parent
_VERSIONS_DIR = _API_ROOT / "alembic" / "versions"

_DROP_OP_NAMES = {"drop_column", "drop_table"}
_GUARD_NAMES = {
    "require_upgrade_ack",
    "require_downgrade_ack",
    "require_downgrade_precondition",
}

_DESTRUCTIVE_SQL_RE = re.compile(
    r"\b(DELETE\s+FROM|TRUNCATE|DROP\s+TABLE|DROP\s+COLUMN|ALTER\s+TABLE\s+\S+\s+DROP)\b",
    re.IGNORECASE,
)

# Override comment. `# migration-guard: ok — <reason text>` (any dash
# character works). Bare `ok` is not enough — the reason is what makes
# the override reviewable.
_OVERRIDE_RE = re.compile(
    r"#\s*migration-guard:\s*ok\s*[-–—]\s*\S+",
    re.IGNORECASE,
)


class Finding:
    __slots__ = ("path", "function", "line", "op_summary")

    def __init__(self, path: Path, function: str, line: int, op_summary: str) -> None:
        self.path = path
        self.function = function
        self.line = line
        self.op_summary = op_summary


def _extract_sql_from_execute(call: ast.Call) -> str | None:
    """Return the SQL string arg to `op.execute(...)` if it's a literal
    (constant or `f"..."` with no interpolation on the destructive
    keyword). Returns None when the arg is a dynamic expression we
    can't statically inspect."""
    if not call.args:
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    if isinstance(arg, ast.JoinedStr):
        # f-string; concatenate the literal parts so we can grep them.
        parts = []
        for value in arg.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        return "".join(parts) if parts else None
    return None


def _is_destructive_op_call(call: ast.Call) -> str | None:
    """If `call` is a destructive op we care about, return a short
    label for the finding; otherwise return None."""
    func = call.func
    # `op.drop_column(...)` / `op.drop_table(...)`
    if (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "op"
        and func.attr in _DROP_OP_NAMES
    ):
        return f"op.{func.attr}(...)"
    # `op.execute(<sql literal>)` with a destructive keyword
    if (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "op"
        and func.attr == "execute"
    ):
        sql = _extract_sql_from_execute(call)
        if sql and _DESTRUCTIVE_SQL_RE.search(sql):
            match = _DESTRUCTIVE_SQL_RE.search(sql)
            assert match is not None
            return f"op.execute(... {match.group(0).upper()} ...)"
    return None


def _calls_in_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            calls.append(node)
    return calls


def _function_has_guard(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for call in _calls_in_function(fn):
        func = call.func
        if isinstance(func, ast.Name) and func.id in _GUARD_NAMES:
            return True
        # Handle `module.name(...)` in case someone qualifies the import.
        if isinstance(func, ast.Attribute) and func.attr in _GUARD_NAMES:
            return True
    return False


def _function_has_override_comment(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]
) -> bool:
    if not fn.body:
        return False
    start = fn.lineno - 1  # 0-indexed
    end = (fn.end_lineno or fn.lineno) - 1
    for line in source_lines[start : end + 1]:
        if _OVERRIDE_RE.search(line):
            return True
    return False


def check_file(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    source_lines = source.splitlines()

    findings: list[Finding] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in ("upgrade", "downgrade"):
            continue

        destructive_ops: list[tuple[int, str]] = []
        for call in _calls_in_function(node):
            label = _is_destructive_op_call(call)
            if label:
                destructive_ops.append((call.lineno, label))

        if not destructive_ops:
            continue
        if _function_has_guard(node):
            continue
        if _function_has_override_comment(node, source_lines):
            continue

        for lineno, label in destructive_ops:
            findings.append(Finding(path, node.name, lineno, label))

    return findings


def main() -> int:
    if not _VERSIONS_DIR.is_dir():
        print(f"ERROR: versions dir not found at {_VERSIONS_DIR}", file=sys.stderr)
        return 2

    all_findings: list[Finding] = []
    for path in sorted(_VERSIONS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            all_findings.extend(check_file(path))
        except SyntaxError as exc:
            print(f"ERROR parsing {path}: {exc}", file=sys.stderr)
            return 2

    if not all_findings:
        print(
            f"OK: every destructive migration under {_VERSIONS_DIR.name}/ is "
            "either guarded via app.migration_guards or carries an explicit "
            "override comment."
        )
        return 0

    print(
        f"FAIL: {len(all_findings)} unguarded destructive operation(s) found.\n"
        "Each destructive `upgrade()` or `downgrade()` must call one of "
        f"{sorted(_GUARD_NAMES)} OR include a comment "
        "`# migration-guard: ok — <reason>` on any line of the function body.\n"
    )
    for f in all_findings:
        try:
            rel = f.path.relative_to(_API_ROOT)
        except ValueError:
            rel = f.path  # tests may point us at a tmp dir outside the tree
        print(f"  {rel}:{f.line}  {f.function}()  {f.op_summary}")
    print(
        "\nSee app/migration_guards.py for the guard helpers, and CLAUDE.md "
        "for the convention."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
