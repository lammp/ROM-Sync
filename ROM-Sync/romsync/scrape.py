"""Match store games against IGDB: cover, summary, dates, rating, genres.

ROM Curator 1 did this with the same rules; ROM-Sync carries the matched rows
over (legacy.py) and scrapes only what is still 'pending' - newly added games.
Matching: IGDB full-text search on the cleaned title, restricted to the
system's platform first; best difflib ratio over name + alternative names,
platform misses ranked 0.15 lower; accept at 0.55 like ROM Curator did.
"""
import difflib
import json
import os
import re

from . import db, igdb

FIELDS = ("name,summary,storyline,first_release_date,total_rating,total_rating_count,"
          "rating,rating_count,genres.name,themes.name,cover.image_id,platforms,"
          "alternative_names.name")
ACCEPT = 0.55

PLATFORM_ALIASES = {
    "snes": ["Super Nintendo Entertainment System", "Super Famicom", "SNES"],
    "nes": ["Nintendo Entertainment System", "Family Computer", "NES"],
    "fds": ["Family Computer Disk System"],
    "gb": ["Game Boy"], "gbc": ["Game Boy Color"], "gba": ["Game Boy Advance"],
    "n64": ["Nintendo 64"], "nds": ["Nintendo DS", "Nintendo DSi"],
    "n3ds": ["Nintendo 3DS", "New Nintendo 3DS"],
    "gc": ["Nintendo GameCube"], "wii": ["Wii"], "wiiu": ["Wii U"], "switch": ["Nintendo Switch"],
    "virtualboy": ["Virtual Boy"],
    "mastersystem": ["Sega Master System/Mark III", "Sega Master System", "Master System"],
    "megadrive": ["Sega Mega Drive/Genesis", "Sega Mega Drive", "Genesis"],
    "genesis": ["Sega Mega Drive/Genesis", "Genesis"],
    "gamegear": ["Sega Game Gear", "Game Gear"], "sega32x": ["Sega 32X"],
    "segacd": ["Sega CD", "Sega Mega-CD"], "saturn": ["Sega Saturn"], "dreamcast": ["Dreamcast"],
    "psx": ["PlayStation"], "ps2": ["PlayStation 2"], "ps3": ["PlayStation 3"],
    "psp": ["PlayStation Portable"], "psvita": ["PlayStation Vita"],
    "atari2600": ["Atari 2600"], "atari7800": ["Atari 7800"], "atarilynx": ["Atari Lynx", "Lynx"],
    "atarijaguar": ["Atari Jaguar"], "pcengine": ["TurboGrafx-16/PC Engine", "PC Engine"],
    "tg16": ["TurboGrafx-16/PC Engine", "TurboGrafx-16"],
    "neogeo": ["Neo Geo AES", "Neo Geo MVS"], "ngp": ["Neo Geo Pocket"], "ngpc": ["Neo Geo Pocket Color"],
    "wonderswan": ["WonderSwan"], "wonderswancolor": ["WonderSwan Color"],
    "arcade": ["Arcade"], "fbneo": ["Arcade"], "mame": ["Arcade"],
    "dos": ["DOS"], "pc": ["PC (Microsoft Windows)"], "amiga": ["Amiga"], "c64": ["Commodore C64/128/MAX"],
    "3do": ["3DO Interactive Multiplayer"], "colecovision": ["ColecoVision"],
}


def resolve_platforms(client):
    """Fill systems.platform_id from IGDB's platform list. Returns {system: id}."""
    rows = client.query("platforms", "fields id,name,alternative_name; limit 500;")
    by_name = {}
    for p in rows:
        by_name[p["name"].lower()] = p["id"]
        if p.get("alternative_name"):
            by_name.setdefault(p["alternative_name"].lower(), p["id"])
    conn = db.connect()
    out = {}
    for s in conn.execute("SELECT key, label, platform_id FROM systems").fetchall():
        pid = s["platform_id"]
        if not pid:
            for alias in PLATFORM_ALIASES.get(s["key"], []) + [s["label"]]:
                pid = by_name.get(alias.lower())
                if pid:
                    break
            if pid:
                conn.execute("UPDATE systems SET platform_id=? WHERE key=?", (pid, s["key"]))
        if pid:
            out[s["key"]] = pid
    conn.commit()
    return out


def _norm(s):
    s = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def _score(wanted, cand):
    names = [cand.get("name", "")] + [a["name"] for a in cand.get("alternative_names") or [] if a.get("name")]
    w = _norm(wanted)
    return max((difflib.SequenceMatcher(None, w, _norm(n)).ratio() for n in names if n), default=0.0)


def match(client, title, platform_id):
    """(best_candidate, confidence 0..1) for one title."""
    safe = title.replace('"', "").strip()
    if not safe:
        return None, 0.0
    plat = f"where platforms = ({platform_id}); " if platform_id else ""
    queries = [f'search "{safe}"; fields {FIELDS}; {plat}limit 10;']
    head = safe.split(":")[0].strip()
    if head and head != safe and platform_id:
        queries.append(f'search "{head}"; fields {FIELDS}; {plat}limit 10;')
    queries.append(f'search "{safe}"; fields {FIELDS}; limit 10;')
    best, best_score, on_plat = None, 0.0, False
    for q in queries:
        for c in client.query("games", q):
            hit = bool(platform_id) and platform_id in (c.get("platforms") or [])
            score = _score(safe, c) - (0.0 if hit or not platform_id else 0.15)
            if score > best_score:
                best, best_score, on_plat = c, score, hit
        if best_score >= 0.92 and (on_plat or not platform_id):
            break
    return best, max(0.0, round(best_score, 3))


def summarise(text, words=100):
    if not text:
        return ""
    clean = re.sub(r"\s+", " ", text).strip()
    parts = clean.split(" ")
    if len(parts) <= words:
        return clean
    cut = " ".join(parts[:words])
    stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: stop + 1] if stop > len(cut) * 0.6 else cut.rstrip(",;: ") + "…"


def cover(image_id):
    if not image_id:
        return None
    fname = f"{image_id}.jpg"
    dest = os.path.join(db.data_dir(), "covers", fname)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return fname
    return fname if igdb.fetch_image(image_id, "t_cover_big", dest) else None


def apply(conn, game_id, best, score):
    genres = [g["name"] for g in best.get("genres") or []]
    genres += [t["name"] for t in best.get("themes") or [] if t["name"] not in genres]
    conn.execute(
        """UPDATE games SET scrape_state='matched', confidence=?, igdb_id=?, igdb_name=?, summary=?,
               release_date=?, rating=?, rating_count=?, genres=?,
               cover_file=COALESCE(?, CASE WHEN cover_file LIKE 'lr-%' THEN cover_file END) WHERE id=?""",
        (score, best.get("id"), best.get("name"), summarise(best.get("summary") or best.get("storyline")),
         best.get("first_release_date"), best.get("total_rating") or best.get("rating"),
         best.get("total_rating_count") or best.get("rating_count"), json.dumps(genres),
         cover((best.get("cover") or {}).get("image_id")), game_id))


def run(systems=None, only_pending=True, limit=None, progress=None, ids=None, states=None):
    """Scrape pending games (or the given ids / states). Returns counts.

    states: which scrape_state values to (re)do; default pending+error. only_pending=False
    means everything, and the IGDB-sourced tags and media of those games are dropped first
    so the enrich pass refreshes them.
    """
    conn = db.connect()
    client = igdb.Client()
    platforms = resolve_platforms(client)
    where, params = [], []
    if ids:
        where.append("id IN (%s)" % ",".join("?" * len(ids)))
        params += list(ids)
    else:
        if systems:
            where.append("system IN (%s)" % ",".join("?" * len(systems)))
            params += list(systems)
        if states:
            where.append("scrape_state IN (%s)" % ",".join("?" * len(states)))
            params += list(states)
        elif only_pending:
            where.append("scrape_state IN ('pending','error')")
        else:
            from . import enrich
            enrich.ensure()
            sub = "SELECT id FROM games" + (" WHERE system IN (%s)" % ",".join("?" * len(systems)) if systems else "")
            conn.execute(f"DELETE FROM tags WHERE source='igdb' AND game_id IN ({sub})", list(systems or []))
            conn.execute(f"DELETE FROM game_media WHERE game_id IN ({sub})", list(systems or []))
            conn.commit()
    sql = "SELECT id, system, title FROM games"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY system, title"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql, params).fetchall()
    done = matched = unmatched = errors = 0
    for r in rows:
        if progress:
            progress(f"{done}/{len(rows)}  {r['system']}: {r['title']}  (matched {matched}, unmatched {unmatched})")
        try:
            best, score = match(client, r["title"], platforms.get(r["system"]))
            if best and score >= ACCEPT:
                apply(conn, r["id"], best, score)
                matched += 1
            else:
                conn.execute("UPDATE games SET scrape_state='unmatched', confidence=? WHERE id=?", (score, r["id"]))
                unmatched += 1
            conn.commit()
        except igdb.IgdbError as e:
            conn.execute("UPDATE games SET scrape_state='error' WHERE id=?", (r["id"],))
            conn.commit()
            errors += 1
            if errors > 25:
                raise igdb.IgdbError(f"stopped after repeated failures: {e}")
        done += 1
    out = {"games": len(rows), "matched": matched, "unmatched": unmatched, "errors": errors}
    if progress:
        progress(f"done: {out}")
    return out


def rematch(game_id, ref):
    """Pin a game to a specific IGDB game: numeric id, slug, or an igdb.com URL (manual fix from the UI)."""
    client = igdb.Client()
    ref = str(ref).strip().rstrip("/")
    if "igdb.com/games/" in ref:
        ref = ref.split("igdb.com/games/", 1)[1].split("/")[0].split("?")[0]
    if ref.isdigit():
        res = client.query("games", f"fields {FIELDS}; where id = {int(ref)};")
    else:
        slug = re.sub(r"[^a-z0-9-]+", "-", ref.lower()).strip("-")
        res = client.query("games", f'fields {FIELDS}; where slug = "{slug}";')
    if not res:
        raise igdb.IgdbError(f"IGDB game not found: {ref}")
    from . import enrich
    enrich.ensure()
    conn = db.connect()
    conn.execute("DELETE FROM tags WHERE game_id=? AND source='igdb'", (game_id,))
    conn.execute("DELETE FROM game_media WHERE game_id=?", (game_id,))
    apply(conn, game_id, res[0], 1.0)
    conn.commit()
    return res[0].get("name")
