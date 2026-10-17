"""Rebuild the source checkpoint from full saved annual filings and captured companyfacts."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import annual_history as history


def build(raw):
    inv = json.loads((ROOT / "samples/annual_source_inventory.json").read_text())
    locations = json.loads((ROOT / "tests/fixtures/annual_history_locations.json").read_text())
    cf = {}
    for item in inv["companyfacts"]:
        data = (raw / "xbrl" / item["document"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["source_sha256"]:
            raise ValueError("Captured companyfacts differs: " + item["ticker"])
        cf[item["ticker"]] = json.loads(data)
    original = [history.reconcile(s, raw / "sec" / s["ticker"] / s["document"], cf[s["ticker"]], locations[s["accession"]])
            for s in inv["sources"]]
    rows = deepcopy(original)
    for row in rows:
        source = row["source"]
        row["source_basis"] = "Original annual filing"
        if row["ticker"] == "VST" and row["fiscal_year"] in (2021, 2024):
            later = next(s for s in inv["sources"] if s["ticker"] == "VST" and int(s["period_end"][:4]) == row["fiscal_year"]+1)
            selected = {**later, "filing_period_end": later["period_end"],
                        "period_start": source["period_start"], "period_end": source["period_end"]}
            replacement = history.reconcile(selected, raw / "sec/VST" / later["document"], cf["VST"], locations[later["accession"]+":"+source["period_end"]])
            replacement["source_basis"] = "Complete comparative snapshot from one later annual filing; no original/later input mixing"
            replacement["original_source_accession"] = source["accession"]
            rows[rows.index(row)] = replacement
    for row in rows:
        if row["ticker"] != "LLY" or row["fiscal_year"] not in (2021, 2022):
            continue
        original_source = row["source"]
        later = next(s for s in inv["sources"] if s["ticker"] == "LLY" and s["period_end"] == "2023-12-31")
        selected = {**later, "filing_period_end": later["period_end"],
                    "period_start": original_source["period_start"], "period_end": original_source["period_end"]}
        revised = history.reconcile(selected, raw / "sec/LLY" / later["document"], cf["LLY"], locations[later["accession"]+":"+original_source["period_end"]])
        # Cash and borrowing remain the original balance-sheet pair. Every flow calculation
        # uses both inputs from FY2023's explicitly reclassified comparative presentation.
        for key in ("operating_cash_flow", "capital_spending", "free_cash_flow"):
            row["metrics"][key] = revised["metrics"][key]
        row["flow_source"] = selected
        row["source_basis"] = "Original balance sheet; full reclassified annual flow pair from FY2023. No filing versions are mixed within borrowing or FCF calculations."
        row["reclassification"] = {
            "source_url": later["source_url"], "accession": later["accession"],
            "location": "Note 1, Reclassifications, printed page 63", "printed_page": 63,
            "original_ocf": history.usd(history.CONTROLS["LLY"][row["fiscal_year"]][3]),
            "reclassified_ocf": row["metrics"]["operating_cash_flow"]["value"],
            "increase": history.usd(105.2 if row["fiscal_year"] == 2021 else 501.3),
            "reason": "Development-milestone payments for externally developed IPR&D acquired outside a business combination moved from operating activities to purchases of IPR&D in investing activities.",
        }
        for key in ("operating_cash_flow", "free_cash_flow"):
            row["metrics"][key]["basis"] += " Uses the FY2023 reclassification. This FCF measure does not deduct purchases of IPR&D or acquisitions."
    return {"as_of": inv["as_of"], "stage": "Source reconciliation; not connected to app or Excel history",
            "selection_rule": "Original annual balance sheets, except two complete Vistra comparative snapshots. Lilly 2021/2022 flow pairs use FY2023's disclosed reclassification. Every calculation uses one filing version; independent stock and flow observations retain their own sources. Retain originals and later differences.",
            "original_observations": original, "observations": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT.parent / "data/raw")
    parser.add_argument("--check", action="store_true", help="Compare with the checkpoint instead of writing it")
    args = parser.parse_args()
    result = build(args.raw)
    target = ROOT / "samples/annual_history_reconciliation.json"
    if args.check:
        if result != json.loads(target.read_text()):
            raise SystemExit("Annual reconciliation differs from the saved checkpoint")
    else:
        target.write_text(json.dumps(result, indent=2) + "\n")
    missing = [(r["ticker"], r["fiscal_year"], k) for r in result["observations"] for k, v in r["metrics"].items() if v["value"] is None]
    print(f"{len(result['observations'])} annual filings; {75-len(missing)} reconciled observations; {len(missing)} Unavailable")
    for row in missing:
        print(*row)
