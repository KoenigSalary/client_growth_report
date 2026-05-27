"""
Client Growth Report processing logic - clean version.

Fixes included:
1. Accepts exchange_rate from Streamlit.
2. Aggregates duplicate CorporateID rows before merging.
3. Detects the correct INR revenue column instead of blindly using TotalNR1.
4. Keeps UserName and URL in output.
5. Adds audit columns showing INR values used for verification.

Expected call from streamlit_app.py:
    process_growth_report(df_24m, df_12m, output_file, exchange_rate=90)
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd

DEFAULT_EXCHANGE_RATE = 84.0

# Put the real RMS INR amount column first if you know it.
# The script will pick the first matching column present in the uploaded Excel.
REVENUE_COLUMN_CANDIDATES = [
    "TotalINR",
    "Total INR",
    "Total_In_INR",
    "AmountINR",
    "Amount INR",
    "RevenueINR",
    "Revenue INR",
    "NetRevenueINR",
    "Net Revenue INR",
    "NetAmountINR",
    "Net Amount INR",
    "TotalRevenue",
    "Total Revenue",
    "TotalAmount",
    "Total Amount",
    "Amount",
    "TotalNR1",  # fallback only; older script used this and may be wrong for current RMS export
]


def _normalize_col_name(name: object) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def _find_column(df: pd.DataFrame, candidates: Iterable[str], required_name: str) -> str:
    normalized_map = {_normalize_col_name(col): col for col in df.columns}
    for candidate in candidates:
        key = _normalize_col_name(candidate)
        if key in normalized_map:
            return normalized_map[key]
    raise ValueError(
        f"Missing required column for {required_name}. Tried: {', '.join(candidates)}. "
        f"Available columns: {', '.join(map(str, df.columns))}"
    )


def _first_non_blank(series: pd.Series):
    for value in series:
        if pd.notna(value) and str(value).strip() != "":
            return value
    return ""


def _to_number(series: pd.Series) -> pd.Series:
    """Convert Indian currency/text values like ₹56,96,918 to numeric."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip(),
        errors="coerce",
    ).fillna(0)


def _prepare_rcb(df: pd.DataFrame, revenue_col_name: str) -> tuple[pd.DataFrame, str]:
    """Prepare one RMS export and aggregate duplicate CorporateID rows."""
    corporate_id_col = _find_column(df, ["CorporateID", "Corporate ID", "CorpID", "Corp ID"], "CorporateID")
    corporate_name_col = _find_column(
        df,
        ["CorporateName", "Corporate Name", "CompanyName", "Company Name", "ClientName", "Client Name"],
        "CorporateName",
    )
    user_col = _find_column(df, ["UserName", "User Name", "SalesPerson", "Sales Person", "Counsellor"], "UserName")
    revenue_source_col = _find_column(df, REVENUE_COLUMN_CANDIDATES, "INR revenue")

    work = df.copy()
    work[corporate_id_col] = pd.to_numeric(work[corporate_id_col], errors="coerce")
    work[revenue_source_col] = _to_number(work[revenue_source_col])
    work = work.dropna(subset=[corporate_id_col])

    agg = {
        revenue_source_col: "max",  # duplicate CorporateID rows generally repeat same RMS total; max avoids double count
        corporate_name_col: _first_non_blank,
        user_col: _first_non_blank,
    }

    url_col = None
    for possible in ["URL", "Corp_URL", "Corp URL", "CorporateURL", "Corporate URL", "Domain"]:
        matches = [col for col in work.columns if _normalize_col_name(col) == _normalize_col_name(possible)]
        if matches:
            url_col = matches[0]
            agg[url_col] = _first_non_blank
            break

    grouped = work.groupby(corporate_id_col, as_index=False).agg(agg)
    grouped[corporate_id_col] = grouped[corporate_id_col].astype(int)

    rename_map = {
        corporate_id_col: "CorporateID",
        corporate_name_col: "CorporateName",
        user_col: "UserName",
        revenue_source_col: revenue_col_name,
    }
    if url_col:
        rename_map[url_col] = "URL"

    grouped = grouped.rename(columns=rename_map)

    if "URL" not in grouped.columns:
        grouped["URL"] = ""

    return grouped, revenue_source_col


def _make_url(value, corporate_id: int) -> str:
    if pd.notna(value) and str(value).strip():
        return str(value).strip()
    return f"https://rms2.koenig-solutions.com/corporate/{corporate_id}"


def process_growth_report(df_24m, df_12m, output_file, exchange_rate=DEFAULT_EXCHANGE_RATE):
    """
    Generate Client Growth Report.

    df_24m: 24-month RMS export. Revenue should be total 24-month INR revenue.
    df_12m: 12-month RMS export. Revenue should be current 12-month INR revenue.
    output_file: Excel output path.
    exchange_rate: INR per 1 USD. Example: 90 means USD = INR / 90.
    """
    exchange_rate = float(exchange_rate or DEFAULT_EXCHANGE_RATE)
    if exchange_rate <= 0:
        raise ValueError("exchange_rate must be greater than zero")

    df_24, revenue_col_24 = _prepare_rcb(df_24m, "24_Month_Revenue_INR")
    df_12, revenue_col_12 = _prepare_rcb(df_12m, "12_Month_Revenue_INR")

    df_24 = df_24.rename(
        columns={
            "CorporateName": "CorporateName_prev",
            "UserName": "UserName_prev",
            "URL": "URL_prev",
        }
    )
    df_12 = df_12.rename(
        columns={
            "CorporateName": "CorporateName_curr",
            "UserName": "UserName_curr",
            "URL": "URL_curr",
        }
    )

    merged = pd.merge(df_24, df_12, on="CorporateID", how="outer", validate="one_to_one")
    merged["24_Month_Revenue_INR"] = merged["24_Month_Revenue_INR"].fillna(0)
    merged["12_Month_Revenue_INR"] = merged["12_Month_Revenue_INR"].fillna(0)

    # Previous 12 months = 24M total less current 12M total.
    merged["Previous_12M_INR"] = merged["24_Month_Revenue_INR"] - merged["12_Month_Revenue_INR"]
    merged["Current_12M_INR"] = merged["12_Month_Revenue_INR"]

    merged["Previous_12M_USD"] = merged["Previous_12M_INR"] / exchange_rate
    merged["Current_12M_USD"] = merged["Current_12M_INR"] / exchange_rate

    exceptions = merged[(merged["Previous_12M_USD"] < 0) | (merged["Current_12M_USD"] < 0)].copy()
    clean = merged[(merged["Previous_12M_USD"] >= 0) & (merged["Current_12M_USD"] >= 0)].copy()

    clean["Growth_USD"] = clean["Current_12M_USD"] - clean["Previous_12M_USD"]
    clean["Growth_%"] = clean.apply(
        lambda r: (r["Growth_USD"] / r["Previous_12M_USD"] * 100) if r["Previous_12M_USD"] else 0,
        axis=1,
    )

    clean["UserName"] = clean["UserName_curr"].fillna(clean["UserName_prev"])
    clean["CompanyName"] = clean["CorporateName_curr"].fillna(clean["CorporateName_prev"])
    clean["URL"] = clean["URL_curr"].fillna(clean["URL_prev"])
    clean["URL"] = clean.apply(lambda r: _make_url(r["URL"], int(r["CorporateID"])), axis=1)

    # Round display/report values only after calculations.
    for col in ["Previous_12M_INR", "Current_12M_INR", "Previous_12M_USD", "Current_12M_USD", "Growth_USD"]:
        clean[col] = clean[col].round(0).astype(int)

    growth_comparison = clean[
        [
            "CorporateID",
            "CompanyName",
            "UserName",
            "URL",
            "Previous_12M_INR",
            "Current_12M_INR",
            "Previous_12M_USD",
            "Current_12M_USD",
            "Growth_USD",
            "Growth_%",
        ]
    ].sort_values("Growth_USD", ascending=False).reset_index(drop=True)

    high_growth = growth_comparison[
        (growth_comparison["Previous_12M_USD"] <= 5000)
        & (growth_comparison["Current_12M_USD"] >= 50000)
    ].sort_values("Growth_%", ascending=False).reset_index(drop=True)

    if len(exceptions):
        exceptions["CompanyName"] = exceptions["CorporateName_curr"].fillna(exceptions["CorporateName_prev"])
        exceptions["UserName"] = exceptions["UserName_curr"].fillna(exceptions["UserName_prev"])
        exceptions["Previous_12M_INR"] = exceptions["Previous_12M_INR"].round(0).astype(int)
        exceptions["Current_12M_INR"] = exceptions["Current_12M_INR"].round(0).astype(int)
        exceptions["Previous_12M_USD"] = exceptions["Previous_12M_USD"].round(0).astype(int)
        exceptions["Current_12M_USD"] = exceptions["Current_12M_USD"].round(0).astype(int)
        exc_out = exceptions[
            [
                "CorporateID",
                "CompanyName",
                "UserName",
                "Previous_12M_INR",
                "Current_12M_INR",
                "Previous_12M_USD",
                "Current_12M_USD",
            ]
        ].copy()
    else:
        exc_out = pd.DataFrame(
            columns=[
                "CorporateID",
                "CompanyName",
                "UserName",
                "Previous_12M_INR",
                "Current_12M_INR",
                "Previous_12M_USD",
                "Current_12M_USD",
            ]
        )

    top = growth_comparison.iloc[0] if len(growth_comparison) else None

    def fmt_usd(v):
        return f"${int(v):,}" if pd.notna(v) else "N/A"

    def fmt_inr(v):
        return f"₹{int(v):,}" if pd.notna(v) else "N/A"

    summary = pd.DataFrame(
        {
            "Metric": [
                "★ TOP PERFORMER – BIGGEST MOVER",
                "Company Name",
                "Corporate ID",
                "User Name",
                "Previous 12M Revenue (INR)",
                "Current 12M Revenue (INR)",
                "Previous 12M Revenue (USD)",
                "Current 12M Revenue (USD)",
                "Growth Amount (USD)",
                "Growth Percentage",
                "Company URL",
                "",
                "■ OVERALL STATISTICS",
                "Total Clients Analyzed",
                "High Growth Clients (Prev ≤$5K → Curr ≥$50K)",
                "Average Previous 12M Revenue (USD)",
                "Average Current 12M Revenue (USD)",
                "Total Growth (USD)",
                "Average Growth % (All Clients)",
                "Total Exceptions",
                "Exchange Rate",
                "24M Revenue Source Column",
                "12M Revenue Source Column",
                "Report Generated",
            ],
            "Value": [
                "",
                top["CompanyName"] if top is not None else "N/A",
                str(top["CorporateID"]) if top is not None else "N/A",
                top["UserName"] if top is not None else "N/A",
                fmt_inr(top["Previous_12M_INR"]) if top is not None else "N/A",
                fmt_inr(top["Current_12M_INR"]) if top is not None else "N/A",
                fmt_usd(top["Previous_12M_USD"]) if top is not None else "N/A",
                fmt_usd(top["Current_12M_USD"]) if top is not None else "N/A",
                fmt_usd(top["Growth_USD"]) if top is not None else "N/A",
                f"{top['Growth_%']:.1f}%" if top is not None else "N/A",
                top["URL"] if top is not None else "N/A",
                "",
                "",
                len(growth_comparison),
                len(high_growth),
                fmt_usd(growth_comparison["Previous_12M_USD"].mean()) if len(growth_comparison) else "N/A",
                fmt_usd(growth_comparison["Current_12M_USD"].mean()) if len(growth_comparison) else "N/A",
                fmt_usd(growth_comparison["Growth_USD"].sum()) if len(growth_comparison) else "N/A",
                f"{growth_comparison['Growth_%'].mean():.1f}%" if len(growth_comparison) else "N/A",
                len(exc_out),
                f"1 USD = {exchange_rate:g} INR",
                revenue_col_24,
                revenue_col_12,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        }
    )

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        growth_comparison.to_excel(writer, sheet_name="Growth Comparison", index=False)
        high_growth.to_excel(writer, sheet_name="High Growth 5K-50K USD", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        exc_out.to_excel(writer, sheet_name="Exceptions", index=False)

    return {
        "total_clients": int(len(growth_comparison)),
        "high_growth_clients": int(len(high_growth)),
        "exceptions": int(len(exc_out)),
        "total_growth_usd": int(growth_comparison["Growth_USD"].sum()) if len(growth_comparison) else 0,
        "avg_growth_pct": round(float(growth_comparison["Growth_%"].mean()), 1) if len(growth_comparison) else 0,
        "top_performer": top["CompanyName"] if top is not None else "N/A",
        "top_performer_growth": int(top["Growth_USD"]) if top is not None else 0,
        "exchange_rate": exchange_rate,
        "revenue_col_24m": revenue_col_24,
        "revenue_col_12m": revenue_col_12,
    }
