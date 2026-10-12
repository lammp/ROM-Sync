"""Diagnostics: what the engine is, where it is, its last sync and its recent
failures (F15-S1, SETTINGS.md section 7), and what its data folder holds
(F15-S2). Every field is read from its source
when asked: the version, the shell and the bind from the running application,
the address from the request the page made, the last sync from the run
records, and the errors from the job records."""

from __future__ import annotations

import sys

from fastapi import APIRouter, Depends, Request, Response

from romsync import __version__
from romsync.compose import Engine
from romsync_api.deps import engine
from romsync_api.models import Diagnostics, LastSync, RecentError, StorageList, StorageRow
from romsync_api.routes.sync import run_view

router = APIRouter(tags=["diagnostics"])

#: Failed jobs shown, newest first.
RECENT = 5


def last_sync(e: Engine) -> LastSync | None:
    latest: LastSync | None = None
    for profile in e.devices.profiles():
        for run in e.syncs.history(profile.id, 1):
            if run.id is None:
                continue
            if latest is None or run.started > latest.run.started:
                latest = LastSync(device_id=profile.id, device=profile.name, run=run_view(run))
    return latest


def recent_errors(e: Engine) -> list[RecentError]:
    failed = [j for j in e.jobs.all() if str(j.state) == "failed"]
    failed.sort(key=lambda j: j.finished or "", reverse=True)
    return [
        RecentError(
            job=j.id,
            kind=j.kind,
            target=j.target,
            finished=j.finished,
            code=j.error_code,
            message=j.error_message,
        )
        for j in failed[:RECENT]
    ]


@router.get("/diagnostics", response_model=Diagnostics)
def diagnostics(request: Request, e: Engine = Depends(engine)) -> Diagnostics:  # noqa: B008
    state = request.app.state
    return Diagnostics(
        application="ROM-Sync",
        version=__version__,
        api="v1",
        kind=state.shell_kind,
        capabilities=list(state.binding.capabilities),
        address=str(request.base_url),
        data_folder=str(e.data),
        log_folder=str(e.data / "logs"),
        last_sync=last_sync(e),
        recent_errors=recent_errors(e),
    )


@router.get("/storage", response_model=StorageList)
def storage(e: Engine = Depends(engine)) -> StorageList:  # noqa: B008
    """The data folder by part, every subfolder counted, with what maintenance
    would reclaim from each (F15-S2)."""
    rows = [
        StorageRow(
            component=r.component, files=r.files, bytes=r.bytes, reclaimable=r.reclaimable
        )
        for r in e.maintenance.storage()
    ]
    return StorageList(
        components=rows,
        total_bytes=sum(r.bytes for r in rows),
        reclaimable_bytes=sum(r.reclaimable for r in rows),
    )


def _platform() -> str:
    """The operating system, read without starting a process: the `platform`
    module asks a subprocess on some hosts, Windows among them."""
    windows = getattr(sys, "getwindowsversion", None)
    return sys.platform if windows is None else f"{sys.platform} build {windows().build}"


@router.get(
    "/diagnostics/bundle",
    response_class=Response,
    responses={200: {"content": {"application/zip": {}}}},
)
def support_bundle(request: Request, e: Engine = Depends(engine)) -> Response:  # noqa: B008
    """A zip for a bug report: the system, the settings with every secret left
    out, the recent jobs and the logs, each searched for every secret (F15-S3).
    Built in memory; nothing is written."""
    state = request.app.state
    system = {
        "application": "ROM-Sync",
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": _platform(),
        "shell": state.shell_kind,
        "address": str(request.base_url),
    }
    return Response(
        e.support(system),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="romsync-support.zip"'},
    )
