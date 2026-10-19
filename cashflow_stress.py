"""A historical cash-generation sensitivity, not a complete repayment or cash-balance model."""
import csv
from decimal import Decimal
from io import StringIO
import math

import funding_conclusions
import ratio_review

LIMIT = ("OCF less the checked capital-spending line only. Acquisitions, dividends, buybacks, debt principal, "
         "capital calls and other cash uses are not deducted. It does not measure cash available at a payment date "
         "or establish funding coverage. No credit draw or Parent cash transfer is assumed.")
REQUIREMENTS = {
    "LLY": "A complete remaining principal calendar, post-expiry credit evidence and acquisition/manufacturing payment timing are needed for a repayment cash path.",
    "VST": "A complete borrower-level debt-service calendar, Parent-accessible cash, transfer restrictions and dated borrowing-base/draw-condition evidence are needed for a repayment cash path.",
    "ORCL": "Oracle's separate cash-path model has a dated note/term-loan calendar, with explicitly assumed commercial paper and financing availability.",
}


def build(snapshot):
    if funding_conclusions.for_snapshot(snapshot) is None:
        raise ValueError("The sensitivity requires the exact checked company snapshot")
    review = ratio_review.build(snapshot)
    metrics = snapshot['metrics']
    ocf, capex = (metrics[k] for k in ('operating_cash_flow', 'capital_spending'))
    if any(f['value'] is None or not math.isfinite(f['value']) for f in (ocf, capex)):
        raise ValueError("Checked OCF and capital spending are required; missing does not mean zero")
    return dict(ticker=snapshot['ticker'], company=snapshot['company_name'],
                start=ocf['period_start'], end=ocf['period_end'], ocf=ocf['value'], capex=capex['value'],
                ocf_basis=next(r['basis'] for r in review['rows'] if r['key']=='operating_cash_flow'),
                capex_basis=next(r['basis'] for r in review['rows'] if r['key']=='capital_spending'),
                inputs=[dict(metric=key, **fact) for key in ('operating_cash_flow', 'capital_spending')
                        for fact in metrics[key]['inputs']],
                requirement=REQUIREMENTS[snapshot['ticker']], limit=LIMIT)


def calculate(model, ocf_decline=0, capex_change=0):
    """Percent shocks are user assumptions applied to historical TTM flows, never estimated future ranges."""
    if (not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (ocf_decline, capex_change))
            or not 0 <= ocf_decline <= 100 or not -100 <= capex_change <= 200):
        raise ValueError("OCF decline must be 0–100%; capital-spending change must be −100–200%")
    ocf = float(Decimal(str(model['ocf'])) * (1 - Decimal(str(ocf_decline)) / 100))
    capex = float(Decimal(str(model['capex'])) * (1 + Decimal(str(capex_change)) / 100))
    return dict(ocf_decline=ocf_decline, capex_change=capex_change, ocf=ocf, capex=capex,
                residual=ocf-capex, historical_residual=model['ocf']-model['capex'],
                change=(ocf-capex)-(model['ocf']-model['capex']))


def csv_bytes(model, result):
    """Small evidence record for the sensitivity; the checked company Excel remains a separate download."""
    stream = StringIO(newline='')
    out = csv.writer(stream)
    out.writerow(['Company', model['company'], model['ticker']])
    out.writerow(['Basis', 'Illustrative historical cash-generation sensitivity; not a forecast'])
    out.writerow(['Historical TTM start', model['start'], 'Historical TTM end', model['end']])
    out.writerow(['Kind', 'Measure', 'Value', 'Unit', 'Formula / basis'])
    for label, key, basis in [('Historical OCF', 'ocf', model['ocf_basis']), ('Historical capital spending', 'capex', model['capex_basis'])]:
        out.writerow(['Checked derived input', label, model[key], 'USD', basis])
    out.writerow(['Assumption', 'OCF decline', result['ocf_decline'], 'percent', 'User-selected shock'])
    out.writerow(['Assumption', 'Capital-spending change', result['capex_change'], 'percent', 'User-selected shock'])
    out.writerow(['Calculation', 'Stressed OCF', result['ocf'], 'USD', 'Historical OCF * (1 - decline / 100)'])
    out.writerow(['Calculation', 'Stressed capital spending', result['capex'], 'USD', 'Historical capital spending * (1 + change / 100)'])
    out.writerow(['Calculation', 'Cash generation after capital spending', result['residual'], 'USD', 'Stressed OCF - stressed capital spending'])
    out.writerow(['Limit', model['limit']])
    out.writerow(['Repayment-path requirements', model['requirement']])
    out.writerow([])
    out.writerow(['Metric', 'Value (USD)', 'Coefficient in TTM', 'Period start', 'Period end', 'Form', 'Filed', 'Accession', 'Tag', 'Source URL'])
    for f in model['inputs']:
        url = f['source_url']
        out.writerow([f['metric'], f['value'], f['coefficient'], f['period_start'], f['period_end'],
                      f['form'], f['filed'], f['accession'], f['tag'], url])
    return stream.getvalue().encode('utf-8-sig')


def render(st, snapshot):
    import hashlib
    import json
    from company_review import money
    from simulation_view import _dollars
    try:
        model = build(snapshot)
    except (ValueError, KeyError, OSError) as exc:
        st.warning('Cash-generation sensitivity Unavailable: ' + str(exc))
        return
    ticker = model['ticker']
    st.subheader(model['company'] + ' · stress test')
    st.markdown('**Historical cash-generation sensitivity.** Change OCF and capital spending relative to the checked '
                'trailing twelve months. The result is conditional arithmetic, not a forecast or a repayment conclusion.')
    st.caption(f"Historical reference: {model['start']} to {model['end']} · USD billions · {model['ocf_basis']}")
    st.caption(model['capex_basis'])
    version = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    state_key = f'cashflow_{ticker}_completed'
    with st.form(f'cashflow_{ticker}_form'):
        a, b = st.columns(2)
        decline = a.slider('OCF decline from historical TTM (%)', 0, 100, 0, 5,
                           key=f'cashflow_{ticker}_decline', persist_state='session')
        change = b.slider('Capital-spending change from historical TTM (%)', -100, 200, 0, 5,
                          key=f'cashflow_{ticker}_capex', persist_state='session')
        st.caption('Zero changes reproduce the historical reference. Slider limits are editing bounds, not estimated future ranges.')
        submitted = st.form_submit_button('Apply stress', key=f'cashflow_{ticker}_apply')
    completed = st.session_state.get(state_key)
    if submitted or completed is None or completed['version'] != version:
        completed = dict(version=version, result=calculate(model, decline, change))
        st.session_state[state_key] = completed
    result = completed['result']
    if (decline, change) != (result['ocf_decline'], result['capex_change']):
        st.info('Results and download retain the last applied stress. Select Apply stress to use the edited assumptions.')
    st.markdown(f"**Applied assumptions:** OCF decline {result['ocf_decline']}%; capital-spending change {result['capex_change']:+}%. ")
    a, b, c = st.columns(3)
    a.metric('Stressed operating cash flow', money(result['ocf']))
    b.metric('Stressed capital spending', money(result['capex']))
    c.metric('OCF less capital spending', money(result['residual']))
    st.markdown(_dollars(f"Historical OCF less capital spending: **{money(result['historical_residual'])}**. "
                        f"Change under the applied stress: **{money(result['change'])}**."))
    st.info(model['limit'])
    st.markdown('**Why there is no repayment simulation for this company yet:** ' + model['requirement'])
    with st.expander('Calculation and filing inputs'):
        st.code('Stressed OCF = historical OCF × (1 − assumed decline / 100)\n'
                'Stressed capital spending = historical capital spending × (1 + assumed change / 100)\n'
                'Cash generation after capital spending = stressed OCF − stressed capital spending')
        st.markdown(f"[Checked {ticker} balance-sheet filing]({snapshot['source_url']}). "
                    'The download retains all six FY/current-YTD/prior-YTD flow inputs, their coefficients, periods and accessions.')
    st.download_button('Download sensitivity and evidence (CSV)', csv_bytes(model, result), mime='text/csv',
                       file_name=f'{ticker}_Cash_Generation_Stress_{model["end"]}.csv',
                       key=f'cashflow_{ticker}_download', on_click='ignore')
    st.caption('The complete checked Excel review remains under Checked review; this CSV records the applied stress and its evidence.')
