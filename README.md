# ROM-Sync

A Windows desktop app that keeps a curated retro game library in order and
syncs a chosen subset of it to an Android handheld, a memory card or an
external drive.

It is built for the case a general file-sync tool handles badly: a library far
larger than the device, where what goes on the device is a **selection** rather
than a folder, and where the device also holds saves, cheats and emulator state
that must never be touched.

**Current release: 2.0.0.** Download it from
[Releases](https://github.com/lammp/ROM-Sync/releases). What changed is in
[docs/CHANGELOG.md](docs/CHANGELOG.md).

---

## What it does

| Capability | Detail |
|---|---|
| Library | Scans your ROMs folder (one subfolder per system, as ES-DE lays it out) into a local database. Browse by cover, search with a small query language (`system:snes year>1995 rating>=80`), filter by system, genre, franchise and more. |
| Metadata | One action fills it: game details from IGDB (summary, year, rating, genres) and box art from IGDB or, for anything IGDB has none for, the public libretro thumbnails. A game matched by hand stays matched. |
| Cross-system identity | The same game on two consoles is recognised as one title, so you can compare the versions side by side. |
| Selection | Per device: each system is all, none or left alone, with per-game exceptions. |
| Three transports | A drive letter, an Android device over ADB, or an Android device over MTP. A device is recognised over whichever it is plugged in on. |
| Sync | Works out what to send, replace and remove, shows it, and asks before it removes anything. |
| Guards | Folders that are not systems in your library, `bios`, and emulator state such as `psp\PSP` or `n3ds\nand` are never removed. |
| System files | Shows which BIOS, firmware and key files each system needs, which your library has, and stages them on the device for you to install with each emulator's own menus. |
| Recover | Copies a game that is on a device but not in your library back into the library. |
| Notifications | Device connected, sync finished, metadata passes, scans and failures, kept in a bell until you clear them. |

## What it does not do

- It does not acquire anything. There is no downloader and no sources list.
- It does not ship BIOS files, firmware or keys, and will not fetch them.
- It is Windows-only.
- It does not sync save files back from the device. The sync is games-only by
  design.

Everything else worth knowing before you rely on it is in
[docs/KNOWN-LIMITATIONS.md](docs/KNOWN-LIMITATIONS.md).

---

## Install

| | |
|---|---|
| Windows | 10 or 11, 64-bit |
| Runtime | Microsoft Edge WebView2, for the window. Present on Windows 11 and most Windows 10 machines; the installer says if it is missing. |
| Optional | `adb.exe` (Android platform tools) for the faster Android transport. Without it, MTP is used and nothing breaks. |
| Optional | A free Twitch developer application, for IGDB game details. Without it you still get libretro box art. |

1. Download `ROM-Sync-2.0.0-setup.exe` from the
   [release](https://github.com/lammp/ROM-Sync/releases/tag/v2.0.0).
2. Run it. It installs for your user only, needs no administrator rights, and
   puts the application in `%LOCALAPPDATA%\Programs\ROM-Sync`.
3. Windows may warn that the publisher is unknown: the installer is not
   code-signed. Choose **More info**, then **Run anyway**. The release lists
   SHA-256 sums in `SHA256SUMS.txt` if you want to check the file first.

Your data (the library database, covers, logs) lives apart from the
application, in `%LOCALAPPDATA%\ROM-Sync\data`. Uninstalling removes the
application and leaves the data, and says so.

A portable zip, `ROM-Sync-2.0.0-portable.zip`, is attached to the release too:
unzip it anywhere and run `ROM-Sync\ROM-Sync.exe`.

**Then read [docs/USER-GUIDE.md](docs/USER-GUIDE.md).** It walks through first
run, metadata, connecting a device, choosing games and syncing, without
assuming you will read the code.

---

## How it is built

Version 2 is a rewrite of the original application, specified in
[docs/rewrite/SPEC.md](docs/rewrite/SPEC.md) and built story by story from
[docs/rewrite/BACKLOG.md](docs/rewrite/BACKLOG.md).
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) is the overview.

| Part | What it is |
|---|---|
| `engine/` | The application: domain rules, use cases, ports and their adapters (SQLite, the file system, ADB, MTP, drives, IGDB, libretro). Python 3.12. |
| `api/` | A FastAPI HTTP API over the engine, on loopback only. |
| `desktop/` | The desktop shell: runs the engine and API in-process and shows the interface in a WebView2 window. |
| `ui/` | The interface: Next.js, exported as static files, built from atoms, molecules and organisms, each with stories and tests. |
| `tools/` | The verification gate, the installer and release builder, the version 1 importer. |
| `tests/` | Unit, contract and golden tests for the engine and API. |
| `docs/` | This documentation, and the rewrite's specifications under `docs/rewrite/`. |
| `ROM-Sync/` | Version 1's source, kept for reference. Version 2 does not use it. |

### Build from source

You need Python 3.12 and Node.js 22.

```
git clone https://github.com/lammp/ROM-Sync.git
cd ROM-Sync
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
npm ci --prefix ui
npx --prefix ui playwright install chromium
```

Run every check the continuous integration runs, in 12 stages:

```
.venv\Scripts\python tools\verify.py
```

Build and run the desktop app:

```
npm run bundle --prefix ui
.venv\Scripts\python -m pip install -e ".[build]"
.venv\Scripts\python tools\installer.py build
reports\release\dist\ROM-Sync\ROM-Sync.exe
```

`ROM-Sync.exe --self-test report.json` checks a build without opening a window.

### Continuous integration

| Workflow | When | What |
|---|---|---|
| `gate` | Every push to `v2` and every pull request | The 12-stage gate on a Windows runner. |
| `installer` | Every push to `v2` | Builds the installer, installs it silently, self-tests it with no Python present, starts it, and uninstalls it keeping the data. |
| `nightly` | Daily | The gate with every dependency resolved fresh, and the tests in random order. Opens an issue if it fails. |
| `release` | A `v*` tag | The gate, then the installer and portable zip, checksums, the same install proof, and the GitHub release. |

Work happens on `v2` and reaches `main` by pull request.

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
as the worked example they are. The application itself has no fixed paths.

## Working on this repository

```
git config core.hooksPath .githooks
python _tools/repo-lint.py --strict
```

The ignore rules deny by default: the first rule excludes the whole tree and
everything published is named explicitly. A pre-commit hook reads staged content
for credentials and personal paths. [SECURITY.md](SECURITY.md) explains what must
never be committed, how to verify it rather than trust it, and the application's
own security model.

## Contributing

The repository is public and read by anyone; changes are by invitation.

- **Open an issue first** describing what you want to change and why. If it
  fits, you will be invited or asked to send a pull request.
  [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) has the detail.
- **Pull requests come from your own fork.** `main` changes only through a pull
  request that the owner has reviewed and approved, with the `gate` check
  passing on it. A workflow from a fork runs only once the owner approves it.
- **Releases are immutable.** A published release, its files and its tag
  cannot be changed or deleted, by anyone. A correction is a new release.
- **Security problems** go through the repository's private vulnerability
  reporting, never a public issue. See [SECURITY.md](SECURITY.md).

## Licence

MIT. See [LICENSE](LICENSE).

The licence covers the source here. It does not extend to game data, BIOS
images, console firmware or keys, none of which are distributed with this
project.
