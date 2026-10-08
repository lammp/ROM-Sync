"""Indexes the store: an ES-DE style ROMs tree, one folder per system.

A game unit is either a single file with an accepted extension, or a folder
inside the system folder (a multi-disc ``Game.m3u`` folder, the GTA V folder).
Folders are one unit: their size is the sum of their files and their mtime is
the newest file inside.

The scanner never writes inside the store.
"""
import os
import re

from . import db

# Files that are bookkeeping, not games.
SKIP_FILES = {"systeminfo.txt", "systems.txt", ".nomedia", "gamelist.xml", "desktop.ini"}
# Folders under a system folder that are never game units.
SKIP_DIRS = {"media", "images", "videos", "manuals", "downloaded_media", "covers",
             "shaders", "states", "saves", "sdmc", "cache", "textures"}
# Top-level folders under the store that are not systems.
NOT_SYSTEMS = {"bios", "emulators"}

TAG_RE = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
ARTICLE_RE = re.compile(r"^(.*),\s*(The|A|An|Le|La|Les|Der|Die|Das|El|Los)$", re.I)

# Arcade sets are named by their MAME/FBNeo short name; the title has to come from a table.
ARCADE_SYSTEMS = {"fbneo", "arcade", "mame", "neogeo", "cps1", "cps2", "cps3"}
ARCADE_TITLES = {
    "1943": "1943: The Battle of Midway", "aburner2": "After Burner II", "altbeast": "Altered Beast",
    "arkanoid": "Arkanoid", "asteroid": "Asteroids", "atetris": "Tetris", "avsp": "Alien vs. Predator",
    "btoads": "Battletoads", "bublbobl": "Bubble Bobble", "captcomm": "Captain Commando",
    "centiped": "Centipede", "contra": "Contra", "ddonpach": "DoDonPachi", "ddragon": "Double Dragon",
    "defender": "Defender", "digdug": "Dig Dug", "dino": "Cadillacs and Dinosaurs", "dkong": "Donkey Kong",
    "ffight": "Final Fight", "frogger": "Frogger", "galaga": "Galaga", "galaxian": "Galaxian",
    "garou": "Garou: Mark of the Wolves", "gauntlet": "Gauntlet", "gng": "Ghosts 'n Goblins",
    "goldnaxe": "Golden Axe", "gradius": "Gradius", "invaders": "Space Invaders", "joust": "Joust",
    "kof98": "The King of Fighters '98", "mario": "Mario Bros.", "missile": "Missile Command",
    "mk": "Mortal Kombat", "mk2": "Mortal Kombat II", "mslug": "Metal Slug", "mslug3": "Metal Slug 3",
    "mslugx": "Metal Slug X", "mspacman": "Ms. Pac-Man", "mvsc": "Marvel vs. Capcom: Clash of Super Heroes",
    "nbajam": "NBA Jam", "neogeo": "Neo Geo BIOS", "outrun": "OutRun", "pacman": "Pac-Man",
    "pbobblen": "Puzzle Bobble", "punchout": "Punch-Out!!", "qbert": "Q*bert", "raiden": "Raiden",
    "rampage": "Rampage", "rbisland": "Rainbow Islands", "robotron": "Robotron: 2084",
    "rthunder": "Rolling Thunder", "rtype": "R-Type", "samsho2": "Samurai Shodown II",
    "sf2": "Street Fighter II: The World Warrior", "sfa3": "Street Fighter Alpha 3",
    "sfiii3": "Street Fighter III: 3rd Strike", "sharrier": "Space Harrier", "shinobi": "Shinobi",
    "simpsons": "The Simpsons", "smashtv": "Smash T.V.", "snowbros": "Snow Bros.", "spyhunt": "Spy Hunter",
    "ssf2t": "Super Street Fighter II Turbo", "ssriders": "Sunset Riders", "starwars": "Star Wars",
    "tmnt": "Teenage Mutant Ninja Turtles", "tnzs": "The NewZealand Story", "toki": "Toki",
    "turfmast": "Neo Turf Masters", "umk3": "Ultimate Mortal Kombat 3", "wjammers": "Windjammers",
    "xmen": "X-Men",
}


def read_systeminfo(folder):
    """(label, accepted_extensions) from systeminfo.txt; label falls back to the folder name."""
    path = os.path.join(folder, "systeminfo.txt")
    label, exts = os.path.basename(folder), set()
    if not os.path.isfile(path):
        return label, exts
    try:
        lines = [l.rstrip("\n") for l in open(path, encoding="utf-8", errors="replace")]
    except OSError:
        return label, exts
    for i, line in enumerate(lines):
        if line.strip() == "Full system name:" and i + 1 < len(lines):
            label = lines[i + 1].strip() or label
        if line.strip() == "Supported file extensions:" and i + 1 < len(lines):
            exts = {e.lower() for e in lines[i + 1].split() if e.startswith(".")}
    return label, exts


def clean_title(name, system=None):
    """'Legend of Zelda, The - A Link to the Past (USA).zip' -> 'The Legend of Zelda: A Link to the Past'"""
    stem = os.path.splitext(name)[0] if "." in name else name
    if system in ARCADE_SYSTEMS:
        return ARCADE_TITLES.get(stem.lower(), stem)
    stem = TAG_RE.sub("", stem).strip()
    m = ARTICLE_RE.match(stem)
    if m:
        stem = f"{m.group(2)} {m.group(1)}"
    else:
        head, sep, tail = stem.partition(" - ")
        m2 = ARTICLE_RE.match(head)
        if m2 and sep:
            stem = f"{m2.group(2)} {m2.group(1)} - {tail}"
    stem = stem.replace(" - ", ": ")
    return re.sub(r"\s+", " ", stem).strip()


def region_of(name):
    tags = re.findall(r"\(([^()]*)\)", name)
    return tags[0] if tags else None


def _walk_unit(folder):
    """All files under a folder unit: list of (abs_path, size, mtime)."""
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f in SKIP_FILES or f.startswith("."):
                continue
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            out.append((p, st.st_size, st.st_mtime))
    return out


def scan(store=None, progress=None):
    """Index every game unit under the store. Returns a summary dict.

    Rows for units that have gone are removed. Existing rows keep their metadata.
    """
    store = store or db.store_root()
    conn = db.connect()
    seen, added, updated, systems = set(), 0, 0, 0
    stamp = db.now()

    for entry in sorted(os.scandir(store), key=lambda e: e.name.lower()):
        n = entry.name
        if not entry.is_dir() or n.startswith(".") or n.startswith("_") or n.lower() in NOT_SYSTEMS:
            continue
        label, exts = read_systeminfo(entry.path)
        if not exts:
            continue                                 # not an ES-DE system folder
        conn.execute("INSERT INTO systems(key,label,exts) VALUES(?,?,?) "
                     "ON CONFLICT(key) DO UPDATE SET label=excluded.label, exts=excluded.exts",
                     (n, label, __import__("json").dumps(sorted(exts))))
        systems += 1
        if progress:
            progress(f"scanning {label}")

        for item in os.scandir(entry.path):
            name = item.name
            if name in SKIP_FILES or name.startswith(".") or name.startswith("_"):
                continue
            if item.is_dir():
                if name.lower() in SKIP_DIRS:
                    continue
                files = _walk_unit(item.path)
                if not files:
                    continue
                kind, size = "folder", sum(f[1] for f in files)
                mtime, count = max(f[2] for f in files), len(files)
            elif item.is_file():
                ext = os.path.splitext(name)[1].lower()
                if ext not in exts:
                    continue
                st = item.stat()
                kind, size, mtime, count, files = "file", st.st_size, st.st_mtime, 1, None
            else:
                continue

            rel = os.path.relpath(item.path, store)
            seen.add(rel)
            row = conn.execute("SELECT id,size,mtime FROM games WHERE rel_path=?", (rel,)).fetchone()
            if row is None:
                cur = conn.execute(
                    """INSERT INTO games(system,rel_path,kind,name,title,region,size,mtime,file_count,seen_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (n, rel, kind, name, clean_title(name, n), region_of(name), size, mtime, count, stamp))
                gid, added = cur.lastrowid, added + 1
            else:
                gid = row["id"]
                if row["size"] != size or abs(row["mtime"] - mtime) > 1:
                    conn.execute("UPDATE games SET size=?,mtime=?,file_count=?,seen_at=?,"
                                 "hash=NULL,hash_size=NULL,hash_mtime=NULL WHERE id=?",
                                 (size, mtime, count, stamp, gid))
                    updated += 1
                else:
                    conn.execute("UPDATE games SET seen_at=? WHERE id=?", (stamp, gid))
            if files is not None:
                conn.execute("DELETE FROM game_files WHERE game_id=?", (gid,))
                conn.executemany(
                    "INSERT INTO game_files(game_id,rel_path,size,mtime) VALUES(?,?,?,?)",
                    [(gid, os.path.relpath(p, store), s, m) for p, s, m in files])
        conn.commit()

    gone = [r["rel_path"] for r in conn.execute("SELECT rel_path FROM games").fetchall()
            if r["rel_path"] not in seen]
    for rel in gone:
        conn.execute("DELETE FROM games WHERE rel_path=?", (rel,))
    conn.execute("DELETE FROM systems WHERE key NOT IN (SELECT DISTINCT system FROM games)")
    conn.commit()

    total = conn.execute("SELECT COUNT(*) c FROM games").fetchone()["c"]
    return {"systems": systems, "games": total, "added": added, "updated": updated, "removed": len(gone)}
