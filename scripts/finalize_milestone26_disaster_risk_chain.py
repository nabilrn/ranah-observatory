#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_QUAL = ROOT / "data/manifests/milestone26_source_qualification.json"
POP = ROOT / "data/manifests/milestone26_stage1_population_component.json"
CAP = ROOT / "data/manifests/milestone26_stage1_capacity_component.json"
DIBI = ROOT / "data/manifests/milestone26_stage1_dibi_occurrence_context.json"
IMPACT = ROOT / "data/manifests/milestone26_stage2_observed_impact_decision.json"
SPEC = ROOT / "research/MILESTONE26_DISASTER_RISK_CHAIN_SPEC.md"
OUT = ROOT / "data/manifests/milestone26_disaster_risk_chain_complete.json"
DOC = ROOT / "docs/MILESTONE26_DISASTER_RISK_CHAIN.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_csv(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def build_doc(payload: dict[str, Any]) -> str:
    c = payload["components"]
    return f"""# Milestone 26 — Disaster-Risk Evidence Chain Qualification

## Result

M26 is complete as a **staged evidence-qualification package**, not as a composite disaster-risk model.

Three official BNPB/InaRISK component sources were qualified and materialized across all 19 current Sumatera Barat kabupaten/kota:

- population exposure proxy: 2020, 19 observations;
- capacity index: 2021, 19 observations;
- DIBI recorded hydrometeorological occurrence/context: source-declared aggregate coverage 2015–2024, 19 observations.

The DIBI component is crosswalked through the previously qualified BNPB/Permendagri-to-canonical geography registry. Source `NO_KAB` values are retained in provenance and are **not** treated as BPS codes.

## Components that remain held

Flood and landslide hazard/vulnerability ImageServers remain blocked because exact official raster vintage/methodology binding is unresolved. The current InaRISK methodology page is framework evidence only and cannot supply a missing raster vintage.

Event-level observed impact also remains held. The legacy BNPB Data Bencana page exposes the desired impact fields, but the dated POST transport did not qualify deterministically. BNPB Satu Data was checked through metadata-only discovery in both the primary compilation package and the dedicated 2024 package; those packages expose aggregate impact resources but no metadata-qualified event-level candidate compatible with the locked Stage 2 estimand.

A zero-row dated legacy-table response is **not** interpreted as zero disaster occurrence or zero observed impact. Aggregate CKAN impact resources are **not** relabeled as event rows.

## Scientific boundary

`risk_synthesis_authorized = false`.

M26 does not:

- combine 2020 exposure, 2021 capacity, 2015–2024 occurrence context, or 2024 evidence into a contemporaneous score;
- aggregate undated hazard/vulnerability rasters;
- infer observed impact from DIBI occurrence fields;
- convert missing impact values to zero;
- rank kabupaten/kota by risk;
- fit a statistical or causal model;
- infer monetary disaster loss or monetary wasted potential.

## Frozen status

| Component | Status | Numeric footprint |
|---|---|---:|
| Population exposure proxy | {c['population_exposure']['status']} | {c['population_exposure']['observation_count']} |
| Capacity | {c['capacity']['status']} | {c['capacity']['observation_count']} |
| DIBI occurrence/context | {c['recorded_occurrence_context']['status']} | {c['recorded_occurrence_context']['observation_count']} |
| Event-level observed impact | {c['observed_impact']['status']} | 0 promoted |
| Flood hazard | {c['flood_hazard']['status']} | 0 |
| Landslide hazard | {c['landslide_hazard']['status']} | 0 |
| Flood vulnerability | {c['flood_vulnerability']['status']} | 0 |
| Landslide vulnerability | {c['landslide_vulnerability']['status']} | 0 |

## Reconsideration gates

Observed impact can be revisited only if a deterministic public event-level BNPB transport appears with documented event identity, target-period coverage, geography mapping, and missing-value semantics.

Hazard or vulnerability can be revisited only when an official source binds the exact raster/service to a dated release or methodology version.

Any future risk synthesis requires a separate preregistered temporal and estimand design; M26 itself does not authorize it.
"""


def main() -> int:
    source = load(SOURCE_QUAL)
    pop = load(POP)
    cap = load(CAP)
    dibi = load(DIBI)
    impact = load(IMPACT)

    assert source["schema"] == "ranah-observatory/milestone26-source-qualification/v1"
    assert source["stage0_complete"] is True
    assert source["expected_qualification_states_match"] is True
    assert source["qualified_numeric_source_ids"] == [
        "inarisk_capacity_2021", "inarisk_population_2020", "dibi_kabupaten_hidromet_2015_2024"
    ]
    states = source["qualification_states"]
    assert states["inarisk_capacity_2021"] == "qualified_explicit_vintage_metadata"
    assert states["inarisk_population_2020"] == "qualified_explicit_vintage_metadata"
    assert states["dibi_kabupaten_hidromet_2015_2024"] == "qualified_explicit_coverage_metadata"
    for sid in (
        "inarisk_flood_hazard", "inarisk_landslide_hazard",
        "inarisk_flood_vulnerability", "inarisk_landslide_vulnerability",
    ):
        assert states[sid] == "endpoint_verified_version_binding_unresolved"

    assert pop["population_component_materialized"] is True
    assert pop["geography_count"] == 19 and pop["observation_count"] == 19
    assert pop["reference_year"] == 2020
    assert pop["empty_statistics_imputed"] is False
    assert pop["risk_synthesis_authorized"] is False
    pop_frame = ROOT / pop["outputs"]["component_frame"]
    assert count_csv(pop_frame) == 19
    assert digest(pop_frame) == pop["outputs"]["component_frame_sha256"]

    assert cap["capacity_component_materialized"] is True
    assert cap["geography_count"] == 19 and cap["observation_count"] == 19
    assert cap["reference_year"] == 2021
    assert cap["risk_synthesis_authorized"] is False
    cap_frame = ROOT / cap["outputs"]["component_frame"]
    assert count_csv(cap_frame) == 19
    assert digest(cap_frame) == cap["outputs"]["component_frame_sha256"]

    assert dibi["schema"] == "ranah-observatory/milestone26-stage1-dibi-occurrence-context/v2"
    assert dibi["geography_count"] == 19 and dibi["observation_count"] == 19
    assert dibi["exact_source_key_set_pass"] is True
    assert dibi["exact_canonical_geography_set_pass"] is True
    assert dibi["canonical_crosswalk_applied"] is True
    assert dibi["source_key_assumed_canonical"] is False
    assert dibi["source_numeric_values_changed_by_crosswalk_correction"] is False
    assert dibi["historical_boundary_reconstruction_performed"] is False
    assert dibi["semantic_interpretation_of_abbreviated_field_names_performed"] is False
    assert dibi["risk_synthesis_authorized"] is False
    dibi_frame = ROOT / dibi["outputs"]["component_frame"]
    assert count_csv(dibi_frame) == 19
    assert digest(dibi_frame) == dibi["outputs"]["component_frame_sha256"]

    assert impact["schema"] == "ranah-observatory/milestone26-stage2-observed-impact-decision/v1"
    assert impact["decision"] == "held_deterministic_event_level_transport_unqualified"
    assert impact["event_level_observed_impact_qualified"] is False
    assert impact["aggregate_ckan_impact_resources_promoted_as_event_rows"] is False
    assert impact["zero_rows_interpreted_as_zero_disaster_occurrence"] is False
    assert impact["zero_rows_interpreted_as_zero_observed_impact"] is False
    assert impact["risk_synthesis_authorized"] is False

    payload = {
        "schema": "ranah-observatory/milestone26-disaster-risk-chain-complete/v1",
        "milestone": 26,
        "milestone26_evidence_qualification_complete": True,
        "completion_semantics": "staged_evidence_qualification_complete_composite_risk_model_not_authorized",
        "geography_regime": "BIG_June_2026_fixed_current_boundary",
        "geography_count": 19,
        "components": {
            "population_exposure": {
                "status": "qualified_and_materialized",
                "reference_year": 2020,
                "observation_count": 19,
                "manifest": ref(POP),
            },
            "capacity": {
                "status": "qualified_and_materialized",
                "reference_year": 2021,
                "observation_count": 19,
                "manifest": ref(CAP),
            },
            "recorded_occurrence_context": {
                "status": "qualified_and_materialized_source_native_aggregate",
                "declared_start_year": 2015,
                "declared_end_year": 2024,
                "observation_count": 19,
                "canonical_crosswalk_applied": True,
                "manifest": ref(DIBI),
            },
            "observed_impact": {
                "status": "held_event_level_transport_unqualified",
                "observation_count_promoted": 0,
                "manifest": ref(IMPACT),
            },
            "flood_hazard": {"status": states["inarisk_flood_hazard"], "numeric_extraction_authorized": False},
            "landslide_hazard": {"status": states["inarisk_landslide_hazard"], "numeric_extraction_authorized": False},
            "flood_vulnerability": {"status": states["inarisk_flood_vulnerability"], "numeric_extraction_authorized": False},
            "landslide_vulnerability": {"status": states["inarisk_landslide_vulnerability"], "numeric_extraction_authorized": False},
        },
        "source_qualification": ref(SOURCE_QUAL),
        "milestone_spec": ref(SPEC),
        "promoted_numeric_component_count": 3,
        "materialized_component_observation_count": 57,
        "event_level_observed_impact_promoted": False,
        "undated_hazard_or_vulnerability_raster_aggregated": False,
        "dibi_abbreviated_fields_semantically_reinterpreted": False,
        "historical_boundary_reconstruction_performed": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_loss_inferred": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(build_doc(payload), encoding="utf-8")
    print(json.dumps({
        "milestone26_evidence_qualification_complete": True,
        "materialized_component_observation_count": 57,
        "risk_synthesis_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
