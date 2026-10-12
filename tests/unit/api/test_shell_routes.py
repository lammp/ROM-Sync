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

    def reveal(self, path: Path) -> None:
        self.revealed.append(path)

    def pick_folder(self, title: str) -> Path | None:
        return self.picks.pop(0)

    def open_url(self, url: str) -> None:
        self.opened.append(url)


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
        {"root": "store", "path": "nes/../../.."},
    ):
        refused = c.post(f"{PREFIX}/shell/reveal", json=body)
        assert refused.status_code == 422, body
    unset = c.post(f"{PREFIX}/shell/reveal", json={"root": "firmware"})
    assert unset.json()["error"]["code"] == "config.missing"
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
    ):
        refused = c.post(f"{PREFIX}/shell/{path}", json=body)
        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "shell.unavailable"
    assert shell.revealed == [] and shell.opened == []
    assert c.get(f"{PREFIX}/session").json()["capabilities"] == []


def test_a_browser_on_loopback_is_offered_every_action(tmp_path: Path) -> None:
    c, _ = setup(tmp_path)
    got = c.get(f"{PREFIX}/session").json()
    assert got["kind"] == "browser"
    assert got["capabilities"] == ["reveal", "pick_folder", "open_url"]
