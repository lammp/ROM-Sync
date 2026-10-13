"""Leaving secrets out of anything written for a person to read (F15-S3, S4)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

#: What a secret's value becomes wherever it is found.
REDACTED: Final = "[redacted]"
#: A secret shorter than this is not searched for: it would match ordinary text.
SHORTEST: Final = 4


def redact(text: str, secrets: Iterable[str]) -> str:
    """`text` with every secret's value replaced, longest first."""
    for secret in sorted({s for s in secrets if len(s) >= SHORTEST}, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    return text
