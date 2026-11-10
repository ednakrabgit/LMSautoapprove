@echo off
title Viriyah Auto Approve Bot
cd /d "%~dp0"

if exist "%~dp0ms-playwright" (
    set "PLAYWRIGHT_BROWSERS_PATH=%~dp0ms-playwright"
)

REM 1. Use portable python_runtime if available
if exist "%~dp0python_runtime\python.exe" (
    start "" "%~dp0python_runtime\python.exe" "%~dp0gui.py"
    exit /b 0
)

REM 2. Check if existing .venv is valid on this machine (remove if copied from another user/PC)
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -V >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Removing old .venv from another machine...
        rmdir /s /q "%~dp0.venv"
    )
)

REM 3. Create .venv if needed
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo ===================================================
    echo   Viriyah Online Learning - Auto Approve Setup
    echo ===================================================
    echo [1/3] Creating Python Virtual Environment (.venv)...
    where python >nul 2>&1
    if not errorlevel 1 (
        python -m venv "%~dp0.venv"
    ) else (
        where py >nul 2>&1
        if not errorlevel 1 (
            py -3 -m venv "%~dp0.venv"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
            "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv "%~dp0.venv"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m venv "%~dp0.venv"
        ) else (
            echo [ERROR] Python not found. Please install Python 3.10+ from https://www.python.org
            pause
            exit /b 1
        )
    )

    echo [2/3] Installing dependencies and Chromium browser...
    "%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    "%~dp0.venv\Scripts\pip.exe" install -r "%~dp0requirements.txt" --quiet
    "%~dp0.venv\Scripts\python.exe" -m playwright install chromium
)

REM 4. Launch application
echo [3/3] Starting Viriyah Auto Approve...
start "" "%~dp0.venv\Scripts\python.exe" "%~dp0gui.py"
exit /b 0
