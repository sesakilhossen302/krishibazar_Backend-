@echo off
title KrishiBazar Live Backend Server
echo ===================================================
echo       KRISHI BAZAR LIVE BACKEND SERVER
echo ===================================================
echo.
echo [1/2] Starting FastAPI Backend on Port 8000...
start /b python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
timeout /t 3 > nul
echo.
echo [2/2] Starting Cloudflare Public Tunnel for Clients...
..\cloudflared.exe tunnel --url http://127.0.0.1:8000
pause
