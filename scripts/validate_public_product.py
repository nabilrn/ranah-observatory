from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERVIEW = ROOT / "site" / "data" / "overview.json"
DEFAULT_LEDGER = ROOT / "publication" / "v0.1" / "claim-ledger.csv"
M36_MANIFEST = ROOT / "data" / "validation" / "climate" / "station" / "m36" / "manifest.json"
M36_OVERLAP = ROOT / "data" / "validation" / "climate" / "station" / "m36" / "station-overlap.json"
M45_MANIFEST = ROOT / "data" / "manifests" / "milestone45_bnpb_total_events_candidate.json"
M46_MANIFEST = ROOT / "data" / "manifests" / "milestone46_total_events_panel_integration.json"
M45_PATH = "data/manifests/milestone45_bnpb_total_events_candidate.json"
M46_PATH = "data/manifests/milestone46_total_events_panel_integration.json"
DISASTER_SOURCE_PATHS = {M45_PATH, M46_PATH}

STATE_MAP = {
    "supported": "publishable_bounded",
    "negative_result": "publishable_negative_result",
    "context": "context_only",
    "not_supported": "blocked",
}

EXPECTED_BLOCKED = {
    "B01_MONETARY_WASTED_POTENTIAL",
    "B02_THEORETICAL_MAXIMUM",
    "B03_CAUSAL_RESIDUAL",
    "B04_GUARANTEED_POLICY_GAIN",
    "B05_CAUSAL_RAINFALL_UNEMPLOYMENT",
    "B06_EVENT_COUNTS_AS_IMPACT",
    "B07_COMPOSITE_DISASTER_RISK",
    "B08_SENSITIVITY_AS_POLICY_EFFECT",
    "B09_POLICY_RANKING",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object JSON: {path}")
    return payload


def load_ledger(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ledger: dict[str, dict[str, str]] = {}
    for row in rows:
        claim_id = row.get("claim_id", "").strip()
        assert claim_id, "claim ledger contains an empty claim_id"
        assert claim_id not in ledger, f"duplicate claim id: {claim_id}"
        ledger[claim_id] = row
    return ledger


def require_claims(
    claim_ids: list[str],
    ledger: dict[str, dict[str, str]],
    *,
    expected_state: str | None = None,
    context: str,
) -> None:
    assert claim_ids, f"{context}: missing source_claim_ids"
    for claim_id in claim_ids:
        assert claim_id in ledger, f"{context}: unknown claim id {claim_id}"
        state = ledger[claim_id]["state"]
        if expected_state is not None:
            assert state == expected_state, (
                f"{context}: {claim_id} has ledger state {state}, "
                f"expected {expected_state}"
            )
        else:
            assert state != "blocked", f"{context}: blocked claim used as a positive fact: {claim_id}"


def validate_m36_story(story: dict[str, Any]) -> None:
    assert story.get("source_claim_ids") in (None, []), (
        "post-v0.1 M36 story must not pretend to be in the frozen v0.1 claim ledger"
    )
    source_paths = set(story.get("source_paths") or [])
    expected_paths = {
        "data/validation/climate/station/m36/manifest.json",
        "data/validation/climate/station/m36/station-overlap.json",
    }
    assert source_paths == expected_paths, "M36 story must cite the exact frozen evidence paths"

    manifest = load_json(M36_MANIFEST)
    overlap = load_json(M36_OVERLAP)
    assert manifest["classification"] == "station_overlap_directionally_supportive"
    assert manifest["offline_rebuild_supported"] is True
    assert manifest["raw_source_files_frozen"] is True
    assert manifest["causal_claim_authorized"] is False
    assert manifest["chirps_baseline_modified"] is False
    assert manifest["publication_package_modified"] is False

    annual = {int(row["year"]): row for row in overlap["annual"]}
    assert annual[1997]["valid_prcp_days"] == 345
    assert annual[1998]["valid_prcp_days"] == 340
    assert annual[1997]["annual_prcp_mm"] == 774.192
    assert annual[1998]["annual_prcp_mm"] == 2730.5
    assert overlap["comparison"]["classification"] == "station_overlap_directionally_supportive"
    assert overlap["comparison"]["comparison_scope"] == "directional_independent_overlap_only"
    assert overlap["conclusions"]["safe_to_relabel_chirps_as_observed"] is False
    assert overlap["conclusions"]["safe_to_mark_global_chirps_station_validation_complete"] is False
    assert overlap["conclusions"]["causal_claim_authorized"] is False

    copy = " ".join(
        str(story.get(key, ""))
        for key in ("title", "plain_language", "why_it_matters", "caveat")
    )
    for token in ("345", "340", "774.192", "2,730.500"):
        assert token in copy, f"M36 public copy lost frozen fact {token}"


def validate_m45_m46_disaster_story(story: dict[str, Any]) -> None:
    assert story.get("source_claim_ids") in (None, []), (
        "post-v0.1 M45/M46 disaster story must use frozen evidence paths, not the v0.1 claim ledger"
    )
    assert set(story.get("source_paths") or []) == DISASTER_SOURCE_PATHS, (
        "M45/M46 disaster story must cite the exact frozen milestone manifests"
    )

    m45 = load_json(M45_MANIFEST)
    m46 = load_json(M46_MANIFEST)
    assert m45["indicator_id"] == "total_disaster_events"
    assert m45["period"] == [2010, 2024]
    assert m45["observation_count"] == 285
    assert m45["geography_count"] == 19
    assert m45["years_count"] == 15
    assert m45["complete_geography_year_matrix"] is True
    assert m45["geography_contract"]["exact_polygon_harmonization"] == "not_proven"
    assert m45["geography_contract"]["generic_comparable_flag"] == "unset"
    assert m45["qualification"]["within_source_longitudinal_use_authorized_with_caveat"] is True
    assert m45["qualification"]["type_specific_interpretation_forbidden"] is True
    assert m45["qualification"]["true_incidence_claim_forbidden"] is True

    assert m46["integration_success"] is True
    assert m46["added_indicator_id"] == "total_disaster_events"
    assert m46["added_observation_count"] == 133
    assert m46["base_observation_count"] == 2679
    assert m46["long_observation_count"] == 2812
    assert m46["indicator_count"] == 23
    assert m46["total_event_full_canonical_period"] == [2010, 2024]
    assert m46["total_event_panel_period"] == [2018, 2024]
    assert m46["total_event_2025_state"] == "missing_not_zero"
    assert m46["total_event_comparable_flag"] == "unset"
    assert m46["exact_polygon_harmonization_proven"] is False
    assert m46["causal_analysis_performed"] is False
    assert m46["cross_indicator_aggregation_performed"] is False
    assert m46["imputation_performed"] is False
    assert m46["zero_fill_performed"] is False

    copy = " ".join(
        str(story.get(key, ""))
        for key in ("title", "plain_language", "why_it_matters", "caveat")
    ).casefold()
    for token in ("285", "19", "15", "133", "2025"):
        assert token in copy, f"M45/M46 public copy lost frozen fact {token}"
    assert "missing" in copy and "bukan nol" in copy
    assert "bukan" in copy and "kerugian" in copy


def validate_disaster_headline_stat(stat: dict[str, Any]) -> None:
    assert set(stat.get("source_paths") or []) == DISASTER_SOURCE_PATHS
    assert stat.get("source_claim_ids") in (None, [])
    assert str(stat.get("value")) == "285"
    text = " ".join(str(stat.get(field, "")) for field in ("label", "detail")).casefold()
    for token in ("19", "15", "2010", "2024", "2025"):
        assert token in text, f"disaster headline stat lost frozen fact {token}"
    assert "missing" in text and "bukan nol" in text


def validate(overview_path: Path = DEFAULT_OVERVIEW, ledger_path: Path = DEFAULT_LEDGER) -> dict[str, int]:
    overview = load_json(overview_path)
    ledger = load_ledger(ledger_path)

    assert overview["schema"] == "ranah-observatory/public-overview/v1"
    assert overview["version"] == "0.1.0"
    assert overview["language"] == "id"

    stories = overview.get("stories")
    boundaries = overview.get("boundaries")
    stats = overview.get("headline_stats")
    assert isinstance(stories, list) and stories, "stories must be a non-empty list"
    assert isinstance(boundaries, list) and boundaries, "boundaries must be a non-empty list"
    assert isinstance(stats, list) and stats, "headline_stats must be a non-empty list"

    story_ids: set[str] = set()
    m36_count = 0
    m45_m46_count = 0
    for story in stories:
        assert isinstance(story, dict)
        story_id = str(story.get("id", "")).strip()
        assert story_id, "story missing id"
        assert story_id not in story_ids, f"duplicate story id: {story_id}"
        story_ids.add(story_id)

        state = story.get("evidence_state")
        assert state in {*STATE_MAP.keys(), "supported_post_v0_1"}, (
            f"{story_id}: unknown public evidence state {state}"
        )
        for field in ("category", "title", "plain_language", "why_it_matters", "caveat"):
            assert str(story.get(field, "")).strip(), f"{story_id}: missing {field}"

        if state == "supported_post_v0_1":
            assert story_id == "rainfall-1998-crosscheck", (
                "only the frozen M36 station cross-check is currently allowed as post-v0.1 supported evidence"
            )
            validate_m36_story(story)
            m36_count += 1
            continue

        if story_id == "disaster-components":
            assert state == "context", "M45/M46 disaster story must remain context, not a positive impact claim"
            validate_m45_m46_disaster_story(story)
            m45_m46_count += 1
            continue

        expected_ledger_state = STATE_MAP[state]
        require_claims(
            list(story.get("source_claim_ids") or []),
            ledger,
            expected_state=expected_ledger_state,
            context=f"story {story_id}",
        )
        assert not story.get("source_paths"), (
            f"story {story_id}: v0.1 claim-ledger story should use claim IDs, not ad-hoc source paths"
        )

    assert m36_count == 1, "public overview must contain exactly one bounded post-v0.1 M36 story"
    assert m45_m46_count == 1, "public overview must contain exactly one bounded M45/M46 disaster context story"

    disaster_stat_count = 0
    for index, stat in enumerate(stats):
        assert isinstance(stat, dict)
        for field in ("value", "label", "detail"):
            assert str(stat.get(field, "")).strip(), f"headline stat {index}: missing {field}"
        claim_ids = list(stat.get("source_claim_ids") or [])
        source_paths = list(stat.get("source_paths") or [])
        assert bool(claim_ids) ^ bool(source_paths), (
            f"headline stat {index}: use claim IDs or source paths, not both/neither"
        )
        if claim_ids:
            require_claims(claim_ids, ledger, context=f"headline stat {index}")
        elif set(source_paths) == DISASTER_SOURCE_PATHS:
            validate_disaster_headline_stat(stat)
            disaster_stat_count += 1
        else:
            assert source_paths == ["data/validation/climate/station/m36/manifest.json"], (
                f"headline stat {index}: unsupported direct evidence path"
            )

    assert disaster_stat_count == 1, "public overview must contain exactly one M45/M46 disaster coverage headline stat"

    boundary_ids: set[str] = set()
    for boundary in boundaries:
        assert isinstance(boundary, dict)
        claim_id = str(boundary.get("claim_id", "")).strip()
        assert claim_id and claim_id not in boundary_ids, f"duplicate/empty boundary claim {claim_id}"
        boundary_ids.add(claim_id)
        assert boundary.get("evidence_state") == "not_supported"
        for field in ("title", "reason"):
            assert str(boundary.get(field, "")).strip(), f"boundary {claim_id}: missing {field}"
        require_claims(
            [claim_id],
            ledger,
            expected_state="blocked",
            context=f"boundary {claim_id}",
        )

    assert boundary_ids == EXPECTED_BLOCKED, (
        f"blocked-claim coverage drift: missing={sorted(EXPECTED_BLOCKED-boundary_ids)}, "
        f"extra={sorted(boundary_ids-EXPECTED_BLOCKED)}"
    )

    hero_text = " ".join(str(value) for value in overview.get("hero", {}).values()).casefold()
    assert "belum ada" in hero_text
    assert "rupiah" in hero_text
    assert "tidak" in hero_text or "belum" in hero_text

    return {
        "stories": len(stories),
        "headline_stats": len(stats),
        "blocked_boundaries": len(boundaries),
        "ledger_claims": len(ledger),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Ranah Observatory public-product claim gating")
    parser.add_argument("--overview", type=Path, default=DEFAULT_OVERVIEW)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()
    result = validate(args.overview, args.ledger)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
