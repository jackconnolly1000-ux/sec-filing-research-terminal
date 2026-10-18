"""Convert the checked calendar to an authoring specification; no workbook edits here."""
import json
import xml.etree.ElementTree as ET
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import oracle_principal as op
from oracle_principal_view import ladder_years
from add_oracle_principal_block import block, DATE, BLUE

def build():
    review=op.load()
    if not review:
        raise ValueError('Checked Oracle principal calendar required')
    rows,last=block(review)
    root=ET.fromstring('<rows xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+rows+'</rows>')
    ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    cells=[]
    for cell in root.findall('.//x:c',ns):
        ref=cell.get('r'); v=cell.findtext('x:v',namespaces=ns); f=cell.findtext('x:f',namespaces=ns)
        if f:
            f=f.replace('*0.0125','*$F$77').replace('*0.025','*$F$78').replace('50000000','$F$80').replace('5137000000','C151')
        cells.append(dict(ref=ref,value=v if cell.get('t') in ('str','d') else float(v),formula=f,
                          date=cell.get('s')==str(DATE),reported=cell.get('s')==str(BLUE)))
    return dict(cells=cells,last=last,heights={int(row.get('r')):float(row.get('ht')) for row in root},
                years=ladder_years(review),decades=op.by_decade(review),fingerprint=op.fingerprint(),annual=review['annual'])
if __name__=='__main__':print(json.dumps(build()))
