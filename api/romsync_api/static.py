"""The interface's files, served by name from the build's manifest (F10-S6).

The build writes `manifest.json` beside the bundle: every URL the interface
has, mapped to the file that answers it and its media type. A request is
answered only by looking its path up in that table. Nothing from the request is
ever joined to a folder, so no spelling of `..`, no encoding and no drive
letter can reach a file the build did not list (SPEC section 12, S2).

Each listed file is checked once, when the manifest is loaded, to be a file
inside the bundle; a manifest that names anything else is refused whole.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, Response

from romsync_api.errors import respond

MANIFEST = "manifest.json"


@dataclass(frozen=True, slots=True)
class Asset:
    path: Path
    media_type: str


class ManifestError(ValueError):
    """The manifest is not one the build wrote."""


def load(bundle: Path) -> Mapping[str, Asset]:
    """URL path to asset, every file checked to sit inside `bundle`."""
    root = bundle.resolve()
    try:
        raw = json.loads((bundle / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManifestError(f"no readable manifest in {bundle}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError("the manifest is not a table")
    assets: dict[str, Asset] = {}
    for url, entry in raw.items():
        if not (isinstance(url, str) and url.startswith("/") and isinstance(entry, dict)):
            raise ManifestError(f"not a manifest entry: {url!r}")
        file, media = entry.get("file"), entry.get("type")
        if not isinstance(file, str) or not isinstance(media, str):
            raise ManifestError(f"{url}: an entry names a file and a type")
        path = (root / file).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ManifestError(f"{url}: {file!r} is not a file in the bundle")
        assets[url] = Asset(path, media)
    return MappingProxyType(assets)


def lookup(assets: Mapping[str, Asset], url: str) -> Asset | None:
    """The asset for a request path: the path itself, or the page at that folder."""
    return (
        assets.get(url) or assets.get(url.rstrip("/") + "/") or assets.get(url + "/index.html")
    )


def install(app: FastAPI, bundle: Path) -> None:
    assets = load(bundle)
    router = APIRouter(include_in_schema=False)

    @router.get("/{rest:path}", response_model=None)
    def serve(request: Request, rest: str) -> Response:
        asset = lookup(assets, request.url.path)
        if asset is None:
            return respond("request.not_found", "no such page", status=404)
        return FileResponse(asset.path, media_type=asset.media_type)

    app.include_router(router)
