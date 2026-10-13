"""Jobs: list, get, cancel, read as snapshots (F10-S13)."""

from __future__ import annotations

from pathlib import Path

from romsync_api.app import PREFIX
from romsync_api.models import JobList, JobView
from tests.unit.api.test_sync_routes import Later, setup


def test_list_get_cancel(tmp_path: Path) -> None:
    runner = Later()
    c, ref, _, _ = setup(tmp_path, runner=runner)
    job = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sync", json={}).json())
    listed = JobList.model_validate(c.get(f"{PREFIX}/jobs").json())
    assert [j.id for j in listed.jobs] == [job.id]
    assert JobView.model_validate(c.get(f"{PREFIX}/jobs/{job.id}").json()) == job
    cancelled = JobView.model_validate(c.post(f"{PREFIX}/jobs/{job.id}/cancel").json())
    assert cancelled.state == "cancelling"
    runner.run_all()
    done = JobView.model_validate(c.get(f"{PREFIX}/jobs/{job.id}").json())
    assert done.state == "cancelled" and done.finished is not None
    unchanged = JobView.model_validate(c.post(f"{PREFIX}/jobs/{job.id}/cancel").json())
    assert unchanged == done, "a finished job is left as it is"


def test_a_snapshot_carries_structured_progress(tmp_path: Path) -> None:
    c, ref, _, _ = setup(tmp_path)
    job = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sync", json={}).json())
    assert job.progress is not None
    assert job.progress.phase == "send" and job.progress.total == 1


def test_unknown_jobs(tmp_path: Path) -> None:
    c, ref, _, _ = setup(tmp_path)
    for got in (c.get(f"{PREFIX}/jobs/nope"), c.post(f"{PREFIX}/jobs/nope/cancel")):
        assert got.status_code == 404 and got.json()["error"]["code"] == "job.not_found"
    nothing = c.post(f"{PREFIX}/devices/{ref}/sync/cancel")
    assert nothing.status_code == 404
