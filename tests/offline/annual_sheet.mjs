// Shared source-backed annual table; used by every company build, not a post-build migration.
import {execFileSync} from 'node:child_process';
import {frame,header} from './workbook_style.mjs';
const date=s=>s?new Date(s+'T00:00:00Z'):null;
const USD='#,##0.0,,;(#,##0.0,,);"-"';
export function addAnnualSheet(wb,root,ticker){
 const model=JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,['-c','import json,sys,annual_history_view as a;print(json.dumps(a.build(sys.argv[1])))',ticker],{cwd:root,encoding:'utf8'}));
 return {model,sheet:wb.worksheets.add('Annual history')};
}
export function finishAnnualSheet(wb,root,ticker,{model,sheet}){
 const data=wb.worksheets.getItem('Data'),start=data.getUsedRange().values.length+3;
 const records=[],refs=new Map(),cols=ticker==='LLY'?15:18;
 const factKey=f=>[f.accession,f.tag,f.context_id,f.period_start||'',f.period_end,JSON.stringify(f.dimensions||[])].join('|');
 function input(f,label){
  const key=factKey(f);if(refs.has(key))return refs.get(key);
  const n=start+records.length+1;
  const location=typeof f.location==='object'?'Printed p. '+f.location.printed_page+'; '+f.location.row_text:f.location;
  const dims=f.dimensions?.length?f.dimensions.map(d=>d.join(' = ')).join('; '):'None (consolidated total)';
  const row=ticker==='LLY'?[label,f.value,date(f.period_start),date(f.period_end),f.form,date(f.filed),f.accession,f.tag,f.context_id,f.scale??null,f.decimals??null,f.source_url,location,'Checked exact USD period and filing version.',f.source_sha256]:
   [label,f.value,label,date(f.period_start),date(f.period_end),f.form,date(f.filed),f.accession,f.tag,f.context_id,
    ...(ticker==='VST'?[dims,f.scale??null,f.decimals??null]:[f.scale??null,f.decimals??null]),f.source_url,location,'Checked exact USD period and filing version.',...(ticker==='VST'?[]:[dims]),f.source_sha256,'USD'];
  records.push(row);refs.set(key,`'Data'!B${n}`);return refs.get(key);
 }
 sheet.getRange('A2').values=[[ticker+' annual history']];sheet.getRange('A3').values=[['USD millions. Five completed fiscal years; the latest TTM is separate.']];
 sheet.getRange('B4:F4').values=[model.rows.map(r=>date(r.source.period_end))];sheet.getRange('B4:F4').setNumberFormat('mmm d, yyyy');
 sheet.getRange('A5:F5').values=[['Measure',...model.rows.map(r=>'FY'+r.fiscal_year)]];
 for(const [i,key] of model.keys.entries()){
  const row=6+i;sheet.getRange(`A${row}`).values=[[model.labels[i]]];
  for(const [j,obs] of model.rows.entries()){
   const c='BCDEF'[j],metric=obs.metrics[key];
   if(metric.value===null){sheet.getRange(`${c}${row}`).values=[['Unavailable']];continue;}
   let formula;
   if(key==='free_cash_flow')formula=`=${c}8-${c}9`;
   else {const references=metric.inputs.map(f=>input(f,key));formula='='+references.map(ref=>`IF(ISNUMBER(${ref}),${ref},NA())`).join('+');}
   sheet.getRange(`${c}${row}`).formulas=[[formula]];
  }
 }
 data.getRangeByIndexes(start-1,0,1,cols).values=data.getRangeByIndexes(0,0,1,cols).values;
 data.getRangeByIndexes(start,0,records.length,cols).values=records;
 const final=start+records.length,lastCol=ticker==='LLY'?'O':'R';
 const range=data.getRange(`A${start}:${lastCol}${final}`);range.format.font.name='Arial';range.format.font.size=10;range.format.wrapText=true;range.format.verticalAlignment='top';range.format.rowHeight=78;
 data.getRange(`B${start+1}:B${final}`).setNumberFormat(USD);data.getRange(`B${start+1}:B${final}`).format.font.color='#0000FF';frame(data,`A${start}:${lastCol}${final}`);header(data,`A${start}:${lastCol}${start}`);
 sheet.showGridLines=false;sheet.getRange('A1:F61').format.font.name='Arial';sheet.getRange('A1:F61').format.font.size=10;
 sheet.getRange('A1:F61').format.verticalAlignment='top';sheet.getRange('A1:F22').format.rowHeight=27;
 sheet.getRange('A1:A61').format.columnWidth=44;sheet.getRange('B1:F61').format.columnWidth=22;sheet.getRange('B6:F10').setNumberFormat(USD);
 sheet.getRange('B6:F9').format.font.color='#008000';sheet.getRange('B10:F10').format.font.color='#000000';
 sheet.getRange('A2').format.font.bold=true;sheet.getRange('A2').format.font.size=14;frame(sheet,'A5:F10');header(sheet,'A5:F5');sheet.freezePanes.freezeRows(5);
 const notes=['Cash/debt: fiscal-year-end balances. OCF/capex: full fiscal years.',
 'FCF = OCF less capital spending; acquisitions and financing uses excluded.',
 'Historical cash generation does not establish future funding coverage.',
 ticker==='LLY'?'FY2021/22 OCF includes disclosed reclassification, not new cash generation.':
 ticker==='VST'?'FY2021/24 use complete comparative snapshots, including reported zeros.':'Oracle fiscal years end May 31; other pilot calendars differ.'];
 notes.forEach((note,i)=>{sheet.getRange(`A${13+i}`).values=[[note]];sheet.getRange(`A${13+i}`).format.wrapText=false;});
 const about=wb.worksheets.getItem('About'),ar=about.getUsedRange().values.length+1;
 model.notes.forEach((note,i)=>{about.getRange(`A${ar+i}:C${ar+i}`).values=[['Annual history basis',note,'https://github.com/jackconnolly1000-ux/sec-filing-research-terminal/blob/main/docs/annual_history.md']];about.getRange(`A${ar+i}:C${ar+i}`).format.wrapText=true;about.getRange(`A${ar+i}:C${ar+i}`).format.rowHeight=125;});
 // Range-backed clustered columns, retaining missing values as NA rather than zero.
 sheet.getRange('A61').values=[['Capital spending (use of cash)']];
 for(const c of 'BCDEF')sheet.getRange(`${c}61`).formulas=[[`=IF(ISNUMBER(${c}9),-${c}9,NA())`]];
 sheet.getRange('B61:F61').setNumberFormat(USD);
 for(const [ranges,title,top,bottom,colors] of [
  [['A5:F7'],'Fiscal-year-end cash and baseline borrowing (USD millions)','A24','G40',[model.palette.cash,model.palette.borrowing]],
  [['A5:F5','A8:F8','A61:F61','A10:F10'],'Annual OCF, capital spending and FCF (USD millions)','A42','G58',[model.palette.ocf,model.palette.capex,model.palette.fcf]]]){
  // A transposed helper keeps Excel's categories and source formulas explicit.
  const first=top==='A24'?64:73,series=top==='A24'?[6,7]:[8,61,10],end=first+5;
  sheet.getRangeByIndexes(first-1,0,1,series.length+1).values=[['Fiscal year',...series.map(r=>sheet.getRange(`A${r}`).values[0][0])]];
  for(let j=0;j<5;j++){const c='BCDEF'[j],rr=first+1+j;sheet.getRange(`A${rr}`).values=[['FY'+model.rows[j].fiscal_year]];sheet.getRangeByIndexes(rr-1,1,1,series.length).formulas=[series.map(r=>`=IF(ISNUMBER(${c}${r}),${c}${r},NA())`)];}
  const ch=sheet.charts.add('bar',sheet.getRangeByIndexes(first-1,0,6,series.length+1));ch.barOptions.direction='column';ch.barOptions.grouping='clustered';ch.title=title;ch.titleTextStyle.fontSize=12;ch.titleTextStyle.typeface='Arial';ch.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};ch.yAxis={numberFormatCode:'#,##0,,',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:10}};ch.yAxis.title.text='USD millions';ch.legend={position:'bottom',textStyle:{typeface:'Arial'}};ch.series.items.forEach((s,i)=>s.fill=colors[i]);ch.setPosition(top,bottom);
 }
 sheet.getRange('A19').values=[['Historical OCF / year-end borrowing (not repayment coverage)']];sheet.getRange('A19').format.wrapText=false;
 sheet.getRange('A20').values=[['Annual flow / closing borrowing']];
 for(const c of 'BCDEF')sheet.getRange(`${c}20`).formulas=[[`=IF(AND(ISNUMBER(${c}7),${c}7>0,ISNUMBER(${c}8)),${c}8/${c}7,NA())`]];
 sheet.getRange('B20:F20').setNumberFormat('0.0%;(0.0%);"0.0%"');frame(sheet,'A20:F20');
 sheet.getRange('A90:B90').values=[['Fiscal year','Historical OCF / year-end borrowing']];
 model.rows.forEach((r,i)=>{sheet.getRange(`A${91+i}`).values=[['FY'+r.fiscal_year]];sheet.getRange(`B${91+i}`).formulas=[['='+'BCDEF'[i]+'20']];});
 const ratio=sheet.charts.add('line',sheet.getRange('A90:B95'));ratio.title='Annual OCF / year-end borrowing (%)';ratio.titleTextStyle.fontSize=12;ratio.titleTextStyle.typeface='Arial';ratio.yAxis={numberFormatCode:'0%',numberFormatSourceLinked:false};ratio.hasLegend=false;ratio.series.items[0].fill=model.palette.ocf;ratio.setPosition('A102','G118');
 return {annual_data_start:start,annual_data_last:final};
}
