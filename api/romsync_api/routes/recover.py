"""Recover: what only the device holds, placed in the store without overwriting (F10-S20)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.app.devices import Attached
from romsync.compose import Engine
from romsync.domain.errors import ProfileNotFound
from romsync.jobs.registry import Context
from romsync_api.deps import engine
from romsync_api.models import JobView, RecoverItem, RecoverList, RecoverOne
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["recover"])


def _attached(e: Engine, ref: str) -> tuple[str, Attached]:
    attached = e.devices.find(ref)
    if attached.profile is None:
        raise ProfileNotFound("this device has no profile yet", field="device")
    return attached.profile.id, attached


@router.get("/devices/{ref}/recover", response_model=RecoverList)
def candidates(ref: str, e: Engine = Depends(engine)) -> RecoverList:  # noqa: B008
    """What the device holds that the library does not, from what was recorded."""
    device_id, _ = _attached(e, ref)
    return RecoverList(
        items=[
            RecoverItem(system=i.system, name=i.name, kind=i.kind, size=i.size)
            for i in e.recover.candidates(device_id)
        ]
    )


@router.post("/devices/{ref}/recover", response_model=JobView)
def recover(ref: str, body: RecoverOne, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Pull one item and place it in the store, never overwriting, as a job."""
    device_id, attached = _attached(e, ref)

    def work(ctx: Context) -> dict[str, int]:
        done = e.recover.recover(device_id, attached.dest, body.system, body.name)
        return {"placed": 1, "bytes": done.size or 0}

    return job_view(e.jobs.submit("recover", ref, work))
