"""Settings writes: per-field errors, null deletes, the secret never returned (F10-S8)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.compose import build
from romsync_api.app import PREFIX, create_app
from romsync_api.models import SettingsList
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.unit.api.conftest import BASE

TYPED = "zzq-s3cr3t-value-0042"


def client(tmp_path: Path) -> TestClient:
    c = TestClient(create_app(build(tmp_path / "data", clock=FrozenClock())), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c


def items(response_json: object) -> dict[str, object]:
    return {s.key: s for s in SettingsList.model_validate(response_json).settings}


def test_field_error(tmp_path: Path) -> None:
    c = client(tmp_path)
    refused = c.post(
        f"{PREFIX}/settings",
        json={"values": {"log.level": "debug", "capacity.warn_fraction": 9}},
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "config.out_of_range"
    assert refused.json()["error"]["field"] == "capacity.warn_fraction"
    unknown = c.post(f"{PREFIX}/settings", json={"values": {"no.such": 1}})
    assert unknown.json()["error"] == {
        "code": "config.unknown_key",
        "message": "no such setting: no.such",
        "field": "no.such",
    }
    wrong = c.post(f"{PREFIX}/settings", json={"values": {"device.probe_interval": "often"}})
    assert wrong.json()["error"]["field"] == "device.probe_interval"
    after = items(c.get(f"{PREFIX}/settings").json())
    assert after["log.level"].stored is False, "a rejected write stores nothing"  # type: ignore[attr-defined]


def test_null_deletes(tmp_path: Path) -> None:
    c = client(tmp_path)
    written = items(
        c.post(f"{PREFIX}/settings", json={"values": {"log.level": "debug"}}).json()
    )
    assert written["log.level"].value == "debug"  # type: ignore[attr-defined]
    deleted = items(c.post(f"{PREFIX}/settings", json={"values": {"log.level": None}}).json())
    assert deleted["log.level"].stored is False  # type: ignore[attr-defined]


def test_secret_never_returned(tmp_path: Path) -> None:
    c = client(tmp_path)
    written = c.post(f"{PREFIX}/settings", json={"values": {"igdb.client_secret": TYPED}})
    assert written.status_code == 200
    assert TYPED not in written.text
    state = items(written.json())["igdb.client_secret"].secret_state  # type: ignore[attr-defined]
    assert (state.present, state.length) == (True, len(TYPED))
    read = c.get(f"{PREFIX}/settings")
    assert TYPED not in read.text
    for path in ("/library", "/systems", "/version", "/session", "/openapi.json"):
        assert TYPED not in c.get(f"{PREFIX}{path}").text


def test_a_write_needs_the_token(tmp_path: Path) -> None:
    c = TestClient(create_app(build(tmp_path / "data", clock=FrozenClock())), base_url=BASE)
    refused = c.post(f"{PREFIX}/settings", json={"values": {"log.level": "debug"}})
    assert refused.status_code == 403
