"""Evidence remains accessible while repeated limitations leave the main reading path."""
import json
from pathlib import Path
import re
import unittest
from bs4 import BeautifulSoup

import borrowing_leases
import company_review
import funding_conclusions
import review_presentation as rp

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = json.loads((ROOT / 'samples/liquidity_pilots.json').read_text())['snapshots']


class Presentation(unittest.TestCase):
    def test_checked_borrowing_values_and_explicit_missing_values_remain_accessible(self):
        for snapshot in SNAPSHOTS:
            model = borrowing_leases.build(snapshot)
            rendered = BeautifulSoup(rp.borrowing(model, company_review.money), 'html.parser')
            for f in model['borrowing']:
                shown = '$0 · reported' if f['value'] == 0 else company_review.money(f['value'], 3)
                self.assertIn(shown, rendered.get_text())
            if snapshot['ticker'] == 'ORCL':
                self.assertIn('does not establish a separate commercial-paper balance', rendered.get_text())
                self.assertIn('Unavailable', rendered.find('details').get_text())

    def test_the_primary_oracle_reading_path_has_one_explained_funding_limit(self):
        s = SNAPSHOTS[1]
        soup = BeautifulSoup(company_review.render(s), 'html.parser')
        self.assertIn('Future funding coverage: Unavailable.', soup.get_text())
        # Detailed reasons and sources are retained, rather than replaced by missing-data zeroes.
        self.assertIn('Funding coverage: Unavailable for every period.', soup.get_text())
        self.assertIn('What would resolve it:', soup.get_text())
        for d in list(soup.find_all('details')):
            if d.parent is None: continue
            summary = d.find('summary', recursive=False)
            d.replace_with(summary.get_text() if summary else '')
        self.assertLessEqual(len(re.findall('Unavailable', soup.get_text(), re.I)), 10)
        self.assertIn('What remains unresolved?', soup.get_text())
        self.assertIn('Commercial paper and capex financing', soup.get_text())

    def test_folded_conclusion_retains_all_checked_source_links(self):
        for s in SNAPSHOTS:
            before = BeautifulSoup(funding_conclusions.render(s), 'html.parser')
            after = BeautifulSoup(rp.funding_details(str(before)), 'html.parser')
            self.assertEqual(before.get_text(' ', strip=True).replace(' ', ''),
                             after.get_text(' ', strip=True).replace(
                                 'Obligations, resources, competing uses and source evidence', '').replace(' ', ''))
            self.assertEqual([a['href'] for a in before.find_all('a')], [a['href'] for a in after.find_all('a')])
            self.assertIsNone(after.find('p', class_='lr-answer').find_parent('details'))

