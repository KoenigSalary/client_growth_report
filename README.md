# Client Growth Report — v5.3

Automated monthly growth analysis for Koenig Solutions clients,
with RMS2 OTP support. Designed for **two operators** (maker + one colleague)
to run from their own laptops, sharing a single read-only dashboard for viewing.

## 🚀 Quick start

- **New user / colleague?** Follow [`COLLEAGUE_SETUP.md`](COLLEAGUE_SETUP.md) — one-page guide, ~15 min.
- **Already set up?** See [`HOW_TO_RUN.md`](HOW_TO_RUN.md) for the 3 ways to launch.
- **Maintainer / developer?** Read on.

## 🗺️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  STREAMLIT CLOUD (shared URL for everyone)                          │
│  https://clientgrowthreport-xxxx.streamlit.app                      │
│  ───────────────────────────────────────                            │
│  • Anyone can VIEW past reports                                     │
│  • Download history (Excel files)                                   │
│  • Mobile-friendly                                                  │
│  • Login: admin / admin123                                          │
└─────────────────────────────────────────────────────────────────────┘
                                ↑
                                │ Reads files committed to data/ and
                                │ generated_reports/ in this git repo
                                │
┌─────────────────────────────────────────────────────────────────────┐
│  YOUR LAPTOP (once per month, on the 14th)                          │
│  ───────────────────────────────────────                            │
│  Double-click  run_local_windows.bat   (Windows)                    │
│             or run_local_mac_linux.sh  (Mac/Linux)                  │
│                                                                     │
│  This runs run_monthly.py which does END-TO-END:                    │
│    1. Opens Chromium window                                         │
│    2. Auto-fills RMS2 email + password                              │
│    3. ⏸  You type the OTP into the Chromium window                 │
│    4. Downloads 24-month + 12-month Excel from RMS2                 │
│    5. Builds the 4-sheet growth report                              │
│    6. Emails it (if SMTP configured)                                │
│    7. Commits + pushes new files to git                             │
│                                                                     │
│  Total time: ~5 minutes (mostly waiting for downloads)              │
└─────────────────────────────────────────────────────────────────────┘
```

## 📦 What's in this repo

| File / Folder | Purpose |
|---|---|
| `streamlit_app.py` | The Streamlit Cloud viewer dashboard |
| `run_monthly.py` | End-to-end script that does the entire monthly job |
| `rms2_downloader_local.py` | Playwright module: visible Chromium + RMS2 navigation |
| `process_report.py` | Builds the 4-sheet Excel growth report |
| `launchers/run_local_*` | One-click monthly run on Windows / Mac / Linux |
| `launchers/view_reports_*` | One-click "view reports locally" (optional) |
| `requirements.txt` | Python deps |
| `packages.txt` | Empty (Streamlit Cloud doesn't need browser libs) |
| `.env.example` | Template — copy to `.env` and fill in |
| `data/` | RCB Excel files (committed to git after each local run) |
| `generated_reports/` | Generated reports (committed to git after each local run) |
| `assets/koenig_logo.png` | Branding |

---

## 🚀 Setup (one-time, on your laptop)

### Prerequisites
- **Python 3.10 or newer** ([download](https://python.org))
- **Git** ([download](https://git-scm.com))

### Steps

1. **Clone the repo to your laptop:**
   ```bash
   git clone https://github.com/KoenigSalary/client_growth_report.git
   cd client_growth_report
   ```

2. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   ```
   Then open `.env` in any text editor and fill in:
   - `RMS_USERNAME` and `RMS_PASSWORD` (your RMS2 login)
   - `SMTP_*` and `REPORT_RECIPIENTS` (optional, for auto-email)
   - `AUTO_GIT_COMMIT=1` (so Streamlit Cloud sees new reports)

3. **First-time install** — just double-click the launcher and let it auto-install:
   - **Windows:** `launchers\run_local_windows.bat`
   - **Mac/Linux:** `./launchers/run_local_mac_linux.sh`
   - The launcher creates a venv, installs dependencies, downloads Chromium

That's it — first run takes ~3 minutes for installation, then proceeds.

---

## 🗓️ Monthly Workflow

Every 14th (or whenever you want fresh data):

1. **Double-click** the launcher (`.bat` on Windows, `.sh` on Mac/Linux)
2. **Watch** as a Chromium window pops up showing RMS2
3. **Wait** until the email + password are auto-filled and you reach the OTP screen
4. **Check Outlook** for the 6-digit code
5. **Type the OTP** into the Chromium window's RMS2 OTP field, click Submit/Verify
6. **Walk away** — the script handles everything else:
   - Navigates to RCB page
   - Filters 24 months, exports Excel
   - Filters 12 months, exports Excel
   - Closes browser
   - Builds report
   - Sends email
   - Commits to git
7. **Done!** ~5 minutes total.

You can verify by:
- Checking your Outlook for the report email
- Refreshing the Streamlit Cloud URL (new report appears in history)

---

## ☁️ Streamlit Cloud Setup (one-time)

The Streamlit Cloud app is **view-only** — colleagues can see past reports
on any device. Setup:

1. Push this repo to GitHub
2. Connect it to Streamlit Cloud at https://share.streamlit.io
3. Set the main file: `streamlit_app.py`
4. **No secrets needed on Streamlit Cloud** — it only reads committed files

The dashboard at `https://clientgrowthreport-xxxx.streamlit.app` will:
- Show the latest report (downloadable)
- Show the full report history
- Display raw data file status
- Provide instructions for the monthly run

---

## 🔐 Credentials Storage

| Where | What | How |
|---|---|---|
| **Your laptop** | RMS2 + SMTP credentials | `.env` file (gitignored) |
| **GitHub Secrets** | Not used (the local laptop is now in charge) | n/a |
| **Streamlit Cloud Secrets** | Not used (cloud is view-only) | n/a |

---

## 📊 Report Output

`Client_Growth_Report_YYYYMMDD_HHMMSS.xlsx` — 4 sheets:

1. **Growth Comparison** — all clients, sorted by Growth_USD desc
2. **High Growth 5K-50K USD** — Previous ≤ $5K AND Current ≥ $50K
3. **Summary** — top performer + overall stats
4. **Exceptions** — rows with negative values

Columns: `CorporateID`, `CompanyName`, `UserName`, `URL`,
`Previous_12M_USD`, `Current_12M_USD`, `Growth_USD`, `Growth_%`

Exchange rate: **1 USD = 86 INR** (edit `process_report.py` to change).

---

## 🩺 Troubleshooting

| Symptom | Fix |
|---|---|
| "Python not found" | Install Python 3.10+ from python.org, tick "Add to PATH" on Windows |
| Chromium window doesn't appear | The launcher runs `playwright install chromium` first time — give it 2-3 min |
| OTP timeout (5 min) | You missed it. Click Cancel in the script or just re-run the launcher |
| "Cannot push to git" | `git remote set-url origin` with a token-authenticated URL, or set `AUTO_GIT_COMMIT=0` |
| Streamlit Cloud doesn't show new report | Check that `AUTO_GIT_COMMIT=1` in `.env` AND `git push` worked from your laptop |
| Email not sent | Check `SMTP_EMAIL`/`SMTP_PASSWORD` in `.env`; Outlook may need an "app password" |

---

## 💡 Tips

- **Calendar reminder**: set a recurring monthly reminder for the 14th
- **Headless run**: if you want truly hands-free (no OTP), ask Koenig IT for
  a service account that bypasses 2FA, then re-enable the GitHub Actions
  workflow in `.github/workflows/`
- **View on phone**: the Streamlit Cloud URL works on mobile browsers
