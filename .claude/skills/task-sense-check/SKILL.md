---
name: task-sense-check
description: >
  End-of-task sense check, run BEFORE reporting substantive work complete. Use
  when you are about to conclude a task, land a change, or say "done": confirm
  every dimension is covered and surface any known issues with the
  implementation, cross-referenced against Repository Memory. Answers two
  questions explicitly and honestly — are all dimensions covered? are there
  known pitfalls that apply here and are they handled?
---

# Sense-check before concluding

A final pass that catches the gap you'd otherwise ship. Two parts: dimension
coverage, and known-issue recall from memory.

## 1. Dimensions — are they all covered?

Walk the dimensions that apply to what you changed and mark each covered / not /
n-a, in one line each:

- **Correctness** — does it do what was asked, including edge cases?
- **Off-limits paths** — nothing read, moved, deleted or counted under `_torrents\_incomplete` or the legacy `Downloading` (law 2).
- **C: / outside D:\Games** — no library data written, moved or staged outside `D:\Games`; any access outside it was prompted and approved (laws 3, 5).
- **No permanent deletion** — every removal or move of library files went through the `save` skill / SavePoint.ps1, recycled with a manifest, never hard-deleted (law 4).
- **Device safety** — nothing written to or wiped from a connected device without explicit approval for that action; ROM-Sync's own sync is exempt.
- **No procurement** — no purchase, sign-up, login or price research was performed (law 6).
- **Tests** — new behaviour covered; suites green.
- **Privacy** — nothing personal/secret staged (Constitution law 1).
- **Docs / memory** — Legislation and memory updated if the change is durable.

If a dimension that applies is NOT covered, say so plainly — do not round up to
"done."

## 2. Known issues — does memory warn about this?

Query the experience layer for pitfalls touching this work:

    D:\Games\.venv\Scripts\python.exe scripts/memory.py search "<area keywords>" --tags issue,fix,verification

For each relevant hit: does the pitfall apply here, and is it handled? List any
that apply and are NOT yet addressed as an explicit caveat in your final report.

## Output

A short checklist (dimensions ✓/✗, applicable known-issues + status) and a
one-line verdict: genuinely complete, or complete-with-caveats (named). Never
silently omit a known gap.
