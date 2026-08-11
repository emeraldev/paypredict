"""Tests for the destructive-migration guard enforcement script.

The script is what actually prevents a future migration from
shipping an unguarded `op.drop_column`; without tests on the script
itself, a bug in the checker silently disables the enforcement.

Each test writes a tiny synthetic migration into a temp
`versions/` directory and points the checker at it, so we can
exercise every branch (guarded, unguarded, override present,
override missing, non-destructive) in isolation from real project
migrations.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_migration_guards.py"


def _run(tmp_versions: Path) -> subprocess.CompletedProcess:
    """Run the checker against a temporary `versions/` layout.

    The script auto-discovers `_API_ROOT/alembic/versions/` relative
    to its own location, so we spawn it as a subprocess with a
    monkeypatched module path. Simpler: install a symlink at the
    expected location. Even simpler: patch the module-level constant
    at import time by importing the module and rewriting the path.
    """
    # Simplest reliable path: import the module in-process, override
    # the constant, and call `main()`. subprocess/tempdir hackery is
    # more code for no gain.
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_migration_guards", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    original = module._VERSIONS_DIR
    module._VERSIONS_DIR = tmp_versions
    try:
        # `main()` writes to stdout/stderr and returns an int; the
        # subprocess wrapper models the same shape so the assertions
        # below stay uniform.
        import io
        from contextlib import redirect_stdout, redirect_stderr

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = module.main()
        return subprocess.CompletedProcess(
            args=[], returncode=rc, stdout=out.getvalue(), stderr=err.getvalue()
        )
    finally:
        module._VERSIONS_DIR = original


def _write(versions: Path, name: str, body: str) -> None:
    versions.mkdir(exist_ok=True, parents=True)
    (versions / name).write_text(textwrap.dedent(body).strip() + "\n")


# ---------------------------------------------------------------------------
# Baseline: a benign migration passes
# ---------------------------------------------------------------------------


def test_non_destructive_migration_passes(tmp_path: Path):
    _write(tmp_path, "aaaaa_benign.py", '''
        from alembic import op
        def upgrade() -> None:
            op.add_column("x", None)
        def downgrade() -> None:
            op.drop_column  # attribute access, not a call
    ''')
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Every destructive op shape is caught
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("op_call", [
    'op.drop_column("x", "y")',
    'op.drop_table("x")',
    'op.execute("DELETE FROM x")',
    'op.execute("TRUNCATE x")',
    'op.execute("DROP TABLE x")',
    'op.execute("ALTER TABLE x DROP COLUMN y")',
])
def test_destructive_ops_without_guard_fail(tmp_path: Path, op_call: str):
    _write(tmp_path, "aaaaa_bad.py", f'''
        from alembic import op
        def downgrade() -> None:
            {op_call}
    ''')
    result = _run(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "unguarded destructive operation" in result.stdout


# ---------------------------------------------------------------------------
# Guarded functions pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("guard_name", [
    "require_downgrade_ack",
    "require_downgrade_precondition",
])
def test_downgrade_with_guard_passes(tmp_path: Path, guard_name: str):
    _write(tmp_path, "aaaaa_ok.py", f'''
        from alembic import op
        from app.migration_guards import {guard_name}
        def downgrade() -> None:
            {guard_name}(revision="x", check=lambda b: 0, unmet_message="") \
                if "{guard_name}" == "require_downgrade_precondition" \
                else {guard_name}(revision="x", at_risk_count=lambda b: 0, description="")
            op.drop_table("x")
    ''')
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_upgrade_with_upgrade_ack_passes(tmp_path: Path):
    _write(tmp_path, "aaaaa_ok.py", '''
        from alembic import op
        from app.migration_guards import require_upgrade_ack
        def upgrade() -> None:
            require_upgrade_ack(revision="x", at_risk_count=lambda b: 0, description="")
            op.execute("DELETE FROM x")
    ''')
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout


# ---------------------------------------------------------------------------
# Override comments
# ---------------------------------------------------------------------------


def test_override_comment_with_reason_passes(tmp_path: Path):
    _write(tmp_path, "aaaaa_override.py", '''
        from alembic import op
        def downgrade() -> None:
            # migration-guard: ok — internal cleanup, no customer data
            op.drop_table("_scratch")
    ''')
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_bare_override_without_reason_fails(tmp_path: Path):
    """The reason is what makes the override reviewable. A bare `ok`
    is exactly the shape of a lazy override; reject it."""
    _write(tmp_path, "aaaaa_bare.py", '''
        from alembic import op
        def downgrade() -> None:
            # migration-guard: ok
            op.drop_table("_scratch")
    ''')
    result = _run(tmp_path)
    assert result.returncode == 1


# ---------------------------------------------------------------------------
# Deliberate non-flags
# ---------------------------------------------------------------------------


def test_drop_type_not_flagged(tmp_path: Path):
    """DROP TYPE removes an enum type, not customer data. Not our concern."""
    _write(tmp_path, "aaaaa_droptype.py", '''
        from alembic import op
        def downgrade() -> None:
            op.execute("DROP TYPE some_enum")
    ''')
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_update_statement_not_flagged(tmp_path: Path):
    """UPDATE modifies rows but doesn't destructively drop them.
    Value changes are a conscious data decision, not a class of
    accident this check is designed to prevent."""
    _write(tmp_path, "aaaaa_update.py", '''
        from alembic import op
        def downgrade() -> None:
            op.execute("UPDATE tenants SET is_active = false")
    ''')
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_string_containing_drop_in_comment_not_flagged(tmp_path: Path):
    """Comments and docstrings can mention `DROP TABLE` without
    triggering the check. AST-based scanning prevents regex
    false-positives on documentation."""
    _write(tmp_path, "aaaaa_comment.py", '''
        """This migration explains DROP TABLE without doing one."""
        from alembic import op
        def downgrade() -> None:
            # We used to DROP TABLE here but no longer.
            op.add_column("x", None)
    ''')
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout


# ---------------------------------------------------------------------------
# Real project passes at the current point in history
# ---------------------------------------------------------------------------


def test_project_migrations_pass():
    """The real `alembic/versions/` directory — all guards and overrides
    in place — must pass. Regression barrier: if someone adds an
    unguarded migration or removes a guard, this test breaks."""
    result = _run(Path(__file__).resolve().parent.parent / "alembic" / "versions")
    assert result.returncode == 0, result.stdout + result.stderr
