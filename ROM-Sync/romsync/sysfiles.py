"""System files: what each emulator on a device needs, what the store has, what is staged
on the device and what is actually installed.

The app checks and stages these; it never generates them, and it never writes into an
emulator's own folders. Everything it places goes to one static place on the device,
grouped by system:

    <ROMs>\\bios\\<system>\\<file>          e.g. ROMs\\bios\\nds\\bios7.bin, ROMs\\bios\\switch\\prod.keys

Matt installs from there with each emulator's own UI (Eden's Install keys / firmware,
DuckStation's BIOS directory, melonDS's BIOS path, RetroArch's system directory).

Two statuses per file, no dates:
    staged     in ROMs\\bios\\<system>: current (same content as the store copy, judged by
               size and, for files up to HASH_LIMIT, an MD5 of a copy pulled back), a
               different version, or not staged
    installed  what the emulator will actually read: its real location on the device,
               listed read-only by the scan (DuckStation and NetherSX2 app bios folders,
               Eden's keys folder and installed firmware, RetroArch\\system, and the
               staged folder itself for melonDS)

Per-system actions: stage (Add / Update: the whole set for that system) and unstage
(Remove: that system's folder contents). Stray files anywhere under ROMs\\bios that belong
to no system are listed as "other files" with a per-file remove.

Store side: BIOS files in <store>\\bios; Switch keys and the firmware zip under
D:\\Games\\_firmware. Key file contents are never read or logged (Constitution law 1);
hashing a key file reads bytes, prints nothing.

Readiness (the dot) comes from the installed status only; staging never turns a system green.
    ready / missing / optional / none / unseen / unknown (not scanned)
"""
import hashlib
import os
import re

from . import db

FIRMWARE_DIR = r"D:\Games\_firmware"
HASH_LIMIT = 32 * 1024 * 1024        # pull-and-hash staged files up to this size to compare content
STAGE = "{roms}/bios/{system}"       # where every system's files are staged on the device

# Install locations (where the emulator really reads), relative to the storage root.
LOC = {
    "staged":           (STAGE,                                                          "the staged folder (point the emulator at it)"),
    "retroarch-system": ("RetroArch/system",                                             "RetroArch's System/BIOS directory"),
    "app-bios":         ("Android/data/{pkg}/files/bios",                                "the emulator's own bios folder"),
    "eden-keys":        ("Android/data/{pkg}/files/keys",                                "Eden's keys folder"),
    "eden-firmware":    ("Android/data/{pkg}/files/nand/system/Contents/registered",    "Eden's installed firmware"),
}
ANDROID_DATA = "Android/data"


def R(name, required, store, install, md5s=(), note="", group=None, match=None):
    """One system file. store: (kind, name) in the store; install: LOC key the emulator reads from;
    match: for the install check, a name pattern instead of the exact name (firmware NCAs)."""
    return {"name": name, "required": required, "store": store, "install": install, "md5s": list(md5s),
            "note": note, "group": group, "match": match}


# system key -> emulator label, Android package pattern, requirements, system note
SYSTEMS = {
    "switch": ("Eden", r"eden", [
        R("prod.keys", True, ("firmware", "prod.keys"), "eden-keys", note="Switch keys: Eden > Install keys"),
        R("title.keys", False, ("firmware", "title.keys"), "eden-keys", note="title keys; optional"),
        R("Firmware.zip", True, ("firmware-zip", "Firmware"), "eden-firmware", match=r"\.nca$",
          note="Switch firmware zip: Eden > Install firmware; installed status counts Eden's registered packages"),
    ], "Eden needs keys and firmware for every game; install both from ROMs\\bios\\switch through Eden's menus."),
    "nds": ("melonDS", r"melonds", [
        R("bios7.bin", True, ("bios", "bios7.bin"), "staged", ["df692a80a5b1bc90728bc3dfc76cd948"], "DS ARM7 BIOS"),
        R("bios9.bin", True, ("bios", "bios9.bin"), "staged", ["a392174eb3e572fed6447e956bde4b25"], "DS ARM9 BIOS"),
        R("firmware.bin", True, ("bios", "firmware.bin"), "staged", [], "DS firmware (any dump)"),
        R("dsi_bios7.bin", False, ("bios", "dsi_bios7.bin"), "staged", [], "DSi ARM7 BIOS (DSi mode only)"),
        R("dsi_bios9.bin", False, ("bios", "dsi_bios9.bin"), "staged", [], "DSi ARM9 BIOS (DSi mode only)"),
    ], "melonDS reads a folder you choose: point its BIOS directory at ROMs\\bios\\nds."),
    "psx": ("DuckStation", r"duckstation", [
        R("scph5501.bin", True, ("bios", "scph5501.bin"), "app-bios", ["490f666e1afb15b7362b406ed1cea246"], "PS1 BIOS, USA", group="ps1"),
        R("scph5502.bin", True, ("bios", "scph5502.bin"), "app-bios", ["32736f17079d0b2b7024407c39bd3050"], "PS1 BIOS, Europe", group="ps1"),
        R("scph5500.bin", True, ("bios", "scph5500.bin"), "app-bios", ["8dd7d5296a650fac7319bce665a6a53c"], "PS1 BIOS, Japan", group="ps1"),
    ], "DuckStation needs one PS1 BIOS of any region; copy it into its bios folder, or point its BIOS directory at ROMs\\bios\\psx."),
    "ps2": ("NetherSX2", r"aethersx2|nethersx2", [
        R("SCPH-70012.bin", True, ("bios", "SCPH-70012.bin"), "app-bios", [], "PS2 BIOS", group="ps2"),
    ], "NetherSX2 needs a PS2 BIOS in its own bios folder."),
    "gba": ("RetroArch (mGBA)", r"retroarch", [
        R("gba_bios.bin", False, ("bios", "gba_bios.bin"), "retroarch-system", ["a860e8c0b6d573d191e4ec7db1b1e4f6"],
          "GBA BIOS; optional, used when the mGBA core option 'Use BIOS file if found' is on"),
    ], "RetroArch has one system directory (RetroArch\\system); copy the file there by hand."),
    "gbc": ("RetroArch (Gambatte)", r"retroarch", [
        R("gbc_bios.bin", False, ("bios", "gbc_bios.bin"), "retroarch-system", ["dbfce9db9deaa2567f6a84fde55f9680"],
          "Game Boy Color boot ROM; optional"),
    ], "RetroArch has one system directory (RetroArch\\system); copy the file there by hand."),
    "n3ds": ("Azahar", r"azahar|lime3ds|citra", [], "Decrypted images need no keys or BIOS."),
    "psp": ("PPSSPP", r"ppsspp", [], "Nothing needed."),
    "gc": ("Dolphin", r"dolphin", [], "Nothing needed."),
    "wii": ("Dolphin", r"dolphin", [], "Nothing needed."),
    "fbneo": ("RetroArch (FBNeo)", r"retroarch", [], "Arcade sets carry their own BIOS zips inside the ROM folder."),
    "nes": ("RetroArch (Mesen)", r"retroarch", [], "Nothing needed."),
    "snes": ("RetroArch (Snes9x)", r"retroarch", [], "Nothing needed."),
    "n64": ("RetroArch (Mupen64Plus-Next)", r"retroarch", [], "Nothing needed."),
    "mastersystem": ("RetroArch (Genesis Plus GX)", r"retroarch", [], "Nothing needed."),
}
KNOWN_NAMES = {r["name"] for _, (_, _, reqs, _) in SYSTEMS.items() for r in reqs}


# ---------------------------------------------------------------- store side

def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _find_in_firmware(name, folder=False):
    """First match under _firmware by name (a file, or a folder whose name starts with `name`)."""
    if not os.path.isdir(FIRMWARE_DIR):
        return None
    for r, ds, fs in os.walk(FIRMWARE_DIR):
        if folder:
            hit = [d for d in ds if d.lower().startswith(name.lower())]
            if hit:
                return os.path.join(r, hit[0])
        elif name in fs:
            return os.path.join(r, name)
    return None


def _find_zip(prefix):
    if not os.path.isdir(FIRMWARE_DIR):
        return None
    for r, ds, fs in os.walk(FIRMWARE_DIR):
        hit = sorted(f for f in fs if f.lower().startswith(prefix.lower()) and f.lower().endswith(".zip"))
        if hit:
            return os.path.join(r, hit[-1])       # highest version name sorts last
    return None


_store_cache = {}


def store_item(req):
    """The store copy: {present, path, size, md5, verified, staged_name}. staged_name is the file name
    on the device (Firmware.zip keeps the zip's real name so the version is visible)."""
    kind, name = req["store"]
    if kind == "bios":
        p = os.path.join(db.store_root(), "bios", name)
    elif kind == "firmware":
        p = _find_in_firmware(name)
    elif kind == "firmware-zip":
        p = _find_zip(name)
    else:
        p = None
    if not p or not os.path.isfile(p):
        return {"present": False, "path": None, "size": None, "md5": None, "verified": None, "staged_name": req["name"]}
    size = os.path.getsize(p)
    key = (p, size, int(os.path.getmtime(p)))
    if key not in _store_cache:
        _store_cache[key] = _md5(p) if size <= HASH_LIMIT else None
    md5 = _store_cache[key]
    verified = (md5 in req["md5s"]) if (req["md5s"] and md5) else None
    return {"present": True, "path": p, "size": size, "md5": md5, "verified": verified,
            "staged_name": os.path.basename(p) if kind == "firmware-zip" else req["name"]}


# ---------------------------------------------------------------- device side

def _roms_root(device_id):
    r = db.connect().execute("SELECT roms_root, kind FROM devices WHERE id=?", (device_id,)).fetchone()
    return (r["roms_root"] or "ROMs").strip("\\/").replace("\\", "/"), r["kind"]


def _stage_path(roms, system):
    return STAGE.format(roms=roms, system=system)


def watched_paths(device_id, apps=None, subfolders=()):
    """Folders the scan lists: the staging root and its subfolders, the install locations."""
    roms, kind = _roms_root(device_id)
    paths = {f"{roms}/bios", LOC["retroarch-system"][0]}
    for sub in subfolders:
        paths.add(f"{roms}/bios/{sub}")
    for key in SYSTEMS:
        paths.add(_stage_path(roms, key))
    if kind == "mtp":
        paths.add(ANDROID_DATA)
        for key, (_, pat, reqs, _) in SYSTEMS.items():
            pkg = (apps or {}).get(pat)
            if not pkg:
                continue
            for r in reqs:
                if r["install"] != "staged":
                    paths.add(LOC[r["install"]][0].format(pkg=pkg, roms=roms, system=key))
    return sorted(paths)


def detect_apps(rows):
    """{pattern: package} from an Android/data listing."""
    names = [n for p, n, k, _ in rows if p == ANDROID_DATA and k == "folder"]
    out = {}
    for _, (_, pat, _, _) in SYSTEMS.items():
        if pat in out:
            continue
        hit = [n for n in names if re.search(pat, n, re.I)]
        if hit:
            out[pat] = sorted(hit)[0]
    return out


def _hash_dir():
    d = os.path.join(db.data_dir(), "tmp", "sysfile-hash")
    os.makedirs(d, exist_ok=True)
    return d


def _hash_staged(device_id, dest, rows, progress=None):
    """Pull small staged files back and MD5 them (skipping ones whose size and name are already hashed)."""
    conn = db.connect()
    roms, _ = _roms_root(device_id)
    known = {(r["path"], r["name"], r["size"]): r["hash"] for r in conn.execute(
        "SELECT path, name, size, hash FROM device_sysfile_hashes WHERE device_id=?", (device_id,))}
    conn.execute("DELETE FROM device_sysfile_hashes WHERE device_id=?", (device_id,))
    stage_root = f"{roms}/bios"
    for path, name, kind, size in rows:
        if kind != "file" or not name or not path.startswith(stage_root) or size > HASH_LIMIT or size <= 0:
            continue
        h = known.get((path, name, size))
        if not h:
            if progress:
                progress(f"checking {name}")
            local = dest.get_file(path, name, _hash_dir())
            if not local:
                continue
            try:
                h = _md5(local)
            finally:
                try:
                    os.remove(local)
                except OSError:
                    pass
        conn.execute("INSERT OR REPLACE INTO device_sysfile_hashes(device_id,path,name,size,hash) VALUES(?,?,?,?,?)",
                     (device_id, path, name, size, h))
    conn.commit()


def scan(device_id, dest, progress=None):
    """List the staging and install folders on the device (read-only), hash the staged files, record it."""
    if progress:
        progress("listing folders")
    roms, _ = _roms_root(device_id)
    first = dest.list_paths(watched_paths(device_id))
    apps = detect_apps(first) if dest.kind in ("mtp", "adb") else {}
    subs = [n for p, n, k, _ in first if p == f"{roms}/bios" and k == "folder" and n]
    more = [p for p in watched_paths(device_id, apps, subs) if p not in {r[0] for r in first}]
    rows = first + (dest.list_paths(more) if more else [])
    _hash_staged(device_id, dest, rows, progress)
    conn = db.connect()
    now = db.now()
    conn.execute("DELETE FROM device_sysfiles WHERE device_id=?", (device_id,))
    for path, name, kind, size in rows:
        conn.execute("INSERT OR REPLACE INTO device_sysfiles(device_id,path,name,kind,size,seen_at) VALUES(?,?,?,?,?,?)",
                     (device_id, path, name, kind, size, now))
    conn.commit()
    return {"paths": len(set(r[0] for r in rows)), "entries": sum(1 for r in rows if r[1]), "apps": apps, "at": now}


def _device_listing(device_id):
    conn = db.connect()
    rows = conn.execute("SELECT path, name, kind, size, seen_at FROM device_sysfiles WHERE device_id=?", (device_id,)).fetchall()
    by_path = {}
    for r in rows:
        by_path.setdefault(r["path"], {})[r["name"]] = (r["kind"], r["size"])
    hashes = {(r["path"], r["name"], r["size"]): r["hash"] for r in conn.execute(
        "SELECT path, name, size, hash FROM device_sysfile_hashes WHERE device_id=?", (device_id,))}
    seen_at = rows[0]["seen_at"] if rows else None
    return by_path, hashes, seen_at


def _folder_state(listing, path):
    """'missing' (folder absent), 'empty', or 'ok' with entries."""
    d = listing.get(path)
    if d is None or (len(d) == 1 and "" in d and d[""][0] == "missing"):
        return "missing"
    return "ok"


# ---------------------------------------------------------------- readiness

def readiness(device_id):
    """Per-system view for the System files page: staged and installed status, sorted by games on the device."""
    conn = db.connect()
    roms, dkind = _roms_root(device_id)
    listing, hashes, seen_at = _device_listing(device_id)
    flat = [(p, n, k, sz) for p, d in listing.items() for n, (k, sz) in d.items()]
    apps = detect_apps(flat) if dkind == "mtp" else {}
    from . import profiles
    on_dev = {r["system"]: {"n": r["n"], "bytes": r["bytes"] or 0} for r in profiles.summary(device_id) if r["system"] != "bios"}
    store = {r["key"]: {"n": r["games"], "bytes": r["bytes"], "label": r["label"]} for r in db.system_rows()}
    labels = {r["key"]: r["label"] for r in conn.execute("SELECT key, label FROM systems")}
    claimed = set()      # (path, name) accounted for by a system

    out = []
    for key in sorted(set(store) | set(on_dev), key=lambda k: (-(on_dev.get(k, {}).get("n", 0)), k)):
        emu, pat, reqs, sys_note = SYSTEMS.get(key, ("unknown emulator", None, [], ""))
        pkg = apps.get(pat) if pat else None
        emu_seen = None if dkind != "mtp" or not seen_at else (pkg is not None)
        stage = _stage_path(roms, key)
        staged_dir = listing.get(stage) or {}
        rows, groups = [], {}
        for r in reqs:
            st = store_item(r)
            sname = st["staged_name"]
            # ---- staged
            if seen_at is None:
                staged = "unknown"
            elif sname in staged_dir and staged_dir[sname][0] == "file":
                claimed.add((stage, sname))
                sz = staged_dir[sname][1]
                h = hashes.get((stage, sname, sz))
                if not st["present"]:
                    staged = "staged"                                    # nothing to compare against
                elif sz != st["size"]:
                    staged = "different"
                elif st["md5"] and h:
                    staged = "current" if h == st["md5"] else "different"
                else:
                    staged = "current"                                   # too big to hash: size match is the test
            else:
                staged = "not staged"
            # ---- installed (the emulator's real location)
            if r["install"] == "staged":
                ipath, ilabel = stage, LOC["staged"][1]
            else:
                tpl, ilabel = LOC[r["install"]]
                ipath = tpl.format(roms=roms, pkg=pkg or "?", system=key)
            if dkind != "mtp" and r["install"] not in ("staged", "retroarch-system"):
                installed = "n/a"
            elif seen_at is None:
                installed = "unknown"
            elif r["install"] != "staged" and r["install"] != "retroarch-system" and not pkg:
                installed = "unseen"
            elif _folder_state(listing, ipath) == "missing":
                installed = "missing"
            else:
                d = listing[ipath]
                if r["match"]:
                    n = sum(1 for n_, (k_, _) in d.items() if n_ and k_ == "file" and re.search(r["match"], n_, re.I))
                    installed = "installed" if n else "missing"
                elif r["install"] == "staged":
                    installed = "installed" if staged in ("current", "staged") else "missing"
                elif r["name"] in d and d[r["name"]][0] == "file":
                    installed = "installed" if (st["size"] is None or d[r["name"]][1] == st["size"]) else "different"
                else:
                    installed = "missing"
            ok = installed == "installed"
            if r["group"]:
                groups[r["group"]] = groups.get(r["group"], False) or ok
            rows.append({"name": r["name"], "staged_name": sname, "required": r["required"], "group": r["group"], "note": r["note"],
                         "store_present": st["present"], "store_size": st["size"], "store_verified": st["verified"],
                         "store_path": st["path"], "staged": staged, "staged_path": stage.replace("/", "\\"),
                         "installed": installed, "installed_path": ipath.replace("/", "\\"), "installed_label": ilabel, "ok": ok})
        # ---- readiness from the installed status
        if not reqs:
            state = "unseen" if (emu_seen is False and key in SYSTEMS) else "none"
        elif seen_at is None:
            state = "unknown"
        elif emu_seen is False:
            state = "unseen"
        else:
            need = [x for x in rows if x["required"]]
            grouped_ok = all(groups[g] for g in {x["group"] for x in need if x["group"]}) if groups else True
            single_ok = all(x["ok"] for x in need if not x["group"])
            if need and not (grouped_ok and single_ok):
                state = "missing"
            elif any(not x["ok"] and not x["required"] for x in rows):
                state = "optional"
            else:
                state = "ready"
        missing = [x["name"] for x in rows if x["required"] and not x["ok"] and not (x["group"] and groups.get(x["group"]))]
        # ---- staging summary and the two buttons
        stageable = [x for x in rows if x["store_present"]]
        n_current = sum(1 for x in stageable if x["staged"] == "current")
        n_staged_any = sum(1 for x in rows if x["staged"] in ("current", "different", "staged"))
        if not stageable:
            stage_state, stage_action = "nothing to stage", None
        elif seen_at is None:
            stage_state, stage_action = "unknown", None
        elif n_current == len(stageable):
            stage_state, stage_action = "current", None
        elif n_staged_any:
            stage_state, stage_action = "update available", "update"
        else:
            stage_state, stage_action = "not staged", "add"
        out.append({"system": key, "label": labels.get(key, key), "emulator": emu, "package": pkg,
                    "emulator_seen": emu_seen, "on_device": on_dev.get(key, {"n": 0, "bytes": 0}),
                    "in_store": store.get(key, {"n": 0, "bytes": 0}), "state": state, "missing": missing,
                    "note": sys_note, "requirements": rows, "stage_path": stage.replace("/", "\\"),
                    "stage_state": stage_state, "stage_action": stage_action, "can_unstage": n_staged_any > 0})
    # ---- other files: anything under ROMs\bios (root or any subfolder) not claimed by a system
    others = []
    root = f"{roms}/bios"
    for path, d in listing.items():
        if path != root and not path.startswith(root + "/"):
            continue
        for n_, (k_, sz) in d.items():
            if not n_ or (path, n_) in claimed:
                continue
            if k_ == "folder" and path == root and n_ in SYSTEMS:
                continue                                    # a system's staging folder
            others.append({"path": path.replace("/", "\\"), "rel": path, "name": n_, "kind": k_, "size": sz})
    others.sort(key=lambda o: (o["rel"], o["name"].lower()))
    on = [s for s in out if s["on_device"]["n"]]
    off = [s for s in out if not s["on_device"]["n"]]
    return {"device_id": device_id, "scanned_at": seen_at, "kind": dkind, "apps": apps, "systems": on + off,
            "others": others, "stage_root": root.replace("/", "\\")}


# ---------------------------------------------------------------- actions

def _record(conn, device_id, path, name, kind, size, md5=None):
    now = db.now()
    conn.execute("INSERT OR REPLACE INTO device_sysfiles(device_id,path,name,kind,size,seen_at) VALUES(?,?,?,?,?,?)",
                 (device_id, path, name, kind, size, now))
    if md5:
        conn.execute("INSERT OR REPLACE INTO device_sysfile_hashes(device_id,path,name,size,hash) VALUES(?,?,?,?,?)",
                     (device_id, path, name, size, md5))


def stage(device_id, dest, system, progress=None):
    """Add / Update: put every store-present file of the system into ROMs\\bios\\<system>, replacing
    staged copies that differ. Returns {system row, placed: [names], skipped: [names]}."""
    if system not in SYSTEMS:
        raise ValueError(f"unknown system {system}")
    roms, _ = _roms_root(device_id)
    folder = _stage_path(roms, system)
    before = next(s for s in readiness(device_id)["systems"] if s["system"] == system)
    conn = db.connect()
    placed, skipped = [], []
    for row, req in zip(before["requirements"], SYSTEMS[system][2]):
        if not row["store_present"]:
            skipped.append(row["name"])
            continue
        if row["staged"] == "current":
            skipped.append(row["name"])
            continue
        st = store_item(req)
        if progress:
            progress(f"copying {row['staged_name']}")
        if row["staged"] in ("different", "staged"):
            dest.delete_file(folder, row["staged_name"])
        size = dest.put_file(folder, st["path"], create=True)
        _record(conn, device_id, folder, row["staged_name"], "file", size, st["md5"])
        placed.append(row["staged_name"])
    _record(conn, device_id, folder, "", "folder", 0)
    conn.commit()
    after = next(s for s in readiness(device_id)["systems"] if s["system"] == system)
    return {"system": after, "placed": placed, "skipped": skipped}


def unstage(device_id, dest, system):
    """Remove: delete the system's staged files from ROMs\\bios\\<system> (the folder stays)."""
    if system not in SYSTEMS:
        raise ValueError(f"unknown system {system}")
    roms, _ = _roms_root(device_id)
    folder = _stage_path(roms, system)
    before = next(s for s in readiness(device_id)["systems"] if s["system"] == system)
    conn = db.connect()
    removed = []
    for row in before["requirements"]:
        if row["staged"] in ("current", "different", "staged"):
            if not dest.delete_file(folder, row["staged_name"]):
                raise RuntimeError(f"{row['staged_name']} is still on the device after the delete")
            conn.execute("DELETE FROM device_sysfiles WHERE device_id=? AND path=? AND name=?", (device_id, folder, row["staged_name"]))
            conn.execute("DELETE FROM device_sysfile_hashes WHERE device_id=? AND path=? AND name=?", (device_id, folder, row["staged_name"]))
            removed.append(row["staged_name"])
    conn.commit()
    after = next(s for s in readiness(device_id)["systems"] if s["system"] == system)
    return {"system": after, "removed": removed}


def remove_other(device_id, dest, rel, name):
    """Delete one stray file or folder under ROMs\\bios."""
    roms, _ = _roms_root(device_id)
    root = f"{roms}/bios"
    rel = rel.replace("\\", "/")
    if not (rel == root or rel.startswith(root + "/")):
        raise ValueError("only files under ROMs\\bios can be removed here")
    if not dest.delete_file(rel, name):
        raise RuntimeError(f"{name} is still on the device after the delete")
    conn = db.connect()
    conn.execute("DELETE FROM device_sysfiles WHERE device_id=? AND path=? AND name=?", (device_id, rel, name))
    conn.execute("DELETE FROM device_sysfiles WHERE device_id=? AND path=?", (device_id, f"{rel}/{name}"))
    conn.execute("DELETE FROM device_sysfile_hashes WHERE device_id=? AND path=? AND name=?", (device_id, rel, name))
    conn.commit()
    return readiness(device_id)["others"]


# ---------------------------------------------------------------- store-only view (no device)

def store_status():
    """Every requirement with only the store side, for the page when no device is chosen."""
    out = []
    for key, (emu, _, reqs, note) in SYSTEMS.items():
        for r in reqs:
            st = store_item(r)
            out.append({"system": key, "emulator": emu, "name": r["name"], "required": r["required"],
                        "store_present": st["present"], "store_size": st["size"], "store_verified": st["verified"],
                        "store_path": st["path"], "note": r["note"]})
    return out
