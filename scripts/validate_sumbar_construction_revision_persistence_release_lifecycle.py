from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_revision_persistence_release_lifecycle_2002_2006.json"
LOCALIZATION = BASE / "bps_construction_revision_localization_2001_2004.json"
MECHANISM = BASE / "bps_construction_revision_mechanism_candidate.json"


def _official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    localization = json.loads(LOCALIZATION.read_text(encoding="utf-8"))
    mechanism = json.loads(MECHANISM.read_text(encoding="utf-8"))

    assert manifest["schema"] == (
        "ranah-observatory/bps-construction-revision-persistence-release-lifecycle-2002-2006/v1"
    )
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["canonical_historical_geography_id"] == "idn.13.h1958"
    assert manifest["unit"] == "thousand rupiahs"

    assert manifest["depends_on"]["revision_localization"] == LOCALIZATION.name
    assert manifest["depends_on"]["mechanism_candidate"] == MECHANISM.name

    earlier = manifest["earlier_vintage"]
    source_later = localization["later_yearbook"]
    assert earlier["publication_number"] == source_later["publication_number"] == "07330.0608"
    assert _official_bps_url(earlier["official_page_url"])

    for year in (2002, 2003, 2004, 2005):
        key = str(year)
        assert earlier["sumatera_barat"][key] == source_later["sumatera_barat"][key]

    later = manifest["later_dedicated_series"]
    assert later["title"] == "Statistik Tahunan Perusahaan Konstruksi 2002-2006"
    assert later["catalog_number"] == "6301003"
    assert later["publication_number"] == "05340.0704"
    assert later["issn_isbn"] == "1978-9149"
    assert later["official_bps_metadata_release_date"] == "2007-05-15"
    assert later["pdf_preface_date_text"] == "Jakarta, Nopember 2007"
    assert later["metadata_preface_date_conflict_preserved"] is True
    assert _official_bps_url(later["official_page_url"])
    assert _official_bps_url(later["official_deep_search_url"])
    assert "Annual Construction Establishment Surveys" in later["series_basis"]
    assert later["table_number"] == "14"

    expected_later = {
        "2002": 717_299_178,
        "2003": 844_516_928,
        "2004": 956_619_300,
        "2005": 1_315_105_562,
        "2006": 1_324_786_176,
    }
    for year, expected in expected_later.items():
        assert later["sumatera_barat"][year]["value_thousand_rupiah"] == expected

    assert later["sumatera_barat"]["2006"]["status"] == "preliminary"
    for year in ("2002", "2003", "2004", "2005"):
        assert later["sumatera_barat"][year]["status"] == "published_without_provisional_marker"

    comparison = manifest["cross_vintage_comparison"]
    for year in ("2002", "2003"):
        row = comparison[year]
        assert row["earlier_value"] == row["later_value"]
        assert row["delta"] == 0
        assert row["earlier_status"] == "revised"
        assert row["classification"] == (
            "explicit_revision_persists_exactly_into_later_dedicated_series"
        )

    row_2004 = comparison["2004"]
    assert row_2004["delta"] == row_2004["later_value"] - row_2004["earlier_value"] == 24_177_485
    assert Decimal(str(row_2004["delta_percent"])).quantize(Decimal("0.000001")) == Decimal("2.592922")
    assert row_2004["earlier_status"] == "preliminary"
    assert row_2004["classification"] == "ordinary_provisional_to_later_release_maturation"

    row_2005 = comparison["2005"]
    assert row_2005["delta"] == row_2005["later_value"] - row_2005["earlier_value"] == 268_543_618
    assert Decimal(str(row_2005["delta_percent"])).quantize(Decimal("0.000001")) == Decimal("25.659601")
    assert row_2005["earlier_status"] == "estimated"
    assert row_2005["classification"] == "ordinary_estimated_to_later_release_maturation"

    inference = manifest["inference"]
    assert inference["revised_2002_2003_values_are_single_yearbook_anomaly"] is False
    assert inference["revised_2002_2003_values_persist_in_later_dedicated_bps_series"] is True
    assert inference["2004_2005_changes_are_distinguishable_by_prior_provisional_status"] is True
    assert inference["persistent_historical_revision_distinguished_from_release_maturation"] is True
    assert inference["persistence_proves_revision_mechanism"] is False
    assert inference["persistence_proves_2005_directory_update_caused_revision"] is False
    assert inference["persistence_authorizes_cross_vintage_backcast"] is False

    effect = manifest["mechanism_candidate_effect"]
    candidate = mechanism["candidate_mechanism"]
    assert effect["candidate_id"] == candidate["id"]
    assert effect["candidate_status_changed"] is False
    assert effect["candidate_status_remains"] == candidate["status"]
    assert candidate["causal_claim_authorized"] is False

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

    boundary = manifest["source_boundary"]
    assert boundary["official_bps_metadata_page_verified"] is True
    assert boundary["official_bps_deep_search_text_verified"] is True
    assert boundary["later_series_table_values_verified_from_bps_authored_publication_text_surface"] is True
    assert boundary["raw_pdf_sha256_available_in_repository"] is False

    return {
        "persistent_revised_years": [2002, 2003],
        "release_maturation_years": [2004, 2005],
        "revised_values_persist_exactly": True,
        "single_yearbook_anomaly": False,
        "causal_revision_link_proven": False,
        "cross_vintage_bridge_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
