# RMS2 Client Growth Report - Streamlit Dashboard

A simple, elegant dashboard for generating client growth reports from RMS2 data.

## 🌟 Features

- **📥 Manual File Upload** - Upload Excel files directly
- **🤖 Auto Download** - Automatically fetch data from RMS2 (requires ChromeDriver)
- **📊 Comprehensive Reports** - 4-sheet Excel with Growth Comparison, High Growth, Summary, Exceptions
- **🎨 Koenig Branding** - Professional interface with company colors
- **✅ Fixed High Growth Filter** - Correctly identifies clients: Previous ≤ $5K, Current ≥ $50K

## 🚀 Quick Start

### Local Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd rms2_dashboard
```

2. **Install dependencies**
```bash
pip install -r requirements_streamlit.txt
```

3. **Run the dashboard**
```bash
streamlit run streamlit_app.py
```

4. **Open browser**
```
http://localhost:8501
```

### Using the Dashboard

#### Option 1: Manual Upload (Recommended)
1. Download `RCB_24months.xlsx` and `RCB_12months.xlsx` from RMS2
2. Upload both files in the dashboard
3. Click "Generate Client Growth Report"
4. Download your Excel report

#### Option 2: Auto Download (Advanced)
1. Install ChromeDriver: `brew install chromedriver`
2. Create `.env` file with RMS2 credentials:
```
RMS_USERNAME=your.email@koenig-solutions.com
RMS_PASSWORD=your_password
RMS_LOGIN_URL=https://rms2.koenig-solutions.com
RCB_BASE_URL=https://rms2.koenig-solutions.com/RCB
INR_TO_USD_RATE=84
```
3. Click "Download Data & Generate Report"

## 📦 Dependencies

- streamlit
- pandas
- openpyxl
- python-dotenv (for auto-download)
- selenium (for auto-download)

## 🌐 Deploy to Streamlit Cloud

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Deploy on Streamlit Cloud**
- Go to https://share.streamlit.io/
- Connect your GitHub repository
- Select `streamlit_app.py` as main file
- Add secrets (for auto-download):
  - Go to Settings > Secrets
  - Add your RMS2 credentials

3. **Access your app**
- Your app will be live at: `https://your-app-name.streamlit.app`

## 📊 Report Structure

### Sheet 1: Growth Comparison
- All clients with clean data
- Sorted by Growth_USD descending
- Includes Previous/Current revenue in USD and INR

### Sheet 2: High Growth 5K-50K USD
- Clients who crossed $50K threshold
- Filter: Previous_12M_USD ≤ $5,000 AND Current_12M_USD ≥ $50,000
- Sorted by Growth_% descending

### Sheet 3: Summary
- Total clients analyzed
- High growth count
- Exceptions count
- Biggest mover statistics

### Sheet 4: Exceptions
- Clients with negative revenue values
- Data quality issues identified

## 🔧 Configuration

### Currency Conversion
Default: 1 USD = 84 INR

To change, update `.env`:
```
INR_TO_USD_RATE=85
```

### High Growth Threshold
Current filter: Previous ≤ $5K, Current ≥ $50K

To modify, edit `process_report.py` lines 104-107.

## 🐛 Troubleshooting

**File upload not working?**
- Check file format is .xlsx
- File size should be < 200MB

**Auto-download fails?**
- Ensure ChromeDriver is installed
- Verify credentials in `.env`
- Try manual upload as fallback

**Report generation error?**
- Check data files have required columns (CorporateID, TotalNR1, etc.)
- Verify Excel files are not corrupted

## 📝 License

Proprietary - Koenig Solutions

## 👥 Support

For issues or questions, contact IT Support.
