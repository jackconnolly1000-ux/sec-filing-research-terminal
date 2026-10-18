"""Small OpenXML primitives shared by the template hydrators; authored layouts stay offline."""
from datetime import date
import math
import xml.etree.ElementTree as ET
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'

def column(index):
    if not isinstance(index,int) or index<1:raise ValueError('Columns are one-based positive integers')
    name=''
    while index:index,rem=divmod(index-1,26);name=chr(65+rem)+name
    return name

def write_cell(cell,value):
    cell.attrib.pop('t',None)
    for child in list(cell):cell.remove(child)
    if value is None:return
    if isinstance(value,date):value=(value-date(1899,12,30)).days
    if isinstance(value,dict):
        ET.SubElement(cell,'{'+NS+'}f').text=value['formula'].removeprefix('=');value=value['value']
    if isinstance(value,(int,float)):
        if not math.isfinite(value):raise ValueError('Nonfinite workbook value')
        ET.SubElement(cell,'{'+NS+'}v').text=repr(value)
    else:
        cell.set('t','inlineStr');ET.SubElement(ET.SubElement(cell,'{'+NS+'}is'),'{'+NS+'}t').text=str(value)

def attach_links(sheet,links,existing=None):
    rels=ET.fromstring(existing) if existing else ET.Element('{'+PKG+'}Relationships')
    for c in list(rels):
        if c.get('Type')==REL+'/hyperlink':rels.remove(c)
    old=sheet.find('{'+NS+'}hyperlinks')
    if old is not None:sheet.remove(old)
    block=ET.Element('{'+NS+'}hyperlinks')
    ids={r.get('Id') for r in rels}
    for k,(ref,url) in enumerate(links):
        rid='rIdSource'+str(k)
        while rid in ids:rid+='x'
        ids.add(rid)
        ET.SubElement(block,'{'+NS+'}hyperlink',{'ref':ref,'{'+REL+'}id':rid})
        ET.SubElement(rels,'{'+PKG+'}Relationship',Id=rid,Type=REL+'/hyperlink',Target=url,TargetMode='External')
    position=next((i for i,c in enumerate(sheet) if c.tag=='{'+NS+'}pageMargins'),len(sheet));sheet.insert(position,block)
    return ET.tostring(rels,encoding='utf-8',xml_declaration=True)

def chart_cache(cache,values):
    ns='http://schemas.openxmlformats.org/drawingml/2006/chart'
    for child in list(cache):
        if child.tag in ('{'+ns+'}ptCount','{'+ns+'}pt'):cache.remove(child)
    ET.SubElement(cache,'{'+ns+'}ptCount',val=str(len(values)))
    for k,value in enumerate(values):
        if value is None:continue
        point=ET.SubElement(cache,'{'+ns+'}pt',idx=str(k));ET.SubElement(point,'{'+ns+'}v').text=str(value)
