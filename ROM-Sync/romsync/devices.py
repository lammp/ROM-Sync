"""Destinations: a drive with a letter, a USB (MTP) device, or an Android device over ADB.

Both present the same operations to the rest of the app. Every write to a device
is explicit and named; nothing here deletes anything on the store.
"""
import hashlib
import json
import os
import shutil
import ctypes

from . import adb, db, ps

MARKER = "ROM-Sync.json"
SYSTEM_DRIVE = os.environ.get("SystemDrive", "C:").rstrip("\\").upper()
SKIP_NAMES = {"systeminfo.txt", "systems.txt", ".nomedia", "gamelist.xml", "desktop.ini", MARKER}
SKIP_DIRS = {"media", "images", "videos", "manuals", "downloaded_media", "covers",
             "shaders", "states", "saves", "sdmc", "cache", "textures",
             "gpu_drivers", "config", "sysdata", "log", "logs", "dump", "screenshots"}
# Files an emulator leaves next to games; never games themselves.
SKIP_EXTS = {".sav", ".srm", ".state", ".auto", ".mcr", ".mcd", ".dsv", ".cfg", ".ini", ".txt",
             ".nomedia", ".ldci", ".rtc", ".sa1", ".eep", ".fla", ".bak", ".log"}


def is_game_unit(name, kind):
    """Whether an entry seen on a device counts as a game unit (the same test the store scan uses)."""
    if name in SKIP_NAMES or name.startswith(".") or name.startswith("_"):
        return False
    if kind == "folder":
        return name.lower() not in SKIP_DIRS
    return os.path.splitext(name)[1].lower() not in SKIP_EXTS


def blake2(path, chunk=4 * 1024 * 1024):
    h = hashlib.blake2b(digest_size=16)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- probing

PROBE = r'''
$ErrorActionPreference = 'SilentlyContinue'
$vols = @()
foreach ($v in (Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -in 2,3 })) {
  $vols += [ordered]@{ letter=$v.DeviceID; label=$v.VolumeName; fs=$v.FileSystem;
                       serial=$v.VolumeSerialNumber; size=[int64]$v.Size; free=[int64]$v.FreeSpace;
                       removable=($v.DriveType -eq 2) }
}
$shell = New-Object -ComObject Shell.Application
$devs = @()
foreach ($i in $shell.NameSpace(17).Items()) {
  if ($i.IsFolder -and $i.Path -like '*::*usb*') {
    $stores = @()
    try {
      foreach ($s in $i.GetFolder.Items()) {
        $cap = $null; $free = $null
        try { $cap = [int64]$s.ExtendedProperty('System.Capacity') } catch {}
        try { $free = [int64]$s.ExtendedProperty('System.FreeSpace') } catch {}
        $stores += [ordered]@{ name=$s.Name; capacity=$cap; free=$free }
      }
    } catch {}
    $devs += [ordered]@{ name=$i.Name; path=$i.Path; storages=$stores }
  }
}
[ordered]@{ volumes=$vols; mtp=$devs } | ConvertTo-Json -Compress -Depth 5
'''


def probe():
    """Everything that could be a destination right now."""
    data = ps.run_json(PROBE, timeout=90) or {}
    vols = [v for v in data.get("volumes", []) if v["letter"].upper() != SYSTEM_DRIVE]
    return {"volumes": vols, "mtp": data.get("mtp", []), "adb": adb.devices()}


# ---------------------------------------------------------------- volume

class VolumeDest:
    kind = "volume"

    def __init__(self, letter, roms_root="ROMs"):
        self.letter = letter.rstrip("\\").upper()
        self.roms_root = roms_root.strip("\\/")
        self.root = os.path.join(self.letter + "\\", self.roms_root)

    def describe(self):
        return f"{self.letter}\\{self.roms_root}"

    def root_exists(self):
        return os.path.isdir(self.root)

    def create_root(self):
        os.makedirs(self.root, exist_ok=True)

    def info(self):
        total, used, free = shutil.disk_usage(self.letter + "\\")
        buf = ctypes.create_unicode_buffer(64)
        serial = ctypes.c_uint32(0)
        ctypes.windll.kernel32.GetVolumeInformationW(self.letter + "\\", None, 0, ctypes.byref(serial),
                                                     None, None, buf, 64)
        return {"capacity": total, "free": free, "filesystem": buf.value, "serial": f"{serial.value:08X}"}

    def read_marker(self):
        p = os.path.join(self.root, MARKER)
        if not os.path.isfile(p):
            return None
        try:
            return json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def write_marker(self, obj):
        os.makedirs(self.root, exist_ok=True)
        tmp = os.path.join(self.root, MARKER + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
        os.replace(tmp, os.path.join(self.root, MARKER))

    def scan(self, systems=None, progress=None):
        """Rows: (system, name, kind, size). kind is file or folder. system '' = top-level folder seen."""
        rows = []
        if not self.root_exists():
            return rows
        for entry in sorted(os.scandir(self.root), key=lambda e: e.name.lower()):
            if not entry.is_dir():
                continue
            rows.append(("", entry.name, "seen", 0))
            if systems is not None and entry.name not in systems:
                continue
            if progress:
                progress(entry.name)
            for item in os.scandir(entry.path):
                if item.name in SKIP_NAMES or item.name.startswith("."):
                    continue
                if item.is_dir():
                    if item.name.lower() in SKIP_DIRS or item.name.startswith("_"):
                        continue
                    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(item.path) for f in fs)
                    rows.append((entry.name, item.name, "folder", size))
                else:
                    rows.append((entry.name, item.name, "file", item.stat().st_size))
        return rows

    def path_of(self, system, name):
        return os.path.join(self.root, system, name)

    # ---- arbitrary locations (system files live outside the ROMs root too)
    def _abs(self, rel):
        return os.path.join(self.letter + "\\", *[x for x in rel.replace("\\", "/").split("/") if x])

    def list_paths(self, paths):
        """[(path, name, kind, size)] for each folder path (relative to the drive root).
        A missing folder yields one row (path, '', 'missing', 0); an empty one (path, '', 'folder', 0)."""
        rows = []
        for rel in paths:
            d = self._abs(rel)
            if not os.path.isdir(d):
                rows.append((rel, "", "missing", 0))
                continue
            rows.append((rel, "", "folder", 0))
            for e in os.scandir(d):
                rows.append((rel, e.name, "folder" if e.is_dir() else "file",
                             0 if e.is_dir() else e.stat().st_size))
        return rows

    def put_file(self, rel_folder, src, create=True):
        d = self._abs(rel_folder)
        if create:
            os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, os.path.basename(src))
        shutil.copy2(src, dst + ".rs-part")
        if os.path.exists(dst):
            os.remove(dst)
        os.replace(dst + ".rs-part", dst)
        return os.path.getsize(dst)

    def delete_file(self, rel_folder, name):
        p = os.path.join(self._abs(rel_folder), name)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)
        return not os.path.exists(p)

    def get_file(self, rel_folder, name, dst_dir):
        """Copy one device file to dst_dir; returns the local path or None."""
        p = os.path.join(self._abs(rel_folder), name)
        if not os.path.isfile(p):
            return None
        os.makedirs(dst_dir, exist_ok=True)
        out = os.path.join(dst_dir, name)
        shutil.copy2(p, out)
        return out

    def hash_of(self, system, name):
        p = self.path_of(system, name)
        if os.path.isdir(p):
            h = hashlib.blake2b(digest_size=16)
            for r, _, fs in os.walk(p):
                for f in sorted(fs):
                    h.update(f.encode("utf-8"))
                    h.update(bytes.fromhex(blake2(os.path.join(r, f))))
            return h.hexdigest()
        return blake2(p)


# ---------------------------------------------------------------- MTP

SCAN = ps.MTP_PROLOGUE + r'''
$out = $env:RS_OUT
$sw = New-Object System.IO.StreamWriter($out, $false, $utf8)
try {
  $st = Resolve-Storage $env:RS_DEVICE $env:RS_STORAGE
  $roms = Resolve-Path-OnDevice $st $env:RS_ROOT $false
  if (-not $roms) { $sw.WriteLine("ERROR`tno root"); $sw.Close(); exit 0 }
  $only = @{}
  if ($env:RS_SYSTEMS) { foreach ($n in ($env:RS_SYSTEMS -split "`n" | Where-Object { $_ })) { $only[$n.Trim()] = $true } }
  foreach ($sysItem in $roms.Items()) {
    if (-not $sysItem.IsFolder) { continue }
    $sysName = $sysItem.Name
    $sw.WriteLine("`t$sysName`tseen`t0")
    if ($only.Count -gt 0 -and -not $only.ContainsKey($sysName)) { continue }
    foreach ($g in $sysItem.GetFolder.Items()) {
      if ($g.IsFolder) {
        $total = [int64]0
        foreach ($f in $g.GetFolder.Items()) { if (-not $f.IsFolder) { $total += Size-Of $f } }
        $sw.WriteLine("$sysName`t$($g.Name)`tfolder`t$total")
      } else {
        $sw.WriteLine("$sysName`t$($g.Name)`tfile`t$(Size-Of $g)")
      }
    }
  }
} catch { $sw.WriteLine("ERROR`t$($_.Exception.Message)") }
$sw.Close()
'''

READ_FILE = ps.MTP_PROLOGUE + r'''
$st = Resolve-Storage $env:RS_DEVICE $env:RS_STORAGE
$folder = Resolve-Path-OnDevice $st $env:RS_ROOT $false
if (-not $folder) { exit 0 }
$item = Get-Child $folder $env:RS_NAME $false
if (-not $item) { exit 0 }
$shell = New-Object -ComObject Shell.Application
$tmp = $shell.NameSpace($env:RS_TMPDIR)
if (Test-Path -LiteralPath (Join-Path $env:RS_TMPDIR $env:RS_NAME)) { Remove-Item -LiteralPath (Join-Path $env:RS_TMPDIR $env:RS_NAME) -Force }
$tmp.CopyHere($item, 1556)
for ($i=0; $i -lt 100; $i++) { Start-Sleep -Milliseconds 200; if (Test-Path -LiteralPath (Join-Path $env:RS_TMPDIR $env:RS_NAME)) { break } }
Write-Output "ok"
'''

WRITE_FILE = ps.MTP_PROLOGUE + r'''
$st = Resolve-Storage $env:RS_DEVICE $env:RS_STORAGE
$folder = Resolve-Path-OnDevice $st $env:RS_ROOT ($env:RS_CREATE -eq '1')
if (-not $folder) { throw "root not found" }
$name = [IO.Path]::GetFileName($env:RS_SRC)
$existing = Get-Child $folder $name $false
if ($existing) { [void](Remove-DeviceItems @($existing)); Start-Sleep -Milliseconds 400 }
$folder.CopyHere($env:RS_SRC, 1556)
$size = (Get-Item -LiteralPath $env:RS_SRC).Length
$ok = $false
for ($i=0; $i -lt 300; $i++) {
  Start-Sleep -Milliseconds 300
  $it = Get-Child $folder $name $false
  if ($it -and (Size-Of $it) -ge $size) { $ok = $true; break }
}
if ($ok) { Write-Output "ok" } else { Write-Output "incomplete" }
'''


LIST_PATHS = ps.MTP_PROLOGUE + r'''
$out = $env:RS_OUT
$sw = New-Object System.IO.StreamWriter($out, $false, $utf8)
try {
  $st = Resolve-Storage $env:RS_DEVICE $env:RS_STORAGE
  foreach ($rel in ($env:RS_PATHS -split "`n" | Where-Object { $_ })) {
    $rel = $rel.Trim()
    $f = Resolve-Path-OnDevice $st $rel $false
    if (-not $f) { $sw.WriteLine("$rel`t`tmissing`t0"); continue }
    $sw.WriteLine("$rel`t`tfolder`t0")
    foreach ($i in $f.Items()) {
      if ($i.IsFolder) { $sw.WriteLine("$rel`t$($i.Name)`tfolder`t0") }
      else { $sw.WriteLine("$rel`t$($i.Name)`tfile`t$(Size-Of $i)") }
    }
  }
} catch { $sw.WriteLine("ERROR`t$($_.Exception.Message)`t`t0") }
$sw.Close()
'''

DELETE_FILE = ps.MTP_PROLOGUE + r'''
$st = Resolve-Storage $env:RS_DEVICE $env:RS_STORAGE
$folder = Resolve-Path-OnDevice $st $env:RS_ROOT $false
if (-not $folder) { Write-Output "ok"; exit 0 }
$it = Get-Child $folder $env:RS_NAME $false
if (-not $it) { Write-Output "ok"; exit 0 }
[void](Remove-DeviceItems @($it)); Start-Sleep -Milliseconds 500
if (Get-Child $folder $env:RS_NAME $false) { Write-Output "still-present" } else { Write-Output "ok" }
'''


class MtpDest:
    kind = "mtp"

    def __init__(self, device_name, storage_name, roms_root="ROMs"):
        self.device_name = device_name
        self.storage_name = storage_name
        self.roms_root = roms_root.strip("\\/")

    def describe(self):
        return f"{self.device_name} \\ {self.storage_name} \\ {self.roms_root}"

    def _env(self, **kw):
        e = {"RS_DEVICE": self.device_name, "RS_STORAGE": self.storage_name, "RS_ROOT": self.roms_root}
        e.update({k: str(v) for k, v in kw.items()})
        return e

    def _tmpdir(self):
        d = os.path.join(db.data_dir(), "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def info(self):
        p = probe()
        for d in p["mtp"]:
            if d["name"] == self.device_name:
                for s in d["storages"]:
                    if s["name"] == self.storage_name:
                        return {"capacity": s.get("capacity"), "free": s.get("free"),
                                "filesystem": "mtp", "serial": None, "path": d.get("path")}
        return {"capacity": None, "free": None, "filesystem": "mtp", "serial": None, "path": None}

    def root_exists(self):
        rows = self.scan(systems=[])
        return not (rows and rows[0][0] == "ERROR")

    def create_root(self):
        # Creating happens on first write; WRITE_FILE with RS_CREATE=1 makes the path.
        pass

    def read_marker(self):
        tmpdir = self._tmpdir()
        target = os.path.join(tmpdir, MARKER)
        if os.path.exists(target):
            os.remove(target)
        ps.run(READ_FILE, self._env(RS_NAME=MARKER, RS_TMPDIR=tmpdir), timeout=120)
        if not os.path.isfile(target):
            return None
        try:
            return json.load(open(target, encoding="utf-8"))
        finally:
            try:
                os.remove(target)
            except OSError:
                pass

    def write_marker(self, obj):
        src = os.path.join(self._tmpdir(), MARKER)
        with open(src, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
        r = ps.run(WRITE_FILE, self._env(RS_SRC=src, RS_CREATE=1), timeout=300)
        if "ok" not in (r.stdout or ""):
            raise RuntimeError("marker write did not complete: " + (r.stderr or r.stdout or "")[:400])

    def list_paths(self, paths):
        """Same shape as VolumeDest.list_paths; paths are relative to the storage root."""
        out = os.path.join(self._tmpdir(), "device-paths.tsv")
        if os.path.exists(out):
            os.remove(out)
        ps.run(LIST_PATHS, self._env(RS_OUT=out, RS_PATHS="\n".join(paths)), timeout=600)
        rows = []
        if not os.path.exists(out):
            raise RuntimeError("the device listing produced nothing")
        for line in open(out, encoding="utf-8-sig", errors="replace"):
            f = line.rstrip("\r\n").split("\t")
            if f and f[0] == "ERROR":
                raise RuntimeError(f[1] if len(f) > 1 else "device listing failed")
            if len(f) == 4:
                try:
                    rows.append((f[0], f[1], f[2], int(f[3] or 0)))
                except ValueError:
                    pass
        return rows

    def put_file(self, rel_folder, src, create=True):
        r = ps.run(WRITE_FILE, self._env(RS_ROOT=rel_folder, RS_SRC=src, RS_CREATE="1" if create else "0"), timeout=1800)
        if "ok" not in (r.stdout or ""):
            raise RuntimeError("copy did not complete: " + (r.stderr or r.stdout or "")[:400])
        return os.path.getsize(src)

    def delete_file(self, rel_folder, name):
        r = ps.run(DELETE_FILE, self._env(RS_ROOT=rel_folder, RS_NAME=name), timeout=300)
        return "ok" in (r.stdout or "")

    def get_file(self, rel_folder, name, dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
        out = os.path.join(dst_dir, name)
        if os.path.exists(out):
            os.remove(out)
        ps.run(READ_FILE, self._env(RS_ROOT=rel_folder, RS_NAME=name, RS_TMPDIR=dst_dir), timeout=600)
        return out if os.path.isfile(out) else None

    def scan(self, systems=None, progress=None):
        out = os.path.join(self._tmpdir(), "device-scan.tsv")
        if os.path.exists(out):
            os.remove(out)
        env = self._env(RS_OUT=out, RS_SYSTEMS="\n".join(systems) if systems is not None else "")
        if systems is not None and len(systems) == 0:
            env["RS_SYSTEMS"] = "\n__none__"
        ps.run(SCAN, env, timeout=3600)
        rows = []
        if not os.path.exists(out):
            return [("ERROR", "scan produced nothing", "", 0)]
        for line in open(out, encoding="utf-8-sig", errors="replace"):
            p = line.rstrip("\r\n").split("\t")
            if p and p[0] == "ERROR":
                return [("ERROR", p[1] if len(p) > 1 else "", "", 0)]
            if len(p) == 4:
                try:
                    rows.append((p[0], p[1], p[2], int(p[3])))
                except ValueError:
                    pass
        return rows


# ---------------------------------------------------------------- ADB

class AdbDest:
    """An Android device reached over the debug bridge.

    Same contract as VolumeDest and MtpDest, so planner, transfer and sysfiles do not
    care which one they are handed. The wins over MTP are that a whole-device scan is a
    single `find`, transfers run at USB speed with real byte progress, and files can be
    hashed on the device instead of being dragged back across the cable.
    """
    kind = "adb"

    def __init__(self, serial, roms_root="ROMs", storage="/sdcard", label=None):
        self.serial = serial
        self.roms_root = roms_root.strip("\\/")
        self.storage = "/" + storage.strip("/")
        self.label = label or serial
        self.root = f"{self.storage}/{self.roms_root}"

    def describe(self):
        return f"{self.label} (adb) \\ {self.root}"

    # ---- paths
    def _abs(self, rel):
        parts = [x for x in str(rel).replace("\\", "/").split("/") if x]
        return "/".join([self.storage] + parts)

    def path_of(self, system, name):
        return f"{self.root}/{system}/{name}" if system else f"{self.root}/{name}"

    # ---- identity and capacity
    def info(self):
        cap = free = None
        ok, out = adb.sh_ok(self.serial, "df -k " + adb.q(self.storage), timeout=30)
        if ok:
            for line in (out or "").splitlines():
                f = line.split()
                if len(f) >= 4 and f[1].isdigit():
                    cap, free = int(f[1]) * 1024, int(f[3]) * 1024
        return {"capacity": cap, "free": free, "filesystem": "adb", "serial": self.serial}

    def root_exists(self):
        ok, out = adb.sh_ok(self.serial, f"[ -d {adb.q(self.root)} ] && echo yes", timeout=30)
        return ok and "yes" in out

    def create_root(self):
        adb.sh_ok(self.serial, "mkdir -p " + adb.q(self.root), timeout=60)

    # ---- marker
    def _tmpdir(self):
        d = os.path.join(db.data_dir(), "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def read_marker(self):
        target = os.path.join(self._tmpdir(), MARKER)
        if adb.pull(self.serial, f"{self.root}/{MARKER}", target) is None:
            return None
        try:
            return json.load(open(target, encoding="utf-8"))
        except (OSError, ValueError):
            return None
        finally:
            try:
                os.remove(target)
            except OSError:
                pass

    def write_marker(self, obj):
        self.create_root()
        src = os.path.join(self._tmpdir(), MARKER)
        with open(src, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
        adb.push(self.serial, src, f"{self.root}/{MARKER}")

    # ---- listing
    def scan(self, systems=None, progress=None):
        """Rows: (system, name, kind, size), matching VolumeDest exactly.

        One `find` covers the whole tree, so this is a single round trip rather than a
        walk. Folder rows carry the summed size of everything beneath them.
        """
        if not self.root_exists():
            return []
        if systems is not None and len(systems) == 0:
            ok, out = adb.sh_ok(self.serial, f"find {adb.q(self.root)} -mindepth 1 -maxdepth 1 -type d -printf '%f\\n'", timeout=120)
            if not ok:
                return [("ERROR", out, "", 0)]
            return [("", n.strip(), "seen", 0) for n in (out or "").splitlines() if n.strip()]

        if progress:
            progress("reading the device")
        r = adb.q(self.root)
        cmd = ("echo '@@@D'; find " + r + " -mindepth 1 -type d -printf '%P\\n'; "
               "echo '@@@F'; find " + r + " -mindepth 1 -type f -printf '%s" + "\t" + "%P\\n'")
        ok, out = adb.sh_ok(self.serial, cmd, timeout=900)
        if not ok:
            return [("ERROR", out, "", 0)]

        tops, files, dirs, mode = [], {}, set(), None
        for line in (out or "").splitlines():
            line = line.rstrip("\r")
            if line.startswith("@@@"):
                mode = line[3:4]
                continue
            if mode == "D":
                parts = [x for x in line.split("/") if x]
                if len(parts) == 1:
                    tops.append(parts[0])
                elif len(parts) == 2:
                    dirs.add((parts[0], parts[1]))
                continue
            if mode != "F" or "\t" not in line:
                continue
            size, rel = line.split("\t", 1)
            parts = [x for x in rel.split("/") if x]
            if len(parts) < 2:
                continue
            system, item = parts[0], parts[1]
            try:
                n = int(size or 0)
            except ValueError:
                continue
            files[(system, item)] = files.get((system, item), 0) + n

        rows = []
        for t in sorted(tops, key=str.lower):
            rows.append(("", t, "seen", 0))
        wanted = None if systems is None else set(systems)
        seen_items = sorted(set(list(files.keys()) + list(dirs)), key=lambda x: (x[0].lower(), x[1].lower()))
        for system, item in seen_items:
            if wanted is not None and system not in wanted:
                continue
            if item in SKIP_NAMES or item.startswith("."):
                continue
            if (system, item) in dirs:
                if item.lower() in SKIP_DIRS or item.startswith("_"):
                    continue
                rows.append((system, item, "folder", files.get((system, item), 0)))
            else:
                rows.append((system, item, "file", files[(system, item)]))
        return rows

    def list_paths(self, paths):
        """[(path, name, kind, size)] per folder, relative to the storage root.
        Missing folders yield (path, '', 'missing', 0); empty ones (path, '', 'folder', 0)."""
        if not paths:
            return []
        chunks = []
        for rel in paths:
            a = adb.q(self._abs(rel))
            chunks.append("echo '@@@" + str(rel) + "'; if [ -d " + a + " ]; then echo '@@@DIR'; "
                          "find " + a + " -mindepth 1 -maxdepth 1 -type d -printf '@@@d%f\\n' 2>/dev/null; "
                          "find " + a + " -mindepth 1 -maxdepth 1 -type f -printf '%s" + "\t" + "%f\\n' 2>/dev/null; "
                          "else echo '@@@MISSING'; fi")
        ok, out = adb.sh_ok(self.serial, "; ".join(chunks), timeout=900)
        if not ok:
            raise RuntimeError("the device listing failed: " + str(out)[:300])
        rows, cur = [], None
        for line in (out or "").splitlines():
            line = line.rstrip("\r")
            if line.startswith("@@@MISSING"):
                rows.append((cur, "", "missing", 0))
            elif line.startswith("@@@DIR"):
                rows.append((cur, "", "folder", 0))
            elif line.startswith("@@@d"):
                rows.append((cur, line[4:], "folder", 0))
            elif line.startswith("@@@"):
                cur = line[3:]
            elif cur is not None and "\t" in line:
                size, name = line.split("\t", 1)
                try:
                    rows.append((cur, name, "file", int(size or 0)))
                except ValueError:
                    pass
        return rows

    # ---- moving bytes
    def put_file(self, rel_folder, src, create=True):
        d = self._abs(rel_folder)
        if create:
            adb.sh_ok(self.serial, "mkdir -p " + adb.q(d), timeout=60)
        return adb.push(self.serial, src, f"{d}/{os.path.basename(src)}")

    def delete_file(self, rel_folder, name):
        p = f"{self._abs(rel_folder)}/{name}"
        adb.sh_ok(self.serial, "rm -rf " + adb.q(p), timeout=300)
        ok, out = adb.sh_ok(self.serial, f"[ -e {adb.q(p)} ] && echo present", timeout=60)
        return not (ok and "present" in out)

    def get_file(self, rel_folder, name, dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
        return adb.pull(self.serial, f"{self._abs(rel_folder)}/{name}", os.path.join(dst_dir, name))

    # ---- verification, computed on the device
    def md5_of(self, system, name):
        return adb.md5(self.serial, self.path_of(system, name))

    def md5_many(self, remote_paths):
        """{path: md5} for many files in one call. This is what makes a library-wide
        integrity check cheap: nothing crosses the cable but the hashes."""
        if not remote_paths:
            return {}
        cmd = "md5sum " + " ".join(adb.q(p) for p in remote_paths)
        ok, out = adb.sh_ok(self.serial, cmd, timeout=3600)
        if not ok:
            return {}
        got = {}
        for line in (out or "").splitlines():
            line = line.strip()
            if "  " in line:
                h, p = line.split("  ", 1)
                got[p.strip()] = h.strip()
        return got
