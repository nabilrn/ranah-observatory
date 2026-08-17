#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEATURE_REGISTRY = ROOT / "data/registries/milestone7_expected_performance_features.csv"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
TARGET_PANEL = ROOT / "data/analysis/comparative/bps-current38-province-panel-wide.csv"
SNAPSHOT_ROOT = ROOT / "data/snapshots/bps/milestone7"
OUTPUT_ROOT = ROOT / "data/analysis/expected_performance"
LONG_OUT = OUTPUT_ROOT / "m7-feature-frame-long.csv"
WIDE_OUT = OUTPUT_ROOT / "m7-feature-frame-wide.csv"
MODEL_OUT = OUTPUT_ROOT / "m7-model-frame-2024.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone7_feature_frame.json"
YEAR = 2024


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_provinces() -> dict[str, dict[str, str]]:
    rows = read_csv(GEOGRAPHIES)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["geography_level"] != "province" or row["status"] != "current" or not row["bps_code"]:
            continue
        source_code = row["bps_code"].strip() + "00"
        if source_code in result:
            raise ValueError(f"duplicate current province BPS source code: {source_code}")
        result[source_code] = row
    if len(result) != 38:
        raise ValueError(f"expected 38 current provinces, got {len(result)}")
    if "1300" not in result or result["1300"]["geography_id"] != "idn.13":
        raise ValueError("current West Sumatra mapping is missing")
    return result


def numeric(raw: str, *, context: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"non-numeric value for {context}: {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite value for {context}")
    return value


def build() -> dict[str, Any]:
    features = read_csv(FEATURE_REGISTRY)
    if len(features) != 4:
        raise ValueError(f"Milestone 7 primary registry must contain exactly 4 predictors, got {len(features)}")
    if any(row["qualification_status"] != "qualified_for_freeze" for row in features):
        raise ValueError("all Milestone 7 predictors must be qualified_for_freeze")

    provinces = current_provinces()
    expected_codes = set(provinces)
    long_rows: list[dict[str, Any]] = []
    feature_values: dict[str, dict[str, float]] = {}
    source_hashes: dict[str, str] = {}

    for feature in features:
        var_id = feature["bps_var_id"].strip()
        source_path = SNAPSHOT_ROOT / f"var-{var_id}" / f"var-{var_id}-long.csv"
        if not source_path.exists():
            raise ValueError(f"missing frozen normalized source: {source_path.relative_to(ROOT)}")
        source_hashes[str(source_path.relative_to(ROOT))] = sha256(source_path)
        rows = read_csv(source_path)
        selected: dict[str, dict[str, str]] = {}
        for row in rows:
            code = row["bps_vervar_id"].strip()
            if code not in expected_codes:
                continue
            if row["bps_th_label"].strip() != feature["bps_period_label"].strip():
                continue
            if row["bps_turvar_id"].strip() != feature["bps_turvar_id"].strip():
                continue
            if row["bps_turth_id"].strip() != feature["bps_turth_id"].strip():
                continue
            if code in selected:
                raise ValueError(f"duplicate qualified row for {feature['feature_id']} geography {code}")
            selected[code] = row
        if set(selected) != expected_codes:
            missing = sorted(expected_codes - set(selected))
            extra = sorted(set(selected) - expected_codes)
            raise ValueError(f"{feature['feature_id']} does not have exact current-38 coverage; missing={missing}, extra={extra}")

        values: dict[str, float] = {}
        for code in sorted(expected_codes):
            source = selected[code]
            geo = provinces[code]
            value = numeric(source["value"], context=f"{feature['feature_id']} {code}")
            values[geo["geography_id"]] = value
            long_rows.append({
                "geography_id": geo["geography_id"],
                "geography_name": geo["canonical_name"],
                "bps_province_code": geo["bps_code"],
                "year": YEAR,
                "feature_id": feature["feature_id"],
                "feature_group": feature["feature_group"],
                "value": f"{value:.10g}",
                "unit": feature["canonical_unit"],
                "bps_var_id": var_id,
                "bps_turvar_id": feature["bps_turvar_id"],
                "bps_turth_id": feature["bps_turth_id"],
                "source_key": source["source_key"],
            })
        feature_values[feature["feature_id"]] = values

    feature_ids = [row["feature_id"] for row in features]
    wide_rows: list[dict[str, Any]] = []
    by_geography_id = {row["geography_id"]: row for row in provinces.values()}
    for geography_id in sorted(by_geography_id):
        geo = by_geography_id[geography_id]
        row: dict[str, Any] = {
            "geography_id": geography_id,
            "geography_name": geo["canonical_name"],
            "bps_province_code": geo["bps_code"],
            "year": YEAR,
        }
        for feature_id in feature_ids:
            row[feature_id] = f"{feature_values[feature_id][geography_id]:.10g}"
        wide_rows.append(row)

    target_rows = [row for row in read_csv(TARGET_PANEL) if row["year"] == str(YEAR)]
    if len(target_rows) != 38:
        raise ValueError(f"expected 38 target rows for 2024, got {len(target_rows)}")
    targets = {row["geography_id"]: numeric(row["real_grdp_per_capita"], context=row["geography_id"]) for row in target_rows}
    if set(targets) != set(by_geography_id):
        raise ValueError("target geography footprint does not match feature footprint")

    model_rows: list[dict[str, Any]] = []
    for row in wide_rows:
        geography_id = str(row["geography_id"])
        target = targets[geography_id]
        if target <= 0:
            raise ValueError(f"non-positive real GRDP per capita target for {geography_id}")
        model_row = dict(row)
        model_row["real_grdp_per_capita"] = f"{target:.10g}"
        model_row["log_real_grdp_per_capita"] = f"{math.log(target):.12g}"
        model_rows.append(model_row)

    long_rows.sort(key=lambda row: (str(row["geography_id"]), str(row["feature_id"])))
    write_csv(LONG_OUT, [
        "geography_id", "geography_name", "bps_province_code", "year", "feature_id", "feature_group", "value", "unit",
        "bps_var_id", "bps_turvar_id", "bps_turth_id", "source_key",
    ], long_rows)
    wide_fields = ["geography_id", "geography_name", "bps_province_code", "year", *feature_ids]
    write_csv(WIDE_OUT, wide_fields, wide_rows)
    write_csv(MODEL_OUT, [*wide_fields, "real_grdp_per_capita", "log_real_grdp_per_capita"], model_rows)

    output_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in (LONG_OUT, WIDE_OUT, MODEL_OUT)}
    manifest = {
        "schema": "ranah-observatory/milestone7-feature-frame/v1",
        "year": YEAR,
        "geography_regime": "bps_current_38_province_2024plus",
        "province_filter_contract": "current province registry mapped to BPS source vervar as bps_code + '00'",
        "feature_ids": feature_ids,
        "feature_count": len(feature_ids),
        "geography_count": 38,
        "observation_count": len(long_rows),
        "model_row_count": len(model_rows),
        "west_sumatra_present": any(row["geography_id"] == "idn.13" for row in model_rows),
        "target": "real_grdp_per_capita",
        "target_unit": "million_rupiah_per_person_constant_2010",
        "target_source": str(TARGET_PANEL.relative_to(ROOT)),
        "source_hashes": source_hashes,
        "output_hashes": output_hashes,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    manifest = build()
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
