"""Library, game, systems and settings reads (F10-S7)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.compose import build
from romsync_api.app import PREFIX, create_app
from romsync_api.models import GameDetail, Library, SettingsList, Systems
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE


def client(tmp_path: Path) -> tuple[TestClient, dict[str, int]]:
    data = tmp_path / "data"
    engine = build(data, clock=FrozenClock())
    ids = seed.library(data)
    return TestClient(create_app(engine), base_url=BASE), ids


def test_library(tmp_path: Path) -> None:
    c, ids = client(tmp_path)
    body = Library.model_validate(c.get(f"{PREFIX}/library").json())
    games = {g.id: g for g in body.games}
    contra = games[ids["contra"]]
    assert (contra.system, contra.title, contra.region, contra.year) == (
        "nes",
        "Contra",
        "USA",
        1987,
    )
    assert contra.matched and contra.votes == 320 and contra.genres == ["Shooter", "Platform"]
    assert contra.tags == {"franchise": ["Contra"], "user": ["co-op"]}, (
        "a proposal is not a tag yet"
    )
    okami = games[ids["okami"]]
    assert (okami.kind, okami.files, okami.matched, okami.state, okami.year) == (
        "folder",
        2,
        False,
        "pending",
        None,
    )


def test_game(tmp_path: Path) -> None:
    c, ids = client(tmp_path)
    detail = GameDetail.model_validate(c.get(f"{PREFIX}/games/{ids['okami']}").json())
    assert [(m.name, m.size) for m in detail.members] == [
        ("disc1.iso", 100),
        ("disc2.iso", 200),
    ]
    assert GameDetail.model_validate(
        c.get(f"{PREFIX}/games/{ids['contra']}").json()
    ).summary == ("Run and gun.")
    missing = c.get(f"{PREFIX}/games/999")
    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "game.not_found",
        "message": "no game 999",
        "field": "game_id",
    }
    assert c.get(f"{PREFIX}/games/abc").status_code == 422


def test_systems(tmp_path: Path) -> None:
    c, _ = client(tmp_path)
    body = Systems.model_validate(c.get(f"{PREFIX}/systems").json())
    assert [(s.key, s.games, s.bytes, s.extensions) for s in body.systems] == [
        ("nes", 1, 131_088, [".nes", ".zip"]),
        ("ps2", 1, 300, [".iso"]),
    ]


def test_settings(tmp_path: Path) -> None:
    c, _ = client(tmp_path)
    body = SettingsList.model_validate(c.get(f"{PREFIX}/settings").json())
    items = {s.key: s for s in body.settings}
    assert items["log.level"].choices and items["log.level"].stored is False
    secret = items["igdb.client_secret"]
    assert secret.secret and secret.value is None and secret.default is None
    assert secret.secret_state is not None and secret.secret_state.present is False
    margin = items["plan.free_space_margin"]
    assert margin.value == margin.default


def test_a_recorded_cover_is_served(tmp_path: Path) -> None:
    c, _ = client(tmp_path)
    covers = tmp_path / "data" / "covers"
    covers.mkdir(parents=True, exist_ok=True)
    (covers / "1234.jpg").write_bytes(b"\xff\xd8jpeg")
    got = c.get(f"{PREFIX}/covers/1234.jpg")
    assert got.status_code == 200 and got.content == b"\xff\xd8jpeg"
    assert got.headers["content-type"] == "image/jpeg"
    assert got.headers["x-content-type-options"] == "nosniff"


def test_only_a_recorded_cover_is_served(tmp_path: Path) -> None:
    c, _ = client(tmp_path)
    data = tmp_path / "data"
    (data / "covers").mkdir(parents=True, exist_ok=True)
    (data / "covers" / "stray.jpg").write_bytes(b"not recorded")
    for name in ("stray.jpg", "..%2Fgames.db", "%2E%2E", "missing.jpg"):
        got = c.get(f"{PREFIX}/covers/{name}")
        assert got.status_code == 404, name
        assert got.json()["error"]["code"] in ("cover.not_found", "request.not_found"), name


def test_a_recorded_name_whose_file_is_gone_is_not_found(tmp_path: Path) -> None:
    c, _ = client(tmp_path)
    got = c.get(f"{PREFIX}/covers/1234.jpg")
    assert got.status_code == 404 and got.json()["error"]["code"] == "cover.not_found"
