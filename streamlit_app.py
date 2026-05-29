"""
Client Growth Report Dashboard -- v5.0 (cloud viewer)

This Streamlit app is intentionally simple:
  - Shows the LATEST generated report (download button)
  - Shows the report history (all files in generated_reports/)
  - Tells users to run the monthly job LOCALLY on the 14th

The actual RMS2 download + OTP + email pipeline runs OFFLINE via
`run_monthly.py` on your laptop (launched by the .bat / .sh scripts).
"""

import os
import time
from pathlib import Path
from datetime import datetime

import streamlit as st


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
.run-instructions {
    padding: 1.5rem; background: #fff7e6; border-left: 4px solid #ff9800;
    border-radius: 8px; margin: 1rem 0;
}
.run-instructions code {
    background: #fff; padding: 2px 6px; border-radius: 3px;
    border: 1px solid #ddd; font-size: 0.9rem;
}
.report-card {
    padding: 1rem; background: #ffffff; border: 1px solid #e0e0e0;
    border-radius: 8px; margin-bottom: 0.6rem;
}
.report-newest { border-left: 4px solid #4caf50; }
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
]:
    if k not in st.session_state:
        st.session_state[k] = v


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

st.markdown("---")


# ============ SIDEBAR ============
with st.sidebar:
    if Path("assets/koenig_logo.png").exists():
        st.image("assets/koenig_logo.png", width=200)

    st.markdown("### About")
    st.info(
        "**High Growth Filter**\n\n"
        "- Previous ≤ $5,000\n"
        "- Current ≥ $50,000\n\n"
        "**Output**: 4 Excel sheets\n"
        "1. Growth Comparison\n"
        "2. High Growth 5K-50K\n"
        "3. Summary\n"
        "4. Exceptions\n\n"
        "**Exchange rate**: 1 USD = 86 INR"
    )

    st.markdown("---")
    st.markdown("### Schedule")
    st.success(
        "🗓️ **Monthly Run: 14th of each month**\n\n"
        "Run `run_monthly.py` locally on your laptop. See homepage for instructions."
    )

    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()


# ============ HOW-TO-RUN PANEL ============
st.markdown("## ▶️ How to Run the Monthly Report")

st.markdown(
    """<div class='run-instructions'>
<b>Because RMS2 now requires OTP on every login, the report must be triggered
from your local computer</b> (laptop/desktop) so you can type the OTP into the
Chromium window that pops up.<br><br>

<b>One-time setup</b>: clone the repo + install dependencies (see <code>README.md</code>).<br>

<b>Every 14th</b> — three steps:
<ol>
<li>Open the project folder on your computer</li>
<li>Double-click <code>launchers\\run_local_windows.bat</code>
(Windows) or run <code>./launchers/run_local_mac_linux.sh</code> (Mac/Linux)</li>
<li>When the Chromium window appears, <b>type the OTP from your Outlook
inbox</b> into the RMS2 login screen. Everything after that is automatic:
download &rarr; build report &rarr; email &rarr; commit to git.</li>
</ol>
The report will appear in this dashboard once committed to git.
</div>""",
    unsafe_allow_html=True,
)


# ============ REPORT VIEWER ============
st.markdown("---")
st.markdown("## 📑 Generated Reports")

reports_dir = Path("generated_reports")
if not reports_dir.exists():
    st.info("No reports generated yet. Run `run_monthly.py` locally first.")
else:
    reports = sorted(
        reports_dir.glob("Client_Growth_Report_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not reports:
        st.info("No reports generated yet. Run `run_monthly.py` locally first.")
    else:
        # Latest report -- big card
        latest = reports[0]
        ts = datetime.fromtimestamp(latest.stat().st_mtime)
        size_mb = latest.stat().st_size / 1024 / 1024

        st.markdown(
            f"""<div class='report-card report-newest'>
<b>🆕 Latest Report</b><br>
<code>{latest.name}</code><br>
Generated: <b>{ts:%Y-%m-%d %H:%M:%S}</b> &nbsp;•&nbsp; Size: {size_mb:.1f} MB
</div>""",
            unsafe_allow_html=True,
        )
        with open(latest, "rb") as f:
            st.download_button(
                "📥 Download Latest Report",
                f, latest.name,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # History
        if len(reports) > 1:
            st.markdown("### 📚 History")
            with st.expander(f"Show all {len(reports)} reports", expanded=False):
                for r in reports[1:]:
                    rts = datetime.fromtimestamp(r.stat().st_mtime)
                    rmb = r.stat().st_size / 1024 / 1024
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(
                            f"`{r.name}` &nbsp;•&nbsp; "
                            f"{rts:%Y-%m-%d %H:%M} &nbsp;•&nbsp; {rmb:.1f} MB"
                        )
                    with c2:
                        with open(r, "rb") as f:
                            st.download_button(
                                "📥 Download",
                                f, r.name,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_{r.name}",
                            )


# ============ RAW DATA STATUS ============
st.markdown("---")
st.markdown("## 📦 Raw Data Files")
f24 = Path("data/RCB_24months.xlsx")
f12 = Path("data/RCB_12months.xlsx")
c1, c2 = st.columns(2)
with c1:
    if f24.exists():
        u = datetime.fromtimestamp(f24.stat().st_mtime)
        st.success(
            f"✅ **24M data**\n\n"
            f"{f24.stat().st_size/1024/1024:.1f} MB\n\n"
            f"Updated: {u:%Y-%m-%d %H:%M}"
        )
    else:
        st.warning("⚠️ RCB_24months.xlsx not in data/")
with c2:
    if f12.exists():
        u = datetime.fromtimestamp(f12.stat().st_mtime)
        st.success(
            f"✅ **12M data**\n\n"
            f"{f12.stat().st_size/1024/1024:.1f} MB\n\n"
            f"Updated: {u:%Y-%m-%d %H:%M}"
        )
    else:
        st.warning("⚠️ RCB_12months.xlsx not in data/")


# ============ FOOTER ============
st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size:0.9rem; color:grey;'>"
    "Client Growth Report v5.0 (Cloud Viewer) | © 2025 Koenig Solutions"
    "</div>",
    unsafe_allow_html=True,
)
