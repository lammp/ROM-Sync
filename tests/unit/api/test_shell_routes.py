"""Shell endpoints: root-checked, allow-listed, loopback only (F10-S15)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync_api.app import PREFIX, create_app
from romsync_api.binding import Binding
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.unit.api.conftest import BASE


class RecordingShell:
    def __init__(self) -> None:
        self.revealed: list[Path] = []
        self.opened: list[str] = []
        self.picks: list[Path | None] = [None]
        self.notified: list[tuple[str, str]] = []

    def reveal(self, path: Path) -> None:
        self.revealed.append(path)

    def pick_folder(self, title: str) -> Path | None:
        return self.picks.pop(0)

    def open_url(self, url: str) -> None:
        self.opened.append(url)

    def notify(self, title: str, body: str) -> bool:
        self.notified.append((title, body))
        return True


def setup(tmp_path: Path, binding: Binding | None = None) -> tuple[TestClient, RecordingShell]:
    shell = RecordingShell()
    store = tmp_path / "store"
    (store / "nes").mkdir(parents=True)
    engine = build(
        tmp_path / "data", {"store.root": str(store)}, clock=FrozenClock(), shell=shell
    )
    base = "http://192.168.1.5:8765" if binding and not binding.loopback else BASE
    c = TestClient(create_app(engine, binding), base_url=base)
    c.headers.update({"Origin": base, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c, shell


def test_root_check(tmp_path: Path) -> None:
    c, shell = setup(tmp_path)
    assert c.post(f"{PREFIX}/shell/reveal", json={"root": "store"}).status_code == 200
    assert (
        c.post(f"{PREFIX}/shell/reveal", json={"root": "store", "path": "nes"}).status_code
        == 200
    )
    assert c.post(f"{PREFIX}/shell/reveal", json={"root": "data"}).status_code == 200
    assert shell.revealed == [tmp_path / "store", tmp_path / "store" / "nes", tmp_path / "data"]
    for body in (
        {"root": "store", "path": "../data"},
        {"root": "store", "path": "C:/Windows"},
        {"root": "store", "path": "/etc"},
        {"root": "home"},
        {"root": "firmware"},  # retired: system files live in the store's bios folder
        {"root": "store", "path": "nes/../../.."},
    ):
        refused = c.post(f"{PREFIX}/shell/reveal", json=body)
        assert refused.status_code == 422, body
    assert len(shell.revealed) == 3

    bare = build(tmp_path / "bare", clock=FrozenClock(), shell=shell)
    b = TestClient(create_app(bare), base_url=BASE)
    b.headers.update({"Origin": BASE, TOKEN_HEADER: b.get(f"{PREFIX}/session").json()["token"]})
    unset = b.post(f"{PREFIX}/shell/reveal", json={"root": "store"})
    assert unset.json()["error"]["code"] == "config.missing", "no store chosen yet"
    assert len(shell.revealed) == 3


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///C:/Windows/win.ini",
        "http://www.igdb.com/",
        "https://evil.example/",
        # built in pieces, so the file holds nothing shaped like an address
        "https://www.igdb.com" + "@" + "evil.example/",
        "https://user:pw" + "@" + "www.igdb.com/",
        "ms-settings:privacy",
        "",
    ],
)
def test_scheme_allowlist(tmp_path: Path, url: str) -> None:
    c, shell = setup(tmp_path)
    refused = c.post(f"{PREFIX}/shell/open", json={"url": url})
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "shell.link_refused"
    assert shell.opened == []


def test_an_allowed_link_opens(tmp_path: Path) -> None:
    c, shell = setup(tmp_path)
    assert (
        c.post(f"{PREFIX}/shell/open", json={"url": "https://api-docs.igdb.com/"}).status_code
        == 200
    )
    assert shell.opened == ["https://api-docs.igdb.com/"]


def test_pick_folder(tmp_path: Path) -> None:
    c, shell = setup(tmp_path)
    assert c.post(f"{PREFIX}/shell/pick-folder", json={"title": "Store"}).json() == {
        "path": None
    }
    shell.picks.append(tmp_path)
    assert c.post(f"{PREFIX}/shell/pick-folder", json={"title": "Store"}).json() == {
        "path": str(tmp_path)
    }


def test_off_loopback_the_shell_is_refused(tmp_path: Path) -> None:
    c, shell = setup(tmp_path, Binding("0.0.0.0", 8765))
    for path, body in (
        ("reveal", {"root": "store"}),
        ("open", {"url": "https://www.igdb.com/"}),
        ("pick-folder", {"title": "x"}),
        ("notify", {"title": "x", "body": "y"}),
    ):
        refused = c.post(f"{PREFIX}/shell/{path}", json=body)
        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "shell.unavailable"
    browsed = c.get(f"{PREFIX}/shell/folders", params={"path": str(tmp_path)})
    assert browsed.status_code == 403, "off loopback no page may read this computer's folders"
    assert shell.revealed == [] and shell.opened == [] and shell.notified == []
    assert c.get(f"{PREFIX}/session").json()["capabilities"] == []


def test_a_browser_on_loopback_is_offered_every_action(tmp_path: Path) -> None:
    c, _ = setup(tmp_path)
    got = c.get(f"{PREFIX}/session").json()
    assert got["kind"] == "browser"
    assert got["capabilities"] == [
        "reveal",
        "pick_folder",
        "browse_folders",
        "open_url",
        "notify",
    ]


def test_notify(tmp_path: Path) -> None:
    c, shell = setup(tmp_path)
    sent = c.post(f"{PREFIX}/shell/notify", json={"title": "ROM-Sync", "body": "Scan done"})
    assert sent.json() == {"delivered": True}
    assert shell.notified == [("ROM-Sync", "Scan done")]
    assert c.post(f"{PREFIX}/shell/notify", json={"title": "", "body": "x"}).status_code == 422


def test_browse_folders(tmp_path: Path) -> None:
    """Folders by name, files only of the kinds asked for, sorted as Explorer does (F11-S45)."""
    c, _ = setup(tmp_path)
    tools = tmp_path / "tools"
    (tools / "platform-tools").mkdir(parents=True)
    (tools / "Zelda").mkdir()
    (tools / ".git").mkdir()
    (tools / "adb.EXE").write_bytes(b"MZ")
    (tools / "notes.txt").write_text("x", encoding="utf-8")
    got = c.get(f"{PREFIX}/shell/folders", params={"path": str(tools)})
    assert got.status_code == 200
    assert got.json() == {
        "path": str(tools),
        "parent": str(tmp_path),
        "folders": [
            {"name": "platform-tools", "path": str(tools / "platform-tools")},
            {"name": "Zelda", "path": str(tools / "Zelda")},
        ],
        "files": [],
    }
    files = c.get(f"{PREFIX}/shell/folders", params={"path": str(tools), "files": ["exe"]})
    assert files.json()["files"] == [{"name": "adb.EXE", "path": str(tools / "adb.EXE")}]


def test_browse_starts_at_the_drives(tmp_path: Path) -> None:
    c, _ = setup(tmp_path)
    got = c.get(f"{PREFIX}/shell/folders").json()
    assert got["path"] is None and got["parent"] is None and got["files"] == []
    assert got["folders"], "at least one drive"


@pytest.mark.parametrize("path", ["relative/folder", "missing"])
def test_a_folder_that_cannot_be_listed_is_said(tmp_path: Path, path: str) -> None:
    c, _ = setup(tmp_path)
    asked = path if path != "missing" else str(tmp_path / "missing")
    got = c.get(f"{PREFIX}/shell/folders", params={"path": asked})
    assert got.status_code == 422
    error = got.json()["error"]
    assert error["code"] == "path.unreadable" and error["field"] == "path"
    assert asked in error["message"]
