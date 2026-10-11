"""Devices by stable reference, and their selections (F10-S10, F10-S11).

A device crosses the boundary only as its reference: never as a position in a
list. Selection changes go through the domain's algebra in the application
layer; there is no SQL here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.app.devices import Attached, Blocked, DeviceProfile
from romsync.compose import Engine
from romsync.domain.models import Mode, Selection, SystemKey
from romsync.domain.refs import encode
from romsync_api.deps import engine
from romsync_api.models import (
    AttachedDevice,
    AttachedDevices,
    BlockedDevice,
    CapacityView,
    GamesChange,
    GamesChanged,
    Inventory,
    InventoryItem,
    ModeChange,
    NewProfile,
    Profile,
    Profiles,
    SelectionView,
)

router = APIRouter(tags=["devices"])


def profile_of(p: DeviceProfile) -> Profile:
    return Profile(
        id=p.id,
        name=p.name,
        kind=str(p.kind),
        roms_root=p.roms_root,
        first_seen=p.first_seen,
        last_seen=p.last_seen,
        capacity=p.capacity,
        free=p.free,
        ref=encode(p.identity.ref) if p.identity is not None else None,
    )


def attached_of(a: Attached, roms_root: str) -> AttachedDevice:
    return AttachedDevice(
        ref=a.ref,
        kind=str(a.dest.kind),
        description=a.description,
        has_marker=a.marker is not None,
        profile=profile_of(a.profile) if a.profile is not None else None,
        roms_root=roms_root,
    )


def blocked_of(b: Blocked) -> BlockedDevice:
    return BlockedDevice(kind=b.kind, description=b.description, reason=b.reason)


@router.get("/devices", response_model=AttachedDevices)
def devices(e: Engine = Depends(engine)) -> AttachedDevices:  # noqa: B008
    found = e.devices.refresh()
    return AttachedDevices(
        devices=[attached_of(a, e.devices.roms_root(a)) for a in found],
        blocked=[blocked_of(b) for b in e.devices.blocked],
        unreachable=e.devices.unreachable,
    )


@router.get("/devices/{ref}", response_model=AttachedDevice)
def device(ref: str, e: Engine = Depends(engine)) -> AttachedDevice:  # noqa: B008
    found = e.devices.find(ref)
    return attached_of(found, e.devices.roms_root(found))


@router.get("/devices/{ref}/capacity", response_model=CapacityView)
def capacity(ref: str, e: Engine = Depends(engine)) -> CapacityView:  # noqa: B008
    c = e.devices.capacity(ref)
    return CapacityView(total=c.total, free=c.free)


@router.post("/devices/{ref}/profile", response_model=Profile)
def create_profile(ref: str, body: NewProfile, e: Engine = Depends(engine)) -> Profile:  # noqa: B008
    return profile_of(e.devices.create(ref, body.name, body.write_marker))


@router.post("/devices/{ref}/adopt", response_model=Profile)
def adopt(ref: str, e: Engine = Depends(engine)) -> Profile:  # noqa: B008
    return profile_of(e.devices.adopt(ref))


@router.get("/profiles", response_model=Profiles)
def profiles(e: Engine = Depends(engine)) -> Profiles:  # noqa: B008
    return Profiles(profiles=[profile_of(p) for p in e.devices.profiles()])


def selection_of(device_id: str, s: Selection) -> SelectionView:
    return SelectionView(
        device_id=device_id,
        modes={str(k): str(m) for k, m in sorted(s.modes.items())},
        overrides={str(g): o.include for g, o in sorted(s.overrides.items())},
    )


@router.get("/profiles/{device_id}/selection", response_model=SelectionView)
def selection(device_id: str, e: Engine = Depends(engine)) -> SelectionView:  # noqa: B008
    return selection_of(device_id, e.selections.get(device_id))


@router.get("/profiles/{device_id}/inventory", response_model=Inventory)
def inventory(device_id: str, e: Engine = Depends(engine)) -> Inventory:  # noqa: B008
    """What the device held when it was last read (F10-S22, added)."""
    return Inventory(
        items=[
            InventoryItem(system=i.system, name=i.name, kind=i.kind, size=i.size)
            for i in e.devices.inventory(device_id)
        ]
    )


@router.post("/profiles/{device_id}/selection/mode", response_model=SelectionView)
def set_mode(device_id: str, body: ModeChange, e: Engine = Depends(engine)) -> SelectionView:  # noqa: B008
    return selection_of(
        device_id, e.selections.set_mode(device_id, SystemKey(body.system), Mode(body.mode))
    )


@router.post("/profiles/{device_id}/selection/games", response_model=GamesChanged)
def set_games(device_id: str, body: GamesChange, e: Engine = Depends(engine)) -> GamesChanged:  # noqa: B008
    s, changed = e.selections.set_games(device_id, body.game_ids, body.include)
    return GamesChanged(selection=selection_of(device_id, s), changed=changed)


@router.post("/profiles/{device_id}/selection/clear", response_model=SelectionView)
def clear(device_id: str, e: Engine = Depends(engine)) -> SelectionView:  # noqa: B008
    return selection_of(device_id, e.selections.clear(device_id))
