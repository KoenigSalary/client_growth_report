"""
Client Growth Report Dashboard -- Dual-mode (Streamlit Cloud + Local)

The app auto-detects where it is running:
  - On Streamlit Cloud  -> shows Manual Upload + Use Last Files modes only
  - On the user's PC    -> ALSO shows "Local RMS2 Download" mode that opens
                           a visible Chromium window so the user can type OTP
                           directly into RMS2
"""

import os
import time
import smtplib
import ssl
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd
import streamlit as st


# ============ DETECT ENVIRONMENT ============
def is_running_locally() -> bool:
    """
    Detect whether we are running on Streamlit Cloud or on the user's PC.
    Streamlit Cloud sets several environment variables we can sniff.
    """
    cloud_indicators = [
        os.environ.get("STREAMLIT_RUNTIME_CREDENTIALS_FILE"),
        os.environ.get("HOSTNAME", "").startswith("streamlit-"),
        Path("/mount/src").exists(),       # streamlit cloud mount point
        os.environ.get("USER") == "appuser",
    ]
    # If ANY cloud indicator is true, treat as Streamlit Cloud (not local)
    return not any(cloud_indicators)


IS_LOCAL = is_running_locally()


# ============ PAGE CONFIG ============
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
.env-badge {
    display: inline-block; padding: 0.3rem 0.7rem; border-radius: 12px;
    font-size: 0.8rem; font-weight: 600;
}
.env-local { background: #c8e6c9; color: #1b5e20; }
.env-cloud { background: #bbdefb; color: #0d47a1; }
</style>
""",
    unsafe_allow_html=True,
)


# ============ AUTH ============
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

for k, v in [
    ("authenticated", False),
    ("login_password", DEFAULT_PASSWORD),
    ("reset_stage", None),
    ("rms2_session", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v


# ============ HELPERS ============
def send_email_report(report_file_path, recipient_emails):
    try:
        sender    = st.secrets.get("SMTP_EMAIL", "")
        sender_pw = st.secrets.get("SMTP_PASSWORD", "")
        server_h  = st.secrets.get("SMTP_SERVER", "smtp.office365.com")
        port      = int(st.secrets.get("SMTP_PORT", 587))
        if not sender or not sender_pw:
            return False, "Email credentials not configured"

        msg = MIMEMultipart()
        msg["From"]    = sender
        msg["To"]      = ", ".join(recipient_emails)
        msg["Subject"] = f"Client Growth Report - {datetime.now():%Y-%m-%d}"
        body = (
            f"Hi Team,\n\n"
            f"Please find attached the Client Growth Report generated on "
            f"{datetime.now():%Y-%m-%d %H:%M:%S}.\n\n"
            "Best regards,\nKoenig Solutions Automated Report System"
        )
        msg.attach(MIMEText(body, "plain"))
        with open(report_file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f"attachment; filename={Path(report_file_path).name}")
        msg.attach(part)

        s = smtplib.SMTP(server_h, port)
        s.starttls()
        s.login(sender, sender_pw)
        s.sendmail(sender, recipient_emails, msg.as_string())
        s.quit()
        return True, f"Email sent to {len(recipient_emails)} recipient(s)"
    except Exception as e:
        return False, str(e)


def generate_report(file_24m, file_12m):
    try:
        from process_report import process_growth_report
        df24 = pd.read_excel(file_24m)
        df12 = pd.read_excel(file_12m)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("generated_reports")
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f"Client_Growth_Report_{timestamp}.xlsx"
        result = process_growth_report(df24, df12, str(out_file))
        return True, out_file, result
    except Exception as e:
        return False, None, {"error": str(e)}


# ============ LOGIN SCREEN ============
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if Path("assets/koenig_logo.png").exists():
            st.image("assets/koenig_logo.png", width=300)

        if st.session_state.reset_stage is None:
            st.markdown("### 🔐 Login Required")
            with st.form("login_form"):
                u = st.text_input("Username", placeholder="admin")
                p = st.text_input("Password", type="password",
                                  placeholder="admin123")
                if st.form_submit_button("🔓 Login"):
                    if u == DEFAULT_USERNAME and p == st.session_state.login_password:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
            if st.button("Forgot Password?"):
                st.session_state.reset_stage = "new_pw"
                st.rerun()
        else:
            st.markdown("### 🔐 Set New Password")
            n1 = st.text_input("New Password", type="password", key="np1")
            n2 = st.text_input("Confirm",       type="password", key="np2")
            ca, cb = st.columns(2)
            with ca:
                if st.button("Update"):
                    if not n1 or n1 != n2:
                        st.error("Passwords don't match")
                    else:
                        st.session_state.login_password = n1
                        st.session_state.reset_stage = None
                        st.success("Password updated!")
                        time.sleep(0.8)
                        st.rerun()
            with cb:
                if st.button("Cancel"):
                    st.session_state.reset_stage = None
                    st.rerun()
    st.stop()


# ============ MAIN APP ============
h1, h2 = st.columns([3, 1])
with h1:
    st.title("📊 Client Growth Report")
    st.markdown("**Powered by Koenig Solutions**")
with h2:
    if IS_LOCAL:
        st.markdown(
            "<span class='env-badge env-local'>🖥️ LOCAL MODE</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span class='env-badge env-cloud'>☁️ CLOUD MODE</span>",
            unsafe_allow_html=True,
        )
st.markdown("---")


# ============ SIDEBAR ============
with st.sidebar:
    if Path("assets/koenig_logo.png").exists():
        st.image("assets/koenig_logo.png", width=200)

    st.markdown("### Mode")
    if IS_LOCAL:
        modes = [
            "🌐 Local RMS2 Download (visible browser + OTP)",
            "📥 Manual Upload",
            "🤖 Use Last Downloaded Files",
        ]
    else:
        modes = [
            "📥 Manual Upload",
            "🤖 Use Last Downloaded Files",
        ]
        st.caption(
            "💡 To download fresh data from RMS2, run this app locally. "
            "See README.md for instructions."
        )
    mode = st.radio("Choose:", modes, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### Info")
    st.info(
        "**High Growth Filter**\n"
        "- Previous ≤ $5,000\n"
        "- Current ≥ $50,000\n\n"
        "**Output**: 4 Excel sheets\n"
        "1. Growth Comparison\n"
        "2. High Growth 5K-50K\n"
        "3. Summary\n"
        "4. Exceptions"
    )

    st.markdown("---")
    if st.button("🚪 Logout"):
        if st.session_state.rms2_session:
            try:
                st.session_state.rms2_session.cancel()
            except Exception:
                pass
            st.session_state.rms2_session = None
        st.session_state.authenticated = False
        st.rerun()


# ============ MODE: LOCAL RMS2 DOWNLOAD (visible browser) ============
if mode.startswith("🌐 Local RMS2 Download"):
    st.header("🌐 Local RMS2 Download — Visible Browser + OTP")
    st.markdown(
        "This mode opens a **real Chromium window** on your computer. "
        "The script fills email + password automatically, then **you type "
        "the OTP directly into the RMS2 window** and click Submit. "
        "Once you're authenticated, the script downloads both Excel files "
        "and closes the browser."
    )

    # Read RMS2 credentials -- from .env, secrets.toml, OR an input box
    rms_user = (
        os.environ.get("RMS_USERNAME", "").strip()
        or st.secrets.get("RMS_USERNAME", "")
    )
    rms_pass = (
        os.environ.get("RMS_PASSWORD", "").strip()
        or st.secrets.get("RMS_PASSWORD", "")
    )

    if not rms_user or not rms_pass:
        st.warning(
            "⚠️ RMS2 credentials not found. Enter them below "
            "(or set them in `.env` / `.streamlit/secrets.toml`)."
        )
        with st.form("creds_form"):
            in_user = st.text_input("RMS2 Email", value=rms_user)
            in_pass = st.text_input("RMS2 Password", type="password",
                                    value=rms_pass)
            if st.form_submit_button("💾 Use these credentials"):
                rms_user = in_user.strip()
                rms_pass = in_pass.strip()
                st.session_state["_rms_user_tmp"] = rms_user
                st.session_state["_rms_pass_tmp"] = rms_pass
                st.rerun()
        # Use temp creds if user just entered them
        rms_user = rms_user or st.session_state.get("_rms_user_tmp", "")
        rms_pass = rms_pass or st.session_state.get("_rms_pass_tmp", "")
        if not (rms_user and rms_pass):
            st.stop()

    st.success(f"✅ Credentials loaded for: **{rms_user}**")

    session = st.session_state.rms2_session

    # --- Start button ---
    if session is None or session.state in ("idle", "done", "error"):
        if session is not None and session.state == "error":
            st.error(f"❌ Last run failed: {session.error}")

        if st.button("▶️ Launch Browser & Start Login",
                     use_container_width=True, key="start_local"):
            try:
                from rms2_downloader_local import RMS2LocalSession
                new_sess = RMS2LocalSession(rms_user, rms_pass, "data")
                new_sess.start()
                st.session_state.rms2_session = new_sess
                st.rerun()
            except ImportError:
                st.error(
                    "❌ Playwright is not installed locally. "
                    "Run:\n```\npip install playwright\npython -m playwright install chromium\n```"
                )
            except Exception as e:
                st.error(f"Could not start: {e}")
        st.stop()

    # --- Display live state ---
    state = session.state
    msg = session.message or ""

    if state in ("opening_browser", "filling_credentials"):
        st.info(f"🚀 {msg}")
        st.caption("A Chromium window will appear in a moment...")
        time.sleep(3)
        st.rerun()

    elif state == "waiting_for_user_otp":
        st.markdown(
            f"<div class='otp-box'><b>🔑 ACTION REQUIRED</b><br><br>"
            f"{msg.replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("👀 **Look at the Chromium window that opened** — that's where you enter the OTP.")
        cA, cB = st.columns(2)
        with cA:
            if st.button("🔄 Refresh status", key="refresh_otp"):
                st.rerun()
        with cB:
            if st.button("❌ Cancel"):
                session.cancel()
                st.session_state.rms2_session = None
                st.rerun()
        time.sleep(3)
        st.rerun()

    elif state in ("authenticated", "downloading_24m", "downloading_12m"):
        st.success(f"✅ {msg}")
        st.caption("Downloads run in the background. This page auto-refreshes.")
        time.sleep(3)
        st.rerun()

    elif state == "done":
        st.success(f"🎉 {msg}")
        st.markdown(f"- 24M file: `{session.file_24m}`")
        st.markdown(f"- 12M file: `{session.file_12m}`")
        st.markdown("---")
        st.markdown("### 📊 Generate Report")
        if st.button("Generate Growth Report & Email",
                     use_container_width=True):
            with st.spinner("Building report..."):
                ok, report_file, result = generate_report(
                    session.file_24m, session.file_12m
                )
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
                    st.success(f"📧 {em_msg}") if em_ok else st.warning(em_msg)
                with open(report_file, "rb") as f:
                    st.download_button(
                        "📥 Download Excel Report",
                        f, report_file.name,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                st.balloons()
            else:
                st.error(f"❌ {result.get('error', 'Unknown error')}")

        if st.button("🔄 Start a fresh RMS2 session"):
            st.session_state.rms2_session = None
            st.rerun()

    elif state == "error":
        st.error(f"❌ {msg}")
        if st.button("🔄 Try again"):
            try:
                session.cancel()
            except Exception:
                pass
            st.session_state.rms2_session = None
            st.rerun()


# ============ MODE: MANUAL UPLOAD ============
elif mode == "📥 Manual Upload":
    st.header("📥 Manual Upload")
    st.markdown(
        "Upload the two RCB Excel files you downloaded from RMS2 manually."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("24-Month")
        f24 = st.file_uploader("RCB_24months.xlsx", type=["xlsx"], key="up24")
        if f24:
            st.success(f"✅ {f24.name} ({f24.size/1024/1024:.1f} MB)")
    with c2:
        st.subheader("12-Month")
        f12 = st.file_uploader("RCB_12months.xlsx", type=["xlsx"], key="up12")
        if f12:
            st.success(f"✅ {f12.name} ({f12.size/1024/1024:.1f} MB)")

    st.markdown("---")
    if st.button("📊 Generate Report & Email", use_container_width=True,
                 disabled=not (f24 and f12)):
        d = Path("data"); d.mkdir(exist_ok=True)
        t24 = d / "temp_RCB_24months.xlsx"
        t12 = d / "temp_RCB_12months.xlsx"
        with open(t24, "wb") as f: f.write(f24.getbuffer())
        with open(t12, "wb") as f: f.write(f12.getbuffer())
        with st.spinner("Generating report..."):
            ok, rf, result = generate_report(t24, t12)
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
                em_ok, em_msg = send_email_report(rf, recipients)
                st.success(f"📧 {em_msg}") if em_ok else st.warning(em_msg)
            with open(rf, "rb") as f:
                st.download_button(
                    "📥 Download Excel Report",
                    f, rf.name,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            st.balloons()
        else:
            st.error(f"❌ {result.get('error', 'Unknown error')}")


# ============ MODE: USE LAST DOWNLOADED FILES ============
else:
    st.header("🤖 Use Last Downloaded Files")
    f24 = Path("data/RCB_24months.xlsx")
    f12 = Path("data/RCB_12months.xlsx")
    if f24.exists() and f12.exists():
        lu24 = datetime.fromtimestamp(f24.stat().st_mtime)
        lu12 = datetime.fromtimestamp(f12.stat().st_mtime)
        st.info(
            f"✅ Files available\n\n"
            f"- RCB_24months.xlsx ({f24.stat().st_size/1024/1024:.1f} MB, "
            f"updated {lu24:%Y-%m-%d %H:%M})\n"
            f"- RCB_12months.xlsx ({f12.stat().st_size/1024/1024:.1f} MB, "
            f"updated {lu12:%Y-%m-%d %H:%M})"
        )
        if st.button("📊 Generate Report & Email", use_container_width=True):
            with st.spinner("Generating report..."):
                ok, rf, result = generate_report(f24, f12)
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
                    em_ok, em_msg = send_email_report(rf, recipients)
                    st.success(f"📧 {em_msg}") if em_ok else st.warning(em_msg)
                with open(rf, "rb") as f:
                    st.download_button(
                        "📥 Download Excel Report",
                        f, rf.name,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                st.balloons()
            else:
                st.error(f"❌ {result.get('error', 'Unknown error')}")
    else:
        st.warning(
            "⚠️ No downloaded files in `data/`. "
            "Use **Manual Upload** or **Local RMS2 Download** first."
        )


# ============ FOOTER ============
st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size:0.9rem; color:grey;'>"
    "Client Growth Report v4.0 (Dual-Mode) | © 2025 Koenig Solutions"
    "</div>",
    unsafe_allow_html=True,
)
