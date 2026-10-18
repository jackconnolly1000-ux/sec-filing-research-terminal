"""Verify fixed coupons against exact saved annual filing contexts; no network."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import filing_xbrl as fx
import oracle_principal as op

def build(path):
    r=op.load();root=fx.parse(path);contexts=fx._contexts(root);facts={}
    for row in r['remaining']:
        if row['kind']!='Fixed-rate senior notes':continue
        matches=[]
        for f in root.iter('{'+fx.IX+'}nonFraction'):
            if f.get('name')!='us-gaap:DebtInstrumentInterestRateStatedPercentage':continue
            ctx=contexts[f.get('contextRef')]
            if ctx['instant']==op.AS_OF and [tuple(d) for d in ctx['dimensions']]==[(row['axis'],row['member'])]:
                value,_=fx._number(f)
                if value is None:raise ValueError('Missing fixed coupon')
                matches.append(dict(value=float(value),context_id=f.get('contextRef'),decimals=f.get('decimals'),scale=f.get('scale') or 0,dimensions=ctx['dimensions']))
        if not matches or len({m['value'] for m in matches})!=1 or abs(matches[0]['value']*100-row['stated_rate'])>1e-10:raise ValueError('Fixed coupon disagrees: '+row['member'])
        facts[row['member']]=dict(matches[0],tag='us-gaap:DebtInstrumentInterestRateStatedPercentage',unit='pure',form=r['annual']['form'],filed=r['annual']['filed'],accession=r['annual']['accession'],period_end=op.AS_OF,source_url=r['annual']['source_url'],source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),location='10-K Note 6, pp. 83–84')
    return facts
if __name__=='__main__':
    p=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'data/raw/sec/ORCL/orcl-20260531.htm'
    out=ROOT/'samples/oracle_coupon_sources.json';out.write_text(json.dumps(build(p),indent=2)+'\n');print(hashlib.sha256(out.read_bytes()).hexdigest())
