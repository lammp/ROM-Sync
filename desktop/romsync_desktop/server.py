"""Serving the API on loopback, in this process (F12-S1).

`Server` is the shell's port onto an HTTP server: started with the
application and the bind the settings ask for, it answers with the address
the window opens, and stops when told. `UvicornServer` is the real one; it
opens a socket, so tests use a fake and no test runs it.
"""

from __future__ import annotations

import threading
import time
from typing import Protocol

from fastapi import FastAPI


class Server(Protocol):
    def start(self, app: FastAPI, host: str, port: int) -> str:
        """Serve `app` and return its address once it answers."""
        ...

    def stop(self) -> None:
        """Stop serving and wait for the server to finish."""
        ...


def uvicorn_settings() -> dict[str, object]:
    """How uvicorn is configured beyond the address.

    `log_config` is None so uvicorn leaves logging alone: the application's own
    log records it (F15-S4), and the windowed build has no console, so
    uvicorn's default formatter, which asks the console whether it is a
    terminal, fails before the server can start.
    """
    return {"log_level": "warning", "lifespan": "off", "log_config": None}


class UvicornServer:  # pragma: no cover - opens a socket
    """uvicorn in a thread. Port 0, or a preferred port already taken, gets a free one."""

    def __init__(self, ready_within: float = 15.0) -> None:
        self._ready_within = ready_within
        self._server: object | None = None
        self._thread: threading.Thread | None = None

    def _serve(self, app: FastAPI, host: str, port: int) -> int:
        import uvicorn

        config = uvicorn.Config(app, host=host, port=port, **uvicorn_settings())  # type: ignore[arg-type]
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, name="romsync-api", daemon=True)
        thread.start()
        for _ in range(int(self._ready_within / 0.05)):
            if server.started or not thread.is_alive():
                break
            time.sleep(0.05)
        if not server.started:
            raise OSError(f"the server could not listen on {host}:{port}")
        self._server, self._thread = server, thread
        return int(server.servers[0].sockets[0].getsockname()[1])

    def start(self, app: FastAPI, host: str, port: int) -> str:
        try:
            bound = self._serve(app, host, port)
        except OSError:
            if port == 0:
                raise
            bound = self._serve(app, host, 0)
        return f"http://{host}:{bound}/"

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True  # type: ignore[attr-defined]
        if self._thread is not None:
            self._thread.join(timeout=10)
