@echo off
title Coilover Remastered
cd /d "%~dp0"
echo Starting Coilover Remastered...
echo.
echo   The window below prints a http://192.168.x.x address as well.
echo   Open that one on your phone over the same Wi-Fi, then use
echo   Add to Home Screen. After the first load it runs with no signal.
echo.
rem Port 8798, so this can run at the same time as the original on 8797.
set PORT=8798
start "" http://localhost:8798
node server.mjs
