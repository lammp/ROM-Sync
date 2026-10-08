#!/usr/bin/env python3
"""Publication lint: prove that nothing private can reach the repository.

The ignore rules deny by default, so in principle nothing sensitive can be
staged. This tool does not take that on trust. It asks git what it would
actually stage, classifies every one of those paths, reads their contents
looking for credentials and personal identifiers, and then checks from the
other direction that a list of canary paths really is excluded.

    python _tools/repo-lint.py            report only
    python _tools/repo-lint.py --strict   exit 1 on any finding (use in CI)
    python _tools/repo-lint.py --staged   lint the git index instead of the
                                          whole publishable set

Machine-local identifiers (a Windows account name, a machine name, an email
address) are read from _tools/repo-lint.local.txt, which is itself excluded
from the repository so that the lint does not publish the very strings it
exists to catch. Copy repo-lint.local.example.txt to that name to populate it.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

# A file with one of these extensions is never publishable, whatever its path.
FORBIDDEN_EXT = {
    # credentials and key material
    ".keys", ".pem", ".key", ".crt", ".cer", ".p12", ".pfx", ".jks",
    ".keystore", ".ppk", ".netrc",
    # application and library state
    ".db", ".sqlite", ".sqlite3", ".tsv", ".csv", ".jsonl",
    # console system files
    ".bin", ".rom", ".nca", ".tik", ".sav", ".srm", ".state",
    # game and disc images
    ".chd", ".iso", ".cue", ".gdi", ".rvz", ".wbfs", ".nkit", ".xci",
    ".nsp", ".nsz", ".3ds", ".cia", ".nds", ".gba", ".gbc", ".gb", ".nes",
    ".sfc", ".smc", ".n64", ".z64", ".v64", ".gcm", ".wad", ".pbp", ".cso",
    ".m3u",
    # archives
    ".zip", ".7z", ".rar", ".gz", ".bz2", ".xz",
}

FORBIDDEN_NAME = {
    "prod.keys", "title.keys", "memory.md", ".env", ".npmrc", ".pypirc",
    "romsync.db", "settings.json", "id_rsa", "id_ed25519", "status.json",
    "rom-sync.json",
}

# No publishable file lives under any of these.
FORBIDDEN_DIR = {
    "roms", "_firmware", "_torrents", "memory", ".memory-log", ".exchange",
    ".venv", "node_modules", "__pycache__", "webview", "ebwebview", "rounds",
    "covers", "screens", "runs", "records", "logs", "pull", "_deleted",
    "_holding", "_push",
}

# Directories whose Legislation ships but whose contents never do. A .gitkeep
# and a CLAUDE.md (or CLAUDE.example.md) are the only things allowed out.
SKELETON_ALLOW = {".gitkeep", "CLAUDE.md", "CLAUDE.example.md"}

# Nothing publishable here is large. A big file means a mistake.
MAX_BYTES = 2 * 1024 * 1024

TEXT_EXT = {
    ".py", ".js", ".css", ".html", ".md", ".json", ".txt", ".bat", ".cmd",
    ".ps1", ".yml", ".yaml", ".toml", ".cfg", ".ini", "",
}

# --------------------------------------------------------------------------
# Content patterns
# --------------------------------------------------------------------------

SECRET_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.")),
    ("Twitch/IGDB credential literal", re.compile(
        r"""client_(?:id|secret)["']?\s*[:=]\s*["'][A-Za-z0-9_\-]{12,}["']""",
        re.IGNORECASE)),
    ("generic secret literal", re.compile(
        r"""\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)"""
        r"""["']?\s*[:=]\s*["'][^"'\s]{8,}["']""", re.IGNORECASE)),
    ("bearer token literal", re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}")),
    ("Windows user profile path", re.compile(r"[Cc]:\\+Users\\+[A-Za-z0-9._-]+")),
    ("POSIX home path", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+")),
    ("environment user variable", re.compile(r"%USERPROFILE%|%USERNAME%", re.IGNORECASE)),
    ("email address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
]

# Matches that are expected and harmless. Keep this list short and specific.
ALLOWED_MATCHES = {
    "noreply@anthropic.com",
    "%LOCALAPPDATA%",
}

# Files that legitimately contain the patterns this tool searches for, because
# defining or documenting a pattern means writing it down. Each entry names
# the specific labels tolerated in that file; everything else still fails, so
# a real secret pasted into one of these is still caught.
EXPECTED_BY_FILE = {
    "_tools/repo-lint.py": {
        "environment user variable", "Windows user profile path",
        "POSIX home path", "email address", "AWS access key id",
        "GitHub token", "Slack token", "OpenAI-style key",
        "JSON web token", "private key block", "bearer token literal",
        "generic secret literal", "Twitch/IGDB credential literal",
    },
    ".githooks/pre-commit": {
        "environment user variable", "Windows user profile path",
        "AWS access key id", "GitHub token", "Slack token",
        "OpenAI-style key", "JSON web token", "private key block",
        "bearer token literal", "generic secret literal",
        "Twitch/IGDB credential literal",
    },
    "SECURITY.md": {"Windows user profile path", "environment user variable"},
    "_tools/repo-lint.local.example.txt": {"email address"},
    "CLAUDE.md": {"Windows user profile path"},
}

# Paths whose exclusion is asserted positively. If git ever stops ignoring
# one of these, the rules have regressed and the lint fails.
CANARIES = [
    "ROMs/psx/example.chd",
    "ROMs/switch/example.xci",
    "_firmware/ProdKeys.NET-v22.5.0/prod.keys",
    "_firmware/Firmware-22.5.0.zip",
    "_torrents/_incomplete/example.part",
    "ROM-Sync/data/romsync.db",
    "ROM-Sync/data/covers/example.jpg",
    "ROM-Sync/data/webview/EBWebView/Default/Cookies",
    "ROM-Sync/data/records/sync-log.tsv",
    "memory/example-fact.md",
    "MEMORY.md",
    ".memory-log/queries.jsonl",
    ".claude/settings.json",
    ".venv/Scripts/python.exe",
    "_tools/repo-lint.local.txt",
    "_tools/platform-tools/adb.exe",
    "_tools/same-system-duplicates.tsv",
]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def run(args, root):
    return subprocess.run(args, cwd=root, capture_output=True, text=False)


def repo_root():
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("not inside a git repository (run `git init` first)")
    return out.stdout.strip()


def publishable_paths(root, staged_only):
    """Every path git would put in a commit, as repo-relative POSIX strings."""
    if staged_only:
        args = ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"]
    else:
        args = ["git", "ls-files", "--cached", "--others",
                "--exclude-standard", "-z"]
    out = run(args, root)
    if out.returncode != 0:
        sys.exit(out.stderr.decode("utf-8", "replace").strip())
    raw = out.stdout.decode("utf-8", "replace")
    return sorted(p for p in raw.split("\0") if p)


def local_terms(root):
    path = os.path.join(root, "_tools", "repo-lint.local.txt")
    if not os.path.isfile(path):
        return [], False
    terms = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(line)
    return terms, True


def classify(path):
    """Return a list of reasons this path must not be published."""
    reasons = []
    parts = path.split("/")
    name = parts[-1]
    lower = name.lower()
    stem, ext = os.path.splitext(lower)

    for part in parts[:-1]:
        if part.lower() in FORBIDDEN_DIR and name not in SKELETON_ALLOW:
            reasons.append(f"lives under a private directory ({part}/)")
            break

    if ext in FORBIDDEN_EXT:
        reasons.append(f"forbidden file type ({ext})")
    if lower in FORBIDDEN_NAME:
        reasons.append(f"forbidden filename ({name})")
    if re.search(r"\.bak(-|$)|\.orig$|\.rej$|~$", lower):
        reasons.append("backup or scratch artefact")
    if ".local." in lower and not lower.endswith(".example.txt"):
        reasons.append("machine-local configuration")
    return reasons


def scan_content(root, path, terms):
    """Return a list of (pattern name, redacted sample, line number)."""
    full = os.path.join(root, path.replace("/", os.sep))
    ext = os.path.splitext(path)[1].lower()
    if ext not in TEXT_EXT:
        return []
    try:
        with open(full, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return []

    findings = []
    for n, line in enumerate(lines, 1):
        for label, pattern in SECRET_PATTERNS:
            for m in pattern.finditer(line):
                hit = m.group(0)
                if any(a in hit for a in ALLOWED_MATCHES):
                    continue
                if label in EXPECTED_BY_FILE.get(path, ()):
                    continue
                findings.append((label, redact(hit), n))
        low = line.lower()
        for term in terms:
            t = term.lower()
            if t not in low:
                continue
            # The GitHub account name is also the Windows account name. A term
            # used as `github.com/<term>/` is this repository's own address.
            if ("github.com/" + t) in low:
                continue
            findings.append(("machine-local identifier", redact(term), n))
    return findings


def redact(value):
    """Never print a secret in full, even in a local report."""
    if len(value) <= 8:
        return value[:2] + "*" * (len(value) - 2)
    return value[:4] + "*" * 8 + value[-2:]


def check_canaries(root):
    """Assert that each canary path is ignored. Returns the failures."""
    failures = []
    for path in CANARIES:
        out = run(["git", "check-ignore", "-q", "--no-index", "--", path], root)
        if out.returncode != 0:
            failures.append(path)
    return failures


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on any finding")
    ap.add_argument("--staged", action="store_true",
                    help="lint the git index rather than the whole publishable set")
    args = ap.parse_args()

    root = repo_root()
    terms, have_terms = local_terms(root)
    paths = publishable_paths(root, args.staged)

    path_failures = []
    content_failures = []
    size_failures = []

    for path in paths:
        reasons = classify(path)
        if reasons:
            path_failures.append((path, reasons))
            continue
        full = os.path.join(root, path.replace("/", os.sep))
        try:
            size = os.path.getsize(full)
        except OSError:
            size = 0
        if size > MAX_BYTES:
            size_failures.append((path, size))
        for label, sample, line in scan_content(root, path, terms):
            content_failures.append((path, line, label, sample))

    canary_failures = check_canaries(root)

    # ---- report ----------------------------------------------------------
    scope = "staged changes" if args.staged else "everything git would commit"
    print(f"repo-lint  root={root}")
    print(f"scope: {scope}  files: {len(paths)}")
    if not have_terms:
        print("WARNING  _tools/repo-lint.local.txt is missing, so machine-local")
        print("         identifiers are not being checked. Copy")
        print("         _tools/repo-lint.local.example.txt to that name.")
    print()

    if path_failures:
        print(f"FAIL  {len(path_failures)} path(s) must not be published")
        for path, reasons in path_failures:
            print(f"      {path}")
            for r in reasons:
                print(f"          {r}")
        print()

    if size_failures:
        print(f"FAIL  {len(size_failures)} file(s) over {MAX_BYTES // 1024} KB")
        for path, size in size_failures:
            print(f"      {path}  ({size // 1024} KB)")
        print()

    if content_failures:
        print(f"FAIL  {len(content_failures)} sensitive pattern(s) in file content")
        for path, line, label, sample in content_failures:
            print(f"      {path}:{line}  {label}  [{sample}]")
        print()

    if canary_failures:
        print(f"FAIL  {len(canary_failures)} canary path(s) are NOT ignored")
        print("      The ignore rules have regressed. Do not push.")
        for path in canary_failures:
            print(f"      {path}")
        print()

    total = (len(path_failures) + len(size_failures)
             + len(content_failures) + len(canary_failures))
    if total == 0:
        print("PASS  nothing publishable matched a sensitive class,")
        print(f"      and all {len(CANARIES)} canary paths are correctly ignored.")
    else:
        print(f"{total} finding(s).")

    if args.strict and total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
