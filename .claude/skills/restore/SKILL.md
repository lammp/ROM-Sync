---
name: restore
description: >
  Roll back a save point in D:\Games. Triggered by "/restore", "restore", or
  "roll back that" in plain language. Lists the save points from the last 48 h,
  lets Matt pick one, then reverses its moves and restores its recycled files
  from the Windows Recycle Bin.
---

# Restore a save point

Undoes a round made by the save skill. Wraps `_tools\SavePoint.ps1`.

## Flow

1. **Show the list.** Run `D:\Games\_tools\SavePoint.ps1 -List` and present the
   numbered save points to Matt as they come back — time, id, items, GB, ops,
   description. `-List` prunes anything older than 48 h first, so only rollable
   rounds appear. If the list is empty, say so (nothing in the last 48 h).
2. **Wait for his pick.** Do not choose for him. He gives a number or an id.
3. **Preview.** Run `-Restore <pick> -WhatIf` and show what would move back and
   what would be restored from the bin. Confirm it is the round he meant — the
   description and the file list are the check.
4. **Restore.** Run `-Restore <pick>` and report restored / failed / missing.
   "missing" means a recycled file is no longer in the bin (emptied, or already
   restored); name those so Matt knows what could not come back.

## Laws

- **Always `-WhatIf` before the real restore** (`_tools` Legislation law 2). A
  wrong number undoes a good round; restoring pulls files back out of the bin.
- **Retention is 48 h by design.** A round pruned from the list can still be
  restored file-by-file from Explorer while the bin holds it, but not by this
  skill. Tell Matt that rather than implying it is unrecoverable.
