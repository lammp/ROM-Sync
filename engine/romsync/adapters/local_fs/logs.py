"""The application's log (F15-S4): `logs/romsync.log` in the data folder, at
the level Settings chooses, rotated, and with every secret left out.

Redaction happens on the finished line, after the message, its arguments and
any traceback are formatted, so a secret reaches the file by no route: not as
an argument, not inside an exception's message, not in a traceback.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

from romsync.domain.redaction import redact

#: The log, inside the data folder's `logs`.
LOG_FILE: Final = "romsync.log"
#: Every logger the application names sits below this one.
ROOT_LOGGER: Final = "romsync"
#: A log file is rotated at this size, and this many old ones are kept.
MAX_BYTES: Final = 1024 * 1024
KEEP: Final = 3

Secrets = Callable[[], Iterable[str]]


class RedactingFormatter(logging.Formatter):
    def __init__(self, secrets: Secrets) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self._secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record), self._secrets())


@dataclass(slots=True)
class AppLog:
    """The log as configured; `close` detaches and closes it."""

    path: Path
    handler: logging.Handler
    logger: logging.Logger
    #: The level the logger had before, given back on close.
    before: int

    def close(self) -> None:
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.before)
        self.handler.close()


def configure(data: Path, level: str, secrets: Secrets) -> AppLog:
    """Write the application's loggers to its log in `data`, at `level`."""
    folder = data / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / LOG_FILE
    handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=KEEP, encoding="utf-8")
    handler.setFormatter(RedactingFormatter(secrets))
    logger = logging.getLogger(ROOT_LOGGER)
    before = logger.level
    logger.setLevel(level.upper())
    logger.addHandler(handler)
    return AppLog(path, handler, logger, before)
