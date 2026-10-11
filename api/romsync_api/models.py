"""Every request and response body, declared (SPEC section 9).

No route returns an ad-hoc dict: each names one of these as its response
model, and `tests/unit/api/test_contracts.py` holds the route table to it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ErrorBody(Model):
    code: str
    message: str
    field: str | None = None


class ErrorEnvelope(Model):
    error: ErrorBody


class Version(Model):
    application: str
    version: str
    api: str


class Session(Model):
    """What a page needs before it can change anything."""

    token: str
    #: Whether the shell endpoints answer: only while the bind is loopback.
    shell: bool
