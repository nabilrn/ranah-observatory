#!/usr/bin/env python3
"""Validate the frozen BPS legacy variable-216 retention boundary."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_legacy_var216_retention_boundary.json"
SNAPSHOT = ROOT / "data/snapshots/bps/bps_construction_legacy_var216_2005_bounded_source_snapshot.json"


def validate() -> dict[str, object]:
    """Validate source-native 2005 identity, value, retention limits, and research gates."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-legacy-var216-retention-boundary/v1"
    assert snapshot["schema"] == "ranah-observatory/bps-legacy-var216-2005-bounded-source-snapshot/v1"
    assert snapshot["source_report_schema"] == "ranah-observatory/bps-legacy-construction-qualification-2005-surfaces/v4"
    assert snapshot["provenance"]["api_key_persisted"] is False

    source_var = snapshot["variable"]
    assert source_var["var_id"] == 216
    assert source_var["title"] == "Banyaknya Perusahaan Konstruksi"
    assert source_var["subject"] == "Konstruksi"
    assert "Direktori Perusahaan Konstruksi" in source_var["source_note"]

    source_periods = snapshot["periods"]
    assert len(source_periods) == 26
    assert source_periods[0] == {"th": "2025", "th_id": 125}
    assert source_periods[-1] == {"th": "2000", "th_id": 100}
    assert [row for row in source_periods if row["th"] == "2005"] == [{"th": "2005", "th_id": 105}]

    source_turvars = [(x["turvar"], x["turvar_id"]) for x in snapshot["derived_variables"]]
    assert source_turvars == [
        ("Kecil", 454),
        ("Menengah", 455),
        ("Besar", 456),
        ("Jumlah", 457),
    ]
    assert snapshot["derived_periods"] == [
        {"group_turth_id": 0, "name_group_turth": "Tahunan", "turth": "Tahun", "turth_id": 0}
    ]

    source_total = snapshot["dynamic_2005_total"]
    assert source_total["status"] == "OK"
    assert source_total["data-availability"] == "available"
    assert source_total["tahun"] == [{"label": "2005", "val": 105}]
    assert source_total["turtahun"] == [{"label": "Tahun", "val": 0}]
    assert source_total["turvar"] == [{"label": "Jumlah", "val": 457}]
    assert source_total["sumatera_barat_vervar"] == {"label": "SUMATERA BARAT", "val": 1300}
    assert source_total["sumatera_barat_datacontent_key"] == "13002164571050"
    assert source_total["sumatera_barat_value"] == 2435

    component_error_stages = [x["stage"] for x in snapshot["component_probe_errors"]]
    assert component_error_stages == [
        "dynamic_2005_turvar:454",
        "dynamic_2005_turvar:455",
        "dynamic_2005_turvar:456",
    ]
    assert all(
        x["error"] == "BPS dynamic data is not available for the requested selection"
        for x in snapshot["component_probe_errors"]
    )

    snapshot_csa = snapshot["current_csa"]
    assert snapshot_csa["status"] == "OK"
    assert snapshot_csa["data-availability"] == "available"
    assert snapshot_csa["available_years"] == [str(year) for year in range(2025, 2015, -1)]
    assert "2005" not in snapshot_csa["available_years"]

    legacy = manifest["legacy_variable"]
    assert legacy["domain"] == "0000"
    assert legacy["var_id"] == source_var["var_id"]
    assert legacy["title"] == source_var["title"]
    assert legacy["source"] == "Direktori Perusahaan Konstruksi"
    assert legacy["period_count"] == len(source_periods)
    assert legacy["period_start"] == {"th": "2000", "th_id": 100}
    assert legacy["period_end"] == {"th": "2025", "th_id": 125}
    assert legacy["target_period"] == {"th": "2005", "th_id": 105}
    assert legacy["derived_variable_group"] == "Jenis Golongan Perusahaan"
    assert [(x["label"], x["turvar_id"]) for x in legacy["derived_variables"]] == source_turvars

    total = manifest["legacy_2005_total"]
    assert total["var_id"] == 216
    assert total["turvar_id"] == 457
    assert total["th_id"] == source_total["tahun"][0]["val"]
    assert total["sumatera_barat"]["vervar_id"] == source_total["sumatera_barat_vervar"]["val"]
    assert total["sumatera_barat"]["datacontent_key"] == source_total["sumatera_barat_datacontent_key"]
    assert total["sumatera_barat"]["value"] == source_total["sumatera_barat_value"]

    components = manifest["legacy_2005_component_probe"]
    assert components["requested_turvar_ids"] == [454, 455, 456]
    assert components["component_values_recovered"] is False
    assert components["result"] == "data_not_available_under_tested_legacy_dynamic_contract"

    csa = manifest["current_csa_surface"]
    assert csa["encoded_id"] == "MjE2IzI="
    assert csa["decoded_id"] == "216#2"
    assert csa["model"] == "tablestatistic"
    assert csa["available"] is True
    assert csa["available_years"] == [str(year) for year in range(2016, 2026)]
    assert csa["year_2005_exposed"] is False
    assert set(csa["available_years"]) == set(snapshot_csa["available_years"])

    boundary = manifest["retention_boundary"]
    assert boundary["legacy_period_metadata_contains_2005"] is True
    assert boundary["legacy_2005_total_retrievable"] is True
    assert boundary["legacy_2005_small_medium_large_retrievable_under_tested_contract"] is False
    assert boundary["current_csa_full_size_surface_earliest_year"] == 2016
    assert boundary["current_csa_contains_2005"] is False
    assert boundary["classification"] == "legacy_total_survives_before_current_csa_component_retention_window"

    gates = manifest["research_gates"]
    assert gates["official_2005_sumbar_total_confirmed"] is True
    for key, value in gates.items():
        if key != "official_2005_sumbar_total_confirmed":
            assert value is False, key

    expected_artifact_sha = "d79f788355571fb7b6150ee01c6dc8e7e59cb5085bf208504d6863e3c399d3af"
    assert manifest["provenance"]["artifact_zip_sha256"] == expected_artifact_sha
    assert snapshot["provenance"]["artifact_zip_sha256"] == expected_artifact_sha
    assert manifest["provenance"]["api_key_persisted"] is False

    return {
        "source_snapshot_verified": True,
        "legacy_variable_verified": True,
        "legacy_period_start": legacy["period_start"]["th"],
        "legacy_period_end": legacy["period_end"]["th"],
        "source_native_2005_th_id": source_total["tahun"][0]["val"],
        "sumbar_2005_total": total["sumatera_barat"]["value"],
        "component_strata_2005_recovered": False,
        "current_csa_earliest_year": 2016,
        "historical_comparison_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
