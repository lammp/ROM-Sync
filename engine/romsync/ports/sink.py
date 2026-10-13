"""Progress and job reporting.

Progress is structured. The engine never formats a sentence for a human: it
reports a phase, a count, a total and the item in hand, and the interface
decides what that reads like. Version 1 wrote `JSON.stringify(result)` into the
page because the engine had no contract here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """One observation of work in progress.

    `phase` is a stable identifier, not a label: `scan`, `send`, `remove`,
    `verify`, `match`. `done` and `total` are counts of items, not bytes, and
    `total` is None while it is genuinely unknown rather than guessed at.
    `current` names the item in hand. `detail` carries numbers the interface may
    use, never prose.
    """

    phase: str
    done: int = 0
    total: int | None = None
    current: str | None = None
    detail: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if not self.phase or self.phase != self.phase.strip():
            raise ValueError("phase must be a non-empty identifier")
        if self.done < 0:
            raise ValueError("done cannot be negative")
        if self.total is not None and self.total < self.done:
            raise ValueError("total cannot be less than done")


class ProgressSink(Protocol):
    """Where a worker reports progress."""

    def emit(self, event: ProgressEvent) -> None: ...


class JobSink(Protocol):
    """Where a worker reports a job's state changes."""

    def started(self, job_id: str) -> None: ...

    def progress(self, job_id: str, event: ProgressEvent) -> None: ...

    def finished(self, job_id: str, result: dict[str, int]) -> None: ...

    def failed(self, job_id: str, code: str, message: str) -> None: ...


class NullSink:
    """A sink that discards. For a caller that wants no reporting at all."""

    def emit(self, event: ProgressEvent) -> None:
        return None
