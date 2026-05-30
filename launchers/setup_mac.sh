#!/bin/bash
# ============================================================
# Client Growth Report — One-Time Setup Wizard (macOS)
#
# What this does:
#   1. Checks Python 3.10+ is installed (helps you install it if not)
#   2. Creates a Python virtual environment
#   3. Installs all dependencies including Playwright + Chromium
#   4. Prompts for RMS2 + SMTP credentials, writes .env
#   5. Creates "Client Growth Report.app" in /Applications for one-click launch
# ============================================================

set -e

# Color codes for nicer output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "  Client Growth Report - One-Time Setup"
echo "============================================================"
echo ""

# 0. Navigate to repo root
cd "$(dirname "$0")/.."
REPO_DIR="$(pwd)"
echo -e "${BLUE}Working in: ${REPO_DIR}${NC}"
echo ""

# ─── 1. Check Python ─────────────────────────────────────────
echo -e "${BLUE}Step 1: Checking Python...${NC}"
if command -v python3 >/dev/null 2>&1; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}  ✓ Python $PY_VERSION found${NC}"
    PY=python3
else
    echo -e "${RED}  ✗ Python not found!${NC}"
    echo ""
    echo "  Install Python 3.10+ from https://python.org/downloads/"
    echo "  Or via Homebrew: brew install python@3.11"
    exit 1
fi
echo ""

# ─── 2. Virtual environment ──────────────────────────────────
echo -e "${BLUE}Step 2: Creating virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    $PY -m venv .venv
    echo -e "${GREEN}  ✓ Created .venv${NC}"
else
    echo -e "${GREEN}  ✓ .venv already exists${NC}"
fi
source .venv/bin/activate
echo ""

# ─── 3. Install Python dependencies ──────────────────────────
echo -e "${BLUE}Step 3: Installing Python packages (~2 minutes)...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "${GREEN}  ✓ All packages installed${NC}"
echo ""

# ─── 4. Install Chromium ─────────────────────────────────────
echo -e "${BLUE}Step 4: Installing Chromium browser (~2 minutes, 130MB)...${NC}"
python -m playwright install chromium
echo -e "${GREEN}  ✓ Chromium ready${NC}"
echo ""

# ─── 5. Configure .env ───────────────────────────────────────
echo -e "${BLUE}Step 5: Configure credentials${NC}"
if [ -f ".env" ]; then
    echo -e "${YELLOW}  .env already exists. Keep it? (y/n)${NC}"
    read -r KEEP
    if [ "$KEEP" = "y" ] || [ "$KEEP" = "Y" ]; then
        echo "  Keeping existing .env"
        SKIP_ENV=1
    fi
fi

if [ -z "$SKIP_ENV" ]; then
    echo ""
    echo "  Please enter your RMS2 credentials."
    echo "  (Press Enter to skip optional fields)"
    echo ""

    read -p "  RMS2 email: " RMS_USER
    read -s -p "  RMS2 password: " RMS_PASS
    echo ""

    echo ""
    echo "  Email delivery (optional — press Enter to skip):"
    read -p "  Your Outlook email for sending reports: " SMTP_E
    SMTP_P=""
    if [ -n "$SMTP_E" ]; then
        read -s -p "  Outlook app password: " SMTP_P
        echo ""
        read -p "  Recipients (comma-separated): " RECIPS
    fi

    cat > .env << ENVEOF
# RMS2 login
RMS_USERNAME=$RMS_USER
RMS_PASSWORD=$RMS_PASS

# Email delivery
SMTP_EMAIL=$SMTP_E
SMTP_PASSWORD=$SMTP_P
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
REPORT_RECIPIENTS=$RECIPS

# Currency and auto-commit
INR_TO_USD=86
AUTO_GIT_COMMIT=0
ENVEOF
    chmod 600 .env
    echo -e "${GREEN}  ✓ .env saved (mode 600, readable only by you)${NC}"
fi
echo ""

# ─── 6. Create the Mac .app ──────────────────────────────────
echo -e "${BLUE}Step 6: Creating one-click Mac app...${NC}"
APP_DIR="launchers/Client Growth Report.app"
mkdir -p "$APP_DIR/Contents/MacOS"

cat > "$APP_DIR/Contents/Info.plist" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.koenig.client-growth-report</string>
    <key>CFBundleName</key>
    <string>Client Growth Report</string>
    <key>CFBundleDisplayName</key>
    <string>Client Growth Report</string>
    <key>CFBundleVersion</key>
    <string>5.3</string>
    <key>CFBundleShortVersionString</key>
    <string>5.3</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
PLISTEOF

cat > "$APP_DIR/Contents/MacOS/launcher" << 'LAUNCHEOF'
#!/bin/bash
REPO_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
osascript << APPLE
tell application "Terminal"
    activate
    do script "cd \"${REPO_DIR}\" && ./launchers/run_local_mac_linux.sh"
end tell
APPLE
LAUNCHEOF
chmod +x "$APP_DIR/Contents/MacOS/launcher"

# Try to copy to /Applications so it shows in Launchpad
if [ -w "/Applications" ]; then
    cp -R "$APP_DIR" "/Applications/" 2>/dev/null && \
        echo -e "${GREEN}  ✓ Installed to /Applications (visible in Launchpad)${NC}" || \
        echo -e "${YELLOW}  Could not copy to /Applications. App available at: $APP_DIR${NC}"
else
    echo -e "${YELLOW}  App created at: $APP_DIR${NC}"
    echo "  To install: drag it from Finder into your Applications folder"
fi
echo ""

# ─── DONE ────────────────────────────────────────────────────
echo "============================================================"
echo -e "${GREEN}  Setup complete!${NC}"
echo "============================================================"
echo ""
echo "  How to run the report each month:"
echo ""
echo "    Option 1 — Click \"Client Growth Report\" in Launchpad"
echo "    Option 2 — Run: ./launchers/run_local_mac_linux.sh"
echo "    Option 3 — Open the dashboard: streamlit run streamlit_app.py"
echo "               then click the ▶ Run Now button in the sidebar"
echo ""
echo "  When the Chromium window opens, type the OTP from your Outlook"
echo "  inbox to complete the login."
echo ""
