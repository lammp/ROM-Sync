"""The application's log (F15-S4): its level from Settings, and no secret in it."""

from __future__ import annotations

import logging
from pathlib import Path

from romsync.compose import build, start_log
from tests.helpers.fakes import FrozenClock

TYPED = "zzq-log-value-0046"


def test_no_secret_in_logs(tmp_path: Path) -> None:
    """A secret passed through the engine never reaches the log: not as an
    argument, not inside an exception's message, not in its traceback."""
    engine = build(tmp_path / "data", clock=FrozenClock())
    engine.settings.write({"igdb.client_id": "client-7", "igdb.client_secret": TYPED})
    log = start_log(engine)
    try:
        said = logging.getLogger("romsync.metadata")
        said.info("requesting a token with %s", engine.settings.value("igdb.client_secret"))
        try:
            raise RuntimeError(f"the service refused {TYPED}")
        except RuntimeError:
            said.exception("the token request failed")
        logging.getLogger("romsync.api").warning("bound with secret=%s", TYPED)
    finally:
        log.close()
    text = log.path.read_text(encoding="utf-8")
    assert TYPED not in text
    assert "requesting a token with [redacted]" in text
    assert "RuntimeError: the service refused [redacted]" in text, "the traceback too"
    assert "bound with secret=[redacted]" in text
    assert log.path == tmp_path / "data" / "logs" / "romsync.log"


def test_the_level_comes_from_settings(tmp_path: Path) -> None:
    engine = build(tmp_path / "data", {"log.level": "warning"}, clock=FrozenClock())
    log = start_log(engine)
    try:
        said = logging.getLogger("romsync.jobs")
        said.info("not at this level")
        said.warning("at this level")
    finally:
        log.close()
    text = log.path.read_text(encoding="utf-8")
    assert "at this level" in text and "not at this level" not in text
    root = logging.getLogger("romsync")
    assert log.handler not in root.handlers, "closing detaches it"
    assert root.level == log.before, "and gives the level back"
