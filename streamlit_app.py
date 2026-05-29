"""
Client Growth Report Dashboard -- OTP-aware version

Flow when user clicks "Run RMS2 Download":
  1. Streamlit starts a background Playwright session (RMS2Session)
  2. The session logs in with username + password
  3. RMS2 shows the OTP screen; the session pauses
  4. Streamlit polls the session state and shows an OTP input box
  5. User checks Outlook, types the 6-digit code, clicks "Submit OTP"
  6. Session resumes -> downloads 24M + 12M Excel files
  7. process_report.py generates the final report
  8. Optionally emails it to recipients
"""

import os
import time
import smtplib
import ssl
import threading
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd
import streamlit as st

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Client Growth Report",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.main { background-color: #f5f7fa; }
.stButton>button {
    background: linear-gradient(135deg, #0099cc 0%, #003d5c 100%);
    color: white; font-weight: 600; border: none;
    padding: 0.5rem 2rem; border-radius: 25px;
}
.stButton>button:hover {
    background: linear-gradient(135deg, #007aa3 0%, #002d4c 100%);
}
h1 { color: #0099cc; }
.otp-box {
    padding: 1.5rem; background-color: #fff3e0;
    border-left: 4px solid #ff9800; border-radius: 4px; margin: 1rem 0;
}
</style>
""",
    unsafe_allow_html=True,
)

# ----------------- AUTH -----------------
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "login_password" not in st.session_state:
    st.session_state.login_password = DEFAULT_PASSWORD
if "reset_stage" not in st.session_state:
    st.session_state.reset_stage = None
if "rms2_session" not in st.session_state:
    st.session_state.rms2_session = None
if "auto_refresh_otp" not in st.session_state:
    st.session_state.auto_refresh_otp = False


# ----------------- HELPERS -----------------
def send_email_report(report_file_path, recipient_emails):
    """Send report via Outlook SMTP."""
    try:
        sender_email    = st.secrets.get("SMTP_EMAIL", "")
        sender_password = st.secrets.get("SMTP_PASSWORD", "")
        smtp_server     = st.secrets.get("SMTP_SERVER", "smtp.office365.com")
        smtp_port       = int(st.secrets.get("SMTP_PORT", 587))

        if not sender_email or not sender_password:
            return False, "Email credentials not configured"

        msg = MIMEMultipart()
        msg["From"]    = sender_email
        msg["To"]      = ", ".join(recipient_emails)
        msg["Subject"] = f"Client Growth Report - {datetime.now().strftime('%Y-%m-%d')}"
        body = f"""Hi Team,

Please find attached the Client Growth Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

Best regards,
Koenig Solutions Automated Report System"""
        msg.attach(MIMEText(body, "plain"))

        with open(report_file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f"attachment; filename={Path(report_file_path).name}")
        msg.attach(part)

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_emails, msg.as_string())
        server.quit()
        return True, f"Email sent to {len(recipient_emails)} recipient(s)"
    except Exception as e:
        return False, str(e)


def generate_report(file_24m, file_12m):
    """Run process_report.py on the two RCB files."""
    try:
        from process_report import process_growth_report
        df_24m = pd.read_excel(file_24m)
        df_12m = pd.read_excel(file_12m)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("generated_reports")
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f"Client_Growth_Report_{timestamp}.xlsx"
        result = process_growth_report(df_24m, df_12m, str(out_file))
        return True, out_file, result
    except Exception as e:
        return False, None, {"error": str(e)}


# ----------------- LOGIN SCREEN -----------------
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        logo_path = "assets/koenig_logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=300)

        if st.session_state.reset_stage is None:
            st.markdown("### 🔐 Login Required")
            with st.form("login_form"):
                u = st.text_input("Username", placeholder="admin")
                p = st.text_input("Password", type="password", placeholder="admin123")
                submit = st.form_submit_button("🔓 Login")
                if submit:
                    if u == DEFAULT_USERNAME and p == st.session_state.login_password:
                        st.session_state.authenticated = True
                        st.success("✅ Login successful!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
            if st.button("Forgot Password?"):
                st.session_state.reset_stage = "new_pw"
                st.rerun()
        else:
            st.markdown("### 🔐 Set New Password")
            np1 = st.text_input("New Password", type="password", key="np1")
            np2 = st.text_input("Confirm Password", type="password", key="np2")
            ca, cb = st.columns(2)
            with ca:
                if st.button("Update"):
                    if not np1 or np1 != np2:
                        st.error("Passwords don't match")
                    else:
                        st.session_state.login_password = np1
                        st.session_state.reset_stage = None
                        st.success("Password updated!")
                        time.sleep(0.8)
                        st.rerun()
            with cb:
                if st.button("Cancel"):
                    st.session_state.reset_stage = None
                    st.rerun()
    st.stop()


# ----------------- MAIN APP -----------------
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 Client Growth Report")
    st.markdown("**Powered by Koenig Solutions**")
st.markdown("---")

with st.sidebar:
    logo_path = "assets/koenig_logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)

    st.markdown("### Mode")
    mode = st.radio(
        "Choose:",
        ["🌐 Live RMS2 Download (with OTP)",
         "📥 Manual Upload",
         "🤖 Use Last Downloaded Files"],
    )

    st.markdown("---")
    st.markdown("### About")
    st.info(
        "**High Growth Filter**\n"
        "- Previous ≤ $5,000\n"
        "- Current ≥ $50,000\n\n"
        "**Output Sheets**\n"
        "1. Growth Comparison\n"
        "2. High Growth 5K-50K USD\n"
        "3. Summary\n"
        "4. Exceptions"
    )

    st.markdown("---")
    if st.button("🚪 Logout"):
        # Clean up any in-flight RMS2 session
        if st.session_state.rms2_session:
            try:
                st.session_state.rms2_session.close()
            except Exception:
                pass
            st.session_state.rms2_session = None
        st.session_state.authenticated = False
        st.rerun()


# ----------------- MODE: LIVE RMS2 DOWNLOAD (with OTP) -----------------
if mode == "🌐 Live RMS2 Download (with OTP)":
    st.header("🌐 Live RMS2 Download — with OTP")
    st.markdown(
        "This mode logs into RMS2, waits for the OTP sent to your Outlook, "
        "and downloads both 24-month and 12-month RCB files automatically."
    )

    # ── Step 1: configure credentials ──────────────────────────────────────
    rms_user = st.secrets.get("RMS_USERNAME", "")
    rms_pass = st.secrets.get("RMS_PASSWORD", "")

    if not rms_user or not rms_pass:
        st.warning(
            "⚠️ RMS2 credentials not set in Streamlit secrets. "
            "Go to Manage app → Secrets and add:\n```\nRMS_USERNAME = \"you@koenig-solutions.com\"\nRMS_PASSWORD = \"your-rms-password\"\n```"
        )
        st.stop()

    st.success(f"✅ RMS2 credentials loaded for: {rms_user}")

    session = st.session_state.rms2_session

    # ── Step 2: Start / Manual Run button ───────────────────────────────────
    if session is None or session.state in ("idle", "done", "error"):
        st.markdown("### Step 1: Start RMS2 Login")
        if st.button("▶️ Run RMS2 Download (Manual Trigger)",
                     use_container_width=True, key="start_rms2"):
            try:
                from rms2_downloader import RMS2Session
                new_session = RMS2Session(rms_user, rms_pass, data_dir="data",
                                          headless=True)
                new_session.start()
                st.session_state.rms2_session = new_session
                st.session_state.auto_refresh_otp = True
                st.rerun()
            except Exception as e:
                st.error(f"Could not start RMS2 session: {e}")

        # Show previous error if any
        if session is not None and session.state == "error":
            st.error(f"❌ Last run failed: {session.error}")

        st.stop()

    # ── Step 3: Display current session state ───────────────────────────────
    state = session.state
    msg = session.message or ""

    if state == "logging_in":
        with st.spinner("🔐 Logging in to RMS2..."):
            st.info(msg)
        time.sleep(2)
        st.rerun()

    elif state == "waiting_for_otp":
        st.markdown(
            f"<div class='otp-box'><b>📧 OTP Required</b><br>"
            f"{msg}</div>",
            unsafe_allow_html=True,
        )
        with st.form("otp_form"):
            otp_code = st.text_input(
                "Enter 6-digit OTP from your Outlook inbox:",
                max_chars=6, placeholder="123456",
            )
            submit_otp = st.form_submit_button("✅ Submit OTP")
            if submit_otp:
                if otp_code and otp_code.strip().isdigit():
                    session.submit_otp(otp_code)
                    st.success(f"OTP submitted: {otp_code}. Verifying...")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Please enter a valid 6-digit numeric code.")
        ca, cb = st.columns(2)
        with ca:
            if st.button("🔄 Refresh status"):
                st.rerun()
        with cb:
            if st.button("❌ Cancel"):
                session.close()
                st.session_state.rms2_session = None
                st.rerun()

    elif state == "authenticated":
        st.success(f"✅ {msg}")
        st.markdown("### Step 2: Download Both RCB Files")
        if st.button("📥 Download 24M + 12M from RCB", use_container_width=True):
            session.request_download()
            time.sleep(1)
            st.rerun()

    elif state == "downloading":
        with st.spinner(f"⬇️ {msg}"):
            st.info(msg)
        time.sleep(3)
        st.rerun()

    elif state == "done":
        st.success(f"🎉 {msg}")
        st.markdown(f"- 24M file: `{session.file_24m}`")
        st.markdown(f"- 12M file: `{session.file_12m}`")
        st.markdown("---")
        st.markdown("### Step 3: Generate Growth Report")
        if st.button("📊 Generate Report & Email", use_container_width=True):
            with st.spinner("Generating report..."):
                ok, report_file, result = generate_report(
                    session.file_24m, session.file_12m
                )
            if ok:
                st.success(
                    f"✅ Report generated! "
                    f"{result.get('total_clients', 0)} clients analyzed. "
                    f"{result.get('high_growth_clients', 0)} high-growth."
                )
                # Try to email it
                recipients = [
                    r.strip()
                    for r in st.secrets.get("REPORT_RECIPIENTS", "").split(",")
                    if r.strip()
                ]
                if recipients:
                    em_ok, em_msg = send_email_report(report_file, recipients)
                    if em_ok:
                        st.success(f"📧 {em_msg}")
                    else:
                        st.warning(f"⚠️ Email failed: {em_msg}")
                # Download button
                with open(report_file, "rb") as f:
                    st.download_button(
                        "📥 Download Excel Report",
                        f, report_file.name,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                st.balloons()
            else:
                st.error(f"❌ {result.get('error', 'Unknown error')}")

    elif state == "error":
        st.error(f"❌ {session.message}")
        if st.button("🔄 Reset and try again"):
            try:
                session.close()
            except Exception:
                pass
            st.session_state.rms2_session = None
            st.rerun()


# ----------------- MODE: MANUAL UPLOAD -----------------
elif mode == "📥 Manual Upload":
    st.header("📥 Manual Upload")
    st.markdown(
        "Upload the two RCB Excel files you downloaded manually from RMS2."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("24-Month Data")
        file_24m = st.file_uploader(
            "RCB_24months.xlsx", type=["xlsx"], key="up24"
        )
        if file_24m:
            st.success(f"✅ {file_24m.name} ({file_24m.size/1024/1024:.1f} MB)")
    with col2:
        st.subheader("12-Month Data")
        file_12m = st.file_uploader(
            "RCB_12months.xlsx", type=["xlsx"], key="up12"
        )
        if file_12m:
            st.success(f"✅ {file_12m.name} ({file_12m.size/1024/1024:.1f} MB)")

    st.markdown("---")
    if st.button("📊 Generate Report & Email",
                 use_container_width=True,
                 disabled=not (file_24m and file_12m)):
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        t24 = data_dir / "temp_RCB_24months.xlsx"
        t12 = data_dir / "temp_RCB_12months.xlsx"
        with open(t24, "wb") as f: f.write(file_24m.getbuffer())
        with open(t12, "wb") as f: f.write(file_12m.getbuffer())

        with st.spinner("Generating report..."):
            ok, report_file, result = generate_report(t24, t12)
        if ok:
            st.success(
                f"✅ {result.get('total_clients', 0)} clients analyzed | "
                f"{result.get('high_growth_clients', 0)} high-growth"
            )
            recipients = [
                r.strip()
                for r in st.secrets.get("REPORT_RECIPIENTS", "").split(",")
                if r.strip()
            ]
            if recipients:
                em_ok, em_msg = send_email_report(report_file, recipients)
                if em_ok:
                    st.success(f"📧 {em_msg}")
                else:
                    st.warning(f"⚠️ Email failed: {em_msg}")
            with open(report_file, "rb") as f:
                st.download_button(
                    "📥 Download Excel Report",
                    f, report_file.name,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            st.balloons()
        else:
            st.error(f"❌ {result.get('error', 'Unknown error')}")


# ----------------- MODE: USE LAST DOWNLOADED FILES -----------------
else:  # "🤖 Use Last Downloaded Files"
    st.header("🤖 Use Last Downloaded Files")
    f24 = Path("data/RCB_24months.xlsx")
    f12 = Path("data/RCB_12months.xlsx")

    if f24.exists() and f12.exists():
        last_24 = datetime.fromtimestamp(f24.stat().st_mtime)
        last_12 = datetime.fromtimestamp(f12.stat().st_mtime)
        st.info(
            f"✅ Files available\n\n"
            f"- RCB_24months.xlsx ({f24.stat().st_size/1024/1024:.1f} MB, "
            f"updated {last_24:%Y-%m-%d %H:%M})\n"
            f"- RCB_12months.xlsx ({f12.stat().st_size/1024/1024:.1f} MB, "
            f"updated {last_12:%Y-%m-%d %H:%M})"
        )
        if st.button("📊 Generate Report & Email", use_container_width=True):
            with st.spinner("Generating report..."):
                ok, report_file, result = generate_report(f24, f12)
            if ok:
                st.success(
                    f"✅ {result.get('total_clients', 0)} clients | "
                    f"{result.get('high_growth_clients', 0)} high-growth"
                )
                recipients = [
                    r.strip()
                    for r in st.secrets.get("REPORT_RECIPIENTS", "").split(",")
                    if r.strip()
                ]
                if recipients:
                    em_ok, em_msg = send_email_report(report_file, recipients)
                    if em_ok:
                        st.success(f"📧 {em_msg}")
                    else:
                        st.warning(f"⚠️ Email failed: {em_msg}")
                with open(report_file, "rb") as f:
                    st.download_button(
                        "📥 Download Excel Report",
                        f, report_file.name,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                st.balloons()
            else:
                st.error(f"❌ {result.get('error', 'Unknown error')}")
    else:
        st.warning(
            "⚠️ No downloaded files found. Use **Live RMS2 Download** or "
            "**Manual Upload** mode first."
        )


# ----------------- FOOTER -----------------
st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size:0.9rem; color:grey;'>"
    "Client Growth Report v3.0 (OTP-aware) | © 2025 Koenig Solutions"
    "</div>",
    unsafe_allow_html=True,
)
