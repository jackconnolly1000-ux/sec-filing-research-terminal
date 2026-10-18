import fs from 'node:fs/promises';
// The checked calendar is authored as part of the normal Oracle build.
import {execFileSync} from 'node:child_process';
import {frame,header} from './workbook_style.mjs';
export async function finishPrincipal(wb,root){
 const m=JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,['tests/offline/principal_records.py'],{cwd:root,encoding:'utf8'}));
 const s=wb.worksheets.getItem('Payment dates');
 const USD='#,##0.0,,;(#,##0.0,,);"0"';
 for(const c of m.cells){const cell=s.getRange(c.ref);if(c.formula)cell.formulas=[['='+c.formula]];else cell.values=[[c.date?new Date(c.value):c.value]];if(c.date)cell.setNumberFormat('mmm d, yyyy');else if(typeof c.value==='number')cell.setNumberFormat(USD);cell.format.font.color=c.formula?'#000000':c.reported?'#0000FF':'#222222';}
 s.getRange('A35:F153').format.font.name='Arial';s.getRange('A35:F153').format.font.size=10;s.getRange('A35:F153').format.wrapText=true;s.getRange('A35:F153').format.verticalAlignment='top';
 for(const [row,h] of Object.entries(m.heights))s.getRange(`A${row}:F${row}`).format.rowHeight=Math.max(h,38);
 for(const rr of [38,48,57,76,94]){header(s,`A${rr}:F${rr}`);}
 s.getRange('A35').format.font.bold=true;s.getRange('A35').format.font.size=14;s.getRange('A35:F36').format.rowHeight=75;
 s.getRange('A29').values=[['May schedule is historical. August principal starts at row 35; commercial paper remains Unavailable.']];
 for(const ref of ['C45','E152','B26'])s.getRange(ref).values=[['Unavailable']];
 s.getRange('E76:F80').values=[['Contract/rounding input','Value'],['First-stage amortization rate',.0125],['Later amortization rate',.025],['Tagged decimals',-8],['Half rounding interval',null]];
 s.getRange('F77:F78').setNumberFormat('0.00%');s.getRange('F77:F79').format.font.color='#0000FF';s.getRange('F80').formulas=[['=0.5*10^(-F79)']];s.getRange('F80').setNumberFormat(USD);frame(s,'E76:F80');header(s,'E76:F76');
 s.getRange('E82').values=[['Rates: 10-K Note 6 pp. 85–86; decimals: 10-Q Note 2 p. 9.']];s.getRange('E82:F84').format.wrapText=true;s.getRange('E82:F84').format.rowHeight=45;
 s.getRange('E85').values=[[m.annual.source_url]];
 const rec=wb.worksheets.getItem('Repayment review');rec.getRange('A40').values=[['Note and term-loan principal is dated in Payment dates, row 35 onward. CP and interest dates are Unavailable.']];
 rec.getRange('A53').values=[['Commercial paper and interest at August 31']];rec.getRange('D53').values=[['The principal calendar excludes August CP and interest, which remain Unavailable. Grouped quarter repayments are not assigned to instruments.']];
 s.getRange('E48:F48').values=[['FY2032 onward, by decade','Principal (USD millions)']];
 m.decades.forEach((d,k)=>{const rr=49+k,y=+d.start.slice(0,4),end=+d.end.slice(0,4);s.getRange(`E${rr}`).values=[[d.label]];s.getRange(`F${rr}`).formulas=[[`=SUMIFS($E$95:$E$152,$B$95:$B$152,">="&DATE(${y},6,1),$B$95:$B$152,"<="&DATE(${end},5,31))`]];});
 s.getRange('F53').formulas=[['=SUM(F49:F52)']];s.getRange('F54').formulas=[['=F53-C54']];s.getRange('F49:F54').setNumberFormat(USD);
 for(const area of ['A38:D46','A48:D55','A57:D73','A76:D92','A94:F152'])frame(s,area);
 s.getRange('H61:I61').values=[['Fiscal year','Principal due (USD millions)']];
 m.years.forEach((y,k)=>{const rr=62+k,fy=y.fy,start=fy===2027?'DATE(2026,9,1)':`DATE(${fy-1},6,1)`,end=`DATE(${fy},5,31)`;
  s.getRange(`H${rr}`).values=[[y.label]];
  s.getRange(`I${rr}`).formulas=[[`=SUMIFS($E$95:$E$152,$B$95:$B$152,">="&${start},$B$95:$B$152,"<="&${end},$F$95:$F$152,"<>Term loan")+SUMIFS($C$78:$C$90,$B$78:$B$90,">="&${start},$B$78:$B$90,"<="&${end})`]];
 });
 s.getRange(`I62:I${61+m.years.length}`).setNumberFormat(USD);header(s,'H61:I61');frame(s,`H61:I${61+m.years.length}`);
 const chart=s.charts.add('bar',s.getRange(`H61:I${61+m.years.length}`));chart.barOptions.direction='column';chart.barOptions.grouping='clustered';chart.title='Principal by fiscal year (USD billions)';chart.titleTextStyle.fontSize=12;chart.titleTextStyle.typeface='Arial';chart.hasLegend=false;chart.yAxis={numberFormatCode:'0.0,,,',numberFormatSourceLinked:false};chart.yAxis.title.text='USD billions';chart.series.items[0].fill='#D95926';chart.setPosition('H35','U43');
 s.getRange('H44').values=[['FY2027 remainder: Sep 2026–May 2027. CP, interest and leases excluded; term loan may be extended.']];s.getRange('H44').format.wrapText=false;
 wb.recalculate();
 if(s.getRange('C46').values[0][0]!==7317000000||s.getRange('F54').values[0][0]!==0)throw Error('Principal calendar reconciliation failed');
 const preview=await wb.render({sheetName:'Payment dates',range:'H35:U44',scale:1,format:'png'});await fs.writeFile('oracle-annual-maturities-authored.png',new Uint8Array(await preview.arrayBuffer()));
 return {principal_sha256:m.fingerprint};
}
