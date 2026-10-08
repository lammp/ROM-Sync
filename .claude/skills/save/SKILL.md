---
name: save
description: >
  Create a save point before removing or moving library files in D:\Games, or
  when Matt says "save this" / "/save". Recycles rejects to the Windows Recycle
  Bin and moves files with a manifest, so the change can be rolled back with the
  restore skill. Every Claude removal or move of library files MUST go through
  this. Matt can also drive it: he names what to save, this verifies it can be.
---

# Save a round

The only path by which library files in `D:\Games` are removed or moved
(Constitution law 4). Wraps `_tools\SavePoint.ps1 -Save`, which recycles to the
bin and records every operation into `_tools\rounds\<id>.tsv`.

## When

- Before any round that recycles or moves games, sources, or library folders.
- When Matt asks to save specific things. He names them; this checks each can be
  saved and refuses the round if any check fails, changing nothing.

## How

1. Build two optional lists in `_tools\` (tab-separated, UTF-8, no BOM):
   - **recycle** rows: `path<TAB>reason`
   - **move** rows: `from<TAB>to`
   Write the lists from a short Python script (real tab, UTF-8, no BOM). One-row
   lists are fine: SavePoint.ps1 parses rows as objects, so nothing unrolls.

2. Dry-run first:
   `D:\Games\_tools\SavePoint.ps1 -Save -Name <slug> -Description "<what+why>" -RecycleList <tsv> -MoveList <tsv> -WhatIf`
   Read back the planned operations and confirm they are what was intended.
3. Run it without `-WhatIf`. Report the save-point id, done/failed counts and GB.
4. Delete the temporary list files.

## Verifying Matt's request

When Matt supplies the round, resolve each item to a full path, put recycles and
moves into the two lists, and run the `-WhatIf` first. `SavePoint.ps1` enforces:
inside `D:\Games`, not under `_torrents\_incomplete`, destination free, bin under
its 4 TB cap. Relay any refusal verbatim and ask him to amend; do not work
around a failed check.

## Never

- Never `Remove-Item` or `Move-Item` a library file directly to avoid the save
  point. Scratch files inside `_tools` are the only exception.
- Never permanently delete game data (Constitution law 4). Emptying the Recycle
  Bin is Matt's action.
