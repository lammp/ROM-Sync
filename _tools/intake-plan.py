"""Intake plan: classify a completed No-Intro/Redump-style set in _torrents\\_complete
against the ROMs filtering policy (ROMs\\CLAUDE.md) and its Common Law precedents.
Writes a plan TSV and a summary; moves nothing.

  python intake-plan.py --src "<set folder>" --system nds [--ext zip]
      --src     folder holding the set's files (usually one per game)
      --system  the ROMs\\<system> folder the keepers go to
      --ext     extension(s) counted as games in the set, comma-separated (default: zip)
      --out     plan TSV (default _tools\\intake-<system>-plan.tsv)

Policy applied (see ROMs\\CLAUDE.md + memory: nds-uk-region-rank, highest-revision-wins,
alt-dumps-dropped, datel-minigames-unlicensed, no-intro-bios-entries-are-system-files):
  drop  [b] bad dumps; Demo/Beta/Proto/Sample/Kiosk/Program/Aging/Test/Debug/Promo/Pirate/Unl (anywhere in a tag);
        (Alt) alternate dumps; not English; lower-ranked region duplicates; lower revisions
  keep  one per title: Australia > USA/World > Europe = United Kingdom > other English
  bios  [BIOS] entries are system files -> _firmware, never the system folder
"""
import os, re, sys, csv, collections, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True); ap.add_argument("--system", required=True)
ap.add_argument("--ext", default="zip"); ap.add_argument("--out", default="")
a = ap.parse_args()
SRC = a.src; DST = os.path.join(r"D:\Games\ROMs", a.system)
EXTS = tuple("." + e.strip().lower().lstrip(".") for e in a.ext.split(","))
OUT = a.out or os.path.join(r"D:\Games\_tools", f"intake-{a.system}-plan.tsv")
SUMMARY = OUT.replace("-plan.tsv", "-summary.txt")

# Tag words match anywhere inside a paren group (deleted-audit lesson: "(Auto Demo)" and "(Possible Proto)"
# were kept as keepers, then dropped later as demos, orphaning Moonwalker and Tiger-Heli).
DROP_TAGS = re.compile(r"\([^)]*\b(Demo|Beta|Proto|Prototype|Sample|Kiosk|Program|Aging|Test|Debug|Pirate|Unl|Promo)\b[^)]*\)", re.I)
BAD = re.compile(r"\[b\]|\[b[^\]]*\]")
ALT = re.compile(r"\(Alt[^)]*\)")
REV = re.compile(r"\((?:Rev|v)\s*([0-9A-Za-z.]+)\)")
PAREN = re.compile(r"\(([^)]*)\)")
REGION_RANK = {"Australia": 0, "World": 1, "USA": 1, "UK": 2, "United Kingdom": 2, "Europe": 2}
ENGLISH_REGIONS = {"Australia", "World", "USA", "UK", "United Kingdom", "Europe", "Canada", "Ireland", "New Zealand"}
NON_ENGLISH_REGIONS = {"Japan", "Korea", "China", "Taiwan", "Asia", "Germany", "France", "Italy", "Spain", "Netherlands",
                       "Scandinavia", "Russia", "Poland", "Sweden", "Norway", "Denmark", "Finland", "Brazil", "Portugal",
                       "Greece", "Turkey", "Belgium", "Austria", "Switzerland", "Czech", "Hungary", "Latin America", "Mexico",
                       "Argentina", "Israel", "Hong Kong", "Singapore", "India", "South Africa"}
LANG_RE = re.compile(r"^[A-Z][a-z](?:[,+][A-Z][a-z])*$")   # (En) (En,Fr) (En+En,Es) - '+' separates the games of a multi-game cart

def is_english(langs, regions):
    """A language tag decides when present: every '+'-separated game on the cart must list En.
    Without a tag, an English region decides (United Kingdom counts - the old filter dropped TG Rally 2)."""
    if langs is None: return any(r in ENGLISH_REGIONS for r in regions)
    return all("En" in seg.split(",") for seg in langs.split("+"))

def parse(name):
    base = os.path.splitext(name)[0]
    title = base.split(" (")[0].strip()
    regions, langs = [], None
    for g in PAREN.findall(base):
        parts = [p.strip() for p in g.split(",")]
        if not regions and all(p in ENGLISH_REGIONS or p in NON_ENGLISH_REGIONS for p in parts): regions = parts
        elif langs is None and LANG_RE.match(g): langs = g
    rev = REV.search(base)
    return title, regions, langs, (rev.group(1) if rev else "")

ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}

# Stylised spellings that a title strip would otherwise turn into a different key: Ac!d -> acid,
# Ac!d^2 -> acid2 (deleted-audit round 29: four Metal Gear files were two games, kept twice).
LEET = {"!": "i", "@": "a", "$": "s", "^": "", "0": "o", "1": "l"}

def norm_title(t):
    """Normalised title for dedupe. Numerals are kept distinct (I & II is not III), roman numerals
    become arabic so 'Part II' and '2' meet, articles drop, and stylised letters are folded back."""
    t = t.lower().replace("&", "and").replace("'", "")
    t = "".join(LEET.get(ch, ch) if not ch.isalnum() or ch in "!@$^" else ch for ch in t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return "".join(ROMAN.get(w, w) for w in t.split() if w not in ("the", "a", "an", "part"))

def rev_key(r):
    if not r: return (0,)
    try: return (1, float(re.sub(r"[^0-9.]", "", r) or 0))
    except ValueError: return (1, 0)

rows = []
for name in sorted(os.listdir(SRC)):
    if not name.lower().endswith(EXTS): continue
    path = os.path.join(SRC, name); size = os.path.getsize(path)
    title, regions, langs, rev = parse(name)
    reason = None; action = "keep"
    if name.startswith("[BIOS]"): action, reason = "bios", "system file -> _firmware"
    elif BAD.search(name): reason = "bad dump [b]"
    elif DROP_TAGS.search(name): reason = "tag: " + DROP_TAGS.search(name).group(1).lower()
    elif ALT.search(name): reason = "alternate dump (Alt)"
    elif not regions: reason = "no region tag"
    else:
        english = is_english(langs, regions)
        if not english: reason = "not English"
    if reason and action == "keep": action = "drop"
    rank = min((REGION_RANK.get(r, 3) for r in regions), default=3) if action == "keep" else 9
    rows.append(dict(name=name, path=path, bytes=size, title=title, regions="/".join(regions), rank=rank, rev=rev, action=action, reason=reason or ""))

by_title = collections.defaultdict(list)
for r in rows:
    if r["action"] == "keep": by_title[norm_title(r["title"])].append(r)
for t, cands in by_title.items():
    cands.sort(key=lambda r: (r["rank"], tuple(-x for x in rev_key(r["rev"])), -r["name"].count(","), r["name"]))
    best = cands[0]
    for r in cands[1:]:
        r["action"] = "drop"; r["reason"] = f"duplicate of keeper ({best['regions']}{' Rev ' + best['rev'] if best['rev'] else ''})"

keep_titles = {norm_title(r["title"]) for r in rows if r["action"] == "keep"}

# Orphan guard (deleted-audit lesson, 2026-09-16): a drop must leave the game somewhere. Any "duplicate"
# or "no region" drop whose title has no keeper in this set and no copy in the store (same system, by
# normalised title from the ROM-Sync database) is flagged orphan-drop for review. "not English" drops are
# not guarded: the policy removes them even when no English edition exists, and localised titles
# (Findet Nemo) never match an English keeper by name.
try:
    import sqlite3
    _db = sqlite3.connect(r"D:\Games\ROM-Sync\data\romsync.db")
    store_titles = {norm_title(t or n.split(" (")[0]) for n, t in _db.execute("SELECT name, title FROM games WHERE system=?", (a.system,))}
except Exception:
    store_titles = set()
orphan_drops = []
for r in rows:
    if r["action"] == "drop" and (r["reason"].startswith("duplicate") or r["reason"] == "no region tag"):
        k = norm_title(r["title"])
        if k not in keep_titles and k not in store_titles:
            r["reason"] += " | ORPHAN-DROP: no keeper in set or store, review"
            orphan_drops.append(r)
superseded, unmatched_loose, collisions = [], [], []
if os.path.isdir(DST):
    for f in sorted(os.listdir(DST)):
        if f in ("systeminfo.txt", "CLAUDE.md") or f.startswith("_") or f.startswith("[BIOS]"): continue
        if f.lower().endswith(EXTS):
            if any(r["action"] == "keep" and r["name"] == f for r in rows): collisions.append(f)
            continue
        t, _, _, _ = parse(f)
        (superseded if norm_title(t) in keep_titles else unmatched_loose).append(f)

with open(OUT, "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t", lineterminator="\n")
    w.writerow(["action", "reason", "title", "regions", "rev", "bytes", "path"])
    for r in rows: w.writerow([r["action"], r["reason"], r["title"], r["regions"], r["rev"], r["bytes"], r["path"]])
    for f in superseded: p = os.path.join(DST, f); w.writerow(["recycle-loose", "superseded by verified keeper", parse(f)[0], "", "", os.path.getsize(p), p])

keep = [r for r in rows if r["action"] == "keep"]; drop = [r for r in rows if r["action"] == "drop"]; bios = [r for r in rows if r["action"] == "bios"]
gb = lambda rs: round(sum(r["bytes"] for r in rs) / 1e9, 1)
reasons = collections.Counter(re.sub(r" \(.*", "", r["reason"]) for r in drop)
lines = [f"set: {SRC}", f"source files: {len(rows)}  ({gb(rows)} GB)",
         f"KEEP: {len(keep)}  ({gb(keep)} GB)  -> move to {DST}",
         f"BIOS: {len(bios)}  -> move to _firmware", f"DROP: {len(drop)}  ({gb(drop)} GB)  -> recycle", ""]
lines += [f"  {c:5d}  {k}" for k, c in reasons.most_common()]
lines += ["", "keepers by region: " + ", ".join(f"{k}={v}" for k, v in sorted(collections.Counter(r['regions'] for r in keep).items(), key=lambda kv: -kv[1])[:8]),
          f"loose files in {DST} superseded by a keeper: {len(superseded)}  (recycle)",
          f"loose files with no match (stay, review): {len(unmatched_loose)}", *["    " + f for f in unmatched_loose],
          f"name collisions in {DST}: {len(collisions)}", *["    " + f for f in collisions],
          f"ORPHAN-DROPS (dropped, yet no copy of the game would remain; review before recycling): {len(orphan_drops)}",
          *["    " + r["name"] + "  <- " + r["reason"].split(" | ")[0] for r in orphan_drops[:60]],
          "", "sample keepers:", *["    " + r["name"] for r in keep[:10]],
          "", "sample 'not English' drops:", *["    " + r["name"] for r in drop if r["reason"] == "not English"][:6],
          "", "sample duplicate drops:", *["    " + r["name"] + "  <- " + r["reason"] for r in drop if r["reason"].startswith("duplicate")][:6],
          "", "unlicensed / no-region (check by eye):", *["    " + r["name"] for r in drop if r["reason"] in ("tag: unl", "no region tag")][:20]]
open(SUMMARY, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
