# ROM-Sync

A desktop app that keeps a curated retro game library in order and syncs a
chosen subset of it to an Android handheld, a memory card or an external drive.

It is built for the case a general file-sync tool handles badly: a library far
larger than the device, where what goes on the device is a **selection** rather
than a folder, and where the device also holds saves, cheats and emulator state
that must never be touched.

> **Read this before you install.** ROM-Sync was written by one person for one
> library, and several paths are still fixed to that author's machine. It will
> not run from another folder without editing source. The exact lines are listed
> in [docs/KNOWN-LIMITATIONS.md](docs/KNOWN-LIMITATIONS.md), and making them
> configurable is the next piece of work. The code is public now so the refactor
> can happen in the open.

---

## What it does

| Capability | Detail |
|---|---|
| Inventory | Scans your library into SQLite. The database is the inventory; there is no index file to maintain. |
| Metadata | IGDB via Twitch OAuth: cover art, summaries, ratings, screenshots, franchise tags. |
| Cross-system identity | Normalises titles across platforms, including roman numerals, leetspeak and edition suffixes, so the same game on two consoles is recognised as one title. |
| Selection | Per-device selection, with per-system modes and per-game overrides. |
| Three transports | A drive letter, an Android device over ADB, or an Android device over MTP. All implement one contract, so the planner never asks which it has. |
| Sync | A mirror diff over the selection: send, update, remove. |
| Guards | Unmanaged folders, `bios`, and emulator state such as `psp\PSP` or `n3ds\nand` are never removed. |
| System files | BIOS, firmware and keys are staged to a holding folder on the device for you to install with each emulator's own menus, never written into an emulator's directories. |
| Verification | Hashes device copies on the device itself over ADB, so proving a transfer costs no transfer. |

## What it does not do

- It does not acquire anything. There is no downloader and no sources list.
- It does not ship BIOS files, firmware or keys, and will not fetch them.
- It is Windows-only today. The transports and the paths assume Windows.
- It does not sync save files back from the device. Reading saves is on the
  roadmap; the sync is games-only by design.

---

## Requirements

| | |
|---|---|
| Windows | 10 or 11 |
| Python | 3.11 to 3.15. Developed on 3.14. |
| Runtime | Microsoft Edge WebView2, for the desktop window. Already present on most Windows 11 machines. |
| Packages | `pywebview` for the window, `PyYAML` only if you use the agent framework |
| Optional | `adb.exe` for the fast Android transport. Without it, MTP is used instead and nothing breaks. |
| Account | A free Twitch developer application, for IGDB metadata. The app works without it, with no artwork. |

## Install from source

```
git clone https://github.com/lammp/ROM-Sync.git
cd ROM-Sync
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Then edit the two launchers in `ROM-Sync\` so the paths point at your clone and
your virtual environment, and set your library path. The lines to change are
listed in [docs/KNOWN-LIMITATIONS.md](docs/KNOWN-LIMITATIONS.md).

Run it:

```
ROM-Sync\ROM-Sync.bat             a desktop window
ROM-Sync\ROM-Sync (browser).bat   serves on 127.0.0.1:8765 in your browser
```

Both wrap `python -m romsync.app`.

Planning work on it? [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) is the lint of the
current code and the plan to split it into an engine, a browser UI and a desktop
UI. [docs/SETTINGS.md](docs/SETTINGS.md) is the Settings page design.

New here? [docs/USER-GUIDE.md](docs/USER-GUIDE.md) walks through first run,
metadata, connecting a device, choosing games and syncing, without assuming you
will read the code.

---

## The agent framework

This repository also carries the **Legal Framework**: a Constitution
(`CLAUDE.md`), per-directory Legislation (a `CLAUDE.md` in each unit), and a
Common Law memory system (`scripts/memory.py` plus the `memory/` directory) that
records what has been learned as atomic facts with provenance.

It is the governance that was used to build and operate ROM-Sync with a coding
agent, and it is reusable on its own. The pattern is described
[here](https://blog.matthelam.com/blog/a-legal-framework-for-agent-context).

The paths it names, `D:\Games` and its subfolders, are the author's. Read them
as the worked example they are.

## Layout

```
CLAUDE.md               Constitution: values and supreme laws
.claude/skills/         Agent skills: save, restore, memory, triage, lint
scripts/                Common Law memory engine
ROM-Sync/
  romsync/              Application source
  ui/                   Interface: one HTML page, one stylesheet, one script
  CLAUDE.md             Legislation for the application
  data/                 Runtime state. Empty in a clone.
_tools/                 Library tooling, the save/restore mechanism, the publication lint
ROMs/                   Where the library goes. Empty in a clone.
_firmware/ _torrents/   Firmware store and download intake. Empty in a clone.
memory/                 Common Law facts. Empty in a clone.
docs/                   User guide and known limitations
```

A clone reproduces the shape of the workspace and none of its contents. The
empty directories are deliberate: the application and the Legislation both
assume they exist.

## Working on this repository

```
git config core.hooksPath .githooks
python _tools/repo-lint.py --strict
```

The ignore rules deny by default: the first rule excludes the whole tree and
everything published is named explicitly. A pre-commit hook reads staged content
for credentials and personal paths. [SECURITY.md](SECURITY.md) explains what must
never be committed and how to verify it rather than trust it.

## Licence

MIT. See [LICENSE](LICENSE).

The licence covers the source here. It does not extend to game data, BIOS
images, console firmware or keys, none of which are distributed with this
project.
