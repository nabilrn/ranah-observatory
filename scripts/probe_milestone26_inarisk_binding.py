#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
M16_MANIFEST = ROOT / "data/manifests/milestone16_spatial_climate_risk.json"
M16_REGISTRY = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-evidence-component-registry.csv"
M16_DOC = ROOT / "docs/MILESTONE16_SPATIAL_CLIMATE_RISK.md"
OUT_DIR = ROOT / "data/analysis/engine/inarisk_binding_v1"
DISCOVERY_OUT = OUT_DIR / "m26-service-discovery.csv"
ENDPOINT_OUT = OUT_DIR / "m26-metadata-endpoints.csv"
ASSESSMENT_OUT = OUT_DIR / "m26-binding-assessment.csv"
RAW_DIR = ROOT / "data/processed/bnpb/inarisk_metadata"
MANIFEST_OUT = ROOT / "data/manifests/milestone26_inarisk_version_binding.json"

SERVICE_RE = re.compile(r"https?://[^\s\"'<>]+?/(?:MapServer|ImageServer)(?:/\d+)?", re.IGNORECASE)
YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
OFFICIAL_HOST_MARKERS = ("bnpb.go.id", "inarisk")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, value: str) -> str:
    return prefix + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def canonical_service_url(url: str) -> str:
    url = url.rstrip("),.;]}")
    url = re.sub(r"/(MapServer|ImageServer)/\d+$", r"/\1", url, flags=re.IGNORECASE)
    return url.rstrip("/")


def official_service(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").casefold()
    return any(marker in host for marker in OFFICIAL_HOST_MARKERS)


def context_component(text: str) -> str:
    value = text.casefold()
    hazard = "hazard" in value or "bahaya" in value
    vulnerability = "vulnerab" in value or "kerentanan" in value
    flood = "flood" in value or "banjir" in value
    landslide = "landslide" in value or "longsor" in value
    if hazard and flood:
        return "flood_hazard"
    if hazard and landslide:
        return "landslide_hazard"
    if vulnerability and flood:
        return "flood_vulnerability"
    if vulnerability and landslide:
        return "landslide_vulnerability"
    if vulnerability:
        return "vulnerability_unspecified"
    if hazard:
        return "hazard_unspecified"
    return "m16_unresolved_inarisk_component"


def discover_services() -> list[dict[str, Any]]:
    if not M16_MANIFEST.exists() or not M16_REGISTRY.exists():
        raise ValueError("M26 requires committed M16 manifest and component registry")
    manifest = json.loads(M16_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("milestone16_complete") is not True:
        raise ValueError("M26 requires completed M16")
    if manifest.get("risk_synthesis_authorized") is not False:
        raise ValueError("M26 expects M16 risk synthesis to remain blocked")

    sources: list[tuple[str, str, str]] = []
    for row_index, row in enumerate(read_csv(M16_REGISTRY), start=2):
        joined = " | ".join(str(value) for value in row.values())
        if "inarisk" not in joined.casefold() and "bnpb" not in joined.casefold():
            continue
        for match in SERVICE_RE.findall(joined):
            # findall returns full match because pattern has only noncapturing groups.
            url = canonical_service_url(match)
            if official_service(url):
                sources.append((url, f"m16-evidence-component-registry.csv:{row_index}", joined))
    for path in (M16_DOC, M16_MANIFEST):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in SERVICE_RE.finditer(text):
            url = canonical_service_url(match.group(0))
            if official_service(url):
                start = max(0, match.start() - 220)
                end = min(len(text), match.end() + 220)
                sources.append((url, path.name, text[start:end]))

    if not sources:
        raise ValueError("no official InaRISK ArcGIS service URL discovered from M16 committed evidence")

    grouped: dict[str, dict[str, Any]] = {}
    for url, locator, context in sources:
        row = grouped.setdefault(
            url,
            {
                "service_id": stable_id("m26svc_", url),
                "service_url": url,
                "service_type": "ImageServer" if url.casefold().endswith("imageserver") else "MapServer",
                "m16_locators": set(),
                "m16_contexts": [],
                "component_types": set(),
            },
        )
        row["m16_locators"].add(locator)
        row["m16_contexts"].append(context)
        row["component_types"].add(context_component(context))

    result: list[dict[str, Any]] = []
    for url in sorted(grouped):
        row = grouped[url]
        result.append(
            {
                "service_id": row["service_id"],
                "service_url": url,
                "service_type": row["service_type"],
                "m16_locators": "|".join(sorted(row["m16_locators"])),
                "component_types": "|".join(sorted(row["component_types"])),
                "m16_status": "endpoint_verified_version_binding_unresolved",
                "pixel_ingestion_authorized": False,
            }
        )
    return result


def fetch(url: str, timeout: float = 30.0, retries: int = 3) -> tuple[int, bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "RanahObservatory/1.0 metadata qualification",
            "Accept": "application/json,text/xml,text/plain,*/*",
        },
    )
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return int(getattr(response, "status", 200)), response.read(), str(response.headers.get("Content-Type", ""))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(float(attempt))
    raise RuntimeError(f"metadata fetch failed after {retries} attempts for {url}: {last}")


def endpoint_filename(service_id: str, kind: str, suffix: str = "json") -> str:
    clean = re.sub(r"[^a-zA-Z0-9._-]+", "_", kind)
    return f"{service_id}__{clean}.{suffix}"


def decode_json(data: bytes) -> Any:
    return json.loads(data.decode("utf-8", errors="strict"))


def crawl_service(service: Mapping[str, Any], raw_dir: Path) -> tuple[list[dict[str, Any]], list[tuple[str, Any]]]:
    service_id = str(service["service_id"])
    base = str(service["service_url"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    endpoint_rows: list[dict[str, Any]] = []
    payloads: list[tuple[str, Any]] = []

    def attempt(kind: str, url: str, required: bool, expect_json: bool = True) -> Any | None:
        try:
            status, data, content_type = fetch(url)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            ext = "json" if expect_json else "xml"
            path = raw_dir / endpoint_filename(service_id, kind, ext)
            path.write_bytes(data)
            payload: Any | None = None
            parse_ok = True
            if expect_json:
                try:
                    payload = decode_json(data)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    parse_ok = False
            else:
                payload = data.decode("utf-8", errors="replace")
            endpoint_rows.append(
                {
                    "service_id": service_id,
                    "endpoint_kind": kind,
                    "source_url": url,
                    "required": required,
                    "http_status": status,
                    "fetch_status": "success",
                    "content_type": content_type,
                    "json_parse_ok": parse_ok if expect_json else "",
                    "response_sha256": sha256_bytes(data),
                    "frozen_path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix(),
                    "error": "",
                }
            )
            if expect_json and not parse_ok and required:
                raise RuntimeError(f"required JSON metadata endpoint returned non-JSON: {url}")
            if payload is not None:
                payloads.append((kind, payload))
            return payload
        except Exception as exc:  # record optional surface failures; required surfaces fail after row emission
            endpoint_rows.append(
                {
                    "service_id": service_id,
                    "endpoint_kind": kind,
                    "source_url": url,
                    "required": required,
                    "http_status": "",
                    "fetch_status": "failed",
                    "content_type": "",
                    "json_parse_ok": "",
                    "response_sha256": "",
                    "frozen_path": "",
                    "error": str(exc),
                }
            )
            if required:
                raise
            return None

    root = attempt("service_root", base + "?f=pjson", True, True)
    layers_payload = attempt("layers_collection", base + "/layers?f=pjson", False, True)
    attempt("iteminfo", base + "/info/iteminfo?f=pjson", False, True)
    attempt("metadata", base + "/info/metadata", False, False)

    layer_ids: set[int] = set()
    for payload in (root, layers_payload):
        if isinstance(payload, Mapping):
            for key in ("layers", "tables"):
                value = payload.get(key)
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, Mapping) and isinstance(item.get("id"), int):
                            layer_ids.add(int(item["id"]))
    for layer_id in sorted(layer_ids):
        attempt(f"layer_{layer_id}", f"{base}/{layer_id}?f=pjson", False, True)
    return endpoint_rows, payloads


def flatten(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from flatten(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from flatten(child, path + (str(index),))
    else:
        yield path, value


def classify_binding(payloads: list[tuple[str, Any]]) -> dict[str, Any]:
    year_tokens: set[str] = set()
    explicit_vintage_fields: list[str] = []
    methodology_fields: list[str] = []
    methodology_mentions: list[str] = []
    time_info_present = False

    disallowed_vintage_path_tokens = {
        "modified", "created", "lastmodified", "lastupdate", "lasteditdate", "copyright", "documentinfo",
        "currentversion", "version", "serviceitemid",
    }
    vintage_key_tokens = {
        "datayear", "referenceyear", "vintage", "datasetvintage", "tahun_data", "tahundata", "tahun",
        "reference_year", "data_year", "yearofdata", "datareferenceyear",
    }

    for kind, payload in payloads:
        if isinstance(payload, Mapping) and payload.get("timeInfo"):
            time_info_present = True
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True) if not isinstance(payload, str) else payload
        year_tokens.update(YEAR_RE.findall(text))
        if re.search(r"\b(metodologi|methodology|methodological)\b", text, flags=re.IGNORECASE):
            methodology_mentions.append(kind)
        for path, scalar in flatten(payload):
            if scalar is None:
                continue
            path_lower = tuple(token.casefold() for token in path)
            key = path_lower[-1] if path_lower else ""
            scalar_text = str(scalar).strip()
            if not scalar_text:
                continue
            compact_key = re.sub(r"[^a-z0-9_]", "", key)
            if compact_key in vintage_key_tokens and not any(token in disallowed_vintage_path_tokens for token in path_lower):
                years = YEAR_RE.findall(scalar_text)
                if years:
                    explicit_vintage_fields.append("/".join(path) + "=" + scalar_text[:160])
            if "metodologi" in key or "methodology" in key:
                methodology_fields.append("/".join(path) + "=" + scalar_text[:200])

    if explicit_vintage_fields:
        vintage_status = "explicit_dataset_vintage_bound"
    elif time_info_present:
        vintage_status = "time_enabled_not_dataset_vintage"
    elif year_tokens:
        vintage_status = "year_tokens_present_binding_unresolved"
    else:
        vintage_status = "no_explicit_vintage_metadata"

    if methodology_fields:
        methodology_status = "explicit_methodology_version_bound"
    elif methodology_mentions:
        methodology_status = "methodology_reference_present_binding_unresolved"
    else:
        methodology_status = "no_explicit_methodology_binding"

    qualified = vintage_status == "explicit_dataset_vintage_bound" and methodology_status == "explicit_methodology_version_bound"
    return {
        "vintage_binding_status": vintage_status,
        "methodology_binding_status": methodology_status,
        "metadata_binding_qualified_for_future_ingestion": qualified,
        "year_tokens": "|".join(sorted(year_tokens)),
        "explicit_vintage_fields": " || ".join(explicit_vintage_fields),
        "explicit_methodology_fields": " || ".join(methodology_fields),
        "methodology_mention_endpoints": "|".join(sorted(set(methodology_mentions))),
        "time_info_present": time_info_present,
    }


def run(raw_dir: Path, discovery_out: Path, endpoint_out: Path, assessment_out: Path, manifest_out: Path) -> dict[str, Any]:
    services = discover_services()
    endpoint_rows: list[dict[str, Any]] = []
    assessments: list[dict[str, Any]] = []
    for service in services:
        rows, payloads = crawl_service(service, raw_dir)
        endpoint_rows.extend(rows)
        binding = classify_binding(payloads)
        assessments.append(
            {
                "service_id": service["service_id"],
                "service_url": service["service_url"],
                "component_types": service["component_types"],
                **binding,
                "pixel_ingestion_performed": False,
                "risk_synthesis_authorized": False,
            }
        )
    if not all(any(row["service_id"] == service["service_id"] and row["endpoint_kind"] == "service_root" and row["fetch_status"] == "success" for row in endpoint_rows) for service in services):
        raise ValueError("not every discovered InaRISK service root was successfully frozen")

    write_csv(discovery_out, list(services[0].keys()), services)
    write_csv(endpoint_out, list(endpoint_rows[0].keys()), endpoint_rows)
    write_csv(assessment_out, list(assessments[0].keys()), assessments)
    qualified = [row["service_id"] for row in assessments if row["metadata_binding_qualified_for_future_ingestion"]]
    manifest = {
        "schema": "ranah-observatory/milestone26-inarisk-version-binding/v1",
        "milestone": 26,
        "phase": "post_phase2_disaster_risk_evidence_expansion",
        "criterion": "audit M16 unresolved InaRISK ArcGIS endpoint metadata for explicit data-vintage and methodology binding without pixel ingestion",
        "milestone26_complete": True,
        "service_count": len(services),
        "metadata_endpoint_attempt_count": len(endpoint_rows),
        "successful_metadata_endpoint_count": sum(row["fetch_status"] == "success" for row in endpoint_rows),
        "failed_optional_metadata_endpoint_count": sum(row["fetch_status"] == "failed" and not row["required"] for row in endpoint_rows),
        "metadata_binding_qualified_service_count": len(qualified),
        "metadata_binding_qualified_service_ids": qualified,
        "pixel_ingestion_performed": False,
        "composite_risk_score_created": False,
        "exposure_component_created": False,
        "capacity_component_created": False,
        "observed_impact_component_created": False,
        "risk_synthesis_authorized": False,
        "service_modified_timestamp_used_as_dataset_vintage": False,
        "inputs": {
            "m16_manifest": {"path": M16_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256_file(M16_MANIFEST)},
            "m16_component_registry": {"path": M16_REGISTRY.relative_to(ROOT).as_posix(), "sha256": sha256_file(M16_REGISTRY)},
            "m16_documentation": {"path": M16_DOC.relative_to(ROOT).as_posix(), "sha256": sha256_file(M16_DOC)} if M16_DOC.exists() else None,
        },
        "outputs": {
            "service_discovery": {"path": discovery_out.relative_to(ROOT).as_posix() if discovery_out.is_relative_to(ROOT) else discovery_out.as_posix(), "sha256": sha256_file(discovery_out)},
            "metadata_endpoints": {"path": endpoint_out.relative_to(ROOT).as_posix() if endpoint_out.is_relative_to(ROOT) else endpoint_out.as_posix(), "sha256": sha256_file(endpoint_out)},
            "binding_assessment": {"path": assessment_out.relative_to(ROOT).as_posix() if assessment_out.is_relative_to(ROOT) else assessment_out.as_posix(), "sha256": sha256_file(assessment_out)},
        },
    }
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit unresolved M16 InaRISK service metadata bindings.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--discovery", type=Path, default=DISCOVERY_OUT)
    parser.add_argument("--endpoints", type=Path, default=ENDPOINT_OUT)
    parser.add_argument("--assessment", type=Path, default=ASSESSMENT_OUT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_OUT)
    args = parser.parse_args()
    try:
        manifest = run(args.raw_dir, args.discovery, args.endpoints, args.assessment, args.manifest)
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "milestone26_complete": manifest["milestone26_complete"],
        "service_count": manifest["service_count"],
        "metadata_binding_qualified_service_count": manifest["metadata_binding_qualified_service_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
