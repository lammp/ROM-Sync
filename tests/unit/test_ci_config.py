"""Continuous integration adds nothing the local gate does not do.

If CI can fail where a clean local run passed, the gate is wrong, and that is
the defect to fix rather than a difference to live with.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _text(name: str) -> str:
    path = WORKFLOWS / name
    assert path.exists(), f"{name} is missing"
    return path.read_text(encoding="utf-8")


def test_gate_workflow_exists() -> None:
    assert _text("gate.yml")


def test_gate_is_the_only_entrypoint() -> None:
    """One step that matters: the gate. No reimplementation of its stages."""
    text = _text("gate.yml")
    assert "tools/verify.py" in text
    for tool in ("ruff check", "mypy ", "pytest tests", "vitest run"):
        assert tool not in text, (
            f"the workflow runs {tool!r} itself, so CI can diverge from the gate"
        )


def test_gate_runs_on_windows() -> None:
    """The application is Windows only, and so are the path rules it enforces."""
    assert "windows-" in _text("gate.yml")


def test_gate_runs_on_pull_requests_to_the_v2_branch() -> None:
    text = _text("gate.yml")
    assert "pull_request" in text
    assert "v2" in text


def test_no_secret_reaches_the_gate() -> None:
    """A workflow that needs a credential to pass is testing the network."""
    assert "secrets." not in _text("gate.yml")


def test_nightly_workflow_randomises_the_test_order() -> None:
    """Order dependence is found by the nightly, not by a developer."""
    text = _text("nightly.yml")
    assert "schedule" in text
    assert "-p randomly" in text or "--randomly-seed" in text


@pytest.mark.parametrize("name", ["gate.yml", "nightly.yml"])
def test_workflows_pin_their_actions(name: str) -> None:
    """An unpinned action is a dependency that can change under us."""
    for line in _text(name).splitlines():
        stripped = line.strip()
        if stripped.startswith("- uses:"):
            assert "@" in stripped, f"{name}: {stripped} is not pinned"
