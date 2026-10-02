@echo off
title Coilover
cd /d "%~dp0"
echo Starting Coilover...
start "" http://localhost:8797
node server.mjs
