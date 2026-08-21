#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "data/manifests/milestone26_design_gate.json"
REGISTRY = ROOT / "data/registries/m26-bnpb-source-candidates.csv"
OUT = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-source-qualification.csv"
MANIFEST = ROOT / "data/manifests/milestone26_source_qualification.json"
SNAPSHOT_DIR = ROOT / "data/processed/bnpb/m26_source_qualification"

EXPECTED_IDS = [
    "inarisk_capacity_2021",
    "inarisk_population_2020",
    "dibi_kabupaten_hidromet_2015_2024",
    "bnpb_event_impact_table",
    "inarisk_flood_hazard",
    "inarisk_landslide_hazard",
    "inarisk_flood_vulnerability",
    "inarisk_landslide_vulnerability",
    "inarisk_current_methodology",
]

EXPECTED_FINAL_STATES = {
    "inarisk_capacity_2021": "qualified_explicit_vintage_metadata",
    "inarisk_population_2020": "qualified_explicit_vintage_metadata",
    "dibi_kabupaten_hidromet_2015_2024": "qualified_explicit_coverage_metadata",
    "bnpb_event_impact_table": "field_surface_verified_retrieval_contract_pending",
    "inarisk_flood_hazard": "endpoint_verified_version_binding_unresolved",
    "inarisk_landslide_hazard": "endpoint_verified_version_binding_unresolved",
    "inarisk_flood_vulnerability": "endpoint_verified_version_binding_unresolved",
    "inarisk_landslide_vulnerability": "endpoint_verified_version_binding_unresolved",
    "inarisk_current_methodology": "framework_verified_current_surface",
}

ARC_EXTRA = {
    "inarisk_population_2020": ["info/iteminfo"],
    # The official DIBI service currently exposes duplicate logical layers 0 and 1.
    # Either may be used to verify the schema; a transient failure on one child
    # resource must not invalidate the service when the other independently
    # exposes the locked field surface.
    "dibi_kabupaten_hidromet_2015_2024": ["0", "1"],
}

EXPECTED_SERVICE_TOKENS = {
    "inarisk_capacity_2021": "INDEKS_KAPASITAS_2021",
    "inarisk_population_2020": "INARISKPOP_2020",
    "dibi_kabupaten_hidromet_2015_2024": "DIBI_Kabupaten_2015_2024",
    "inarisk_flood_hazard": "INDEKS_BAHAYA_BANJIR",
    "inarisk_landslide_hazard": "INDEKS_BAHAYA_TANAHLONGSOR",
    "inarisk_flood_vulnerability": "INDEKS_KERENTANAN_BANJIR",
    "inarisk_landslide_vulnerability": "INDEKS_KERENTANAN_TANAH_LONGSOR",
}


class M26ProbeError(RuntimeError):
    pass


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def read_registry() -> list[dict[str, str]]:
    with REGISTRY.open("r", encoding="utf-8", newline="") as handle:
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]
    ids = [row["source_id"] for row in rows]
    if ids != EXPECTED_IDS:
        raise M26ProbeError(f"M26 source registry order/identity drift: {ids}")
    if len(set(ids)) != len(ids):
        raise M26ProbeError("duplicate M26 source ids")
    return rows


def load_design() -> dict[str, Any]:
    payload = json.loads(DESIGN.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-design-gate/v1":
        raise M26ProbeError("unexpected M26 design schema")
    if payload.get("design_locked_before_live_source_probe") is not True:
        raise M26ProbeError("M26 design was not locked before source probe")
    for key in (
        "stage0_numeric_spatial_aggregation_authorized",
        "stage0_event_panel_materialization_authorized",
        "risk_synthesis_authorized",
        "cross_component_temporal_aggregation_authorized",
        "posthoc_source_family_search_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise M26ProbeError(f"M26 design boundary violated: {key}")
    if payload.get("preregistered_source_ids") != EXPECTED_IDS:
        raise M26ProbeError("M26 preregistered source set drift")
    if set(payload.get("numeric_extraction_authorized_states", [])) != {
        "qualified_explicit_vintage_metadata",
        "qualified_explicit_coverage_metadata",
    }:
        raise M26ProbeError("M26 numeric extraction state contract drift")
    return payload


def fetch(url: str, *, timeout: float = 45.0, retries: int = 3) -> tuple[int, str, str, bytes]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                    "Accept": "application/json,text/html,application/xhtml+xml,*/*",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return int(response.status), str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise M26ProbeError(f"request failed after retries: {url}") from last_error


def with_json_format(url: str) -> str:
    return url + ("&" if "?" in url else "?") + "f=pjson"


def normalize_text(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def canonical_snapshot(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def methodology_surface_qualifies(final_url: str, content_type: str, body: bytes) -> tuple[bool, str]:
    """Verify the current InaRISK methodology route without treating SPA text as raster-version evidence."""
    parsed = urlparse(final_url)
    route_ok = (
        parsed.scheme == "https"
        and parsed.hostname == "inarisk2.bnpb.go.id"
        and parsed.path.rstrip("/") == "/v4/metodologi"
    )
    html_ok = "text/html" in content_type.casefold()
    raw = body.decode("utf-8", errors="replace").casefold()
    visible = normalize_text(body).casefold()
    semantic_text_ok = "inarisk" in visible and ("metodologi" in visible or "menghitung risiko" in visible)
    spa_shell_ok = len(body) >= 100 and "<html" in raw and ("<script" in raw or "id=\"app\"" in raw or "id='app'" in raw)
    qualifies = route_ok and html_ok and (semantic_text_ok or spa_shell_ok)
    mode = "rendered_semantic_text" if semantic_text_ok else "official_route_html_spa_shell" if spa_shell_ok else "unverified"
    return qualifies, mode


def probe_arcgis(row: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    source_id = row["source_id"]
    base = row["source_url"].rstrip("/")
    status, final_url, content_type, body = fetch(with_json_format(base))
    if status != 200:
        raise M26ProbeError(f"ArcGIS HTTP {status}: {source_id}")
    try:
        primary = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise M26ProbeError(f"ArcGIS JSON parse failure: {source_id}") from exc
    if isinstance(primary, dict) and primary.get("error"):
        raise M26ProbeError(f"ArcGIS service error: {source_id}: {primary['error']}")

    snapshot: dict[str, Any] = {
        "source_id": source_id,
        "requested_url": with_json_format(base),
        "final_url": final_url,
        "content_type": content_type,
        "primary": primary,
        "extra": {},
    }
    for suffix in ARC_EXTRA.get(source_id, []):
        extra_url = with_json_format(base + "/" + suffix)
        try:
            extra_status, extra_final, extra_type, extra_body = fetch(extra_url)
            if extra_status != 200:
                raise M26ProbeError(f"ArcGIS extra HTTP {extra_status}: {source_id}/{suffix}")
            try:
                extra_payload = json.loads(extra_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise M26ProbeError(f"ArcGIS extra JSON parse failure: {source_id}/{suffix}") from exc
            if isinstance(extra_payload, dict) and extra_payload.get("error"):
                raise M26ProbeError(f"ArcGIS extra service error: {source_id}/{suffix}: {extra_payload['error']}")
            snapshot["extra"][suffix] = {
                "requested_url": extra_url,
                "final_url": extra_final,
                "content_type": extra_type,
                "payload": extra_payload,
            }
        except M26ProbeError as exc:
            if source_id != "dibi_kabupaten_hidromet_2015_2024":
                raise
            snapshot["extra"][suffix] = {
                "requested_url": extra_url,
                "error": str(exc),
            }

    expected = EXPECTED_SERVICE_TOKENS[source_id]
    service_identity = " ".join(str(primary.get(key, "")) for key in ("name", "serviceDescription", "mapName"))
    identity_ok = expected.casefold() in service_identity.casefold()
    if not identity_ok:
        raise M26ProbeError(f"ArcGIS source identity mismatch: {source_id}: {service_identity!r}")

    metadata: dict[str, Any] = {
        "service_identity": service_identity.strip(),
        "band_count": primary.get("bandCount"),
        "pixel_type": primary.get("pixelType"),
        "spatial_reference": (primary.get("spatialReference") or {}).get("wkid"),
        "full_extent": primary.get("fullExtent"),
    }

    if source_id == "inarisk_capacity_2021":
        qualifies = primary.get("bandCount") == 1 and "2021" in service_identity
        state = "qualified_explicit_vintage_metadata" if qualifies else "unavailable_or_unparseable"
        evidence = "official ImageServer identity explicitly includes 2021; single-band raster metadata verified" if qualifies else "capacity service failed explicit-vintage raster contract"
    elif source_id == "inarisk_population_2020":
        item = snapshot["extra"]["info/iteminfo"]["payload"]
        item_text = " ".join(str(item.get(key, "")) for key in ("title", "name", "description", "snippet", "summary"))
        metadata["item_title"] = item.get("title", "")
        qualifies = primary.get("bandCount") == 1 and "2020" in (service_identity + " " + item_text)
        state = "qualified_explicit_vintage_metadata" if qualifies else "unavailable_or_unparseable"
        evidence = "official ImageServer/item metadata explicitly binds population-distribution surface to 2020" if qualifies else "population service failed explicit-vintage metadata contract"
    elif source_id == "dibi_kabupaten_hidromet_2015_2024":
        required_fields = {"id_kab_bps", "NAMA_KAB", "Total_basa", "Total_keri"}
        qualified_layers: list[str] = []
        layer_fields: dict[str, list[str]] = {}
        for suffix in ARC_EXTRA[source_id]:
            extra = snapshot["extra"].get(suffix, {})
            layer = extra.get("payload") if isinstance(extra, dict) else None
            if not isinstance(layer, dict):
                continue
            field_names = [str(field.get("name", "")) for field in layer.get("fields", [])]
            layer_fields[suffix] = field_names
            if required_fields.issubset(set(field_names)):
                qualified_layers.append(suffix)
        metadata["layer_fields"] = layer_fields
        metadata["qualified_layer_ids"] = qualified_layers
        primary_layer_ids = [str(layer.get("id")) for layer in primary.get("layers", []) if isinstance(layer, dict)]
        metadata["primary_layer_ids"] = primary_layer_ids
        qualifies = "2015_2024" in service_identity and bool(qualified_layers)
        state = "qualified_explicit_coverage_metadata" if qualifies else "unavailable_or_unparseable"
        evidence = "official MapServer identity binds 2015-2024 and at least one declared kabupaten layer exposes BPS id plus locked aggregate hydromet fields" if qualifies else "DIBI service failed explicit-coverage/schema contract"
    else:
        raster_ok = primary.get("bandCount") == 1
        state = "endpoint_verified_version_binding_unresolved" if raster_ok else "unavailable_or_unparseable"
        evidence = "official single-band ImageServer endpoint verified; exact raster vintage/methodology binding remains absent" if raster_ok else "official endpoint did not satisfy basic raster metadata contract"

    return snapshot, {
        "qualification_state": state,
        "identity_evidence": evidence,
        "metadata_evidence": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
    }


def probe_html(row: dict[str, str]) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    source_id = row["source_id"]
    status, final_url, content_type, body = fetch(row["source_url"])
    if status != 200:
        raise M26ProbeError(f"HTML HTTP {status}: {source_id}")
    text = normalize_text(body)
    lower = text.casefold()
    metadata = {"text_length": len(text), "raw_length": len(body), "final_url": final_url, "content_type": content_type}
    if source_id == "bnpb_event_impact_table":
        required = [
            "tanggal kejadian",
            "kejadian",
            "kabupaten",
            "provinsi",
            "meninggal",
            "hilang",
            "terluka",
            "rumah rusak",
            "rumah terendam",
            "fasum rusak",
        ]
        present = [item for item in required if item in lower]
        metadata["required_fields"] = required
        metadata["present_fields"] = present
        qualifies = len(present) == len(required)
        state = "field_surface_verified_retrieval_contract_pending" if qualifies else "unavailable_or_unparseable"
        evidence = "official event table exposes event identity/geography and explicit human/building/public-facility impact columns" if qualifies else "event impact field surface incomplete"
    elif source_id == "inarisk_current_methodology":
        qualifies, verification_mode = methodology_surface_qualifies(final_url, content_type, body)
        metadata["verification_mode"] = verification_mode
        state = "framework_verified_current_surface" if qualifies else "unavailable_or_unparseable"
        evidence = "current official InaRISK methodology route verified as framework evidence only; this route-level verification does not version-bind any raster" if qualifies else "current methodology surface identity could not be verified"
    else:
        raise M26ProbeError(f"unexpected HTML source: {source_id}")
    return body, metadata, {"qualification_state": state, "identity_evidence": evidence}


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_id",
        "component_class",
        "hazard_family",
        "source_url",
        "http_status",
        "snapshot_path",
        "snapshot_sha256",
        "qualification_state",
        "identity_evidence",
        "metadata_evidence",
        "numeric_extraction_authorized",
        "blocking_reason",
    ]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def run() -> dict[str, Any]:
    design = load_design()
    registry = read_registry()
    allowed_numeric_states = set(design["numeric_extraction_authorized_states"])
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for row in registry:
        source_id = row["source_id"]
        try:
            if "ArcGIS" in row["access_surface"]:
                payload, outcome = probe_arcgis(row)
                snapshot_body = canonical_snapshot(payload)
                extension = "json"
                metadata_evidence = outcome["metadata_evidence"]
            else:
                snapshot_body, metadata, outcome = probe_html(row)
                extension = "html"
                metadata_evidence = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            state = outcome["qualification_state"]
            identity_evidence = outcome["identity_evidence"]
            http_status = 200
        except M26ProbeError as exc:
            snapshot_body = (str(exc) + "\n").encode("utf-8")
            extension = "txt"
            state = "unavailable_or_unparseable"
            identity_evidence = str(exc)
            metadata_evidence = "{}"
            http_status = 0

        snapshot_path = SNAPSHOT_DIR / f"{source_id}.{extension}"
        snapshot_path.write_bytes(snapshot_body)
        numeric_authorized = state in allowed_numeric_states
        blocking_reason = "" if numeric_authorized else row["blocking_reason"]
        results.append(
            {
                "source_id": source_id,
                "component_class": row["component_class"],
                "hazard_family": row["hazard_family"],
                "source_url": row["source_url"],
                "http_status": http_status,
                "snapshot_path": snapshot_path.relative_to(ROOT).as_posix(),
                "snapshot_sha256": sha256_bytes(snapshot_body),
                "qualification_state": state,
                "identity_evidence": identity_evidence,
                "metadata_evidence": metadata_evidence,
                "numeric_extraction_authorized": numeric_authorized,
                "blocking_reason": blocking_reason,
            }
        )

    write_csv(results)
    state_by_id = {row["source_id"]: row["qualification_state"] for row in results}
    states_match = state_by_id == EXPECTED_FINAL_STATES
    manifest = {
        "schema": "ranah-observatory/milestone26-source-qualification/v1",
        "milestone": 26,
        "stage": 0,
        "source_count": len(results),
        "source_ids": [row["source_id"] for row in results],
        "qualification_states": state_by_id,
        "expected_qualification_states_match": states_match,
        "qualified_numeric_source_ids": [
            row["source_id"] for row in results if bool(row["numeric_extraction_authorized"])
        ],
        "hazard_vulnerability_numeric_extraction_authorized": False,
        "event_impact_panel_materialized": False,
        "numeric_spatial_aggregation_performed": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "posthoc_source_family_search_performed": False,
        "stage0_complete": states_match and len(results) == len(EXPECTED_IDS),
        "outputs": {
            "source_qualification": OUT.relative_to(ROOT).as_posix(),
            "source_qualification_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        },
        "snapshots": [
            {
                "source_id": row["source_id"],
                "path": row["snapshot_path"],
                "sha256": row["snapshot_sha256"],
            }
            for row in results
        ],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not manifest["stage0_complete"]:
        mismatches = {
            key: {"expected": EXPECTED_FINAL_STATES[key], "actual": state_by_id.get(key)}
            for key in EXPECTED_IDS
            if state_by_id.get(key) != EXPECTED_FINAL_STATES[key]
        }
        details = {
            row["source_id"]: row["identity_evidence"]
            for row in results
            if row["source_id"] in mismatches
        }
        raise M26ProbeError(
            f"M26 Stage 0 qualification did not meet preregistered outcome gates: {mismatches}; details={details}"
        )
    return manifest


def main() -> int:
    try:
        manifest = run()
    except (OSError, ValueError, json.JSONDecodeError, M26ProbeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "stage0_complete": manifest["stage0_complete"],
        "source_count": manifest["source_count"],
        "qualified_numeric_source_ids": manifest["qualified_numeric_source_ids"],
        "risk_synthesis_authorized": manifest["risk_synthesis_authorized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
