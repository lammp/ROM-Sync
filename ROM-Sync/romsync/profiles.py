"""Profiles: the app's memory of each device.

A device is recognised by the ROM-Sync.json file at its ROMs root (drives and USB
devices alike); a USB device without one is also matched by its shell path. The
file on the device carries enough to rebuild the profile on another PC.
"""
import json

from . import db, devices


def _dest_for(row):
    if row["kind"] == "volume":
        return None   # a volume needs its current letter; resolved at recognition time
    if row["kind"] == "adb":
        return devices.AdbDest(row["mtp_device_id"], row["roms_root"])
    return devices.MtpDest(row["mtp_device_id"], row["mtp_storage_id"], row["roms_root"])


def list_profiles():
    return [dict(r) for r in db.connect().execute("SELECT * FROM devices ORDER BY name").fetchall()]


def get(device_id):
    r = db.connect().execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchone()
    return dict(r) if r else None


def recognise(roms_root="ROMs"):
    """Look at everything plugged in and say which profile each one is, if any.

    Returns a list of candidates: {dest, kind, label, profile (dict or None), marker (dict or None), info}.
    """
    p = devices.probe()
    conn = db.connect()
    out = []
    # A drive's ROMs root may be nested (E:\Emulation\ROMs); try every root a volume profile has used.
    known_roots = [roms_root] + sorted({r["roms_root"] for r in conn.execute(
        "SELECT roms_root FROM devices WHERE kind='volume'")} - {roms_root})
    for v in p["volumes"]:
        dest, marker, prof = devices.VolumeDest(v["letter"], roms_root), None, None
        for root in known_roots:
            d = devices.VolumeDest(v["letter"], root)
            m = d.read_marker() if d.root_exists() else None
            if m and m.get("id"):
                r = conn.execute("SELECT * FROM devices WHERE id=?", (m["id"],)).fetchone()
                dest, marker, prof = d, m, (dict(r) if r else None)
                break
        out.append({"dest": dest, "kind": "volume", "label": f"{v['letter']} {v['label'] or ''}".strip(),
                    "profile": prof, "marker": marker,
                    "info": {"capacity": v["size"], "free": v["free"], "filesystem": v["fs"],
                             "serial": v["serial"], "removable": v["removable"]}})
    # ADB first: an Android handheld may also be visible over MTP, and when both are
    # present ADB supersedes it. They are matched by the ROM-Sync.json marker rather than
    # by USB serial, because the MTP shell path drops the serial once ADB is enabled.
    adb_markers = set()
    for a in p.get("adb", []):
        if a.get("state") != "device":
            out.append({"dest": None, "kind": "adb", "label": f"{a['label']} (adb, {a.get('state')})",
                        "profile": None, "marker": None,
                        "info": {"capacity": None, "free": None, "filesystem": "adb",
                                 "serial": a["serial"], "state": a.get("state")}})
            continue
        dest, marker, prof = devices.AdbDest(a["serial"], roms_root, label=a["label"]), None, None
        for root in known_roots:
            d2 = devices.AdbDest(a["serial"], root, label=a["label"])
            m = d2.read_marker() if d2.root_exists() else None
            if m and m.get("id"):
                r = conn.execute("SELECT * FROM devices WHERE id=?", (m["id"],)).fetchone()
                dest, marker, prof = d2, m, (dict(r) if r else None)
                adb_markers.add(m["id"])
                break
        if prof is None:
            r = conn.execute("SELECT * FROM devices WHERE kind='adb' AND mtp_device_id=?",
                             (a["serial"],)).fetchone()
            prof = dict(r) if r else None
        out.append({"dest": dest, "kind": "adb", "label": f"{a['label']} (adb)",
                    "profile": prof, "marker": marker, "info": dest.info()})
    for d in p["mtp"]:
        for s in d["storages"]:
            dest = devices.MtpDest(d["name"], s["name"], roms_root)
            if adb_markers:
                m = None
                try:
                    m = dest.read_marker()
                except Exception:  # noqa: BLE001 - a duplicate check must never break the list
                    m = None
                if m and m.get("id") in adb_markers:
                    continue           # same handheld, already listed on the faster transport
            r = conn.execute("SELECT * FROM devices WHERE kind='mtp' AND mtp_device_id=? AND mtp_storage_id=?",
                             (d["name"], s["name"])).fetchone()
            prof = dict(r) if r else None
            out.append({"dest": dest, "kind": "mtp", "label": f"{d['name']} \\ {s['name']}",
                        "profile": prof, "marker": None,
                        "info": {"capacity": s.get("capacity"), "free": s.get("free"), "filesystem": "mtp",
                                 "serial": None, "path": d.get("path")}})
    return out


def create(candidate, name, write_marker=True):
    """Make a profile for a plugged-in destination. Writes ROM-Sync.json unless told not to."""
    dest, info = candidate["dest"], candidate["info"]
    conn = db.connect()
    did = db.new_id()
    now = db.now()
    conn.execute(
        """INSERT INTO devices(id,name,kind,volume_serial,mtp_device_id,mtp_storage_id,roms_root,
                               capacity,free,filesystem,first_seen,last_seen)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (did, name, dest.kind, info.get("serial"),
         getattr(dest, "device_name", None) or getattr(dest, "serial", None),
         getattr(dest, "storage_name", None),
         dest.roms_root, info.get("capacity"), info.get("free"), info.get("filesystem"), now, now))
    conn.commit()
    if write_marker:
        dest.write_marker(marker_for(did))
    return did


def adopt(candidate, marker):
    """Rebuild a profile from the file on a device this PC has not seen."""
    conn = db.connect()
    now = db.now()
    dest, info = candidate["dest"], candidate["info"]
    conn.execute(
        """INSERT OR IGNORE INTO devices(id,name,kind,volume_serial,mtp_device_id,mtp_storage_id,roms_root,
                               capacity,free,filesystem,first_seen,last_seen)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (marker["id"], marker.get("name", "Adopted device"), dest.kind, info.get("serial"),
         getattr(dest, "device_name", None) or getattr(dest, "serial", None),
         getattr(dest, "storage_name", None),
         dest.roms_root, info.get("capacity"), info.get("free"), info.get("filesystem"),
         marker.get("created", now), now))
    for s in marker.get("selection", {}).get("systems", []):
        conn.execute("INSERT OR REPLACE INTO selections(device_id,system,mode) VALUES(?,?,?)",
                     (marker["id"], s, "all"))
    for f in marker.get("inventory", []):
        conn.execute(
            """INSERT OR REPLACE INTO device_files(device_id,rel_path,kind,size,hash,sent_size,sent_mtime,last_confirmed)
               VALUES(?,?,?,?,?,?,?,?)""",
            (marker["id"], f["path"], f.get("kind", "file"), f.get("size"), f.get("hash"),
             f.get("sent_size"), f.get("sent_mtime"), f.get("confirmed")))
    conn.commit()
    return marker["id"]


def marker_for(device_id):
    """The ROM-Sync.json content: identity, selection, inventory, run history."""
    conn = db.connect()
    d = get(device_id)
    sel = [r["system"] for r in conn.execute(
        "SELECT system FROM selections WHERE device_id=? AND mode='all'", (device_id,))]
    inv = [{"path": r["rel_path"], "kind": r["kind"], "size": r["size"], "hash": r["hash"],
            "sent_size": r["sent_size"], "sent_mtime": r["sent_mtime"], "confirmed": r["last_confirmed"]}
           for r in conn.execute("SELECT * FROM device_files WHERE device_id=? AND missing_since IS NULL "
                                 "ORDER BY rel_path", (device_id,))]
    runs = [{"started": r["started"], "finished": r["finished"], "state": r["state"], "counts": r["counts"]}
            for r in conn.execute("SELECT * FROM sync_runs WHERE device_id=? ORDER BY id DESC LIMIT 20",
                                  (device_id,))]
    return {"app": "ROM-Sync", "format": 1, "id": d["id"], "name": d["name"], "kind": d["kind"],
            "roms_root": d["roms_root"], "created": d["first_seen"], "written": db.now(),
            "selection": {"systems": sel}, "inventory": inv, "runs": runs}


def scan_into(device_id, dest, systems=None, progress=None):
    """Read the device and update the profile's inventory. Read-only on the device."""
    conn = db.connect()
    if systems is None:
        systems = [r["key"] for r in conn.execute("SELECT key FROM systems")] + ["bios"]
    rows = dest.scan(systems=systems, progress=progress)
    if rows and rows[0][0] == "ERROR":
        raise RuntimeError(rows[0][1])
    now = db.now()
    seen_folders = [r[1] for r in rows if r[2] == "seen"]
    present = {}
    for system, name, kind, size in rows:
        if kind == "seen" or not devices.is_game_unit(name, kind):
            continue
        rel = f"{system}\\{name}"
        k = "sysfile" if system == "bios" else kind
        present[rel] = (k, size)
        conn.execute(
            """INSERT INTO device_files(device_id,rel_path,kind,size,last_confirmed,missing_since)
               VALUES(?,?,?,?,?,NULL)
               ON CONFLICT(device_id,rel_path) DO UPDATE SET kind=excluded.kind, size=excluded.size,
                 last_confirmed=excluded.last_confirmed, missing_since=NULL""",
            (device_id, rel, k, size, now))
    # Anything previously recorded in a scanned system but not seen now is missing.
    scanned = set(systems)
    for r in conn.execute("SELECT rel_path, kind FROM device_files WHERE device_id=? AND missing_since IS NULL",
                          (device_id,)).fetchall():
        rel = r["rel_path"]
        sysname, _, leaf = rel.partition("\\")
        if not devices.is_game_unit(leaf, r["kind"]):
            conn.execute("DELETE FROM device_files WHERE device_id=? AND rel_path=?", (device_id, rel))
            continue
        if sysname in scanned and rel not in present:
            conn.execute("UPDATE device_files SET missing_since=? WHERE device_id=? AND rel_path=?",
                         (now, device_id, rel))
    conn.execute("UPDATE devices SET last_seen=? WHERE id=?", (now, device_id))
    conn.commit()
    return {"folders_seen": len(seen_folders), "files": len(present),
            "systems_scanned": sorted(set(s for s, _, k, _ in rows if k != "seen"))}


def summary(device_id):
    conn = db.connect()
    per = conn.execute(
        """SELECT substr(rel_path,1,instr(rel_path,'\\')-1) AS system, COUNT(*) AS n, SUM(size) AS bytes
           FROM device_files WHERE device_id=? AND missing_since IS NULL GROUP BY 1 ORDER BY 1""",
        (device_id,)).fetchall()
    return [dict(r) for r in per]
