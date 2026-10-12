"""The frozen build (F13-S1): the interpreter, the engine, the API and the
desktop shell with the built interface, and nothing a person keeps. What the
computer must provide, checked before the window opens (F13-S2). The
installer, which keeps the data apart from the application (F13-S3), and the
uninstaller, which leaves it (F13-S4)."""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path, PureWindowsPath

import pytest

from romsync_desktop.__main__ import default_bundle
from romsync_desktop.checks import (
    MIN_WINDOWS_BUILD,
    WEBVIEW2_BOOTSTRAPPER,
    WEBVIEW2_KEYS,
    Check,
    SystemProbe,
    checks,
    inside,
    nearest,
    preflight,
    words,
)
from tools.installer import (
    BUNDLE,
    DATA_DIR,
    INSTALL_DIR,
    INTERFACE,
    MANIFEST,
    NotBuilt,
    inno_script,
    pyinstaller_args,
)


def built(root: Path) -> Path:
    interface = root / INTERFACE[0]
    interface.mkdir(parents=True)
    (interface / MANIFEST).write_text("{}", encoding="utf-8")
    return root


def pairs(args: list[str], flag: str) -> list[str]:
    return [args[i + 1] for i, a in enumerate(args) if a == flag]


def test_bundle_contents(tmp_path: Path) -> None:
    root = built(tmp_path / "repo")
    args = pyinstaller_args(BUNDLE, root, tmp_path / "dist", tmp_path / "work", sep=";")
    assert args[0] == str(root / "desktop" / "romsync_desktop" / "__main__.py")
    assert {"--onedir", "--windowed", "--noconfirm", "--clean"} <= set(args), (
        "one folder carrying its own interpreter, with no console window"
    )
    assert pairs(args, "--name") == ["ROM-Sync"]
    assert pairs(args, "--paths") == [str(root / t) for t in ("engine", "api", "desktop")]
    assert pairs(args, "--add-data") == [f"{root / 'ui' / 'out'};ui"], (
        "the built interface is the only thing besides code"
    )
    assert {"tests", "tools", "pytest"} <= set(pairs(args, "--exclude-module"))
    assert "uvicorn.protocols.http.auto" in pairs(args, "--hidden-import")
    assert pairs(args, "--distpath") == [str(tmp_path / "dist")]


def test_an_unbuilt_interface_stops_the_build(tmp_path: Path) -> None:
    with pytest.raises(NotBuilt, match="build the interface first"):
        pyinstaller_args(BUNDLE, tmp_path, tmp_path / "dist", tmp_path / "work")


def test_the_frozen_application_finds_its_interface_inside_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inside = tmp_path / "ROM-Sync" / "_internal"
    (inside / "ui").mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(inside), raising=False)
    assert default_bundle() is None, "no manifest, no interface"
    (inside / "ui" / MANIFEST).write_text("{}", encoding="utf-8")
    assert default_bundle() == inside / "ui"


class Machine:
    """A computer stated in full: Windows build, WebView2 version, free space, access."""

    def __init__(
        self,
        build: int | None = 22631,
        runtime: str | None = "130.0.2849.80",
        free: int = 50 * 1024**3,
        writable: bool = True,
    ) -> None:
        self.build, self.runtime, self.free, self.can_write = build, runtime, free, writable
        self.judged: list[Path] = []

    def windows_build(self) -> int | None:
        return self.build

    def webview2(self) -> str | None:
        return self.runtime

    def free_bytes(self, folder: Path) -> int:
        self.judged.append(folder)
        return self.free

    def writable(self, folder: Path) -> bool:
        return self.can_write


def test_checks_reported(tmp_path: Path) -> None:
    """Each of the four is checked and said, passing or not."""
    data = tmp_path / "ROM-Sync" / "data"
    healthy = Machine()
    found = checks(healthy, data)
    assert [(c.name, c.ok) for c in found] == [
        ("Windows version", True),
        ("Embedded browser (WebView2)", True),
        ("Disk space for the data folder", True),
        ("Data folder writable", True),
    ]
    assert healthy.judged == [tmp_path], "space is judged where the data folder will be"
    said: list[Sequence[Check]] = []
    assert preflight(healthy, data, said.append) is True and said == []

    poor = Machine(build=17134, free=10 * 1024 * 1024, writable=False)
    failed = [c for c in checks(poor, data) if not c.ok]
    assert [c.name for c in failed] == [
        "Windows version",
        "Disk space for the data folder",
        "Data folder writable",
    ]
    assert failed[0].detail == f"build 17134; {MIN_WINDOWS_BUILD} or later is needed"
    assert failed[1].detail == "10 MB free" and not failed[1].blocking

    assert words([failed[1]]) == "Disk space for the data folder: 10 MB free", (
        "a warning alone does not say the start is stopped"
    )

    short = Machine(free=10 * 1024 * 1024)
    assert preflight(short, data, said.append) is True, "short of space warns, never blocks"
    assert [[c.name for c in r] for r in said] == [["Disk space for the data folder"]]


def test_missing_runtime_blocks(tmp_path: Path) -> None:
    """No WebView2: the start is refused, the reason said, and the download offered."""
    said: list[Sequence[Check]] = []
    assert preflight(Machine(runtime=None), tmp_path / "data", said.append) is False
    (missing,) = said[0]
    assert missing.blocking and missing.offer == WEBVIEW2_BOOTSTRAPPER
    assert words(said[0]) == (
        "Embedded browser (WebView2): the Microsoft Edge WebView2 runtime is missing\n"
        "ROM-Sync cannot start until this is fixed.\n"
        f"Get it from {WEBVIEW2_BOOTSTRAPPER}"
    )
    assert not checks(Machine(build=None), tmp_path)[0].ok, "off Windows is not Windows"


def test_the_system_probe_judges_space_and_access(tmp_path: Path) -> None:
    probe = SystemProbe()
    data = tmp_path / "ROM-Sync" / "data"
    assert probe.free_bytes(nearest(data)) > 0
    assert probe.writable(data) and data.is_dir()
    assert list(data.iterdir()) == [], "the access check leaves nothing behind"
    blocked = tmp_path / "file"
    blocked.write_text("x", encoding="utf-8")
    assert probe.writable(blocked / "data") is False, "a folder under a file cannot be made"


def sections(script: str) -> dict[str, list[str]]:
    """The script's sections, each a list of its lines without comments or blanks."""
    found: dict[str, list[str]] = {}
    current = ""
    for line in script.splitlines():
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            found[current] = []
        elif current and line.strip() and not line.startswith(";"):
            found[current].append(line)
    return found


def entries(lines: list[str]) -> list[dict[str, str]]:
    """An entry section's lines as name/value pairs."""
    field = re.compile(r'(\w+): ("(?:[^"]|"")*"|[^;]*)')
    return [
        {name: value[1:-1] if value.startswith('"') else value for name, value in found}
        for found in (field.findall(line) for line in lines)
    ]


def setting(lines: list[str], name: str) -> str:
    return next(line.split("=", 1)[1] for line in lines if line.startswith(f"{name}="))


def test_data_outside_install(tmp_path: Path) -> None:
    """The application has its own folder and the data another; the installer and the
    application both refuse to put one inside the other, and nothing the installer
    writes or deletes is outside the application's folder."""
    script = sections(inno_script("2.0.0", tmp_path / "dist"))
    install = PureWindowsPath(setting(script["Setup"], "DefaultDirName"))
    data = PureWindowsPath(DATA_DIR)
    assert install == PureWindowsPath(INSTALL_DIR)
    assert not data.is_relative_to(install) and not install.is_relative_to(data)
    assert setting(script["Setup"], "PrivilegesRequired") == "lowest"
    assert setting(script["Setup"], "MinVersion") == f"10.0.{MIN_WINDOWS_BUILD}"

    for written in entries(script["Files"]):
        assert written["DestDir"] == "{app}"
    for removed in entries(script["InstallDelete"]) + entries(script["UninstallDelete"]):
        assert removed["Name"].startswith("{app}"), removed
    for shortcut in entries(script["Icons"]) + entries(script["Run"]):
        assert shortcut["Filename"] == "{app}\\ROM-Sync.exe"
        assert '--data ""{code:DataDir}""' in shortcut["Parameters"], (
            "every start names the chosen data folder"
        )
    code = "\n".join(script["Code"])
    assert "Inside(DataPage.Values[0], WizardDirValue)" in code
    assert "Inside(WizardDirValue, DataPage.Values[0])" in code
    assert f"ExpandConstant('{DATA_DIR}')" in code

    # and the installed application refuses a data folder inside its own
    app = tmp_path / "Programs" / "ROM-Sync"
    said: list[Sequence[Check]] = []
    assert preflight(Machine(), app / "data", said.append, installed=app) is False
    assert [c.name for c in said[0]] == ["Data folder apart from the application"]
    assert preflight(Machine(), tmp_path / "ROM-Sync" / "data", said.append, installed=app)
    assert inside(Path("X:/Apps/ROM-Sync/data"), Path("x:/apps/rom-sync")), (
        "Windows ignores case"
    )


def test_the_installer_offers_the_runtime(tmp_path: Path) -> None:
    code = "\n".join(sections(inno_script("2.0.0", tmp_path))["Code"])
    for hive, key in WEBVIEW2_KEYS:
        assert f"HasRuntime({hive}, '{key}')" in code
    assert WEBVIEW2_BOOTSTRAPPER in code and "Result := False;" in code


def test_uninstall_keeps_data(tmp_path: Path) -> None:
    """The uninstaller removes the application only, keeps where the data is, and says so."""
    script = sections(inno_script("2.0.0", tmp_path / "dist"))
    assert entries(script["UninstallDelete"]) == [{"Type": "filesandordirs", "Name": "{app}"}]
    (recorded,) = entries(script["Registry"])
    assert recorded["ValueName"] == "DataDir" and "Flags" not in recorded, (
        "the data folder's record outlives the application, so a reinstall finds it"
    )
    code = "\n".join(script["Code"])
    for removal in ("DelTree", "DeleteFile", "RemoveDir", "RegDeleteKey", "RegDeleteValue"):
        assert removal not in code, f"the script's own code never calls {removal}"
    said = code[code.index("procedure CurUninstallStepChanged") :]
    assert "usPostUninstall" in said and "was kept in ' + Kept" in said
    assert "Kept := Recorded(ExpandConstant('" + DATA_DIR + "'))" in code
