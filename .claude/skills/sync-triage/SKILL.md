---
name: sync-triage
description: When Matt reports a game on a device (AYN Thor) that will not launch, shows as encrypted, is missing, or looks wrong after a ROM-Sync sync. Finds the run that sent it, proves whether the store copy or the device copy is at fault, repairs it, and records the precedent.
---

# Sync triage

Use when Matt says a synced game is broken on the device: "X says encrypted", "X won't boot", "X is missing", "X shows as a raw filename". The device copy is guilty until proven otherwise: a completed send is not proof of an intact file (Constitution law 1 of this skill, learnt 2026-09-16 from Xenoblade Chronicles 3D: reported sent, same size, different bytes, Azahar said "Your ROM is Encrypted").

## Evidence, in this order

1. **Which file, which run.** Resolve the title to the exact store name (`games` table or the Library). Find the run(s) that touched it:
   `data\records\sync-log.tsv` (one line per sync: counts and failed items), then `data\runs\<run>\results.tsv` (one line per op: `system  name  op  result  size  detail`) and `plan.tsv`. `sync_ops` in `data\romsync.db` has the same per-op record.
2. **Store copy first, by content.** Header checks: `_tools\intake-verify.py --system <sys> --only "<name>*"` (per-format checks), and for 3DS the deeper executable-header test in `ROM-Sync\data\tmp\n3ds-exh.py` (program ID in the exheader must equal the partition ID; readable title). A store copy that decodes is innocent; stop blaming the ROM.
3. **Device copy, by hash.** `python _tools\device-verify.py --name "<file>"` pulls the device copy back over USB and MD5s it against the store. `--run N --failed` checks everything a run flagged; `--run N` everything it sent; `--system x` a whole system on the device; `--keep` reports without deleting; `--dry` lists only. Results append to `data\records\device-verify.tsv`.
4. **Emulator side only after 2 and 3 pass.** Then the cause is configuration: New 3DS mode in Azahar for New 3DS exclusives, BIOS path, missing emulator app folder (System files page).

## Remedy

- A DIFFERENT or SIZE result: the tool deletes the device copy and its inventory row; press Sync (or `POST profile/<id>/sync`) and the file is re-sent alone. Verify again with `--name` afterwards.
- MATCH on device and store: not a transfer problem; go to step 4.
- PULL-FAILED: the Thor dropped off USB. Dismiss any "device is unreachable" dialog on the PC (it holds the copy), wait, rerun. If nothing new lands on the device at all, unplug and replug it (a killed or aborted copy wedges the USB session).

## Rules

- Never run device-verify while a sync, scan or stage job is running on the same device: two USB workers wedge the session.
- Never kill a worker mid-copy.
- Xenoblade-class files (4 GB, exactly 2^32 bytes) transfer fine; size alone proved nothing, only the hash did.
- Record the outcome as a Common Law fact (`scripts/memory.py create ... --scope rom-sync`) when it teaches something new; append the run and file to this skill's history below.

## History

- 2026-09-16 run 10: 45 sends flagged "stalled" by the old 45 s rule; 44 verified intact by hash, 1 re-sent in run 11. Xenoblade Chronicles 3D (reported sent, not flagged) was the one damaged file; deleted and re-sent in run 13.