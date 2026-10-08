---
name: process-intake
description: >
  Process what is waiting in D:\Games\_torrents\_complete into the library: review
  the completed sets, plan each against the ROMs filtering policy, get Matt's go,
  move keepers into ROMs\<system> (converted where the system needs it), recycle
  the rest under a save point, verify every keeper from its bytes, rescan and
  scrape in ROM-Sync. Triggered by "process the intake", "process _complete",
  "sort what's downloaded", "process what's in complete", or "/process-intake".
---

# Process the intake

The round that turns a finished download into library entries. It follows the
Constitution (laws 2, 3, 4), `ROMs\CLAUDE.md` (formats and filtering policy) and
`_torrents\CLAUDE.md`. Consult memory first: `memory.py search "<system> intake"`
and the precedents on `roms#filtering-policy`.

## 1. Review what is there

List `_torrents\_complete` recursively: each set is normally one folder named for
its source (`No-Intro\<System>`, `Redump\<System>`, an Internet Archive item).
For each set report: system it belongs to, file count, size, extension mix, and
whether anything is still incomplete (`.!qB` suffix = still downloading: that set
is not ready; leave it, say so). Map the set to its `ROMs\<system>` folder using
`ROMs\<system>\systeminfo.txt` (system name and accepted extensions).

## 2. Plan the round

For cartridge / archive sets (No-Intro style, one zip per game):

    D:\Games\.venv\Scripts\python.exe D:\Games\_tools\intake-plan.py --src "<set folder>" --system <system>

It applies the policy and the recorded precedents (region rank with United Kingdom
level with Europe, highest revision wins, `(Alt)` dropped, `(Unl)` dropped,
`[BIOS]` entries to `_firmware`) and writes `_tools\intake-<system>-plan.tsv` plus
a summary. Read the summary and the "check by eye" section; a rule the text does
not settle is a decision for Matt, recorded afterwards as a precedent
(`memory.py create ... --rule roms#filtering-policy`).

For disc sets (Redump: PS1/PS2/PSP as cue+bin / iso; GC/Wii as iso/rvz; 3DS):
keepers are filtered the same way but must be **converted** to the library format
(`ROMs\CLAUDE.md`): PS1 `chdman createcd -i <cue> -o <chd>`, PS2/PSP
`chdman createdvd -i <iso> -o <chd>`, GC/Wii to RVZ with DolphinTool (not in
`_tools` yet: if missing, name it and stop, procurement is Matt's), 3DS must be
the decrypted set. Conversion runs detached (`Start-Process ... -WindowStyle
Hidden` with a log), the PowerShell tool cannot wait for it. Multi-disc PS1
games get an `.m3u` beside the discs.

Keep zipped where `systeminfo.txt` lists `.zip`; extract only where it does not.

## 3. Show the plan, wait for go

Present in one message: source files/GB; keep count/GB and where; drop counts by
reason; region mix of keepers; loose files in the destination that the keepers
supersede; loose files with no match (they stay); any name collisions; any
judgement the policy text does not settle. Nothing moves before Matt says go.
He may amend a rule; re-run the plan if he does.

## 4. Execute under a save point (the `save` skill)

Build the lists from the plan TSV with a short Python script (real tabs, UTF-8):
moves for keepers (`<set>\<file>` -> `ROMs\<system>\<file>`, or the converted
output), moves for `[BIOS]` rows to `_firmware\BIOS - <system> (<source>)`,
recycles for drops and superseded loose files. Then:

    D:\Games\_tools\SavePoint.ps1 -Save -Name round-<n>-<system>-<source> -Description "..." -RecycleList <tsv> -MoveList <tsv>

Run it detached with a log when it has thousands of rows (about 25 recycles a
second); poll the manifest's row count. A second small save point recycles the
emptied source folder tree afterwards. Delete the temporary list files.

## 5. Verify every keeper from its bytes

    D:\Games\.venv\Scripts\python.exe D:\Games\_tools\intake-verify.py --system <system>

Header checks per format (NDS logo+header CRC, GBA complement, GB/GBC checksum,
NES magic, SNES checksum pair, N64 magic, 3DS NCSD+NoCrypto, RVZ magic, CHD via
chdman). Results land in `ROM-Sync\data\records\intake-<system>-verify.tsv`.
Anything not `ok` is reported by name with its reason; never round up to "done".
Move the plan TSV into `ROM-Sync\data\records\` as well.

## 6. Rescan and scrape

    set PYTHONPATH=D:\Games\ROM-Sync ; cd D:\Games\ROM-Sync
    python -m romsync scan            (fast; reports added/removed)
    python -m romsync scrape <system> (IGDB; ~4 titles/s, run detached with a log)

Report added count from the scan and that the scrape is running.

## 7. Record

Capture with `memory-capture`: any new precedent Matt decided, any format or
tool lesson, anything that failed verification and why. Report to Matt: counts,
verification result, save-point ids (rollable 48 h via `restore`), and any
leftovers for his decision.

## Never

- Never read `_torrents\_incomplete` or `Downloading` (law 2).
- Never move or delete outside a save point (law 4); never hard-delete.
- Never convert with a tool that is not in `_tools` without saying it is missing.
- Never declare a set processed until every keeper passed verification or its
  failure is listed by name.