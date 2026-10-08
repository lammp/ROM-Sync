"""Local HTTP server behind the desktop window.

Serves the UI (ui\), cover art (data\covers) and a JSON API on 127.0.0.1.
Everything long (device scan, sync) runs as a job in a thread and is polled.
"""
import json
import os
import threading
import time
import traceback
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

from . import db, profiles, planner, transfer, sysfiles, tags, scanner, devices, enrich, scrape, reason, thumbs

UI_DIR = os.path.join(db.app_dir(), "ui")
COVERS = os.path.join(db.data_dir(), "covers")

# ---------------------------------------------------------------- jobs

_jobs = {}
_jobs_lock = threading.Lock()


def _job(kind, target, with_progress=False, with_state=False, **meta):
    """Run target in a thread. with_progress=True: target(progress_fn) and the job carries a 'progress' line.
    with_state=True: target(state) so a long job can update its own fields (phase, run) as it goes."""
    jid = f"{kind}-{int(time.time() * 1000)}"
    state = {"id": jid, "kind": kind, "state": "running", "started": db.now(), "result": None, "error": None,
             "progress": "", **meta}
    with _jobs_lock:
        _jobs[jid] = state

    def run():
        try:
            state["result"] = (target(lambda m: state.__setitem__("progress", m)) if with_progress
                               else target(state) if with_state else target())
            state["state"] = "done"
        except Exception as e:  # noqa: BLE001
            state["error"] = f"{e}\n{traceback.format_exc()[-1500:]}"
            state["state"] = "error"
        state["finished"] = db.now()

    threading.Thread(target=run, daemon=True, name=jid).start()
    return state


# ---------------------------------------------------------------- devices (cached probe)

_cands = {"at": 0, "list": [], "error": None}
_cands_lock = threading.Lock()


def candidates(refresh=False):
    with _cands_lock:
        if refresh or time.time() - _cands["at"] > 45:
            try:
                _cands["list"] = profiles.recognise()
                _cands["error"] = None
            except Exception as e:  # noqa: BLE001 - a failed probe must not take the page down
                _cands["list"] = []
                _cands["error"] = str(e)
            _cands["at"] = time.time()
        return _cands["list"]


def _cand_json(i, c):
    return {"index": i, "kind": c["kind"], "label": c["label"], "roms_root": c["dest"].roms_root,
            "profile": ({"id": c["profile"]["id"], "name": c["profile"]["name"]} if c["profile"] else None),
            "marker": ({"id": c["marker"].get("id"), "name": c["marker"].get("name")} if c["marker"] else None),
            "info": {k: v for k, v in c["info"].items() if k != "path"},
            "is_store_drive": c["kind"] == "volume" and c["dest"].letter == db.store_root()[:2].upper()}


def device_entries():
    """One list for the Devices page: every profile, plus anything plugged in without one.

    A profile carries its own online state, so the same handheld is never shown twice.
    The store drive is filtered out: it is where the library lives, never a destination.
    """
    conn = db.connect()
    cands = candidates()
    store_letter = db.store_root()[:2].upper()
    by_profile = {}
    for i, c in enumerate(cands):
        if c["kind"] == "volume" and getattr(c["dest"], "letter", "") == store_letter:
            continue                       # the store drive is not a destination
        if c["profile"]:
            by_profile[c["profile"]["id"]] = (i, c)

    out = []
    for p in profiles.list_profiles():
        i, c = by_profile.get(p["id"], (None, None))
        online = c is not None
        info = c["info"] if online else {"capacity": p.get("capacity"), "free": p.get("free"),
                                         "filesystem": p.get("filesystem")}
        sel = conn.execute("SELECT COUNT(*) n FROM selection_overrides WHERE device_id=? AND include=1",
                           (p["id"],)).fetchone()["n"]
        on_dev = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(size),0) b FROM device_files "
                              "WHERE device_id=? AND missing_since IS NULL", (p["id"],)).fetchone()
        out.append({"kind": "profile", "id": p["id"], "name": p["name"], "online": online,
                    "index": i, "transport": (c["kind"] if online else p["kind"]),
                    "label": (c["label"] if online else ""), "roms_root": p["roms_root"],
                    "last_seen": p.get("last_seen"), "info": info,
                    "selected": sel, "on_device": on_dev["n"], "on_device_bytes": on_dev["b"]})

    known = {p["id"] for p in profiles.list_profiles()}
    for i, c in enumerate(cands):
        if c["kind"] == "volume" and getattr(c["dest"], "letter", "") == store_letter:
            continue
        if c["profile"] and c["profile"]["id"] in known:
            continue
        out.append({"kind": "candidate", "index": i, "transport": c["kind"], "label": c["label"],
                    "roms_root": c["dest"].roms_root if c["dest"] else "",
                    "info": c["info"], "marker": (c["marker"] or None),
                    "state": c["info"].get("state")})
    out.sort(key=lambda e: (e["kind"] != "profile", not e.get("online", False), (e.get("name") or e.get("label") or "").lower()))
    return out


def _cand_for(device_id):
    for c in candidates():
        if c["profile"] and c["profile"]["id"] == device_id:
            return c
    return None


# ---------------------------------------------------------------- library

def library():
    conn = db.connect()
    systems = {r["key"]: r["label"] for r in conn.execute("SELECT key, label FROM systems")}
    all_tags = tags.for_all()
    rows = []
    for g in conn.execute("SELECT id, system, name, title, region, size, mtime, kind, file_count, scrape_state, "
                          "igdb_id, igdb_name, release_date, rating, rating_count, genres, cover_file FROM games"):
        try:
            genres = json.loads(g["genres"]) if g["genres"] else []
        except ValueError:
            genres = []
        year = time.gmtime(g["release_date"]).tm_year if g["release_date"] else None
        rows.append({"id": g["id"], "system": g["system"], "name": g["name"], "title": g["title"],
                     "region": g["region"], "size": g["size"], "kind": g["kind"], "files": g["file_count"],
                     "matched": g["scrape_state"] == "matched", "igdb": g["igdb_name"], "year": year,
                     "rating": round(g["rating"]) if g["rating"] else None, "votes": g["rating_count"],
                     "genres": genres, "cover": g["cover_file"] or None,
                     "tags": all_tags.get(g["id"], [])})
    return {"systems": systems, "games": rows, "store": db.store_root()}


def game_detail(gid):
    conn = db.connect()
    g = conn.execute("SELECT * FROM games WHERE id=?", (gid,)).fetchone()
    if not g:
        return None
    d = dict(g)
    d["genres"] = json.loads(d["genres"]) if d.get("genres") else []
    d["tags"] = tags.for_all().get(gid, [])
    d["path"] = os.path.join(db.store_root(), d["rel_path"])
    # other versions: same title (or igdb id) on other systems
    d["versions"] = [dict(r) for r in conn.execute(
        "SELECT id, system, name, size, region FROM games WHERE id != ? AND ("
        "(igdb_name IS NOT NULL AND lower(igdb_name) = lower(?)) OR (igdb_id IS NOT NULL AND igdb_id = ?) "
        "OR lower(title) = lower(?)) ORDER BY system",
        (gid, d.get("igdb_name") or "", d.get("igdb_id"), d.get("title") or ""))]
    d["media"] = enrich.media_for(gid)
    d["on_devices"] = [r["name"] for r in conn.execute(
        "SELECT d.name FROM device_files f JOIN devices d ON d.id = f.device_id "
        "WHERE f.rel_path = ? AND f.missing_since IS NULL AND d.name != '_test'", (f"{d['system']}\\{d['name']}",))]
    return d


# ---------------------------------------------------------------- settings

def _dir_stats(path):
    n = b = 0
    if os.path.isdir(path):
        for e in os.scandir(path):
            if e.is_file():
                n += 1
                b += e.stat().st_size
    return {"files": n, "bytes": b}


def settings_view():
    conn = db.connect()
    tags.ensure()
    cfg = db.get_config()
    counts = {r["scrape_state"]: r["n"] for r in conn.execute(
        "SELECT scrape_state, COUNT(*) AS n FROM games GROUP BY scrape_state")}
    dbp = db.db_path() if hasattr(db, "db_path") else os.path.join(db.data_dir(), "romsync.db")
    return {"store_root": db.store_root(), "data_dir": db.data_dir(), "app_dir": db.app_dir(),
            "igdb": {"client_id": cfg.get("client_id", ""), "has_secret": bool(cfg.get("client_secret"))},
            "counts": {"games": sum(counts.values()), "matched": counts.get("matched", 0),
                       "unmatched": counts.get("unmatched", 0), "pending": counts.get("pending", 0) + counts.get("error", 0),
                       "nocover": conn.execute("SELECT COUNT(*) FROM games WHERE cover_file IS NULL OR cover_file=''").fetchone()[0],
                       "libretro": conn.execute("SELECT COUNT(*) FROM games WHERE cover_file LIKE 'lr-%'").fetchone()[0],
                       "proposed": conn.execute("SELECT COUNT(*) FROM tags WHERE state='proposed'").fetchone()[0],
                       "systems": conn.execute("SELECT COUNT(*) FROM systems").fetchone()[0],
                       "devices": conn.execute("SELECT COUNT(*) FROM devices WHERE name != '_test'").fetchone()[0]},
            "db": {"path": dbp, "bytes": os.path.getsize(dbp) if os.path.isfile(dbp) else 0},
            "covers": _dir_stats(os.path.join(db.data_dir(), "covers")),
            "screens": _dir_stats(os.path.join(db.data_dir(), "screens")),
            "jobs": [{k: v for k, v in j.items() if k != "result"} for j in list(_jobs.values())[-8:]]}


# ---------------------------------------------------------------- profile views

def profile_view(device_id):
    p = profiles.get(device_id)
    if not p:
        return None
    modes, overrides = planner.selection(device_id)
    c = _cand_for(device_id)
    info = c["info"] if c else {}
    conn = db.connect()
    per_system = {r["system"]: {"n": r["n"], "bytes": r["bytes"]} for r in profiles.summary(device_id)}
    store = {r["key"]: {"n": r["games"], "bytes": r["bytes"]} for r in db.system_rows()}
    on_device = [r["rel_path"] for r in conn.execute(
        "SELECT rel_path FROM device_files WHERE device_id=? AND missing_since IS NULL", (device_id,))]
    runs = [dict(r) for r in conn.execute(
        "SELECT id, started, finished, state, counts, bytes_moved FROM sync_runs WHERE device_id=? "
        "ORDER BY id DESC LIMIT 15", (device_id,))]
    decisions = {r["rel_path"]: r["decision"] for r in conn.execute(
        "SELECT rel_path, decision FROM decisions WHERE device_id=?", (device_id,))}
    return {"profile": p, "connected": c is not None, "info": info, "modes": modes,
            "overrides": {str(k): v for k, v in overrides.items()},
            "device_systems": per_system, "store_systems": store, "on_device": on_device,
            "runs": runs, "decisions": decisions,
            "readiness": sysfiles.readiness(device_id)["systems"]}


def plan_view(device_id):
    c = _cand_for(device_id)
    p = planner.plan(device_id, c["info"].get("free") if c else None)
    return {**p, "summary": planner.summary(p)}


FULL_MARGIN = 512 * 1024 * 1024   # bytes that must stay free after a sync for the device to count as "fits"


def _sync_log(rid, did, cand, summary, res):
    """One line per sync in data\\records\\sync-log.tsv, plus the run's own folder (data\\runs\\<id>\\:
    plan.tsv, results.tsv per op, status.json). The triage skill starts from these."""
    try:
        rec = os.path.join(db.data_dir(), "records", "sync-log.tsv")
        new = not os.path.exists(rec)
        fails = [r for r in transfer.read_results(rid) if r["result"] != "ok"]
        with open(rec, "a", encoding="utf-8") as f:
            if new:
                f.write("run\tdevice\tstarted\tfinished\tsend\tupdate\tremove\tsent\tremoved\tfailed\tbytes\tfailed_items\n")
            f.write("\t".join(str(x) for x in [
                rid, cand["profile"]["name"], res.get("started", ""), db.now(),
                summary["send"]["n"], summary["update"]["n"], summary["remove"]["n"],
                res.get("sent", 0), res.get("removed", 0), res.get("failed", 0), res.get("bytes", 0),
                "; ".join(f"{r['op']} {r['system']}\\{r['name']}: {r['detail']}" for r in fails)]) + "\n")
    except Exception:  # noqa: BLE001 - the log must never fail a sync
        pass


def _device_busy(device_id):
    """A sync or scan is running for this device: no second worker on the same USB device."""
    with _jobs_lock:
        return any(j["state"] == "running" and j.get("device") == device_id and j["kind"] in ("sync", "scan", "scan-sysfiles", "sysfiles-stage")
                   for j in _jobs.values())


def capacity_view(device_id, refresh=False):
    """Live capacity meter for a device: what is selected (actual file sizes), what is on the
    device now, and the projected fill after the pending sync. Colour bands: green < 80 %,
    yellow 80-90 %, red >= 90 %; "full" when the sync would leave less than FULL_MARGIN free."""
    if refresh:
        candidates(refresh=True)
    c = _cand_for(device_id)
    conn = db.connect()
    prof = conn.execute("SELECT capacity, free, last_seen FROM devices WHERE id=?", (device_id,)).fetchone()
    if c:
        cap, free, live = c["info"].get("capacity"), c["info"].get("free"), True
        if cap:
            conn.execute("UPDATE devices SET capacity=?, free=? WHERE id=?", (cap, free, device_id))
            conn.commit()
    else:
        cap, free, live = (prof["capacity"] if prof else None), (prof["free"] if prof else None), False
    wanted = planner.selected_games(device_id)
    sel_bytes = sum((g.get("size") or 0) for g in wanted.values())
    od = conn.execute("SELECT COUNT(*) AS n, COALESCE(SUM(size),0) AS b FROM device_files "
                      "WHERE device_id=? AND missing_since IS NULL", (device_id,)).fetchone()
    plan = planner.plan(device_id, free)
    b = plan["bytes"]
    out = {"connected": live, "capacity": cap, "free": free, "probed_at": _cands["at"],
           "last_seen": prof["last_seen"] if prof else None,
           "selected": {"n": len(wanted), "bytes": sel_bytes},
           "on_device": {"n": od["n"], "bytes": od["b"]},
           "plan": {"add": b["add"], "drop": b["drop"], "net": b["net"]}, "state": "unknown"}
    if cap and free is not None:
        after_free = free - b["net"]
        used_after = cap - after_free
        frac = used_after / cap
        out["after"] = {"used": used_after, "free": after_free, "fraction": frac}
        out["short_by"] = max(0, FULL_MARGIN - after_free)
        out["state"] = ("full" if after_free < FULL_MARGIN else "red" if frac >= 0.90
                        else "yellow" if frac >= 0.80 else "green")
    return out


# ---------------------------------------------------------------- handler

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype=None):
        if not os.path.isfile(path):
            self.send_error(404)
            return
        ctype = ctype or self.guess_type(path)
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if path.startswith(COVERS):
            self.send_header("Cache-Control", "max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def do_GET(self):
        u = urlparse(self.path)
        parts = [unquote(x) for x in u.path.strip("/").split("/") if x]
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if not parts:
                return self._file(os.path.join(UI_DIR, "index.html"), "text/html; charset=utf-8")
            if parts[0] == "ui":
                return self._file(os.path.join(UI_DIR, *parts[1:]))
            if parts[0] == "covers":
                return self._file(os.path.join(COVERS, parts[1]))
            if parts[0] == "screens" and len(parts) == 3:
                p = enrich.screenshot_path(parts[2], parts[1])
                return self._file(p) if p else self.send_error(404)
            if parts[0] != "api":
                return self.send_error(404)
            return self._api_get(parts[1:], q)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e), "trace": traceback.format_exc()[-2000:]}, 500)

    def do_POST(self):
        u = urlparse(self.path)
        parts = [unquote(x) for x in u.path.strip("/").split("/") if x]
        try:
            body = self._body()
            if parts[:1] != ["api"]:
                return self.send_error(404)
            return self._api_post(parts[1:], body)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e), "trace": traceback.format_exc()[-2000:]}, 500)

    # ---- GET
    def _api_get(self, p, q):
        if p == ["library"]:
            return self._json(library())
        if p[0] == "game":
            return self._json(game_detail(int(p[1])))
        if p == ["devices"]:
            cands = candidates(refresh=q.get("refresh") == "1")
            return self._json({"candidates": [_cand_json(i, c) for i, c in enumerate(cands)],
                               "profiles": [x for x in profiles.list_profiles() if x["name"] != "_test"],
                               "entries": device_entries(), "probed_at": _cands["at"], "probe_error": _cands["error"]})
        if p[0] == "profile" and len(p) == 2:
            v = profile_view(p[1])
            return self._json(v) if v else self._json({"error": "no such profile"}, 404)
        if p[0] == "profile" and p[2] == "plan":
            return self._json(plan_view(p[1]))
        if p[0] == "profile" and len(p) == 3 and p[2] == "capacity":
            return self._json(capacity_view(p[1], refresh=q.get("refresh") == "1"))
        if p[0] == "job":
            j = _jobs.get(p[1])
            return self._json(j) if j else self._json({"error": "no such job"}, 404)
        if p[0] == "run":
            rid = int(p[1])
            results = transfer.read_results(rid)
            moved = sum(r["size"] for r in results if r["result"] == "ok" and r["op"] in ("send", "update", "pull"))
            removed_bytes = 0
            if results:
                sizes = {(o["system"], o["name"]): o["size"] for o in transfer.load_ops(rid) if o["op"] == "remove"}
                removed_bytes = sum(sizes.get((r["system"], r["name"]), 0) for r in results
                                    if r["result"] == "ok" and r["op"] == "remove")
            out = {"status": transfer.read_status(rid), "bytes_done": moved, "bytes_removed": removed_bytes,
                   "failures": [r for r in results if r["result"] != "ok"]}
            if q.get("brief") != "1":
                out["results"] = results
                out["pulled"] = transfer.pulled_items(rid)
            return self._json(out)
        if p == ["sysfiles"]:
            if q.get("device"):
                return self._json(sysfiles.readiness(q["device"]))
            return self._json({"store": sysfiles.store_status()})
        if p == ["settings"]:
            return self._json(settings_view())
        if p == ["tags", "proposed"]:
            tags.ensure()
            rows = [dict(r) for r in db.connect().execute(
                "SELECT t.game_id, t.tag, t.kind, t.source, g.title, g.system FROM tags t JOIN games g ON g.id=t.game_id "
                "WHERE t.state='proposed' ORDER BY g.title")]
            return self._json(rows)
        return self._json({"error": "unknown endpoint"}, 404)

    # ---- POST
    def _api_post(self, p, b):
        if p == ["scan-store"]:
            return self._json(_job("scan-store", lambda: scanner.scan()))
        if p == ["enrich"]:
            return self._json(_job("enrich", lambda cb: enrich.run(progress=cb, only_missing=not b.get("all")),
                                   with_progress=True))
        if p == ["scrape"]:
            # match pending games against IGDB, then pull screenshots/tags for the new matches
            def go(cb):
                out = scrape.run(systems=b.get("systems"), only_pending=not b.get("all"), progress=cb,
                                 ids=b.get("ids"), states=(("unmatched",) if b.get("retry_unmatched") else None))
                out["enrich"] = enrich.run(progress=cb, only_missing=True)
                out["libretro"] = thumbs.run(progress=cb)   # covers IGDB could not give
                return out
            return self._json(_job("scrape", go, with_progress=True))
        if p == ["covers-libretro"]:
            return self._json(_job("covers-libretro", lambda cb: thumbs.run(progress=cb, refresh=bool(b.get("refresh"))),
                                   with_progress=True))
        if p == ["reason"]:
            return self._json(reason.propose())
        if p == ["settings"]:
            new = {}
            for k in ("store_root", "client_id", "client_secret"):
                v = (b.get(k) or "").strip()
                if v:
                    new[k] = v
            if "store_root" in new and not os.path.isdir(new["store_root"]):
                return self._json({"error": f"not a folder: {new['store_root']}"}, 400)
            if new:
                db.save_config(new)
            return self._json(settings_view())
        if p == ["tags", "decide-many"]:
            n = 0
            for it in b.get("items") or []:
                tags.decide(int(it["game_id"]), it["tag"], bool(b.get("accept")))
                n += 1
            return self._json({"ok": True, "n": n})
        if len(p) == 3 and p[0] == "game" and p[2] == "rematch":
            name = scrape.rematch(int(p[1]), b.get("igdb") or b.get("igdb_id"))
            enrich.run(only_missing=True)
            return self._json({"ok": True, "igdb_name": name})
        if p == ["profile", "new"]:
            c = candidates()[int(b["index"])]
            if b.get("roms_root"):
                if c["kind"] == "volume":
                    c["dest"] = devices.VolumeDest(c["dest"].letter, b["roms_root"])
                elif c["kind"] == "adb":
                    c["dest"] = devices.AdbDest(c["dest"].serial, b["roms_root"],
                                                c["dest"].storage, c["dest"].label)
                else:
                    c["dest"] = devices.MtpDest(c["dest"].device_name, c["dest"].storage_name, b["roms_root"])
            if c["kind"] in ("volume", "adb"):
                c["dest"].create_root()
            did = profiles.create(c, b["name"], write_marker=bool(b.get("marker", True)))
            candidates(refresh=True)
            return self._json({"id": did})
        if p == ["profile", "adopt"]:
            c = candidates()[int(b["index"])]
            did = profiles.adopt(c, c["marker"])
            candidates(refresh=True)
            return self._json({"id": did})
        if p[0] == "profile":
            did = p[1]
            action = p[2]
            if action == "select-system":
                planner.set_system(did, b["system"], b["mode"])
            elif action == "select-game":
                if b.get("include") is None:
                    conn = db.connect()
                    conn.execute("DELETE FROM selection_overrides WHERE device_id=? AND game_id=?", (did, b["game_id"]))
                    conn.commit()
                else:
                    planner.set_game(did, int(b["game_id"]), bool(b["include"]))
            elif action == "select-games":          # bulk: {game_ids: [...], include: true|false}
                n = planner.set_games(did, [int(x) for x in b.get("game_ids", [])], bool(b.get("include")))
                return self._json({"ok": True, "changed": n})
            elif action == "select-clear":
                planner.clear_selection(did)
            elif action == "decide":
                planner.decide(did, b["rel_path"], b["decision"])
            elif action == "decide-many":          # bulk: {items: [{rel_path, decision}]}
                for it in b.get("items", []):
                    planner.decide(did, it["rel_path"], it["decision"])
            elif action == "rename":
                conn = db.connect()
                conn.execute("UPDATE devices SET name=? WHERE id=?", (b["name"], did))
                conn.commit()
            elif action == "scan":
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                if _device_busy(did):
                    return self._json({"error": "the device is busy (a sync or scan is running)"}, 409)
                return self._json(_job("scan", lambda: profiles.scan_into(did, c["dest"]), device=did))
            elif action == "scan-sysfiles":            # read-only look at the emulator folders
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                if _device_busy(did):
                    return self._json({"error": "the device is busy (a sync or scan is running)"}, 409)
                return self._json(_job("scan-sysfiles", lambda cb: sysfiles.scan(did, c["dest"], progress=cb),
                                       with_progress=True, device=did))
            elif action in ("sysfiles-stage", "sysfiles-unstage", "sysfiles-remove-other"):
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                if _device_busy(did):
                    return self._json({"error": "the device is busy (a sync or scan is running)"}, 409)
                try:
                    if action == "sysfiles-stage":       # Add / Update the whole set for one system: a job (firmware zips are big)
                        system = b["system"]
                        return self._json(_job("sysfiles-stage", lambda cb: sysfiles.stage(did, c["dest"], system, progress=cb),
                                               with_progress=True, device=did, system=system))
                    if action == "sysfiles-unstage":
                        return self._json({"ok": True, **sysfiles.unstage(did, c["dest"], b["system"])})
                    return self._json({"ok": True, "others": sysfiles.remove_other(did, c["dest"], b["path"], b["name"])})
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
            elif action == "rename":
                conn = db.connect()
                conn.execute("UPDATE devices SET name=? WHERE id=?", (b["name"], did))
                conn.commit()
            elif action == "scan":
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                if _device_busy(did):
                    return self._json({"error": "the device is busy (a sync or scan is running)"}, 409)
                return self._json(_job("scan", lambda: profiles.scan_into(did, c["dest"]), device=did))
            elif action == "scan-sysfiles":            # read-only look at the emulator folders
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                if _device_busy(did):
                    return self._json({"error": "the device is busy (a sync or scan is running)"}, 409)
                return self._json(_job("scan-sysfiles", lambda cb: sysfiles.scan(did, c["dest"], progress=cb),
                                       with_progress=True, device=did))
            elif action == "sysfile":                  # {system, name, action: add|replace|remove}, one file, in-request
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                if _device_busy(did):
                    return self._json({"error": "the device is busy (a sync or scan is running)"}, 409)
                try:
                    row = sysfiles.apply(did, c["dest"], b["system"], b["name"], b["action"])
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
                return self._json({"ok": True, "system": row})
            elif action == "sync":
                # One action, one run: make the device's game folders match the selection.
                # Removes first, then updates and sends. bios / system files are never touched.
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                if _device_busy(did):
                    return self._json({"error": "the device is busy (a sync or scan is running)"}, 409)
                pl = planner.plan(did, c["info"].get("free"))
                ops = planner.ops_of(pl)
                if not ops:
                    return self._json({"error": "nothing to do: the device already matches the selection"}, 400)
                if pl["bytes"]["fits"] is False:
                    return self._json({"error": "the selection does not fit on the device"}, 400)
                dest = c["dest"]
                summary = planner.summary(pl)
                rid = transfer.create_run(did, ops, summary)

                def go(state):
                    state["phase"] = "sync"
                    transfer.start(rid, dest)
                    transfer.wait(rid)
                    res = transfer.ingest(rid, did)
                    try:
                        dest.write_marker(profiles.marker_for(did))
                        res["marker"] = "written"
                    except Exception as e:  # noqa: BLE001
                        res["marker"] = f"not written: {e}"
                    candidates(refresh=True)      # fresh free-space figure for the meter
                    _sync_log(rid, did, c, summary, res)
                    return res
                j = _job("sync", go, with_state=True, device=did, run=rid, phase="starting",
                         plan={k: summary[k] for k in ("send", "update", "remove")},
                         bytes_total=summary["send"]["bytes"] + summary["update"]["bytes"],
                         free_at_start=c["info"].get("free"), capacity=c["info"].get("capacity"))
                return self._json(j)
            elif action == "write-marker":
                c = _cand_for(did)
                if not c:
                    return self._json({"error": "device not connected"}, 400)
                c["dest"].write_marker(profiles.marker_for(did))
            else:
                return self._json({"error": "unknown action"}, 404)
            return self._json({"ok": True})
        if p == ["place"]:
            return self._json({"path": transfer.place_pulled(int(b["run"]), b["system"], b["name"])})
        if p[0] == "tag":
            if p[1] == "add":
                tags.set_tag(int(b["game_id"]), b["tag"], b.get("kind", "user"))
            elif p[1] == "remove":
                tags.remove(int(b["game_id"]), b["tag"])
            elif p[1] == "decide":
                tags.decide(int(b["game_id"]), b["tag"], bool(b["accept"]))
            return self._json({"ok": True})
        return self._json({"error": "unknown endpoint"}, 404)


def serve(port=0):
    tags.ensure()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True, name="romsync-http")
    t.start()
    return httpd, httpd.server_address[1]


if __name__ == "__main__":
    httpd, port = serve(8765)
    print(f"ROM-Sync at http://127.0.0.1:{port}/")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
