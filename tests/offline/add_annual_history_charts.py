"""Add two native five-year charts to each company workbook's Annual history sheet (Oct 17, 2026).

1. Fiscal-year-end cash and baseline borrowing (clustered columns), bound to the table's rows 6 and 7.
2. Annual OCF, capital spending and FCF (clustered columns), bound to rows 8 and 10 and to one helper row (61) that
   shows capital spending as a use of cash (the negative of row 9), the same convention as the app.

Why a Python XML patch: tests/offline/integrate_annual_history.mjs has a --charts branch, but it needs Node and the
Artifact Tool runtime, neither available on the build laptop, and its chart-data links (=B7) would chart a missing
value as zero. Here every series cell is a table formula that already returns NA() when an input is missing, and an
#N/A cell draws no column: a gap, never a zero. The charts carry cached points from the table's cached values, so
readers that don't recalculate show the same numbers.

Only the Annual history sheet XML, its new relationships, one drawing, two charts and [Content_Types].xml change;
every other part is copied byte for byte. Each manifest's workbook SHA-256 and annual-history fingerprint are rebound.

Run once from app/:  .venv/Scripts/python tests/offline/add_annual_history_charts.py
"""
import hashlib
import json
import posixpath
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import annual_history_view  # noqa: E402
import theme as T  # noqa: E402

STEMS = {"LLY": "lly_liquidity", "ORCL": "oracle_liquidity", "VST": "vistra_liquidity"}
SHEET = "Annual history"
REF = "'Annual history'"
COLS = "BCDEF"
HELPER_ROW = 61                       # capital spending as a use (negative), below the second chart
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = R
MILLIONS = '#,##0,,;(#,##0,,)'        # whole USD shown in millions, negatives in parentheses
# App identity colors (theme.py): cash and borrowing; flows use the app's in/out convention plus one result color
SERIES = {
    "balances": [(6, T.SERIES_CASH), (7, T.SERIES_BORROWING)],
    "flows": [(8, T.FLOW_IN), (HELPER_ROW, "#7F838C"), (10, "#47627F")],   # out: a mid-grey legible on white
}
TITLES = {"balances": "Fiscal-year-end cash and baseline borrowing (USD millions)",
          "flows": "Annual operating cash flow, capital spending (a use, below zero) and FCF (USD millions)"}


def text_props(size=1000, bold=False):
    return (f'<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="{size}" b="{int(bold)}">'
            '<a:latin typeface="Arial"/><a:cs typeface="Arial"/></a:defRPr></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr>')


def chart_xml(kind, labels, values):
    """One clustered column chart. labels: the five FY labels; values: {row: [five numbers or None]}."""
    cats = "".join(f'<c:pt idx="{i}"><c:v>{escape(v)}</c:v></c:pt>' for i, v in enumerate(labels))
    series = ""
    for k, (row, color) in enumerate(SERIES[kind]):
        name, points = values[row]
        pts = "".join(f'<c:pt idx="{i}"><c:v>{v!r}</c:v></c:pt>' for i, v in enumerate(points) if v is not None)
        series += (f'<c:ser><c:idx val="{k}"/><c:order val="{k}"/>'
                   f'<c:tx><c:strRef><c:f>{REF}!$A${row}</c:f><c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>{escape(name)}</c:v></c:pt></c:strCache></c:strRef></c:tx>'
                   f'<c:spPr><a:solidFill><a:srgbClr val="{color.lstrip("#").upper()}"/></a:solidFill></c:spPr>'
                   '<c:invertIfNegative val="0"/>'
                   f'<c:cat><c:strRef><c:f>{REF}!$B$5:$F$5</c:f><c:strCache><c:ptCount val="5"/>{cats}</c:strCache></c:strRef></c:cat>'
                   f'<c:val><c:numRef><c:f>{REF}!$B${row}:$F${row}</c:f><c:numCache><c:formatCode>{escape(MILLIONS)}</c:formatCode>'
                   f'<c:ptCount val="5"/>{pts}</c:numCache></c:numRef></c:val></c:ser>')
    grid = '<c:majorGridlines><c:spPr><a:ln w="6350"><a:solidFill><a:srgbClr val="D9D9D9"/></a:solidFill></a:ln></c:spPr></c:majorGridlines>'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<c:chartSpace xmlns:c="{C}" xmlns:a="{A}" xmlns:r="{R}"><c:roundedCorners val="0"/><c:chart>'
            f'<c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1100" b="1"><a:latin typeface="Arial"/></a:defRPr></a:pPr>'
            f'<a:r><a:rPr lang="en-US" sz="1100" b="1"><a:latin typeface="Arial"/></a:rPr><a:t>{escape(TITLES[kind])}</a:t></a:r></a:p></c:rich></c:tx>'
            '<c:overlay val="0"/></c:title><c:autoTitleDeleted val="0"/><c:plotArea><c:layout/>'
            f'<c:barChart><c:barDir val="col"/><c:grouping val="clustered"/><c:varyColors val="0"/>{series}'
            '<c:gapWidth val="80"/><c:axId val="5001"/><c:axId val="5002"/></c:barChart>'
            '<c:catAx><c:axId val="5001"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/>'
            '<c:axPos val="b"/><c:numFmt formatCode="General" sourceLinked="0"/><c:majorTickMark val="none"/>'
            f'<c:minorTickMark val="none"/><c:tickLblPos val="low"/>{text_props()}<c:crossAx val="5002"/><c:crosses val="autoZero"/>'
            '<c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/><c:noMultiLvlLbl val="0"/></c:catAx>'
            f'<c:valAx><c:axId val="5002"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="l"/>{grid}'
            '<c:title><c:tx><c:rich><a:bodyPr rot="-5400000" vert="horz"/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1000"><a:latin typeface="Arial"/></a:defRPr></a:pPr>'
            '<a:r><a:rPr lang="en-US" sz="1000"><a:latin typeface="Arial"/></a:rPr><a:t>USD millions</a:t></a:r></a:p></c:rich></c:tx><c:overlay val="0"/></c:title>'
            f'<c:numFmt formatCode="{escape(MILLIONS)}" sourceLinked="0"/><c:majorTickMark val="out"/><c:minorTickMark val="none"/>'
            f'<c:tickLblPos val="nextTo"/>{text_props()}<c:crossAx val="5001"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx>'
            f'</c:plotArea><c:legend><c:legendPos val="b"/><c:overlay val="0"/>{text_props()}</c:legend>'
            '<c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/></c:chart>'
            f'{text_props()}</c:chartSpace>')


def anchor(rel_id, first, last, number):
    return ('<xdr:twoCellAnchor editAs="oneCell">'
            f'<xdr:from><xdr:col>0</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>{first - 1}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
            f'<xdr:to><xdr:col>6</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>{last}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>'
            f'<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="{number + 1}" name="Annual chart {number}"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>'
            '<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">'
            f'<c:chart xmlns:c="{C}" r:id="{rel_id}"/></a:graphicData></a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor>')


def rebind(manifest):
    """Every fingerprint that includes annual_history_view.py: the app charts live in that module, so the history
    and core-chart fingerprints that nest it change with it."""
    import company_history
    import core_charts
    manifest["annual_history_sha256"] = annual_history_view.fingerprint()
    manifest["history_sha256"] = company_history.fingerprint()
    manifest["charts_sha256"] = core_charts.fingerprint()


def sheet_path(z):
    book, rels = z.read("xl/workbook.xml").decode(), z.read("xl/_rels/workbook.xml.rels").decode()
    rid = re.search(r'name="Annual history"[^>]*r:id="([^"]+)"', book).group(1)
    target = re.search(r'Target="([^"]+)"', re.search(r'<[^>]*Id="%s"[^>]*>' % rid, rels).group(0)).group(1)
    return target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)


def patch(ticker):
    path = ROOT / "samples" / f"{STEMS[ticker]}.xlsx"
    manifest_path = path.with_suffix(".manifest.json")
    content = path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(content).hexdigest() != manifest["workbook_sha256"]:
        raise SystemExit(f"{path.name} does not match its manifest; nothing changed")
    model = annual_history_view.build(ticker)
    src = zipfile.ZipFile(BytesIO(content))
    names = src.namelist()
    sheet = sheet_path(src)
    xml = src.read(sheet).decode("utf-8")
    if "<x:drawing " in xml or f'<x:row r="{HELPER_ROW}"' in xml:
        raise SystemExit(f"{ticker}: Annual history already has a drawing or helper row; nothing changed")
    # The checked table cells, cached: labels row 5, measures rows 6-10 (NA() cells read back as None or '#N/A')
    cached = load_workbook(BytesIO(content), data_only=True)[SHEET]
    labels = [cached[f"{c}5"].value for c in COLS]
    if labels != [f"FY{r['fiscal_year']}" for r in model["rows"]]:
        raise SystemExit(f"{ticker}: table headers do not match the checked fiscal years")
    number = lambda v: v if isinstance(v, (int, float)) else None
    values = {row: (cached[f"A{row}"].value, [number(cached[f"{c}{row}"].value) for c in COLS]) for row in (6, 7, 8, 9, 10)}
    for k, key in enumerate(annual_history_view.KEYS):          # the cached table equals the checked dataset
        if values[6 + k][1] != [r["metrics"][key]["value"] for r in model["rows"]]:
            raise SystemExit(f"{ticker}: cached {key} differs from the checked annual dataset")
    values[HELPER_ROW] = ("Capital spending (a use of cash)", [None if v is None else -v for v in values[9][1]])

    # Helper row: same label and number styles as row 9, formulas that keep a missing value as NA()
    style = lambda ref: re.search(r'<x:c r="%s" s="(\d+)"' % ref, xml).group(1)
    cells = f'<x:c r="A{HELPER_ROW}" s="{style("A9")}" t="str"><x:v>{escape(values[HELPER_ROW][0])}</x:v></x:c>'
    for c, v in zip(COLS, values[HELPER_ROW][1]):
        cached_value = "<x:v>#N/A</x:v>" if v is None else f"<x:v>{v!r}</x:v>"
        kind = ' t="e"' if v is None else ' t="n"'
        cells += f'<x:c r="{c}{HELPER_ROW}" s="{style(c + "9")}"{kind}><x:f>IF(ISNUMBER({c}9),-{c}9,NA())</x:f>{cached_value}</x:c>'
    note = ('<x:c r="A60" s="%s" t="str"><x:v>Chart data: capital spending as a use of cash, the negative of row 9 '
            '(missing years stay #N/A, so they leave a gap).</x:v></x:c>' % style("A12"))
    rows = f'<x:row r="60">{note}</x:row><x:row r="{HELPER_ROW}">{cells}</x:row>'
    xml = xml.replace("</x:sheetData>", rows + "</x:sheetData>", 1)
    if 'xmlns:r=' not in xml[:600]:
        xml = xml.replace("<x:worksheet ", f'<x:worksheet xmlns:r="{R}" ', 1)
    xml = re.sub(r'(<x:pageMargins[^>]*/>)', r'\1<x:drawing r:id="rIdAnnualCharts" />', xml, count=1)

    drawing_no = 1 + max([int(m) for n in names for m in re.findall(r"^xl/drawings/drawing(\d+)\.xml$", n)] or [0])
    chart_no = 1 + max([int(m) for n in names for m in re.findall(r"^xl/drawings/charts/chart(\d+)\.xml$", n)] or [0])
    drawing = f"xl/drawings/drawing{drawing_no}.xml"
    charts = [f"xl/drawings/charts/chart{chart_no}.xml", f"xl/drawings/charts/chart{chart_no + 1}.xml"]
    parts = {
        sheet: xml.encode("utf-8"),
        posixpath.join(posixpath.dirname(sheet), "_rels", posixpath.basename(sheet) + ".rels"):
            ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             f'<Relationship Id="rIdAnnualCharts" Type="{REL}/drawing" Target="/{drawing}"/></Relationships>').encode("utf-8"),
        drawing: ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  f'<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="{A}" xmlns:r="{R}">'
                  + anchor("rIdAnnualBalances", 24, 40, 1) + anchor("rIdAnnualFlows", 42, 58, 2) + '</xdr:wsDr>').encode("utf-8"),
        posixpath.join("xl/drawings/_rels", posixpath.basename(drawing) + ".rels"):
            ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             f'<Relationship Id="rIdAnnualBalances" Type="{REL}/chart" Target="/{charts[0]}"/>'
             f'<Relationship Id="rIdAnnualFlows" Type="{REL}/chart" Target="/{charts[1]}"/></Relationships>').encode("utf-8"),
        charts[0]: chart_xml("balances", labels, values).encode("utf-8"),
        charts[1]: chart_xml("flows", labels, values).encode("utf-8"),
    }
    if any(p in names for p in parts if p != sheet):
        raise SystemExit(f"{ticker}: a new part name already exists; nothing changed")
    types = src.read("[Content_Types].xml").decode("utf-8")
    overrides = (f'<Override PartName="/{drawing}" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml" />'
                 + "".join(f'<Override PartName="/{c}" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml" />' for c in charts))
    parts["[Content_Types].xml"] = types.replace("</Types>", overrides + "</Types>", 1).encode("utf-8")

    out = BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, parts.get(info.filename, src.read(info.filename)))
        for name in parts.keys() - set(names):
            dst.writestr(zipfile.ZipInfo(name, date_time=(2026, 10, 17, 0, 0, 0)), parts[name], zipfile.ZIP_DEFLATED)
    new = out.getvalue()
    path.write_bytes(new)
    manifest["workbook_sha256"] = hashlib.sha256(new).hexdigest()
    rebind(manifest)
    manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))   # LF, as git stores it
    print(ticker, "annual charts added;", path.name, manifest["workbook_sha256"][:12])


if __name__ == "__main__":
    if sys.argv[1:] == ["--rebind"]:          # after a later edit to annual_history_view.py; workbook bytes unchanged
        for ticker, stem in STEMS.items():
            path = ROOT / "samples" / f"{stem}.manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if hashlib.sha256((ROOT / "samples" / f"{stem}.xlsx").read_bytes()).hexdigest() != manifest["workbook_sha256"]:
                raise SystemExit(f"{stem}.xlsx does not match its manifest; nothing changed")
            rebind(manifest)
            path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        print("Three manifests rebound to the current annual-history code")
    else:
        for ticker in STEMS:
            patch(ticker)
