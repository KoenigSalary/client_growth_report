#!/usr/bin/env python3

import os
import sys
import json
import time
import atexit
import smtplib
import subprocess
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


APP_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = APP_DIR / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True)

STATUS_FILE = RUNTIME_DIR / "run_status.json"
PID_FILE = RUNTIME_DIR / "run_monthly.pid"


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_status(state: str, message: str, **extra):
    payload = {
        "state": state,
        "message": message,
        "updated_at": now_str(),
        "error": None,
        "report_path": None,
    }
    if STATUS_FILE.exists():
        try:
            old = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            if old.get("started_at"):
                payload["started_at"] = old["started_at"]
        except Exception:
            pass

    payload.setdefault("started_at", now_str())
    payload.update(extra)
    STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fail(msg, code=1):
    write_status("error", msg, error=msg)
    print(f"\n❌ ERROR: {msg}\n")
    sys.exit(code)


def cleanup():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


atexit.register(cleanup)


def send_email(report_path, recipients):
    sender = os.environ.get("SMTP_EMAIL", "").strip()
    sender_pw = os.environ.get("SMTP_PASSWORD", "").strip()
    server_h = os.environ.get("SMTP_SERVER", "smtp.office365.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))

    if not sender or not sender_pw:
        print("⚠️ SMTP credentials not set, skipping email send")
        return False
    if not recipients:
        print("⚠️ No recipients configured, skipping email send")
        return False

    write_status("sending_email", "Sending report email...")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"Client Growth Report - {datetime.now():%Y-%m-%d}"

    body = (
        f"Hi Team,\n\n"
        f"Please find attached the Client Growth Report generated on "
        f"{datetime.now():%Y-%m-%d %H:%M:%S}.\n\n"
        "Best regards,\n"
        "Automated Report System"
    )
    msg.attach(MIMEText(body, "plain"))

    with open(report_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={Path(report_path).name}")
    msg.attach(part)

    try:
        s = smtplib.SMTP(server_h, port)
        s.starttls()
        s.login(sender, sender_pw)
        s.sendmail(sender, recipients, msg.as_string())
        s.quit()
        print(f"📧 Email sent to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        print(f"⚠️ Email send failed: {e}")
        return False


def git_auto_commit(report_path):
    if os.environ.get("AUTO_GIT_COMMIT", "").lower() not in ("1", "true", "yes"):
        return

    write_status("git_commit", "Committing generated files to git...")

    try:
        subprocess.run(
            [
                "git", "add",
                "data/RCB_24months.xlsx",
                "data/RCB_12months.xlsx",
                str(report_path)
            ],
            check=False,
        )
        msg = f"Auto-update report {datetime.now():%Y-%m-%d %H:%M}"
        r = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)

        if r.returncode == 0:
            subprocess.run(["git", "push"], check=False)
            print("✅ Files committed and pushed to git")
        else:
            print("(nothing new to commit)")
    except Exception as e:
        print(f"⚠️ git auto-commit failed: {e}")


def main():
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    write_status("starting", "Runner started...")

    rms_user = os.environ.get("RMS_USERNAME", "").strip()
    rms_pass = os.environ.get("RMS_PASSWORD", "").strip()

    if not rms_user or not rms_pass:
        fail("RMS_USERNAME / RMS_PASSWORD not set.")

    try:
        from rms2_downloader_local import RMS2LocalSession
    except ImportError as e:
        fail(
            f"Could not import rms2_downloader_local: {e}. "
            f"Run: pip install -r requirements.txt && python -m playwright install chromium"
        )

    write_status("opening_browser", "Opening Chromium browser window...")
    session = RMS2LocalSession(rms_user, rms_pass, data_dir="data")
    session.start()

    last_state = None
    while True:
        if session.state != last_state:
            last_state = session.state
            write_status(session.state, session.message)

        if session.state == "done":
            break
        if session.state == "error":
            fail(f"Download failed: {session.error}")

        time.sleep(2)

    if not (session.file_24m and session.file_24m.exists() and session.file_12m and session.file_12m.exists()):
        fail("Downloads claimed success but files are missing.")

    write_status(
        "processing_report",
        "Downloads complete. Building report...",
    )

    try:
        import pandas as pd
        from process_report import process_growth_report

        df24 = pd.read_excel(session.file_24m)
        df12 = pd.read_excel(session.file_12m)

        out_dir = APP_DIR / "generated_reports"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = out_dir / f"Client_Growth_Report_{ts}.xlsx"

        rate = float(os.environ.get("INR_TO_USD", "86"))
        result = process_growth_report(df24, df12, str(report_path), inr_to_usd=rate)

    except Exception as e:
        fail(f"Report build failed: {e}")

    recipients = [
        r.strip()
        for r in os.environ.get("REPORT_RECIPIENTS", "").split(",")
        if r.strip()
    ]

    send_email(report_path, recipients)
    git_auto_commit(report_path)

    write_status(
        "done",
        "Run completed successfully.",
        report_path=str(report_path),
        result=result,
    )
    print(f"✅ Report saved to: {report_path}")


if __name__ == "__main__":
    main()
