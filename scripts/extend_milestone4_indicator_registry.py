#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "registries" / "indicators.csv"
FIELDS = [
    "indicator_id", "name", "domain", "definition", "unit", "frequency",
    "preferred_geography", "source_priority", "allowed_claim_types", "status",
    "comparability_notes",
]

UPDATES = {
    "urban_population_share": {
        "preferred_geography": "regency_city",
        "allowed_claim_types": "observed|derived|model_estimate",
        "comparability_notes": "Urban rural classification and projection vintages can change over time; projection-based values remain model_estimate",
    },
    "net_migration_rate": {
        "preferred_geography": "regency_city",
        "comparability_notes": "Migration interval residence definition and source rate denominator must be retained; SUPAS recent migration is five-year recent migration",
    },
    "infant_mortality_rate": {
        "preferred_geography": "regency_city",
        "comparability_notes": "Survey-based mortality estimates and direct registration counts must not be silently combined; retain survey and reference-period methodology",
    },
    "internet_access": {
        "name": "Internet access/use",
        "definition": "Share of the stated household or person universe accessing the internet under the source recall-period definition",
        "comparability_notes": "Universe device definition and recall period are material; the qualified BPS series is persons age 5+ accessing internet in the previous 3 months",
    },
    "road_condition_good": {
        "comparability_notes": "Road authority and condition categories must remain explicit; the qualified BPS batch covers provincial-authority roads only",
    },
}

NEW_ROWS = [
    {"indicator_id":"neet_rate","name":"Youth NEET rate","domain":"labor_livelihoods","definition":"Share of people age 15 to 24 who are not in employment education or training under the source definition","unit":"percent","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Age universe survey period and education training definitions must be retained"},
    {"indicator_id":"mobile_phone_use","name":"Mobile phone use","domain":"infrastructure_connectivity","definition":"Share of the stated population universe using a mobile phone within the source recall period","unit":"percent","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Qualified BPS series covers persons age 5+ and a 3-month recall period; device definition may evolve"},
    {"indicator_id":"average_employee_wage","name":"Average monthly employee wage","domain":"labor_livelihoods","definition":"Average net monthly wage or salary of employees under the source labor-force definition","unit":"rupiah_per_month","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Employment status universe survey weights and nominal price level must be retained"},
    {"indicator_id":"dependency_ratio","name":"Dependency ratio","domain":"demography_migration","definition":"Population age 0 to 14 plus age 65+ relative to population age 15 to 64 under the source definition","unit":"dependents_per_100_working_age","frequency":"census_or_survey","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Age-group definitions and census or survey methodology must be retained"},
    {"indicator_id":"total_fertility_rate","name":"Total fertility rate","domain":"demography_migration","definition":"Average number of children a woman would bear under the source age-specific fertility schedule","unit":"births_per_woman","frequency":"census_or_survey","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Life-table or survey estimation methodology and reference period must remain explicit"},
    {"indicator_id":"child_mortality_rate","name":"Child mortality rate","domain":"health","definition":"Mortality measure for children age 1 to 4 under the official source definition","unit":"per_1000_live_births","frequency":"census_or_survey","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Preserve the exact official SUPAS mortality definition and estimation method"},
    {"indicator_id":"under_five_mortality_rate","name":"Under-five mortality rate","domain":"health","definition":"Probability or rate of dying before age five under the official source definition","unit":"per_1000_live_births","frequency":"census_or_survey","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Preserve the exact official SUPAS mortality definition and estimation method"},
    {"indicator_id":"elderly_population_share","name":"Elderly population share","domain":"demography_migration","definition":"Share of population classified as elderly under the source age threshold","unit":"percent","frequency":"census_or_survey","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Age threshold and census or survey methodology must be retained"},
    {"indicator_id":"domestic_investment_realization","name":"Domestic investment realization","domain":"production_trade","definition":"Realized additional domestic investment recorded under the official PMDN reporting system","unit":"million_rupiah","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS|Ministry_of_Investment","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Nominal values reporting coverage project definition and revisions must be retained"},
    {"indicator_id":"foreign_investment_realization","name":"Foreign investment realization","domain":"production_trade","definition":"Realized additional foreign investment recorded under the official PMA reporting system","unit":"million_rupiah","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS|Ministry_of_Investment","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Nominal values reporting coverage project definition and revisions must be retained"},
    {"indicator_id":"household_expenditure_per_capita_monthly","name":"Monthly expenditure per capita","domain":"income_productivity_poverty_inequality","definition":"Average monthly food and non-food expenditure per person under the source household-survey definition","unit":"rupiah_per_person_month","frequency":"annual_or_survey","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Nominal prices survey month welfare aggregate and sampling design must be retained"},
    {"indicator_id":"food_inadequacy_prevalence","name":"Prevalence of food inadequacy","domain":"income_productivity_poverty_inequality","definition":"Share of population with insufficient dietary energy consumption under the official source methodology","unit":"percent","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Estimation methodology dietary-energy threshold and reference period must be retained"},
    {"indicator_id":"labor_force_count","name":"Labor force population","domain":"labor_livelihoods","definition":"Population age 15+ classified in the labor force under the source survey definition","unit":"persons","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Sakernas reference month weighting and working-age definition must be retained"},
    {"indicator_id":"employed_population","name":"Employed population","domain":"labor_livelihoods","definition":"Population age 15+ classified as employed under the source survey definition","unit":"persons","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Sakernas reference month weighting and employment definition must be retained"},
    {"indicator_id":"unemployed_population","name":"Unemployed population","domain":"labor_livelihoods","definition":"Population age 15+ classified as openly unemployed under the source survey definition","unit":"persons","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Sakernas reference month weighting and unemployment definition must be retained"},
    {"indicator_id":"provincial_road_length","name":"Provincial road length","domain":"infrastructure_connectivity","definition":"Total length of provincial-authority roads across the source road-condition categories","unit":"kilometres","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS|Ministry_of_Public_Works","allowed_claim_types":"derived","status":"backlog","comparability_notes":"This is provincial-authority road length only; do not interpret as total road network length"},
    {"indicator_id":"large_medium_industry_employment","name":"Large and medium industry employment","domain":"production_trade","definition":"Workers recorded in large and medium manufacturing establishments under the source industrial survey","unit":"persons","frequency":"annual","preferred_geography":"regency_city","source_priority":"BPS","allowed_claim_types":"observed","status":"backlog","comparability_notes":"Industry-size classification establishment coverage and missing geographies must be retained; absence is not zero"},
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def update_registry(path: Path) -> tuple[int, int]:
    rows = read_rows(path)
    by_id = {row["indicator_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("indicator registry contains duplicate indicator_id values")
    for indicator_id, patch in UPDATES.items():
        if indicator_id not in by_id:
            raise ValueError(f"required existing indicator missing: {indicator_id}")
        by_id[indicator_id].update(patch)
    added = 0
    for row in NEW_ROWS:
        iid = row["indicator_id"]
        if iid in by_id:
            if by_id[iid] != row:
                raise ValueError(f"new Milestone 4 indicator already exists with different definition: {iid}")
            continue
        rows.append(row)
        by_id[iid] = row
        added += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), added


def main() -> int:
    parser = argparse.ArgumentParser(description="Extend the canonical indicator registry for the Milestone 4 closure batch.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    try:
        total, added = update_registry(args.registry)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"indicator_registry_rows={total}; newly_added={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
