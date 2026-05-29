"""
Helper: ensure Playwright's Chromium browser is installed.
Safe to call multiple times; gracefully handles permission errors on
restricted hosts like Streamlit Cloud where /root is inaccessible.
"""
import os
import subprocess
import sys
from pathlib import Path


def _safe_exists(p: Path) -> bool:
    """Check existence without raising PermissionError on restricted dirs."""
    try:
        return p.exists()
    except (PermissionError, OSError):
        return False


def _safe_has_chromium(d: Path) -> bool:
    """Check if a directory contains a chromium-* subfolder, ignoring errors."""
    try:
        if not _safe_exists(d):
            return False
        return any(d.glob("chromium-*"))
    except (PermissionError, OSError, StopIteration):
        return False


def ensure_chromium_installed() -> tuple[bool, str]:
    """
    Returns (success, message).
    Tries `playwright install chromium` if the binary isn't present yet.
    """
    # Build a list of candidate cache directories WITHOUT crashing on dirs
    # we can't access. Streamlit Cloud runs as `appuser`, so /root is forbidden.
    candidate_dirs = []
    try:
        candidate_dirs.append(Path.home() / ".cache" / "ms-playwright")
    except Exception:
        pass

    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if env_path:
        candidate_dirs.append(Path(env_path))

    # Add a few common locations -- but check permissions first
    for extra in [
        Path("/home/appuser/.cache/ms-playwright"),
        Path("/home/adminuser/venv/lib/python3.13/site-packages/playwright/driver/package/.local-browsers"),
        Path("/tmp/ms-playwright"),
    ]:
        candidate_dirs.append(extra)

    # Quick check -- already installed?
    for d in candidate_dirs:
        if _safe_has_chromium(d):
            return True, f"Chromium already installed at {d}"

    # Not found -- install it
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return True, "Chromium installed successfully"
        # Retry with --with-deps in case OS libs are also missing
        result2 = subprocess.run(
            [sys.executable, "-m", "playwright", "install",
             "--with-deps", "chromium"],
            capture_output=True, text=True, timeout=600,
        )
        if result2.returncode == 0:
            return True, "Chromium installed (with OS deps)"
        # Return useful diagnostic text
        tail = (result.stderr or result.stdout or "")[-500:]
        return False, f"playwright install failed.\nLast 500 chars:\n{tail}"
    except subprocess.TimeoutExpired:
        return False, "playwright install timed out (>5 min)"
    except Exception as e:
        return False, f"Could not invoke playwright install: {e}"
