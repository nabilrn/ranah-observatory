import csv
from common import FIGURES, TABLES, fmt, svg_open, svg_close, text, rect, line, polyline

SHORT={
'observed_trajectory_foundation':'Observed trajectory','expected_performance':'Expected performance','attainable_reference':'Empirical reference','development_gaps':'Development gaps','associated_bottlenecks':'Association screen','causal_evidence':'Identification evidence','spatial_climate_constraints':'Spatial/climate constraints','intervention_scenarios':'Predictive sensitivities','uncertainty_evidence_strength':'Uncertainty & claim boundaries'}

def f01(d):
    nodes=sorted(d['nodes'],key=lambda r:int(r['stage_order'])); edges=d['edges']; W,H=1320,500; s=svg_open(W,H,'F01 Ranah Observatory evidence chain')
    text(s,40,38,'F01. Ranah Observatory evidence chain',22,'bold'); text(s,40,62,'All arrows are analytical/evidence relationships; none are causal.',13)
    pos={}; main=[n for n in nodes if n['node_id']!='uncertainty_evidence_strength']
    for i,n in enumerate(main):
        x=30+i*158; y=140 if i%2==0 else 260; pos[n['node_id']]=(x,y); rect(s,x,y,135,70,'#f7f7f7','#111',1,6); text(s,x+67.5,y+28,SHORT[n['node_id']],12,'bold','middle'); text(s,x+67.5,y+50,'M'+n['upstream'],10,'normal','middle')
    ux,uy,uw=330,405,660; pos['uncertainty_evidence_strength']=(ux,uy); rect(s,ux,uy,uw,52,'#ededed','#111',1,6); text(s,ux+uw/2,uy+31,SHORT['uncertainty_evidence_strength'],14,'bold','middle')
    for e in edges:
        a,b=e['from_node'],e['to_node']
        if a not in pos or b not in pos: continue
        if b=='uncertainty_evidence_strength':
            x,y=pos[a]; line(s,x+67.5,y+70,ux+uw/2,uy,'#777',1,'4 4')
        else:
            x1,y1=pos[a]; x2,y2=pos[b]; line(s,x1+135,y1+35,x2,y2+35,'#333',1,'5 4' if e['edge_type']=='readiness_constraint' else None)
    text(s,40,486,'Solid = dependency/extension; dashed = readiness constraint or uncertainty. causal_edge=False for all 18 edges.',11); svg_close(s,FIGURES/'F01-evidence-chain.svg')

def f02(d):
    m=d['m13']; W,H=1050,520; s=svg_open(W,H,'F02 Gap qualification and method disagreement'); text(s,40,38,'F02. Gap qualification and method disagreement',22,'bold')
    c=m['expected_interval_classification_counts']; items=[('Less favorable',c['materially_less_favorable_than_expected']),('Within interval',c['within_expected_interval']),('More favorable',c['materially_more_favorable_than_expected'])]; mx=max(v for _,v in items); text(s,40,82,'Expected-performance interval classification (342 rows)',15,'bold')
    for i,(lab,val) in enumerate(items):
        y=110+i*60; text(s,40,y+22,lab,13); w=600*val/mx; rect(s,180,y,w,28,'#444' if i!=1 else '#999'); text(s,190+w,y+21,val,13,'bold')
    a,b=m['gap_interpretation_authorized_row_count'],m['gap_interpretation_blocked_row_count']; total=a+b; text(s,40,330,'Support authorization',15,'bold'); aw=700*a/total; rect(s,40,350,aw,34,'#333'); rect(s,40+aw,350,700-aw,34,'#ddd'); text(s,50,373,f'Authorized {a}',13,'bold'); text(s,50+aw,373,f'Blocked {b}',13,'bold'); text(s,40,430,f"Primary vs structural-neighbor frontier sign disagreements: {m['frontier_gap_sign_disagreement_count']} / {total}",15,'bold'); text(s,40,458,'Disagreements remain explicit; no averaging, composite score, or monetary conversion.',12); svg_close(s,FIGURES/'F02-gap-qualification.svg')

def f03(d):
    rows=d['m22_geo']; summ={r['indicator_id']:r for r in d['m22_summary']}; inds=[r['indicator_id'] for r in d['m22_summary']]; geos=[]; seen=set()
    for r in rows:
        if r['geography_id'] not in seen: geos.append((r['geography_id'],r['geography_name'])); seen.add(r['geography_id'])
    by={(r['indicator_id'],r['geography_id']):r for r in rows}; W,H=1260,600; s=svg_open(W,H,'F03 Modern trajectory classification matrix'); text(s,30,34,'F03. Modern trajectory classification matrix',22,'bold'); x0,y0,cw,ch=280,160,45,42
    for j,(_,name) in enumerate(geos): text(s,x0+j*cw+18,y0-10,name,9,anchor='end',rotate=-60)
    fills={'persistent_increase':'#222','persistent_decrease':'#999','trajectory_not_robust':'#fff'}
    for i,ind in enumerate(inds):
        y=y0+i*ch; q=summ[ind]['hierarchical_trajectory_qualified']=='True'; text(s,25,y+24,ind,12,'bold' if q else 'normal'); text(s,215,y+24,'qualified' if q else 'failed gate',10,anchor='end')
        for j,(gid,_) in enumerate(geos):
            r=by[(ind,gid)]; rect(s,x0+j*cw,y,cw-3,ch-4,fills.get(r['trajectory_classification'],'#fff'),'#555');
            if not q: text(s,x0+j*cw+(cw-3)/2,y+26,'×',16,'bold','middle')
    ly=y0+len(inds)*ch+35; rect(s,30,ly,24,18,'#222'); text(s,62,ly+14,'persistent increase',11); rect(s,200,ly,24,18,'#999'); text(s,232,ly+14,'persistent decrease',11); rect(s,380,ly,24,18,'#fff'); text(s,412,ly+14,'not robust',11); text(s,530,ly+14,'× = indicator failed benchmark; geography classifications are not authorized',11); svg_close(s,FIGURES/'F03-trajectory-matrix.svg')

def f04(d):
    rows=d['m19_summary']; W,H=1140,560; s=svg_open(W,H,'F04 One-year-ahead forecast benchmark failure'); text(s,35,38,'F04. One-year-ahead forecast benchmark failure',22,'bold'); text(s,35,62,'Each target uses its own scale. Lower error is better; zero of three targets qualify.',12)
    for i,r in enumerate(rows):
        x0=40+i*365; top,h=125,300; vals=[float(r[k]) for k in ['dynamic_ridge_rmse','persistence_rmse','dynamic_ridge_mae','persistence_mae']]; mx=max(vals)*1.08; text(s,x0+150,100,r['target_id'],14,'bold','middle')
        for j,(lab,val,fill) in enumerate(zip(['RMSE dyn','RMSE pers','MAE dyn','MAE pers'],vals,['#333','#aaa','#333','#aaa'])):
            x=x0+30+j*70; bh=h*val/mx; rect(s,x,top+h-bh,55,bh,fill); text(s,x+27.5,top+h+22,lab,9,anchor='middle',rotate=-35); text(s,x+27.5,top+h-bh-7,fmt(val,3),10,'bold','middle')
        text(s,x0+150,492,'FAILED',13,'bold','middle')
    svg_close(s,FIGURES/'F04-forecast-benchmark-failure.svg')

def f05(d):
    annual=d['m20_annual']; tr=d['m20_trend'][0]; reg=d['m21_regime'][0]; rolling=d['m21_rolling']; W,H=1220,650; s=svg_open(W,H,'F05 Historical rainfall qualification diagnostics'); text(s,35,36,'F05. Historical rainfall qualification diagnostics',22,'bold'); text(s,35,61,'CHIRPS model-estimate evidence on a fixed current-boundary frame; candidate patterns remain unqualified.',12)
    x0,y0,w,h=70,105,1080,330; years=[int(r['analysis_year']) for r in annual]; vals=[float(r['unweighted_mean_rainfall_mm']) for r in annual]; ymin,ymax=min(vals)*.92,max(vals)*1.04; px=lambda y:x0+w*(y-years[0])/(years[-1]-years[0]); py=lambda v:y0+h-h*(v-ymin)/(ymax-ymin)
    for frac in [0,.25,.5,.75,1]:
        v=ymin+frac*(ymax-ymin); yy=py(v); line(s,x0,yy,x0+w,yy,'#ddd'); text(s,x0-10,yy+4,f'{v:.0f}',9,anchor='end')
    polyline(s,[(px(y),py(v)) for y,v in zip(years,vals)],'#222',1.8); br=int(reg['selected_break_year']); line(s,px(br),y0,px(br),y0+h,'#555',1,'5 4'); text(s,px(br)+6,y0+18,f'candidate break {br}',11,'bold'); text(s,x0,462,f"Full-period slope {fmt(tr['sen_slope_mm_per_year'],2)} mm/year; early {fmt(tr['early_sen_slope_mm_per_year'],2)}, late {fmt(tr['late_sen_slope_mm_per_year'],2)}.",12); text(s,x0,484,f"M20: {tr['robust_monotonic_classification']}; public claim={tr['public_claim_authorized']}",12,'bold'); text(s,x0,520,'Rolling-origin selected break years',12,'bold')
    rx,ry,rw,rh=300,535,760,70; bv=[int(r['selected_break_year']) for r in rolling]; fy=[int(r['forecast_year']) for r in rolling]; bmin,bmax=min(bv)-1,max(bv)+1
    for a,b in zip(fy,bv):
        x=rx+rw*(a-fy[0])/(fy[-1]-fy[0]); y=ry+rh-rh*(b-bmin)/(bmax-bmin); s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#333"/>')
    text(s,1080,548,f"median {reg['rolling_median_break_year']}",10); text(s,1080,566,f"within ±3y {float(reg['rolling_break_within_3y_fraction'])*100:.0f}%",10); text(s,1080,584,'stability FAIL',10,'bold'); svg_close(s,FIGURES/'F05-rainfall-qualification.svg')

def f06(d):
    W,H=1180,500; s=svg_open(W,H,'F06 Post-M18 evidence coverage expansion'); text(s,35,38,'F06. Post-M18 evidence coverage expansion',22,'bold'); text(s,35,62,'Cards show source-native coverage. Counts are not compared on a common magnitude axis.',12)
    with (TABLES/'T06-post-M18-evidence-expansion.csv').open(encoding='utf-8') as h: rows=list(csv.DictReader(h))
    for i,r in enumerate(rows):
        x=35+i*225; rect(s,x,110,205,300,'#f8f8f8','#111',1,8); text(s,x+16,140,r['milestone'],18,'bold'); text(s,x+16,165,r['evidence_family'],10,'bold'); text(s,x+16,202,'Period: '+r['period'],11); text(s,x+16,224,'Geographies: '+r['geographies'],11); text(s,x+16,246,'Observations: '+r['observations'],11); words=r['held_or_boundary'].split(); cur=[]; yy=282
        for word in words:
            if len(' '.join(cur+[word]))>28: text(s,x+16,yy,' '.join(cur),10); yy+=17; cur=[word]
            else: cur.append(word)
        if cur: text(s,x+16,yy,' '.join(cur),10)
        text(s,x+16,390,'context_only',11,'bold')
    svg_close(s,FIGURES/'F06-evidence-expansion.svg')

def build_figures(d):
    f01(d); f02(d); f03(d); f04(d); f05(d); f06(d)
