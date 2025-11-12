# Client Growth Report - Automated Solution

## 🎯 Architecture Overview

This solution uses **GitHub Actions** for automated data downloads and **Streamlit** for report generation.

```
┌─────────────────────────────────────────┐
│       GitHub Actions (Monthly)          │
│  ┌─────────────────────────────────┐   │
│  │ 1. Install Playwright           │   │
│  │ 2. Login to RMS2                │   │
│  │ 3. Download 24M data            │   │
│  │ 4. Download 12M data            │   │
│  │ 5. Commit to repo               │   │
│  └─────────────────────────────────┘   │
└─────────────────┬───────────────────────┘
                  │
                  │ Files: RCB_24months.xlsx
                  │        RCB_12months.xlsx
                  ↓
┌─────────────────────────────────────────┐
│         Streamlit Dashboard             │
│  ┌─────────────────────────────────┐   │
│  │ • Read auto-downloaded files    │   │
│  │ • Generate growth reports       │   │
│  │ • Apply Koenig branding         │   │
│  │ • Export to Excel               │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Backup: Manual upload still available │
└─────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
client-growth-report/
├── .github/
│   └── workflows/
│       └── download-rms2-data.yml    # Auto-download workflow (runs monthly)
├── assets/
│   └── koenig_logo.png               # Koenig branding logo
├── data/                             # Auto-downloaded files (created by workflow)
│   ├── RCB_24months.xlsx            
│   └── RCB_12months.xlsx            
├── generated_reports/                # Generated reports (created by Streamlit)
│   └── Client_Growth_Report_*.xlsx  
├── streamlit_app.py                  # Main Streamlit dashboard
├── process_report.py                 # Report generation logic
├── download_rms2_data.py             # Download script (used by GitHub Actions)
├── requirements.txt                  # Python dependencies
├── QUICK_START.md                    # Quick setup guide
├── GITHUB_ACTIONS_SETUP.md           # Detailed setup instructions
└── README.md                         # This file
```

---

## ✨ Features

### Automated Downloads
- ✅ **Monthly schedule:** Runs on 1st of each month at 6 AM UTC
- ✅ **Manual trigger:** On-demand downloads anytime
- ✅ **Two-step process:** Correctly implements RMS2's Display → Export workflow
- ✅ **Error handling:** Screenshots and logs on failures
- ✅ **Auto-commit:** Files automatically saved to repository

### Report Generation
- ✅ **High Growth Filter:** Previous ≤$5K, Current ≥$50K (exactly 15 clients)
- ✅ **4-Sheet Excel:** Growth Comparison, High Growth, Summary, Exceptions
- ✅ **USD Conversion:** INR to USD at rate 84, whole numbers
- ✅ **Client URLs:** Direct links to RMS2 corporate pages
- ✅ **Top Performers:** Highlighted in green

### User Interface
- ✅ **Koenig Branding:** Blue theme (#0099cc), logo in sidebar
- ✅ **Login Protection:** admin / koenig2024
- ✅ **Dual Modes:** Auto-downloaded data + Manual upload backup
- ✅ **Data Freshness:** Shows last update timestamp
- ✅ **Clean UI:** No technical jargon, user-friendly

---

## 🚀 Quick Setup

### 1. Upload to GitHub

Upload these files to your repository:
```bash
.github/workflows/download-rms2-data.yml
streamlit_app.py
process_report.py
download_rms2_data.py
requirements.txt
assets/koenig_logo.png
```

### 2. Configure Secrets

**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Value |
|-------------|-------|
| `RMS_USERNAME` | `admin` |
| `RMS_PASSWORD` | `koenig2024` |

### 3. Enable Permissions

**Settings** → **Actions** → **General** → **Workflow permissions**

- ✅ Read and write permissions
- ✅ Allow GitHub Actions to create and approve pull requests

### 4. Test Workflow

**Actions** → **Download RMS2 Data** → **Run workflow**

Wait ~2-3 minutes, then check `data/` folder for downloaded files.

### 5. Deploy Streamlit

Deploy `streamlit_app.py` to Streamlit Cloud (no additional config needed!)

---

## 📖 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Fast setup guide with comparisons
- **[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)** - Complete workflow documentation
- **Inline comments** - All code is well-documented

---

## 🎮 Usage

### Automatic (No Action Needed)
1. Workflow runs on 1st of every month
2. Downloads fresh data from RMS2
3. Commits files to `data/` folder
4. Team can generate reports anytime

### Manual Download (On-Demand)
1. Go to **Actions** tab
2. Click **Download RMS2 Data**
3. Click **Run workflow**
4. Files downloaded in ~2-3 minutes

### Generate Reports
1. Open Streamlit app
2. Login: `admin` / `koenig2024`
3. Select **"🤖 Use Auto-Downloaded Data"**
4. Click **"Generate Client Growth Report"**
5. Download Excel file

### Manual Upload (Backup)
1. Select **"📥 Manual Upload"** mode
2. Upload RCB_24months.xlsx
3. Upload RCB_12months.xlsx
4. Generate report

---

## 🔧 Technical Details

### GitHub Actions Workflow

**Trigger:**
```yaml
schedule:
  - cron: '0 6 1 * *'  # Monthly on 1st at 6 AM UTC
workflow_dispatch:       # Manual trigger
```

**Key Steps:**
1. Install Playwright + Chromium
2. Run `download_rms2_data.py`
3. Verify files exist and have valid size
4. Commit and push to repository

**Environment Variables:**
- `RMS_USERNAME` (from secrets)
- `RMS_PASSWORD` (from secrets)
- `RMS_LOGIN_URL`: https://rms2.koenig-solutions.com
- `RCB_BASE_URL`: https://rms2.koenig-solutions.com/RCB

### Download Script Logic

**Two-Step Download Process:**
```python
# Step 1: Select period
page.select_option("select", "24")

# Step 2: Click Display button
page.click("button.ui.mini.button:has-text('Display')")
page.wait_for_timeout(3000)

# Step 3: Click Export button
with page.expect_download():
    page.click("button.ui.mini.button:has-text('Export to excel')")
```

**Why two steps?**
RMS2 requires clicking "Display" first to load the data, then "Export" to trigger the download.

### Streamlit App Features

**Mode Detection:**
```python
auto_files_exist = (
    Path('data/RCB_24months.xlsx').exists() and 
    Path('data/RCB_12months.xlsx').exists()
)
```

**Data Freshness:**
```python
last_update = datetime.fromtimestamp(
    file_path.stat().st_mtime
)
```

---

## 🛠️ Troubleshooting

### Workflow Not Running
- ✅ Check file path: `.github/workflows/download-rms2-data.yml`
- ✅ Verify GitHub Actions enabled in Settings
- ✅ Try manual trigger first

### Login Fails
- ✅ Verify secrets: RMS_USERNAME, RMS_PASSWORD
- ✅ Check RMS2 website is accessible
- ✅ Review `login_error.png` in failed run artifacts

### Download Timeout
- ✅ Verify two-step process implemented correctly
- ✅ Check button selectors in workflow logs
- ✅ Review `download_*_error.png` screenshots

### Git Push Fails
- ✅ Enable write permissions in Settings → Actions
- ✅ Ensure "Allow GitHub Actions to create PRs" is checked

### Files Not in Data Folder
- ✅ Check Actions tab for workflow status
- ✅ Review workflow logs for errors
- ✅ Verify files committed in latest commit

---

## 📊 Dependencies

### Python Packages
```
streamlit          # Dashboard framework
pandas             # Data processing
openpyxl           # Excel file handling
python-dotenv      # Environment variables
playwright         # Browser automation
```

### System Requirements
- Python 3.11+
- Chromium browser (auto-installed by Playwright)

---

## 🔒 Security

### Credentials
- ✅ Stored as encrypted GitHub secrets
- ✅ Never visible in logs or code
- ✅ Only accessible during workflow execution

### Access Control
- ✅ Streamlit login required: admin / koenig2024
- ✅ Repository access controls apply
- ✅ GitHub Actions audit logs available

---

## 📅 Maintenance

### Monthly Tasks
- ✅ **Automatic:** Workflow downloads data (no action needed)

### Periodic Tasks
- 🔄 **Quarterly:** Review workflow logs for any issues
- 🔄 **Yearly:** Rotate RMS2 credentials (update secrets)

### Monitoring
- Check **Actions** tab for workflow status
- Review **data/** folder for latest files
- Monitor Streamlit app for any errors

---

## 🎯 Benefits Over Previous Approach

| Aspect | Old (Streamlit Auto-Download) | New (GitHub Actions) |
|--------|------------------------------|---------------------|
| **Reliability** | ❌ Timeout errors | ✅ Robust runners |
| **Browser Support** | ❌ ChromeDriver issues | ✅ Full Playwright support |
| **Debugging** | ❌ Hard to debug | ✅ Detailed logs |
| **Automation** | ❌ On-demand only | ✅ Scheduled + on-demand |
| **Maintenance** | ❌ Complex code | ✅ Simple, clean |
| **Resources** | ❌ Browser in cloud | ✅ Efficient |
| **Two-step Download** | ❌ Not implemented | ✅ Correctly implemented |

---

## 📝 Version History

### v2.0 (Current) - GitHub Actions Integration
- ✅ Automated monthly downloads via GitHub Actions
- ✅ Two-step download process (Display → Export)
- ✅ Dual mode: Auto-downloaded + Manual upload
- ✅ Data freshness indicators
- ✅ Improved reliability and maintainability

### v1.2 - Streamlit Cloud Attempts
- ⚠️ Browser automation in Streamlit Cloud
- ⚠️ Multiple timeout and selector issues
- ⚠️ Complex deployment requirements

### v1.1 - Koenig Branding
- ✅ Blue theme (#0099cc)
- ✅ Logo integration
- ✅ Clean UI polish

### v1.0 - Initial Release
- ✅ Fixed High Growth filter bug
- ✅ USD conversion and formatting
- ✅ 4-sheet Excel output

---

## 🤝 Support

**Need help?**
1. Check **QUICK_START.md** for setup guidance
2. Review **GITHUB_ACTIONS_SETUP.md** for detailed docs
3. Check **Actions** tab for workflow logs
4. Review error screenshots in failed run artifacts

---

## 📄 License

Internal use - Koenig Solutions

---

## ✨ Credits

**Developed for Koenig Solutions**

**Architecture:**
- GitHub Actions for automation
- Playwright for browser control
- Streamlit for dashboard UI
- Pandas for data processing

---

**Happy Reporting! 📊**
