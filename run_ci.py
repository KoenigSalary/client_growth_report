"""
run_ci.py  --  CI/CD Report Runner (GitHub Actions)

Expects data files to already exist in data/ (downloaded by download_rms2_data.py).
Does two things:
  1. Generates the 4-sheet Excel report via process_report.py
  2. Emails the report via Office 365 SMTP

Required env vars (set as GitHub Secrets):
  SMTP_EMAIL          - sender address (your Office 365 / Outlook account)
  SMTP_PASSWORD       - app password or account password
  REPORT_RECIPIENTS   - comma-separated list of recipient email addresses

Optional env vars:
  SMTP_SERVER         - default: smtp.office365.com
  SMTP_PORT           - default: 587
  INR_TO_USD          - exchange rate, default: 86.0
"""

import os
import sys
import smtplib
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


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def fail(msg: str, code: int = 1):
    print(f"\n❌ ERROR: {msg}\n", file=sys.stderr, flush=True)
    sys.exit(code)


# ── Step 1: Verify source data files ──────────────────────────────────────────
def check_data_files():
    f24 = Path("data/RCB_24months.xlsx")
    f12 = Path("data/RCB_12months.xlsx")
    if not f24.exists():
        fail(f"data/RCB_24months.xlsx not found. Run download_rms2_data.py first.")
    if not f12.exists():
        fail(f"data/RCB_12months.xlsx not found. Run download_rms2_data.py first.")
    log(f"✅ 24M data: {f24} ({f24.stat().st_size/1024:.1f} KB)")
    log(f"✅ 12M data: {f12} ({f12.stat().st_size/1024:.1f} KB)")
    return f24, f12


# ── Step 2: Generate the Excel report ─────────────────────────────────────────
def generate_report(f24: Path, f12: Path) -> Path:
    log("Generating Excel report...")
    try:
        import pandas as pd
        from process_report import process_growth_report
    except ImportError as e:
        fail(f"Import error: {e}\nMake sure pandas, openpyxl, and process_report.py are available.")

    df24 = pd.read_excel(f24)
    df12 = pd.read_excel(f12)

    out_dir = Path("generated_reports")
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = out_dir / f"Client_Growth_Report_{ts}.xlsx"

    rate = float(os.environ.get("INR_TO_USD", "86"))
    log(f"  Exchange rate: 1 USD = ₹{rate:.2f}")

    result = process_growth_report(df24, df12, str(report_path), inr_to_usd=rate)

    log(f"✅ Report saved: {report_path}")
    log(f"   Total clients  : {result.get('total_clients', '?')}")
    log(f"   High-growth    : {result.get('high_growth_clients', '?')}")
    log(f"   Top performer  : {result.get('top_performer', '?')}")
    log(f"   Total growth   : ${result.get('total_growth_usd', 0):,}")

    return report_path, result


# ── Step 3: Send email via Office 365 ─────────────────────────────────────────
def send_email(report_path: Path, result: dict):
    sender     = os.environ.get("SMTP_EMAIL", "").strip()
    password   = os.environ.get("SMTP_PASSWORD", "").strip()
    server_h   = os.environ.get("SMTP_SERVER", "smtp.office365.com").strip()
    port       = int(os.environ.get("SMTP_PORT", "587"))
    recipients_raw = os.environ.get("REPORT_RECIPIENTS", "").strip()

    if not sender or not password:
        fail(
            "SMTP_EMAIL and SMTP_PASSWORD are not set.\n"
            "Add them as GitHub Secrets:\n"
            "  Settings → Secrets and variables → Actions → New repository secret"
        )

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        fail(
            "REPORT_RECIPIENTS is not set or empty.\n"
            "Set it as a GitHub Secret (comma-separated email addresses)."
        )

    log(f"Sending report to {len(recipients)} recipient(s) via {server_h}:{port}...")

    today = datetime.now().strftime("%Y-%m-%d")
    month_year = datetime.now().strftime("%B %Y")

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"Client Growth Report – {month_year}"

    body = f"""Hi Team,

Please find attached the Client Growth Report for {month_year}, auto-generated on {today}.

Report Highlights:
  • Total Clients Analyzed : {result.get('total_clients', 'N/A'):,}
  • High-Growth Clients    : {result.get('high_growth_clients', 'N/A')} (Prev ≤$5K → Curr ≥$50K)
  • Total Growth (USD)     : ${result.get('total_growth_usd', 0):,}
  • Avg Growth %           : {result.get('avg_growth_pct', 0):.1f}%
  • Top Performer          : {result.get('top_performer', 'N/A')}

Excel Sheets Included:
  1. Growth Comparison     – all clients ranked by growth
  2. High Growth 5K-50K    – clients with highest relative jump
  3. Summary               – key statistics and top performer
  4. Exceptions            – negative revenue rows (if any)

Settings Used:
  • Exchange Rate  : 1 USD = ₹{os.environ.get('INR_TO_USD', '86')}
  • Data Period    : Previous 12M vs Current 12M
  • High Growth    : Previous ≤$5K AND Current ≥$50K

This report was generated automatically by GitHub Actions.

Best regards,
Koenig Solutions – Automated Report System
"""
    msg.attach(MIMEText(body, "plain"))

    # Attach Excel file
    with open(report_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{report_path.name}"',
    )
    msg.attach(part)

    try:
        smtp = smtplib.SMTP(server_h, port, timeout=60)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender, password)
        smtp.sendmail(sender, recipients, msg.as_string())
        smtp.quit()
        log(f"✅ Email sent to: {', '.join(recipients)}")
    except smtplib.SMTPAuthenticationError:
        fail(
            "SMTP authentication failed.\n"
            "  For Office 365 with MFA enabled, generate an App Password:\n"
            "  https://support.microsoft.com/en-us/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944"
        )
    except Exception as e:
        fail(f"Email send failed: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  CLIENT GROWTH REPORT – CI Runner")
    print(f"  Started: {datetime.now():%Y-%m-%d %H:%M:%S UTC}")
    print("=" * 60)

    f24, f12           = check_data_files()
    report_path, result = generate_report(f24, f12)
    send_email(report_path, result)

    print("\n" + "=" * 60)
    print("  ✅ ALL DONE")
    print(f"  Finished: {datetime.now():%Y-%m-%d %H:%M:%S UTC}")
    print("=" * 60)


if __name__ == "__main__":
    main()
