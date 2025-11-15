"""
Client Growth Report - Streamlit Dashboard WITH FULL AUTOMATION
Complete one-click solution with GitHub API integration and email notifications
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import time
import traceback
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Page configuration
st.set_page_config(
    page_title="Client Growth Report",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Koenig branding
st.markdown("""

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
    .automation-progress {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }

""", unsafe_allow_html=True)

# GitHub API Functions
def trigger_github_workflow():
    """Trigger GitHub Actions workflow via API"""
    try:
        url = "https://api.github.com/repos/KoenigSalary/client_growth_report/actions/workflows/download-rms2-data.yml/dispatches"
        token = st.secrets.get("GITHUB_TOKEN", "")
        
        if not token:
            st.error("❌ GITHUB_TOKEN not configured in Streamlit secrets")
            return False
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        data = {"ref": "main"}
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        return response.status_code == 204
        
    except Exception as e:
        st.error(f"❌ Error triggering workflow: {str(e)}")
        return False

def check_workflow_status():
    """Check if workflow completed successfully"""
    try:
        url = "https://api.github.com/repos/KoenigSalary/client_growth_report/actions/runs"
        token = st.secrets.get("GITHUB_TOKEN", "")
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        response = requests.get(url, headers=headers, params={"per_page": 1}, timeout=30)
        
        if response.status_code == 200:
            runs = response.json().get("workflow_runs", [])
            if runs:
                latest_run = runs[0]
                return latest_run.get("status"), latest_run.get("conclusion"), latest_run.get("html_url")
        
        return None, None, None
        
    except Exception as e:
        st.warning(f"⚠️ Error checking workflow status: {str(e)}")
        return None, None, None

def send_email_report(report_file_path, recipient_emails):
    """Send email with report attachment"""
    try:
        sender_email = st.secrets.get("SMTP_EMAIL", "")
        sender_password = st.secrets.get("SMTP_PASSWORD", "")
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        
        if not sender_email or not sender_password:
            st.warning("⚠️ Email credentials not configured in Streamlit secrets")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipient_emails)
        msg['Subject'] = f"Client Growth Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        body = f"""
Hi Team,

Please find attached the Client Growth Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

Report Summary:
- Data Period: Previous 12M vs Current 12M
- Exchange Rate: 1 USD = 84 INR
- High Growth Filter: Previous ≤$5K, Current ≥$50K

The report includes:
1. Growth Comparison (all clients)
2. High Growth 5K-50K USD (filtered results)
3. Summary statistics
4. Exception handling details

Best regards,
Koenig Solutions Automated Report System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach Excel file
        with open(report_file_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {Path(report_file_path).name}')
        msg.attach(part)
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_emails, text)
        server.quit()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Email sending failed: {str(e)}")
        return False

# Login credentials
LOGIN_USERNAME = "monika.chopra"
LOGIN_PASSWORD = "manyamey"

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ===== LOGIN PAGE =====
if not st.session_state.authenticated:
    st.markdown("", unsafe_allow_html=True)
    
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

# Header with Koenig branding
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 Client Growth Report")
    st.markdown("**Powered by Koenig Solutions**")
with col2:
    st.markdown("### ")

st.markdown("---")

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
    st.markdown("### 🤖 Full Automation Control")
    
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
    
    # ONE-CLICK FULL AUTOMATION BUTTON
    if st.button("🚀 Run Full Automation", key="full_auto_trigger", use_container_width=True):
        progress_container = st.empty()
        status_container = st.empty()
        
        with progress_container.container():
            st.markdown('', unsafe_allow_html=True)
            st.markdown("### 🔄 Full Automation in Progress...")
            progress_bar = st.progress(0)
            st.markdown('', unsafe_allow_html=True)
            
            # Step 1: Trigger workflow
            status_container.info("📡 Step 1/5: Triggering GitHub Actions workflow...")
            progress_bar.progress(10)
            
            if trigger_github_workflow():
                status_container.success("✅ Workflow triggered successfully!")
                time.sleep(2)
                
                # Step 2: Wait for download
                status_container.info("⬇️ Step 2/5: Downloading data from RMS2... (2-3 minutes)")
                progress_bar.progress(30)
                
                # Poll workflow status
                max_wait = 300  # 5 minutes max
                waited = 0
                workflow_url = None
                
                while waited < max_wait:
                    status, conclusion, url = check_workflow_status()
                    workflow_url = url
                    
                    if status == "completed":
                        if conclusion == "success":
                            status_container.success("✅ Data downloaded successfully!")
                            break
                        else:
                            status_container.error("❌ Download failed. Check GitHub Actions logs.")
                            if workflow_url:
                                st.link_button("View Error Details", workflow_url)
                            st.stop()
                    
                    time.sleep(15)
                    waited += 15
                    progress_bar.progress(30 + int((waited / max_wait) * 30))
                
                if waited >= max_wait:
                    status_container.warning("⚠️ Download taking longer than expected. Check workflow status.")
                    if workflow_url:
                        st.link_button("Check Workflow Status", workflow_url)
                
                progress_bar.progress(60)
                time.sleep(2)
                
                # Step 3: Validate data
                status_container.info("✅ Step 3/5: Validating downloaded data...")
                progress_bar.progress(70)
                
                # Force refresh of file existence check
                st.rerun() if not (Path('data/RCB_24months.xlsx').exists() and Path('data/RCB_12months.xlsx').exists()) else None
                
                if Path('data/RCB_24months.xlsx').exists() and Path('data/RCB_12months.xlsx').exists():
                    status_container.success("✅ Data validation passed!")
                    time.sleep(1)
                else:
                    status_container.error("❌ Data files not found after download")
                    st.stop()
                
                # Step 4: Generate report
                status_container.info("📊 Step 4/5: Generating growth report...")
                progress_bar.progress(80)
                
                # Auto-generate report with new data
                try:
                    from process_report import process_growth_report
                    
                    df_24m = pd.read_excel('data/RCB_24months.xlsx')
                    df_12m = pd.read_excel('data/RCB_12months.xlsx')
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_dir = Path('generated_reports')
                    output_dir.mkdir(exist_ok=True)
                    output_file = output_dir / f'Client_Growth_Report_{timestamp}.xlsx'
                    
                    result = process_growth_report(df_24m, df_12m, str(output_file))
                    
                    status_container.success("✅ Report generated successfully!")
                    progress_bar.progress(90)
                    time.sleep(1)
                    
                    # Step 5: Send email
                    status_container.info("📧 Step 5/5: Sending email notification...")
                    
                    recipient_emails = st.secrets.get("REPORT_RECIPIENTS", "").split(",")
                    recipient_emails = [email.strip() for email in recipient_emails if email.strip()]
                    
                    if recipient_emails:
                        if send_email_report(str(output_file), recipient_emails):
                            status_container.success("✅ Email sent successfully!")
                        else:
                            status_container.warning("⚠️ Email failed, but report is ready for download")
                    else:
                        status_container.info("ℹ️ No email recipients configured. Skipping email.")
                    
                    progress_bar.progress(100)
                    
                    # Final success
                    st.balloons()
                    st.success(f"""
                    ### 🎉 Full Automation Completed Successfully!
                    
                    ✅ Data downloaded from RMS2
                    ✅ Data validated ({len(df_24m)} 24M records, {len(df_12m)} 12M records)
                    ✅ Growth report generated
                    ✅ Email notification sent (if configured)
                    
                    **Report Summary:**
                    - Total clients analyzed: {result.get('total_clients', 'N/A')}
                    - High growth clients: {result.get('high_growth_count', 'N/A')}
                    - Average growth: {result.get('avg_growth', 0):.1f}%
                    
                    **Report file:** {output_file.name}
                    """)
                    
                    # Download button
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            label="📥 Download Excel Report",
                            data=f,
                            file_name=output_file.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key='download_auto_generated'
                        )
                    
                except Exception as e:
                    status_container.error(f"❌ Report generation failed: {str(e)}")
                    st.code(traceback.format_exc())
            
            else:
                status_container.error("❌ Failed to trigger workflow. Check GITHUB_TOKEN secret.")
    
    st.markdown("---")
    if st.button("🚪 Logout", key="logout"):
        st.session_state.authenticated = False
        st.rerun()

# Main content area (existing code continues...)
# [Rest of your existing streamlit_app.py code for manual upload and report generation]

# Footer
st.markdown("---")
st.markdown("""

    Client Growth Report Generator v3.0 (Full Automation) | © 2024 Koenig Solutions

""", unsafe_allow_html=True)
