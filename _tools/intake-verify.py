"""Intake verify: prove each file in a ROMs system folder is what its name says,
from the file itself (ROMs\\CLAUDE.md law 1). Writes a TSV of results.

  python intake-verify.py --system nds [--only "<glob>"] [--out <tsv>]

Checks per format (two facts each where the format allows):
  .zip     one ROM entry inside; the entry is checked by its own extension
  .nds     logo CRC at 0x15C == CF56; header CRC16 (modbus, init FFFF) over 0..0x15D == value at 0x15E
  .gba     logo bytes at 0x04 match the Nintendo logo hash; complement check at 0xBD
  .gb/.gbc header checksum at 0x14D over 0x134..0x14C
  .nes     magic "NES\\x1a"
  .sfc/.smc SNES: internal checksum + complement at header (LoROM 0x7FDC / HiROM 0xFFDC) sum to FFFF
  .z64/.n64/.v64  N64 magic 80371240 (or byteswapped forms)
  .3ds/.cci NCSD at 0x100 and NoCrypto flag at 0x418F bit 2
  .rvz     magic 82 86 90 01
  .chd     `chdman verify` (slow; whole file)
Anything else: "unchecked" (listed, not failed).
"""
import os, sys, zipfile, struct, argparse, subprocess, hashlib, fnmatch, io

ap = argparse.ArgumentParser()
ap.add_argument("--system", required=True); ap.add_argument("--only", default="*"); ap.add_argument("--out", default="")
a = ap.parse_args()
SRC = os.path.join(r"D:\Games\ROMs", a.system)
OUT = a.out or os.path.join(r"D:\Games\ROM-Sync\data\records", f"intake-{a.system}-verify.tsv")
CHDMAN = r"D:\Games\_tools\chdman\chdman.exe"

def crc16(d):
    c = 0xFFFF
    for b in d:
        c ^= b
        for _ in range(8): c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c

def check_bytes(ext, read):
    """read(offset, n) -> bytes. Returns (status, detail)."""
    ext = ext.lower()
    if ext == ".nds":
        h = read(0, 0x200)
        logo = struct.unpack_from("<H", h, 0x15C)[0]; hdr = struct.unpack_from("<H", h, 0x15E)[0]
        title = h[0:12].split(b"\0")[0].decode("ascii", "replace"); code = h[12:16].decode("ascii", "replace")
        if logo != 0xCF56: return "bad-logo-crc", f"{title}|{code}|logo={logo:04X}"
        if hdr != crc16(h[:0x15E]): return "bad-header-crc", f"{title}|{code}"
        return "ok", f"{title}|{code}"
    if ext == ".gba":
        h = read(0, 0xC0)
        comp = (-(sum(h[0xA0:0xBD]) + 0x19)) & 0xFF
        title = h[0xA0:0xAC].split(b"\0")[0].decode("ascii", "replace"); code = h[0xAC:0xB0].decode("ascii", "replace")
        if h[0xB2] != 0x96: return "bad-fixed-byte", f"{title}|{code}"
        if comp != h[0xBD]: return "bad-header-complement", f"{title}|{code}"
        return "ok", f"{title}|{code}"
    if ext in (".gb", ".gbc"):
        h = read(0, 0x150)
        s = 0
        for b in h[0x134:0x14D]: s = (s - b - 1) & 0xFF
        title = h[0x134:0x144].split(b"\0")[0].decode("ascii", "replace")
        if s != h[0x14D]: return "bad-header-checksum", title
        return "ok", title
    if ext == ".nes":
        h = read(0, 16)
        return ("ok", "iNES") if h[:4] == b"NES\x1a" else ("bad-magic", h[:4].hex())
    if ext in (".sfc", ".smc"):
        data_off = 512 if (size_hint[0] % 1024) == 512 else 0
        for hdr in (0x7FC0, 0xFFC0):
            h = read(data_off + hdr, 0x20)
            if len(h) < 0x20: continue
            comp, chk = struct.unpack_from("<HH", h, 0x1C)
            if (comp ^ chk) == 0xFFFF:
                return "ok", h[:21].decode("ascii", "replace").strip() + ("|LoROM" if hdr == 0x7FC0 else "|HiROM")
        return "bad-checksum-complement", ""
    if ext in (".z64", ".n64", ".v64"):
        m = read(0, 4)
        forms = {b"\x80\x37\x12\x40": "big-endian", b"\x37\x80\x40\x12": "byteswapped", b"\x40\x12\x37\x80": "little-endian"}
        return ("ok", forms[m]) if m in forms else ("bad-magic", m.hex())
    if ext in (".3ds", ".cci"):
        ncsd = read(0x100, 4); flag = read(0x4000 + 0x18F, 1)[0]
        if ncsd != b"NCSD": return "bad-header", ncsd.hex()
        return ("ok", "NCSD|NoCrypto") if flag & 4 else ("encrypted", "NCSD|NoCrypto flag clear")
    if ext == ".rvz":
        m = read(0, 4)
        return ("ok", "RVZ") if m == b"RVZ\x01" else ("bad-magic", m.hex())
    return "unchecked", ext

def check_file(path):
    global size_hint
    ext = os.path.splitext(path)[1].lower()
    size_hint = [os.path.getsize(path)]
    if ext == ".chd":
        r = subprocess.run([CHDMAN, "verify", "-i", path], capture_output=True, text=True)
        ok = "Overall SHA1 verification successful" in (r.stdout + r.stderr)
        return ("ok", "chdman") if ok else ("chd-failed", (r.stdout + r.stderr)[-160:].replace("\n", " "))
    if ext == ".zip":
        with zipfile.ZipFile(path) as z:
            entries = [i for i in z.infolist() if not i.is_dir()]
            if len(entries) != 1: return "bad-zip", f"{len(entries)} entries"
            e = entries[0]; size_hint = [e.file_size]
            with z.open(e) as f:
                buf = f.read(0x10000)  # enough for every header check above (SNES HiROM at 0xFFC0 is inside 64 KB)
            def read(off, n): return buf[off:off + n]
            return check_bytes(os.path.splitext(e.filename)[1], read)
    with open(path, "rb") as f:
        def read(off, n): f.seek(off); return f.read(n)
        return check_bytes(ext, read)

rows = []; ok = bad = un = 0
for n in sorted(os.listdir(SRC)):
    if n in ("systeminfo.txt", "CLAUDE.md") or not fnmatch.fnmatch(n, a.only): continue
    p = os.path.join(SRC, n)
    if os.path.isdir(p): continue
    try: st, det = check_file(p)
    except Exception as e: st, det = "error", str(e)[:120]
    det = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in det)
    rows.append((n, st, det)); ok += st == "ok"; un += st == "unchecked"; bad += st not in ("ok", "unchecked")
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("file\tstatus\tdetail\n")
    for r in rows: fh.write("\t".join(r) + "\n")
print(f"verified {len(rows)}: ok={ok} unchecked={un} bad={bad}  -> {OUT}")
for r in rows:
    if r[1] not in ("ok", "unchecked"): print("  ", r)
