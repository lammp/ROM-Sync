"""Moving games between the store and a destination.

A run is a list of ops the user has already approved:

    send    store -> device, nothing there yet
    update  store -> device, replacing what is there
    remove  delete from the device
    pull    device -> the app's pull folder (never straight into the store)

Every op names one unit: a file, or a whole game folder. The worker for a USB
(MTP) device is one PowerShell process per run; the worker for a drive with a
letter is plain Python in a thread. Both write the same three files under
data\runs\<run_id>\ so the UI reads one shape:

    status.json   state, phase, done/total, current item, counts
    results.tsv   system  name  op  result  size  detail     (one line per op)
    plan.tsv      what was asked

Nothing here writes to the store. Pulled items land in data\pull\<run_id>\ and
are placed into the store only by place_pulled(), which refuses to overwrite.
"""
import json
import os
import shutil
import threading
import time

from . import adb, db, devices, ps

OPS = ("send", "update", "remove", "pull")


# ---------------------------------------------------------------- run folders

def run_dir(run_id):
    d = os.path.join(db.data_dir(), "runs", str(run_id))
    os.makedirs(d, exist_ok=True)
    return d


def pull_dir(run_id):
    d = os.path.join(db.data_dir(), "pull", str(run_id))
    os.makedirs(d, exist_ok=True)
    return d


def _paths(run_id):
    d = run_dir(run_id)
    return {"plan": os.path.join(d, "plan.tsv"), "status": os.path.join(d, "status.json"),
            "results": os.path.join(d, "results.tsv"), "log": os.path.join(d, "worker.log")}


# ---------------------------------------------------------------- ops

def make_op(op, system, name, kind="file", size=0, src="", mtime=None, hash_=None):
    if op not in OPS:
        raise ValueError(op)
    return {"op": op, "system": system, "name": name, "kind": kind, "size": int(size or 0),
            "src": src or "", "mtime": mtime, "hash": hash_}


def op_from_game(op, game_row):
    """An op for a store game row (dict from the games table)."""
    src = os.path.join(db.store_root(), game_row["rel_path"])
    return make_op(op, game_row["system"], game_row["name"], game_row["kind"], game_row["size"], src,
                   game_row.get("mtime"), game_row.get("hash"))


def create_run(device_id, ops, summary=None):
    """Record the approved plan and its ops. Returns run_id."""
    conn = db.connect()
    cur = conn.execute("INSERT INTO sync_runs(device_id,started,state,plan) VALUES(?,?,?,?)",
                       (device_id, db.now(), "planned", json.dumps(summary or _summarise(ops))))
    run_id = cur.lastrowid
    for i, o in enumerate(ops):
        conn.execute("INSERT INTO sync_ops(run_id,seq,op,rel_path,size) VALUES(?,?,?,?,?)",
                     (run_id, i, o["op"], f"{o['system']}\\{o['name']}", o["size"]))
    conn.commit()
    p = _paths(run_id)
    with open(p["plan"], "w", encoding="utf-8", newline="\n") as f:
        f.write("# op\tsystem\tname\tkind\tsize\tsrc\n")
        for o in ops:
            f.write("\t".join([o["op"], o["system"], o["name"], o["kind"], str(o["size"]), o["src"]]) + "\n")
    with open(p["plan"] + ".json", "w", encoding="utf-8") as f:
        json.dump(ops, f)
    return run_id


def _summarise(ops):
    s = {k: {"n": 0, "bytes": 0} for k in OPS}
    for o in ops:
        s[o["op"]]["n"] += 1
        s[o["op"]]["bytes"] += o["size"]
    return s


def load_ops(run_id):
    return json.load(open(_paths(run_id)["plan"] + ".json", encoding="utf-8"))


# ---------------------------------------------------------------- status

def _write_status(run_id, **kw):
    p = _paths(run_id)["status"]
    cur = read_status(run_id)
    cur.update(kw)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cur, f)
    # A reader may have the file open for a moment; Windows refuses the replace until it closes.
    for attempt in range(40):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            time.sleep(0.05)
    os.replace(tmp, p)


_IDLE = {"state": "idle", "phase": "", "done": 0, "total": 0, "current": "",
         "sent": 0, "removed": 0, "pulled": 0, "failed": 0, "message": ""}


def read_status(run_id):
    p = _paths(run_id)["status"]
    for attempt in range(10):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return dict(_IDLE)
        except (OSError, ValueError):
            time.sleep(0.05)   # mid-replace or half-written; try again
    return dict(_IDLE)


def read_results(run_id):
    p = _paths(run_id)["results"]
    out = []
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8-sig", errors="replace"):
        f = line.rstrip("\r\n").split("\t")
        if len(f) >= 5:
            out.append({"system": f[0], "name": f[1], "op": f[2], "result": f[3],
                        "size": int(f[4] or 0), "detail": f[5] if len(f) > 5 else ""})
    return out


def _append_result(run_id, system, name, op, result, size, detail=""):
    with open(_paths(run_id)["results"], "a", encoding="utf-8", newline="\n") as f:
        f.write("\t".join([system, name, op, result, str(size), detail.replace("\t", " ").replace("\n", " ")]) + "\n")


# ---------------------------------------------------------------- start

def start(run_id, dest):
    """Launch the worker for a run. Returns immediately."""
    ops = load_ops(run_id)
    conn = db.connect()
    conn.execute("UPDATE sync_runs SET state='running', started=? WHERE id=?", (db.now(), run_id))
    conn.commit()
    for o in ops:
        if o["op"] in ("send", "update") and not os.path.exists(o["src"]):
            raise RuntimeError(f"source missing: {o['src']}")
    if dest.kind == "mtp":
        return _start_mtp(run_id, dest, ops)
    if dest.kind == "adb":
        th = threading.Thread(target=_run_adb, args=(run_id, dest, ops), daemon=True,
                              name=f"romsync-run-{run_id}")
        th.start()
        return th
    t = threading.Thread(target=_run_volume, args=(run_id, dest, ops), daemon=True, name=f"romsync-run-{run_id}")
    t.start()
    return t


def wait(run_id, poll=1.0, progress=None):
    while True:
        s = read_status(run_id)
        if progress:
            progress(s)
        if s.get("state") in ("done", "error"):
            return s
        time.sleep(poll)


# ---------------------------------------------------------------- volume worker

_SLOW = float(os.environ.get("ROMSYNC_SLOW_COPY", "0"))   # test hook: seconds to sleep per chunk


def _copy_chunks(src, dst, progress=None):
    """Plain chunked copy that reports bytes written as it goes (for the live % / ETA)."""
    done = 0
    with open(src, "rb") as f, open(dst, "wb") as g:
        while True:
            b = f.read(4 * 1024 * 1024)
            if not b:
                break
            g.write(b)
            done += len(b)
            if progress:
                progress(done)
            if _SLOW:
                time.sleep(_SLOW)
    shutil.copystat(src, dst)


def _copy_file_verified(src, dst, expect_hash=None, progress=None):
    part = dst + ".rs-part"
    if os.path.exists(part):
        os.remove(part)
    _copy_chunks(src, part, progress)
    if expect_hash:
        got = devices.blake2(part)
        if got != expect_hash:
            os.remove(part)
            raise RuntimeError(f"hash mismatch after copy ({got[:8]} != {expect_hash[:8]})")
    elif os.path.getsize(part) != os.path.getsize(src):
        os.remove(part)
        raise RuntimeError("size mismatch after copy")
    if os.path.exists(dst):
        os.remove(dst)
    os.replace(part, dst)


def _copy_tree_verified(src, dst, progress=None):
    base = [0]

    def copy_fn(a, b):
        _copy_chunks(a, b, (lambda n: progress(base[0] + n)) if progress else None)
        base[0] += os.path.getsize(a)
    part = dst + ".rs-part"
    if os.path.exists(part):
        shutil.rmtree(part)
    shutil.copytree(src, part, copy_function=copy_fn)
    for r, _, fs in os.walk(src):
        rel = os.path.relpath(r, src)
        for f in fs:
            a = os.path.join(r, f)
            b = os.path.join(part, rel, f) if rel != "." else os.path.join(part, f)
            if devices.blake2(a) != devices.blake2(b):
                shutil.rmtree(part)
                raise RuntimeError(f"hash mismatch in folder copy: {f}")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.replace(part, dst)


def _run_volume(run_id, dest, ops):
    try:
        _run_volume_inner(run_id, dest, ops)
    except Exception as e:  # noqa: BLE001 - the run must always end in a terminal state
        _write_status(run_id, state="error", phase="error", message=str(e))


def _run_volume_inner(run_id, dest, ops):
    counts = {"sent": 0, "removed": 0, "pulled": 0, "failed": 0}
    total = len(ops)
    _write_status(run_id, state="running", phase="starting", done=0, total=total, current="", **counts)
    order = [o for o in ops if o["op"] == "remove"] + [o for o in ops if o["op"] in ("send", "update")] + \
            [o for o in ops if o["op"] == "pull"]
    done = 0
    for o in order:
        sysdir = os.path.join(dest.root, o["system"])
        target = os.path.join(sysdir, o["name"])
        _write_status(run_id, phase=o["op"], current=o["name"], done=done, cur_bytes=0)
        last = [0.0]

        def progress(n):                                   # at most one status write a second
            if time.time() - last[0] >= 1.0:
                last[0] = time.time()
                _write_status(run_id, cur_bytes=n)
        try:
            if o["op"] == "remove":
                if os.path.isdir(target):
                    shutil.rmtree(target)
                elif os.path.exists(target):
                    os.remove(target)
                if os.path.exists(target):
                    raise RuntimeError("still present after delete")
                counts["removed"] += 1
                _append_result(run_id, o["system"], o["name"], o["op"], "ok", 0)
            elif o["op"] in ("send", "update"):
                os.makedirs(sysdir, exist_ok=True)
                if o["kind"] == "folder":
                    _copy_tree_verified(o["src"], target, progress)
                else:
                    _copy_file_verified(o["src"], target, o.get("hash"), progress)
                counts["sent"] += 1
                _append_result(run_id, o["system"], o["name"], o["op"], "ok", o["size"])
            elif o["op"] == "pull":
                if not os.path.exists(target):
                    raise RuntimeError("not on device")
                outdir = os.path.join(pull_dir(run_id), o["system"])
                os.makedirs(outdir, exist_ok=True)
                out = os.path.join(outdir, o["name"])
                if os.path.isdir(target):
                    _copy_tree_verified(target, out, progress)
                    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(out) for f in fs)
                else:
                    _copy_file_verified(target, out, None, progress)
                    size = os.path.getsize(out)
                counts["pulled"] += 1
                _append_result(run_id, o["system"], o["name"], o["op"], "ok", size)
        except Exception as e:  # noqa: BLE001 - every failure is a result line
            counts["failed"] += 1
            _append_result(run_id, o["system"], o["name"], o["op"], "failed", o["size"], str(e))
        done += 1
        _write_status(run_id, done=done, **counts)
    _write_status(run_id, state="done", phase="done", current="", done=done, **counts)


# ---------------------------------------------------------------- ADB worker

def _run_adb(run_id, dest, ops):
    try:
        _run_adb_inner(run_id, dest, ops)
    except Exception as e:  # noqa: BLE001 - the run must always end in a terminal state
        _write_status(run_id, state="error", phase="error", message=str(e))


def _run_adb_inner(run_id, dest, ops):
    """Same shape as the volume worker, over the debug bridge.

    adb push reports its own progress, so cur_bytes is real rather than inferred from a
    growing file the way MTP forces. There is no arrival-stall guesswork here: push
    either returns zero or it failed.
    """
    counts = {"sent": 0, "removed": 0, "pulled": 0, "failed": 0}
    total = len(ops)
    _write_status(run_id, state="running", phase="starting", done=0, total=total, current="", **counts)
    order = [o for o in ops if o["op"] == "remove"] + [o for o in ops if o["op"] in ("send", "update")] + \
            [o for o in ops if o["op"] == "pull"]
    done = 0
    made = set()
    for o in order:
        remote_dir = f"{dest.root}/{o['system']}"
        target = f"{remote_dir}/{o['name']}"
        _write_status(run_id, phase=o["op"], current=o["name"], done=done, cur_bytes=0)
        last = [0.0]

        def progress(n):                                   # at most one status write a second
            if time.time() - last[0] >= 1.0:
                last[0] = time.time()
                _write_status(run_id, cur_bytes=n)
        try:
            if o["op"] == "remove":
                adb.sh_ok(dest.serial, "rm -rf " + adb.q(target), timeout=600)
                ok, out = adb.sh_ok(dest.serial, f"[ -e {adb.q(target)} ] && echo present", timeout=60)
                if ok and "present" in out:
                    raise RuntimeError("still present after delete")
                counts["removed"] += 1
                _append_result(run_id, o["system"], o["name"], o["op"], "ok", 0)
            elif o["op"] in ("send", "update"):
                if remote_dir not in made:
                    adb.sh_ok(dest.serial, "mkdir -p " + adb.q(remote_dir), timeout=60)
                    made.add(remote_dir)
                adb.sh_ok(dest.serial, "rm -rf " + adb.q(target), timeout=600)
                sent = adb.push(dest.serial, o["src"], target, progress)
                counts["sent"] += 1
                _append_result(run_id, o["system"], o["name"], o["op"], "ok", sent or o["size"])
            elif o["op"] == "pull":
                outdir = os.path.join(pull_dir(run_id), o["system"])
                os.makedirs(outdir, exist_ok=True)
                out = adb.pull(dest.serial, target, os.path.join(outdir, o["name"]))
                if out is None:
                    raise RuntimeError("not on device, or the pull failed")
                if os.path.isdir(out):
                    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(out) for f in fs)
                else:
                    size = os.path.getsize(out)
                counts["pulled"] += 1
                _append_result(run_id, o["system"], o["name"], o["op"], "ok", size)
        except Exception as e:  # noqa: BLE001 - every failure is a result line
            counts["failed"] += 1
            _append_result(run_id, o["system"], o["name"], o["op"], "failed", o["size"], str(e))
        done += 1
        _write_status(run_id, done=done, **counts)
    _write_status(run_id, state="done", phase="done", current="", done=done, **counts)



# ---------------------------------------------------------------- MTP worker

MTP_WORKER = ps.MTP_PROLOGUE + r'''
$plan = @(Get-Content -LiteralPath $env:RS_PLAN -Encoding UTF8 | Where-Object { $_ -and -not $_.StartsWith('#') })
$statusPath = $env:RS_STATUS
$resultsPath = $env:RS_RESULTS
$pullRoot = $env:RS_PULL
$total = $plan.Count
$c = @{ sent=0; removed=0; pulled=0; failed=0 }
$script:done = 0; $script:phase = 'starting'; $script:current = ''; $script:curBytes = 0

function Write-Line($path, $text) { [IO.File]::AppendAllText($path, $text + "`n", $utf8) }
function Write-Status($state, $message) {
  $o = [ordered]@{ state=$state; phase=$script:phase; done=$script:done; total=$total; current=$script:current
                   sent=$c.sent; removed=$c.removed; pulled=$c.pulled; failed=$c.failed; message=$message; cur_bytes=$script:curBytes }
  [IO.File]::WriteAllText("$statusPath.tmp", ($o | ConvertTo-Json -Compress), $utf8)
  for ($try = 0; $try -lt 40; $try++) {
    try { Move-Item -LiteralPath "$statusPath.tmp" -Destination $statusPath -Force; return } catch { Start-Sleep -Milliseconds 50 }
  }
}
function Result($system, $name, $op, $result, $size, $detail) {
  $detail = ("$detail" -replace "[`t`r`n]", ' ')
  Write-Line $resultsPath "$system`t$name`t$op`t$result`t$size`t$detail"
}
function Fail($system, $name, $op, $size, $why) { $c['failed']++; Result $system $name $op 'failed' $size $why }

function Size-Deep($item) {
  if (-not $item.IsFolder) { return (Size-Of $item) }
  $t = [int64]0
  foreach ($i in $item.GetFolder.Items()) { $t += (Size-Deep $i) }
  return $t
}
# Wait for an item under $folder to reach $size. Stops when it has not grown for $stallSec.
function Wait-Arrival($folder, $name, $size, $stallSec) {
  $last = -1; $still = 0; $tick = 0
  while ($true) {
    Start-Sleep -Milliseconds 500
    $it = Get-Child $folder $name $false
    if ($it) {
      $now = Size-Deep $it
      $script:curBytes = $now; $tick++
      if (($tick % 3) -eq 0) { Write-Status 'running' '' }
      if ($now -ge $size) { return $true }
      if ($now -eq $last) { $still++ } else { $still = 0 }
      $last = $now
      if ($still -ge ($stallSec * 2)) { return $false }
    } else {
      $still++
      if ($still -ge ($stallSec * 2)) { return $false }
    }
  }
}

Write-Status 'running' ''
try {
  $st = Resolve-Storage $env:RS_DEVICE $env:RS_STORAGE
  $roms = Resolve-Path-OnDevice $st $env:RS_ROOT $true
  if (-not $roms) { throw "ROMs root could not be found or created" }
} catch { $script:phase = 'error'; Write-Status 'error' $_.Exception.Message; exit 1 }

$sysFolders = @{}
function Get-SystemFolder($name, $create) {
  if ($sysFolders.ContainsKey($name)) { return $sysFolders[$name] }
  $item = Get-Child $roms $name $true
  if (-not $item -and $create) { $roms.NewFolder($name); Start-Sleep -Milliseconds 800; $item = Get-Child $roms $name $true }
  if (-not $item) { return $null }
  $sysFolders[$name] = $item.GetFolder
  return $sysFolders[$name]
}

$rows = @()
foreach ($line in $plan) {
  $p = $line -split "`t"
  $rows += [pscustomobject]@{ op=$p[0]; system=$p[1]; name=$p[2]; kind=$p[3]; size=[int64]$p[4]; src=$p[5] }
}

# ---- 1. removals, batched per system --------------------------------------
$dels = @($rows | Where-Object { $_.op -eq 'remove' })
if ($dels.Count -gt 0) {
  $script:phase = 'remove'
  foreach ($group in ($dels | Group-Object system)) {
    $system = $group.Name
    $script:current = $system; Write-Status 'running' ''
    $f = Get-SystemFolder $system $false
    if (-not $f) { foreach ($r in $group.Group) { $script:done++; Fail $system $r.name 'remove' 0 'system folder not on device' }; continue }
    $wanted = @{}; foreach ($r in $group.Group) { $wanted[$r.name] = $true }
    $items = New-Object System.Collections.ArrayList
    foreach ($i in $f.Items()) { if ($wanted.ContainsKey($i.Name)) { [void]$items.Add($i) } }
    $hr = 0
    if ($items.Count -gt 0) { try { $hr = Remove-DeviceItems $items } catch { $hr = 1; $err = $_.Exception.Message } }
    Start-Sleep -Milliseconds 500
    $left = @{}; foreach ($i in $f.Items()) { $left[$i.Name] = $true }
    foreach ($r in $group.Group) {
      $script:done++
      if ($left.ContainsKey($r.name)) {
        $why = if ($hr -eq 0) { 'still present after delete' } else { 'delete failed, hr=0x{0:X8} {1}' -f $hr, $err }
        Fail $system $r.name 'remove' 0 $why
      } else { $c['removed']++; Result $system $r.name 'remove' 'ok' 0 '' }
    }
    Write-Status 'running' ''
  }
}

# ---- 2. sends and updates -------------------------------------------------
foreach ($r in @($rows | Where-Object { $_.op -eq 'send' -or $_.op -eq 'update' })) {
  $script:phase = $r.op; $script:current = $r.name; $script:curBytes = 0; Write-Status 'running' ''
  $script:done++
  $f = Get-SystemFolder $r.system $true
  if (-not $f) { Fail $r.system $r.name $r.op $r.size 'could not create system folder'; continue }
  if (-not (Test-Path -LiteralPath $r.src)) { Fail $r.system $r.name $r.op $r.size 'source missing'; continue }
  $existing = Get-Child $f $r.name $false
  if ($existing) {
    if ($r.op -eq 'send' -and (Size-Deep $existing) -eq $r.size) { $c['sent']++; Result $r.system $r.name $r.op 'ok' $r.size 'already there'; continue }
    try { [void](Remove-DeviceItems @($existing)); Start-Sleep -Milliseconds 500 } catch {}
    if (Get-Child $f $r.name $false) { Fail $r.system $r.name $r.op $r.size 'could not replace existing copy'; continue }
  }
  try { $f.CopyHere($r.src, 1556) } catch { Fail $r.system $r.name $r.op $r.size $_.Exception.Message; continue }
  # MTP reports a growing copy's size in coarse steps (a 4 GB file can sit at one size for minutes), so the
  # stall allowance scales with size: at least 10 min, plus 1 s per 2 MB (run 10 flagged 45 big files that then
  # finished anyway). CopyHere is asynchronous; giving up early just loses track of a copy still running.
  $stall = [math]::Max(600, [int]($r.size / 2MB))
  if (Wait-Arrival $f $r.name $r.size $stall) { $c['sent']++; Result $r.system $r.name $r.op 'ok' $r.size '' }
  else { Fail $r.system $r.name $r.op $r.size 'copy stalled or did not reach full size' }
  Write-Status 'running' ''
}

# ---- 3. pulls -------------------------------------------------------------
$pulls = @($rows | Where-Object { $_.op -eq 'pull' })
if ($pulls.Count -gt 0) {
  $shell = New-Object -ComObject Shell.Application
  foreach ($r in $pulls) {
    $script:phase = 'pull'; $script:current = $r.name; $script:curBytes = 0; Write-Status 'running' ''
    $script:done++
    $f = Get-SystemFolder $r.system $false
    $it = if ($f) { Get-Child $f $r.name $false } else { $null }
    if (-not $it) { Fail $r.system $r.name 'pull' 0 'not on device'; continue }
    $outDir = Join-Path $pullRoot $r.system
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $target = Join-Path $outDir $r.name
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    $want = Size-Deep $it
    try { $shell.NameSpace($outDir).CopyHere($it, 1556) } catch { Fail $r.system $r.name 'pull' $want $_.Exception.Message; continue }
    $last = -1; $still = 0; $ok = $false; $tick = 0
    while ($true) {
      Start-Sleep -Milliseconds 500
      $now = [int64]0
      if (Test-Path -LiteralPath $target) {
        $now = (Get-ChildItem -LiteralPath $target -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        if (-not $now) { $now = (Get-Item -LiteralPath $target).Length }
      }
      $script:curBytes = $now; $tick++
      if (($tick % 3) -eq 0) { Write-Status 'running' '' }
      if ($now -ge $want -and $want -gt 0) { $ok = $true; break }
      if ($now -eq $last) { $still++ } else { $still = 0 }
      $last = $now
      if ($still -ge ([math]::Max(1200, [int]($want / 1MB)))) { break }
    }
    if ($ok) { $c['pulled']++; Result $r.system $r.name 'pull' 'ok' $want '' } else { Fail $r.system $r.name 'pull' $want 'pull stalled or incomplete' }
  }
}

$script:phase = 'done'; $script:current = ''
Write-Status 'done' ''
'''


def _start_mtp(run_id, dest, ops):
    p = _paths(run_id)
    _write_status(run_id, state="running", phase="starting", done=0, total=len(ops), current="",
                  sent=0, removed=0, pulled=0, failed=0)
    env = dest._env(RS_PLAN=p["plan"], RS_STATUS=p["status"], RS_RESULTS=p["results"], RS_PULL=pull_dir(run_id))
    return ps.run(MTP_WORKER, env, background=True, log=p["log"], name=f"run-{run_id}")


# ---------------------------------------------------------------- after a run

def ingest(run_id, device_id):
    """Fold a finished run's results into the profile. Idempotent."""
    conn = db.connect()
    ops = {(o["system"], o["name"], o["op"]): o for o in load_ops(run_id)}
    seq = {(r["rel_path"], r["op"]): r["seq"] for r in conn.execute(
        "SELECT seq, op, rel_path FROM sync_ops WHERE run_id=?", (run_id,))}
    now = db.now()
    moved = 0
    for r in read_results(run_id):
        rel = f"{r['system']}\\{r['name']}"
        o = ops.get((r["system"], r["name"], r["op"]), {})
        ok = r["result"] == "ok"
        s = seq.get((rel, r["op"]))
        if s is not None:
            conn.execute("UPDATE sync_ops SET status=?, error=? WHERE run_id=? AND seq=?",
                         ("done" if ok else "failed", None if ok else r["detail"], run_id, s))
        if not ok:
            continue
        if r["op"] in ("send", "update"):
            moved += r["size"]
            conn.execute(
                """INSERT INTO device_files(device_id,rel_path,kind,size,hash,sent_size,sent_mtime,last_confirmed,missing_since)
                   VALUES(?,?,?,?,?,?,?,?,NULL)
                   ON CONFLICT(device_id,rel_path) DO UPDATE SET kind=excluded.kind, size=excluded.size,
                     hash=excluded.hash, sent_size=excluded.sent_size, sent_mtime=excluded.sent_mtime,
                     last_confirmed=excluded.last_confirmed, missing_since=NULL""",
                (device_id, rel, "sysfile" if r["system"] == "bios" else o.get("kind", "file"),
                 r["size"], o.get("hash"), o.get("size"), o.get("mtime"), now))
        elif r["op"] == "remove":
            conn.execute("DELETE FROM device_files WHERE device_id=? AND rel_path=?", (device_id, rel))
            conn.execute("DELETE FROM decisions WHERE device_id=? AND rel_path=?", (device_id, rel))
        elif r["op"] == "pull":
            moved += r["size"]
    st = read_status(run_id)
    counts = {k: st.get(k, 0) for k in ("sent", "removed", "pulled", "failed")}
    started = conn.execute("SELECT started FROM sync_runs WHERE id=?", (run_id,)).fetchone()["started"]
    conn.execute("UPDATE sync_runs SET finished=?, state=?, counts=?, bytes_moved=? WHERE id=?",
                 (now, "failed" if st.get("state") == "error" else "done", json.dumps(counts), moved, run_id))
    conn.execute("UPDATE devices SET last_seen=? WHERE id=?", (now, device_id))
    conn.commit()
    return {"run": run_id, "started": started, **counts, "bytes": moved}


def pulled_items(run_id):
    """What a run pulled: [{system, name, path, in_store}]."""
    out = []
    root = pull_dir(run_id)
    for system in sorted(os.listdir(root)):
        sd = os.path.join(root, system)
        if not os.path.isdir(sd):
            continue
        for name in sorted(os.listdir(sd)):
            store_path = os.path.join(db.store_root(), system, name)
            out.append({"system": system, "name": name, "path": os.path.join(sd, name),
                        "in_store": os.path.exists(store_path)})
    return out


def place_pulled(run_id, system, name):
    """Move one pulled item into the store. Refuses if the store already has that name."""
    src = os.path.join(pull_dir(run_id), system, name)
    dst = os.path.join(db.store_root(), system, name)
    if not os.path.exists(src):
        raise RuntimeError("nothing pulled by that name")
    if os.path.exists(dst):
        raise RuntimeError(f"the store already has {system}\\{name}; not overwriting")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    return dst
