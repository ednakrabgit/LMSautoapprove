@echo off
chcp 65001 >nul
title Viriyah Auto Approve Bot

cd /d "%~dp0"

if exist "%~dp0ms-playwright" (
    set "PLAYWRIGHT_BROWSERS_PATH=%~dp0ms-playwright"
)

if exist "%~dp0python_runtime\python.exe" (
    start "" "%~dp0python_runtime\python.exe" "%~dp0gui.py"
    exit /b 0
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [1/3] กำลังสร้าง Virtual Environment ^(.venv^)...
    python -m venv "%~dp0.venv"
    echo [2/3] กำลังติดตั้งไลบรารีและเบราว์เซอร์ Chromium...
    "%~dp0.venv\Scripts\pip.exe" install --upgrade pip --quiet
    "%~dp0.venv\Scripts\pip.exe" install -r "%~dp0requirements.txt" --quiet
    "%~dp0.venv\Scripts\python.exe" -m playwright install chromium
)

if exist "%~dp0.venv\Scripts\python.exe" (
    start "" "%~dp0.venv\Scripts\python.exe" "%~dp0gui.py"
    exit /b 0
)

start "" python "%~dp0gui.py"
exit /b 0
