"""
run_monthly.py  --  End-to-end monthly runner

This is the script the local launcher (.bat / .sh) executes.
Does EVERYTHING in one shot:

  1. Opens a visible Chromium window pointed at RMS2
  2. Auto-fills email + password from .env / env vars
  3. Waits for the USER to enter the OTP in the visible window
  4. Once authenticated, navigates to RCB and downloads 24M + 12M files
  5. Closes the browser
  6. Runs process_report.py to build the 4-sheet Excel report
  7. Sends the report by email (if SMTP credentials configured)
  8. Optionally git-commits the new data + report so Streamlit Cloud sees it

Credentials come from EITHER:
  - .env file in the repo root (preferred for local use)
  - environment variables (preferred for CI / scripted runs)

Required env vars:
  RMS_USERNAME, RMS_PASSWORD

Optional env vars (for email + auto-commit):
  SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER (default smtp.office365.com),
  SMTP_PORT (default 587), REPORT_RECIPIENTS (comma-separated emails),
  AUTO_GIT_COMMIT (set to "1" to auto-commit + push after a successful run)
"""

import os
import sys
import smtplib
import subprocess
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


# ----- Load .env if present -----
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def banner(title):
    line = "=" * 70
    print(f"\n{line}\n  {title}\n{line}\n")


def fail(msg, code=1):
    print(f"\n❌ ERROR: {msg}\n")
    sys.exit(code)


def send_email(report_path, recipients):
    """Send the report via Outlook SMTP (Office 365)."""
    sender    = os.environ.get("SMTP_EMAIL", "").strip()
    sender_pw = os.environ.get("SMTP_PASSWORD", "").strip()
    server_h  = os.environ.get("SMTP_SERVER", "smtp.office365.com").strip()
    port      = int(os.environ.get("SMTP_PORT", "587"))

    if not sender or not sender_pw:
        print("⚠️  SMTP credentials not set, skipping email send")
        return False
    if not recipients:
        print("⚠️  No recipients configured, skipping email send")
        return False

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"Client Growth Report - {datetime.now():%Y-%m-%d}"
    body = (
        f"Hi Team,\n\n"
        f"Please find attached the Client Growth Report generated on "
        f"{datetime.now():%Y-%m-%d %H:%M:%S}.\n\n"
        "Report Summary:\n"
        "- Data Period: Previous 12M vs Current 12M\n"
        "- Exchange Rate: 1 USD = 86 INR\n"
        "- High Growth Filter: Previous <= $5K, Current >= $50K\n\n"
        "Sheets included:\n"
        "  1. Growth Comparison (all clients)\n"
        "  2. High Growth 5K-50K (filtered)\n"
        "  3. Summary (statistics)\n"
        "  4. Exceptions (if any)\n\n"
        "Best regards,\n"
        "Koenig Solutions Automated Report System"
    )
    msg.attach(MIMEText(body, "plain"))

    with open(report_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",
                    f"attachment; filename={Path(report_path).name}")
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
        print(f"⚠️  Email send failed: {e}")
        return False


def git_auto_commit(report_path):
    """Optionally commit + push the new data and report so Streamlit Cloud
    sees the latest files."""
    if os.environ.get("AUTO_GIT_COMMIT", "").lower() not in ("1", "true", "yes"):
        return
    try:
        subprocess.run(["git", "add",
                        "data/RCB_24months.xlsx",
                        "data/RCB_12months.xlsx",
                        str(report_path)],
                       check=False)
        msg = f"Auto-update report {datetime.now():%Y-%m-%d %H:%M}"
        r = subprocess.run(["git", "commit", "-m", msg], capture_output=True)
        if r.returncode == 0:
            subprocess.run(["git", "push"], check=False)
            print("✅ Files committed and pushed to git")
        else:
            print("(nothing new to commit)")
    except Exception as e:
        print(f"⚠️  git auto-commit failed: {e}")


def main():
    banner("CLIENT GROWTH REPORT - Monthly Run")
    print(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")

    # ----- Validate credentials -----
    rms_user = os.environ.get("RMS_USERNAME", "").strip()
    rms_pass = os.environ.get("RMS_PASSWORD", "").strip()
    if not rms_user or not rms_pass:
        fail(
            "RMS_USERNAME / RMS_PASSWORD not set.\n"
            "  Either:\n"
            "    1) Create a .env file (copy .env.example -> .env), OR\n"
            "    2) Set them as environment variables before running."
        )
    print(f"✅ RMS2 user: {rms_user}")

    # ----- Step 1: Download from RMS2 -----
    banner("STEP 1 / 3   Open Chromium and download RMS2 data")
    print("A Chromium window will open shortly.")
    print("Auto-filling email + password, then waiting for you to enter OTP.\n")

    try:
        from rms2_downloader_local import RMS2LocalSession
    except ImportError as e:
        fail(f"Could not import rms2_downloader_local: {e}\n"
             "  Run: pip install -r requirements.txt\n"
             "       python -m playwright install chromium")

    session = RMS2LocalSession(rms_user, rms_pass, data_dir="data")
    session.start()

    # Wait for the worker thread to reach DONE or ERROR
    import time
    last_state = None
    while True:
        if session.state != last_state:
            print(f"   [state: {session.state}] {session.message}")
            last_state = session.state
        if session.state == "done":
            break
        if session.state == "error":
            fail(f"Download failed: {session.error}")
        time.sleep(2)

    if not (session.file_24m and session.file_24m.exists()
            and session.file_12m and session.file_12m.exists()):
        fail("Downloads claimed success but files are missing.")
    print(f"✅ 24M: {session.file_24m}")
    print(f"✅ 12M: {session.file_12m}")

    # ----- Step 2: Generate the report -----
    banner("STEP 2 / 3   Build the growth report")
    try:
        import pandas as pd
        from process_report import process_growth_report
        df24 = pd.read_excel(session.file_24m)
        df12 = pd.read_excel(session.file_12m)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("generated_reports"); out_dir.mkdir(exist_ok=True)
        report_path = out_dir / f"Client_Growth_Report_{ts}.xlsx"
        result = process_growth_report(df24, df12, str(report_path))
    except Exception as e:
        fail(f"Report build failed: {e}")

    print(f"✅ Report: {report_path}")
    print(f"   Total clients: {result.get('total_clients', '?')}")
    print(f"   High-growth:   {result.get('high_growth_clients', '?')}")
    print(f"   Top performer: {result.get('top_performer', '?')}")

    # ----- Step 3: Email + (optional) git commit -----
    banner("STEP 3 / 3   Email + commit")
    recipients = [r.strip()
                  for r in os.environ.get("REPORT_RECIPIENTS", "").split(",")
                  if r.strip()]
    send_email(report_path, recipients)
    git_auto_commit(report_path)

    banner("🎉 ALL DONE")
    print(f"Report saved to: {report_path}")
    print(f"Finished: {datetime.now():%Y-%m-%d %H:%M:%S}\n")


if __name__ == "__main__":
    main()
