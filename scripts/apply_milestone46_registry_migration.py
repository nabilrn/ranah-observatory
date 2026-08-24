#!/usr/bin/env python3
"""Apply the narrow M46 registry/validator migration for total disaster events.

The migration is intentionally idempotent and anchor-based. It refuses to edit
an unexpected pre-M46 state, which prevents a broad or silent ontology rewrite.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDICATORS = ROOT / "data/registries/indicators.csv"
QUALIFICATIONS = ROOT / "data/registries/bnpb_indicator_qualification.csv"
BPS_COVERAGE = ROOT / "data/registries/bps_indicator_coverage.csv"
CLIMATE_VALIDATOR = ROOT / "scripts/validate_climate_disaster_foundation.py"

OLD_LANDSLIDE_LINE = (
    "landslide_events,Recorded landslide events,disaster_resilience,Count of officially recorded landslide events under source event definition,count,annual,regency_city,BNPB,observed,backlog,Reporting intensity and event deduplication must be assessed"
)
NEW_TOTAL_LINE = (
    "total_disaster_events,Recorded total disaster events,disaster_resilience,Count of all disaster events recorded by BNPB for the stated geography and calendar year under the qualified source release,count,annual,regency_city,BNPB,observed,qualified,Within-source 2010-2024 entity series; exact historical-to-current polygon harmonization is not proven and reporting intensity classification practice and release revisions remain material"
)

OLD_QUALIFICATION_LINE = (
    "q_bnpb_total_events_context,total_disaster_events_2010_2024,,bnpb_total_events_kab_2010_2024,year_columns_2010_2024,2010,2024,count,observed,source_native_context,current_name_and_admin_type_match,never_relabel_as_type_specific,Useful contextual burden series but no canonical indicator currently represents all-disaster event counts"
)
NEW_QUALIFICATION_LINE = (
    "q_bnpb_total_events_context,total_disaster_events_2010_2024,total_disaster_events,bnpb_total_events_kab_2010_2024,year_columns_2010_2024,2010,2024,count,observed,canonical_ready_separate_layer,current_entity_identity_2010_2024_exact_polygon_not_proven,require_m44_reconciliation_and_m45_fingerprint;never_relabel_as_type_specific,Qualified canonical separate-layer recorded-event series; global panel uses only 2018-2024 and leaves comparability unset"
)

BPS_COVERAGE_ANCHOR = (
    "landslide_events,not_primary,defer,longsor tanah longsor kejadian bencana,defer_non_bps,BNPB is primary disaster-event source"
)
NEW_BPS_COVERAGE_LINE = (
    "total_disaster_events,not_primary,defer,jumlah kejadian bencana total kejadian bencana,defer_non_bps,BNPB is primary all-disaster recorded-event source"
)

OLD_REQUIRED_INDICATORS = (
    'for indicator_id in ("flood_events", "landslide_events", "disaster_affected_population"):'
)
NEW_REQUIRED_INDICATORS = (
    'for indicator_id in ("flood_events", "landslide_events", "total_disaster_events", "disaster_affected_population"):'
)
OLD_TOTAL_BLOCK = '''    total_context = [row for row in qualifications if row["series_id"] == "total_disaster_events_2010_2024"]
    if len(total_context) != 1 or total_context[0]["promotion_status"] != "source_native_context":
        errors.append("2010-2024 total disaster events must remain source-native context")
    if total_context and total_context[0]["indicator_id"]:
        errors.append("all-disaster total series must not masquerade as a canonical indicator")
'''
NEW_TOTAL_BLOCK = '''    total_context = [row for row in qualifications if row["series_id"] == "total_disaster_events_2010_2024"]
    if len(total_context) != 1 or total_context[0]["promotion_status"] != "canonical_ready_separate_layer":
        errors.append("2010-2024 total disaster events must be qualified in the separate canonical layer")
    if total_context and total_context[0]["indicator_id"] != "total_disaster_events":
        errors.append("all-disaster total series must map only to total_disaster_events")
    if total_context and "exact_polygon_not_proven" not in total_context[0]["geography_rule"]:
        errors.append("total-disaster geography qualification must preserve the exact-polygon caveat")
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one pre-M46 anchor, found {count}")
    return text.replace(old, new, 1)


def migrate() -> dict[str, bool]:
    indicators = INDICATORS.read_text(encoding="utf-8")
    if NEW_TOTAL_LINE not in indicators:
        anchor = OLD_LANDSLIDE_LINE
        if indicators.count(anchor) != 1:
            raise RuntimeError("indicator registry landslide anchor drift")
        indicators = indicators.replace(anchor, anchor + "\n" + NEW_TOTAL_LINE, 1)
        INDICATORS.write_text(indicators, encoding="utf-8", newline="")
        indicators_changed = True
    else:
        if indicators.count(NEW_TOTAL_LINE) != 1:
            raise RuntimeError("total_disaster_events indicator must exist exactly once")
        indicators_changed = False

    qualifications = QUALIFICATIONS.read_text(encoding="utf-8")
    migrated_qualifications = replace_once(
        qualifications,
        OLD_QUALIFICATION_LINE,
        NEW_QUALIFICATION_LINE,
        "BNPB qualification registry",
    )
    qualifications_changed = migrated_qualifications != qualifications
    if qualifications_changed:
        QUALIFICATIONS.write_text(migrated_qualifications, encoding="utf-8", newline="")

    bps_coverage = BPS_COVERAGE.read_text(encoding="utf-8")
    if NEW_BPS_COVERAGE_LINE not in bps_coverage:
        if bps_coverage.count(BPS_COVERAGE_ANCHOR) != 1:
            raise RuntimeError("BPS coverage landslide anchor drift")
        bps_coverage = bps_coverage.replace(
            BPS_COVERAGE_ANCHOR,
            BPS_COVERAGE_ANCHOR + "\n" + NEW_BPS_COVERAGE_LINE,
            1,
        )
        BPS_COVERAGE.write_text(bps_coverage, encoding="utf-8", newline="")
        bps_coverage_changed = True
    else:
        if bps_coverage.count(NEW_BPS_COVERAGE_LINE) != 1:
            raise RuntimeError("total_disaster_events BPS coverage row must exist exactly once")
        bps_coverage_changed = False

    validator = CLIMATE_VALIDATOR.read_text(encoding="utf-8")
    migrated_validator = replace_once(
        validator,
        OLD_REQUIRED_INDICATORS,
        NEW_REQUIRED_INDICATORS,
        "climate validator required indicators",
    )
    migrated_validator = replace_once(
        migrated_validator,
        OLD_TOTAL_BLOCK,
        NEW_TOTAL_BLOCK,
        "climate validator total-event contract",
    )
    validator_changed = migrated_validator != validator
    if validator_changed:
        CLIMATE_VALIDATOR.write_text(migrated_validator, encoding="utf-8")

    return {
        "indicators_changed": indicators_changed,
        "qualifications_changed": qualifications_changed,
        "bps_coverage_changed": bps_coverage_changed,
        "validator_changed": validator_changed,
    }


def main() -> int:
    result = migrate()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
