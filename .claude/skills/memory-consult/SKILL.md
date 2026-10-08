---
name: memory-consult
description: >
  Consult Repository Memory (the Common Law tier) BEFORE acting — at Ambiguity
  Events and at the start of investigation, design, and verification work. Use
  when: a requirement is unclear, under-specified, or you are guessing; you are
  about to investigate a bug or unexpected behaviour; you are designing or
  choosing between approaches; you are starting a verification / QA pass; or you
  need a domain fact about how this workspace actually works. Runs
  scripts/memory.py search and applies the relevant prior facts before you
  proceed, so past experience shapes the work instead of being rediscovered.
---

# Consult memory before acting

Repository Memory is the accumulated experience of this codebase as atomic OKF
facts under `memory/`. Query it through the single point of contact:

    D:\Games\.venv\Scripts\python.exe scripts/memory.py search "<keywords>" [--tags ...] [--scope <unit>] \
        [--provenance ...] [--rule ...] [--open] [--stale-days N] [--top 5]

## Search with KEYWORDS, never with the sentence you were asked

This is the single largest determinant of whether the consult is worth running.
The scorer matches **substrings**, so a short function word matches nearly every
fact: pass a natural-language question and the whole corpus scores above zero and
the ranking collapses into noise. Measured on a 135-fact corpus, the same
information need returned **0.38 recall** as a keyword query and **0.11** as the
user's own sentence, at the same result count.

So: read the situation, name the concepts, query those.

> "the widget came back empty and I don't know why"
> → `search "widget empty render absent"`

Two or three narrow queries beat one broad one. If the first returns nothing,
re-phrase in the workspace's own vocabulary before concluding memory is silent —
an absent result is evidence about the query at least as often as about the
corpus.

## Pick the mode, then query

| Situation (why you invoked) | Tag filter | What to do with hits |
|---|---|---|
| **Ambiguity** — unclear/under-specified requirement | *(none — broad)* | Resolve the ambiguity using the fact; if none applies, state the assumption you're making so it's visible. |
| **Investigation** — a bug / unexpected behaviour | `--tags issue,fix,knowledge` | Check whether this class of problem is already known and how it was closed before reproducing from scratch. Add `--open` to see what is still unresolved. |
| **Design** — choosing an approach | `--tags preference,issue,knowledge` | Steer the design away from recorded pitfalls and toward established preferences; note which fact shaped the choice. |
| **Domain grounding** — you need a fact about how this workspace actually works | `--tags knowledge` | Apply what was previously established rather than re-deriving or re-asking; if nothing is found, ask the user rather than assuming. |
| **Verification** — starting a QA/verify pass | `--tags verification,fix` | Fold prior verification lessons into the plan (what broke before, what to re-check). |

Scope the query with `--scope repo, roms, rom-sync, torrents, firmware, tools` when the work is in one unit; omit for
cross-cutting concerns (repo-scoped facts always match).

## Read the provenance before you rely on a hit

Every result prints its tier. It is not decoration — it decides what the fact
licenses:

- **`observed`** — run and seen. Rely on it. Under law 3 it outranks a
  contradicting document for immediate work.
- **`documented`** — claimed by the vendor, untested. Report what is *claimed*.
  Never restate it as how the thing behaves; that is the rounding-up law 2
  forbids.
- **`contractual`** — authoritative but unpublished, and it names its source.
  Rely on it, and cite the source when you do.
- **`unverified`** — inference, or a house rule. Usable as a working assumption,
  and say that it is one.

A result flagged **STALE** was last confirmed long enough ago that the thing it
describes may have moved. Treat it as a lead to re-check, not as a finding.

## Precedent arrives on its own — do not go looking for it

Facts carrying a `rule:` are settled readings of a rule in a CLAUDE.md. They are
**pushed**: Constitution-scoped precedent is emitted by the SessionStart hook, and
all precedent is rendered at the top of `MEMORY.md`, grouped by the rule it
construes. By the time you would think to search for an interpretation, you have
already read the rule and formed one of your own, so a precedent you had to look
up arrived too late to do its job.

Use `--rule <unit>#<rule-name>` only to pull the full set for a rule you are
actively applying. Otherwise, apply the readings already in front of you rather
than re-litigating them.

## Rules

- **Search before you guess.** One query is cheap; a rediscovered pitfall is not.
- Cite the fact you applied (its id) in your reasoning so the influence is
  traceable, and cite its tier when the tier is what makes it usable.
- If nothing relevant is found, proceed — but say so, and if the work later
  yields a durable lesson, capture it (see the `memory-capture` skill).
- If you close a problem that memory had recorded as an open issue, capture the
  resolution with `--resolves`. An open case nobody ever closes is the corpus
  quietly asking a question that has already been answered.
- Never hand-read or hand-edit `memory/`; recall is read-only through `memory.py`.
