"""Command line entry points while the UI is being built.

    python -m romsync scan                      index the store
    python -m romsync import-old                carry cover art and descriptions over from ROM Curator 1
    python -m romsync systems                   per-system counts
    python -m romsync where                     paths the app uses
    python -m romsync devices                   what is plugged in, and which profile each one is
    python -m romsync profile-new <n> "<name>"  create a profile for candidate n (writes ROM-Sync.json)
    python -m romsync profile-new <n> "<name>" --no-marker     same, without writing to the device
    python -m romsync profiles                  list profiles
    python -m romsync scan-device <n>           read-only inventory of candidate n into its profile
    python -m romsync device <id>               per-system summary of a profile
    python -m romsync xfer <profile|test> <send|update|remove|pull> <system> "<name>" ...
                                                run approved ops against a device (test = scratch folder on the store drive)
    python -m romsync run-status <run>          status and results of a run
    python -m romsync pulled <run>              what a run pulled, and whether the store already has it
    python -m romsync place <run> <system> "<name>"   move a pulled item into the store (never overwrites)
    python -m romsync select <profile> <system> all|none          whole-system selection
    python -m romsync select-game <profile> <system> "<name>" in|out
    python -m romsync decide <profile> <system> "<name>" leave|pull|remove   for device items the store lacks
    python -m romsync plan <profile> [--full]   what a sync would do (read-only)
    python -m romsync sync <profile> [--go]     run it against the plugged-in device
    python -m romsync sysfiles [<profile>]      BIOS/firmware/keys status
    python -m romsync enrich [--all]            IGDB screenshots and linking tags for matched games
    python -m romsync scrape [--all] [sys ...]   match pending games against IGDB (cover, summary, rating), then enrich
    python -m romsync reason [--dry]             propose franchise tags for games IGDB left without one (review in the UI)
"""
import json
import sys

from . import db, scanner, legacy, profiles


def fmt_bytes(n):
    if n is None:
        return "?"
    if n < 0:
        return "-" + fmt_bytes(-n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def cmd_scan(_):
    res = scanner.scan(progress=lambda s: print(s, end="\r", flush=True))
    print(" " * 60, end="\r")
    print(f"systems {res['systems']}  games {res['games']}  added {res['added']}  "
          f"updated {res['updated']}  removed {res['removed']}")


def cmd_systems(_):
    rows = db.system_rows()
    print(f"{'system':<18}{'games':>7}{'folders':>9}{'matched':>9}  size")
    tot = 0
    for r in rows:
        tot += r["bytes"]
        print(f"{r['key']:<18}{r['games']:>7}{r['folders'] or 0:>9}{r['matched'] or 0:>9}  {fmt_bytes(r['bytes'])}")
    print(f"{'total':<18}{sum(r['games'] for r in rows):>7}{'':>9}{'':>9}  {fmt_bytes(tot)}")


def cmd_import_old(_):
    print(legacy.import_metadata())


def cmd_where(_):
    print("store   ", db.store_root())
    print("data    ", db.data_dir())
    print("database", db.db_path())


def _candidates():
    return profiles.recognise()


def cmd_devices(_):
    for i, c in enumerate(_candidates()):
        info = c["info"]
        who = (f"profile: {c['profile']['name']} ({c['profile']['id'][:8]})" if c["profile"]
               else ("marker without profile: adopt" if c["marker"] else "new"))
        print(f"[{i}] {c['kind']:<6} {c['label']:<40} free {fmt_bytes(info.get('free'))} / "
              f"{fmt_bytes(info.get('capacity'))}  fs {info.get('filesystem')}  {who}")


def cmd_profile_new(args):
    n, name = int(args[0]), args[1]
    write = "--no-marker" not in args
    c = _candidates()[n]
    did = profiles.create(c, name, write_marker=write)
    print(f"created {did} for {c['label']}  marker {'written' if write else 'not written'}")


def cmd_profiles(_):
    for p in profiles.list_profiles():
        print(f"{p['id'][:8]}  {p['kind']:<6} {p['name']:<24} {p['roms_root']:<10} last seen {p['last_seen']}")


def cmd_scan_device(args):
    n = int(args[0])
    c = _candidates()[n]
    if not c["profile"]:
        print("no profile for this candidate; create one first")
        return
    res = profiles.scan_into(c["profile"]["id"], c["dest"], progress=lambda s: print(s, end="\r", flush=True))
    print(" " * 60, end="\r")
    print(json.dumps(res))
    for r in profiles.summary(c["profile"]["id"]):
        print(f"  {r['system']:<16}{r['n']:>6}  {fmt_bytes(r['bytes'])}")


def cmd_device(args):
    did = args[0]
    for p in profiles.list_profiles():
        if p["id"].startswith(did):
            print(p["name"], p["kind"], p["roms_root"])
            for r in profiles.summary(p["id"]):
                print(f"  {r['system']:<16}{r['n']:>6}  {fmt_bytes(r['bytes'])}")


TEST_ROOT = r"Games\ROM-Sync\data\test-dest\ROMs"   # on the store's drive, used by `xfer test ...`


def _resolve_dest(token):
    """'test' -> a scratch VolumeDest on the store drive; else a plugged-in candidate by profile id prefix."""
    from . import devices as dv
    if token == "test":
        letter = db.store_root()[:2]
        dest = dv.VolumeDest(letter, TEST_ROOT)
        dest.create_root()
        conn = db.connect()
        row = conn.execute("SELECT id FROM devices WHERE name='_test' AND kind='volume'").fetchone()
        if row:
            return row["id"], dest
        did = db.new_id()
        conn.execute("INSERT INTO devices(id,name,kind,roms_root,first_seen,last_seen) VALUES(?,?,?,?,?,?)",
                     (did, "_test", "volume", TEST_ROOT, db.now(), db.now()))
        conn.commit()
        return did, dest
    for c in _candidates():
        if c["profile"] and c["profile"]["id"].startswith(token):
            return c["profile"]["id"], c["dest"]
    raise SystemExit(f"no plugged-in device with a profile starting {token}")


def cmd_xfer(args):
    """xfer <profile|test> <send|update|remove|pull> <system> "<name>" [<system> "<name>" ...]"""
    from . import transfer
    did, dest = _resolve_dest(args[0])
    op = args[1]
    pairs = list(zip(args[2::2], args[3::2]))
    conn = db.connect()
    ops = []
    for system, name in pairs:
        g = conn.execute("SELECT * FROM games WHERE system=? AND name=?", (system, name)).fetchone()
        if g:
            ops.append(transfer.op_from_game(op, dict(g)))
        elif op in ("remove", "pull"):
            ops.append(transfer.make_op(op, system, name))
        else:
            raise SystemExit(f"not in the store: {system}\\{name}")
    run_id = transfer.create_run(did, ops)
    print(f"run {run_id}: {len(ops)} op(s) to {dest.describe()}")
    transfer.start(run_id, dest)
    st = transfer.wait(run_id, progress=lambda s: print(f"  {s['phase']:<8}{s['done']}/{s['total']}  {s['current'][:50]:<50}",
                                                        end="\r", flush=True))
    print(" " * 78, end="\r")
    print(json.dumps(transfer.ingest(run_id, did)))
    for r in transfer.read_results(run_id):
        print(f"  {r['op']:<7}{r['result']:<7}{r['system']}\\{r['name']}  {fmt_bytes(r['size'])}  {r['detail']}")


def cmd_run_status(args):
    from . import transfer
    print(json.dumps(transfer.read_status(int(args[0]))))
    for r in transfer.read_results(int(args[0])):
        print(f"  {r['op']:<7}{r['result']:<7}{r['system']}\\{r['name']}  {r['detail']}")


def cmd_pulled(args):
    from . import transfer
    for it in transfer.pulled_items(int(args[0])):
        print(f"  {it['system']}\\{it['name']}  {'ALREADY IN STORE' if it['in_store'] else 'can place'}")


def cmd_place(args):
    from . import transfer
    print(transfer.place_pulled(int(args[0]), args[1], args[2]))


def _profile_id(token):
    for p in profiles.list_profiles():
        if p["id"].startswith(token) or p["name"] == token:
            return p["id"]
    raise SystemExit(f"no profile {token}")


def cmd_select(args):
    """select <profile> <system> all|none"""
    from . import planner
    planner.set_system(_profile_id(args[0]), args[1], args[2])
    print("ok")


def cmd_select_game(args):
    """select-game <profile> <system> "<name>" in|out"""
    from . import planner
    g = db.connect().execute("SELECT id FROM games WHERE system=? AND name=?", (args[1], args[2])).fetchone()
    if not g:
        raise SystemExit("not in the store")
    planner.set_game(_profile_id(args[0]), g["id"], args[3] == "in")
    print("ok")


def cmd_decide(args):
    """decide <profile> <system> "<name>" leave|pull|remove   (for items on the device the store lacks)"""
    from . import planner
    planner.decide(_profile_id(args[0]), f"{args[1]}\\{args[2]}", args[3])
    print("ok")


def _print_plan(p, full=False):
    b = p["bytes"]
    print(f"managed systems: {', '.join(p['managed_systems']) or '(none selected)'}")
    for k in ("send", "update", "remove", "pull"):
        n = len(p[k])
        print(f"{k:<8}{n:>6}  {fmt_bytes(sum(o['size'] for o in p[k]))}")
        if full or n <= 12:
            for o in p[k]:
                print(f"          {o['system']}\\{o['name']}  {fmt_bytes(o['size'])}")
    print(f"unchanged {p['unchanged']}")
    if p["missing_at_source"]:
        print(f"on device, not in store: {len(p['missing_at_source'])} (listed, not touched unless decided)")
        for m in p["missing_at_source"][: (None if full else 12)]:
            print(f"          {m['rel_path']}  {fmt_bytes(m['size'])}  decision={m['decision']}")
    if p["unmanaged"]:
        print("unmanaged on device: " + ", ".join(f"{s} ({n})" for s, n in sorted(p["unmanaged"].items())))
    print(f"net change {fmt_bytes(b['net'])}  (add {fmt_bytes(b['add'])}, drop {fmt_bytes(b['drop'])})"
          + (f"  free {fmt_bytes(b['free'])}  fits={b['fits']}" if b["free"] is not None else ""))


def cmd_plan(args):
    """plan <profile> [--full]   what a sync would do, from the last inventory. Read-only."""
    from . import planner
    did = _profile_id(args[0])
    free = None
    for c in _candidates():
        if c["profile"] and c["profile"]["id"] == did:
            free = c["info"].get("free")
    _print_plan(planner.plan(did, free), full="--full" in args)


def cmd_sync(args):
    """sync <profile> --go   run the plan against the plugged-in device, then refresh ROM-Sync.json"""
    from . import planner, transfer
    did = _profile_id(args[0])
    cand = next((c for c in _candidates() if c["profile"] and c["profile"]["id"] == did), None)
    if not cand:
        raise SystemExit("that device is not plugged in")
    p = planner.plan(did, cand["info"].get("free"))
    _print_plan(p)
    ops = planner.ops_of(p)
    if "--go" not in args:
        print("\n(dry run; add --go to execute)")
        return
    if not ops:
        print("nothing to do")
        return
    if p["bytes"]["fits"] is False:
        raise SystemExit("not enough free space on the device")
    run_id = transfer.create_run(did, ops, planner.summary(p))
    print(f"run {run_id}: {len(ops)} op(s)")
    transfer.start(run_id, cand["dest"])
    transfer.wait(run_id, progress=lambda s: print(f"  {s['phase']:<8}{s['done']}/{s['total']}  {s['current'][:50]:<50}",
                                                   end="\r", flush=True))
    print(" " * 78, end="\r")
    print(json.dumps(transfer.ingest(run_id, did)))
    cand["dest"].write_marker(profiles.marker_for(did))
    for r in transfer.read_results(run_id):
        if r["result"] != "ok":
            print(f"  FAILED {r['op']} {r['system']}\\{r['name']}: {r['detail']}")


def cmd_sysfiles(args):
    """sysfiles [<profile>]   per-system readiness: emulator, what it needs, store and device state"""
    from . import sysfiles
    did = _profile_id(args[0]) if args else None
    if not did:
        for r in sysfiles.store_status():
            print(f"{r['system']:<8}{r['name']:<16}{'required' if r['required'] else 'optional':<9}"
                  f"{fmt_bytes(r['store_size']) if r['store_present'] else 'MISSING':<12}{r['note']}")
        return
    rd = sysfiles.readiness(did)
    print(f"scanned: {rd['scanned_at'] or 'never (run scan-sysfiles)'}")
    for s in rd["systems"]:
        print(f"{s['system']:<14}{s['on_device']['n']:>5} on device  {s['state']:<12}{s['emulator']}"
              + (f"  missing: {', '.join(s['missing'])}" if s['missing'] else ""))
        for r in s["requirements"]:
            print(f"    {r['name']:<16}{'required' if r['required'] else 'optional':<9}"
                  f"store={'yes' if r['store_present'] else 'NO':<4} device={r['device_state']:<13}{r['device_path']}")


def cmd_enrich(args):
    """enrich [--all]   second IGDB pass: screenshots and linking tags for matched games"""
    from . import enrich
    print(enrich.run(progress=lambda m: print(m, flush=True), only_missing="--all" not in args))


def cmd_scrape(args):
    """scrape [--all] [system ...]   IGDB match for pending games (or all), then the enrich pass"""
    from . import scrape, enrich
    systems = [a for a in args if not a.startswith("--")] or None
    print(scrape.run(systems=systems, only_pending="--all" not in args, progress=lambda m: print(m, flush=True)))
    print(enrich.run(progress=lambda m: print(m, flush=True), only_missing=True))


def cmd_reason(args):
    """reason [--dry]   propose franchise tags (state=proposed) for games without one"""
    from . import reason
    r = reason.propose(dry="--dry" in args)
    print("\n".join(r["sample"]))
    print({k: v for k, v in r.items() if k != "sample"})


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "systems"
    rest = argv[2:]
    {"scan": cmd_scan, "systems": cmd_systems, "import-old": cmd_import_old, "where": cmd_where,
     "devices": cmd_devices, "profile-new": cmd_profile_new, "profiles": cmd_profiles,
     "scan-device": cmd_scan_device, "device": cmd_device, "xfer": cmd_xfer, "run-status": cmd_run_status,
     "pulled": cmd_pulled, "place": cmd_place, "select": cmd_select, "select-game": cmd_select_game,
     "decide": cmd_decide, "plan": cmd_plan, "sync": cmd_sync, "sysfiles": cmd_sysfiles, "enrich": cmd_enrich, "scrape": cmd_scrape, "reason": cmd_reason}.get(cmd, lambda a: print(__doc__))(rest)


if __name__ == "__main__":
    main(sys.argv)
