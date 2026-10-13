"""The interface is served by manifest lookup only (F10-S6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from romsync_api.app import PREFIX, create_app
from romsync_api.static import ManifestError, load
from tests.unit.api.conftest import BASE

SECRET = b"prod.keys would be here"

#: Ways a request might try to leave the bundle.
TRAVERSAL = [
    "/../secret.txt",
    "/..%2fsecret.txt",
    "/%2e%2e/secret.txt",
    "/%2e%2e%2fsecret.txt",
    "/_next/../../secret.txt",
    "/_next/%2e%2e/%2e%2e/secret.txt",
    "/..\\secret.txt",
    "/..%5csecret.txt",
    "/....//secret.txt",
    "/.%2e/secret.txt",
    "/%252e%252e/secret.txt",
    "/C:/Windows/win.ini",
    "/C:%5cWindows%5cwin.ini",
    "//server/share/secret.txt",
    "/%5c%5cserver%5cshare",
    "/secret.txt%00.js",
    "/index.html/../../secret.txt",
    "/./../secret.txt",
    "/hidden.txt",
    "/manifest.json",
    "/" + "../" * 20 + "secret.txt",
    "/%c0%ae%c0%ae/secret.txt",
]


def _bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    (bundle / "_next" / "static").mkdir(parents=True)
    (bundle / "index.html").write_text("<h1>library</h1>", encoding="utf-8")
    (bundle / "devices").mkdir()
    (bundle / "devices" / "index.html").write_text("<h1>devices</h1>", encoding="utf-8")
    (bundle / "_next" / "static" / "app.js").write_text("run()", encoding="utf-8")
    (bundle / "hidden.txt").write_text("built but not listed", encoding="utf-8")
    (tmp_path / "secret.txt").write_bytes(SECRET)
    manifest = {
        "/": {"file": "index.html", "type": "text/html"},
        "/devices/": {"file": "devices/index.html", "type": "text/html"},
        "/_next/static/app.js": {"file": "_next/static/app.js", "type": "text/javascript"},
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(None, bundle=_bundle(tmp_path)), base_url=BASE)


def test_manifest_lookup_only(tmp_path: Path) -> None:
    client = _client(tmp_path)
    page = client.get("/")
    assert page.status_code == 200 and "library" in page.text
    assert page.headers["content-type"].startswith("text/html")
    script = client.get("/_next/static/app.js")
    assert script.headers["content-type"].startswith("text/javascript")
    assert "devices" in client.get("/devices").text
    assert "devices" in client.get("/devices/").text
    unlisted = client.get("/hidden.txt")
    assert unlisted.status_code == 404
    assert unlisted.json()["error"]["code"] == "request.not_found"
    assert client.get(f"{PREFIX}/version").status_code == 200, "the API still answers"


@pytest.mark.parametrize("path", TRAVERSAL)
def test_traversal_corpus_refused(tmp_path: Path, path: str) -> None:
    client = _client(tmp_path)
    got = client.get(path)
    assert got.status_code in (404, 400), path
    assert SECRET not in got.content


def test_the_corpus_is_the_size_the_story_names() -> None:
    assert len(TRAVERSAL) == 22


@pytest.mark.parametrize(
    "manifest",
    [
        {"/x": {"file": "../secret.txt", "type": "text/plain"}},
        {"/x": {"file": "/etc/passwd", "type": "text/plain"}},
        {"/x": {"file": "missing.js", "type": "text/javascript"}},
        {"/x": {"file": "_next", "type": "text/plain"}},
        {"x": {"file": "index.html", "type": "text/html"}},
        {"/x": {"file": "index.html"}},
        {"/x": "index.html"},
        ["/x"],
    ],
)
def test_a_manifest_naming_anything_else_is_refused(tmp_path: Path, manifest: object) -> None:
    bundle = _bundle(tmp_path)
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestError):
        load(bundle)


def test_no_manifest_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ManifestError):
        load(tmp_path)
