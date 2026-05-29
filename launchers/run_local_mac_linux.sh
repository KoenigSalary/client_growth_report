#!/bin/bash
# ============================================================
# Client Growth Report - Monthly Run (macOS / Linux)
# ============================================================
set -e

cd "$(dirname "$0")/.."

echo ""
echo "============================================================"
echo " Client Growth Report - Monthly Run"
echo "============================================================"
echo ""

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[ERROR] Python not found! Install Python 3.10+ from https://python.org"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[INFO] First-time setup: creating virtual environment..."
    $PY -m venv .venv
fi
source .venv/bin/activate

echo "[INFO] Checking dependencies..."
pip install -q -r requirements.txt
python -m playwright install chromium

echo ""
echo "============================================================"
echo " Starting run_monthly.py"
echo " - A Chromium window will open"
echo " - Type the OTP from your Outlook when it appears"
echo " - Everything else is automatic"
echo "============================================================"
echo ""

python run_monthly.py

echo ""
echo "============================================================"
echo " Done!"
echo "============================================================"
