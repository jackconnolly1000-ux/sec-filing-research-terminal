"""Open the scenario workbook's Results sheet with what it is (Oct 17, 2026; first-time-reader obstacle 2).

The first sheet showed simulated figures such as a mean ending cash of -$11,233M with no statement that they come
from assumptions; the label sat on the sixth sheet and About was last. This patch moves the Results table down two
rows and reserves row 1 for that label and row 2 for a pointer to About, linked to its first cell. The frozen header
moves with the table. Every other part of the template is copied byte for byte, and the template manifest records
the new row count and SHA-256. scenario_export.tables() writes the two rows on every download.

Run once from app/:  .venv/Scripts/python tests/offline/patch_scenario_results_label.py
"""
import hashlib
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "samples/scenario_template.xlsx"
MANIFEST = TEMPLATE.with_suffix(".manifest.json")
SHEET = "xl/worksheets/sheet1.xml"
SHIFT = 2
LABEL_STYLE, NOTE_STYLE = "56", "55"   # the Scenario sheet's own title and note styles (bold / plain Arial 10)


def shift_rows(xml: str) -> str:
    start, end = xml.index("<x:sheetData>"), xml.index("</x:sheetData>")
    data = xml[start:end]
    if '<x:row r="1" ht="40"' not in data or 'r="A1" s="31"' not in data:
        raise SystemExit("Results sheet is not the unpatched layout; nothing changed")
    data = re.sub(r'<x:row r="(\d+)"', lambda m: f'<x:row r="{int(m[1]) + SHIFT}"', data)
    data = re.sub(r'<x:c r="([A-Z]+)(\d+)"', lambda m: f'<x:c r="{m[1]}{int(m[2]) + SHIFT}"', data)
    reserved = (f'<x:row r="1" ht="22" customHeight="1"><x:c r="A1" s="{LABEL_STYLE}" /></x:row>'
                f'<x:row r="2" ht="22" customHeight="1"><x:c r="A2" s="{NOTE_STYLE}" /></x:row>')
    data = data.replace("<x:sheetData>", "<x:sheetData>" + reserved, 1)
    xml = xml[:start] + data + xml[end:]
    pane = '<x:pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen" />'
    if xml.count(pane) != 1:
        raise SystemExit("Unexpected frozen pane")
    xml = xml.replace(pane, f'<x:pane ySplit="{1 + SHIFT}" topLeftCell="A{2 + SHIFT}" activePane="bottomLeft" state="frozen" />')
    # An internal link (a location, no relationship) from the pointer row to About; hydration keeps it
    link = """<x:hyperlinks><x:hyperlink ref="A2" location="'About'!A1" display="About" /></x:hyperlinks>"""
    return xml.replace("<x:pageMargins", link + "<x:pageMargins", 1)


def main():
    content = TEMPLATE.read_bytes()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
        raise SystemExit("Template does not match its manifest; nothing changed")
    src = zipfile.ZipFile(BytesIO(content))
    patched = shift_rows(src.read(SHEET).decode("utf-8")).encode("utf-8")
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, patched if info.filename == SHEET else src.read(info.filename))
    new = out.getvalue()
    TEMPLATE.write_bytes(new)
    manifest["sheets"]["Results"]["rows"] += SHIFT
    manifest["sha256"] = hashlib.sha256(new).hexdigest()
    MANIFEST.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))   # LF, as git stores it
    print("Results sheet labelled;", TEMPLATE.name, manifest["sha256"][:12])


if __name__ == "__main__":
    main()
