"""The device marker, as bytes.

A marker is the `ROM-Sync.json` file at a destination's ROMs root. It is the
device's identity, so it is read from devices this computer has never seen and
is untrusted: `decode` turns anything malformed into `None` and never raises
(contract requirement C5), and the paths it carries are validated on ingress
by the application before anything is written (F6-S12).

The format is version 1's, so a device prepared by version 1 is recognised:

    {"app": "ROM-Sync", "format": 1, "id": ..., "name": ..., "created": ...,
     "selection": {"systems": [...]},
     "inventory": [{"path", "kind", "size", "hash", "sent_size", "sent_mtime"}]}
"""

from __future__ import annotations

import json
from typing import Final

from romsync.domain.errors import NotAName
from romsync.domain.models import Marker, MarkerEntry, SystemKey

NAME: Final = "ROM-Sync.json"
APP: Final = "ROM-Sync"
FORMAT: Final = 1

#: A marker larger than this is not read. Version 1's largest is a few hundred
#: kilobytes for a full handheld; this is a ceiling against a crafted file.
MAX_BYTES: Final = 16 * 1024 * 1024


def encode(marker: Marker) -> bytes:
    """The marker as version 1 wrote it."""
    body = {
        "app": APP,
        "format": marker.format,
        "id": marker.device_id,
        "name": marker.name,
        "created": marker.created,
        "selection": {"systems": [str(s) for s in marker.systems]},
        "inventory": [
            {
                "path": e.path,
                "kind": e.kind,
                "size": e.size,
                "hash": e.hash,
                "sent_size": e.sent_size,
                "sent_mtime": e.sent_mtime,
            }
            for e in marker.inventory
        ],
    }
    return json.dumps(body, indent=1, ensure_ascii=False).encode("utf-8")


def _int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(value)
    return value


def _float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(value)
    return float(value)


def _text(value: object, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise ValueError(value)
    return value


def _entry(raw: object) -> MarkerEntry:
    if not isinstance(raw, dict):
        raise ValueError(raw)
    path = _text(raw.get("path"))
    kind = _text(raw.get("kind", "file"))
    assert path is not None and kind is not None
    return MarkerEntry(
        path=path,
        kind=kind,
        size=_int(raw.get("size")),
        hash=_text(raw.get("hash"), optional=True),
        sent_size=_int(raw.get("sent_size")),
        sent_mtime=_float(raw.get("sent_mtime")),
    )


def decode(data: bytes) -> Marker | None:
    """The marker in `data`, or `None` when it is not one. Never raises."""
    if len(data) > MAX_BYTES:
        return None
    try:
        raw = json.loads(data.decode("utf-8-sig"))
        if not isinstance(raw, dict):
            return None
        device_id = raw.get("id")
        if not isinstance(device_id, str) or not device_id.strip():
            return None
        fmt = raw.get("format", FORMAT)
        if fmt != FORMAT:
            return None
        selection = raw.get("selection", {})
        systems = selection.get("systems", []) if isinstance(selection, dict) else None
        inventory = raw.get("inventory", [])
        if not isinstance(systems, list) or not isinstance(inventory, list):
            return None
        return Marker(
            device_id=device_id,
            name=_text(raw.get("name", "")) or "",
            created=_text(raw.get("created", "")) or "",
            systems=tuple(SystemKey(_text(s) or "") for s in systems),
            inventory=tuple(_entry(e) for e in inventory),
        )
    except (UnicodeDecodeError, ValueError, NotAName, RecursionError):
        return None
