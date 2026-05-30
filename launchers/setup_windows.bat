@echo off
REM ============================================================
REM Client Growth Report -- One-Time Setup Wizard (Windows)
REM ============================================================

cd /d "%~dp0\.."

echo.
echo ============================================================
echo  Client Growth Report - One-Time Setup
echo ============================================================
echo.

REM Step 1: Python check
echo Step 1: Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Install Python 3.10+ from https://python.org/downloads/
    echo Make sure to tick "Add to PATH" during installation.
    pause
    exit /b 1
)
echo   OK - Python found
echo.

REM Step 2: Virtual environment
echo Step 2: Creating virtual environment...
if not exist ".venv\" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo   OK
echo.

REM Step 3: Install dependencies
echo Step 3: Installing Python packages (~2 minutes)...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo   OK - Packages installed
echo.

REM Step 4: Install Chromium
echo Step 4: Installing Chromium browser (~2 minutes, 130MB)...
python -m playwright install chromium
echo   OK - Chromium ready
echo.

REM Step 5: Configure .env
echo Step 5: Configure credentials
if exist ".env" (
    set /p KEEP="  .env already exists. Keep it? (y/n): "
    if /i "%KEEP%"=="y" goto SKIP_ENV
)

echo.
echo   Please enter your RMS2 credentials.
echo.
set /p RMS_USER="  RMS2 email: "
set /p RMS_PASS="  RMS2 password: "
echo.
set /p SMTP_E="  Outlook email for sending reports (optional, Enter to skip): "
set "SMTP_P="
set "RECIPS="
if defined SMTP_E (
    set /p SMTP_P="  Outlook app password: "
    set /p RECIPS="  Recipients (comma-separated): "
)

(
echo # RMS2 login
echo RMS_USERNAME=%RMS_USER%
echo RMS_PASSWORD=%RMS_PASS%
echo.
echo # Email delivery
echo SMTP_EMAIL=%SMTP_E%
echo SMTP_PASSWORD=%SMTP_P%
echo SMTP_SERVER=smtp.office365.com
echo SMTP_PORT=587
echo REPORT_RECIPIENTS=%RECIPS%
echo.
echo # Currency and auto-commit
echo INR_TO_USD=86
echo AUTO_GIT_COMMIT=0
) > .env
echo   OK - .env saved
:SKIP_ENV
echo.

REM Step 6: Desktop shortcut
echo Step 6: Creating Desktop shortcut...
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Client Growth Report.lnk"
set "SCRIPT_PATH=%CD%\launchers\run_local_windows.bat"

powershell -NoProfile -Command ^
    "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');" ^
    "$s.TargetPath='%SCRIPT_PATH%';" ^
    "$s.WorkingDirectory='%CD%';" ^
    "$s.Description='Run monthly Client Growth Report';" ^
    "$s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo   OK - Desktop shortcut created
) else (
    echo   Could not create shortcut. Manually: drag launchers\run_local_windows.bat to Desktop
)
echo.

echo ============================================================
echo  Setup complete!
echo ============================================================
echo.
echo  How to run the report each month:
echo.
echo    Option 1 — Double-click "Client Growth Report" on your Desktop
echo    Option 2 — Run: launchers\run_local_windows.bat
echo    Option 3 — streamlit run streamlit_app.py, then click "Run Now"
echo.
echo  When Chromium opens, type the OTP from your Outlook inbox.
echo.
pause
