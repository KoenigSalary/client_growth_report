name: Download RMS2 Data

on:
  # Run monthly on the 14th at 6 AM UTC
  schedule:
    - cron: '0 6 14 * *'

  # Allow manual trigger from GitHub Actions UI
  workflow_dispatch:

permissions:
  contents: write

jobs:
  download-data:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          persist-credentials: true

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install playwright pandas openpyxl python-dotenv requests

      - name: Install Playwright Chromium browser + OS dependencies
        # playwright install-deps installs the correct system packages for the current
        # Ubuntu version automatically — no manual packages.txt conflicts.
        run: |
          playwright install chromium
          playwright install-deps chromium

      - name: Create data directory
        run: mkdir -p data

      - name: Download RMS2 data files
        env:
          RMS_USERNAME: ${{ secrets.RMS_USERNAME }}
          RMS_PASSWORD: ${{ secrets.RMS_PASSWORD }}
          RMS_LOGIN_URL: 'https://rms2.koenig-solutions.com'
          RCB_BASE_URL: 'https://rms2.koenig-solutions.com/RCB'
        run: |
          python download_rms2_data.py

      - name: Verify downloaded files
        run: |
          echo "=== Checking downloaded files ==="
          ls -lh data/

          if [ ! -f "data/RCB_24months.xlsx" ]; then
            echo "ERROR: RCB_24months.xlsx not found!"
            exit 1
          fi

          if [ ! -f "data/RCB_12months.xlsx" ]; then
            echo "ERROR: RCB_12months.xlsx not found!"
            exit 1
          fi

          echo "SUCCESS: Both data files present."

      - name: Configure Git for commit
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "GitHub Actions Bot"

      - name: Commit and push updated data files
        run: |
          git add data/RCB_24months.xlsx data/RCB_12months.xlsx

          if git diff --staged --quiet; then
            echo "No data changes to commit (files unchanged)."
          else
            git commit -m "chore: update RMS2 data files [$(date +'%Y-%m-%d %H:%M UTC')]"
            git push
          fi

      - name: Upload error screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: error-screenshots
          path: data/*error*.png
          if-no-files-found: ignore
