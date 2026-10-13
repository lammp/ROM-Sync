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


@pytest.mark.parametrize("name", ["gate.yml", "nightly.yml", "release.yml"])
def test_workflows_pin_their_actions(name: str) -> None:
    """An unpinned action is a dependency that can change under us."""
    for line in _text(name).splitlines():
        stripped = line.strip()
        if stripped.startswith("- uses:"):
            assert "@" in stripped, f"{name}: {stripped} is not pinned"


def test_release_workflow() -> None:
    """A version tag produces a release with checksums (F13-S7), built only after
    the gate passes on that commit, and from nothing but the repository."""
    text = _text("release.yml")
    assert 'tags: ["v*"]' in text and "pull_request" not in text, "tags only"
    assert "windows-" in text
    order = [
        "python tools/verify.py",
        "npm run bundle --prefix ui",
        "python tools/installer.py build",
        "python tools/installer.py installer",
        "python tools/installer.py package",
        "python tools/smoke_install.py",
        "gh release create",
    ]
    places = [text.index(step) for step in order]
    assert places == sorted(places), (
        "gate, interface, freeze, installer, sums, the installer proved, release"
    )
    assert "path: reports/release/artefacts/" in text and "artefacts/*" in text, (
        "every artefact, the sums among them"
    )
    assert "--generate-notes" in text and "--verify-tag" in text
    assert "secrets." not in text, "the run's own token, nothing stored"


def test_release_token_reaches_only_the_publishing_job() -> None:
    """Every step that runs third-party code has a read-only token not kept in
    the checkout; only the publishing job may write, and it installs nothing
    (F16-S5). The tag reaches a script only as a variable."""
    text = _text("release.yml")
    build, publish = text.split("\n  publish:", 1)
    assert "permissions:\n  contents: read" in text
    assert "contents: write" not in build and "persist-credentials: false" in build
    assert "contents: write" in publish
    for installing in ("checkout", "pip install", "npm ci", "choco"):
        assert installing not in publish, installing
    assert "${{ github.ref_name }}" in text
    for line in text.splitlines():
        if "${{ github.ref_name }}" in line:
            assert line.strip() == "TAG: ${{ github.ref_name }}", line


def test_installer_workflow() -> None:
    """Every push to v2 builds the installer and proves it installed (F13-S9), with
    no tag and nothing published: the installer is kept as the run's artefact."""
    text = _text("installer.yml")
    assert "branches: [v2]" in text and "workflow_dispatch" in text
    assert "tags:" not in text and "gh release" not in text, "nothing published"
    assert "windows-" in text
    order = [
        "npm run bundle --prefix ui",
        "python tools/installer.py build",
        "choco install innosetup",
        "python tools/installer.py installer",
        "python tools/installer.py package",
        "python tools/smoke_install.py",
        "actions/upload-artifact",
    ]
    places = [text.index(step) for step in order]
    assert places == sorted(places), "interface, freeze, compile, sums, proved, kept"
    assert "path: reports/release/artefacts/" in text
    assert "retention-days: 14" in text
    assert "secrets." not in text


def test_only_the_release_may_write() -> None:
    for name in ("gate.yml", "nightly.yml", "installer.yml"):
        assert "contents: write" not in _text(name)


def test_a_hung_test_fails_with_its_tracebacks() -> None:
    """A hang must fail the gate where it happens, not run the CI job out of time."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "faulthandler_timeout = 300" in text
    assert "faulthandler_exit_on_timeout = true" in text
