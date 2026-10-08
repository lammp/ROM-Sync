---
name: memory-promote
description: >
  Codify a recurring Common Law pattern into Legislation — draft the rule, take
  it to sign-off, never write it unilaterally. Use when `scripts/memory.py
  promote` reports a theme learned many times that the governing CLAUDE.md
  barely mentions, when the user asks "what should be a rule by now", "promote
  this to legislation", "codify what we keep learning", "why do we keep
  re-deriving this", or after a `reflect` run shows a cluster being consulted
  over and over. Produces a drafted Legislation edit for human approval. Never
  edits a CLAUDE.md directly and never deletes the facts it promotes.
---

# Promote accumulated experience into a rule

Common Law accumulates. When the same lesson has been learned enough times, and
keeps being reached for, it has stopped being experience and become a rule. This
skill is the staircase between the two tiers — the point at which repeated
precedent gets codified into statute.

    D:\Games\.venv\Scripts\python.exe scripts/memory.py promote [--top 8] [--min-cluster 4]

The command counts; it does not decide. It reports themes that clear two gates:

- **Frequency** — the theme appears in at least `--min-cluster` facts. Learned
  once is an anecdote; learned nine times is a pattern.
- **Absence** — the governing `CLAUDE.md` barely mentions it. A theme the
  Legislation already covers needs no promotion, however often it recurs.

It also reports **demand** from `reflect`: how often those facts are actually
surfaced and opened. Frequency without demand is a theme that got written down a
lot; demand without frequency is one easy to retrieve. A rule is what you would
otherwise look up again and again, so both must be present.

## The three rules of promotion

**1. Never edit a CLAUDE.md yourself.** Legislation is authored content and the
human's own words. Draft the edit, show it, and wait. An agent that edits the
rules it is governed by has stopped being governed by them. This is the same
wall as law 5: drafting is allowed, committing is not.

**2. Never delete the facts you promote.** The rule states the position; the
facts remain as its evidence. Deleting them leaves a rule nobody can re-check,
and re-checking is the entire reason the provenance tiers exist. A promoted fact
is unchanged — not superseded, not retagged.

**3. The weakest tier in the cluster bounds what the rule may assert.** `promote`
reports it. A rule drafted from a cluster containing one `unverified` fact cannot
be worded as established behaviour, however many `observed` facts sit beside it.
Word it as the practice to follow, not as a claim about how the platform works —
"attach the page item rather than passing a URL" survives a tier that "the URL
path returns nothing" does not.

## Drafting

1. **Read the constituent facts** — all of them, via `memory.py read <id>`,
   not just the one-line index entries. The Context blocks carry the how-to-apply
   detail and the open questions, and both shape the wording.
2. **Find the through-line.** The rule is not a summary of the facts. It is the
   instruction someone would need in order not to relearn them. If you cannot
   state it without listing the facts, the cluster is not ready.
3. **Match the file's idiom.** Read the target `CLAUDE.md` first and write in its
   register, at its heading depth, with its level of specificity. A promoted rule
   that reads like it came from somewhere else will be ignored.
4. **Cite the evidence.** The rule names the fact ids it rests on, so the next
   reader can go back to the atoms. A rule with no citation is an assertion.
5. **Keep it short.** Legislation is loaded whenever the directory is worked in.
   A rule that costs a paragraph must save more than a paragraph.

## Presenting for sign-off

Show, in this order: the proposed rule text verbatim; which file and where in it;
the fact ids it rests on and their tiers; the weakest tier and what that permits;
and what changes in practice if it is adopted. Then stop.

If the human declines, that is a complete outcome. Record nothing — a rejected
promotion is not a fact, and writing "we decided not to codify X" turns a
judgement into apparent precedent.

## When NOT to promote

- The cluster is one incident described from several angles. That is one fact
  badly split, and the fix is consolidation, not codification.
- The facts contradict each other. Resolve the contradiction first; a rule built
  over an unresolved divergence hard-codes the confusion.
- The theme is about a specific tool, version, or configuration that is likely to
  change. That belongs in Common Law, where it can go stale honestly and carry a
  `checked` date. Legislation has no staleness mechanism, which is exactly why
  only durable positions belong there.
- The rule would restate something the Constitution already says. Legislation
  governs a unit; it does not re-litigate supreme law.
