"""
Client Growth Report Dashboard -- v5.3 (multi-user edition)

What's new in v5.3:
  - "Run Now" button (visible only when Streamlit runs locally)
  - Auto-detects local vs Streamlit Cloud via env + filesystem checks
  - Supports two operators (maker + one colleague) from separate laptops
  - Onboarding via launchers/setup_mac.sh and launchers/setup_windows.bat

Inherited from v5.2:
  - KPI cards, Top-10 bar chart, High-Growth table, distribution pie
  - Configurable exchange rate slider
"""

import os
import sys
import time
import platform
import subprocess
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


# ============ LOCAL vs CLOUD DETECTION ============
def is_running_locally() -> bool:
    """
    Return True only when Streamlit is running on the user's own laptop
    (Mac/Windows/Linux desktop), False on Streamlit Cloud or any container.

    Strategy: positive signals + negative signals. We require zero negative
    signals AND at least one positive signal.
    """
    # --- NEGATIVE SIGNALS (Streamlit Cloud / containers) ---
    if Path("/mount/src").exists():           # Streamlit Cloud mount
        return False
    if os.environ.get("STREAMLIT_SHARING_MODE"):
        return False
    if os.environ.get("HOSTNAME", "").startswith("streamlit-"):
        return False
    try:
        if os.environ.get("USER") == "appuser":  # cloud user
            return False
    except Exception:
        pass

    # --- POSITIVE SIGNALS (real desktop) ---
    system = platform.system()
    if system == "Darwin":     # macOS
        return True
    if system == "Windows":
        return True
    if system == "Linux":
        # On Linux desktops there's usually a DISPLAY or WAYLAND_DISPLAY var
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            return True
    return False


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
.kpi-card {
    background: white; padding: 1.2rem 1.5rem; border-radius: 12px;
    border-left: 4px solid #0099cc; box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    height: 100%;
}
.kpi-card h3 {
    margin: 0; color: #666; font-size: 0.85rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.kpi-card .value {
    font-size: 1.8rem; font-weight: 700; color: #003d5c; margin-top: 0.3rem;
}
.kpi-card .sub {
    font-size: 0.8rem; color: #999; margin-top: 0.2rem;
}
.kpi-good   { border-left-color: #4caf50; }
.kpi-warn   { border-left-color: #ff9800; }
.kpi-info   { border-left-color: #2196f3; }
.kpi-purple { border-left-color: #9c27b0; }
.run-instructions {
    padding: 1.2rem; background: #fff7e6; border-left: 4px solid #ff9800;
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
    ("inr_to_usd", 86.0),
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


# ============ MAIN APP HEADER + SIDEBAR ============
h1, h2 = st.columns([3, 1])
with h1:
    st.title("📊 Client Growth Report")
    st.markdown("**Powered by Koenig Solutions**")
st.markdown("---")

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
        "4. Exceptions"
    )

    st.markdown("---")
    st.markdown("### ▶ Run Report")

    if IS_LOCAL:
        st.caption(f"Detected: **local** ({platform.system()}) — manual run available")
        run_clicked = st.button(
            "▶ Run Now",
            use_container_width=True,
            help="Launches run_monthly.py in a new window. RMS2 OTP prompt will appear in Terminal.",
        )
        if run_clicked:
            try:
                proj_root = Path(__file__).resolve().parent
                system = platform.system()

                if system == "Darwin":
                    # macOS: open a new Terminal window running the launcher script
                    sh = proj_root / "launchers" / "run_local_mac_linux.sh"
                    if sh.exists():
                        subprocess.Popen([
                            "osascript", "-e",
                            f'tell application "Terminal" to do script "bash {sh}"'
                        ])
                        st.success("✅ Launched in a new Terminal window. Watch that window for the RMS2 OTP prompt.")
                    else:
                        # Fallback: run in background, no terminal
                        subprocess.Popen(
                            [sys.executable, str(proj_root / "run_monthly.py")],
                            cwd=str(proj_root),
                        )
                        st.success("✅ Started in background. Check your inbox for the OTP and look at the Streamlit console.")

                elif system == "Windows":
                    bat = proj_root / "launchers" / "run_local_windows.bat"
                    if bat.exists():
                        subprocess.Popen(
                            ["cmd.exe", "/c", "start", "", str(bat)],
                            cwd=str(proj_root),
                            shell=False,
                        )
                        st.success("✅ Launched in a new Command Prompt window. Watch that window for the OTP prompt.")
                    else:
                        subprocess.Popen(
                            [sys.executable, str(proj_root / "run_monthly.py")],
                            cwd=str(proj_root),
                        )
                        st.success("✅ Started in background.")
                else:
                    # Linux
                    subprocess.Popen(
                        [sys.executable, str(proj_root / "run_monthly.py")],
                        cwd=str(proj_root),
                    )
                    st.success("✅ Started. Check the Streamlit console for the OTP prompt.")
            except Exception as e:
                st.error(f"Could not start the run: {e}")

        st.caption("💡 Tip: After clicking, switch to the Terminal/Command-Prompt window to enter the RMS2 OTP from your Outlook inbox.")
    else:
        st.info(
            "🌐 **Cloud mode (view-only)**\n\n"
            "To generate a fresh report, run the **Client Growth Report** app on your laptop "
            "(or `python run_monthly.py`).\n\n"
            "This dashboard auto-refreshes once the new file is committed to GitHub."
        )

    st.markdown("---")
    st.markdown("### 🗓️ Schedule")
    st.success("Run on the **14th of every month**")

    st.markdown("---")
    st.markdown("### 💱 Exchange Rate")
    st.session_state.inr_to_usd = st.number_input(
        "1 USD = ? INR",
        min_value=50.0, max_value=120.0,
        value=float(st.session_state.get("inr_to_usd", 86.0)),
        step=0.5,
        help="Used for the dashboard's recomputed USD figures.",
    )
    st.caption(f"Current: 1 USD = ₹{st.session_state.inr_to_usd:.2f}")

    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()


# ============ HELPER FUNCTIONS ============
@st.cache_data(show_spinner=False)
def load_latest_report(file_path: str, mtime: float):
    """Load the latest report Excel as DataFrames (Growth Comparison & High Growth)."""
    growth = pd.read_excel(file_path, sheet_name="Growth Comparison")
    try:
        hg = pd.read_excel(file_path, sheet_name="High Growth 5K-50K USD")
    except Exception:
        hg = pd.DataFrame()
    try:
        summary = pd.read_excel(file_path, sheet_name="Summary")
    except Exception:
        summary = pd.DataFrame()
    return growth, hg, summary


def latest_report_path() -> Path | None:
    reports_dir = Path("generated_reports")
    if not reports_dir.exists():
        return None
    reports = sorted(
        reports_dir.glob("Client_Growth_Report_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return reports[0] if reports else None


def fmt_money(n: float) -> str:
    """Format a number as $X.XM / $X.XK / $X."""
    n = float(n or 0)
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:,.0f}"


def kpi_card(title: str, value: str, sub: str = "", color: str = "info"):
    return f"""<div class="kpi-card kpi-{color}">
        <h3>{title}</h3>
        <div class="value">{value}</div>
        <div class="sub">{sub}</div>
    </div>"""


# ============ LATEST REPORT VIEW ============
report = latest_report_path()

if report is None:
    # No report yet -- show instructions only
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
    st.info("ℹ️ No reports generated yet. Run `run_monthly.py` locally first.")
else:
    # We have a report -- show the rich dashboard
    growth, hg, summary = load_latest_report(str(report), report.stat().st_mtime)

    ts = datetime.fromtimestamp(report.stat().st_mtime)
    st.markdown(f"### 📅 Latest Report: `{report.name}`")
    st.caption(f"Generated: **{ts:%Y-%m-%d %H:%M:%S}** &nbsp;•&nbsp; "
               f"Size: {report.stat().st_size/1024/1024:.1f} MB &nbsp;•&nbsp; "
               f"{len(growth):,} clients analyzed")

    # ---------- KPI cards ----------
    total_clients = len(growth)
    high_growth   = len(hg)
    total_growth  = growth["Growth_USD"].sum() if "Growth_USD" in growth.columns else 0
    avg_growth_pct = growth["Growth_%"].mean() if "Growth_%" in growth.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            kpi_card("Total Clients", f"{total_clients:,}",
                     "across all 12-month data", "info"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_card("High-Growth", f"{high_growth}",
                     "Prev ≤ $5K → Curr ≥ $50K", "good"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_card("Total Growth", fmt_money(total_growth),
                     "USD, all clients combined", "purple"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            kpi_card("Avg Growth %", f"{avg_growth_pct:.1f}%",
                     "mean across clients", "warn"),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ---------- Two columns: Top 10 chart  ::  Distribution pie ----------
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown("### 📈 Top 10 Growth Clients (USD)")
        if "Growth_USD" in growth.columns and len(growth):
            top10 = (growth.sort_values("Growth_USD", ascending=False)
                            .head(10)
                            [["CompanyName", "Growth_USD"]])
            # Use a horizontal bar chart -- nicest in Streamlit
            chart_df = top10.set_index("CompanyName")
            st.bar_chart(chart_df, horizontal=True, height=400)
        else:
            st.info("Growth_USD column missing -- skipping chart.")

    with c2:
        st.markdown("### 🥧 Growth Tiers")
        if "Growth_USD" in growth.columns and len(growth):
            tiers = pd.cut(
                growth["Growth_USD"],
                bins=[-1e15, 0, 5_000, 50_000, 250_000, 1e15],
                labels=["Declining (<0)",
                        "Flat ($0-$5K)",
                        "Growing ($5K-$50K)",
                        "Strong ($50K-$250K)",
                        "Star (>$250K)"],
            )
            tier_counts = tiers.value_counts().reset_index()
            tier_counts.columns = ["Tier", "Count"]
            # Streamlit doesn't have native pie, but we can use plotly if avail
            try:
                import plotly.express as px
                fig = px.pie(
                    tier_counts, names="Tier", values="Count",
                    color="Tier",
                    color_discrete_map={
                        "Declining (<0)":      "#ef5350",
                        "Flat ($0-$5K)":       "#bdbdbd",
                        "Growing ($5K-$50K)":  "#42a5f5",
                        "Strong ($50K-$250K)": "#66bb6a",
                        "Star (>$250K)":       "#ffa726",
                    },
                    hole=0.4,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(showlegend=True, height=400, margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                # Fallback: just show counts as a table
                st.table(tier_counts)

    st.markdown("---")

    # ---------- High-growth table ----------
    st.markdown("### 🚀 High-Growth Clients (Prev ≤ $5K → Curr ≥ $50K)")
    if len(hg) > 0:
        display_cols = [c for c in
            ["CompanyName", "UserName", "Previous_12M_USD",
             "Current_12M_USD", "Growth_USD", "Growth_%", "URL"]
            if c in hg.columns]
        st.dataframe(
            hg[display_cols].sort_values(
                "Growth_USD" if "Growth_USD" in hg.columns else display_cols[0],
                ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Previous_12M_USD": st.column_config.NumberColumn(
                    "Previous 12M", format="$%d"),
                "Current_12M_USD":  st.column_config.NumberColumn(
                    "Current 12M",  format="$%d"),
                "Growth_USD":       st.column_config.NumberColumn(
                    "Growth USD",   format="$%d"),
                "Growth_%":         st.column_config.NumberColumn(
                    "Growth %",     format="%.1f%%"),
                "URL":              st.column_config.LinkColumn("URL"),
            },
        )
    else:
        st.info("No high-growth clients in this report.")

    st.markdown("---")

    # ---------- Full Growth Comparison (collapsed) ----------
    with st.expander(f"📋 Full Growth Comparison ({len(growth):,} rows)", expanded=False):
        display_cols = [c for c in
            ["CompanyName", "UserName", "CorporateID",
             "Previous_12M_USD", "Current_12M_USD", "Growth_USD", "Growth_%"]
            if c in growth.columns]
        st.dataframe(
            growth[display_cols].sort_values(
                "Growth_USD" if "Growth_USD" in growth.columns else display_cols[0],
                ascending=False
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Previous_12M_USD": st.column_config.NumberColumn(
                    "Previous 12M", format="$%d"),
                "Current_12M_USD":  st.column_config.NumberColumn(
                    "Current 12M",  format="$%d"),
                "Growth_USD":       st.column_config.NumberColumn(
                    "Growth USD",   format="$%d"),
                "Growth_%":         st.column_config.NumberColumn(
                    "Growth %",     format="%.1f%%"),
            },
        )

    # ---------- Download buttons ----------
    st.markdown("### 📥 Downloads")
    with open(report, "rb") as f:
        st.download_button(
            f"📥 Download Latest Excel Report ({report.name})",
            f, report.name,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ============ REPORT HISTORY ============
st.markdown("---")
st.markdown("## 📚 Report History")
reports_dir = Path("generated_reports")
if reports_dir.exists():
    all_reports = sorted(
        reports_dir.glob("Client_Growth_Report_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if len(all_reports) > 1:
        with st.expander(f"Show all {len(all_reports)} reports", expanded=False):
            for r in all_reports[1:]:
                rts = datetime.fromtimestamp(r.stat().st_mtime)
                rmb = r.stat().st_size / 1024 / 1024
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f"`{r.name}` &nbsp;•&nbsp; "
                        f"{rts:%Y-%m-%d %H:%M} &nbsp;•&nbsp; {rmb:.1f} MB"
                    )
                with col2:
                    with open(r, "rb") as f:
                        st.download_button(
                            "📥", f, r.name,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{r.name}",
                        )
    elif len(all_reports) == 1:
        st.caption("Only one report so far — it's shown above.")
    else:
        st.caption("No history yet.")
else:
    st.caption("No reports folder yet.")


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
    "Client Growth Report v5.2 (Visual Edition) | © 2025 Koenig Solutions"
    "</div>",
    unsafe_allow_html=True,
)
