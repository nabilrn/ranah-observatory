#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "milestone48_bnpb_annual_republication_lineage.json"
REGISTRY = ROOT / "data" / "registries" / "bnpb_annual_portal_republication_lineage.csv"
M42 = ROOT / "data" / "manifests" / "milestone42_bnpb_historical_source_native_staging.json"
M43 = ROOT / "data" / "manifests" / "milestone43_bnpb_historical_semantics_geography_gate.json"
M47 = ROOT / "data" / "manifests" / "milestone47_bnpb_impact_overlap_eligibility.json"

EXPECTED = {
    2010: ("a7e098a3-dace-459f-9bc2-bfc42bbeafc2", "1HuADXppt6XVdfCt8FZ4Cobw1uAl8QO9F", "1grzKv-JYqXh8iLRXwztFOtSQL3vqiG0G", 28112, "bc720b2e9eff0d6fc246a6df98b862b9047d3dc35b754c0b707f6e5d91918a32"),
    2011: ("4040fe7c-530b-49e8-8dec-09cec50f319c", "1AsFCoVXTcx_gKbLeWSTXZdvPyzS_b58y", "1aiyS3evqAIdS_qvAIMXkPcT6ZHsYJcEJ", 27987, "92cf736ef5c128d00ed6c7d37223f62ff3d0654d3bd36392d1b679495c626e1a"),
    2012: ("e734e68d-c526-46d7-9601-755d9e14ff82", "1iAhPmnbQ6ymdRnUqGUuUhApmymWHjfg3", "1bH89AFGZ3-lSFyhM0uD-D58MhCF_Xq_F", 28150, "f6b8388cba8cd8e471bb0703226a7f02abbeba5a83944fbf53909bc2ec46b081"),
    2013: ("9076aeb3-ff85-4591-8f2b-82e049075901", "1P6aH3hmMQ8K3A6J0ABtT-uM4bfLeYFdr", "16xTOHKIcvm6-35MouBc5SAhWzHCFMfAJ", 28150, "3e541817cdcc82a4fbc49fbcb1352b37663b1d571a70fb730ef9345f47fb4d20"),
    2014: ("89599698-64c7-4a3d-9aba-0ff8bd68df49", "1NsN2l293L8vyxPq0wxRbmvRyqBQvVq-Z", "1iX-fioBCs0ucwYWdJcPauWrBBNPfeT0g", 28030, "c8396605b8a8fde621f77cc64e4caa1aa519bd2083f6dd336ce830f0b02a627f"),
    2015: ("2fe6e372-0af6-413b-9175-9e3a896ebca9", "1iJ3br2AAf2y92CrODRa_q_5YzevneOa6", "1vRof8V29l81XhKfA0ERodnV8AzBChwCe", 28032, "91f9479e3d55765a317763148f8169e3d8d11a7c3916eb56e663d5a50f1c9342"),
    2016: ("dd3bc505-6f45-40b5-873d-caa82ea4bf10", "19q72ocka_qm4cA0VYp0fFKYL4cgh4dLS", "14TV7RFzAJwFHYTzbkfOEvFcYbSbueNJY", 28312, "7d1ae5ac65aa2dd9e3e18ba2b058a2db9b8e504fb213990a4f108950553c5ee4"),
    2017: ("282bd95e-fe10-4a90-afa7-69cea5fb02c8", "1tuz5clbQ3r65MSj25SPuNLzqszlrkMzb", "1qRNz3QLxm0UERt1L_qiZNcP25tSZ25YN", 28058, "de218de3da3c16db20442a5e9fbedac1f6b6906128160b43c3400bf5a63f266d"),
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def validate() -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    rows = _read_csv(REGISTRY)
    m42 = _read_json(M42)
    m43 = _read_json(M43)
    m47 = _read_json(M47)

    assert manifest["milestone"] == 48
    assert manifest["depends_on"] == [42, 43, 47]
    assert manifest["review_scope"]["years"] == [2010, 2017]
    assert manifest["review_scope"]["portal_dataset_pages_reviewed"] == 8
    assert manifest["review_scope"]["portal_declared_source"] == "https://dibi.bnpb.go.id"

    assert len(rows) == 8
    by_year = {int(row["year"]): row for row in rows}
    assert set(by_year) == set(EXPECTED)

    m42_by_year = {int(item["year"]): item for item in m42["workbooks"]}
    for year, (dataset_id, folder_id, file_id, expected_bytes, expected_sha256) in EXPECTED.items():
        row = by_year[year]
        assert row["portal_dataset_id"] == dataset_id
        assert row["portal_dataset_url"] == f"https://data.bnpb.go.id/dataset/jumlah-kejadian-dan-dampak-bencana-tahun-{year}"
        assert row["portal_source"] == "https://dibi.bnpb.go.id"
        assert row["portal_geography_claim"] == "kabupaten_kota"
        assert row["drive_folder_id"] == folder_id
        assert row["sumbar_file_name"] == f"stat_by_wil_13_{year}.xlsx"
        assert row["sumbar_drive_file_id"] == file_id
        assert row["m42_locator_id"] == file_id
        assert int(row["observed_bytes"]) == expected_bytes
        assert int(row["m42_bytes"]) == expected_bytes
        assert row["observed_sha256"] == expected_sha256
        assert row["m42_sha256"] == expected_sha256
        assert row["drive_locator_match"] == "true"
        assert row["byte_size_match"] == "true"
        assert row["sha256_match"] == "true"
        assert row["evidence_independence_state"] == "same_source_object_byte_identical_republication"
        assert row["independent_crosscheck_eligible"] == "false"

        m42_row = m42_by_year[year]
        assert m42_row["locator_kind"] == "google_drive_file_id"
        assert m42_row["locator_id"] == file_id
        assert m42_row["bytes"] == expected_bytes
        assert m42_row["sha256"] == expected_sha256

    result = manifest["result"]
    assert result["annual_dataset_pages_reviewed"] == 8
    assert result["annual_pages_claiming_district_city_grain"] == 8
    assert result["annual_pages_declaring_dibi_source"] == 8
    assert result["sumbar_workbooks_located"] == 8
    assert result["exact_drive_locator_matches_to_m42"] == 8
    assert result["exact_byte_size_matches_to_m42"] == 8
    assert result["exact_sha256_matches_to_m42"] == 8
    assert result["same_grain_portal_counterpart_found"] is True
    assert result["independent_same_grain_counterpart_found"] is False
    assert result["new_independent_source_object_count"] == 0
    assert result["portal_family_may_count_as_independent_crosscheck"] is False
    assert result["value_level_reconciliation_as_independent_crosscheck_authorized"] is False
    assert result["canonical_historical_impact_promotion_authorized"] is False

    qualification = manifest["qualification"]
    assert qualification["sumbar_source_object_identity_confirmed_all_years"] is True
    assert qualification["raw_byte_identity_reconfirmed_all_years"] is True
    assert qualification["evidence_independence_gate_frozen"] is True
    assert qualification["current_boundary_comparability_promoted"] is False
    assert qualification["promotion_gate_fail_closed"] is True

    assert m42["qualification"]["canonical_historical_panel_authorized"] is False
    assert m43["qualification"]["canonical_historical_panel_promotion_authorized"] is False
    assert m47["result"]["district_overlap_eligible_metric_count"] == 0
    assert m47["result"]["canonical_district_impact_promotion_authorized"] is False

    return {
        "schema": "ranah-observatory/milestone48-bnpb-annual-republication-lineage-audit/v1",
        "milestone": 48,
        "years_verified": len(rows),
        "exact_locator_matches": 8,
        "exact_sha256_matches": 8,
        "independent_same_grain_counterpart_found": False,
        "canonical_historical_impact_promotion_authorized": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M48 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
