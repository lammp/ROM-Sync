@echo off
rem ROM-Sync in your normal browser: serves on http://127.0.0.1:8765 and opens it. Keep this window open; close it to stop.
set PYTHONPATH=D:\Games\ROM-Sync
cd /d D:\Games\ROM-Sync
start "" http://127.0.0.1:8765
"D:\Games\.venv\Scripts\python.exe" -m romsync.app --browser