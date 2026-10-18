"""Legacy chart-cache regression fixture; workbook authoring now uses build_workbooks.py."""
import sys
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import theme as T  # noqa: E402

REF = "'Annual history'"
HELPER_ROW = 61                       # capital spending as a use (negative), below the second chart
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MILLIONS = '#,##0,,;(#,##0,,)'        # whole USD shown in millions, negatives in parentheses
# App identity colors (theme.py): cash and borrowing; flows use the app's in/out convention plus one result color
SERIES = {
    "balances": [(6, T.SERIES_CASH), (7, T.SERIES_BORROWING)],
    "flows": [(8, T.FLOW_IN), (HELPER_ROW, T.FLOW_OUT), (10, T.FLOW_RESULT)],   # out: a mid-grey legible on white
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


if __name__=="__main__":
    raise SystemExit("Retired migration. Use python tests/offline/build_workbooks.py.")
