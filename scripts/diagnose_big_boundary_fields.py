from __future__ import annotations

import json
import urllib.parse

from probe_big_sumbar_boundaries import LAYER_URL, fetch, json_body, normalize_code


def main() -> None:
    params = {
        "where": "1=1",
        "outFields": "OBJECTID,NAMOBJ,KDBBPS,KDPBPS,KDPKAB,KDPPUM,WADMKK,WADMPR,REMARK,METADATA",
        "returnGeometry": "false",
        "resultRecordCount": "1000",
        "orderByFields": "OBJECTID ASC",
        "f": "json",
    }
    result = fetch(f"{LAYER_URL}/query?{urllib.parse.urlencode(params)}")
    payload = json_body(result)
    if not isinstance(payload, dict):
        print(json.dumps({"transport": {k: v for k, v in result.items() if k != "body"}}, indent=2))
        raise SystemExit(1)

    features = payload.get("features") if isinstance(payload.get("features"), list) else []
    rows = [
        feature.get("attributes", {})
        for feature in features
        if isinstance(feature, dict) and isinstance(feature.get("attributes"), dict)
    ]

    province_values = sorted(
        {str(row.get("WADMPR") or "").strip() for row in rows if str(row.get("WADMPR") or "").strip()}
    )
    sumbar = [
        row
        for row in rows
        if "sumatera barat" in str(row.get("WADMPR") or "").strip().casefold()
    ]
    if not sumbar:
        target_names = {
            "kepulauan mentawai", "pesisir selatan", "solok", "sijunjung",
            "tanah datar", "padang pariaman", "agam", "lima puluh kota",
            "pasaman", "solok selatan", "dharmasraya", "pasaman barat",
            "padang", "sawahlunto", "padang panjang", "bukittinggi",
            "payakumbuh", "pariaman",
        }
        sumbar = [
            row
            for row in rows
            if str(row.get("WADMKK") or row.get("NAMOBJ") or "").strip().casefold() in target_names
        ]

    field_nonblank_counts = {}
    for field in ("KDBBPS", "KDPBPS", "KDPKAB", "KDPPUM", "WADMKK", "WADMPR", "NAMOBJ"):
        field_nonblank_counts[field] = sum(1 for row in rows if str(row.get(field) or "").strip())

    summary = {
        "transport": {key: value for key, value in result.items() if key != "body"},
        "row_count": len(rows),
        "exceeded_transfer_limit": payload.get("exceededTransferLimit"),
        "field_nonblank_counts": field_nonblank_counts,
        "province_value_count": len(province_values),
        "province_values": province_values,
        "sumbar_candidate_count": len(sumbar),
        "sumbar_candidates": [
            {
                "OBJECTID": row.get("OBJECTID"),
                "NAMOBJ": row.get("NAMOBJ"),
                "KDBBPS": row.get("KDBBPS"),
                "KDBBPS_normalized": normalize_code(row.get("KDBBPS")),
                "KDPBPS": row.get("KDPBPS"),
                "KDPKAB": row.get("KDPKAB"),
                "KDPPUM": row.get("KDPPUM"),
                "WADMKK": row.get("WADMKK"),
                "WADMPR": row.get("WADMPR"),
                "REMARK": row.get("REMARK"),
                "METADATA": row.get("METADATA"),
            }
            for row in sumbar
        ],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
