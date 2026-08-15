from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
CANDIDATES = ROOT / "data" / "registries" / "bps_live_candidates.csv"

ALLOWED_STATUSES = {
    "metadata_qualified_candidate",
    "requires_source_segmentation",
    "needs_period_inventory",
    "needs_definition_review",
    "methodology_version_candidate",
    "needs_unit_and_definition_review",
    "needs_unit_crosscheck",
    "needs_turvar_selection",
    "needs_unit_semantics_review",
    "needs_industry_dimension_review",
    "needs_turvar_and_unit_review",
    "needs_turvar_and_concept_review",
    "not_direct_measure",
}
PERIOD_SCOPE = re.compile(r"^(?:\d{4}(?:-\d{4})?|\d{4}(?:;\d{4})*)?$")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    indicators = {row["indicator_id"].strip() for row in read_csv(INDICATORS)}
    candidates = read_csv(CANDIDATES)
    seen_pairs: set[tuple[str, str]] = set()

    for row_number, row in enumerate(candidates, start=2):
        indicator_id = row["indicator_id"].strip()
        var_id = row["bps_var_id"].strip()
        status = row["qualification_status"].strip()
        if indicator_id not in indicators:
            errors.append(f"candidate row {row_number}: unknown indicator_id={indicator_id!r}")
        try:
            if int(var_id) <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"candidate row {row_number}: bps_var_id must be a positive integer")
        pair = (indicator_id, var_id)
        if pair in seen_pairs:
            errors.append(f"candidate row {row_number}: duplicate indicator/variable pair {pair}")
        seen_pairs.add(pair)
        if status not in ALLOWED_STATUSES:
            errors.append(f"candidate row {row_number}: invalid qualification_status={status!r}")
        if not row["candidate_role"].strip():
            errors.append(f"candidate row {row_number}: candidate_role is required")
        if not row["bps_title"].strip():
            errors.append(f"candidate row {row_number}: bps_title is required")
        if not row["source_unit"].strip():
            errors.append(f"candidate row {row_number}: source_unit is required, even when BPS reports no unit")
        if not row["source_geography"].strip():
            errors.append(f"candidate row {row_number}: source_geography is required")
        scope = row["known_period_scope"].strip()
        if not PERIOD_SCOPE.match(scope):
            errors.append(f"candidate row {row_number}: invalid known_period_scope={scope!r}")
        if status == "metadata_qualified_candidate" and not row["comparability_notes"].strip():
            errors.append(f"candidate row {row_number}: qualified metadata candidate requires comparability notes")

    by_indicator: dict[str, list[dict[str, str]]] = {}
    for row in candidates:
        by_indicator.setdefault(row["indicator_id"].strip(), []).append(row)

    population = by_indicator.get("population_total", [])
    if not any(row["bps_var_id"].strip() == "484" for row in population):
        errors.append("population_total must retain var 484 as the census/SUPAS anchor candidate")
    mixed = next((row for row in population if row["bps_var_id"].strip() == "32"), None)
    if not mixed or mixed["qualification_status"].strip() != "requires_source_segmentation":
        errors.append("population var 32 must remain marked requires_source_segmentation")

    internet = next(
        (row for row in by_indicator.get("internet_access", []) if row["bps_var_id"].strip() == "320"),
        None,
    )
    if not internet or "5" not in internet["comparability_notes"] or "3 months" not in internet["comparability_notes"]:
        errors.append("internet var 320 must retain its age-5+ and 3-month universe notes")

    electricity = next(
        (
            row
            for row in by_indicator.get("household_electricity_access", [])
            if row["bps_var_id"].strip() == "797"
        ),
        None,
    )
    if not electricity or electricity["qualification_status"].strip() != "not_direct_measure":
        errors.append("electricity customer count var 797 must not be treated as direct household access")

    counts = {
        "candidate_rows": len(candidates),
        "candidate_indicators": len(by_indicator),
        "metadata_qualified": sum(
            row["qualification_status"].strip() == "metadata_qualified_candidate"
            for row in candidates
        ),
    }
    return errors, counts


def main() -> int:
    errors, counts = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "BPS live candidate registry valid: "
        f"{counts['candidate_rows']} rows across {counts['candidate_indicators']} indicators; "
        f"{counts['metadata_qualified']} metadata-qualified candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
