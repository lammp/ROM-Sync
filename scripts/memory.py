r"""Repository Memory — the single point of contact for the Common Law layer.

Implements the Legal Framework (see the root CLAUDE.md): Constitution (root
CLAUDE.md) -> Legislation (per-directory CLAUDE.md) -> Common Law (memory/ —
accumulated experience as ATOMIC facts, consulted at Ambiguity Events when
Legislation is unclear). Conceptually the facts are the project's Issues,
Learnings, and Resolutions; mechanically they carry the fixed tag taxonomy
below (issue / fix / preference / example / verification / knowledge).

Every fact file follows the OKF standard — One Key Fact:
  * exactly ONE atomic fact per file: a single sentence, <= 240 chars,
    present tense, specific (the CRUD tool enforces the mechanical parts);
  * schema'd frontmatter: id, tags (from the fixed taxonomy), keywords,
    scope, status, dates, provenance, checked;
  * optional short "## Context" (<= 10 lines) for how-to-apply detail.

A fact is one of two kinds, and the kind decides how it reaches a decision:

  * a CASE — an issue and, when one is found, the resolution that closes it.
    Retrieved by SEARCH, from a symptom, mid-investigation. A `fix` names the
    issue it closes via `resolves:`; an issue no fix names is an OPEN case, and
    open cases are rendered in the index rather than waiting to be searched for.
  * a PRECEDENT — a fine-tuned reading of a rule in a CLAUDE.md. Retrieved
    DETERMINISTICALLY via `rule:`, because by the time you would think to search
    for an interpretation you have already read the rule and formed your own.
    Precedent is pushed by the index and the SessionStart hook, never pulled.

Every fact also carries its PROVENANCE — how it is known — because the tier
governs what may be done with it, and a tier buried in prose can be neither
filtered, linted, nor aged:

  observed     ran it, saw the result
  documented   the vendor's documentation says so, untested
  contractual  authoritative vendor statement outside the documentation
               (entitlement, commercial terms, support-channel guidance);
               REQUIRES `source:` naming who stated it and when
  unverified   inference, no backing — the default, and an honest one

`checked:` is the date the fact was last confirmed true, which on continuously
released software is what decides whether it can still be relied on.

ALL memory changes go through this tool — it validates the schema BEFORE any
write lands, and regenerates the MEMORY.md index atomically, so the index and
the OKF standard cannot drift. `lint` is the enforcement gate: run it before
committing (Constitution pre-commit ritual) and in any CI. Errors block; the
WARNINGS block reports what the standard asks for but cannot mechanically
compel, and never fails the gate on its own.

Usage:
  python scripts/memory.py create --id <kebab-id> --tags preference \
      --keywords k1,k2 --scope repo --provenance observed \
      --fact "<one sentence, <=240 chars, ends with a full stop>" \
      [--context "..."] [--checked YYYY-MM-DD] [--source "..."] \
      [--resolves <issue-id>] [--rule constitution#law-2]
  python scripts/memory.py search "<keywords>" [--tags fix] [--scope <unit>]
      [--provenance observed] [--rule <rule>] [--top 5]
  python scripts/memory.py read <id> | update <id> ... | supersede <id> [--by <id>] | delete <id>
  python scripts/memory.py lint | reindex | list
  python scripts/memory.py audit [--stale-days 90]   # open cases, stale claims
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import itertools
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MEMORY_DIR = REPO / "memory"
INDEX = REPO / "MEMORY.md"
# Usage telemetry, not content: how the corpus is being queried. Local and
# gitignored — it records what was asked of memory in this working copy, which
# is a private working record and not part of the shareable Common Law.
QUERY_LOG = REPO / ".memory-log" / "queries.jsonl"

# ---------------------------------------------------------------------------
# PER-PROJECT CONFIG — set by the legal-framework scaffold; everything else in
# this file is fixed machinery, identical across installations.
#
# SCOPES: "repo" + one scope per Legislation unit (+ "docs" if the project
#         keeps governed docs). Must track the Legislation index in CLAUDE.md.
# PRIVACY_MARKERS: lowercase substrings that must never appear in committed
#         memory (repo memory is shareable by design). A floor, not a scanner.
SCOPES = ("repo", "roms", "rom-sync", "torrents", "firmware", "tools")
# Generic markers ship with the framework. Personal identifiers (an account
# name, an email domain, a machine name) are read from the local terms file,
# which is excluded from the repository: a literal here would be published by
# the very file meant to keep it private. Missing file means generic only.
_BASE_PRIVACY_MARKERS = ("prod.keys", "title.keys", "client_secret",
                         "password", "api key", "api_key", "secret", "token")


def _local_privacy_terms():
    path = REPO / "_tools" / "repo-lint.local.txt"
    try:
        with open(path, encoding="utf-8") as fh:
            return tuple(ln.strip().lower() for ln in fh
                         if ln.strip() and not ln.startswith("#"))
    except OSError:
        return ()


PRIVACY_MARKERS = _BASE_PRIVACY_MARKERS + _local_privacy_terms()
# STALE_DAYS: how long an `observed` claim stays trustworthy without re-checking.
#         Tune to the release cadence of whatever the project observes —
#         continuously released SaaS ages faster than a versioned product.
STALE_DAYS = 120
# ---------------------------------------------------------------------------

# Framework version of this installation. Read by the legal-framework skill's
# Upgrade mode to decide which migrations to apply. Bump only via that skill.
FRAMEWORK_VERSION = "1.4.0"

TAGS = ("verification", "issue", "fix", "preference", "example", "knowledge")
STATUSES = ("active", "superseded")
# Provenance tiers, ordered weakest to strongest claim on reality. The tier is
# defined by WHERE THE AUTHORITY SITS, never by the subject matter: a claim the
# documentation does not sanction can never be `documented`, however
# authoritative the person who stated it.
PROVENANCE = ("unverified", "documented", "contractual", "observed")
# The tier that may not stand alone. An unattributed `contractual` claim is
# `unverified` wearing a better label, so the gate demands a named source.
PROVENANCE_NEEDS_SOURCE = ("contractual",)
# Tiers that decay: a claim about how something BEHAVES goes stale as the thing
# changes. `unverified` never goes stale because it was never fresh.
PROVENANCE_PERISHABLE = ("observed", "documented")
FACT_MAX = 240
CONTEXT_MAX_LINES = 10
SOURCE_MAX = 200
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A rule reference: the unit whose CLAUDE.md carries it, optionally a fragment
# naming the specific rule — "constitution", "constitution#law-2", "agents#retrieval".
RULE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*(#[a-z0-9]+(-[a-z0-9]+)*)?$")
# The unit half of a rule reference must be a real Legislation unit. "constitution"
# is accepted alongside the scopes because the root CLAUDE.md is not a scope.
RULE_UNITS = ("constitution",) + SCOPES


class OkfError(Exception):
    pass


# ---------------------------------------------------------------- parsing

def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise OkfError(f"{path.name}: missing frontmatter block")
    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2).strip()
    if "\n## Context\n" in "\n" + body:
        fact, _, context = ("\n" + body).partition("\n## Context\n")
        fact, context = fact.strip(), context.strip()
    else:
        fact, context = body, ""
    return {"meta": meta, "fact": fact, "context": context, "path": path}


def validate(doc: dict) -> list[str]:
    """The OKF gate. Returns violations (empty = compliant)."""
    errs: list[str] = []
    meta, fact, context = doc["meta"], doc["fact"], doc["context"]
    name = doc["path"].name

    fid = meta.get("id", "")
    if not ID_RE.match(str(fid)):
        errs.append(f"{name}: id must be kebab-case, got {fid!r}")
    if doc["path"].stem != fid:
        errs.append(f"{name}: filename must equal id ({fid!r})")
    tags = meta.get("tags") or []
    if not tags or not all(t in TAGS for t in tags):
        errs.append(f"{name}: tags must be non-empty, from {TAGS}")
    kws = meta.get("keywords") or []
    if not kws or not all(isinstance(k, str) and k.strip() for k in kws):
        errs.append(f"{name}: keywords must be a non-empty string list")
    if meta.get("scope") not in SCOPES:
        errs.append(f"{name}: scope must be one of {SCOPES}")
    if meta.get("status") not in STATUSES:
        errs.append(f"{name}: status must be one of {STATUSES}")
    for k in ("created", "updated"):
        if not DATE_RE.match(str(meta.get(k, ""))):
            errs.append(f"{name}: {k} must be YYYY-MM-DD")

    # --- provenance: how the fact is known, and what that permits -----------
    prov = meta.get("provenance")
    if prov not in PROVENANCE:
        errs.append(f"{name}: provenance must be one of {PROVENANCE}, got {prov!r}")
    src = str(meta.get("source") or "").strip()
    if prov in PROVENANCE_NEEDS_SOURCE and not src:
        errs.append(f"{name}: provenance {prov!r} requires source naming who "
                    "stated it and when — an unattributed claim at this tier "
                    "is 'unverified' wearing a better label")
    # A placeholder is not an attribution. Left unchecked it would satisfy the
    # gate while leaving the claim exactly as unsourced as before, which is the
    # failure the source requirement exists to prevent.
    if src and re.match(r"^(todo|tbc|tbd|fixme|xxx)\b", src, re.I):
        errs.append(f"{name}: source is still a placeholder ({src!r}) — name the "
                    "person or channel and the date, or drop the tier to "
                    "'unverified'")
    if src and prov not in PROVENANCE_NEEDS_SOURCE and prov != "documented":
        errs.append(f"{name}: source is meaningful only on "
                    f"{PROVENANCE_NEEDS_SOURCE + ('documented',)}, not {prov!r}")
    if len(src) > SOURCE_MAX:
        errs.append(f"{name}: source exceeds {SOURCE_MAX} chars ({len(src)})")
    if not DATE_RE.match(str(meta.get("checked", ""))):
        errs.append(f"{name}: checked must be YYYY-MM-DD (the date the fact was "
                    "last confirmed true, not the date the file was edited)")

    # --- the two kinds: a case's resolution link, a precedent's rule --------
    res = meta.get("resolves")
    if res is not None:
        if not ID_RE.match(str(res)):
            errs.append(f"{name}: resolves must be a kebab-case fact id, got {res!r}")
        elif "fix" not in tags:
            errs.append(f"{name}: only a 'fix' resolves an issue; this fact is "
                        f"tagged {tags} — retag it or drop resolves")
        elif str(res) == str(fid):
            errs.append(f"{name}: resolves must not point at itself")
    rule = meta.get("rule")
    if rule is not None:
        if not RULE_RE.match(str(rule)):
            errs.append(f"{name}: rule must be <unit>[#<rule-name>], "
                        f"got {rule!r}")
        elif str(rule).split("#")[0] not in RULE_UNITS:
            errs.append(f"{name}: rule names unit "
                        f"{str(rule).split('#')[0]!r}, which is not one of "
                        f"{RULE_UNITS}")

    # the One Key Fact: a single short sentence
    if not fact:
        errs.append(f"{name}: missing the key fact")
    else:
        if len(fact) > FACT_MAX:
            errs.append(f"{name}: fact exceeds {FACT_MAX} chars ({len(fact)})")
        if "\n" in fact:
            errs.append(f"{name}: fact must be a single line")
        if not fact.endswith((".", "!", ")")):
            errs.append(f"{name}: fact must end with a full stop")
        if re.search(r"\.\s+[A-Z0-9]", fact):
            errs.append(f"{name}: fact must be ONE sentence (split extras "
                        "into their own facts or Context)")
    if context and len(context.splitlines()) > CONTEXT_MAX_LINES:
        errs.append(f"{name}: Context exceeds {CONTEXT_MAX_LINES} lines")
    # privacy floor: no obvious personal/secret markers in committed memory
    lowered = (fact + " " + context).lower()
    for marker in PRIVACY_MARKERS:
        if marker in lowered:
            errs.append(f"{name}: possible personal/secret content ({marker!r})"
                        " — repo memory must stay shareable")
    return errs


def load_all() -> list[dict]:
    if not MEMORY_DIR.exists():
        return []
    docs = []
    for p in sorted(MEMORY_DIR.glob("*.md")):
        docs.append(parse(p))
    return docs


def active(docs: list[dict]) -> list[dict]:
    return [d for d in docs if d["meta"].get("status") == "active"]


def days_since(iso: str, today: date | None = None) -> int:
    """Whole days between an ISO date and today; -1 when unparseable."""
    try:
        y, m, dd = (int(x) for x in str(iso).split("-"))
        return ((today or date.today()) - date(y, m, dd)).days
    except Exception:
        return -1


def open_cases(docs: list[dict]) -> list[dict]:
    """Issues no fix claims to resolve.

    Derived, never stored: the `fix` names the issue it closes, so "open" has
    exactly one owner and cannot drift out of step with a second state field.
    """
    closed = {str(d["meta"]["resolves"]) for d in active(docs)
              if d["meta"].get("resolves")}
    return [d for d in active(docs)
            if "issue" in d["meta"].get("tags", []) and d["meta"]["id"] not in closed]


def precedents(docs: list[dict]) -> list[dict]:
    return [d for d in active(docs) if d["meta"].get("rule")]


def lint_all(docs: list[dict] | None = None) -> list[str]:
    docs = docs if docs is not None else load_all()
    errs: list[str] = []
    seen: dict[str, str] = {}
    for d in docs:
        errs += validate(d)
        fid = str(d["meta"].get("id"))
        if fid in seen:
            errs.append(f"duplicate id {fid!r} in {seen[fid]} and {d['path'].name}")
        seen[fid] = d["path"].name
    # cross-file: a resolution must point at an issue that actually exists
    by_id = {str(d["meta"].get("id")): d for d in docs}
    for d in docs:
        res = d["meta"].get("resolves")
        if not res:
            continue
        target = by_id.get(str(res))
        if target is None:
            errs.append(f"{d['path'].name}: resolves {res!r}, which is not a "
                        "fact in this repository")
        elif "issue" not in target["meta"].get("tags", []):
            errs.append(f"{d['path'].name}: resolves {res!r}, which is tagged "
                        f"{target['meta'].get('tags')} — a resolution closes an "
                        "'issue'")
    # index freshness
    if docs and INDEX.exists() and render_index(docs) != INDEX.read_text(encoding="utf-8"):
        errs.append("MEMORY.md is stale — run: python scripts/memory.py reindex")
    return errs


def lint_warnings(docs: list[dict] | None = None,
                  stale_days: int = STALE_DAYS) -> list[str]:
    """What the standard asks for but cannot mechanically compel.

    Reported, never fatal. These are judgement calls: a missing open question
    might be an oversight or a fact that genuinely has none, and a stale claim
    is a prompt to re-run, not a defect. Making them errors would either block
    honest work or train the author to satisfy the gate rather than the intent.
    """
    docs = docs if docs is not None else load_all()
    warns: list[str] = []
    for d in sorted(active(docs), key=lambda x: x["meta"]["id"]):
        meta, name = d["meta"], d["path"].name
        # A discrepancy carrying no open question names nothing to exclude next.
        if "issue" in meta.get("tags", []) and not d["context"]:
            warns.append(f"{name}: issue has no Context — no open question is "
                         "recorded (what has not yet been excluded?)")
        age = days_since(meta.get("checked", ""))
        if meta.get("provenance") in PROVENANCE_PERISHABLE and age > stale_days:
            warns.append(f"{name}: {meta['provenance']} claim last checked "
                         f"{meta.get('checked')} ({age}d ago, limit {stale_days}d)"
                         " — re-confirm or downgrade it")
    return warns


# ---------------------------------------------------------------- writing

def compose(meta: dict, fact: str, context: str) -> str:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    body = fact if not context else f"{fact}\n\n## Context\n{context}"
    return f"---\n{fm}\n---\n{body}\n"


def write_fact(meta: dict, fact: str, context: str) -> Path:
    """Validate-then-write: a non-compliant fact never lands on disk."""
    path = MEMORY_DIR / f"{meta['id']}.md"
    candidate = {"meta": meta, "fact": fact.strip(),
                 "context": context.strip(), "path": path}
    errs = validate(candidate)
    if errs:
        raise OkfError("OKF violation(s):\n  " + "\n  ".join(errs))
    MEMORY_DIR.mkdir(exist_ok=True)
    path.write_text(compose(meta, fact.strip(), context.strip()),
                    encoding="utf-8")
    reindex()
    return path


def _row(d: dict) -> str:
    meta = d["meta"]
    tags = ",".join(meta.get("tags", []))
    prov = meta.get("provenance", "?")
    return f"- **{meta['id']}** [{tags}·{prov}] — {d['fact']}"


def render_index(docs: list[dict]) -> str:
    """The index, ordered by the question a reader arrives with.

    Scope answers "where does this live", which is the one thing nobody needs at
    the moment of decision. Precedent and open cases come first because they are
    the two things that must be seen WITHOUT being searched for: an interpretation
    you had to look up arrived too late, and an open case nobody re-reads is a
    question that quietly stops being asked.
    """
    lines = [
        "# Repository Memory — Common Law index",
        "",
        "<!-- GENERATED by scripts/memory.py — DO NOT EDIT BY HAND. -->",
        "<!-- All memory CRUD goes through scripts/memory.py (the OKF gate). -->",
        "",
        "One Key Fact per file under `memory/`. Consult at **Ambiguity",
        "Events** — when the Legislation (directory CLAUDE.md) doesn't answer,",
        "query before guessing, and query with KEYWORDS rather than the",
        "sentence you were asked:",
        "",
        "    python scripts/memory.py search \"<keywords>\" [--tags fix] [--scope <unit>]",
        "",
        "Each entry reads `id [tags·provenance] — fact`. Provenance is how the",
        "fact is known, and it governs what may be done with it: `observed` was",
        "run and seen, `documented` is claimed but untested, `contractual` is an",
        "authoritative statement made outside the documentation, `unverified` is",
        "inference. Never read one tier as another.",
        "",
    ]
    act = active(docs)
    superseded = [d for d in docs if d["meta"].get("status") != "active"]

    # The two decision-axis sections are INDEXES, not copies. Every fact is
    # written out exactly once, under its scope; these sections carry ids only.
    # Rendering them in full doubled the file for the ~45% of facts that appear
    # in one, which taxes every reader to serve two lookups.
    # --- Precedent: pushed, not pulled -------------------------------------
    prec = precedents(docs)
    if prec:
        lines += ["## Precedent — settled readings of a rule", "",
                  "How a rule in a CLAUDE.md has been read before. Consult when",
                  "applying the rule; do not re-litigate a settled reading. Full",
                  "text below, under each fact's scope.", ""]
        byrule: dict[str, list[dict]] = {}
        for d in sorted(prec, key=lambda x: (str(x["meta"]["rule"]), x["meta"]["id"])):
            byrule.setdefault(str(d["meta"]["rule"]), []).append(d)
        for rule, rows in byrule.items():
            lines.append(f"- **{rule}** — " + ", ".join(d["meta"]["id"] for d in rows))
        lines.append("")

    # --- Open cases: the questions still owed an answer ---------------------
    op = open_cases(docs)
    if op:
        lines += [f"## Open cases — {len(op)} issue(s) with no recorded resolution", "",
                  "An issue no `fix` names via `resolves:`. Either the resolution",
                  "has not been found yet, or it was found and never linked —",
                  "check before re-investigating from scratch.", "",
                  "    python scripts/memory.py search \"<keywords>\" --open", ""]
        for d in sorted(op, key=lambda x: (x["meta"]["scope"], x["meta"]["id"])):
            lines.append(f"- {d['meta']['id']} ({d['meta']['scope']})")
        lines.append("")

    # --- Everything, by scope ----------------------------------------------
    lines += ["## All facts by scope", ""]
    for scope in SCOPES:
        rows = [d for d in act if d["meta"].get("scope") == scope]
        if not rows:
            continue
        lines.append(f"### {scope}")
        lines += [_row(d) for d in rows]
        lines.append("")
    if superseded:
        lines.append(f"_{len(superseded)} superseded fact(s) retained for history._")
        lines.append("")
    return "\n".join(lines)


def reindex() -> None:
    INDEX.write_text(render_index(load_all()), encoding="utf-8")


# ---------------------------------------------------------------- search

# Scoring is unanchored substring matching, which is what makes a short function
# word catastrophic: "a" is a substring of almost every fact, so an unfiltered
# natural-language query scores the whole corpus and the ranking becomes noise.
# Measured on a 135-fact corpus: dropping these lifted recall on vague queries
# from 0.375 to 0.522 with no other change.
STOPWORDS = frozenset("""
a an the this that these those there here and or but so if when what which who
whom whose how why is are was were be been being am do does did done have has
had can could should would will shall may might must not no nor of to in on at
by for with from into out up down over under again further then once all any
both each few more most other some such only own same than too very just now
i me my we us our you your he him his she her it its they them their as about
""".split())


def _terms(query: str) -> list[str]:
    """Query tokens worth scoring: no stopwords, nothing under three characters."""
    toks = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]
    kept = [t for t in toks if len(t) > 2 and t not in STOPWORDS]
    # A query made entirely of stopwords still has to match something; falling
    # back to the raw tokens is worse than nothing only when there is an
    # alternative, and here there is none.
    return kept or toks


def log_query(kind: str, query: str, filters: dict, hits: list,
              outcome: str | None = None, note: str = "") -> None:
    """Append one line to the query log — the corpus's only record of its own use.

    Without it, every claim about whether memory is CONSULTED — including
    whether the instruction to search with keywords is being followed — is
    unfalsifiable. The log answers three questions nothing else can: how often
    is memory queried, in what form, and does the query return anything.

    `stopworded` is the tell. A query whose token count collapses once
    stopwords are removed was a sentence, not a set of keywords, and sentences
    measured roughly a third of the recall of keywords on this corpus.

    Never fatal: a logging failure must not cost the caller their search.
    """
    try:
        raw = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]
        kept = _terms(query)
        rec = {
            "at": _dt.datetime.now().isoformat(timespec="seconds"),
            "kind": kind,
            "query": query[:200],
            "tokens": len(raw),
            "kept": len(kept),
            "stopworded": len(raw) - len(kept),
            "filters": {k: v for k, v in filters.items() if v},
            "n": len(hits),
            "top": [d["meta"]["id"] for _, d in hits[:3]],
            "top_score": round(hits[0][0], 1) if hits else 0,
        }
        if outcome:
            rec["outcome"] = outcome
        if note:
            rec["note"] = note[:300]
        QUERY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with QUERY_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def search(query: str, tags: list[str], scope: str | None,
           top: int, include_superseded: bool = False,
           provenance: list[str] | None = None, rule: str | None = None,
           open_only: bool = False, stale_days: int | None = None,
           log: bool = False) -> list[tuple[float, dict]]:
    terms = _terms(query)
    docs = load_all()
    open_ids = {d["meta"]["id"] for d in open_cases(docs)} if open_only else None
    hits = []
    for d in docs:
        meta = d["meta"]
        if not include_superseded and meta.get("status") != "active":
            continue
        if tags and not set(tags) & set(meta.get("tags", [])):
            continue
        if scope and meta.get("scope") not in (scope, "repo"):
            continue
        if provenance and meta.get("provenance") not in provenance:
            continue
        if rule and str(meta.get("rule") or "") != rule:
            continue
        if open_ids is not None and meta["id"] not in open_ids:
            continue
        if stale_days is not None and days_since(meta.get("checked", "")) <= stale_days:
            continue
        score = 0.0
        kws = [k.lower() for k in meta.get("keywords", [])]
        fact_l, ctx_l, id_l = d["fact"].lower(), d["context"].lower(), meta["id"]
        for t in terms:
            if t in kws:
                score += 3
            if t in fact_l:
                score += 2
            if t in id_l:
                score += 1
            if t in ctx_l:
                score += 1
        if score > 0:
            hits.append((score, d))
    hits.sort(key=lambda h: (-h[0], h[1]["meta"]["id"]))
    hits = hits[:top]
    if log:
        log_query("search", query,
                  {"tags": tags, "scope": scope, "provenance": provenance,
                   "rule": rule, "open": open_only, "stale_days": stale_days},
                  hits)
    return hits


# ---------------------------------------------------------------- reflect

# Signal weights. `read` is the workhorse because it is derived from behaviour
# and therefore always present; the marked outcomes are stronger but optional,
# and the system must stay useful when nobody ever marks anything.
OUTCOME_WEIGHT = {"read": 1.0, "useful": 2.0, "corrected": -1.0, "dead_end": -2.0}
REFLECT_HALF_LIFE_DAYS = 30.0   # a signal's weight halves every 30 days
REFLECT_MIN_CORROBORATION = 2   # distinct positive signals before "relied on"


def _decay(iso: str, half_life: float = REFLECT_HALF_LIFE_DAYS) -> float:
    """Weight in (0, 1], halving every `half_life` days.

    Decay rather than expiry is the point: a fact consulted twice last week and
    a fact consulted twice last year are not equally live, but neither is dead.
    A cliff would make the report lurch; a half-life lets it drift.
    """
    age = days_since(str(iso)[:10])
    if age < 0 or half_life <= 0:
        return 1.0
    return 0.5 ** (age / half_life)


def read_log() -> list[dict]:
    if not QUERY_LOG.exists():
        return []
    out = []
    for line in QUERY_LOG.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def reflect(docs: list[dict] | None = None,
            records: list[dict] | None = None) -> dict:
    """Which facts are earning their place — from behaviour, not self-report.

    Deterministic: no model call, stable ordering, same input gives the same
    output for a given day. It reads the query log and nothing else, and it
    writes no facts, because experiential signal and the durable record have
    different lifetimes and must not be stored in the same place.

    The report nobody else can give you is `never_surfaced`: facts that have
    never once appeared in a search result. Two very different causes, and
    telling them apart is the human's job — the fact is dead weight, or its
    keywords do not match how anyone actually asks. The second is a retrieval
    defect wearing the costume of a content defect, and this repository already
    holds the precedent for it: an absent result is evidence about the query
    rather than about the corpus.
    """
    docs = docs if docs is not None else load_all()
    records = records if records is not None else read_log()
    live = {d["meta"]["id"]: d for d in active(docs)}

    score: dict[str, float] = {i: 0.0 for i in live}
    positives: dict[str, int] = {i: 0 for i in live}
    surfaced: dict[str, int] = {i: 0 for i in live}
    events: dict[str, list] = {i: [] for i in live}
    empty_queries, sessions, searches = [], 0, 0

    for r in records:
        kind, at = r.get("kind"), r.get("at", "")
        if kind == "session":
            sessions += 1
            continue
        if kind == "search":
            searches += 1
            if not r.get("n"):
                empty_queries.append((at, r.get("query", "")))
            for fid in r.get("top", []):
                if fid in surfaced:
                    surfaced[fid] += 1
            continue
        # `read` logs the id as the query; `mark` carries an explicit outcome.
        fid = r.get("query") or ""
        outcome = r.get("outcome") or ("read" if kind == "read" else None)
        if fid not in live or outcome not in OUTCOME_WEIGHT:
            continue
        w = OUTCOME_WEIGHT[outcome] * _decay(at)
        score[fid] += w
        if w > 0:
            positives[fid] += 1
        events[fid].append((at[:10], outcome, r.get("note", "")))

    def bucket(fid: str) -> str:
        s, p = score[fid], positives[fid]
        if s < 0:
            return "contested" if p else "dead_end"
        if p >= REFLECT_MIN_CORROBORATION:
            return "relied_on"
        if p:
            return "tentative"
        return "surfaced_unopened" if surfaced[fid] else "never_surfaced"

    out: dict[str, list] = {k: [] for k in
                            ("relied_on", "tentative", "contested", "dead_end",
                             "surfaced_unopened", "never_surfaced")}
    for fid in sorted(live):
        out[bucket(fid)].append(
            {"id": fid, "score": round(score[fid], 3), "positives": positives[fid],
             "surfaced": surfaced[fid], "scope": live[fid]["meta"]["scope"],
             "events": events[fid][-3:]})
    for k in out:
        out[k].sort(key=lambda r: (-r["score"], -r["surfaced"], r["id"]))
    return {"buckets": out, "sessions": sessions, "searches": searches,
            "empty_queries": empty_queries[-10:], "n_facts": len(live)}


# ---------------------------------------------------------------- promote

PROMOTE_MIN_CLUSTER = 4      # a pattern learned fewer times than this is anecdote
PROMOTE_MAX_COVERAGE = 0.34  # above this the Legislation already says it


def legislation_path(scope: str) -> Path:
    return REPO / "CLAUDE.md" if scope == "repo" else REPO / scope / "CLAUDE.md"


def cluster_facts(docs: list[dict]) -> dict[tuple, list[dict]]:
    """Group facts by shared keywords, deterministically and without a model.

    A keyword two or more facts have in common is a candidate theme. This is
    crude on purpose: the tool's job is to say "you have written about X eleven
    times", which is a counting question. Whether those eleven amount to a rule
    is a judgement, and it stays with the human.
    """
    by_scope_kw: dict[tuple, list[dict]] = {}
    for d in active(docs):
        scope = d["meta"]["scope"]
        for k in {k.lower() for k in d["meta"].get("keywords", [])}:
            by_scope_kw.setdefault((scope, k), []).append(d)
    return {k: v for k, v in by_scope_kw.items() if len(v) >= PROMOTE_MIN_CLUSTER}


def coverage(theme: str, scope: str) -> float:
    """How much the governing Legislation already says about a theme.

    Word-stem presence, not comprehension. It answers "has this word ever been
    written into the rules", which is enough to separate a theme the Legislation
    has never mentioned from one it already governs.
    """
    p = legislation_path(scope)
    if not p.exists():
        return 0.0
    text = p.read_text(encoding="utf-8").lower()
    stem = theme[:6]
    hits = text.count(stem)
    words = max(len(text.split()), 1)
    return min(hits / max(words / 100, 1), 1.0)


def promote_candidates(docs: list[dict] | None = None,
                       reflection: dict | None = None) -> list[dict]:
    """Themes learned often enough, and consulted enough, to deserve a rule.

    Two gates, and both matter. **Frequency** alone promotes whatever happened
    to get written down a lot. **Use** alone promotes whatever is easy to
    retrieve. A theme earns codification when it has been learned repeatedly
    AND keeps being reached for, because that combination is what a rule is:
    something you would otherwise look up again and again.

    Returns candidates only. Nothing here writes to a CLAUDE.md — Legislation
    is authored content, and an agent that edits the rules it is governed by
    has stopped being governed by them.
    """
    docs = docs if docs is not None else load_all()
    reflection = reflection if reflection is not None else reflect(docs)
    pull = {}
    for b, rows in reflection["buckets"].items():
        for r in rows:
            pull[r["id"]] = r["surfaced"] + max(r["positives"], 0) * 2

    out = []
    for (scope, theme), facts in cluster_facts(docs).items():
        cov = coverage(theme, scope)
        if cov > PROMOTE_MAX_COVERAGE:
            continue
        ids = sorted(d["meta"]["id"] for d in facts)
        demand = sum(pull.get(i, 0) for i in ids)
        tiers = collections.Counter(d["meta"]["provenance"] for d in facts)
        out.append({
            "theme": theme, "scope": scope, "n": len(facts),
            "coverage": round(cov, 3), "demand": demand,
            "legislation": str(legislation_path(scope).relative_to(REPO)),
            "provenance": dict(tiers),
            # The weakest tier in the cluster bounds what the rule may assert.
            # A rule drafted from a set containing one `unverified` fact cannot
            # be stated as established behaviour.
            "weakest": min(tiers, key=lambda t: PROVENANCE.index(t)),
            "facts": ids,
            "score": round(len(facts) * (1 - cov) * (1 + demand / 10), 2),
        })
    out.sort(key=lambda c: (-c["score"], c["scope"], c["theme"]))
    return out


# ---------------------------------------------------------------- dream

DREAM_LOG = REPO / ".memory-log" / "dream.jsonl"
STATE = REPO / ".memory-log" / "state.json"
DREAM_EVERY_DAYS = 7
DREAM_EVERY_SESSIONS = 10
# Similarity floors. Deliberately high: an unattended merge is the one hygiene
# action that loses information, so it must only fire on pairs a human would
# call the same fact written twice.
MERGE_KW_FLOOR = 0.75
MERGE_TEXT_FLOOR = 0.60
ENRICH_MIN_KEYWORDS = 8    # target vocabulary size for an unfindable fact
ENRICH_MIN_SEARCHES = 30   # history needed before "never surfaced" means anything
ENRICH_MAX_DF = 0.25       # a word in more than a quarter of facts discriminates nothing


def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")


def _dream_log(action: str, **kw) -> None:
    try:
        DREAM_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DREAM_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": _dt.datetime.now().isoformat(timespec="seconds"),
                                 "action": action, **kw}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z0-9]{3,}", text.lower())
            if w not in STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def dream(docs: list[dict] | None = None, apply: bool = True) -> dict:
    """Unattended hygiene. Everything it does is logged and reversible via git.

    Three things it does, and one it deliberately refuses.

    **Enrich** the keywords of facts no search has ever surfaced. This is the
    highest-value automated fix available, because "never surfaced" is usually a
    retrieval defect rather than a content defect: the fact is fine, its
    vocabulary just does not match how anyone asks. Enrichment is additive —
    existing keywords are never removed — so it cannot make a fact less findable.

    **Merge** near-identical pairs by superseding the older into the newer. It
    supersedes rather than deletes: supersession keeps the history and the
    `superseded_by` trail, and deletion is the only operation this system cannot
    undo from inside itself.

    **Reindex**, so the generated index can never trail the facts.

    It does NOT resolve contradictions. Deciding which of two conflicting facts
    is false, with no run to settle it, manufactures a verdict — and law 3 wants
    a discrepancy recorded with its open question named, not quietly closed.
    Contradictions are detected and queued for the human.
    """
    docs = docs if docs is not None else load_all()
    rows = active(docs)
    refl = reflect(docs)
    report = {"enriched": [], "merged": [], "contradictions": [], "checked": len(rows)}

    by_id = {d["meta"]["id"]: d for d in rows}

    # --- 1. enrich the vocabulary of facts nothing ever finds ---------------
    # Gate on having enough history to mean anything. With an empty log EVERY
    # fact is "never surfaced", which says nothing about the facts and
    # everything about the log — enriching on that signal would rewrite the
    # whole corpus on the strength of no evidence at all.
    if refl["searches"] < ENRICH_MIN_SEARCHES:
        report["enrich_skipped"] = (
            f"only {refl['searches']} search(es) logged; needs "
            f"{ENRICH_MIN_SEARCHES} before 'never surfaced' means anything")
        unfindable = set()
    else:
        unfindable = {r["id"] for r in refl["buckets"]["never_surfaced"]}

    # A word is worth adding only if it DISCRIMINATES. Document frequency across
    # the corpus is the test: a term in a quarter of all facts cannot narrow a
    # search, and as a keyword it scores +3 on every one of them, so adding it
    # costs precision everywhere to gain recall nowhere.
    df: dict[str, int] = collections.Counter()
    for d in rows:
        for w in _words(d["fact"]):
            df[w] += 1
    ceiling = max(2, int(len(rows) * ENRICH_MAX_DF))

    for fid in sorted(unfindable):
        d = by_id.get(fid)
        if not d:
            continue
        have = {k.lower() for k in d["meta"].get("keywords", [])}
        if len(have) >= ENRICH_MIN_KEYWORDS:
            continue
        cand = (_words(d["fact"]) | _words(fid.replace("-", " "))) - have
        cand = {w for w in cand if df.get(w, 1) <= ceiling}
        # Rarest first: the most discriminating terms this fact owns.
        add = sorted(cand, key=lambda w: (df.get(w, 1), w))[:ENRICH_MIN_KEYWORDS - len(have)]
        if not add:
            continue
        report["enriched"].append({"id": fid, "added": add})
        if apply:
            meta = dict(d["meta"])
            meta["keywords"] = list(d["meta"]["keywords"]) + add
            meta["updated"] = date.today().isoformat()
            # `checked` is untouched: giving a fact better keywords does not
            # re-confirm that the fact is still true.
            write_fact(meta, d["fact"], d["context"])
            _dream_log("enrich", id=fid, added=add)

    # --- 2. merge what is plainly the same fact written twice ---------------
    docs = load_all() if apply else docs
    rows = active(docs)
    kw = {d["meta"]["id"]: {k.lower() for k in d["meta"].get("keywords", [])} for d in rows}
    tx = {d["meta"]["id"]: _words(d["fact"]) for d in rows}
    seen: set = set()
    for a, b in itertools.combinations(sorted(kw), 2):
        if a in seen or b in seen:
            continue
        kj, tj = _jaccard(kw[a], kw[b]), _jaccard(tx[a], tx[b])
        if kj < MERGE_KW_FLOOR or tj < MERGE_TEXT_FLOOR:
            continue
        da, db = by_id.get(a), by_id.get(b)
        if not da or not db:
            continue
        # Newest `checked` wins; it is the more recently confirmed statement.
        keep, drop = ((da, db) if str(da["meta"]["checked"]) >= str(db["meta"]["checked"])
                      else (db, da))
        report["merged"].append({"kept": keep["meta"]["id"], "superseded": drop["meta"]["id"],
                                 "kw_sim": round(kj, 2), "text_sim": round(tj, 2)})
        seen |= {a, b}
        if apply:
            meta = dict(drop["meta"])
            meta["status"] = "superseded"
            meta["superseded_by"] = keep["meta"]["id"]
            meta["updated"] = date.today().isoformat()
            drop["path"].write_text(compose(meta, drop["fact"], drop["context"]),
                                    encoding="utf-8")
            _dream_log("merge", kept=keep["meta"]["id"], superseded=drop["meta"]["id"],
                       kw_sim=round(kj, 2), text_sim=round(tj, 2))

    # --- 3. detect contradictions, and stop there ---------------------------
    # A pair sharing most of its vocabulary while one negates and the other does
    # not is a candidate divergence. Reported, never acted on.
    NEG = re.compile(r"\b(not|never|no|cannot|without|nothing|neither)\b")
    for a, b in itertools.combinations(sorted(tx), 2):
        if _jaccard(tx[a], tx[b]) < 0.42:
            continue
        na = bool(NEG.search(by_id[a]["fact"].lower())) if a in by_id else False
        nb = bool(NEG.search(by_id[b]["fact"].lower())) if b in by_id else False
        if na != nb:
            report["contradictions"].append({"a": a, "b": b})
    if report["contradictions"]:
        _dream_log("contradictions_queued", n=len(report["contradictions"]),
                   pairs=report["contradictions"][:20])

    if apply:
        reindex()
        _dream_log("dream", enriched=len(report["enriched"]),
                   merged=len(report["merged"]),
                   contradictions=len(report["contradictions"]))
        s = _state()
        s["last_dream"] = _dt.datetime.now().isoformat(timespec="seconds")
        s["sessions_since_dream"] = 0
        s["last_dream_report"] = {k: (len(v) if isinstance(v, list) else v)
                                  for k, v in report.items()}
        _save_state(s)
    return report


PROMOTE_NOTIFY_SCORE = 6.0


def cycle(event: str) -> str:
    """The whole automated loop, in one command the hooks call.

    Split by cost. `stop` fires when the session is over: nothing is waiting,
    nothing is injected into anyone's context, so that is where work belongs.
    `session-start` fires in front of the first prompt and its output IS
    context, so it only ever reports, and only ever reports something new.

    Silence is the design. A trigger that speaks every session is indistinguishable
    from noise within a fortnight, and it would erode the precedent block sitting
    beside it. This returns "" unless something actually happened.
    """
    s = _state()
    if event == "stop":
        s["sessions_since_dream"] = int(s.get("sessions_since_dream", 0)) + 1
        # First run ever: start the clock rather than dreaming immediately. An
        # install with no history has nothing to clean and no usage evidence to
        # clean it by, so a dream here could only report that it did nothing.
        if not s.get("last_dream"):
            s["last_dream"] = _dt.datetime.now().isoformat(timespec="seconds")
            s["sessions_since_dream"] = 0
            _save_state(s)
            return ""
        _save_state(s)
        due, why = dream_due(s)
        if due:
            r = dream()
            s = _state()
            s["pending_report"] = {
                "why": why,
                "enriched": len(r["enriched"]), "merged": len(r["merged"]),
                "contradictions": len(r["contradictions"]),
                "merged_pairs": r["merged"][:5],
                "contradiction_pairs": r["contradictions"][:5],
            }
            _save_state(s)
            # Promotion candidates are checked ONLY when a dream ran, which ties
            # the notice to the weekly cadence rather than to every session.
            # Checked per-session it would hand over the next three candidates
            # each time and walk the whole backlog, which is a feed, not a
            # notification — and a feed is what gets skimmed and then ignored.
            try:
                announced = set(s.get("promote_announced", []))
                dismissed = set(s.get("promote_dismissed", []))
                fresh = [c for c in promote_candidates()
                         if c["score"] >= PROMOTE_NOTIFY_SCORE
                         and f"{c['scope']}:{c['theme']}" not in announced | dismissed]
                if fresh:
                    s = _state()
                    s["pending_promote"] = [
                        {"theme": c["theme"], "scope": c["scope"], "n": c["n"],
                         "score": c["score"], "legislation": c["legislation"],
                         "weakest": c["weakest"]} for c in fresh[:3]]
                    s["promote_backlog"] = len(fresh)
                    _save_state(s)
            except Exception:
                pass
        return ""

    # --- session-start: report, then forget -------------------------------
    out: list[str] = []
    rep = s.pop("pending_report", None)
    if rep:
        bits = []
        if rep["enriched"]:
            bits.append(f"enriched the keywords of {rep['enriched']} fact(s) no "
                        "search had ever surfaced")
        if rep["merged"]:
            bits.append(f"superseded {rep['merged']} duplicate(s)")
        line = (f"Memory dreamt since you were last here ({rep['why']}): "
                + ("; ".join(bits) if bits else "nothing needed changing")
                + ". Full log: .memory-log/dream.jsonl")
        out.append(line)
        for m in rep.get("merged_pairs", []):
            out.append(f"  · merged {m['superseded']} into {m['kept']}")
        if rep["contradictions"]:
            out.append(f"  · {rep['contradictions']} possible contradiction(s) "
                       "detected and LEFT ALONE — deciding which side is false "
                       "without a run would manufacture a verdict. Review with: "
                       "python scripts/memory.py dream --dry-run")
            for c in rep.get("contradiction_pairs", []):
                out.append(f"      {c['a']}  vs  {c['b']}")
    prom = s.pop("pending_promote", None)
    backlog = s.pop("promote_backlog", 0)
    if prom:
        out.append("")
        out.append("Codification candidate(s) — themes learned often enough that "
                   "re-deriving them each session is now the expensive option:")
        for c in prom:
            out.append(f"  · '{c['theme']}' ({c['n']} facts) -> {c['legislation']}; "
                       f"a rule may claim no more than '{c['weakest']}'")
        if backlog > len(prom):
            out.append(f"  ({backlog - len(prom)} more behind these; "
                       "python scripts/memory.py promote shows the full list)")
        out.append("  Run the memory-promote skill to draft one, or dismiss it: "
                   "python scripts/memory.py promote --dismiss <scope>:<theme>")
        s["promote_announced"] = sorted(set(s.get("promote_announced", []))
                                        | {f"{c['scope']}:{c['theme']}" for c in prom})
    if rep or prom:
        _save_state(s)
    return "\n".join(out)


def dream_due(s: dict | None = None) -> tuple[bool, str]:
    s = s if s is not None else _state()
    sess = int(s.get("sessions_since_dream", 0))
    last = str(s.get("last_dream", ""))[:10]
    days = days_since(last) if last else 999
    if days >= DREAM_EVERY_DAYS:
        return True, f"{days}d since the last dream"
    if sess >= DREAM_EVERY_SESSIONS:
        return True, f"{sess} sessions since the last dream"
    return False, f"{days}d / {sess} session(s) since the last dream"


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="memory.py", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create")
    c.add_argument("--id", required=True)
    c.add_argument("--tags", required=True, help="comma-sep from " + ",".join(TAGS))
    c.add_argument("--keywords", required=True, help="comma-sep")
    c.add_argument("--scope", required=True, choices=SCOPES)
    c.add_argument("--fact", required=True)
    c.add_argument("--context", default="")
    # Defaulting to `unverified` rather than demanding a tier keeps capture
    # cheap and keeps the default honest: an unclaimed fact claims nothing.
    c.add_argument("--provenance", default="unverified", choices=PROVENANCE,
                   help="how this is known (default: unverified)")
    c.add_argument("--source", default="",
                   help="who stated it and when — required for --provenance contractual")
    c.add_argument("--checked", default="",
                   help="date last confirmed true (default: today)")
    c.add_argument("--resolves", default="",
                   help="id of the issue this fix closes (fix-tagged facts only)")
    c.add_argument("--rule", default="",
                   help="rule construed, e.g. constitution#law-2 (makes this a precedent)")

    u = sub.add_parser("update")
    u.add_argument("id")
    u.add_argument("--fact")
    u.add_argument("--tags")
    u.add_argument("--keywords")
    u.add_argument("--context")
    u.add_argument("--provenance", default=None, choices=PROVENANCE)
    u.add_argument("--source", default=None)
    u.add_argument("--checked", default=None,
                   help="use 'today' to re-confirm the fact as of now")
    u.add_argument("--resolves", default=None)
    u.add_argument("--rule", default=None)

    for name in ("read", "delete"):
        p = sub.add_parser(name)
        p.add_argument("id")

    sp = sub.add_parser("supersede")
    sp.add_argument("id")
    sp.add_argument("--by", default="")

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--tags", default="")
    s.add_argument("--scope", default=None, choices=(*SCOPES, None))
    s.add_argument("--provenance", default="",
                   help="comma-sep from " + ",".join(PROVENANCE))
    s.add_argument("--rule", default=None, help="exact rule reference")
    s.add_argument("--open", action="store_true",
                   help="only issues with no recorded resolution")
    s.add_argument("--stale-days", type=int, default=None,
                   help="only facts not checked within N days")
    s.add_argument("--top", type=int, default=5)

    li = sub.add_parser("lint")
    li.add_argument("--quiet-warnings", action="store_true",
                    help="errors only; suppress the advisory block")
    au = sub.add_parser("audit")
    au.add_argument("--stale-days", type=int, default=STALE_DAYS)
    us = sub.add_parser("usage")
    us.add_argument("--days", type=int, default=14)
    mk = sub.add_parser("mark")
    mk.add_argument("id")
    mk.add_argument("--outcome", required=True,
                    choices=("useful", "dead_end", "corrected"))
    mk.add_argument("--note", default="")
    rf = sub.add_parser("reflect")
    rf.add_argument("--out", default="",
                    help="also write the report to this path (default: stdout only)")
    pr = sub.add_parser("promote")
    pr.add_argument("--top", type=int, default=8)
    pr.add_argument("--min-cluster", type=int, default=PROMOTE_MIN_CLUSTER)
    pr.add_argument("--dismiss", default="",
                    help="<scope>:<theme> — stop announcing this candidate")
    dr = sub.add_parser("dream")
    dr.add_argument("--dry-run", action="store_true",
                    help="report what a dream would do and change nothing")
    cy = sub.add_parser("cycle")
    cy.add_argument("--event", required=True, choices=("stop", "session-start"))
    sub.add_parser("reindex")
    sub.add_parser("list")

    a = ap.parse_args(argv)
    today = date.today().isoformat()

    def _find(fid: str) -> dict:
        for d in load_all():
            if d["meta"].get("id") == fid:
                return d
        raise OkfError(f"no fact with id {fid!r}")

    try:
        if a.cmd == "create":
            meta = {"id": a.id, "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
                    "keywords": [k.strip() for k in a.keywords.split(",") if k.strip()],
                    "scope": a.scope, "status": "active",
                    "provenance": a.provenance,
                    "checked": a.checked or today,
                    "created": today, "updated": today}
            if a.source:
                meta["source"] = a.source
            if a.resolves:
                meta["resolves"] = a.resolves
            if a.rule:
                meta["rule"] = a.rule
            path = write_fact(meta, a.fact, a.context)
            print(f"created {path.relative_to(REPO)}")
        elif a.cmd == "update":
            d = _find(a.id)
            meta = dict(d["meta"])
            meta["updated"] = today
            if a.tags:
                meta["tags"] = [t.strip() for t in a.tags.split(",") if t.strip()]
            if a.keywords:
                meta["keywords"] = [k.strip() for k in a.keywords.split(",") if k.strip()]
            if a.provenance:
                meta["provenance"] = a.provenance
            # `updated` is when the FILE changed; `checked` is when the CLAIM was
            # re-confirmed. Rewording a fact does not make it true again, so
            # `checked` only ever moves when the caller says it did.
            if a.checked:
                meta["checked"] = today if a.checked == "today" else a.checked
            for k in ("source", "resolves", "rule"):
                v = getattr(a, k)
                if v is None:
                    continue
                if v == "":
                    meta.pop(k, None)      # empty string clears the field
                else:
                    meta[k] = v
            write_fact(meta, a.fact or d["fact"],
                       a.context if a.context is not None else d["context"])
            print(f"updated {a.id}")
        elif a.cmd == "supersede":
            d = _find(a.id)
            meta = dict(d["meta"])
            meta["status"] = "superseded"
            meta["updated"] = today
            if a.by:
                meta["superseded_by"] = a.by
            # superseded facts bypass the active gate but keep structure valid
            path = d["path"]
            path.write_text(compose(meta, d["fact"], d["context"]), encoding="utf-8")
            reindex()
            print(f"superseded {a.id}" + (f" by {a.by}" if a.by else ""))
        elif a.cmd == "read":
            d = _find(a.id)
            # A `read` is the cheapest honest usage signal there is. Search shows
            # the one-line fact; only `read` returns the Context, so opening one
            # means the fact was worth going deeper on. Derived from behaviour,
            # so it cannot be forgotten the way a self-reported outcome can.
            log_query("read", a.id, {}, [(1.0, d)])
            print(d["path"].read_text(encoding="utf-8"))
        elif a.cmd == "delete":
            d = _find(a.id)
            d["path"].unlink()
            reindex()
            print(f"deleted {a.id}")
        elif a.cmd == "search":
            tags = [t.strip() for t in a.tags.split(",") if t.strip()]
            prov = [p.strip() for p in a.provenance.split(",") if p.strip()]
            hits = search(a.query, tags, a.scope, a.top, provenance=prov,
                          rule=a.rule, open_only=a.open, stale_days=a.stale_days,
                          log=True)
            if not hits:
                print("no matching facts")
            docs = load_all()
            open_ids = {d["meta"]["id"] for d in open_cases(docs)}
            for score, d in hits:
                meta = d["meta"]
                tagstr = ",".join(meta.get("tags", []))
                flags = []
                if meta["id"] in open_ids:
                    flags.append("OPEN")
                if meta.get("rule"):
                    flags.append(f"rule:{meta['rule']}")
                if meta.get("resolves"):
                    flags.append(f"resolves:{meta['resolves']}")
                age = days_since(meta.get("checked", ""))
                if meta.get("provenance") in PROVENANCE_PERISHABLE and age > STALE_DAYS:
                    flags.append(f"STALE {age}d")
                tail = ("  " + " ".join(flags)) if flags else ""
                print(f"[{score:>4.1f}] {meta['id']} "
                      f"({meta['scope']}/{tagstr}/{meta.get('provenance','?')})"
                      f"{tail}")
                print(f"       {d['fact']}")
        elif a.cmd == "lint":
            errs = lint_all()
            if errs:
                print("OKF LINT FAILED:")
                for e in errs:
                    print("  " + e)
                return 1
            docs = load_all()
            print(f"OKF lint OK ({len(docs)} fact(s))")
            if not a.quiet_warnings:
                warns = lint_warnings(docs)
                if warns:
                    print(f"\nWARNINGS ({len(warns)}) — advisory, the gate still passes:")
                    for w in warns:
                        print("  " + w)
        elif a.cmd == "audit":
            docs = load_all()
            op = open_cases(docs)
            prec = precedents(docs)
            byprov: dict[str, int] = {}
            for d in active(docs):
                byprov[d["meta"].get("provenance", "?")] = \
                    byprov.get(d["meta"].get("provenance", "?"), 0) + 1
            stale = [d for d in active(docs)
                     if d["meta"].get("provenance") in PROVENANCE_PERISHABLE
                     and days_since(d["meta"].get("checked", "")) > a.stale_days]
            noq = [d for d in active(docs)
                   if "issue" in d["meta"].get("tags", []) and not d["context"]]
            print(f"Common Law audit — {len(active(docs))} active fact(s)\n")
            print("provenance: " + ", ".join(
                f"{k}={byprov.get(k, 0)}" for k in PROVENANCE))
            print(f"precedent (facts naming a rule): {len(prec)}")
            print(f"open cases (issues with no resolution): {len(op)}")
            print(f"issues with no open question recorded: {len(noq)}")
            print(f"perishable claims older than {a.stale_days}d: {len(stale)}\n")
            if op:
                print("OPEN CASES")
                for d in sorted(op, key=lambda x: x["meta"]["id"]):
                    print(f"  {d['meta']['id']} ({d['meta']['scope']}/"
                          f"{d['meta'].get('provenance','?')})")
            if stale:
                print("\nDUE A RE-CHECK")
                for d in sorted(stale, key=lambda x: x["meta"].get("checked", "")):
                    print(f"  {d['meta']['checked']}  {d['meta']['id']} "
                          f"({d['meta']['provenance']})")
        elif a.cmd == "usage":
            if not QUERY_LOG.exists():
                print("no query log yet — memory has not been searched from this "
                      "working copy since logging was added")
                return 0
            cutoff = (date.today() - _dt.timedelta(days=a.days)).isoformat()
            recs, sessions = [], 0
            for line in QUERY_LOG.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("at", "") < cutoff:
                    continue
                if r.get("kind") == "session":
                    sessions += 1
                else:
                    recs.append(r)
            print(f"Memory usage — last {a.days} day(s)\n")
            print(f"sessions:  {sessions}")
            print(f"searches:  {len(recs)}")
            if sessions:
                print(f"searches per session: {len(recs)/sessions:.1f}")
            if not recs:
                print("\nNo searches recorded. Either the work needed none, or the "
                      "consult nudge is not landing — the hook cannot tell you "
                      "which, but the ratio above can.")
                return 0
            empty = sum(1 for r in recs if not r.get("n"))
            # A query whose tokens mostly survive the stopword filter was
            # written as keywords; one that collapses was a sentence.
            sent = [r for r in recs if r.get("tokens", 0) >= 6
                    and r.get("stopworded", 0) / max(r.get("tokens", 1), 1) >= 0.35]
            print(f"returned nothing: {empty} ({empty/len(recs):.0%})")
            print(f"phrased as a SENTENCE rather than keywords: {len(sent)} "
                  f"({len(sent)/len(recs):.0%})")
            if sent:
                print("\n  Sentence-form queries measured about a third of the recall of\n"
                      "  keyword queries on this corpus. A high share here means the\n"
                      "  hook's instruction is not being followed:")
                for r in sent[:5]:
                    print(f"    [{r['n']} hit(s)] {r['query'][:70]}")
            filt = sum(1 for r in recs if r.get("filters"))
            print(f"\nused at least one filter: {filt} ({filt/len(recs):.0%})")
        elif a.cmd == "mark":
            d = _find(a.id)
            log_query("mark", a.id, {}, [(1.0, d)], outcome=a.outcome, note=a.note)
            print(f"marked {a.id} as {a.outcome}")
        elif a.cmd == "reflect":
            r = reflect()
            L = []
            L.append(f"Reflection — {r['n_facts']} active fact(s), "
                     f"{r['searches']} search(es) across {r['sessions']} session(s)")
            if not r["searches"]:
                L.append("")
                L.append("The query log is empty, so nothing can be said yet. This "
                         "report is worth reading after a fortnight of ordinary use, "
                         "not today.")
                print("\n".join(L))
                return 0
            b = r["buckets"]
            L.append("")
            L.append(f"  relied on         {len(b['relied_on']):3}   consulted and "
                     f"re-consulted ({REFLECT_MIN_CORROBORATION}+ positive signals)")
            L.append(f"  tentative         {len(b['tentative']):3}   opened once; not "
                     "yet corroborated")
            L.append(f"  contested         {len(b['contested']):3}   positive and "
                     "negative signals; recency decides")
            L.append(f"  dead end          {len(b['dead_end']):3}   marked unhelpful")
            L.append(f"  surfaced, unread  {len(b['surfaced_unopened']):3}   found by a "
                     "search, never opened")
            L.append(f"  never surfaced    {len(b['never_surfaced']):3}   no search has "
                     "ever returned these")
            if b["relied_on"]:
                L.append("\nRELIED ON — these are carrying the corpus:")
                for x in b["relied_on"][:10]:
                    L.append(f"  {x['score']:+6.2f}  {x['id']} ({x['scope']})")
            if b["dead_end"] or b["contested"]:
                L.append("\nNEGATIVE SIGNAL — re-check or supersede:")
                for x in (b["dead_end"] + b["contested"])[:10]:
                    last = x["events"][-1] if x["events"] else ("", "", "")
                    L.append(f"  {x['score']:+6.2f}  {x['id']}  {last[1]} {last[0]} "
                             f"{last[2][:60]}")
            if b["never_surfaced"]:
                L.append(f"\nNEVER SURFACED ({len(b['never_surfaced'])}) — two very "
                         "different causes, and only you can tell them apart:")
                L.append("  dead weight, OR keywords that do not match how anyone asks.")
                L.append("  The second is a retrieval defect, not a content defect: an "
                         "absent")
                L.append("  result is evidence about the query at least as often as "
                         "about the corpus.")
                for x in b["never_surfaced"][:15]:
                    L.append(f"          {x['id']} ({x['scope']})")
                if len(b["never_surfaced"]) > 15:
                    L.append(f"          ... and {len(b['never_surfaced'])-15} more")
            if r["empty_queries"]:
                L.append("\nQUERIES THAT RETURNED NOTHING — the corpus's vocabulary "
                         "gaps:")
                for at, q in r["empty_queries"]:
                    L.append(f"  {at[:10]}  {q[:66]}")
            txt = "\n".join(L)
            print(txt)
            if a.out:
                p = Path(a.out)
                if not p.is_absolute():
                    p = REPO / p
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(txt + "\n", encoding="utf-8")
                print(f"\nwritten to {p.relative_to(REPO)}")
        elif a.cmd == "dream":
            r = dream(apply=not a.dry_run)
            head = "Dream (dry run) would:" if a.dry_run else "Dream:"
            print(f"{head}\n")
            if r.get("enrich_skipped"):
                print(f"  enrichment SKIPPED — {r['enrich_skipped']}")
            print(f"  enrich keywords on   {len(r['enriched']):3} fact(s) that no "
                  "search has ever surfaced")
            for e in r["enriched"][:8]:
                print(f"      {e['id']}  += {','.join(e['added'])}")
            if len(r["enriched"]) > 8:
                print(f"      ... and {len(r['enriched'])-8} more")
            print(f"  supersede            {len(r['merged']):3} near-identical pair(s)")
            for m in r["merged"]:
                print(f"      {m['superseded']} -> {m['kept']} "
                      f"(kw {m['kw_sim']}, text {m['text_sim']})")
            print(f"  queue for you        {len(r['contradictions']):3} possible "
                  "contradiction(s)")
            for c in r["contradictions"][:8]:
                print(f"      {c['a']}\n         vs {c['b']}")
            if not a.dry_run:
                print("\n  index regenerated; every action logged to "
                      ".memory-log/dream.jsonl")
            print("\nDream never deletes (supersession keeps the history) and never "
                  "resolves a\ncontradiction (law 3: the open question is named, not "
                  "quietly closed).")
        elif a.cmd == "cycle":
            out = cycle(a.event)
            if out:
                print(out)
        elif a.cmd == "promote":
            globals()["PROMOTE_MIN_CLUSTER"] = a.min_cluster
            if a.dismiss:
                st = _state()
                st["promote_dismissed"] = sorted(
                    set(st.get("promote_dismissed", [])) | {a.dismiss})
                _save_state(st)
                print(f"dismissed {a.dismiss} — it will not be announced again")
                return 0
            cands = promote_candidates()
            if not cands:
                print("No codification candidates: every recurring theme is either "
                      "too small to be a pattern or already covered by its "
                      "Legislation.")
                return 0
            print(f"Codification candidates — {len(cands)} theme(s) learned "
                  f"{a.min_cluster}+ times that the Legislation barely mentions.\n")
            print("A candidate is not a decision. These are counts; whether a count "
                  "amounts to")
            print("a rule is yours. Nothing here has been written to any CLAUDE.md.\n")
            for c in cands[:a.top]:
                print(f"[{c['score']:>6.2f}]  '{c['theme']}'  ->  {c['legislation']}")
                print(f"          {c['n']} fact(s), Legislation coverage "
                      f"{c['coverage']:.0%}, demand {c['demand']}")
                print(f"          tiers {c['provenance']} — a rule drafted from this "
                      f"may claim no more than '{c['weakest']}'")
                for i in c["facts"][:6]:
                    print(f"            · {i}")
                if len(c["facts"]) > 6:
                    print(f"            · ... and {len(c['facts'])-6} more")
                print()
            print("Next: the `memory-promote` skill drafts the wording and takes it to "
                  "sign-off.")
            print("Promoting never deletes the facts — the rule states the position, "
                  "the facts remain its evidence.")
        elif a.cmd == "reindex":
            reindex()
            print("MEMORY.md regenerated")
        elif a.cmd == "list":
            for d in load_all():
                print(f"{d['meta']['id']:40} {d['meta'].get('scope','?'):8} "
                      f"{d['meta'].get('status','?')}")
    except OkfError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
