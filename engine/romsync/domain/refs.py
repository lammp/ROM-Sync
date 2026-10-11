"""A device's stable reference, as text (F6-S9).

A reference is derived from the device's identity, never from where it came in
a probe's list, so it survives a refresh and a reordering. The text is the
unpadded URL-safe base64 of the kind and the transport's key, because a key
can hold characters a URL path cannot. Only the canonical encoding decodes: a
reference with padding, other characters or a different spelling of the same
bytes is refused, so one device has exactly one reference.
"""

from __future__ import annotations

import base64
import binascii
import re

from romsync.domain.errors import BadDeviceRef
from romsync.domain.models import DeviceKind, DeviceRef

_ALPHABET = re.compile(r"[A-Za-z0-9_-]+")
_SEP = "\x00"
MAX_LENGTH = 1024


def encode(ref: DeviceRef) -> str:
    raw = f"{ref.kind}{_SEP}{ref.key}".encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode(text: str) -> DeviceRef:
    """The reference `text` names, or `BadDeviceRef`."""
    if not isinstance(text, str) or len(text) > MAX_LENGTH or not _ALPHABET.fullmatch(text):
        raise BadDeviceRef("not a device reference", field="device")
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)).decode("utf-8")
        kind, sep, key = raw.partition(_SEP)
        ref = DeviceRef(DeviceKind(kind), key)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise BadDeviceRef("not a device reference", field="device") from exc
    if not sep or not key or encode(ref) != text:
        raise BadDeviceRef("not a device reference", field="device")
    return ref
