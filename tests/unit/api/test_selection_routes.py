"""Selection through the domain (F10-S11)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.dest_fake import FakeDest
from romsync_api.app import PREFIX
from romsync_api.models import GamesChanged, SelectionView
from tests.unit.api import seed
from tests.unit.api.test_device_routes import Probe, client


def profiled(tmp_path: Path) -> tuple[TestClient, str, dict[str, int]]:
    c = client(tmp_path, Probe(FakeDest("thor")))
    ids = seed.library(tmp_path / "data")
    ref = c.get(f"{PREFIX}/devices").json()["devices"][0]["ref"]
    device_id = c.post(f"{PREFIX}/devices/{ref}/profile", json={"name": "Thor"}).json()["id"]
    return c, device_id, ids


def test_modes_and_overrides_through_the_algebra(tmp_path: Path) -> None:
    c, device, ids = profiled(tmp_path)
    url = f"{PREFIX}/profiles/{device}/selection"
    assert SelectionView.model_validate(c.get(url).json()).modes == {}
    mode = SelectionView.model_validate(
        c.post(f"{url}/mode", json={"system": "nes", "mode": "all"}).json()
    )
    assert mode.modes == {"nes": "all"}
    excluded = GamesChanged.model_validate(
        c.post(f"{url}/games", json={"game_ids": [ids["contra"]], "include": False}).json()
    )
    assert excluded.changed == 1
    assert excluded.selection.overrides == {str(ids["contra"]): False}
    agreeing = GamesChanged.model_validate(
        c.post(f"{url}/games", json={"game_ids": [ids["contra"]], "include": True}).json()
    )
    assert agreeing.selection.overrides == {}, (
        "an override that agrees with the mode is not stored"
    )
    c.post(f"{url}/games", json={"game_ids": [ids["contra"]], "include": False})
    whole = SelectionView.model_validate(
        c.post(f"{url}/mode", json={"system": "nes", "mode": "none"}).json()
    )
    assert whole.overrides == {}, "a whole-system choice clears that system's overrides"
    c.post(f"{url}/mode", json={"system": "ps2", "mode": "off"})
    cleared = SelectionView.model_validate(c.post(f"{url}/clear").json())
    assert cleared.modes == {"nes": "none", "ps2": "off"}


def test_refusals(tmp_path: Path) -> None:
    c, device, _ = profiled(tmp_path)
    url = f"{PREFIX}/profiles/{device}/selection"
    assert c.post(f"{url}/mode", json={"system": "nes", "mode": "most"}).status_code == 422
    bad_system = c.post(f"{url}/mode", json={"system": "../nes", "mode": "all"})
    assert bad_system.json()["error"]["code"] == "path.not_a_name"
    missing_game = c.post(f"{url}/games", json={"game_ids": [999], "include": True})
    assert missing_game.status_code == 404
    unknown = c.get(f"{PREFIX}/profiles/nobody/selection")
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "profile.not_found"
