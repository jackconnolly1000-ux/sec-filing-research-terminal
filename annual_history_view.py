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


# The marker company_review.render_app splits on to draw the two Plotly charts directly under the table
CHARTS_MARK = "<!-- lr-annual-charts -->"
# Flow colors: inflow blue and use grey as in the latest-TTM chart; FCF amber, a result, distinct from both
OCF_COLOR, CAPEX_COLOR, FCF_COLOR = "#3987e5", "#9598a1", "#d4a72c"


def figures(model):
    """Two grouped-column charts, fiscal years left to right, from the same checked rows as the table.

    Balances: cash and baseline borrowing at each fiscal year end. Flows: OCF, capital spending drawn below zero as
    a use of cash, and FCF (the result). One y-axis each, starting at zero. A missing value is None, which Plotly
    leaves as an empty slot: a gap, never a zero bar."""
    import plotly.graph_objects as go
    import theme as T
    rows = model["rows"]
    years = [f"FY{r['fiscal_year']}" for r in rows]
    ends = [r["source"]["period_end"] for r in rows]
    value = lambda key: [None if r["metrics"][key]["value"] is None else r["metrics"][key]["value"] / 1e9 for r in rows]
    capex = [None if v is None else -v for v in value("capital_spending")]

    def chart(series, title):
        fig = go.Figure()
        for name, values, color in series:
            shown = ["Unavailable" if v is None else f"{'−' if v < 0 else ''}${abs(v):,.2f}B" for v in values]
            fig.add_trace(go.Bar(x=years, y=values, name=name, marker=dict(color=color, line=dict(width=0)),
                                 customdata=list(zip(ends, shown)),
                                 hovertemplate=f"{name}<br>%{{x}}, to %{{customdata[0]}}: %{{customdata[1]}}<extra></extra>"))
        fig.add_hline(y=0, line_color=T.TEXT_MUTED, line_width=1)
        fig.update_layout(height=340, margin=dict(l=56, r=8, t=48, b=36), barmode="group", bargap=0.28, bargroupgap=0.08,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=T.TEXT, size=12),
                          legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title=None),
                          xaxis=dict(type="category", fixedrange=True, showgrid=False, tickfont=dict(size=12)),
                          yaxis=dict(title=title, fixedrange=True, gridcolor=T.BORDER, zeroline=False, rangemode="tozero",
                                     tickformat=",.0f"),
                          hoverlabel=dict(font=dict(size=12)))
        return fig

    balances = chart([("Cash and equivalents", value("cash"), T.SERIES_CASH),
                      ("Baseline borrowing", value("gross_debt"), T.SERIES_BORROWING)], "USD billions")
    flows = chart([("Operating cash flow", value("operating_cash_flow"), OCF_COLOR),
                   ("Capital spending (use of cash)", capex, CAPEX_COLOR),
                   ("Free cash flow", value("free_cash_flow"), FCF_COLOR)], "USD billions")
    return balances, flows


def chart_captions(model):
    """What each chart shows, with any Unavailable year named, so a gap is never read as zero."""
    missing = lambda keys: [f"FY{r['fiscal_year']}" for r in model["rows"] if any(r["metrics"][k]["value"] is None for k in keys)]
    gap = lambda years: f" Unavailable, no bar: {', '.join(years)}." if years else ""
    from datetime import date
    day = lambda iso: (lambda d: f"{d:%b} {d.day}, {d:%Y}")(date.fromisoformat(iso))
    first, last = day(model["rows"][0]["source"]["period_end"]), day(model["rows"][-1]["source"]["period_end"])
    return (f"Cash and baseline borrowing at each fiscal year end, {first} to {last}. Borrowing excludes leases; cash "
            "excludes restricted cash." + gap(missing(("cash", "gross_debt"))),
            "Operating cash flow, capital spending (below zero, a use of cash) and FCF = OCF − capital spending, for "
            "each completed fiscal year. Separate from the overlapping latest TTM."
            + gap(missing(("operating_cash_flow", "capital_spending", "free_cash_flow"))))


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
    out += '</section>' + CHARTS_MARK + '<section class="lr-obligations lr-history lr-annual">'
    for note in model["notes"]:
        out += f'<p class="lr-meta">{esc(note)}</p>'
    out += '<details><summary>Annual filing sources and presentation choices</summary>'
    for row in model["rows"]:
        sources = {f["accession"]: f for m in row["metrics"].values() for f in m["inputs"]}
        out += f'<p><strong>FY{row["fiscal_year"]}</strong>: {esc(row["source_basis"])}<br>'
        out += ' · '.join(f'<a href="{esc(f["source_url"])}">10-K filed {esc(f["filed"])} ({esc(acc)})</a>' for acc, f in sources.items())
        out += '</p>'
    return out + '</details></section>'
