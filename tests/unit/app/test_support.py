"""The support bundle's redaction (F15-S3)."""

from __future__ import annotations

from romsync.app.support import REDACTED, redact


def test_every_secret_is_replaced_longest_first() -> None:
    text = "token abcd-efgh then abcd and ab"
    assert redact(text, ["abcd", "abcd-efgh", "ab", ""]) == (
        f"token {REDACTED} then {REDACTED} and ab"
    ), "a secret shorter than four characters would match ordinary text"
