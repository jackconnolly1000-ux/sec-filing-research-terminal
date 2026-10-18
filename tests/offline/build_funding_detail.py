"""Reconcile short-term funding detail and liability totals to saved filing facts; no network."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import filing_xbrl as fx
from fact_registry import FactRegistry
import liquidity_pilot

CP_DIMENSIONS = (
    ("us-gaap:FairValueByMeasurementBasisAxis", "us-gaap:CarryingReportedAmountFairValueDisclosureMember"),
    ("us-gaap:ShortTermDebtTypeAxis", "us-gaap:CommercialPaperMember"),
    ("us-gaap:FairValueByFairValueHierarchyLevelAxis", "us-gaap:FairValueInputsLevel2Member"),
)


def build(raw):
    snapshots = json.loads(liquidity_pilot.SAMPLE.read_text())["snapshots"]
    out = {"checked_as_of": "2026-10-18", "companies": {}}
    controls = {"LLY": (47741, 60663), "ORCL": (47514, 188549), "VST": (10557, 26552)}
    for snapshot in snapshots:
        ticker = snapshot["ticker"]
        meta = liquidity_pilot.PILOTS[ticker]
        path = raw / ticker / meta["document"]
        anchor = snapshot["metrics"]["cash"]
        registry = FactRegistry()
        def read(tag, label, page, dims=()):
            f = fx.read_instant(path, meta["accession"], tag, anchor["period_end"], dimensions=dims)
            context = fx.parse(path).find(".//{http://www.xbrl.org/2003/instance}context[@id='" + str(f["context_id"]) + "']")
            entity = context.findtext("{http://www.xbrl.org/2003/instance}entity/{http://www.xbrl.org/2003/instance}identifier") if context is not None else None
            if f["value"] is None or str(entity).lstrip("0") != str(meta["cik"]):
                raise ValueError((ticker, tag, f))
            f.update(label=label, unit="USD", period_end=anchor["period_end"], source_url=snapshot["source_url"],
                     source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), form=anchor["form"],
                     filed=anchor["filed"], location=page, status="Reported",
                     selection_rule="Exact filing, entity, USD instant and allowed dimensions; agreeing duplicates only.")
            f["document"] = meta["document"]
            registry.add(f)
            return f
        current = read("us-gaap:LiabilitiesCurrent", "Current liabilities", "Balance sheet, p. " + ("7" if ticker == "LLY" else "1" if ticker == "ORCL" else "2"))
        if ticker == "VST":
            total = read("us-gaap:Liabilities", "Total liabilities", "Balance sheet, p. 2")
            noncurrent = dict(total, label="Noncurrent liabilities", tag=None, context_id=None,
                              value=total["value"] - current["value"], status="Derived", formula="Total liabilities - current liabilities",
                              inputs=[total, current])
        else:
            noncurrent = read("us-gaap:LiabilitiesNoncurrent", "Noncurrent liabilities", current["location"])
        if (current["value"], noncurrent["value"]) != tuple(v * 1_000_000 for v in controls[ticker]):
            raise ValueError("Liability controls differ: " + ticker)
        facts = {"current_liabilities": current, "noncurrent_liabilities": noncurrent}
        if ticker == "LLY":
            cp = read("us-gaap:CommercialPaper", "Commercial paper, carrying value", "Note 8, p. 17", CP_DIMENSIONS)
            if cp["value"] != 5284e6 or cp["context_id"] != "c-295":
                raise ValueError("Lilly commercial paper carrying control differs")
            facts["commercial_paper"] = cp
        out["companies"][ticker] = {"accession": meta["accession"], "period_end": anchor["period_end"],
                                    "facts": facts, "registry": registry.facts}
    return out


if __name__ == "__main__":
    raw = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "data/raw/sec"
    text = json.dumps(build(raw), indent=2) + "\n"
    (ROOT / "samples/funding_detail.json").write_text(text)
    print(hashlib.sha256(text.encode()).hexdigest())
