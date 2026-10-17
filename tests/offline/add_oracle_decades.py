"""Split the Oracle workbook's FY2032-onward principal by decade (Oct 17, 2026; roadmap item 11).

The Payment dates sheet's fiscal-year calendar ends with one "Thereafter" row ($90.25B). This adds a small block
beside it (E48:F54; the ladder chart starts at column H) with one SUMIFS per decade over the existing instrument rows
(B95:B152 maturity, E95:E152 August 31 principal), the sum of the decades and its difference from Thereafter (C54),
which should be zero. The formulas carry their computed values so readers that don't recalculate show them too.
Only the Payment dates sheet XML changes; every other part is copied byte for byte. The Oracle manifest's workbook
SHA-256 is rebound.

Run once from app/:  .venv/Scripts/python tests/offline/add_oracle_decades.py
"""
import hashlib
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import oracle_principal as op  # noqa: E402

WORKBOOK = ROOT / "samples/oracle_liquidity.xlsx"
MANIFEST = WORKBOOK.with_suffix(".manifest.json")
SHEET = "xl/worksheets/sheet8.xml"           # Payment dates
# Styles already used by the fiscal-year calendar in A48:D55 (header, row label, USD millions, total label/value)
HEAD_FIRST, HEAD, LABEL, NUMBER, TOTAL_LABEL, TOTAL = "469", "470", "378", "472", "473", "474"


def text(ref, value, style):
    return f'<x:c r="{ref}" s="{style}" t="str"><x:v>{escape(value)}</x:v></x:c>'


def formula(ref, expression, value, style):
    return f'<x:c r="{ref}" s="{style}" t="n"><x:f>{escape(expression)}</x:f><x:v>{value}</x:v></x:c>'


def block(review):
    rows = op.by_decade(review)
    if rows is None:
        raise SystemExit("Decades do not add up to the Thereafter amount; nothing changed")
    cells = {48: text("E48", "FY2032 onward, by decade", HEAD_FIRST) + text("F48", "Principal (USD millions)", HEAD)}
    for k, r in enumerate(rows):
        row = 49 + k
        (y1, m1, d1), (y2, m2, d2) = (map(int, r["start"].split("-")), map(int, r["end"].split("-")))
        sumifs = (f'SUMIFS($E$95:$E$152,$B$95:$B$152,">="&DATE({y1},{m1},{d1}),'
                  f'$B$95:$B$152,"<="&DATE({y2},{m2},{d2}),$F$95:$F$152,"<>Term loan")')
        cells[row] = text(f"E{row}", r["label"], LABEL) + formula(f"F{row}", sumifs, r["principal"], NUMBER)
    total = sum(r["principal"] for r in rows)
    cells[53] = text("E53", "Sum of decades", TOTAL_LABEL) + formula("F53", "SUM(F49:F52)", total, TOTAL)
    cells[54] = text("E54", "Less Thereafter (C54); should be 0", LABEL) + formula("F54", "F53-C54", 0, NUMBER)
    return cells


def patch(xml, cells):
    for row, extra in cells.items():
        start = xml.index(f'<x:row r="{row}"')
        end = xml.index("</x:row>", start)
        if f'r="E{row}"' in xml[start:end] or f'r="F{row}"' in xml[start:end]:
            raise SystemExit(f"Row {row} already has cells in E or F; nothing changed")
        xml = xml[:end] + extra + xml[end:]     # rows 48-54 end at column D, so E and F follow in order
    return xml


def main():
    review = op.load()
    if review is None:
        raise SystemExit("Checked principal calendar Unavailable; nothing changed")
    content = WORKBOOK.read_bytes()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if hashlib.sha256(content).hexdigest() != manifest["workbook_sha256"]:
        raise SystemExit("Workbook does not match its manifest; nothing changed")
    src = zipfile.ZipFile(BytesIO(content))
    sheet = patch(src.read(SHEET).decode("utf-8"), block(review)).encode("utf-8")
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, sheet if info.filename == SHEET else src.read(info.filename))
    new = out.getvalue()
    WORKBOOK.write_bytes(new)
    manifest["workbook_sha256"] = hashlib.sha256(new).hexdigest()
    MANIFEST.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))   # LF, as git stores it
    print("Decade block added;", WORKBOOK.name, manifest["workbook_sha256"][:12])


if __name__ == "__main__":
    main()
