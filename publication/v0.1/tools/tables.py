from common import TABLES, fmt, write_csv

def build_tables(d):
    write_csv(TABLES/'T01-evidence-claim-architecture.csv',
      ['stage_order','node_id','upstream','claim_class','evidence_strength','status','causal_claim_authorized','uncertainty_or_limit'], d['nodes'])

    m10,m28=d['m10'],d['m28']
    rows=[
      {'panel':'M10 base panel','geographies':m10['geography_count'],'period':f"{m10['start_year']}-{m10['end_year']}",'indicators':m10['indicator_count'],'present_observations':m10['long_observation_count'],'missing_cells':m10['missing_indicator_cells'],'complete_indicators':len(m10['complete_2018_2025_indicator_ids']),'interpretation':'Frozen analytical panel; explicit missingness; no imputation.'},
      {'panel':'M28 panel v2','geographies':m28['geography_count'],'period':'2018-2025','indicators':m28['panel_v2']['combined_indicator_count'],'present_observations':m28['panel_v2']['combined_observation_count'],'missing_cells':m28['panel_v2']['missing_indicator_cells'],'complete_indicators':m28['panel_v2']['complete_2018_2025_indicator_count'],'interpretation':'Context expansion only; M10 rows preserved; source methodology states retained.'}]
    write_csv(TABLES/'T02-modern-panel-evidence-expansion.csv',list(rows[0]),rows)

    m11,m12,m13=d['m11'],d['m12'],d['m13']; rows=[]
    for target in m11['target_ids']:
      x=m11['target_metrics'][target]
      rows.append({'target_id':target,'m11_benchmark_qualified':x['benchmark_qualified'],'m11_model_rmse':fmt(x['model_rmse'],6),'m11_naive_rmse':fmt(x['naive_rmse'],6),'m11_model_mae':fmt(x['model_mae'],6),'m11_naive_mae':fmt(x['naive_mae'],6),'m12_primary_reference':m12['district_primary_method'],'m12_alternative_reference':m12['district_alternative_method'],'m13_gap_rows_total':m13['gap_panel_row_count'],'m13_authorized_rows_total':m13['gap_interpretation_authorized_row_count'],'m13_blocked_rows_total':m13['gap_interpretation_blocked_row_count'],'m13_frontier_sign_disagreements_total':m13['frontier_gap_sign_disagreement_count']})
    write_csv(TABLES/'T03-expected-reference-gap-qualification.csv',list(rows[0]),rows)

    fields=['indicator_id','hierarchical_trajectory_qualified','hierarchical_rmse','hierarchical_mae','independent_ols_rmse','independent_ols_mae','rmse_improvement_vs_independent_ols','mae_improvement_vs_independent_ols','shared_slope_per_year','persistent_increase_count','persistent_decrease_count','robust_trajectory_count']
    write_csv(TABLES/'T04-socioeconomic-trajectory-qualification.csv',fields,[{k:r[k] for k in fields} for r in d['m22_summary']])

    rows=[]
    for r in d['m19_summary']:
      rows.append({'analysis':'M19 one-year-ahead forecast','target_or_series':r['target_id'],'qualification_rule':r['qualification_rule'],'qualified':r['forecast_qualified'],'primary_diagnostic':f"dynamic RMSE {fmt(r['dynamic_ridge_rmse'],6)} vs persistence {fmt(r['persistence_rmse'],6)}; dynamic MAE {fmt(r['dynamic_ridge_mae'],6)} vs persistence {fmt(r['persistence_mae'],6)}",'public_state':'forecast blocked'})
    m20,m21=d['m20'],d['m21']
    rows += [
      {'analysis':'M20 robust monotonic rainfall trend','target_or_series':'19 current-boundary geographies','qualification_rule':'adjusted trend + Holm + split-direction + leave-one-year-out stability','qualified':False,'primary_diagnostic':f"{m20['robust_monotonic_geography_count']}/{m20['geography_count']} geographies qualified",'public_state':m20['regional_robust_monotonic_classification']},
      {'analysis':'M21 single-break rainfall regime','target_or_series':'regional unweighted mean rainfall','qualification_rule':'rolling-origin predictive performance + breakpoint stability','qualified':m21['public_claim_authorized'],'primary_diagnostic':f"full break {m21['full_series_selected_break_year']}; predictive pass={m21['predictive_qualification_pass']}; stability pass={m21['rolling_break_stability_pass']}",'public_state':m21['classification']}]
    write_csv(TABLES/'T05-predictive-climate-negative-results.csv',list(rows[0]),rows)

    m24,m25,m26,m27=d['m24'],d['m25'],d['m26'],d['m27']
    rows=[
      {'milestone':'M24','evidence_family':'BPS stable-32 province comparator','period':'2018-2025','geographies':m24['geography_count'],'observations':m24['observation_count'],'held_or_boundary':f"{m24['excluded_current_papua_geography_count']} current Papua-region provinces excluded; no backcasting",'claim_state':'context_only'},
      {'milestone':'M25','evidence_family':'DJPK annual-final public finance','period':'2018-2025','geographies':m25['geography_count'],'observations':m25['observation_count'],'held_or_boundary':'central_transfer_revenue held; no derived ratios','claim_state':'context_only'},
      {'milestone':'M26','evidence_family':'disaster-risk component evidence','period':'mixed component vintages','geographies':m26['geography_count'],'observations':m26['materialized_component_observation_count'],'held_or_boundary':'observed impact and hazard/vulnerability numeric promotion held; no composite risk','claim_state':'context_only'},
      {'milestone':'M27','evidence_family':'BKPM quarterly investment history','period':f"{m27['inventory_period_start']}-{m27['inventory_period_end']}",'geographies':m27['canonical_geography_count'],'observations':m27['materialized_geography_quarter_status_observation_count'],'held_or_boundary':'2024-Q1 held; PMA/PMDN and source currencies remain separate','claim_state':'context_only'},
      {'milestone':'M28','evidence_family':'broader BPS outcome/infrastructure/health/demographic panel','period':'2018-2025','geographies':m28['geography_count'],'observations':m28['stage2_numeric_evidence']['promoted_observation_count'],'held_or_boundary':'electricity-access candidate held at structure stage; methodology-specific missingness retained','claim_state':'context_only'}]
    write_csv(TABLES/'T06-post-M18-evidence-expansion.csv',list(rows[0]),rows)

    rows=[{'claim_id':r['claim_id'],'statement':r['statement'],'authorized_interpretation':r['authorized_interpretation'],'prohibited_upgrade':r['prohibited_upgrade']} for r in d['claims'] if r['state']=='blocked']
    write_csv(TABLES/'T07-blocked-claims-upgrade-boundaries.csv',list(rows[0]),rows)
