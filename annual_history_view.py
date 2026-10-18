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
CHARTS_MARK = "<!-- chart:annual -->"
# Flow colors: inflow blue and use grey as in the latest-TTM chart; FCF amber, a result, distinct from both
OCF_COLOR, CAPEX_COLOR, FCF_COLOR = "#3987e5", "#9598a1", "#d4a72c"


def _day(iso):
    from datetime import date
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d:%Y}"


def latest_balances(snapshot):
    """The review's checked latest-quarter cash and borrowing: point-in-time balances like the fiscal year ends, so
    they can sit beside them (flows cannot: the latest TTM overlaps the last fiscal year)."""
    m = snapshot["metrics"]
    return {"period_end": m["cash"]["period_end"], "cash": m["cash"]["value"], "gross_debt": m["gross_debt"]["value"]}


def figures(model, latest=None):
    """Two grouped-column charts, fiscal years left to right, from the same checked rows as the table.

    Balances: cash and baseline borrowing at each fiscal year end. Flows: OCF, capital spending drawn below zero as
    a use of cash, and FCF (the result). One y-axis each, starting at zero. A missing value is None, which Plotly
    leaves as an empty slot: a gap, never a zero bar."""
    import plotly.graph_objects as go
    import theme as T
    rows = model["rows"]
    years = [f"FY{r['fiscal_year']}" for r in rows]
    ends = [_day(r["source"]["period_end"]) for r in rows]
    value = lambda key: [None if r["metrics"][key]["value"] is None else r["metrics"][key]["value"] / 1e9 for r in rows]
    capex = [None if v is None else -v for v in value("capital_spending")]

    def chart(series, title, extra=None):
        fig = go.Figure()
        for name, values, color in series:
            x, at, pattern = list(years), list(ends), [""] * len(years)
            if extra:                                   # the latest quarter: hatched, after a divider
                x.append(extra["label"]); at.append(extra["date"]); pattern.append("/")
                values = list(values) + [extra[name]]
            shown = ["Unavailable" if v is None else f"{'−' if v < 0 else ''}${abs(v):,.2f}B" for v in values]
            fig.add_trace(go.Bar(x=x, y=values, name=name,
                                 marker=dict(color=color, line=dict(width=0), pattern=dict(shape=pattern, fillmode="overlay", fgcolor=T.SURFACE, size=6, solidity=0.3)),
                                 customdata=list(zip(at, shown)),
                                 hovertemplate=f"{name}<br>%{{x}}, at %{{customdata[0]}}: %{{customdata[1]}}<extra></extra>"))
        fig.add_hline(y=0, line_color=T.TEXT_MUTED, line_width=1)
        if extra:
            fig.add_vline(x=len(years) - 0.5, line_color=T.TEXT_MUTED, line_width=1, line_dash="dot")
        fig.update_layout(height=340, margin=dict(l=56, r=8, t=48, b=36), barmode="group", bargap=0.28, bargroupgap=0.08,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=T.TEXT, size=12),
                          legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title=None),
                          xaxis=dict(type="category", fixedrange=True, showgrid=False, tickfont=dict(size=12)),
                          yaxis=dict(title=title, fixedrange=True, gridcolor=T.BORDER, zeroline=False, rangemode="tozero",
                                     tickformat=",.0f"),
                          hoverlabel=dict(font=dict(size=12)))
        return fig

    extra = None
    if latest:
        b = lambda v: None if v is None else v / 1e9
        from datetime import date
        extra = {"label": f"{date.fromisoformat(latest['period_end']):%b %Y}<br>10-Q", "date": _day(latest["period_end"]),
                 "Cash and equivalents": b(latest["cash"]), "Baseline borrowing": b(latest["gross_debt"])}
    balances = chart([("Cash and equivalents", value("cash"), T.SERIES_CASH),
                      ("Baseline borrowing", value("gross_debt"), T.SERIES_BORROWING)], "USD billions", extra)
    flows = chart([("Operating cash flow", value("operating_cash_flow"), OCF_COLOR),
                   ("Capital spending (use of cash)", capex, CAPEX_COLOR),
                   ("Free cash flow", value("free_cash_flow"), FCF_COLOR)], "USD billions")
    return balances, flows


def chart_captions(model, latest=None):
    """What each chart shows, with any Unavailable year named, so a gap is never read as zero."""
    missing = lambda keys: [f"FY{r['fiscal_year']}" for r in model["rows"] if any(r["metrics"][k]["value"] is None for k in keys)]
    gap = lambda years: f" Unavailable, no bar: {', '.join(years)}." if years else ""
    first, last = _day(model["rows"][0]["source"]["period_end"]), _day(model["rows"][-1]["source"]["period_end"])
    since = ""
    if latest:
        final = model["rows"][-1]["metrics"]
        def change(key, name):
            a, b = final[key]["value"], latest[key]
            if a is None or b is None:
                return f"{name} change Unavailable"
            d = b - a
            from decimal import Decimal, ROUND_HALF_UP   # the review's own rounding (company_review.money)
            sign = '+' if d > 0 else '−' if d < 0 else ''
            if abs(d) < 10**9:
                return f"{name} {sign}${(Decimal(abs(d)) / Decimal(10**6)).quantize(Decimal('1'), rounding=ROUND_HALF_UP):,}M"
            return f"{name} {sign}${(Decimal(abs(d)) / Decimal(10**9)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}B"
        since = (f" Hatched, after the dotted line: the latest 10-Q balance at {_day(latest['period_end'])}; since {last}, "
                 f"{change('cash', 'cash')}, {change('gross_debt', 'borrowing')}.")
    return (f"Cash and baseline borrowing at each fiscal year end, {first} to {last}.{since} Borrowing excludes leases; "
            "cash excludes restricted cash. Balances do not establish repayment coverage." + gap(missing(("cash", "gross_debt"))),
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
