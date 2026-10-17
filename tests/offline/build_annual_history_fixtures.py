"""Preserve real facts/contexts/units and original companyfacts rows for offline reconciliation.

Full public filings and raw companyfacts remain outside git. The committed subsets are
not replacements for the sources: their hashes and source inventory identify their origin.
"""
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
import warnings
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import annual_history as history
import filing_xbrl as fx

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def locate(soup, result):
    node = soup.find(lambda n: n.name and n.name.lower().endswith("nonfraction")
                     and n.get("name") == result["tag"] and n.get("contextref") == result["context_id"])
    table = node.find_parent("table")
    page = None
    for element in table.next_elements:
        if (isinstance(element, Tag) and element.name in ("p", "div", "span")
                and table not in element.parents and not element.find_parent("table")):
            text = element.get_text(strip=True)
            if text.isdigit() and 1 <= int(text) <= 500:
                page = int(text)
                break
    return {"printed_page": page, "row_text": " ".join(node.find_parent("tr").stripped_strings),
            "context_id": result["context_id"]}


def build(raw):
    inv = json.loads((ROOT / "samples/annual_source_inventory.json").read_text())
    dest = ROOT / "tests/fixtures/annual_history"
    dest.mkdir(parents=True, exist_ok=True)
    meta, locations, cf = {}, {}, {}
    target_dates = {s["period_end"] for s in inv["sources"]}
    for item in inv["companyfacts"]:
        captured = (raw / "xbrl" / item["document"]).read_bytes()
        if hashlib.sha256(captured).hexdigest() != item["source_sha256"]:
            raise ValueError("Wrong captured companyfacts: " + item["ticker"])
        original = json.loads(captured)
        ticker = item["ticker"]
        names = {t.split(":", 1)[1] for t in [history.CASH, history.OCF, history.CAPEX, history.LLY_CAPEX,
                                             history.TOTALS[ticker], *history.BORROWING[ticker]]}
        kept = {}
        for name in sorted(names):
            tag = original["facts"].get("us-gaap", {}).get(name)
            if tag:
                rows = [r for r in tag.get("units", {}).get("USD", [])
                        if r.get("end") in target_dates and r.get("filed", "") <= inv["as_of"]]
                kept[name] = {"units": {"USD": rows}}
        cf[ticker] = {"cik": original["cik"], "facts": {"us-gaap": kept}}
    (dest / "companyfacts.json").write_text(json.dumps(cf, separators=(",", ":")) + "\n")

    for source in inv["sources"]:
        ticker = source["ticker"]
        path = raw / "sec" / ticker / source["document"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["source_sha256"]:
            raise ValueError("Wrong raw source: " + source["document"])
        tree = fx.parse(path)
        contexts = fx._contexts(tree)
        tags = {history.CASH, history.OCF, history.CAPEX, history.LLY_CAPEX,
                history.TOTALS[ticker], *history.BORROWING[ticker]}
        if ticker == "VST":
            tags.add("vistra:PaymentsToAcquirePropertyPlantAndEquipmentAndNuclearFuel")
        observations = [source]
        if ticker == "VST" and source["period_end"] in {"2022-12-31", "2025-12-31"}:
            year = int(source["period_end"][:4])-1
            observations.append({**source, "period_start": f"{year}-01-01", "period_end": f"{year}-12-31"})
        if ticker == "LLY" and source["period_end"] == "2023-12-31":
            observations += [{**source, "period_start": f"{y}-01-01", "period_end": f"{y}-12-31"}
                             for y in (2021, 2022)]
        soup = BeautifulSoup(path.read_bytes(), "lxml")
        for observation in observations:
            loc = {}
            for tag in (history.CASH, history.OCF, history.LLY_CAPEX if ticker == "LLY" else history.CAPEX,
                        *history.BORROWING[ticker], history.TOTALS[ticker]):
                duration = tag in {history.OCF, history.CAPEX, history.LLY_CAPEX}
                r = (fx.read_duration(path, source["accession"], tag, observation["period_start"], observation["period_end"])
                     if duration else fx.read_instant(path, source["accession"], tag, observation["period_end"]))
                loc[tag] = (locate(soup, r) if r["value"] is not None else
                            {"printed_page": None, "row_text": None, "context_id": None,
                             "note": "No exact-date consolidated fact for this tag in the selected filing."})
            key = source["accession"] if observation is source else source["accession"]+":"+observation["period_end"]
            locations[key] = loc

        facts = []
        for fact in tree.iter(f"{{{fx.IX}}}nonFraction"):
            c = contexts.get(fact.get("contextRef"), {})
            if fact.get("name") in tags and any(c.get("instant") == o["period_end"] or
                    (c.get("start") == o["period_start"] and c.get("end") == o["period_end"]) for o in observations):
                facts.append(fact)
        context_ids = {f.get("contextRef") for f in facts}
        unit_ids = {f.get("unitRef") for f in facts}
        nodes = [n for n in tree.iter() if n.tag == f"{{{fx.XBRLI}}}context" and n.get("id") in context_ids]
        nodes += [n for n in tree.iter() if n.tag == f"{{{fx.XBRLI}}}unit" and n.get("id") in unit_ids]
        nodes += facts
        # iterparse emits (event, (prefix, URI)); preserve prefixes used by QName values too.
        bindings = dict(value for _, value in ET.iterparse(BytesIO(path.read_bytes()), events=["start-ns"]))
        used = {n.tag[1:].split("}")[0] for node in nodes for n in node.iter() if n.tag.startswith("{")}
        used |= {k[1:].split("}")[0] for node in nodes for n in node.iter() for k in n.attrib if k.startswith("{")}
        for prefix, uri in bindings.items():
            if prefix and not prefix.startswith("ns"):
                ET.register_namespace(prefix, uri)
        root = ET.Element("annual-fixture", {"xmlns:"+p: uri for p, uri in bindings.items() if p and uri not in used})
        for node in nodes:
            copied = deepcopy(node)
            copied.tail = None
            root.append(copied)
        target = dest / (ticker + "_" + source["document"])
        content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        target.write_bytes(content)
        meta[source["accession"]] = {"document": target.name, "sha256": hashlib.sha256(content).hexdigest(),
                                     "facts": len(facts), "contexts": len(context_ids)}
    (dest / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    (ROOT / "tests/fixtures/annual_history_locations.json").write_text(json.dumps(locations, indent=2) + "\n")
    print("Preserved", len(meta), "source subsets and", len(locations), "dated statement-location sets")


if __name__ == "__main__":
    build(ROOT.parent / "data/raw")
