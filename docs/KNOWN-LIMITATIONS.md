# Known limitations

Written so nothing here is a surprise after you have cloned it. Every item is a
real constraint of the current code, not a disclaimer.

## 1. Fixed paths

ROM-Sync was written for one library at `D:\Games`. Those paths are in the
source rather than in configuration, so a clone elsewhere will not run until
they are changed. Nothing below is a secret; it is simply the wrong default for
anyone but the author.

**Making these configurable is the next piece of work.** The intended end state
is that every one is resolved from configuration, set on first run and editable
in Settings, with defaults relative to the install rather than absolute.

| File | Line | Value today | Should become |
|---|---|---|---|
| `ROM-Sync/ROM-Sync.bat` | 3, 4, 5 | `D:\Games\ROM-Sync`, `D:\Games\.venv\Scripts\pythonw.exe` | Paths relative to the launcher's own folder |
| `ROM-Sync/ROM-Sync (browser).bat` | 3, 4, 6 | the same two | the same |
| `ROM-Sync/romsync/db.py` | 248 | store root defaults to `D:\Games\ROMs` | No default: asked for on first run, held in config |
| `ROM-Sync/romsync/adb.py` | 20 | bundled adb at `D:\Games\_tools\platform-tools\adb.exe` | Config value, falling back to `adb` on PATH |
| `ROM-Sync/romsync/sysfiles.py` | 39 | firmware store at `D:\Games\_firmware` | Config value, optional |
| `ROM-Sync/romsync/igdb.py` | 21 | credential fallback reads a retired app's database on `D:` | Removed |
| `ROM-Sync/romsync/legacy.py` | 12 | metadata import from the same retired app | Removed, or made a path you choose |
| `ROM-Sync/ui/app.js` | 973 | prints the firmware path in the interface | Reads the configured value |
| `_tools/*.py` | various | each library tool hardcodes `D:\Games\...` | Arguments with config defaults |
| `_tools/SavePoint.ps1` | 49, 51 | library root and off-limits list | Parameters |

The agent skills under `.claude/skills/` also name an interpreter at
`D:\Games\.venv\Scripts\python.exe`. They are the author's operating
instructions rather than application code, but they carry the same problem for
anyone adopting the framework.

## 2. The RomCurator import is dead weight

`legacy.py` and the credential fallback in `igdb.py` exist to migrate from
"ROM Curator 1", an earlier app by the same author that no longer exists
publicly. No new user can use either path. They are carried here rather than
deleted so the history of the data model stays legible, and they are first in
line for removal.

## 3. Windows only

The transports, the paths and the launchers assume Windows. The MTP transport
uses Windows shell COM. There is no macOS or Linux support and none is planned
by the author.

## 4. Dependencies were under-declared

`requirements.txt` previously listed only PyYAML, which the application does not
use. The application needs `pywebview`; PyYAML belongs to the agent framework's
memory engine. That is now corrected, but it means early clones may have failed
to start with an import error on `webview`.

## 5. No automated tests

There is one test harness, `_tools/test-twins2.js`, for the cross-system title
matcher. Everything else has been verified by hand against a real library and a
real device. Treat the sync against a device you care about accordingly, and
read what a sync will do before running it.

## 6. The sync is games-only, deliberately

A sync sends, replaces and removes games. It does not touch `bios`, emulator
state folders, or any folder on the device that is not a system in your store.
That is a safety property, not an omission: the planner's remove pass skips
`planner.EMULATOR_STATE` so a device's saves, cheats and NAND are never
mistaken for unselected games.

The consequence is that save data does not come back from the device. There is
no save sync.

## 7. Removal from a device is a real delete

The recycle-bin protection in this project covers the store on your PC, not the
device. When a sync removes a game from a handheld, the file is gone.

## 8. Metadata depends on a third party

Cover art, summaries and screenshots come from IGDB through Twitch OAuth. You
supply your own client ID and secret. If IGDB changes its terms, its schema or
its rate limits, the scraper is what breaks. The library itself does not depend
on it: without credentials you get a working, artwork-free catalogue.

## 9. Single author, no support commitment

This is a personal tool published in the hope it is useful. There is no release
cadence, no support promise and no guarantee the next commit will not change
behaviour you relied on.
