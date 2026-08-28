#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
import urllib.error
import urllib.request

DATASET_ID = "95930772-cddb-412c-9d6e-e43b11e9ccd6"
DATASET_URL = "https://data.go.id/dataset/dataset/banyaknya-perusahaan-konstruksi"
JSONLD_URL = DATASET_URL + ".jsonld"
OUTDIR = Path("probe-output")
MAX_RESOURCE_BYTES = 8 * 1024 * 1024
TARGET_LABELS = ("kecil", "menengah", "besar", "jumlah")


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        data = {k.casefold(): v for k, v in attrs}
        self._current = {"href": data.get("href"), "attrs": data, "text": ""}

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._current is not None:
            self._current["text"] = " ".join(str(self._current["text"]).split())
            self.anchors.append(self._current)
            self._current = None


def fetch_bytes(url: str, *, max_bytes: int = MAX_RESOURCE_BYTES) -> tuple[bytes, dict[str, str], str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "*/*",
            "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read(max_bytes + 1)
        headers = {k.casefold(): v for k, v in response.headers.items()}
        final_url = response.geturl()
    if len(raw) > max_bytes:
        raise RuntimeError(f"resource exceeds bounded probe limit {max_bytes} bytes")
    return raw, headers, final_url


def folded(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def extract_csv_sumbar_2005(raw: bytes) -> list[dict[str, Any]]:
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return []
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows: list[dict[str, Any]] = []
    try:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        for row in reader:
            haystack = folded(row)
            if "sumatera barat" in haystack and "2005" in haystack:
                rows.append({str(k): v for k, v in row.items()})
    except csv.Error:
        return []
    return rows[:20]


def walk_jsonld(node: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        text = folded(node)
        if any(label in text for label in TARGET_LABELS) and any(
            key in node for key in ("distribution", "contentUrl", "downloadURL", "accessURL", "url")
        ):
            found.append({str(k): v for k, v in node.items()})
        for value in node.values():
            walk_jsonld(value, found)
    elif isinstance(node, list):
        for value in node:
            walk_jsonld(value, found)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    page_raw, page_headers, page_final_url = fetch_bytes(DATASET_URL, max_bytes=4 * 1024 * 1024)
    html = page_raw.decode("utf-8", errors="replace")
    parser = AnchorParser()
    parser.feed(html)

    candidate_anchors: list[dict[str, Any]] = []
    for anchor in parser.anchors:
        href = anchor.get("href")
        text = folded(anchor.get("text"))
        attrs_text = folded(anchor.get("attrs"))
        if not href:
            continue
        combined = f"{text} {attrs_text} {folded(href)}"
        if any(label in combined for label in TARGET_LABELS) or "resource" in folded(href) or "download" in folded(href):
            candidate_anchors.append({
                "text": anchor.get("text"),
                "href": urljoin(DATASET_URL, str(href)),
                "attrs": anchor.get("attrs"),
            })

    jsonld_status: dict[str, Any] = {"url": JSONLD_URL, "available": False, "error": None, "nodes": []}
    try:
        jsonld_raw, jsonld_headers, jsonld_final_url = fetch_bytes(JSONLD_URL, max_bytes=4 * 1024 * 1024)
        parsed = json.loads(jsonld_raw.decode("utf-8"))
        nodes: list[dict[str, Any]] = []
        walk_jsonld(parsed, nodes)
        jsonld_status.update({
            "available": True,
            "content_type": jsonld_headers.get("content-type"),
            "final_url": jsonld_final_url,
            "nodes": nodes[:50],
        })
    except Exception as exc:
        jsonld_status["error"] = f"{type(exc).__name__}: {exc}"

    resource_urls: dict[str, dict[str, Any]] = {}
    for anchor in candidate_anchors:
        url = str(anchor["href"])
        if url.startswith("https://"):
            resource_urls[url] = {"source": "html_anchor", "label": anchor.get("text")}
    for node in jsonld_status.get("nodes", []):
        for key in ("contentUrl", "downloadURL", "accessURL", "url"):
            value = node.get(key)
            values = value if isinstance(value, list) else [value]
            for candidate in values:
                if isinstance(candidate, str) and candidate.startswith("https://"):
                    resource_urls[candidate] = {"source": "jsonld", "label": node.get("name") or node.get("title")}

    inspected: list[dict[str, Any]] = []
    for url, meta in list(resource_urls.items())[:24]:
        item: dict[str, Any] = {
            "url": url,
            "source": meta["source"],
            "label": meta.get("label"),
            "fetch_error": None,
            "sumbar_2005_rows": [],
        }
        try:
            raw, headers, final_url = fetch_bytes(url)
            item["final_url"] = final_url
            item["fetched_bytes"] = len(raw)
            item["content_type"] = headers.get("content-type")
            ctype = folded(headers.get("content-type"))
            if "csv" in ctype or url.casefold().endswith(".csv"):
                item["sumbar_2005_rows"] = extract_csv_sumbar_2005(raw)
        except Exception as exc:
            item["fetch_error"] = f"{type(exc).__name__}: {exc}"
        inspected.append(item)

    report: dict[str, Any] = {
        "schema": "ranah-observatory/data-go-bps-construction-resources/v3",
        "dataset_id": DATASET_ID,
        "dataset_url": DATASET_URL,
        "page_final_url": page_final_url,
        "page_content_type": page_headers.get("content-type"),
        "target_anchor_count": len(candidate_anchors),
        "target_anchors": candidate_anchors[:80],
        "jsonld": jsonld_status,
        "inspected_resources": inspected,
        "boundary": {
            "canonical_preference": "official BPS WebAPI/publication remains canonical; data.go.id is corroborative transport unless BPS provenance is explicit",
            "max_resource_bytes": MAX_RESOURCE_BYTES,
            "no_endpoint_guessing": True,
        },
    }

    path = OUTDIR / "data-go-bps-construction-resources.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "target_anchor_count": len(candidate_anchors),
        "jsonld_available": jsonld_status["available"],
        "jsonld_nodes": len(jsonld_status.get("nodes", [])),
        "resource_urls": len(resource_urls),
        "inspected_resources": len(inspected),
        "sumbar_2005_hits": sum(len(r["sumbar_2005_rows"]) for r in inspected),
        "fetch_errors": sum(1 for r in inspected if r["fetch_error"]),
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
