"""The harness itself.

Each guard is exercised by a planted violation. A harness nobody tests is a
harness that quietly stops working, and then every test below it is worth less
than it looks.
"""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

from tests.conftest import (
    SEED,
    NetworkInTest,
    ReadOutsideSandbox,
    SleepInTest,
    SubprocessInTest,
    WriteOutsideSandbox,
)
from tests.helpers.fakes import EPOCH, CountingIds, FrozenClock


def test_socket_guard() -> None:
    with pytest.raises(NetworkInTest):
        socket.socket()


def test_a_socket_pair_is_allowed_and_the_guard_returns() -> None:
    """An event loop's self-pipe never leaves the process; nothing else gets through."""
    a, b = socket.socketpair()
    a.close()
    b.close()
    with pytest.raises(NetworkInTest):
        socket.socket()


def test_the_guard_keeps_socket_a_class() -> None:
    """Windows' proactor event loop asks `isinstance(conn, socket.socket)` of its
    self-pipe on every wake-up. With the guard in place that question must still
    have an answer, or every in-process API test waits forever on Windows."""
    a, b = socket.socketpair()
    try:
        assert isinstance(socket.socket, type)
        assert isinstance(a, socket.socket) and isinstance(b, socket.socket)
        a.send(b"\0")
        assert b.recv(1) == b"\0"
    finally:
        a.close()
        b.close()


def test_socket_guard_covers_resolution() -> None:
    with pytest.raises(NetworkInTest):
        socket.getaddrinfo("example.invalid", 443)


def test_subprocess_guard() -> None:
    with pytest.raises(SubprocessInTest):
        subprocess.run(["echo", "no"], check=False)


def test_sleep_guard() -> None:
    with pytest.raises(SleepInTest):
        time.sleep(0.001)


def test_write_outside_the_sandbox_is_refused() -> None:
    with (
        pytest.raises(WriteOutsideSandbox),
        open(Path(__file__).resolve(), "a", encoding="utf-8"),
    ):
        pass


def test_write_inside_tmp_path_is_allowed(tmp_path: Path) -> None:
    target = tmp_path / "fine.txt"
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("ok")
    assert target.read_text(encoding="utf-8") == "ok"


def test_read_outside_the_sandbox_is_refused() -> None:
    outside = Path("/etc/hostname") if Path("/etc").exists() else Path("C:/Windows/win.ini")
    with pytest.raises(ReadOutsideSandbox), open(outside, encoding="utf-8"):
        pass


def test_reading_the_repository_is_allowed() -> None:
    assert (Path(__file__).resolve()).read_text(encoding="utf-8")


def test_clock_frozen(clock: FrozenClock) -> None:
    first = clock.now()
    assert first == EPOCH
    assert clock.now() == first, "a frozen clock does not move on its own"
    clock.advance(90)
    assert (clock.now() - first).total_seconds() == 90


def test_clock_does_not_go_backwards(clock: FrozenClock) -> None:
    with pytest.raises(ValueError, match="backwards"):
        clock.advance(-1)


def test_identifiers_are_predictable(ids: CountingIds) -> None:
    assert [ids.new_id() for _ in range(3)] == ["id-000001", "id-000002", "id-000003"]


def test_the_random_order_plugin_is_installed() -> None:
    """One source of randomness, and it is the one that also fixes the order."""
    assert importlib.util.find_spec("pytest_randomly") is not None


def test_the_gate_pins_the_random_seed() -> None:
    """Every pytest step the gate runs carries the same seed.

    Asserting "random is seeded" from inside a test the plugin has just
    reseeded proves nothing. The testable fact is that the gate pins a seed and
    the nightly overrides it.
    """
    from tools.verify import STAGES

    pytest_steps = [step for stage in STAGES for step in stage.steps if "pytest" in step.argv]
    assert pytest_steps, "the gate runs no pytest step"
    for step in pytest_steps:
        assert any(a.startswith("--randomly-seed=") for a in step.argv), step.argv
    seeds = {a for step in pytest_steps for a in step.argv if a.startswith("--randomly-seed=")}
    assert len(seeds) == 1, f"the gate uses more than one seed: {seeds}"
    assert seeds == {f"--randomly-seed={SEED}"}


def test_environment_cannot_resolve_a_real_user_path(tmp_path: Path) -> None:
    for name in ("HOME", "USERPROFILE", "APPDATA"):
        value = os.environ.get(name)
        assert value is not None
        assert str(tmp_path) in value, f"{name} still points outside the sandbox"


def test_no_direct_clock_use_in_production_source() -> None:
    """Production code asks a port for the time. The audit is the enforcement."""
    root = Path(__file__).resolve().parents[2]
    offenders: list[str] = []
    forbidden = ("datetime.now(", "time.time(", "time.monotonic(", "perf_counter(")
    for tree in ("engine", "api", "desktop"):
        for path in sorted((root / tree).rglob("*.py")):
            if path.name == "clock.py":
                continue
            text = path.read_text(encoding="utf-8")
            offenders += [
                f"{path.relative_to(root)}: {call}" for call in forbidden if call in text
            ]
    assert not offenders, "ask the clock port instead:\n" + "\n".join(offenders)


def test_no_uuid4_in_production_source() -> None:
    root = Path(__file__).resolve().parents[2]
    offenders = [
        str(path.relative_to(root))
        for tree in ("engine", "api", "desktop")
        for path in sorted((root / tree).rglob("*.py"))
        if "uuid4(" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, "ask the id port instead: " + ", ".join(offenders)
