# ROM-Sync 2: scope

## Goal

One engine, two interfaces, no machine-specific paths, every rule covered by a
deterministic test. The engine is rewritten. The interface is ported.

## Decisions

| # | Decision |
|---|---|
| D1 | The engine is rewritten from scratch as a ports-and-adapters package. The domain layer imports nothing outside the standard library. |
| D2 | The interface is ported, not redesigned. Views, search grammar, facet model, twin swapper and detail panel keep their current behaviour. |
| D3 | The interface is TypeScript, built with Vite, no UI framework. The API client is generated from the engine's OpenAPI document. |
| D4 | The port folds in the accessibility and contrast corrections, because every line is being touched. |
| D5 | The engine is Python 3.12 or newer. The HTTP layer is FastAPI on uvicorn. The desktop shell is pywebview over WebView2. |
| D6 | The repository ships no data: no database, no library, no covers, no BIOS, no firmware, no keys, no ROMs. |
| D7 | The repository ships an installer and a dependency check. A first run on a machine that has never held the application must reach a working state through the interface alone. |
| D8 | Every configurable value is resolved from a config registry at call time. No absolute path, credential, threshold or timeout is a module constant. |
| D9 | Nothing destructive accepts a string path. A destructive call takes a path object that cannot be constructed outside its permitted root. |
| D10 | The schema is versioned and forward-migrated once at startup, under a lock, after a backup. |
| D11 | Jobs are owned by the engine, persisted, cancellable, and reconciled at startup. |
| D12 | One contract test suite runs against all three destination adapters and against a fake. A destination that fails it is not a destination. |
| D13 | The whole verification gate is one command. An autonomous run stops on the first red. |
| D14 | Importing an existing ROM-Sync 1 database is a shipped, opt-in tool that takes a path. It is code, not data. |
| D15 | Work lands as one branch and one pull request per story, gated on D13. |
| D16 | Version 2 is developed on a `v2` branch of the existing repository. Version 1 stays on `main` until v2 passes its gate. |

## Non-goals

| Not in scope | Tracked as |
|---|---|
| The Android client | a later epic, from the existing 17-section scope |
| Save data and memory card sync | a later epic |
| Acquiring content of any kind | never |
| Shipping or fetching BIOS, firmware or keys | never |
| macOS or Linux support | not planned |
| Re-tuning the matcher | the thresholds are ported as given and pinned by fixtures |
| A light colour theme | not planned |

## What the rewrite must not lose

These are the behaviours the current code earned the hard way. Each has a named
test in [BACKLOG.md](BACKLOG.md) and must pass before the story that touches it
is closed.

| Behaviour | Why it exists |
|---|---|
| One row per game unit, `kind` of file or folder, members listed separately | multi-disc sets and folder games |
| Title identity folding roman numerals, leetspeak, punctuation and edition words | cross-system twins, and the matcher's input |
| Matcher thresholds: 0.55 accept, 0.92 early exit, 0.15 off-platform penalty | calibrated against a real library |
| Cover preservation on re-match when the new match has no cover | a re-scrape must not lose a libretro cover |
| Machine passes never overwrite a human tag decision | the proposed and accepted model |
| Marker file, not USB serial, is the device identity | a device that gains USB debugging keeps its profile |
| Emulator state folders are never removed by a sync | saves, cheats and NAND live inside managed systems |
| Folders that are not store systems are never touched | the destination is not mirrored |
| `bios` is system files, never games | it is not filtered by the game policy |
| Copy to a part file, then atomic replace | a killed copy leaves an orphan, never a corrupt game |
| Never kill a transfer worker mid-copy | an aborted copy wedges an Android USB session |
| Arrival polling sized by file size, not a fixed timeout | a large file over MTP sits at one reported size for minutes |
| Removal from a device is permanent and is stated as such | the recycle bin covers the store, not the device |
| The sync log is a plain text file that cannot fail a sync | triage starts from it |
| Run folders on disk, written by the worker | an interrupted run stays observable, and the MTP worker is out of process |

## Defects this rewrite exists to make impossible

| Defect | Structural fix |
|---|---|
| Deletion escaping its root through an unchecked name | D9: a contained path object; a raw string cannot reach a delete |
| Static file serving escaping its root | D9 applied to the asset route; a whitelist, not a join |
| A rescan deleting games because a system file could not be read | the prune is scoped to systems actually visited, and refuses when nothing was indexed |
| A corrupt transfer recorded as success and then self-confirming | an unverified transfer records no hash, and verification is a declared capability |
| Transport behaviour differing per adapter | D12: one contract suite |
| Jobs vanishing on restart, no cancellation | D11 |
| Credentials read from the database by the HTTP client | D1: the host supplies them |
| A new column silently ignored on an existing database | D10 |
| Settings that cannot be cleared, and twelve values that cannot be set at all | D8 |
| No test anywhere | D13 |

## Residual risk

| Risk | Statement |
|---|---|
| No golden master from a real library | D6 removes the owner's database as an oracle. Behaviour is pinned by synthetic fixtures and a corpus of public game titles. This is weaker than diffing against a real 7,900-game library, and the matcher is the part most exposed. |
| Device behaviour cannot be unit tested | The contract suite proves the adapters agree with each other and with the fake. It cannot prove any of them agrees with a handheld. Real-device verification stays manual and is listed per story. |
| A TypeScript port is a rewrite of the interface by another name | Mitigated by D2 and by behaviour fixtures for the search grammar, the facet counts and the twin clustering, taken from the current implementation's output. |
