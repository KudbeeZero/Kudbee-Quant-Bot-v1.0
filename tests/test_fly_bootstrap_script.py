"""Sanity checks for scripts/fly_bootstrap.sh — can't exercise it end-to-end (it
needs a real Fly.io account), so this pins the properties that matter: it parses,
it's executable, it fails closed on missing prerequisites, and it never bakes in a
literal secret value.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fly_bootstrap.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")


def test_script_exists_and_is_executable():
    assert SCRIPT.exists()
    assert SCRIPT.stat().st_mode & 0o111, "script must be executable"


def test_script_parses_cleanly():
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_script_uses_strict_mode():
    text = SCRIPT.read_text()
    assert "set -euo pipefail" in text


def test_script_never_hardcodes_a_secret_value():
    """Every credential must be generated (secrets.token_urlsafe) or sourced from
    an env var / interactive prompt — never a literal string in the script."""
    text = SCRIPT.read_text()
    for name in ("KUDBEE_API_TOKEN", "KUDBEE_SESSION_SECRET",
                 "KUDBEE_DASHBOARD_PASSWORD", "KUDBEE_GH_TOKEN"):
        # every assignment site for these names must be a variable expansion or
        # a generator call, never `NAME="literal-looking-value"`.
        for line in text.splitlines():
            if f"{name}=" in line and "secrets set" not in line and "echo" not in line:
                rhs = line.split(f"{name}=", 1)[1]
                assert rhs.startswith(("$", '"$')), (
                    f"{name} assignment looks hardcoded: {line!r}"
                )


def test_script_fails_without_flyctl(tmp_path):
    """With an empty PATH (no flyctl), the script must exit non-zero with a clear
    fix instead of proceeding or crashing obscurely."""
    bash = shutil.which("bash")
    result = subprocess.run(
        [bash, str(SCRIPT)],
        capture_output=True, text=True,
        env={"PATH": str(tmp_path)},  # empty dir: no fly/flyctl/python3/curl found
    )
    assert result.returncode != 0
    assert "flyctl not found" in result.stderr
