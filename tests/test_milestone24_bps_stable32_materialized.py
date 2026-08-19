from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "data/manifests/milestone24_bps_stable32_probe.json"
COVERAGE = ROOT / "data/analysis/engine/bps_stable32_v1/m24-probe-coverage.csv"
FINAL = ROOT / "data/manifests/milestone24_bps_stable32_complete.json"
PANEL_MANIFEST = ROOT / "data/processed/bps/comparative_stable32/bps-stable32.manifest.json"
OBS = ROOT / "data/processed/bps/comparative_stable32/bps-stable32-canonical-observations.csv"
PROV = ROOT / "data/processed/bps/comparative_stable32/bps-stable32-provenance.csv"
VERIFY = ROOT / "data/processed/bps/comparative_stable32/m24-probe-freeze-verification.json"
RAW_ROOT = ROOT / "data/processed/bps/comparative_stable32/source"

EXPECTED_SERIES = {
    "m5_poverty_march",
    "m5_gini_march",
    "m5_unemployment_august",
    "m5_underemployment_source_period",
    "m5_real_grdp_pc_adhk2010",
    "m5_neet_source_period",
}
EXPECTED_INDICATORS = {
    "poverty_rate",
    "gini_ratio",
    "unemployment_rate",
    "underemployment_rate",
    "real_grdp_per_capita",
    "neet_rate",
}
EXCLUDED_GEOS = {"idn.91", "idn.92", "idn.94", "idn.95", "idn.96", "idn.97"}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_probe_qualified_all_locked_series_without_selector_search() -> None:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    coverage = rows(COVERAGE)
    assert probe["qualified_candidate_count"] == 6
    assert set(probe["qualified_series_ids"]) == EXPECTED_SERIES
    assert probe["candidate_year_probe_count"] == 48
    assert probe["selector_search_after_probe_performed"] is False
    assert probe["imputation_performed"] is False
    assert probe["geographic_backcasting_performed"] is False
    assert probe["credential_persisted"] is False
    assert len(coverage) == 48
    assert all(row["probe_pass"] == "True" for row in coverage)
    assert all(int(row["stable32_selected_count"]) == 32 for row in coverage)
    assert {int(row["year"]) for row in coverage} == set(range(2018, 2026))


def test_canonical_panel_is_exact_6_by_32_by_8() -> None:
    observations = rows(OBS)
    assert len(observations) == 1536
    assert {row["indicator_id"] for row in observations} == EXPECTED_INDICATORS
    geographies = {row["geography_id"] for row in observations}
    assert len(geographies) == 32
    assert geographies.isdisjoint(EXCLUDED_GEOS)
    assert {int(row["year"]) for row in observations} == set(range(2018, 2026))
    keys = {(row["indicator_id"], row["geography_id"], row["year"]) for row in observations}
    assert len(keys) == 1536
    counts = Counter(row["indicator_id"] for row in observations)
    assert set(counts.values()) == {32 * 8}
    assert {row["comparability_regime"] for row in observations} == {"bps_stable32_province_2018_2025_v1"}
    assert {row["geographic_backcasting_performed"] for row in observations} == {"False"}
    assert {row["imputation_performed"] for row in observations} == {"False"}


def test_provenance_and_frozen_snapshot_footprint() -> None:
    provenance = rows(PROV)
    assert len(provenance) == 48
    assert len({row["panel_provenance_id"] for row in provenance}) == 48
    assert {row["source_series_id"] for row in provenance} == EXPECTED_SERIES
    assert {int(row["year"]) for row in provenance} == set(range(2018, 2026))
    dynamic = [
        path for path in RAW_ROOT.glob("var-*/*.json")
        if "periods" not in path.name and "manifest" not in path.name and path.name.count("-") >= 2
    ]
    checksums = [path for path in RAW_ROOT.glob("var-*/*.json.sha256") if "periods" not in path.name]
    assert len(dynamic) == 48
    assert len(checksums) == 48


def test_probe_freeze_semantics_match_exactly() -> None:
    verification = json.loads(VERIFY.read_text(encoding="utf-8"))
    assert verification["qualified_candidate_count"] == 6
    assert verification["verified_snapshot_count"] == 48
    assert verification["semantic_probe_freeze_match"] is True
    assert len(verification["verified"]) == 48


def test_panel_and_completion_manifests_fail_closed() -> None:
    panel = json.loads(PANEL_MANIFEST.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    assert panel["qualified_series_count"] == 6
    assert panel["observation_count"] == 1536
    assert panel["provenance_count"] == 48
    assert panel["geography_count"] == 32
    assert panel["year_count"] == 8
    assert panel["geographic_backcasting_performed"] is False
    assert panel["imputation_performed"] is False
    assert panel["province_district_model_pooling_performed"] is False
    assert panel["credential_persisted"] is False

    assert final["milestone24_complete"] is True
    assert final["probe_complete"] is True
    assert final["panel_materialization_complete"] is True
    assert final["qualified_candidate_count"] == 6
    assert final["observation_count"] == 1536
    assert final["frozen_dynamic_snapshot_count"] == 48
    assert final["probe_freeze_semantic_match"] is True
    assert final["statistical_model_fit"] is False
    assert final["comparison_universe_materially_expanded"] is True
    assert final["district_city_training_sample_directly_expanded"] is False
    assert final["geographic_backcasting_performed"] is False
    assert final["imputation_performed"] is False
    assert final["selector_search_after_probe_performed"] is False
    assert final["province_district_model_pooling_performed"] is False
    assert final["credential_persisted"] is False
