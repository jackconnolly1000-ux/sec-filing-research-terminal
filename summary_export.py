"""Programmatic pilot export using an Artifact Tool-authored layout, without a second spreadsheet engine."""
from datetime import date
from io import BytesIO
import hashlib,json,zipfile,math
from pathlib import Path
import xml.etree.ElementTree as ET
from xlsx_xml import column,write_cell,attach_links,NS
ROOT=Path(__file__).parent
TEMPLATE=ROOT/'samples/summary_template.xlsx'
HEADERS={
 'Debt and liquidity':['Ticker','Metric','Value','Unit','Period end','Formula','Status','Notes'],
 'Liquidity inputs':['Ticker','Metric','Reported input','Value (USD)','Period end','Form','Filed','Accession','Tag','Selection rule','Source document','Notes','Context ID','Scale','Decimals','Period start','TTM role','Coefficient'],
 'About':['Item','Description'],
 'Other obligations':['Ticker','Disclosure','Amount as disclosed','Reporting date','Classification','Filing location','Accession','Source','Notes']}
WIDTHS={'Debt and liquidity':[10,36,22,28,19,60,18,90],'Liquidity inputs':[10,36,48,22,19,14,19,32,68,65,100,70,30,12,12,19,18,16],'About':[30,115],'Other obligations':[10,35,28,19,35,50,32,100,95]}

def tables(snapshots):
    from liquidity_pilot import leaf_inputs,PILOTS
    from company_review import NOTES
    out={name:[list(head)] for name,head in HEADERS.items()}
    metrics,raw=out['Debt and liquidity'],out['Liquidity inputs']
    for snap in snapshots:
        metric_rows={}
        for key,m in snap['metrics'].items():
            n=len(metrics)+1;metric_rows[key]=n;refs=[]
            derived={'net_debt':('gross_debt','cash','-'),'free_cash_flow':('operating_cash_flow','capital_spending','-'),
                     'ocf_to_debt':('operating_cash_flow','gross_debt','/'),'fcf_to_debt':('free_cash_flow','gross_debt','/')}
            if key not in derived:
                for f in leaf_inputs(m):
                    raw.append([snap['ticker'],m['label'],f['label'],f['value'],f['period_end'],f.get('form'),f.get('filed'),f.get('accession'),f.get('tag'),f.get('selection_rule'),f.get('source_url') or snap['source_url'],'; '.join(f.get('notes',[])) or f.get('detail',''),f.get('context_id'),f.get('scale'),f.get('decimals'),f.get('period_start'),f.get('role'),f.get('coefficient')])
                    refs.append((f.get('coefficient',1),f"'Liquidity inputs'!D{len(raw)}"))
            result=None
            if m['value'] is not None:
                if key in derived:
                    a,b,op=derived[key];formula=f'C{metric_rows[a]}{op}C{metric_rows[b]}'
                elif key=='current_ratio':formula='/'.join(ref for _,ref in refs)
                else:formula=refs[0][1]+''.join(('-' if sign<0 else '+')+ref for sign,ref in refs[1:])
                result=dict(formula=formula,value=m['value'])
            notes=[*m.get('notes',[]),*m.get('caveats',[])]
            if m.get('not_added'):notes.append('Excluded: '+m['not_added'])
            metrics.append([snap['ticker'],m['label'],result,'USD (displayed in millions)' if m['unit']=='USD' else 'fraction (displayed as %)' if m['unit']=='fraction' else 'ratio',m['period_end'],m.get('formula') or m.get('tag'),('Reported' if key=='cash' else 'Calculated') if m['value'] is not None else 'Unavailable','; '.join(notes) or m.get('detail','')])
        for item in NOTES[snap['ticker']]:
            out['Other obligations'].append([snap['ticker'],item['name'],item['amount'],item['date'],item['kind'],item['location'],PILOTS[snap['ticker']]['accession'],snap['source_url'],item['detail']])
    out['About'] += [['Scope','Programmatic metric record. Individual saved reviews are the primary exports; this is not a peer ranking.'],['Units','Full USD stored, displayed in millions; percentages are fractions, ratios multiples.'],['Colors','Arial 10. Blue reported inputs, green links to another sheet, black local formulas.'],['Missing values','Unavailable inputs remain blank with a stated reason; no zero is substituted.'],['Sources','Accession-specific source URLs are clickable. Selected obligations are not a complete schedule. Not investment advice.']]
    return out

def workbook(snapshots):
    payload=tables(snapshots);raw=TEMPLATE.read_bytes();meta=json.loads(TEMPLATE.with_suffix('.manifest.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Summary layout changed; rebuild before exporting')
    replacements={}
    with zipfile.ZipFile(BytesIO(raw)) as src:
        for name,rows in payload.items():
            part=meta['sheets'][name]['path'];sheet=ET.fromstring(src.read(part));data=sheet.find('{'+NS+'}sheetData');prototypes=list(data);data.clear();links=[]
            for ri,row in enumerate(rows,1):
                lines=max((math.ceil(len(v)/(WIDTHS[name][k]*.85)) for k,v in enumerate(row) if isinstance(v,str)),default=1)
                out=ET.SubElement(data,'{'+NS+'}row',r=str(ri),ht=str(max(32,min(400,lines*14+10))),customHeight='1')
                cells=list(prototypes[0 if ri==1 else 1])
                for ci,value in enumerate(row,1):
                    c=ET.SubElement(out,'{'+NS+'}c',r=column(ci)+str(ri),s=cells[ci-1].get('s','0'))
                    if ri>1 and isinstance(value,str) and len(value)==10 and value[4:5]=='-' and value[7:8]=='-':
                        try:value=date.fromisoformat(value)
                        except ValueError:pass
                    if isinstance(value,date):c.set('s',meta['styles']['date'])
                    if isinstance(value,dict):
                        style='fraction' if row[3]=='fraction (displayed as %)' else 'multiple' if row[3]=='ratio' else 'link_usd' if "'Liquidity inputs'!" in value['formula'] else 'formula_usd';c.set('s',meta['styles'][style])
                    elif name=='Liquidity inputs' and ci==4 and ri>1 and value is not None:c.set('s',meta['styles']['input_usd'])
                    write_cell(c,value)
                    if isinstance(value,str) and value.startswith('https://'):links.append((c.get('r'),value))
            dimension=sheet.find('{'+NS+'}dimension')
            if dimension is not None:dimension.set('ref',f'A1:{column(len(rows[0]))}{len(rows)}')
            relpath=part.replace('worksheets/','worksheets/_rels/')+'.rels'
            if links:replacements[relpath]=attach_links(sheet,links,src.read(relpath) if relpath in src.namelist() else None)
            replacements[part]=ET.tostring(sheet,encoding='utf-8',xml_declaration=True)
        output=BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as dst:
            for name in src.namelist():dst.writestr(name,replacements.pop(name,src.read(name)))
            for name,data in replacements.items():dst.writestr(name,data)
    return output.getvalue()
