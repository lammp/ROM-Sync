# Legislation — ROM-Sync/

The management app: a local desktop application (Python package `romsync`, data under `data/`) that indexes the store, shows games by cover, title, description, screenshots and tags, and syncs a chosen selection to a destination drive or MTP device with a per-device memory of what is on it. It is games-first with tags for finding and filtering; it manages the ES-DE directory layout so Matt does not have to. Its SQLite database is the authoritative inventory of the library (it replaced the old `_index` TSVs). It is the one tool; the retired RomCurator is gone.

## Stack and layout

| Piece | Detail |
|---|---|
| Python | 3.10 at `%LOCALAPPDATA%\Programs\Python\Python310\python.exe`; run with `PYTHONPATH=D:\Games\ROM-Sync` |
| Run | `ROM-Sync.bat` (desktop window) or `ROM-Sync (browser).bat` (serves 127.0.0.1:8765 in the default browser); both wrap `python -m romsync.app` |
| DB | `data\romsync.db`, SQLite (WAL); covers in `data\covers`, screenshots on demand |
| Metadata | IGDB via Twitch OAuth; `scrape.py` matches, `enrich.py` adds screenshots/tags, `reason.py` proposes franchise tags |
| Cover fallback | `thumbs.py` fills covers IGDB could not give from libretro-thumbnails by No-Intro name (no account); files are `covers\lr-*.png`, never replace an IGDB cover, and survive a later IGDB match that has none. Runs after every Match and from Settings |
| Server | `server.py` `_job` runs background jobs; Settings page (cog) holds store root, IGDB creds, scrape/enrich/rematch, franchise proposals, bulk tag review |
| WebView | storage under `data\webview` (kept off C:) |
| Records | `data\records\` holds the retired-index provenance and the round-20 result/verify TSVs |

## Working on the PC (conventions that bite)

- **PowerShell tool has a ~60 s limit.** Long jobs launch detached: `Start-Process powershell -WindowStyle Hidden` writing to a log, then poll the log. Never block on a long job in one call.
- **Command length ~32 KB.** Write a `.py` or `.ps1` to `data\tmp\` (or `_tools\`) and run it, rather than passing a huge command.
- **Pushing code to the PC:** zip → base64 → ≤3000-char chunks (max 3 per call), each with its MD5; `_push\add.ps1` verifies each chunk's MD5 before appending (PowerShell `-eq` is case-insensitive, so compare hashes as strings deliberately). Extract with .NET `[IO.Compression.ZipFile]`, not `Expand-Archive`. A chunk that reports BAD is resent in 1000/1500-char pieces.
- **Restart the server:** find the PID via `Get-NetTCPConnection -LocalPort 8765 -State Listen`, `Stop-Process` by Id (never kill by command-line pattern), relaunch hidden with a log.
- **PowerShell output over ~100 KB** is truncated by the tool; write large results to a file and parse them, do not echo them.

## Laws for this directory

1. **The database is the inventory.** When the library changes, ROM-Sync's scan is what re-reads it; there is no separate index file to maintain.
2. **Nothing ROM-Sync stores goes on C:.** WebView storage, DB, covers and logs all live under `data\` on D: (Constitution law 3).
3. **Kill a process by PID, never by a command-line pattern match.** A pattern can match the wrong process.

4. **A sync never removes an emulator's own state.** Folders such as `psp\PSP`, `n3ds\nand` and `n3ds\cheats` sit inside a managed system but hold the person's saves, cheats and NAND rather than games. `planner.EMULATOR_STATE` lists them and the remove pass skips them. Without it the mirror treats them as unselected games and deletes them.

## Transports (a destination is reached three ways)

Every transport implements the same contract, so planner, transfer and sysfiles never ask which
one they have: `describe, info, root_exists, create_root, read_marker, write_marker, scan,
list_paths, put_file, delete_file, get_file`.

| Transport | Class | For |
|---|---|---|
| Volume | `VolumeDest` | a drive letter: microSD in a reader, USB stick, external SSD, a share from another machine such as a Steam Deck |
| ADB | `AdbDest` | an Android handheld with USB debugging on |
| MTP | `MtpDest` | an Android device without USB debugging |

**Detection is automatic and ordered.** `devices.probe()` reports all three. `profiles.recognise()`
lists ADB devices first, then hides the MTP entry for the same handheld, so a device that offers
both appears once on the faster transport. The two are matched by the `ROM-Sync.json` marker at the
ROMs root, **not** by USB serial: once USB debugging is on, the MTP shell path is a composite-child
path and no longer carries the serial.

Because the marker is the join, a device profiled over MTP keeps its profile, its selection and its
whole `device_files` inventory when it starts being reached over ADB. There is no migration.

**Why ADB is preferred.** Transfers run at roughly 50 MB/s against MTP's few, with real byte
progress from `adb push` rather than the arrival-polling MTP forces. A full device scan is two
`find` commands, about two seconds against several minutes. Files can be hashed **on the device**
with `md5sum`, so verifying the library costs no transfer at all.

**Quoting.** adb is invoked straight from Python, never through PowerShell, which mangles the
spaces, commas, ampersands and apostrophes these game names are full of. On the device side,
toybox's `find` supports `-printf` but **not** `%y`, and expands `\n` but **not** `\t`, so the
scan uses two typed finds and a literal tab.

**Requirement.** `adb.exe` at `_tools\platform-tools\`. Without it the ADB transport simply does
not appear and MTP is used, so nothing breaks when it is absent.

## Sync model (Matt's rule: never wipe the destination; tactical copy and remove, games only)

- **One action.** The Library toolbar's `Sync` button (it replaced "Open device"; the device name is the link to the device page) makes the device's game folders match the selection. A modal shows the counts (send / replace / remove / in place, net change, free before and after) with Start and Cancel; there is no plan page to tick and no safety net: `planner.plan` is a mirror diff and the sync job runs it in one run.
- **What a sync does:** `send` selected games not on the device; `update` selected games whose store copy differs or is newer; `remove` every unselected item in a store system's folder, whether or not the store has a copy. Folders on the device that are not store systems are never touched, and **neither is `bios` or any system file**: a sync moves games only.
- **Removal from the device is real deletion**; the Recycle Bin law covers the store, not the device.
- **Live progress:** the button becomes spinner + % + ETA; the worker writes `cur_bytes` (bytes of the current item so far) into `status.json`, and `GET /api/run/<id>?brief=1` returns `bytes_done`/`bytes_removed` so the UI can show % by bytes, the on-device count and the free space as they change.
- Every store system is managed (a system with no selection row counts as none); the per-system `all`/`none` buttons on the device page are just a bulk selection.

## System files (staging and readiness)

- The app never writes into an emulator's own folders. Add / Update stages a system's whole set into **`ROMs\bios\<system>\`** on the device (e.g. `ROMs\bios\nds\bios7.bin`, `ROMs\bios\switch\prod.keys`, `ROMs\bios\switch\Firmware-22.5.0.zip`); Matt installs from there with each emulator's own menus. Remove deletes that system's set. RetroArch-served systems (gba, gbc) stage the same way even though RetroArch reads one system directory; Matt copies by hand.
- Two statuses per file, never a date. **Staged**: current / different version / not staged, judged against the store copy by size and, for files up to 32 MB, an MD5 of a copy pulled back from the device (`device_sysfile_hashes`). **Installed**: what the emulator actually reads, listed read-only by the scan: Eden's `files\keys` and `files\nand\system\Contents\registered` (NCA count), DuckStation's and NetherSX2's `files\bios`, `RetroArch\system`, and the staged folder itself for melonDS. The readiness dot comes from Installed only.
- The registry is `sysfiles.SYSTEMS`; an emulator counts as installed when its app folder exists under `Android\data`. Files under `ROMs\bios` that belong to no system are listed as "Other files" with a per-file Remove.
- Endpoints: `GET sysfiles?device=`, `POST profile/<id>/scan-sysfiles` (job), `sysfiles-stage {system}` (job), `sysfiles-unstage {system}`, `sysfiles-remove-other {path, name}`; all refuse while a sync or scan runs on the device.
- `Android\data` on the Thor is readable and writable over USB (verified 2026-09-16).
- **A killed copy wedges the Thor's USB session**: after one aborted CopyHere, no new file landed anywhere on the device (replacing existing files still worked) until it was unplugged and plugged back in. Never kill a worker mid-copy; if it happens, ask for a replug before retrying.
- Sync stays games-only; system files move only through this page.

## Sync log and triage

- Every sync appends one line to `data\records\sync-log.tsv` (run, device, counts, bytes, failed items); the run's own folder `data\runs\<run>\` keeps `plan.tsv`, `results.tsv` (one line per op) and `status.json`. `data\records\device-verify.tsv` records every hash check of a device copy.
- A completed send is not proof of an intact file. When Matt reports a synced game as broken, the `sync-triage` skill applies: find the run, prove the store copy by content, prove the device copy by hash (`_tools\device-verify.py`), delete and re-send on mismatch, record the precedent.

## Publication

<!-- publication-law -->
5. **The application ships; its `data\\` directory never does (Constitution
   law 8).** `romsync.db` holds the IGDB `client_id` and `client_secret`, so a
   committed database is a committed credential. `data\\webview` is a full
   Chromium profile including cookies and session state. `data\\records` and
   `data\\runs` enumerate the library. All of it is excluded.
6. **Credentials are read from configuration, never written into source.** A
   literal key or secret in a `.py`, `.js` or `.bat` file fails the pre-commit
   gate and the publication lint, and rightly so.
7. **Absolute machine paths do not belong in source.** `D:\\Games` as the
   documented store root is fine; a hardcoded path into a C: user folder, or
   one naming the Windows account, is a personal identifier under Constitution
   law 1.
