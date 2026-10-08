"""Second IGDB pass: screenshots and linking tags for games that already matched.

One batched query per 200 games (IGDB allows `where id = (...)`), so the whole
library is a handful of requests. Writes:

    game_media   screenshot image ids per game (downloaded on demand by the server)
    tags         franchise / collection / theme / mode / perspective, source=igdb, accepted

Existing tags and decisions are left alone (INSERT OR IGNORE).
"""
import json
import os

from . import db, igdb, tags

SCHEMA = """
CREATE TABLE IF NOT EXISTS game_media (
    game_id  INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    kind     TEXT NOT NULL,          -- screenshot | artwork
    image_id TEXT NOT NULL,
    seq      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (game_id, kind, image_id)
);
"""
FIELDS = ("id,screenshots.image_id,artworks.image_id,franchises.name,franchise.name,collections.name,"
          "themes.name,game_modes.name,player_perspectives.name,similar_games")
KINDS = {"franchises": "franchise", "collections": "collection", "themes": "theme",
         "game_modes": "mode", "player_perspectives": "perspective"}


def ensure():
    conn = db.connect()
    conn.executescript(SCHEMA)
    conn.commit()
    tags.ensure()


def screens_dir():
    d = os.path.join(db.data_dir(), "screens")
    os.makedirs(d, exist_ok=True)
    return d


def run(progress=None, only_missing=True):
    ensure()
    conn = db.connect()
    client = igdb.Client()
    rows = conn.execute("SELECT id, igdb_id FROM games WHERE igdb_id IS NOT NULL").fetchall()
    if only_missing:
        have = {r["game_id"] for r in conn.execute("SELECT DISTINCT game_id FROM game_media")}
        have |= {r["game_id"] for r in conn.execute("SELECT DISTINCT game_id FROM tags WHERE source='igdb'")}
        rows = [r for r in rows if r["id"] not in have]
    by_igdb = {}
    for r in rows:
        by_igdb.setdefault(r["igdb_id"], []).append(r["id"])
    ids = sorted(by_igdb)
    done, media, ntags = 0, 0, 0
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        body = f"fields {FIELDS}; where id = ({','.join(map(str, chunk))}); limit 500;"
        data = client.query("games", body)
        for g in data:
            for gid in by_igdb.get(g["id"], []):
                for seq, s in enumerate((g.get("screenshots") or [])[:6]):
                    if s.get("image_id"):
                        conn.execute("INSERT OR IGNORE INTO game_media(game_id,kind,image_id,seq) VALUES(?,?,?,?)",
                                     (gid, "screenshot", s["image_id"], seq))
                        media += 1
                for seq, s in enumerate((g.get("artworks") or [])[:2]):
                    if s.get("image_id"):
                        conn.execute("INSERT OR IGNORE INTO game_media(game_id,kind,image_id,seq) VALUES(?,?,?,?)",
                                     (gid, "artwork", s["image_id"], seq))
                names = []
                for field, kind in KINDS.items():
                    for item in g.get(field) or []:
                        if item.get("name"):
                            names.append((item["name"], kind))
                if g.get("franchise") and g["franchise"].get("name"):
                    names.append((g["franchise"]["name"], "franchise"))
                for name, kind in dict.fromkeys(names):
                    cur = conn.execute("INSERT OR IGNORE INTO tags(game_id,tag,kind,state,source) VALUES(?,?,?,?,?)",
                                       (gid, name, kind, "accepted", "igdb"))
                    ntags += cur.rowcount
                if g.get("similar_games"):
                    conn.execute("UPDATE games SET similar = ? WHERE id = ?", (json.dumps(g["similar_games"][:10]), gid)) \
                        if _has_column(conn, "games", "similar") else None
        conn.commit()
        done += len(chunk)
        if progress:
            progress(f"{done}/{len(ids)} games, {media} screenshots, {ntags} tags")
    return {"games": len(ids), "screenshots": media, "tags": ntags}


def _has_column(conn, table, col):
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def media_for(game_id):
    ensure()
    return [dict(r) for r in db.connect().execute(
        "SELECT kind, image_id, seq FROM game_media WHERE game_id=? ORDER BY kind, seq", (game_id,))]


def screenshot_path(image_id, size="t_screenshot_med"):
    """Local path for an IGDB image, downloading it the first time."""
    dest = os.path.join(screens_dir(), f"{size}_{image_id}.jpg")
    return igdb.fetch_image(image_id, size, dest)
