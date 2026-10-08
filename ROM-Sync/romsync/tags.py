"""Tags on games beyond what IGDB's genre list gives.

    kind     genre | franchise | theme | suggested | user
    state    accepted | proposed | rejected

IGDB genres are not stored here (they live on the game row). Linked tags that
a reasoning pass proposes arrive as state=proposed and become accepted only
when Matt says so in the UI.
"""
from . import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS tags (
    game_id  INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    tag      TEXT NOT NULL,
    kind     TEXT NOT NULL DEFAULT 'user',
    state    TEXT NOT NULL DEFAULT 'accepted',
    source   TEXT,
    PRIMARY KEY (game_id, tag, kind)
);
CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
"""


def ensure():
    conn = db.connect()
    conn.executescript(SCHEMA)
    conn.commit()


def for_all():
    """{game_id: [{tag, kind, state}]} for every game with tags."""
    ensure()
    out = {}
    for r in db.connect().execute("SELECT game_id, tag, kind, state FROM tags WHERE state != 'rejected'"):
        out.setdefault(r["game_id"], []).append({"tag": r["tag"], "kind": r["kind"], "state": r["state"]})
    return out


def set_tag(game_id, tag, kind="user", state="accepted", source=None):
    ensure()
    conn = db.connect()
    conn.execute("INSERT OR REPLACE INTO tags(game_id, tag, kind, state, source) VALUES(?,?,?,?,?)",
                 (game_id, tag.strip(), kind, state, source))
    conn.commit()


def remove(game_id, tag, kind=None):
    ensure()
    conn = db.connect()
    if kind:
        conn.execute("DELETE FROM tags WHERE game_id=? AND tag=? AND kind=?", (game_id, tag, kind))
    else:
        conn.execute("DELETE FROM tags WHERE game_id=? AND tag=?", (game_id, tag))
    conn.commit()


def decide(game_id, tag, accept):
    """Accept or reject a proposed tag."""
    ensure()
    conn = db.connect()
    conn.execute("UPDATE tags SET state=? WHERE game_id=? AND tag=?",
                 ("accepted" if accept else "rejected", game_id, tag))
    conn.commit()


def import_proposals(rows, source):
    """rows: [{game_id, tag, kind}] from a reasoning pass. Existing decisions are kept."""
    ensure()
    conn = db.connect()
    n = 0
    for r in rows:
        cur = conn.execute("INSERT OR IGNORE INTO tags(game_id, tag, kind, state, source) VALUES(?,?,?,?,?)",
                           (r["game_id"], r["tag"].strip(), r.get("kind", "suggested"), "proposed", source))
        n += cur.rowcount
    conn.commit()
    return n
