"""Run folders and file placement on this computer's filesystem.

Each run has `runs/<id>/` in the data folder: `ops.json` (what was asked),
`status.json` (replaced whole on every write) and `results.jsonl` (one line per
finished operation, appended and flushed). The sync log is `logs/sync.log`.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from romsync.adapters.dest_common import local
from romsync.domain.errors import WouldOverwrite
from romsync.domain.paths import ContainedPath


class FsRunFolders:
    def __init__(self, data: Path) -> None:
        self.data = data

    def _dir(self, run_id: int) -> Path:
        return self.data / "runs" / str(int(run_id))

    def open(self, run_id: int, ops: Sequence[Mapping[str, object]]) -> None:
        folder = self._dir(run_id)
        folder.mkdir(parents=True, exist_ok=True)
        self._replace(folder / "ops.json", [dict(o) for o in ops])

    @staticmethod
    def _replace(path: Path, value: object) -> None:
        part = path.with_name(path.name + ".part")
        part.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        os.replace(part, path)

    def status(self, run_id: int, status: Mapping[str, object]) -> None:
        self._replace(self._dir(run_id) / "status.json", dict(status))

    def result(self, run_id: int, row: Mapping[str, object]) -> None:
        with open(self._dir(run_id) / "results.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
            f.flush()

    def read_status(self, run_id: int) -> Mapping[str, object] | None:
        try:
            value = json.loads((self._dir(run_id) / "status.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def read_results(self, run_id: int) -> tuple[Mapping[str, object], ...]:
        try:
            lines = (
                (self._dir(run_id) / "results.jsonl").read_text(encoding="utf-8").splitlines()
            )
        except OSError:
            return ()
        rows: list[Mapping[str, object]] = []
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue  # a line cut short by the process dying mid-write
            if isinstance(row, dict):
                rows.append(row)
        return tuple(rows)

    def exists(self, run_id: int) -> bool:
        return self._dir(run_id).is_dir()

    def log(self, line: str) -> None:
        logs = self.data / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        with open(logs / "sync.log", "a", encoding="utf-8") as f:
            f.write(line.replace("\n", " ") + "\n")


class FsLocalFiles:
    def place(self, src: ContainedPath, dst: ContainedPath) -> None:
        source, target = local(src), local(dst)
        if target.exists() or target.is_symlink():
            raise WouldOverwrite(f"{dst.relative('/')} is already there; nothing was moved")
        target.parent.mkdir(parents=True, exist_ok=True)
        # a hard link then an unlink fails rather than replacing a file that
        # appeared in between; a folder, or a move across volumes, falls back
        try:
            os.link(source, target)
        except OSError:
            if target.exists():
                raise WouldOverwrite(
                    f"{dst.relative('/')} is already there; nothing was moved"
                ) from None
            os.rename(source, target)
            return
        source.unlink()
