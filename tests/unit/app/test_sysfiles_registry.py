"""The system-files registry is data (F8-S1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from romsync.adapters.dest_fake import FakeDest
from romsync.app.sysfiles import SystemFiles
from romsync.app.sysfiles_registry import DATA, LOCATIONS, load
from romsync.ports.repo import Repos
from tests.unit.app.sysfiles_kit import DEVICE, build

SATURN = {
    "key": "saturn",
    "emulator": "Yaba Sanshiro",
    "package": "yabasanshiro",
    "note": "Needs a Saturn BIOS.",
    "requires": (
        {
            "name": "saturn_bios.bin",
            "required": True,
            "source": ("bios", "saturn_bios.bin"),
            "install": "staged",
        },
    ),
}


def test_data_driven(tmp_path: Path, r: Repos) -> None:
    systems = load((*DATA, SATURN))
    assert systems[-1].key == "saturn"
    assert systems[-1].requirements[0].install is LOCATIONS["staged"]
    sysfiles, files = build(tmp_path, r)
    with_saturn = type(sysfiles)(
        files, r.sysfiles, sysfiles._clock, sysfiles._scratch, sysfiles.template, 1024, systems
    )
    report = with_saturn.report(DEVICE, FakeDest().roots())
    saturn = next(s for s in report.systems if s.system.key == "saturn")
    assert saturn.missing == ("saturn_bios.bin",)
    assert isinstance(with_saturn, SystemFiles)


def test_version_ones_rows_load() -> None:
    systems = {s.key: s for s in load()}
    assert len(systems) == len(DATA)
    psx = systems["psx"]
    assert {r.group for r in psx.requirements} == {"ps1"}
    assert systems["switch"].requirements[2].match == r"\.nca$"


def _with(**change: object) -> dict[str, object]:
    row = dict(SATURN)
    requirement = dict(SATURN["requires"][0])  # type: ignore[index]
    for key, value in change.items():
        if key in ("key", "package"):
            row[key] = value
        else:
            requirement[key] = value
    row["requires"] = (requirement,)
    return row


@pytest.mark.parametrize(
    "row",
    [
        _with(install="the-moon"),
        _with(source=("cloud", "x")),
        _with(source="bios"),
        _with(md5s=("not-an-md5",)),
        _with(md5s="abc"),
        _with(name="sub/dir.bin"),
        _with(name=""),
        _with(match="("),
        _with(key="Saturn!"),
        _with(package="("),
    ],
)
def test_a_malformed_row_is_refused(row: dict[str, object]) -> None:
    with pytest.raises(Exception):  # noqa: B017 - ValueError or re.error, both refusals
        load((row,))


def test_a_key_appears_once() -> None:
    with pytest.raises(ValueError, match="new system key"):
        load((SATURN, SATURN))
