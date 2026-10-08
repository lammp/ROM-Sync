@echo off
rem ROM-Sync desktop window. Double-click to open; close the window to quit.
set PYTHONPATH=D:\Games\ROM-Sync
cd /d D:\Games\ROM-Sync
start "" /b "D:\Games\.venv\Scripts\pythonw.exe" -m romsync.app