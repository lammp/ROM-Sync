---
name: open-rom-sync
description: >
  Open the ROM-Sync app on Matt's desktop. Triggered by "open ROM-Sync", "open the
  app", "launch ROM-Sync", "start the app", or "/open-rom-sync". Starts the desktop
  window if it is not already running, or brings the running instance to him, and
  reports the state. Also handles "close ROM-Sync" / "stop the app".
---

# Open ROM-Sync

ROM-Sync lives at `D:\Games\ROM-Sync`. Its launcher is `ROM-Sync.bat` (desktop
window, pywebview, no console). The app serves on 127.0.0.1 and reads the SQLite
database in WAL mode, so it can be open while a scrape or scan job runs.

## Open

1. Check whether it is already running:
   `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*romsync.app*' }`
   (a `pythonw.exe` with `-m romsync.app`). If found, say so: it is already open
   on the desktop; do not start a second instance.
2. Otherwise start it, detached, so the PowerShell tool's 60-second limit does
   not kill it:
   `Start-Process -FilePath 'D:\Games\ROM-Sync\ROM-Sync.bat' -WorkingDirectory 'D:\Games\ROM-Sync' -WindowStyle Hidden`
3. Wait ~5 s and confirm the process is there. If the window did not appear,
   check `D:\Games\ROM-Sync\data\logs\server.log` (last 20 lines) and report the
   error rather than retrying blindly.
4. Report in one line: opened / already open, and anything running in the
   background that the app will show on its Settings page (scrape, enrich, scan).

Browser variant: if Matt asks for it "in the browser", run
`ROM-Sync (browser).bat` the same way; it serves http://127.0.0.1:8765 and opens
the default browser.

## Close / stop

Find the process as above and `Stop-Process -Id <pid>`; never kill by a
command-line pattern (ROM-Sync Legislation law 3). Confirm it is gone. Jobs started
from the app's Settings page run inside the app process, so closing the app stops
them; a job launched from the command line is a separate python process and is
unaffected. Say which applies before closing, and let Matt decide.

## Never

- Never start it from C: or copy anything to C:.
- Never open the app through a second instance to "refresh" it; one process only.
