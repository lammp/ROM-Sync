"""The frozen build (F13-S1): the interpreter, the engine, the API and the
desktop shell with the built interface, and nothing a person keeps. What the
computer must provide, checked before the window opens (F13-S2). The
installer, which keeps the data apart from the application (F13-S3), and the
uninstaller, which leaves it (F13-S4). No content in any of it, and no default
path to any (F13-S5)."""

from __future__ import annotations

import hashlib
import io
import re
import sys
import tokenize
import zipfile
from collections.abc import Sequence
from pathlib import Path, PureWindowsPath

import pytest

from romsync.config.registry import REGISTRY
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
    INTERFACE_TYPES,
    MANIFEST,
    ROOT,
    HoldsContent,
    NotBuilt,
    inno_script,
    iscc,
    package,
    pyinstaller_args,
    refuse_content,
    release_version,
    stray,
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
    for removed in entries(script["InstallDelete"]):
        assert removed["Name"].startswith("{app}\\"), removed
    assert setting(script["Setup"], "DisableDirPage") == "yes", (
        "the install folder is the application's own, never one the person points at"
    )
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
    # the uninstaller removes what the installer put there, from its log, and no
    # folder wholesale: a folder removed whole could hold more than the app (F16-S5)
    assert "UninstallDelete" not in script
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


def test_no_content_bundled(tmp_path: Path) -> None:
    """The interface is the only non-code file; it may hold web assets only, and no
    folder that heads for the artefact may hold a key, firmware, a game or a database."""
    assert BUNDLE.data == (INTERFACE,)
    root = built(tmp_path / "repo")
    interface = root / INTERFACE[0]
    (interface / "_next").mkdir()
    (interface / "_next" / "app.js").write_text("", encoding="utf-8")
    assert stray(interface, INTERFACE_TYPES) == []
    pyinstaller_args(BUNDLE, root, tmp_path / "dist", tmp_path / "work")

    for planted in ("prod.keys", "bios/Firmware.NCA", "Super Game.sfc", "romsync.db"):
        (interface / planted).parent.mkdir(parents=True, exist_ok=True)
        (interface / planted).write_text("", encoding="utf-8")
    (interface / "cover.png").write_text("", encoding="utf-8")
    with pytest.raises(HoldsContent, match="5 file"):
        pyinstaller_args(BUNDLE, root, tmp_path / "dist", tmp_path / "work")
    assert stray(interface) == [
        Path("Super Game.sfc"),
        Path("bios/Firmware.NCA"),
        Path("prod.keys"),
        Path("romsync.db"),
    ], "content is refused anywhere, whatever the folder's own rule"

    app = tmp_path / "dist" / "ROM-Sync"
    (app / "_internal").mkdir(parents=True)
    (app / "_internal" / "base_library.zip").write_text("", encoding="utf-8")
    refuse_content(app)
    (app / "_internal" / "title.keys").write_text("", encoding="utf-8")
    with pytest.raises(HoldsContent, match=r"title\.keys"):
        refuse_content(app)

    real = ROOT / INTERFACE[0]
    if (real / MANIFEST).is_file():  # the interface built in this checkout, when it is
        assert stray(real, INTERFACE_TYPES) == []


def test_no_content_default_paths() -> None:
    """No setting, installer default or line of source names a place content is kept."""
    for setting in REGISTRY.settings:
        if setting.kind == "path":
            assert setting.default in ("", None), setting.key
    for constant in (INSTALL_DIR, DATA_DIR):
        assert constant.startswith("{localappdata}\\"), "the person's own folders only"
    drive = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
    found = []
    for tree in ("engine", "api", "desktop", "tools"):
        for source in sorted((ROOT / tree).rglob("*.py")):
            text = source.read_text(encoding="utf-8")
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type == tokenize.STRING and drive.search(token.string):
                    found.append(f"{source.relative_to(ROOT)}:{token.start[0]}")
    assert found == [], "a drive path in the source is a default path to someone's files"


def test_release_artefacts_are_packaged_with_checksums(tmp_path: Path) -> None:
    out = tmp_path / "release"
    app = out / "dist" / "ROM-Sync"
    (app / "_internal" / "ui").mkdir(parents=True)
    (app / "ROM-Sync.exe").write_bytes(b"exe")
    (app / "_internal" / "ui" / "index.html").write_text("<html>", encoding="utf-8")
    artefacts = out / "artefacts"
    artefacts.mkdir()
    (artefacts / "ROM-Sync-0.1.0-setup.exe").write_bytes(b"setup")
    made = package(out, release_version("v0.1.0"))
    assert [p.name for p in made] == [
        "ROM-Sync-0.1.0-portable.zip",
        "ROM-Sync-0.1.0-setup.exe",
        "SHA256SUMS.txt",
    ]
    with zipfile.ZipFile(made[0]) as archive:
        assert sorted(archive.namelist()) == [
            "ROM-Sync/ROM-Sync.exe",
            "ROM-Sync/_internal/ui/index.html",
        ]
    sums = (artefacts / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    assert sums[1] == f"{hashlib.sha256(b'setup').hexdigest()}  ROM-Sync-0.1.0-setup.exe"
    assert [line.split("  ")[1] for line in sums] == [p.name for p in made[:2]]
    assert release_version("0.1.0") == "0.1.0"

    (app / "_internal" / "prod.keys").write_text("", encoding="utf-8")
    with pytest.raises(HoldsContent):
        package(out, "0.1.0")


def test_the_compiler_is_found_where_inno_setup_installs_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert iscc(lambda name: "X:/bin/iscc.exe" if name == "iscc" else None) == Path(
        "X:/bin/iscc.exe"
    )
    for base in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        monkeypatch.delenv(base, raising=False)
    assert iscc(lambda name: None) is None
    installed = tmp_path / "Program Files (x86)" / "Inno Setup 6"
    installed.mkdir(parents=True)
    (installed / "ISCC.exe").write_bytes(b"")
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "Program Files (x86)"))
    assert iscc(lambda name: None) == installed / "ISCC.exe"


@pytest.mark.parametrize(
    "tag",
    ["v2.0.0'; Remove-Item x", "v1 .0", "latest", "v1.0.0\nx", "v1.0.0\n", "", "v2.0.0-rc.1;"],
)
def test_a_release_tag_that_is_not_a_version_is_refused(tag: str) -> None:
    """The version goes into the installer's script and file name, so a tag that
    is not a plain version stops the release (F16-S5)."""
    with pytest.raises(ValueError, match="is not a release version"):
        release_version(tag)
    assert release_version("v2.0.0-rc.1") == "2.0.0-rc.1"
