# Legislation — _tools/

The build-and-check tools for the library, and the save/restore mechanism that makes every library change reversible (Constitution law 4). Nothing here is a game; `ROM-Sync` is the app and lives separately.

## Contents

| Item | What | Use |
|---|---|---|
| `SavePoint.ps1` | the save/restore engine | `-Save`, `-List`, `-Restore` (see below) |
| `rounds\` | one save-point manifest per round (`<yyyyMMdd-HHmm>-<name>.tsv`) | the audit trail and what `-Restore` reads |
| `SAK\` | Switch Army Knife 0.7.14 | merge Switch base+update+DLC into one XCI/NSP |
| `nsz\` | NSZ (CLI + GUI) | decompress `.nsz` Switch dumps to `.nsp` |
| `chdman\` | chdman from MAME 0.289 | create and verify CHD (`chdman verify -i file.chd`) |
| `intake-plan.py` | classifies a completed set against the ROMs policy and precedents | `--src <set> --system <sys>`; writes `intake-<sys>-plan.tsv` + summary; moves nothing |
| `intake-verify.py` | proves each keeper from its bytes (per-format header checks, chdman for CHD) | `--system <sys>`; results to `ROM-Sync\data\records\` |

## The save/restore mechanism

`SavePoint.ps1` is the only path by which Claude removes or moves library files.

- **`-Save -Name <n> [-Description <d>] -RecycleList <tsv> -MoveList <tsv> [-WhatIf]`** — verifies every operation before touching anything: each path exists and is inside `D:\Games`; nothing under `_torrents\_incomplete`; no move destination already exists or collides; the Recycle Bin has room under its quota (read live from the BitBucket key for D:, or the Windows default of 10% of the first 40 GB plus 5% of the rest when no custom size is set). Any failed check refuses the whole round, changing nothing. What passes runs, recycling files to the bin and performing moves, recording each into `rounds\<id>.tsv`. `RecycleList` rows are `path<TAB>reason`; `MoveList` rows are `from<TAB>to`.
- **`-List`** — prunes save points older than 48 h (their manifests go to the bin), then numbers the survivors newest-first: time, id, items, GB, ops, description.
- **`-Restore <#|id> [-WhatIf]`** — reverses the moves (last first), then restores the recycled files from the bin by original path, and reports anything no longer in the bin.

Retention is 48 h: after two days a rollback is pointless because the library has moved on. A pruned round can no longer be restored by name, but its files sit in the Recycle Bin until Matt empties it and can still be put back from Explorer.

## Laws for this directory

1. **Every library removal or move goes through `SavePoint.ps1 -Save`.** Direct `Remove-Item` or `Move-Item` on library files bypasses the audit trail and the reversibility that Constitution law 4 requires. The one exception is scratch files inside `_tools` itself.
2. **`-Restore` acts on live data — never run it without `-WhatIf` first to confirm the target.** Restoring a save point pulls its files back out of the bin; running it against the wrong number undoes a good round (this has happened during testing).
3. **A save is verified, not trusted.** When Matt names a round, the pre-flight checks are the gate; report what failed and change nothing until the list is amended.

## Publication

<!-- publication-law -->
4. **Tool source ships; the manifests beside it do not (Constitution law 8).**
   Every `.tsv` in this directory and under `rounds\\` is a round's record of
   real library files and is excluded. So are the third-party binaries
   (`chdman`, `nsz`, `SAK`, `platform-tools`): they are not ours to
   redistribute and they are large.
5. **`repo-lint.py` is the publication gate and is run, not assumed.**
   `--strict` before any first push and after any change to `.gitignore`. It
   reads what git would actually stage rather than what the rules claim, and
   it asserts from the other direction that a list of canary paths is still
   ignored.
6. **`repo-lint.local.txt` never ships.** It holds the literal personal
   identifiers the lint searches for; publishing it would defeat the exercise.
   The example file is what ships.
