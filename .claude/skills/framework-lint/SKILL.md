---
name: framework-lint
description: >
  Verify the whole Legal Framework of this repository — technical integrity AND
  the absence of contradictions between Common Law, Legislation and the
  Constitution. Use when the user asks to "lint the framework", "check the
  legal framework", "verify my agent context", "is my memory consistent with my
  CLAUDE.md", "audit the constitution and memory", after importing knowledge
  from elsewhere (the import's mandatory final step), after editing a
  Constitution or Legislation file, before a release, or when taking over a
  repository someone else set up. Runs the mechanical gates and then reads the
  three tiers against each other. Reports; repairs only with approval.
---

# Lint the whole framework

`memory.py lint` proves every fact is *well-formed*. It cannot prove the facts
are *consistent with the law they sit under* — that needs reading, not parsing.
This skill does both passes and reports one verdict.

The failure it exists to catch: a Constitution that says one thing, a
Legislation file that assumes another, and a memory fact that records a third.
Each tier is individually valid; the agent's behaviour depends on which one it
happens to load first. That is worse than any single wrong rule.

## Pass 1 — Mechanical

    D:\Games\.venv\Scripts\python.exe scripts/memory.py lint
    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py structure
    echo {} | D:\Games\.venv\Scripts\python.exe scripts/memory_hook.py

`structure` returns the inventory the rest of this pass needs. Check:

| Check | Fail looks like |
|---|---|
| OKF gate | `lint` non-zero — schema, privacy markers, duplicate ids |
| Index freshness | `index_stale: true` — `MEMORY.md` drifted from `memory/` |
| Scope integrity | `scopes_used_but_undeclared` non-empty — a fact points at a scope `SCOPES` doesn't declare |
| Legislation parity | `units_without_a_matching_scope` — a governed unit no memory can be scoped to |
| Constitution index | The Legislation table in root `CLAUDE.md` lists files that don't exist, or omits ones that do |
| Operating skills | `memory-consult`, `memory-capture`, `task-sense-check`, `knowledge-export`, `knowledge-import`, `framework-lint` all present |
| Hook | Non-zero exit, or not wired in `.claude/settings.json` |
| Version | `framework_version` older than the installed `legal-framework` skill — needs its Upgrade mode |

`empty_scopes` is not a failure. A scope with no facts yet is a scope nobody
has learned anything in.

## Pass 2 — Semantic, across the tiers

Read the root `CLAUDE.md`, every unit `CLAUDE.md`, and `MEMORY.md` (drop into
individual facts where a one-liner is ambiguous). Then check each direction:

**Common Law vs Constitution.** Does any fact recommend, assume, or normalise
something a supreme law forbids? A fact that describes a workaround for a guard
the Constitution installed deliberately is the classic hit.

**Common Law vs Legislation.** Does any fact prescribe a pattern the owning
unit's laws forbid, or assume an architecture that unit no longer has? Facts
outlive refactors — this is where staleness shows up as contradiction.

**Common Law vs Common Law.** Two active facts that cannot both be acted on.
Usually one superseded the other in practice and nobody ran `supersede`.

**Legislation vs Constitution.** Does a unit law permit what a supreme law
forbids, or restate a supreme law in weakened terms? A restatement that drifts
is more dangerous than no restatement, because the unit file is what gets loaded
while working in that unit.

**Legislation vs Legislation.** Two units giving opposite instructions about a
shared boundary — the API's contract described one way in the client's
Legislation and another in the server's.

Pay particular attention to facts stamped `imported` and to any unit changed
since the facts scoped to it were written. Those are where contradictions
concentrate.

## Pass 3 — Report and repair

One report:

- **Mechanical**: each check pass/fail, with the failing detail.
- **Contradictions**: for each, the two texts quoted, which tiers they sit in,
  and which one you believe is wrong — with your reasoning, and stated as your
  reading rather than a verdict.
- **Verdict**: clean, clean-with-observations, or contradictions-found.

Then repair, under these limits:

- **Repair freely**: `reindex` when the index is stale. It is generated.
- **Repair on approval**: everything else. Superseding a fact, editing
  Legislation, editing the Constitution, changing `SCOPES` — each is a change
  to the project's law and needs the human to say which side wins.
- **Never**: hand-edit `memory/` or `MEMORY.md`, or resolve a contradiction by
  softening both sides into agreement. One of them is wrong; the point of the
  lint is to find out which.

Re-run both passes after any repair. A framework-lint that ends on an unverified
repair has not finished.

## Rules

- Higher tier wins by default when proposing a resolution — Constitution over
  Legislation over Common Law — but say so as a default, not a law. Sometimes
  the fact is right and the Constitution is stale, and that is the most valuable
  finding this skill produces.
- Report contradictions you are unsure about. A false positive costs one line of
  the user's attention; a missed one costs the agent's consistency.
- Never conclude "clean" on the mechanical pass alone. If the semantic sweep was
  skipped or truncated, say that instead.
