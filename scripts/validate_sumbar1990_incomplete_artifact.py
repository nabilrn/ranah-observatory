from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "validation" / "historical" / "sumbar1990" / "incomplete_artifact_manifest.json"
EXPECTED_SHA256 = "317fbbb6f2ec465cc444ed753211532a148e99c114b712b55a284bcae827c734"
EXPECTED_BYTES = 14_702_296
EXPECTED_PAGES = 58


def validate() -> dict[str, int | bool]:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert m["schema"] == "ranah-observatory/sumbar1990-incomplete-official-artifact/v1"
    assert m["title"] == "Sumatera Barat Dalam Angka Tahun 1990"
    assert m["catalog_number"] == "1102001.13"
    assert m["publication_number"] == "13000.1991"
    assert m["artifact_sha256"] == EXPECTED_SHA256
    assert m["artifact_bytes"] == EXPECTED_BYTES
    assert m["pdf_page_count"] == EXPECTED_PAGES
    assert m["builtin_text_char_count"] == 1450
    assert urlparse(m["official_page_url"]).hostname == "sumbar.bps.go.id"
    assert urlparse(m["official_direct_artifact_url"]).hostname == "web-api.bps.go.id"
    assert m["raw_pdf_committed"] is False

    review = m["visual_completeness_review"]
    assert review["cover_present"] is True
    assert review["sampled_pdf_pages"] == [1, 30, 58]
    assert review["sampled_page_30_is_table_of_contents"] is True
    assert review["sampled_toc_references_tables_through_printed_page"] == 396
    assert review["final_pdf_page_content"] == "methodology section 8. Regional Income"
    assert review["final_pdf_page_printed_roman"] == "lix"
    assert review["data_table_body_present_in_downloaded_pdf"] is False
    assert review["review_method"].startswith("manual visual review of rasterized pages")

    assert m["artifact_role"] == "official digitized front matter / table-of-contents / methodology fragment only"
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
