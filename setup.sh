#!/bin/bash
echo "Installing Playwright Chromium with OS dependencies..."
python -m playwright install --with-deps chromium || \
  python -m playwright install chromium || \
  echo "Playwright install returned non-zero, will rely on packages.txt"
echo "Done."
