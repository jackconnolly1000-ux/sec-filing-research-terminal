import {execFileSync} from 'node:child_process';
import {frame,header} from './workbook_style.mjs';
const col=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
export function addDebtDetail(wb){return wb.worksheets.add('Debt detail');}
export function finishDebtDetail(wb,root,s){
 const m=JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,['-c','import json,debt_detail;print(json.dumps(debt_detail.build()))'],{cwd:root,encoding:'utf8'}));
 const data=wb.worksheets.getItem('Data'),dataStart=data.getUsedRange().values.length+3,couponRows=[];
 const last=119+m.events.length,end=53+m.fixed.length,usd='#,##0.0,,,;(#,##0.0,,,);"0.0"';
 s.showGridLines=false;s.getRange(`A1:${col(m.years.length+1)}${last}`).format.font.name='Arial';s.getRange(`A1:${col(m.years.length+1)}${last}`).format.font.size=10;
 s.getRange(`A1:A${last}`).format.columnWidth=36;s.getRange(`B1:${col(m.years.length+1)}${last}`).format.columnWidth=13;s.getRange(`A1:${col(m.years.length+1)}${last}`).format.rowHeight=26;
 s.getRange('A2').values=[['Oracle principal detail at August 31, 2026']];s.getRange('A2').format.font.bold=true;s.getRange('A2').format.font.size=14;s.getRange('A3').values=[[m.note]];
 s.getRange('A5').values=[['Principal due (USD billions)']];s.getRangeByIndexes(4,1,1,m.years.length).values=[m.years.map(y=>y.label)];
 for(let i=0;i<3;i++){const rr=6+i;s.getRange(`A${rr}`).values=[[m.kinds[i]]];m.years.forEach((y,k)=>{const cell=s.getRange(`${col(k+2)}${rr}`);cell.formulas=[[`=SUMIFS($D$120:$D$${last},$B$120:$B$${last},${y.fy},$C$120:$C$${last},$A${rr})`]];cell.setNumberFormat(usd);const mag=m.matrix[i][k]/Math.max(...m.matrix.flat());cell.format.fill=mag>.75?'#235589':mag>.4?'#5B91C8':mag>0?'#BDD5EE':'#F2F4F7';cell.format.font.color=mag>.75?'#FFFFFF':'#111111';});}
 header(s,`A5:${col(m.years.length+1)}5`);frame(s,`A5:${col(m.years.length+1)}8`);
 s.getRange('A10').values=[['Darker = more principal, not a risk grade. Zero cells mean no known principal in that category/year. Unknown CP is excluded.']];
 s.getRange('A14:E14').values=[['Fixed coupon bucket','Principal (USD B)','Tranche count','Weighted coupon %','Upper bound (exclusive)']];
 m.bins.forEach((b,k)=>{const rr=15+k;s.getRange(`A${rr}:E${rr}`).values=[[`${b.coupon_low_pct}–<${b.coupon_high_pct}%`,null,null,null,b.coupon_high_pct/100]];
  const crit=`$C$54:$C$${end},">="&(${b.coupon_low_pct/100}),$C$54:$C$${end},"<"&E${rr}`;
  s.getRange(`B${rr}`).formulas=[[`=SUMIFS($D$54:$D$${end},${crit})`]];
  s.getRange(`C${rr}`).formulas=[[`=COUNTIFS(${crit})`]];
  s.getRange(`D${rr}`).formulas=[[b.principal_usd?`=SUMIFS($F$54:$F$${end},${crit})/B${rr}`:'=NA()']];
 });
 // An empty bucket has no weighted coupon, rather than an invented zero rate.
 m.bins.forEach((b,k)=>{if(!b.principal_usd)s.getRange(`D${15+k}`).values=[['No tranches']];});
 s.getRange('A14:E25').format.wrapText=true;s.getRange('A14:E14').format.rowHeight=50;
 s.getRange('B15:B25').setNumberFormat(usd);s.getRange('D15:D25').setNumberFormat('0.00%');s.getRange('E15:E25').setNumberFormat('0%');frame(s,'A14:E25');header(s,'A14:E14');
 s.getRange('A28').values=[['Only fixed-rate notes. Floating spreads and term-loan amortization rates excluded. Height is principal, not tranche count.']];
 s.getRange('A31:B34').values=[['Instrument type','Principal (USD B)'],...m.kinds.map(k=>[k,null])];
 m.kinds.forEach((k,i)=>s.getRange('B'+(32+i)).formulas=[[`=SUM(B${6+i}:${col(m.years.length+1)}${6+i})`]]);s.getRange('B32:B34').setNumberFormat(usd);frame(s,'A31:B34');header(s,'A31:B31');
 s.getRange('A36').values=[['Known principal only. Percentages exclude unknown CP, leases and interest.']];
 const hist=s.charts.add('bar',[s.getRange('A14:A25'),s.getRange('B14:B25')]);hist.barOptions.direction='column';hist.barOptions.grouping='clustered';hist.title='Fixed-rate principal by coupon bucket';hist.titleTextStyle.fontSize=12;hist.hasLegend=false;hist.yAxis={numberFormatCode:'0.0,,,',numberFormatSourceLinked:false};hist.yAxis.title.text='USD billions';hist.series.items[0].fill='#3987E5';hist.setPosition('G14','R27');
 const pie=s.charts.add('doughnut',s.getRange('A31:B34'));pie.title='Known principal by instrument';pie.titleTextStyle.fontSize=12;pie.legend={position:'bottom'};pie.setPosition('G30','R47');
 s.getRange('A50').values=[['Source: '+m.source]];s.getRange('A51').values=[['Inputs below link to Payment dates. Coupons are fractions displayed as percentages; weighted coupon = sum(principal × coupon) / principal.']];
 s.getRange('A53:G53').values=[['Fixed-rate note','Maturity','Stated coupon %','Principal USD B','Source member','Principal × coupon','Principal context']];
 m.fixed.forEach((f,k)=>{const rr=54+k;s.getRange(`A${rr}:G${rr}`).values=[[f.label,new Date(f.maturity+'T00:00:00Z'),null,null,f.member,null,f.principal_context]];const src=f.coupon_source,dr=dataStart+couponRows.length+1;couponRows.push([f.member,src.value,'Stated fixed coupon',null,new Date(src.period_end+'T00:00:00Z'),src.form,new Date(src.filed+'T00:00:00Z'),src.accession,src.tag,src.context_id,src.scale,src.decimals,src.source_url,src.location,'Unit pure; stated coupon as fraction. Exact instrument dimension; agreeing duplicates.',src.dimensions.map(d=>d.join(' = ')).join('; '),src.source_sha256,'pure fraction, displayed as %']);s.getRange(`C${rr}`).formulas=[[`='Data'!B${dr}`]];s.getRange(`D${rr}`).formulas=[[`='Payment dates'!${f.formula_ref}`]];s.getRange(`F${rr}`).formulas=[[`=C${rr}*D${rr}`]];});
 s.getRange(`B54:B${end}`).setNumberFormat('mmm d, yyyy');s.getRange(`C54:C${end}`).setNumberFormat('0.00%');s.getRange(`C54:C${end}`).format.font.color='#008000';s.getRange(`D54:D${end}`).setNumberFormat(usd);s.getRange(`D54:D${end}`).format.font.color='#008000';frame(s,`A53:G${end}`);header(s,'A53:G53');
 s.getRange('A119:E119').values=[['Payment date','Fiscal year','Instrument class','Principal USD B','Source instrument member']];
 m.events.forEach((e,k)=>{const rr=120+k;s.getRange(`A${rr}:E${rr}`).values=[[new Date(e.date+'T00:00:00Z'),+e.date.slice(0,4)+(+e.date.slice(5,7)>5?1:0),e.kind,null,e.member]];s.getRange(`D${rr}`).formulas=[[`='Payment dates'!${e.formula_ref}`]];});
 s.getRange(`A120:A${last}`).setNumberFormat('mmm d, yyyy');s.getRange(`D120:D${last}`).setNumberFormat(usd);s.getRange(`D120:D${last}`).format.font.color='#008000';frame(s,`A119:E${last}`);header(s,'A119:E119');s.freezePanes.freezeRows(5);
 s.getRange(`A53:G${last}`).format.wrapText=true;s.getRange(`A53:G${last}`).format.rowHeight=60;
 data.getRangeByIndexes(dataStart-1,0,1,18).values=data.getRange('A1:R1').values;data.getRangeByIndexes(dataStart,0,couponRows.length,18).values=couponRows;data.getRange(`B${dataStart+1}:B${dataStart+couponRows.length}`).setNumberFormat('0.00%');data.getRange(`B${dataStart+1}:B${dataStart+couponRows.length}`).format.font.color='#0000FF';data.getRange(`A${dataStart}:R${dataStart+couponRows.length}`).format.wrapText=true;data.getRange(`A${dataStart}:R${dataStart+couponRows.length}`).format.rowHeight=80;frame(data,`A${dataStart}:R${dataStart+couponRows.length}`);header(data,`A${dataStart}:R${dataStart}`);
 wb.recalculate();
 if(s.getRange('B32:B34').values.reduce((sum,r)=>sum+r[0],0)!==m.total)throw Error('Debt detail total does not reconcile');
 m.bins.forEach((b,i)=>{if(s.getRange(`B${15+i}`).values[0][0]!==b.principal_usd)throw Error('Coupon bins differ from app');});
}
