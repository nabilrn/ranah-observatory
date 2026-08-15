#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERIES = ROOT / "data" / "registries" / "bps_expansion_series.csv"
DEFAULT_QUALIFICATIONS = ROOT / "data" / "registries" / "bps_expansion_qualification.csv"

OBS_FIELDS = [
    "observation_id", "indicator_id", "geography_id", "time_start", "time_end", "frequency",
    "value_numeric", "unit", "claim_type", "provenance_id", "suppressed", "comparable",
    "methodology_version", "price_basis", "notes",
]
PROV_FIELDS = [
    "provenance_id", "source_id", "artifact_locator", "retrieved_at", "source_release",
    "checksum_sha256", "parser_revision", "transform_revision", "extraction_method", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _period_bounds(year: int, rule: str) -> tuple[str, str]:
    months = {
        "calendar_month_august": 8,
        "calendar_month_march": 3,
        "calendar_month_september": 9,
    }
    if rule == "calendar_year":
        return f"{year:04d}-01-01", f"{year:04d}-12-31"
    month = months.get(rule)
    if month is None:
        raise ValueError(f"unsupported expansion reference_period_rule {rule!r}")
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"


def _transform_value(row: dict[str, str]) -> float:
    try:
        raw = float(row["raw_value"])
    except ValueError as exc:
        raise ValueError(f"{row['expansion_row_id']}: non-numeric raw_value") from exc
    transform = row["transform"]
    if transform == "identity":
        return raw
    if transform == "quintal_per_hectare_to_tonnes_per_hectare":
        return raw * 0.1
    if transform == "share_percent":
        try:
            denominator = float(row["denominator_raw_value"])
        except ValueError as exc:
            raise ValueError(f"{row['expansion_row_id']}: invalid share denominator") from exc
        if denominator <= 0:
            raise ValueError(f"{row['expansion_row_id']}: share denominator must be positive")
        value = 100.0 * raw / denominator
        if not 0 <= value <= 100:
            raise ValueError(f"{row['expansion_row_id']}: derived share outside 0-100: {value}")
        return value
    raise ValueError(f"{row['expansion_row_id']}: unsupported transform {transform!r}")


def _provenance_id(row: dict[str, str]) -> str:
    token = "|".join(
        [row["source_id"], row["domain"], row["bps_var_id"], row["bps_th_id"], row["source_snapshot_sha256"]]
    )
    return "bpsexpprov_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _observation_id(row: dict[str, str]) -> str:
    token = "|".join([row["expansion_series_id"], row["canonical_geography_id"], row["bps_th_id"]])
    return "bpsexpobs_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _comparable(series_id: str, year: int) -> str:
    if series_id == "underemployment_regency":
        return ""
    if series_id == "rice_yield_ksa" and year == 2025:
        return ""
    return "true"


def _price_basis(series_id: str) -> str:
    if series_id in {"agriculture_share_adhb", "manufacturing_share_adhb"}:
        return "current_prices_series_2010"
    return ""


def build_canonical(
    source_panel: Path,
    series_registry: Path = DEFAULT_SERIES,
    qualification_registry: Path = DEFAULT_QUALIFICATIONS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    source_rows = read_csv(source_panel)
    series = {row["expansion_series_id"]: row for row in read_csv(series_registry)}
    qualifications = {row["qualification_id"]: row for row in read_csv(qualification_registry)}

    observations: list[dict[str, Any]] = []
    provenance: dict[str, dict[str, Any]] = {}
    held: list[dict[str, str]] = []
    series_counts: dict[str, int] = {}
    seen_obs: set[str] = set()

    for row in source_rows:
        config = series.get(row["expansion_series_id"])
        if config is None:
            raise ValueError(f"unknown expansion series {row['expansion_series_id']}")
        qualification = qualifications.get(config["qualification_id"])
        if qualification is None:
            raise ValueError(f"missing qualification {config['qualification_id']}")

        if config["canonical_scope"] == "province_only" and row["canonical_geography_id"] != "idn.13":
            held.append(row)
            continue
        if qualification["decision"] not in {"canonical_ready", "canonical_ready_province_only"}:
            held.append(row)
            continue

        year = int(row["bps_th_label"])
        value = _transform_value(row)
        start, end = _period_bounds(year, qualification["reference_period_rule"])
        prov_id = _provenance_id(row)
        if prov_id not in provenance:
            provenance[prov_id] = {
                "provenance_id": prov_id,
                "source_id": row["source_id"],
                "artifact_locator": f"bps-webapi://domain/{row['domain']}/var/{row['bps_var_id']}/th/{row['bps_th_id']}",
                "retrieved_at": row["retrieved_at_utc"],
                "source_release": row["bps_last_update"],
                "checksum_sha256": row["source_snapshot_sha256"],
                "parser_revision": "normalize_bps_dynamic:v2",
                "transform_revision": "build_bps_expansion_canonical:v1",
                "extraction_method": "api" if row["claim_type"] == "observed" else "api+deterministic_transform",
                "notes": (
                    f"snapshot={row['source_snapshot']}; var={row['bps_var_id']} {row['bps_var_label']}; "
                    f"period={row['bps_th_id']}:{row['bps_th_label']}"
                ),
            }

        obs_id = _observation_id(row)
        if obs_id in seen_obs:
            raise ValueError(f"duplicate expansion canonical observation id {obs_id}")
        seen_obs.add(obs_id)
        notes = [
            f"qualification_id={config['qualification_id']}",
            f"source_universe={qualification['source_universe']}",
            f"source_geography={row['source_geography_dimension']}:{row['source_geography_id']}:{row['source_geography_label']}",
            f"geography_mapping={row['geography_mapping_status']}",
            f"source_selector=vervar:{row['selected_vervar_id']}:{row['selected_vervar_label']}|turvar:{row['selected_turvar_id']}:{row['selected_turvar_label']}",
            f"transform={row['transform']}",
        ]
        if row["denominator_raw_value"]:
            notes.append(f"source_denominator={row['denominator_raw_value']}")
        if qualification["quality_flags_rule"]:
            notes.append(f"quality_rule={qualification['quality_flags_rule']}")
        observations.append(
            {
                "observation_id": obs_id,
                "indicator_id": row["indicator_id"],
                "geography_id": row["canonical_geography_id"],
                "time_start": start,
                "time_end": end,
                "frequency": "annual",
                "value_numeric": value,
                "unit": qualification["canonical_unit"],
                "claim_type": row["claim_type"],
                "provenance_id": prov_id,
                "suppressed": "false",
                "comparable": _comparable(config["expansion_series_id"], year),
                "methodology_version": qualification["method_version"],
                "price_basis": _price_basis(config["expansion_series_id"]),
                "notes": "; ".join(notes),
            }
        )
        series_counts[config["expansion_series_id"]] = series_counts.get(config["expansion_series_id"], 0) + 1

    observations.sort(key=lambda row: row["observation_id"])
    held.sort(key=lambda row: row["expansion_row_id"])
    provenance_rows = sorted(provenance.values(), key=lambda row: row["provenance_id"])
    return observations, provenance_rows, held, {
        "schema": "ranah-observatory/bps-expansion-canonical/v1",
        "source_id": "bps_webapi",
        "observation_count": len(observations),
        "provenance_count": len(provenance_rows),
        "held_source_native_count": len(held),
        "canonical_series_count": len(series_counts),
        "series_rows": dict(sorted(series_counts.items())),
        "held_series": sorted({row["expansion_series_id"] for row in held}),
    }


def _write(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_outputs(
    observations: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
    held: list[dict[str, str]],
    manifest: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    obs_path = output_dir / "bps-expansion-canonical-observations.csv"
    prov_path = output_dir / "bps-expansion-canonical-provenance.csv"
    held_path = output_dir / "bps-expansion-held-source-native.csv"
    obs_sha = _write(obs_path, OBS_FIELDS, observations)
    prov_sha = _write(prov_path, PROV_FIELDS, provenance)
    held_fields = list(held[0].keys()) if held else []
    held_sha = _write(held_path, held_fields, held) if held else ""
    manifest = dict(manifest)
    manifest.update(
        {
            "observations_file": obs_path.name,
            "observations_sha256": obs_sha,
            "provenance_file": prov_path.name,
            "provenance_sha256": prov_sha,
            "held_file": held_path.name,
            "held_sha256": held_sha,
        }
    )
    (output_dir / "bps-expansion-canonical.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical and held layers from the BPS structural-economic expansion panel.")
    parser.add_argument("source_panel", type=Path)
    parser.add_argument("--series-registry", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--qualification-registry", type=Path, default=DEFAULT_QUALIFICATIONS)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        observations, provenance, held, manifest = build_canonical(
            args.source_panel, args.series_registry, args.qualification_registry
        )
        manifest = write_outputs(observations, provenance, held, manifest, args.output_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
