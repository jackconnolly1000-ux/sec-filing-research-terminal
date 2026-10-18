// Visual QA of every company worksheet plus each new table and chart area.
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const root=process.argv[2],out=process.argv[3];await fs.mkdir(out,{recursive:true});
for(const [ticker,stem] of [['LLY','lly'],['ORCL','oracle'],['VST','vistra']]){
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(root+'/samples/'+stem+'_liquidity.xlsx'));
 // Import does not evaluate every SUMIFS. Preview reconciled cached results in memory only; never save this copy.
 const rec=JSON.parse(execFileSync(process.env.CODEX_PRIMARY_RUNTIME_PYTHON,[root+'/tests/offline/export_layout_records.py',root+'/samples/'+stem+'_liquidity.xlsx'],{cwd:root,encoding:'utf8'}));
 for(const [name,r] of Object.entries(rec)){const sh=wb.worksheets.getItem(name);for(const [ref,value] of r.cells)if(typeof value==='number'&&sh.getRange(ref).formulas[0][0])sh.getRange(ref).values=[[value]];}
 for(const sh of wb.worksheets.items){
  let range=sh.name==='Borrowing and leases'?'A27:E34':sh.name==='Annual history'?'A2:F17':sh.name==='About'?'A1:C8':sh.name==='Data'?'A1:H8':sh.name==='Debt detail'?'A14:R27':sh.name==='Core charts'?'A2:O20':sh.name==='Funding conclusion'?'A2:B18':'A2:F15';
  const image=await wb.render({sheetName:sh.name,range,scale:1,format:'png'});
  await fs.writeFile(`${out}/${ticker}-${sh.name.replaceAll(' ','-')}.png`,new Uint8Array(await image.arrayBuffer()));
 }
 for(const [sheet,range,label] of [['Borrowing and leases','A37:E47','liabilities'],['Annual history','A24:G58','annual-charts'],['Annual history','A102:G118','historical-flow-ratio'],['Borrowing and leases','G5:P18','liability-stack'],...(ticker==='ORCL'?[['Payment dates','H35:U44','annual-maturities'],['Debt detail','A5:AO10','maturity-heatmap'],['Debt detail','A30:R47','principal-composition']]:[])]){
  const png=await wb.render({sheetName:sheet,range,scale:1,format:'png'});await fs.writeFile(`${out}/${ticker}-${label}.png`,new Uint8Array(await png.arrayBuffer()));
 }
 console.log(ticker+' all sheets rendered');
}
