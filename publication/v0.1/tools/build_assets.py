#!/usr/bin/env python3
from __future__ import annotations
import json, shutil
from common import ROOT, OUT, TABLES, FIGURES, read_csv, read_json, sha256
from tables import build_tables
from figures import build_figures

SOURCES=[
'publication/v0.1/claim-ledger.csv','data/analysis/engine/final_synthesis_v1/m18-evidence-nodes.csv','data/analysis/engine/final_synthesis_v1/m18-evidence-edges.csv','data/manifests/milestone10_analytical_panel.json','data/manifests/milestone11_expected_performance_v2.json','data/manifests/milestone12_attainable_frontier.json','data/manifests/milestone13_development_gap_decomposition.json','data/manifests/milestone19_dynamic_forecast_engine.json','data/analysis/engine/dynamic_forecast_v1/m19-target-summary.csv','data/manifests/milestone20_historical_climate_trend.json','data/analysis/engine/historical_climate_trend_v1/m20-regional-annual-mean.csv','data/analysis/engine/historical_climate_trend_v1/m20-regional-trend.csv','data/manifests/milestone21_climate_regime_shift.json','data/analysis/engine/climate_regime_shift_v1/m21-full-series-regime.csv','data/analysis/engine/climate_regime_shift_v1/m21-rolling-backtest.csv','data/manifests/milestone22_hierarchical_socioeconomic_trajectory.json','data/analysis/engine/hierarchical_trajectory_v1/m22-indicator-summary.csv','data/analysis/engine/hierarchical_trajectory_v1/m22-geography-trajectories.csv','data/manifests/milestone24_bps_stable32_complete.json','data/manifests/milestone25_djpk_public_finance_complete.json','data/manifests/milestone26_disaster_risk_chain_complete.json','data/manifests/milestone27_completion.json','data/manifests/milestone28_completion.json']

def load():
    return {'claims':read_csv(SOURCES[0]),'nodes':read_csv(SOURCES[1]),'edges':read_csv(SOURCES[2]),'m10':read_json(SOURCES[3]),'m11':read_json(SOURCES[4]),'m12':read_json(SOURCES[5]),'m13':read_json(SOURCES[6]),'m19':read_json(SOURCES[7]),'m19_summary':read_csv(SOURCES[8]),'m20':read_json(SOURCES[9]),'m20_annual':read_csv(SOURCES[10]),'m20_trend':read_csv(SOURCES[11]),'m21':read_json(SOURCES[12]),'m21_regime':read_csv(SOURCES[13]),'m21_rolling':read_csv(SOURCES[14]),'m22':read_json(SOURCES[15]),'m22_summary':read_csv(SOURCES[16]),'m22_geo':read_csv(SOURCES[17]),'m24':read_json(SOURCES[18]),'m25':read_json(SOURCES[19]),'m26':read_json(SOURCES[20]),'m27':read_json(SOURCES[21]),'m28':read_json(SOURCES[22])}

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    TABLES.mkdir(parents=True); FIGURES.mkdir(parents=True)
    data=load(); build_tables(data); build_figures(data)
    outputs=sorted(p for p in OUT.rglob('*') if p.is_file())
    manifest={'schema':'ranah-observatory/publication-v0.1-render-manifest/v1','release':'v0.1','builder':'publication/v0.1/tools/build_assets.py','new_source_acquisition':False,'new_statistical_or_ml_model_fit':False,'table_count':7,'figure_count':6,'source_sha256':{r:sha256(ROOT/r) for r in SOURCES},'output_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in outputs}}
    (OUT/'render-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print({'tables':7,'figures':6,'rendered_root':'publication/v0.1/rendered'})

if __name__=='__main__': main()
