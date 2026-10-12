@echo off
title Washer PdM - Cloud to Google Drive Auto-Sync Daemon
color 0A
echo ======================================================================
echo    Starting Washer PdM Cloud-to-Drive Autonomous Sync Daemon...
echo    Monitors ESP32 stream in Firebase and auto-saves CSV to Google Drive
echo ======================================================================
echo.
cd /d "%~dp0"
py firmware/auto_drive_sync_daemon.py --timeout 20 --interval 5
pause
