@echo off
REM Launches the Streamlit dashboard locally (view reports only, no RMS2 download)
cd /d "%~dp0\.."

if not exist ".venv\" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

streamlit run streamlit_app.py
pause
