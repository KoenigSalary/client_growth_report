#!/bin/bash
# ==============================================================
# Client Growth Report -- One-Click Local Launcher (macOS/Linux)
# ==============================================================
set -e

cd "$(dirname "$0")/.."

echo ""
echo "============================================================"
echo " Client Growth Report - Local Mode"
echo "============================================================"
echo ""

# Detect Python command (python3 preferred)
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[ERROR] Python not found! Install Python 3.10+ from https://python.org"
    exit 1
fi

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment..."
    $PY -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "[INFO] Checking dependencies..."
pip install -q -r requirements.txt
python -m playwright install chromium

echo ""
echo "============================================================"
echo " Starting Streamlit app... Browser will open automatically."
echo " Press Ctrl+C in this window to stop the app."
echo "============================================================"
echo ""

streamlit run streamlit_app.py
