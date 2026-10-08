---
name: knowledge-import
description: >
  Import Common Law from elsewhere into this repository — an exported knowledge
  bundle (.zip), or another workspace's or repository's memory/ directory. Use
  when the user wants to bring in outside experience: "import the Next.js
  knowledge", "pull in the memory from the other repo", "load this bundle",
  "bring across what we learned on the last project", "reuse my other
  workspace's memory here". Scans the source for relevant facts, reconciles
  every one against THIS repository's Constitution and Legislation, and raises
  every conflict to the human to resolve. Conflicting knowledge is never
  imported — that is a hard rule. Always finishes with a full framework-lint.
---

# Import knowledge into this repository

Imported facts become Common Law here — the agent will act on them, and it will
apply them at exactly the moments it is least certain. So the bar is not "is
this fact true?" but **"is this fact true *here*, and does it sit under this
repository's Constitution and Legislation without contradicting them?"**

A fact that contradicts a law is worse than a missing fact: it makes the agent's
behaviour depend on which tier it happens to consult first. Hence the hard rule
below.

    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py import-scan  --source <zip|dir>
    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py import-plan  --source <dir>
    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py import-apply --plan <file> [--dry-run]

## The hard rule

**No fact that conflicts with this repository's Constitution or Legislation may
be written to `memory/`.** Not with a warning, not with a caveat in Context, not
"the human can sort it later". Only the human can clear a conflict, and they
clear it by changing something — the fact, the Legislation, or the Constitution
— never by waiving it.

`import-apply` enforces the mechanical half: any plan entry that is unresolved,
or flagged `conflict: true` with no recorded `resolution`, refuses the *entire*
import. Nothing partially applies.

## The questioning rule — ask per class, not per fact

Raise each decision the moment it appears, but raise it as a rule. "All eleven
of these came from the source's `services-api` scope — map them to `api` here,
or leave them at `repo`?" is one question that resolves eleven facts. Asking
per fact turns an import into an interrogation and the user stops reading.

Instance-level questions are reserved for **conflicts**. Those are never
batched into a rule, because each one is a decision about this project's law.

## Phase 1 — Find the source

Ask which of the two the user has, unless it is already obvious from the path:

- **An exported bundle** (`<repo>_<dimension>_<timestamp>.zip`) — facts are
  already generalised and carry provenance. The normal case.
- **A raw `memory/` directory** from another workspace or repository — facts
  are still written for *that* project. They have not been generalised, so
  expect to rewrite most of them during review, and expect a lower keep rate.
  Say this up front; it sets the right expectation for the report.

If they have neither to hand, offer to look: bundles usually sit in
`.exchange/`, and a sibling repository's memory is at `<repo>/memory/`.

## Phase 2 — Scan

    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py import-scan --source <zip|dir>

The scan reports, per fact: destination-gate blockers (foreign tags, privacy
markers this repo declares, oversized facts), mapping issues (unknown scope, id
collision), and near-duplicates already here. It writes nothing.

Then do the part the tool cannot: **decide what is relevant**. For a targeted
bundle that is usually everything. For a foreign `memory/` directory it rarely
is — most of another project's Common Law is about that project. Read the
corpus and select; report what you rejected wholesale so the user can push back
on the boundary.

## Phase 3 — Reconcile against the law

This is the heart of the import. Read, for real:

- the root `CLAUDE.md` — values and every supreme law;
- the `CLAUDE.md` of each unit an incoming fact would land in;
- the existing facts the scan flagged as near-duplicates.

Then classify every candidate:

| Verdict | Meaning | Plan action |
|---|---|---|
| **Clean** | Consistent with the law here, adds something | `accept` |
| **Duplicate** | This repo already knows it | `merge` into the existing fact, or `skip` |
| **Irrelevant** | True, but not about anything this repo does | `skip` |
| **Conflict** | Contradicts a supreme law, a unit law, or an existing fact | `conflict: true` — blocked until resolved |

What counts as a conflict:

1. **Against a supreme law** — the fact recommends, assumes, or normalises
   something a supreme law forbids. ("Run the seed script against prod to
   reproduce" vs. a never-touch-prod law.)
2. **Against Legislation** — the fact prescribes a pattern the unit's laws
   forbid, or assumes an architecture this unit does not have.
3. **Against an existing fact** — two facts that cannot both be acted on.
4. **Against reality here** — the fact depends on a tool, version, or service
   this repository does not use. Often mistaken for a conflict; it is usually
   just irrelevant. Check before escalating.

A fact that is merely *stricter* than local law is not a conflict — it is a
preference, and it is the user's call whether to adopt it. Say which it is.

## Phase 4 — Resolve conflicts with the human

Present each conflict individually and concretely: the incoming fact, the exact
law or fact it contradicts, quoted, and what would go wrong if both were
believed. Then offer the four resolutions — and only these four:

1. **Drop the fact.** The law wins. Most common, and the safe default.
2. **Amend the fact** so it no longer contradicts — usually by narrowing it to
   the conditions under which it is true here. Record the amended wording.
3. **Amend the Legislation.** The incoming knowledge shows a unit law is wrong
   or too broad.
4. **Amend the Constitution.** The incoming knowledge shows a supreme law is
   wrong.

Record the chosen resolution in the plan entry's `resolution` field, in the
user's words. An entry with `conflict: true` and an empty `resolution` blocks
the whole import.

> **Options 3 and 4 need their own sign-off.** Changing Legislation, and above
> all changing the Constitution, is a legislative act — it must not ride along
> inside an import approval. Make the edit a separate, explicit proposal:
> show the current text, the proposed text, and what else it affects. Get a yes
> to *that* on its own. Apply the CLAUDE.md edit first, then re-run the scan so
> the fact is reconciled against the law as it now stands. A Constitution
> amended to accommodate an import is exactly the failure mode the Constitution
> exists to prevent, so it should be rare, deliberate, and visible.

## Phase 5 — Plan and one sign-off

    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py import-plan --source <dir> --out .exchange/plan.yaml

Fill in every entry: `action` (`accept` / `merge` / `skip`), destination `id`
(rename on collision — a source-repo prefix works well), destination `scope`
(from the mapping rule you agreed in Phase 2), `merge_into` for merges,
`conflict` + `resolution` where they applied, and `fact_override` /
`context_override` where the wording was amended.

Present one summary — N accepted, N merged, N skipped, every conflict with its
resolution, the scope mapping, and any renames — and wait for approval.

Then dry-run before you write:

    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py import-apply --plan .exchange/plan.yaml --dry-run
    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py import-apply --plan .exchange/plan.yaml

Every accepted fact passes the same OKF gate as a locally captured one, keeps
its `origin_repo` / `origin_id` / `origin_scope` provenance, and is stamped
`imported`. `MEMORY.md` regenerates automatically.

## Phase 6 — Verify the whole framework

An import is not complete when the facts land. Run the **framework-lint** skill
over the repository: mechanical integrity (OKF gate, index freshness, scope and
Legislation parity, hook and skills present) *and* the semantic sweep for
contradictions across Common Law, Legislation and Constitution.

If framework-lint finds a contradiction the reconciliation missed, that is a
failed import: supersede or delete the offending imported facts, then re-run
the lint until it is clean. Report what was rolled back — a quiet rollback is
how the next import repeats the same mistake.

## Rules

- Never hand-copy files into `memory/`. The import exists to catch conflicts;
  copying skips it.
- Never apply a partially resolved plan — the tool refuses, and so should you.
- Never resolve a conflict on the user's behalf, and never resolve one by
  weakening the fact until it says nothing.
- Never import `superseded` facts; history does not travel.
- Provenance stays on the fact. A year from now, "where did this come from?"
  must have an answer.
- Report the rejects. What you refused to import is as informative as what you
  brought in.
