import sqlite3, subprocess, sys, os, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ADB = r"D:\Games\_tools\platform-tools\adb.exe"
ser = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout.split()
ser = [ser[i] for i in range(len(ser)) if ser[i] == "device" and i > 0][:1]
ser = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout.strip().splitlines()[1:]
serial = ser[0].split()[0]
root = "/sdcard/ROMs"
cmd = "find '%s' -mindepth 1 -maxdepth 2 -printf '%%s\t%%P\\n'" % root
out = subprocess.run([ADB, "-s", serial, "shell", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
dev = collections.defaultdict(dict)
for line in out.splitlines():
    if "\t" not in line: continue
    sz, rel = line.split("\t", 1)
    rel = rel.strip("\r")
    if "/" not in rel: continue
    sysn, nm = rel.split("/", 1)
    try: dev[sysn][nm] = int(sz)
    except ValueError: dev[sysn][nm] = 0

c = sqlite3.connect("file:D:/Games/ROM-Sync/data/romsync.db?mode=ro", uri=True)
c.row_factory = sqlite3.Row
d = c.execute("select id, name from devices").fetchone()
sel = [r for r in c.execute(
    "select g.system, g.rel_path, g.name, g.kind, g.size from selection_overrides o join games g on g.id=o.game_id "
    "where o.device_id=? and o.include=1", (d["id"],))]
print("device: %s (%s)   selected: %d" % (d["name"], serial, len(sel)))
missing, sizebad = [], []
for r in sel:
    base = os.path.basename(r["rel_path"].replace("\\", "/"))
    have = dev.get(r["system"], {})
    if base not in have:
        missing.append((r["system"], base))
    elif r["kind"] == "file" and r["size"] and have[base] and have[base] != r["size"]:
        sizebad.append((r["system"], base, r["size"], have[base]))
print("on device, size matches store : %d" % (len(sel) - len(missing) - len(sizebad)))
print("MISSING from device           : %d" % len(missing))
for s, b in sorted(missing)[:40]: print("   %-6s %s" % (s, b))
print("size mismatch                 : %d" % len(sizebad))
for s, b, a, bb in sizebad[:20]: print("   %-6s %-56s store %d dev %d" % (s, b[:56], a, bb))
sysset = {r["system"] for r in sel}
print("")
print("%-8s %6s %6s" % ("system", "sel", "ondev"))
for s in sorted(sysset):
    print("%-8s %6d %6d" % (s, sum(1 for r in sel if r["system"] == s), len(dev.get(s, {}))))
extra_sys = sorted(set(dev) - sysset)
if extra_sys:
    print("")
    print("folders on device with no selection: " + ", ".join("%s(%d)" % (s, len(dev[s])) for s in extra_sys))
