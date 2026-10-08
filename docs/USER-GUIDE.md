# ROM-Sync user guide

Written for someone who will never open the source. If a step needs a file path
or a command, it is given in full.

- [1. What this is for](#1-what-this-is-for)
- [2. What you need first](#2-what-you-need-first)
- [3. Installing](#3-installing)
- [4. First run](#4-first-run)
- [5. Scanning your library](#5-scanning-your-library)
- [6. Artwork and game details](#6-artwork-and-game-details)
- [7. Connecting a device](#7-connecting-a-device)
- [8. Choosing what goes on the device](#8-choosing-what-goes-on-the-device)
- [9. Syncing](#9-syncing)
- [10. BIOS, firmware and keys](#10-bios-firmware-and-keys)
- [11. When a game does not work](#11-when-a-game-does-not-work)
- [12. Troubleshooting](#12-troubleshooting)
- [13. Where your data lives](#13-where-your-data-lives)
- [14. Command line reference](#14-command-line-reference)

---

## 1. What this is for

You have a game library on a PC that is far bigger than the handheld you play
on. ROM-Sync lets you browse the library by cover art, mark the games you want
on a particular device, and then make that device match your choices in one
action.

The important word is **selection**. ROM-Sync does not mirror a folder. It keeps
a per-device record of what you chose, works out the difference between that and
what is actually on the device, and moves only the difference.

It is equally careful about what it leaves alone. Folders on your device that
are not part of your library are never touched, and neither are an emulator's
own saves, cheats or system memory.

## 2. What you need first

| | |
|---|---|
| A Windows PC | 10 or 11 |
| Your games, sorted into folders by system | One folder per system, for example `psx`, `snes`, `gc`. This is the layout ES-DE uses. |
| Python | 3.11 or newer, from python.org or the Microsoft Store |
| A handheld, memory card or drive | Android over USB, or any drive letter |
| Optional: a Twitch developer account | Free. Only needed for cover art and descriptions. |

If your games are not already in per-system folders, sort them first. ROM-Sync
reads the folder name to decide what system a game belongs to.

## 3. Installing

```
git clone https://github.com/lammp/ROM-Sync.git
cd ROM-Sync
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

**Then the part that is currently manual.** Open `ROM-Sync\ROM-Sync.bat` in
Notepad. It contains three lines with `D:\Games` in them. Change them so they
point at where you put the clone and its `.venv`. Do the same in
`ROM-Sync\ROM-Sync (browser).bat`.

This is a known rough edge and is being fixed. See
[KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md) for the full list of paths that are
still fixed in the code.

Start it by double-clicking `ROM-Sync.bat`. You get a desktop window. If the
window does not appear, use `ROM-Sync (browser).bat` instead, which serves the
same interface at `http://127.0.0.1:8765` in your normal browser; that also
tells you whether the problem is the window or the app.

## 4. First run

Open **Settings**, the cog in the toolbar.

**Store root.** The folder that holds your per-system game folders. Everything
else follows from this.

**IGDB credentials.** Two values, a Client ID and a Client Secret. To get them:

1. Go to the Twitch developer console and register a new application.
2. Set the OAuth redirect URL to `http://localhost` (it is not used, but the
   form requires one).
3. Choose any category.
4. Copy the Client ID, then generate a Client Secret and copy that.

Paste both into Settings. They are stored in ROM-Sync's own database on your
machine and are never written into the source or sent anywhere except Twitch and
IGDB.

You can skip this. Everything works without it; you just get a catalogue with
filenames and no artwork.

## 5. Scanning your library

In Settings, run a **scan**. ROM-Sync walks your store root, reads each system
folder, and records every game it finds with its size and region.

The scan is also how the library stays current. When you add or remove games on
disk, scan again; there is no separate index to keep in step.

What the scan understands:

- One folder per system, named the way ES-DE names them.
- Multi-disc sets, where an `.m3u` playlist sits beside the discs.
- A `bios` folder, which it treats as system files rather than games and never
  counts as library titles.
- `.nomedia`, `systeminfo.txt` and `systems.txt`, which belong to the front end
  and are not games.

## 6. Artwork and game details

Three steps, all in Settings, all safe to re-run:

**Scrape** matches your games against IGDB and brings back a cover, a summary
and a rating. It works through games that have not been matched yet; use the
"all" option to re-run over everything.

**Enrich** adds screenshots and linking tags to games that already matched.

**Franchise proposals** suggests a series for games IGDB left without one, for
example grouping the Mario Kart titles. These are proposals: you review and
accept them in the interface rather than having them applied for you.

Matching is by normalised title, which is deliberately forgiving. It folds roman
numerals, punctuation, leetspeak (`Metal Gear Ac!d` matches `Metal Gear Acid`)
and edition words like `3D`, `HD` or `Remastered`. That is also how it spots the
same game on two different systems.

## 7. Connecting a device

Plug the device in and ROM-Sync finds it. Three kinds are supported:

| Kind | Used for |
|---|---|
| **Volume** | Anything with a drive letter: a microSD in a reader, a USB stick, an external SSD, a network share |
| **ADB** | An Android handheld with USB debugging turned on |
| **MTP** | An Android device without USB debugging |

**Prefer ADB if you can.** It transfers at roughly 50 MB/s against MTP's few,
reports real progress rather than polling for arrivals, scans a whole device in
about two seconds instead of several minutes, and can hash files on the device so
verification costs no transfer. To use it, put `adb.exe` in
`_tools\platform-tools\` and turn on USB debugging on the handheld. If `adb.exe`
is absent, the ADB option simply does not appear and MTP is used instead.

**Creating a profile.** The first time you use a device, give it a name. ROM-Sync
writes a small marker file, `ROM-Sync.json`, at the ROMs root on the device. That
marker, not the USB serial number, is how the device is recognised next time.
This matters in practice: if you later turn USB debugging on, the device starts
arriving over ADB instead of MTP, and because the marker is the link it keeps its
profile, its selection and its whole inventory. Nothing has to be migrated.

**Scan the device.** This is read-only. It records what is already on the device
so the first sync does not re-send things that are already there.

## 8. Choosing what goes on the device

Open the device page.

- **Per system**, use the all or none buttons to take a whole system or drop it.
- **Per game**, mark individual titles in or out, overriding the system setting.
- **Versions.** Where the same game exists on more than one system, the detail
  panel offers a version picker, so you can swap a Nintendo 64 copy for the
  GameCube one without hunting for it. A badge on the cover marks games that
  have a twin elsewhere in the library, and an amber mark means you currently
  have both selected.

A system with no selection counts as none. Nothing is selected by default.

## 9. Syncing

One button, **Sync**, on the Library toolbar. A dialog shows what will happen
before anything moves:

| | |
|---|---|
| send | selected games not on the device |
| update | selected games whose store copy differs or is newer |
| remove | unselected items sitting in a managed system folder |
| in place | already correct, nothing to do |

It also shows the net change in bytes and your free space before and after.
Start or Cancel.

**What a sync never touches:**

- Folders on the device that are not systems in your store.
- `bios` and any system file. Those move only through the System Files page.
- An emulator's own state. `psp\PSP`, `n3ds\nand`, `n3ds\cheats` and their kin
  sit inside managed systems but hold your saves and cheats, not games. The
  remove pass skips them. Without this they would look like unselected games and
  be deleted.

**Progress.** The button becomes a spinner with a percentage and an estimate,
measured by bytes rather than file count, with the on-device count and free
space updating as it goes.

**Removal from the device is permanent.** The recycle-bin protection in this
project covers your PC's library, not the handheld.

## 10. BIOS, firmware and keys

ROM-Sync never writes into an emulator's own folders. Instead, the System Files
page **stages** a system's files into a holding folder on the device:

```
ROMs\bios\<system>\
```

for example `ROMs\bios\nds\bios7.bin`. You then install from there using each
emulator's own menus. Some emulators, such as RetroArch, read a single system
directory; for those you copy from the staged folder by hand.

Two statuses are shown per file, never a date:

- **Staged**: current, a different version, or not staged. Judged by size, and
  for files up to 32 MB by comparing an MD5 of a copy pulled back from the
  device.
- **Installed**: what the emulator actually reads, listed read-only from a scan
  of the emulator's own folders. The readiness dot comes from this, not from
  what is staged.

ROM-Sync does not supply BIOS files, firmware or keys, and will not fetch them.
You provide them.

## 11. When a game does not work

A completed transfer is not proof of an intact file. If a synced game misbehaves:

1. Find the run. Every sync appends a line to `data\records\sync-log.tsv`, and
   each run keeps its own folder under `data\runs\<run>\` with the plan, a line
   per operation, and a status file.
2. Prove the copy on your PC by its contents, not its name.
3. Prove the copy on the device by hash. `_tools\device-verify.py` does this over
   ADB.
4. On a mismatch, delete it on the device and send it again.

A frequent cause is not ROM-Sync at all: a front end such as Cocoon keys games
by filename and caches its own database, so after files move it needs a rescan
before it will find them.

## 12. Troubleshooting

| Symptom | Likely cause |
|---|---|
| The window never opens | The Edge WebView2 runtime is missing. Install it from Microsoft, or use the browser launcher. |
| `No module named webview` | The dependency install did not run, or the launcher is pointing at the wrong Python. |
| "No IGDB credentials in the config" | Settings has no Client ID and Secret yet. See section 4. |
| The scan finds no games | The store root is wrong, or your games are not in per-system folders. |
| The device does not appear | For ADB: USB debugging off, or `adb.exe` missing. For MTP: the phone is in charging-only mode rather than file transfer. |
| The device appears twice | It should not. ROM-Sync hides the MTP entry when the same device is reachable over ADB, matched by the marker file. If you see two, the marker is missing from one of them. |
| A transfer stalls partway and nothing new lands | A killed copy can wedge an Android USB session. Unplug the device and plug it back in. Do not kill a transfer mid-copy. |
| Games are on the device but the front end cannot see them | Rescan in the front end. Its database is its own. |

## 13. Where your data lives

Everything ROM-Sync creates sits under `ROM-Sync\data\`:

| | |
|---|---|
| `romsync.db` | The catalogue, your selections, and your IGDB credentials |
| `covers\`, `screens\` | Downloaded artwork |
| `records\` | The sync log and verification records |
| `runs\<n>\` | Per-run plan, results and status |
| `logs\` | Server logs |
| `webview\` | The embedded browser's profile |

Two consequences worth knowing. **Back up `romsync.db`**: it holds your
selections, which are the work you have actually put in. And **never share it**:
your IGDB client secret is inside it, and it lists your whole library.

## 14. Command line reference

The interface covers everything; these exist for scripting and for when you want
to see exactly what a sync would do.

```
python -m romsync scan                        index the store
python -m romsync systems                     per-system counts
python -m romsync where                       the paths the app is using
python -m romsync devices                     what is plugged in, and which profile each is
python -m romsync profiles                    list profiles
python -m romsync profile-new <n> "<name>"    create a profile for candidate n
python -m romsync scan-device <n>             read-only inventory of candidate n
python -m romsync device <id>                 per-system summary of a profile
python -m romsync select <profile> <system> all|none
python -m romsync select-game <profile> <system> "<name>" in|out
python -m romsync plan <profile> [--full]     what a sync would do, read-only
python -m romsync sync <profile> [--go]       run it
python -m romsync run-status <run>            status and results of a run
python -m romsync sysfiles [<profile>]        BIOS, firmware and key status
python -m romsync scrape [--all] [sys ...]    match games against IGDB
python -m romsync enrich [--all]              screenshots and tags for matched games
python -m romsync reason [--dry]              propose franchise tags
```

`plan` changes nothing. Run it before `sync --go` on any device you care about.
