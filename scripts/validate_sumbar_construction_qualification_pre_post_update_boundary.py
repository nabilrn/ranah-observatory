from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_qualification_pre_post_update_acquisition_boundary.json"
MECHANISM = BASE / "bps_construction_revision_mechanism_candidate.json"
PERIOD = BASE / "bps_construction_revision_period_method_support_2004_2009.json"
DATA = ROOT / "data" / "processed" / "bps" / "historical_construction_qualification_sumbar_2003.csv"


def _official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def _rows() -> list[dict[str, str]]:
    with DATA.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mechanism = json.loads(MECHANISM.read_text(encoding="utf-8"))
    period = json.loads(PERIOD.read_text(encoding="utf-8"))
    rows = _rows()

    assert manifest["schema"] == (
        "ranah-observatory/bps-construction-qualification-pre-post-update-acquisition-boundary/v1"
    )
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["canonical_historical_geography_id"] == "idn.13.h1958"
    assert manifest["depends_on"]["mechanism_candidate"] == MECHANISM.name
    assert manifest["depends_on"]["period_method_support"] == PERIOD.name

    pre = manifest["pre_update_published_baseline"]
    assert pre["status"] == "acquired_and_tabulated"
    assert pre["year"] == 2003
    assert pre["title"] == "Statistik Konstruksi 2004"
    assert pre["publication_number"] == "05230.0506"
    assert pre["legacy_catalog_number_on_pdf"] == "6513"
    assert pre["isbn"] == "979-724-383-4"
    assert pre["official_bps_release_date"] == "2005-09-12"
    assert _official_bps_url(pre["official_page_url"])
    assert pre["table_number"] == "4.3"
    assert "KUALIFIKASI" in pre["table_title"]
    assert pre["district_row_count"] == 16
    assert pre["processed_path"] == DATA.relative_to(ROOT).as_posix()
    assert "not labeled or treated as the exact old sampling frame" in pre["interpretation_boundary"]

    expected_totals = {"B": 0, "M1": 16, "M2": 134, "K1": 334, "K2": 1084, "K3": 1314, "total": 2882}
    assert pre["province_total"] == expected_totals
    assert len(rows) == 16
    assert all(row["source_year"] == "2003" for row in rows)
    assert all(row["source_geography"] == "Sumatera Barat" for row in rows)
    assert all(row["source_publication_number"] == "05230.0506" for row in rows)
    assert all(row["source_table"] == "4.3" for row in rows)

    computed = {
        "B": sum(int(row["qualification_B"]) for row in rows),
        "M1": sum(int(row["qualification_M1"]) for row in rows),
        "M2": sum(int(row["qualification_M2"]) for row in rows),
        "K1": sum(int(row["qualification_K1"]) for row in rows),
        "K2": sum(int(row["qualification_K2"]) for row in rows),
        "K3": sum(int(row["qualification_K3"]) for row in rows),
        "total": sum(int(row["total_establishments"]) for row in rows),
    }
    assert computed == expected_totals
    for row in rows:
        subtotal = sum(int(row[f"qualification_{key}"]) for key in ("B", "M1", "M2", "K1", "K2", "K3"))
        assert subtotal == int(row["total_establishments"]), row["district_name"]

    post = manifest["post_update_target"]
    assert post["status"] == "official_opac_record_recovered_softcopy_sso_gated"
    assert post["title"] == "Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005"
    assert post["publication_number"] == "05230.0610"
    assert post["legacy_catalog_number"] == "6507"
    assert post["isbn"] == "979-724-565-9"
    assert post["page_count_text"] == "xxiii + 647"
    assert post["scope_relevant_to_sumatera_barat"] is True
    assert post["opac_record_id"] == "111.0614.1380"
    for key in ("opac_search_url", "opac_detail_url", "opac_read_url", "softcopy_request_final_url"):
        assert _official_bps_url(post[key]), key
    assert post["exact_title_search_record_recovered"] is True
    assert post["matching_detail_and_read_record_id"] is True
    assert post["softcopy_request_final_url"] == "https://sso-pst.bps.go.id/login"
    assert post["softcopy_request_http_status"] == 200
    assert post["softcopy_response_content_type"] == "text/html; charset=utf-8"
    assert post["softcopy_pdf_signature"] is False
    assert post["softcopy_pdf_eof"] is False
    assert post["raw_pdf_acquired"] is False
    assert post["post_update_sumbar_qualification_composition_acquired"] is False

    provenance = manifest["opac_locator_provenance"]
    assert provenance["method"] == "public BPS OPAC exact-title GET search using the site's q field"
    assert provenance["search_query_title"] == post["title"]
    assert provenance["discovery_workflow_run_id"] == 33156939897
    assert provenance["discovery_workflow_job_id"] == 98801856553
    assert provenance["discovery_artifact_id"] == 9679984516
    assert len(provenance["discovery_artifact_zip_sha256"]) == 64
    assert provenance["verified_softcopy_workflow_run_id"] == 33157241994
    assert provenance["verified_softcopy_workflow_job_id"] == 98802837444
    assert provenance["verified_softcopy_artifact_id"] == 9680104397
    assert len(provenance["verified_softcopy_artifact_zip_sha256"]) == 64
    assert provenance["record_id_guessed_or_bruteforced"] is False

    comparison = manifest["comparison_gate"]
    assert comparison["pre_update_baseline_available"] is True
    assert comparison["post_update_comparable_table_available"] is False
    assert comparison["pre_post_qualification_comparison_authorized"] is False
    assert comparison["frame_change_quantification_authorized"] is False
    assert comparison["old_vs_new_sumbar_frame_counts_recovered"] is False
    assert comparison["causal_revision_attribution_authorized"] is False

    bounded = manifest["bounded_inference"]
    assert bounded["pre_update_2003_qualification_composition_confirmed"] is True
    assert bounded["post_update_source_identity_confirmed"] is True
    assert bounded["post_update_source_locator_confirmed"] is True
    assert bounded["post_update_raw_bytes_confirmed"] is False
    assert bounded["post_update_table_semantics_confirmed"] is False
    assert bounded["post_update_sumbar_values_confirmed"] is False
    assert bounded["opac_sso_gate_is_transport_access_blocker"] is True
    assert bounded["sso_gate_is_not_evidence_that_artifact_is_absent"] is True
    assert bounded["published_2003_baseline_is_not_asserted_as_exact_sampling_frame"] is True

    candidate = mechanism["candidate_mechanism"]
    assert candidate["id"] == "sampling_frame_refresh_plus_qualification_based_expansion_reestimation"
    assert candidate["causal_claim_authorized"] is False
    assert period["classification"]["frame_identity_with_2005_directory_update"] == "unproven"

    gate = manifest["gate"]
    assert gate["retain_all_vintages"] is True
    for key in (
        "silent_overwrite_authorized",
        "single_continuous_1998_2006_trajectory_authorized",
        "cross_vintage_bridge_authorized",
        "backcast_authorized",
        "attribute_revision_to_2005_directory_update_authorized",
        "causal_claim_authorized",
        "panel_v3_integration_authorized",
    ):
        assert gate[key] is False, key

    return {
        "pre_update_district_rows": len(rows),
        "pre_update_total_establishments": computed["total"],
        "post_update_opac_record_id": post["opac_record_id"],
        "post_update_raw_pdf_acquired": False,
        "pre_post_comparison_authorized": False,
        "causal_revision_link_proven": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
