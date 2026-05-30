"""Client Growth Report Dashboard v5.2 - Visual Edition."""

import os
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


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
</style>
""",
    unsafe_allow_html=True,
)


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
                p = st.text_input("Password", type="password", placeholder="admin123")
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
            n2 = st.text_input("Confirm", type="password", key="np2")
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


st.title("📊 Client Growth Report")
st.markdown("**Powered by Koenig Solutions**")
st.markdown("---")

with st.sidebar:
    if Path("assets/koenig_logo.png").exists():
        st.image("assets/koenig_logo.png", width=200)
    st.markdown("### About")
    st.info(
        "**High Growth Filter**\n\n- Previous <= $5,000\n- Current >= $50,000\n\n"
        "**Output**: 4 Excel sheets\n1. Growth Comparison\n2. High Growth 5K-50K\n"
        "3. Summary\n4. Exceptions"
    )
    st.markdown("---")
    st.markdown("### Schedule")
    st.success(
        "🗓️ **Monthly Run: 14th of each month**\n\n"
        "Run `run_monthly.py` locally on your laptop."
    )
    st.markdown("---")
    st.markdown("### 💱 Exchange Rate")
    st.session_state.inr_to_usd = st.number_input(
        "1 USD = ? INR", min_value=50.0, max_value=120.0,
        value=float(st.session_state.get("inr_to_usd", 86.0)),
        step=0.5,
    )
    st.caption(f"Current: 1 USD = INR {st.session_state.inr_to_usd:.2f}")
    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()


@st.cache_data(show_spinner=False)
def load_latest_report(file_path: str, mtime: float):
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


def latest_report_path():
    reports_dir = Path("generated_reports")
    if not reports_dir.exists():
        return None
    reports = sorted(
        reports_dir.glob("Client_Growth_Report_*.xlsx"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    return reports[0] if reports else None


def fmt_money(n):
    n = float(n or 0)
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:,.0f}"


def kpi_card(title, value, sub="", color="info"):
    return f"""<div class="kpi-card kpi-{color}">
<h3>{title}</h3>
<div class="value">{value}</div>
<div class="sub">{sub}</div>
</div>"""


report = latest_report_path()

if report is None:
    st.markdown("## ▶️ How to Run the Monthly Report")
    st.markdown(
        """<div class='run-instructions'>
Because RMS2 now requires OTP on every login, the report must be triggered
from your local computer. See <code>HOW_TO_RUN.md</code> for instructions.
</div>""",
        unsafe_allow_html=True,
    )
    st.info("No reports yet. Run the monthly job locally to populate this dashboard.")
else:
    growth, hg, summary = load_latest_report(str(report), report.stat().st_mtime)

    ts = datetime.fromtimestamp(report.stat().st_mtime)
    st.markdown(f"### 📅 Latest Report: `{report.name}`")
    st.caption(
        f"Generated: **{ts:%Y-%m-%d %H:%M:%S}** | "
        f"{report.stat().st_size/1024/1024:.1f} MB | "
        f"{len(growth):,} clients analyzed"
    )

    total_clients = len(growth)
    high_growth = len(hg)
    total_growth = growth["Growth_USD"].sum() if "Growth_USD" in growth.columns else 0
    avg_growth_pct = growth["Growth_%"].mean() if "Growth_%" in growth.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(kpi_card("Total Clients", f"{total_clients:,}",
                             "across all 12-month data", "info"),
                    unsafe_allow_html=True)
    with k2:
        st.markdown(kpi_card("High-Growth", f"{high_growth}",
                             "Prev <= $5K, Curr >= $50K", "good"),
                    unsafe_allow_html=True)
    with k3:
        st.markdown(kpi_card("Total Growth", fmt_money(total_growth),
                             "USD, all clients combined", "purple"),
                    unsafe_allow_html=True)
    with k4:
        st.markdown(kpi_card("Avg Growth %", f"{avg_growth_pct:.1f}%",
                             "mean across clients", "warn"),
                    unsafe_allow_html=True)

    st.markdown("---")

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("### 📈 Top 10 Growth Clients (USD)")
        if "Growth_USD" in growth.columns and len(growth):
            top10 = (growth.sort_values("Growth_USD", ascending=False)
                     .head(10)[["CompanyName", "Growth_USD"]])
            st.bar_chart(top10.set_index("CompanyName"),
                         horizontal=True, height=400)
        else:
            st.info("Growth_USD column missing.")

    with c2:
        st.markdown("### 🥧 Growth Tiers")
        if "Growth_USD" in growth.columns and len(growth):
            tiers = pd.cut(
                growth["Growth_USD"],
                bins=[-1e15, 0, 5_000, 50_000, 250_000, 1e15],
                labels=["Declining (<0)", "Flat ($0-$5K)",
                        "Growing ($5K-$50K)", "Strong ($50K-$250K)",
                        "Star (>$250K)"],
            )
            tier_counts = tiers.value_counts().reset_index()
            tier_counts.columns = ["Tier", "Count"]
            try:
                import plotly.express as px
                fig = px.pie(
                    tier_counts, names="Tier", values="Count", color="Tier",
                    color_discrete_map={
                        "Declining (<0)": "#ef5350", "Flat ($0-$5K)": "#bdbdbd",
                        "Growing ($5K-$50K)": "#42a5f5",
                        "Strong ($50K-$250K)": "#66bb6a",
                        "Star (>$250K)": "#ffa726",
                    },
                    hole=0.4,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(showlegend=True, height=400,
                                  margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.table(tier_counts)

    st.markdown("---")

    st.markdown("### 🚀 High-Growth Clients (Prev <= $5K, Curr >= $50K)")
    if len(hg) > 0:
        cols = [c for c in
                ["CompanyName", "UserName", "Previous_12M_USD",
                 "Current_12M_USD", "Growth_USD", "Growth_%", "URL"]
                if c in hg.columns]
        st.dataframe(
            hg[cols].sort_values(
                "Growth_USD" if "Growth_USD" in hg.columns else cols[0],
                ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "Previous_12M_USD": st.column_config.NumberColumn(
                    "Previous 12M", format="$%d"),
                "Current_12M_USD": st.column_config.NumberColumn(
                    "Current 12M", format="$%d"),
                "Growth_USD": st.column_config.NumberColumn(
                    "Growth USD", format="$%d"),
                "Growth_%": st.column_config.NumberColumn(
                    "Growth %", format="%.1f%%"),
                "URL": st.column_config.LinkColumn("URL"),
            },
        )
    else:
        st.info("No high-growth clients in this report.")

    st.markdown("---")

    with st.expander(f"📋 Full Growth Comparison ({len(growth):,} rows)",
                     expanded=False):
        cols = [c for c in
                ["CompanyName", "UserName", "CorporateID",
                 "Previous_12M_USD", "Current_12M_USD", "Growth_USD", "Growth_%"]
                if c in growth.columns]
        st.dataframe(
            growth[cols].sort_values(
                "Growth_USD" if "Growth_USD" in growth.columns else cols[0],
                ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "Previous_12M_USD": st.column_config.NumberColumn(
                    "Previous 12M", format="$%d"),
                "Current_12M_USD": st.column_config.NumberColumn(
                    "Current 12M", format="$%d"),
                "Growth_USD": st.column_config.NumberColumn(
                    "Growth USD", format="$%d"),
                "Growth_%": st.column_config.NumberColumn(
                    "Growth %", format="%.1f%%"),
            },
        )

    st.markdown("### 📥 Downloads")
    with open(report, "rb") as f:
        st.download_button(
            f"📥 Download Latest Excel Report ({report.name})",
            f, report.name,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


st.markdown("---")
st.markdown("## 📚 Report History")
reports_dir = Path("generated_reports")
if reports_dir.exists():
    all_reports = sorted(
        reports_dir.glob("Client_Growth_Report_*.xlsx"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if len(all_reports) > 1:
        with st.expander(f"Show all {len(all_reports)} reports", expanded=False):
            for r in all_reports[1:]:
                rts = datetime.fromtimestamp(r.stat().st_mtime)
                rmb = r.stat().st_size / 1024 / 1024
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f"`{r.name}` | {rts:%Y-%m-%d %H:%M} | {rmb:.1f} MB"
                    )
                with col2:
                    with open(r, "rb") as f:
                        st.download_button(
                            "📥", f, r.name,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{r.name}",
                        )


st.markdown("---")
st.markdown("## 📦 Raw Data Files")
f24 = Path("data/RCB_24months.xlsx")
f12 = Path("data/RCB_12months.xlsx")
c1, c2 = st.columns(2)
with c1:
    if f24.exists():
        u = datetime.fromtimestamp(f24.stat().st_mtime)
        st.success(
            f"**24M data**\n\n"
            f"{f24.stat().st_size/1024/1024:.1f} MB\n\n"
            f"Updated: {u:%Y-%m-%d %H:%M}"
        )
    else:
        st.warning("RCB_24months.xlsx not in data/")
with c2:
    if f12.exists():
        u = datetime.fromtimestamp(f12.stat().st_mtime)
        st.success(
            f"**12M data**\n\n"
            f"{f12.stat().st_size/1024/1024:.1f} MB\n\n"
            f"Updated: {u:%Y-%m-%d %H:%M}"
        )
    else:
        st.warning("RCB_12months.xlsx not in data/")


st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size:0.9rem; color:grey;'>"
    "Client Growth Report v5.2 (Visual Edition) | © 2025 Koenig Solutions"
    "</div>",
    unsafe_allow_html=True,
)
