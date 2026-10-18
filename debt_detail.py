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

def maturity_periods(model):
    """Five nearby annual columns and four later ranges; retain every dated principal dollar."""
    years=model['years']
    groups=[(2027,2027),(2028,2028),(2029,2029),(2030,2030),(2031,2031),
            (2032,2041),(2042,2051),(2052,2061),(2062,years[-1]['fy'])]
    periods=[]
    for lo,hi in groups:
        rows=[i for i,y in enumerate(years) if lo<=y['fy']<=hi]
        if not rows:continue
        label=('FY27 rem.' if lo==2027 else f'FY{lo%100:02d}' if lo==hi
               else f'FY{lo}–{hi}')
        periods.append(dict(label=label,start=years[rows[0]]['start'],end=years[rows[-1]]['end'],indices=rows))
    if [i for p in periods for i in p['indices']]!=list(range(len(years))):
        raise ValueError('Maturity periods must cover each fiscal year exactly once')
    return periods

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
        periods=maturity_periods(model)
        z=[[sum(row[i] for i in p['indices'])/1e9 for p in periods] for row in model['matrix']]
        if abs(sum(map(sum,z))-model['total']/1e9)>1e-8:raise ValueError('Grouped maturity chart does not reconcile')
        custom=[[[p['start'],p['end']] for p in periods] for _ in KINDS]
        # The precise figures remain in hover and the checked table. Cell text collides at phone width.
        period_labels=[]
        for p in periods:
            label=p['label']
            if label.endswith(' rem.'):
                label=label[:4]
            elif '–' in label:
                start,end=label[2:].split('–')
                label=f'{int(start)%100:02d}–{int(end)%100:02d}'
            period_labels.append(label)
        f=go.Figure(go.Heatmap(x=period_labels,y=model['kinds'],z=z,customdata=custom,
                            colorscale=[[0,T.SURFACE],[0.01,'#203450'],[1,T.SERIES_CASH]],zmin=0,zmax=max(map(max,z)),
                            xgap=2,ygap=3,colorbar=dict(title='USD B',thickness=12,thicknessmode='pixels',
                                                         tickfont=dict(color=T.TEXT),titlefont=dict(color=T.TEXT)),
                            hovertemplate='%{y}, %{x}<br>%{customdata[0]} to %{customdata[1]}<br>%{z:.3f}B principal<extra></extra>'))
        f.update_layout(height=375,margin=dict(l=145,r=50,t=50,b=85),
                        title=dict(text='Dated principal concentration · USD billions',font=dict(size=14),x=0.02),
                        plot_bgcolor=T.BG)
        f.update_xaxes(tickangle=-70,side='bottom',tickfont=dict(size=10),fixedrange=True)
        f.update_yaxes(automargin=True,fixedrange=True)
    elif view=='Fixed-rate coupon distribution':
        # Empty bins add eleven labels without information. They remain in the checked model and workbook.
        bins=[b for b in model['bins'] if b['principal_usd']]
        f=go.Figure(go.Bar(x=[f"{b['coupon_low_pct']}–<{b['coupon_high_pct']}%" for b in bins],
            y=[b['principal_usd']/1e9 for b in bins],marker_color=T.SERIES_BORROWING,
            customdata=[[b['tranche_count'],b['weighted_coupon_pct']] for b in bins],
            hovertemplate='%{x}<br>Principal: %{y:.3f}B<br>Tranches: %{customdata[0]}<br>Weighted coupon: %{customdata[1]:.2f}%<extra></extra>'))
        f.update_yaxes(title='USD billions',rangemode='tozero',gridcolor=T.BORDER,
                       zerolinecolor=T.TEXT_MUTED,fixedrange=True)
        f.update_xaxes(title='Fixed coupon bucket',showgrid=False,fixedrange=True)
    elif view=='Instrument composition':
        classes=model['composition'];values=[c['principal_usd']/1e9 for c in classes]
        f=go.Figure(go.Bar(x=values,y=[c['kind'] for c in classes],orientation='h',
            marker_color=T.SERIES_BORROWING,cliponaxis=False,
            text=[f'${v:,.3f}B · {v/(model["total"]/1e9):.1%}' for v in values],
            textposition='outside',textfont=dict(color=T.TEXT_STRONG,size=12),
            hovertemplate='%{y}<br>%{x:.3f}B principal<extra></extra>'))
        f.update_layout(height=255,margin=dict(l=180,r=145,t=12,b=48),bargap=.5)
        f.update_xaxes(title='USD billions',range=[0,max(values)*1.25],gridcolor=T.BORDER,fixedrange=True)
        f.update_yaxes(categoryorder='array',categoryarray=[c['kind'] for c in reversed(classes)],
                       automargin=True,fixedrange=True)
    else:raise ValueError('Unknown debt detail view')
    f.update_layout(paper_bgcolor='rgba(0,0,0,0)',font=dict(color=T.TEXT,size=12),showlegend=False)
    if view=='Fixed-rate coupon distribution':
        f.update_layout(height=350,margin=dict(l=65,r=50,t=25,b=75),plot_bgcolor='rgba(0,0,0,0)')
    elif view=='Instrument composition':
        f.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    return f
