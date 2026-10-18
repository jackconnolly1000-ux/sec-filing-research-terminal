"""Oracle's dated borrowing principal at August 31, 2026, for the company review (model: oracle_principal.py)."""
from datetime import date

from ui import esc


def ladder_years(review):
    """Dated note and term-loan principal in every fiscal year from the remainder of FY2027 to the last maturity.

    One scale for all years: no single year exceeds about $11B, so nothing is cut. Refused (ValueError) unless the
    years add up to the checked principal total; commercial paper has no dates and is excluded, never a zero."""
    import oracle_principal as op
    last = max(op.fiscal_year(r["maturity"]) for r in review["remaining"] if r["maturity"])
    years = []
    for fy in range(2027, last + 1):
        start = "2026-09-01" if fy == 2027 else f"{fy - 1}-06-01"
        years.append({"fy": fy, "label": "Rem. FY2027" if fy == 2027 else f"FY{fy}", "start": start, "end": f"{fy}-05-31",
                      "principal": op.principal_between(review, start, f"{fy}-05-31")})
    if sum(y["principal"] for y in years) != review["reconciliation"]["known_principal_excluding_cp"]:
        raise ValueError("Fiscal-year principal does not add up to the checked calendar")
    return years


def ladder_figure(review):
    """The first ten fiscal years on a readable annual scale; full calendar remains reconciled below."""
    import plotly.graph_objects as go
    import theme as T
    years = ladder_years(review)[:10]
    nice = lambda iso: (lambda d: f"{d:%b} {d.day}, {d:%Y}")(date.fromisoformat(iso))
    labels = [y["label"] for y in years]
    fig = go.Figure(go.Bar(
        x=labels, y=[y["principal"] / 1e9 for y in years], marker=dict(color=T.SERIES_BORROWING, line=dict(width=0)),
        customdata=[(nice(y["start"]), nice(y["end"]), f"${y['principal'] / 1e9:,.3f}B" if y["principal"] else "none dated")
                    for y in years],
        hovertemplate="%{x}: %{customdata[0]} – %{customdata[1]}<br>Principal due: %{customdata[2]}<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=56, r=8, t=12, b=54), bargap=0.35, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=T.TEXT, size=12), showlegend=False,
                      xaxis=dict(type="category", fixedrange=True, showgrid=False, tickangle=-45,
                                 tickfont=dict(size=10),
                                 tickvals=labels,ticktext=["FY27*" if y["fy"]==2027 else f"FY{y['fy']%100:02d}" for y in years]),
                      yaxis=dict(title="USD billions", fixedrange=True, gridcolor=T.BORDER, zeroline=True,
                                 zerolinecolor=T.TEXT_MUTED, rangemode="tozero"))
    near = review["next_twelve_months"]["principal"]
    first = years[0]["principal"]
    caption = (f"Chart shows the first ten fiscal years (June–May), FY2027–FY2036, on one scale. FY27* is the remainder starting September 2026. "
               "The dated table below covers the complete calendar, including later years; no column here means no dated principal in that year. "
               f"The ${near / 1e9:,.3f}B due September 2026–August 2027 "
               f"is the FY2027 remainder (${first / 1e9:,.3f}B) plus June–August 2027 (${(near - first) / 1e9:,.3f}B of FY2028). "
               "Excludes commercial paper (Unavailable), interest and leases. The term-loan date may be extended; "
               "this is not funding coverage.")
    return fig, caption


def decades(review, money):
    """The cut FY2032-onward bar, split by decade, so its $90B is not one undifferentiated amount."""
    import oracle_principal as op
    rows = op.by_decade(review)
    output = '<div class="op-decades"><h4>FY2032 onward, by decade</h4>'
    if rows is None:
        return output + '<p class="lr-meta">Unavailable: the decades do not add up to the combined amount.</p></div>'
    nice = lambda iso: (lambda d: f"{d:%b} {d.day}, {d:%Y}")(date.fromisoformat(iso))
    output += ('<div class="ol-table-wrap"><table class="ol-table"><thead><tr><th>Fiscal years</th><th>Period</th>'
               '<th>Principal</th></tr></thead><tbody>')
    for r in rows:
        output += (f'<tr><td>{esc(r["label"])}</td><td>{esc(nice(r["start"]))} – {esc(nice(r["end"]))}</td>'
                   f'<td>{esc(money(r["principal"], 3))}</td></tr>')
    total = sum(r["principal"] for r in rows)
    return output + (f'<tr><td>FY2032 onward</td><td>All dated principal from FY2032</td><td>{esc(money(total, 3))}</td></tr>'
                     '</tbody></table></div><p class="lr-meta">Senior notes at their stated maturities; no term loan or '
                     'commercial paper falls in these years. Principal only, excluding interest.</p></div>')


def render(snapshot, money):
    """Oracle's August 31 principal by instrument and date; commercial paper stays Unavailable.

    Shown directly under the dated lease and purchase payments, so everything due soon reads in one place."""
    import oracle_principal as op
    from oracle_principal import percent
    cash = snapshot.get("metrics", {}).get("cash", {})
    if (snapshot.get("ticker"), cash.get("accession"), cash.get("period_end")) != ("ORCL", op.QUARTERLY["accession"], op.ANCHOR):
        return ""
    review = op.load()
    output = '<section class="lr-maturity"><h3>Which borrowing principal is due after August 31?</h3>'
    if review is None:
        return output + '<p>Unavailable: the saved principal calendar is missing or its checks do not agree.</p></section>'
    rec, near = review["reconciliation"], review["next_twelve_months"]
    link = lambda doc, text: f'<a href="{esc(doc["source_url"])}" target="_blank" rel="noopener noreferrer">{esc(text)}</a>'
    tl = review["term_loan"]
    output += (f'<p class="lr-meta">At August 31, 2026 · principal, excluding interest · instruments from the '
               f'{link(review["annual"], "10-K debt table, Note 6, pp. 83–84")}, carried forward with the '
               f'{link(review["quarter"], "August 10-Q")} · checked {esc(review["checked_as_of"])}</p>')
    installments = sum(s["amount"] for s in tl["installments"] if op.ANCHOR < s["date"] <= near["end"])
    output += (f'<p class="lr-answer">{esc(money(near["principal"], 3))} of senior-note and term-loan principal falls due '
               f'from September 2026 through August 2027: {esc(money(2_250_000_000, 3))} of notes on April 1, 2027, and the '
               f'term loan’s {esc(money(installments, 3))} of installments and {esc(money(tl["final"]["amount"], 3))} remainder on '
               'August 16, 2027. Commercial paper is not included: its August balance and maturity dates are not reported.</p>')
    from company_review import chart_slot
    output += '<p class="lr-annual-title">Principal due, FY2027–FY2036 · USD billions</p>' + chart_slot("oracle_ladder", "lr-maturity")
    output += decades(review, money)
    output += '<div class="lr-grid"><div><h4>Next twelve months</h4><div class="ol-table-wrap"><table class="ol-table">'
    output += '<thead><tr><th>Due</th><th>Instrument</th><th>Principal</th></tr></thead><tbody>'
    for row in near["rows"]:
        day = date.fromisoformat(row["date"])
        # Installments are 2.50% of $5,630M, $140.75M each: shown exactly, since rounding hides that they sum to $563M
        amount = (f'${row["amount"] / 1_000_000:,.2f}M' if row["amount"] % 1_000_000 else money(row["amount"], 3))
        label = "Term loan installment" if row["label"].startswith("Term loan, scheduled") else row["label"]
        output += (f'<tr><td>{esc(f"{day:%b} {day.day}, {day:%Y}")}</td><td>{esc(label)}</td>'
                   f'<td>{esc(amount)}</td></tr>')
    output += (f'<tr><td>No dates disclosed</td><td>Commercial paper</td><td>Unavailable</td></tr></tbody></table></div>'
               '<p class="lr-meta">Term-loan installments are 2.50% of the $5.630B borrowed, calculated from its stated amortization. They assume no prepayment and are '
               'not separately reported. Oracle may extend the August 16, 2027 date by up to two years.</p></div>')
    output += '<div><h4>By fiscal year</h4><div class="ol-table-wrap"><table class="ol-table">'
    output += '<thead><tr><th>Fiscal year</th><th>Period</th><th>Principal</th></tr></thead><tbody>'
    for bucket in review["calendar"]:
        nice = lambda iso: (lambda d: f"{d:%b} {d.day}, {d:%Y}")(date.fromisoformat(iso))
        period = (f'{nice(bucket["start"])} – {nice(bucket["end"])}' if bucket["end"] else f'From {nice(bucket["start"])}')
        output += f'<tr><td>{esc(bucket["label"])}</td><td>{esc(period)}</td><td>{esc(money(bucket["principal"], 3))}</td></tr>'
    output += (f'<tr><td>Total</td><td>Excludes commercial paper</td><td>{esc(money(rec["known_principal_excluding_cp"], 3))}</td></tr>'
               '</tbody></table></div><p class="lr-meta">FY2028 includes the term-loan remainder. Only fiscal 2027 differs from '
               'the May 31 schedule: the July 2026 notes and the June 30 installment fell due before August 31, and '
               'commercial paper is no longer counted.</p></div></div>')
    lo, hi = rec["commercial_paper_range"]
    dlo, dhi = rec["implied_discount_range"]
    output += '<details><summary>How principal reconciles to reported borrowing</summary>'
    output += (f'<p><strong>Principal versus carrying value.</strong> The August balance sheet reports '
               f'{esc(money(rec["carrying_reported"], 3))} of borrowing at carrying value ({esc(money(rec["current_reported"], 3))} '
               f'current, {esc(money(rec["noncurrent_reported"], 3))} noncurrent). Carrying value is principal less unamortized '
               'discounts and issuance costs. At May 31 those were $564M: $130.105B principal less $564M equals $129.541B '
               'carrying debt.</p>')
    output += (f'<p><strong>Long-term borrowing.</strong> Senior-note and term-loan principal of '
               f'{esc(money(rec["known_principal_excluding_cp"], 3))} compares with long-term carrying value the 10-Q reports '
               f'as $125.0B, rounded to $0.1B (Note 2, p. 9). The implied August discount and issuance costs are '
               f'{esc(money(dlo))}–{esc(money(dhi))}, consistent with $564M at May 31 less amortization. They are not '
               'reported at August 31, so no exact figure is shown.</p>')
    output += (f'<p><strong>Commercial paper.</strong> $1.468B at May 31, with no maturity dates disclosed. Total carrying '
               f'borrowing less the rounded long-term figure leaves about {esc(money(lo))}–{esc(money(hi))} at August 31. '
               'That range rests on a rounded fact, so the August balance is Unavailable.</p>')
    note = review["matured"][0]
    output += (f'<p><strong>June–August repayments.</strong> The July 2026 notes ({esc(money(note["principal_may_31"], 3))}, '
               f'{esc(percent(note["stated_rate"]))}%) matured on July 15, 2026, '
               f'and the term loan’s June 30 installment was scheduled at $70.4M. Together, '
               f'{esc(money(rec["scheduled_principal_quarter"], 3))} agrees with MD&A’s “$3.1 billion … scheduled repayments of '
               f'debt”. The cash-flow line groups {esc(money(rec["repayments_quarter"], 3))} of note, term-loan and other '
               'repayments. MD&A separately describes about $1.1B of commercial-paper repayment, while the commercial-paper '
               'row is a reported zero. The 10-Q does not assign the grouped line to instruments, so it is not subtracted '
               'from any balance.</p>')
    output += ('<p class="lr-meta">No borrowing proceeds are reported for the quarter. MD&A’s $4.6B of long-term borrowing '
               'reclassified to current agrees with the term loan’s June 2027 installment and remainder entering the '
               'twelve-month window. A principal calendar is not funding coverage and does not establish drawable credit.</p>')
    output += f'<p class="lr-meta">Sources: {link(review["annual"], "10-K Note 6, pp. 83–86")} · {link(review["quarter"], "10-Q pp. 1, 5, 9 and 33")}</p></details>'
    output += f'<details><summary>All {len(review["remaining"])} instruments outstanding at August 31</summary>'
    output += '<div class="ol-table-wrap"><table class="ol-table"><thead><tr><th>Instrument</th><th>Maturity</th><th>Principal</th><th>Basis</th></tr></thead><tbody>'
    for row in review["remaining"]:
        value = "Unavailable" if row["principal_aug_31"] is None else money(row["principal_aug_31"], 3)
        output += (f'<tr><td>{esc(row["label"])}</td><td>{esc(row["maturity"] or "Not disclosed")}</td>'
                   f'<td>{esc(value)}</td><td>{esc(row["status"])}</td></tr>')
    output += '</tbody></table></div></details></section>'
    return output
