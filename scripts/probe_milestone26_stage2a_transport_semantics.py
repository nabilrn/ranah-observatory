#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts.probe_milestone26_event_impact_retrieval import parse_html

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_stage2a_transport_diagnostic_contract.json"
OUT = ROOT / "data/manifests/milestone26_stage2a_transport_diagnostic.json"
RAW = ROOT / "data/processed/bnpb/m26_stage2_transport_diagnostic"
EXPECTED_HEADERS = [
    "No.", "Kode Identitas Bencana", "ID Kabupaten", "Tanggal Kejadian", "Kejadian",
    "Lokasi", "Kabupaten", "Provinsi", "Kronologi & Dokumentasi", "Penyebab",
    "Meninggal", "Hilang", "Terluka", "Rumah Rusak", "Rumah Terendam", "Fasum Rusak"
]


def request(url: str, method: str, form: dict[str, str] | None) -> tuple[str, str, bytes]:
    data = None if form is None else urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
            "Accept": "text/html,application/xhtml+xml,*/*",
            **({"Content-Type": "application/x-www-form-urlencoded"} if data is not None else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["schema"] == "ranah-observatory/milestone26-stage2a-transport-diagnostic-contract/v1"
    assert contract["locked_before_diagnostic_requests"] is True
    for key in (
        "impact_cell_values_inspection_authorized", "row_level_impact_promotion_authorized",
        "impact_aggregation_authorized", "duplicate_resolution_authorized", "target_contract_change_authorized",
        "cross_component_temporal_aggregation_authorized", "risk_synthesis_authorized",
        "statistical_model_fit_authorized", "causal_claim_authorized", "monetary_loss_inference_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        assert contract[key] is False

    RAW.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for variant in contract["variants"]:
        final_url, content_type, body = request(contract["source_url"], variant["method"], variant["form"])
        path = RAW / f"{variant['id']}.html"
        path.write_bytes(body)
        parser = parse_html(body)
        header_match = parser.headers == EXPECTED_HEADERS
        if not header_match:
            raise RuntimeError(f"table header drift in {variant['id']}: {parser.headers}")
        results.append({
            "id": variant["id"],
            "method": variant["method"],
            "form": variant["form"],
            "final_url": final_url,
            "content_type": content_type,
            "raw_path": path.relative_to(ROOT).as_posix(),
            "row_count": len(parser.rows),
            "header_match": True,
            "impact_cell_values_inspected": False,
        })

    by_id = {row["id"]: row for row in results}
    if by_id["get_default"]["row_count"] > 0 and by_id["post_banjir_2026"]["row_count"] == 0 and by_id["post_tanah_longsor_2026"]["row_count"] == 0:
        classification = "post_filter_transport_not_proven"
    elif by_id["post_banjir_2026"]["row_count"] > 0 or by_id["post_tanah_longsor_2026"]["row_count"] > 0:
        classification = "post_filter_transport_proven"
    else:
        classification = "transport_diagnostic_inconclusive"

    payload = {
        "schema": "ranah-observatory/milestone26-stage2a-transport-diagnostic/v1",
        "milestone": 26,
        "stage": "2a_event_impact_transport_diagnostic",
        "results": results,
        "classification": classification,
        "target_2024_row_count_observed": by_id["post_banjir_2024_repeat"]["row_count"],
        "impact_cell_values_inspected": False,
        "row_level_impact_promotion_authorized": False,
        "impact_aggregation_performed": False,
        "target_contract_changed": False,
        "risk_synthesis_authorized": False,
        "causal_claim_created": False,
        "monetary_loss_inferred": False,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"classification": classification, "row_counts": {r['id']: r['row_count'] for r in results}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
