"""Principal-only Oracle views from the checked instrument calendar; no inferred CP or floating coupons."""
from collections import defaultdict
import math
import hashlib,json
from pathlib import Path
COUPONS=Path(__file__).with_name("samples")/"oracle_coupon_sources.json"
COUPON_SHA256="8d3a0b60aa04450ce71e897cf48958dab575470dedb48512c1ff9cf421553c7b"
import oracle_principal as op
from oracle_principal_view import ladder_years
KINDS=('Fixed-rate notes','Floating-rate notes','Term loan')
CLASS={'Fixed-rate senior notes':KINDS[0],'Floating-rate senior notes':KINDS[1],'Term loan':KINDS[2]}
NOTE=('At August 31, 2026. Known note and term-loan principal only; commercial paper is Unavailable and excluded. '
      'Excludes interest and leases. Term-loan maturity assumes no optional extension. Not funding coverage.')

def build(review=None):
    r=review if review is not None else op.load()
    if r is None:raise ValueError('Checked principal calendar required')
    if hashlib.sha256(COUPONS.read_bytes()).hexdigest()!=COUPON_SHA256:raise ValueError('Fixed coupon sources changed; reconcile before use')
    sources=json.loads(COUPONS.read_text())
    years=ladder_years(r);events=[];fixed=[]
    for row in r['remaining']:
        if row['kind']=='Commercial paper':continue
        if row['kind'] not in CLASS:raise ValueError('Unknown instrument class')
        kind=CLASS[row['kind']]
        if kind=='Term loan':
            for step in [*r['term_loan']['installments'],r['term_loan']['final']]:
                if step['date']>op.ANCHOR:events.append(dict(date=step['date'],kind=kind,principal_usd=step['amount'],member=row['member']))
        else:
            events.append(dict(date=row['maturity'],kind=kind,principal_usd=row['principal_aug_31'],member=row['member']))
        if kind==KINDS[0]:
            rate=row['stated_rate']
            if not isinstance(rate,(int,float)) or not math.isfinite(rate) or not 0<=rate<11:raise ValueError('Fixed coupon outside explicit bins')
            source=sources[row['member']]
            if abs(source['value']*100-rate)>1e-10:raise ValueError('Fixed coupon differs from checked source')
            fixed.append(dict(row,coupon_pct=rate,coupon_source=source))
    matrix=[[sum(e['principal_usd'] for e in events if e['kind']==k and op.fiscal_year(e['date'])==y['fy']) for y in years] for k in KINDS]
    composition=[dict(kind=k,principal_usd=sum(row)) for k,row in zip(KINDS,matrix)]
    bins=[]
    for lo in range(11):
        group=[row for row in fixed if lo<=row['coupon_pct']<lo+1];p=sum(row['principal_aug_31'] for row in group)
        bins.append(dict(coupon_low_pct=lo,coupon_high_pct=lo+1,principal_usd=p,tranche_count=len(group),
                         weighted_coupon_pct=sum(row['principal_aug_31']*row['coupon_pct'] for row in group)/p if p else None))
    total=r['reconciliation']['known_principal_excluding_cp']
    if sum(e['principal_usd'] for e in events)!=total or sum(c['principal_usd'] for c in composition)!=total:raise ValueError('Instrument views do not reconcile')
    if sum(b['principal_usd'] for b in bins)!=composition[0]['principal_usd']:raise ValueError('Fixed coupon bins do not reconcile')
    refs={row['member']:95+i for i,row in enumerate(r['matured']+r['remaining'])}
    for e in events:
        if e['kind']=='Term loan':
            e['formula_ref']='C'+str(78+next((i for i,step in enumerate(r['term_loan']['installments']) if step['date']==e['date']),len(r['term_loan']['installments'])))
        else:e['formula_ref']='E'+str(refs[e['member']])
    for row in fixed:row['formula_ref']='E'+str(refs[row['member']])
    return dict(years=years,kinds=list(KINDS),matrix=matrix,bins=bins,composition=composition,events=events,fixed=fixed,note=NOTE,total=total,
                source=r['annual']['source_url'],accession=r['annual']['accession'])

def figure(model,view):
    import plotly.graph_objects as go
    import theme as T
    if view=='Maturity concentration':
        years=model['years'];z=[[v/1e9 for v in row] for row in model['matrix']]
        custom=[[[y['start'],y['end'],k] for y in years] for k in KINDS]
        f=go.Figure(go.Heatmap(x=[y['label'] for y in years],y=model['kinds'],z=z,customdata=custom,colorscale='Blues',zmin=0,
                            colorbar=dict(title='USD B'),hovertemplate='%{y}, %{x}<br>%{customdata[0]} to %{customdata[1]}<br>%{z:.3f}B principal<extra></extra>'))
    elif view=='Fixed-rate coupon distribution':
        bins=model['bins'];f=go.Figure(go.Bar(x=[f"{b['coupon_low_pct']}–<{b['coupon_high_pct']}%" for b in bins],y=[b['principal_usd']/1e9 for b in bins],
            marker=dict(color=[b['weighted_coupon_pct'] if b['weighted_coupon_pct'] is not None else 0 for b in bins],colorscale='Blues',colorbar=dict(title='Weighted<br>coupon %')),
            customdata=[[b['tranche_count'],b['weighted_coupon_pct']] for b in bins],hovertemplate='%{x}<br>Principal: %{y:.3f}B<br>Tranches: %{customdata[0]}<br>Weighted coupon: %{customdata[1]:.2f}%<extra></extra>'))
        f.update_yaxes(title='USD billions',rangemode='tozero');f.update_xaxes(title='Fixed coupon buckets (lower inclusive, upper exclusive)')
    elif view=='Instrument composition':
        f=go.Figure(go.Pie(labels=[c['kind'] for c in model['composition']],values=[c['principal_usd']/1e9 for c in model['composition']],hole=.55,
                          marker=dict(colors=[T.SERIES_BORROWING,T.SERIES_CASH,T.SERIES_SMA_FAST]),textinfo='label+percent',hovertemplate='%{label}<br>%{value:.3f}B<extra></extra>'))
    else:raise ValueError('Unknown debt detail view')
    f.update_layout(height=350,margin=dict(l=50,r=20,t=25,b=65),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color=T.TEXT,size=12),showlegend=False)
    return f
