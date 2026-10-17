// Run a copy in an OS temporary directory with the bundled Artifact Tool runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {Workbook, SpreadsheetFile, FileBlob} from '@oai/artifact-tool';
import {frame, header} from './workbook_style.mjs';

const root=process.argv[2], out=process.argv[3];
await fs.mkdir(out,{recursive:true});
const py=process.env.CODEX_PRIMARY_RUNTIME_PYTHON;
const payload=JSON.parse(execFileSync(py,['-c',
  "import json,research_export as r;from pathlib import Path;print(json.dumps(r.tables([json.loads(Path('samples/'+t+'.json').read_text()) for t in ['AAPL','STRL']], '2026-10-17T18:00:00-04:00')))"],
  {cwd:root,encoding:'utf8'}));
const widths={
  'Research record':[30,110], 'About':[30,110],
  'Market data':[12,27,24,31,34,75,28,90],
  'Findings':[12,26,44,80,70,80,24,65,60,28,38,16,19,19,90,25,55,45,85,85],
  '8-K events':[12,19,19,22,28,48,85,95,27,90],
  'Evidence':[12,20,48,25,16,19,19,23,23,23,100,90],
  'Filing review':[12,23,21,25,16,19,19,22,32,34,90,95,19,30,95,90,90],
  'Data':[12,28,75,27,29,19,19,16,19,32,95,95],
};
const w=Workbook.create();
for(const [name,rows] of Object.entries(payload)){
  const s=w.worksheets.add(name), n=rows[0].length;
  s.getRangeByIndexes(0,0,3,n).values=[rows[0],Array(n).fill('prototype'),Array(n).fill('prototype')];
  const fmt=s.getRangeByIndexes(0,0,3,n).format;
  fmt.font.name='Arial';fmt.font.size=10;fmt.wrapText=true;fmt.verticalAlignment='top';
  s.showGridLines=false;
  widths[name].forEach((width,i)=>s.getRangeByIndexes(0,i,3,1).format.columnWidth=width);
  s.getRangeByIndexes(0,0,3,n).format.rowHeight=55;
  frame(s,s.getRangeByIndexes(0,0,3,n).address.split('!').pop());
  header(s,s.getRangeByIndexes(0,0,1,n).address.split('!').pop());
  if(!['Research record','About'].includes(name))s.freezePanes.freezeRows(1);
}
const s=w.worksheets.getItem('Market data');
const formats={usd:'#,##0,,;(#,##0,,);"-"',fraction:'0.0%;(0.0%);"-"',multiple:'0.0"x"',price:'"$"#,##0.00;("$"#,##0.00);"-"',integer:'#,##0',formula_usd:'#,##0,,;(#,##0,,);"-"',formula_fraction:'0.0%;(0.0%);"-"',date:'yyyy-mm-dd'};
const refs={};
let k=10;
for(const [key,fmt] of Object.entries(formats)){
  const ref='C'+k++;refs[key]=ref;
  s.getRange(ref).values=[[key==='date'?46000:1000000]];
  s.getRange(ref).setNumberFormat(fmt);
  s.getRange(ref).format.font.color=key.startsWith('formula')?'#008000':key==='date'?'#000000':'#0000FF';
  s.getRange(ref).format.font.name='Arial';s.getRange(ref).format.font.size=10;
  s.getRange(ref).format.verticalAlignment='top';s.getRange(ref).format.horizontalAlignment='right';
  s.getRange(ref).format.borders={left:{style:'thin',color:'#DDE2E7'},right:{style:'thin',color:'#DDE2E7'}};
}
w.recalculate();
const dest=path.join(root,'samples/research_template.xlsx');
await(await SpreadsheetFile.exportXlsx(w)).save(dest);
// Read exported style IDs rather than assuming any authoring runtime's ID allocation.
const meta=JSON.parse(execFileSync(py,['-c',
  "import json,zipfile,xml.etree.ElementTree as E;z=zipfile.ZipFile('samples/research_template.xlsx');ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};print(json.dumps({n:{c.get('r'):c.get('s','0') for c in E.fromstring(z.read(n)).findall('.//s:c',ns)} for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')}))"],
  {cwd:root,encoding:'utf8'}));
const manifest={sheets:{},styles:{},sha256:crypto.createHash('sha256').update(await fs.readFile(dest)).digest('hex')};
let idx=0;
for(const name of Object.keys(payload))manifest.sheets[name]={path:`xl/worksheets/sheet${++idx}.xml`,widths:widths[name]};
for(const [key,ref] of Object.entries(refs))manifest.styles[key]=meta[manifest.sheets['Market data'].path][ref];
await fs.writeFile(dest.replace('.xlsx','.manifest.json'),JSON.stringify(manifest,null,2)+'\n');
// Hydrate an actual archived record, then recalculate and render all changed sheets.
execFileSync(py,['-c',`import json,research_export as r;from pathlib import Path;Path(${JSON.stringify(path.join(out,'research-record.xlsx'))}).write_bytes(r.workbook([json.loads(Path('samples/'+t+'.json').read_text()) for t in ['AAPL','STRL']], '2026-10-17T18:00:00-04:00'))`],{cwd:root});
const actual=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(out,'research-record.xlsx')));
actual.recalculate();
console.log((await actual.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10}})).ndjson);
const input=actual.worksheets.getItem('Data').getRange('E2');
const result=actual.worksheets.getItem('Market data').getRange('C12');
const initialInput=input.values[0][0], initialResult=result.values[0][0];
input.values=[[initialInput+1e6]];actual.recalculate();
if(Math.abs(result.values[0][0]-initialResult-1e6)>1)throw new Error('Research formula did not recalculate');
input.values=[[initialInput]];actual.recalculate();
for(const name of Object.keys(payload)){
 const ws=actual.worksheets.getItem(name),cols=widths[name].length;
 const range=ws.getRangeByIndexes(0,0,Math.min(payload[name].length,12),cols).address.split('!').pop();
 const png=await actual.render({sheetName:name,range,scale:1});
 await fs.writeFile(path.join(out,name.replaceAll(' ','_')+'.png'),new Uint8Array(await png.arrayBuffer()));
}
for(const [name,range,suffix] of [['Findings','A1:F6','narrative'],['Findings','K1:T6','sources'],['Market data','A10:H16','sec']]){
 const png=await actual.render({sheetName:name,range,scale:1});
 await fs.writeFile(path.join(out,`${name.replaceAll(' ','_')}-${suffix}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('Authored research template and inspected eight sheets.');
