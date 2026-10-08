"""Audit _deleted with the round manifests: which dropped games does the store hold NO copy of, and
was each one a decision or an error?

Pass 1 (mechanical): every game file under _deleted\<system> is parsed (No-Intro name), classified by
the tag rules, normalised and matched against the store's games for that system (exact normalised
title, fuzzy >= 0.86, containment). Drops with a store match are "covered". Drops with no match that
are English and not demo/beta/proto/bad/alt/unl/pirate are ORPHAN candidates.

Pass 2 (reasoning): for each orphan title the round manifests (_deleted\rounds\*.tsv, _tools\rounds)
say who dropped every copy and why. The cited keeper ("duplicate of X", "kept on <system>",
"replaced by X", "chosen as the playable copy") is checked against the store:
    DECIDED   the keeper exists (another system, another region, a remake Matt chose): not a loss
    ERROR     the keeper is gone too, or the reason names a different game, or a "library reset /
              duplicate exists elsewhere" claim with no copy anywhere: a real loss
    UNKNOWN   no manifest line found (pre-manifest rounds)
For ERROR and UNKNOWN the best copy to restore is chosen: region rank Australia > USA/World >
Europe/UK > other, plain release over Virtual Console / LodgeNet / GameCube / collection dumps,
highest revision. Writes two TSVs and a summary; moves nothing.

  python _tools\deleted-audit.py [--out <tsv>]
"""
import os, re, sys, csv, glob, collections, difflib, argparse

sys.path.insert(0, r"D:\Games\ROM-Sync")
from romsync import db

ap = argparse.ArgumentParser(); ap.add_argument("--out", default=r"D:\Games\ROM-Sync\data\records\deleted-audit.tsv"); a = ap.parse_args()
OUT2 = a.out.replace(".tsv", "-orphans.tsv")
DEL = r"D:\Games\_deleted"
FOLDERS = {"gba": "gba", "gbc": "gbc", "mastersystem": "mastersystem", "n64": "n64", "NDS": "nds", "nes": "nes", "SNES": "snes",
           r"round22\Downloaded\Minerva_Myrient\Redump\Sony - PlayStation": "psx"}
GAME_EXT = {".zip", ".7z", ".nes", ".sfc", ".smc", ".gba", ".gb", ".gbc", ".sms", ".z64", ".n64", ".v64", ".nds", ".chd", ".cue", ".bin", ".iso"}

DROP_TAGS = re.compile(r"\((Demo|Beta|Proto|Sample|Kiosk|Wi-Fi Kiosk|Program|Aging|Test|Debug|Pirate|Unl|Promo|Trade Demo|Tech Demo|Competition Cart|Training|Possible Proto)[^)]*\)", re.I)
BAD = re.compile(r"\[b\]|\[b[^\]]*\]|\[h\]|\[o\]|\[t\]|\[f\]")
ALT = re.compile(r"\(Alt[^)]*\)")
REV = re.compile(r"\((?:Rev|v)\s*([0-9A-Za-z.]+)\)")
PAREN = re.compile(r"\(([^)]*)\)")
RERELEASE = re.compile(r"\((Virtual Console|LodgeNet|GameCube|Zelda Collection|Limited Run Games|Evercade|Switch Online|Classic Mini|Disney Classic Games|Castlevania [A-Za-z ]*Collection|Namco[^)]*|Aladdin Compact Cartridge|Sega 3D Classics|NP|Wii U Virtual Console|iQue)[^)]*\)", re.I)
ENGLISH = {"Australia", "World", "USA", "UK", "United Kingdom", "Europe", "Canada", "Ireland", "New Zealand"}
NON_ENGLISH = {"Japan", "Korea", "China", "Taiwan", "Asia", "Germany", "France", "Italy", "Spain", "Netherlands", "Scandinavia", "Russia",
               "Poland", "Sweden", "Norway", "Denmark", "Finland", "Brazil", "Portugal", "Greece", "Turkey", "Belgium", "Austria", "Switzerland",
               "Czech", "Hungary", "Latin America", "Mexico", "Argentina", "Israel", "Hong Kong", "Singapore", "India", "South Africa"}
RANK = {"Australia": 0, "World": 1, "USA": 1, "UK": 2, "United Kingdom": 2, "Europe": 2}
LANG_RE = re.compile(r"^[A-Z][a-z](,[A-Z][a-z](\+[A-Z][a-z])*)*$|^[A-Z][a-z]\+[A-Z][a-z]$")
ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}

# Regional renames: the same game under another name in the store (checked by hand 2026-09-16).
# key: (system, normalised deleted title) -> normalised kept title. Extend as new sets are processed.
RENAMES = {
    ("n64", "holymagiccentury"): "quest64", ("n64", "gaspfightersnextream"): "deadlyarts", ("n64", "tonyhawksskateboarding"): "tonyhawksproskater",
    ("n64", "nbapro98"): "nbainzone98", ("n64", "nbapro99"): "nbainzone99", ("n64", "nhlpro99"): "nhlbladesofsteel99",
    ("n64", "operationwinback"): "winbackcovertoperations", ("n64", "donaldduckquackattack"): "donaldduckgoinquackers",
    ("n64", "bustamove3dx"): "bustamove99", ("n64", "internationaltrackandfieldsummergames"): "internationaltrackandfield2000",
    ("n64", "fifa64"): "fifaroadtoworldcup98", ("n64", "starfox64"): "lylatwars", ("n64", "batmanoffuturereturnofjoker"): "batmanbeyondreturnofjoker",
    ("snes", "illusionoftime"): "illusionofgaia", ("snes", "kirbysfunpak"): "kirbysuperstar", ("snes", "kirbysghosttrap"): "kirbysavalanche",
    ("snes", "lufia"): "lufiaandfortressofdoom", ("snes", "superbckid"): "superbonk", ("snes", "unirally"): "uniracers", ("snes", "superaleste"): "spacemegaforce",
    ("snes", "superswiv"): "firepower2000", ("snes", "castlevaniavampireskiss"): "castlevaniadraculax", ("snes", "anotherworld"): "outofthisworld",
    ("snes", "blackhawk"): "blackthorne", ("snes", "agurisuzukif1superdriving"): "redlinef1racer", ("snes", "suzukiagurinof1superdriving"): "redlinef1racer",
    ("snes", "topracer"): "topgear", ("snes", "topracer2"): "topgear2", ("snes", "wildtrax"): "stuntracefx", ("snes", "pitfallmayanodaibouken"): "pitfallmayanadventure",
    ("snes", "takahashimeijinnodaiboukenjima"): "superadventureisland", ("snes", "krustyworld"): "krustyssuperfunhouse", ("snes", "humangrandprix"): "f1poleposition",
    ("snes", "nigelmansellindycar"): "nigelmansellsworldchampionshipracing", ("snes", "skymission"): "wings2aceshigh",
    ("snes", "superkickboxingbestofbest"): "bestofbestchampionshipkarate", ("snes", "simpsonsbartnofushiginayumenodaibouken"): "simpsonsbartsnightmare",
    ("snes", "zoolnoyumebouken"): "zoolninjaofnthdimension", ("snes", "barkleynopowerdunk"): "barkleyshutupandjam", ("snes", "crashdummydrzabuosukuidase"): "incrediblecrashdummies",
    ("snes", "raidendensetsu"): "raidentrad", ("snes", "tomtojerry"): "tomandjerry", ("snes", "puttymoon"): "superputty",
    ("snes", "looneytunesroadrunner"): "roadrunnersdeathvalleyrally", ("snes", "looneytunesroadrunnervswileecoyote"): "roadrunnersdeathvalleyrally",
    ("snes", "pinkpanther"): "pinkgoestohollywood", ("snes", "wizardry5saikanochuushin"): "wizardry5heartofmaelstrom", ("snes", "superpang"): "superbusterbros",
    ("snes", "tinytoonadventureswildandwackysports"): "tinytoonadventureswackysportschallenge", ("snes", "tetrisflash"): "tetris2",
    ("snes", "superedf"): "earthdefenseforce", ("snes", "chaosengine"): "soldiersoffortune", ("snes", "3jigenkakutouballz"): "ballz3d",
    ("snes", "gekitotsudanganjidoushakessenbattlemobile"): "battlemobile", ("snes", "tatakaegenshijin2rookienobouken"): "superbonk",
    ("gba", "contrahardspirits"): "contraadvancealienwarsex", ("gba", "gameandwatchgalleryadvance"): "gameandwatchgallery4",
    ("gba", "mariopowertennis"): "mariotennispowertour", ("gba", "ninjacop"): "ninjafiveo", ("gba", "supermarioball"): "mariopinballland",
    ("gba", "wariowareincminigamemania"): "wariowareincmegamicrogame", ("gba", "yugiohduelmonstersinternationalworldwideedition"): "yugiohworldwideeditionstairwaytodestinedduel",
    ("gba", "strawberryshortcakeicecreamislandridingcamp"): "strawberryshortcakesummertimeadventure",
    ("nes", "probotector2returnofevilforces"): "superc", ("nes", "teenagemutantheroturtles"): "teenagemutantninjaturtles",
    ("mastersystem", "mazewalker"): "mazehunter3d",
}

def parse(name):
    base = os.path.splitext(name)[0]
    title = base.split(" (")[0].split(" [")[0].strip()
    regions, langs = [], None
    for g in PAREN.findall(base):
        parts = [p.strip() for p in g.split(",")]
        if not regions and all(p in ENGLISH or p in NON_ENGLISH for p in parts): regions = parts
        elif langs is None and LANG_RE.match(g): langs = set(re.split(r"[,+]", g))
    m = REV.search(base)
    return title, regions, langs, (m.group(1) if m else "")

def norm(t):
    t = t.lower().replace("&", "and").replace("'", "")
    t = re.sub(r"\b(the|a|an)\b", " ", t)
    t = re.sub(r"\bpart\b", " ", t)
    words = [ROMAN.get(w, w) for w in re.sub(r"[^a-z0-9]+", " ", t).split()]
    return "".join(words)

def reason_for(name, regions, langs):
    if name.startswith("[BIOS]"): return "system file"
    if BAD.search(name): return "bad/hacked dump"
    m = DROP_TAGS.search(name)
    if m: return "tag: " + m.group(1).lower()
    if ALT.search(name): return "alternate dump"
    if not regions: return "no region tag"
    english = ("En" in langs) if langs is not None else any(r in ENGLISH for r in regions)
    if not english: return "not English"
    return "region/revision duplicate"

def rev_key(r):
    try: return float(re.sub(r"[^0-9.]", "", r) or 0)
    except ValueError: return 0

# ---- store index: system -> norm -> name ; and a global norm -> [(system, name)]
conn = db.connect()
store = collections.defaultdict(dict); store_any = collections.defaultdict(list)
for r in conn.execute("SELECT system, name, title FROM games"):
    k = norm(r["title"] or parse(r["name"])[0]); store[r["system"]][k] = r["name"]; store_any[k].append((r["system"], r["name"]))

def find(system, key):
    key = RENAMES.get((system, key), key)
    if key in store[system]: return store[system][key], "exact"
    close = difflib.get_close_matches(key, list(store[system].keys()), n=1, cutoff=0.86)
    if close: return store[system][close[0]], "fuzzy"
    cont = [k for k in store[system] if len(key) >= 6 and (key in k or k in key)]
    if cont: return store[system][cont[0]], "contains"
    return None, ""

# ---- manifests: file name -> [(round, reason)]
manifest = collections.defaultdict(list)
for mf in sorted(glob.glob(os.path.join(DEL, "rounds", "*.tsv")) + glob.glob(r"D:\Games\_tools\rounds\*.tsv")):
    rnd = os.path.splitext(os.path.basename(mf))[0]
    for line in open(mf, encoding="utf-8", errors="replace"):
        if line.startswith("#") or "\t" not in line: continue
        f = line.rstrip("\r\n").split("\t")
        manifest[os.path.basename(f[0])].append((rnd, f[2] if len(f) > 2 else ""))

def keeper_status(system, reasons, depth=0):
    """Look at every reason for a title's copies; decide DECIDED / ERROR / UNKNOWN with evidence.
    A keeper that is itself gone is followed through its own manifest lines (a decision on the keeper
    settles the title; a keeper lost by a later error is still an error)."""
    if not reasons: return "UNKNOWN", "no manifest line"
    ev = []
    for rnd, reason in reasons:
        m = re.search(r"kept on (\w+)", reason)
        if m:
            sys_ = m.group(1); t = re.search(r"'([^']+)'", reason)
            key = norm(t.group(1)) if t else None
            if key and store[sys_].get(key) or (key and find(sys_, key)[0]):
                return "DECIDED", f"{rnd}: kept on {sys_}"
            ev.append(f"{rnd}: says kept on {sys_} but it is not there")
        m = re.search(r"(?:duplicate of|replaced by (?:Australian release )?)\s*(.+?)(?:\.zip)?(?:\s*\(region ranking.*)?$", reason)
        if m and "already in ROMs" not in reason and "exists elsewhere" not in reason:
            kname = m.group(1).strip()
            kt = parse(kname + ".zip")[0]
            if norm(kt) != norm(parse(reasons[0][1] and kname + ".zip")[0]) and False: pass
            hit, how = find(system, norm(kt))
            if hit: return "DECIDED", f"{rnd}: superseded by {hit}"
            kfile = kname if kname.lower().endswith(".zip") else kname + ".zip"
            if depth < 3 and manifest.get(kfile):
                v, e = keeper_status(system, manifest[kfile], depth + 1)
                if v == "DECIDED": return "DECIDED", f"keeper {kname} -> {e}"
                ev.append(f"keeper '{kname}' -> {e}")
            else:
                ev.append(f"{rnd}: keeper '{kname}' is gone from the store")
            continue
        if "chosen as the playable copy" in reason or "requests" in rnd or "Matt" in reason or "not wanted" in reason or "not a game" in reason:
            return "DECIDED", f"{rnd}: {reason[:90]}"
        if "same game as" in reason or "under another name" in reason or "renamed duplicate" in reason:
            m2 = re.search(r"(?:same game as|renamed duplicate of) '?([^':]+?)'?(?:\.zip)?(?:'|:|$)", reason)
            if m2:
                hit, _ = find(system, norm(parse(m2.group(1).strip() + ".zip")[0]))
                if hit: return "DECIDED", f"{rnd}: same game as {hit}"
                ev.append(f"{rnd}: says same game as '{m2.group(1).strip()}', which is not in the store")
            else:
                ev.append(f"{rnd}: {reason[:80]} (name not stated; check by hand)")
            continue
        if "exists elsewhere" in reason or "already in ROMs" in reason:
            ev.append(f"{rnd}: claimed a duplicate elsewhere; none in the store now")
        if "cross-system" in reason and "kept on" not in reason:
            ev.append(f"{rnd}: {reason[:80]}")
    return ("ERROR", "; ".join(ev)) if ev else ("UNKNOWN", reasons[0][0] + ": " + reasons[0][1][:80])

# ---- every game file anywhere under _deleted (round-06/10 copies live outside the system folders)
ALL = collections.defaultdict(list)          # norm title -> [(path, name, rank, rerelease, rev)]
for root, ds, fs in os.walk(DEL):
    if os.path.basename(root) in ("rounds", "RomCurator", "covers") or "RomCurator" in root: continue
    for n in fs:
        if os.path.splitext(n)[1].lower() not in GAME_EXT: continue
        t, regions, langs, rev = parse(n)
        if reason_for(n, regions, langs) not in ("region/revision duplicate",): continue
        ALL[norm(t)].append((os.path.join(root, n), n, min((RANK.get(r, 3) for r in regions), default=3), bool(RERELEASE.search(n)), rev))

# ---- pass 1
rows = []
for folder, system in FOLDERS.items():
    root = os.path.join(DEL, folder)
    if not os.path.isdir(root): continue
    for n in sorted(os.listdir(root)):
        p = os.path.join(root, n)
        if os.path.isdir(p) or os.path.splitext(n)[1].lower() not in GAME_EXT: continue
        title, regions, langs, rev = parse(n)
        reason = reason_for(n, regions, langs)
        key = norm(title)
        match, how = find(system, key)
        status = "covered" if match else ("orphan" if reason == "region/revision duplicate" else "dropped-by-rule")
        rows.append(dict(system=system, file=n, title=title, key=key, regions="/".join(regions), rev=rev, reason=reason, status=status,
                         store_match=match or "", how=how, bytes=os.path.getsize(p), path=p,
                         rank=min((RANK.get(r, 3) for r in regions), default=3), rerelease=bool(RERELEASE.search(n))))

with open(a.out, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=[k for k in rows[0].keys() if k not in ("key",)], delimiter="\t", lineterminator="\n", extrasaction="ignore")
    w.writeheader(); w.writerows(rows)

# ---- pass 2: orphan titles
groups = collections.defaultdict(list)
for r in rows:
    if r["status"] == "orphan": groups[(r["system"], r["key"])].append(r)
verdicts = []
for (system, key), copies in sorted(groups.items()):
    reasons = [(rnd, rs) for c in copies for rnd, rs in manifest.get(c["file"], [])]
    verdict, evidence = keeper_status(system, reasons)
    elsewhere = [f"{s}: {n}" for s, n in store_any.get(key, []) if s != system]
    if verdict != "DECIDED" and elsewhere:
        verdict, evidence = "DECIDED", "same title kept on " + ", ".join(elsewhere)
    cands = ALL.get(key) or [(c["path"], c["file"], c["rank"], c["rerelease"], c["rev"]) for c in copies]
    bp, bn, _, _, _ = sorted(cands, key=lambda c: (c[3], c[2], -rev_key(c[4]), c[1]))[0]
    verdicts.append(dict(system=system, title=copies[0]["title"], verdict=verdict, evidence=evidence, copies=len(copies),
                         restore=bn, bytes=os.path.getsize(bp), path=bp))

with open(OUT2, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(verdicts[0].keys()), delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(verdicts)

by = collections.Counter((r["system"], r["status"]) for r in rows)
print(f"pass 1: audited {len(rows)} deleted game files -> {a.out}")
for s in sorted({r['system'] for r in rows}):
    print(f"  {s:<13} covered={by[(s,'covered')]:>5} dropped-by-rule={by[(s,'dropped-by-rule')]:>5} orphan-files={by[(s,'orphan')]:>4}")
vc = collections.Counter(v["verdict"] for v in verdicts)
print(f"\npass 2: {len(verdicts)} orphan titles -> {OUT2}: " + ", ".join(f"{k}={n}" for k, n in vc.items()))
for kind in ("ERROR", "UNKNOWN", "DECIDED"):
    print(f"\n{kind}:")
    for v in verdicts:
        if v["verdict"] == kind: print(f"  [{v['system']}] {v['restore']}  <- {v['evidence']}")
