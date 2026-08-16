from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MONTHLY_COG_DIR = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/"
STABLE_FIRST_FILE = "chirps-v3.0.1981.01.cog"
STABLE_RECENT_COMPLETE_FILE = "chirps-v3.0.2025.12.cog"
MONTHLY_PATTERN = re.compile(r"^chirps-v3\.0\.(\d{4})\.(\d{2})\.cog$")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)


def fetch_text(url: str, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "url": url,
                "reachable": True,
                "http_status": int(getattr(response, "status", 200)),
                "content_type": response.headers.get("Content-Type", ""),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "text": body.decode("utf-8", errors="replace"),
            }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        status = exc.code if isinstance(exc, urllib.error.HTTPError) else None
        return {"url": url, "reachable": False, "http_status": status, "error": f"{type(exc).__name__}: {exc}"}


def fetch_prefix(url: str, byte_count: int = 16384, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream,*/*",
            "Range": f"bytes=0-{byte_count - 1}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(byte_count)
            status = int(getattr(response, "status", 200))
            return {
                "url": url,
                "reachable": True,
                "http_status": status,
                "content_type": response.headers.get("Content-Type", ""),
                "content_range": response.headers.get("Content-Range", ""),
                "accept_ranges": response.headers.get("Accept-Ranges", ""),
                "content_length": response.headers.get("Content-Length", ""),
                "bytes_read": len(body),
                "sha256_prefix": hashlib.sha256(body).hexdigest(),
                "is_tiff": body.startswith(b"II*\x00") or body.startswith(b"MM\x00*"),
                "range_supported": status == 206 or bool(response.headers.get("Content-Range")),
            }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        status = exc.code if isinstance(exc, urllib.error.HTTPError) else None
        return {"url": url, "reachable": False, "http_status": status, "error": f"{type(exc).__name__}: {exc}"}


def inspect_listing(result: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in result.items() if key != "text"}
    public.update(
        {
            "monthly_cog_count": 0,
            "first_period": "",
            "last_period": "",
            "has_1981_01": False,
            "has_2025_12": False,
            "complete_years_through_2025": False,
        }
    )
    text = result.get("text")
    if result.get("http_status") != 200 or not isinstance(text, str):
        return public

    parser = LinkParser()
    parser.feed(text)
    periods: set[tuple[int, int]] = set()
    for href in parser.hrefs:
        filename = href.rsplit("/", 1)[-1]
        match = MONTHLY_PATTERN.match(filename)
        if not match:
            continue
        year, month = (int(match.group(1)), int(match.group(2)))
        if 1 <= month <= 12:
            periods.add((year, month))

    ordered = sorted(periods)
    public["monthly_cog_count"] = len(ordered)
    if ordered:
        public["first_period"] = f"{ordered[0][0]:04d}-{ordered[0][1]:02d}"
        public["last_period"] = f"{ordered[-1][0]:04d}-{ordered[-1][1]:02d}"
    public["has_1981_01"] = (1981, 1) in periods
    public["has_2025_12"] = (2025, 12) in periods
    expected = {(year, month) for year in range(1981, 2026) for month in range(1, 13)}
    public["complete_years_through_2025"] = expected.issubset(periods)
    return public


def run_probe() -> dict[str, Any]:
    listing = inspect_listing(fetch_text(MONTHLY_COG_DIR))
    first = fetch_prefix(MONTHLY_COG_DIR + STABLE_FIRST_FILE)
    recent = fetch_prefix(MONTHLY_COG_DIR + STABLE_RECENT_COMPLETE_FILE)

    qualified = all(
        [
            listing.get("http_status") == 200,
            listing.get("has_1981_01"),
            listing.get("has_2025_12"),
            listing.get("complete_years_through_2025"),
            first.get("is_tiff"),
            recent.get("is_tiff"),
            first.get("range_supported"),
            recent.get("range_supported"),
        ]
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_version": 1,
        "source": "CHIRPS v3 final monthly global COGs",
        "evidence_class": "satellite_station_gridded_estimate",
        "canonical_claim_type": "model_estimate",
        "listing": listing,
        "first_month_cog": first,
        "recent_complete_month_cog": recent,
        "conclusions": {
            "credential_free_machine_readable_access": qualified,
            "stable_monthly_coverage_1981_through_2025": qualified,
            "range_read_transport_suitable_for_spatial_subsetting": bool(first.get("range_supported") and recent.get("range_supported")),
            "eligible_as_observed_station_data": False,
            "eligible_as_rainfall_model_estimate_candidate": qualified,
            "daily_extreme_rainfall_indicator_qualified_by_this_probe": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe CHIRPS v3 final monthly COG access")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run_probe()
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
