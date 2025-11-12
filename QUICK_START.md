# 🚀 Quick Start Guide - RMS2 Streamlit Dashboard

Get up and running in **2 minutes**!

---

## ⚡ Installation (3 Steps)

### Step 1: Extract Files
```bash
unzip rms2_streamlit_package.zip
cd rms2_streamlit_package
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Dashboard
```bash
streamlit run streamlit_app.py
```

**That's it!** Open http://localhost:8501 in your browser.

---

## 📥 Using the Dashboard

### **Manual Upload Mode** (Recommended - Always Works)

1. **Download data from RMS2**:
   - Go to: https://rms2.koenig-solutions.com/RCB
   - Login with your credentials
   - Export 24-month data → Save as `RCB_24months.xlsx`
   - Export 12-month data → Save as `RCB_12months.xlsx`

2. **Upload in dashboard**:
   - Open http://localhost:8501
   - Select "📥 Manual Upload" in sidebar
   - Upload both Excel files
   - Click "📊 Generate Client Growth Report"

3. **Download report**:
   - Wait 1-2 minutes
   - Click "⬇️ Download Excel Report"

**Done!** 🎉

---

## 🤖 Auto-Download Mode (Optional - Advanced)

If you want automatic data download:

### Requirements:
- Chrome browser installed
- ChromeDriver installed: `brew install chromedriver` (Mac)

### Setup:
1. Update `.env` file with your RMS2 password (replace XXXXXXXX)
2. In dashboard, select "🤖 Auto Download"
3. Click "Download Data & Generate Report"

---

## 📊 Report Output

Your Excel file contains **4 sheets**:

1. **Growth Comparison** - All clients with revenue growth
2. **High Growth 5K-50K USD** - Clients who crossed $50K threshold (15 clients)
3. **Summary** - Statistics and biggest mover
4. **Exceptions** - Data quality issues

---

## 🌐 Deploy to Cloud (Optional)

Want to access from anywhere?

1. **Push to GitHub**:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/rms2-dashboard.git
git push -u origin main
```

2. **Deploy on Streamlit Cloud**:
   - Go to: https://share.streamlit.io/
   - Connect your GitHub repo
   - Click "Deploy"

3. **Access anywhere**:
   - Your app URL: `https://your-app-name.streamlit.app`

See `GITHUB_DEPLOYMENT.md` for detailed instructions.

---

## 🐛 Troubleshooting

**Issue: "pip not found"**
```bash
# Install Python 3.12 first
brew install python@3.12  # macOS
```

**Issue: "streamlit: command not found"**
```bash
pip3 install streamlit
```

**Issue: "Can't upload files"**
- Check file format is `.xlsx`
- File size should be < 200MB
- Try refreshing the page

---

## 📁 Project Structure

```
rms2_streamlit_package/
├── streamlit_app.py          # Main dashboard (run this!)
├── process_report.py          # Report generation logic
├── download_rms2_data.py      # Auto-download (optional)
├── requirements.txt           # Dependencies
├── .env                       # RMS2 credentials
├── README.md                  # Full documentation
├── QUICK_START.md            # This file
└── GITHUB_DEPLOYMENT.md      # Cloud deployment guide
```

---

## ✅ Success Checklist

- [ ] Extracted zip file
- [ ] Installed dependencies
- [ ] Dashboard opens at http://localhost:8501
- [ ] Can see Koenig logo
- [ ] File upload widgets visible
- [ ] Can upload Excel files
- [ ] Report generates successfully
- [ ] Can download Excel report

---

## 🎯 Key Features

- ✅ **Simple file upload** - Built-in Streamlit widgets
- ✅ **No ChromeDriver needed** - For manual upload mode
- ✅ **Fixed High Growth filter** - Correct 15 clients
- ✅ **Koenig branding** - Professional interface
- ✅ **4-sheet Excel reports** - Comprehensive analysis
- ✅ **Deploy anywhere** - Local or Streamlit Cloud

---

## 📞 Need Help?

1. Check `README.md` for full documentation
2. See `GITHUB_DEPLOYMENT.md` for cloud deployment
3. Review `COMPLETION_SUMMARY.md` for technical details

---

## 🎉 You're Ready!

**Run this command:**
```bash
streamlit run streamlit_app.py
```

**Open browser:**
```
http://localhost:8501
```

**Upload files and generate your report!** 🚀

**Total time: 2 minutes** ⚡
