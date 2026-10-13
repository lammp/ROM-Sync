"""Seeding an engine's database from a test, through the repositories."""

from __future__ import annotations

from pathlib import Path

from romsync.adapters.db_sqlite.connect import connect
from romsync.adapters.db_sqlite.repos import repos
from romsync.compose import DATABASE
from romsync.domain.models import GameUnit, Kind, Member, SystemKey
from romsync.ports.repo import GameMeta, Repos, SystemInfo, TagRecord

NES = SystemKey("nes")
PS2 = SystemKey("ps2")


def stores(data: Path) -> Repos:
    return repos(connect(data / DATABASE, 1000))


def library(data: Path) -> dict[str, int]:
    r = stores(data)
    r.games.put_system(SystemInfo(NES, "Nintendo Entertainment System", (".nes", ".zip")))
    r.games.put_system(SystemInfo(PS2, "PlayStation 2", (".iso",)))
    contra = r.games.add(
        GameUnit(NES, "Contra (USA).nes", Kind.FILE, 131_088, 1_700_000_000.0, "Contra", "USA"),
        "2026-01-01",
    )
    game = r.games.add(
        GameUnit(
            PS2,
            "Okami (USA)",
            Kind.FOLDER,
            300,
            1_700_000_100.0,
            "Okami",
            "USA",
            (Member("disc1.iso", 100, 1.0), Member("disc2.iso", 200, 2.0)),
        ),
        "2026-01-01",
    )
    r.games.set_meta(
        contra,
        GameMeta(
            state="matched",
            confidence=0.97,
            igdb_id=1234,
            igdb_name="Contra",
            summary="Run and gun.",
            release_date=540_000_000,
            rating=81.5,
            rating_count=320,
            genres=("Shooter", "Platform"),
            cover="1234.jpg",
        ),
    )
    r.tags.put(contra, TagRecord("Contra", "franchise", "accepted", "rules"))
    r.tags.put(contra, TagRecord("co-op", "user"))
    r.tags.put(contra, TagRecord("Konami", "franchise", "proposed", "rules"))
    return {"contra": contra, "okami": game}
