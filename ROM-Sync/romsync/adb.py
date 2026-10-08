"""ADB transport: talking to an Android device over the debug bridge.

This is the fast path for Android handhelds. MTP stays in place for devices without
USB debugging, and plain volumes stay in place for microSD cards, USB drives and any
other machine that presents a filesystem. Nothing here changes those.

adb is invoked directly from Python. It is never routed through PowerShell, because
PowerShell mangles the quoting of the game names this library is full of (spaces,
commas, ampersands, apostrophes, parentheses) long before the device shell sees them.
"""
import os
import re
import shutil
import subprocess
import threading
import time

# Where the binary lives. The bundled copy under _tools wins so the app does not depend
# on whatever happens to be on PATH.
BUNDLED = r"D:\Games\_tools\platform-tools\adb.exe"

_NOWINDOW = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW: the app runs headless


def exe():
    """Path to adb, or None if it is not installed."""
    if os.path.isfile(BUNDLED):
        return BUNDLED
    found = shutil.which("adb")
    return found if found else None


def available():
    return exe() is not None


def _run(args, timeout=60, stdin=None):
    return subprocess.run([exe()] + args, capture_output=True, text=True, errors="replace",
                          timeout=timeout, creationflags=_NOWINDOW, input=stdin)


def devices():
    """[{serial, state, model, product}] for everything attached.

    Only devices in state 'device' are usable. 'unauthorized' means the person has not
    accepted the debugging prompt on the handheld yet, and is reported so the UI can say so.
    """
    if not available():
        return []
    try:
        r = _run(["devices", "-l"], timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for line in (r.stdout or "").splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        d = {"serial": parts[0], "state": parts[1], "model": "", "product": ""}
        for p in parts[2:]:
            if ":" in p:
                k, v = p.split(":", 1)
                if k in ("model", "product", "device"):
                    d[k] = v
        d["label"] = (d.get("model") or d["serial"]).replace("_", " ")
        out.append(d)
    return out


def q(path):
    """Quote one path for the device shell. Single quotes, with embedded ones broken out."""
    return "'" + str(path).replace("'", "'\\''") + "'"


class AdbError(RuntimeError):
    pass


def sh(serial, command, timeout=120):
    """Run a command in the device shell and return stdout.

    `command` is sent as a single argument, so it is parsed once by the device shell and
    not by anything on this side. Callers quote their own paths with q().
    """
    r = _run(["-s", serial, "shell", command], timeout=timeout)
    if r.returncode != 0:
        raise AdbError((r.stderr or r.stdout or "adb shell failed").strip()[:400])
    return r.stdout or ""


def sh_ok(serial, command, timeout=120):
    """Like sh() but returns (ok, output) instead of raising."""
    try:
        return True, sh(serial, command, timeout)
    except (AdbError, OSError, subprocess.SubprocessError) as e:
        return False, str(e)


_PCT = re.compile(r"\[\s*(\d+)%\]")


def push(serial, src, remote, progress=None, timeout=None):
    """Push one local file. progress(bytes_done) is called as it goes.

    Remote paths travel over the adb protocol rather than a shell, so they need no quoting
    here however odd the filename is.

    A watchdog kills the transfer at a deadline derived from the file size. This is not
    belt-and-braces: adb suppresses its progress output when stdout is a pipe, so there is
    no output to time out on, and a wedged adb server otherwise leaves the read blocked
    forever. Learned the hard way on 2026-09-17, when an 8 GB push sat dead for 36 minutes
    looking busy.
    """
    size = os.path.getsize(src)
    # 5 MB/s is a floor well under the ~50 MB/s a healthy USB 3 link gives, so a real
    # transfer never trips it; a dead one fails in bounded time.
    deadline = timeout if timeout else max(300.0, size / (5 * 1024 * 1024))
    p = subprocess.Popen([exe(), "-s", serial, "push", src, remote],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, errors="replace", bufsize=1, creationflags=_NOWINDOW)

    killed = {"by_watchdog": False}

    def _watchdog():
        if p.poll() is None:
            killed["by_watchdog"] = True
            try:
                p.kill()
            except OSError:
                pass

    timer = threading.Timer(deadline, _watchdog)
    timer.daemon = True
    timer.start()

    tail = []
    try:
        buf = ""
        while True:
            ch = p.stdout.read(1)
            if not ch:
                break
            if ch in "\r\n":
                if buf.strip():
                    tail.append(buf.strip())
                    del tail[:-6]
                    m = _PCT.search(buf)
                    if m and progress:
                        progress(int(size * int(m.group(1)) / 100))
                buf = ""
            else:
                buf += ch
    finally:
        timer.cancel()
        try:
            p.stdout.close()
        except OSError:
            pass
    rc = p.wait()
    if killed["by_watchdog"]:
        raise AdbError(f"push stalled: no completion within {int(deadline)}s for {size/1e9:.1f} GB "
                       f"(the adb server or the device stopped responding)")
    if rc != 0:
        raise AdbError("push failed: " + (" | ".join(tail))[:400])
    if progress:
        progress(size)
    return size


def pull(serial, remote, dst, timeout=7200):
    """Pull one remote file to a local path. Returns the local path, or None if it did not arrive."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    r = _run(["-s", serial, "pull", remote, dst], timeout=timeout)
    if r.returncode != 0 or not os.path.exists(dst):
        return None
    return dst


def md5(serial, remote):
    """MD5 of a file computed ON the device. The reason ADB is worth having: verifying a
    54 GB library costs seconds per file instead of dragging every byte back over USB."""
    ok, out = sh_ok(serial, "md5sum " + q(remote), timeout=600)
    if not ok:
        return None
    first = (out or "").strip().split("\n")[0].strip()
    return first.split()[0] if first and " " in first else None
