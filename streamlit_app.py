"""
Client Growth Report - Streamlit Dashboard
Simple, clean interface for generating growth reports
Supports both auto-downloaded files (from GitHub Actions) and manual upload
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Client Growth Report",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Koenig branding
st.markdown("""
<style>
    .main {
        background-color: #f5f7fa;
    }
    .stButton>button {
        background: linear-gradient(135deg, #0099cc 0%, #003d5c 100%);
        color: white;
        font-weight: 600;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 25px;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #007aa3 0%, #002d4c 100%);
    }
    h1 {
        color: #0099cc;
    }
    .success-box {
        padding: 1rem;
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .data-update-badge {
        background-color: #0099cc;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        display: inline-block;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header with Koenig branding
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 Client Growth Report")
    st.markdown("**Powered by Koenig Solutions**")
with col2:
    st.markdown("### ")
    st.markdown("### ")

st.markdown("---")

# Login credentials
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "koenig2024"

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'report_path' not in st.session_state:
    st.session_state.report_path = None

# ===== LOGIN PAGE =====
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Show Koenig logo
        logo_path = "assets/koenig_logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=300)
        
        st.markdown("### 🔐 Login Required")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("🔓 Login")
            
            if submit:
                if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.success("✅ Login successful! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please try again.")
        
        st.markdown("---")
    
    st.stop()

# ===== MAIN APPLICATION =====

# Sidebar
with st.sidebar:
    # Use local logo file
    logo_path = "assets/koenig_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        # Fallback to URL if local file not found
        st.image("https://page.gensparksite.com/v1/base64_upload/9059197631dfa630291fc03acffc1eb4", width=200)
    st.markdown("### Options")
    
    # Check if auto-downloaded files exist
    auto_files_exist = (Path('data/RCB_24months.xlsx').exists() and 
                       Path('data/RCB_12months.xlsx').exists())
    
    if auto_files_exist:
        options = ["🤖 Use Auto-Downloaded Data", "📥 Manual Upload"]
        default_option = 0
    else:
        options = ["📥 Manual Upload"]
        default_option = 0
    
    option = st.radio("Select Mode:", options, index=default_option)
    
    st.markdown("---")
    st.markdown("### About")
    st.info("""
    **High Growth Filter:**
    - Previous ≤ $5,000
    - Current ≥ $50,000
    
    **Report Sheets:**
    1. Growth Comparison
    2. High Growth 5K-50K
    3. Summary
    4. Exceptions
    """)
    
    st.markdown("---")
    if st.button("🚪 Logout", key="logout"):
        st.session_state.authenticated = False
        st.session_state.report_generated = False
        st.session_state.report_path = None
        st.rerun()

# Main content area
if option == "🤖 Use Auto-Downloaded Data":
    st.header("🤖 Auto-Downloaded Data")
    
    # Show data update info
    file_24m_path = Path('data/RCB_24months.xlsx')
    file_12m_path = Path('data/RCB_12months.xlsx')
    
    if file_24m_path.exists() and file_12m_path.exists():
        # Get last modified time
        last_update_24m = datetime.fromtimestamp(file_24m_path.stat().st_mtime)
        last_update_12m = datetime.fromtimestamp(file_12m_path.stat().st_mtime)
        last_update = max(last_update_24m, last_update_12m)
        
        st.markdown(f"""
        <div class="success-box">
        <strong>✅ Data files available</strong><br>
        <span class="data-update-badge">Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')}</span>
        <ul style="margin-top: 0.5rem;">
            <li>RCB_24months.xlsx ({file_24m_path.stat().st_size / 1024 / 1024:.1f} MB)</li>
            <li>RCB_12months.xlsx ({file_12m_path.stat().st_size / 1024 / 1024:.1f} MB)</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
        <strong>ℹ️ About Auto-Download:</strong><br>
        Data is automatically downloaded monthly via GitHub Actions on the 1st of each month at 6 AM UTC.
        You can also trigger manual downloads from the GitHub Actions tab in your repository.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Generate Report Button
        if st.button("📊 Generate Client Growth Report", key='generate_auto'):
            with st.spinner("Generating report... This may take 1-2 minutes..."):
                try:
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Step 1: Read files
                    status_text.text("📖 Reading data files...")
                    progress_bar.progress(20)
                    df_24m = pd.read_excel(file_24m_path)
                    df_12m = pd.read_excel(file_12m_path)
                    
                    # Step 2: Process data
                    status_text.text("⚙️ Processing data and calculating growth...")
                    progress_bar.progress(40)
                    
                    from process_report import process_growth_report
                    
                    # Step 3: Generate report
                    status_text.text("📊 Generating Excel report...")
                    progress_bar.progress(60)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_dir = Path('generated_reports')
                    output_dir.mkdir(exist_ok=True)
                    output_file = output_dir / f'Client_Growth_Report_{timestamp}.xlsx'
                    
                    result = process_growth_report(df_24m, df_12m, str(output_file))
                    
                    # Step 4: Complete
                    progress_bar.progress(100)
                    status_text.text("✅ Report generated successfully!")
                    
                    st.session_state.report_generated = True
                    st.session_state.report_path = str(output_file)
                    
                    st.markdown(f"""
                    <div class="success-box">
                    <h3>✅ Report Generated Successfully!</h3>
                    <p><strong>Summary:</strong></p>
                    <ul>
                        <li>Total clients analyzed: {result['total_clients']:,}</li>
                        <li>High growth clients (≤$5K → ≥$50K): {result['high_growth_count']}</li>
                        <li>Average growth: {result['avg_growth']:.1f}%</li>
                        <li>Report saved: <code>{output_file.name}</code></li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Download button
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            label="📥 Download Excel Report",
                            data=f,
                            file_name=output_file.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key='download_auto'
                        )
                    
                except Exception as e:
                    st.error(f"❌ Error generating report: {str(e)}")
                    st.exception(e)
    else:
        st.warning("⚠️ Auto-downloaded data files not found. Please use Manual Upload mode or wait for the next scheduled download.")

else:  # Manual Upload
    st.header("📥 Upload Data Files")
    
    st.markdown("""
    <div class="info-box">
    <strong>Instructions:</strong>
    <ol>
        <li>Download RCB_24months.xlsx and RCB_12months.xlsx from RMS2</li>
        <li>Upload both files below</li>
        <li>Click "Generate Report"</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("24-Month Data")
        file_24m = st.file_uploader(
            "Upload RCB_24months.xlsx",
            type=['xlsx'],
            key='file_24m'
        )
        if file_24m:
            st.success(f"✅ Uploaded: {file_24m.name} ({file_24m.size / 1024 / 1024:.1f} MB)")
    
    with col2:
        st.subheader("12-Month Data")
        file_12m = st.file_uploader(
            "Upload RCB_12months.xlsx",
            type=['xlsx'],
            key='file_12m'
        )
        if file_12m:
            st.success(f"✅ Uploaded: {file_12m.name} ({file_12m.size / 1024 / 1024:.1f} MB)")
    
    st.markdown("---")
    
    # Generate Report Button
    if st.button("📊 Generate Client Growth Report", key='generate_manual', disabled=not (file_24m and file_12m)):
        with st.spinner("Generating report... This may take 1-2 minutes..."):
            try:
                # Save uploaded files temporarily
                data_dir = Path('data')
                data_dir.mkdir(exist_ok=True)
                
                # Save 24-month file
                with open(data_dir / 'RCB_24months.xlsx', 'wb') as f:
                    f.write(file_24m.getbuffer())
                
                # Save 12-month file
                with open(data_dir / 'RCB_12months.xlsx', 'wb') as f:
                    f.write(file_12m.getbuffer())
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Read files
                status_text.text("📖 Reading data files...")
                progress_bar.progress(20)
                df_24m = pd.read_excel(data_dir / 'RCB_24months.xlsx')
                df_12m = pd.read_excel(data_dir / 'RCB_12months.xlsx')
                
                # Step 2: Process data
                status_text.text("⚙️ Processing data and calculating growth...")
                progress_bar.progress(40)
                
                from process_report import process_growth_report
                
                # Step 3: Generate report
                status_text.text("📊 Generating Excel report...")
                progress_bar.progress(60)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_dir = Path('generated_reports')
                output_dir.mkdir(exist_ok=True)
                output_file = output_dir / f'Client_Growth_Report_{timestamp}.xlsx'
                
                result = process_growth_report(df_24m, df_12m, str(output_file))
                
                # Step 4: Complete
                progress_bar.progress(100)
                status_text.text("✅ Report generated successfully!")
                
                st.session_state.report_generated = True
                st.session_state.report_path = str(output_file)
                
                st.markdown(f"""
                <div class="success-box">
                <h3>✅ Report Generated Successfully!</h3>
                <p><strong>Summary:</strong></p>
                <ul>
                    <li>Total clients analyzed: {result['total_clients']:,}</li>
                    <li>High growth clients (≤$5K → ≥$50K): {result['high_growth_count']}</li>
                    <li>Average growth: {result['avg_growth']:.1f}%</li>
                    <li>Report saved: <code>{output_file.name}</code></li>
                </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # Download button
                with open(output_file, 'rb') as f:
                    st.download_button(
                        label="📥 Download Excel Report",
                        data=f,
                        file_name=output_file.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key='download_manual'
                    )
                
            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
                st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <small>Client Growth Report Generator v2.0 | © 2024 Koenig Solutions</small>
</div>
""", unsafe_allow_html=True)
