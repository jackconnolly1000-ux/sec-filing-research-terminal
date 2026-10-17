"""Offline annual-source reconciliation, including reclassifications and complete comparatives."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import annual_history as history

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures/annual_history"
INVENTORY = json.loads((ROOT / "samples/annual_source_inventory.json").read_text())
CHECKPOINT = json.loads((ROOT / "samples/annual_history_reconciliation.json").read_text())
META = json.loads((FIX / "manifest.json").read_text())
CF = json.loads((FIX / "companyfacts.json").read_text())
LOCATIONS = json.loads((ROOT / "tests/fixtures/annual_history_locations.json").read_text())

# cash, borrowing, OCF, reported capex, OCF less capex, USD millions.
EXPECTED = {
    "LLY": [(3818.5,16884.7,7365.9,1309.8,6056.1), (2067,16238.6,7585.7,1854.3,5731.4),
            (2818.6,25225.3,4240.1,3447.6,792.5), (3268.4,33644.2,8817.9,5057.8,3760.1),
            (7268,42503,16813,7841,8972)],
    "ORCL": [(21383,75859,9539,4511,5028), (9765,90481,17165,8695,8470),
             (10454,86869,18673,6866,11807), (10786,92568,20821,21215,-394),
             (31289,129541,31977,55663,-23686)],
    "VST": [(1325,10731,-206,1033,-1239), (455,13046,485,1301,-816),
            (3485,14402,5453,1676,3777), (1188,17048,4563,2078,2485),
            (785,20068,4070,2752,1318)],
}
KEYS = ("cash", "gross_debt", "operating_cash_flow", "capital_spending", "free_cash_flow")


def replay(source, facts=None):
    meta = META[source["accession"]]
    key = source["accession"] + (":"+source["period_end"] if source.get("filing_period_end") else "")
    return history.reconcile(source, FIX / meta["document"], facts or CF[source["ticker"]],
                             LOCATIONS[key], expected_sha256=meta["sha256"])


class AnnualHistory(unittest.TestCase):
    def test_fifteen_originals_and_seventy_five_selected_observations(self):
        self.assertEqual(len(INVENTORY["sources"]),15)
        self.assertEqual(len(CHECKPOINT["original_observations"]),15)
        self.assertEqual(len(CHECKPOINT["observations"]),15)
        for ticker, expected in EXPECTED.items():
            rows = [r for r in CHECKPOINT["observations"] if r["ticker"]==ticker]
            for row, values in zip(rows,expected):
                self.assertEqual([row["metrics"][k]["value"] for k in KEYS], [history.usd(v) for v in values])
                self.assertTrue(all(row["metrics"][k]["status"]=="Reconciled" for k in KEYS))

    def test_every_original_and_selected_record_replays_real_fact_context_subsets(self):
        for row in CHECKPOINT["original_observations"] + CHECKPOINT["observations"]:
            actual = replay(row["source"])
            if row.get("flow_source"):
                flows = replay(row["flow_source"])
                for k in ("operating_cash_flow", "capital_spending", "free_cash_flow"):
                    actual["metrics"][k] = flows["metrics"][k]
            for key in KEYS:
                self.assertEqual(actual["metrics"][key]["value"],row["metrics"][key]["value"])
                self.assertEqual(actual["metrics"][key]["inputs"],row["metrics"][key]["inputs"])

    def test_each_calculation_has_one_accession_exact_period_and_usd_contexts(self):
        for row in CHECKPOINT["observations"]:
            for key, metric in row["metrics"].items():
                inputs = metric["inputs"]
                self.assertEqual(len({f["accession"] for f in inputs}),1,(row["ticker"],key))
                for fact in inputs:
                    self.assertEqual(fact["period_end"],row["source"]["period_end"])
                    self.assertEqual(fact["unit"],"USD")
                    self.assertFalse(fact["dimensions"])
                    self.assertEqual(fact["location"]["context_id"],fact["context_id"])
                    self.assertIsInstance(fact["location"]["printed_page"],int)

    def test_lilly_reclassification_is_not_misread_as_new_cash_generation(self):
        for year, delta in ((2021,105.2),(2022,501.3)):
            row = next(r for r in CHECKPOINT["observations"] if r["ticker"]=="LLY" and r["fiscal_year"]==year)
            old = next(r for r in CHECKPOINT["original_observations"] if r["ticker"]=="LLY" and r["fiscal_year"]==year)
            self.assertEqual(row["metrics"]["operating_cash_flow"]["value"]-old["metrics"]["operating_cash_flow"]["value"],history.usd(delta))
            self.assertEqual(row["reclassification"]["increase"],history.usd(delta))
            self.assertEqual(row["metrics"]["capital_spending"]["value"],old["metrics"]["capital_spending"]["value"])
            self.assertTrue(all(f["accession"]=="0000059478-24-000065" for f in row["metrics"]["free_cash_flow"]["inputs"]))

    def test_vistra_missing_original_is_not_zero_and_comparative_is_complete(self):
        for year in (2021,2024):
            old=next(r for r in CHECKPOINT["original_observations"] if r["ticker"]=="VST" and r["fiscal_year"]==year)
            self.assertIsNone(old["metrics"]["gross_debt"]["value"])
            self.assertIsNone(old["metrics"]["gross_debt"]["inputs"][2]["value"])
            row=next(r for r in CHECKPOINT["observations"] if r["ticker"]=="VST" and r["fiscal_year"]==year)
            self.assertIn("Complete comparative",row["source_basis"])
            accs={f["accession"] for m in row["metrics"].values() for f in m["inputs"]}
            self.assertEqual(accs,{row["source"]["accession"]})
            self.assertEqual(row["metrics"]["gross_debt"]["inputs"][2]["value"],0)

    def test_vistra_financing_line_is_counted_once_without_an_invented_split(self):
        row=next(r for r in CHECKPOINT["observations"] if r["ticker"]=="VST" and r["fiscal_year"]==2025)
        debt=row["metrics"]["gross_debt"]
        self.assertEqual([f["value"] for f in debt["inputs"]],[1201e6,15842e6,1800e6,1225e6])
        self.assertEqual(debt["value"],20068e6)
        self.assertIn("not explicit",debt["notes"][0])
        self.assertEqual(debt["total_check"]["value"],17043e6)

    def test_conflicting_companyfacts_are_refused_and_later_rows_cannot_override(self):
        source=INVENTORY["sources"][0]
        check=history.companyfacts_check(CF["LLY"],history.OCF,source,True)
        self.assertEqual(check["value"],7260700000)
        self.assertTrue(check["later_differences_not_used"])
        bad=deepcopy(CF["LLY"])
        rows=bad["facts"]["us-gaap"][history.OCF.split(":")[1]]["units"]["USD"]
        original=next(r for r in rows if r["accn"]==source["accession"] and r.get("start")==source["period_start"] and r["end"]==source["period_end"])
        rows.append({**original,"val":original["val"]+1})
        with self.assertRaisesRegex(ValueError,"Conflicting original"):
            replay(source,bad)

    def test_source_hash_and_wrong_entity_are_refused(self):
        source=INVENTORY["sources"][0]
        with self.assertRaisesRegex(ValueError,"source hash"):
            history.reconcile(source,FIX/META[source["accession"]]["document"],CF["LLY"],LOCATIONS[source["accession"]])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"wrong.htm"
            root=ET.parse(FIX/META[source["accession"]]["document"]).getroot()
            for node in root.iter("{http://www.xbrl.org/2003/instance}identifier"):
                node.text="999999"
            data=ET.tostring(root);p.write_bytes(data)
            with self.assertRaisesRegex(ValueError,"another entity"):
                history.reconcile(source,p,CF["LLY"],LOCATIONS[source["accession"]],expected_sha256=hashlib.sha256(data).hexdigest())

    def test_negative_operating_cash_is_kept_and_fcf_uses_reported_capex(self):
        row=next(r for r in CHECKPOINT["observations"] if r["ticker"]=="VST" and r["fiscal_year"]==2021)
        self.assertEqual(row["metrics"]["operating_cash_flow"]["value"],-206e6)
        self.assertEqual(row["metrics"]["free_cash_flow"]["value"],-1239e6)
        self.assertEqual(row["metrics"]["capital_spending"]["inputs"][0]["tag"],history.CAPEX)
        self.assertIn("LTSA",row["metrics"]["capital_spending"]["basis"])

    def test_latest_annual_regression_matches_the_existing_checked_facts(self):
        prior=json.loads((ROOT/"samples/company_history.json").read_text())
        for ticker in ("LLY","ORCL","VST"):
            row=next(r for r in CHECKPOINT["observations"] if r["ticker"]==ticker and r["source"]["period_end"]==prior[ticker]["annual_end"])
            self.assertEqual(row["metrics"]["cash"]["value"],prior[ticker]["facts"][0]["value"])
            if ticker!="VST":
                self.assertEqual(row["metrics"]["gross_debt"]["value"],sum(f["value"] for f in prior[ticker]["facts"][3:]))

    def test_full_source_rebuild_when_public_raw_files_are_saved(self):
        if not (ROOT.parent/"data/raw/xbrl/LLY_companyfacts_20261017.json").exists():
            self.skipTest("Full raw annual source set not saved here; committed subsets cover offline replay")
        spec=importlib.util.spec_from_file_location("build_annual",ROOT/"tests/offline/build_annual_history.py")
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.build(ROOT.parent/"data/raw"),CHECKPOINT)
