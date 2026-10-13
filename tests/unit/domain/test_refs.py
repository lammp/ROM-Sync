"""Stable device references: derived from identity, one spelling per device."""

from __future__ import annotations

import base64

import pytest

from romsync.domain.errors import BadDeviceRef
from romsync.domain.models import DeviceKind, DeviceRef
from romsync.domain.refs import MAX_LENGTH, decode, encode

REFS = [
    DeviceRef(DeviceKind.VOLUME, "1A2B3C4D"),
    DeviceRef(DeviceKind.ADB, "R5CT123"),
    DeviceRef(DeviceKind.MTP, "AYN Thor\tInternal shared storage"),
    DeviceRef(DeviceKind.MTP, "Ünïcødé/../\\?#%"),
    DeviceRef(DeviceKind.FAKE, "x"),
]


@pytest.mark.parametrize("ref", REFS, ids=lambda r: r.kind)
def test_round_trip_and_url_safe(ref: DeviceRef) -> None:
    text = encode(ref)
    assert decode(text) == ref
    assert "=" not in text and "/" not in text and "+" not in text


def _raw(body: bytes) -> str:
    return base64.urlsafe_b64encode(body).rstrip(b"=").decode()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "0",
        "1",
        encode(REFS[0]) + "=",
        encode(REFS[0]) + "==",
        "/" + encode(REFS[0]),
        encode(REFS[0]).replace(encode(REFS[0])[0], "+", 1),
        _raw(b"floppy\x00key"),
        _raw(b"volume"),
        _raw(b"volume\x00"),
        _raw(b"\xff\xfe\x00x"),
        "A" * (MAX_LENGTH + 1),
        "has space",
    ],
)
def test_only_the_canonical_spelling_decodes(text: str) -> None:
    with pytest.raises(BadDeviceRef):
        decode(text)


ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def test_spare_bits_must_be_zero() -> None:
    """Two spellings that decode to the same bytes: only the canonical one is accepted."""
    text = encode(REFS[1])
    assert len(text) % 4 in (2, 3), "this reference leaves spare bits in its last character"
    last = ALPHABET.index(text[-1])
    other = text[:-1] + ALPHABET[last ^ 1]
    assert base64.urlsafe_b64decode(
        other + "=" * (-len(other) % 4)
    ) == base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    with pytest.raises(BadDeviceRef):
        decode(other)


def test_text_is_required() -> None:
    with pytest.raises(BadDeviceRef):
        decode(5)  # type: ignore[arg-type]
