#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CHIRPS = ROOT / "data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv"
CHIRPS_MANIFEST = ROOT / "data/processed/climate/rainfall/chirps-rainfall-materialization.manifest.json"
BNPB = ROOT / "data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv"
BNPB_MANIFEST = ROOT / "data/processed/bnpb/disaster/bnpb-disaster-panel.manifest.json"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
DESIGN_GATE = ROOT / "data/manifests/milestone9_design_gate.json"
OUT_DIR = ROOT / "data/analysis/climate_disaster"
FRAME = OUT_DIR / "m9-hydroclimate-2024-geography-frame.csv"
CORRELATIONS = OUT_DIR / "m9-hydroclimate-2024-correlations.csv"
LOO = OUT_DIR / "m9-hydroclimate-2024-leave-one-out.csv"
MANIFEST = ROOT / "data/manifests/milestone9_hydroclimate_case_study.json"

EXPECTED_YEARS = list(range(1981, 2026))
BASELINE_YEARS = list(range(1981, 2024))
STUDY_YEAR = 2024
EXPECTED_INDICATORS = {"flood_events", "landslide_events"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("correlation requires equal vectors with at least two values")
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    denom = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denom == 0:
        return 0.0
    return sum(a * b for a, b in zip(dx, dy)) / denom


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        average = ((i + 1) + j) / 2.0
        for k in range(i, j):
            result[indexed[k][0]] = average
        i = j
    return result


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(average_ranks(x), average_ranks(y))


def descending_average_ranks(values: list[float]) -> list[float]:
    return average_ranks([-v for v in values])


def main() -> int:
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    if gate.get("schema") != "ranah-observatory/milestone9-design-gate/v1":
        raise RuntimeError("Milestone 9 design gate schema drift")
    if gate.get("association_computed") is not False or gate.get("milestone9_complete") is not False:
        raise RuntimeError("Milestone 9 pre-analysis gate no longer records a pre-computation state")
    if gate.get("study_year") != STUDY_YEAR or gate.get("baseline_start_year") != 1981 or gate.get("baseline_end_year") != 2023:
        raise RuntimeError("Milestone 9 locked year/baseline contract drift")

    chirps_manifest = json.loads(CHIRPS_MANIFEST.read_text(encoding="utf-8"))
    if chirps_manifest.get("schema") != "ranah-observatory/chirps-annual-rainfall/v1":
        raise RuntimeError("Unexpected CHIRPS materialization schema")
    if chirps_manifest.get("observation_count") != 855 or chirps_manifest.get("geography_count") != 19:
        raise RuntimeError("CHIRPS materialization footprint drift")
    if chirps_manifest.get("first_year") != 1981 or chirps_manifest.get("last_year") != 2025:
        raise RuntimeError("CHIRPS year coverage drift")
    if chirps_manifest.get("claim_type") != "model_estimate" or chirps_manifest.get("eligible_as_observed_station_data") is not False:
        raise RuntimeError("CHIRPS evidence-class drift")
    if chirps_manifest.get("historical_boundary_continuity_claimed") is not False:
        raise RuntimeError("CHIRPS must not claim historical boundary continuity")
    if chirps_manifest.get("independent_station_validation") != "pending":
        raise RuntimeError("Milestone 9 expects station validation to remain pending")
    if sha256(CHIRPS) != chirps_manifest.get("observations_sha256"):
        raise RuntimeError("CHIRPS observations SHA-256 drift")

    bnpb_manifest = json.loads(BNPB_MANIFEST.read_text(encoding="utf-8"))
    if bnpb_manifest.get("schema") != "ranah-observatory/bnpb-disaster-panel/v1":
        raise RuntimeError("Unexpected BNPB disaster-panel schema")
    if bnpb_manifest.get("canonical_observation_count") != 38 or bnpb_manifest.get("mapped_geography_count") != 19:
        raise RuntimeError("BNPB canonical footprint drift")
    if set(bnpb_manifest.get("canonical_indicators", [])) != EXPECTED_INDICATORS:
        raise RuntimeError("BNPB indicator set drift")
    if bnpb_manifest.get("official_crosscheck") != "passed":
        raise RuntimeError("BNPB independent official cross-check no longer passes")
    if sha256(BNPB) != bnpb_manifest.get("canonical_observations_sha256"):
        raise RuntimeError("BNPB observations SHA-256 drift")

    names = {
        row["geography_id"]: row["canonical_name"]
        for row in read_csv(GEOGRAPHIES)
        if row.get("parent_geography_id") == "idn.13" and row.get("geography_level") in {"regency", "city"}
    }

    climate: dict[str, dict[int, float]] = {}
    for row in read_csv(CHIRPS):
        if row.get("indicator_id") != "annual_rainfall":
            raise RuntimeError("Unexpected CHIRPS indicator")
        if row.get("claim_type") != "model_estimate" or row.get("comparable").lower() != "true":
            raise RuntimeError("CHIRPS row claim/comparability drift")
        gid = row["geography_id"]
        year = int(row["time_start"][:4])
        value = float(row["value_numeric"])
        if not math.isfinite(value) or value < 0:
            raise RuntimeError(f"Invalid CHIRPS rainfall for {gid} {year}")
        if year in climate.setdefault(gid, {}):
            raise RuntimeError(f"Duplicate CHIRPS semantic key {gid} {year}")
        climate[gid][year] = value

    if len(climate) != 19:
        raise RuntimeError(f"Expected 19 CHIRPS geographies, got {len(climate)}")
    for gid, yearly in climate.items():
        if sorted(yearly) != EXPECTED_YEARS:
            raise RuntimeError(f"CHIRPS year footprint drift for {gid}")

    disaster: dict[str, dict[str, int]] = {}
    seen_disaster_keys: set[tuple[str, str]] = set()
    for row in read_csv(BNPB):
        gid = row["geography_id"]
        indicator = row["indicator_id"]
        if indicator not in EXPECTED_INDICATORS:
            raise RuntimeError(f"Unexpected BNPB indicator {indicator}")
        if row.get("time_start") != "2024-01-01" or row.get("time_end") != "2024-12-31":
            raise RuntimeError("BNPB study-year footprint drift")
        if row.get("claim_type") != "observed":
            raise RuntimeError("BNPB event count must remain observed recorded-event evidence")
        key = (gid, indicator)
        if key in seen_disaster_keys:
            raise RuntimeError(f"Duplicate BNPB semantic key {key}")
        seen_disaster_keys.add(key)
        value_float = float(row["value_numeric"])
        if not math.isfinite(value_float) or value_float < 0 or not value_float.is_integer():
            raise RuntimeError(f"Invalid BNPB event count {key}: {value_float}")
        disaster.setdefault(gid, {})[indicator] = int(value_float)

    if len(disaster) != 19 or len(seen_disaster_keys) != 38:
        raise RuntimeError("BNPB exact 19x2 footprint lost")
    if set(disaster) != set(climate):
        raise RuntimeError("CHIRPS and BNPB geography sets do not match exactly")
    if set(disaster) != set(names):
        missing = sorted(set(disaster) ^ set(names))
        raise RuntimeError(f"Canonical geography-name footprint mismatch: {missing}")

    frame_rows: list[dict[str, object]] = []
    for gid in sorted(climate):
        baseline = [climate[gid][year] for year in BASELINE_YEARS]
        if len(baseline) != 43:
            raise RuntimeError(f"Expected 43 baseline years for {gid}")
        mean = statistics.fmean(baseline)
        sd = statistics.stdev(baseline)
        if not math.isfinite(sd) or sd <= 0:
            raise RuntimeError(f"Invalid baseline standard deviation for {gid}")
        rain2024 = climate[gid][STUDY_YEAR]
        anomaly = rain2024 - mean
        pct = 100.0 * anomaly / mean
        z = anomaly / sd
        percentile = 100.0 * sum(value <= rain2024 for value in baseline) / len(baseline)
        floods = disaster[gid]["flood_events"]
        landslides = disaster[gid]["landslide_events"]
        frame_rows.append(
            {
                "geography_id": gid,
                "geography_name": names[gid],
                "study_year": STUDY_YEAR,
                "rainfall_2024_mm": rain2024,
                "baseline_1981_2023_mean_mm": mean,
                "baseline_1981_2023_sample_sd_mm": sd,
                "rainfall_anomaly_mm": anomaly,
                "rainfall_anomaly_percent": pct,
                "rainfall_z_2024": z,
                "rainfall_baseline_percentile": percentile,
                "flood_events": floods,
                "landslide_events": landslides,
                "hydroclimate_event_count": floods + landslides,
            }
        )

    rank_columns = {
        "rainfall_z_rank_desc": [float(row["rainfall_z_2024"]) for row in frame_rows],
        "flood_events_rank_desc": [float(row["flood_events"]) for row in frame_rows],
        "landslide_events_rank_desc": [float(row["landslide_events"]) for row in frame_rows],
        "hydroclimate_event_count_rank_desc": [float(row["hydroclimate_event_count"]) for row in frame_rows],
    }
    for column, values in rank_columns.items():
        ranks = descending_average_ranks(values)
        for row, rank in zip(frame_rows, ranks):
            row[column] = rank

    frame_fields = list(frame_rows[0].keys())
    write_csv(FRAME, frame_fields, frame_rows)

    outcome_columns = ["flood_events", "landslide_events", "hydroclimate_event_count"]
    climate_columns = ["rainfall_z_2024", "rainfall_2024_mm"]
    correlation_rows: list[dict[str, object]] = []
    for climate_column in climate_columns:
        x = [float(row[climate_column]) for row in frame_rows]
        for outcome in outcome_columns:
            y = [float(row[outcome]) for row in frame_rows]
            correlation_rows.append(
                {
                    "climate_metric": climate_column,
                    "disaster_metric": outcome,
                    "pearson": pearson(x, y),
                    "spearman": spearman(x, y),
                    "geography_count": len(frame_rows),
                    "claim_scope": "descriptive_spatial_association_not_causal",
                }
            )
    write_csv(
        CORRELATIONS,
        ["climate_metric", "disaster_metric", "pearson", "spearman", "geography_count", "claim_scope"],
        correlation_rows,
    )

    loo_rows: list[dict[str, object]] = []
    for outcome in outcome_columns:
        for excluded in frame_rows:
            kept = [row for row in frame_rows if row["geography_id"] != excluded["geography_id"]]
            x = [float(row["rainfall_z_2024"]) for row in kept]
            y = [float(row[outcome]) for row in kept]
            loo_rows.append(
                {
                    "disaster_metric": outcome,
                    "excluded_geography_id": excluded["geography_id"],
                    "excluded_geography_name": excluded["geography_name"],
                    "remaining_geography_count": len(kept),
                    "spearman": spearman(x, y),
                    "pearson": pearson(x, y),
                }
            )
    write_csv(
        LOO,
        ["disaster_metric", "excluded_geography_id", "excluded_geography_name", "remaining_geography_count", "spearman", "pearson"],
        loo_rows,
    )

    primary_correlations = {
        row["disaster_metric"]: {"pearson": row["pearson"], "spearman": row["spearman"]}
        for row in correlation_rows
        if row["climate_metric"] == "rainfall_z_2024"
    }
    raw_sensitivity = {
        row["disaster_metric"]: {"pearson": row["pearson"], "spearman": row["spearman"]}
        for row in correlation_rows
        if row["climate_metric"] == "rainfall_2024_mm"
    }
    loo_summary: dict[str, dict[str, float]] = {}
    for outcome in outcome_columns:
        values = [float(row["spearman"]) for row in loo_rows if row["disaster_metric"] == outcome]
        loo_summary[outcome] = {"spearman_min": min(values), "spearman_max": max(values)}

    wettest = max(frame_rows, key=lambda row: float(row["rainfall_z_2024"]))
    driest = min(frame_rows, key=lambda row: float(row["rainfall_z_2024"]))
    max_flood = max(float(row["flood_events"]) for row in frame_rows)
    max_landslide = max(float(row["landslide_events"]) for row in frame_rows)

    manifest = {
        "schema": "ranah-observatory/milestone9-hydroclimate-case-study/v1",
        "criterion": gate["criterion"],
        "case_study": gate["case_study"],
        "study_year": STUDY_YEAR,
        "study_year_selected_before_association_inspection": True,
        "geography_count": 19,
        "baseline_years": [1981, 2023],
        "baseline_year_count": 43,
        "climate_claim_type": "model_estimate",
        "climate_spatial_frame": chirps_manifest.get("spatial_frame"),
        "independent_station_validation": chirps_manifest.get("independent_station_validation"),
        "station_observation_equivalence": False,
        "disaster_claim_type": "observed_recorded_event_count",
        "bnpb_official_crosscheck": bnpb_manifest.get("official_crosscheck"),
        "zero_event_geographies_retained": True,
        "frame_row_count": len(frame_rows),
        "correlation_row_count": len(correlation_rows),
        "leave_one_out_row_count": len(loo_rows),
        "primary_correlations": primary_correlations,
        "raw_rainfall_sensitivity_correlations": raw_sensitivity,
        "leave_one_out_primary_spearman_ranges": loo_summary,
        "positive_rainfall_anomaly_geography_count": sum(float(row["rainfall_anomaly_mm"]) > 0 for row in frame_rows),
        "wettest_relative_geography": {"geography_id": wettest["geography_id"], "geography_name": wettest["geography_name"], "rainfall_z_2024": wettest["rainfall_z_2024"]},
        "driest_relative_geography": {"geography_id": driest["geography_id"], "geography_name": driest["geography_name"], "rainfall_z_2024": driest["rainfall_z_2024"]},
        "max_recorded_flood_events": max_flood,
        "max_recorded_landslide_events": max_landslide,
        "causal_attribution_performed": False,
        "climate_change_attribution_performed": False,
        "daily_rainfall_claim_performed": False,
        "annual_rainfall_temporal_resolution_limitation": True,
        "inputs": {
            "chirps_observations": {"path": str(CHIRPS.relative_to(ROOT)), "sha256": sha256(CHIRPS)},
            "chirps_manifest": {"path": str(CHIRPS_MANIFEST.relative_to(ROOT)), "sha256": sha256(CHIRPS_MANIFEST)},
            "bnpb_observations": {"path": str(BNPB.relative_to(ROOT)), "sha256": sha256(BNPB)},
            "bnpb_manifest": {"path": str(BNPB_MANIFEST.relative_to(ROOT)), "sha256": sha256(BNPB_MANIFEST)},
            "design_gate": {"path": str(DESIGN_GATE.relative_to(ROOT)), "sha256": sha256(DESIGN_GATE)},
        },
        "outputs": {
            "geography_frame": {"path": str(FRAME.relative_to(ROOT)), "sha256": sha256(FRAME)},
            "correlations": {"path": str(CORRELATIONS.relative_to(ROOT)), "sha256": sha256(CORRELATIONS)},
            "leave_one_out": {"path": str(LOO.relative_to(ROOT)), "sha256": sha256(LOO)},
        },
        "claim_classification": "descriptive_climate_disaster_spatial_case_study",
        "milestone9_complete": True,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
