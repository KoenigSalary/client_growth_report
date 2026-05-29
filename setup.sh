#!/bin/bash
# Streamlit Cloud runs this once after installing requirements.txt
# Installs the Chromium browser binary needed by Playwright
echo "Installing Playwright Chromium..."
python -m playwright install chromium || echo "Playwright install returned non-zero, continuing"
echo "Done."
