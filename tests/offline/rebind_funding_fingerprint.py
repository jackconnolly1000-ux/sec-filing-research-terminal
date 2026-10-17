"""Rebind the three company manifests to the current funding_conclusions.py fingerprint.

Use only when funding_conclusions.py changes without changing anything a workbook contains (Oct 17, 2026: the plain
"Future funding coverage: Unavailable" answer, its one-line reasons and the terms list are shown in the app only; the
workbooks' Decisive unknowns rows already begin with that answer). Workbook bytes are not touched; the script refuses
to run if a workbook no longer matches its manifest, so it can't hide a real change.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import funding_conclusions as fc  # noqa: E402

SAMPLES = ROOT / "samples"


def main():
    new = fc.fingerprint()
    for stem in ("lly_liquidity", "oracle_liquidity", "vistra_liquidity"):
        path = SAMPLES / f"{stem}.manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        workbook = hashlib.sha256((SAMPLES / f"{stem}.xlsx").read_bytes()).hexdigest()
        if manifest.get("workbook_sha256") != workbook:
            raise SystemExit(f"{stem}.xlsx does not match its manifest; rebuild or patch it instead")
        manifest["funding_sha256"] = new
        path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))   # LF, as git stores it
    print("Three manifests rebound to", new[:12])


if __name__ == "__main__":
    main()
