@echo off
REM ============================================================
REM Client Growth Report - Monthly Run (Windows)
REM
REM This script runs the end-to-end monthly job:
REM   1. Opens Chromium (you enter OTP in it)
REM   2. Downloads 24M + 12M from RMS2
REM   3. Builds the Excel growth report
REM   4. Emails it
REM   5. Commits files to git so Streamlit Cloud sees them
REM ============================================================

cd /d "%~dp0\.."

echo.
echo ============================================================
echo  Client Growth Report - Monthly Run
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Create venv on first run
if not exist ".venv\" (
    echo [INFO] First-time setup: creating virtual environment...
    python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install dependencies (silent if already installed)
echo [INFO] Checking dependencies...
pip install -q -r requirements.txt

REM Install Chromium browser (first-time only takes ~2 min)
python -m playwright install chromium

echo.
echo ============================================================
echo  Starting run_monthly.py
echo  - A Chromium window will open
echo  - Type the OTP from your Outlook when it appears
echo  - Everything else is automatic
echo ============================================================
echo.

python run_monthly.py

echo.
echo ============================================================
echo  Done! Press any key to close.
echo ============================================================
pause
