#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "data/manifests/milestone24_bps_stable32_probe.json"
COVERAGE = ROOT / "data/analysis/engine/bps_stable32_v1/m24-probe-coverage.csv"
PANEL_MANIFEST = ROOT / "data/processed/bps/comparative_stable32/bps-stable32.manifest.json"
OBS = ROOT / "data/processed/bps/comparative_stable32/bps-stable32-canonical-observations.csv"
PROV = ROOT / "data/processed/bps/comparative_stable32/bps-stable32-provenance.csv"
VERIFY = ROOT / "data/processed/bps/comparative_stable32/m24-probe-freeze-verification.json"
RAW_ROOT = ROOT / "data/processed/bps/comparative_stable32/source"
DESIGN = ROOT / "data/manifests/milestone24_design_gate.json"
SPEC = ROOT / "research/MILESTONE24_BPS_STABLE32_COMPARATOR_SPEC.md"
OUT = ROOT / "data/manifests/milestone24_bps_stable32_complete.json"

EXPECTED_SERIES = [
    "m5_poverty_march",
    "m5_gini_march",
    "m5_unemployment_august",
    "m5_underemployment_source_period",
    "m5_real_grdp_pc_adhk2010",
    "m5_neet_source_period",
]
EXPECTED_INDICATORS = [
    "poverty_rate",
    "gini_ratio",
    "unemployment_rate",
    "underemployment_rate",
    "real_grdp_per_capita",
    "neet_rate",
]
EXCLUDED_GEO_IDS = {"idn.91", "idn.92", "idn.94", "idn.95", "idn.96", "idn.97"}
YEARS = set(range(2018, 2026))


class M24FinalizationError(RuntimeError):
    pass


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise M24FinalizationError(message)


def finalize() -> dict[str, Any]:
    for path in (PROBE, COVERAGE, PANEL_MANIFEST, OBS, PROV, VERIFY, DESIGN, SPEC):
        require(path.exists(), f"missing M24 completion input: {path}")

    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    panel = json.loads(PANEL_MANIFEST.read_text(encoding="utf-8"))
    verification = json.loads(VERIFY.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    coverage = rows(COVERAGE)
    observations = rows(OBS)
    provenance = rows(PROV)

    require(probe.get("schema") == "ranah-observatory/milestone24-bps-stable32-probe/v1", "probe schema drift")
    require(probe.get("qualified_candidate_count") == 6, "M24 requires all six locked candidates qualified")
    require(probe.get("qualified_series_ids") == EXPECTED_SERIES, "M24 qualified series order/identity drift")
    require(probe.get("candidate_year_probe_count") == 48, "M24 probe count drift")
    require(probe.get("stable_geography_count") == 32, "M24 probe geography count drift")
    require(probe.get("selector_search_after_probe_performed") is False, "post-probe selector search detected")
    require(probe.get("imputation_performed") is False, "probe imputation detected")
    require(probe.get("geographic_backcasting_performed") is False, "probe geographic backcasting detected")
    require(probe.get("credential_persisted") is False, "probe claims credential persistence")

    require(len(coverage) == 48, "M24 coverage row count drift")
    require(all(row.get("probe_pass") == "True" for row in coverage), "at least one M24 candidate-year probe failed")
    require({int(row["year"]) for row in coverage} == YEARS, "M24 coverage years drift")
    require({row["series_id"] for row in coverage} == set(EXPECTED_SERIES), "M24 coverage series drift")
    require(all(int(row["stable32_selected_count"]) == 32 for row in coverage), "M24 stable32 selected count drift")

    require(panel.get("schema") == "ranah-observatory/bps-stable32-comparator/v1", "panel schema drift")
    require(panel.get("qualified_series_count") == 6, "panel qualified-series count drift")
    require(panel.get("qualified_series_ids") == EXPECTED_SERIES, "panel qualified-series identity drift")
    require(panel.get("indicator_ids") == EXPECTED_INDICATORS, "panel indicator identity drift")
    require(panel.get("observation_count") == 1536, "panel observation count drift")
    require(panel.get("provenance_count") == 48, "panel provenance count drift")
    require(panel.get("geography_count") == 32 and panel.get("year_count") == 8, "panel geography/year footprint drift")
    require(panel.get("imputation_performed") is False, "panel imputation detected")
    require(panel.get("geographic_backcasting_performed") is False, "panel backcasting detected")
    require(panel.get("province_district_model_pooling_performed") is False, "province/district pooling detected")
    require(panel.get("credential_persisted") is False, "panel claims credential persistence")

    require(len(observations) == 1536, "canonical observation file row count drift")
    keys = {(row["indicator_id"], row["geography_id"], int(row["year"])) for row in observations}
    require(len(keys) == 1536, "duplicate canonical stable32 observation keys")
    require({row["indicator_id"] for row in observations} == set(EXPECTED_INDICATORS), "canonical indicator set drift")
    require({int(row["year"]) for row in observations} == YEARS, "canonical years drift")
    require(len({row["geography_id"] for row in observations}) == 32, "canonical geography set is not 32")
    require(not ({row["geography_id"] for row in observations} & EXCLUDED_GEO_IDS), "excluded current Papua geography leaked into stable32 panel")
    require({row["geographic_backcasting_performed"] for row in observations} == {"False"}, "canonical backcasting flag drift")
    require({row["imputation_performed"] for row in observations} == {"False"}, "canonical imputation flag drift")
    require({row["comparability_regime"] for row in observations} == {"bps_stable32_province_2018_2025_v1"}, "comparability regime drift")

    require(len(provenance) == 48, "provenance row count drift")
    require(len({row["panel_provenance_id"] for row in provenance}) == 48, "duplicate provenance IDs")
    require({int(row["year"]) for row in provenance} == YEARS, "provenance year drift")
    require({row["source_series_id"] for row in provenance} == set(EXPECTED_SERIES), "provenance series drift")

    dynamic_snapshots = sorted(RAW_ROOT.glob("var-*/*.json"))
    dynamic_snapshots = [path for path in dynamic_snapshots if path.name.count("-") >= 2 and "periods" not in path.name and "manifest" not in path.name]
    require(len(dynamic_snapshots) == 48, f"expected 48 frozen dynamic snapshots, found {len(dynamic_snapshots)}")
    checksum_files = sorted(RAW_ROOT.glob("var-*/*.json.sha256"))
    dynamic_checksums = [path for path in checksum_files if "periods" not in path.name]
    require(len(dynamic_checksums) == 48, f"expected 48 dynamic snapshot checksums, found {len(dynamic_checksums)}")

    require(verification.get("schema") == "ranah-observatory/milestone24-probe-freeze-verification/v1", "freeze verification schema drift")
    require(verification.get("qualified_candidate_count") == 6, "freeze verification candidate count drift")
    require(verification.get("verified_snapshot_count") == 48, "freeze verification snapshot count drift")
    require(verification.get("semantic_probe_freeze_match") is True, "probe/freeze semantic mismatch")

    require(design.get("design_locked_before_probe") is True, "M24 design was not locked before probe")
    require(design.get("selector_search_after_probe_authorized") is False, "M24 design allows selector shopping")
    require(design.get("province_district_model_pooling_authorized") is False, "M24 design allows province/district pooling")

    result = {
        "schema": "ranah-observatory/milestone24-bps-stable32-complete/v1",
        "milestone": 24,
        "phase": "post_phase2_national_comparator_expansion",
        "criterion": "six exact-selector BPS series with complete stable-boundary 32-province coverage for 2018-2025",
        "milestone24_complete": True,
        "probe_complete": True,
        "panel_materialization_complete": True,
        "candidate_count": 6,
        "qualified_candidate_count": 6,
        "qualified_series_ids": EXPECTED_SERIES,
        "indicator_ids": EXPECTED_INDICATORS,
        "geography_level": "province",
        "geography_count": 32,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "observation_count": 1536,
        "provenance_count": 48,
        "frozen_dynamic_snapshot_count": 48,
        "probe_freeze_semantic_match": True,
        "excluded_current_papua_geography_count": 6,
        "geographic_backcasting_performed": False,
        "imputation_performed": False,
        "selector_search_after_probe_performed": False,
        "province_district_model_pooling_performed": False,
        "credential_persisted": False,
        "statistical_model_fit": False,
        "comparison_universe_materially_expanded": True,
        "district_city_training_sample_directly_expanded": False,
        "inputs": {
            "design_gate": {"path": DESIGN.relative_to(ROOT).as_posix(), "sha256": sha256(DESIGN)},
            "spec": {"path": SPEC.relative_to(ROOT).as_posix(), "sha256": sha256(SPEC)},
            "probe": {"path": PROBE.relative_to(ROOT).as_posix(), "sha256": sha256(PROBE)},
            "coverage": {"path": COVERAGE.relative_to(ROOT).as_posix(), "sha256": sha256(COVERAGE)},
            "panel_manifest": {"path": PANEL_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(PANEL_MANIFEST)},
            "probe_freeze_verification": {"path": VERIFY.relative_to(ROOT).as_posix(), "sha256": sha256(VERIFY)},
        },
        "outputs": {
            "canonical_observations": {"path": OBS.relative_to(ROOT).as_posix(), "sha256": sha256(OBS)},
            "provenance": {"path": PROV.relative_to(ROOT).as_posix(), "sha256": sha256(PROV)},
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    try:
        result = finalize()
    except (OSError, json.JSONDecodeError, M24FinalizationError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps({
        "milestone24_complete": result["milestone24_complete"],
        "qualified_candidate_count": result["qualified_candidate_count"],
        "observation_count": result["observation_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
