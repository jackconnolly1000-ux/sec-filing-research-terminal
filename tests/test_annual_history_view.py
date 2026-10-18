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
