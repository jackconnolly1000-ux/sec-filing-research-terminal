"""General research records: original findings plus explicit SEC calculation inputs.

Workbook layout is authored offline with Artifact Tool. Runtime hydrates that verified layout
using OpenXML so Streamlit needs no Node process or spreadsheet authoring dependency.
"""
from datetime import date, datetime
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import ui
import xbrl

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "samples/research_template.xlsx"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def tables(profiles, run_at=None):
    profiles = list(profiles)
    run_at = run_at or datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")
    rows = {"Research record": [["Research record", "General filing research — experimental"],
        ["Companies", ", ".join(p["ticker"] for p in profiles)], ["Export created", str(run_at)],
        ["Record version", "1"], ["Scope", "Saved findings, market data and SEC calculations. Not investment advice."],
        ["Data dates", "Each metric retains its own period and retrieval time. Export time is not a market quote time or filing date."],
        ["Reading order", "Market data, Findings and 8-K events contain results. Data retains SEC inputs; Evidence and Filing review retain retrieval and review limits. About explains units and colors."],
        ["Source distinction", "Yahoo margins can use an unstated period. SEC margins use the stated TTM period. Different sources and definitions are not interchangeable."],
        ["AI figures", "AI narrative is retained as written with its filing period, excerpt check and unsupported-figure flags. A filing's report date does not establish the period of every number in the narrative."]],}
    ws = rows["Market data"] = []
    ws.append(["Ticker", "Metric", "Value", "Unit", "Period", "Source", "Retrieved at", "Filings used"])
    for p in profiles:
        f = p["financials"]
        if f["status"] != "ok":
            ws.append([p["ticker"], "All Yahoo metrics", None, None, None, f"Failed: {f['reason']}", None])
        else:
            for m in f["metrics"].values():
                ws.append([p["ticker"], m["label"], m["value"], m["unit"], m["period"] or "Period not stated",
                           f"{f['source']}: {m['field']}", f["retrieved_at"]])
        sec = p.get("sec_metrics")
        if sec and sec["status"] != "ok":
            ws.append([p["ticker"], "All SEC metrics", None, None, None, f"Failed: {sec['reason']}", None])
        elif sec:
            for key, m in sec["metrics"].items():
                op = " minus " if key == "free_cash_flow" else " / "   # FCF subtracts capex; the margins divide by revenue
                tags = op.join(m["tags"]) if m["tags"] else f"{xbrl.NOT_REPORTED} ({m['detail']})"
                ws.append([p["ticker"], m["label"], m["value"], m["unit"], f"TTM to {m['period_end']}",
                           f"{sec['source']}: {tags}", sec["retrieved_at"],
                           "; ".join(f"{x['form']} {x['accession']} (period {x['period']}, filed {x['filed']})" for x in m["filings"])])

    ws = rows["Findings"] = []
    ws.append(["Ticker", "Type", "Headline", "Summary", "Potential implication", "Detail", "Impact (AI assessment)",
               "Impact basis", "Change vs prior 10-K (code)", "Category", "Source", "Form", "Filed", "Period", "Quote",
               "Excerpt check", "Figures not in cited source", "Wording flags", "Filing URL", "Other sources for figures"])
    for p in profiles:
        for kind in ("catalysts", "risks", "other_risks"):
            for i in p["analysis"]["sections"][kind]["items"]:
                s = i["source"]
                ws.append([p["ticker"], {"catalysts": "Catalyst", "risks": "Risk factor change",
                                         "other_risks": "Other risk (management's discussion)"}[kind], i["headline"], i["summary"], i["implication"], i["detail"],
                           i["impact"], i["impact_basis"], ui.trend_text(i) if kind == "risks" else "", i["category"],
                           s["role"], s["form"], s["filed"], s["period"], i["quote"], i["excerpt"]["status"],
                           "; ".join(i.get("unsupported_figures", [])), "; ".join(i.get("wording_flags", [])), s["url"],
                           "; ".join(f"{o['label']} {o['url']}" for o in i.get("other_sources", []))])

    ws = rows["8-K events"] = []
    ws.append(["Ticker", "Filed", "Event date", "8-K items", "Category", "Headline", "Summary", "Quote", "Excerpt check", "Filing URL"])
    for p in profiles:
        for e in p["analysis"]["sections"]["events"]["items"]:
            s = e["source"]
            ws.append([p["ticker"], s["filed"], s["period"], s.get("items", ""), e["category"], e["headline"],
                       e["summary"], e["quote"], e["excerpt"]["status"], s["url"]])

    ws = rows["Evidence"] = []
    ws.append(["Ticker", "Source ID", "Source", "Status", "Form", "Filed", "Period", "Characters found",
               "Characters sent", "Characters omitted", "Note", "Filing URL"])
    for p in profiles:
        for c in p["evidence"]:
            ws.append([p["ticker"], c["id"], c["role"], c["status"], c.get("form"), c.get("filed"), c.get("period"),
                       c["chars"], c["sent_chars"], c["omitted_chars"], c["note"], c.get("url")])

    ws = rows["Filing review"] = []
    ws.append(["Ticker", "Balance-sheet date", "Index through", "Index status", "Form", "Filed", "Report date",
               "8-K items", "Accession", "Content review", "EDGAR index", "Index note",
               "Event date", "Amount type", "Checked finding", "Source document", "Related documents"])
    for p in profiles:
        inv = p.get("filing_review")
        if not inv:
            ws.append([p["ticker"], None, None, "Not checked", None, None, None, None, None, None, None,
                       "Saved result has no subsequent-filing index."])
            continue
        for f in inv["filings"]:
            ws.append([p["ticker"], inv["since"], inv["through"], inv["status"], f["form"], f["filed"],
                       f["period"], f["items"], f["accession"], f["review"], f["url"], "; ".join(inv["notes"]),
                       f.get("event_date"), f.get("kind"), f.get("finding"), f.get("source_url"),
                       "; ".join(url for _, url in f.get("related", []))])
        if not inv["filings"]:
            ws.append([p["ticker"], inv["since"], inv["through"], inv["status"], None, None, None, None, None,
                       "Not checked", None, "; ".join(inv["notes"]) or "No candidate forms indexed; contents not reviewed."])

    rows["Data"] = [["Ticker", "Metric", "Tag", "TTM role", "Value (USD, displayed in millions)",
                     "Period start", "Period end", "Form", "Filed", "Accession", "Source URL", "Notes"]]
    for p in profiles:
        sec = p.get("sec_metrics", {})
        if sec.get("status") != "ok":
            continue
        for key, metric in sec["metrics"].items():
            refs = {}
            calculated = {}
            for fact in metric.get("components", []):
                url = next((e.get("url") for e in p["evidence"] if e.get("accession") == fact["accession"] and e.get("url")), None)
                rows["Data"].append([p["ticker"], metric["label"], fact["tag"], fact["role"], fact["value"],
                    fact["start"], fact["end"], fact["form"], fact["filed"], fact["accession"],
                    url or "Source URL not retained", "Reported SEC companyfacts component; no missing value is filled with zero."])
                refs.setdefault(fact["tag"], []).append((len(rows["Data"]), fact))
            for tag, facts in refs.items():
                roles = [f["role"] for _, f in facts]
                valid = sorted(roles) == sorted(["fiscal year", "current year to date", "prior year to date"]) or roles == ["fiscal year"]
                if not valid or any(not isinstance(f["value"], (int, float)) or not math.isfinite(f["value"]) for _, f in facts):
                    continue
                terms = [(('-' if f["role"] == "prior year to date" else '+'), r, f["value"]) for r, f in facts]
                formula = ''.join(sign + f"'Data'!E{r}" for sign, r, _ in terms).lstrip('+')
                value = sum((-v if sign == '-' else v) for sign, _, v in terms)
                calculated[tag] = (formula, value)
            tags = metric["tags"]
            if metric["value"] is None:
                continue
            if any(tag not in calculated for tag in tags) or not tags:
                # Older saved profiles may lack inputs. Preserve their result, with an explicit limit.
                for row in rows["Market data"][1:]:
                    if row[0] == p["ticker"] and row[1] == metric["label"] and str(row[5]).startswith(sec["source"]):
                        row[5] += "; calculated result retained; component formula unavailable"
                continue
            expression, value = calculated[tags[0]]
            if len(tags) == 2:
                rhs, rhs_value = calculated[tags[1]]
                if key == "free_cash_flow":
                    expression, value = f"({expression})-({rhs})", value-rhs_value
                elif rhs_value:
                    expression, value = f"({expression})/({rhs})", value/rhs_value
                else:
                    raise ValueError("SEC calculation has a zero denominator")
            if not math.isclose(value, metric["value"], rel_tol=1e-10, abs_tol=1e-5):
                raise ValueError("SEC result does not reconcile to its retained components")
            for row in rows["Market data"][1:]:
                if row[0] == p["ticker"] and row[1] == metric["label"] and str(row[5]).startswith(sec["source"]):
                    row[2] = {"formula": expression, "value": value}
    rows["Market data"][0][2] = "Value (see unit)"
    for row in rows["Market data"][1:]:
        if row[3] == "USD":
            row[3] = "USD per share" if any(k in str(row[5]) for k in ("currentPrice", "regularMarketPrice")) else "USD, displayed in millions"
        elif row[3] == "fraction":
            row[3] = "fraction, displayed as %"
        elif row[3] == "multiple":
            row[3] = "multiple (x)"
    rows["About"] = [["Topic", "Meaning"],
        ["Units", "Dollar amounts are stored in whole USD and displayed in millions. Share prices are USD per share. Percentages are stored as fractions; multiples display x. Character counts are integers."],
        ["Colors", "Blue text: retained numeric inputs. Green: formulas linking to another sheet. Black: narrative and labels. No editable scenario assumptions are introduced."],
        ["Calculations", "Market data formulas use SEC components in Data: fiscal year plus current YTD less prior YTD. Margins divide the matching components; FCF subtracts capex from OCF. Formula caches match the saved result. Older profiles without components are explicitly labelled."],
        ["Source dates", "Market retrieval time, filing date and fiscal period are different. A source with no period says Period not stated. The report period alongside an AI finding does not verify each narrative number's period."],
        ["Narrative", "AI assessments and potential implications are retained with excerpt checks, unsupported figures and wording flags. They are not verified forecasts. Filing review distinguishes an indexed candidate from reviewed content."],
        ["Limits", "This experimental general-research record is separate from the three checked debt/liquidity reviews. Saved archived examples retain their original dates. Not investment advice."],
        ["Links", "Source URLs link to their displayed address. Missing source URLs remain explicit; no replacement URL is guessed."]]
    return rows


def _column(k):
    name = ""
    while k:
        k, r = divmod(k-1, 26)
        name = chr(65+r) + name
    return name


def workbook(profiles, run_at=None):
    payload = tables(profiles, run_at)
    raw = TEMPLATE.read_bytes()
    meta = json.loads(TEMPLATE.with_suffix(".manifest.json").read_text())
    if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
        raise ValueError("Research workbook layout changed; rebuild and verify its template")
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(raw)) as src, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
        replacements = {}
        for name, values in payload.items():
            layout = meta["sheets"][name]
            sheet = ET.fromstring(src.read(layout["path"]))
            data = sheet.find(f"{{{NS}}}sheetData")
            prototypes = list(data)
            data.clear()
            links = []
            for r, row in enumerate(values, 1):
                # Each row keeps its role's authored styles while allowing arbitrary record counts.
                template = prototypes[0 if r == 1 else 1]
                new = ET.SubElement(data, f"{{{NS}}}row", r=str(r))
                widths = layout["widths"]
                lines = max((math.ceil(len(str(v))/(widths[k]*.85)) for k, v in enumerate(row) if isinstance(v, str)), default=1)
                new.set('ht', str(max(28, min(400, 14*lines+12))))
                new.set('customHeight','1')
                cells = list(template)
                for k, v in enumerate(row, 1):
                    c = ET.SubElement(new, f"{{{NS}}}c", r=_column(k)+str(r), s=cells[k-1].get('s', '0'))
                    if v is None:
                        continue
                    if isinstance(v, str) and len(v)==10 and v[4]=='-' and v[7]=='-':
                        try:
                            v=date.fromisoformat(v)
                        except ValueError:
                            pass
                    if isinstance(v, date):
                        c.set('s',meta['styles']['date'])
                        ET.SubElement(c,f'{{{NS}}}v').text=str((v-date(1899,12,30)).days)
                    elif isinstance(v, dict):
                        c.set('s', meta['styles']['formula_fraction' if values[r-1][3]=='fraction, displayed as %' else 'formula_usd'])
                        ET.SubElement(c, f"{{{NS}}}f").text = v['formula']
                        ET.SubElement(c, f"{{{NS}}}v").text = str(v['value'])
                    elif isinstance(v, (int,float)):
                        if name == 'Market data' and k==3:
                            key={'USD per share':'price','fraction, displayed as %':'fraction','multiple (x)':'multiple'}.get(row[3],'usd')
                        elif name == 'Data' and k==5:
                            key='usd'
                        else:
                            key='integer'
                        c.set('s',meta['styles'][key])
                        ET.SubElement(c,f"{{{NS}}}v").text=str(v)
                    else:
                        c.set('t','inlineStr')
                        ET.SubElement(ET.SubElement(c,f"{{{NS}}}is"),f"{{{NS}}}t").text=str(v)
                        if str(v).startswith('https://') and not any(ch.isspace() for ch in str(v)):
                            links.append((c.get('r'),str(v)))
            dimension = sheet.find(f"{{{NS}}}dimension")
            if dimension is None:
                dimension = ET.Element(f"{{{NS}}}dimension")
                index = 1 if len(sheet) and sheet[0].tag == f"{{{NS}}}sheetPr" else 0
                sheet.insert(index, dimension)
            dimension.set('ref',f'A1:{_column(len(values[0]))}{len(values)}')
            if links:
                block = ET.Element(f"{{{NS}}}hyperlinks")
                rels = ET.Element(f'{{{PKG}}}Relationships')
                for n,(ref,url) in enumerate(links):
                    rid='rIdSource'+str(n)
                    ET.SubElement(block,f"{{{NS}}}hyperlink",{'ref':ref,f'{{{REL}}}id':rid})
                    ET.SubElement(rels,f'{{{PKG}}}Relationship',Id=rid,Type=REL+'/hyperlink',Target=url,TargetMode='External')
                position=next((i for i,x in enumerate(sheet) if x.tag==f'{{{NS}}}pageMargins'),len(sheet))
                sheet.insert(position,block)
                replacements[layout['path'].replace('worksheets/','worksheets/_rels/')+'.rels']=ET.tostring(rels)
            replacements[layout['path']]=ET.tostring(sheet,encoding='utf-8',xml_declaration=True)
        for name in src.namelist():
            dst.writestr(name,replacements.pop(name,src.read(name)))
        for name, content in replacements.items():
            dst.writestr(name,content)
    return out.getvalue()
