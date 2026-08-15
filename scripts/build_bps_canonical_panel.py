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
DEFAULT_SERIES = ROOT / "data" / "registries" / "bps_panel_series.csv"
DEFAULT_QUALIFICATIONS = ROOT / "data" / "registries" / "bps_panel_qualification.csv"

OBSERVATION_FIELDS = [
    "observation_id", "indicator_id", "geography_id", "time_start", "time_end", "frequency",
    "value_numeric", "unit", "claim_type", "provenance_id", "suppressed", "comparable",
    "methodology_version", "price_basis", "notes",
]
PROVENANCE_FIELDS = [
    "provenance_id", "source_id", "artifact_locator", "retrieved_at", "source_release",
    "checksum_sha256", "parser_revision", "transform_revision", "extraction_method", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _period_bounds(year: int, rule: str) -> tuple[str, str]:
    if rule == "calendar_month_august":
        month = 8
    elif rule == "calendar_month_march":
        month = 3
    elif rule == "calendar_year":
        return f"{year:04d}-01-01", f"{year:04d}-12-31"
    else:
        raise ValueError(f"unsupported canonical reference period rule {rule!r}")
    end_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{end_day:02d}"


def _release_status(series_id: str, year: int) -> str:
    if series_id != "real_grdp_growth_regency":
        return ""
    if year == 2024:
        return "very_provisional"
    if year == 2025:
        return "very_very_provisional"
    return ""


def _price_basis(series_id: str) -> str:
    return "constant_2010" if series_id == "real_grdp_growth_regency" else ""


def _comparable(series_id: str, year: int) -> str:
    if series_id in {"labor_tpt_regency", "labor_tpak_regency"}:
        # The API explicitly identifies SUPAS-2015 projection weighting for 2018-2021,
        # but does not document the post-2021 weighting basis in the variable metadata.
        # Keep the values canonical and observed while leaving cross-regime comparability unresolved.
        return ""
    return "true"


def _provenance_id(row: dict[str, str]) -> str:
    token = "|".join(
        [
            row["source_id"], row["domain"], row["bps_var_id"], row["bps_th_id"],
            row["source_snapshot_sha256"],
        ]
    )
    return "bpsprov_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _observation_id(row: dict[str, str]) -> str:
    token = "|".join(
        [row["panel_series_id"], row["canonical_geography_id"], row["bps_th_id"], row["bps_turth_id"]]
    )
    return "bpsobs_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def build_canonical(
    source_panel: Path,
    series_registry: Path = DEFAULT_SERIES,
    qualification_registry: Path = DEFAULT_QUALIFICATIONS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source_rows = read_csv(source_panel)
    series = {row["panel_series_id"]: row for row in read_csv(series_registry)}
    qualifications = {row["qualification_id"]: row for row in read_csv(qualification_registry)}

    observations: list[dict[str, Any]] = []
    provenance_by_id: dict[str, dict[str, Any]] = {}
    series_counts: dict[str, int] = {}
    seen_observation_ids: set[str] = set()

    for row in source_rows:
        config = series.get(row["panel_series_id"])
        if config is None:
            raise ValueError(f"source panel references unknown series {row['panel_series_id']!r}")
        if config["canonical_promotion_status"] != "canonical_ready":
            continue
        qualification = qualifications.get(config["qualification_id"])
        if qualification is None or qualification["decision"] != "canonical_ready":
            raise ValueError(f"canonical-ready series {config['panel_series_id']} lacks a canonical-ready qualification")

        year = int(row["bps_th_label"])
        time_start, time_end = _period_bounds(year, qualification["reference_period_rule"])
        try:
            value = float(row["value"])
        except ValueError as exc:
            raise ValueError(f"non-numeric source value for {row['panel_row_id']}: {row['value']!r}") from exc

        provenance_id = _provenance_id(row)
        if provenance_id not in provenance_by_id:
            provenance_by_id[provenance_id] = {
                "provenance_id": provenance_id,
                "source_id": row["source_id"],
                "artifact_locator": (
                    f"bps-webapi://domain/{row['domain']}/var/{row['bps_var_id']}/th/{row['bps_th_id']}"
                ),
                "retrieved_at": row["retrieved_at_utc"],
                "source_release": row.get("bps_last_update", ""),
                "checksum_sha256": row["source_snapshot_sha256"],
                "parser_revision": "normalize_bps_dynamic:v2",
                "transform_revision": "build_bps_canonical_panel:v1",
                "extraction_method": "api",
                "notes": (
                    f"source_snapshot={row['source_snapshot']}; "
                    f"source_var={row['bps_var_id']} {row['bps_var_label']}; "
                    f"source_period={row['bps_th_id']}:{row['bps_th_label']}"
                ),
            }

        release_status = _release_status(config["panel_series_id"], year)
        notes = [
            f"qualification_id={config['qualification_id']}",
            f"source_universe={qualification['source_universe']}",
            f"reference_period_rule={qualification['reference_period_rule']}",
            f"source_geography={row['bps_vervar_id']}:{row['bps_vervar_label']}",
            f"geography_mapping={row['geography_mapping_status']}",
        ]
        if qualification["quality_flags_rule"]:
            notes.append(f"quality_rule={qualification['quality_flags_rule']}")
        if release_status:
            notes.append(f"release_status={release_status}")
        if row.get("bps_var_definition"):
            notes.append("source_definition=" + row["bps_var_definition"].replace("\n", " ").strip())

        observation_id = _observation_id(row)
        if observation_id in seen_observation_ids:
            raise ValueError(f"duplicate canonical observation id {observation_id}")
        seen_observation_ids.add(observation_id)
        observations.append(
            {
                "observation_id": observation_id,
                "indicator_id": row["indicator_id"],
                "geography_id": row["canonical_geography_id"],
                "time_start": time_start,
                "time_end": time_end,
                "frequency": "annual",
                "value_numeric": value,
                "unit": qualification["canonical_unit"],
                "claim_type": "observed",
                "provenance_id": provenance_id,
                "suppressed": "false",
                "comparable": _comparable(config["panel_series_id"], year),
                "methodology_version": qualification["method_version"],
                "price_basis": _price_basis(config["panel_series_id"]),
                "notes": "; ".join(notes),
            }
        )
        series_counts[config["panel_series_id"]] = series_counts.get(config["panel_series_id"], 0) + 1

    provenance = list(provenance_by_id.values())
    observations.sort(key=lambda row: row["observation_id"])
    provenance.sort(key=lambda row: row["provenance_id"])
    manifest = {
        "schema": "ranah-observatory/bps-canonical-panel/v1",
        "source_id": "bps_webapi",
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "canonical_series_count": len(series_counts),
        "held_series": sorted(
            config["panel_series_id"]
            for config in series.values()
            if config["canonical_promotion_status"] != "canonical_ready"
        ),
        "series_rows": dict(sorted(series_counts.items())),
    }
    return observations, provenance, manifest


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_outputs(
    observations: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
    manifest: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    observations_path = output_dir / "bps-canonical-observations.csv"
    provenance_path = output_dir / "bps-canonical-provenance.csv"
    observation_sha = _write_csv(observations_path, OBSERVATION_FIELDS, observations)
    provenance_sha = _write_csv(provenance_path, PROVENANCE_FIELDS, provenance)
    manifest = dict(manifest)
    manifest.update(
        {
            "observations_file": observations_path.name,
            "observations_sha256": observation_sha,
            "provenance_file": provenance_path.name,
            "provenance_sha256": provenance_sha,
        }
    )
    (output_dir / "bps-canonical-panel.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote evidence-qualified BPS source-native rows to canonical observations.")
    parser.add_argument("source_panel", type=Path)
    parser.add_argument("--series-registry", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--qualification-registry", type=Path, default=DEFAULT_QUALIFICATIONS)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        observations, provenance, manifest = build_canonical(
            args.source_panel, args.series_registry, args.qualification_registry
        )
        manifest = write_outputs(observations, provenance, manifest, args.output_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
