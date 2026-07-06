import os
import sys
import json
import time
import signal
import platform
import subprocess
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = APP_DIR / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True)

STATUS_FILE = RUNTIME_DIR / "run_status.json"
PID_FILE = RUNTIME_DIR / "run_monthly.pid"
LOG_FILE = RUNTIME_DIR / "run_monthly.log"

REPORTS_DIR = APP_DIR / "generated_reports"
DATA_DIR = APP_DIR / "data"


# ---------------------------
# Helpers
# ---------------------------
def read_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "state": "idle",
        "message": "No run started yet.",
        "started_at": None,
        "updated_at": None,
        "report_path": None,
        "error": None,
    }


def read_log_tail(lines: int = 80) -> str:
    if not LOG_FILE.exists():
        return ""
    try:
        content = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(content[-lines:])
    except Exception:
        return ""


def pid_alive(pid: int) -> bool:
    try:
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def get_running_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        if pid_alive(pid):
            return pid
    except Exception:
        pass
    return None


def is_run_active() -> bool:
    return get_running_pid() is not None


def build_runner_env() -> dict:
    env = os.environ.copy()

    secret_keys = [
        "RMS_USERNAME",
        "RMS_PASSWORD",
        "SMTP_EMAIL",
        "SMTP_PASSWORD",
        "SMTP_SERVER",
        "SMTP_PORT",
        "REPORT_RECIPIENTS",
        "AUTO_GIT_COMMIT",
        "INR_TO_USD",
    ]

    for key in secret_keys:
        if key in st.secrets and str(st.secrets[key]).strip():
            env[key] = str(st.secrets[key]).strip()

    env["PYTHONUNBUFFERED"] = "1"
    return env


def validate_required_secrets(env: dict) -> list[str]:
    missing = []
    for key in ["RMS_USERNAME", "RMS_PASSWORD"]:
        if not env.get(key, "").strip():
            missing.append(key)
    return missing


def start_local_run() -> tuple[bool, str]:
    if is_run_active():
        return False, "A run is already in progress."

    env = build_runner_env()
    missing = validate_required_secrets(env)
    if missing:
        return False, f"Missing required secrets: {', '.join(missing)}"

    runner = APP_DIR / "run_monthly.py"
    if not runner.exists():
        return False, "run_monthly.py not found."

    with open(LOG_FILE, "a", encoding="utf-8") as log_fp:
        if platform.system() == "Windows":
            creationflags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW
            )
            proc = subprocess.Popen(
                [sys.executable, str(runner)],
                cwd=str(APP_DIR),
                env=env,
                stdout=log_fp,
                stderr=log_fp,
                creationflags=creationflags,
                shell=False,
            )
        else:
            proc = subprocess.Popen(
                [sys.executable, str(runner)],
                cwd=str(APP_DIR),
                env=env,
                stdout=log_fp,
                stderr=log_fp,
                start_new_session=True,
                shell=False,
            )

    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    return True, f"Run started successfully. PID={proc.pid}"


def stop_local_run() -> tuple[bool, str]:
    pid = get_running_pid()
    if not pid:
        return False, "No active run found."

    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            os.kill(pid, signal.SIGTERM)

        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass

        return True, "Run stop requested."
    except Exception as e:
        return False, f"Failed to stop run: {e}"


def latest_report_path() -> Path | None:
    if not REPORTS_DIR.exists():
        return None
    reports = sorted(
        REPORTS_DIR.glob("Client_Growth_Report_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return reports[0] if reports else None


@st.cache_data(show_spinner=False)
def load_report_sheets(path: str, mtime: float):
    growth = pd.read_excel(path, sheet_name="Growth Comparison")
    try:
        hg = pd.read_excel(path, sheet_name="High Growth 5K-50K USD")
    except Exception:
        hg = pd.DataFrame()
    try:
        summary = pd.read_excel(path, sheet_name="Summary")
    except Exception:
        summary = pd.DataFrame()
    return growth, hg, summary


def fmt_money(n) -> str:
    try:
        n = float(n or 0)
    except Exception:
        n = 0
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:,.0f}"


# ---------------------------
# UI
# ---------------------------
st.set_page_config(
    page_title="Client Growth Report",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Client Growth Report")
st.caption("Local runner mode: Click Run Now → browser opens → enter OTP → report completes automatically")

status = read_status()
active = is_run_active()

left, right = st.columns([2, 1])

with left:
    st.subheader("Run Control")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶ Run Now", use_container_width=True, type="primary", disabled=active):
            ok, msg = start_local_run()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with c2:
        if st.button("■ Stop Run", use_container_width=True, disabled=not active):
            ok, msg = stop_local_run()
            if ok:
                st.warning(msg)
                st.rerun()
            else:
                st.error(msg)

    state = status.get("state", "idle")
    message = status.get("message", "")
    updated_at = status.get("updated_at", "")
    error = status.get("error")

    if state in {"opening_browser", "filling_credentials", "waiting_for_user_otp", "authenticated", "downloading_24m", "downloading_12m", "processing_report", "sending_email", "git_commit"}:
        st.info(f"**Status:** {state}\n\n{message}")
    elif state == "done":
        st.success(f"**Status:** done\n\n{message}")
    elif state == "error":
        st.error(f"**Status:** error\n\n{message}\n\n{error or ''}")
    else:
        st.write(f"**Status:** {state}")
        st.write(message)

    if updated_at:
        st.caption(f"Last update: {updated_at}")

    if active:
        st.markdown(
            """
            <script>
            setTimeout(function() {
                window.location.reload();
            }, 3000);
            </script>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Auto-refreshing every 3 seconds while the run is active.")

with right:
    st.subheader("Credentials Check")
    env_preview = build_runner_env()
    if env_preview.get("RMS_USERNAME") and env_preview.get("RMS_PASSWORD"):
        st.success("RMS credentials available")
    else:
        st.error("RMS credentials missing")

    if env_preview.get("SMTP_EMAIL") and env_preview.get("SMTP_PASSWORD"):
        st.success("SMTP configured")
    else:
        st.warning("SMTP not configured")

st.markdown("---")

with st.expander("Runtime log", expanded=False):
    log_tail = read_log_tail()
    st.code(log_tail or "No log yet.", language="text")

st.markdown("---")

report = latest_report_path()

if report is None:
    st.info("No generated report found yet. Run the process once.")
else:
    growth, hg, summary = load_report_sheets(str(report), report.stat().st_mtime)
    ts = datetime.fromtimestamp(report.stat().st_mtime)

    st.subheader("Latest Report")
    st.caption(f"{report.name} • {ts:%Y-%m-%d %H:%M:%S}")

    k1, k2, k3, k4 = st.columns(4)
    total_clients = len(growth)
    high_growth = len(hg)
    total_growth = growth["Growth_USD"].sum() if "Growth_USD" in growth.columns else 0
    avg_growth_pct = growth["Growth_%"].mean() if "Growth_%" in growth.columns else 0

    k1.metric("Total Clients", f"{total_clients:,}")
    k2.metric("High Growth", f"{high_growth:,}")
    k3.metric("Total Growth", fmt_money(total_growth))
    k4.metric("Avg Growth %", f"{avg_growth_pct:.1f}%")

    st.markdown("### High-Growth Clients")
    if len(hg) > 0:
        cols = [c for c in [
            "CompanyName", "UserName", "Previous_12M_USD",
            "Current_12M_USD", "Growth_USD", "Growth_%", "URL"
        ] if c in hg.columns]
        st.dataframe(hg[cols], use_container_width=True, hide_index=True)
    else:
        st.info("No high-growth clients in latest report.")

    st.markdown("### Full Growth Comparison")
    cols = [c for c in [
        "CompanyName", "UserName", "CorporateID",
        "Previous_12M_USD", "Current_12M_USD", "Growth_USD", "Growth_%"
    ] if c in growth.columns]
    st.dataframe(growth[cols], use_container_width=True, hide_index=True)

    with open(report, "rb") as f:
        st.download_button(
            "Download Latest Report",
            f,
            file_name=report.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

st.markdown("---")

st.subheader("Report History")
if REPORTS_DIR.exists():
    reports = sorted(
        REPORTS_DIR.glob("Client_Growth_Report_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if reports:
        for rep in reports:
            c1, c2 = st.columns([4, 1])
            with c1:
                rep_ts = datetime.fromtimestamp(rep.stat().st_mtime)
                st.write(f"{rep.name} • {rep_ts:%Y-%m-%d %H:%M:%S}")
            with c2:
                with open(rep, "rb") as f:
                    st.download_button(
                        "Download",
                        f,
                        file_name=rep.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{rep.name}",
                    )
    else:
        st.caption("No reports yet.")
else:
    st.caption("generated_reports folder not found yet.")
