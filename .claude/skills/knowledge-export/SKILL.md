---
name: knowledge-export
description: >
  Export this repository's Common Law as a portable, GENERALISED knowledge
  bundle — all of it, or one dimension of it. Use when the user wants to take
  what this project learned somewhere else: "export what we learned about
  Next.js", "bundle up the Tailwind experience", "export the memory for the new
  repo", "share our testing knowledge with the other team", "export all the
  common law", or names a technology/topic and asks for it as a package. The
  export REASONS over each fact and rewrites it as transferable knowledge — the
  lesson without the project — then seals OKF files into
  <repo>_<all|dimension>_<yyyyMMddHHmm>.zip, usable in any OKF filesystem.
  Read-only against memory/; nothing in this repository is modified.
---

# Export knowledge along a dimension

A fact recorded here is written for here. `"Stride's checkout server action
throws on /cart because it is called before hydration"` is true and useful — and
worthless in another repository. The exportable version is the lesson
underneath: `"A Next.js App Router server action invoked from a client
component before hydration fails silently rather than throwing."`

That rewrite is the whole point of this skill. Copying `memory/` into another
repo is not an export; it is contamination. **Every staged fact must be true in
a repository that has never heard of this project.**

Everything runs through the exchange tool, which shares `memory.py`'s OKF gate —
a staged fact that would fail the gate never lands:

    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py export-list [--scope <unit>] [--tags <t>]
    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py export-stage --repo-name <name> --dimension "<all|title>"
    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py export-add --stage <dir> ...
    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py export-seal --stage <dir>

## The questioning rule — ask per class, not per fact

Judgement calls will surface: a fact that names a client, one that may be two
lessons, one whose generalisation is a guess. **Raise each one the moment it
appears** — do not batch them to the end, and do not carry an unresolved
question into the bundle.

But raise it as a *class*, not an instance. The first time a kind of decision
appears, ask the guiding question, get the rule, then apply that rule silently
to every later fact of the same kind. "Six facts name the client by name — strip
the name and keep the lesson?" is one question. Asking it six times is how a
twenty-fact export becomes an afternoon.

## Phase 1 — Name the dimension

Confirm two things before reading anything: the **repository name** for the
filename (default: the directory name) and the **dimension**.

A dimension is any axis the user thinks in — a technology (`Next.js`,
`Tailwind`), a concern (`testing`, `accessibility`), a unit, or `all`. It is not
restricted to tags or scopes; those are filters, not the dimension itself.

If the request is vague ("export the useful stuff"), propose two or three
concrete dimensions drawn from what the corpus actually contains, and let the
user pick.

## Phase 2 — Shortlist

Run `export-list` to get the full active corpus (one line per fact — cheap even
at hundreds of facts), then decide relevance **by reading**, not by keyword
match. `search` is an accelerator for a large corpus, not the selector: a fact
about hydration order belongs in a Next.js export whether or not it contains the
string "next".

Show the shortlist and the near-misses you rejected. A user who sees "I left out
these four" corrects the boundary in one line; a user who sees only the
inclusions cannot.

## Phase 3 — Generalise, one fact at a time

For each shortlisted fact, write the version that survives leaving this
repository. Work through it in this order:

1. **Find the lesson.** Why would someone in another project want to know this?
   If there is no answer, the fact is not exportable — say so and move on.
2. **Strip the particulars.** Project names, client names, internal service
   and file names, bespoke paths, ticket numbers, people. Replace a specific
   with the general category it stands for (`/cart` → "a client component";
   `PaymentsGateway` → "a payment adapter").
3. **Keep what makes it actionable.** Versions, tool names, error text and
   conditions are what make the fact useful — a lesson generalised into
   `"be careful with server actions"` is worse than no fact at all. Strip the
   *identity* of the project, not the *specificity* of the knowledge.
4. **Re-check the tag.** A project `issue` is usually general `knowledge`; a
   project `fix` is often a general `preference` or `knowledge`. Tag what the
   fact now IS, not what it was.
5. **Re-derive keywords** for the destination's vocabulary — the terms someone
   else would search, not this repo's internal names.

Then stage it:

    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py export-add --stage <dir> \
        --id <kebab-id> --tags <tag[,tag]> --keywords <k1,k2> \
        --origin-id <the source fact id> --origin-scope <its scope here> \
        --fact "<one generalised sentence, <=240 chars, ends with a full stop>" \
        [--context "<how to apply it, <=10 lines>"]

Staged facts always land as scope `repo` with the source scope preserved in
`origin_scope` — `repo` exists in every installation, so the bundle is
lint-clean anywhere. The destination remaps during import; that is not this
skill's decision to make.

### Surface it now, not later

Ask the moment one of these appears — then apply the answer to every subsequent
fact of the same kind:

| What you hit | Ask (once, as a rule) |
|---|---|
| Names a client, employer, or person | "Strip the name and keep the lesson, or drop these facts entirely?" |
| Two lessons in one fact | "Split into two exportable facts?" — the gate rejects multi-sentence facts anyway |
| Generalising loses the point | "This only makes sense with our architecture — drop it, or export it with the caveat in Context?" |
| A fix to a bug in *our* code | "Is the lesson about the language/framework (exportable) or about our code (not)?" |
| Ambiguous scope of a claim | "Does this hold for the framework generally, or only at the version we pin?" |

## Phase 4 — Seal

    D:\Games\.venv\Scripts\python.exe scripts/memory_exchange.py export-seal --stage <dir>

Seal lints the whole staged set against the OKF gate, writes `MANIFEST.yaml`
(origin repo, dimension, framework version, tag taxonomy, origin scopes) and a
human-readable `README.md`, and zips to:

    <repository-name>_<all|dimension-slug>_<yyyyMMddHHmm>.zip

e.g. `stride_all_202607311430.zip`, `stride_nextjs-app-router_202607311430.zip`.
Inside, facts sit under `memory/` so the bundle drops straight into any OKF
filesystem.

If seal fails the lint, fix the staged fact and re-seal — never hand-edit a
staged file to get past the gate.

## Phase 5 — Report

- The dimension, the fact count, and the bundle path.
- **What was left behind and why** — rejected as not-transferable, dropped by a
  rule the user gave, or too project-bound to survive. This is the most useful
  part of the report; it is the user's chance to overrule a boundary call.
- Any generalisation you were unsure of, named explicitly.

## Rules

- Never export a fact you have not reasoned over. A verbatim copy in a bundle
  is the failure mode this skill exists to prevent.
- Never export `superseded` facts — superseded knowledge is history, and
  history does not travel.
- Never invent a fact the corpus does not support, and never merge two facts
  into one "richer" fact; one key fact per file is the standard everywhere.
- Read-only against `memory/`: exporting never modifies, supersedes, or
  reindexes this repository's Common Law.
- Personal or secret content must not reach a bundle. The gate blocks the
  markers it knows; you are responsible for the ones it does not — a bundle is
  built to be sent to someone else.
