"""Every request and response body, declared (SPEC section 9).

No route returns an ad-hoc dict: each names one of these as its response
model, and `tests/unit/api/test_contracts.py` holds the route table to it.
"""

from __future__ import annotations

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
