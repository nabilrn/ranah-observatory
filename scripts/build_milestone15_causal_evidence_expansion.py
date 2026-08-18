#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
M8 = ROOT / "data/manifests/milestone8_complete_audit.json"
M14 = ROOT / "data/manifests/milestone14_bottleneck_association.json"
M10 = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
OUT = ROOT / "data/analysis/engine/causal_evidence_v1/m15-causal-evidence-library.csv"
MANIFEST = ROOT / "data/manifests/milestone15_causal_evidence_expansion.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def main() -> int:
    m8 = json.loads(M8.read_text(encoding="utf-8"))
    m14 = json.loads(M14.read_text(encoding="utf-8"))
    panel = read_csv(M10)

    if m8.get("milestone8_complete") is not True or m8.get("quasi_causal_estimate_authorized") is not True:
        raise RuntimeError("M8 completed quasi-causal study is not authorized")
    signals = {(row["target_id"], row["candidate_id"]): row for row in m14.get("stable_association_signals", [])}
    rainfall_signal = signals.get(("unemployment_rate", "annual_rainfall"))
    if rainfall_signal is None:
        raise RuntimeError("M14 rainfall/unemployment stable association signal is missing")

    pre2020_years = sorted({int(row["analysis_year"]) for row in panel if int(row["analysis_year"]) < 2020 and row["unemployment_rate"] and row["poverty_rate"] and row["real_grdp_growth"]})
    if pre2020_years != [2018, 2019]:
        raise RuntimeError(f"unexpected M10 complete pre-COVID year set: {pre2020_years}")
    m14_discovery_years = list(range(2019, 2025))
    available_unemployment_years = sorted({int(row["analysis_year"]) for row in panel if row["unemployment_rate"]})
    new_post_discovery_years = [year for year in available_unemployment_years if year > max(m14_discovery_years)]

    rows: list[dict[str, Any]] = [
        {
            "entry_id": "m15_e1_earthquake_2009",
            "candidate_mechanism": "2009 earthquake physical shaking -> real GRDP trajectory",
            "design_family": "continuous_intensity_twfe_event_study",
            "evidence_origin": "milestone8",
            "entry_state": "completed_quasi_causal_study",
            "model_fit_authorized": True,
            "new_model_fit_in_m15": False,
            "completed_estimate_exists": True,
            "identification_gate_summary": "M8 internal identification diagnostics passed; completed estimate inherited without reinterpretation",
            "blocking_reasons": "",
            "result_summary": m8.get("claim_classification", ""),
            "causal_claim_authorized": False,
            "monetary_wasted_potential_claim": False,
        },
        {
            "entry_id": "m15_e2_rainfall_unemployment",
            "candidate_mechanism": "lagged annual rainfall shock -> unemployment",
            "design_family": "weather_shock_panel_candidate",
            "evidence_origin": "milestone14_hypothesis_generation",
            "entry_state": "not_identification_ready",
            "model_fit_authorized": False,
            "new_model_fit_in_m15": False,
            "completed_estimate_exists": False,
            "identification_gate_summary": "fails independent-confirmation gate because current outcome window substantially reuses M14 discovery years",
            "blocking_reasons": "same-data hypothesis selection; only one new annual unemployment year after M14 discovery; CHIRPS station validation pending; annual rainfall temporally coarse; spatially correlated weather shocks require dedicated inference",
            "result_summary": f"M14 discovery rank association={rainfall_signal['within_year_rank_association']}; permutation_p={rainfall_signal['geography_block_permutation_p_two_sided']}",
            "causal_claim_authorized": False,
            "monetary_wasted_potential_claim": False,
        },
        {
            "entry_id": "m15_e3_covid_structural_exposure",
            "candidate_mechanism": "pre-pandemic structural exposure -> differential COVID-era local economic outcomes",
            "design_family": "continuous_exposure_event_study_candidate",
            "evidence_origin": "m10_current_boundary_panel",
            "entry_state": "not_identification_ready",
            "model_fit_authorized": False,
            "new_model_fit_in_m15": False,
            "completed_estimate_exists": False,
            "identification_gate_summary": "fails minimum three-pre-event-year trend diagnostic rule",
            "blocking_reasons": f"only {len(pre2020_years)} complete pre-2020 annual outcome years available in M10 ({'|'.join(map(str, pre2020_years))})",
            "result_summary": "no event-study coefficient estimated",
            "causal_claim_authorized": False,
            "monetary_wasted_potential_claim": False,
        },
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)

    manifest = {
        "schema": "ranah-observatory/milestone15-causal-evidence-expansion/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 15,
        "criterion": "causal evidence library containing completed designs and fail-closed identification attempts",
        "entry_count": len(rows),
        "completed_quasi_causal_study_count": sum(row["entry_state"] == "completed_quasi_causal_study" for row in rows),
        "not_identification_ready_count": sum(row["entry_state"] == "not_identification_ready" for row in rows),
        "new_causal_model_fit_count": sum(row["new_model_fit_in_m15"] for row in rows),
        "rainfall_unemployment_discovery_years": m14_discovery_years,
        "available_unemployment_years": available_unemployment_years,
        "genuinely_new_post_m14_unemployment_years": new_post_discovery_years,
        "covid_complete_pre_event_years": pre2020_years,
        "minimum_covid_pre_event_years_required": 3,
        "same_data_m14_signal_upgraded_to_causal_model": False,
        "failed_identification_attempts_retained": True,
        "causal_claim_created_from_m14_association": False,
        "monetary_wasted_potential_estimated": False,
        "inputs": {
            "m8_complete_audit": {"path": str(M8.relative_to(ROOT)), "sha256": sha256(M8)},
            "m14_manifest": {"path": str(M14.relative_to(ROOT)), "sha256": sha256(M14)},
            "m10_panel": {"path": str(M10.relative_to(ROOT)), "sha256": sha256(M10)},
        },
        "output": {"path": str(OUT.relative_to(ROOT)), "sha256": sha256(OUT)},
        "milestone15_complete": True,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
