// Shared programmatic export layout; runtime fills this verified template, not an openpyxl workbook.
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import crypto from 'node:crypto';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
import {frame,header} from './workbook_style.mjs';
const root=process.argv[2],py=process.env.CODEX_PRIMARY_RUNTIME_PYTHON;
const m=JSON.parse(execFileSync(py,['-c','import json,summary_export as s;print(json.dumps({"headers":s.HEADERS,"widths":s.WIDTHS}))'],{cwd:root,encoding:'utf8'}));
const w=Workbook.create();let i=0;const meta={sheets:{},styles:{}};
for(const [name,headers] of Object.entries(m.headers)){
 const s=w.worksheets.add(name),n=headers.length;s.getRangeByIndexes(0,0,2,n).values=[headers,Array(n).fill('Prototype')];s.showGridLines=false;
 const f=s.getRangeByIndexes(0,0,2,n).format;f.font.name='Arial';f.font.size=10;f.wrapText=true;f.verticalAlignment='top';f.rowHeight=75;
 m.widths[name].forEach((v,k)=>s.getRangeByIndexes(0,k,2,1).format.columnWidth=v);frame(s,s.getRangeByIndexes(0,0,2,n).address.split('!').pop());header(s,s.getRangeByIndexes(0,0,1,n).address.split('!').pop());s.freezePanes.freezeRows(1);
 meta.sheets[name]={path:`xl/worksheets/sheet${++i}.xml`};
}
const s=w.worksheets.getItem('Debt and liquidity'),styles={input_usd:['#,##0,,;(#,##0,,);"-"','#0000FF'],link_usd:['#,##0,,;(#,##0,,);"-"','#008000'],formula_usd:['#,##0,,;(#,##0,,);"-"','#000000'],fraction:['0.0%;(0.0%);"-"','#000000'],multiple:['0.00"x"','#000000'],date:['yyyy-mm-dd','#000000']};
const refs={};let rr=10;for(const [key,[fmt,color]] of Object.entries(styles)){const ref='C'+rr++;s.getRange(ref).values=[[1]];s.getRange(ref).setNumberFormat(fmt);s.getRange(ref).format.font.name='Arial';s.getRange(ref).format.font.size=10;s.getRange(ref).format.font.color=color;s.getRange(ref).format.borders={left:{style:'thin',color:'#DDE2E7'},right:{style:'thin',color:'#DDE2E7'}};refs[key]=ref;}
const dest=root+'/samples/summary_template.xlsx';await(await SpreadsheetFile.exportXlsx(w)).save(dest);
const map=JSON.parse(execFileSync(py,['-c',"import json,zipfile,xml.etree.ElementTree as E;z=zipfile.ZipFile('samples/summary_template.xlsx');ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};print(json.dumps({c.get('r'):c.get('s','0') for c in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:c',ns)}))"],{cwd:root,encoding:'utf8'}));
for(const [key,ref] of Object.entries(refs))meta.styles[key]=map[ref];meta.sha256=crypto.createHash('sha256').update(await fs.readFile(dest)).digest('hex');await fs.writeFile(dest.replace('.xlsx','.manifest.json'),JSON.stringify(meta,null,2)+'\n');
console.log('Summary template authored.');
