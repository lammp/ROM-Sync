"""Every request and response body, declared (SPEC section 9).

No route returns an ad-hoc dict: each names one of these as its response
model, and `tests/unit/api/test_contracts.py` holds the route table to it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ErrorBody(Model):
    code: str
    message: str
    field: str | None = None


class ErrorEnvelope(Model):
    error: ErrorBody


class Version(Model):
    application: str
    version: str
    api: str


class Session(Model):
    """What a page needs before it can change anything."""

    token: str
    #: Whether the shell endpoints answer: only while the bind is loopback.
    shell: bool


class Member(Model):
    name: str
    size: int


class GameSummary(Model):
    """One game as the library lists it."""

    id: int
    system: str
    name: str
    title: str
    region: str | None
    kind: str
    size: int
    mtime: float
    files: int
    state: str
    matched: bool
    confidence: float | None
    igdb_id: int | None
    igdb_name: str | None
    year: int | None
    genres: list[str]
    rating: float | None
    votes: int | None
    cover: str | None
    tags: dict[str, list[str]]


class GameDetail(GameSummary):
    summary: str | None
    members: list[Member]


class Library(Model):
    games: list[GameSummary]


class SystemSummary(Model):
    key: str
    label: str
    extensions: list[str]
    games: int
    bytes: int


class Systems(Model):
    systems: list[SystemSummary]


class Secret(Model):
    present: bool
    length: int
    saved_at: str | None
    source: str | None


class SettingItem(Model):
    """One setting: how to render its control, and its value."""

    key: str
    kind: str
    description: str
    secret: bool
    restart: bool
    default: str | int | float | bool | None
    minimum: float | None
    maximum: float | None
    choices: list[str]
    unit: str
    value: str | int | float | bool | None
    stored: bool
    secret_state: Secret | None


class SettingsList(Model):
    settings: list[SettingItem]


class SettingsWrite(Model):
    """A partial write: only these keys change; null deletes a key."""

    values: dict[str, str | int | float | bool | None]


class CredentialTest(Model):
    """What was typed. A field left out or blank falls back to the saved value."""

    client_id: str | None = None
    client_secret: str | None = None


class CredentialStage(Model):
    name: str
    outcome: str
    code: str | None
    message: str | None


class CredentialResult(Model):
    ok: bool
    failed_at: str | None
    stages: list[CredentialStage]


class Profile(Model):
    """A device this computer has a profile for, attached or not."""

    id: str
    name: str
    kind: str
    roms_root: str
    first_seen: str
    last_seen: str
    capacity: int | None
    free: int | None
    #: The stable reference of the transport it was last seen on, if known.
    ref: str | None


class Profiles(Model):
    profiles: list[Profile]


class AttachedDevice(Model):
    """One attached destination, named by its stable reference."""

    ref: str
    kind: str
    description: str
    has_marker: bool
    profile: Profile | None
    #: Where a profile made for it keeps its ROMs: the destination's own root.
    roms_root: str


class BlockedDevice(Model):
    """An attached destination the probe could not read, and why."""

    kind: str
    description: str
    reason: str


class AttachedDevices(Model):
    devices: list[AttachedDevice]
    blocked: list[BlockedDevice]
    unreachable: int


class CapacityView(Model):
    total: int
    free: int


class NewProfile(Model):
    name: str
    write_marker: bool = True


class SelectionView(Model):
    device_id: str
    modes: dict[str, str]
    overrides: dict[str, bool]


class ModeChange(Model):
    system: str
    mode: Literal["all", "none", "off"]


class GamesChange(Model):
    game_ids: list[int]
    include: bool


class GamesChanged(Model):
    selection: SelectionView
    changed: int


class PlanOp(Model):
    action: str
    system: str
    name: str
    kind: str
    size: int
    game_id: int | None


class PlanBytes(Model):
    add: int
    drop: int
    net: int
    peak: int
    free: int | None
    fits: bool | None


class PlanView(Model):
    device_id: str
    send: list[PlanOp]
    update: list[PlanOp]
    remove: list[PlanOp]
    unchanged: int
    unknown_systems: dict[str, int]
    managed_systems: list[str]
    bytes: PlanBytes


class StartSync(Model):
    #: The removal count, when it is at or above the confirmation threshold.
    confirm_removals: int | None = None


class ProgressView(Model):
    phase: str
    done: int
    total: int | None
    current: str | None
    detail: dict[str, int] | None


class JobView(Model):
    id: str
    kind: str
    target: str | None
    state: str
    progress: ProgressView | None
    result: dict[str, int] | None
    error_code: str | None
    error_message: str | None
    started: str | None
    finished: str | None


class JobList(Model):
    jobs: list[JobView]


class RunView(Model):
    id: int
    state: str
    started: str
    finished: str | None
    counts: dict[str, int | str] | None
    bytes_moved: int | None


class RunList(Model):
    runs: list[RunView]


class InventoryItem(Model):
    #: The device folder it sits in, which need not be a store system.
    system: str
    name: str
    kind: str
    size: int | None


class Inventory(Model):
    """What the device held when it was last read."""

    items: list[InventoryItem]


class SyncStatusView(Model):
    job: JobView | None
    run: RunView | None


class MaintenanceReport(Model):
    action: str
    count: int
    bytes: int
    names: list[str]


class MaintenanceRun(Model):
    #: The count the dry run found; required for a destructive action.
    expected: int | None = None


class Reveal(Model):
    #: One of the configured folders: "store", "data" or "firmware".
    root: str
    #: A path below it, or nothing for the folder itself.
    path: str | None = None


class PickFolder(Model):
    title: str


class PickedFolder(Model):
    path: str | None


class OpenLink(Model):
    url: str


class ShellDone(Model):
    done: bool


class Rematch(Model):
    #: A metadata id, a slug, or the service's link to the game.
    ref: str


class TagView(Model):
    tag: str
    kind: str
    state: str
    source: str | None


class TagList(Model):
    game_id: int
    tags: list[TagView]


class TagAdd(Model):
    tag: str
    kind: str = "user"


class TagRef(Model):
    tag: str
    kind: str


class TagDecision(Model):
    tag: str
    kind: str
    accept: bool


class SysStoreCopy(Model):
    present: bool
    staged_name: str
    size: int | None
    verified: bool | None


class SysRequirement(Model):
    name: str
    required: bool
    group: str | None
    note: str
    install_label: str
    installed_at: str
    staged: str
    installed: str
    store: SysStoreCopy


class SysSystem(Model):
    key: str
    emulator: str
    package: str | None
    emulator_seen: bool | None
    readiness: str
    staging: str
    staging_folder: str
    note: str
    requirements: list[SysRequirement]
    missing: list[str]
    staged_any: bool


class SysOther(Model):
    path: str
    name: str
    kind: str
    size: int | None


class SysReport(Model):
    surveyed_at: str | None
    apps: dict[str, str]
    systems: list[SysSystem]
    others: list[SysOther]


class SysStoreItem(Model):
    system: str
    emulator: str
    name: str
    required: bool
    present: bool
    size: int | None
    verified: bool | None
    note: str


class SysStore(Model):
    items: list[SysStoreItem]


class RemoveOther(Model):
    #: The folder, relative to the device's storage, under the staging root.
    path: str
    name: str


class RecoverItem(Model):
    system: str
    name: str
    kind: str
    size: int | None


class RecoverList(Model):
    items: list[RecoverItem]


class RecoverOne(Model):
    system: str
    name: str
