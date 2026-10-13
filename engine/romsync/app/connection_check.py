"""Testing the metadata credentials, stage by stage (F10-S9).

The person types a client id and a secret and asks whether they work, before
saving them. The answer says which stage failed, because each has its own fix:

    input   both values are there          type the missing one
    token   the token service accepts them  the pair is wrong or revoked
    query   the metadata service answers    the service is down or refusing

A later stage is skipped once one fails. Nothing is stored: the test runs on
what was typed, falling back to the saved value only for a field left blank.

The module is not called `credentials.py` because the publication rules deny
any file whose name begins with "credential".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol

from romsync.domain.catalogue import Platform
from romsync.domain.errors import MetadataCredentialsMissing, RomSyncError

STAGES: Final = ("input", "token", "query")


class Outcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    outcome: Outcome
    code: str | None = None
    message: str | None = None


class Probe(Protocol):
    def token(self) -> str: ...
    def platforms(self) -> tuple[Platform, ...]: ...


ProbeFactory = Callable[[str, str], Probe]
Saved = Callable[[], tuple[str, str]]


@dataclass(frozen=True, slots=True)
class CheckResult:
    stages: tuple[Stage, ...]

    @property
    def ok(self) -> bool:
        return all(s.outcome is Outcome.PASSED for s in self.stages)

    @property
    def failed_at(self) -> str | None:
        return next((s.name for s in self.stages if s.outcome is Outcome.FAILED), None)


class ConnectionCheck:
    def __init__(self, make: ProbeFactory, saved: Saved) -> None:
        self._make = make
        self._saved = saved

    def run(self, client_id: str | None, client_secret: str | None) -> CheckResult:
        saved_id, saved_secret = self._saved()
        cid = (client_id or "").strip() or saved_id
        secret = (client_secret or "").strip() or saved_secret
        stages: list[Stage] = []

        def failed(name: str, exc: RomSyncError) -> CheckResult:
            stages.append(Stage(name, Outcome.FAILED, exc.code, exc.message))
            rest = STAGES[STAGES.index(name) + 1 :]
            return CheckResult((*stages, *(Stage(n, Outcome.SKIPPED) for n in rest)))

        if not cid or not secret:
            missing = "client id" if not cid else "secret"
            return failed("input", MetadataCredentialsMissing(f"the {missing} is empty"))
        stages.append(Stage("input", Outcome.PASSED))
        try:
            probe = self._make(cid, secret)
            probe.token()
        except RomSyncError as exc:
            return failed("token", exc)
        stages.append(Stage("token", Outcome.PASSED))
        try:
            probe.platforms()
        except RomSyncError as exc:
            return failed("query", exc)
        stages.append(Stage("query", Outcome.PASSED))
        return CheckResult(tuple(stages))
