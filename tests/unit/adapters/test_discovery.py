"""Discovery over every transport (F10-S26, added), with each transport that
cannot be asked a state rather than an error."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from romsync.adapters.dest_adb.adb import AdbDest, Completed
from romsync.adapters.dest_mtp.mtp import MtpDest, OnLine, PsResult
from romsync.adapters.dest_mtp.scripts import Script
from romsync.adapters.dest_volume.volume import VolumeDest
from romsync.adapters.discovery import (
    PROBE,
    ROMS,
    Discovery,
    TransportState,
    Waiting,
    overlaps,
    parse_probe,
)
from romsync.domain.errors import DestinationUnavailable
from romsync.domain.models import DeviceKind
from romsync.domain.paths import LocalRoot
from romsync.ports.dest import VolumeIdentity

ADB_LIST = (
    "List of devices attached\n"
    "R5CT1234 device usb:1-1 product:thor model:AYN_Thor device:thor\n"
    "9A8B7C unauthorized usb:1-2 transport_id:3\n"
)


def found(volumes: object, mtp: object) -> PsResult:
    body = json.dumps({"volumes": volumes, "mtp": mtp})
    return PsResult(0, ("noise", f"FOUND\t{body}"))


class Shell:
    def __init__(self, answer: PsResult) -> None:
        self.answer = answer
        self.scripts: list[str] = []

    def __call__(
        self, script: Script, timeout: float | None, on_line: OnLine | None
    ) -> PsResult:
        self.scripts.append(script.text)
        return self.answer


class Adb:
    def __init__(self, answer: Completed) -> None:
        self.answer = answer
        self.asked: list[list[str]] = []

    def __call__(self, argv: Sequence[str], timeout: float) -> Completed:
        self.asked.append(list(argv))
        return self.answer


SETTINGS: dict[str, object] = {
    "adb.enabled": True,
    "adb.path": "",
    "mtp.enabled": True,
    "mtp.arrival_floor": 600,
    "mtp.arrival_rate": 2 * 1024 * 1024,
    "store.root": "",
}


def discovery(
    tmp_path: Path,
    shell: PsResult | None = None,
    adb: Completed | None = None,
    which: str | None = "/tools/adb",
    **settings: object,
) -> tuple[Discovery, Shell, Adb]:
    ps = Shell(
        shell
        or found(
            [{"letter": "E:", "label": "SD"}, {"letter": "F:", "label": None}],
            [{"name": "Thor", "storages": ["Internal shared storage", "SD card"]}],
        )
    )
    bridge = Adb(adb or Completed(0, ADB_LIST.encode()))
    values = {**SETTINGS, **{k.replace("_", "."): v for k, v in settings.items()}}
    made = Discovery(
        values.__getitem__,
        ps,
        bridge,
        LocalRoot(str(tmp_path / "tmp")),
        lambda storage: VolumeIdentity("1234ABCD", str(storage)),
        which=lambda name: which,
    )
    return made, ps, bridge


def test_every_transport_is_asked(tmp_path: Path) -> None:
    probe, ps, adb = discovery(tmp_path)
    dests = probe()
    assert [type(d) for d in dests] == [
        VolumeDest,
        VolumeDest,
        MtpDest,
        MtpDest,
        AdbDest,
        Waiting,
    ]
    assert ps.scripts == [PROBE] and adb.asked == [["/tools/adb", "devices", "-l"]]
    for dest in dests[:5]:
        assert dest.roots().roms_at.relative("/") == ROMS, "every ROMs folder is ROMs"
    drive = dests[0]
    assert isinstance(drive, VolumeDest) and drive.storage == Path("E:\\")
    thor = dests[4]
    assert isinstance(thor, AdbDest)
    assert (thor.serial, thor.model, thor.storage) == ("R5CT1234", "AYN Thor", "/sdcard")
    assert [(s.kind, s.available) for s in probe.transports] == [
        ("volume", True),
        ("mtp", True),
        ("adb", True),
    ]


def test_a_device_waiting_on_its_prompt_is_listed_with_why(tmp_path: Path) -> None:
    waiting = discovery(tmp_path)[0]()[-1]
    assert isinstance(waiting, Waiting) and waiting.kind is DeviceKind.ADB
    assert waiting.describe() == "9A8B7C (adb)"
    for ask in (
        waiting.identity,
        waiting.root_exists,
        waiting.create_root,
        waiting.read_marker,
        lambda: waiting.write_marker(None),
    ):
        with pytest.raises(
            DestinationUnavailable, match="unauthorized: accept the debugging prompt"
        ):
            ask()
    offline = Completed(0, b"List of devices attached\nZZ1 offline\nZZ2 sideload\n")
    later = discovery(tmp_path, adb=offline)[0]()[-2:]
    with pytest.raises(DestinationUnavailable, match="offline: unplug"):
        later[0].identity()  # type: ignore[attr-defined]
    with pytest.raises(DestinationUnavailable, match="sideload: not ready"):
        later[1].identity()  # type: ignore[attr-defined]


def test_an_absent_tool_is_a_state_not_an_error(tmp_path: Path) -> None:
    probe, _, adb = discovery(tmp_path, which=None)
    dests = probe()
    assert len(dests) == 4 and adb.asked == [], "drives and portable devices still found"
    assert probe.transports[-1] == TransportState(
        "adb", False, "the Android debug bridge (adb) was not found on the PATH"
    )
    configured, _, _ = discovery(tmp_path, which=None, adb_path="X:/tools/adb.exe")
    configured()
    assert configured.transports[-1].detail.endswith("not found at X:/tools/adb.exe")


def test_a_transport_turned_off_is_not_asked(tmp_path: Path) -> None:
    probe, _, adb = discovery(tmp_path, adb_enabled=False, mtp_enabled=False)
    assert [type(d) for d in probe()] == [VolumeDest, VolumeDest]
    assert adb.asked == []
    assert [(s.kind, s.available, s.detail) for s in probe.transports][1:] == [
        ("mtp", False, "turned off in Settings"),
        ("adb", False, "turned off in Settings"),
    ]


def test_a_failing_probe_leaves_the_others_asked(tmp_path: Path) -> None:
    probe, _, _ = discovery(tmp_path, shell=PsResult(1, ("something broke",)))
    assert [type(d) for d in probe()] == [AdbDest, Waiting]
    assert [(s.kind, s.available) for s in probe.transports] == [
        ("volume", False),
        ("mtp", False),
        ("adb", True),
    ]
    assert "the device probe reported nothing" in probe.transports[0].detail
    silent, _, _ = discovery(tmp_path, adb=Completed(1, b"", b"daemon not running"))
    assert [type(d) for d in silent()] == [VolumeDest, VolumeDest, MtpDest, MtpDest]
    assert silent.transports[-1].detail == "adb did not answer: daemon not running"


def test_powershell_unrolled_answers_are_read() -> None:
    one = found({"letter": "E:", "label": "SD"}, {"name": "Thor", "storages": "Internal"})
    assert parse_probe(one.lines) == ([("E:", "SD")], [("Thor", "Internal")])
    empty = found(None, [{"name": "Phone", "storages": None}, {"name": ""}])
    assert parse_probe(empty.lines) == ([], [])


def test_the_composed_engine_lists_what_discovery_finds(tmp_path: Path) -> None:
    from romsync.compose import build
    from tests.helpers.fakes import FrozenClock

    made: list[Discovery] = []

    def discover(setting: object, data: Path) -> Discovery:
        probe, _, _ = discovery(tmp_path, shell=found([], []))
        made.append(probe)
        return probe

    engine = build(tmp_path / "data", clock=FrozenClock(), discover=discover)
    attached = engine.devices.refresh()
    assert [a.description for a in attached] == ["AYN Thor (adb) /sdcard/ROMs"]
    assert [(b.kind, b.description, b.reason) for b in engine.devices.blocked] == [
        ("adb", "9A8B7C (adb)", "unauthorized: accept the debugging prompt on the device")
    ]
    assert made[0].transports[-1] == TransportState("adb", True, "2 device(s)")


def test_the_librarys_own_drive_folder_is_never_a_destination(tmp_path: Path) -> None:
    """A drive whose ROMs folder is, holds or sits in the library is listed as
    waiting, never offered: a sync to it would write over the library (F16-S4)."""
    probe, _, _ = discovery(tmp_path, store_root="e:/ROMs/")
    drives = probe()[:2]
    assert isinstance(drives[0], Waiting) and drives[0].describe() == "E:\\ROMs"
    assert isinstance(drives[1], VolumeDest), "another drive is offered as before"


@pytest.mark.parametrize(
    ("a", "b", "overlap"),
    [
        ("E:\\ROMs", "e:/roms", True),
        ("E:\\ROMs", "E:\\ROMs\\snes", True),
        ("E:\\", "E:\\ROMs", True),
        ("D:\\ROMs", "D:\\Games\\ROMs", False),
        ("E:\\ROMs", "E:\\ROMs2", False),
    ],
)
def test_overlaps(a: str, b: str, overlap: bool) -> None:
    assert overlaps(a, b) is overlap
