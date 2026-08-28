from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_revision_mechanism_candidate.json"
LOCALIZATION = BASE / "bps_construction_revision_localization_2001_2004.json"
DATA = ROOT / "data" / "processed" / "bps" / "historical_construction_revision_mechanism_evidence.csv"

EXPECTED_EVIDENCE = {
    "construction_revision_mech_01": {
        "year": 2005,
        "publication_number": "05230.0609",
        "strength": "direct_confirmed",
    },
    "construction_revision_mech_02": {
        "year": 2005,
        "publication_number": "05230.0610",
        "strength": "direct_confirmed",
    },
    "construction_revision_mech_03": {
        "year": 2009,
        "publication_number": "03210.0803",
        "strength": "direct_confirmed",
    },
    "construction_revision_mech_04": {
        "year": 2010,
        "publication_number": "",
        "strength": "direct_method_support_not_contemporaneous",
    },
    "construction_revision_mech_05": {
        "year": 2006,
        "publication_number": "07330.0608",
        "strength": "direct_confirmed",
    },
    "construction_revision_mech_06": {
        "year": 2006,
        "publication_number": "05230.0607",
        "strength": "direct_confirmed",
    },
}


def _official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def _rows() -> list[dict[str, str]]:
    with DATA.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    localization = json.loads(LOCALIZATION.read_text(encoding="utf-8"))
    rows = _rows()

    assert manifest["schema"] == "ranah-observatory/bps-construction-revision-mechanism-candidate/v1"

    binding = manifest["revision_checkpoint_binding"]
    assert binding["localization_checkpoint"] == LOCALIZATION.name
    assert binding["major_break_checkpoint"] == "bps_construction_financing_major_release_break_2002_2003.json"
    assert binding["revision_event_confirmed"] is True
    assert binding["revision_mechanism_documented"] is False
    assert binding["affected_confirmed_revised_years"] == [2001, 2002, 2003]

    refinement = localization["classification_refinement"]
    assert refinement["revision_event_confirmed_by_bps_status_marker"] is True
    assert refinement["revision_mechanism_or_formula_documented"] is False
    assert localization["revision_localization"]["revision_first_confirmed_by_examined_yearbook_vintage"] == (
        "Statistik Indonesia 2005/2006"
    )

    period = manifest["period_evidence"]

    update = period["directory_update_2005"]
    assert update["status"] == "confirmed"
    assert update["source"] == "Katalog Publikasi 2007"
    assert _official_bps_url(update["official_page_url"])
    assert update["profile_java_publication_number"] == "05230.0609"
    assert update["profile_outside_java_publication_number"] == "05230.0610"
    assert update["profile_outside_java_relevant_to_sumatera_barat"] is True
    assert "end of 2005" in update["finding"]

    frame = period["directory_update_sampling_frame_use"]
    assert frame["status"] == "confirmed"
    assert frame["publication_number"] == "03210.0803"
    assert frame["bps_catalog_number"] == "1103004"
    assert frame["data_year"] == 2005
    assert frame["national_coverage"] is True
    assert frame["covered_establishments"] == 20_450
    assert frame["approximate_universe_establishments"] == 80_000
    assert frame["recorded_data_use"] == (
        "Sampling frame kegiatan survei konstruksi sebagai direktori awal perusahaan konstruksi"
    )
    assert frame["artifact_sha256_available_in_repository"] is False

    method = period["annual_survey_expansion_method_support"]
    assert method["status"] == "confirmed_later_method_not_contemporaneous"
    assert "take-all" in method["finding_sampling"]
    assert "take-some" in method["finding_sampling"]
    assert "expansion factor" in method["finding_estimation"]
    assert "2010" in method["temporal_limitation"]
    assert method["artifact_sha256_available_in_repository"] is False

    environment = period["revised_series_publication_environment"]
    assert environment["status"] == "confirmed"
    assert environment["construction_statistics_2005_publication_number"] == "05230.0607"
    assert "Annual Construction Establishment Survey" in environment["finding"]

    candidate = manifest["candidate_mechanism"]
    assert candidate["id"] == "sampling_frame_refresh_plus_qualification_based_expansion_reestimation"
    assert candidate["status"] == "operationally_plausible_period_link_confirmed_causal_revision_link_unproven"
    assert len(candidate["supporting_chain"]) == 5
    assert len(candidate["evidence_missing_for_causal_confirmation"]) == 5
    assert candidate["causal_claim_authorized"] is False

    numeric = manifest["numerical_consistency"]
    localization_numeric = localization["revision_localization"]
    assert Decimal(str(numeric["year_2001_later_to_earlier_ratio"])) == Decimal(
        str(localization_numeric["year_2001_later_to_earlier_ratio"])
    )
    assert Decimal(str(numeric["year_2002_later_to_earlier_ratio"])) == Decimal(
        str(localization_numeric["year_2002_later_to_earlier_ratio"])
    )
    assert numeric["common_2001_2002_scale_pattern"] is True
    assert numeric["pattern_compatible_with_multiplier_change"] is True
    assert numeric["pattern_proves_multiplier_change"] is False

    classification = manifest["classification"]
    assert classification["revision_event"] == "confirmed"
    assert classification["revision_timing_by_vintage"] == "localized"
    assert classification["sampling_frame_refresh"] == "confirmed"
    assert classification["sampling_frame_use_for_construction_surveys"] == "confirmed"
    assert classification["qualification_based_population_expansion"] == (
        "confirmed_in_later_bps_method_documentation"
    )
    assert classification["candidate_mechanism"] == "plausible_and_operationally_linked"
    assert classification["causal_mechanism"] == "unproven"

    gate = manifest["gate"]
    assert gate["retain_all_vintages"] is True
    assert gate["silent_overwrite_authorized"] is False
    assert gate["single_continuous_1998_2006_trajectory_authorized"] is False
    assert gate["cross_vintage_bridge_authorized"] is False
    assert gate["apply_common_2001_2002_ratio_as_backcast_factor_authorized"] is False
    assert gate["attribute_revision_to_2005_directory_update_authorized"] is False
    assert gate["canonical_fiscal_mapping_authorized"] is False
    assert gate["panel_v3_integration_authorized"] is False
    assert gate["causal_claim_authorized"] is False

    assert len(rows) == len(EXPECTED_EVIDENCE)
    by_id = {row["evidence_id"]: row for row in rows}
    assert set(by_id) == set(EXPECTED_EVIDENCE)
    assert len(by_id) == len(rows)

    for evidence_id, expected in EXPECTED_EVIDENCE.items():
        row = by_id[evidence_id]
        assert int(row["evidence_year"]) == expected["year"]
        assert row["source_publication_number"] == expected["publication_number"]
        assert row["evidence_strength"] == expected["strength"]
        assert row["causal_revision_link_status"] != "proven"

    assert by_id["construction_revision_mech_02"]["period_specificity"] == "contemporaneous"
    assert "Sumatera Barat" in by_id["construction_revision_mech_02"]["notes"]
    assert by_id["construction_revision_mech_04"]["period_specificity"] == "later_method_support"
    assert "does not prove" in by_id["construction_revision_mech_04"]["notes"]

    return {
        "evidence_rows": len(rows),
        "revision_event_confirmed": True,
        "candidate_mechanism": candidate["id"],
        "candidate_status": candidate["status"],
        "causal_revision_link_proven": False,
        "cross_vintage_bridge_authorized": False,
        "backcast_factor_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
