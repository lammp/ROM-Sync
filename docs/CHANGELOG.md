# Changelog

## 2.0.0

The first release of ROM-Sync 2: a rewrite of the original application, to the
specification in [rewrite/SPEC.md](rewrite/SPEC.md), with every story in
[rewrite/BACKLOG.md](rewrite/BACKLOG.md) built, tested and gated.

### Install

- A Windows installer, for one user with no administrator rights, and a
  portable zip. No Python needed.
- The application and your data are kept apart: the app in
  `%LOCALAPPDATA%\Programs\ROM-Sync`, the data in
  `%LOCALAPPDATA%\ROM-Sync\data`. Uninstalling keeps the data and says so.
- No fixed paths: the ROMs folder, ADB and everything else are chosen in
  Settings.
- The installer checks for the WebView2 runtime and offers Microsoft's
  download if it is missing.

### Library

- Browse by cover or list; search with fields (`system:`, `year>`,
  `rating>=`, `genre:`, `tag:`, `region:`, `size>`, `files>`); filter by
  system, genre, franchise and decade with counts; smart lists.
- The same game on two systems recognised as twins, with a side-by-side
  comparison.
- Franchise tags proposed, never applied without your decision.

### Metadata

- One action: **Run Initial**, then **Update Metadata**, looks up every game
  not yet looked up and fills missing covers from libretro. **Refresh
  Metadata** looks everything up again and keeps games matched by hand.
- A tracker beside the settings: progress while a run goes, with the game,
  the time left and Stop; the run's outcome after; matched, not matched, not
  looked up and without a cover counts; a badge saying which view it is.
- Twitch credentials tested stage by stage before they are saved; the secret
  never shown again once saved.

### Devices and sync

- Drives, ADB and MTP, discovered automatically; a device recognised over
  whichever transport it comes back on, preferring ADB.
- Device profiles, with an optional `ROM-Sync.json` marker so a device is
  recognised on any PC; adopt a profile made on another PC.
- Per-system selection (all, none, left alone) with per-game exceptions.
- A plan before every sync; removals need their count ticked; a device's first
  sync always asks before removing anything.
- Copies verified by hash over ADB and to drives; a copy that does not match
  is removed, never left half-written.
- Recover a game that is on a device but not in the library.

### System files

- Per system, the BIOS, firmware and key files its emulators need, which the
  library's `bios` folder has, and which the device has; staged to a holding
  folder on the device to install with each emulator's menus.

### Settings and the shell

- Settings in tabs, each saving on its own; each tab's main actions at its
  top; saved values locked behind an edit icon; sliders and lists for bounded
  values.
- Notifications in a bell: devices connecting, syncs, metadata runs, scans and
  failures.
- Diagnostics, a storage breakdown with upkeep, and a support bundle with every
  secret removed.

### Security

- The local server binds to loopback only, checks the `Host` header, requires
  the page's origin and a session token for every change, and forbids framing.
- Network and device paths refused in path settings.
- See [SECURITY.md](../SECURITY.md) section 5, and the open items in
  [KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md) section 8.

### From version 1

- `tools/import_v1.py` imports a version 1 database's games, selections, tag
  decisions and device profiles, with a dry run; it never changes the source.
