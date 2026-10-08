"""Carries cover art and descriptions over from ROM Curator 1.

Only metadata moves: IGDB match, summary, dates, ratings, genres and the cached
cover file. Flags, device state and everything else in the old database are ignored.
"""
import os
import shutil
import sqlite3

from . import db

OLD_DIR = r"D:\Games\RomCurator\romcurator\data"


def import_metadata(old_dir=OLD_DIR):
    old_db = os.path.join(old_dir, "library.db")
    if not os.path.isfile(old_db):
        return {"error": f"not found: {old_db}"}
    src = sqlite3.connect(old_db)
    src.row_factory = sqlite3.Row
    rows = src.execute(
        "SELECT system, filename, scrape_state, confidence, igdb_id, name, summary, "
        "release_date, rating, rating_count, genres, cover_file FROM games "
        "WHERE scrape_state='matched'").fetchall()
    conn = db.connect()
    matched, covers = 0, 0
    cover_src = os.path.join(old_dir, "covers")
    cover_dst = os.path.join(db.data_dir(), "covers")
    for r in rows:
        cur = conn.execute(
            """UPDATE games SET scrape_state='matched', confidence=?, igdb_id=?, igdb_name=?,
                 summary=?, release_date=?, rating=?, rating_count=?, genres=?, cover_file=?
               WHERE system=? AND name=? AND scrape_state='pending'""",
            (r["confidence"], r["igdb_id"], r["name"], r["summary"], r["release_date"],
             r["rating"], r["rating_count"], r["genres"], r["cover_file"], r["system"], r["filename"]))
        if cur.rowcount:
            matched += cur.rowcount
            cf = r["cover_file"]
            if cf and os.path.isfile(os.path.join(cover_src, cf)) \
                    and not os.path.isfile(os.path.join(cover_dst, cf)):
                shutil.copy2(os.path.join(cover_src, cf), os.path.join(cover_dst, cf))
                covers += 1
    conn.commit()
    src.close()
    return {"old_matched_rows": len(rows), "applied": matched, "covers_copied": covers}
