GitHub Actions Setup Guide
🎯 Overview
This guide explains how to set up automated monthly data downloads from RMS2 using GitHub Actions. The workflow will:

✅ Run automatically on the 1st of every month at 6 AM UTC
✅ Download RCB_24months.xlsx and RCB_12months.xlsx from RMS2
✅ Commit files to your repository
✅ Make data available for Streamlit app
✅ Can be triggered manually anytime
📁 File Structure
After setup, your repository should look like this:

your-repo/
├── .github/
│   └── workflows/
│       └── download-rms2-data.yml    # ← GitHub Actions workflow
├── assets/
│   └── koenig_logo.png
├── data/                              # ← Auto-downloaded files go here
│   ├── RCB_24months.xlsx             # ← Downloaded by workflow
│   └── RCB_12months.xlsx             # ← Downloaded by workflow
├── streamlit_app.py
├── process_report.py
├── download_rms2_data.py
├── requirements.txt
└── README.md
🔧 Setup Steps
Step 1: Upload Files to GitHub
Upload these files to your GitHub repository:

.github/workflows/download-rms2-data.yml - The workflow configuration
download_rms2_data.py - Download script with two-step process (Display → Export)
streamlit_app.py - Updated app that uses auto-downloaded files
process_report.py - Report generation logic
requirements.txt - Python dependencies
assets/koenig_logo.png - Logo file
Step 2: Configure GitHub Secrets
The workflow needs your RMS2 credentials to download files.

Add secrets to your repository:

Go to your GitHub repository

Click Settings → Secrets and variables → Actions

Click New repository secret

Add these two secrets:

Name	Value
RMS_USERNAME	admin
RMS_PASSWORD	koenig2024
Security Note: Secrets are encrypted and never visible in logs or workflow output.

Step 3: Enable GitHub Actions
Go to Settings → Actions → General
Under "Actions permissions", select Allow all actions and reusable workflows
Under "Workflow permissions", select:
✅ Read and write permissions
✅ Allow GitHub Actions to create and approve pull requests
Click Save
Why this is needed: The workflow needs write permissions to commit downloaded files back to your repository.

🚀 Usage
Automatic Scheduled Downloads
The workflow runs automatically on the 1st of every month at 6 AM UTC.

No action required from you! Files will be downloaded and committed automatically.

Manual Trigger (On-Demand Download)
You can also trigger downloads manually anytime:

Go to Actions tab in your GitHub repository
Click on Download RMS2 Data workflow
Click Run workflow button
Click Run workflow (green button)
The workflow will start immediately and download fresh data.

📊 How It Works
Workflow Steps
1. Checkout repository
2. Set up Python 3.11
3. Install Playwright + dependencies
4. Install Chromium browser
5. Run download_rms2_data.py
   ├── Login to RMS2
   ├── Select 24 months period
   ├── Click "Display" button
   ├── Click "Export to excel" button
   ├── Download RCB_24months.xlsx
   ├── Select 12 months period
   ├── Click "Display" button
   ├── Click "Export to excel" button
   └── Download RCB_12months.xlsx
6. Verify files exist and have valid size
7. Commit files to data/ folder
8. Push to repository
Two-Step Download Process
The script implements RMS2's required workflow:

Copy# Step 1: Select period
page.select_option("select", "24")

# Step 2: Click "Display" button
page.click("button.ui.mini.button:has-text('Display')")
wait 3 seconds

# Step 3: Click "Export to excel" button
page.click("button.ui.mini.button:has-text('Export to excel')")
Download starts
🔍 Monitoring Workflow Runs
View Workflow Status
Go to Actions tab in your repository
Click on any workflow run to see details
Green checkmark ✅ = Success
Red X ❌ = Failed
View Logs
Click on a workflow run
Click on download-data job
Expand any step to see detailed logs
Example log output:

[2024-12-01 06:00:15] Setting up browser...
[2024-12-01 06:00:18] Browser ready
[2024-12-01 06:00:18] Logging in to RMS2...
[2024-12-01 06:00:22] Login successful
[2024-12-01 06:00:22] Downloading 24-month data...
[2024-12-01 06:00:25] Selecting 24 months period...
[2024-12-01 06:00:27] Clicking 'Display' button...
[2024-12-01 06:00:30] Clicking 'Export to excel' button...
[2024-12-01 06:00:35] ✓ Downloaded: RCB_24months.xlsx (2,345,678 bytes)
[2024-12-01 06:00:35] Downloading 12-month data...
[2024-12-01 06:00:40] ✓ Downloaded: RCB_12months.xlsx (1,234,567 bytes)
[2024-12-01 06:00:40] ✓ All files downloaded successfully!
Check Downloaded Files
After successful run:

Go to Code tab
Open data/ folder
You should see:
RCB_24months.xlsx
RCB_12months.xlsx
🎨 Streamlit App Integration
How Streamlit Uses Auto-Downloaded Files
The updated Streamlit app automatically detects files in data/ folder:

Mode Selection:

If files exist → Shows "🤖 Use Auto-Downloaded Data" option
If files missing → Shows only "📥 Manual Upload" option
Data Freshness:

Shows last update timestamp
Displays file sizes
Indicates when next auto-download will occur
Backup Option:

Manual upload still available
Use if you need to override auto-downloaded files
🛠️ Troubleshooting
Issue: Workflow Not Running
Check:

GitHub Actions enabled in Settings
Workflow file in correct path: .github/workflows/download-rms2-data.yml
No syntax errors in YAML file
Solution: Try manual trigger first to test workflow.

Issue: Download Fails - Login Error
Symptoms:

Login failed: Timeout waiting for button
Check:

Secrets configured correctly (RMS_USERNAME, RMS_PASSWORD)
RMS2 website accessible
Credentials still valid
Solution:

Verify secrets in Settings → Secrets
Check login_error.png in failed run artifacts
Issue: Download Fails - Timeout
Symptoms:

Download 24M failed: Timeout 60000ms exceeded
Possible causes:

"Display" button not clicked (missing step)
Wrong button selector
Page takes longer to load
Solution:

Check download script has both button clicks
Review error screenshot in artifacts
Increase timeout if needed
Issue: Files Not Committed
Symptoms: Workflow succeeds but files not in repository

Check:

Workflow has write permissions (Settings → Actions → Workflow permissions)
Check commit step logs for errors
Solution:

Copy# Ensure these permissions in workflow file
permissions:
  contents: write
Issue: Git Push Fails
Symptoms:

remote: Permission to user/repo.git denied
Solution:

Go to Settings → Actions → General
Enable "Read and write permissions"
Enable "Allow GitHub Actions to create and approve pull requests"
Save and re-run workflow
🔒 Security Notes
Credentials Storage
✅ Stored as encrypted secrets
✅ Never visible in logs
✅ Never visible in code
✅ Only accessible during workflow execution
Best Practices
Don't hardcode credentials in workflow file
Use repository secrets for sensitive data
Review workflow logs to ensure no credential leakage
Rotate credentials periodically (update secrets)
📅 Schedule Customization
Change Schedule
Edit .github/workflows/download-rms2-data.yml:

Copyschedule:
  - cron: '0 6 1 * *'  # Current: 1st of month at 6 AM UTC
Common schedules:

Schedule	Cron Expression	Description
Daily at 6 AM	0 6 * * *	Every day
Weekly (Monday)	0 6 * * 1	Every Monday
Monthly (1st)	0 6 1 * *	1st of each month ✅
Bi-weekly	0 6 1,15 * *	1st and 15th
Cron format: minute hour day month weekday

Tool: Use crontab.guru to build custom schedules

📧 Email Notifications
Get Notified on Failures
GitHub sends email notifications by default for workflow failures.

Configure:

Go to Settings → Notifications
Under "Actions", enable:
✅ Send notifications for failed workflows on repositories you watch
🎯 Next Steps
✅ Upload all files to GitHub
✅ Configure secrets (RMS_USERNAME, RMS_PASSWORD)
✅ Enable workflow permissions
✅ Test with manual trigger
✅ Wait for first scheduled run (1st of next month)
✅ Deploy Streamlit app pointing to same repository
Streamlit will automatically use files from data/ folder!

📝 Summary
Component	Purpose	Status
GitHub Actions	Automated downloads	✅ Monthly schedule
Playwright	Browser automation	✅ Two-step process
GitHub Secrets	Secure credentials	✅ Encrypted
Data folder	File storage	✅ Auto-committed
Streamlit app	Report generation	✅ Auto-detects files
Manual upload	Backup option	✅ Always available
🆘 Need Help?
Check these resources:

Workflow logs in Actions tab
Error screenshots in failed run artifacts
GitHub Actions documentation
This setup guide
Common commands:

Copy# Test download script locally
python download_rms2_data.py

# Check if files downloaded
ls -lh data/

# View workflow syntax
cat .github/workflows/download-rms2-data.yml
You're all set! 🎉

The workflow will run automatically every month, and your Streamlit app will always have fresh data without any manual intervention.
