"""Building IGDB queries (F5-S6).

IGDB's query language has no documented escape inside a quoted string, so a
title is made safe by removal rather than escaping: a double quote, a
backslash and any control character are dropped. What is left can only be
text inside the query's one quoted string; it cannot close the string, so it
cannot add a clause.
"""

from __future__ import annotations

import re

FIELDS = (
    "name,summary,storyline,first_release_date,total_rating,total_rating_count,"
    "rating,rating_count,genres.name,themes.name,cover.image_id,platforms,"
    "alternative_names.name"
)
LIMIT = 10

_UNSAFE = re.compile(r'["\\\x00-\x1f\x7f]')
_SLUG = re.compile(r"[^a-z0-9-]+")


def safe_text(title: str) -> str:
    return _UNSAFE.sub("", title).strip()


def search(text: str, platform_id: int | None) -> str:
    where = f"where platforms = ({int(platform_id)}); " if platform_id else ""
    return f'search "{safe_text(text)}"; fields {FIELDS}; {where}limit {LIMIT};'


def by_id(igdb_id: int) -> str:
    return f"fields {FIELDS}; where id = {int(igdb_id)};"


def slug(ref: str) -> str:
    return _SLUG.sub("-", ref.lower()).strip("-")


def by_slug(ref: str) -> str:
    return f'fields {FIELDS}; where slug = "{slug(ref)}";'


PLATFORMS = "fields id,name,alternative_name; limit 500;"
