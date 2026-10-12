"""Every destination attached right now, over every transport that can say
(F10-S26, added).

Drives and MTP devices come from one PowerShell probe, read as version 1 read
them: fixed and removable drives other than the system drive, and the
portable devices Windows lists under This PC, each with its storages. ADB
devices come from `adb devices -l`. Each destination keeps its ROMs in a
`ROMs` folder at the top of its storage, as version 1 did and as every
profile this version makes records.

A transport that cannot be asked is a state, not an error (F13-S8): turned
off in Settings, its tool absent, or its probe failing. The others are still
asked. A device that is attached but cannot be read yet, an ADB device
waiting on its debugging prompt say, is handed on as a destination whose
identity cannot be read, so the devices page lists it with the reason
(F10-S23).
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final, NoReturn

from romsync.adapters.dest_adb import commands as cmd
from romsync.adapters.dest_adb.adb import AdbDest, Runner
from romsync.adapters.dest_common import Declared, make_roots
from romsync.adapters.dest_mtp.mtp import MtpDest, PowerShell
from romsync.adapters.dest_mtp.scripts import ArrivalPolicy, Script
from romsync.adapters.dest_volume.volume import Identify, VolumeDest
from romsync.domain.errors import DestinationToolMissing, DestinationUnavailable
from romsync.domain.models import DeviceKind
from romsync.domain.paths import LocalRoot
from romsync.ports.dest import Dest, DestIdentity

#: Where every destination found keeps its ROMs, below the top of its storage.
ROMS: Final = "ROMs"
#: Where an ADB device's shared storage is.
ADB_STORAGE: Final = "/sdcard"
#: Seconds the probes may take: Windows answers slowly while a device mounts.
PROBE_TIMEOUT: Final = 90.0

#: Drives and portable devices, one JSON line after `FOUND` and a tab.
PROBE: Final = r"""
$ErrorActionPreference = 'SilentlyContinue'
$vols = @(Get-CimInstance Win32_LogicalDisk |
  Where-Object { $_.DriveType -in 2,3 -and $_.DeviceID -ne $env:SystemDrive } |
  ForEach-Object { [ordered]@{ letter=$_.DeviceID; label=$_.VolumeName } })
$devs = @()
$shell = New-Object -ComObject Shell.Application
foreach ($i in $shell.NameSpace(17).Items()) {
  if ($i.IsFolder -and $i.Path -like '*::*usb*') {
    $stores = @()
    try { foreach ($s in $i.GetFolder.Items()) { $stores += [string]$s.Name } } catch {}
    $devs += [ordered]@{ name=[string]$i.Name; storages=$stores }
  }
}
'FOUND' + "`t" + ([ordered]@{ volumes=$vols; mtp=$devs } | ConvertTo-Json -Compress -Depth 4)
"""

#: What an ADB device's state means to the person, for each state adb reports
#: other than `device`.
WAITING: Final = {
    "unauthorized": "unauthorized: accept the debugging prompt on the device",
    "offline": "offline: unplug the cable and plug it in again",
    "no permissions": "no permissions: the computer may not use this device yet",
    "authorizing": "authorizing: accept the debugging prompt on the device",
}

Setting = Callable[[str], object]
Which = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class TransportState:
    """Whether a transport was asked this time, and in words what it said."""

    kind: str
    available: bool
    detail: str


class Waiting(Declared):
    """A device attached but not readable yet. Asking who it is says why."""

    ROLES: ClassVar[frozenset[type]] = frozenset({DestIdentity})

    def __init__(self, kind: DeviceKind, description: str, reason: str) -> None:
        self.kind = kind
        self._description = description
        self._reason = reason
        self._roots = make_roots(description, ROMS)

    def describe(self) -> str:
        return self._description

    def _refuse(self) -> NoReturn:
        raise DestinationUnavailable(self._reason)

    def identity(self) -> NoReturn:
        self._refuse()

    def root_exists(self) -> NoReturn:
        self._refuse()

    def create_root(self) -> NoReturn:
        self._refuse()

    def read_marker(self) -> NoReturn:
        self._refuse()

    def write_marker(self, marker: object) -> NoReturn:
        self._refuse()


def _listed(value: object) -> list[object]:
    """A JSON value PowerShell may have unrolled: a list, one item, or nothing."""
    if isinstance(value, list):
        return value
    return [] if value in (None, "", {}) else [value]


def parse_probe(lines: Sequence[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(drive letter, label) pairs and (device, storage) pairs from the probe's output."""
    for line in reversed(lines):
        word, _, rest = line.partition("\t")
        if word == "FOUND":
            found = json.loads(rest)
            break
    else:
        raise DestinationUnavailable("the device probe reported nothing")
    volumes = [
        (str(v["letter"]), str(v.get("label") or ""))
        for v in _listed(found.get("volumes"))
        if isinstance(v, dict) and v.get("letter")
    ]
    portable = [
        (str(d["name"]), str(s))
        for d in _listed(found.get("mtp"))
        if isinstance(d, dict) and d.get("name")
        for s in _listed(d.get("storages"))
        if s
    ]
    return volumes, portable


class Discovery:
    """The probe the composed engine asks for what is attached."""

    def __init__(
        self,
        setting: Setting,
        powershell: PowerShell,
        adb: Runner,
        scratch: LocalRoot,
        identify: Identify,
        which: Which = shutil.which,
    ) -> None:
        self._setting = setting
        self._ps = powershell
        self._adb = adb
        self._scratch = scratch
        self._identify = identify
        self._which = which
        self.transports: tuple[TransportState, ...] = ()

    def __call__(self) -> tuple[Dest, ...]:
        states: list[TransportState] = []
        found: list[Dest] = []
        found += self._windows(states)
        found += self._android(states)
        self.transports = tuple(states)
        return tuple(found)

    # --- drives and portable devices ---------------------------------------------------

    def _windows(self, states: list[TransportState]) -> list[Dest]:
        try:
            result = self._ps(Script(PROBE, {}), PROBE_TIMEOUT, None)
            volumes, portable = parse_probe(result.lines)
        except (DestinationUnavailable, ValueError) as e:
            states.append(TransportState("volume", False, f"drives were not read: {e}"))
            states.append(TransportState("mtp", False, f"devices were not read: {e}"))
            return []
        found: list[Dest] = [
            VolumeDest(Path(f"{letter}\\"), ROMS, self._identify) for letter, _ in volumes
        ]
        states.append(TransportState("volume", True, f"{len(volumes)} drive(s)"))
        if not self._setting("mtp.enabled"):
            states.append(TransportState("mtp", False, "turned off in Settings"))
            return found
        policy = ArrivalPolicy(
            int(str(self._setting("mtp.arrival_floor"))),
            int(str(self._setting("mtp.arrival_rate"))),
        )
        found += [
            MtpDest(device, storage, ROMS, self._scratch, self._ps, policy)
            for device, storage in portable
        ]
        states.append(TransportState("mtp", True, f"{len(portable)} storage(s)"))
        return found

    # --- Android debug bridge ------------------------------------------------------------

    def _android(self, states: list[TransportState]) -> list[Dest]:
        if not self._setting("adb.enabled"):
            states.append(TransportState("adb", False, "turned off in Settings"))
            return []
        try:
            exe = cmd.locate(str(self._setting("adb.path") or ""), self._which)
        except DestinationToolMissing as e:
            states.append(TransportState("adb", False, str(e)))
            return []
        listed = self._adb(cmd.devices(exe), PROBE_TIMEOUT)
        if listed.code != 0:
            states.append(TransportState("adb", False, f"adb did not answer: {listed.why()}"))
            return []
        found: list[Dest] = []
        for device in cmd.parse_devices(listed.text):
            if device.usable:
                found.append(
                    AdbDest(
                        exe,
                        device.serial,
                        ROMS,
                        self._scratch,
                        self._adb,
                        storage=ADB_STORAGE,
                        model=device.model,
                    )
                )
            else:
                reason = WAITING.get(device.state, f"{device.state}: not ready")
                found.append(
                    Waiting(DeviceKind.ADB, f"{device.model or device.serial} (adb)", reason)
                )
        states.append(TransportState("adb", True, f"{len(found)} device(s)"))
        return found
