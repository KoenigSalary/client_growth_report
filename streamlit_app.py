"""
Client Growth Report - Streamlit Dashboard
Simple version with Manual Upload only (no Auto Download confusion)
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
    # Show login form
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
    
    st.stop()  # Stop execution here if not authenticated

# ===== MAIN APPLICATION (Only shown if authenticated) =====

# Sidebar
with st.sidebar:
    # Use local logo file
    logo_path = "assets/koenig_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        # Fallback to URL if local file not found
        st.image("https://page.gensparksite.com/v1/base64_upload/9059197631dfa630291fc03acffc1eb4", width=200)
    
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

# Main content area - Manual Upload Only
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
if st.button("📊 Generate Client Growth Report", key='generate', disabled=not (file_24m and file_12m)):
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
            
            # Complete
            progress_bar.progress(100)
            status_text.text("✅ Report generated successfully!")
            
            st.session_state.report_generated = True
            st.session_state.report_path = output_file
            st.session_state.report_stats = result
            
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error generating report: {str(e)}")
            import traceback
            with st.expander("Show error details"):
                st.code(traceback.format_exc())

if not (file_24m and file_12m):
    st.warning("⚠️ Please upload both files to generate the report.")

# Show results if report was generated
if st.session_state.report_generated and st.session_state.report_path:
    st.markdown("---")
    st.header("✅ Report Generated Successfully!")
    
    stats = st.session_state.report_stats
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Clients", f"{stats['total_clients']:,}")
    with col2:
        st.metric("High Growth Clients", f"{stats['high_growth_clients']}")
    with col3:
        st.metric("Exceptions", f"{stats['exceptions']}")
    with col4:
        file_size = st.session_state.report_path.stat().st_size / 1024
        st.metric("File Size", f"{file_size:.1f} KB")
    
    st.markdown("### 📥 Download Report")
    
    # Download button
    with open(st.session_state.report_path, 'rb') as f:
        st.download_button(
            label="⬇️ Download Excel Report",
            data=f,
            file_name=st.session_state.report_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    st.markdown("""
    <div class="success-box">
    <strong>Report Contents:</strong><br>
    ✓ <strong>Sheet 1:</strong> Growth Comparison (All clients)<br>
    ✓ <strong>Sheet 2:</strong> High Growth 5K-50K USD (Threshold-crossing clients)<br>
    ✓ <strong>Sheet 3:</strong> Summary (Statistics and biggest mover)<br>
    ✓ <strong>Sheet 4:</strong> Exceptions (Data quality issues)
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Generate Another Report"):
        st.session_state.report_generated = False
        st.session_state.report_path = None
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>Powered by <strong>Koenig Solutions</strong> | Client Growth Report System</p>
    <p style='font-size: 0.8em;'>High Growth Filter: Previous ≤ $5K AND Current ≥ $50K</p>
</div>
""", unsafe_allow_html=True)
