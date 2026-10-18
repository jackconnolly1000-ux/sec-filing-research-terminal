"""Install Artifact Tool-authored annual views and targeted edits, preserving unrelated workbook parts.

Run integrate_annual_history.mjs first and pass its output directory. No financial values or styles
are authored here: this remaps styles/relationships and copies the tool's cells and native charts.
"""
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
ET.register_namespace('x', NS)
ET.register_namespace('r', REL)
ET.register_namespace('', CT)


def xml(z, name):
    return ET.fromstring(z.read(name))


def serialized(root):
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def sheets(z):
    rels = {r.get('Id'): posixpath.normpath('xl/' + r.get('Target').lstrip('/')) if not r.get('Target').startswith('/') else r.get('Target').lstrip('/')
            for r in xml(z, 'xl/_rels/workbook.xml.rels')}
    return {s.get('name'): rels[s.get('{'+REL+'}id')] for s in xml(z, 'xl/workbook.xml').find('{'+NS+'}sheets')}


def rel_path(part):
    return posixpath.dirname(part) + '/_rels/' + posixpath.basename(part) + '.rels'


def apply(ticker, stem, folder):
    path = ROOT / 'samples' / (stem + '_liquidity.xlsx')
    original = path.read_bytes()
    src = zipfile.ZipFile(BytesIO(original))
    authored = zipfile.ZipFile(folder / (ticker + '-annual.xlsx'))
    meta = json.loads((folder / (ticker + '-annual-edits.json')).read_text())
    old_sheets, new_sheets = sheets(src), sheets(authored)
    changes = {}
    old_styles, new_styles = xml(src, 'xl/styles.xml'), xml(authored, 'xl/styles.xml')
    offsets = {}
    # Style indices in the copied cells refer to the appended authored collections.
    for name in ('fonts', 'fills', 'borders', 'cellStyleXfs', 'cellXfs'):
        old = old_styles.find('{'+NS+'}'+name)
        new = new_styles.find('{'+NS+'}'+name)
        offsets[name] = len(old)
        old.extend(deepcopy(list(new)))
        old.set('count', str(len(old)))
    old_num = old_styles.find('{'+NS+'}numFmts')
    if old_num is None:
        old_num = ET.Element('{'+NS+'}numFmts', count='0'); old_styles.insert(0, old_num)
    next_fmt = max([163] + [int(n.get('numFmtId')) for n in old_num]) + 1
    formats = {}
    for n in new_styles.findall('{'+NS+'}numFmts/{'+NS+'}numFmt'):
        copy = deepcopy(n); formats[int(n.get('numFmtId'))] = next_fmt
        copy.set('numFmtId', str(next_fmt)); old_num.append(copy); next_fmt += 1
    old_num.set('count', str(len(old_num)))
    for name in ('cellStyleXfs', 'cellXfs'):
        for xf in list(old_styles.find('{'+NS+'}'+name))[offsets[name]:]:
            for attr, kind in [('fontId', 'fonts'), ('fillId', 'fills'), ('borderId', 'borders'), ('xfId', 'cellStyleXfs')]:
                if attr in xf.attrib: xf.set(attr, str(int(xf.get(attr)) + offsets[kind]))
            if int(xf.get('numFmtId', '0')) in formats:
                xf.set('numFmtId', str(formats[int(xf.get('numFmtId'))]))
    changes['xl/styles.xml'] = serialized(old_styles)
    strings = xml(authored, 'xl/sharedStrings.xml') if 'xl/sharedStrings.xml' in authored.namelist() else []

    def remap_cell(c):
        c = deepcopy(c)
        c.set('s', str(int(c.get('s', '0')) + offsets['cellXfs']))
        if c.get('t') == 's':
            item = strings[int(c.find('{'+NS+'}v').text)]
            c.remove(c.find('{'+NS+'}v')); c.set('t', 'inlineStr')
            inline = ET.SubElement(c, '{'+NS+'}is'); inline.extend(deepcopy(list(item)))
        return c

    for name, refs in meta['edits'].items():
        part = old_sheets[name]
        old, new = xml(src, part), xml(authored, new_sheets[name])
        target = old.find('{'+NS+'}sheetData')
        rows = {int(r.get('r')): r for r in target}
        new_rows = {int(r.get('r')): r for r in new.find('{'+NS+'}sheetData')}
        new_cells = {c.get('r'): c for c in new.findall('.//{'+NS+'}sheetData/{'+NS+'}row/{'+NS+'}c')}
        for ref in sorted(set(refs), key=lambda r: (int(re.search(r'\d+', r)[0]), len(re.match(r'[A-Z]+', r)[0]), r)):
            n = int(re.search(r'\d+', ref)[0])
            if n not in rows:
                rows[n] = ET.Element('{'+NS+'}row', dict(new_rows[n].attrib)); target.append(rows[n])
            elif n in new_rows:
                # Preserve authored fitted row heights without moving existing cells.
                for attr in ('ht', 'customHeight'):
                    if attr in new_rows[n].attrib: rows[n].set(attr, new_rows[n].get(attr))
            prev = next((c for c in rows[n] if c.get('r') == ref), None)
            if prev is not None: rows[n].remove(prev)
            if ref in new_cells: rows[n].append(remap_cell(new_cells[ref]))
            rows[n][:] = sorted(rows[n], key=lambda c: (len(re.match(r'[A-Z]+', c.get('r'))[0]), c.get('r')))
        target[:] = sorted(target, key=lambda r: int(r.get('r')))
        dimension = old.find('{'+NS+'}dimension')
        if name == 'Data' and dimension is not None:
            dimension.set('ref', f"A1:{'O' if ticker=='LLY' else 'R'}{meta['annualDataLast']}")
        # Extend native source hyperlinks without replacing existing relationship IDs.
        if name in {'Data', 'About'}:
            rp = rel_path(part)
            rels = xml(src, rp) if rp in src.namelist() else ET.Element('{'+PKG+'}Relationships')
            links = old.find('{'+NS+'}hyperlinks')
            linked = {n.get('ref') for n in links} if links is not None else set()
            ids = {n.get('Id') for n in rels}
            for cell in old.findall('.//{'+NS+'}sheetData/{'+NS+'}row/{'+NS+'}c'):
                v = cell.find('{'+NS+'}v')
                text = v.text if v is not None and cell.get('t') == 'str' else ''.join(t.text or '' for t in cell.findall('.//{'+NS+'}t'))
                if not text.startswith('https://') or cell.get('r') in linked:continue
                if links is None:
                    links = ET.Element('{'+NS+'}hyperlinks')
                    margin = old.find('{'+NS+'}pageMargins')
                    old.insert(list(old).index(margin) if margin is not None else len(old), links)
                k = len(ids)+1
                while 'rIdAnnualSource'+str(k) in ids:k += 1
                rid = 'rIdAnnualSource'+str(k);ids.add(rid)
                ET.SubElement(rels, '{'+PKG+'}Relationship', Id=rid, Type=REL+'/hyperlink', Target=text, TargetMode='External')
                ET.SubElement(links, '{'+NS+'}hyperlink', {'ref':cell.get('r'), '{'+REL+'}id':rid})
            changes[rp] = serialized(rels)
        changes[part] = serialized(old)

    types = xml(src, '[Content_Types].xml')
    authored_types = {e.get('PartName').lstrip('/'): e.get('ContentType') for e in xml(authored, '[Content_Types].xml') if e.get('PartName')}
    copied = {}

    def copy_part(old_part, target_part=None):
        if old_part in copied: return copied[old_part]
        target_part = target_part or posixpath.join(posixpath.dirname(old_part), 'annual-' + posixpath.basename(old_part))
        copied[old_part] = target_part
        content = authored.read(old_part)
        if old_part in authored_types:
            if not any(e.get('PartName') == '/'+target_part for e in types):
                ET.SubElement(types, '{'+CT+'}Override', PartName='/'+target_part, ContentType=authored_types[old_part])
        if old_part.startswith('xl/worksheets/'):
            root = ET.fromstring(content)
            for c in root.findall('.//{'+NS+'}sheetData/{'+NS+'}row/{'+NS+'}c'):
                replacement = remap_cell(c);c.attrib.clear();c.attrib.update(replacement.attrib);c[:]=list(replacement)
            for col in root.findall('{'+NS+'}cols/{'+NS+'}col'):
                if col.get('style'):col.set('style', str(int(col.get('style')) + offsets['cellXfs']))
            content = serialized(root)
        rp = rel_path(old_part)
        if rp in authored.namelist():
            rels = xml(authored, rp)
            for rel in rels:
                if rel.get('TargetMode') == 'External':continue
                dependency = posixpath.normpath(posixpath.join(posixpath.dirname(old_part), rel.get('Target')))
                if rel.get('Target').startswith('/'): dependency = rel.get('Target').lstrip('/')
                mapped = copy_part(dependency)
                rel.set('Target', posixpath.relpath(mapped, posixpath.dirname(target_part)))
            changes[rel_path(target_part)] = serialized(rels)
        changes[target_part] = content
        return target_part

    annual_part = old_sheets.get('Annual history')
    if annual_part is None:
        number = max(int(re.search(r'sheet(\d+)', p)[1]) for p in old_sheets.values()) + 1
        annual_part = f'xl/worksheets/sheet{number}.xml'
        book, rels = xml(src, 'xl/workbook.xml'), xml(src, 'xl/_rels/workbook.xml.rels')
        elements = book.find('{'+NS+'}sheets'); rid = 'rIdAnnualHistory'
        node = ET.Element('{'+NS+'}sheet', {'name': 'Annual history', 'sheetId': str(max(int(s.get('sheetId')) for s in elements)+1), '{'+REL+'}id': rid})
        elements.insert(next(i for i, s in enumerate(elements) if s.get('name')=='Core charts'), node)
        ET.SubElement(rels, '{'+PKG+'}Relationship', Id=rid, Type=REL+'/worksheet', Target=annual_part[3:])
        changes['xl/workbook.xml'], changes['xl/_rels/workbook.xml.rels'] = serialized(book), serialized(rels)
    copy_part(new_sheets['Annual history'], annual_part)
    if meta.get('replaceCoreBalanceChart'):
        def chart_part(z, part):
            relations = xml(z, rel_path(part))
            drawing = next(r.get('Target') for r in relations if r.get('Type') == REL+'/drawing')
            drawing = posixpath.normpath(posixpath.join(posixpath.dirname(part), drawing)).lstrip('/')
            charts = [posixpath.normpath(posixpath.join(posixpath.dirname(drawing), r.get('Target'))).lstrip('/') for r in xml(z, rel_path(drawing)) if r.get('Type') == REL+'/chart']
            return charts[1]
        changes[chart_part(src, old_sheets['Core charts'])] = authored.read(chart_part(authored, new_sheets['Core charts']))
    changes['[Content_Types].xml'] = serialized(types)
    out = BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dest:
        for info in src.infolist():dest.writestr(deepcopy(info), changes.get(info.filename, src.read(info.filename)))
        for name in changes.keys()-set(src.namelist()):dest.writestr(name, changes[name])
    content = out.getvalue()
    # Every unlisted part must survive byte-for-byte; charts and their layouts are preserved.
    result = zipfile.ZipFile(BytesIO(content))
    assert all(result.read(p) == src.read(p) for p in src.namelist() if p not in changes)
    path.write_bytes(content)
    import annual_history_view, company_history, core_charts, export_guide
    manifest_path = path.with_suffix('.manifest.json'); manifest = json.loads(manifest_path.read_text())
    manifest.update(annual_history_sha256=annual_history_view.fingerprint(), history_sha256=company_history.fingerprint(),
                    charts_sha256=core_charts.fingerprint(), guide_sha256=export_guide.fingerprint(),
                    annual_data_start=meta['annualDataStart'], annual_data_last=meta['annualDataLast'],
                    workbook_sha256=hashlib.sha256(content).hexdigest())
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    print(ticker, 'installed annual history;', len(changes), 'parts changed; unrelated parts preserved')


def normalize_for_import(source, output):
    # The .NET OPC reader rejects prefixed Types roots; only normalize package metadata.
    z = zipfile.ZipFile(source)
    with zipfile.ZipFile(output, 'w') as dest:
        for info in z.infolist():
            content = z.read(info.filename)
            if info.filename == '[Content_Types].xml':
                content = serialized(xml(z, info.filename))
            elif re.fullmatch(r'xl/worksheets/sheet\d+\.xml', info.filename):
                sheet = xml(z, info.filename)
                # This disposable import is a cached presentation reference. Final installation
                # copies original formulas byte-for-byte except explicitly authored edits.
                for cell in sheet.findall('.//{'+NS+'}c'):
                    formula = cell.find('{'+NS+'}f')
                    if formula is not None:cell.remove(formula)
                content = serialized(sheet)
            dest.writestr(info, content)


if __name__ == '__main__':
    if sys.argv[1] == '--normalize':
        normalize_for_import(Path(sys.argv[2]), Path(sys.argv[3])); sys.exit(0)
    for ticker, stem in [('LLY', 'lly'), ('ORCL', 'oracle'), ('VST', 'vistra')]:apply(ticker, stem, Path(sys.argv[1]))
