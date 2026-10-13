"""The path escape corpus.

Every entry must raise PathEscape from RomsRoot.resolve and StoreRoot.resolve.
`NAME256` is a 256-character name, one over the limit.
"""

from __future__ import annotations

NAME256 = "x" * 256

ESCAPES: tuple[str, ...] = (
    "..",
    "../outside",
    "nes/../..",
    "nes/../../outside",
    "nes\\..\\..\\outside",
    "nes/./../../outside",
    "nes\\..//..\\outside",
    "/etc/passwd",
    "\\Windows\\System32",
    "C:\\Windows\\System32",
    "C:/Windows/System32",
    "c:relative",
    "D:",
    "\\\\server\\share\\nes",
    "//server/share/nes",
    "\\\\?\\C:\\Windows",
    "\\\\.\\pipe\\name",
    "nes/Contra.",
    "nes/Contra..",
    "nes/Contra ",
    "nes/...",
    "nes/CON",
    "nes/con.txt",
    "nes/NUL",
    "nes/aux.zip",
    "nes/PRN",
    "nes/COM1",
    "nes/com9.nes.txt",
    "nes/LPT1",
    "nes/lpt9",
    "nes/CONIN$",
    "nes/Contra:stream",
    "nes/" + NAME256,
)
