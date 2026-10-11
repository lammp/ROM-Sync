"""Library, game, systems and settings reads (F10-S7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.app.library import GameView, by_kind
from romsync.app.settings import SettingView
from romsync.compose import Engine
from romsync_api.deps import engine
from romsync_api.models import (
    GameDetail,
    GameSummary,
    Library,
    Member,
    Secret,
    SettingItem,
    SettingsList,
    SettingsWrite,
    Systems,
    SystemSummary,
)

router = APIRouter(tags=["library"])

Scalar = str | int | float | bool | None


def summary_of(view: GameView) -> dict[str, object]:
    u, m = view.unit, view.meta
    return {
        "id": view.id,
        "system": str(u.system),
        "name": u.name,
        "title": u.title,
        "region": u.region,
        "kind": str(u.kind),
        "size": u.size,
        "mtime": u.mtime,
        "files": max(1, len(u.members)),
        "state": m.state,
        "matched": m.igdb_id is not None,
        "confidence": m.confidence,
        "igdb_id": m.igdb_id,
        "igdb_name": m.igdb_name,
        "year": view.year,
        "genres": list(m.genres),
        "rating": m.rating,
        "votes": m.rating_count,
        "cover": m.cover,
        "tags": {k: list(v) for k, v in by_kind(view.tags).items()},
    }


@router.get("/library", response_model=Library)
def library(e: Engine = Depends(engine)) -> Library:  # noqa: B008
    return Library(games=[GameSummary(**summary_of(v)) for v in e.library.games()])  # type: ignore[arg-type]


@router.get("/games/{game_id}", response_model=GameDetail)
def game(game_id: int, e: Engine = Depends(engine)) -> GameDetail:  # noqa: B008
    view = e.library.game(game_id)
    return GameDetail(
        **summary_of(view),  # type: ignore[arg-type]
        summary=view.meta.summary,
        members=[Member(name=m.name, size=m.size) for m in view.unit.members],
    )


@router.get("/systems", response_model=Systems)
def systems(e: Engine = Depends(engine)) -> Systems:  # noqa: B008
    return Systems(
        systems=[
            SystemSummary(
                key=str(s.info.key),
                label=s.info.label,
                extensions=list(s.info.exts),
                games=s.games,
                bytes=s.bytes,
            )
            for s in e.library.systems()
        ]
    )


def _scalar(value: object) -> Scalar:
    return value if isinstance(value, str | int | float | bool) or value is None else str(value)


def setting_item(view: SettingView) -> SettingItem:
    s = view.setting
    state = view.secret
    return SettingItem(
        key=s.key,
        kind=s.kind,
        description=s.description,
        secret=s.secret,
        restart=s.restart,
        default=None if s.secret else _scalar(s.default),
        minimum=s.minimum,
        maximum=s.maximum,
        choices=list(s.choices),
        unit=s.unit,
        value=None if s.secret else _scalar(view.value),
        stored=view.stored,
        secret_state=None
        if state is None
        else Secret(
            present=state.present,
            length=state.length,
            saved_at=state.saved_at,
            source=state.source,
        ),
    )


@router.get("/settings", response_model=SettingsList)
def settings(e: Engine = Depends(engine)) -> SettingsList:  # noqa: B008
    return SettingsList(settings=[setting_item(v) for v in e.settings.describe()])


@router.post("/settings", response_model=SettingsList)
def write_settings(body: SettingsWrite, e: Engine = Depends(engine)) -> SettingsList:  # noqa: B008
    """Validate every key, store them, delete a key sent as null. A rejection
    names its field; a secret is never echoed back."""
    return SettingsList(settings=[setting_item(v) for v in e.settings.write(body.values)])
