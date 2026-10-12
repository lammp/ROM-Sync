"""The determinism harness.

Applied to every test, with no opt-out marker. A test that needs an exception
is a test in the wrong tree.

What is guarded, and why each one is here rather than trusted:

- randomness, by pinning pytest-randomly's seed in the gate rather than
  seeding here, so there is exactly one source of it;
- the network, because a test that reaches it passes or fails on someone
  else's availability;
- subprocesses, because the device transports are built by assembling argument
  vectors and the assertion is on the vector, never on running a binary;
- sleeping, because a test that waits is a test that is slow on a good day and
  flaky on a bad one;
- writing into the repository, because a test that leaves a file behind makes
  the next run different from this one;
- reading outside the repository, the temporary directory and the interpreter,
  because a test that can see a real home directory is a test that passes on
  one machine.

The harness is itself tested, in `tests/unit/test_determinism.py`. A harness
nobody tests is a harness that quietly stops working.
"""

from __future__ import annotations

import builtins
import io
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.helpers.fakes import EPOCH, CountingIds, FrozenClock

# The interpreter caches what it imports. During a test that is the test
# writing outside its sandbox: a module imported lazily for the first time, or
# rewritten by pytest because it is a plugin (anyio is), lands a .pyc in
# site-packages, which a fresh CI install has not cached yet. Imports made
# while tests run write nothing; the write guard stays exactly as strict.
sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
SEED = 20261008

#: The seed the gate pins for test order and for every random source
#: pytest-randomly reseeds. The nightly overrides it, which is how order
#: dependence gets found. Nothing here seeds `random` itself: the plugin owns
#: that, and a second seeder would silently win or lose depending on fixture
#: order.
GATE_SEED = SEED

#: Paths inside the repository a test run is allowed to write. Everything the
#: verification gate itself produces, and nothing else.
WRITABLE_IN_REPO = (
    ".coverage",
    "coverage.xml",
    "reports",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
)


class NetworkInTest(RuntimeError):
    """A test tried to open a socket."""


class SubprocessInTest(RuntimeError):
    """A test tried to start a process it had not declared."""


class SleepInTest(RuntimeError):
    """A test tried to sleep."""


class WriteOutsideSandbox(RuntimeError):
    """A test tried to write where it may not."""


class ReadOutsideSandbox(RuntimeError):
    """A test tried to read where it may not."""


def _is_write(mode: str) -> bool:
    return any(c in mode for c in "wxa+")


def _allowed_in_repo(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    head = rel.parts[0] if rel.parts else ""
    return head in WRITABLE_IN_REPO or "__pycache__" in rel.parts


def _temp_roots() -> list[Path]:
    roots = [Path("/tmp")]
    for name in ("TMPDIR", "TEMP", "TMP"):
        value = os.environ.get(name)
        if value:
            roots.append(Path(value))
    return [r.resolve() for r in roots if r.exists()]


def _readable(path: Path) -> bool:
    """The repository, the interpreter and any temporary directory."""
    resolved = path.resolve()
    roots = [REPO_ROOT, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
    roots += [Path(entry).resolve() for entry in sys.path if entry]
    roots += _temp_roots()
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: Any, **_k: Any) -> Any:
        raise NetworkInTest(
            "a test opened a socket. Every HTTP interaction goes through a fake "
            "or a recorded response."
        )

    real_socket = socket.socket
    real_socketpair = socket.socketpair
    permit = threading.local()

    class Guarded(real_socket):  # type: ignore[misc, valid-type]
        """Still a socket class, so `isinstance(s, socket.socket)` keeps working:
        Windows' proactor event loop asks exactly that of its self-pipe, and a
        guard that replaced the class with a function broke the check and left
        every in-process API test waiting forever. Constructing one is refused
        except inside `socketpair`."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            if not getattr(permit, "on", False):
                refuse()
            super().__init__(*args, **kwargs)

    def socketpair(*args: Any, **kwargs: Any) -> Any:
        """An event loop wakes itself through a connected pair that never leaves
        the process, so an in-process API test needs one. Sockets may be made
        only for this call, on this thread."""
        permit.on = True
        try:
            return real_socketpair(*args, **kwargs)
        finally:
            permit.on = False

    monkeypatch.setattr(socket, "socket", Guarded)
    monkeypatch.setattr(socket, "socketpair", socketpair)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


@pytest.fixture(autouse=True)
def _no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: Any, **_k: Any) -> Any:
        raise SubprocessInTest(
            "a test started a process. Command construction is asserted on the "
            "argument vector, never by running a binary."
        )

    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "call", refuse)
    monkeypatch.setattr(subprocess, "check_output", refuse)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(_seconds: float) -> None:
        raise SleepInTest(
            "a test slept. Waiting is modelled with the frozen clock and explicit events."
        )

    monkeypatch.setattr(time, "sleep", refuse)


def _under(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


@pytest.fixture(autouse=True)
def _sandboxed_filesystem(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Two rules, and nothing clever.

    A write lands in the test's own temporary directory, a system temporary
    directory, or one of the few paths the gate itself produces inside the
    repository. A read comes from the repository, the interpreter, the import
    path or a temporary directory. Anything else raises, naming the path.
    """
    real_open = builtins.open
    sandbox = tmp_path.resolve()
    write_roots = [sandbox, *_temp_roots()]

    def guarded(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, int):
            return real_open(file, mode, *args, **kwargs)
        path = Path(os.fspath(file))
        if path.is_absolute():
            if _is_write(mode):
                # Precedence matters. A repository that happens to sit inside a
                # temporary directory must not exempt itself through the temp
                # allowance, so the sandbox is checked first and the repository
                # second. Found by test_write_outside_the_sandbox_is_refused.
                if _under(path, [sandbox]):
                    permitted = True
                elif _under(path, [REPO_ROOT]):
                    permitted = _allowed_in_repo(path)
                else:
                    permitted = _under(path, write_roots)
                if not permitted:
                    raise WriteOutsideSandbox(
                        f"a test wrote where it may not: {path}. Writes go to tmp_path."
                    )
            elif not _readable(path):
                raise ReadOutsideSandbox(
                    f"a test read where it may not: {path}. A test that can see "
                    f"a real user path passes on one machine."
                )
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)
    monkeypatch.setattr(io, "open", guarded)
    yield
    monkeypatch.setattr(builtins, "open", real_open)


@pytest.fixture(autouse=True)
def _temp_data_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect the home, application-data and temporary variables.

    No test can resolve a real user path, on any platform, whatever it reads
    them from.
    """
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME"):
        monkeypatch.setenv(name, str(home))
    monkeypatch.setenv("ROMSYNC_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(EPOCH)


@pytest.fixture
def ids() -> CountingIds:
    return CountingIds()


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
