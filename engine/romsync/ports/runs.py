"""A sync run's durable folder, and moving a file into the store (F7-S2, F7-S11).

A run writes three things beside its database row: what was asked, where it
has got to, and one line per operation as it finishes. They are written by
the worker as it goes, so a run interrupted by the process dying is still
there to read, and startup reconciliation can tell a run whose worker is still
alive from one that is gone.

The sync log is one line per run in the data folder. Appending to it can never
fail a sync.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from romsync.domain.paths import ContainedPath


class RunFolders(Protocol):
    def open(self, run_id: int, ops: Sequence[Mapping[str, object]]) -> None:
        """Make the run's folder and write what it was asked to do."""
        ...

    def status(self, run_id: int, status: Mapping[str, object]) -> None:
        """Replace the run's status, whole, so a reader never sees half of one."""
        ...

    def result(self, run_id: int, row: Mapping[str, object]) -> None:
        """Append one operation's terminal result."""
        ...

    def read_status(self, run_id: int) -> Mapping[str, object] | None: ...

    def read_results(self, run_id: int) -> tuple[Mapping[str, object], ...]: ...

    def exists(self, run_id: int) -> bool: ...

    def log(self, line: str) -> None:
        """Append one line to the sync log."""
        ...


class LocalFiles(Protocol):
    def place(self, src: ContainedPath, dst: ContainedPath) -> None:
        """Move `src` to `dst`, refusing if anything is already at `dst`."""
        ...
