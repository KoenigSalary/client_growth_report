@echo off
REM ==============================================================
REM Client Growth Report -- One-Click Local Launcher for Windows
REM ==============================================================
echo.
echo ============================================================
echo  Client Growth Report - Local Mode
echo ============================================================
echo.

cd /d "%~dp0\.."

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Create venv if needed
if not exist ".venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install dependencies (only if not already installed)
echo [INFO] Checking dependencies...
pip install -q -r requirements.txt
python -m playwright install chromium

echo.
echo ============================================================
echo  Starting Streamlit app... Browser will open automatically.
echo  Press Ctrl+C in this window to stop the app.
echo ============================================================
echo.

streamlit run streamlit_app.py

pause
