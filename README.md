# Client Growth Report

Automated client growth analysis for Koenig Solutions.
Downloads RMS2 RCB data monthly, computes 12-month growth in USD, and
generates Excel reports.

## Architecture

```
GitHub Actions (monthly on the 14th)
    |
    +-- download_rms2_data.py
    |       Plays back the RMS2 UI with Playwright/Chromium:
    |         1. Login
    |         2. Open RCB page
    |         3. Filter "Last Months = 24" -> Export Excel
    |         4. Filter "Last Months = 12" -> Export Excel
    |       Commits both files to /data/
    |
    +-- Streamlit Cloud (always running)
            streamlit_app.py reads data/, runs process_report.py,
            shows the dashboard, optionally emails the report.
```

## Files

| File | Purpose |
|------|---------|
| `streamlit_app.py` | The dashboard. Login: `admin` / `admin123` |
| `process_report.py` | Pure data processing -> 4-sheet Excel output |
| `download_rms2_data.py` | Playwright script that downloads RCB data |
| `.github/workflows/download-rms2-data.yml` | Monthly automation on the 14th |
| `requirements.txt` | Python deps for Streamlit Cloud |
| `packages.txt` | Empty -- no OS packages needed on Streamlit Cloud |
| `assets/koenig_logo.png` | Branding |
| `data/` | RCB Excel files (populated by GitHub Actions) |
| `generated_reports/` | Output of the Streamlit dashboard |

## GitHub Secrets Required

Set in **Settings -> Secrets and variables -> Actions**:

| Secret | Value |
|--------|-------|
| `RMS_USERNAME` | RMS2 login email |
| `RMS_PASSWORD` | RMS2 password |

## Streamlit Cloud Secrets (optional)

In Streamlit Cloud **Manage app -> Secrets**:

```toml
GITHUB_TOKEN       = "ghp_..."               # to trigger Actions from UI
SMTP_EMAIL         = "you@yourdomain.com"    # for emailing reports
SMTP_PASSWORD      = "app-password"
SMTP_SERVER        = "smtp.office365.com"
SMTP_PORT          = "587"
REPORT_RECIPIENTS  = "a@x.com,b@x.com"
```

## Output Format

`Client_Growth_Report_YYYYMMDD_HHMMSS.xlsx` -- 4 sheets:

1. **Growth Comparison** -- all clients, sorted by growth USD desc
2. **High Growth 5K-50K USD** -- Previous <= $5K AND Current >= $50K
3. **Summary** -- top performer + overall statistics
4. **Exceptions** -- rows with negative values

Columns: CorporateID, CompanyName, UserName, URL, Previous_12M_USD,
Current_12M_USD, Growth_USD, Growth_%

## Manual Trigger

GitHub -> Actions -> "Download RMS2 Data" -> Run workflow

## Login to Dashboard

- URL: your Streamlit Cloud app URL
- Username: `admin`
- Password: `admin123`
- "Forgot Password?" lets you set a new one without email
