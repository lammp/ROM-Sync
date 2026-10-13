"""The metadata action as a job (F5-S12), and re-matching one game (F10-S17)."""

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


def run(c: TestClient, refresh: bool = False) -> JobView:
    return JobView.model_validate(
        c.post(f"{PREFIX}/library/metadata", json={"refresh": refresh}).json()
    )


def test_an_update_matches_what_needs_it_then_fills_covers(tmp_path: Path) -> None:
    c, ids, web = setup(tmp_path, recorded())
    job = run(c)
    assert (job.kind, job.state) == ("metadata", "done")
    assert job.result is not None
    assert {k: job.result[k] for k in ("refresh", "games", "matched", "unmatched")} == {
        "refresh": 0,
        "games": 2,
        "matched": 1,
        "unmatched": 1,
    }
    assert job.result["not_found"] == 1, "Okami has no cover and libretro lists none for it"
    contra = game(c, ids["contra"])
    assert (contra.igdb_id, contra.cover) == (1234, "co1abc.jpg")
    assert (tmp_path / "data" / "covers" / "co1abc.jpg").is_file()
    assert any("co1abc" in url for url in web.asked)
    again = run(c)
    assert again.result is not None and again.result["games"] == 0, "nothing new to look up"


def test_a_refresh_matches_every_game_again_but_a_pin(tmp_path: Path) -> None:
    c, ids, _ = setup(tmp_path, recorded())
    c.post(f"{PREFIX}/games/{ids['okami']}/rematch", json={"ref": "okami"})
    from romsync.ports.repo import GameMeta

    seed.stores(tmp_path / "data").games.set_meta(
        ids["contra"], GameMeta(state="matched", confidence=0.6, igdb_id=1, igdb_name="Old")
    )
    update = run(c).result
    assert update is not None and update["games"] == 0, "an update leaves matched games alone"
    job = run(c, refresh=True)
    assert job.result is not None
    assert (job.result["refresh"], job.result["games"], job.result["matched"]) == (1, 1, 1)
    assert game(c, ids["contra"]).igdb_name == "Contra", "matched again"
    assert game(c, ids["okami"]).igdb_name == "Okami", "the pin is kept"


def test_without_credentials_the_match_is_skipped_and_covers_still_fill(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data"
    engine = build(data, clock=FrozenClock(), runner=inline, fetch=Web())
    seed.library(data)
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    job = run(c)
    assert job.state == "done" and job.result is not None
    assert job.result["no_credentials"] == 1 and "matched" not in job.result
    assert "not_found" in job.result, "libretro covers need no account"


def test_covers_follow_their_setting(tmp_path: Path) -> None:
    c, _, _ = setup(tmp_path, recorded())
    c.post(f"{PREFIX}/settings", json={"values": {"match.auto_libretro_covers": False}})
    job = run(c)
    assert job.result is not None and "filled" not in job.result


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
