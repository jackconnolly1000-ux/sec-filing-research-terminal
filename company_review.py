"""Financial questions first; filing mechanics remain available in the evidence disclosure.

The notes are selected, manually checked disclosures, not an exhaustive obligations list. Each belongs to the
pilot's specified 10-Q and remains separate from borrowing and ratios (docs/pilot_evidence_*.md).
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from ui import esc
from oracle_liquidity_view import CSS as ORACLE_LIQUIDITY_CSS
from vistra_liquidity_view import CSS as VISTRA_LIQUIDITY_CSS

NOTES = {
    "LLY": [
        {"name": "Pending AtaiBeckley acquisition", "amount": "Approximately $2.8B",
         "date": "2026-08-05", "kind": "Conditional closing payment, disclosed after quarter end", "location": "10-Q MD&A, p. 31",
         "detail": "Potential payment at closing, subject to closing conditions. Not recognized as borrowing."},
        {"name": "Venture fund commitments", "amount": "Approximately $806M",
         "date": "2026-06-30", "kind": "Unfunded commitment", "location": "10-Q MD&A, p. 31; Note 8",
         "detail": "Expected to be paid over up to ten years. Not recognized as borrowing."},
    ],
    "ORCL": [
        {"name": "Leases not yet commenced", "amount": "$288B",
         "date": "2026-08-31", "kind": "Future commitment", "location": "10-Q Note 6, p. 13",
         "detail": "Substantially all data centers; expected to commence in fiscal 2027–2029 with 15–19 year terms. Not on the balance sheet or in the lease maturities table."},
        {"name": "Operating lease liabilities", "amount": "$34.621B",
         "date": "2026-08-31", "kind": "Recognized liability", "location": "10-Q Note 6, p. 12",
         "detail": "Recognized leases, separate from borrowing and from leases not yet commenced."},
        {"name": "Finance lease liabilities", "amount": "$9.185B",
         "date": "2026-08-31", "kind": "Recognized liability", "location": "10-Q Note 6, p. 12",
         "detail": "Shown separately under this review's borrowing definition; excluded from baseline gross debt."},
        {"name": "Purchase and other obligations", "amount": "$34.150B",
         "date": "2026-08-31", "kind": "Unrecorded commitment", "location": "10-Q Note 6, p. 13",
         "detail": "Primarily cloud infrastructure components and data center power. Overlap with other commitments is not established; no combined total is presented."},
    ],
    "VST": [
        {"name": "Nuveen final payment", "amount": "$631M due Dec 31, 2026",
         "date": "2026-06-30", "kind": "Recognized purchase obligation", "location": "10-Q Note 12, p. 28",
         "detail": "Principal and interest on the minority-interest purchase. The current balance-sheet obligation is $613M. Both describe the same obligation; neither is added to baseline borrowing."},
        {"name": "Helix initial commitment", "amount": "$500M",
         "date": "2026-06-30", "kind": "Callable investment commitment", "location": "10-Q MD&A, p. 69; Note 7, p. 15",
         "detail": "Remains callable by the fund's general partner, who determines timing and amount. Amount funded to date is not separately disclosed."},
        {"name": "Helix additional commitment", "amount": "Up to $500M",
         "date": "2026-06-30", "kind": "Conditional investment commitment", "location": "10-Q MD&A, p. 69; Note 7, p. 15",
         "detail": "The specified milestones had not occurred at June 30. Vistra may also elect to fund it regardless of those milestones."},
    ],
}

LIMITS = {
    "LLY": "June lease liabilities, updated principal maturities, drawable credit and detailed payment dates remain Unavailable. The selected acquisitions and manufacturing review is not a complete review of contingencies, tax, collaboration or investment obligations.",
    "ORCL": "Commercial paper is not separately disclosed in this 10-Q. The capex-financing balance and the later status of the 10-K's $3.3B lessor guarantee remain unresolved. August 31 note and term-loan principal is dated in the principal calendar; interest payment dates and current revolver availability are Unavailable.",
    "VST": "June 30 lease liabilities are Unavailable. Derivatives, litigation and the remaining retirement-obligation detail need further review. Credit-support overlaps are unresolved; the selected notes above are not a complete obligations list.",
}

CSS = """<style>
.lr-review {max-width:1180px; margin:8px auto 0; color:var(--text); font-variant-numeric:tabular-nums;}
.lr-review * {box-sizing:border-box;}
.lr-review h2 {font-size:2rem;line-height:1.2;letter-spacing:-.025em;padding:0;margin:6px 0 12px;color:var(--text-strong);}
.lr-review h3 {font-size:1.25rem;line-height:1.35;margin:0 0 12px;padding:0;color:var(--text-strong);}
.lr-review p {font-size:.9rem;line-height:1.55;margin:8px 0;}
.lr-review .lr-meta {font-size:.78rem;color:var(--text-muted);line-height:1.5;}
.lr-lead {border-bottom:1px solid var(--border);padding:0 0 18px;}
.lr-lead .lr-plain {font-size:1.12rem;max-width:850px;color:var(--text-strong);margin-top:12px;}
.lr-lead .lr-answer {font-size:.98rem;max-width:850px;color:var(--text);margin-top:6px;}
.lr-lead .lr-terms {max-width:850px;}
.lr-summary {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;padding:18px 0;border-bottom:1px solid var(--border);}
.lr-stat-label {font-size:.8rem;color:var(--text-muted);}
.lr-stat-value {font-size:1.5rem;font-weight:650;line-height:1.5;color:var(--text-strong);}
.lr-stat-detail {font-size:.75rem;color:var(--text-muted);}
.lr-grid {display:grid;grid-template-columns:1.15fr 1fr;gap:30px;margin:24px 0;}
.lr-section {min-width:0;}
.lr-chart {margin:18px 0;}
/* Rows touch and each track fills its row, so the zero line is continuous */
.lr-bar-row {display:grid;grid-template-columns:150px minmax(40px,1fr) 85px;gap:12px;align-items:center;margin:0;min-height:38px;font-size:.8rem;}
.lr-bar-value {text-align:right;color:var(--text-strong);white-space:nowrap;}
.lr-track {display:grid;grid-template-columns:1fr 1fr;align-self:stretch;}
.lr-half {display:flex;align-items:center;min-width:0;}
.lr-half:first-child {justify-content:flex-end;border-right:1px solid var(--text-muted);}
.lr-bar {display:block;height:12px;background:var(--flow-out);min-width:1px;}
.lr-bar.in {background:var(--flow-in);}
.lr-half:first-child .lr-bar {border-radius:4px 0 0 4px;}
.lr-half:last-child .lr-bar {border-radius:0 4px 4px 0;}
.lr-row {display:flex;justify-content:space-between;gap:16px;border-bottom:1px solid var(--border);padding:10px 0;font-size:.85rem;}
.lr-row span {max-width:75%;}
.lr-row strong {white-space:nowrap;font-weight:600;}
.lr-equation {display:flex;align-items:flex-end;gap:22px;flex-wrap:wrap;margin:14px 0 6px;}
.lr-equation strong {display:block;font-size:1.35rem;font-weight:650;color:var(--text-strong);}
.lr-eq-op {font-size:1.35rem;color:var(--text-muted);padding-bottom:2px;}
@media(max-width:560px) {.lr-equation {gap:10px;flex-wrap:nowrap;} .lr-equation strong,.lr-eq-op {font-size:1.08rem;} .lr-equation .lr-stat-label {font-size:.7rem;}}
[class*="st-key-review_chart_"] {max-width:1180px;margin:0 auto;width:100%;}
.lr-review .lr-continued {border-top:0;margin-top:0;padding-top:0;}
.lr-review .op-decades h4 {font-size:1rem;font-weight:600;margin:18px 0 8px;padding:0;}
.lr-ratios {display:grid;grid-template-columns:1fr 1fr;gap:18px;border-top:1px solid var(--border);padding-top:14px;margin-top:20px;}
.lr-ratios strong {display:block;font-size:1.2rem;color:var(--text-strong);}
.lr-obligations {border-top:1px solid var(--border);padding:22px 0 8px;}
.lr-obligation {display:grid;grid-template-columns:minmax(160px,1fr) minmax(0,2fr);gap:24px;border-bottom:1px solid var(--border);padding:14px 0;}
.lr-obligation p {margin:0 0 5px;}
.lr-obligation strong {color:var(--text-strong);}
.lr-limits {padding:15px 0 4px;margin-top:36px;border-top:2px solid var(--border-strong);}
.lr-maturity {border-top:1px solid var(--border);padding:22px 0;}
.lr-maturity-row {display:grid;grid-template-columns:85px minmax(20px,1fr) 90px;gap:12px;align-items:center;margin:15px 0;font-size:.82rem;}
.lr-maturity-track {height:14px;background:var(--surface-raised);}
.lr-maturity-bar {display:block;height:14px;background:var(--text-muted);}
/* Vertical gridlines, one per scale step, so each bar reads against the dollar scale below. */
  background-image:repeating-linear-gradient(to right,var(--border-strong) 0 1px,transparent 1px 100%);background-size:calc(100% / var(--ticks)) 100%;}
/* A cut bar runs past the scale: a gap near its end marks the break, and the value says "bar cut". */
.lr-event {display:grid;grid-template-columns:145px minmax(0,1fr);gap:20px;border-top:1px solid var(--border);padding:14px 0;}
.lr-event p {margin:0 0 7px;}
.lr-review a {color:var(--link);}
.lr-history-scroll {overflow-x:auto;}
.lr-history table {width:100%;border-collapse:collapse;font-size:.85rem;}
.lr-history th,.lr-history td {padding:10px 8px;border-bottom:1px solid var(--border);text-align:right;}
.lr-history th:first-child,.lr-history td:first-child {text-align:left;}
.lr-review + .irt-evidence {max-width:1180px;margin:12px auto;}
.lr-funding {padding:22px 0;border-bottom:1px solid var(--border);}
.lr-review .lr-group {font-size:.95rem;font-weight:600;line-height:1.3;letter-spacing:.02em;color:var(--text);margin:36px 0 0;padding:14px 0 0;border-top:2px solid var(--border-strong);}
.lr-group + section {border-top:0;}
.lr-block {padding:12px 0 22px;}
.lr-annual-title {font-size:1rem;font-weight:600;color:var(--text-strong);margin:18px 0 0;max-width:1180px;}
.lr-bal-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:32px;margin:16px 0 6px;}
.lr-bal-panel h4 {display:flex;align-items:center;gap:8px;font-size:.9rem;font-weight:600;margin:0 0 6px;color:var(--text-strong);}
.lr-swatch {display:inline-block;width:10px;height:10px;border-radius:2px;flex:none;margin-right:6px;}
.lr-cash {background:var(--series-cash);}
.lr-borrowing {background:var(--series-borrowing);}
.lr-bal-row {display:grid;grid-template-columns:96px minmax(40px,1fr) 80px;gap:12px;align-items:center;margin:10px 0;font-size:.82rem;}
.lr-bal-date {color:var(--text-muted);}
.lr-bal-track {display:flex;align-items:center;height:16px;border-left:1px solid var(--border-strong);}
.lr-bal-bar {display:block;height:14px;border-radius:0 4px 4px 0;}
.lr-bal-value {text-align:right;white-space:nowrap;font-weight:600;color:var(--text-strong);}
@media(max-width:760px) {.lr-bal-grid {grid-template-columns:1fr;gap:18px;} .lr-bal-row {grid-template-columns:88px minmax(30px,1fr) 72px;gap:8px;}}
.lr-funding-row {display:grid;grid-template-columns:165px minmax(0,1fr);gap:20px;padding:12px 0;border-top:1px solid var(--border);}
.lr-funding-row h4 {font-size:.9rem;margin:8px 0;font-weight:600;}
.lr-funding-row p {margin-top:6px;}
.lr-funding .lr-meta {overflow-wrap:anywhere;}
.lr-funding details {margin-top:14px;font-size:.85rem;}
@media(max-width:760px) {.lr-funding-row {grid-template-columns:1fr;gap:0;}}
@media(max-width:760px) {.lr-grid {grid-template-columns:1fr;gap:28px;} .lr-summary {grid-template-columns:repeat(2,minmax(0,1fr));} .lr-obligation,.lr-event {grid-template-columns:1fr;gap:4px;} .lr-review h2 {font-size:1.7rem;} .lr-review h3 {font-size:1.15rem;} .lr-bar-row {grid-template-columns:112px minmax(30px,1fr) 75px;gap:7px;} .lr-stat-value {font-size:1.3rem;}}
</style>"""

# Nested style blocks are parsed as raw text by the Markdown renderer and can hide headings.
CSS = CSS.replace("</style>", ORACLE_LIQUIDITY_CSS + VISTRA_LIQUIDITY_CSS + "</style>")


def money(value, digits=2):
    if value is None:
        return "Unavailable"
    magnitude = Decimal(str(abs(value)))
    if 0 < magnitude < 1_000_000_000:
        millions = (magnitude / 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{'−' if value < 0 else ''}${millions:,.0f}M"
    billions = (magnitude / 1_000_000_000).quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)
    return f"{'−' if value < 0 else ''}${billions:,.{digits}f}B"


def pct(metric):
    return "Unavailable" if metric["value"] is None else f"{metric['value']:.1%}"


def headline(snapshot):
    m = snapshot["metrics"]
    fcf = m["free_cash_flow"]["value"]
    if fcf is None:
        return "TTM cash generation could not be established from the checked inputs."
    if fcf < 0:
        return f"TTM reported capital spending exceeded operating cash flow by {money(-fcf)}."
    if fcf == 0:
        return "TTM operating cash flow equalled reported capital spending."
    return f"TTM operating cash flow exceeded reported capital spending by {money(fcf)}."


def maturity_html(snapshot):
    """A historical principal schedule with subsequent disclosures kept on their actual dates."""
    import oracle_financing as of
    review = of.for_snapshot(snapshot)
    if review is None:
        return ""
    if review["status"] != "Checked":
        return ('<section class="lr-maturity"><h3>Debt maturity review</h3>'
                f'<p>Unavailable: {esc(review["detail"])}</p></section>')
    output = '<section class="lr-maturity"><h3>When was borrowing scheduled to be repaid?</h3>'
    output += (f'<p class="lr-meta">Historical schedule at May 31, 2026 · principal in USD billions · '
               f'<a href="{esc(review["source_url"])}" target="_blank" rel="noopener noreferrer">10-K Note 6, p. 84</a>'
               ' · fiscal years end May 31</p>')
    output += ('<p>The saved August 31 10-Q does not disclose an updated debt maturity schedule. '
               'Fiscal 2027 below includes June–August, which had already elapsed by that balance-sheet date.</p>')
    output += '<div class="lr-grid"><div>'
    # The current August calendar owns the chart. Retain annual facts here as a historical table.
    output += '<table class="ol-table"><thead><tr><th>Historical fiscal year</th><th>Principal</th></tr></thead><tbody>'
    for fact in review["buckets"][:5]:
        output += f'<tr><td>{esc(fact["label"].replace("Fiscal", "FY"))}</td><td>{esc(money(fact["value"],3))}</td></tr>'
    output += '</tbody></table>'
    output += (f'<p><strong>{esc(money(review["buckets"][5]["value"], 3))} thereafter</strong>'
               ' · fiscal 2032 onward, combined. This is not a single-year payment.</p></div><div>')
    share = f'{review["first_five_share"]:.1%}' if review["first_five_share"] is not None else "Unavailable"
    output += (f'<p>{esc(money(review["first_five_years"], 3))}, or {share} '
               f'of the {esc(money(review["total"], 3))} principal total, was scheduled through fiscal 2031 '
               'at May 31.</p>')
    c = review["controls"]
    output += (f'<p class="lr-meta">The schedule excludes interest and leases. Principal of {esc(money(review["total"], 3))} less '
               f'{esc(money(c["discount_and_costs"]["value"], 3))} of discounts and issuance costs equals '
               f'{esc(money(c["carrying_debt"]["value"], 3))} carrying debt at May 31. '
               'This reconciles to the annual balance sheet, not the later August balance sheet.</p>')
    cash = snapshot["metrics"]["cash"]["value"]
    current = snapshot["metrics"]["gross_debt"]["inputs"][0]["value"]
    output += (f'<p>At August 31, the 10-Q reports {esc(money(cash))} cash and '
               f'{esc(money(current, 3))} current borrowing. Current borrowing is a carrying amount, '
               'not a replacement for the annual principal schedule.</p>')
    output += (f'<p class="lr-meta"><a href="{esc(of.QUARTER_SOURCE)}" target="_blank" rel="noopener noreferrer">'
               '10-Q balance sheet, p. 1</a>. These figures and historical cash flows do not establish '
               'a funding surplus or shortfall for future payment dates.</p></div></div>')
    output += '<h3>What financing was reported afterward?</h3>'
    output += '<div class="lr-event"><div class="lr-meta">Jun 1–Aug 31, 2026</div><div>'
    for fact in review["quarter_flows"]:
        output += f'<p><strong>{esc(fact["label"])}: {esc(money(fact["value"], 3))}</strong></p>'
        if fact["value"] is None:
            output += f'<p class="lr-meta">Unavailable: {esc(fact["detail"])}</p>'
    output += ('<p>The cash-flow statement groups senior notes, term loans and other repayments. '
               'The MD&A separately describes about $3.1B scheduled debt repayment and $1.1B commercial-paper '
               'repayment, while the cash-flow commercial-paper row shows a dash. This unresolved '
               'presentation difference prevents assigning repayments to the old maturity buckets.</p>')
    output += (f'<p class="lr-meta"><a href="{esc(of.QUARTER_SOURCE)}" target="_blank" rel="noopener noreferrer">'
               '10-Q, pp. 5 and 33–35, filed Sep 11, 2026</a>. Quarter flows already affect the August balance sheet.</p></div></div>')
    for accession, event in of.FILINGS.items():
        output += (f'<article class="lr-event"><div class="lr-meta">Event {esc(event["event_date"])}<br>'
                   f'Filed {esc(event["filed"])}</div><div><p><strong>{esc(event["kind"])}</strong></p>'
                   f'<p>{esc(event["finding"])}</p><p class="lr-meta">'
                   f'<a href="{esc(event["source_url"])}" target="_blank" rel="noopener noreferrer">'
                   f'8-K · {esc(accession)}</a> · '
                   f'<a href="{esc(event["related"][0][1])}" target="_blank" rel="noopener noreferrer">Exhibit 99.1</a>'
                   '</p></div></article>')
    output += ('<p class="lr-meta">These two saved 8-Ks and their exhibits were checked. Neither establishes '
               'new borrowing after August 31. ')
    import oracle_revolver
    audit = oracle_revolver.for_snapshot(snapshot)
    output += ('The saved SEC financing-candidate index through October 15, 2026 lists only these two later filings. '
               if audit and audit["status"] == "Checked" else 'The saved financing-index check is Unavailable. ')
    output += ('Later or mismatched filings remain Not checked. Events are not added '
               'to the dated balance-sheet amounts.</p>')
    output += '<details><summary>Revolver terms and limits of this review</summary>'
    for term in of.TERMS:
        output += (f'<p><strong>{esc(term["label"])}</strong> · May 31, 2026<br>{esc(term["detail"])} '
                   f'<a href="{esc(term["source_url"])}" target="_blank" rel="noopener noreferrer">{esc(term["location"])}</a></p>')
    output += '<p class="lr-meta">The $10B revolver matures March 6, 2031, subject to the agreement. Capacity is not a payment due in that year.</p></details></section>'
    return output.replace("$", "&#36;")


# Where the page places the company's download: after the header, figures and funding conclusion, before the detail.
# render() ends one review section and opens the next here, so its single-string output is unchanged in effect.
SPLIT = '</section><!-- lr-download --><section class="lr-review">'


CHART_SLOT = r"<!-- chart:(\w+) -->"


def chart_slot(name, section_class):
    """Where a Plotly chart sits in the review HTML; render_app splits on it. It closes the section it interrupts and
    reopens one with the same class, so the text after the chart keeps its styles. As one string it renders nothing."""
    return f'</section><!-- chart:{name} --><section class="{section_class} lr-continued">'


def draw_chart(st, name, snapshot):
    """Draw one review chart by slot name, with its title and caption, from the same checked data as the text."""
    from charts import CHART_CONFIG
    config = {**CHART_CONFIG, "displayModeBar": False}
    if name == "annual":
        import annual_history_view
        model = annual_history_view.build(snapshot["ticker"])
        latest = annual_history_view.latest_balances(snapshot)
        charts = zip(("Cash and baseline borrowing: five fiscal year ends and the latest quarter",
                      "Annual operating cash flow, capital spending and FCF"),
                     annual_history_view.figures(model, latest), annual_history_view.chart_captions(model, latest))
    elif name == "liabilities":
        import borrowing_leases
        charts = [("Current and noncurrent total liabilities", *borrowing_leases.liability_figure(snapshot))]
    elif name == "oracle_ladder":
        import oracle_principal, oracle_principal_view
        charts = [(None, *oracle_principal_view.ladder_figure(oracle_principal.load()))]
    elif name == "oracle_bridge":
        import oracle_liquidity_view
        charts = [(None, *oracle_liquidity_view.bridge_figure(snapshot))]
    elif name == "lly_bridge":
        import lly_liquidity_view
        charts = [(None, *lly_liquidity_view.bridge_figure(snapshot))]
    else:
        raise ValueError(f"Unknown review chart {name}")
    for title, fig, caption in charts:
        if title:
            st.markdown(f'<p class="lr-annual-title">{title}</p>', unsafe_allow_html=True)
        st.plotly_chart(fig, width="stretch", theme=None, config=config)
        if caption:
            st.caption(caption.replace("$", "\\$"))   # two "$" would otherwise render as LaTeX math


    if name == "oracle_ladder":
        with st.expander("Debt detail — alternative views"):
            import debt_detail
            choice=st.selectbox("Principal view",["Maturity concentration","Fixed-rate coupon distribution","Instrument composition"],key="review_debt_detail_ORCL")
            model=debt_detail.build()
            st.plotly_chart(debt_detail.figure(model,choice),width="stretch",theme=None,config=config,key="review_debt_detail_chart")
            st.caption(model["note"].replace("$","\\$"))
            if choice=="Fixed-rate coupon distribution":st.caption("Height is principal; color is principal-weighted fixed coupon. Floating SOFR spreads and term-loan amortization rates are excluded.")
    if name == "annual":
        with st.expander("Historical cash generation relative to borrowing"):
            fig,caption=annual_history_view.funding_history(model)
            st.plotly_chart(fig,width="stretch",theme=None,config=config,key="review_flow_debt_"+snapshot["ticker"])
            st.caption(caption)


def ttm_equation(flow, money):
    """The latest TTM as one line: OCF − capital spending = FCF. Three figures, so long bars don't repeat the
    five-year chart below; that chart covers completed fiscal years, this the overlapping latest TTM."""
    (ocf_name, ocf), (_, capex), (fcf_name, fcf) = flow
    cells = ((ocf_name, money(ocf)), ("Capital spending", "Unavailable" if capex is None else money(-capex)),
             (fcf_name, money(fcf)))
    out = '<div class="lr-equation" role="group" aria-label="TTM operating cash flow less capital spending equals free cash flow">'
    for k, (label, shown) in enumerate(cells):
        if k:
            out += f'<span class="lr-eq-op" aria-hidden="true">{"−" if k == 1 else "="}</span>'
        out += f'<div><span class="lr-stat-label">{esc(label)}</span><strong>{esc(shown)}</strong></div>'
    return out + '</div>'


def render(snapshot):
    """Deterministic, source-linked explanations; no ratings or implied repayment assumptions."""
    m = snapshot["metrics"]
    end = date.fromisoformat(m["cash"]["period_end"]).strftime("%b %d, %Y")
    source = snapshot["source_url"]
    output = CSS + '<section class="lr-review">'
    output += f'<header class="lr-lead"><div class="lr-meta">{esc(snapshot["ticker"])} · Debt and liquidity review</div>'
    output += f'<h2>{esc(snapshot["company_name"])}</h2><div class="lr-meta">Balance sheet: {esc(end)} · '
    output += f'<a href="{esc(source)}" target="_blank" rel="noopener noreferrer">Source 10-Q</a> · Balance-sheet facts checked {esc(snapshot["checked_as_of"])}</div>'
    from funding_conclusions import plain_answer, terms_html, render as funding_html
    # The plain answer first; the historical comparison follows it, so a favourable past figure isn't read as the answer
    output += plain_answer(snapshot)
    output += f'<p class="lr-answer">Historical: {esc(headline(snapshot))}</p>'
    output += '<p class="lr-meta">Cash flows cover the trailing twelve months to this balance-sheet date. Borrowing is at carrying amount and excludes leases. Figures are rounded; evidence retains exact inputs.</p>' + terms_html() + '</header>'
    output += '<div class="lr-summary">'
    for label, value, detail in (
        ("Cash and equivalents", money(m["cash"]["value"]), "Excludes restricted cash"),
        ("Baseline gross debt", money(m["gross_debt"]["value"]), "Borrowing, excluding leases"),
        ("Net debt", money(m["net_debt"]["value"]), "Gross debt less cash"),
        ("Current ratio", f'{m["current_ratio"]["value"]:.2f}x' if m["current_ratio"]["value"] is not None else "Unavailable", "Current assets / current liabilities"),
    ):
        # The same identity swatch as the balance chart, so the headline figure and its bars read as one quantity
        swatch = {"Cash and equivalents": "cash", "Baseline gross debt": "borrowing"}.get(label)
        mark = f'<span class="lr-swatch lr-{swatch}" aria-hidden="true"></span>' if swatch else ''
        output += f'<div><div class="lr-stat-label">{mark}{esc(label)}</div><div class="lr-stat-value">{esc(value)}</div><div class="lr-stat-detail">{esc(detail)}</div></div>'
    output += '</div>' + funding_html(snapshot) + SPLIT
    # Financial order: what the company owes, the cash it generates, how cash was funded, when debt falls due and what
    # could pay it, how earnings covered interest, how balances changed, then what stays unresolved. Each group but the
    # last gets a label; "What remains unresolved?" carries its own rule.
    group = lambda label: f'<div class="lr-group" role="heading" aria-level="2">{esc(label)}</div>'
    output += group("What it owes") + '<section class="lr-section lr-block">'
    import borrowing_leases
    try:
        borrowing_model = borrowing_leases.build(snapshot)
        output += borrowing_leases.render_borrowing(borrowing_model, money)
        output += chart_slot("liabilities", "lr-section")
    except (OSError, ValueError, KeyError, TypeError):
        borrowing_model = None
        output += '<h3>Borrowing and lease presentation unavailable</h3><p>The checked evidence is missing or does not match this review.</p>'
    output += '</section>'
    if borrowing_model is not None:
        output += borrowing_leases.render_leases(borrowing_model, money)
    output += '<section class="lr-obligations"><h3>What sits outside baseline borrowing?</h3><p class="lr-meta">Selected disclosures, each shown separately. Commitments are not all payable now and are not added to debt or to each other.</p>'
    for item in NOTES[snapshot["ticker"]]:
        # The legacy workbook still consumes NOTES; the app shows these in its dedicated lease section.
        if snapshot["ticker"] == "ORCL" and item["name"] in {
                "Leases not yet commenced", "Operating lease liabilities", "Finance lease liabilities"}:
            continue
        output += (f'<article class="lr-obligation"><div><p><strong>{esc(item["name"])}</strong></p>'
                   f'<p>{esc(item["amount"])}</p><div class="lr-meta">As of {esc(item["date"])} · {esc(item["kind"])}</div></div>'
                   f'<div><p>{esc(item["detail"])}</p><a class="lr-meta" href="{esc(source)}" target="_blank" rel="noopener noreferrer">{esc(item["location"])}</a></div></article>')
    output += '</section>'
    output += group("Cash generation and liquidity")
    output += '<section class="lr-section lr-block"><h3>What remained after capital spending?</h3>'
    output += f'<div class="lr-meta">TTM ended {esc(end)} · USD billions · 10-K and 10-Q cash-flow statements</div>'
    import core_charts
    output += ttm_equation(core_charts.build(snapshot)["flow"], money)
    output += f'<p class="lr-meta">{esc(m["free_cash_flow"]["notes"][0])}</p>'
    output += '<div class="lr-ratios">'
    for key, label in (("ocf_to_debt", "TTM operating cash flow / debt"), ("fcf_to_debt", "TTM free cash flow / debt")):
        output += f'<div><span class="lr-stat-label">{esc(label)}</span><strong>{esc(pct(m[key]))}</strong></div>'
    output += '</div><p class="lr-meta">Historical flows relative to period-end borrowing; these percentages are not repayment forecasts. FCF excludes acquisitions, dividends and other cash uses.</p>'
    assets = m["current_ratio"]["inputs"]["current_assets"]
    liabilities = m["current_ratio"]["inputs"]["current_liabilities"]
    if assets["value"] is not None and liabilities["value"] is not None:
        gap = assets["value"] - liabilities["value"]
        direction = "exceeded" if gap >= 0 else "were below"
        output += (f'<p>Current assets of {esc(money(assets["value"]))} {direction} current liabilities of '
                   f'{esc(money(liabilities["value"]))} by {esc(money(abs(gap)))}.</p>')
    output += '<p class="lr-meta">Current assets include items other than cash. This comparison does not establish whether specific payments can be met; a maturity schedule and financing terms are still needed.</p></section>'
    output += group("Funding and repayment")
    from oracle_liquidity_view import render as oracle_liquidity_html
    output += oracle_liquidity_html(snapshot, money)
    from vistra_liquidity_view import render as vistra_liquidity_html
    output += vistra_liquidity_html(snapshot, money)
    from lly_liquidity_view import render as lilly_liquidity_html
    output += lilly_liquidity_html(snapshot, money)
    output += maturity_html(snapshot)   # Oracle's historical May 31 schedule and later financing, after its current calendar
    output += group("Interest coverage")
    from lly_interest_view import render as lilly_interest_html
    output += lilly_interest_html(snapshot, money)
    from oracle_interest_view import render as oracle_interest_html
    output += oracle_interest_html(snapshot, money)
    from vistra_interest_view import render as vistra_interest_html
    output += vistra_interest_html(snapshot, money)
    output += group("Change over time")
    import company_history
    output += company_history.render(snapshot, money)
    import annual_history_view
    output += annual_history_view.render(snapshot["ticker"])
    output += '<section class="lr-limits"><h3>What remains unresolved?</h3>'
    remaining = {"VST": "Historical interest-component coverage is shown above. Receivables/Nuveen allocation, Other composition and an all-in financing-cost denominator remain Unavailable.",
                 "ORCL": "Historical reported-line interest coverage is shown above; borrowing-only coverage, capitalization basis and covenant headroom remain Unavailable.",
                 "LLY": "Historical interest coverage uses derived operating income; its capitalization and other limits are stated above."}[snapshot["ticker"]]
    output += f'<p class="lr-meta">{esc(LIMITS[snapshot["ticker"]])} {remaining}</p></section></section>'
    return output.replace("$", "&#36;")


def evidence_html(snapshot: dict) -> str:
    """Read-only display; every input keeps its filing and selection information."""
    import ui
    from liquidity_pilot import leaf_inputs
    import ratio_review
    reconciled = {r["key"]: r for r in ratio_review.build(snapshot)["rows"]}
    metrics = snapshot["metrics"]
    output = '<details class="irt-evidence"><summary>Calculations and filing evidence</summary>'
    for key, metric in metrics.items():
        row = reconciled[key]
        output += f'<p><strong>{ui.esc(metric["label"])}</strong>'
        period = ((row["period_start"] + " to ") if row["period_start"] else "As of ") + row["period_end"]
        output += f'<br>{ui.esc(ratio_review.display(row))} · {ui.esc(period)}'
        if metric.get("formula"):
            output += f' · {ui.esc(metric["formula"])}'
        if metric["value"] is None:
            output += f'<br>Unavailable: {ui.esc(metric["detail"])}'
        for note in metric.get("notes", []):
            output += f'<br>{ui.esc(note)}'
        output += f'<br>{ui.esc(row["basis"])}'
        output += '</p><ul class="irt-ol" style="overflow-wrap:anywhere">'
        # Ratios and net debt reference the metrics already documented above.
        facts = [] if metric.get("unit") == "fraction" or metric["label"] in {"Net debt", "Free cash flow"} else leaf_inputs(metric)
        for fact in facts:
            value = f"{fact['value']:,.0f} USD" if fact["value"] is not None else "Unavailable"
            context = (f" · Context {fact['context_id']}, scale {fact['scale']}, decimals {fact['decimals']}"
                       if fact.get("context_id") else "")
            period = ((fact["period_start"] + " to ") if fact.get("period_start") else "") + fact["period_end"]
            output += (f'<li>{ui.esc(fact["label"])}: {ui.esc(value)} · {ui.esc(fact["tag"])}<br>'
                       f'Period {ui.esc(period)} · {ui.esc(fact.get("form") or "Form unavailable")} '
                       f'filed {ui.esc(fact.get("filed") or "Unavailable")} · '
                       f'{ui.esc(fact.get("accession") or "Accession unavailable")}<br>'
                       f'{ui.esc(fact.get("selection_rule") or fact.get("detail", ""))}{ui.esc(context)}'
                       f'<br><a href="{ui.esc(fact.get("source_url") or snapshot["source_url"])}" target="_blank" rel="noopener noreferrer">Source filing</a></li>')
        output += '</ul>'
    import company_history
    import borrowing_leases
    history = company_history.build(snapshot)
    lease_model = borrowing_leases.build(snapshot)
    lease_inputs = []
    for item in lease_model["leases"]:
        lease_inputs.extend(item.get("inputs", []))
        if item.get("reported_total"):
            lease_inputs.append(item["reported_total"])
    if lease_model["commitment"]["value"] is not None:
        lease_inputs.append(lease_model["commitment"])
    groups = [("Annual history source inputs", history["annual_facts"] + history["annual_flows"]),
              ("Lease source inputs", lease_inputs)]
    for heading, inputs in groups:
        output += f'<h4>{ui.esc(heading)}</h4><ul class="irt-ol" style="overflow-wrap:anywhere">'
        for fact in inputs:
            period = ((fact["period_start"] + " to ") if fact.get("period_start") else "As of ") + fact["period_end"]
            output += (f'<li>{ui.esc(fact.get("label") or fact["tag"])}: {fact["value"]:,.0f} USD · {ui.esc(fact["tag"])}<br>'
                       f'{ui.esc(period)} · {ui.esc(fact["form"])} filed {ui.esc(fact["filed"])} · {ui.esc(fact["accession"])}<br>'
                       f'{ui.esc(fact["selection_rule"])} · Context {ui.esc(fact.get("context_id") or "Unavailable")} · '
                       f'scale {ui.esc(fact.get("scale"))} · decimals {ui.esc(fact.get("decimals"))}<br>'
                       f'<a href="{ui.esc(fact["source_url"])}" target="_blank" rel="noopener noreferrer">Source filing</a></li>')
        output += '</ul>'
    debt = metrics["gross_debt"]
    # The reconciled borrowing explanation already includes filing-specific caveats;
    # metric notes were displayed with the calculation above.
    caveats = []
    if debt.get("not_added"):
        caveats.append("Excluded from baseline debt: " + debt["not_added"])
    output += ''.join(f'<p class="irt-note">{ui.esc(n)}</p>' for n in caveats)
    return output + '</details>'


def workbook(snapshots: list[dict]) -> bytes:
    """Compatibility API using the common authored-template exporter."""
    from summary_export import workbook as export
    return export(snapshots)



def saved_workbook(snapshots, folder=None, ticker=None):
    """Serve the styled export only with the exact source snapshots used to build it."""
    import hashlib
    import json
    from pathlib import Path
    folder = Path(folder) if folder is not None else Path(__file__).parent / "samples"
    try:
        if ticker not in {None, "LLY"}:
            return None
        stem = "lly_liquidity" if ticker == "LLY" else "liquidity_pilots"
        manifest = json.loads((folder / f"{stem}.manifest.json").read_text())
        saved = json.loads((folder / "liquidity_pilots.json").read_text())
        if snapshots != saved["snapshots"]:
            return None
        if ticker == "LLY":
            from workbook_manifest import common_matches
            if not common_matches(manifest):
                return None
            import funding_conclusions as funding
            if manifest.get("funding_sha256") != funding.fingerprint() or funding.load(ticker, folder) is None:
                return None
        expected = {"liquidity_pilots.json", "lly_liquidity.json", "lly_financing.json", "lly_interest.json"} if ticker else {"liquidity_pilots.json", "oracle_financing.json"}
        for name, digest in manifest["sources"].items():
            if name not in expected:
                return None
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
                return None
        if set(manifest["sources"]) != expected:
            return None
        content = (folder / f"{stem}.xlsx").read_bytes()
        return content if hashlib.sha256(content).hexdigest() == manifest["workbook_sha256"] else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


SELECTOR_NAMES = {"LLY": "Eli Lilly", "ORCL": "Oracle", "VST": "Vistra"}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render_download(st, snapshot, snapshots) -> None:
    """Each company's checked workbook, served only while its manifest still matches the saved sources."""
    ticker = snapshot["ticker"]
    import export_guide
    st.caption(export_guide.CAPTION)
    if ticker == "LLY":
        content = saved_workbook(snapshots, ticker="LLY")
        if content:
            st.download_button("Download LLY review and evidence", content,
                file_name="Lilly_Liquidity_2026-06-30.xlsx", mime=XLSX, key="review_download_LLY", on_click="ignore")
        else:
            st.caption("Lilly review workbook Unavailable: its saved sources must match the workbook.")
    if ticker == "VST":
        import vistra_liquidity as vl
        review = vl.for_snapshot(snapshot)
        content = vl.workbook_bytes(review) if review else None
        if content:
            st.download_button("Download VST review and evidence", content,
                file_name="Vistra_Liquidity_2026-06-30.xlsx", mime=XLSX, key="review_download_VST", on_click="ignore")
        else:
            st.caption("Vistra repayment workbook Unavailable: its saved review must match the workbook.")
    if ticker == "ORCL":
        import oracle_liquidity as ol
        review = ol.for_snapshot(snapshot)
        content = ol.workbook_bytes(review) if review else None
        if content:
            st.download_button("Download ORCL review and evidence", content,
                file_name="Oracle_Liquidity_2026-08-31.xlsx", mime=XLSX, key="review_download_ORCL", on_click="ignore")
        else:
            st.caption("Oracle cash-analysis workbook Unavailable: its saved source review must match the workbook.")


def render_app() -> None:
    """The app's default page: pick a checked company and its saved review opens directly.

    Only the selected review and its workbook are built, so the page makes no SEC, Yahoo or Claude request and
    needs no secrets. The selection survives a visit to general filing research (persist_state="session")."""
    import json
    import streamlit as st
    from ui import notice
    from liquidity_pilot import SAMPLE, financing_html
    try:
        saved = json.loads(SAMPLE.read_text(encoding="utf-8"))
        snapshots = {s["ticker"]: s for s in saved["snapshots"]}
    except (OSError, ValueError, KeyError, TypeError):
        snapshots = {}
    if not snapshots:
        st.markdown(notice("Saved reviews unavailable", "The saved debt and liquidity reviews could not be loaded. "
                           "No live figures are substituted.", "caution"), unsafe_allow_html=True)
        return
    # A selection from an older session (or a company no longer saved) falls back to the first checked review.
    if st.session_state.get("review_company") not in snapshots:
        st.session_state.review_company = next(iter(snapshots))
    ticker = st.segmented_control(
        "Company", list(snapshots), required=True, key="review_company", persist_state="session",
        format_func=lambda t: f"{SELECTOR_NAMES.get(t, t)} ({t})")
    snapshot = snapshots[ticker]
    st.caption("Saved filing reviews · source dates shown in each review · no live or paid request")
    import simulation_view
    if simulation_view.available(snapshot):
        # A separate view, not a section of the review: the scenario's figures are assumptions, so they never sit
        # in the same flow as checked filing facts. The choice survives switching companies and pages.
        if st.session_state.get("review_view") not in simulation_view.VIEWS:
            st.session_state.review_view = simulation_view.VIEWS[0]
        view = st.segmented_control("View", simulation_view.VIEWS, required=True, key="review_view",
                                    persist_state="session")
        if view == simulation_view.VIEWS[1]:
            simulation_view.render(st, snapshot)
            return
    try:
        page = render(snapshot)
        tail = evidence_html(snapshot) + financing_html(snapshot)
    except (OSError, KeyError, TypeError, ValueError):
        # A saved file edited out of shape shows a stated gap, not a stack trace or partial figures.
        import traceback
        traceback.print_exc()
        st.markdown(notice(f"{ticker} review unavailable", "This saved review is incomplete or out of date, so it is "
                           "not shown. The other saved reviews are unaffected.", "caution"), unsafe_allow_html=True)
        return
    # The reader sees the company, its figures and the funding conclusion before being offered the workbook
    head, body = page.split(SPLIT, 1)
    st.markdown(head + '</section>', unsafe_allow_html=True)
    render_download(st, snapshot, saved["snapshots"])
    # The review HTML marks where each Plotly chart goes (<!-- chart:name -->); draw it there, in the review's column
    import re
    parts = re.split(CHART_SLOT, body)
    st.markdown('<section class="lr-review">' + parts[0] + '</section>', unsafe_allow_html=True)   # first block's styles apply page-wide
    for name, rest in zip(parts[1::2], parts[2::2]):
        with st.container(key=f"review_chart_{name}"):
            draw_chart(st, name, snapshot)
        st.markdown('<section class="lr-review">' + rest + '</section>', unsafe_allow_html=True)
    if simulation_view.available(snapshot):
        st.caption(f"An illustrative stress scenario for these obligations is under View → {simulation_view.VIEWS[1]}, "
                   "above. It uses stated assumptions and does not change this review.")
    st.markdown(tail, unsafe_allow_html=True)
    with st.expander("Optional combined export"):
        import export_guide
        st.caption(export_guide.COMBINED_CAPTION)
        content = saved_workbook(saved["snapshots"])
        if content:
            st.download_button("Download three-company metric summary (optional)", content,
                file_name="Liquidity_Pilot_2026-10-14.xlsx", mime=XLSX, key="review_download_summary", on_click="ignore")
        else:
            st.caption("Combined workbook Unavailable: its saved sources must match the workbook.")
