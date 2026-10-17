"""Reconcile original annual filing observations before publishing a five-year view.

No network or Streamlit. Historical borrowing mappings are checked per source; current
company mappings are not extended automatically. Existing frozen reviews do not use this module.
"""
from datetime import date
from decimal import Decimal
import hashlib

import filing_xbrl as fx

CASH = "us-gaap:CashAndCashEquivalentsAtCarryingValue"
OCF = "us-gaap:NetCashProvidedByUsedInOperatingActivities"
CAPEX = "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"
LLY_CAPEX = "us-gaap:PaymentsToAcquireOtherPropertyPlantAndEquipment"
RECEIVABLES = "vistra:AccountsReceivableSecuritizationProgramAmountsBorrowed"
BORROWING = {
    "LLY": ["us-gaap:DebtCurrent", "us-gaap:LongTermDebtNoncurrent"],
    "ORCL": ["us-gaap:NotesPayableCurrent", "us-gaap:LongTermNotesAndLoans"],
    "VST": ["us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations", "us-gaap:ShortTermBorrowings", RECEIVABLES],
}
TOTALS = {"LLY": "us-gaap:DebtLongtermAndShorttermCombinedAmount",
          "ORCL": "us-gaap:DebtLongtermAndShorttermCombinedAmount",
          "VST": "us-gaap:LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"}

# Printed statement controls, USD millions. Entered independently of companyfacts selection.
# cash, current borrowing, noncurrent borrowing, OCF, reported capex.
CONTROLS = {
    "LLY": {
        2021: (3818.5, 1538.3, 15346.4, 7260.7, 1309.8),
        2022: (2067.0, 1501.1, 14737.5, 7084.4, 1854.3),
        2023: (2818.6, 6904.5, 18320.8, 4240.1, 3447.6),
        2024: (3268.4, 5117.1, 28527.1, 8817.9, 5057.8),
        2025: (7268, 1635, 40868, 16813, 7841),
    },
    "ORCL": {
        2022: (21383, 3749, 72110, 9539, 4511),
        2023: (9765, 4061, 86420, 17165, 8695),
        2024: (10454, 10605, 76264, 18673, 6866),
        2025: (10786, 7271, 85297, 20821, 21215),
        2026: (31289, 7199, 122342, 31977, 55663),
    },
    "VST": {
        2021: (1325, 254, 10477, -206, 1033),
        2022: (455, 38, 11933, 485, 1301),
        2023: (3485, 2286, 12116, 5453, 1676),
        2024: (1188, 880, 15418, 4563, 2078),
        2025: (785, 1201, 15842, 4070, 2752),
    },
}
VST_FINANCING_CONTROLS = {2021: (0, 0), 2022: (650, 425), 2023: (0, 0),
                          2024: (0, 750), 2025: (1800, 1225)}
VST_FINANCING_NOTE = ("Count the reported accounts-receivable financing balance-sheet line once. "
                     "The 2025 line's assignment between receivables and repurchase facilities is not explicit. "
                     "Do not add the separately disclosed 1,100M or 125M facility amounts again. "
                     "The separate Nuveen forward-repurchase obligation is outside baseline borrowing.")
# FY2023 Note 1 reclassifies development-milestone payments to purchases of IPR&D
# within investing cash flows. These complete annual flow pairs use that filing's basis.
RECLASSIFIED_FLOWS = {
    ("LLY", 2021, "0000059478-24-000065"): (7365.9, 1309.8),
    ("LLY", 2022, "0000059478-24-000065"): (7585.7, 1854.3),
}


def usd(millions):
    return int(Decimal(str(millions)) * 1_000_000)


def companyfacts_check(facts, tag, source, duration=False):
    """Exact selected accession and period, USD; no individual input is taken from another filing."""
    prefix, local = tag.split(":", 1)
    rows = facts.get("facts", {}).get(prefix, {}).get(local, {}).get("units", {}).get("USD", [])
    original = [r for r in rows if r.get("accn") == source["accession"] and r.get("form") == "10-K"
                and r.get("end") == source["period_end"]
                and (r.get("start") == source["period_start"] if duration else not r.get("start"))]
    values = sorted({r["val"] for r in original})
    if len(values) > 1:
        raise ValueError("Conflicting original companyfacts rows: " + tag)
    later = [r for r in rows if r.get("end") == source["period_end"]
             and (r.get("start") == source["period_start"] if duration else not r.get("start"))
             and source["filed"] < r.get("filed", "") <= "2026-10-17"
             and r.get("form") in {"10-K", "10-Q", "10-K/A", "10-Q/A"}]
    revisions = [{"accession": r["accn"], "filed": r["filed"], "form": r["form"], "value": r["val"]}
                 for r in later if values and r["val"] != values[0]]
    unique = {tuple(r.items()): r for r in revisions}
    return {"value": values[0] if values else None,
            "status": "Exact accession and period" if values else "Not in captured companyfacts",
            "later_differences_not_used": list(unique.values())}


def reconcile(source, document, companyfacts, locations, *, expected_sha256=None):
    """One source's five measures, with original facts, independent controls and explicit gaps.

    Fixture replay passes the hash of its unchanged fact/context subset. Full builds require
    the original source hash. A mismatched raw file never produces checked observations.
    """
    expected_sha256 = expected_sha256 or source["source_sha256"]
    if hashlib.sha256(document.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Annual source hash differs from the reviewed document")
    ticker, year = source["ticker"], int(source["period_end"][:4])
    if source["form"] != "10-K" or source["filed"] > "2026-10-17":
        raise ValueError("History requires the selected original annual filing within the cutoff")
    if not 360 <= (date.fromisoformat(source["period_end"])-date.fromisoformat(source["period_start"])).days <= 371:
        raise ValueError("History flow must cover a full fiscal year")
    root = fx.parse(document)
    contexts = fx._contexts(root)
    controls = CONTROLS[ticker][year]
    flow_controls = RECLASSIFIED_FLOWS.get((ticker, year, source["accession"]), controls[3:])

    def fact(tag, control=None, duration=False):
        r = (fx.read_duration(document, source["accession"], tag, source["period_start"], source["period_end"])
             if duration else fx.read_instant(document, source["accession"], tag, source["period_end"]))
        r.update({k: source[k] for k in ("form", "filed", "source_url", "source_sha256")})
        r["document"] = source["document"]
        r["detail"] = r["detail"].replace(document.name, source["document"])
        r["unit_measure"] = r.get("unit")
        if r["value"] is not None:
            r["unit"] = "USD"
        r["period_start"] = source["period_start"] if duration else None
        r["period_end"] = source["period_end"]
        r["location"] = locations.get(tag, {"printed_page": locations[CASH]["printed_page"],
                                            "statement": "Consolidated balance sheet or debt note", "tag": tag})
        r["companyfacts"] = companyfacts_check(companyfacts, tag, source, duration)
        if r["value"] is not None:
            ctx = contexts[r["context_id"]]
            if (ctx.get("entity_identifier") or "").lstrip("0") != str(source["cik"]):
                raise ValueError("Annual fact belongs to another entity")
            if control is not None and r["value"] != usd(control):
                raise ValueError("Annual filing differs from printed control: " + tag)
            other = r["companyfacts"]["value"]
            if other is not None and other != r["value"]:
                raise ValueError("Original companyfacts differs from filing: " + tag)
        return r

    cash = fact(CASH, controls[0])
    ocf = fact(OCF, flow_controls[0], True)
    capex = fact(LLY_CAPEX if ticker == "LLY" else CAPEX, flow_controls[1], True)
    debt = [fact(tag, controls[k+1] if k < 2 else VST_FINANCING_CONTROLS[year][k-2])
            for k, tag in enumerate(BORROWING[ticker])]
    total = fact(TOTALS[ticker], controls[1]+controls[2])
    if all(f["value"] is not None for f in debt[:2]) and total["value"] is not None:
        if sum(f["value"] for f in debt[:2]) != total["value"]:
            raise ValueError("Annual borrowing components differ from reported total")
    missing = [f["tag"] for f in debt if f["value"] is None]
    debt_detail = "Missing borrowing component in this original filing: " + ", ".join(missing) if missing else ""
    if any(f["value"] is not None and f["value"] < 0 for f in debt):
        raise ValueError("Negative annual borrowing component")
    metrics = {
        "cash": {"value": cash["value"], "inputs": [cash], "basis": "Cash and equivalents, excluding restricted cash."},
        "gross_debt": {"value": None if debt_detail else sum(f["value"] for f in debt), "inputs": debt,
                       "detail": debt_detail, "total_check": {**total, "scope": "Current plus noncurrent long-term debt only" if ticker == "VST" else "The two borrowing components"},
                       "formula": " + ".join(BORROWING[ticker]),
                       "basis": "Carrying borrowing; excludes lease liabilities. Project debt within long-term debt is not added again.",
                       "notes": [VST_FINANCING_NOTE] if ticker == "VST" else []},
        "operating_cash_flow": {"value": ocf["value"], "inputs": [ocf], "basis": "Reported full-fiscal-year operating cash flow, including working-capital movements."},
        "capital_spending": {"value": capex["value"], "inputs": [capex],
                             "basis": "Reported capital expenditures including nuclear fuel purchases and LTSA prepayments." if ticker == "VST" else "Reported purchases of property and equipment; excludes acquisitions and other investing flows."},
        "free_cash_flow": {"value": ocf["value"]-capex["value"] if ocf["value"] is not None and capex["value"] is not None else None,
                           "formula": "operating_cash_flow - capital_spending", "inputs": [ocf, capex],
                           "basis": "Historical OCF less reported capital spending; not future repayment coverage."},
    }
    for metric in metrics.values():
        metric["unit"] = "USD"
        metric["status"] = "Reconciled" if metric["value"] is not None else "Unavailable"
        if metric["value"] is None and not metric.get("detail"):
            metric["detail"] = "; ".join(f["detail"] for f in metric["inputs"] if f["value"] is None)
    return {"ticker": ticker, "fiscal_year": year, "source": source, "metrics": metrics,
            "note": "One selected filing version per calculation; independent stock and flow sources recorded explicitly. Later differing inputs are never substituted individually. Fiscal calendars, capital-spending definitions and business perimeters differ; no company ranking or future funding conclusion."}
