"""Cover fallback from libretro-thumbnails, for games IGDB gave no cover.

libretro keeps box art per system under thumbnails.libretro.com/<playlist>/Named_Boxarts/,
one PNG per game named by its No-Intro name, with & * / : ` < > ? \\ | " replaced by _.
The store is No-Intro named, so the file name usually matches exactly.

Only games with no cover are touched, and an IGDB cover is never replaced. A libretro cover
is stored as data\\covers\\lr-<system>-<hash>.png; scrape.apply keeps it when a later IGDB
match still has no cover. No account, key or rate limit is involved.

Matching, strongest first, within one system's listing:
  exact      the file stem (or the game's title) after the character substitution
  nocase     the same, ignoring case
  region     base title + first parenthesis, e.g. "Game (USA)" for "Game (USA) (En,Fr,Es)"
  title      base title only; a same-region name is preferred, then World, USA, Europe
"""
import hashlib
import os
import re
import time
import urllib.parse
import urllib.request

from . import db

BASE = "https://thumbnails.libretro.com/"
LISTING_MAX_AGE = 7 * 86400
BAD = re.compile(r'[&*/:`<>?\\|"]')

PLAYLISTS = {
    "nes": "Nintendo - Nintendo Entertainment System",
    "fds": "Nintendo - Family Computer Disk System",
    "snes": "Nintendo - Super Nintendo Entertainment System",
    "n64": "Nintendo - Nintendo 64",
    "gb": "Nintendo - Game Boy", "gbc": "Nintendo - Game Boy Color", "gba": "Nintendo - Game Boy Advance",
    "nds": "Nintendo - Nintendo DS", "n3ds": "Nintendo - Nintendo 3DS",
    "gc": "Nintendo - GameCube", "wii": "Nintendo - Wii", "virtualboy": "Nintendo - Virtual Boy",
    "mastersystem": "Sega - Master System - Mark III", "megadrive": "Sega - Mega Drive - Genesis",
    "genesis": "Sega - Mega Drive - Genesis", "gamegear": "Sega - Game Gear", "sega32x": "Sega - 32X",
    "segacd": "Sega - Mega-CD - Sega CD", "saturn": "Sega - Saturn", "dreamcast": "Sega - Dreamcast",
    "psx": "Sony - PlayStation", "ps2": "Sony - PlayStation 2", "psp": "Sony - PlayStation Portable",
    "atari2600": "Atari - 2600", "atari7800": "Atari - 7800", "atarilynx": "Atari - Lynx",
    "pcengine": "NEC - PC Engine - TurboGrafx 16", "tg16": "NEC - PC Engine - TurboGrafx 16",
    "ngp": "SNK - Neo Geo Pocket", "ngpc": "SNK - Neo Geo Pocket Color",
    "wonderswan": "Bandai - WonderSwan", "wonderswancolor": "Bandai - WonderSwan Color",
    "fbneo": "FBNeo - Arcade Games",
}
REGION_PREF = ("(World)", "(USA)", "(Europe)")


def _cache_dir():
    d = os.path.join(db.data_dir(), "tmp", "libretro")
    os.makedirs(d, exist_ok=True)
    return d


def listing(system, refresh=False):
    """{display name without .png: href} for one system's Named_Boxarts, cached for a week."""
    folder = PLAYLISTS.get(system)
    if not folder:
        return None
    cache = os.path.join(_cache_dir(), system + ".tsv")
    if not refresh and os.path.isfile(cache) and time.time() - os.path.getmtime(cache) < LISTING_MAX_AGE:
        with open(cache, encoding="utf-8") as f:
            return dict(line.rstrip("\n").split("\t", 1) for line in f if "\t" in line)
    url = BASE + urllib.parse.quote(folder) + "/Named_Boxarts/"
    with urllib.request.urlopen(url, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    out = {}
    for href in re.findall(r'href="([^"?/][^"]*\.png)"', html):
        out[urllib.parse.unquote(href)[:-4]] = href
    tmp = cache + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(f"{k}\t{v}\n" for k, v in out.items())
    os.replace(tmp, cache)
    return out


def _stem(name):
    base, ext = os.path.splitext(name)
    return base if ext and len(ext) <= 5 else name


def _head(s):
    """Base title and first parenthesis: ('game', '(USA)')."""
    m = re.match(r"^(.*?)\s*(\([^)]*\))?(?:\s*[(\[].*)?$", s)
    return (m.group(1) or s).strip().lower(), (m.group(2) or "")


class Index:
    def __init__(self, names):
        self.exact = {}
        self.nocase = {}
        self.region = {}
        self.title = {}
        for n in names:
            self.exact[n] = n
            self.nocase.setdefault(n.lower(), n)
            t, reg = _head(n)
            if reg:
                self.region.setdefault((t, reg.lower()), []).append(n)
            self.title.setdefault(t, []).append(n)

    def find(self, wanted):
        """(listing name, level) or (None, None)."""
        for w in wanted:
            w = BAD.sub("_", w)
            if w in self.exact:
                return w, "exact"
        for w in wanted:
            w = BAD.sub("_", w).lower()
            if w in self.nocase:
                return self.nocase[w], "nocase"
        for w in wanted:
            t, reg = _head(BAD.sub("_", w))
            hits = self.region.get((t, reg.lower()))
            if hits:
                return min(hits, key=len), "region"
        for w in wanted:
            t, reg = _head(BAD.sub("_", w))
            hits = self.title.get(t)
            if hits:
                for pref in ([reg] if reg else []) + list(REGION_PREF):
                    pick = [h for h in hits if pref and pref.lower() in h.lower()]
                    if pick:
                        return min(pick, key=len), "title"
                return min(hits, key=len), "title"
        return None, None


def _fetch(system, href, dest):
    url = BASE + urllib.parse.quote(PLAYLISTS[system]) + "/Named_Boxarts/" + href
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(url, timeout=30) as r, open(tmp, "wb") as f:
            f.write(r.read())
        if os.path.getsize(tmp) < 100:
            raise OSError("empty image")
        os.replace(tmp, dest)
        return True
    except (urllib.error.URLError, OSError):
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def run(progress=None, ids=None, refresh=False, workers=8):
    """Fill missing covers from libretro. Returns counts by outcome and match level.

    Matching is local against each system's cached listing; the downloads run in parallel
    and each cover is written to the database as it lands, so an interrupted run resumes.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    conn = db.connect()
    sql = "SELECT id, system, name, title FROM games WHERE (cover_file IS NULL OR cover_file='')"
    params = []
    if ids:
        sql += " AND id IN (%s)" % ",".join("?" * len(ids))
        params = list(ids)
    rows = conn.execute(sql + " ORDER BY system, name", params).fetchall()
    out = {"games": len(rows), "filled": 0, "not_found": 0, "failed": 0, "no_libretro_system": 0,
           "levels": {}, "systems": {}}
    covers = os.path.join(db.data_dir(), "covers")
    os.makedirs(covers, exist_ok=True)
    indexes, jobs = {}, []
    for r in rows:
        sysk = r["system"]
        if sysk not in indexes:
            if progress:
                progress(f"reading the libretro box-art list for {sysk}")
            try:
                lst = listing(sysk, refresh)
                indexes[sysk] = (Index(lst.keys()), lst) if lst else None
            except (urllib.error.URLError, OSError):
                indexes[sysk] = None
        s = out["systems"].setdefault(sysk, {"filled": 0, "missing": 0})
        ix = indexes[sysk]
        if ix is None:
            out["no_libretro_system"] += 1
            s["missing"] += 1
            continue
        index, lst = ix
        hit, level = index.find([w for w in (_stem(r["name"]), r["title"]) if w])
        if not hit:
            out["not_found"] += 1
            s["missing"] += 1
            continue
        fname = f"lr-{sysk}-{hashlib.md5(hit.encode('utf-8')).hexdigest()[:16]}.png"
        jobs.append((r["id"], sysk, lst[hit], fname, level))

    def fetch(job):
        dest = os.path.join(covers, job[3])
        return job, (os.path.isfile(dest) and os.path.getsize(dest) > 0) or _fetch(job[1], job[2], dest)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch, j) for j in jobs]
        for n, fut in enumerate(as_completed(futures), 1):
            (gid, sysk, _href, fname, level), ok = fut.result()
            s = out["systems"][sysk]
            if ok:
                conn.execute("UPDATE games SET cover_file=? WHERE id=? AND (cover_file IS NULL OR cover_file='')",
                             (fname, gid))
                conn.commit()
                out["filled"] += 1
                s["filled"] += 1
                out["levels"][level] = out["levels"].get(level, 0) + 1
            else:
                out["failed"] += 1
                s["missing"] += 1
            if progress and n % 10 == 0:
                progress(f"{n}/{len(jobs)} covers downloaded  (filled {out['filled']}, failed {out['failed']})")
    if progress:
        progress(f"libretro covers: {out}")
    return out
