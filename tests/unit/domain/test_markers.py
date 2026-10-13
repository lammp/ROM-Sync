"""The device marker codec: version 1's format, and nothing malformed gets through."""

from __future__ import annotations

import json

import pytest

from romsync.domain import markers
from romsync.domain.models import Marker, MarkerEntry, SystemKey

MARKER = Marker(
    "dev-1",
    "Handheld",
    "2026-01-01T00:00:00+00:00",
    (SystemKey("nes"), SystemKey("snes")),
    (
        MarkerEntry("nes\\Contra.nes", "file", 3, "abc", 3, 1.5),
        MarkerEntry("psx\\Game", "folder", None, None, None, None),
    ),
)

#: A marker as version 1 wrote it, runs and all.
VERSION_ONE = {
    "app": "ROM-Sync",
    "format": 1,
    "id": "dev-1",
    "name": "Handheld",
    "kind": "adb",
    "roms_root": "ROMs",
    "created": "2026-01-01T00:00:00+00:00",
    "written": "2026-02-01T00:00:00+00:00",
    "selection": {"systems": ["nes"]},
    "inventory": [
        {
            "path": "nes\\Contra.nes",
            "kind": "file",
            "size": 3,
            "hash": None,
            "sent_size": 3,
            "sent_mtime": 2,
            "confirmed": "2026-02-01T00:00:00+00:00",
        }
    ],
    "runs": [{"started": "x", "state": "done"}],
}


def test_round_trip() -> None:
    assert markers.decode(markers.encode(MARKER)) == MARKER


def test_encodes_version_ones_keys() -> None:
    body = json.loads(markers.encode(MARKER))
    assert body["app"] == "ROM-Sync"
    assert body["id"] == "dev-1"
    assert body["selection"] == {"systems": ["nes", "snes"]}
    assert body["inventory"][0]["sent_mtime"] == 1.5


def test_reads_a_version_one_marker() -> None:
    found = markers.decode(json.dumps(VERSION_ONE).encode())
    assert found == Marker(
        "dev-1",
        "Handheld",
        "2026-01-01T00:00:00+00:00",
        (SystemKey("nes"),),
        (MarkerEntry("nes\\Contra.nes", "file", 3, None, 3, 2.0),),
    )


def test_a_byte_order_mark_is_tolerated() -> None:
    assert markers.decode(b"\xef\xbb\xbf" + markers.encode(MARKER)) == MARKER


def test_defaults_for_what_version_one_could_omit() -> None:
    found = markers.decode(b'{"id": "dev-2", "inventory": [{"path": "nes\\\\A.nes"}]}')
    assert found == Marker(
        "dev-2", "", "", (), (MarkerEntry("nes\\A.nes", "file", None, None, None, None),)
    )


def _with(**changes: object) -> bytes:
    body = dict(VERSION_ONE)
    body.update(changes)
    return json.dumps(body).encode()


def _entry(**changes: object) -> bytes:
    entry = dict(VERSION_ONE["inventory"][0])  # type: ignore[index]
    entry.update(changes)
    return _with(inventory=[entry])


def _short(data: bytes) -> str:
    """A case's name, kept short: pytest puts it in an environment variable, and
    Windows refuses one over 32,767 characters (the 200,000-byte nesting case)."""
    head = data[:40].decode("utf-8", errors="replace")
    return head if len(data) <= 40 else f"{head}...({len(data):,} bytes)"


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not json",
        b"\xff\xfe",
        b"[]",
        b'"a string"',
        _with(id=None),
        _with(id=7),
        _with(id="  "),
        _with(format=2),
        _with(selection=[]),
        _with(selection={"systems": "nes"}),
        _with(selection={"systems": ["../etc"]}),
        _with(selection={"systems": [5]}),
        _with(inventory={}),
        _with(inventory=["nes\\A.nes"]),
        _with(name=5),
        _entry(path=None),
        _entry(kind=3),
        _entry(size="3"),
        _entry(size=True),
        _entry(hash=5),
        _entry(sent_mtime="soon"),
        _entry(sent_mtime=False),
        b"[" * 100_000 + b"]" * 100_000,
    ],
    ids=lambda data: _short(data),
)
def test_malformed_is_none_never_an_error(data: bytes) -> None:
    assert markers.decode(data) is None


def test_an_oversized_marker_is_not_read() -> None:
    padding = b" " * markers.MAX_BYTES
    assert markers.decode(markers.encode(MARKER) + padding) is None
