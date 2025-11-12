# 🚀 GitHub + Streamlit Deployment Guide

Complete guide to deploy your RMS2 Dashboard to GitHub and Streamlit Cloud.

---

## 📦 Step 1: Prepare Repository

### Files to Include (Already created):
- ✅ `streamlit_app.py` - Main Streamlit dashboard
- ✅ `process_report.py` - Report generation logic
- ✅ `download_rms2_data.py` - Auto-download (optional)
- ✅ `requirements_streamlit.txt` - Dependencies
- ✅ `.gitignore` - Excludes sensitive files
- ✅ `README_STREAMLIT.md` - Documentation

### Files to EXCLUDE (in .gitignore):
- ❌ `.env` - Contains passwords
- ❌ `data/*.xlsx` - Data files
- ❌ `generated_reports/` - Generated reports
- ❌ `*.log` - Log files

---

## 🔧 Step 2: Initialize Git Repository

```bash
cd /home/user/rms2_dashboard

# Initialize git
git init

# Add all files (gitignore will exclude sensitive data)
git add .

# Commit
git commit -m "Initial commit: RMS2 Client Growth Report Dashboard"
```

---

## 🌐 Step 3: Push to GitHub

### Option A: Create new repository on GitHub

1. **Go to GitHub**: https://github.com/new
2. **Create repository**:
   - Name: `rms2-dashboard`
   - Description: `RMS2 Client Growth Report Generator`
   - Visibility: **Private** (recommended)
   - Don't initialize with README

3. **Push your code**:
```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/rms2-dashboard.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Option B: Using GitHub CLI

```bash
# Install GitHub CLI (if not installed)
brew install gh  # macOS
# OR
# Download from: https://cli.github.com/

# Login to GitHub
gh auth login

# Create repo and push
gh repo create rms2-dashboard --private --source=. --remote=origin --push
```

---

## ☁️ Step 4: Deploy to Streamlit Cloud

### 4.1 Sign up for Streamlit Cloud

1. Go to: https://share.streamlit.io/
2. Click "Sign up" and connect your GitHub account
3. Authorize Streamlit to access your repositories

### 4.2 Deploy Your App

1. **Click "New app"**

2. **Configure deployment**:
   - Repository: `YOUR_USERNAME/rms2-dashboard`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: Choose your custom name (e.g., `rms2-report`)

3. **Click "Deploy!"**

### 4.3 Add Secrets (for auto-download feature)

If you want auto-download to work:

1. Go to your app settings
2. Click "Secrets" (⚙️ icon > Secrets)
3. Add your credentials:

```toml
RMS_USERNAME = "monika.chopra@koenig-solutions.com"
RMS_PASSWORD = "your_actual_password"
RMS_LOGIN_URL = "https://rms2.koenig-solutions.com"
RCB_BASE_URL = "https://rms2.koenig-solutions.com/RCB"
INR_TO_USD_RATE = "84"
```

4. Click "Save"

---

## 🎉 Step 5: Access Your Dashboard

Your app will be live at:
```
https://YOUR_APP_NAME.streamlit.app
```

For example:
```
https://rms2-report.streamlit.app
```

---

## 📱 Using the Deployed Dashboard

### Manual Upload Mode (Always Works):
1. Open your Streamlit app URL
2. Select "Manual Upload" in sidebar
3. Upload RCB_24months.xlsx and RCB_12months.xlsx
4. Click "Generate Report"
5. Download Excel file

### Auto Download Mode (If secrets configured):
1. Select "Auto Download" in sidebar
2. Click "Download Data & Generate Report"
3. Wait 3-4 minutes
4. Download Excel file

---

## 🔄 Updating Your App

Whenever you make changes:

```bash
# Make your changes to the code
# ... edit files ...

# Commit and push
git add .
git commit -m "Description of changes"
git push origin main

# Streamlit Cloud will automatically redeploy!
```

---

## 🔒 Security Best Practices

### ✅ DO:
- Keep repository **private**
- Store credentials in Streamlit Secrets (not in code)
- Use `.gitignore` to exclude sensitive files
- Regularly update dependencies

### ❌ DON'T:
- Commit `.env` file to GitHub
- Hard-code passwords in Python files
- Make repository public with credentials
- Share Streamlit app URL publicly

---

## 🐛 Troubleshooting

### App won't start?
**Check logs:**
- In Streamlit Cloud, click "Manage app" > "Logs"
- Look for error messages

**Common issues:**
- Missing dependencies: Update `requirements_streamlit.txt`
- Import errors: Check file paths
- Secrets not set: Add in app settings

### Auto-download not working?
**Possible causes:**
- ChromeDriver not available on Streamlit Cloud (expected)
- Use **Manual Upload mode** instead
- Auto-download works better on local machine

### File upload fails?
**Solutions:**
- Check file size < 200MB
- Ensure file is .xlsx format
- Try refreshing the page

---

## 💰 Streamlit Cloud Pricing

**Free Tier Includes:**
- ✅ 1 private app
- ✅ Unlimited public apps
- ✅ 1 GB memory
- ✅ Community support

**Paid Tiers:**
- More private apps
- Increased resources
- Priority support

**For most use cases, FREE tier is sufficient!**

---

## 📊 Monitoring Usage

**View app analytics:**
1. Go to https://share.streamlit.io/
2. Click on your app
3. View "Analytics" tab

**Metrics available:**
- Number of visitors
- Page views
- App load time
- Error rates

---

## 🎯 Next Steps

1. ✅ **Test locally**: `streamlit run streamlit_app.py`
2. ✅ **Push to GitHub**: Follow Step 2-3 above
3. ✅ **Deploy to Streamlit**: Follow Step 4 above
4. ✅ **Share URL**: With your team
5. ✅ **Bookmark**: For easy access

---

## 📞 Support

**Streamlit Documentation:**
- https://docs.streamlit.io/

**GitHub Help:**
- https://docs.github.com/

**Deployment Issues:**
- Check Streamlit Community: https://discuss.streamlit.io/

---

## ✨ Summary

**Local Testing:**
```bash
streamlit run streamlit_app.py
# Open: http://localhost:8501
```

**Deploy to Cloud:**
```bash
git push origin main
# App auto-deploys on Streamlit Cloud
```

**Access Anywhere:**
```
https://your-app-name.streamlit.app
```

**It's that simple!** 🚀
