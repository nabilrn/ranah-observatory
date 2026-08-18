from __future__ import annotations

from scripts.audit_milestone8_complete import audit


def test_milestone8_case_study_is_complete() -> None:
    report = audit()
    assert report["errors"] == []
    assert report["milestone8_complete"] is True


def test_milestone8_required_evidence_gates_are_closed() -> None:
    report = audit()
    assert report["source_anomalies_resolved"] is True
    assert report["overlap_2009_reconciled"] is True
    assert report["core_identification_diagnostics_passed"] is True
    assert report["housing_damage_validation_complete"] is True
    assert report["grdp_growth_robustness_complete"] is True
    assert report["small_cluster_inference_implemented"] is True


def test_milestone8_claim_strength_remains_narrow() -> None:
    report = audit()
    assert report["quasi_causal_effect_estimated"] is True
    assert report["quasi_causal_estimate_authorized"] is True
    assert report["directional_nonzero_effect_claim_authorized"] is False
    assert report["causal_claim_authorized"] is False
    assert (
        report["claim_classification"]
        == "quasi_causal_estimate_no_statistically_robust_differential_effect_detected"
    )
