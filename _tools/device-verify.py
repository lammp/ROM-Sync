"""Device verify: prove that files on a device are byte-identical to the store, from the device
itself (pull a copy back over USB and hash it). A completed send is not proof of an intact file
(run 10, 2026-09-16: Xenoblade Chronicles 3D reported sent, same size, different bytes).

  python _tools\device-verify.py [--device "AYN Thor"] (--run N [--failed] | --name "<file>"... | --system <sys>)
                                 [--keep] [--dry]

  --run N        every file run N tried to send (add --failed for only the ones it flagged)
  --name         one or more exact file names (system is looked up in the store)
  --system       every game of that system that is on the device
  --keep         report only: never delete a damaged copy
  --dry          list what would be checked and stop

For each file: pull -> size check -> MD5 against the store copy -> MATCH / DIFFERENT / SIZE / PULL-FAILED.
A DIFFERENT or SIZE result deletes the device copy and drops its inventory row, so the next Sync
re-sends it (unless --keep). Every result is appended to ROM-Sync\data\records\device-verify.tsv.
Pulls retry three times with a pause, because the Thor drops off USB now and then under sustained
reads; a "device is unreachable" dialog on the PC must be dismissed by hand (it holds the copy).
Never run this while a sync is running on the same device (two USB workers wedge the session).
"""
import argparse, hashlib, os, sys, time
sys.path.insert(0, r"D:\Games\ROM-Sync")
from romsync import devices, db, transfer, profiles

ap = argparse.ArgumentParser()
ap.add_argument("--device", default="AYN Thor")
ap.add_argument("--run", type=int); ap.add_argument("--failed", action="store_true")
ap.add_argument("--name", action="append", default=[]); ap.add_argument("--system")
ap.add_argument("--keep", action="store_true"); ap.add_argument("--dry", action="store_true")
a = ap.parse_args()

conn = db.connect()
prof = next((p for p in profiles.list_profiles() if p["name"] == a.device or p["id"] == a.device), None)
if not prof:
    sys.exit(f"no device profile named {a.device}")
D = prof["id"]
present = {r["rel_path"]: r["size"] for r in conn.execute(
    "SELECT rel_path, size FROM device_files WHERE device_id=? AND missing_since IS NULL", (D,))}

todo = []
if a.run:
    for r in transfer.read_results(a.run):
        if r["op"] in ("send", "update") and (not a.failed or r["result"] != "ok"):
            todo.append((r["system"], r["name"]))
for n in a.name:
    g = conn.execute("SELECT system FROM games WHERE name=?", (n,)).fetchone()
    if not g:
        print(f"not in the store: {n}"); continue
    todo.append((g["system"], n))
if a.system:
    todo += [tuple(rel.split("\\", 1)) for rel in present if rel.startswith(a.system + "\\")]
todo = [(s, n) for s, n in dict.fromkeys(todo) if f"{s}\\{n}" in present]
print(f"{len(todo)} file(s) to verify on {prof['name']}")
if a.dry:
    for s, n in todo: print(f"  {s}\\{n}")
    sys.exit()

if prof["kind"] == "mtp":
    dest = devices.MtpDest(prof["mtp_device_id"], prof["mtp_storage_id"], prof["roms_root"])
else:                                   # a drive: use whatever letter it has right now
    cand = next((c for c in profiles.recognise() if c["profile"] and c["profile"]["id"] == D), None)
    if not cand:
        sys.exit(f"{prof['name']} is not plugged in")
    dest = cand["dest"]
out = os.path.join(db.data_dir(), "tmp", "pullcheck"); os.makedirs(out, exist_ok=True)
for f in os.listdir(out): os.remove(os.path.join(out, f))
store = db.store_root()
rec = os.path.join(db.data_dir(), "records", "device-verify.tsv")
new = not os.path.exists(rec)

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""): h.update(b)
    return h.hexdigest()

bad = []
with open(rec, "a", encoding="utf-8") as tsv:
    if new: tsv.write("when\tdevice\tsystem\tname\tstore_size\tdevice_size\tresult\taction\n")
    for s, n in todo:
        t0 = time.time()
        g = conn.execute("SELECT rel_path, size, kind FROM games WHERE system=? AND name=?", (s, n)).fetchone()
        if not g or g["kind"] != "file":
            print(f"skip     {s}\\{n}: not a single store file"); continue
        local = None
        for attempt in range(3):
            local = dest.get_file(f"{prof['roms_root']}/{s}", n, out)
            if local: break
            time.sleep(15)
        if not local:
            res, tsize = "PULL-FAILED", ""
        else:
            tsize = os.path.getsize(local)
            res = f"SIZE {tsize}!={g['size']}" if tsize != g["size"] else ("MATCH" if md5(local) == md5(os.path.join(store, g["rel_path"])) else "DIFFERENT")
            os.remove(local)
        action = ""
        if res != "MATCH":
            bad.append(n)
            if local is not None and not a.keep:
                ok = dest.delete_file(f"{prof['roms_root']}/{s}", n)
                conn.execute("DELETE FROM device_files WHERE device_id=? AND rel_path=?", (D, f"{s}\\{n}")); conn.commit()
                action = "removed from device; next Sync re-sends" if ok else "delete FAILED"
        print(f"{res:<10} {s}\\{n}  ({round(time.time()-t0)} s) {action}", flush=True)
        tsv.write(f"{db.now()}\t{prof['name']}\t{s}\t{n}\t{g['size']}\t{tsize}\t{res}\t{action}\n"); tsv.flush()
print(f"DONE: {len(todo)-len(bad)} match, {len(bad)} not ok" + (": " + "; ".join(bad) if bad else ""))
