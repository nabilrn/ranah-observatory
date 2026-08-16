#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS = ROOT / "data" / "analysis" / "comparative"
DEFAULT_SERIES = ROOT / "data" / "registries" / "bps_comparative_panel_series.csv"
DEFAULT_GEOS = ROOT / "data" / "registries" / "geographies.csv"
DEFAULT_REPORT = ROOT / "data" / "manifests" / "milestone5_comparative_panel_audit.json"
REGIME = "bps_current_38_province_2024plus"
YEARS = {2024, 2025}
INDICATORS = {
    "poverty_rate",
    "gini_ratio",
    "unemployment_rate",
    "underemployment_rate",
    "real_grdp_per_capita",
    "neet_rate",
}
EXPECTED_LONG_ROWS = 38 * len(YEARS) * len(INDICATORS)
EXPECTED_WIDE_ROWS = 38 * len(YEARS)
EXPECTED_PROVENANCE_ROWS = len(YEARS) * len(INDICATORS)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_result_sha(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"snapshot result is not an object: {path}")
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def province_registry(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    provinces = {
        row["geography_id"]: row
        for row in rows
        if row.get("status") == "current"
        and row.get("geography_level") == "province"
        and row.get("parent_geography_id") == "idn"
    }
    if len(provinces) != 38:
        raise ValueError(f"expected 38 current provinces in geography registry; got {len(provinces)}")
    return provinces


def audit(analysis_dir: Path, series_path: Path, geography_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    long_path = analysis_dir / "bps-current38-province-panel-long.csv"
    wide_path = analysis_dir / "bps-current38-province-panel-wide.csv"
    prov_path = analysis_dir / "bps-current38-province-panel-provenance.csv"
    manifest_path = analysis_dir / "bps-current38-province-panel.manifest.json"
    for path in (long_path, wide_path, prov_path, manifest_path):
        if not path.exists():
            errors.append(f"missing required panel artifact: {path.relative_to(ROOT).as_posix()}")
    if errors:
        return {"schema": "ranah-observatory/milestone5-comparative-panel-audit/v1", "errors": errors, "milestone5_complete": False}

    provinces = province_registry(geography_path)
    series = read_csv(series_path)
    series_by_id = {row["series_id"]: row for row in series}
    if len(series_by_id) != 6 or {row["indicator_id"] for row in series} != INDICATORS:
        errors.append("series registry is not the exact six-indicator Milestone 5 contract")
    if any(row.get("qualification_status") != "qualified_current38" for row in series):
        errors.append("not every comparative series is qualified_current38")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("comparability_regime") != REGIME:
        errors.append("manifest comparability regime drift")
    if set(manifest.get("years", [])) != YEARS:
        errors.append("manifest year scope drift")
    if set(manifest.get("indicator_ids", [])) != INDICATORS:
        errors.append("manifest indicator scope drift")
    if int(manifest.get("geography_count", -1)) != 38:
        errors.append("manifest geography count is not 38")

    provenance = read_csv(prov_path)
    provenance_ids: set[str] = set()
    provenance_by_series_year: set[tuple[str, int]] = set()
    for row in provenance:
        pid = row.get("panel_provenance_id", "")
        if not pid:
            errors.append("empty panel_provenance_id")
            continue
        if pid in provenance_ids:
            errors.append(f"duplicate panel_provenance_id {pid}")
        provenance_ids.add(pid)
        series_id = row.get("source_series_id", "")
        try:
            year = int(row.get("year", ""))
        except ValueError:
            errors.append(f"invalid provenance year for {pid}")
            continue
        provenance_by_series_year.add((series_id, year))
        if series_id not in series_by_id:
            errors.append(f"unknown source_series_id in provenance: {series_id}")
        if year not in YEARS:
            errors.append(f"unexpected provenance year {year}")
        if row.get("comparability_regime") != REGIME:
            errors.append(f"provenance regime drift for {pid}")
        snapshot_rel = row.get("source_snapshot", "")
        if not snapshot_rel:
            errors.append(f"missing source_snapshot for {pid}")
            continue
        snapshot_path = ROOT / snapshot_rel
        if not snapshot_path.exists():
            errors.append(f"unresolved source snapshot for {pid}: {snapshot_rel}")
            continue
        actual_sha = sha256_file(snapshot_path)
        if actual_sha != row.get("source_snapshot_sha256"):
            errors.append(f"snapshot byte checksum mismatch for {pid}")
        try:
            actual_semantic = semantic_result_sha(snapshot_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(str(exc))
        else:
            if actual_semantic != row.get("semantic_result_sha256"):
                errors.append(f"snapshot semantic checksum mismatch for {pid}")
        manifest_rel = row.get("source_manifest", "")
        if not manifest_rel or not (ROOT / manifest_rel).exists():
            errors.append(f"unresolved source manifest for {pid}: {manifest_rel}")

    if len(provenance) != EXPECTED_PROVENANCE_ROWS:
        errors.append(f"expected {EXPECTED_PROVENANCE_ROWS} provenance rows; got {len(provenance)}")
    expected_series_years = {(row["series_id"], year) for row in series for year in YEARS}
    if provenance_by_series_year != expected_series_years:
        errors.append("provenance does not cover every series-year exactly")

    long_rows = read_csv(long_path)
    observation_ids: set[str] = set()
    panel_keys: set[tuple[str, str, int]] = set()
    coverage: dict[tuple[str, int], set[str]] = defaultdict(set)
    values: dict[tuple[str, int, str], float] = {}
    units = {row["indicator_id"]: row["canonical_unit"] for row in series}
    series_for_indicator = {row["indicator_id"]: row["series_id"] for row in series}

    for row in long_rows:
        oid = row.get("panel_observation_id", "")
        if not oid:
            errors.append("empty panel_observation_id")
        elif oid in observation_ids:
            errors.append(f"duplicate panel_observation_id {oid}")
        observation_ids.add(oid)
        indicator_id = row.get("indicator_id", "")
        geography_id = row.get("geography_id", "")
        try:
            year = int(row.get("year", ""))
        except ValueError:
            errors.append(f"invalid panel year for {oid}")
            continue
        key = (indicator_id, geography_id, year)
        if key in panel_keys:
            errors.append(f"duplicate panel semantic key {key}")
        panel_keys.add(key)
        if indicator_id not in INDICATORS:
            errors.append(f"unexpected indicator {indicator_id}")
        if geography_id not in provinces:
            errors.append(f"unexpected geography {geography_id}")
        if year not in YEARS:
            errors.append(f"unexpected year {year}")
        if row.get("comparability_regime") != REGIME:
            errors.append(f"comparability regime drift for {oid}")
        if row.get("unit") != units.get(indicator_id):
            errors.append(f"unit mismatch for {oid}")
        if row.get("source_series_id") != series_for_indicator.get(indicator_id):
            errors.append(f"source series mismatch for {oid}")
        if row.get("panel_provenance_id") not in provenance_ids:
            errors.append(f"unresolved panel provenance for {oid}")
        geo = provinces.get(geography_id)
        if geo:
            if row.get("bps_province_code") != geo.get("bps_code"):
                errors.append(f"BPS province code mismatch for {oid}")
            if row.get("geography_name") != geo.get("canonical_name"):
                errors.append(f"geography name mismatch for {oid}")
        try:
            value = float(row.get("value_numeric", ""))
        except ValueError:
            errors.append(f"non-numeric panel value for {oid}")
            continue
        if not math.isfinite(value):
            errors.append(f"non-finite panel value for {oid}")
        coverage[(indicator_id, year)].add(geography_id)
        values[(geography_id, year, indicator_id)] = value

    if len(long_rows) != EXPECTED_LONG_ROWS:
        errors.append(f"expected {EXPECTED_LONG_ROWS} long rows; got {len(long_rows)}")
    for indicator_id in INDICATORS:
        for year in YEARS:
            if coverage[(indicator_id, year)] != set(provinces):
                errors.append(f"coverage mismatch for {indicator_id} {year}")

    wide_rows = read_csv(wide_path)
    wide_keys: set[tuple[str, int]] = set()
    for row in wide_rows:
        geography_id = row.get("geography_id", "")
        try:
            year = int(row.get("year", ""))
        except ValueError:
            errors.append("invalid wide panel year")
            continue
        key = (geography_id, year)
        if key in wide_keys:
            errors.append(f"duplicate wide panel key {key}")
        wide_keys.add(key)
        if geography_id not in provinces or year not in YEARS:
            errors.append(f"unexpected wide panel key {key}")
            continue
        for indicator_id in INDICATORS:
            try:
                wide_value = float(row.get(indicator_id, ""))
            except ValueError:
                errors.append(f"missing/non-numeric wide value for {key} {indicator_id}")
                continue
            long_value = values.get((geography_id, year, indicator_id))
            if long_value is None or not math.isclose(wide_value, long_value, rel_tol=0.0, abs_tol=1e-12):
                errors.append(f"wide/long mismatch for {key} {indicator_id}")
    if len(wide_rows) != EXPECTED_WIDE_ROWS:
        errors.append(f"expected {EXPECTED_WIDE_ROWS} wide rows; got {len(wide_rows)}")

    west_sumatra_complete = all((indicator_id, "idn.13", year) in panel_keys for indicator_id in INDICATORS for year in YEARS)
    if not west_sumatra_complete:
        errors.append("West Sumatra does not have complete six-indicator 2024-2025 coverage")

    complete = not errors
    return {
        "schema": "ranah-observatory/milestone5-comparative-panel-audit/v1",
        "criterion": "a comparative Indonesian panel where feasible",
        "comparability_regime": REGIME,
        "geography_count": len(provinces),
        "years": sorted(YEARS),
        "indicator_ids": sorted(INDICATORS),
        "indicator_count": len(INDICATORS),
        "panel_observation_count": len(long_rows),
        "panel_provenance_count": len(provenance),
        "wide_row_count": len(wide_rows),
        "west_sumatra_complete": west_sumatra_complete,
        "errors": errors,
        "milestone5_complete": complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the frozen Milestone 5 Indonesian comparative panel.")
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--series-registry", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--geography-registry", type=Path, default=DEFAULT_GEOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(args.analysis_dir, args.series_registry, args.geography_registry)
    except (OSError, csv.Error, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.require_complete and not report["milestone5_complete"]:
        return 3
    return 0 if report["milestone5_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
