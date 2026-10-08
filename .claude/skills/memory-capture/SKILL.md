---
name: memory-capture
description: >
  Capture a new atomic fact into Repository Memory (Common Law) via
  scripts/memory.py. Use in exactly four situations: (1) the user CHALLENGES a
  prior outcome — record the corrected understanding, run in the BACKGROUND so
  the main task keeps moving; (2) a statement in a CLAUDE.md (Constitution or
  Legislation) is CLARIFIED — explained, not changed — record the clarified
  interpretation as a PRECEDENT carrying `--rule`; (3) net-new KNOWLEDGE
  relevant to the workspace topic is provided and the conversation shows the
  model did not know it prior — record the learned fact, tag `knowledge`, run in
  the BACKGROUND; (4) an issue recorded earlier is RESOLVED — record the
  resolution as a `fix` carrying `--resolves`, which closes the open case. Never
  used to change a rule; only to record a learned fact. All writes go through
  scripts/memory.py (the OKF schema gate).
---

# Capture a learned fact

Turn a moment of learning into one atomic, reusable OKF fact. Writes go only
through the single point of contact, which enforces the schema and blocks
personal/secret content:

    D:\Games\.venv\Scripts\python.exe scripts/memory.py create --id <kebab-id> --tags <tag[,tag]> \
        --keywords <k1,k2> --scope <repo, roms, rom-sync, torrents, firmware, tools> --provenance <tier> \
        --fact "<one sentence, <=240 chars, ends with a full stop>" \
        [--context "<<=10 lines of how-to-apply detail>"] \
        [--source "<who stated it and when>"] [--checked <YYYY-MM-DD>] \
        [--resolves <issue-id>] [--rule <unit>#<rule-name>]

## Every fact declares how it is known

`--provenance` is not paperwork. The tier governs what may later be done with
the fact, so a wrong tier is worse than a missing one:

| Tier | Means | You may |
|---|---|---|
| `observed` | It was run and the result was seen | Rely on it, and cite it against a contradicting document |
| `documented` | The vendor's own material says so, untested | Repeat what is claimed — never assert the thing behaves that way |
| `contractual` | An authoritative statement made outside the documentation: entitlement, commercial terms, support-channel guidance | Rely on it, **only** with `--source` naming who said it and when |
| `unverified` | Inference, or a house rule that asserts nothing about external behaviour | Treat as a working assumption, and say so |

**The tier follows where the AUTHORITY sits, never the subject matter.** A
workaround a vendor engineer recommends that the documentation does not sanction
is `contractual`, never `documented` — relabelling it empties the one tier whose
job is to tell the next reader where to go and re-check. An unattributed
`contractual` claim is `unverified` wearing a better label, and the gate rejects
it, placeholders included.

`--checked` is the date the claim was last confirmed true, defaulting to today.
It is **not** the date the file was edited: rewording a fact never refreshes it.
On `update`, pass `--checked today` only when you actually re-confirmed the
claim. `observed` and `documented` facts age; `unverified` never does, because it
was never fresh.

## The two kinds of fact

A fact is a CASE or a PRECEDENT, and the kind decides how it reaches a decision.

**A case** is an issue and, when one is found, the resolution that closes it.
Retrieved by search, from a symptom, mid-investigation. Modes 1, 3 and 4.

**A precedent** is a fine-tuned reading of a rule in a CLAUDE.md. Retrieved
deterministically by `--rule`, because by the time anyone would think to search
for an interpretation they have already read the rule and formed their own.
Precedent is pushed by the index and the SessionStart hook, never pulled. Mode 2.

## Mode 1 — a challenge (run ASYNC)

When the user challenges an outcome (they say it's wrong, question why you did
something, or correct your result):

1. First **resolve the challenge in the main flow** — the user's task comes first.
2. Then spawn the capture as a **background subagent** (Agent tool,
   `run_in_background: true`). The subagent:
   - distils the corrected understanding into ONE fact, tag **`fix`** (or
     `issue` if it's a newly-found problem not yet fixed);
   - `search`es first — if a near-duplicate exists, `update` it instead of
     creating a second;
   - sets `--provenance` from how the correction was established;
   - if this closes a recorded issue, adds `--resolves <issue-id>`;
   - writes it via `memory.py create`.
3. Do not make the user wait on the capture.

## Mode 2 — a CLAUDE.md clarification, captured as PRECEDENT

When a Constitution/Legislation statement is *clarified* — the user explains what
an existing rule means, without changing or pivoting from it — record the
clarified interpretation so it isn't re-litigated:

- tag **`example`** (a worked interpretation) or `preference`;
- **`--rule <unit>#<rule-name>`** naming what is being construed —
  `constitution#law-2`, `agents#retrieval`. This is what makes it a precedent
  rather than an opinion, and a reading that does not cite the rule it construes
  is not a precedent at all;
- `--scope` = the unit the CLAUDE.md governs (repo for the Constitution);
- `--provenance unverified` unless the reading rests on something stronger — a
  reading of a rule is a decision about meaning, not a claim about the world;
- state the interpretation itself, not the conversation: "the <rule> covers X but
  not Y", never "the user said the rule means X";
- this does NOT edit the CLAUDE.md — if the rule itself should change, that's a
  Constitution/Legislation edit, not a memory capture.

## Mode 3 — net-new knowledge (run ASYNC)

When knowledge relevant to the workspace topic is supplied *and the conversation
shows it was not already known to the model* — a domain fact, a system's actual
behaviour, a constraint, or a relationship the model got wrong or plainly lacked
— record it so it need not be re-supplied next session.

The net-new test is **conversational, not introspective**: capture only when the
transcript itself shows the gap — the model asked and was told, guessed wrong and
was corrected, or was handed a fact it evidently did not have. Do not judge
against training knowledge; if there is no visible gap in the conversation, do
not capture. General knowledge the model already had is not Common Law and only
bloats the corpus.

1. Do not block the conversation — spawn the capture as a **background subagent**
   (Agent tool, `run_in_background: true`).
2. The subagent:
   - distils the supplied knowledge into ONE atomic fact, tag **`knowledge`**;
   - `--scope` = the unit the knowledge pertains to (repo for cross-cutting);
   - sets `--provenance` from how the user knows it, asking if it is unclear
     rather than assuming the strongest tier;
   - `search`es first — if a near-duplicate exists, `update` it (refining it if
     the new information is sharper) instead of creating a second;
   - writes it via `memory.py create`.
3. Capture the knowledge, not the conversation around it — the fact should read
   as a standing truth about the workspace, not as "the user told me X".

The line against Mode 2: Mode 2 *interprets an existing rule*; Mode 3 *records a
fact the Legislation never covered*. If the knowledge implies a rule **should**
exist, that's a Legislation edit, not a capture.

## Mode 4 — a resolution closes an open case

When work resolves a problem already recorded as an `issue`:

- capture the resolution as its own fact, tag **`fix`**, with
  **`--resolves <issue-id>`**;
- that link is what closes the case. "Open" is derived from it and stored nowhere
  else, so the state has one owner and nothing to drift out of step;
- do NOT edit the issue to say it is fixed. The issue records what went wrong and
  stays true; the fix records what closed it. Two facts, one edge;
- if the fix turns out not to hold, `supersede` the fix — the case reopens by
  itself, because nothing else was asserting it closed.

An issue that stays open is not a failure. Under law 3 an unresolved finding is
provisional and legitimate; what it must carry is the **open question** — what
has not yet been excluded — in its Context. `memory.py lint` warns about issues
carrying none, and `memory.py audit` lists every open case.

## Rules

- ONE fact per capture (the gate rejects multi-sentence facts). Split extras.
- Never include personal/secret data — the gate blocks it, and it must never be
  in shareable repo memory anyway (Constitution law 1).
- Prefer the weaker tier when unsure. Downgrading a fact costs nothing;
  discovering that a confident claim was never verified costs a decision.
- After any capture, `memory.py` regenerates `MEMORY.md` automatically.
