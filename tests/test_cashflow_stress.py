"""Independent arithmetic, provenance and cross-company state checks for the limited stress views."""
import csv
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
import cashflow_stress as cf
import simulation_view

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = {s['ticker']: s for s in json.loads((ROOT / 'samples/liquidity_pilots.json').read_text())['snapshots']}


class Arithmetic(unittest.TestCase):
    def test_neutral_case_matches_checked_fcf_and_twenty_percent_shock(self):
        for ticker, snapshot in SNAPSHOTS.items():
            m = cf.build(snapshot)
            self.assertEqual(cf.calculate(m)['residual'], snapshot['metrics']['free_cash_flow']['value'])
            r = cf.calculate(m, 20, 10)
            self.assertAlmostEqual(r['residual'], m['ocf'] * .8 - m['capex'] * 1.1, delta=.001)
            self.assertEqual((m['start'], m['end']), (snapshot['metrics']['operating_cash_flow']['period_start'],
                                                     snapshot['metrics']['capital_spending']['period_end']))

    def test_zero_ocf_and_zero_capex_are_real_boundaries(self):
        m = cf.build(SNAPSHOTS['VST'])
        self.assertEqual(cf.calculate(m, 100)['residual'], -m['capex'])
        self.assertEqual(cf.calculate(m, 0, -100)['residual'], m['ocf'])
        self.assertEqual(cf.calculate(m, 100, -100)['residual'], 0)

    def test_bad_assumptions_and_changed_evidence_are_refused(self):
        m = cf.build(SNAPSHOTS['LLY'])
        for a, b in ((-1, 0), (101, 0), (0, -101), (0, 201), (float('nan'), 0), (0, float('inf'))):
            with self.assertRaises(ValueError): cf.calculate(m, a, b)
        altered = deepcopy(SNAPSHOTS['LLY'])
        altered['metrics']['capital_spending']['value'] = 0
        with self.assertRaises(ValueError): cf.build(altered)

    def test_download_retains_all_source_inputs_and_applied_assumptions(self):
        for snapshot in SNAPSHOTS.values():
            m = cf.build(snapshot)
            r = cf.calculate(m, 25, 15)
            rows = list(csv.reader(StringIO(cf.csv_bytes(m, r).decode('utf-8-sig'))))
            self.assertIn(['Assumption', 'OCF decline', '25', 'percent', 'User-selected shock'], rows)
            self.assertIn(['Calculation', 'Cash generation after capital spending', str(r['residual']), 'USD',
                           'Stressed OCF - stressed capital spending'], rows)
            for f in m['inputs']:
                self.assertTrue(any(f['tag'] in row and f['accession'] in row and f['source_url'] in row for row in rows))
            self.assertEqual(len(m['inputs']), 6)
            self.assertIn('No credit draw or Parent cash transfer is assumed', m['limit'])


class CompanyState(unittest.TestCase):
    def test_switching_company_never_reuses_another_companys_assumptions_or_results(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=90).run()
        next(w for w in app.segmented_control if w.key == 'review_view').set_value(simulation_view.VIEWS[1]).run()
        app.slider(key='cashflow_LLY_decline').set_value(40)
        app.button(key='cashflow_LLY_apply').click().run()
        self.assertEqual(app.session_state['cashflow_LLY_completed']['result']['ocf_decline'], 40)
        app.segmented_control[0].set_value('VST').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.slider(key='cashflow_VST_decline').value, 0)
        self.assertEqual(app.session_state['cashflow_VST_completed']['result']['ocf_decline'], 0)
        app.segmented_control[0].set_value('ORCL').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(w.key == 'sim_ocf_low' for w in app.number_input))
        app.segmented_control[0].set_value('LLY').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.slider(key='cashflow_LLY_decline').value, 40)
        self.assertEqual(app.session_state['cashflow_LLY_completed']['result']['ocf_decline'], 40)

