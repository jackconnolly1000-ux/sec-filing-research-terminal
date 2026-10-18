"""Checked annual table shared by the app and individual Excel exports."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLE = ROOT / "samples/annual_history_reconciliation.json"
CHECKED_SHA256 = "db4b88c8f0c1e0e3704ed49d63c253bb5a1ea79b7b28d78b8efdd2ff9031354f"
KEYS = ("cash", "gross_debt", "operating_cash_flow", "capital_spending", "free_cash_flow")
LABELS = ("Cash and equivalents", "Baseline borrowing", "Operating cash flow", "Capital spending", "Free cash flow")
NOTE = ("Annual cash and borrowing are fiscal-year-end balances. OCF and capital spending cover each full fiscal year. "
        "FCF = OCF − capital spending; it excludes acquisitions and other investing and financing uses. "
        "Historical amounts do not establish future repayment coverage. Fiscal calendars, business perimeters and capital-spending definitions differ.")


def fingerprint():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
            ("annual_history_view.py", "annual_history.py", "samples/annual_history_reconciliation.json",
             "samples/annual_source_inventory.json")}


def build(ticker):
    if hashlib.sha256(SAMPLE.read_bytes()).hexdigest() != CHECKED_SHA256:
        raise ValueError("Annual source checkpoint changed and requires reconciliation")
    captured = json.loads(SAMPLE.read_text())
    rows = [r for r in captured["observations"] if r["ticker"] == ticker]
    expected = list(range(2022, 2027)) if ticker == "ORCL" else list(range(2021, 2026))
    if ticker not in {"LLY", "ORCL", "VST"} or [r["fiscal_year"] for r in rows] != expected:
        raise ValueError("Annual history requires five unique, chronological checked years")
    for row in rows:
        for key in KEYS:
            metric = row["metrics"][key]
            inputs = metric["inputs"]
            if len({f["accession"] for f in inputs}) != 1:
                raise ValueError("Annual calculation mixes filing versions")
            for fact in inputs:
                if (fact.get("unit") != "USD" or fact.get("dimensions") or
                    fact.get("period_end") != row["source"]["period_end"] or
                    not all(fact.get(k) for k in ("source_url", "source_sha256", "accession", "tag", "context_id"))):
                    raise ValueError("Annual input provenance is incomplete")
                if key in {"operating_cash_flow", "capital_spending", "free_cash_flow"} and fact.get("period_start") != row["source"]["period_start"]:
                    raise ValueError("Annual flow covers the wrong fiscal year")
            value = metric["value"]
            if value is None:
                if not metric.get("detail"):
                    raise ValueError("Unavailable annual measure requires a reason")
                continue
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Annual measure must be finite USD")
            actual = (inputs[0]["value"] - inputs[1]["value"] if key == "free_cash_flow" else
                      sum(f["value"] for f in inputs) if key == "gross_debt" else inputs[0]["value"])
            if actual != value:
                raise ValueError("Annual calculation differs from checked inputs")
    notes = [NOTE]
    if ticker == "LLY":
        notes.append("2021/2022 cash flows use FY2023’s disclosed IPR&D milestone reclassification. OCF increased by $105.2M/$501.3M through classification, not new cash generation. Cash and borrowing retain their original balance sheets. FCF does not deduct IPR&D purchases.")
    if ticker == "VST":
        notes.append("2021/2024 use complete comparative snapshots from the following 10-K, including reported zero short-term borrowing. Original missing facts were not treated as zero. Capex includes nuclear fuel and LTSA prepayments. The 2025 financing line is counted once; its facility split remains unresolved.")
    return {"ticker": ticker, "rows": rows, "keys": list(KEYS), "labels": list(LABELS), "notes": notes,
            "as_of": captured["as_of"]}


def render(ticker):
    from ui import esc
    model = build(ticker)
    out = '<section class="lr-obligations lr-history lr-annual"><h3>Five completed fiscal years</h3>'
    out += '<p class="lr-meta">USD millions. Full fiscal years only; the latest TTM is shown separately above.</p>'
    out += '<div class="lr-history-scroll" tabindex="0" role="region" aria-label="Five-year annual history table"><table><thead><tr><th>Measure</th>'
    for row in model["rows"]:
        out += f'<th>FY{row["fiscal_year"]}<br><span class="lr-meta">{esc(row["source"]["period_end"])}</span></th>'
    out += '</tr></thead><tbody>'
    for key, label in zip(KEYS, LABELS):
        out += '<tr><th scope="row">' + esc(label) + '</th>'
        for row in model["rows"]:
            metric = row["metrics"][key]
            value = metric["value"]
            text = "Unavailable" if value is None else f'({abs(value)/1e6:,.1f})' if value < 0 else f'{value/1e6:,.1f}'
            out += f'<td title="{esc(metric.get("detail", ""))}">{esc(text)}</td>'
        out += '</tr>'
    out += '</tbody></table></div>'
    for note in model["notes"]:
        out += f'<p class="lr-meta">{esc(note)}</p>'
    out += '<details><summary>Annual filing sources and presentation choices</summary>'
    for row in model["rows"]:
        sources = {f["accession"]: f for m in row["metrics"].values() for f in m["inputs"]}
        out += f'<p><strong>FY{row["fiscal_year"]}</strong>: {esc(row["source_basis"])}<br>'
        out += ' · '.join(f'<a href="{esc(f["source_url"])}">10-K filed {esc(f["filed"])} ({esc(acc)})</a>' for acc, f in sources.items())
        out += '</p>'
    return out + '</details></section>'
