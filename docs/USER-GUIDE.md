# ROM-Sync user guide

For ROM-Sync 2.0.0. Written for someone who will never open the source.

- [1. What this is for](#1-what-this-is-for)
- [2. What you need](#2-what-you-need)
- [3. Installing](#3-installing)
- [4. First run](#4-first-run)
- [5. The library](#5-the-library)
- [6. Game details and covers](#6-game-details-and-covers)
- [7. Connecting a device](#7-connecting-a-device)
- [8. Choosing what goes on the device](#8-choosing-what-goes-on-the-device)
- [9. Syncing](#9-syncing)
- [10. BIOS, firmware and keys](#10-bios-firmware-and-keys)
- [11. Recovering a game from a device](#11-recovering-a-game-from-a-device)
- [12. Notifications](#12-notifications)
- [13. Settings](#13-settings)
- [14. Troubleshooting](#14-troubleshooting)
- [15. Where your data lives](#15-where-your-data-lives)
- [16. Moving from version 1](#16-moving-from-version-1)

---

## 1. What this is for

You have a game library on a PC that is far bigger than the handheld you play
on. ROM-Sync lets you browse the library by cover art, mark the games you want
on a particular device, and then make that device match your choices in one
action.

The important word is **selection**. ROM-Sync does not mirror a folder. It
keeps a record, per device, of what you chose, works out the difference between
that and what is actually on the device, and moves only the difference.

It is equally careful about what it leaves alone. Folders on your device that
are not systems in your library are never touched, and neither are an
emulator's own saves, cheats or system memory.

## 2. What you need

| | |
|---|---|
| A Windows PC | Windows 10 (1809 or later) or 11, 64-bit. |
| Your games, in folders by system | One folder per system, for example `psx`, `snes`, `gc`, all inside one folder: your **ROMs folder**. This is the layout ES-DE uses. ROM-Sync reads the folder name to know the system. |
| A device to sync to | An Android handheld over USB, or any drive with a letter (an SD card, a USB drive). |
| Optional: Android platform tools | `adb.exe`, for the faster Android transport. Without it ROM-Sync uses MTP, the same connection Explorer uses. |
| Optional: a Twitch developer application | Free. Needed for game details (summary, year, rating, genres). Box art works without it. |

## 3. Installing

1. Download `ROM-Sync-2.0.0-setup.exe` from the
   [2.0.0 release](https://github.com/lammp/ROM-Sync/releases/tag/v2.0.0).
2. Run it. It installs for you alone and needs no administrator rights.
3. The installer is not code-signed, so Windows SmartScreen may say the
   publisher is unknown. Choose **More info**, then **Run anyway**. To check the
   file first, compare its SHA-256 with the one in the release's
   `SHA256SUMS.txt`.
4. If the Microsoft Edge WebView2 runtime is missing, the installer offers to
   open Microsoft's download page. Install the runtime, then run setup again.

Start ROM-Sync from the Start menu. To uninstall, use **Settings > Apps** in
Windows; your library database and covers are kept (see
[section 15](#15-where-your-data-lives)).

## 4. First run

The bell at the top right of the window holds what still needs doing. On a
first run it says:

- **Choose your ROMs folder.** Click it to open **Settings > Library**, then
  choose your ROMs folder with the folder chooser and press **Save library**.
- **Read the library.** Press **Rescan ROMs folder** at the top of the Library
  tab. The table underneath lists each system found, with its game count and
  size. If a system you expected is missing, its folder name is not one
  ROM-Sync recognises.
- **Add IGDB credentials for covers and details.** Optional; see
  [section 6](#6-game-details-and-covers).

Each of these leaves the bell once it is done.

## 5. The library

The **Library** page shows every game as a cover, or as a list with the
grid/list switch. The tile size slider sets how large the covers are.

**Search** with the box in the header. Plain words match titles. Fields narrow
it down, and combine:

| Example | Finds |
|---|---|
| `zelda` | Titles containing "zelda" |
| `system:snes` | Games for one system |
| `year>1995`, `year<=2001` | By release year |
| `rating>=80` | By IGDB rating |
| `genre:rpg` | By genre |
| `tag:metroidvania` | By tag, including franchise tags |
| `region:usa` | By region |
| `size>2gb` | By size |
| `files>1` | Multi-file games |

The **filter sidebar** narrows by system, genre, franchise, decade and more,
with counts, and has smart lists (Top rated, Modern, Retro, Big games, RPGs,
Platformers). The flags at its top keep only games that have cover and
details, are in the device's selection, are on the device now, or are
multi-file.

**Details.** Click a game for its details: cover, summary, screenshots, tags,
and its files. **Fix match** sets the right IGDB entry by its ID, its slug or
its IGDB link, when the automatic match is wrong. A game matched by hand stays
matched.

**The same game on two systems** is marked as a twin; the comparison shows the
versions side by side so you can choose one.

**Tags.** Franchise tags are proposed for you (**Settings > Tag suggestions >
Propose franchise tags**) and wait in each game's details for you to accept or
reject. A decision you make is never overwritten.

## 6. Game details and covers

Covers and details come from two places:

| Source | Gives | Needs |
|---|---|---|
| **IGDB** | Details (summary, release year, rating, genres) and a cover | A free Twitch developer application |
| **libretro thumbnails** | A cover only, matched by file name | Nothing |

**Getting Twitch credentials.** Sign in at the
[Twitch developer console](https://dev.twitch.tv/console), register an
application (any name; OAuth redirect URL `http://localhost`; category
*Application Integration*), and copy its **Client ID** and a new **Client
Secret**. Twitch's own steps may change; theirs are authoritative.

**Entering them.** Open **Settings > Metadata and artwork**. Type the client ID
and the secret, press **Test connection** (it shows a tick if both Twitch and
IGDB accept them, or which stage failed), then **Save metadata and artwork**.
Once saved, both fields lock: the secret shows as dots and is never shown
again. The pencil at a field's end opens it to change it.

**Running it.** The two buttons at the top of the tab:

| Button | Does |
|---|---|
| **Run Initial**, then **Update Metadata** | Looks up every game not looked up yet, then fills any missing cover from libretro. Run it after adding games. |
| **Refresh Metadata** | Asks first, then looks up every game again and replaces what each has, except games you matched by hand. Use it after changing the match threshold. |

**The tracker** beside the settings shows the run. Its badge says which view
you are looking at: **Not run yet**, **Running since** a time, **Complete**,
**Failed** or **Stopped**. While a run goes, the ring is its progress, with the
game being looked up, the time left, and **Stop**. Leaving the page does not
stop a run or lose its progress.

The four counts under the ring are your library's state:

| Count | Means |
|---|---|
| Matched | IGDB found the game and gave it details. |
| Not matched | Looked up, but no IGDB entry scored above the match threshold. Usually compilations, homebrew, hacks, translations and very regional titles. Most still get a libretro cover. Use **Fix match** in a game's details, or lower the threshold and refresh. |
| Not looked up | New since the last run. **Update Metadata** takes them. |
| Without a cover | Neither IGDB nor libretro had box art for it. |

**The match threshold** (0 to 1, default 0.55) is how close a candidate's name
must be to accept it. Lower matches more games, and more of them wrongly.

## 7. Connecting a device

Plug the device in, then open **Devices**. Every device ROM-Sync can reach is a
card. It looks every 15 seconds; the reload icon looks again now.

| Device | How it is reached | Notes |
|---|---|---|
| A drive (SD card, USB drive) | Its drive letter | The ROMs folder is `ROMs` at the drive's root. A drive whose `ROMs` folder is, holds or sits inside your library is never offered. |
| Android, ADB | `adb.exe`, over USB debugging | Fast, and verifies copies on the device itself. Turn on **USB debugging** in the device's Developer options and accept the prompt on the device. Set the path to `adb.exe` in **Settings > Transports and tools** if it is not found. |
| Android, MTP | Windows' own connection, as Explorer uses | Needs the device in **File transfer** mode. Slower. |

The same device can appear on more than one transport. ROM-Sync recognises it
as one device and prefers ADB, then a drive, then MTP.

**A new device** shows **New profile…**. Give it a name and choose whether to
write `ROM-Sync.json` to its ROMs folder. That small file lets ROM-Sync
recognise the device on any PC and over any transport. Creating a profile reads
nothing from and writes nothing to the device except that file, and only if you
ticked it.

**A device with a profile from another PC** carries that file and shows
**Adopt profile**, which recreates the profile here.

**A device ROM-Sync can see but not use** says why, for example that the USB
debugging prompt is waiting on the device.

## 8. Choosing what goes on the device

Choose the device in the header's **Device** list. Then:

- **Per system**, on the device's page: **all** (every game), **none** (no
  games, removing any already there) or **left alone** (ROM-Sync neither sends
  nor removes anything in that system).
- **Per game**, in the Library: each cover has a checkbox for the chosen
  device. A tick in a system set to none adds that game; an untick in a system
  set to all excludes it. **Select shown**, **Clear shown** and **Clear all**
  act on what the current search and filters show.

The bar at the top of the Library says how many games are selected, how much
space they need, and whether they fit, keeping the margin you set in
**Settings > Sync behaviour and guards**.

## 9. Syncing

Open the device's page, or press **Sync** on its card. The page shows what a
sync would do: games to send, replace and remove, with sizes.

Press **Sync**. The confirmation lists the same, and:

- **If anything would be removed**, you must tick *Remove N games from* the
  device before **Start** is enabled.
- **A device's first sync** always asks before removing anything, however few.
- Nothing outside your library's systems, nothing in `bios`, and no emulator
  state folder is ever removed.

Progress shows on the device page and in the Library's selection bar, and the
end of a sync is announced whichever page you are on. **Cancel sync** stops
between games; what was already copied stays. Each run is kept in the device's
**History**.

Copies are checked: over ADB by hashing the copy on the device, on a drive by
reading the copy back and hashing it. A copy that does not match is removed and
reported, never left half-written. Over MTP, Windows offers no way to read a
copy back cheaply, so a copy is judged by its size alone.

**A removal on a device is a real delete.** The device has no recycle bin.

## 10. BIOS, firmware and keys

ROM-Sync never ships or fetches these. It reads them from the `bios` folder in
your ROMs folder.

**System files** lists, per system, the files its emulators need, which your
`bios` folder has, and, for the chosen device, which the device has. Press
**Refresh from device** to read the device. The reload icon reads your `bios`
folder again; it is also read again whenever the window comes back to the
front.

**Stage** copies a system's files to a holding folder on the device
(`ROM-Sync/{system}` by default). Install them from there with each emulator's
own menus. ROM-Sync never writes into an emulator's own folders. Files in the
holding folder that the last survey found and your library does not have are
listed, and can be removed.

## 11. Recovering a game from a device

If a device holds a game your library does not, **Recover** appears in the
header. It lists each such item. **Recover** copies a single-file game back
into your library. Folders, and anything that would replace a file your
library already has, are refused and say why.

Until you recover or remove it, the next sync with that system set to all or
none would remove it from the device, and the Recover page says so.

## 12. Notifications

The bell in the header counts what is new: a device connected or disconnected,
a sync finished, a metadata run, a scan, a recovery, and anything that failed.
Each also shows briefly as a message at the bottom. Open the bell to read them;
**×** clears one, **Clear all** clears every one. A notification that points
somewhere opens it when clicked.

## 13. Settings

Settings is the cog in the header. Each group is a tab, and **Save** and
**Cancel** act on that tab only; a tab with unsaved changes has a dot.

| Tab | Holds |
|---|---|
| Library | The ROMs folder, rescan on launch; **Rescan ROMs folder**; the systems found. |
| Metadata and artwork | **Run Initial / Update Metadata**, **Refresh Metadata**, the tracker; Twitch credentials; match threshold, request rate, error limit; libretro covers on or off. |
| Tag suggestions | **Propose franchise tags**. |
| Transports and tools | **Look for devices again** and what each transport reported; ADB on or off and its path; MTP on or off and its timing; the device staging folder; how large a staged file is verified; how often devices are looked for. |
| Sync behaviour and guards | Space kept free on a device; when the capacity meter warns; how many removals need confirming; writing the device file after each sync. |
| Data and storage | **Reveal the data folder**; the data folder; run and job history kept; what the data folder holds, with upkeep (compact the database, clear caches, delete unreferenced covers, prune old runs). |
| Diagnostics | **Export a support bundle**; version, address, folders, last sync, recent errors, jobs; port, listen address, log level. |

A saved value is locked: the pencil at its end opens it, the undo icon puts the
saved value back. Bounded numbers are sliders with a box to type an exact
value. [SETTINGS.md](SETTINGS.md) specifies every field.

## 14. Troubleshooting

| What you see | What to do |
|---|---|
| A device is missing from **Devices** | Press the reload icon. For Android: unlock the device, check it is in **File transfer** mode for MTP, and for ADB that USB debugging is on and its prompt accepted. |
| A device shows on MTP but not ADB | USB debugging is off, its prompt is waiting, or Android has forgotten the PC's permission (after about 7 days unused, unless *Disable adb authorization timeout* is on in Developer options). Unplug, plug in, and accept the prompt. |
| A Windows "Error Copying File or Folder" dialog during a sync | It comes from Windows' MTP copy. Press OK; the game is reported as failed and the next sync retries it. ADB avoids it. |
| A metadata run fails with "stopped after N failures in a row" | IGDB or Twitch is unreachable, or the credentials were revoked. Press **Test connection**. |
| Many games are **Not matched** | See [section 6](#6-game-details-and-covers). |
| The window does not open | The WebView2 runtime is missing; install it from Microsoft. |
| Anything else | **Settings > Diagnostics > Export a support bundle** makes a zip of versions, settings (with every secret removed), recent jobs and log tails, for a bug report. |

## 15. Where your data lives

Everything ROM-Sync keeps is in `%LOCALAPPDATA%\ROM-Sync\data`, apart from the
application. **Settings > Data and storage** shows each part's size.

| Part | Holds |
|---|---|
| `romsync.db` | The library, device profiles, selections, sync history, settings and the Twitch secret. |
| `covers\` | Box art from IGDB and libretro. |
| `logs\romsync.log` | The log, rotated at 1 MB, three kept. Secrets are removed from every line. |
| `runs\` | One folder per sync, with its record. |
| `webview\` | The window's browser profile. |

Uninstalling leaves this folder. Delete it yourself to remove everything.

## 16. Moving from version 1

Version 2 does not read version 1's database by itself. To bring your games,
selections, tag decisions and device profiles across, run the importer from a
source checkout (see the README's *Build from source*), with ROM-Sync closed:

```
python tools/import_v1.py --from "D:\path\to\version-1\romsync.db" --data "%LOCALAPPDATA%\ROM-Sync\data" --dry-run
```

`--dry-run` reports what would be imported and writes nothing. Run it again
without `--dry-run` to import. It never changes the version 1 database, and it
refuses a version 2 database that already holds a library. Sync history,
settings and credentials are not carried; enter the credentials again in
Settings.
