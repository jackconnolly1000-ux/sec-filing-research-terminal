"""Two source-backed chart questions; unknown history is omitted, never plotted as zero."""
import hashlib
from pathlib import Path
import company_history
import theme


def fingerprint():
    return {"code": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "history": company_history.fingerprint()}


def build(snapshot):
    h = company_history.build(snapshot)
    r = {x["key"]: x for x in h["rows"]}
    flow = [("Operating cash flow", r["operating_cash_flow"]["value"]),
            ("Capital spending", -r["capital_spending"]["value"] if r["capital_spending"]["value"] is not None else None),
            ("Free cash flow", r["free_cash_flow"]["value"])]
    series = ["Cash and equivalents"]
    if r["gross_debt"]["annual_value"] is not None:
        series.append("Baseline borrowing")
    points = [(h["annual_end"], [r["cash"]["annual_value"]] + ([r["gross_debt"]["annual_value"]] if len(series) == 2 else [])),
              (h["period_end"], [r["cash"]["value"]] + ([r["gross_debt"]["value"]] if len(series) == 2 else []))]
    return {"palette": theme.review_palette(), "flow": flow, "points": points, "series": series, "period_start": h["period_start"], "period_end": h["period_end"],
            "title": "How did borrowing and cash change?" if len(series) == 2 else "How did cash change?",
            "note": "Baseline borrowing excludes leases; cash excludes restricted cash and investments. These balances do not establish repayment coverage." if len(series) == 2 else
            "Older borrowing is Unavailable, so this chart compares cash only. No zero borrowing value or debt trend is inferred. Cash excludes restricted cash and investments.",
            "sources": [h["annual_source"], h["current_source"]]}
