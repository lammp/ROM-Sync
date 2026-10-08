"""Turning a device's selection into a list of ops.

The selection is per device: whole systems (selections.mode all|none) with
per-game overrides (selection_overrides.include); a store system with no row
counts as none. The plan mirrors the selection onto the device (see plan()):
send / update / remove. Every store system is managed; folders on the
device that are not store systems are left alone. bios is handled by the
system files registry, not here.
"""
import os

from . import db, transfer

UNMANAGED_ALWAYS = {"bios", "emulators"}


def selection(device_id):
    conn = db.connect()
    modes = {r["system"]: r["mode"] for r in conn.execute(
        "SELECT system, mode FROM selections WHERE device_id=?", (device_id,))}
    overrides = {r["game_id"]: bool(r["include"]) for r in conn.execute(
        "SELECT game_id, include FROM selection_overrides WHERE device_id=?", (device_id,))}
    return modes, overrides


def set_system(device_id, system, mode):
    """mode: all | none | off (off = not managed: the app never touches that system on this device)."""
    if mode not in ("all", "none", "off"):
        raise ValueError(mode)
    conn = db.connect()
    if mode == "off":
        conn.execute("DELETE FROM selections WHERE device_id=? AND system=?", (device_id, system))
    else:
        conn.execute("INSERT OR REPLACE INTO selections(device_id,system,mode) VALUES(?,?,?)", (device_id, system, mode))
    # A whole-system choice clears per-game overrides for that system.
    conn.execute("DELETE FROM selection_overrides WHERE device_id=? AND game_id IN "
                 "(SELECT id FROM games WHERE system=?)", (device_id, system))
    conn.commit()


def set_game(device_id, game_id, include):
    conn = db.connect()
    conn.execute("INSERT OR REPLACE INTO selection_overrides(device_id,game_id,include) VALUES(?,?,?)",
                 (device_id, game_id, 1 if include else 0))
    conn.commit()


def decide(device_id, rel_path, decision):
    if decision not in ("leave", "pull", "remove"):
        raise ValueError(decision)
    conn = db.connect()
    conn.execute("INSERT OR REPLACE INTO decisions(device_id,rel_path,decision,decided_at) VALUES(?,?,?,?)",
                 (device_id, rel_path, decision, db.now()))
    conn.commit()


def set_games(device_id, game_ids, include):
    """Bulk include/exclude. Stored as the minimal override: a game whose system mode already gives
    the wanted state gets no override row; otherwise an override row. Unmanaged systems are left alone."""
    conn = db.connect()
    modes, _ = selection(device_id)
    rows = conn.execute("SELECT id, system FROM games WHERE id IN (%s)" % ",".join("?" * len(game_ids)),
                        list(game_ids)).fetchall() if game_ids else []
    changed = 0
    for r in rows:
        mode = modes.get(r["system"])
        if mode is None:
            continue
        if (mode == "all") == bool(include):
            conn.execute("DELETE FROM selection_overrides WHERE device_id=? AND game_id=?", (device_id, r["id"]))
        else:
            conn.execute("INSERT OR REPLACE INTO selection_overrides(device_id,game_id,include) VALUES(?,?,?)",
                         (device_id, r["id"], 1 if include else 0))
        changed += 1
    conn.commit()
    return changed


def clear_selection(device_id):
    """Nothing selected: every managed system to 'none', all per-game overrides dropped. Systems stay
    managed, so a later sync still removes what the device holds for them."""
    conn = db.connect()
    conn.execute("UPDATE selections SET mode='none' WHERE device_id=?", (device_id,))
    conn.execute("DELETE FROM selection_overrides WHERE device_id=?", (device_id,))
    conn.commit()


def selected_games(device_id):
    """Games the selection says should be on the device: {rel_path: game_row}."""
    modes, overrides = selection(device_id)
    conn = db.connect()
    out = {}
    for g in conn.execute("SELECT * FROM games"):
        g = dict(g)
        if g["system"] in UNMANAGED_ALWAYS:
            continue
        mode = modes.get(g["system"])
        if mode is None:
            continue
        inc = overrides.get(g["id"], mode == "all")
        if inc:
            out[f"{g['system']}\\{g['name']}"] = g
    return out


# Folders an emulator creates inside a system folder to hold its own state. A sync never
# removes these. ROM-Sync did not put them there, they hold the person's saves, cheats and
# NAND, and the mirror would otherwise treat them as unselected games and delete them.
# Found 2026-09-17: a scan recorded psp\\PSP (every PPSSPP save) and n3ds\\nand, both of
# which the remove pass would have taken out on the next sync.
EMULATOR_STATE = {
    "psp", "nand", "cheats", "sdmc", "textures", "dump", "dumps", "states", "savestates",
    "saves", "savedata", "save", "sstates", "memcards", "shaders", "screenshots", "config",
    "system", "bios", "covers", "media", "images", "videos", "manuals", "gamesettings",
    "inputprofiles", "logs", "snaps", "cache",
}


def plan(device_id, free_bytes=None):
    """Mirror plan: after the sync, every store system on the device holds exactly the selected
    games. Nothing is wiped; the plan is the tactical difference:

        send     selected, not on the device
        update   selected, on the device, but the store copy differs or is newer
        remove   on the device in a store system, not selected (whether or not the store has a copy)
        unknown_systems   folders on the device that are not store systems: untouched, reported

    Games only: the bios folder and system files are never sent or removed by a sync.
    """
    conn = db.connect()
    store_systems = {r["key"] for r in conn.execute("SELECT key FROM systems")}
    managed = store_systems - UNMANAGED_ALWAYS
    wanted = selected_games(device_id)
    on_device = {r["rel_path"]: dict(r) for r in conn.execute(
        "SELECT * FROM device_files WHERE device_id=? AND missing_since IS NULL", (device_id,))}

    send, update, remove, unchanged = [], [], [], []
    unknown = {}
    for rel, g in wanted.items():
        d = on_device.get(rel)
        if d is None:
            send.append(transfer.op_from_game("send", g))
            continue
        newer = d.get("sent_mtime") is not None and g["mtime"] is not None and g["mtime"] > d["sent_mtime"] + 1
        differs = (d.get("sent_size") is not None and d["sent_size"] != g["size"]) or \
                  (d.get("sent_size") is None and d.get("size") is not None and d["size"] != g["size"])
        if newer or differs:
            update.append(transfer.op_from_game("update", g))
        else:
            unchanged.append(rel)

    for rel, d in on_device.items():
        system = rel.split("\\", 1)[0]
        if system == "bios":
            continue                      # system files are reconciled by sysfiles, never removed here
        if system not in managed:
            unknown[system] = unknown.get(system, 0) + 1
            continue
        if rel in wanted:
            continue
        name = rel.split("\\", 1)[1]
        if d["kind"] == "folder" and name.lower() in EMULATOR_STATE:
            continue                      # emulator state, not a game: never removed by a sync
        remove.append(transfer.make_op("remove", system, name, d["kind"], d.get("size") or 0))

    for lst in (send, update, remove):
        lst.sort(key=lambda o: (o["system"], o["name"].lower()))
    used = sorted({g["system"] for g in wanted.values()})
    add = sum(o["size"] for o in send) + sum(o["size"] for o in update)
    drop = sum(o["size"] for o in remove) + \
        sum(on_device[f"{o['system']}\\{o['name']}"].get("size") or 0
            for o in update if f"{o['system']}\\{o['name']}" in on_device)
    net = add - drop
    fits = None if free_bytes is None else (free_bytes - net) > 512 * 1024 * 1024
    return {"device_id": device_id, "send": send, "update": update, "remove": remove,
            "unknown_systems": unknown,
            "unchanged": len(unchanged), "managed_systems": used,
            "bytes": {"add": add, "drop": drop, "net": net, "free": free_bytes, "fits": fits}}


def ops_of(p):
    """The ops a plan would run, in worker order."""
    return list(p["remove"]) + list(p["update"]) + list(p["send"])


def summary(p):
    s = {k: {"n": len(p[k]), "bytes": sum(o["size"] for o in p[k])} for k in ("send", "update", "remove")}
    s["unknown_systems"] = p["unknown_systems"]
    s["unchanged"] = p["unchanged"]
    s["bytes"] = p["bytes"]
    return s
