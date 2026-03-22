# 🚀 Deployment Fix Guide – Client Growth Report

## Problems Fixed

### 1. ❌ Streamlit Cloud Startup Failure (Dependency Conflicts)

**Root cause:**  
`packages.txt` listed system packages (`libasound2`, `libcups2`, `libglib2.0-0`, etc.)  
that **no longer exist** on Streamlit Cloud's current OS (Debian Bookworm / Ubuntu 24.04).  
Those libraries were renamed with a `t64` suffix in newer Debian versions, causing conflicts:

```
libasound2t64 conflicts with libasound2
libcups2t64   conflicts with libcups2
libglib2.0-0  requires libffi7 and libpcre3 (no longer present)
```

**Fix:**  
`packages.txt` is now **empty** (just a comment explaining why).  
The Streamlit Cloud app **does not need a browser** — it only reads Excel files.  
Playwright / Chromium runs inside **GitHub Actions**, not Streamlit Cloud.

---

### 2. ❌ GitHub Actions Monthly Run (14th) Would Fail

**Root cause:**  
The workflow did not pin `pandas` or `openpyxl` as a Python dependency,  
and `playwright install-deps` needed to be the correct command.

**Fix:**  
`download-rms2-data.yml` now installs:
```yaml
pip install playwright pandas openpyxl python-dotenv requests
playwright install chromium
playwright install-deps chromium   # auto-installs correct OS libs
```
This lets GitHub Actions install the right system packages for **whatever Ubuntu version** it uses — no hardcoding required.

---

### 3. ✅ UserName Column in Output

`process_report.py` correctly reads the `UserName` column from the RCB source data  
(it IS a proper data column, not just cell A1 — that cell is the header label).  
UserName is included in all output sheets: Growth Comparison, High Growth, Exceptions.

---

### 4. ✅ Corp_URL / URL Column

Corp_URL is taken from the `URL` column in the 12-month RCB export (e.g. `@nh-mitte.de`).  
If the source file has no URL column, a fallback URL is generated:  
`https://rms2.koenig-solutions.com/corporate/{CorporateID}`

---

## Files to Update in GitHub Repo

| File | Action |
|------|--------|
| `packages.txt` | **Replace** with the new file (effectively empty) |
| `requirements.txt` | **Replace** — remove `playwright` (only needed by GitHub Actions) |
| `.github/workflows/download-rms2-data.yml` | **Replace** with fixed workflow |
| `process_report.py` | **Replace** with fixed version |

---

## How to Deploy

1. Go to https://github.com/KoenigSalary/client_growth_report
2. Edit each file (or push via git) with the provided fixed versions
3. Streamlit Cloud will auto-redeploy on the next push
4. The app should start without dependency errors

---

## GitHub Secrets Required

Make sure these are set in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `RMS_USERNAME` | Your RMS2 login email |
| `RMS_PASSWORD` | Your RMS2 password |

---

## Monthly Automation (14th of each month)

The workflow in `.github/workflows/download-rms2-data.yml` is scheduled:
```yaml
schedule:
  - cron: '0 6 14 * *'   # 14th of every month at 06:00 UTC
```
**You can also trigger it manually** via:  
GitHub → Actions → "Download RMS2 Data" → Run workflow

---

## Expected Output Structure (4 Sheets)

| Sheet | Rows | Key Columns |
|-------|------|-------------|
| Growth Comparison | ~5,680 | CorporateID, CompanyName, UserName, URL, Previous_12M_USD, Current_12M_USD, Growth_USD, Growth_% |
| High Growth 5K-50K USD | ~15 | Same — filtered: Prev ≤ $5K AND Curr ≥ $50K |
| Summary | 20 | Metric / Value (top performer + overall stats) |
| Exceptions | ~18 | Negative-value rows flagged for review |

---

## Quick Verification Checklist

After deploying and running:
- [ ] Streamlit app starts without errors
- [ ] 4 sheets in output Excel
- [ ] `UserName` column populated (not blank)
- [ ] `URL` column shows actual URLs from source (e.g. `@nh-mitte.de`)
- [ ] High Growth sheet has ~15 rows (not 236 or 501)
- [ ] GitHub Actions runs successfully on the 14th
