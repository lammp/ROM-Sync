"""System files (F10-S19): the store side and readiness read without touching a
device; survey, stage, unstage and removing a stray item as jobs on the
device's reference."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.app.devices import Attached
from romsync.app.sysfiles import Report, RequirementState, SystemFiles, store_copy
from romsync.compose import Engine
from romsync.domain.errors import ProfileNotFound
from romsync.jobs.registry import Context
from romsync_api.deps import engine
from romsync_api.models import (
    JobView,
    RemoveOther,
    SysOther,
    SysReport,
    SysRequirement,
    SysStore,
    SysStoreCopy,
    SysStoreItem,
    SysSystem,
)
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["sysfiles"])


def _requirement(r: RequirementState) -> SysRequirement:
    req, copy = r.requirement, r.store
    return SysRequirement(
        name=req.name,
        required=req.required,
        group=req.group,
        note=req.note,
        install_label=req.install.label,
        installed_at=r.installed_at,
        staged=str(r.staged),
        installed=str(r.installed),
        store=SysStoreCopy(
            present=copy.present,
            staged_name=copy.staged_name,
            size=copy.size,
            verified=copy.verified,
        ),
    )


def report_view(report: Report) -> SysReport:
    return SysReport(
        surveyed_at=report.surveyed_at,
        apps=dict(report.apps),
        systems=[
            SysSystem(
                key=s.system.key,
                emulator=s.system.emulator,
                package=s.package,
                emulator_seen=s.emulator_seen,
                readiness=str(s.readiness),
                staging=str(s.staging),
                staging_folder=s.staging_folder,
                note=s.system.note,
                requirements=[_requirement(r) for r in s.requirements],
                missing=list(s.missing),
                staged_any=s.staged_any,
            )
            for s in report.systems
        ],
        others=[
            SysOther(path=o.path, name=o.name, kind=o.kind, size=o.size) for o in report.others
        ],
    )


def _attached(e: Engine, ref: str) -> tuple[str, Attached]:
    attached = e.devices.find(ref)
    if attached.profile is None:
        raise ProfileNotFound("this device has no profile yet", field="device")
    return attached.profile.id, attached


@router.get("/sysfiles/store", response_model=SysStore)
def store_side(e: Engine = Depends(engine)) -> SysStore:  # noqa: B008
    """Every requirement with the store's copy only, for when no device is chosen."""
    files: SystemFiles = e.sysfiles()
    items = []
    for system in files.systems:
        for req in system.requirements:
            copy = store_copy(files.store, req, files.hash_limit)
            items.append(
                SysStoreItem(
                    system=system.key,
                    emulator=system.emulator,
                    name=req.name,
                    required=req.required,
                    present=copy.present,
                    size=copy.size,
                    verified=copy.verified,
                    note=req.note,
                )
            )
    return SysStore(items=items)


@router.get("/devices/{ref}/sysfiles", response_model=SysReport)
def readiness(ref: str, e: Engine = Depends(engine)) -> SysReport:  # noqa: B008
    """Readiness from the last survey. Reads nothing from the device."""
    device_id, attached = _attached(e, ref)
    return report_view(e.sysfiles().report(device_id, attached.dest.roots()))


@router.post("/devices/{ref}/sysfiles/survey", response_model=JobView)
def survey(ref: str, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """List the device's staging and install folders, read-only, as a job."""
    device_id, attached = _attached(e, ref)

    def work(ctx: Context) -> dict[str, int]:
        return {"entries": e.sysfiles().survey(device_id, attached.dest)}

    return job_view(e.jobs.submit("sysfiles", ref, work))


@router.post("/devices/{ref}/sysfiles/{system}/stage", response_model=JobView)
def stage(ref: str, system: str, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Stage a system's files to its staging folder, as a job."""
    device_id, attached = _attached(e, ref)

    def work(ctx: Context) -> dict[str, int]:
        return {"placed": len(e.sysfiles().stage(device_id, attached.dest, system))}

    return job_view(e.jobs.submit("sysfiles", ref, work))


@router.post("/devices/{ref}/sysfiles/{system}/unstage", response_model=JobView)
def unstage(ref: str, system: str, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Remove a system's staged files, as a job."""
    device_id, attached = _attached(e, ref)

    def work(ctx: Context) -> dict[str, int]:
        return {"removed": len(e.sysfiles().unstage(device_id, attached.dest, system))}

    return job_view(e.jobs.submit("sysfiles", ref, work))


@router.post("/devices/{ref}/sysfiles/remove-other", response_model=JobView)
def remove_other(ref: str, body: RemoveOther, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Remove one stray item under the staging root, as a job. The folder is
    checked before the job starts."""
    device_id, attached = _attached(e, ref)
    folder = attached.dest.roots().device.resolve(body.path)

    def work(ctx: Context) -> dict[str, int]:
        e.sysfiles().remove_other(device_id, attached.dest, folder, body.name)
        return {"removed": 1}

    return job_view(e.jobs.submit("sysfiles", ref, work))
