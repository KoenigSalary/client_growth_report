# Client Growth Report (OTP-aware v3.0)

Interactive client-growth analysis for Koenig Solutions.
Downloads RMS2 RCB data via the Streamlit dashboard, handles the new
**OTP-on-every-login** requirement, and emails the resulting Excel report.

---

## 🏗️ New Architecture (OTP-aware)

Because RMS2 now sends a fresh OTP to your Outlook every single login,
**fully unattended cron-based automation is no longer possible**.
The flow now runs **interactively** from the Streamlit dashboard:

```
You open the Streamlit app
    ↓
Click "▶ Run RMS2 Download (Manual Trigger)"
    ↓
Streamlit launches headless Chromium in the background
    ↓
Script enters username + password automatically
    ↓
RMS2 sends a 6-digit OTP to your Outlook inbox
    ↓
Streamlit shows an OTP input box:
   ┌───────────────────────────────┐
   │  📧 OTP Required               │
   │  [______]  ✅ Submit OTP       │
   └───────────────────────────────┘
    ↓
You check Outlook → paste the OTP → click Submit
    ↓
Script continues: downloads 24M + 12M Excel files
    ↓
Click "📊 Generate Report & Email"
    ↓
Done! Report is emailed and downloadable.
```

The whole process takes ~3-5 minutes including waiting for the OTP email.

---

## 📁 Files in this repo

| File | Purpose |
|------|---------|
| `streamlit_app.py` | The dashboard. Login: `admin` / `admin123` |
| `rms2_downloader.py` | Threaded Playwright session with OTP handoff |
| `process_report.py` | Builds the 4-sheet Excel output |
| `requirements.txt` | Python deps including Playwright |
| `packages.txt` | Chromium OS libs for Streamlit Cloud |
| `setup.sh` | Installs Chromium binary (`playwright install chromium`) |
| `.github/workflows/download-rms2-data.yml` | Disabled (OTP not automatable) |

---

## 🚀 Streamlit Cloud Setup

### 1. Push these files to your GitHub repo

Just replace the previous repo contents with everything in this folder.

### 2. Configure secrets in Streamlit Cloud

Open your app → **Manage app → Settings → Secrets** and add:

```toml
# RMS2 login (required for Live Download mode)
RMS_USERNAME = "monika.chopra@koenig-solutions.com"
RMS_PASSWORD = "your-rms2-password"

# Optional: email delivery
SMTP_EMAIL        = "you@koenig-solutions.com"
SMTP_PASSWORD     = "your-outlook-app-password"
SMTP_SERVER       = "smtp.office365.com"
SMTP_PORT         = "587"
REPORT_RECIPIENTS = "boss@koenig-solutions.com,team@koenig-solutions.com"
```

### 3. Streamlit Cloud will:
- Install `packages.txt` (Chromium OS libs)
- Install `requirements.txt` (Python deps)
- Run `setup.sh` (downloads the Chromium browser binary)
- Start the app

This takes ~3-5 minutes on first deployment.

---

## 🎯 Using the Dashboard

After logging in (`admin` / `admin123`), the sidebar offers three modes:

### 🌐 Live RMS2 Download (with OTP) — primary workflow
1. Click **"▶ Run RMS2 Download (Manual Trigger)"**
2. Wait for the OTP screen to appear (~10 seconds)
3. Check your Outlook for the 6-digit code from RMS2
4. Paste it into the OTP box and click **"✅ Submit OTP"**
5. Wait for both downloads to complete (~1-2 minutes total)
6. Click **"📊 Generate Report & Email"**

### 📥 Manual Upload — if RMS2 is down or you have files already
Upload the two `.xlsx` files yourself, then generate the report.

### 🤖 Use Last Downloaded Files
Re-process the most recent download without going to RMS2 again.

---

## ✏️ Forgot Dashboard Password

On the login screen, click **"Forgot Password?"** to set a new password
without any email verification. Default is `admin` / `admin123`.

---

## 📑 Output Format

`Client_Growth_Report_YYYYMMDD_HHMMSS.xlsx` — **4 sheets**:

1. **Growth Comparison** — all clients, sorted by Growth_USD descending
2. **High Growth 5K-50K USD** — Previous ≤ $5K AND Current ≥ $50K
3. **Summary** — top performer + overall statistics
4. **Exceptions** — rows with negative values flagged for review

Columns: `CorporateID`, `CompanyName`, `UserName`, `URL`,
`Previous_12M_USD`, `Current_12M_USD`, `Growth_USD`, `Growth_%`

Exchange rate: **1 USD = 86 INR** (configurable in `process_report.py`)

---

## ⚠️ Known Constraint: No Fully-Automatic Monthly Run

Because OTP is required on every RMS2 login and OTPs need a human to
read the email and type the code, the monthly cron-style automation
that ran on the 14th has been **disabled**.

To work around this:
- Set a calendar reminder for the 14th of each month
- Open the Streamlit app
- Complete the OTP flow once (~3-5 minutes of your time)
- The report is generated and emailed automatically from there

If Koenig IT later provides a service account that bypasses OTP, the
old GitHub Actions automation can be re-enabled by editing
`.github/workflows/download-rms2-data.yml` (remove the `if: false`).
