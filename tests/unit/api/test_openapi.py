"""The checked-in OpenAPI document is the application's (F10-S2)."""

from __future__ import annotations

import json
from pathlib import Path

from tools import openapi_check


def test_no_drift() -> None:
    assert openapi_check.check() == [], "run tools/openapi_check.py --write"


def test_drift_fails(tmp_path: Path) -> None:
    document = json.loads(openapi_check.DOCUMENT.read_text(encoding="utf-8"))
    document["paths"]["/api/v1/undeclared"] = {"get": {}}
    planted = tmp_path / "openapi.json"
    planted.write_text(openapi_check.render(document), encoding="utf-8")
    assert openapi_check.main([], path=planted) == 1
    assert any("undeclared" in line for line in openapi_check.check(planted))


def test_write_then_check(tmp_path: Path) -> None:
    path = tmp_path / "openapi.json"
    assert openapi_check.check(path)
    assert openapi_check.main(["--write"], path=path) == 0
    assert openapi_check.main([], path=path) == 0


def test_the_document_is_versioned_and_prefixed() -> None:
    document = json.loads(openapi_check.DOCUMENT.read_text(encoding="utf-8"))
    assert document["info"]["title"] == "ROM-Sync"
    assert all(p.startswith("/api/v1/") for p in document["paths"])
