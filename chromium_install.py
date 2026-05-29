"""
Helper: ensure Playwright's Chromium browser is installed.
Run this once before launching Playwright. Safe to call multiple times.
"""
import subprocess
import sys
import shutil
from pathlib import Path


def ensure_chromium_installed() -> tuple[bool, str]:
    """
    Returns (success, message).
    Tries `playwright install chromium` if the binary isn't present yet.
    """
    # Quick check: does the chromium binary already exist?
    home = Path.home()
    cache_dirs = [
        home / ".cache" / "ms-playwright",
        Path("/home/appuser/.cache/ms-playwright"),
        Path("/root/.cache/ms-playwright"),
    ]
    for d in cache_dirs:
        if d.exists() and any(d.glob("chromium-*")):
            return True, f"Chromium already installed at {d}"

    # Try to install
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return True, "Chromium installed successfully"
        # Try with --with-deps (in case OS libs are also missing)
        result2 = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
            capture_output=True, text=True, timeout=600,
        )
        if result2.returncode == 0:
            return True, "Chromium installed with deps"
        return False, (
            f"playwright install failed.\n"
            f"stdout: {result.stdout[-500:]}\n"
            f"stderr: {result.stderr[-500:]}"
        )
    except subprocess.TimeoutExpired:
        return False, "playwright install timed out (>5 minutes)"
    except Exception as e:
        return False, f"Could not invoke playwright install: {e}"
