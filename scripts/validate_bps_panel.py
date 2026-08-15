#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "registries" / "bps_panel_series.csv"
CANDIDATES = ROOT / "data" / "registries" / "bps_live_candidates.csv"
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"

QUALIFICATION_STATUSES = {
    "source_metadata_qualified",
    "methodology_specific_candidate",
}
PROMOTION_STATUSES = {
    "pending_reference_period_review",
    "pending_unit_crosscheck",
    "pending_indicator_universe_review",
    "pending_period_review",
    "pending_age_universe_review",
    "pending_period_inventory",
    "pending_reference_month_review",
    "pending_unit_and_release_status_review",
    "qualified_source_native",
    "canonical_ready",
}
SUBPERIOD_POLICIES = {"preserve_all"}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    rows = _read(PANEL)
    candidates = _read(CANDIDATES)
    indicators = {row["indicator_id"] for row in _read(INDICATORS)}
    candidate_pairs = {(row["indicator_id"], row["bps_var_id"]): row for row in candidates}

    if len(rows) < 8:
        errors.append(f"{PANEL}: first panel must retain at least 8 qualified series")

    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for line_no, row in enumerate(rows, start=2):
        prefix = f"{PANEL}:{line_no}"
        required = (
            "panel_series_id", "indicator_id", "bps_var_id", "subject_id", "source_title",
            "target_start_year", "target_end_year", "selected_turvar_id", "selected_turvar_label",
            "subperiod_policy", "qualification_status", "canonical_promotion_status", "comparability_notes",
        )
        for field in required:
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")

        series_id = row.get("panel_series_id", "")
        if series_id in ids:
            errors.append(f"{prefix}: duplicate panel_series_id {series_id}")
        ids.add(series_id)

        pair = (row.get("indicator_id", ""), row.get("bps_var_id", ""))
        if pair in pairs:
            errors.append(f"{prefix}: duplicate indicator/BPS variable mapping {pair}")
        pairs.add(pair)

        if row.get("indicator_id") not in indicators:
            errors.append(f"{prefix}: unresolved indicator_id {row.get('indicator_id')}")
        candidate = candidate_pairs.get(pair)
        if candidate is None:
            errors.append(f"{prefix}: mapping is not present in bps_live_candidates.csv")
        elif candidate.get("bps_title") != row.get("source_title"):
            errors.append(f"{prefix}: source_title differs from qualified live-candidate title")

        try:
            start = int(row.get("target_start_year", ""))
            end = int(row.get("target_end_year", ""))
        except ValueError:
            errors.append(f"{prefix}: target years must be integers")
        else:
            if start > end:
                errors.append(f"{prefix}: target_start_year is after target_end_year")
            if start < 1950 or end > 2100:
                errors.append(f"{prefix}: implausible target year range")

        try:
            int(row.get("bps_var_id", ""))
            int(row.get("subject_id", ""))
            int(row.get("selected_turvar_id", ""))
        except ValueError:
            errors.append(f"{prefix}: BPS ids must be integer-compatible")

        if row.get("subperiod_policy") not in SUBPERIOD_POLICIES:
            errors.append(f"{prefix}: unsupported subperiod_policy {row.get('subperiod_policy')!r}")
        if row.get("qualification_status") not in QUALIFICATION_STATUSES:
            errors.append(f"{prefix}: unsupported qualification_status {row.get('qualification_status')!r}")
        if row.get("canonical_promotion_status") not in PROMOTION_STATUSES:
            errors.append(
                f"{prefix}: unsupported canonical_promotion_status {row.get('canonical_promotion_status')!r}"
            )

        if row.get("canonical_promotion_status") == "canonical_ready":
            errors.append(f"{prefix}: no first-panel series is allowed to be canonical_ready before source-native validation")

    by_var = {row["bps_var_id"]: row for row in rows}
    guardrails = {
        "141": "pending_unit_crosscheck",
        "320": "pending_indicator_universe_review",
        "752": "pending_period_inventory",
        "34": "pending_reference_month_review",
        "138": "pending_unit_and_release_status_review",
    }
    for var_id, expected in guardrails.items():
        row = by_var.get(var_id)
        if row is None:
            errors.append(f"required guarded BPS variable {var_id} is missing from first panel")
        elif row["canonical_promotion_status"] != expected:
            errors.append(
                f"var {var_id}: expected canonical_promotion_status {expected}, got {row['canonical_promotion_status']}"
            )

    internet = by_var.get("320")
    if internet and (
        internet["selected_turvar_id"] != "595"
        or "Pernah Mengakses Internet" not in internet["selected_turvar_label"]
    ):
        errors.append("var 320 must explicitly select turvar 595 Pernah Mengakses Internet")

    life = by_var.get("752")
    if life and int(life["target_start_year"]) < 2020:
        errors.append("LF-SP2020 life-expectancy candidate must not be projected before 2020")

    return errors, {"series": len(rows), "indicators": len({row["indicator_id"] for row in rows})}


def main() -> int:
    errors, counts = validate()
    if errors:
        print("BPS normalized-panel registry validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS normalized-panel registry validation passed: "
        f"{counts['series']} source series mapped to {counts['indicators']} canonical indicators."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
