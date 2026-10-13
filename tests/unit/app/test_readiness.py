"""Readiness is state, not presentation (F8-S6)."""

from __future__ import annotations

from pathlib import Path

from romsync.adapters.dest_fake import FakeDest
from romsync.app import sysfiles as module
from romsync.app.sysfiles import Installed, Readiness, Staged, Staging, SystemState
from romsync.ports.repo import Repos
from tests.unit.app.sysfiles_kit import DEVICE, build, put

DUCKSTATION = "Android/data/com.github.stenzek.duckstation/files/bios"
BUTTONS = {"add", "update", "remove", "install", "stage", "unstage", "button"}


def _system(report: object, key: str) -> SystemState:
    return next(s for s in report.systems if s.system.key == key)  # type: ignore[attr-defined]


def test_state_not_presentation(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = FakeDest()
    put(dest, "ROM-Sync/nds/bios7.bin", b"melonds-bios7")
    sysfiles.survey(DEVICE, dest)
    report = sysfiles.report(DEVICE, dest.roots())
    for enum in (Staged, Installed, Readiness, Staging):
        assert not {v.value for v in enum} & BUTTONS, enum.__name__
    psx = _system(report, "psx")
    assert psx.staging is Staging.ABSENT
    assert {r.installed for r in psx.requirements} == {Installed.NOT_APPLICABLE}
    assert psx.readiness is Readiness.MISSING, (
        "a device with no app folders cannot show it installed"
    )
    nds = _system(report, "nds")
    states = {r.requirement.name: (r.staged, r.installed) for r in nds.requirements}
    assert states["bios7.bin"] == (Staged.CURRENT, Installed.INSTALLED)
    assert states["bios9.bin"] == (Staged.ABSENT, Installed.MISSING)
    assert nds.staging is Staging.OUTDATED and nds.staged_any
    assert nds.readiness is Readiness.MISSING
    assert nds.missing == ("bios9.bin", "firmware.bin")


def test_staging_never_makes_a_system_ready(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = FakeDest()
    put(dest, "Android/data/com.github.stenzek.duckstation/files/x", b"")
    sysfiles.survey(DEVICE, dest)
    sysfiles.stage(DEVICE, dest, "psx")
    psx = _system(sysfiles.report(DEVICE, dest.roots()), "psx")
    assert psx.staging is Staging.CURRENT
    assert psx.readiness is Readiness.MISSING
    put(dest, f"{DUCKSTATION}/scph5501.bin", b"ps1-usa")
    sysfiles.survey(DEVICE, dest)
    psx = _system(sysfiles.report(DEVICE, dest.roots()), "psx")
    assert psx.readiness is Readiness.READY, "one BIOS of the group is enough"
    assert psx.missing == ()


def test_before_a_survey_everything_is_unknown(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    report = sysfiles.report(DEVICE, FakeDest().roots())
    assert report.surveyed_at is None
    nds = _system(report, "nds")
    assert (nds.readiness, nds.staging) == (Readiness.UNKNOWN, Staging.UNKNOWN)
    assert {r.staged for r in nds.requirements} == {Staged.UNKNOWN}
    assert _system(report, "nes").readiness is Readiness.NONE
    assert _system(report, "gba").staging is Staging.NOTHING_TO_STAGE


def test_an_emulator_not_installed_is_unseen(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = FakeDest()
    put(dest, "Android/data/org.ppsspp.ppsspp/files/x", b"")
    put(dest, "Android/data/dev.eden.eden_emulator/files/keys/prod.keys", b"keys")
    put(
        dest,
        "Android/data/dev.eden.eden_emulator/files/nand/system/Contents/registered/a.nca",
        b"n",
    )
    sysfiles.survey(DEVICE, dest)
    report = sysfiles.report(DEVICE, dest.roots())
    assert report.apps["eden"] == "dev.eden.eden_emulator"
    assert _system(report, "psx").readiness is Readiness.UNSEEN
    assert _system(report, "psp").emulator_seen is True
    assert _system(report, "n3ds").readiness is Readiness.UNSEEN
    switch = _system(report, "switch")
    installed = {r.requirement.name: r.installed for r in switch.requirements}
    assert installed == {
        "prod.keys": Installed.INSTALLED,
        "title.keys": Installed.MISSING,
        "Firmware.zip": Installed.INSTALLED,
    }
    assert switch.readiness is Readiness.OPTIONAL


def test_a_different_copy_and_a_different_size(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = FakeDest()
    put(dest, "ROM-Sync/nds/bios7.bin", b"melonds-bios8")
    put(dest, "ROM-Sync/nds/bios9.bin", b"short")
    put(
        dest,
        "Android/data/com.github.stenzek.duckstation/files/bios/scph5501.bin",
        b"other size",
    )
    sysfiles.survey(DEVICE, dest)
    report = sysfiles.report(DEVICE, dest.roots())
    nds = {r.requirement.name: r.staged for r in _system(report, "nds").requirements}
    assert (nds["bios7.bin"], nds["bios9.bin"]) == (Staged.DIFFERENT, Staged.DIFFERENT)
    psx = {r.requirement.name: r.installed for r in _system(report, "psx").requirements}
    assert psx["scph5501.bin"] is Installed.DIFFERENT


def test_a_staged_file_with_nothing_in_the_store_is_present(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = FakeDest()
    put(dest, "ROM-Sync/nds/dsi_bios7.bin", b"dsi")
    put(dest, "ROM-Sync/nds/firmware.bin", b"x" * 2000)
    sysfiles.hash_limit = 4
    sysfiles.survey(DEVICE, dest)
    report = sysfiles.report(DEVICE, dest.roots())
    nds = {r.requirement.name: r.staged for r in _system(report, "nds").requirements}
    assert nds["dsi_bios7.bin"] is Staged.PRESENT
    assert nds["firmware.bin"] is Staged.DIFFERENT


def test_others_are_what_no_system_claims(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = FakeDest()
    put(dest, "ROM-Sync/nds/bios7.bin", b"melonds-bios7")
    put(dest, "ROM-Sync/nds/readme.txt", b"x")
    put(dest, "ROM-Sync/loose.bin", b"x")
    put(dest, "ROM-Sync/mystery/a.bin", b"x")
    sysfiles.survey(DEVICE, dest)
    report = sysfiles.report(DEVICE, dest.roots())
    assert [(o.path, o.name) for o in report.others] == [
        ("ROM-Sync", "loose.bin"),
        ("ROM-Sync", "mystery"),
        ("ROM-Sync/mystery", "a.bin"),
        ("ROM-Sync/nds", "readme.txt"),
    ]
    assert module.detect_apps(sysfiles.systems, []) == {}


def test_above_the_limit_a_matching_size_is_current(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r, hash_limit=4)
    dest = FakeDest()
    put(dest, "ROM-Sync/nds/bios9.bin", b"MELONDS-BIOS9")
    sysfiles.survey(DEVICE, dest)
    nds = {
        x.requirement.name: x.staged
        for x in _system(sysfiles.report(DEVICE, dest.roots()), "nds").requirements
    }
    assert nds["bios9.bin"] is Staged.CURRENT
