# 👋 Welcome — Client Growth Report Setup

> A one-page guide to get the **Client Growth Report** running on your laptop.
> You'll only do this once. After that, generating the monthly report is a single click.

**Time needed: ~15 minutes** (most of it is Python downloading).

---

## What you're installing

A small desktop app that:

1. Logs into RMS2 (you'll enter the OTP that Outlook sends you)
2. Downloads the 24-month and 12-month RCB Excel files
3. Computes 12-month growth in USD per client
4. Saves a 4-sheet Excel report into `generated_reports/`
5. (Optionally) emails it to the configured recipients

There is **no server, no cloud cost**. Everything runs on your laptop, on demand.

---

## Step 1 — Install prerequisites

### Mac
1. **Python 3.10 or newer** — https://www.python.org/downloads/macos/
   - During install, leave all defaults checked.
2. **Git** — comes with macOS. To verify, open Terminal and run `git --version`.
   If it prompts you to install developer tools, click **Install**.

### Windows
1. **Python 3.10 or newer** — https://www.python.org/downloads/windows/
   - ⚠️ On the first installer screen, **tick "Add python.exe to PATH"** before clicking Install.
2. **Git for Windows** — https://git-scm.com/download/win
   - Accept all defaults.

---

## Step 2 — Get the code

Open **Terminal** (Mac) or **Git Bash** / **Command Prompt** (Windows) and run:

```bash
cd ~
git clone https://github.com/KoenigSalary/client_growth_report.git
cd client_growth_report
```

That downloads the project to a folder named `client_growth_report` in your home directory.

---

## Step 3 — Run the one-time setup wizard

This is the magic step. It creates a Python environment, installs all dependencies, downloads Chromium, asks you for your RMS2 credentials, and installs a one-click launcher icon.

### Mac
```bash
bash launchers/setup_mac.sh
```

When it asks for credentials:

| Prompt | What to type |
| --- | --- |
| RMS_USERNAME | Your Koenig email (e.g. `yourname@koenig-solutions.com`) |
| RMS_PASSWORD | Your RMS2 password |
| SMTP_* | Press **Enter** to skip — emailing the report is optional |

When done you'll see **Client Growth Report.app** in **/Applications** and the Launchpad.

### Windows
Double-click `launchers\setup_windows.bat` *(or run it from Command Prompt)*.

When done, you'll see a **Client Growth Report** shortcut on your Desktop.

---

## Step 4 — Generate your first report

You have **three ways** to run the report each month — pick whichever feels easiest.

### Option A — Click the app icon (recommended)
- **Mac**: Open Launchpad → click **Client Growth Report**. A dashboard opens in your browser.
- **Windows**: Double-click the **Client Growth Report** shortcut on your Desktop.

In the dashboard (left sidebar), click **▶ Run Now**. A Terminal window will open and ask for the **OTP** that RMS2 just emailed to your Outlook. Type the 6-digit code and press Enter. ~3 minutes later, the report appears in `generated_reports/`.

### Option B — Use the dashboard's Run Now button
Same as Option A — just a different starting point. As long as the dashboard sees you're on a real laptop (not the Cloud), the **▶ Run Now** button shows up automatically.

### Option C — Command line (for power users)
```bash
cd ~/client_growth_report
source .venv/bin/activate     # Mac/Linux
# .venv\Scripts\activate      # Windows
python run_monthly.py
```

---

## Where to find the output

```
client_growth_report/
└── generated_reports/
    └── Client_Growth_Report_<YYYY-MM-DD>.xlsx       ← open this
```

The Excel has 4 sheets:

| Sheet | What it contains |
| --- | --- |
| **Growth Comparison** | Every client, with Previous-12M USD, Current-12M USD, Growth %, URL, CorporateID, UserName |
| **High Growth 5K-50K** | Filter: previous ≤ $5,000 **and** current ≥ $50,000 |
| **Summary** | Aggregated totals + counts |
| **Exceptions** | Rows skipped/flagged during processing |

---

## When something goes wrong

| Symptom | Fix |
| --- | --- |
| `python: command not found` | Re-install Python from python.org and **tick "Add to PATH"** (Windows) or reopen Terminal (Mac). |
| `playwright._impl._api_types.Error: Executable doesn't exist` | Run `playwright install chromium` inside the project folder with `.venv` activated. |
| Stuck on "Waiting for OTP" | Check your Outlook inbox for an email from RMS2; the OTP is valid for 10 minutes. Re-run if it expired. |
| "OTP wrong" 3 times | RMS2 may have temporarily locked the account — wait 10 minutes and try again. |
| Browser window doesn't open | Run from Terminal with `HEADLESS=0 python run_monthly.py` to see what's happening. |

If you're still stuck, screenshot the Terminal window and send it to **Praveen Chaudhary** (praveen.chaudhary@koenig-solutions.com).

---

## Monthly routine (after setup)

Every month, around the **14th**:

1. Click the **Client Growth Report** app icon
2. Click **▶ Run Now**
3. Enter the OTP from Outlook
4. Wait ~3 minutes
5. Open `generated_reports/Client_Growth_Report_<today>.xlsx`

That's the whole job. 🎉

---

## Optional: share your report with the team

If `SMTP_*` is filled in `.env`, the run also emails the Excel automatically — no extra step.

Otherwise, attach the file from `generated_reports/` to your usual mailing list.

---

## Security notes

- `.env` contains your **RMS2 password in plain text**. It lives only on your laptop and is in `.gitignore`, so it's never pushed to GitHub.
- The setup script automatically runs `chmod 600 .env` on Mac/Linux so only you can read it.
- The dashboard's default login is `admin` / `admin123` — you can change it in `streamlit_app.py` if you want.

---

**Maintainer:** Praveen Chaudhary · praveen.chaudhary@koenig-solutions.com
**Repo:** https://github.com/KoenigSalary/client_growth_report
**Version:** v5.3
