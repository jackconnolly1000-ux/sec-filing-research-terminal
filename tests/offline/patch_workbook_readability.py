"""Readability fixes in the three saved company workbooks, then rebind each manifest (Oct 17 reader review).

1. Data-sheet dimensions were raw JSON: "[]" for a fact with no XBRL dimension, and lists such as
   [["us-gaap:LongtermDebtTypeAxis","vistra:ProjectLevelDebtMember"]] otherwise. They become
   "None (consolidated total)" and "us-gaap:LongtermDebtTypeAxis = vistra:ProjectLevelDebtMember".
2. "USD millions unless x (or %)" unit notes become "USD millions, except ratios (x) [and percentages (%)]".
3. Oracle's native ladder chart (Payment dates) was scaled by the $90.25B combined later bucket, which flattened
   the near-term years. Like the app, its value axis now runs $0-$12B in $2B steps (set by the largest single
   year), every bar carries its value, and the title says the Thereafter bar runs past the scale.

Only cell text and that one chart part change; every other byte of every part is copied unchanged, the zip
entries keep their order and settings, and each manifest's workbook_sha256 is rebound (LF bytes). The builders in
tests/offline/*.mjs now write the same text, so a rebuild needs only the chart step re-run.
Run from app/: .venv\\Scripts\\python tests/offline/patch_workbook_readability.py
"""
import hashlib
import html
import json
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
WORKBOOKS = ("lly_liquidity", "oracle_liquidity", "vistra_liquidity")
NO_DIMENSION = "None (consolidated total)"
UNITS = {"USD millions unless x or %.": "USD millions, except ratios (x) and percentages (%).",
         "USD millions unless x": "USD millions, except ratios (x)"}
LADDER_CHART = "xl/drawings/charts/chart4.xml"   # Oracle, Payment dates (attached by add_oracle_ladder.py)
AXIS_MAX, AXIS_STEP = 12_000_000_000, 2_000_000_000
TITLE_OLD = "FY2027 remainder; thereafter = FY2032 onward"
TITLE_NEW = ("FY2027 remainder. Scale ends at $12B; the hatched Thereafter bar (FY2032-FY2066 combined, $90.3B) "
             "runs past it")
THEREAFTER = 5   # last category, A54 on Payment dates


def readable_dimensions(raw: str) -> str:
    pairs = json.loads(html.unescape(raw))
    if not pairs:
        return NO_DIMENSION
    return "; ".join(f"{axis} = {member}" for axis, member in pairs)


def patch_sheet(xml: str) -> tuple[str, int]:
    count = 0

    def dims(match):
        nonlocal count
        count += 1
        return f"{match.group(1)}{html.escape(readable_dimensions(match.group(2)), quote=False)}{match.group(3)}"
    xml = re.sub(r"(<x:v>)(\[(?:\[.*?\])?(?:,\[.*?\])*\])(</x:v>)", dims, xml)
    # The longer note first, so the bare "unless x" form never matches inside it. The bare form is a whole cell.
    long_old, long_new = "USD millions unless x or %.", UNITS["USD millions unless x or %."]
    short_old, short_new = "<x:v>USD millions unless x</x:v>", f"<x:v>{UNITS['USD millions unless x']}</x:v>"
    count += xml.count(long_old) + xml.count(short_old)
    xml = xml.replace(long_old, long_new).replace(short_old, short_new)
    if "unless x" in xml:
        raise ValueError("An unexpected 'unless x' unit note remains")
    return xml, count


def patch_ladder(xml: str) -> str:
    if TITLE_OLD not in xml or "<ns0:max " in xml:
        raise ValueError("Ladder chart is not in the expected original form")
    xml = xml.replace(TITLE_OLD, TITLE_NEW)
    # Value axis: fixed 0-12B scale in 2B steps (schema order: orientation, max, min; majorUnit after crossBetween).
    val_axis = xml[xml.index("<ns0:valAx>"):]
    new_axis = val_axis.replace('<ns0:scaling><ns0:orientation val="minMax" /></ns0:scaling>',
                                f'<ns0:scaling><ns0:orientation val="minMax" /><ns0:max val="{AXIS_MAX}" />'
                                '<ns0:min val="0" /></ns0:scaling>', 1)
    new_axis = new_axis.replace('<ns0:crossBetween val="between" />',
                                f'<ns0:crossBetween val="between" /><ns0:majorUnit val="{AXIS_STEP}" />', 1)
    xml = xml.replace(val_axis, new_axis)
    # Value labels on every bar, in $B, so the clipped Thereafter bar still states its amount.
    labels = ('<ns0:dLbls><ns0:numFmt formatCode="&quot;$&quot;#,##0.0,,,&quot;B&quot;" sourceLinked="0" />'
              '<ns0:txPr><ns1:bodyPr /><ns1:lstStyle /><ns1:p><ns1:pPr><ns1:defRPr sz="750" b="1">'
              '<ns1:latin typeface="Arial" /><ns1:ea typeface="Arial" /><ns1:cs typeface="Arial" /></ns1:defRPr>'
              '</ns1:pPr></ns1:p></ns0:txPr><ns0:dLblPos val="inEnd" /><ns0:showLegendKey val="0" />'
              '<ns0:showVal val="1" /><ns0:showCatName val="0" /><ns0:showSerName val="0" /><ns0:showPercent val="0" />'
              '<ns0:showBubbleSize val="0" /></ns0:dLbls>')
    # The clipped bar gets a hatched fill (Excel has no break mark), so it reads as cut, not as a $12B year.
    hatched = (f'<ns0:dPt><ns0:idx val="{THEREAFTER}" /><ns0:invertIfNegative val="0" /><ns0:bubble3D val="0" />'
               '<ns0:spPr><ns1:pattFill prst="wdUpDiag"><ns1:fgClr><ns1:srgbClr val="D95926" /></ns1:fgClr>'
               '<ns1:bgClr><ns1:srgbClr val="F6D2C2" /></ns1:bgClr></ns1:pattFill></ns0:spPr></ns0:dPt>')
    anchor = '<ns0:invertIfNegative val="0" />'
    if xml.count(anchor) != 1 or "<ns0:pt idx=\"5\"><ns0:v>Thereafter</ns0:v>" not in xml:
        raise ValueError("Expected one series ending with the Thereafter category")
    return xml.replace(anchor, anchor + hatched + labels)


def main() -> None:
    for name in WORKBOOKS:
        path = SAMPLES / f"{name}.xlsx"
        source = zipfile.ZipFile(BytesIO(path.read_bytes()))
        replacements, changed = {}, 0
        for part in source.namelist():
            if part.startswith("xl/worksheets/sheet") and part.endswith(".xml"):
                original = source.read(part).decode("utf-8")
                patched, count = patch_sheet(original)
                if patched != original:
                    replacements[part] = patched.encode("utf-8")
                    changed += count
        chart = source.read(LADDER_CHART).decode("utf-8") if name == "oracle_liquidity" else ""
        if chart and TITLE_NEW not in chart:
            replacements[LADDER_CHART] = patch_ladder(chart).encode("utf-8")
        if not replacements:
            print(f"{name}: already patched")
            continue
        out = BytesIO()
        with zipfile.ZipFile(out, "w") as dest:
            for info in source.infolist():
                dest.writestr(info, replacements.get(info.filename, source.read(info.filename)))
        content = out.getvalue()
        path.write_bytes(content)
        manifest_path = SAMPLES / f"{name}.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["workbook_sha256"] = hashlib.sha256(content).hexdigest()
        manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        print(f"{name}: {len(replacements)} parts patched; workbook_sha256 {manifest['workbook_sha256']}")


if __name__ == "__main__":
    sys.exit(main())
