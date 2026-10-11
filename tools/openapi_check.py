#!/usr/bin/env python3
"""The checked-in OpenAPI document matches the application (F10-S2).

    python tools/openapi_check.py           fail on any difference
    python tools/openapi_check.py --write   rewrite api/openapi.json

The interface's client is generated from `api/openapi.json`, so a change to a
route or a model that is not also a change to that file is drift: the client
and the engine would disagree. The gate runs this as its own stage.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCUMENT = ROOT / "api" / "openapi.json"


def current() -> dict[str, object]:
    """The document the application describes right now."""
    for folder in (ROOT / "api", ROOT / "engine"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    from romsync_api.app import create_app

    # the document describes routes and models; it needs no engine behind them
    return create_app(None).openapi()


def render(document: dict[str, object]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def check(path: Path = DOCUMENT, document: dict[str, object] | None = None) -> list[str]:
    """The differences between `path` and the application, as diff lines."""
    want = render(document if document is not None else current())
    have = path.read_text(encoding="utf-8") if path.exists() else ""
    if have == want:
        return []
    return list(
        difflib.unified_diff(
            have.splitlines(), want.splitlines(), "checked in", "application", lineterm=""
        )
    )


def main(argv: Sequence[str] | None = None, path: Path = DOCUMENT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite the checked-in document")
    args = parser.parse_args(argv)
    if args.write:
        path.write_text(render(current()), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
        return 0
    drift = check(path)
    if not drift:
        print("api/openapi.json matches the application")
        return 0
    print("api/openapi.json differs from the application; run tools/openapi_check.py --write")
    print("\n".join(drift[:80]))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
