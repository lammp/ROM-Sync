"""The taxonomy's codes are the contract."""

from __future__ import annotations

import inspect

from romsync.domain import errors


def _classes() -> list[type[errors.RomSyncError]]:
    return [
        obj
        for _name, obj in inspect.getmembers(errors, inspect.isclass)
        if issubclass(obj, errors.RomSyncError)
    ]


def test_codes_unique_and_stable() -> None:
    codes = [c.code for c in _classes()]
    assert len(codes) == len(set(codes)), "two error classes share a code"


def test_every_class_declares_its_own_code() -> None:
    for cls in _classes():
        if cls is errors.RomSyncError:
            continue
        assert "code" in cls.__dict__, f"{cls.__name__} inherits its code"


def test_a_code_is_a_dotted_identifier() -> None:
    for cls in _classes():
        domain, _, rest = cls.code.partition(".")
        assert domain and rest, f"{cls.__name__}: {cls.code!r} is not domain.reason"
        assert cls.code == cls.code.lower()


def test_an_error_carries_its_field_when_it_has_one() -> None:
    raised = errors.ConfigOutOfRange("too big", field="jobs.history_length")
    assert raised.field == "jobs.history_length"
    assert raised.as_envelope() == {
        "code": "config.out_of_range",
        "message": "too big",
        "field": "jobs.history_length",
    }


def test_the_envelope_has_exactly_three_keys() -> None:
    """SPEC section 9: one error envelope, and only one."""
    assert set(errors.PathEscape("x").as_envelope()) == {"code", "message", "field"}


def test_every_error_is_catchable_as_the_base() -> None:
    for cls in _classes():
        assert issubclass(cls, errors.RomSyncError)
        assert issubclass(cls, Exception)
