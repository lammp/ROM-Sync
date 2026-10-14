# Known limitations

For ROM-Sync 2.0.0. Written so nothing here is a surprise after you install it.
Every item is a real constraint of the current release, not a disclaimer.

## 1. Windows only

The desktop window uses Microsoft Edge WebView2, the MTP transport uses the
Windows shell, and the installer is an Inno Setup program. There is no macOS or
Linux build, and none is planned by the author.

## 2. The installer is not code-signed

Windows SmartScreen may warn that the publisher is unknown. Each release lists
the SHA-256 of every file it ships in `SHA256SUMS.txt`, and every release is
built and proved (installed, self-tested, started and uninstalled) on a
GitHub-hosted Windows runner from the tagged commit. There is no automatic
update: check [Releases](https://github.com/lammp/ROM-Sync/releases).

## 3. MTP is the slow, coarse transport

When an Android device is reached over MTP rather than ADB:

| Constraint | Consequence |
|---|---|
| Copies go through the Windows shell | A copy that fails can raise Windows' own "Error Copying File or Folder" dialog, which holds that copy until OK is pressed. Reads from the device are made with dialogs off; sends are not yet. |
| No cheap read-back | A sent copy is judged by its size, not by a hash. Over ADB and to a drive, every copy is hashed. |
| The device must be in File transfer mode | In charging-only mode it is not seen at all. |
| Arrival is polled | MTP reports a growing file's size in coarse steps, so a large copy is judged stalled only after a time that scales with its size. |

ADB avoids all four. When a device is reachable both ways, ROM-Sync uses ADB.

## 4. ADB depends on the device's goodwill

USB debugging must be on, and its prompt accepted on the device. Android can
also stop offering the debugging connection after a reconnect, or forget the
PC after about seven days unused. ROM-Sync then reaches the device over MTP if
it can, and says which transport each device is on.

## 5. The sync is games-only, deliberately

A sync sends, replaces and removes games. It does not touch `bios`, emulator
state folders, or any folder on the device that is not a system in your
library. That is a safety property, not an omission: a device's saves, cheats
and NAND are never mistaken for unselected games.

The consequence is that save data does not come back from the device. There is
no save sync.

## 6. Removal from a device is a real delete

A device has no recycle bin. When a sync removes a game from a handheld or a
card, the file is gone. ROM-Sync asks before any sync that removes games, and
before a device's first sync removes even one, but once you confirm, the
removal is final. A game that exists only on a device can be copied back first
with **Recover**.

## 7. Game details depend on a third party

Game details come from IGDB through Twitch OAuth, with your own client ID and
secret, at no more than four requests a second (IGDB's limit). A first run
over a large library takes a while: at least half an hour for 8,000 games, as
a title can take more than one lookup. If IGDB changes its terms, its schema or its limits, matching is what
breaks. The library itself does not depend on it: without credentials you get
a working catalogue with libretro box art.

Some games are never matched automatically: compilations, homebrew, hacks,
translations and very regional titles that IGDB does not list as single
games. They are counted as **Not matched** and can be matched by hand.

## 8. Known security items

These are open, each tracked in [docs/rewrite/SCOPE.md](rewrite/SCOPE.md) under
residual risk. None exposes anything beyond your own PC.

| Item | Consequence |
|---|---|
| A device's `ROM-Sync.json` names a profile but is not bound to the device's own identity | A marker copied to another device makes that device be taken for the profile's device. |
| The sync confirmation is checked by count | The engine checks that the number of removals you confirmed matches its plan, not that the items are the same ones. |
| The Twitch secret is stored unencrypted | It is in `romsync.db` in your own data folder, which is never published. Anyone who can read your user folder can read it. |
| Listing devices starts the transport tools | Opening Devices runs `adb` and a PowerShell probe. |

## 9. Moving from version 1 needs a source checkout

The importer for a version 1 database is a command-line tool in the source
(`tools/import_v1.py`), not part of the installed application. See
[the user guide](USER-GUIDE.md#16-moving-from-version-1).

## 10. Single author, no support commitment

This is a personal tool published in the hope it is useful. There is no
release cadence, no support promise and no guarantee the next release will not
change behaviour you relied on. Issues are welcome; answers are not promised.
