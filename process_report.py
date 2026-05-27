"""
Client Growth Report processing logic - clean version.

Business logic:
1. Download/export Last 24 Months data and Last 12 Months data from RMS.
2. Match rows strictly by CorporateID.
3. Previous 12M INR = Last 24M INR - Last 12M INR.
4. Current 12M INR = Last 12M INR.
5. Convert INR to USD using exchange_rate passed from Streamlit:
      USD = INR / exchange_rate
6. High Growth filter:
      Previous_12M_USD <= 5000 AND Current_12M_USD >= 50000

Important:
- Revenue must be picked from the actual INR amount column, not frequency/client/count columns.
- This file prioritizes TotalNR before TotalNR1 because TotalNR1 was producing wrong values.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd


DEFAULT_EXCHANGE_RATE = 84.0

# Update this list only if RMS changes the export header.
# The first matching column will be used.
REVENUE_COLUMN_PRIORITY = [
    "TotalNR",
    "Total NR",
    "TOTALNR",
    "TotalNRAmount",
    "Total NR Amount",
    "TotalINR",
    "Total INR",
    "TOTAL INR",
    "AmountINR",
    "Amount INR",
    "RevenueINR",
    "Revenue INR",
    "NetRevenue",
    "Net Revenue",
    "NetRevenueINR",
    "Net Revenue INR",
    "TotalAmount",
    "Total Amount",
    "TotalAmountINR",
    "Total Amount INR",
    # Keep lower priority because this caused incorrect value in your report.
    "TotalNR1",
]

TEXT_COLUMNS_PRIORITY = {
    "company": ["CorporateName", "Corporate Name", "CompanyName", "Company Name", "ClientName", "Client Name"],
    "username": ["UserName", "User Name", "CCE", "SalesPerson", "Sales Person"],
    "url": ["URL", "Url", "Corp_URL", "Corp URL", "CorporateURL", "Corporate URL"],
}


def _normalise_name(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _first_non_blank(series: pd.Series):
    for value in series:
        if pd.notna(value) and str(value).strip() != "":
            return value
    return ""


def _find_column(df: pd.DataFrame, possible_names: list[str]) -> Optional[str]:
    normalised_map = {_normalise_name(col): col for col in df.columns}
    for name in possible_names:
        key = _normalise_name(name)
        if key in normalised_map:
            return normalised_map[key]
    return None


def _find_corporate_id_column(df: pd.DataFrame) -> str:
    col = _find_column(df, ["CorporateID", "Corporate ID", "CorpID", "Corp ID"])
    if not col:
        raise ValueError("CorporateID column not found. Expected CorporateID / Corporate ID / CorpID.")
    return col


def _detect_revenue_column(df: pd.DataFrame, revenue_column: Optional[str] = None) -> str:
    """
    Detect the INR amount column.

    If revenue_column is provided, it must exist.
    Otherwise, use REVENUE_COLUMN_PRIORITY.
    As a final fallback, choose a numeric column that looks like revenue and not count/frequency/USD.
    """
    if revenue_column:
        col = _find_column(df, [revenue_column])
        if not col:
            raise ValueError(f"Configured revenue column '{revenue_column}' was not found in the file.")
        return col

    col = _find_column(df, REVENUE_COLUMN_PRIORITY)
    if col:
        return col

    blocked_words = [
        "frequency", "client", "clients", "count", "qty", "quantity",
        "usd", "dollar", "growth", "percent", "percentage", "corporateid",
        "id", "serial", "sr", "rank",
    ]

    numeric_candidates = []
    for column in df.columns:
        norm = _normalise_name(column)
        if any(word in norm for word in blocked_words):
            continue

        values = pd.to_numeric(df[column], errors="coerce")
        non_null = values.notna().sum()
        total = values.fillna(0).sum()

        # INR revenue columns usually have meaningful large totals.
        if non_null > 0 and total > 0:
            numeric_candidates.append((column, total, values.max()))

    if not numeric_candidates:
        raise ValueError(
            "Could not detect INR revenue column. Please rename the RMS amount column to 'TotalNR' "
            "or pass revenue_column='ExactColumnName'."
        )

    # Prefer the highest total candidate. This avoids picking count/frequency columns.
    numeric_candidates.sort(key=lambda x: x[1], reverse=True)
    return numeric_candidates[0][0]


def _clean_numeric_money(series: pd.Series) -> pd.Series:
    """
    Converts values like ₹56,96,918 or 56,96,918 to numeric 5696918.
    """
    cleaned = (
        series.astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("INR", "", regex=False)
        .str.strip()
    )
    cleaned = cleaned.replace({"": "0", "nan": "0", "None": "0"})
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)


def _prepare_rcb(
    df: pd.DataFrame,
    revenue_output_col: str,
    revenue_column: Optional[str] = None,
) -> tuple[pd.DataFrame, str]:
    corp_col = _find_corporate_id_column(df)
    amount_col = _detect_revenue_column(df, revenue_column=revenue_column)

    company_col = _find_column(df, TEXT_COLUMNS_PRIORITY["company"])
    username_col = _find_column(df, TEXT_COLUMNS_PRIORITY["username"])
    url_col = _find_column(df, TEXT_COLUMNS_PRIORITY["url"])

    work = df.copy()
    work["_CorporateID"] = pd.to_numeric(work[corp_col], errors="coerce")
    work["_RevenueINR"] = _clean_numeric_money(work[amount_col])
    work = work.dropna(subset=["_CorporateID"])

    work["_CompanyName"] = work[company_col] if company_col else ""
    work["_UserName"] = work[username_col] if username_col else ""
    work["_URL"] = work[url_col] if url_col else ""

    grouped = (
        work.groupby("_CorporateID", as_index=False)
        .agg(
            **{
                revenue_output_col: ("_RevenueINR", "max"),
                f"{revenue_output_col}_SUM_AUDIT": ("_RevenueINR", "sum"),
                f"{revenue_output_col}_DUPLICATE_ROWS": ("_RevenueINR", "size"),
                "CompanyName": ("_CompanyName", _first_non_blank),
                "UserName": ("_UserName", _first_non_blank),
                "URL": ("_URL", _first_non_blank),
            }
        )
    )

    grouped = grouped.rename(columns={"_CorporateID": "CorporateID"})
    grouped["CorporateID"] = grouped["CorporateID"].astype(int)

    return grouped, amount_col


def _fmt_usd(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"${int(round(float(value), 0)):,}"


def process_growth_report(
    df_24m: pd.DataFrame,
    df_12m: pd.DataFrame,
    output_file: str,
    exchange_rate: float = DEFAULT_EXCHANGE_RATE,
    revenue_column_24m: Optional[str] = None,
    revenue_column_12m: Optional[str] = None,
):
    """
    Main processing function used by Streamlit.
    """
    exchange_rate = float(exchange_rate or DEFAULT_EXCHANGE_RATE)
    if exchange_rate <= 0:
        raise ValueError("Exchange rate must be greater than zero.")

    df_24, used_col_24 = _prepare_rcb(df_24m, "Last_24M_INR", revenue_column_24m)
    df_12, used_col_12 = _prepare_rcb(df_12m, "Last_12M_INR", revenue_column_12m)

    df_24 = df_24.rename(
        columns={
            "CompanyName": "CompanyName_24M",
            "UserName": "UserName_24M",
            "URL": "URL_24M",
        }
    )
    df_12 = df_12.rename(
        columns={
            "CompanyName": "CompanyName_12M",
            "UserName": "UserName_12M",
            "URL": "URL_12M",
        }
    )

    merged = pd.merge(df_24, df_12, on="CorporateID", how="outer", validate="one_to_one")

    for col in [
        "Last_24M_INR",
        "Last_12M_INR",
        "Last_24M_INR_SUM_AUDIT",
        "Last_12M_INR_SUM_AUDIT",
        "Last_24M_INR_DUPLICATE_ROWS",
        "Last_12M_INR_DUPLICATE_ROWS",
    ]:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

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

    merged["CompanyName"] = merged.get("CompanyName_12M", "").fillna(merged.get("CompanyName_24M", ""))
    merged["UserName"] = merged.get("UserName_12M", "").fillna(merged.get("UserName_24M", ""))

    if "URL_12M" in merged.columns:
        merged["URL"] = merged["URL_12M"].fillna(merged.get("URL_24M", ""))
    else:
        merged["URL"] = ""

    merged["URL"] = merged.apply(
        lambda r: r["URL"]
        if pd.notna(r["URL"]) and str(r["URL"]).strip()
        else f"https://rms2.koenig-solutions.com/corporate/{int(r['CorporateID'])}",
        axis=1,
    )

    exceptions = merged[
        (merged["Previous_12M_INR"] < 0)
        | (merged["Current_12M_INR"] < 0)
        | (merged["Last_24M_INR_DUPLICATE_ROWS"] > 1)
        | (merged["Last_12M_INR_DUPLICATE_ROWS"] > 1)
    ].copy()

    clean = merged[
        (merged["Previous_12M_INR"] >= 0)
        & (merged["Current_12M_INR"] >= 0)
    ].copy()

    for col in ["Previous_12M_USD", "Current_12M_USD", "Growth_USD"]:
        clean[col] = clean[col].round(0).astype(int)

    for col in ["Last_24M_INR", "Last_12M_INR", "Previous_12M_INR", "Current_12M_INR"]:
        clean[col] = clean[col].round(0).astype(int)

    growth_comparison_cols = [
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

    growth_comparison = (
        clean[growth_comparison_cols]
        .sort_values("Growth_USD", ascending=False)
        .reset_index(drop=True)
    )

    high_growth = (
        growth_comparison[
            (growth_comparison["Previous_12M_USD"] <= 5000)
            & (growth_comparison["Current_12M_USD"] >= 50000)
        ]
        .sort_values("Current_12M_USD", ascending=False)
        .reset_index(drop=True)
    )

    exception_cols = [
        "CorporateID",
        "CompanyName",
        "UserName",
        "Last_24M_INR",
        "Last_12M_INR",
        "Previous_12M_INR",
        "Current_12M_INR",
        "Last_24M_INR_DUPLICATE_ROWS",
        "Last_12M_INR_DUPLICATE_ROWS",
        "Last_24M_INR_SUM_AUDIT",
        "Last_12M_INR_SUM_AUDIT",
    ]
    exc_out = exceptions.copy()
    for col in exception_cols:
        if col not in exc_out.columns:
            exc_out[col] = ""
    exc_out = exc_out[exception_cols].reset_index(drop=True)

    top = growth_comparison.iloc[0] if len(growth_comparison) else None

    summary = pd.DataFrame(
        {
            "Metric": [
                "Business Logic",
                "Previous 12M INR Formula",
                "Current 12M INR Formula",
                "USD Formula",
                "High Growth Filter",
                "",
                "Revenue Column Used - 24M File",
                "Revenue Column Used - 12M File",
                "Exchange Rate Used",
                "Total Clients Analyzed",
                "High Growth Clients",
                "Total Exceptions / Duplicate Audit Rows",
                "",
                "Top Performer",
                "Top Corporate ID",
                "Top User",
                "Top Previous 12M USD",
                "Top Current 12M USD",
                "Top Growth USD",
                "Top Growth %",
                "Report Generated",
            ],
            "Value": [
                "Match by CorporateID only",
                "Last_24M_INR - Last_12M_INR",
                "Last_12M_INR",
                "INR / Exchange Rate",
                "Previous <= $5,000 and Current >= $50,000",
                "",
                used_col_24,
                used_col_12,
                f"1 USD = {exchange_rate:g} INR",
                int(len(growth_comparison)),
                int(len(high_growth)),
                int(len(exc_out)),
                "",
                top["CompanyName"] if top is not None else "N/A",
                str(top["CorporateID"]) if top is not None else "N/A",
                top["UserName"] if top is not None else "N/A",
                _fmt_usd(top["Previous_12M_USD"]) if top is not None else "N/A",
                _fmt_usd(top["Current_12M_USD"]) if top is not None else "N/A",
                _fmt_usd(top["Growth_USD"]) if top is not None else "N/A",
                f"{top['Growth_%']:.1f}%" if top is not None else "N/A",
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
        "revenue_column_24m": used_col_24,
        "revenue_column_12m": used_col_12,
    }
