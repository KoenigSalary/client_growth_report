"""
Client Growth Report - Clean Streamlit Dashboard v2.2

Fixes:
1. Stable login using Streamlit secrets or fallback credentials.
2. Removed temporary/session-only password reset.
3. Adds editable exchange-rate window in sidebar.
4. Passes exchange_rate into process_growth_report().
5. Uses same exchange rate in email body.
"""

import os
import time
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

import pandas as pd
import requests
import streamlit as st


# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Client Growth Report",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------- BASIC STYLE -----------------
st.markdown(
    """
<style>
.stButton>button {
    background: linear-gradient(135deg, #0099cc 0%, #003d5c 100%);
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 22px;
}
h1, h2, h3 {
    color: #0099cc;
}
</style>
""",
    unsafe_allow_html=True,
)


# ----------------- SETTINGS -----------------
DASHBOARD_USERNAME = st.secrets.get("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = st.secrets.get("DASHBOARD_PASSWORD", "koenig1993")
DEFAULT_EXCHANGE_RATE = float(st.secrets.get("DEFAULT_EXCHANGE_RATE", 84.0))

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "exchange_rate" not in st.session_state:
    st.session_state.exchange_rate = DEFAULT_EXCHANGE_RATE


# ----------------- HELPERS -----------------
def trigger_github_workflow():
    """Trigger GitHub Actions workflow via API."""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        if not token:
            return False, "GitHub token not configured"

        url = "https://api.github.com/repos/KoenigSalary/client_growth_report/actions/workflows/download-rms2-data.yml/dispatches"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        response = requests.post(url, headers=headers, json={"ref": "main"}, timeout=30)

        if response.status_code == 204:
            return True, "Workflow triggered successfully"

        return False, f"GitHub API returned status {response.status_code}: {response.text[:300]}"

    except Exception as exc:
        return False, str(exc)


def check_workflow_status():
    """Check latest GitHub Actions workflow run status."""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        if not token:
            return None, None

        url = "https://api.github.com/repos/KoenigSalary/client_growth_report/actions/runs"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        response = requests.get(url, headers=headers, params={"per_page": 1}, timeout=30)

        if response.status_code == 200:
            runs = response.json().get("workflow_runs", [])
            if runs:
                return runs[0].get("status"), runs[0].get("conclusion")

        return None, None

    except Exception:
        return None, None


def get_recipients():
    raw = st.secrets.get("REPORT_RECIPIENTS", "")
    return [email.strip() for email in raw.split(",") if email.strip()]


def send_email_report(report_file_path, recipient_emails, exchange_rate):
    """Send report attachment via Outlook SMTP."""
    try:
        sender_email = st.secrets.get("SMTP_EMAIL", "")
        sender_password = st.secrets.get("SMTP_PASSWORD", "")
        smtp_server = st.secrets.get("SMTP_SERVER", "smtp.office365.com")
        smtp_port = int(st.secrets.get("SMTP_PORT", 587))

        if not sender_email or not sender_password:
            return False, "Email credentials not configured"

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipient_emails)
        msg["Subject"] = f"Client Growth Report - {datetime.now().strftime('%Y-%m-%d')}"

        body = f"""Hi Team,

Please find attached the Client Growth Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

Report Summary:
- Data Period: Previous 12M vs Current 12M
- Exchange Rate Used: 1 USD = {exchange_rate:g} INR
- High Growth Filter: Previous <= $5K and Current >= $50K

Report includes:
1. Growth Comparison
2. High Growth 5K-50K
3. Summary
4. Exceptions

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
            f"attachment; filename={Path(report_file_path).name}",
        )
        msg.attach(part)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_emails, msg.as_string())

        return True, f"Email sent to {len(recipient_emails)} recipient(s)"

    except Exception as exc:
        return False, str(exc)


def generate_report(file_24m_path, file_12m_path, exchange_rate):
    """Generate Excel report and pass exchange_rate to process_report.py."""
    try:
        from process_report import process_growth_report

        df_24m = pd.read_excel(file_24m_path)
        df_12m = pd.read_excel(file_12m_path)

        output_dir = Path("generated_reports")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"Client_Growth_Report_{timestamp}.xlsx"

        # Preferred: process_report.py should support exchange_rate parameter.
        try:
            result = process_growth_report(
                df_24m,
                df_12m,
                str(output_file),
                exchange_rate=exchange_rate,
            )
        except TypeError:
            # Fallback for old process_report.py.
            # NOTE: old process_report.py must read os.environ["INR_TO_USD"] for this to work.
            os.environ["INR_TO_USD"] = str(exchange_rate)
            result = process_growth_report(df_24m, df_12m, str(output_file))

        if output_file.exists():
            return True, output_file, result

        return False, None, {"error": "Report file was not created"}

    except Exception as exc:
        return False, None, {"error": str(exc)}


def show_download_button(report_file, key):
    with open(report_file, "rb") as f:
        st.download_button(
            label="📥 Download Excel Report",
            data=f,
            file_name=Path(report_file).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=key,
        )


def run_report_and_email(file_24m_path, file_12m_path, key_prefix):
    exchange_rate = float(st.session_state.exchange_rate)

    with st.spinner("Generating report..."):
        success, report_file, result = generate_report(
            file_24m_path,
            file_12m_path,
            exchange_rate,
        )

    if not success:
        st.error(f"❌ Report generation failed: {result.get('error', 'Unknown error')}")
        return

    st.success(f"✅ Report generated: {result.get('total_clients', 0)} clients analyzed")
    st.info(f"Exchange rate used: 1 USD = {exchange_rate:g} INR")

    recipients = get_recipients()
    if recipients:
        email_success, email_message = send_email_report(
            report_file,
            recipients,
            exchange_rate,
        )
        if email_success:
            st.success(f"📧 {email_message}")
        else:
            st.warning(f"⚠️ Email failed: {email_message}")
    else:
        st.info("No REPORT_RECIPIENTS configured in Streamlit Secrets.")

    show_download_button(report_file, f"download_{key_prefix}")


# ----------------- LOGIN -----------------
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        logo_path = "assets/koenig_logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=280)

        st.markdown("### 🔐 Login Required")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("🔓 Login")

        if submit:
            if username.strip() == DASHBOARD_USERNAME and password.strip() == DASHBOARD_PASSWORD:
                st.session_state.authenticated = True
                st.success("✅ Login successful")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
                st.caption("Default fallback login is admin / koenig1993 unless Streamlit Secrets override it.")

        st.markdown("---")
        st.caption("Password reset removed because previous reset was session-only and caused login failure after logout.")

    st.stop()


# ----------------- MAIN APP -----------------
col1, col2 = st.columns([4, 1])

with col1:
    st.title("📊 Client Growth Report")
    st.markdown("**Powered by Koenig Solutions**")

with col2:
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

st.markdown("---")


# ----------------- SIDEBAR -----------------
with st.sidebar:
    logo_path = "assets/koenig_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)

    st.markdown("### ⚙️ Report Settings")

    st.session_state.exchange_rate = st.number_input(
        "Exchange Rate: 1 USD = INR",
        min_value=1.0,
        max_value=200.0,
        value=float(st.session_state.exchange_rate),
        step=0.25,
        help="This rate will be used for INR to USD conversion and email summary.",
    )

    st.caption(f"Formula: USD = INR amount ÷ {st.session_state.exchange_rate:g}")
    st.markdown("---")

    auto_files_exist = (
        Path("data/RCB_24months.xlsx").exists()
        and Path("data/RCB_12months.xlsx").exists()
    )

    options = ["📥 Manual Upload"]
    if auto_files_exist:
        options.insert(0, "🤖 Use Auto-Downloaded Data")

    option = st.radio("Select Mode", options)

    if auto_files_exist:
        st.markdown("### 📊 Data Status")
        f24 = Path("data/RCB_24months.xlsx")
        f12 = Path("data/RCB_12months.xlsx")
        last_update = max(
            datetime.fromtimestamp(f24.stat().st_mtime),
            datetime.fromtimestamp(f12.stat().st_mtime),
        )
        hours_ago = (datetime.now() - last_update).total_seconds() / 3600

        if hours_ago < 24:
            st.success(f"Fresh: {hours_ago:.1f}h ago")
        elif hours_ago < 168:
            st.info(f"Recent: {hours_ago / 24:.1f}d ago")
        else:
            st.warning(f"Old: {hours_ago / 24:.1f}d ago")

    if st.secrets.get("GITHUB_TOKEN", ""):
        st.markdown("---")
        if st.button("🚀 Run Full Automation", use_container_width=True):
            st.session_state.run_full_automation = True
            st.rerun()

    st.markdown("---")
    st.info(
        """
High Growth Filter:
- Previous <= $5,000
- Current >= $50,000
"""
    )


# ----------------- FULL AUTOMATION -----------------
if st.session_state.get("run_full_automation", False):
    st.header("🚀 Full Automation")

    progress = st.progress(0)
    status = st.empty()

    status.info("Triggering GitHub Actions workflow...")
    progress.progress(10)

    success, message = trigger_github_workflow()

    if not success:
        status.error(f"Failed to trigger workflow: {message}")
        st.session_state.run_full_automation = False
        st.stop()

    status.success("Workflow triggered successfully")
    progress.progress(25)

    status.info("Waiting for GitHub Actions to complete...")
    max_wait = 240
    waited = 0

    while waited < max_wait:
        workflow_status, conclusion = check_workflow_status()

        if workflow_status == "completed":
            if conclusion == "success":
                status.success("Data download completed")
                break

            status.error("GitHub Actions failed. Please check Actions logs.")
            st.markdown("[Open GitHub Actions](https://github.com/KoenigSalary/client_growth_report/actions)")
            st.session_state.run_full_automation = False
            st.stop()

        time.sleep(10)
        waited += 10
        progress.progress(min(70, 25 + int((waited / max_wait) * 45)))

    f24 = Path("data/RCB_24months.xlsx")
    f12 = Path("data/RCB_12months.xlsx")

    if not (f24.exists() and f12.exists()):
        status.error("Data files not found after workflow completion.")
        st.session_state.run_full_automation = False
        st.stop()

    progress.progress(80)
    status.info("Generating report...")
    run_report_and_email(f24, f12, "automation")
    progress.progress(100)
    st.session_state.run_full_automation = False


# ----------------- AUTO-DOWNLOADED DATA -----------------
elif option == "🤖 Use Auto-Downloaded Data":
    st.header("🤖 Use Auto-Downloaded Data")

    f24 = Path("data/RCB_24months.xlsx")
    f12 = Path("data/RCB_12months.xlsx")

    if f24.exists() and f12.exists():
        st.success("✅ Auto-downloaded files are available")
        st.write(f"24M file: `{f24}`")
        st.write(f"12M file: `{f12}`")

        if st.button("📊 Generate Report & Send Email", key="generate_auto"):
            run_report_and_email(f24, f12, "auto")
    else:
        st.warning("Auto-downloaded files not found. Please use Manual Upload.")


# ----------------- MANUAL UPLOAD -----------------
else:
    st.header("📥 Manual Upload")

    st.markdown(
        """
1. Upload **RCB_24months.xlsx**
2. Upload **RCB_12months.xlsx**
3. Set exchange rate from the sidebar
4. Click **Generate Report & Send Email**
"""
    )

    col1, col2 = st.columns(2)

    with col1:
        file_24m = st.file_uploader(
            "Upload RCB_24months.xlsx",
            type=["xlsx"],
            key="file_24m",
        )
        if file_24m:
            st.success(f"Uploaded: {file_24m.name}")

    with col2:
        file_12m = st.file_uploader(
            "Upload RCB_12months.xlsx",
            type=["xlsx"],
            key="file_12m",
        )
        if file_12m:
            st.success(f"Uploaded: {file_12m.name}")

    if st.button(
        "📊 Generate Report & Send Email",
        disabled=not (file_24m and file_12m),
        key="generate_manual",
    ):
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        temp_24m = data_dir / "temp_RCB_24months.xlsx"
        temp_12m = data_dir / "temp_RCB_12months.xlsx"

        with open(temp_24m, "wb") as f:
            f.write(file_24m.getbuffer())

        with open(temp_12m, "wb") as f:
            f.write(file_12m.getbuffer())

        run_report_and_email(temp_24m, temp_12m, "manual")


# ----------------- FOOTER -----------------
st.markdown("---")
st.markdown(
    """
<div style="text-align:center; font-size:0.9rem; color:grey;">
Client Growth Report Generator v2.2 | © 2026 Koenig Solutions
</div>
""",
    unsafe_allow_html=True,
)
