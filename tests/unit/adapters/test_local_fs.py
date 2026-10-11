"""Run folders and placement on this computer's filesystem."""

from __future__ import annotations

from pathlib import Path

from romsync.adapters.local_fs.runs import FsRunFolders


def test_a_run_folder_reads_back(tmp_path: Path) -> None:
    folders = FsRunFolders(tmp_path)
    assert not folders.exists(1)
    assert folders.read_status(1) is None
    assert folders.read_results(1) == ()
    folders.open(1, [{"action": "send", "name": "A.nes"}])
    folders.status(1, {"state": "running", "done": 0})
    folders.result(1, {"name": "A.nes", "outcome": "done"})
    assert folders.exists(1)
    assert folders.read_status(1) == {"state": "running", "done": 0}
    assert folders.read_results(1) == ({"name": "A.nes", "outcome": "done"},)


def test_a_line_cut_short_is_skipped(tmp_path: Path) -> None:
    folders = FsRunFolders(tmp_path)
    folders.open(2, [])
    folders.result(2, {"n": 1})
    with open(tmp_path / "runs" / "2" / "results.jsonl", "a", encoding="utf-8") as f:
        f.write('{"n": 2, "trunc\n[1]\n')
    assert folders.read_results(2) == ({"n": 1},)
    (tmp_path / "runs" / "2" / "status.json").write_text("[]", encoding="utf-8")
    assert folders.read_status(2) is None


def test_the_sync_log_is_one_line_per_call(tmp_path: Path) -> None:
    folders = FsRunFolders(tmp_path)
    folders.log("run 1\tdone")
    folders.log("run 2\nfailed")
    assert (tmp_path / "logs" / "sync.log").read_text(encoding="utf-8").splitlines() == [
        "run 1\tdone",
        "run 2 failed",
    ]
