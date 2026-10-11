"""The debug bridge's commands, built and parsed, with no process in sight.

Every function here is pure: it builds an argument vector or a device-shell
command, or parses what one printed. The adapter runs them through a runner,
and the tests assert on the vectors (TESTING.md section 3), never on a binary.

The bridge is invoked directly, never through PowerShell, because PowerShell
mangles the quoting of the names this library is full of (spaces, commas,
ampersands, apostrophes, parentheses) before the device shell sees them. A
path inside a shell command is quoted once, by `q`. A path given to `push` or
`pull` travels over the bridge's own protocol and is passed as it is.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Final

from romsync.domain.errors import DestinationToolMissing

#: Where the debug bridge is found when the setting is empty.
TOOL: Final = "adb"

#: The floor of the push deadline, and the slowest rate a healthy link is
#: allowed before a transfer counts as stalled. 5 MB/s is a tenth of what USB 3
#: gives, so a real transfer never trips it and a wedged one fails in bounded
#: time. Version 1 learned this when an 8 GB push sat dead for 36 minutes.
PUSH_FLOOR_SECONDS: Final = 300.0
PUSH_FLOOR_RATE: Final = 5 * 1024 * 1024

Which = Callable[[str], str | None]


def locate(configured: str, which: Which = shutil.which) -> str:
    """The debug bridge executable, or a clear error naming what was looked for."""
    wanted = configured.strip() or TOOL
    found = which(wanted)
    if found is None:
        where = f"at {wanted}" if configured.strip() else "on the PATH"
        raise DestinationToolMissing(
            f"the Android debug bridge (adb) was not found {where}", field="adb.path"
        )
    return found


def q(path: str) -> str:
    """One path, quoted for the device shell: single quotes, embedded ones broken out."""
    return "'" + path.replace("'", "'\\''") + "'"


def remote(storage: str, parts: Sequence[str]) -> str:
    """The device path of `parts` below `storage`."""
    return "/".join(["/" + storage.strip("/"), *parts])


def push_deadline(size: int) -> float:
    return max(PUSH_FLOOR_SECONDS, size / PUSH_FLOOR_RATE)


# --- argument vectors ---------------------------------------------------------------------


def devices(exe: str) -> list[str]:
    return [exe, "devices", "-l"]


def shell(exe: str, serial: str, command: str) -> list[str]:
    """`command` is one argument, parsed once, by the device shell."""
    return [exe, "-s", serial, "shell", command]


def read(exe: str, serial: str, path: str) -> list[str]:
    """A file's bytes on standard output, unmangled by a terminal."""
    return [exe, "-s", serial, "exec-out", "cat " + q(path)]


def push(exe: str, serial: str, src: str, dst: str) -> list[str]:
    return [exe, "-s", serial, "push", src, dst]


def pull(exe: str, serial: str, src: str, dst: str) -> list[str]:
    return [exe, "-s", serial, "pull", src, dst]


# --- device-shell commands ----------------------------------------------------------------


def is_dir(path: str) -> str:
    return f"[ -d {q(path)} ] && echo yes || echo no"


def exists(path: str) -> str:
    return f"[ -e {q(path)} ] && echo present || echo absent"


def mkdir(path: str) -> str:
    return f"mkdir -p {q(path)} && [ -d {q(path)} ] && echo yes"


def remove(path: str) -> str:
    return f"rm -rf {q(path)}; [ -e {q(path)} ] && echo present || echo absent"


def size_of(path: str) -> str:
    """Bytes in a file, or in everything beneath a folder."""
    return f"find {q(path)} -type f -printf '%s\\n' | awk '{{s+=$1}} END {{print s+0}}'"


def place(staged: str, final: str) -> str:
    """Put a staged copy at its final name, keeping the old copy until it is there
    and restoring it if the move fails."""
    old = final + ".rs-old"
    return (
        f"rm -rf {q(old)}; "
        f"if [ -e {q(final)} ]; then mv {q(final)} {q(old)} || exit 1; fi; "
        f"if mv {q(staged)} {q(final)}; then rm -rf {q(old)}; echo placed; "
        f"else [ -e {q(old)} ] && mv {q(old)} {q(final)}; echo failed; fi"
    )


def free_space(path: str) -> str:
    return f"df -k {q(path)}"


def md5(paths: Sequence[str]) -> str:
    return "md5sum " + " ".join(q(p) for p in paths)


def md5_tree(path: str) -> str:
    """md5 of every file beneath a folder, named relative to it."""
    return f"cd {q(path)} && find . -type f -exec md5sum {{}} +"


def scan(root: str) -> str:
    """One round trip for a whole ROMs tree: folders, then files with sizes."""
    r = q(root)
    return (
        f"echo '@@@D'; find {r} -mindepth 1 -type d -printf '%P\\n'; "
        f"echo '@@@F'; find {r} -mindepth 1 -type f -printf '%s\\t%P\\n'"
    )


def listing(paths: Sequence[str]) -> str:
    chunks = []
    for path in paths:
        a = q(path)
        chunks.append(
            f"echo {q('@@@>' + path)}; if [ -d {a} ]; then echo '@@@DIR'; "
            f"find {a} -mindepth 1 -maxdepth 1 -type d -printf '@@@d%f\\n'; "
            f"find {a} -mindepth 1 -maxdepth 1 -type f -printf '%s\\t%f\\n'; "
            "else echo '@@@MISSING'; fi"
        )
    return "; ".join(chunks)


# --- parsing --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Attached:
    serial: str
    state: str
    model: str = ""

    @property
    def usable(self) -> bool:
        return self.state == "device"


def parse_devices(out: str) -> tuple[Attached, ...]:
    found: list[Attached] = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 2 or line.startswith("*"):
            continue
        extra = dict(p.split(":", 1) for p in parts[2:] if ":" in p)
        found.append(Attached(parts[0], parts[1], extra.get("model", "").replace("_", " ")))
    return tuple(found)


def parse_df(out: str) -> tuple[int, int] | None:
    """(total, free) in bytes from `df -k`, or None if nothing parsed."""
    for line in out.splitlines():
        f = line.split()
        if len(f) >= 4 and f[1].isdigit() and f[3].isdigit():
            return int(f[1]) * 1024, int(f[3]) * 1024
    return None


@dataclass
class Tree:
    """A ROMs tree as `scan` printed it."""

    top: list[str] = field(default_factory=list)
    folders: set[tuple[str, str]] = field(default_factory=set)
    sizes: dict[tuple[str, str], int] = field(default_factory=dict)


def parse_scan(out: str) -> Tree:
    tree = Tree()
    mode = ""
    for line in out.splitlines():
        line = line.rstrip("\r")
        if line.startswith("@@@"):
            mode = line[3:4]
            continue
        if mode == "D":
            parts = [p for p in line.split("/") if p]
            if len(parts) == 1:
                tree.top.append(parts[0])
            elif len(parts) == 2:
                tree.folders.add((parts[0], parts[1]))
        elif mode == "F" and "\t" in line:
            size, rel = line.split("\t", 1)
            parts = [p for p in rel.split("/") if p]
            if len(parts) >= 2 and size.isdigit():
                key = (parts[0], parts[1])
                tree.sizes[key] = tree.sizes.get(key, 0) + int(size)
    tree.top.sort(key=str.lower)
    return tree


def parse_listing(out: str) -> dict[str, list[tuple[str, str, int | None]] | None]:
    """Each path to its entries, or None when the folder is absent."""
    found: dict[str, list[tuple[str, str, int | None]] | None] = {}
    current: str | None = None
    for line in out.splitlines():
        line = line.rstrip("\r")
        if line.startswith("@@@>"):
            current = line[4:]
        elif current is None:
            continue
        elif line == "@@@MISSING":
            found[current] = None
        elif line == "@@@DIR":
            found[current] = []
        elif line.startswith("@@@d"):
            entries = found.get(current)
            if entries is not None:
                entries.append((line[4:], "folder", None))
        elif "\t" in line:
            size, name = line.split("\t", 1)
            entries = found.get(current)
            if entries is not None and size.isdigit():
                entries.append((name, "file", int(size)))
    return found


def parse_md5(out: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in out.splitlines():
        digest, sep, path = line.strip().partition("  ")
        if sep and len(digest) == 32:
            found[path.strip()] = digest
    return found
