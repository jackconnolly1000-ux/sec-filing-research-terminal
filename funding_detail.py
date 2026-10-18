"""Checked current-funding disaggregation; a subset never increases baseline borrowing."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLE = ROOT / "samples/funding_detail.json"
CHECKED_SHA256 = "21c9b3909e49260ea81c277451ab0655c6184d6e0c16652fc7f8a31b04b3441b"
COPY = {
    "LLY": "Current borrowing is not missing. At June 30, 2026, Lilly reported $7.050B of short-term borrowings and current maturities combined. Its carrying-value disclosure identifies $5.284B of commercial paper; $1.766B is derived current long-term borrowing, not a separately reported principal-payment schedule. Both are already included in $54.908B baseline borrowing. June unused commitments of $10.1B are separate from debt; $10B supports CP and is not an independent additional funding pool. Post-expiry drawable capacity remains Unavailable.",
    "ORCL": "Current borrowing is a combined carrying amount. Oracle reported $7.625B at August 31, 2026 without an instrument split. The checked calendar identifies $7.317B of note and term-loan principal due over the next twelve months, excluding commercial paper. These bases differ: subtraction cannot establish CP. May CP of $1.468B and an undrawn $10B revolver are historical; August CP and drawable revolver capacity remain Unavailable.",
    "VST": "Zero short-term borrowings does not mean zero current financing obligations. June 30, 2026 current baseline borrowing is $2.176B: $1.876B current long-term debt, a reported zero short-term balance and $300M receivables financing. The revolver was undrawn on that date despite H1 drawings of $400M and repayments of $780M. Its $4.408B reported availability already deducts $1.092B of letters of credit. Availability, debt and cash are separate measures.",
}


@lru_cache(maxsize=4)
def _load(digest):
    if digest != CHECKED_SHA256:
        raise ValueError("Funding-detail evidence changed; reconcile before use")
    return json.loads(SAMPLE.read_text())


def build(snapshot):
    captured = _load(hashlib.sha256(SAMPLE.read_bytes()).hexdigest())["companies"][snapshot["ticker"]]
    cash = snapshot["metrics"]["cash"]
    if (captured["accession"], captured["period_end"]) != (cash["accession"], cash["period_end"]):
        raise ValueError("Funding detail belongs to another filing")
    debt = snapshot["metrics"]["gross_debt"]
    ticker = snapshot["ticker"]
    facts = captured["facts"]
    def row(label, value, status, basis, source=None):
        return dict(label=label, value=value, status=status, basis=basis, period_end=cash["period_end"],
                    source=source, source_url=(source or {}).get("source_url", snapshot["source_url"]))
    if ticker == "LLY":
        cp = facts["commercial_paper"]
        current = debt["inputs"][0]
        residual = current["value"] - cp["value"]
        if residual != 1766e6:
            raise ValueError("Lilly current borrowing no longer reconciles")
        rows = [row("Commercial paper, carrying value", cp["value"], "Reported", "Included in current borrowing; not added again.", cp),
                row("Current long-term borrowing", residual, "Derived", "7,050M current borrowing less 5,284M commercial paper; carrying amount, not dated principal."),
                row("Current borrowing total", current["value"], "Reported", "Breakdown above reconciles to the existing balance-sheet line.", current)]
    elif ticker == "ORCL":
        rows = [row("Current notes and other borrowing", debt["inputs"][0]["value"], "Reported", "Combined carrying amount; not an instrument breakdown.", debt["inputs"][0]),
                row("Commercial paper at August 31", None, "Unavailable", "No exact separately reported balance in the checked 10-Q."),
                row("Current long-term borrowing split", None, "Unavailable", "Not inferred by subtracting principal from carrying value.")]
    else:
        a, _, b, c = debt["inputs"]
        rows = [row(a["label"], a["value"], "Reported", "Included in baseline borrowing.", a),
                row(b["label"], b["value"], "Reported zero", "Reported zero at June 30, 2026; not missing.", b),
                row(c["label"], c["value"], "Reported", "Current receivables financing; included once.", c),
                row("Current baseline borrowing", a["value"] + b["value"] + c["value"], "Derived", "Sum above; excludes leases and the separate Nuveen obligation.")]
    history = []
    if ticker == "VST":
        from annual_history_view import build as annual
        for observation in annual(ticker)["rows"]:
            inputs = observation["metrics"]["gross_debt"]["inputs"]
            history.append({"year": observation["fiscal_year"], **{name: dict(next(f for f in inputs if f["tag"] == tag), selection_rule="Checked fiscal-year presentation; exact period and filing version.")
                for name, tag in (("short_term", "us-gaap:ShortTermBorrowings"), ("receivables", "vistra:AccountsReceivableSecuritizationProgramAmountsBorrowed"))}})
    return dict(ticker=ticker, period_end=cash["period_end"], accession=cash["accession"], rows=rows,
                liabilities=[facts["current_liabilities"], facts["noncurrent_liabilities"]], history=history,
                explanation=COPY[ticker], registry=captured["registry"])
