// Copy to an OS temporary directory with workbook_style.mjs and the runtime node_modules symlink.
// Author affected cells/new annual sheet; apply_annual_history.py preserves every unrelated ZIP part.
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
import {frame,header,dimensionText} from './workbook_style.mjs';
const root=process.argv[2],out=process.argv[3]||process.cwd(),charts=process.argv.includes('--charts');
const run=(code,ticker)=>JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,['-c',code,ticker],{cwd:root,encoding:'utf8'}));
const USD='#,##0.0,,;(#,##0.0,,);"-"',date=s=>s?new Date(s+'T00:00:00Z'):null;
await fs.mkdir(out,{recursive:true});
for(const [ticker,stem] of [['LLY','lly'],['ORCL','oracle'],['VST','vistra']]){
 const model=run('import json,sys,annual_history_view as a;print(json.dumps(a.build(sys.argv[1])))',ticker);
 const history=run('import json,sys,company_history as h;from pathlib import Path;s=next(x for x in json.loads(Path("samples/liquidity_pilots.json").read_text())["snapshots"] if x["ticker"]==sys.argv[1]);print(json.dumps(h.build(s)))',ticker);
 const guides=run('import json,sys,export_guide as g;print(json.dumps(g.contents(sys.argv[1])))',ticker);
 execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,[`${root}/tests/offline/apply_annual_history.py`,'--normalize',`${root}/samples/${stem}_liquidity.xlsx`,`${out}/${ticker}-import.xlsx`]);
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(`${out}/${ticker}-import.xlsx`));
 const cached=JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,[`${root}/tests/offline/export_layout_records.py`,`${root}/samples/${stem}_liquidity.xlsx`],{encoding:'utf8'}));
 // The import engine mis-types some unrelated DATE-containing formulas. Use their saved values
 // in this disposable authoring copy only; the installer retains all original formulas/parts.
 for(const [name,records] of Object.entries(cached)){const s=wb.worksheets.getItem(name);const cells=new Map(records.cells.map(r=>[r[0],r]));s.getUsedRange().values.forEach((row,i)=>row.forEach((v,j)=>{if(v instanceof Date&&!Number.isFinite(v.getTime())){const c=s.getCell(i,j),r=cells.get(c.address.split('!').pop());c.values=[[r[1]]];c.setNumberFormat(r[3]);}}));}
 const oldManifest=JSON.parse(await fs.readFile(`${root}/samples/${stem}_liquidity.manifest.json`,'utf8'));
 const edits={},meta={edits,charts,annualDataStart:oldManifest.annual_data_start};
 const edit=(s,ref,value,formula=false)=>{const c=s.getRange(ref);c[formula?'formulas':'values']=[[value]];(edits[s.name]??=[]).push(ref);return c;};
 // Establish the existing visual baseline before touching its cells.
 for(const [name,range] of [['History','A5:D19'],['Data','A1:H8']]){
  const b=await wb.render({sheetName:name,range,scale:1});await fs.writeFile(`${out}/${ticker}-before-${name}.png`,new Uint8Array(await b.arrayBuffer()));
 }
 const data=wb.worksheets.getItem('Data'),cols=ticker==='LLY'?15:18;
 const start=meta.annualDataStart??data.getUsedRange().values.length+3;meta.annualDataStart=start;
 const records=[],refs=new Map();
 const factKey=f=>[f.tag,f.period_start,f.period_end,f.accession,f.context_id].join('|');
 function factRef(f,label){
  const key=factKey(f);if(refs.has(key))return refs.get(key);
  const n=start+records.length+1,location=typeof f.location==='object'?'Printed p. '+f.location.printed_page+'; '+f.location.row_text:f.location;
  const row=ticker==='LLY'?[label,f.value,date(f.period_start),date(f.period_end),f.form,date(f.filed),f.accession,f.tag,f.context_id,f.scale??null,f.decimals??null,f.source_url,location,'Exact prefixed tag; exact period; USD; no dimensions; checked source version.',f.source_sha256]:
   [label,f.value,label,date(f.period_start),date(f.period_end),f.form,date(f.filed),f.accession,f.tag,f.context_id,...(ticker==='VST'?[dimensionText(f.dimensions),f.scale??null,f.decimals??null,f.source_url,location,f.selection_rule||'Exact prefixed tag; exact period; USD; no dimensions; checked source version.',f.source_sha256,f.unit]:[f.scale??null,f.decimals??null,f.source_url,location,f.selection_rule||'Exact prefixed tag; exact period; USD; no dimensions; checked source version.',dimensionText(f.dimensions),f.source_sha256,f.unit])];
  records.push(row);const ref=`'Data'!B${n}`;refs.set(key,ref);return ref;
 }
 const existingNames=(await wb.inspect({kind:'sheet',include:'name',maxChars:3000})).ndjson;
 const sheet=existingNames.includes('Annual history')?wb.worksheets.getItem('Annual history'):wb.worksheets.add('Annual history');
 sheet.showGridLines=false;
 sheet.getRange('A1:F22').format.font.name='Arial';sheet.getRange('A1:F22').format.font.size=10;
 sheet.getRange('A1:F22').format.verticalAlignment='top';sheet.getRange('A1:F22').format.wrapText=true;
 sheet.getRange('A1:A22').format.columnWidth=34;sheet.getRange('B1:F22').format.columnWidth=20;
 sheet.getRange('A2').values=[[ticker+' — five completed fiscal years']];sheet.getRange('A2').format.font.size=14;sheet.getRange('A2').format.font.bold=true;sheet.getRange('A2').format.wrapText=false;
 sheet.getRange('A3').values=[['USD millions. Full fiscal years; latest TTM remains separate.']];sheet.getRange('A3').format.wrapText=false;
 sheet.getRange('A4:F4').values=[['Fiscal year end',...model.rows.map(r=>date(r.source.period_end))]];sheet.getRange('B4:F4').setNumberFormat('yyyy-mm-dd');
 sheet.getRange('A5:F5').values=[['Measure',...model.rows.map(r=>'FY'+r.fiscal_year)]];header(sheet,'A5:F5');
 model.labels.forEach((label,i)=>sheet.getRange('A'+(6+i)).values=[[label]]);
 for(const [j,row] of model.rows.entries()){
  const col='BCDEF'[j];
  for(const [i,key] of model.keys.entries()){
   const metric=row.metrics[key],n=i+6;
   if(metric.value===null){sheet.getRange(`${col}${n}`).values=[['Unavailable']];continue;}
   let formula;
   if(key==='free_cash_flow')formula=`=${col}8-${col}9`;
   else {const inputRefs=metric.inputs.map(f=>factRef(f,`${ticker} FY${row.fiscal_year} ${key}: ${f.tag}`));formula='='+inputRefs.map(ref=>`IF(ISNUMBER(${ref}),${ref},NA())`).join('+');}
   sheet.getRange(`${col}${n}`).formulas=[[formula]];
   sheet.getRange(`${col}${n}`).format.font.color=key==='free_cash_flow'?'#000000':'#008000';
  }
 }
 sheet.getRange('B6:F10').setNumberFormat(USD);sheet.getRange('A4:F10').format.rowHeight=25;frame(sheet,'A5:F10');sheet.getRange('A10:F10').format.borders={top:{style:'thin',color:'#BBC3CD'}};
 const noteRows=[['Annual basis',model.notes[0]],...model.notes.slice(1).map(n=>['Presentation choice',n])];
 let nr=12;for(const [label,note] of noteRows){sheet.getRange('A'+nr).values=[[label]];let line='';for(const word of note.split(' ')){if((line+' '+word).length>108){sheet.getRange('B'+nr).values=[[line]];sheet.getRange('B'+nr).format.wrapText=false;nr++;line='';}line+=(line?' ':'')+word;}sheet.getRange('B'+nr).values=[[line]];sheet.getRange('B'+nr).format.wrapText=false;nr+=2;}sheet.getRange('A12:F23').format.rowHeight=21;
 sheet.freezePanes.freezeRows(5);sheet.freezePanes.freezeColumns(1);
 const last=start+records.length,letter=ticker==='LLY'?'O':'R';
 const headers=ticker==='LLY'?['Input','USD millions','Period start','Period end','Form','Filed','Accession','Tag','Context','Scale','Decimals','Source','Filing location','Selection rule','Reviewed source SHA256']:(ticker==='VST'?['Input','USD millions','Measure','Period start','Period end','Form','Filed','Accession','Tag','Context','Dimensions','Scale','Decimals','Source','Filing location','Selection rule','Reviewed source SHA256','Unit']:['Input','USD millions','Measure','Period start','Period end','Form','Filed','Accession','Tag','Context','Scale','Decimals','Source','Filing location','Selection rule','Dimensions','Reviewed source SHA256','Unit']);
 data.getRange(`A${start}:${letter}${start}`).values=[headers];
 data.getRange(`A${start+1}:${letter}${last}`).values=records;
 for(let n=start;n<=last;n++)for(let c=0;c<cols;c++)(edits.Data??=[]).push(String.fromCharCode(65+c)+n);
 const df=data.getRange(`A${start}:${letter}${last}`).format;df.font.name='Arial';df.font.size=10;df.wrapText=true;df.verticalAlignment='top';df.rowHeight=72;
 data.getRange(`B${start+1}:B${last}`).setNumberFormat(USD);data.getRange(`B${start+1}:B${last}`).format.font.color='#0000FF';
 for(const c of ticker==='LLY'?['C','D','F']:['D','E','G'])data.getRange(`${c}${start+1}:${c}${last}`).setNumberFormat('yyyy-mm-dd');
 frame(data,`A${start}:${letter}${last}`);header(data,`A${start}:${letter}${start}`);meta.annualDataLast=last;
 // Correct the identified legacy Lilly locator wherever it appears in this workbook.
 for(const name of ['Data','About','History']){
  const s=wb.worksheets.getItem(name),values=s.getUsedRange().values;
  values.forEach((row,i)=>row.forEach((v,j)=>{if(typeof v==='string'&&v.includes('p. 56; cash flows p. 58'))edit(s,s.getCell(i,j).address.split('!').pop(),v.replace('p. 56; cash flows p. 58','p. 59; cash flows p. 61'));}));
 }
 if(ticker==='VST'){
  const hs=wb.worksheets.getItem('History'),debt=model.rows.at(-1).metrics.gross_debt;
  const debtRefs=debt.inputs.map(f=>refs.get(factKey(f)));
  edit(hs,'B7','='+debtRefs.join('+'),true).format.font.color='#008000';
  for(const [ref,formula] of [['B8','=B7-B6'],['B13','=B10/B7'],['B14','=B12/B7']])edit(hs,ref,formula,true).format.font.color='#000000';
  for(const n of [7,8,13,14])edit(hs,'D'+n,history.rows[n-6].history_basis);
  const cs=wb.worksheets.getItem('Core charts');
  edit(cs,'C24','Baseline borrowing');edit(cs,'C25',"='History'!B7",true);edit(cs,'C26',"='History'!C7",true);
  cs.getRange('C25:C26').setNumberFormat('#,##0,,;(#,##0,,);"-"');cs.getRange('C25:C26').format.font.color='#008000';frame(cs,'A24:C26');header(cs,'A24:C24');
  edit(cs,'D29','Baseline borrowing excludes leases; cash excludes restricted cash. FY2025 borrowing is now checked, including the face financing line once; its facility split remains unresolved.');
  cs.charts.items[1].setData(cs.getRange('A24:C26'));cs.charts.items[1].title='How did borrowing and cash change?';cs.charts.items[1].series.items[1].fill='#47627F';
  meta.replaceCoreBalanceChart=true;
 }
 // Existing notes about the once-missing Vistra balance must follow its resolved source audit.
 const about=wb.worksheets.getItem('About');
 for(const name of ['About','Funding conclusion']){
  const s=wb.worksheets.getItem(name),values=s.getUsedRange().values;
  values.forEach((row,i)=>row.forEach((v,j)=>{if(typeof v==='string'&&/([Uu]nsupported older Vistra|Vistra has no supported older borrowing)/.test(v))edit(s,s.getCell(i,j).address.split('!').pop(),v.replace(/Unsupported older Vistra borrowing and dependent ratios remain Unavailable\./g,'Vistra FY2025 borrowing and dependent ratios use the checked annual financing line once.').replace(/Unsupported older Vistra borrowing is omitted, never plotted as zero\./g,'Unavailable observations are omitted, never plotted as zero.').replace(/Vistra has no supported older borrowing series\./g,'Vistra FY2025 borrowing now uses its checked annual presentation.'));}));
 }
 let aboutRow=about.getUsedRange().values.findIndex(r=>r[0]==='Annual history')+1;if(!aboutRow)aboutRow=about.getUsedRange().values.length+1;
 ['Annual history',model.notes.join(' '),'https://github.com/jackconnolly1000-ux/sec-filing-research-terminal/blob/main/docs/annual_history_reconciliation.md'].forEach((v,j)=>edit(about,'ABC'[j]+aboutRow,v));
 const af=about.getRange(`A${aboutRow}:C${aboutRow}`).format;af.font.name='Arial';af.font.size=10;af.wrapText=true;af.rowHeight=Math.max(75,Math.ceil(model.notes.join(' ').length/100)*14+14);af.verticalAlignment='top';frame(about,`A${aboutRow}:C${aboutRow}`);
 const cover=wb.worksheets.getItem('Funding conclusion'),lastGuide=20+guides.length;
 const grid=[['Workbook contents — select the named tab','Question / evidence'],...guides];
 grid.forEach((r,i)=>r.forEach((v,j)=>edit(cover,'AB'[j]+(20+i),v)));
 cover.getRange(`A20:B${lastGuide}`).format.rowHeight=44;cover.getRange(`A20:B${lastGuide}`).format.wrapText=true;cover.getRange(`A20:B${lastGuide}`).format.verticalAlignment='top';cover.getRange(`A20:B${lastGuide}`).format.font.name='Arial';cover.getRange(`A20:B${lastGuide}`).format.font.size=10;cover.getRange(`A21:A${lastGuide}`).format.font.bold=true;edit(cover,'A'+(lastGuide+1),null);edit(cover,'B'+(lastGuide+1),null);cover.getRange(`A${lastGuide+1}:B${lastGuide+1}`).format.rowHeight=12;frame(cover,`A20:B${lastGuide}`);header(cover,'A20:B20');
 const reading=[['Units and dates','Whole USD, displayed in millions except x and %. Annual history uses five full fiscal years. The separate FY-versus-TTM comparison overlaps.'],['Colors','Blue numeric cells are reported inputs; green formulas link to another sheet; black formulas calculate within a sheet.'],['Evidence and uncertainty','Data retains source URLs, periods, accessions, tags and contexts. Select a source URL to open it in a browser. Unavailable is never zero.'],['Reading the charts','FCF is OCF less capex, not another cash flow. Annual charts and the latest TTM keep their own periods and bases.']];
 reading.forEach((r,i)=>r.forEach((v,j)=>edit(cover,'AB'[j]+(lastGuide+2+i),v)));cover.getRange(`A${lastGuide+2}:B${lastGuide+5}`).format.rowHeight=55;cover.getRange(`A${lastGuide+2}:B${lastGuide+5}`).format.verticalAlignment='top';frame(cover,`A${lastGuide+2}:B${lastGuide+5}`);
 if(charts){
  // Native charts bind to the finished annual calculations, so input changes update both.
  sheet.getRange('A62:C67').values=[['Fiscal year','Cash and equivalents','Baseline borrowing'],...model.rows.map(r=>['FY'+r.fiscal_year,null,null])];
  sheet.getRange('A70:D75').values=[['Fiscal year','Operating cash flow','Capital spending','Free cash flow'],...model.rows.map(r=>['FY'+r.fiscal_year,null,null,null])];
  for(let j=0;j<5;j++){const c='BCDEF'[j];sheet.getRange(`B${63+j}:C${63+j}`).formulas=[[`=${c}6`,`=${c}7`]];sheet.getRange(`B${71+j}:D${71+j}`).formulas=[[`=${c}8`,`=${c}9`,`=${c}10`]];}
  sheet.getRange('A62:D75').format.font.name='Arial';sheet.getRange('A62:D75').format.font.size=10;sheet.getRange('B63:D75').setNumberFormat(USD);frame(sheet,'A62:C67');header(sheet,'A62:C62');frame(sheet,'A70:D75');header(sheet,'A70:D70');
  sheet.getRange('A60').values=[['Chart data — formulas linked to the annual table above']];sheet.getRange('A60').format.wrapText=false;
  sheet.charts.deleteAll();
  for(const [range,title,first,last,colors] of [['A62:C67','Fiscal-year-end cash and borrowing (USD millions)','A24','G40',['#3987E5','#D95926']],['A70:D75','Annual OCF, capital spending and FCF (USD millions)','A42','G58',['#47627F','#A17A3C','#3987E5']]]){
   const ch=sheet.charts.add('line',sheet.getRange(range));ch.title=title;ch.titleTextStyle.typeface='Arial';ch.titleTextStyle.fontSize=12;
   ch.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};ch.yAxis={numberFormatCode:'#,##0.0,,;(#,##0.0,,)',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:10}};ch.yAxis.title.text='USD millions';ch.legend={position:'bottom',textStyle:{typeface:'Arial',fontSize:10}};
   ch.series.items.forEach((s,i)=>s.line={fill:colors[i],style:'solid',width:2});ch.setPosition(first,last);
  }
 }
 wb.recalculate();
 for(const [j,r] of model.rows.entries())for(const [i,key] of model.keys.entries()){
  const got=sheet.getRange('BCDEF'[j]+(i+6)).values[0][0];if(got!==r.metrics[key].value)throw Error(`${ticker} annual value mismatch ${key}`);
 }
 // Disposable edit, then restoration, proves the FCF calculation and chart-source dependency update.
 const firstRef=refs.get(factKey(model.rows[0].metrics.operating_cash_flow.inputs[0])).split('!')[1],original=data.getRange(firstRef).values[0][0];
 data.getRange(firstRef).values=[[original+1e6]];wb.recalculate();if(sheet.getRange('B10').values[0][0]!==model.rows[0].metrics.free_cash_flow.value+1e6)throw Error('FCF dependency did not recalculate');
 data.getRange(firstRef).values=[[original]];wb.recalculate();
 const errors=await wb.inspect({kind:'match',range:"'Annual history'!A1:G75",searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:1000});console.log(ticker,errors.ndjson);
 await(await SpreadsheetFile.exportXlsx(wb)).save(`${out}/${ticker}-annual.xlsx`);
 for(const [name,range,suffix] of [['Annual history','A2:F22','table'],['Data',`A${start}:H${last}`,'annual-inputs'],['Data',`${ticker==='LLY'?'I':'I'}${start}:${letter}${last}`,'annual-sources'],['About',`A${aboutRow}:C${aboutRow}`,'about'],['Funding conclusion',`A20:B${lastGuide+5}`,'contents'],...(ticker==='VST'?[['History','A5:D19','prior'],['Core charts','A23:O39','balances']]:[]),...(charts?[['Annual history','A24:G40','balances-chart'],['Annual history','A42:G58','flows-chart']]:[])]){
  const image=await wb.render({sheetName:name,range,scale:1});await fs.writeFile(`${out}/${ticker}-${suffix}.png`,new Uint8Array(await image.arrayBuffer()));
 }
 await fs.writeFile(`${out}/${ticker}-annual-edits.json`,JSON.stringify(meta,null,2)+'\n');console.log(ticker,'annual table reconciled; source block',start,last);
}
