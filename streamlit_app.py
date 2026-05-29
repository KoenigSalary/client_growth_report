"""
Client Growth Report - Production-Ready Dashboard
Combines manual upload, auto-downloaded data, GitHub Actions trigger, and email delivery
FIXED: Default credentials changed to admin / admin123
       Forgot Password now always works (no registered-email gate)
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import time
import requests
import smtplib
import ssl
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Client Growth Report",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- CUSTOM CSS -----------------
st.markdown(
    """
<style>
.main { background-color: #f5f7fa; }
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
h1 { color: #0099cc; }
.success-box {
    padding: 1rem; background-color: #e8f5e9;
    border-left: 4px solid #4caf50; border-radius: 4px; margin: 1rem 0;
}
.info-box {
    padding: 1rem; background-color: #e3f2fd;
    border-left: 4px solid #2196f3; border-radius: 4px; margin: 1rem 0;
}
.warning-box {
    padding: 1rem; background-color: #fff3e0;
    border-left: 4px solid #ff9800; border-radius: 4px; margin: 1rem 0;
}
.error-box {
    padding: 1rem; background-color: #ffebee;
    border-left: 4px solid #f44336; border-radius: 4px; margin: 1rem 0;
}
.data-update-badge {
    background-color: #0099cc; color: white;
    padding: 0.3rem 0.8rem; border-radius: 15px;
    font-size: 0.85rem; display: inline-block; margin-top: 0.5rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIALS  ←  CHANGED HERE
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"      # ← updated from "koenig2024"

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "login_password" not in st.session_state:
    st.session_state.login_password = DEFAULT_PASSWORD

# Forgot-password flow: None → "new_pw" (direct, no email/OTP required)
if "reset_stage" not in st.session_state:
    st.session_state.reset_stage = None


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def trigger_github_workflow():
    """Trigger GitHub Actions workflow via API"""
    try:
        url = (
            "https://api.github.com/repos/KoenigSalary/client_growth_report"
            "/actions/workflows/download-rms2-data.yml/dispatches"
        )
        token = st.secrets.get("GITHUB_TOKEN", "")
        if not token:
            return False, "GitHub token not configured"

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        response = requests.post(url, headers=headers, json={"ref": "main"})
        if response.status_code == 204:
            return True, "Workflow triggered successfully"
        return False, f"API returned status {response.status_code}"
    except Exception as e:
        return False, str(e)


def check_workflow_status():
    """Check latest workflow run status"""
    try:
        url = (
            "https://api.github.com/repos/KoenigSalary/client_growth_report"
            "/actions/runs"
        )
        token = st.secrets.get("GITHUB_TOKEN", "")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        response = requests.get(url, headers=headers, params={"per_page": 1})
        if response.status_code == 200:
            runs = response.json().get("workflow_runs", [])
            if runs:
                return runs[0].get("status"), runs[0].get("conclusion")
        return None, None
    except Exception:
        return None, None


def send_email_report(report_file_path, recipient_emails):
    """Send email with report attachment via Outlook365"""
    try:
        sender_email    = st.secrets.get("SMTP_EMAIL", "")
        sender_password = st.secrets.get("SMTP_PASSWORD", "")
        smtp_server     = st.secrets.get("SMTP_SERVER", "smtp.office365.com")
        smtp_port       = int(st.secrets.get("SMTP_PORT", 587))

        if not sender_email or not sender_password:
            return False, "Email credentials not configured"

        msg             = MIMEMultipart()
        msg["From"]     = sender_email
        msg["To"]       = ", ".join(recipient_emails)
        msg["Subject"]  = f"Client Growth Report - {datetime.now().strftime('%Y-%m-%d')}"

        body = f"""
Hi Team,

Please find attached the Client Growth Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

Report Summary:
- Data Period: Previous 12M vs Current 12M
- Exchange Rate: 1 USD = 86 INR
- High Growth Filter: Previous ≤$5K, Current ≥$50K

Report includes 4 sheets:
1. Growth Comparison (all clients)
2. High Growth 5K-50K (filtered)
3. Summary (statistics)
4. Exceptions (if any)

Best regards,
Koenig Solutions Automated Report System
"""
        msg.attach(MIMEText(body, "plain"))

        with open(report_file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {Path(report_file_path).name}",
        )
        msg.attach(part)

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_emails, msg.as_string())
        server.quit()
        return True, f"Email sent to {len(recipient_emails)} recipient(s)"
    except Exception as e:
        return False, str(e)


def generate_report_with_email(file_24m_path, file_12m_path, source="manual"):
    """Generate report from Excel files"""
    try:
        from process_report import process_growth_report

        df_24m = pd.read_excel(file_24m_path)
        df_12m = pd.read_excel(file_12m_path)

        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("generated_reports")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"Client_Growth_Report_{timestamp}.xlsx"

        result = process_growth_report(df_24m, df_12m, str(output_file))

        if output_file.exists():
            return True, output_file, result
        return False, None, {"error": "Report file not created"}
    except Exception as e:
        return False, None, {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN + FORGOT PASSWORD  (simplified – no email required for reset)
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        logo_path = "assets/koenig_logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=300)

        # ── NORMAL LOGIN ──────────────────────────────────────────────────────
        if st.session_state.reset_stage is None:
            st.markdown("### 🔐 Login Required")

            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input(
                    "Password", type="password", placeholder="Enter password"
                )
                submit = st.form_submit_button("🔓 Login")

                if submit:
                    if (
                        username == DEFAULT_USERNAME
                        and password == st.session_state.login_password
                    ):
                        st.session_state.authenticated = True
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password. Please try again.")

            if st.button("Forgot Password?"):
                st.session_state.reset_stage = "new_pw"
                st.rerun()

            st.markdown("---")

        # ── RESET PASSWORD (direct – no email gate) ───────────────────────────
        elif st.session_state.reset_stage == "new_pw":
            st.markdown("### 🔐 Set New Password")
            st.info(
                "Enter a new password below. No email verification is required."
            )

            new_pass     = st.text_input("New Password",     type="password", key="np1")
            confirm_pass = st.text_input("Confirm Password", type="password", key="np2")

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Update Password"):
                    if not new_pass:
                        st.error("Please enter a new password.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match.")
                    elif len(new_pass) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        st.session_state.login_password = new_pass
                        st.session_state.reset_stage    = None
                        st.success(
                            "✅ Password updated! Please log in with your new password."
                        )
                        time.sleep(1.5)
                        st.rerun()
            with col_b:
                if st.button("Cancel"):
                    st.session_state.reset_stage = None
                    st.rerun()

            st.markdown("---")

    st.stop()  # Don't render the rest of the app until logged in


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 Client Growth Report")
    st.markdown("**Powered by Koenig Solutions**")
st.markdown("---")

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    logo_path = "assets/koenig_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)

    st.markdown("### Options")

    auto_files_exist = (
        Path("data/RCB_24months.xlsx").exists()
        and Path("data/RCB_12months.xlsx").exists()
    )

    if auto_files_exist:
        options        = ["🤖 Use Auto-Downloaded Data", "📥 Manual Upload"]
        default_option = 0
    else:
        options        = ["📥 Manual Upload"]
        default_option = 0

    option = st.radio("Select Mode:", options, index=default_option)

    if auto_files_exist:
        st.markdown("---")
        st.markdown("### 📊 Data Status")
        last_update_24m = datetime.fromtimestamp(
            Path("data/RCB_24months.xlsx").stat().st_mtime
        )
        last_update_12m = datetime.fromtimestamp(
            Path("data/RCB_12months.xlsx").stat().st_mtime
        )
        last_update = max(last_update_24m, last_update_12m)
        hours_ago   = (datetime.now() - last_update).total_seconds() / 3600
        if hours_ago < 24:
            st.success(f"✅ Fresh: {hours_ago:.1f}h ago")
        elif hours_ago < 168:
            st.info(f"📊 Recent: {hours_ago/24:.1f}d ago")
        else:
            st.warning(f"⚠️ Old: {hours_ago/24:.1f}d ago")

    if auto_files_exist or st.secrets.get("GITHUB_TOKEN"):
        st.markdown("---")
        st.markdown("### 🔄 Auto-Download")
        if st.button("🚀 Run Full Automation", key="full_auto", use_container_width=True):
            st.session_state.run_full_automation = True
            st.rerun()

    st.markdown("---")
    st.markdown("### About")
    st.info(
        """
**High Growth Filter:**
- Previous ≤ $5,000
- Current ≥ $50,000

**Report Sheets:**
1. Growth Comparison
2. High Growth 5K-50K
3. Summary
4. Exceptions
"""
    )
    st.markdown("---")
    if st.button("🚪 Logout", key="logout"):
        st.session_state.authenticated = False
        st.rerun()


# ── FULL AUTOMATION FLOW ──────────────────────────────────────────────────────
if st.session_state.get("run_full_automation", False):
    st.header("🚀 Full Automation in Progress")
    progress_bar = st.progress(0)
    status_text  = st.empty()

    status_text.info("📡 Step 1/5: Triggering GitHub Actions workflow...")
    progress_bar.progress(10)
    time.sleep(1)

    success, message = trigger_github_workflow()
    if success:
        status_text.success("✅ Step 1/5: Workflow triggered successfully!")
        time.sleep(2)

        status_text.info("⬇️ Step 2/5: Downloading data from RMS2... (2-3 minutes)")
        progress_bar.progress(30)

        max_wait, waited = 180, 0
        while waited < max_wait:
            wf_status, conclusion = check_workflow_status()
            if wf_status == "completed":
                if conclusion == "success":
                    status_text.success("✅ Step 2/5: Data downloaded successfully!")
                    break
                else:
                    status_text.error("❌ Step 2/5: Download failed. Check GitHub Actions logs.")
                    st.markdown(
                        "[View GitHub Actions →](https://github.com/KoenigSalary/client_growth_report/actions)"
                    )
                    st.session_state.run_full_automation = False
                    st.stop()
            time.sleep(10)
            waited += 10
            progress_bar.progress(30 + int((waited / max_wait) * 30))

        progress_bar.progress(60)
        time.sleep(2)

        status_text.info("✅ Step 3/5: Validating downloaded data...")
        progress_bar.progress(70)
        time.sleep(1)

        if Path("data/RCB_24months.xlsx").exists() and Path("data/RCB_12months.xlsx").exists():
            status_text.success("✅ Step 3/5: Data validation passed!")
        else:
            status_text.error("❌ Step 3/5: Data files not found")
            st.session_state.run_full_automation = False
            st.stop()

        time.sleep(1)
        status_text.info("📊 Step 4/5: Generating growth report...")
        progress_bar.progress(80)

        success, report_file, result = generate_report_with_email(
            Path("data/RCB_24months.xlsx"),
            Path("data/RCB_12months.xlsx"),
            "auto",
        )

        if success:
            status_text.success("✅ Step 4/5: Report generated successfully!")
            progress_bar.progress(90)
            time.sleep(1)

            status_text.info("📧 Step 5/5: Sending email notification...")
            recipient_emails = [
                e.strip()
                for e in st.secrets.get("REPORT_RECIPIENTS", "").split(",")
                if e.strip()
            ]
            if recipient_emails:
                email_success, email_message = send_email_report(report_file, recipient_emails)
                if email_success:
                    status_text.success(f"✅ Step 5/5: {email_message}")
                else:
                    status_text.warning(f"⚠️ Step 5/5: Email failed - {email_message}")
            else:
                status_text.info("ℹ️ Step 5/5: No email recipients configured")

            progress_bar.progress(100)
            time.sleep(1)
            st.balloons()
            st.success(
                f"🎉 Automation Complete! "
                f"✅ {result.get('total_clients', 0)} clients | "
                f"✅ Email sent to {len(recipient_emails)} recipient(s)"
            )
            with open(report_file, "rb") as f:
                st.download_button(
                    "📥 Download Excel Report", f, report_file.name,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_auto",
                )
        else:
            status_text.error(
                f"❌ Step 4/5: Report generation failed - {result.get('error', 'Unknown')}"
            )
    else:
        status_text.error(f"❌ Step 1/5: Failed to trigger workflow - {message}")

    st.session_state.run_full_automation = False


# ── AUTO-DOWNLOADED DATA ──────────────────────────────────────────────────────
elif option == "🤖 Use Auto-Downloaded Data":
    st.header("🤖 Use Auto-Downloaded Data")

    file_24m_path = Path("data/RCB_24months.xlsx")
    file_12m_path = Path("data/RCB_12months.xlsx")

    if file_24m_path.exists() and file_12m_path.exists():
        last_update = max(
            datetime.fromtimestamp(file_24m_path.stat().st_mtime),
            datetime.fromtimestamp(file_12m_path.stat().st_mtime),
        )
        st.info(
            f"✅ Data files available — Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')}  \n"
            f"- RCB_24months.xlsx ({file_24m_path.stat().st_size / 1024 / 1024:.1f} MB)  \n"
            f"- RCB_12months.xlsx ({file_12m_path.stat().st_size / 1024 / 1024:.1f} MB)"
        )
        st.markdown("---")

        if st.button("📊 Generate Report & Send Email", key="generate_auto"):
            with st.spinner("Generating report..."):
                success, report_file, result = generate_report_with_email(
                    file_24m_path, file_12m_path, "auto"
                )
                if success:
                    st.success(
                        f"✅ Report generated: {result.get('total_clients', 0)} clients analyzed"
                    )
                    recipient_emails = [
                        e.strip()
                        for e in st.secrets.get("REPORT_RECIPIENTS", "").split(",")
                        if e.strip()
                    ]
                    if recipient_emails:
                        ok, msg = send_email_report(report_file, recipient_emails)
                        st.success(f"📧 {msg}") if ok else st.warning(f"⚠️ Email failed: {msg}")

                    with open(report_file, "rb") as f:
                        st.download_button(
                            "📥 Download Excel Report", f, report_file.name,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                else:
                    st.error(f"❌ {result.get('error', 'Unknown error')}")
    else:
        st.warning(
            "⚠️ Auto-downloaded data files not found. "
            "Use Manual Upload or trigger auto-download from the sidebar."
        )


# ── MANUAL UPLOAD ─────────────────────────────────────────────────────────────
else:
    st.header("📥 Manual Upload")
    st.markdown(
        """
1. Download **RCB_24months.xlsx** and **RCB_12months.xlsx** from RMS2
2. Upload both files below
3. Click **Generate Report**
"""
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("24-Month Data")
        file_24m = st.file_uploader("Upload RCB_24months.xlsx", type=["xlsx"], key="file_24m")
        if file_24m:
            st.success(f"✅ {file_24m.name} ({file_24m.size / 1024 / 1024:.1f} MB)")
    with col2:
        st.subheader("12-Month Data")
        file_12m = st.file_uploader("Upload RCB_12months.xlsx", type=["xlsx"], key="file_12m")
        if file_12m:
            st.success(f"✅ {file_12m.name} ({file_12m.size / 1024 / 1024:.1f} MB)")

    st.markdown("---")

    if st.button("📊 Generate Report & Send Email", key="generate_manual",
                 disabled=not (file_24m and file_12m)):
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        temp_24m = data_dir / "temp_RCB_24months.xlsx"
        temp_12m = data_dir / "temp_RCB_12months.xlsx"
        with open(temp_24m, "wb") as f: f.write(file_24m.getbuffer())
        with open(temp_12m, "wb") as f: f.write(file_12m.getbuffer())

        with st.spinner("Generating report..."):
            success, report_file, result = generate_report_with_email(
                temp_24m, temp_12m, "manual"
            )
            if success:
                st.success(
                    f"✅ Report generated: {result.get('total_clients', 0)} clients analyzed"
                )
                recipient_emails = [
                    e.strip()
                    for e in st.secrets.get("REPORT_RECIPIENTS", "").split(",")
                    if e.strip()
                ]
                if recipient_emails:
                    ok, msg = send_email_report(report_file, recipient_emails)
                    st.success(f"📧 {msg}") if ok else st.warning(f"⚠️ Email failed: {msg}")

                with open(report_file, "rb") as f:
                    st.download_button(
                        "📥 Download Excel Report", f, report_file.name,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            else:
                st.error(f"❌ {result.get('error', 'Unknown error')}")


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
<div style="text-align:center; font-size:0.9rem; color:grey;">
Client Growth Report Generator v2.0 | © 2025 Koenig Solutions
</div>
""",
    unsafe_allow_html=True,
)
