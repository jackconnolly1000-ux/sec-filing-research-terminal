// Shared finishing pass: canonical fact aliases, consistent typography, and a migration ledger.
import fs from 'node:fs/promises';
export async function finalizeWorkbook(wb,root,ticker,annualStart){
 for(const sh of wb.worksheets.items){const used=sh.getUsedRange();used.format.font.name='Arial';}
 if(ticker==='VST')wb.worksheets.getItem('Borrowing and leases').getRange('B8').setNumberFormat('#,##0,,;(#,##0,,);"0"');
 const data=wb.worksheets.getItem('Data'),values=data.getUsedRange().values;
 const canonical=new Map(),migration=[];
 const tags=new Set(['DebtCurrent','LongTermDebtNoncurrent','NotesPayableCurrent','LongTermNotesAndLoans','LongTermDebtAndCapitalLeaseObligationsCurrent','LongTermDebtAndCapitalLeaseObligations','ShortTermBorrowings','AccountsReceivableSecuritizationProgramAmountsBorrowed']);
 for(let i=1;i<values.length;i++){
  const r=values[i],tag=r[ticker==='LLY'?7:8];
  if(typeof tag!=='string'||!tags.has(tag.split(':').pop())||typeof r[1]!=='number')continue;
  const acc=r[ticker==='LLY'?6:7],period=r[ticker==='LLY'?3:4],context=r[ticker==='LLY'?8:9]||null;
  const key=JSON.stringify([acc,tag,context,period,'USD']);
  if(canonical.has(key)){
   const old=canonical.get(key);if(old.value!==r[1])throw Error('Conflicting duplicate source fact: '+key);
   const from='B'+(i+1),to='B'+old.row;data.getRange(from).formulas=[['='+to]];data.getRange(from).format.font.color='#000000';
   migration.push({sheet:'Data',from,to,identity:JSON.parse(key),treatment:'Same-sheet formula alias; original address retained.'});
  }else canonical.set(key,{row:i+1,value:r[1]});
 }
 await fs.writeFile(root+'/samples/'+ticker.toLowerCase()+'_cell_migrations.json',JSON.stringify({ticker,migrations:migration},null,2)+'\n');
 wb.recalculate();
}
