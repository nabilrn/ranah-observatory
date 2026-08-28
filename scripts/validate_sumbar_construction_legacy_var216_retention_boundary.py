#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_legacy_var216_retention_boundary.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "ranah-observatory/bps-construction-legacy-var216-retention-boundary/v1"

    legacy = manifest["legacy_variable"]
    assert legacy["domain"] == "0000"
    assert legacy["var_id"] == 216
    assert legacy["title"] == "Banyaknya Perusahaan Konstruksi"
    assert legacy["source"] == "Direktori Perusahaan Konstruksi"
    assert legacy["period_count"] == 26
    assert legacy["period_start"] == {"th": "2000", "th_id": 100}
    assert legacy["period_end"] == {"th": "2025", "th_id": 125}
    assert legacy["target_period"] == {"th": "2005", "th_id": 105}
    assert legacy["derived_variable_group"] == "Jenis Golongan Perusahaan"
    assert [(x["label"], x["turvar_id"]) for x in legacy["derived_variables"]] == [
        ("Kecil", 454), ("Menengah", 455), ("Besar", 456), ("Jumlah", 457)
    ]

    total = manifest["legacy_2005_total"]
    assert total["var_id"] == 216
    assert total["turvar_id"] == 457
    assert total["th_id"] == 105
    assert total["sumatera_barat"]["vervar_id"] == 1300
    assert total["sumatera_barat"]["datacontent_key"] == "13002164571050"
    assert total["sumatera_barat"]["value"] == 2435

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

    assert manifest["provenance"]["artifact_zip_sha256"] == "d79f788355571fb7b6150ee01c6dc8e7e59cb5085bf208504d6863e3c399d3af"
    assert manifest["provenance"]["api_key_persisted"] is False

    return {
        "legacy_variable_verified": True,
        "legacy_period_start": legacy["period_start"]["th"],
        "legacy_period_end": legacy["period_end"]["th"],
        "sumbar_2005_total": total["sumatera_barat"]["value"],
        "component_strata_2005_recovered": False,
        "current_csa_earliest_year": 2016,
        "historical_comparison_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
