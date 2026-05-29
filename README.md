# Client Growth Report — Dual-Mode v4.0

Two ways to run, one shared codebase. Use whichever is convenient.

| | **Streamlit Cloud** (always-on URL) | **Local Computer** (run on demand) |
|---|---|---|
| What it does | View reports, upload files manually | **Download fresh data from RMS2 with OTP** + everything else |
| OTP handling | Not possible (no browser to interact with) | ✅ Real Chromium window opens — you type OTP into RMS2 itself |
| Best for | Day-to-day viewing, sharing reports | Monthly download on the 14th |
| Setup | Push to GitHub, configure secrets | Double-click a launcher script |

The app **auto-detects** where it's running and shows the appropriate modes.

---

## 🖥️ Setup A — Run Locally (for RMS2 downloads)

### Prerequisites
- **Python 3.10 or newer** ([download](https://python.org))
- Internet access

### One-Click Launch

**Windows:**
1. Double-click `launchers/run_local_windows.bat`
2. Wait ~2-3 minutes on first run (installs dependencies + Chromium)
3. Your browser opens to `http://localhost:8501`

**macOS / Linux:**
1. Open Terminal in this folder
2. Run: `./launchers/run_local_mac_linux.sh`
3. Wait ~2-3 minutes on first run
4. Your browser opens automatically

### First-Time Setup: Save Credentials (Optional)

Copy `.env.example` to `.env` and fill in your RMS2 login:
```
RMS_USERNAME=your-email@koenig-solutions.com
RMS_PASSWORD=your-rms2-password
```
(If you skip this, the app will ask for credentials in a form.)

### Using Local Mode

1. Open the app at `http://localhost:8501`
2. Login: `admin` / `admin123`
3. Sidebar shows three modes — pick **🌐 Local RMS2 Download (visible browser + OTP)**
4. Click **▶️ Launch Browser & Start Login**
5. A **Chromium window pops up**, automatically fills email + password, clicks Login
6. RMS2 shows the OTP screen — **check your Outlook, then type the OTP directly into the Chromium window** and click Submit
7. Streamlit detects you've authenticated and continues:
   - Downloads 24-month data
   - Downloads 12-month data
   - Closes the browser
8. Click **Generate Growth Report & Email**
9. Done!

---

## ☁️ Setup B — Streamlit Cloud (for viewing & manual uploads)

### Push to GitHub

1. Upload all files in this repo to https://github.com/KoenigSalary/client_growth_report
2. Streamlit Cloud auto-redeploys

### Configure Secrets (Optional, for email)

Streamlit Cloud → **Manage app → Settings → Secrets**:
```toml
SMTP_EMAIL        = "you@koenig-solutions.com"
SMTP_PASSWORD     = "outlook-app-password"
SMTP_SERVER       = "smtp.office365.com"
SMTP_PORT         = "587"
REPORT_RECIPIENTS = "boss@x.com,team@x.com"
```

### Using Cloud Mode

- **📥 Manual Upload** — drag & drop the two RCB Excel files you downloaded from RMS2 (in your normal browser, with OTP), then click Generate Report
- **🤖 Use Last Downloaded Files** — only works if files were synced to the `data/` folder

---

## 📂 File Reference

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Dashboard — auto-detects environment |
| `rms2_downloader_local.py` | Visible-Chromium downloader (local only) |
| `process_report.py` | Builds the 4-sheet Excel output |
| `requirements.txt` | Python deps |
| `packages.txt` | Empty — no OS deps needed |
| `launchers/run_local_windows.bat` | One-click launcher for Windows |
| `launchers/run_local_mac_linux.sh` | One-click launcher for macOS/Linux |
| `.env.example` | Template for local credentials |

---

## 🔑 Dashboard Login

- Username: `admin`
- Password: `admin123`
- "Forgot Password?" lets you set a new one without email verification

---

## 📊 Report Output

`Client_Growth_Report_YYYYMMDD_HHMMSS.xlsx` — 4 sheets:

1. **Growth Comparison** — all clients, sorted by Growth_USD desc
2. **High Growth 5K-50K USD** — Previous ≤ $5K AND Current ≥ $50K
3. **Summary** — top performer + overall stats
4. **Exceptions** — rows with negative values

Columns: `CorporateID`, `CompanyName`, `UserName`, `URL`,
`Previous_12M_USD`, `Current_12M_USD`, `Growth_USD`, `Growth_%`

Exchange rate: **1 USD = 86 INR** (edit in `process_report.py` if needed)

---

## 🩺 Troubleshooting

| Symptom | Fix |
|---|---|
| "Python not found" on Windows | Install Python 3.10+ from python.org; check "Add to PATH" |
| `playwright install` fails | Run `python -m playwright install --with-deps chromium` manually |
| Chromium window doesn't appear | Ensure you're running locally (not on Streamlit Cloud); badge in top-right should say 🖥️ LOCAL MODE |
| OTP timeout | You have 5 minutes to type the OTP. Just click Cancel and try again. |
| Wrong files in Last Downloaded | Run Local Mode again — files are auto-overwritten |

---

## 📅 Monthly Workflow

1. Around the 14th, open your laptop
2. Double-click `run_local_windows.bat` (or `.sh` on Mac/Linux)
3. Wait for the Streamlit page to open
4. Pick "🌐 Local RMS2 Download"
5. Click Launch → OTP → wait → Generate Report
6. Email is sent automatically (if configured)
7. Total time: **~5 minutes**

That's it. No more daily failed GitHub Actions runs.
