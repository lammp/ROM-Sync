"""Tag decisions stand; the franchise pass as a job (F10-S18)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync.domain.models import GameUnit, Kind
from romsync.jobs.registry import inline
from romsync_api.app import PREFIX, create_app
from romsync_api.models import JobView, TagList
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE


def setup(tmp_path: Path) -> tuple[TestClient, dict[str, int]]:
    data = tmp_path / "data"
    engine = build(data, clock=FrozenClock(), runner=inline)
    ids = seed.library(data)
    ids["mario"] = seed.stores(data).games.add(
        GameUnit(
            seed.NES,
            "Super Mario Bros. (World).nes",
            Kind.FILE,
            40_976,
            1.0,
            "Super Mario Bros.",
        ),
        "2026-01-01",
    )
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c, ids


def tags(c: TestClient, game_id: int) -> dict[tuple[str, str], str]:
    body = TagList.model_validate(c.get(f"{PREFIX}/games/{game_id}/tags").json())
    return {(t.tag, t.kind): t.state for t in body.tags}


def test_decision_stands(tmp_path: Path) -> None:
    c, ids = setup(tmp_path)
    okami = ids["mario"]
    first = JobView.model_validate(c.post(f"{PREFIX}/library/franchises").json())
    assert (first.kind, first.state) == ("franchise", "done")
    proposed = {k: v for k, v in tags(c, okami).items() if k[1] == "franchise"}
    assert proposed and set(proposed.values()) == {"proposed"}
    (name, kind) = next(iter(proposed))
    rejected = c.post(
        f"{PREFIX}/games/{okami}/tags/decide", json={"tag": name, "kind": kind, "accept": False}
    )
    assert rejected.status_code == 200
    again = JobView.model_validate(c.post(f"{PREFIX}/library/franchises").json())
    assert again.result is not None
    assert tags(c, okami)[(name, kind)] == "rejected", "the next pass leaves the decision alone"
    c.post(
        f"{PREFIX}/games/{okami}/tags/decide", json={"tag": name, "kind": kind, "accept": True}
    )
    assert tags(c, okami)[(name, kind)] == "accepted"


def test_a_person_adds_and_removes_tags(tmp_path: Path) -> None:
    c, ids = setup(tmp_path)
    contra = ids["contra"]
    added = TagList.model_validate(
        c.post(f"{PREFIX}/games/{contra}/tags", json={"tag": "  two   player  "}).json()
    )
    found = {t.tag: t for t in added.tags}
    assert found["two player"].state == "accepted" and found["two player"].source == "person"
    removed = c.post(
        f"{PREFIX}/games/{contra}/tags/remove", json={"tag": "two player", "kind": "user"}
    )
    assert ("two player", "user") not in {(t["tag"], t["kind"]) for t in removed.json()["tags"]}


@pytest.mark.parametrize("tag", ["", "   ", "x" * 81])
def test_a_tag_has_a_length(tmp_path: Path, tag: str) -> None:
    c, ids = setup(tmp_path)
    refused = c.post(f"{PREFIX}/games/{ids['contra']}/tags", json={"tag": tag})
    assert refused.status_code == 422 and refused.json()["error"]["field"] == "tag"


def test_an_unknown_game(tmp_path: Path) -> None:
    c, _ = setup(tmp_path)
    assert c.get(f"{PREFIX}/games/999/tags").status_code == 404
    assert c.post(f"{PREFIX}/games/999/tags", json={"tag": "x"}).status_code == 404
