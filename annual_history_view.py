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


def _usd(value):
    """$12.34B or $850M; a missing value is Unavailable, never zero."""
    if value is None:
        return "Unavailable"
    sign = "−" if value < 0 else ""
    return f"{sign}${abs(value) / 1e9:,.2f}B" if abs(value) >= 1e9 else f"{sign}${abs(value) / 1e6:,.0f}M"


def charts(model):
    """Two five-year charts from the same checked rows as the table: fiscal-year-end balances, then annual flows.

    Each chart has one scale across all five years. Capital spending is drawn left of zero as a use of cash, as in
    the latest-TTM chart above; FCF is the result, not another flow. A missing value has no bar and says Unavailable."""
    from datetime import date
    from ui import esc
    rows = model["rows"]
    day = lambda iso: (lambda d: f"{d:%b} {d.day}, {d:%Y}")(date.fromisoformat(iso))
    value = lambda row, key: row["metrics"][key]["value"]
    out = '<div class="lr-annual-charts">'
    # 1. Balances: cash and borrowing panels on one shared scale
    known = [value(r, k) for r in rows for k in ("cash", "gross_debt") if value(r, k) is not None]
    top = max(known, default=1) or 1
    out += ('<h4 class="lr-annual-title">Fiscal-year-end cash and baseline borrowing</h4><p class="lr-meta">Balances at each fiscal year end, '
            f'{esc(day(rows[0]["source"]["period_end"]))} to {esc(day(rows[-1]["source"]["period_end"]))} · one scale for both panels</p>'
            '<div class="lr-bal-grid">')
    for key, name, kind in (("cash", "Cash and equivalents", "cash"), ("gross_debt", "Baseline borrowing", "borrowing")):
        out += (f'<div class="lr-bal-panel" role="figure" aria-label="{esc(name)} at five fiscal year ends">'
                f'<h4><span class="lr-swatch lr-{kind}" aria-hidden="true"></span>{esc(name)}</h4>')
        for r in rows:
            v = value(r, key)
            bar = (f'<span class="lr-bal-bar lr-{kind}" style="width:{max(v / top * 100, 0.5):.4f}%"></span>'
                   if v is not None else '')
            out += (f'<div class="lr-bal-row"><span class="lr-bal-date">FY{r["fiscal_year"]}</span>'
                    f'<div class="lr-bal-track" title="{esc(name)}, {esc(day(r["source"]["period_end"]))}: {esc(_usd(v))}">{bar}</div>'
                    f'<strong class="lr-bal-value">{esc(_usd(v))}</strong></div>')
        out += '</div>'
    out += '</div>'
    # 2. Flows: OCF, capital spending (a use) and FCF per fiscal year, one diverging scale
    flows = [(r, [("Operating cash flow", value(r, "operating_cash_flow")),
                  ("Capital spending", None if value(r, "capital_spending") is None else -value(r, "capital_spending")),
                  ("Free cash flow", value(r, "free_cash_flow"))]) for r in rows]
    top = max((abs(v) for _, items in flows for _, v in items if v is not None), default=1) or 1
    out += ('<h4 class="lr-annual-title">Annual operating cash flow, capital spending and FCF</h4><p class="lr-meta">'
            '<span class="ol-key out" aria-hidden="true"></span>Uses cash, left of zero · '
            '<span class="ol-key in" aria-hidden="true"></span>adds cash or a positive result, right of zero · '
            'one scale for all five years</p><div class="lr-chart">')
    for r, items in flows:
        out += f'<div class="lr-annual-year">FY{r["fiscal_year"]} <span class="lr-meta">{esc(day(r["source"]["period_start"]))} – {esc(day(r["source"]["period_end"]))}</span></div>'
        for name, v in items:
            width = abs(v) / top * 100 if v else 0
            bar = f'<span class="lr-bar{" in" if v and v > 0 else ""}" style="width:{width:.4f}%"></span>' if v else ''
            out += (f'<div class="lr-bar-row"><span>{esc(name)}</span><div class="lr-track" aria-hidden="true">'
                    f'<div class="lr-half">{bar if v is not None and v < 0 else ""}</div>'
                    f'<div class="lr-half">{bar if v is not None and v > 0 else ""}</div></div>'
                    f'<span class="lr-bar-value">{esc(_usd(v))}</span></div>')
    return out + ('</div><p class="lr-meta">FCF = OCF − capital spending; the FCF bar is the result, not another cash '
                  'flow to add. These are completed fiscal years; the latest TTM is a separate, overlapping period.</p></div>')


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
    out += charts(model)
    for note in model["notes"]:
        out += f'<p class="lr-meta">{esc(note)}</p>'
    out += '<details><summary>Annual filing sources and presentation choices</summary>'
    for row in model["rows"]:
        sources = {f["accession"]: f for m in row["metrics"].values() for f in m["inputs"]}
        out += f'<p><strong>FY{row["fiscal_year"]}</strong>: {esc(row["source_basis"])}<br>'
        out += ' · '.join(f'<a href="{esc(f["source_url"])}">10-K filed {esc(f["filed"])} ({esc(acc)})</a>' for acc, f in sources.items())
        out += '</p>'
    return out + '</details></section>'
