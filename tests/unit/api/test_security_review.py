"""What the security review of 13 October found, and its fixes stay fixed (F16)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync.domain.errors import ConfigOutOfRange
from romsync.jobs.registry import Context, inline
from romsync_api.app import PREFIX, create_app
from romsync_api.models import Diagnostics
from romsync_api.security import HEADERS, TOKEN_HEADER
from tests.helpers.fakes import CountingIds, FrozenClock
from tests.unit.api.conftest import BASE


def client(tmp_path: Path, token: bool = True) -> TestClient:
    engine = build(tmp_path / "data", clock=FrozenClock(), ids=CountingIds("j"), runner=inline)
    c = TestClient(create_app(engine), base_url=BASE)
    if token:
        c.headers.update(
            {"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]}
        )
    return c


def test_listing_folders_needs_the_page_token(tmp_path: Path) -> None:
    """A page on another site can make the browser send a GET; listing this
    computer's folders is not harmless enough to answer one (F16-S1)."""
    bare = client(tmp_path, token=False)
    refused = bare.get(f"{PREFIX}/shell/folders", params={"path": str(tmp_path)})
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "request.forbidden"
    listed = client(tmp_path).get(f"{PREFIX}/shell/folders", params={"path": str(tmp_path)})
    assert listed.status_code == 200


@pytest.mark.parametrize(
    "path",
    ["\\\\evil.example\\share", "//evil.example/share", "\\\\?\\UNC\\evil\\x", "\\\\.\\C:"],
)
def test_a_share_or_device_path_is_never_opened(tmp_path: Path, path: str) -> None:
    """Opening a share makes Windows authenticate to whatever server it names,
    handing it the person's sign-in hash (F16-S1)."""
    got = client(tmp_path).get(f"{PREFIX}/shell/folders", params={"path": path})
    assert got.status_code == 422
    assert got.json()["error"]["code"] == "path.unreadable"


def test_every_answer_keeps_the_page_out_of_another_sites_frame(tmp_path: Path) -> None:
    c = client(tmp_path, token=False)
    for answer in (c.get(f"{PREFIX}/version"), c.post(f"{PREFIX}/settings", json={})):
        for name, value in HEADERS.items():
            assert answer.headers[name] == value, (answer.status_code, name)
    assert "frame-ancestors 'none'" in HEADERS["Content-Security-Policy"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("store.root", "\\\\server\\share\\ROMs"),
        ("store.root", "//server/share"),
        ("adb.path", "X:\\tools\\evil.exe"),
        ("adb.path", "\\\\server\\tools\\adb.exe"),
        ("device.staging_template", "{roms}/{system}"),
        ("device.staging_template", "Android/data/{system}"),
        ("server.bind_host", "0.0.0.0"),
    ],
)
def test_a_dangerous_setting_is_refused(tmp_path: Path, key: str, value: str) -> None:
    refused = client(tmp_path).post(f"{PREFIX}/settings", json={"values": {key: value}})
    assert refused.status_code == 422, refused.json()
    assert refused.json()["error"]["field"] == key


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("adb.path", "X:\\Games\\_tools\\platform-tools\\adb.exe"),
        ("adb.path", "/usr/bin/adb"),
        ("store.root", "X:\\Games\\ROMs"),
        ("device.staging_template", "ROM-Sync/{system}"),
        ("device.staging_template", "{roms}/bios/{system}"),
    ],
)
def test_an_ordinary_setting_is_kept(tmp_path: Path, key: str, value: str) -> None:
    kept = client(tmp_path).post(f"{PREFIX}/settings", json={"values": {key: value}})
    assert kept.status_code == 200, kept.json()


def test_recent_errors_leave_secrets_out(tmp_path: Path) -> None:
    """Diagnostics shows the newest failures as the support bundle does: with
    every secret left out (F16-S1)."""
    engine = build(tmp_path / "data", clock=FrozenClock(), ids=CountingIds("j"), runner=inline)
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    typed = "zzq-review-value-0077"
    c.post(f"{PREFIX}/settings", json={"values": {"igdb.client_secret": typed}})

    def leaky(ctx: Context) -> dict[str, int]:
        raise ConfigOutOfRange(f"the request carried {typed}")

    engine.jobs.submit("match", None, leaky)
    got = Diagnostics.model_validate(c.get(f"{PREFIX}/diagnostics").json())
    (error,) = got.recent_errors
    assert typed not in (error.message or "") and "[redacted]" in (error.message or "")
