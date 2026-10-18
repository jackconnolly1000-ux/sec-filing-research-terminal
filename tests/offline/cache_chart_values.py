"""Fill native chart caches from already-calculated workbook cells; never invent missing points."""
from io import BytesIO
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET
from openpyxl import load_workbook
C='http://schemas.openxmlformats.org/drawingml/2006/chart'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
ET.register_namespace('c',C);ET.register_namespace('a',A)
def patch(path):
    raw=Path(path).read_bytes();w=load_workbook(BytesIO(raw),data_only=True)
    changes={}
    with zipfile.ZipFile(BytesIO(raw)) as z:
        for name in z.namelist():
            if not re.search(r'/charts/chart\d+\.xml$',name):continue
            root=ET.fromstring(z.read(name))
            for kind in ('numRef','strRef'):
                for ref in root.iter('{'+C+'}'+kind):
                    f=ref.findtext('{'+C+'}f')
                    m=re.fullmatch(r"(?:'(.+)'|([^!]+))!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?",f or '')
                    if not m:continue
                    sheet=m[1] or m[2];end=(m[5] or m[3])+(m[6] or m[4]);start=m[3]+m[4]
                    if sheet not in w:raise ValueError(f'Chart references missing sheet: {f}')
                    cells=[c.value for row in w[sheet][start+':'+end] for c in row]
                    cachetag='{'+C+'}'+('numCache' if kind=='numRef' else 'strCache')
                    old=ref.find(cachetag)
                    if old is not None:ref.remove(old)
                    cache=ET.SubElement(ref,cachetag)
                    if kind=='numRef':ET.SubElement(cache,'{'+C+'}formatCode').text='General'
                    ET.SubElement(cache,'{'+C+'}ptCount',val=str(len(cells)))
                    for i,v in enumerate(cells):
                        if v is None or isinstance(v,str) and v.startswith('#'):continue
                        if kind=='numRef' and not isinstance(v,(int,float)):continue
                        pt=ET.SubElement(cache,'{'+C+'}pt',idx=str(i));ET.SubElement(pt,'{'+C+'}v').text=str(v)
            chart=root.find('{'+C+'}chart')
            if chart is not None and chart.find('{'+C+'}dispBlanksAs') is None:ET.SubElement(chart,'{'+C+'}dispBlanksAs',val='gap')
            changes[name]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        out=BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dst:
            for info in z.infolist():dst.writestr(info,changes.get(info.filename,z.read(info.filename)))
    w.close();Path(path).write_bytes(out.getvalue())
