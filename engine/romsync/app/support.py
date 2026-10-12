"""The support bundle (F15-S3, SETTINGS.md section 7).

A zip a person can attach to a bug report: what the system is, the settings
with every secret's value left out, the recent job records, and the logs.
Every secret the settings hold is also searched for in everything written, so
a secret that found its way into an error message or a log line is replaced
before the bundle leaves the engine, not trusted to have stayed out.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from typing import Final

from romsync.app.settings import Settings
from romsync.ports.repo import JobRecord

#: What a secret's value becomes wherever it is found.
REDACTED: Final = "[redacted]"
#: A secret shorter than this is not searched for: it would match ordinary text.
SHORTEST: Final = 4
#: Every entry carries this date, so the same inputs make the same bundle.
STAMP: Final = (1980, 1, 1, 0, 0, 0)


def redact(text: str, secrets: Iterable[str]) -> str:
    """`text` with every secret's value replaced, longest first."""
    for secret in sorted({s for s in secrets if len(s) >= SHORTEST}, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    return text


def _job(j: JobRecord) -> dict[str, object]:
    return {
        "id": j.id,
        "kind": j.kind,
        "target": j.target,
        "state": str(j.state),
        "started": j.started,
        "finished": j.finished,
        "error_code": j.error_code,
        "error_message": j.error_message,
        "result": dict(j.result) if j.result else None,
    }


def bundle(
    system: Mapping[str, object],
    settings: Settings,
    jobs: Sequence[JobRecord],
    logs: Mapping[str, str],
) -> bytes:
    secret_keys = [s.key for s in settings.registry.settings if s.secret]
    secrets = [str(settings.value(k)) for k in secret_keys]
    shown: dict[str, object] = dict(settings.values())
    for key in secret_keys:
        shown[key] = REDACTED if settings.value(key) else None
    entries = {
        "system.json": json.dumps(dict(system), indent=2, sort_keys=True, default=str),
        "settings.json": json.dumps(shown, indent=2, sort_keys=True, default=str),
        "jobs.json": json.dumps([_job(j) for j in jobs], indent=2, default=str),
        **{f"logs/{name}": text for name, text in sorted(logs.items())},
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in entries.items():
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, redact(text, secrets))
    return out.getvalue()
