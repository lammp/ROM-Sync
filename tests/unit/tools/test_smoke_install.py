"""The installed-application smoke run's parts (F13-S9). The run itself installs
on the Windows runner it is given, so only the installer workflow performs it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.smoke_install import (
    SmokeFailed,
    bare_environment,
    install_args,
    read_report,
    setup_program,
    uninstall_args,
    wait_for,
)


def test_setup_program(tmp_path: Path) -> None:
    with pytest.raises(SmokeFailed, match="found 0"):
        setup_program(tmp_path)
    (tmp_path / "ROM-Sync-0.1.0-setup.exe").write_bytes(b"MZ")
    (tmp_path / "ROM-Sync-0.1.0-portable.zip").write_bytes(b"PK")
    assert setup_program(tmp_path).name == "ROM-Sync-0.1.0-setup.exe"
    (tmp_path / "ROM-Sync-0.0.9-setup.exe").write_bytes(b"MZ")
    with pytest.raises(SmokeFailed, match="found 2"):
        setup_program(tmp_path)


def test_silent_per_user_install_to_the_default_folder() -> None:
    args = install_args(Path("X:/out/ROM-Sync-0.1.0-setup.exe"), Path("X:/out/install.log"))
    assert args[1:5] == ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"]
    assert args[-1].startswith("/LOG=")
    assert not any(a.startswith("/DIR=") for a in args), "the default folder is what is tested"
    assert uninstall_args(Path("X:/Apps/ROM-Sync"))[0].endswith("unins000.exe")


def test_no_python_reaches_the_application() -> None:
    env = {
        "SystemRoot": r"C:\Windows",
        "LOCALAPPDATA": r"X:\Local",
        "PATH": r"C:\hostedtoolcache\Python\3.12\x64;C:\Windows\System32",
        "PYTHONPATH": r"X:\repo\engine",
        "PYTHONHOME": r"C:\hostedtoolcache\Python\3.12\x64",
        "pythonLocation": r"C:\hostedtoolcache\Python\3.12\x64",
        "VIRTUAL_ENV": r"X:\repo\.venv",
    }
    bare = bare_environment(env)
    assert bare == {
        "SystemRoot": r"C:\Windows",
        "LOCALAPPDATA": r"X:\Local",
        "PATH": r"C:\Windows\System32;C:\Windows;C:\Windows\System32\WindowsPowerShell\v1.0",
    }
    assert "python" not in json.dumps(bare).casefold()
    with pytest.raises(SmokeFailed, match="SYSTEMROOT"):
        bare_environment({"PATH": "X:/bin"})


def test_read_report(tmp_path: Path) -> None:
    report = tmp_path / "self-test.json"
    assert read_report(report) == (False, [f"no report at {report}"])
    report.write_text(
        json.dumps(
            {
                "passed": False,
                "steps": [
                    {"name": "imports webview", "ok": True, "detail": "loaded"},
                    {"name": "carries the interface", "ok": False, "detail": "None"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert read_report(report) == (
        False,
        ["  ok   imports webview: loaded", "  FAIL carries the interface: None"],
    )


def test_wait_for() -> None:
    asked: list[int] = []
    slept: list[float] = []

    def third() -> bool:
        asked.append(1)
        return len(asked) >= 3

    assert wait_for(third, within=10, every=2, sleep=slept.append)
    assert slept == [2, 2]
    assert not wait_for(lambda: False, within=3, every=1, sleep=slept.append)
