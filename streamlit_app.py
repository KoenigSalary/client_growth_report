"""
Client Growth Report - Streamlit Dashboard WITH DIAGNOSTICS
This version shows detailed error information to help debug issues
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import time
import traceback

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
    .error-box {
        padding: 1rem;
        background-color: #ffebee;
        border-left: 4px solid #f44336;
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

st.markdown("---")

# Login credentials
LOGIN_USERNAME = "monika.chopra"
LOGIN_PASSWORD = "manyamey"

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ===== LOGIN PAGE =====
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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
    logo_path = "assets/koenig_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    
    st.markdown("### Options")
    
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
        st.rerun()

    # Add after the "About" section in sidebar
    st.markdown("---")
    st.markdown("### 🤖 Auto-Download Control")

    # Show data freshness if files exist
    if auto_files_exist:
        last_update_24m = datetime.fromtimestamp(Path('data/RCB_24months.xlsx').stat().st_mtime)
        last_update_12m = datetime.fromtimestamp(Path('data/RCB_12months.xlsx').stat().st_mtime)
        last_update = max(last_update_24m, last_update_12m)
    
        hours_ago = (datetime.now() - last_update).total_seconds() / 3600
    
        if hours_ago < 24:
            st.success(f"✅ Data: {hours_ago:.1f}h ago")
        elif hours_ago < 168:
            st.info(f"📊 Data: {hours_ago/24:.1f}d ago")
        else:
            st.warning(f"⚠️ Data: {hours_ago/24:.1f}d old")

    # Auto-run trigger button
    if st.button("🔄 Run Auto-Download Now", key="trigger_auto_download"):
        st.info("""
        **📋 To trigger data download:**
    
        1. Click the button below to open GitHub Actions
        2. Click "Run workflow" (green button)
        3. Confirm by clicking "Run workflow" again
        4. Wait 2-3 minutes for completion
        5. Refresh this page to use new data
        """)
    
        st.link_button(
            "🚀 Open GitHub Actions",
            "https://github.com/KoenigSalary/client_growth_report/actions/workflows/download-rms2-data.yml",
            use_container_width=True
        )
    
        st.markdown("**Current workflow status:**")
        st.markdown("[View latest runs →](https://github.com/KoenigSalary/client_growth_report/actions)")

def show_dataframe_info(df, file_name):
    """Show diagnostic information about a dataframe"""
    st.write(f"**{file_name} Information:**")
    st.write(f"- Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    st.write(f"- Columns: {', '.join(df.columns.tolist())}")
    
    with st.expander(f"Show first 5 rows of {file_name}"):
        st.dataframe(df.head())

def generate_report_with_diagnostics(file_24m_path, file_12m_path, source="manual"):
    """Generate report with detailed diagnostics"""
    
    st.subheader("📊 Report Generation Progress")
    
    try:
        # Step 1: Read files
        st.write("**Step 1: Reading files...**")
        
        try:
            df_24m = pd.read_excel(file_24m_path)
            st.success(f"✅ Successfully read 24-month file")
            show_dataframe_info(df_24m, "24-Month Data")
        except Exception as e:
            st.error(f"❌ Error reading 24-month file: {str(e)}")
            st.code(traceback.format_exc())
            return False
        
        try:
            df_12m = pd.read_excel(file_12m_path)
            st.success(f"✅ Successfully read 12-month file")
            show_dataframe_info(df_12m, "12-Month Data")
        except Exception as e:
            st.error(f"❌ Error reading 12-month file: {str(e)}")
            st.code(traceback.format_exc())
            return False
        
        st.markdown("---")
        
        # Step 2: Check required columns
        st.write("**Step 2: Checking required columns...**")
        
        required_columns_24m = ['CorporateID', 'CorporateName', 'TotalNR1']
        required_columns_12m = ['CorporateID', 'TotalNR1']
        
        missing_24m = [col for col in required_columns_24m if col not in df_24m.columns]
        missing_12m = [col for col in required_columns_12m if col not in df_12m.columns]
        
        if missing_24m:
            st.error(f"❌ Missing columns in 24-month file: {', '.join(missing_24m)}")
            st.write("**Available columns:**", ', '.join(df_24m.columns.tolist()))
            return False
        else:
            st.success("✅ All required columns found in 24-month file")
        
        if missing_12m:
            st.error(f"❌ Missing columns in 12-month file: {', '.join(missing_12m)}")
            st.write("**Available columns:**", ', '.join(df_12m.columns.tolist()))
            return False
        else:
            st.success("✅ All required columns found in 12-month file")
        
        st.markdown("---")
        
        # Step 3: Process report
        st.write("**Step 3: Processing report...**")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("⚙️ Processing data and calculating growth...")
            progress_bar.progress(40)
            
            from process_report import process_growth_report
            
            status_text.text("📊 Generating Excel report...")
            progress_bar.progress(60)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = Path('generated_reports')
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f'Client_Growth_Report_{timestamp}.xlsx'
            
            result = process_growth_report(df_24m, df_12m, str(output_file))
            
            progress_bar.progress(100)
            status_text.text("✅ Report generated successfully!")
            
            st.markdown("---")
            
            # Display summary
            st.markdown(f"""
            <div class="success-box">
            <h3>✅ Report Generated Successfully!</h3>
            <p><strong>Summary:</strong></p>
            <ul>
                <li>Total clients analyzed: {result.get('total_clients', 'N/A')}</li>
                <li>High growth clients (≤$5K → ≥$50K): {result.get('high_growth_count', 'N/A')}</li>
                <li>Average growth: {result.get('avg_growth', 0):.1f}%</li>
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
                    key=f'download_{source}'
                )
            
            return True
            
        except Exception as e:
            st.error(f"❌ Error during report generation: {str(e)}")
            st.markdown("""
            <div class="error-box">
            <strong>🔍 Debug Information:</strong>
            </div>
            """, unsafe_allow_html=True)
            st.code(traceback.format_exc())
            return False
        
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        st.code(traceback.format_exc())
        return False


# Main content area
if option == "🤖 Use Auto-Downloaded Data":
    st.header("🤖 Auto-Downloaded Data")
    
    file_24m_path = Path('data/RCB_24months.xlsx')
    file_12m_path = Path('data/RCB_12months.xlsx')
    
    if file_24m_path.exists() and file_12m_path.exists():
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
        
        st.markdown("---")
        
        if st.button("📊 Generate Client Growth Report", key='generate_auto'):
            generate_report_with_diagnostics(file_24m_path, file_12m_path, "auto")
    else:
        st.warning("⚠️ Auto-downloaded data files not found. Please use Manual Upload mode.")

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
    
    if st.button("📊 Generate Client Growth Report", key='generate_manual', disabled=not (file_24m and file_12m)):
        # Save uploaded files temporarily
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        temp_24m = data_dir / 'temp_RCB_24months.xlsx'
        with open(temp_24m, 'wb') as f:
            f.write(file_24m.getbuffer())
        
        temp_12m = data_dir / 'temp_RCB_12months.xlsx'
        with open(temp_12m, 'wb') as f:
            f.write(file_12m.getbuffer())
        
        # Generate report with diagnostics
        generate_report_with_diagnostics(temp_24m, temp_12m, "manual")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <small>Client Growth Report Generator v2.0 (Diagnostic Mode) | © 2024 Koenig Solutions</small>
</div>
""", unsafe_allow_html=True)
