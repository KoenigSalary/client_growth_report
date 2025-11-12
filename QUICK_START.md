🚀 Quick Start Guide - GitHub Actions + Streamlit
What Changed?
Before: Streamlit app tried to download files using browser automation (complex, unreliable on cloud)

Now: GitHub Actions downloads files automatically every month, Streamlit just generates reports (simple, reliable)

✅ Benefits
Reliable: GitHub Actions has full browser support (no more timeout errors)
Automatic: Downloads run monthly on 1st at 6 AM UTC
Simple: Streamlit only does what it's good at (UI + report generation)
Flexible: Can trigger manual downloads anytime
Transparent: Full logs of every download attempt
📦 What You Need to Upload
Upload these files to your GitHub repository:

your-repo/
├── .github/
│   └── workflows/
│       └── download-rms2-data.yml    ← NEW: Auto-download workflow
├── assets/
│   └── koenig_logo.png
├── streamlit_app.py                  ← UPDATED: Uses auto-downloaded files
├── process_report.py
├── download_rms2_data.py             ← UPDATED: Two-step download process
├── requirements.txt
└── README.md
⚡ 3-Step Setup
Step 1: Upload Files to GitHub
Drag and drop all files to your repository.

Step 2: Add Secrets
Go to Settings → Secrets and variables → Actions
Add these secrets:
RMS_USERNAME = admin
RMS_PASSWORD = koenig2024
Step 3: Enable Workflow Permissions
Go to Settings → Actions → General
Under "Workflow permissions":
✅ Select "Read and write permissions"
✅ Check "Allow GitHub Actions to create and approve pull requests"
Click Save
Done! 🎉

🎮 How to Use
Automatic Downloads (No Action Needed)
Runs on 1st of every month at 6 AM UTC
Downloads files automatically
Commits to data/ folder
No manual intervention required
Manual Downloads (On-Demand)
When you need fresh data immediately:

Go to Actions tab
Click Download RMS2 Data
Click Run workflow button
Wait ~2-3 minutes
Files appear in data/ folder
Generate Reports in Streamlit
Open your Streamlit app
Login with: admin / koenig2024
App shows: "🤖 Use Auto-Downloaded Data" mode
Click "Generate Client Growth Report"
Download Excel file
Manual upload still works as backup!

📊 What the Workflow Does
Copy
🔍 Check if It's Working
After First Run:
Go to Actions tab → Should see green checkmark ✅
Go to Code tab → Open data/ folder
Should see:
RCB_24months.xlsx
RCB_12months.xlsx
In Streamlit App:
Mode selector shows: "🤖 Use Auto-Downloaded Data"
Shows last update timestamp
Shows file sizes
🛠️ Troubleshooting
"Workflow not found"
→ Check file is at: .github/workflows/download-rms2-data.yml

"Permission denied" on git push
→ Enable write permissions in Settings → Actions → General

"Login failed"
→ Check secrets: RMS_USERNAME and RMS_PASSWORD are set correctly

Files not appearing in data/ folder
→ Check Actions tab for error logs

Need detailed help?
→ See GITHUB_ACTIONS_SETUP.md for complete guide

📅 Schedule
Event	Time	Action
Monthly	1st at 6 AM UTC	Auto-download files
Anytime	Manual trigger	On-demand download
After download	Automatic	Files committed to repo
When you visit	Anytime	Generate reports
🎯 Comparison
Old Approach (Streamlit Cloud Auto-Download)
❌ Complex browser automation in cloud
❌ Timeout errors
❌ ChromeDriver issues
❌ Button selector problems
❌ Hard to debug
❌ Resource-intensive

New Approach (GitHub Actions + Streamlit)
✅ Browser automation in GitHub Actions (reliable)
✅ No timeout issues (robust Ubuntu runners)
✅ Full Playwright support
✅ Two-step download process implemented
✅ Easy to debug (detailed logs)
✅ Efficient resource usage
✅ Scheduled automation
✅ Manual trigger option

💡 Why This Is Better
Separation of Concerns

GitHub Actions: Downloads data (what it's built for)
Streamlit: Generates reports (what it's good at)
Reliability

GitHub Actions has full browser support
No cloud deployment issues
Detailed logs for debugging
Automation

Set it and forget it
Team always has fresh data
No manual downloads needed
Flexibility

Scheduled automatic downloads
Manual on-demand downloads
Manual upload as backup
📝 Files Explained
.github/workflows/download-rms2-data.yml
GitHub Actions workflow configuration. Defines:

When to run (schedule + manual trigger)
What to do (install, download, commit)
Environment variables and secrets
download_rms2_data.py
Python script that:

Logs into RMS2 using Playwright
Implements two-step download (Display → Export)
Downloads both 24M and 12M files
Saves to data/ folder
streamlit_app.py
Streamlit dashboard that:

Detects auto-downloaded files
Shows "Use Auto-Downloaded Data" mode
Shows last update timestamp
Still supports manual upload
Generates reports with Koenig branding
🎓 Learn More
GitHub Actions: Full guide in GITHUB_ACTIONS_SETUP.md
Workflow logs: Actions tab in your repository
Cron schedules: crontab.guru
✨ You're Ready!
Just upload the files, add secrets, enable permissions, and you're done!

The system will:

✅ Download files automatically every month
✅ Make them available to Streamlit
✅ Let your team generate reports anytime
✅ Keep working reliably without manual intervention
Happy reporting! 📊
