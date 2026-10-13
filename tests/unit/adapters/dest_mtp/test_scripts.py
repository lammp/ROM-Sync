"""MTP scripts and the one arrival policy (F6-S6, F6-S7). No PowerShell runs."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from romsync.adapters.dest_common import local
from romsync.adapters.dest_mtp import ArrivalPolicy, MtpDest, PsResult, Script, scripts
from romsync.config.registry import REGISTRY
from romsync.domain import markers
from romsync.domain.errors import (
    DestinationItemMissing,
    DestinationRootMissing,
    DestinationUnavailable,
    TransferFailed,
)
from romsync.domain.models import Action, Kind
from romsync.domain.paths import LocalRoot, StoreRoot
from romsync.ports.dest import DestVerify, MtpIdentity, Outcome, TransferOp
from tests.helpers.fakes import SinkSpy
from tests.unit.domain.test_markers import MARKER

CONSTANTS = [
    scripts.ROOT_EXISTS,
    scripts.CREATE_ROOT,
    scripts.CAPACITY,
    scripts.FETCH,
    scripts.PUT,
    scripts.DELETE,
    scripts.SCAN,
    scripts.LIST,
    scripts.RUN,
]
Answer = Sequence[str] | Callable[[Script], Sequence[str]]


class Shell:
    """Answers each script with scripted lines, feeding them to the line callback."""

    def __init__(self, *answers: Answer) -> None:
        self.answers = list(answers)
        self.calls: list[Script] = []

    def __call__(
        self, script: Script, timeout: float | None, on_line: Callable[[str], None] | None
    ) -> PsResult:
        self.calls.append(script)
        answer = self.answers.pop(0)
        lines = answer(script) if callable(answer) else answer
        for line in lines:
            if on_line is not None:
                on_line(line)
        return PsResult(0, tuple(lines))


POLICY = ArrivalPolicy(600, 2 * 1024 * 1024)


def mtp(shell: Shell, tmp_path: Path, policy: ArrivalPolicy = POLICY) -> MtpDest:
    return MtpDest(
        "AYN Thor",
        "Internal shared storage",
        "ROMs",
        LocalRoot(str(tmp_path / "tmp")),
        shell,
        policy,
    )


@pytest.fixture
def store(tmp_path: Path) -> StoreRoot:
    root = tmp_path / "store"
    (root / "nes").mkdir(parents=True)
    (root / "nes" / "A.nes").write_bytes(b"abc")
    (root / "big.bin").write_bytes(b"\0" * 10)
    return StoreRoot(str(root))


# --- the arrival policy ------------------------------------------------------------------


def test_arrival_policy_from_config() -> None:
    policy = ArrivalPolicy.from_config(REGISTRY.defaults())
    assert policy == ArrivalPolicy(600, 2 * 1024 * 1024)
    assert (
        ArrivalPolicy.from_config(
            {**REGISTRY.defaults(), "mtp.arrival_floor": 90}
        ).floor_seconds
        == 90
    )
    assert policy.stall_seconds(1024) == 600
    assert policy.stall_seconds(8 * 1024**3) == 4096
    with pytest.raises(ValueError):
        ArrivalPolicy(0, 1)


def test_no_script_carries_a_literal_allowance() -> None:
    for text in CONSTANTS:
        assert "2MB" not in text and "[math]::Max" not in text
    assert "$env:RS_STALL" in scripts.PUT and "$env:RS_STALL" in scripts.FETCH
    assert "$stall = [double]$p[7]" in scripts.RUN


def test_single_arrival_policy(tmp_path: Path, store: StoreRoot) -> None:
    """Staging a file and sending it in a bulk run are given the same budget."""
    policy = ArrivalPolicy(1, 2)
    shell = Shell(["OK\t10"], ["START\t0", "DONE\t0\t10", "OK\tfinished"])
    dest = mtp(shell, tmp_path, policy)
    dest.put_file(dest.roots().roms.resolve("bios"), store.resolve("big.bin"))
    op = TransferOp(
        Action.SEND,
        dest.roots().roms.resolve("nes/big.bin"),
        Kind.FILE,
        10,
        store.resolve("big.bin"),
    )
    dest.run([op], SinkSpy(), threading.Event())
    staged = shell.calls[0].env["RS_STALL"]
    plan = (tmp_path / "tmp" / "run" / "plan.tsv").read_text(encoding="utf-8").split("\t")
    assert staged == plan[7].strip() == str(policy.stall_seconds(10)) == "5"


def test_names_reach_a_script_only_through_its_environment(
    tmp_path: Path, store: StoreRoot
) -> None:
    hostile = "$(Remove-Item -Recurse ~) `whoami` 'x'; echo.nes"
    (Path(store.base) / "nes" / hostile).write_bytes(b"x")
    shell = Shell(["OK\t1"], ["OK\tdeleted"])
    dest = mtp(shell, tmp_path)
    dest.put_file(dest.roots().roms.resolve("nes"), store.resolve(f"nes/{hostile}"))
    dest.delete_file(dest.roots().roms.resolve(f"nes/{hostile}"))
    for call in shell.calls:
        assert call.text in CONSTANTS
        assert hostile not in call.text
    assert shell.calls[0].env["RS_NAME"] == hostile
    assert shell.calls[1].env["RS_PARTS"] == "ROMs\nnes"


# --- the adapter against scripted output ----------------------------------------------


def test_mtp_declares_no_verification(tmp_path: Path) -> None:
    dest = mtp(Shell(), tmp_path)
    assert not dest.supports(DestVerify)
    assert dest.identity() == MtpIdentity("AYN Thor", "Internal shared storage")
    assert dest.describe() == "AYN Thor / Internal shared storage / ROMs"


def test_status_lines_map_to_the_taxonomy(tmp_path: Path) -> None:
    assert mtp(Shell(["OK\tyes"]), tmp_path).root_exists()
    assert not mtp(Shell(["noise", "OK\tno"]), tmp_path).root_exists()
    with pytest.raises(DestinationUnavailable, match="not connected"):
        mtp(Shell(["UNAVAILABLE\tthe device is not connected"]), tmp_path).root_exists()
    with pytest.raises(DestinationUnavailable, match="reported nothing"):
        mtp(Shell([]), tmp_path).root_exists()
    with pytest.raises(DestinationRootMissing):
        mtp(Shell(["FAILED\tnot created"]), tmp_path).create_root()
    mtp(Shell(["OK\tyes"]), tmp_path).create_root()


def test_capacity(tmp_path: Path) -> None:
    assert mtp(Shell(["OK\t1000\t400"]), tmp_path).capacity().free == 400


def test_markers(tmp_path: Path) -> None:
    assert mtp(Shell(["MISSING\tROM-Sync.json"]), tmp_path).read_marker() is None

    def arrive(script: Script) -> list[str]:
        Path(script.env["RS_LOCAL"], markers.NAME).write_bytes(markers.encode(MARKER))
        return ["OK\t100"]

    assert mtp(Shell(arrive), tmp_path).read_marker() == MARKER
    writing = Shell(["OK\t100"])
    mtp(writing, tmp_path).write_marker(MARKER)
    assert writing.calls[0].env["RS_NAME"] == markers.NAME
    assert writing.calls[0].env["RS_STALL"] == "600"


def test_a_marker_that_did_not_land_locally_is_none(tmp_path: Path) -> None:
    assert mtp(Shell(["OK\t100"]), tmp_path).read_marker() is None


def test_scan(tmp_path: Path) -> None:
    lines = [
        "TOP\tsnes",
        "TOP\tnes",
        "ITEM\tnes\tA.nes\tfile\t3",
        "ITEM\tnes\tA.srm\tfile\t1",
        "ITEM\tnes\tGame\tfolder\t9",
        "ITEM\tnes\tbad\tfile\tx",
        "OK\tscanned",
    ]
    shell = Shell(lines)
    found = mtp(shell, tmp_path).scan(["nes"], SinkSpy())
    assert found.folders == ("nes", "snes")
    assert [(i.name, i.kind, i.size) for i in found.items] == [
        ("A.nes", "file", 3),
        ("Game", "folder", 9),
    ]
    assert (shell.calls[0].env["RS_SYSTEMS"], shell.calls[0].env["RS_ALL"]) == ("nes", "0")
    every = Shell(["OK\tscanned"])
    mtp(every, tmp_path).scan(None, SinkSpy())
    assert every.calls[0].env["RS_ALL"] == "1"
    with pytest.raises(DestinationRootMissing):
        mtp(Shell(["MISSING\troot"]), tmp_path).scan(None, SinkSpy())


def test_list_paths(tmp_path: Path) -> None:
    dest = mtp(Shell(), tmp_path)
    assert dest.list_paths([]) == ()
    bios, absent = dest.roots().roms.resolve("bios"), dest.roots().device.resolve("Android/x")
    lines = [
        "PRESENT\t0",
        "ENTRY\t0\tpsx\tfolder\t",
        "ENTRY\t0\tscph.bin\tfile\t10",
        "ABSENT\t1",
        "OK",
    ]
    shell = Shell(lines)
    found = mtp(shell, tmp_path).list_paths([bios, absent])
    assert [(x.present, [(e.name, e.kind, e.size) for e in x.entries]) for x in found] == [
        (True, [("psx", "folder", None), ("scph.bin", "file", 10)]),
        (False, []),
    ]
    assert shell.calls[0].env["RS_PATHS"] == "ROMs\nbios\tAndroid\nx"


def test_files(tmp_path: Path, store: StoreRoot) -> None:
    dest = mtp(Shell(["OK\t3"], ["OK\tabsent"], ["FAILED\tstill present"]), tmp_path)
    assert dest.put_file(dest.roots().roms.resolve("bios"), store.resolve("nes/A.nes")) == 3
    assert dest.delete_file(dest.roots().roms.resolve("bios/A.nes")) is False
    with pytest.raises(TransferFailed):
        dest.delete_file(dest.roots().roms.resolve("bios/A.nes"))
    with pytest.raises(TransferFailed):
        dest.put_file(dest.roots().roms.resolve("bios"), store.resolve("nes/none.nes"))


def test_get_file(tmp_path: Path) -> None:
    def arrive(script: Script) -> list[str]:
        Path(script.env["RS_LOCAL"], script.env["RS_NAME"]).write_bytes(b"abc")
        return ["OK\t3"]

    pulled = LocalRoot(str(tmp_path / "pull")).child("run-1")
    dest = mtp(Shell(arrive, ["MISSING\tA.nes"]), tmp_path)
    got = dest.get_file(dest.roots().roms.resolve("nes/A.nes"), pulled)
    assert local(got).read_bytes() == b"abc"
    assert sorted(p.name for p in local(pulled).iterdir()) == ["A.nes"]
    with pytest.raises(DestinationItemMissing):
        dest.get_file(dest.roots().roms.resolve("nes/A.nes"), pulled)


def _ops(dest: MtpDest, store: StoreRoot) -> list[TransferOp]:
    roms = dest.roots().roms
    return [
        TransferOp(Action.REMOVE, roms.resolve("nes/Old.nes"), Kind.FILE, 0),
        TransferOp(
            Action.SEND, roms.resolve("nes/A.nes"), Kind.FILE, 3, store.resolve("nes/A.nes")
        ),
        TransferOp(
            Action.SEND, roms.resolve("nes/B.nes"), Kind.FILE, 3, store.resolve("nes/A.nes")
        ),
    ]


def test_run_reads_the_workers_lines(tmp_path: Path, store: StoreRoot) -> None:
    lines = [
        "START\t0",
        "DONE\t0\t",
        "START\t1",
        "BYTES\t1\t2",
        "DONE\t1\t3",
        "START\t2",
        "FAIL\t2\tFAILED\tthe copy stalled",
        "BYTES\t9\t1",
        "OK\tfinished",
    ]
    sink = SinkSpy()
    dest = mtp(Shell(lines), tmp_path)
    results = dest.run(_ops(dest, store), sink, threading.Event())
    assert [(r.outcome, r.size, r.digest) for r in results] == [
        (Outcome.DONE, None, None),
        (Outcome.DONE, 3, None),
        (Outcome.FAILED, None, None),
    ]
    assert results[2].error_message == "the copy stalled"
    assert any(getattr(e, "detail", None) == {"bytes": 2} for e in sink.events)
    plan = (tmp_path / "tmp" / "run" / "plan.tsv").read_text(encoding="utf-8").splitlines()
    assert plan[0].split("\t")[:6] == ["0", "remove", "ROMs/nes", "Old.nes", "file", "0"]


def test_cancel_is_left_for_the_worker_to_see_between_items(
    tmp_path: Path, store: StoreRoot
) -> None:
    cancel = threading.Event()
    seen: list[bool] = []

    def worker(script: Script) -> list[str]:
        cancel.set()
        return ["START\t0", "DONE\t0\t", "STOPPED\t1"]

    class Watch(SinkSpy):
        def emit(self, event: object) -> None:
            super().emit(event)
            seen.append(Path(tmp_path / "tmp" / "run" / "cancel").exists())

    dest = mtp(Shell(worker), tmp_path)
    results = dest.run(_ops(dest, store), Watch(), cancel)
    assert [r.outcome for r in results] == [Outcome.DONE, Outcome.SKIPPED, Outcome.SKIPPED]
    assert seen and all(seen)


def test_a_worker_that_dies_fails_what_it_did_not_finish(
    tmp_path: Path, store: StoreRoot
) -> None:
    dest = mtp(Shell(["START\t0", "DONE\t0\t", "UNAVAILABLE\tthe device went away"]), tmp_path)
    results = dest.run(_ops(dest, store), SinkSpy(), threading.Event())
    assert [r.outcome for r in results] == [Outcome.DONE, Outcome.FAILED, Outcome.FAILED]
    assert results[1].error_code == "dest.unavailable"
    assert results[1].error_message == "the device went away"
    quiet = mtp(Shell(["START\t0", "OK\tfinished"]), tmp_path)
    (lost, *_rest) = quiet.run(_ops(quiet, store), SinkSpy(), threading.Event())
    assert lost.error_message == "the transfer worker stopped"


def test_reading_from_the_device_shows_no_dialog() -> None:
    """A read copies through the file operation with every dialog off, so a
    failure is a result and never a Windows dialog that holds the probe until
    someone presses OK (F6-S10)."""
    fetch = scripts.FETCH[len(scripts.PROLOGUE) :]
    assert "CopyHere" not in fetch
    assert "[Mtp]::CopyQuietly(" in fetch
    assert "op.SetOperationFlags(FOF_NO_UI);" in scripts.PROLOGUE.split("CopyQuietly", 1)[1]
    assert "FOF_NO_UI = 0x0004 | 0x0010 | 0x0200 | 0x0400" in scripts.PROLOGUE
