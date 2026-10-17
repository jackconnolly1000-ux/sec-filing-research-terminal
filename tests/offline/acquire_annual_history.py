"""Acquire the inventory's exact original sources outside git; never replace a reviewed hash.

Run from the repo with SEC_CONTACT_EMAIL set, or pass --user-agent with identifying contact
information. The raw companyfacts endpoint changes over time; later captures require review
and cannot reproduce the old raw snapshot hash. Committed trimmed fixtures preserve that check.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def acquire(raw_root, user_agent):
    inventory = json.loads((ROOT / "samples/annual_source_inventory.json").read_text())
    jobs = []
    for source in inventory["sources"]:
        jobs.append((raw_root / "sec" / source["ticker"] / source["document"], source))
        jobs += [(raw_root / "sec" / source["ticker"] / entry["document"], entry)
                 for entry in source.get("extension_definition_sources", [])]
    jobs += [(raw_root / "xbrl" / item["document"], item) for item in inventory["companyfacts"]]
    jobs += [(raw_root / "sec" / item["ticker"] / item["document"], item)
             for item in inventory["submission_sources"]]
    for target, item in jobs:
        if target.exists():
            content = target.read_bytes()
        else:
            with urlopen(Request(item["source_url"], headers={"User-Agent": user_agent}), timeout=60) as response:
                content = response.read()
            time.sleep(.2)  # Stay below EDGAR's request limit even on a fast connection.
        if hashlib.sha256(content).hexdigest() != item["source_sha256"]:
            raise ValueError(f"Reviewed hash differs: {item['document']}. Keep the saved snapshot or review a new capture.")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(content)
        print(target.name, "verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT.parent / "data/raw")
    parser.add_argument("--user-agent", default=("SEC Filing Research Terminal " + os.environ["SEC_CONTACT_EMAIL"])
                        if os.environ.get("SEC_CONTACT_EMAIL") else None)
    args = parser.parse_args()
    if not args.user_agent:
        parser.error("Set SEC_CONTACT_EMAIL or supply --user-agent; do not invent contact information.")
    acquire(args.raw, args.user_agent)
