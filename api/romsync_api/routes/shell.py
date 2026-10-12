"""Shell endpoints: reveal, pick folder, open external (F10-S15), notify (F12-S5).

They answer only while the server listens on loopback; off loopback every one
is refused, whatever it is asked.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from romsync.compose import Engine
from romsync.domain.errors import ShellUnavailable
from romsync_api.deps import engine
from romsync_api.models import (
    Notified,
    Notify,
    OpenLink,
    PickedFolder,
    PickFolder,
    Reveal,
    ShellDone,
)

router = APIRouter(prefix="/shell", tags=["shell"])


def loopback_only(request: Request) -> None:
    if not request.app.state.binding.shell_enabled:
        raise ShellUnavailable("the shell endpoints answer only on loopback")


@router.post("/reveal", response_model=ShellDone, dependencies=[Depends(loopback_only)])
def reveal(body: Reveal, e: Engine = Depends(engine)) -> ShellDone:  # noqa: B008
    e.shell.reveal(body.root, body.path)
    return ShellDone(done=True)


@router.post("/pick-folder", response_model=PickedFolder, dependencies=[Depends(loopback_only)])
def pick_folder(body: PickFolder, e: Engine = Depends(engine)) -> PickedFolder:  # noqa: B008
    chosen = e.shell.pick_folder(body.title)
    return PickedFolder(path=None if chosen is None else str(chosen))


@router.post("/open", response_model=ShellDone, dependencies=[Depends(loopback_only)])
def open_link(body: OpenLink, e: Engine = Depends(engine)) -> ShellDone:  # noqa: B008
    e.shell.open_url(body.url)
    return ShellDone(done=True)


@router.post("/notify", response_model=Notified, dependencies=[Depends(loopback_only)])
def notify(body: Notify, e: Engine = Depends(engine)) -> Notified:  # noqa: B008
    """Never an error: a notification that cannot be shown is `delivered: false`."""
    return Notified(delivered=e.shell.notify(body.title, body.body))
