"""
Client Growth Report processing logic - fixed for duplicate CorporateID rows.
Key fix: aggregate each source by CorporateID before merging to avoid many-to-many merge inflation.
"""

from datetime import datetime
import pandas as pd

INR_TO_USD = 86


def _first_non_blank(series):
    for value in series:
        if pd.notna(value) and str(value).strip() != "":
            return value
    return ""


def _prepare_rcb(df: pd.DataFrame, revenue_col_name: str) -> pd.DataFrame:
    required = ["CorporateID", "CorporateName", "UserName", "TotalNR1"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    work = df.copy()
    work["CorporateID"] = pd.to_numeric(work["CorporateID"], errors="coerce")
    work["TotalNR1"] = pd.to_numeric(work["TotalNR1"], errors="coerce").fillna(0)
    work = work.dropna(subset=["CorporateID"])

    agg = {
        "TotalNR1": "max",  # RMS exports contain duplicate CorporateID rows with same values; do not double count.
        "CorporateName": _first_non_blank,
        "UserName": _first_non_blank,
    }
    if "URL" in work.columns:
        agg["URL"] = _first_non_blank

    grouped = work.groupby("CorporateID", as_index=False).agg(agg)
    grouped["CorporateID"] = grouped["CorporateID"].astype(int)
    grouped = grouped.rename(columns={"TotalNR1": revenue_col_name})
    return grouped


def process_growth_report(df_24m, df_12m, output_file):
    df_24 = _prepare_rcb(df_24m, "24_Month_Revenue").rename(
        columns={"CorporateName": "CorporateName_prev", "UserName": "UserName_prev", "URL": "URL_prev"}
    )
    df_12 = _prepare_rcb(df_12m, "12_Month_Revenue").rename(
        columns={"CorporateName": "CorporateName_curr", "UserName": "UserName_curr", "URL": "URL_curr"}
    )

    merged = pd.merge(df_24, df_12, on="CorporateID", how="outer", validate="one_to_one")
    merged["24_Month_Revenue"] = merged["24_Month_Revenue"].fillna(0)
    merged["12_Month_Revenue"] = merged["12_Month_Revenue"].fillna(0)

    merged["Previous_12M_Revenue"] = merged["24_Month_Revenue"] - merged["12_Month_Revenue"]
    merged["Previous_12M_USD"] = merged["Previous_12M_Revenue"] / INR_TO_USD
    merged["Current_12M_USD"] = merged["12_Month_Revenue"] / INR_TO_USD

    exceptions = merged[(merged["Previous_12M_USD"] < 0) | (merged["Current_12M_USD"] < 0)].copy()
    clean = merged[(merged["Previous_12M_USD"] >= 0) & (merged["Current_12M_USD"] >= 0)].copy()

    clean["Growth_USD"] = clean["Current_12M_USD"] - clean["Previous_12M_USD"]
    clean["Growth_%"] = clean.apply(
        lambda r: (r["Growth_USD"] / r["Previous_12M_USD"] * 100) if r["Previous_12M_USD"] else 0,
        axis=1,
    )
    clean["UserName"] = clean["UserName_curr"].fillna(clean["UserName_prev"])
    clean["CompanyName"] = clean["CorporateName_curr"].fillna(clean["CorporateName_prev"])

    if "URL_curr" in clean.columns:
        clean["URL"] = clean["URL_curr"].fillna(clean.get("URL_prev", ""))
    else:
        clean["URL"] = ""
    clean["URL"] = clean.apply(
        lambda r: r["URL"] if pd.notna(r["URL"]) and str(r["URL"]).strip() else f"https://rms2.koenig-solutions.com/corporate/{r['CorporateID']}",
        axis=1,
    )

    for col in ["Previous_12M_USD", "Current_12M_USD", "Growth_USD"]:
        clean[col] = clean[col].round(0).astype(int)

    growth_comparison = clean[[
        "CorporateID", "CompanyName", "UserName", "URL",
        "Previous_12M_USD", "Current_12M_USD", "Growth_USD", "Growth_%"
    ]].sort_values("Growth_USD", ascending=False).reset_index(drop=True)

    high_growth = growth_comparison[
        (growth_comparison["Previous_12M_USD"] <= 5000) &
        (growth_comparison["Current_12M_USD"] >= 50000)
    ].sort_values("Growth_%", ascending=False).reset_index(drop=True)

    exc_out = exceptions.copy()
    if len(exc_out):
        exc_out["CompanyName"] = exc_out["CorporateName_curr"].fillna(exc_out["CorporateName_prev"])
        exc_out = exc_out[["CorporateID", "CompanyName", "Previous_12M_USD", "Current_12M_USD"]]
    else:
        exc_out = pd.DataFrame(columns=["CorporateID", "CompanyName", "Previous_12M_USD", "Current_12M_USD"])

    top = growth_comparison.iloc[0] if len(growth_comparison) else None

    def fmt_usd(v):
        return f"${int(v):,}" if pd.notna(v) else "N/A"

    summary = pd.DataFrame({
        "Metric": [
            "★ TOP PERFORMER – BIGGEST MOVER", "Company Name", "Corporate ID", "User Name",
            "Previous 12M Revenue (USD)", "Current 12M Revenue (USD)", "Growth Amount (USD)",
            "Growth Percentage", "Company URL", "", "■ OVERALL STATISTICS", "Total Clients Analyzed",
            "High Growth Clients (Prev ≤$5K → Curr ≥$50K)", "Average Previous 12M Revenue (USD)",
            "Average Current 12M Revenue (USD)", "Total Growth (USD)", "Average Growth % (All Clients)",
            "Total Exceptions", "Exchange Rate", "Report Generated"
        ],
        "Value": [
            "", top["CompanyName"] if top is not None else "N/A", str(top["CorporateID"]) if top is not None else "N/A",
            top["UserName"] if top is not None else "N/A", fmt_usd(top["Previous_12M_USD"]) if top is not None else "N/A",
            fmt_usd(top["Current_12M_USD"]) if top is not None else "N/A", fmt_usd(top["Growth_USD"]) if top is not None else "N/A",
            f"{top['Growth_%']:.1f}%" if top is not None else "N/A", top["URL"] if top is not None else "N/A",
            "", "", len(growth_comparison), len(high_growth), fmt_usd(growth_comparison["Previous_12M_USD"].mean()),
            fmt_usd(growth_comparison["Current_12M_USD"].mean()), fmt_usd(growth_comparison["Growth_USD"].sum()),
            f"{growth_comparison['Growth_%'].mean():.1f}%", len(exc_out), f"1 USD = {INR_TO_USD} INR",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ],
    })

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        growth_comparison.to_excel(writer, sheet_name="Growth Comparison", index=False)
        high_growth.to_excel(writer, sheet_name="High Growth 5K-50K USD", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        exc_out.to_excel(writer, sheet_name="Exceptions", index=False)

    return {
        "total_clients": int(len(growth_comparison)),
        "high_growth_clients": int(len(high_growth)),
        "exceptions": int(len(exc_out)),
        "total_growth_usd": int(growth_comparison["Growth_USD"].sum()),
        "avg_growth_pct": round(float(growth_comparison["Growth_%"].mean()), 1),
        "top_performer": top["CompanyName"] if top is not None else "N/A",
        "top_performer_growth": int(top["Growth_USD"]) if top is not None else 0,
    }
