"""The match and cover passes as jobs, and re-matching one game (F10-S17)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.compose import build
from romsync.jobs.registry import inline
from romsync.ports.metadata import Candidate, Platform
from romsync_api.app import PREFIX, create_app
from romsync_api.models import GameDetail, JobView
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fake_metadata import RecordedMetadata
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE

CONTRA = Candidate(
    1234, "Contra", platforms=(18,), cover_image_id="co1abc", genres=("Shooter",)
)
OKAMI = Candidate(5678, "Okami", platforms=(8,), summary="A wolf.")
LISTING = '<a href="Contra%20(USA).png">Contra (USA).png</a>'


class Web:
    def __init__(self) -> None:
        self.asked: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.asked.append(url)
        if url.endswith("/Named_Boxarts/"):
            return LISTING.encode()
        return b"\x89PNG" + b"\x00" * 200


def setup(tmp_path: Path, metadata: RecordedMetadata) -> tuple[TestClient, dict[str, int], Web]:
    web = Web()
    data = tmp_path / "data"
    engine = build(
        data, clock=FrozenClock(), runner=inline, metadata=lambda: metadata, fetch=web
    )
    ids = seed.library(data)
    stores = seed.stores(data)
    from romsync.ports.repo import GameMeta

    stores.games.set_meta(ids["contra"], GameMeta())
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c, ids, web


def recorded() -> RecordedMetadata:
    return RecordedMetadata(
        searches={("Contra", 18): (CONTRA,)},
        slugs={"okami": OKAMI},
        known_platforms=(
            Platform(18, "Nintendo Entertainment System"),
            Platform(8, "PlayStation 2"),
        ),
    )


def game(c: TestClient, game_id: int) -> GameDetail:
    return GameDetail.model_validate(c.get(f"{PREFIX}/games/{game_id}").json())


def test_match_job(tmp_path: Path) -> None:
    c, ids, web = setup(tmp_path, recorded())
    job = JobView.model_validate(c.post(f"{PREFIX}/library/match").json())
    assert (job.kind, job.state) == ("match", "done")
    assert job.result is not None and job.result["matched"] == 1
    contra = game(c, ids["contra"])
    assert (contra.igdb_id, contra.cover) == (1234, "co1abc.jpg")
    assert (tmp_path / "data" / "covers" / "co1abc.jpg").is_file()
    assert any("co1abc" in url for url in web.asked)


def test_rematch(tmp_path: Path) -> None:
    c, ids, _ = setup(tmp_path, recorded())
    job = JobView.model_validate(
        c.post(
            f"{PREFIX}/games/{ids['okami']}/rematch",
            json={"ref": "https://www.igdb.com/games/okami"},
        ).json()
    )
    assert (job.kind, job.target, job.state) == ("rematch", f"game:{ids['okami']}", "done")
    assert game(c, ids["okami"]).igdb_name == "Okami"
    nothing = JobView.model_validate(
        c.post(f"{PREFIX}/games/{ids['okami']}/rematch", json={"ref": "no-such-game"}).json()
    )
    assert (nothing.state, nothing.error_code) == ("failed", "metadata.not_found")
    assert c.post(f"{PREFIX}/games/999/rematch", json={"ref": "okami"}).status_code == 404


def test_cover_job_fills_from_the_thumbnails(tmp_path: Path) -> None:
    c, ids, _web = setup(tmp_path, recorded())
    job = JobView.model_validate(c.post(f"{PREFIX}/library/covers").json())
    assert (job.kind, job.state) == ("covers", "done")
    assert job.result is not None and job.result["filled"] == 1
    assert game(c, ids["contra"]).cover is not None


def test_missing_credentials_fail_the_pass(tmp_path: Path) -> None:
    data = tmp_path / "data"
    engine = build(data, clock=FrozenClock(), runner=inline)
    seed.library(data)
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    job = JobView.model_validate(c.post(f"{PREFIX}/library/match").json())
    assert (job.state, job.error_code) == ("failed", "metadata.credentials_missing")


def test_igdb_covers_fetch_once(tmp_path: Path) -> None:
    from romsync.adapters.metadata_igdb.covers import IgdbCovers

    asked: list[str] = []

    def get(url: str) -> bytes:
        asked.append(url)
        return b"jpeg"

    covers = IgdbCovers(tmp_path, get)
    assert covers.fetch_igdb("co1abc") == "co1abc.jpg"
    assert covers.fetch_igdb("co1abc") == "co1abc.jpg"
    assert len(asked) == 1
    assert covers.fetch_igdb("../evil") is None
    assert IgdbCovers(tmp_path, lambda _u: b"").fetch_igdb("empty") is None

    def down(_url: str) -> bytes:
        raise OSError("offline")

    assert IgdbCovers(tmp_path, down).fetch_igdb("co2") is None
