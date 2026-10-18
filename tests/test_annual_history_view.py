"""Annual presentation reconciles every app/export value to checked input versions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpyxl import load_workbook
import annual_history_view as a
import company_review
import oracle_liquidity
import vistra_liquidity

ROOT = Path(__file__).resolve().parents[1]


class AnnualPresentation(unittest.TestCase):
    def test_five_full_years_and_source_bases_are_visible(self):
        for ticker in ('LLY', 'ORCL', 'VST'):
            m=a.build(ticker);self.assertEqual(len(m['rows']),5)
            html=a.render(ticker)
            self.assertIn('USD millions',html);self.assertIn('TTM',html)
            for r in m['rows']:
                self.assertIn(r['source']['period_end'],html)
                self.assertIn(r['source']['accession'],html)
            self.assertIn('not',m['notes'][0])
        self.assertIn('classification, not new cash generation',a.render('LLY'))
        self.assertIn('reported zero',a.render('VST'))
        self.assertIn('(23,686.0)',a.render('ORCL'))

    def test_bad_years_calculations_and_periods_are_refused(self):
        original=json.loads(a.SAMPLE.read_text())
        for kind in ('year','calculation','period'):
            data=deepcopy(original);row=data['observations'][0]
            if kind=='year':row['fiscal_year']=2020
            if kind=='calculation':row['metrics']['free_cash_flow']['value']+=1
            if kind=='period':row['metrics']['operating_cash_flow']['inputs'][0]['period_start']='2021-02-01'
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'history.json';path.write_text(json.dumps(data))
                with patch.object(a,'SAMPLE',path),patch.object(a,'CHECKED_SHA256',hashlib.sha256(path.read_bytes()).hexdigest()):
                    with self.assertRaises(ValueError):a.build('LLY')

    def test_changed_checkpoint_or_code_refuses_downloads(self):
        snapshots=json.loads((ROOT/'samples/liquidity_pilots.json').read_text())['snapshots']
        with patch.object(a,'CHECKED_SHA256','changed'):
            with self.assertRaises(ValueError):a.build('LLY')
        with patch.object(a,'fingerprint',return_value={'changed':True}):
            self.assertIsNone(company_review.saved_workbook(snapshots,ticker='LLY'))
            self.assertIsNone(oracle_liquidity.workbook_bytes(oracle_liquidity.for_snapshot(snapshots[1])))
            self.assertIsNone(vistra_liquidity.workbook_bytes(vistra_liquidity.for_snapshot(snapshots[2])))

    def test_all_seventy_five_cached_values_and_formulas_match_the_shared_model(self):
        for ticker,stem in [('LLY','lly'),('ORCL','oracle'),('VST','vistra')]:
            p=ROOT/f'samples/{stem}_liquidity.xlsx'
            values=load_workbook(p,data_only=True);formulas=load_workbook(p,data_only=False)
            try:
                for col,row in enumerate(a.build(ticker)['rows'],2):
                    for r,key in enumerate(a.KEYS,6):
                        self.assertEqual(values['Annual history'].cell(r,col).value,row['metrics'][key]['value'])
                        self.assertEqual(formulas['Annual history'].cell(r,col).data_type,'f')
                    letter='BCDEF'[col-2]
                    self.assertEqual(formulas['Annual history'][letter+'10'].value,f'={letter}8-{letter}9')
                self.assertEqual(len(formulas['Annual history'].merged_cells.ranges),0)
                manifest=json.loads(p.with_suffix('.manifest.json').read_text())
                self.assertEqual(manifest['annual_history_sha256'],a.fingerprint())
                data=values['Data'];first,last=manifest['annual_data_start']+1,manifest['annual_data_last']
                self.assertEqual(last-first+1,35 if ticker=='VST' else 25)
                urlcol=12 if ticker=='LLY' else 14 if ticker=='VST' else 13
                accessioncol=7 if ticker=='LLY' else 8
                for r in range(first,last+1):
                    self.assertIsInstance(data.cell(r,2).value,(int,float))
                    self.assertTrue(data.cell(r,urlcol).value.startswith('https://www.sec.gov/Archives/'))
                    self.assertTrue(data.cell(r,accessioncol).value)
                if ticker=='LLY':
                    self.assertNotIn('p. 56; cash flows p. 58',str([r for r in data.values]))
            finally:values.close();formulas.close()


class AnnualCharts(unittest.TestCase):
    """Two five-year charts per company, drawn from the same checked rows in the app and in Excel."""
    STEMS = {'LLY': 'lly', 'ORCL': 'oracle', 'VST': 'vistra'}

    def test_app_figures_are_grouped_columns_from_the_checked_rows(self):
        for ticker in self.STEMS:
            m = a.build(ticker); balances, flows = a.figures(m)
            years = [f"FY{r['fiscal_year']}" for r in m['rows']]
            for fig in (balances, flows):
                self.assertEqual(fig.layout.barmode, 'group')
                self.assertTrue(all(t.type == 'bar' and list(t.x) == years for t in fig.data))   # years left to right
                self.assertEqual(fig.layout.shapes[0].y0, 0)                                        # zero line
            v = lambda k: [r['metrics'][k]['value'] / 1e9 for r in m['rows']]
            self.assertEqual([t.name for t in balances.data], ['Cash and equivalents', 'Baseline borrowing'])
            self.assertEqual(list(balances.data[0].y), v('cash'))
            self.assertEqual(list(balances.data[1].y), v('gross_debt'))
            self.assertEqual(list(flows.data[0].y), v('operating_cash_flow'))
            self.assertEqual(list(flows.data[1].y), [-x for x in v('capital_spending')])             # a use, below zero
            self.assertEqual(list(flows.data[2].y), v('free_cash_flow'))
        self.assertLess(a.figures(a.build('VST'))[1].data[0].y[0], 0)                                # FY2021 OCF stays negative

    def test_a_missing_value_is_a_gap_not_a_zero_bar(self):
        m = deepcopy(a.build('VST'))
        m['rows'][1]['metrics']['gross_debt']['value'] = None
        m['rows'][2]['metrics']['capital_spending']['value'] = None
        balances, flows = a.figures(m)
        self.assertIsNone(balances.data[1].y[1])
        self.assertIsNone(flows.data[1].y[2])
        first, second = a.chart_captions(m)
        self.assertIn('Unavailable, no bar: FY2022.', first)
        self.assertIn('Unavailable, no bar: FY2023.', second)
        self.assertNotIn('Unavailable', a.chart_captions(a.build('VST'))[0])

    def test_latest_quarter_balances_sit_after_the_fiscal_years_and_are_marked(self):
        snaps = {x['ticker']: x for x in json.loads((ROOT / 'samples/liquidity_pilots.json').read_text())['snapshots']}
        for ticker, label, since in (('LLY', 'Jun 2026<br>10-Q', 'cash +$1.68B, borrowing +$12.41B'),
                                     ('ORCL', 'Aug 2026<br>10-Q', 'cash +$5.08B, borrowing −$4.20B'),
                                     ('VST', 'Jun 2026<br>10-Q', 'cash −$350M, borrowing −$173M')):
            m, latest = a.build(ticker), a.latest_balances(snaps[ticker])
            balances, flows = a.figures(m, latest)
            self.assertEqual(list(balances.data[0].x)[-1], label)
            self.assertEqual(balances.data[0].y[-1], snaps[ticker]['metrics']['cash']['value'] / 1e9)
            self.assertEqual(balances.data[1].y[-1], snaps[ticker]['metrics']['gross_debt']['value'] / 1e9)
            self.assertEqual(list(balances.data[0].marker.pattern.shape)[-1], '/')       # hatched
            self.assertEqual(set(list(balances.data[0].marker.pattern.shape)[:-1]), {''})
            self.assertEqual(len(balances.layout.shapes), 2)                              # zero line, divider
            self.assertEqual(len(list(flows.data[0].x)), 5)                              # flows stay annual only
            self.assertIn(since, a.chart_captions(m, latest)[0])

    def test_charts_sit_between_the_table_and_its_notes(self):
        html = a.render('LLY')
        self.assertLess(html.index('</table>'), html.index(a.CHARTS_MARK))
        self.assertLess(html.index(a.CHARTS_MARK), html.index('classification, not new cash generation'))

    def test_excel_charts_bind_to_the_annual_table_and_cache_its_values(self):
        import zipfile, re
        for ticker, stem in self.STEMS.items():
            path = ROOT / f'samples/{stem}_liquidity.xlsx'
            ws = load_workbook(path)['Annual history']; vs = load_workbook(path, data_only=True)['Annual history']
            self.assertEqual(len(ws._charts), 2)
            for c in 'BCDEF':
                self.assertEqual(ws[f'{c}61'].value, f'=IF(ISNUMBER({c}9),-{c}9,NA())')
                self.assertEqual(vs[f'{c}61'].value, -vs[f'{c}9'].value)
            m = a.build(ticker)
            with zipfile.ZipFile(path) as z:
                charts = [z.read(n).decode() for n in z.namelist() if n.startswith('xl/drawings/charts/') and "'Annual history'" in z.read(n).decode()]
            self.assertEqual(len(charts), 2)
            refs = sorted(set(re.findall(r"<c:f>'Annual history'!\$B\$(\d+):\$F\$\1</c:f>", ''.join(charts))))
            self.assertEqual(refs, sorted(['5', '6', '7', '8', '10', '61']))      # FY labels, the table rows, the helper row
            balances = next(x for x in charts if 'Fiscal-year-end cash' in x)
            cash = [float(v) for v in re.findall(r'<c:pt idx="\d"><c:v>([-\d.e+]+)</c:v>', balances.split('$B$6:$F$6')[1].split('</c:numCache>')[0])]
            self.assertEqual(cash, [r['metrics']['cash']['value'] for r in m['rows']])
            for x in charts:
                self.assertIn('<c:dispBlanksAs val="gap"/>', x)

    def test_chart_writer_leaves_a_missing_point_out(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('charts', ROOT / 'tests/offline/add_annual_history_charts.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        labels = ['FY2021', 'FY2022', 'FY2023', 'FY2024', 'FY2025']
        values = {6: ('Cash', [1.0, None, 3.0, 4.0, 5.0]), 7: ('Borrowing', [1.0, 2.0, 3.0, 4.0, 5.0])}
        xml = mod.chart_xml('balances', labels, values)
        cash = xml.split('$B$6:$F$6')[1].split('</c:numCache>')[0]
        self.assertNotIn('<c:pt idx="1">', cash)                                # no cached point: no column
        self.assertIn('<c:ptCount val="5"/>', cash)
