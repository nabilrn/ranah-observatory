from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "validation" / "historical" / "sumbar1980" / "incomplete_artifact_manifest.json"
EXPECTED_SHA256 = "313384e4dd96b48b906eacd9422c5100ed55d5770bb6a6f5202b1c288ad7e606"
EXPECTED_BYTES = 5_361_943
EXPECTED_PAGES = 22


def validate() -> dict[str, int | bool]:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert m["schema"] == "ranah-observatory/sumbar1980-incomplete-official-artifact/v1"
    assert m["title"] == "Sumatera Barat Dalam Angka Tahun 1980"
    assert m["catalog_number"] == "1102001.13"
    assert m["publication_number"] == "13000.1981"
    assert m["artifact_sha256"] == EXPECTED_SHA256
    assert m["artifact_bytes"] == EXPECTED_BYTES
    assert m["pdf_page_count"] == EXPECTED_PAGES
    assert urlparse(m["official_page_url"]).hostname == "sumbar.bps.go.id"
    assert urlparse(m["official_direct_artifact_url"]).hostname == "web-api.bps.go.id"

    review = m["visual_completeness_review"]
    assert review["cover_present"] is True
    assert review["table_of_contents_present"] is True
    assert review["last_pdf_page_is_table_of_contents"] is True
    assert review["toc_references_population_table_start_printed_page"] == 103
    assert review["toc_references_regional_income_tables_through_printed_page"] == 788
    assert review["data_table_body_present_in_downloaded_pdf"] is False
    assert review["review_method"] == "manual visual review of exact official PDF screenshots"

    assert m["artifact_role"] == "official digitized front matter / table-of-contents fragment only"
    assert m["full_publication_artifact_acquired"] is False
    assert m["historical_anchor_satisfied"] is False
    assert m["numeric_extraction_started"] is False
    assert m["numeric_promotion_authorized"] is False

    return {
        "artifact_bytes": m["artifact_bytes"],
        "pdf_pages": m["pdf_page_count"],
        "full_publication_artifact_acquired": m["full_publication_artifact_acquired"],
        "numeric_promotion_authorized": m["numeric_promotion_authorized"],
    }


def main() -> int:
    print(json.dumps(validate(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
