"""
Client Growth Report processing logic - clean final version.

Business logic:
1. Download/export two RMS files:
   - Last 24 months data
   - Last 12 months data

2. Match clients strictly by CorporateID.

3. Calculate:
   Previous 12M INR = Last 24M INR - Last 12M INR
   Current 12M INR  = Last 12M INR

4. Convert both to USD using the exchange rate entered in Streamlit:
   USD = INR / exchange_rate

5. High Growth filter:
   Previous 12M USD <= 5,000
   Current 12M USD >= 50,000

Important:
- Duplicate CorporateID rows are summed first, because RMS may show one total made from multiple rows.
- The script tries to find the correct INR revenue column.
- If your RMS export has a specific revenue column, set REVENUE_COLUMN below.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

DEFAULT_EXCHANGE_RATE = 84.0

# If you know the exact RMS INR revenue column name, put it here.
# Example:
# REVENUE_COLUMN = "TotalNR"
#
# Keep None to auto-detect from the priority list below.
REVENUE_COLUMN: Optional[str] = None

REVENUE_COLUMN_PRIORITY = [
    "TotalNR",
    "Total INR",
    "TotalINR",
    "Total_INR",
    "Amount INR",
    "AmountINR",
    "Revenue INR",
    "RevenueINR",
    "Net Revenue",
    "NetRevenue",
    "Total Revenue",
    "TotalRevenue",
    "Total",
    "TotalNR1",
]

ID_COLUMN_CANDIDATES = [
    "CorporateID",
    "Corporate ID",
    "CorpID",
    "Corp ID",
]

NAME_COLUMN_CANDIDATES = [
    "CorporateName",
    "Corporate Name",
    "CompanyName",
    "Company Name",
    "ClientName",
    "Client Name",
]

USER_COLUMN_CANDIDATES = [
    "UserName",
    "User Name",
    "SalesPerson",
    "Sales Person",
    "CCE",
    "AccountManager",
    "Account Manager",
]

URL_COLUMN_CANDIDATES = [
    "URL",
    "Corp_URL",
    "Corp URL",
    "Domain",
]


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def _normalize_column_name(value) -> str:
    return str(value).strip().replace("\n", " ").replace("\r", " ")


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = [_normalize_column_name(c) for c in work.columns]
    return work


def _find_column(df: pd.DataFrame, candidates: list[str], required: bool = True, label: str = "column") -> Optional[str]:
    cols = list(df.columns)
    lowered = {c.lower().strip(): c for c in cols}

    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lowered:
            return lowered[key]

    # relaxed contains match
    for candidate in candidates:
        candidate_key = candidate.lower().replace(" ", "").replace("_", "")
        for col in cols:
            col_key = col.lower().replace(" ", "").replace("_", "")
            if candidate_key == col_key:
                return col

    if required:
        raise ValueError(
            f"Could not find required {label}. Tried: {', '.join(candidates)}. "
            f"Available columns: {', '.join(cols)}"
        )
    return None


def _detect_revenue_column(df: pd.DataFrame) -> str:
    if REVENUE_COLUMN:
        if REVENUE_COLUMN not in df.columns:
            raise ValueError(
                f"Configured REVENUE_COLUMN '{REVENUE_COLUMN}' not found. "
                f"Available columns: {', '.join(df.columns)}"
            )
        return REVENUE_COLUMN

    # Exact/normalized match using priority
    col = _find_column(df, REVENUE_COLUMN_PRIORITY, required=False, label="revenue column")
    if col:
        return col

    # Fallback: choose a numeric-looking column containing revenue/amount/total but not count/frequency
    blocked_words = ["count", "frequency", "freq", "qty", "quantity", "id", "month", "date"]
    preferred_words = ["total", "revenue", "amount", "nr", "inr"]

    numeric_candidates = []
    for c in df.columns:
        key = c.lower().replace(" ", "").replace("_", "")
        if any(b in key for b in blocked_words):
            continue
        if not any(p in key for p in preferred_words):
            continue

        values = pd.to_numeric(
            df[c].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("₹", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.strip(),
            errors="coerce",
        )
        non_null = values.notna().sum()
        total_abs = values.abs().sum(skipna=True)
        if non_null > 0 and total_abs > 0:
            numeric_candidates.append((c, non_null, total_abs))

    if numeric_candidates:
        # Choose the column with largest total amount. This helps avoid USD/count columns.
        numeric_candidates.sort(key=lambda x: x[2], reverse=True)
        return numeric_candidates[0][0]

    raise ValueError(
        "Could not detect INR revenue column. Please set REVENUE_COLUMN at the top of process_report.py. "
        f"Available columns: {', '.join(df.columns)}"
    )


def _to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("INR", "", regex=False)
        .str.replace("USD", "", regex=False)
        .str.strip(),
        errors="coerce",
    ).fillna(0)


def _first_non_blank(series: pd.Series):
    for value in series:
        if pd.notna(value) and str(value).strip() != "":
            return value
    return ""


def _prepare_rcb(df: pd.DataFrame, period_label: str) -> tuple[pd.DataFrame, str]:
    """
    Prepare one RMS export:
    - Find CorporateID
    - Find INR revenue column
    - Sum duplicate CorporateID rows
    - Keep first non-blank name/user/url
    """
    work = _clean_columns(df)

    id_col = _find_column(work, ID_COLUMN_CANDIDATES, required=True, label="CorporateID column")
    name_col = _find_column(work, NAME_COLUMN_CANDIDATES, required=False, label="corporate name column")
    user_col = _find_column(work, USER_COLUMN_CANDIDATES, required=False, label="user name column")
    url_col = _find_column(work, URL_COLUMN_CANDIDATES, required=False, label="URL column")
    revenue_col = _detect_revenue_column(work)

    work["_CorporateID"] = pd.to_numeric(work[id_col], errors="coerce")
    work["_Revenue_INR"] = _to_number(work[revenue_col])

    if name_col:
        work["_CompanyName"] = work[name_col]
    else:
        work["_CompanyName"] = ""

    if user_col:
        work["_UserName"] = work[user_col]
    else:
        work["_UserName"] = ""

    if url_col:
        work["_URL"] = work[url_col]
    else:
        work["_URL"] = ""

    work = work.dropna(subset=["_CorporateID"])
    work["_CorporateID"] = work["_CorporateID"].astype(int)

    grouped = (
        work.groupby("_CorporateID", as_index=False)
        .agg(
            Revenue_INR=("_Revenue_INR", "sum"),
            CompanyName=("_CompanyName", _first_non_blank),
            UserName=("_UserName", _first_non_blank),
            URL=("_URL", _first_non_blank),
        )
        .rename(
            columns={
                "_CorporateID": "CorporateID",
                "Revenue_INR": f"{period_label}_INR",
                "CompanyName": f"CompanyName_{period_label}",
                "UserName": f"UserName_{period_label}",
                "URL": f"URL_{period_label}",
            }
        )
    )

    return grouped, revenue_col


def _make_url(row) -> str:
    url = row.get("URL", "")
    if pd.notna(url) and str(url).strip():
        return str(url).strip()
    return f"https://rms2.koenig-solutions.com/corporate/{int(row['CorporateID'])}"


def _fmt_usd(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"${int(round(value)):,}"


def _fmt_inr(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"₹{int(round(value)):,}"


# ---------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------

def process_growth_report(
    df_24m: pd.DataFrame,
    df_12m: pd.DataFrame,
    output_file: str,
    exchange_rate: float = DEFAULT_EXCHANGE_RATE,
):
    """
    Generate Client Growth Report.

    Args:
        df_24m: RMS export for last 24 months.
        df_12m: RMS export for last 12 months.
        output_file: Output Excel file path.
        exchange_rate: INR per 1 USD. Comes from Streamlit dashboard.

    Returns:
        dict summary for Streamlit.
    """
    exchange_rate = float(exchange_rate or DEFAULT_EXCHANGE_RATE)
    if exchange_rate <= 0:
        raise ValueError("Exchange rate must be greater than zero.")

    df_24, revenue_col_24 = _prepare_rcb(df_24m, "Last_24M")
    df_12, revenue_col_12 = _prepare_rcb(df_12m, "Last_12M")

    merged = pd.merge(df_24, df_12, on="CorporateID", how="outer", validate="one_to_one")

    for col in ["Last_24M_INR", "Last_12M_INR"]:
        merged[col] = merged[col].fillna(0)

    # Exact requested logic
    merged["Previous_12M_INR"] = merged["Last_24M_INR"] - merged["Last_12M_INR"]
    merged["Current_12M_INR"] = merged["Last_12M_INR"]

    merged["Previous_12M_USD"] = merged["Previous_12M_INR"] / exchange_rate
    merged["Current_12M_USD"] = merged["Current_12M_INR"] / exchange_rate
    merged["Growth_USD"] = merged["Current_12M_USD"] - merged["Previous_12M_USD"]

    merged["Growth_%"] = merged.apply(
        lambda r: (r["Growth_USD"] / r["Previous_12M_USD"] * 100)
        if r["Previous_12M_USD"] not in [0, None] and pd.notna(r["Previous_12M_USD"])
        else 0,
        axis=1,
    )

    merged["CompanyName"] = merged["CompanyName_Last_12M"].fillna("").replace("", pd.NA)
    merged["CompanyName"] = merged["CompanyName"].fillna(merged["CompanyName_Last_24M"]).fillna("")

    merged["UserName"] = merged["UserName_Last_12M"].fillna("").replace("", pd.NA)
    merged["UserName"] = merged["UserName"].fillna(merged["UserName_Last_24M"]).fillna("")

    merged["URL"] = merged["URL_Last_12M"].fillna("").replace("", pd.NA)
    merged["URL"] = merged["URL"].fillna(merged["URL_Last_24M"]).fillna("")
    merged["URL"] = merged.apply(_make_url, axis=1)

    # Exceptions: negative previous means 12M revenue exceeds 24M revenue, likely source/date issue.
    exceptions = merged[
        (merged["Previous_12M_INR"] < 0) |
        (merged["Current_12M_INR"] < 0)
    ].copy()

    clean = merged[
        (merged["Previous_12M_INR"] >= 0) &
        (merged["Current_12M_INR"] >= 0)
    ].copy()

    # Round for output readability
    for col in ["Previous_12M_USD", "Current_12M_USD", "Growth_USD"]:
        clean[col] = clean[col].round(0).astype(int)

    for col in ["Last_24M_INR", "Last_12M_INR", "Previous_12M_INR", "Current_12M_INR"]:
        clean[col] = clean[col].round(0).astype(int)

    growth_comparison = clean[
        [
            "CorporateID",
            "CompanyName",
            "UserName",
            "URL",
            "Last_24M_INR",
            "Last_12M_INR",
            "Previous_12M_INR",
            "Current_12M_INR",
            "Previous_12M_USD",
            "Current_12M_USD",
            "Growth_USD",
            "Growth_%",
        ]
    ].sort_values("Growth_USD", ascending=False).reset_index(drop=True)

    high_growth = growth_comparison[
        (growth_comparison["Previous_12M_USD"] <= 5000) &
        (growth_comparison["Current_12M_USD"] >= 50000)
    ].sort_values(["Current_12M_USD", "Growth_USD"], ascending=False).reset_index(drop=True)

    if len(exceptions):
        exc_out = exceptions[
            [
                "CorporateID",
                "CompanyName",
                "UserName",
                "URL",
                "Last_24M_INR",
                "Last_12M_INR",
                "Previous_12M_INR",
                "Current_12M_INR",
                "Previous_12M_USD",
                "Current_12M_USD",
                "Growth_USD",
                "Growth_%",
            ]
        ].copy()
    else:
        exc_out = pd.DataFrame(
            columns=[
                "CorporateID",
                "CompanyName",
                "UserName",
                "URL",
                "Last_24M_INR",
                "Last_12M_INR",
                "Previous_12M_INR",
                "Current_12M_INR",
                "Previous_12M_USD",
                "Current_12M_USD",
                "Growth_USD",
                "Growth_%",
            ]
        )

    top = growth_comparison.iloc[0] if len(growth_comparison) else None

    summary = pd.DataFrame(
        {
            "Metric": [
                "Calculation Logic",
                "Previous 12M INR Formula",
                "Current 12M INR Formula",
                "USD Conversion Formula",
                "Exchange Rate Used",
                "Revenue Column Used in 24M File",
                "Revenue Column Used in 12M File",
                "",
                "Top Performer",
                "Top Performer CorporateID",
                "Top Performer UserName",
                "Top Performer Previous 12M USD",
                "Top Performer Current 12M USD",
                "Top Performer Growth USD",
                "Top Performer Growth %",
                "",
                "Total Clients Analyzed",
                "High Growth Clients",
                "Average Previous 12M USD",
                "Average Current 12M USD",
                "Total Growth USD",
                "Average Growth %",
                "Total Exceptions",
                "Report Generated",
            ],
            "Value": [
                "Match by CorporateID only",
                "Last 24M INR - Last 12M INR",
                "Last 12M INR",
                "INR / Exchange Rate",
                f"1 USD = {exchange_rate:g} INR",
                revenue_col_24,
                revenue_col_12,
                "",
                top["CompanyName"] if top is not None else "N/A",
                str(top["CorporateID"]) if top is not None else "N/A",
                top["UserName"] if top is not None else "N/A",
                _fmt_usd(top["Previous_12M_USD"]) if top is not None else "N/A",
                _fmt_usd(top["Current_12M_USD"]) if top is not None else "N/A",
                _fmt_usd(top["Growth_USD"]) if top is not None else "N/A",
                f"{top['Growth_%']:.1f}%" if top is not None else "N/A",
                "",
                len(growth_comparison),
                len(high_growth),
                _fmt_usd(growth_comparison["Previous_12M_USD"].mean()) if len(growth_comparison) else "N/A",
                _fmt_usd(growth_comparison["Current_12M_USD"].mean()) if len(growth_comparison) else "N/A",
                _fmt_usd(growth_comparison["Growth_USD"].sum()) if len(growth_comparison) else "N/A",
                f"{growth_comparison['Growth_%'].mean():.1f}%" if len(growth_comparison) else "N/A",
                len(exc_out),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        }
    )

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        growth_comparison.to_excel(writer, sheet_name="Growth Comparison", index=False)
        high_growth.to_excel(writer, sheet_name="High Growth 5K-50K USD", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        exc_out.to_excel(writer, sheet_name="Exceptions", index=False)

        # Helpful audit sheet for checking Rakuten/Jasmeet and any mismatch
        audit_cols = [
            "CorporateID",
            "CompanyName",
            "UserName",
            "URL",
            "Last_24M_INR",
            "Last_12M_INR",
            "Previous_12M_INR",
            "Current_12M_INR",
            "Previous_12M_USD",
            "Current_12M_USD",
            "Growth_USD",
            "Growth_%",
        ]
        growth_comparison[audit_cols].to_excel(writer, sheet_name="Audit INR to USD", index=False)

    return {
        "total_clients": int(len(growth_comparison)),
        "high_growth_clients": int(len(high_growth)),
        "exceptions": int(len(exc_out)),
        "total_growth_usd": int(growth_comparison["Growth_USD"].sum()) if len(growth_comparison) else 0,
        "avg_growth_pct": round(float(growth_comparison["Growth_%"].mean()), 1) if len(growth_comparison) else 0,
        "top_performer": top["CompanyName"] if top is not None else "N/A",
        "top_performer_growth": int(top["Growth_USD"]) if top is not None else 0,
        "exchange_rate": exchange_rate,
        "revenue_column_24m": revenue_col_24,
        "revenue_column_12m": revenue_col_12,
    }
