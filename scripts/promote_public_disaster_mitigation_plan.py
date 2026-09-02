#!/usr/bin/env python3
"""Promote qualified BPBD 2026 mitigation planning context into public disaster contract v5.

This step upgrades public disaster v4 using only the frozen M63 planning outputs.
Targets remain forward planning commitments, not achievements. Qualitative gaps
remain aggregate official diagnostics, not municipality scores or predictions.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SUMMARY = ROOT / "web/static/data/disaster-summary.json"
M63_MANIFEST = ROOT / "data/manifests/milestone63_bpbd_mitigation_plan_2026_final.json"

BASE_PUBLIC_SCHEMA = "ranah-observatory/public-disaster-summary/v4"
PUBLIC_SCHEMA = "ranah-observatory/public-disaster-summary/v5"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verified_output(manifest: dict, key: str) -> Path:
    meta = manifest["outputs"][key]
    path = ROOT / meta["path"]
    require(path.exists(), f"M63 output missing: {meta['path']}")
    require(sha256(path) == meta["sha256"], f"M63 output checksum drift: {meta['path']}")
    return path


def main() -> None:
    require(PUBLIC_SUMMARY.exists(), "public disaster summary missing; run prior public promoters first")
    base = json.loads(PUBLIC_SUMMARY.read_text(encoding="utf-8"))
    require(base.get("schema") == BASE_PUBLIC_SCHEMA, f"expected {BASE_PUBLIC_SCHEMA}, got {base.get('schema')!r}")

    m63 = json.loads(M63_MANIFEST.read_text(encoding="utf-8"))
    require(m63.get("schema") == "ranah-observatory/milestone63-bpbd-mitigation-plan-2026-final/v1", "unsupported M63 schema")
    result = m63["result"]
    require(result["planning_target_count"] == 13, "M63 planning target count drift")
    require(result["qualitative_gap_count"] == 18, "M63 qualitative gap count drift")
    require(result["plan_year"] == 2026, "M63 plan year drift")
    require(result["dashboard_planning_context_ready"] is True, "M63 dashboard context not ready")
    require(result["actual_capacity_score_materialized"] is False, "M63 capacity score unexpectedly materialized")
    require(result["planning_targets_treated_as_actuals"] is False, "M63 planning targets treated as actuals")
    require(result["municipality_gap_attribution_authorized"] is False, "M63 municipality gap attribution unexpectedly authorized")
    require(result["prediction_claim_authorized"] is False, "M63 prediction unexpectedly authorized")
    require(result["budget_comparison_materialized"] is False, "M63 budget comparison unexpectedly materialized")

    boundary = m63["interpretation_boundary"]
    require(boundary["targets_are_forward_planning_commitments"] is True, "M63 target interpretation drift")
    require(boundary["gaps_are_official_qualitative_diagnostics"] is True, "M63 gap interpretation drift")
    require(boundary["gaps_are_not_numeric_capacity_scores"] is True, "M63 gap scoring boundary drift")
    require(boundary["targets_do_not_establish_achievement"] is True, "M63 achievement boundary drift")
    require(boundary["no_unmitigated_probability_inference"] is True, "M63 probability boundary drift")

    target_path = verified_output(m63, "targets")
    gap_path = verified_output(m63, "gaps")
    targets = read_csv(target_path)
    gaps = read_csv(gap_path)
    require(len(targets) == 13, "M67 expected 13 target rows")
    require(len(gaps) == 18, "M67 expected 18 gap rows")

    target_ids: set[str] = set()
    public_targets: list[dict] = []
    for row in targets:
        record_id = row["record_id"]
        require(record_id and record_id not in target_ids, f"duplicate M63 target: {record_id}")
        target_ids.add(record_id)
        require(row["plan_year"] == "2026", f"M63 target year drift: {record_id}")
        require(row["claim_type"] == "official_planning_target", f"M63 target claim type drift: {record_id}")
        require(row["actual_achievement_claimed"] == "false", f"M63 target promoted as actual: {record_id}")
        public_targets.append(
            {
                "record_id": record_id,
                "program_or_activity": row["program_or_activity"],
                "indicator": row["indicator"],
                "target_value": int(row["target_value"]),
                "target_unit": row["target_unit"],
                "geographic_scope": row["geographic_scope"],
                "source_excerpt_pages": row["source_excerpt_pages"],
            }
        )

    gap_ids: set[str] = set()
    theme_counts: Counter[str] = Counter()
    public_gaps: list[dict] = []
    for row in gaps:
        gap_id = row["gap_id"]
        require(gap_id and gap_id not in gap_ids, f"duplicate M63 gap: {gap_id}")
        gap_ids.add(gap_id)
        require(row["plan_year"] == "2026", f"M63 gap year drift: {gap_id}")
        require(row["claim_type"] == "official_planning_diagnostic", f"M63 gap claim type drift: {gap_id}")
        require(row["quantified"] == "false", f"M63 qualitative gap unexpectedly quantified: {gap_id}")
        require(row["municipality_identified"] == "false", f"M63 gap unexpectedly attributed to municipality: {gap_id}")
        theme_counts[row["theme"]] += 1
        public_gaps.append(
            {
                "gap_id": gap_id,
                "theme": row["theme"],
                "gap_label": row["gap_label"],
                "geographic_scope": row["geographic_scope"],
                "source_excerpt_pages": row["source_excerpt_pages"],
            }
        )

    public_targets.sort(key=lambda row: row["record_id"])
    public_gaps.sort(key=lambda row: (row["theme"], row["gap_id"]))

    payload = dict(base)
    payload["schema"] = PUBLIC_SCHEMA
    payload["mitigation_plan_2026"] = {
        "source": {
            "organization": "BPBD Provinsi Sumatera Barat",
            "document": "Rencana Kerja BPBD Provinsi Sumatera Barat Tahun 2026",
            "manifest_path": M63_MANIFEST.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256(M63_MANIFEST),
            "targets_path": target_path.relative_to(ROOT).as_posix(),
            "targets_sha256": sha256(target_path),
            "gaps_path": gap_path.relative_to(ROOT).as_posix(),
            "gaps_sha256": sha256(gap_path),
        },
        "plan_year": 2026,
        "targets": {
            "rows": public_targets,
            "count": len(public_targets),
        },
        "gaps": {
            "rows": public_gaps,
            "count": len(public_gaps),
            "theme_counts": dict(sorted(theme_counts.items())),
        },
        "boundaries": {
            "targets_are_forward_planning_commitments": True,
            "targets_are_actual_achievements": False,
            "gaps_are_official_qualitative_diagnostics": True,
            "gaps_are_numeric_capacity_scores": False,
            "municipality_gap_attribution_authorized": False,
            "prediction_claim_authorized": False,
            "unmitigated_probability_inference_authorized": False,
        },
        "interpretation": {
            "id": "Target 2026 adalah target rencana kerja BPBD, bukan capaian aktual. Daftar kendala adalah diagnosis kualitatif resmi tingkat provinsi/kabupaten-kota agregat; sumber tidak mengidentifikasi kabupaten/kota tertentu untuk setiap kendala dan tidak memberi skor kapasitas numerik.",
            "en": "The 2026 figures are BPBD work-plan targets, not observed achievements. The constraint list is an official qualitative province/aggregate district diagnostic; the source does not identify a specific municipality for each constraint and does not provide numeric capacity scores.",
        },
    }

    PUBLIC_SUMMARY.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": PUBLIC_SCHEMA, "targets": 13, "gaps": 18, "themes": len(theme_counts)}, sort_keys=True))


if __name__ == "__main__":
    main()
