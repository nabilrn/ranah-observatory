from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_financing_revision_audit_1998_2003.json"
REVISION_CSV = ROOT / "data" / "processed" / "bps" / "historical_construction_financing_revision_1998_2003.csv"
COMPOSITION_2000 = ROOT / "data" / "processed" / "bps" / "historical_construction_financing_2000_source_native.csv"

MEASURES = {
    "total_construction_completed": "14",
    "financed_by_central_government_budget": "15.1",
    "financed_by_local_government_budget": "15.2",
    "financed_by_foreign_loan": "15.3",
    "financed_by_state_enterprises": "15.4",
    "financed_by_other_sources": "15.5",
}
COMPONENTS = set(MEASURES) - {"total_construction_completed"}
PRIMARY_YEARS = {1998, 1999, 2000, 2001, 2002}
CROSSCHECK_YEARS = {1999, 2000, 2001, 2002, 2003}
OVERLAP_YEARS = PRIMARY_YEARS & CROSSCHECK_YEARS
EXPECTED_PRIMARY_RESIDUALS = {1998: 0, 1999: 3, 2000: 0, 2001: -1, 2002: -1}
EXPECTED_CROSSCHECK_RESIDUALS = {1999: 0, 2000: 0, 2001: -1, 2002: 0, 2003: 0}
EXPECTED_REVISED_CELLS = {
    ("total_construction_completed", 2002): -11,
    ("financed_by_central_government_budget", 1999): -3,
    ("financed_by_central_government_budget", 2002): -6,
    ("financed_by_local_government_budget", 2002): -1,
    ("financed_by_foreign_loan", 2002): -2,
    ("financed_by_state_enterprises", 2002): -1,
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _value(mapping: dict[str, int], year: int) -> int:
    return int(mapping[str(year)])


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = _read_rows(REVISION_CSV)
    composition_rows = _read_rows(COMPOSITION_2000)

    assert manifest["schema"] == "ranah-observatory/bps-construction-financing-revision-audit-1998-2003/v1"
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["canonical_historical_geography_id"] == "idn.13.h1958"
    assert manifest["source_unit_label"] == "000 Rupiah"
    assert manifest["price_semantics"] == "nominal current rupiah as published"

    releases = manifest["releases"]
    primary_release = releases["construction_statistics_2002"]
    crosscheck_release = releases["construction_statistics_2003"]
    assert primary_release["publication_title"] == "Statistik Konstruksi 2002"
    assert primary_release["publication_number"] == "05230.0307"
    assert primary_release["release_date"] == "2003-09-15"
    assert set(primary_release["coverage_years"]) == PRIMARY_YEARS
    assert primary_release["historical_header_marker"] is None
    assert primary_release["table_note"] == "Angka Sementara/Preliminary Figures"
    assert crosscheck_release["publication_title"] == "Statistik Konstruksi 2003"
    assert crosscheck_release["publication_number"] == "05230.0407"
    assert crosscheck_release["release_date"] == "2004-07-19"
    assert set(crosscheck_release["coverage_years"]) == CROSSCHECK_YEARS
    assert crosscheck_release["historical_header_marker"].startswith("R on 1999")
    assert crosscheck_release["historical_header_marker_interpretation"].startswith("not asserted")
    assert crosscheck_release["table_note"] == "Angka Sementara/Preliminary Figures"

    values = manifest["values_thousand_rupiah"]
    assert set(values) == set(MEASURES)
    for measure_id, table_number in MEASURES.items():
        block = values[measure_id]
        assert block["table_number"] == table_number
        assert set(map(int, block["construction_statistics_2002"])) == PRIMARY_YEARS
        assert set(map(int, block["construction_statistics_2003"])) == CROSSCHECK_YEARS

    deltas = manifest["release_revision_deltas_crosscheck_minus_primary_thousand_rupiah"]
    assert set(map(int, deltas)) == OVERLAP_YEARS
    revised_cells: dict[tuple[str, int], int] = {}
    for year in sorted(OVERLAP_YEARS):
        year_deltas = deltas[str(year)]
        assert set(year_deltas) == set(MEASURES)
        for measure_id in MEASURES:
            primary = _value(values[measure_id]["construction_statistics_2002"], year)
            crosscheck = _value(values[measure_id]["construction_statistics_2003"], year)
            expected_delta = crosscheck - primary
            assert year_deltas[measure_id] == expected_delta
            if expected_delta:
                revised_cells[(measure_id, year)] = expected_delta
    assert revised_cells == EXPECTED_REVISED_CELLS

    reconciliation = manifest["within_release_financing_reconciliation"]
    for release_key, years, expected_residuals in (
        ("construction_statistics_2002", PRIMARY_YEARS, EXPECTED_PRIMARY_RESIDUALS),
        ("construction_statistics_2003", CROSSCHECK_YEARS, EXPECTED_CROSSCHECK_RESIDUALS),
    ):
        release_reconciliation = reconciliation[release_key]
        assert set(map(int, release_reconciliation)) == years
        for year in sorted(years):
            component_sum = sum(_value(values[measure_id][release_key], year) for measure_id in COMPONENTS)
            total = _value(values["total_construction_completed"][release_key], year)
            residual = component_sum - total
            assert residual == expected_residuals[year]
            declared = release_reconciliation[str(year)]
            assert declared["component_sum_minus_reported_total_thousand_rupiah"] == residual
            assert declared["exact"] is (residual == 0)

    findings = manifest["revision_findings"]
    assert findings["year_2000_all_six_measures_stable"] is True
    assert findings["year_1999_later_release_resolves_component_total_residual"] is True
    assert findings["year_2002_later_release_resolves_component_total_residual"] is True
    assert findings["year_2001_one_thousand_rupiah_residual_persists"] is True
    assert findings["silent_latest_value_overwrite_authorized"] is False
    assert "retain release-specific values" in findings["preferred_storage_rule"]

    semantic = manifest["semantic_boundary"]
    assert semantic["source_native_longitudinal_review_authorized"] is True
    assert semantic["canonical_fiscal_account_mapping_authorized"] is False
    assert semantic["panel_v3_integration_authorized"] is False
    assert semantic["deflation_authorized"] is False
    assert semantic["interpolation_authorized"] is False
    assert semantic["causal_claim_authorized"] is False

    boundary = manifest["source_boundary"]
    assert boundary["pdf_sha256_available_in_repository"] is False
    assert boundary["allstats_text_treated_as_artifact_sha_equivalent"] is False

    assert len(rows) == 36
    by_key = {(row["source_measure_id"], int(row["year"])): row for row in rows}
    assert len(by_key) == len(rows)
    assert set(measure for measure, _ in by_key) == set(MEASURES)
    assert set(year for _, year in by_key) == set(range(1998, 2004))

    for measure_id, table_number in MEASURES.items():
        for year in range(1998, 2004):
            row = by_key[(measure_id, year)]
            assert row["source_geography_name"] == "Sumatera Barat"
            assert row["canonical_historical_geography_id"] == "idn.13.h1958"
            assert row["source_table_number"] == table_number
            assert row["canonical_mapping_status"] == "not_authorized"

            primary_csv = row["construction_statistics_2002_value_thousand_rupiah"]
            crosscheck_csv = row["construction_statistics_2003_value_thousand_rupiah"]
            delta_csv = row["revision_delta_crosscheck_minus_primary_thousand_rupiah"]

            if year in PRIMARY_YEARS:
                assert int(primary_csv) == _value(values[measure_id]["construction_statistics_2002"], year)
            else:
                assert primary_csv == ""
            if year in CROSSCHECK_YEARS:
                assert int(crosscheck_csv) == _value(values[measure_id]["construction_statistics_2003"], year)
            else:
                assert crosscheck_csv == ""

            if year in OVERLAP_YEARS:
                delta = _value(values[measure_id]["construction_statistics_2003"], year) - _value(
                    values[measure_id]["construction_statistics_2002"], year
                )
                assert int(delta_csv) == delta
                expected_status = "exact_match" if delta == 0 else "revised"
                assert row["comparison_status"] == expected_status
            elif year == 1998:
                assert delta_csv == ""
                assert row["comparison_status"] == "primary_only"
            else:
                assert year == 2003
                assert delta_csv == ""
                assert row["comparison_status"] == "crosscheck_only"

    composition_2000 = {row["source_measure_id"]: int(row["raw_value_thousand_rupiah"]) for row in composition_rows}
    assert set(composition_2000) == set(MEASURES)
    for measure_id in MEASURES:
        primary_2000 = _value(values[measure_id]["construction_statistics_2002"], 2000)
        crosscheck_2000 = _value(values[measure_id]["construction_statistics_2003"], 2000)
        assert primary_2000 == crosscheck_2000 == composition_2000[measure_id]

    return {
        "rows": len(rows),
        "measures": len(MEASURES),
        "years": 6,
        "overlap_years": len(OVERLAP_YEARS),
        "revised_cells": len(revised_cells),
        "year_2000_stable_measures": 6,
        "primary_exact_reconciliation_years": sum(v == 0 for v in EXPECTED_PRIMARY_RESIDUALS.values()),
        "crosscheck_exact_reconciliation_years": sum(v == 0 for v in EXPECTED_CROSSCHECK_RESIDUALS.values()),
        "silent_latest_value_overwrite_authorized": False,
        "canonical_fiscal_mapping_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
