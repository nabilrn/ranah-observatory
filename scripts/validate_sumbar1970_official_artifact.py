from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "validation" / "historical" / "sumbar1970" / "artifact_manifest.json"
INDEX = ROOT / "data" / "validation" / "historical" / "sumbar1970" / "structural_index.json"
EXPECTED_SHA256 = "f0a441692e25b68f0ac8f4559509d14d707f527c20471832eb06c9a949eae325"
EXPECTED_BYTES = 46_897_865
EXPECTED_PAGES = 138
EXPECTED_DOMAINS = {
    "population",
    "education",
    "health",
    "agriculture",
    "transport",
    "trade",
    "public_finance",
    "industry",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> dict[str, int | bool]:
    manifest = _load(MANIFEST)
    index = _load(INDEX)

    assert manifest["schema"] == "ranah-observatory/sumbar1970-official-artifact/v1"
    assert manifest["title"] == "Sumatera Barat Dalam Angka Tahun 1970"
    assert manifest["catalog_number"] == "1102001.13"
    assert manifest["publication_number"] == "13000.1970"
    assert manifest["artifact_sha256"] == EXPECTED_SHA256
    assert manifest["artifact_bytes"] == EXPECTED_BYTES
    assert manifest["pdf_page_count"] == EXPECTED_PAGES
    assert urlparse(manifest["official_page_url"]).hostname == "sumbar.bps.go.id"
    assert urlparse(manifest["official_direct_artifact_url"]).hostname == "web-api.bps.go.id"
    assert manifest["raw_pdf_committed"] is False
    assert manifest["numeric_extraction_started"] is False
    assert manifest["numeric_promotion_authorized"] is False
    assert manifest["table_semantics_verified"] is False
    assert manifest["current_boundary_mapping_authorized"] is False

    assert index["schema"] == "ranah-observatory/sumbar1970-structural-discovery-index/v1"
    assert index["artifact_sha256"] == EXPECTED_SHA256
    assert index["source_pdf_page_count"] == EXPECTED_PAGES
    assert index["numeric_promotion_authorized"] is False
    assert index["extraction_method"] == "pdftotext-layout-built-in-text-layer-only-no-ocr"
    assert index["evidentiary_role"] == "page discovery only; snippets are not canonical numeric observations"
    assert set(index["domains"]) == EXPECTED_DOMAINS
    assert all(matches == [] for matches in index["domains"].values())
    assert index["text_layer_char_count"] == 28_290
    assert index["text_layer_page_chunks"] == 139

    return {
        "artifact_bytes": manifest["artifact_bytes"],
        "pdf_pages": manifest["pdf_page_count"],
        "text_chars": index["text_layer_char_count"],
        "numeric_promotion_authorized": manifest["numeric_promotion_authorized"],
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
