// One checked presentation feeds the app and each individual workbook.
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {frame,header,subtotal,dimensionText} from './workbook_style.mjs';

export function addBorrowingLeaseSheet(wb,root,ticker){
 const model=JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,['-c',
  'import json,sys,borrowing_leases as b;from pathlib import Path;s=json.loads(Path("samples/liquidity_pilots.json").read_text())["snapshots"];print(json.dumps(b.build(next(x for x in s if x["ticker"]==sys.argv[1]))))',ticker],{cwd:root,encoding:'utf8'}));
 return {model,sheet:wb.worksheets.add('Borrowing and leases')};
}

export async function finishBorrowingLeaseSheet(wb,root,ticker,state){
 const {model,sheet}=state,data=wb.worksheets.getItem('Data');
 const date=s=>s?new Date(s+'T00:00:00Z'):null,USD='#,##0,,;(#,##0,,);"-"';
 const start=data.getUsedRange().values.length+3;
 const headers=data.getRange(ticker==='LLY'?'A1:O1':'A1:R1').values[0];
 if(ticker==='LLY'){headers[12]='Filing location';headers[13]='Selection / Unavailable reason';headers[14]='Reviewed source SHA256';}
 data.getRangeByIndexes(start-1,0,1,headers.length).values=[headers];
 const records=[];
 function input(f,label){
  const n=start+records.length+1;
  const base=ticker==='LLY'?
   [label,f.value,null,date(f.period_end),f.form,date(f.filed),f.accession,f.tag||null,f.context_id||null,f.scale??null,f.decimals??null,f.source_url,f.location,(f.selection_rule||'')+(f.detail?' '+f.detail:''),f.source_sha256||'']:
   [label,f.value,label,null,date(f.period_end),f.form,date(f.filed),f.accession,f.tag||null,f.context_id||null,
    ...(ticker==='VST'?[dimensionText(f.dimensions),f.scale??null,f.decimals??null]:[f.scale??null,f.decimals??null]),
    f.source_url,f.location,f.detail||'',...(ticker==='VST'?[]:[dimensionText(f.dimensions)]),f.source_sha256||'',f.value===null?'Unavailable; no numeric fact established':'USD; '+(f.selection_rule||'exact checked instant')];
  records.push(base);
  return `=IF(ISNUMBER('Data'!B${n}),'Data'!B${n},NA())`;
 }
 const rows=[];
 for(const f of model.borrowing)rows.push({label:f.label,formula:input(f,f.label),date:f.period_end,
  source:f.location+'; filed '+f.filed,note:f.value===0?'Reported zero, not a missing input.':f.filing_label});
 const totalRow=6+rows.length;
 rows.push({label:'Baseline gross debt',formula:`=SUM(B6:B${totalRow-1})`,date:model.period_end,
  source:'Derived from the components above',note:'Carrying amount; excludes leases.'});
 sheet.getRange('A2').values=[[model.company+' borrowing and leases']];
 sheet.getRange('A3').values=[['Amounts in USD millions. Each balance retains its own date. Baseline borrowing excludes leases.']];
 sheet.getRange('A5:E5').values=[['Borrowing component','USD millions','As of','Source / filing','Basis']];
 for(const [i,r] of rows.entries()){
  const n=i+6;sheet.getRange(`A${n}:E${n}`).values=[[r.label,null,date(r.date),r.source,r.note]];
  sheet.getRange(`B${n}`).formulas=[[r.formula]];
 }
 let n=totalRow+2;
 sheet.getRange(`A${n}`).values=[['Borrowing scope']];sheet.getRange(`E${n}`).values=[[model.borrowing_note]];
 // Keep lease dates and reasons on individual records, rather than carrying old balances into June.
 const leaseHeader=n+3;
 sheet.getRange(`A${leaseHeader}:E${leaseHeader}`).values=[['Lease liability / commitment','USD millions','As of','Source / filing','Basis / Unavailable reason']];
 n=leaseHeader;
 const leaseTotalRows=[];
 if(!model.latest_leases_available){
  n++;sheet.getRange(`A${n}:E${n}`).values=[['Lease liabilities at latest balance sheet','Unavailable',date(model.period_end),'Checked 10-Q review','No lease liability amounts established in this 10-Q. Older amounts below are not substituted.']];
  input({...model.borrowing[0],value:null,tag:null,context_id:null,detail:'Latest-date lease liabilities Unavailable; no checked amount in the 10-Q.'},'Latest-date lease liabilities — Unavailable');
 }
 for(const f of model.leases){
  if(f.value===null){
   n++;sheet.getRange(`A${n}:E${n}`).values=[[f.label,'Unavailable',date(f.period_end),f.location,f.detail]];
   input(f,f.label+' — requested date, Unavailable');continue;
  }
  const first=n+1;
  for(const [i,part] of f.inputs.entries()){
   n++;sheet.getRange(`A${n}:E${n}`).values=[[f.label+(i===0?' — current':' — noncurrent'),null,date(part.period_end),part.location+'; filed '+part.filed,'Recognized lease liability; excluded from baseline borrowing.']];
   sheet.getRange(`B${n}`).formulas=[[input(part,f.label+(i===0?' — current':' — noncurrent'))]];
  }
  n++;sheet.getRange(`A${n}:E${n}`).values=[[f.label+' — total',null,date(f.period_end),f.location,f.reported_total?'Components match the reported total.':'Derived current + noncurrent; no separately tagged total.']];
  sheet.getRange(`B${n}`).formulas=[[`=B${first}+B${first+1}`]];leaseTotalRows.push([n,f.value]);
  if(f.reported_total)input(f.reported_total,f.label+' — reported total control');
 }
 n+=2;
 const commitment=model.commitment;
 sheet.getRange(`A${n}:E${n}`).values=[['Leases not yet commenced',commitment.value===null?'Unavailable':null,date(commitment.period_end),commitment.location,commitment.detail]];
 if(commitment.value!==null)sheet.getRange(`B${n}`).formulas=[[input(commitment,'Leases not yet commenced')]];
 else input(commitment,'Leases not yet commenced — Unavailable');
 const last=n;
 // One source-backed breakdown below the established lease rows; no existing row shifts.
 const detail=model.funding_detail;
 sheet.getRange('A27').values=[['Short-term funding structure — included in baseline borrowing']];
 sheet.getRange('A28:E28').values=[['Item','USD millions','As of','Status','Basis / source']];
 const source=f=>({...model.borrowing[0],...f,source_url:f.source_url||model.borrowing[0].source_url,
   location:typeof f.location==='object'?'Printed p. '+f.location.printed_page:f.location||model.borrowing[0].location,source_sha256:f.source_sha256||''});
 for(const [i,r] of detail.rows.entries()){
  const rr=29+i;
  sheet.getRange(`A${rr}:E${rr}`).values=[[r.label,r.value===null?'Unavailable':null,date(r.period_end),r.status,r.basis]];
  if(r.value!==null){
   let formula;
   if(r.source)formula=input(source(r.source),r.label);
   else formula=ticker==='LLY'?'=B6-B29':'=SUM(B29:B31)';
   sheet.getRange(`B${rr}`).formulas=[[formula]];
  }
 }
 sheet.getRange('A34').values=[['Funding structure']];sheet.getRange('E34').values=[[detail.explanation]];
 if(ticker==='VST'){
  sheet.getRange('A37:E37').values=[['Fiscal year','Short-term borrowing','Receivables financing','Year end','Treatment']];
  for(const [i,h] of detail.history.entries()){
   const rr=38+i;
   sheet.getRange(`A${rr}:E${rr}`).values=[[h.year,null,null,date(h.short_term.period_end),'Components already included in annual borrowing.']];
   for(const [col,f] of [['B',h.short_term],['C',h.receivables]])sheet.getRange(`${col}${rr}`).formulas=[[input(source(f),f.tag)]];
  }
  sheet.getRange('B8').setNumberFormat('#,##0,,;(#,##0,,);"0"');
  sheet.getRange('E8').values=[['Reported zero at June 30, 2026; not missing.']];
 }
 sheet.getRange('A44:E44').values=[['Liability classification','USD millions','As of','Status','Source / basis']];
 for(const [i,f] of detail.liabilities.entries()){
  const rr=45+i;let formula;
  if(f.inputs){const refs=f.inputs.map(part=>input(source(part),part.label).slice(1));formula='='+refs.join('-');}
  else formula=input(source(f),f.label);
  sheet.getRange(`A${rr}:E${rr}`).values=[[f.label,null,date(f.period_end),f.status,f.formula||f.location]];
  sheet.getRange(`B${rr}`).formulas=[[formula]];
 }
 sheet.getRange('A47:E47').values=[['Total liabilities',null,date(detail.period_end),'Derived','Current plus noncurrent; includes borrowing and recognized leases. Do not add them again.']];
 sheet.getRange('B47').formulas=[['=SUM(B45:B46)']];
 sheet.getRange('G44:I45').values=[['As of','Current liabilities','Noncurrent liabilities'],[detail.period_end,null,null]];
 sheet.getRange('H45').formulas=[['=B45']];sheet.getRange('I45').formulas=[['=B46']];sheet.getRange('G45').setNumberFormat('mmm d, yyyy');sheet.getRange('H45:I45').setNumberFormat(USD);
 const liabilityChart=sheet.charts.add('bar',sheet.getRange('G44:I45'));liabilityChart.barOptions.direction='column';liabilityChart.barOptions.grouping='stacked';liabilityChart.title='Total liabilities (USD billions)';liabilityChart.titleTextStyle.fontSize=12;liabilityChart.titleTextStyle.typeface='Arial';liabilityChart.yAxis={numberFormatCode:'0.0,,,',numberFormatSourceLinked:false};liabilityChart.legend={position:'bottom'};liabilityChart.series.items[0].fill=model.palette.borrowing;liabilityChart.series.items[1].fill=model.palette.cash;liabilityChart.setPosition('G5','P18');
 const detailFormat=sheet.getRange('A27:E47').format;
 detailFormat.font.name='Arial';detailFormat.font.size=10;detailFormat.wrapText=true;detailFormat.verticalAlignment='top';detailFormat.rowHeight=44;
 sheet.getRange('A34:E34').format.rowHeight=200;
 sheet.getRange('B29:B32').setNumberFormat(USD);sheet.getRange('B29:B32').format.font.color='#008000';sheet.getRange('B45:B47').setNumberFormat(USD);sheet.getRange('B45:B46').format.font.color='#008000';
 sheet.getRange('C29:C32').setNumberFormat('mmm d, yyyy');sheet.getRange('C45:C47').setNumberFormat('mmm d, yyyy');
 if(ticker==='VST'){sheet.getRange('B38:C42').setNumberFormat('#,##0,,;(#,##0,,);"0"');sheet.getRange('D38:D42').setNumberFormat('mmm d, yyyy');header(sheet,'A37:E37');frame(sheet,'A37:E42');}
 for(const rr of [28,44])header(sheet,`A${rr}:E${rr}`);
 for(const area of ['A28:E32','A44:E47'])frame(sheet,area);
 sheet.getRange('A27').format.font.bold=true;
 data.getRangeByIndexes(start,0,records.length,headers.length).values=records;
 const lastData=start+records.length;
 const area=`A${start}:${ticker==='LLY'?'O':'R'}${lastData}`;
 data.getRange(area).format.font.name='Arial';data.getRange(area).format.font.size=10;
 data.getRange(area).format.wrapText=true;data.getRange(area).format.verticalAlignment='top';data.getRange(area).format.rowHeight=78;
 data.getRange(`B${start+1}:B${lastData}`).setNumberFormat(USD);data.getRange(`B${start+1}:B${lastData}`).format.font.color='#0000FF';
 for(const c of ticker==='LLY'?['D','F']:['E','G'])data.getRange(`${c}${start+1}:${c}${lastData}`).setNumberFormat('mmm d, yyyy');
 frame(data,area);header(data,`A${start}:${ticker==='LLY'?'O':'R'}${start}`);
 sheet.showGridLines=false;
 const used=sheet.getRange(`A1:E${last}`);used.format.font.name='Arial';used.format.font.size=10;
 used.format.verticalAlignment='top';used.format.wrapText=true;used.format.rowHeight=42;
 [42,21,20,38,72].forEach((w,i)=>sheet.getRangeByIndexes(0,i,last,1).format.columnWidth=w);
 sheet.getRange('A2').format.font.bold=true;sheet.getRange('A2').format.font.size=14;
 sheet.getRange('A2:A3').format.wrapText=false;sheet.getRange('A2:E3').format.rowHeight=25;
 for(const r of [1,4,totalRow+1,totalRow+3,totalRow+4,last-1])sheet.getRange(`A${r}:E${r}`).format.rowHeight=12;
 sheet.getRange(`C6:C${last}`).setNumberFormat('mmm d, yyyy');
 sheet.getRange(`B6:B${last}`).setNumberFormat(USD);
 for(let r=6;r<=last;r++)if(sheet.getRange(`B${r}`).formulas[0][0])sheet.getRange(`B${r}`).format.font.color=sheet.getRange(`B${r}`).formulas[0][0].includes("'Data'!")?'#008000':'#000000';
 sheet.getRange(`B${totalRow+2}`).format.wrapText=true;
 sheet.getRange(`A${totalRow+2}:E${totalRow+2}`).format.rowHeight=58;
 sheet.getRange(`A${last}:E${last}`).format.rowHeight=54;
 sheet.getRange(`A5:E5`).format.rowHeight=28;sheet.getRange(`A${leaseHeader}:E${leaseHeader}`).format.rowHeight=28;
 header(sheet,'A5:E5');header(sheet,`A${leaseHeader}:E${leaseHeader}`);
 frame(sheet,`A5:E${totalRow}`);frame(sheet,`A${leaseHeader}:E${last-2}`);frame(sheet,`A${last}:E${last}`);
 subtotal(sheet,`A${totalRow}:E${totalRow}`);leaseTotalRows.forEach(([r])=>subtotal(sheet,`A${r}:E${r}`));
 sheet.freezePanes.freezeRows(5);
 wb.recalculate();
 if(sheet.getRange(`B${totalRow}`).values[0][0]!==model.baseline)throw new Error('Borrowing reconciliation failed');
 for(const [r,v] of leaseTotalRows)if(sheet.getRange(`B${r}`).values[0][0]!==v)throw new Error('Lease reconciliation failed');
 // A missing source must never turn into zero in the new presentation.
 const first=data.getRange(`B${start+1}`),original=first.values;
 first.values=[[null]];wb.recalculate();
 if(typeof sheet.getRange(`B${totalRow}`).values[0][0]==='number')throw new Error('Missing borrowing became a total');
 first.values=original;wb.recalculate();
 const about=wb.worksheets.getItem('About'),aboutRow=about.getUsedRange().values.length+1;
 about.getRange(`A${aboutRow}:C${aboutRow}`).values=[['Borrowing and leases','The Borrowing and leases sheet reconciles baseline borrowing and shows lease balances on their own dates. Unavailable means the amount was not established in the checked evidence. Leases never enter baseline debt or its ratios.','https://github.com/jackconnolly1000-ux/sec-filing-research-terminal/blob/main/docs/borrowing_lease_presentation.md']];
 const aboutStyle=about.getRange(`A${aboutRow}:C${aboutRow}`).format;
 aboutStyle.font.name='Arial';aboutStyle.font.size=10;aboutStyle.wrapText=true;aboutStyle.verticalAlignment='top';aboutStyle.rowHeight=78;
 frame(about,`A${aboutRow}:C${aboutRow}`);
 wb.recalculate();
 const invalid=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',options:{useRegex:true,maxResults:5},maxChars:1200});
 console.log(invalid.ndjson);
 for(const [range,name] of [[`A2:E${totalRow}`,'borrowing'],[`A${totalRow+2}:E${last}`,'leases'],[`A${start}:H${lastData}`,'inputs'],[`${ticker==='LLY'?'L':'M'}${start}:${ticker==='LLY'?'O':'R'}${lastData}`,'sources'],[`A${aboutRow}:C${aboutRow}`,'about']]){
  const png=await wb.render({sheetName:name==='about'?'About':['inputs','sources'].includes(name)?'Data':'Borrowing and leases',range,scale:1.2,format:'png'});
  await fs.writeFile(path.join(process.cwd(),`${ticker}-borrowing-${name}.png`),new Uint8Array(await png.arrayBuffer()));
 }
 return {borrowing_leases_sha256:JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,['-c','import json,borrowing_leases as b;print(json.dumps(b.fingerprint()))'],{cwd:root,encoding:'utf8'}))};
}
