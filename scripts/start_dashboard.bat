@echo off
title ZeroKey Dashboard (localhost:5173)
cd /d "%~dp0\..\dashboard"
if not exist node_modules call npm install
start "" http://localhost:5173/
call npm run dev -- --host localhost --port 5173 --strictPort
pause
