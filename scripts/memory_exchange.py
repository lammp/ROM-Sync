r"""Knowledge Exchange — portable Common Law across repositories.

Companion to scripts/memory.py. Where memory.py owns facts *inside* one
repository, this tool moves knowledge *between* repositories:

  * EXPORT — select a dimension of the Common Law ("everything we learned
    about Next.js"), stage each fact as GENERALISED, transferable knowledge,
    and seal it into a bundle that drops straight into any OKF filesystem.
  * IMPORT — read a bundle (or a foreign repo's memory/ directory), scan it
    against THIS repository's gate, and apply a human-approved plan.
  * STRUCTURE — dump the whole framework's structural state for the
    framework-lint skill's mechanical pass.

It shares memory.py's schema and verification gates by importing them — there
is exactly one OKF gate, and exported and imported facts pass through it like
any other. This file adds no new validation rules; it adds transport.

DESIGN RULES (enforced here, explained in the knowledge-export /
knowledge-import / framework-lint skills):

  1. Staged facts are always scope `repo` with the source scope preserved as
     `origin_scope`. `repo` exists in every installation, so a bundle is
     lint-clean in any destination before anyone maps anything.
  2. `import-apply` REFUSES to run if any plan entry is unresolved or is
     flagged as a conflict without a recorded human resolution. Conflicting
     knowledge cannot enter a repository — that is a hard rule, not a warning.
  3. Nothing is written outside a staging directory until the human approves
     a plan.

Usage:
  # export
  python scripts/memory_exchange.py export-list [--scope <s>] [--tags <t>]
  python scripts/memory_exchange.py export-stage --repo-name <name> \
      --dimension "<all | Next.js App Router>"
  python scripts/memory_exchange.py export-add --stage <dir> --id <kebab-id> \
      --tags <t,..> --keywords <k,..> --origin-id <src-id> \
      --origin-scope <src-scope> --fact "<one generalised sentence.>" \
      [--context "..."]
  python scripts/memory_exchange.py export-seal --stage <dir> [--out <dir>]

  # import
  python scripts/memory_exchange.py import-scan --source <zip|dir> \
      [--include-superseded]
  python scripts/memory_exchange.py import-plan --source <dir> [--out <file>]
  python scripts/memory_exchange.py import-apply --plan <file> [--dry-run]

  # verification support
  python scripts/memory_exchange.py structure
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import memory as M  # noqa: E402  — the single OKF gate, shared not duplicated

REPO = M.REPO
EXCHANGE = REPO / ".exchange"
BUNDLE_SCOPE = "repo"
PLAN_ACTIONS = ("accept", "merge", "skip")


class ExchangeError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M")


def load_dir(path: Path) -> list[dict]:
    """Parse every OKF file in a directory WITHOUT the destination gate.

    Foreign facts legitimately carry scopes this repository has never heard
    of; refusing to read them would make the scan useless. Validation happens
    at apply time, against the real gate.
    """
    if not path.exists():
        raise ExchangeError(f"no such directory: {path}")
    docs = []
    for p in sorted(path.glob("*.md")):
        try:
            docs.append(M.parse(p))
        except M.OkfError as exc:
            docs.append({"meta": {}, "fact": "", "context": "", "path": p,
                         "parse_error": str(exc)})
    return docs


def find_memory_dir(root: Path) -> Path:
    """Locate the OKF fact directory inside an arbitrary source tree."""
    if (root / "memory").is_dir():
        return root / "memory"
    if list(root.glob("*.md")):
        return root
    for sub in sorted(p for p in root.iterdir() if p.is_dir()):
        if (sub / "memory").is_dir():
            return sub / "memory"
    raise ExchangeError(f"could not find an OKF memory directory under {root}")


def read_stage_manifest(stage: Path) -> dict:
    mf = stage / "MANIFEST.yaml"
    if not mf.exists():
        raise ExchangeError(f"{stage} is not a staging directory (no MANIFEST.yaml)")
    return yaml.safe_load(mf.read_text(encoding="utf-8")) or {}


# ---------------------------------------------------------------- export

def cmd_export_list(a) -> int:
    """Print the candidate corpus for the agent's dimension pass."""
    tags = [t.strip() for t in (a.tags or "").split(",") if t.strip()]
    rows = []
    for d in M.load_all():
        meta = d["meta"]
        if meta.get("status") != "active":
            continue
        if tags and not set(tags) & set(meta.get("tags", [])):
            continue
        if a.scope and meta.get("scope") != a.scope:
            continue
        rows.append(d)
    print(f"{len(rows)} active fact(s) — the export candidate corpus:\n")
    for d in rows:
        meta = d["meta"]
        print(f"- {meta['id']} [{','.join(meta.get('tags', []))}] "
              f"({meta.get('scope')}) kw={','.join(meta.get('keywords', []))}")
        print(f"    {d['fact']}")
        if d["context"]:
            first = d["context"].splitlines()[0]
            print(f"    context: {first[:100]}")
    return 0


def cmd_export_stage(a) -> int:
    dimension = a.dimension.strip()
    slug = "all" if dimension.lower() == "all" else slugify(dimension)
    stage = EXCHANGE / f"stage-{slug}-{stamp()}"
    (stage / "memory").mkdir(parents=True, exist_ok=True)
    manifest = {
        "bundle_format": "okf-exchange/1",
        "framework_version": M.FRAMEWORK_VERSION,
        "origin_repo": a.repo_name,
        "dimension": dimension,
        "dimension_slug": slug,
        "generalised": True,
        "tag_taxonomy": list(M.TAGS),
        "bundle_scope": BUNDLE_SCOPE,
        "staged": datetime.now().isoformat(timespec="minutes"),
        "facts": [],
    }
    (stage / "MANIFEST.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    print(f"staged {stage.relative_to(REPO)}")
    print("add generalised facts with: export-add --stage "
          f"{stage.relative_to(REPO)} ...")
    return 0


def cmd_export_add(a) -> int:
    stage = Path(a.stage)
    if not stage.is_absolute():
        stage = REPO / stage
    manifest = read_stage_manifest(stage)
    today = date.today().isoformat()
    # What travels and what does not (framework v1.3.0):
    #   provenance / source / checked  TRAVEL. How a fact is known does not
    #     change by crossing a repository boundary, and stripping the tier would
    #     let an `unverified` inference arrive elsewhere looking like plain fact
    #     — the laundering law 2 exists to prevent. `checked` travels for the
    #     same reason: the destination must be able to age what it receives.
    #   resolves  DOES NOT TRAVEL. It names a fact id in the SOURCE repository.
    #     Carried across it would dangle, or worse collide with an unrelated id
    #     in the destination and assert a resolution nobody recorded.
    #   rule  DOES NOT TRAVEL. It names a rule in the source's CLAUDE.md, and a
    #     reading of another repository's law is not a reading of this one's.
    ometa = {}
    for _d in M.load_all():
        if _d["meta"].get("id") == a.origin_id:
            ometa = _d["meta"]
            break
    meta = {
        "id": a.id,
        "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
        "keywords": [k.strip() for k in a.keywords.split(",") if k.strip()],
        "scope": BUNDLE_SCOPE,
        "status": "active",
        "provenance": ometa.get("provenance") or "unverified",
        "checked": ometa.get("checked") or today,
        "created": today,
        "updated": today,
        "origin_repo": manifest.get("origin_repo"),
        "origin_id": a.origin_id,
        "origin_scope": a.origin_scope,
    }
    if ometa.get("source") and meta["provenance"] in (
            M.PROVENANCE_NEEDS_SOURCE + ("documented",)):
        meta["source"] = ometa["source"]
    path = stage / "memory" / f"{meta['id']}.md"
    candidate = {"meta": meta, "fact": a.fact.strip(),
                 "context": (a.context or "").strip(), "path": path}
    errs = M.validate(candidate)
    if errs:
        raise ExchangeError("OKF violation(s) in staged fact:\n  " + "\n  ".join(errs))
    path.write_text(M.compose(meta, a.fact.strip(), (a.context or "").strip()),
                    encoding="utf-8")
    manifest.setdefault("facts", []).append(
        {"id": meta["id"], "origin_id": a.origin_id,
         "origin_scope": a.origin_scope, "tags": meta["tags"]})
    (stage / "MANIFEST.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    print(f"staged fact {meta['id']} (from {a.origin_id})")
    return 0


def render_bundle_readme(manifest: dict, docs: list[dict]) -> str:
    lines = [
        f"# Common Law export — {manifest.get('dimension')}",
        "",
        f"Exported from **{manifest.get('origin_repo')}** on "
        f"{manifest.get('sealed', manifest.get('staged'))} "
        f"(framework {manifest.get('framework_version')}).",
        "",
        "These are OKF facts (One Key Fact per file) that have been "
        "**generalised** — rewritten as transferable knowledge rather than "
        "statements about the project they came from. Each file keeps its "
        "origin in frontmatter (`origin_repo`, `origin_id`, `origin_scope`) "
        "for provenance only.",
        "",
        "## How to use this bundle",
        "",
        "Import it into a repository running the Legal Framework:",
        "",
        "    python scripts/memory_exchange.py import-scan --source <this.zip>",
        "",
        "The import reconciles every fact against the destination's "
        "Constitution and Legislation before anything is written. Do not copy "
        "these files into `memory/` by hand — the import exists to catch "
        "conflicts, and hand-copying skips it.",
        "",
        f"## Facts ({len(docs)})",
        "",
    ]
    for d in docs:
        meta = d["meta"]
        lines.append(f"- **{meta['id']}** [{','.join(meta.get('tags', []))}] "
                     f"— {d['fact']}")
    lines.append("")
    return "\n".join(lines)


def cmd_export_seal(a) -> int:
    stage = Path(a.stage)
    if not stage.is_absolute():
        stage = REPO / stage
    manifest = read_stage_manifest(stage)
    docs = load_dir(stage / "memory")
    if not docs:
        raise ExchangeError("nothing staged — the bundle would be empty")

    errs: list[str] = []
    seen: set[str] = set()
    for d in docs:
        if d.get("parse_error"):
            errs.append(f"{d['path'].name}: {d['parse_error']}")
            continue
        errs += M.validate(d)
        fid = str(d["meta"].get("id"))
        if fid in seen:
            errs.append(f"duplicate id {fid!r} in bundle")
        seen.add(fid)
    if errs:
        print("BUNDLE LINT FAILED:")
        for e in errs:
            print("  " + e)
        return 1

    manifest["sealed"] = datetime.now().isoformat(timespec="minutes")
    manifest["fact_count"] = len(docs)
    manifest["origin_scopes"] = sorted(
        {str(d["meta"].get("origin_scope")) for d in docs
         if d["meta"].get("origin_scope")})
    (stage / "MANIFEST.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    (stage / "README.md").write_text(render_bundle_readme(manifest, docs),
                                     encoding="utf-8")

    out_dir = Path(a.out) if a.out else EXCHANGE
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (f"{slugify(manifest['origin_repo'])}_"
            f"{manifest['dimension_slug']}_{stamp()}.zip")
    zip_path = out_dir / name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(stage))
    print(f"sealed {len(docs)} fact(s) -> {zip_path}")
    print(f"bundle lint OK; dimension={manifest['dimension']}; "
          f"origin scopes={','.join(manifest['origin_scopes']) or '-'}")
    return 0


# ---------------------------------------------------------------- import

def portability_report(d: dict) -> dict:
    """Assess ONE foreign fact against THIS repository's gate."""
    meta = d["meta"]
    issues, blockers = [], []
    if d.get("parse_error"):
        blockers.append(f"unparseable: {d['parse_error']}")
        return {"id": d["path"].stem, "issues": issues, "blockers": blockers,
                "fact": "", "tags": [], "origin_scope": None, "collision": False,
                "near": []}

    fid = str(meta.get("id", d["path"].stem))
    tags = list(meta.get("tags") or [])
    bad_tags = [t for t in tags if t not in M.TAGS]
    if bad_tags:
        blockers.append(f"tags outside this taxonomy: {bad_tags}")
    src_scope = meta.get("scope")
    origin_scope = meta.get("origin_scope") or src_scope
    if src_scope not in M.SCOPES:
        issues.append(f"scope {src_scope!r} not in destination SCOPES "
                      f"— needs mapping (default: repo)")
    lowered = (d["fact"] + " " + d["context"]).lower()
    for marker in M.PRIVACY_MARKERS:
        if marker in lowered:
            blockers.append(f"trips this repo's privacy marker {marker!r}")
    if len(d["fact"]) > M.FACT_MAX:
        blockers.append(f"fact exceeds {M.FACT_MAX} chars")
    if not meta.get("origin_repo"):
        issues.append("no origin_repo — raw memory dir, not a sealed bundle")

    collision = any(x["meta"].get("id") == fid for x in M.load_all())
    if collision:
        issues.append(f"id {fid!r} already exists here — needs a new id or a merge")

    query = " ".join(meta.get("keywords") or []) + " " + d["fact"]
    near = [(round(score, 1), x["meta"]["id"], x["fact"])
            for score, x in M.search(query, [], None, 3)]
    return {"id": fid, "issues": issues, "blockers": blockers,
            "fact": d["fact"], "tags": tags, "origin_scope": origin_scope,
            "collision": collision, "near": near}


def cmd_import_scan(a) -> int:
    source = Path(a.source)
    if not source.is_absolute():
        source = REPO / source
    if not source.exists():
        raise ExchangeError(f"no such source: {source}")

    if source.suffix == ".zip":
        dest = EXCHANGE / f"incoming-{source.stem}"
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        with zipfile.ZipFile(source) as z:
            z.extractall(dest)
        work = dest
        print(f"extracted bundle -> {work}")
    else:
        work = source

    mem = find_memory_dir(work)
    manifest = {}
    for cand in (work / "MANIFEST.yaml", mem.parent / "MANIFEST.yaml"):
        if cand.exists():
            manifest = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
            break

    docs = load_dir(mem)
    if not a.include_superseded:
        docs = [d for d in docs
                if d.get("parse_error") or d["meta"].get("status") == "active"]

    print(f"\nSOURCE   {mem}")
    if manifest:
        print(f"BUNDLE   {manifest.get('origin_repo')} / "
              f"{manifest.get('dimension')} "
              f"(framework {manifest.get('framework_version')}, "
              f"generalised={manifest.get('generalised')})")
        if manifest.get("framework_version") != M.FRAMEWORK_VERSION:
            print(f"  ! bundle framework {manifest.get('framework_version')} "
                  f"!= this install {M.FRAMEWORK_VERSION}")
    else:
        print("BUNDLE   none — raw memory directory; facts are NOT generalised")
    print(f"DEST     scopes={M.SCOPES} facts={len(M.load_all())}\n")

    reports = [portability_report(d) for d in docs]
    blocked = [r for r in reports if r["blockers"]]
    flagged = [r for r in reports if r["issues"] and not r["blockers"]]
    clean = [r for r in reports if not r["issues"] and not r["blockers"]]
    print(f"{len(reports)} candidate fact(s): {len(clean)} clean, "
          f"{len(flagged)} need a mapping decision, {len(blocked)} blocked\n")
    for r in reports:
        mark = "BLOCKED" if r["blockers"] else ("FLAG" if r["issues"] else "ok")
        print(f"[{mark:>7}] {r['id']} ({r['origin_scope']}) "
              f"[{','.join(r['tags'])}]")
        print(f"          {r['fact']}")
        for b in r["blockers"]:
            print(f"          BLOCKER: {b}")
        for i in r["issues"]:
            print(f"          issue:   {i}")
        for score, nid, nfact in r["near"]:
            print(f"          near({score}): {nid} — {nfact[:90]}")
    print(f"\nNext: build a plan with `import-plan --source {work}`, have the "
          "human resolve every conflict, then `import-apply --plan <file>`.")
    return 0


def cmd_import_plan(a) -> int:
    source = Path(a.source)
    if not source.is_absolute():
        source = REPO / source
    mem = find_memory_dir(source)
    docs = [d for d in load_dir(mem)
            if not d.get("parse_error") and d["meta"].get("status") == "active"]
    entries = []
    for d in docs:
        meta = d["meta"]
        r = portability_report(d)
        entries.append({
            "origin_id": meta.get("id"),
            "fact": d["fact"],
            "action": "UNRESOLVED",          # accept | merge | skip
            "id": meta.get("id"),
            "scope": meta.get("scope") if meta.get("scope") in M.SCOPES else "repo",
            "merge_into": None,
            "conflict": False,
            "resolution": None,
            "reason": None,
            "flags": (r["issues"] + r["blockers"]) or None,
        })
    plan = {
        "source": str(mem),
        "destination": str(REPO),
        "generated": datetime.now().isoformat(timespec="minutes"),
        "framework_version": M.FRAMEWORK_VERSION,
        "entries": entries,
    }
    out = Path(a.out) if a.out else (EXCHANGE / f"import-plan-{stamp()}.yaml")
    if not out.is_absolute():
        out = REPO / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(plan, sort_keys=False, allow_unicode=True),
                   encoding="utf-8")
    print(f"plan template -> {out}")
    print(f"{len(entries)} entr(ies), all action: UNRESOLVED. "
          "Every entry needs an explicit action before apply will run.")
    return 0


def cmd_import_apply(a) -> int:
    plan_path = Path(a.plan)
    if not plan_path.is_absolute():
        plan_path = REPO / plan_path
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    mem = Path(plan["source"])
    entries = plan.get("entries") or []
    if not entries:
        raise ExchangeError("plan has no entries")

    # ---- the hard rule, enforced before anything is written -------------
    refusals = []
    for e in entries:
        eid = e.get("origin_id")
        action = e.get("action")
        if action not in PLAN_ACTIONS:
            refusals.append(f"{eid}: action {action!r} is not one of {PLAN_ACTIONS}")
            continue
        if e.get("conflict") and not e.get("resolution"):
            refusals.append(f"{eid}: flagged as a conflict with no recorded "
                            "resolution — conflicting knowledge cannot be imported")
        if action == "accept" and e.get("scope") not in M.SCOPES:
            refusals.append(f"{eid}: scope {e.get('scope')!r} not in {M.SCOPES}")
        if action == "merge" and not e.get("merge_into"):
            refusals.append(f"{eid}: action merge requires merge_into")
    if refusals:
        print("IMPORT REFUSED — the plan is not fully resolved:")
        for r in refusals:
            print("  " + r)
        return 1

    by_id = {str(d["meta"].get("id")): d for d in load_dir(mem)
             if not d.get("parse_error")}
    today = date.today().isoformat()
    existing_by_id = {str(d["meta"].get("id")): d for d in M.load_all()}
    # A raw memory/ directory carries no origin_repo; the directory it came
    # from is the best provenance available, and beats recording "unknown".
    fallback_origin = plan.get("origin_repo") or mem.parent.name or "unknown"

    # ---- resolve every operation and validate it BEFORE writing anything --
    # An import is all-or-nothing: a fact that fails the gate halfway through
    # would otherwise leave the repository half-imported.
    ops: list[tuple[str, dict, str, str]] = []   # (kind, meta, fact, context)
    skipped: list[str] = []
    gate_errs: list[str] = []

    for e in entries:
        action = e["action"]
        if action == "skip":
            skipped.append(e["origin_id"])
            continue
        src = by_id.get(str(e["origin_id"]))
        if src is None:
            raise ExchangeError(f"{e['origin_id']}: not found in {mem}")
        smeta = src["meta"]

        if action == "accept":
            meta = {
                "id": e.get("id") or smeta["id"],
                "tags": list(smeta.get("tags") or []),
                "keywords": list(smeta.get("keywords") or []),
                "scope": e["scope"],
                "status": "active",
                # The tier arrives with the fact; `resolves` and `rule` do not,
                # because both name things that exist only in the source repo.
                "provenance": smeta.get("provenance") or "unverified",
                "checked": smeta.get("checked") or today,
                "created": today,
                "updated": today,
                "origin_repo": smeta.get("origin_repo") or fallback_origin,
                "origin_id": smeta.get("origin_id", smeta.get("id")),
                "origin_scope": smeta.get("origin_scope", smeta.get("scope")),
                "imported": today,
            }
            if smeta.get("source") and meta["provenance"] in (
                    M.PROVENANCE_NEEDS_SOURCE + ("documented",)):
                meta["source"] = smeta["source"]
            fact = e.get("fact_override") or src["fact"]
            context = e.get("context_override") or src["context"]
            path = M.MEMORY_DIR / f"{meta['id']}.md"
            if meta["id"] in existing_by_id:
                gate_errs.append(f"{meta['id']}: id already exists here — "
                                 "rename it or use action: merge")
        else:  # merge
            target = e["merge_into"]
            existing = existing_by_id.get(str(target))
            if existing is None:
                gate_errs.append(f"{e['origin_id']}: merge_into {target!r} "
                                 "does not exist here")
                continue
            meta = dict(existing["meta"])
            meta["updated"] = today
            # A merge folds a foreign fact into one that already exists here.
            # The surviving tier is the WEAKER of the two: merging an
            # `unverified` claim into an `observed` one cannot leave the result
            # claiming it was run and seen. `checked` follows the same rule and
            # takes the earlier date, so a merge can never refresh a
            # confirmation nobody performed.
            _incoming = smeta.get("provenance") or "unverified"
            _here = meta.get("provenance") or "unverified"
            meta["provenance"] = min(
                (_here, _incoming), key=lambda t: M.PROVENANCE.index(t))
            meta["checked"] = min(
                str(meta.get("checked") or today),
                str(smeta.get("checked") or today))
            if meta["provenance"] not in M.PROVENANCE_NEEDS_SOURCE + ("documented",):
                meta.pop("source", None)
            meta["keywords"] = list(dict.fromkeys(
                list(meta.get("keywords") or [])
                + list(smeta.get("keywords") or [])))
            meta["merged_from"] = (f"{smeta.get('origin_repo') or fallback_origin}"
                                   f":{smeta['id']}")
            fact = e.get("fact_override") or existing["fact"]
            context = e.get("context_override") or existing["context"]
            path = existing["path"]

        errs = M.validate({"meta": meta, "fact": fact, "context": context,
                           "path": path})
        gate_errs += [f"{meta['id']}: {x.split(': ', 1)[-1]}" for x in errs]
        ops.append((action, meta, fact, context))

    if gate_errs:
        print("IMPORT REFUSED — these facts do not pass this repository's gate:")
        for g in gate_errs:
            print("  " + g)
        print("\nNothing was written. Amend the plan (fact_override / rename / "
              "skip) and re-run.")
        return 1

    applied = [m["id"] for k, m, _, _ in ops if k == "accept"]
    merged = [m["id"] for k, m, _, _ in ops if k == "merge"]
    verb = "would apply" if a.dry_run else "applied"
    print(f"{verb}: {len(applied)} accepted, {len(merged)} merged, "
          f"{len(skipped)} skipped")
    for i in applied:
        print(f"  + {i}")
    for i in merged:
        print(f"  ~ {i}")
    if a.dry_run:
        print("\ndry run — nothing written; every operation passed the gate. "
              "Re-run without --dry-run to apply.")
        return 0

    for _kind, meta, fact, context in ops:
        M.write_fact(meta, fact, context)

    M.reindex()
    errs = M.lint_all()
    if errs:
        print("\nPOST-IMPORT LINT FAILED:")
        for e2 in errs:
            print("  " + e2)
        return 1
    print(f"\npost-import OKF lint OK ({len(M.load_all())} fact(s)). "
          "Now run the framework-lint skill for the cross-tier check.")
    return 0


# ---------------------------------------------------------------- structure

def cmd_structure(a) -> int:
    """Mechanical inventory of the whole framework, for framework-lint."""
    docs = M.load_all()
    active = [d for d in docs if d["meta"].get("status") == "active"]
    skip_parts = {".exchange", "node_modules", ".venv", ".git"}
    legislation = sorted(
        (p.parent.relative_to(REPO).as_posix() or ".")
        for p in REPO.rglob("CLAUDE.md")
        if not skip_parts & set(p.parts))
    units = [d for d in legislation if d != "."]
    scope_counts = {s: len([d for d in active if d["meta"].get("scope") == s])
                    for s in M.SCOPES}
    used_scopes = {str(d["meta"].get("scope")) for d in active}
    imported = [d["meta"]["id"] for d in active if d["meta"].get("imported")]

    out = {
        "framework_version": M.FRAMEWORK_VERSION,
        "repo": str(REPO),
        "constitution": (REPO / "CLAUDE.md").exists(),
        "legislation_files": legislation,
        "scopes": list(M.SCOPES),
        "privacy_markers": list(M.PRIVACY_MARKERS),
        "tags": list(M.TAGS),
        "fact_count_active": len(active),
        "fact_count_total": len(docs),
        "facts_per_scope": scope_counts,
        "empty_scopes": [s for s, n in scope_counts.items() if n == 0],
        "scopes_used_but_undeclared": sorted(used_scopes - set(M.SCOPES)),
        "units_without_a_matching_scope": [
            u for u in units
            if not any(s in u.replace("/", "-") or u.replace("/", "-") in s
                       for s in M.SCOPES)],
        "imported_facts": imported,
        "index_present": M.INDEX.exists(),
        "index_stale": bool(docs and M.INDEX.exists()
                            and M.render_index(docs)
                            != M.INDEX.read_text(encoding="utf-8")),
        "operating_skills": sorted(
            p.parent.name for p in (REPO / ".claude" / "skills").glob("*/SKILL.md")
        ) if (REPO / ".claude" / "skills").exists() else [],
    }
    print(json.dumps(out, indent=2))
    return 0


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="memory_exchange.py", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    el = sub.add_parser("export-list")
    el.add_argument("--scope", default=None, choices=(*M.SCOPES, None))
    el.add_argument("--tags", default="")

    es = sub.add_parser("export-stage")
    es.add_argument("--repo-name", required=True)
    es.add_argument("--dimension", required=True,
                    help='"all" or a sub-knowledge title, e.g. "Next.js App Router"')

    ea = sub.add_parser("export-add")
    ea.add_argument("--stage", required=True)
    ea.add_argument("--id", required=True)
    ea.add_argument("--tags", required=True)
    ea.add_argument("--keywords", required=True)
    ea.add_argument("--origin-id", required=True)
    ea.add_argument("--origin-scope", required=True)
    ea.add_argument("--fact", required=True)
    ea.add_argument("--context", default="")

    esl = sub.add_parser("export-seal")
    esl.add_argument("--stage", required=True)
    esl.add_argument("--out", default=None)

    isc = sub.add_parser("import-scan")
    isc.add_argument("--source", required=True)
    isc.add_argument("--include-superseded", action="store_true")

    ipl = sub.add_parser("import-plan")
    ipl.add_argument("--source", required=True)
    ipl.add_argument("--out", default=None)

    iap = sub.add_parser("import-apply")
    iap.add_argument("--plan", required=True)
    iap.add_argument("--dry-run", action="store_true")

    sub.add_parser("structure")

    a = ap.parse_args(argv)
    handlers = {
        "export-list": cmd_export_list,
        "export-stage": cmd_export_stage,
        "export-add": cmd_export_add,
        "export-seal": cmd_export_seal,
        "import-scan": cmd_import_scan,
        "import-plan": cmd_import_plan,
        "import-apply": cmd_import_apply,
        "structure": cmd_structure,
    }
    try:
        return handlers[a.cmd](a)
    except (ExchangeError, M.OkfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
