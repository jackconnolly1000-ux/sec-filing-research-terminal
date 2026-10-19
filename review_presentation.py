"""Progressive disclosure for checked reviews; source models and their missing values stay intact."""
from html import escape


GAPS = {
    "LLY": (
        ("Debt payment calendar", "Current borrowing is reported; a complete remaining principal calendar is not established.",
         "Prevents matching all maturities to cash on payment dates.", "A reconciled schedule of remaining principal by instrument and date."),
        ("Credit after facility expiry", "The saved evidence does not establish renewal of the facility expiring in August 2026.",
         "Historical unused commitments cannot establish later drawable funds.", "Renewal terms, dated usage and evidence of compliance with draw conditions."),
        ("Acquisitions and manufacturing", "Several closing dates, payment schedules and commitment overlaps are unresolved.",
         "These uses compete with repayments and are outside the simple OCF-less-capex calculation.", "Closing disclosures and payment schedules reconciled to prior commitments."),
        ("Leases and interest definitions", "June lease balances and the interim interest-capitalization basis are not established.",
         "Older lease balances keep their own dates; earnings coverage retains its stated denominator limits.", "Dated lease disclosures and a reconciliation of interest expense and capitalization."),
    ),
    "ORCL": (
        ("Commercial paper and capex financing", "The August 10-Q does not establish exact separate balances or repayment dates.",
         "The dated note/term-loan calendar is useful but does not cover all financing obligations.", "An instrument-level balance and maturity reconciliation; financing proceeds are not a balance."),
        ("Drawable revolver credit", "The agreement establishes a commitment; May usage is reported, but August usage and borrowing-date conditions are not established.",
         "The $10B commitment cannot be treated as cash available for a future payment.", "Same-date facility usage and evidence covering covenant and other draw conditions."),
        ("Infrastructure payment timing", "Annual payments on uncommenced leases and overlap among purchase obligations, unpaid capex and leases are unresolved.",
         "The obligations cannot be combined into a complete dated cash-use total.", "Commencement schedules and disclosures allocating the overlapping obligations."),
        ("Future cash generation and interest", "Future OCF/prepayment recurrence is uncertain; the reported interest line's full composition and capitalization basis are unstated.",
         "Historical cash generation is evidence, not a forecast; reported-line coverage is not covenant headroom.", "Explicit assumptions for scenarios; later actual cash flows and a contractual interest reconciliation for checked updates."),
    ),
    "VST": (
        ("Cash access and credit conditions", "Parent-accessible cash, the current borrowing base and compliance with draw conditions are not established.",
         "Consolidated reported liquidity does not establish which borrower can fund which payment.", "Cash by borrower, transfer restrictions and dated facility/compliance evidence."),
        ("Remaining debt service", "Selected maturities and project obligations are dated; the complete current repayment calendar is not established.",
         "Selected payments cannot be treated as total debt service.", "A reconciled calendar including principal, interest and borrower/recourse."),
        ("Helix, acquisitions and other uses", "Capital-call timing, closing conditions, funded-to-date amounts and certain redemptions remain unresolved.",
         "These obligations may compete with cash after capital spending.", "Call notices, closing/redemption disclosures and a reconciliation of completed payments."),
        ("Leases and financing cost", "June lease balances, receivables/Nuveen interest allocation and Other interest detail are not established.",
         "Older lease dates stay visible; component interest coverage is not an all-in financing-cost test.", "Dated lease disclosures and a financing-cost reconciliation."),
    ),
}


def funding_details(markup):
    """Retain the dated conclusion first, with its supporting four-row matrix one click away."""
    first = '<div class="lr-funding-row">'
    end = '<details><summary>Historical coverage basis:'
    if first not in markup or end not in markup:
        return markup  # A missing/error conclusion must remain visible.
    return markup.replace(first, '<details><summary>Obligations, resources, competing uses and source evidence</summary>' + first, 1).replace(
        end, '</details>' + end, 1)


def borrowing(model, money):
    """Use the checked borrowing renderer; group Oracle's repeated unknown split as one disclosure gap.

    This presentation adapter leaves the shared financial model and workbook fingerprint unchanged.
    """
    import borrowing_leases
    from ui import esc
    original = borrowing_leases.render_borrowing(model, money)
    if model['ticker'] != 'ORCL':
        return original
    heading = '<h4>Short-term funding structure</h4>'
    if heading not in original:
        return original
    head, detail = original.split(heading, 1)
    head = head.replace(' — instrument split unavailable', '').replace(
        esc(model['borrowing_note']),
        'The 10-Q does not split these borrowing lines by instrument. The rounded $125.0B disclosure is not added.')
    return (head + heading + '<p>The reported current borrowing above is a combined carrying amount. The 10-Q '
            'does not establish a separate commercial-paper balance or current long-term borrowing split. '
            'The dated principal calendar below uses a different basis; subtracting it cannot establish those balances.</p>'
            '<details><summary>Instrument disclosure gaps and historical comparison</summary>' + detail + '</details>')


def unresolved(snapshot):
    """One consequence and resolution per gap, instead of repeating the same status at every row."""
    import funding_conclusions
    review = funding_conclusions.for_snapshot(snapshot)
    if review is None:
        return '<p>Unavailable: evidence must match the checked conclusion before its gaps can be summarized.</p>'
    out = ('<p>Reported figures above remain useful. The following gaps limit the conclusions that can be drawn; '
           'none is treated as zero. Disclosure gaps need source evidence; future cash generation requires explicit scenario assumptions.</p>')
    for label, finding, consequence, resolution in GAPS[snapshot['ticker']]:
        out += (f'<details><summary>{escape(label)}</summary><p><strong>What is known:</strong> {escape(finding)}</p>'
                f'<p><strong>Why it matters:</strong> {escape(consequence)}</p>'
                f'<p><strong>What would resolve it:</strong> {escape(resolution)}</p></details>')
    sources = {s['url']: s for _, _, refs in review['rows'] for s in refs}
    out += '<p class="lr-meta">Checked sources: ' + ' · '.join(
        f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(s["label"])}</a>'
        for url, s in sources.items()) + '</p>'
    return out
