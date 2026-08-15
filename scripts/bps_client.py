from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping

DEFAULT_BASE_URL = "https://webapi.bps.go.id/v1"
RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}


class BPSApiError(RuntimeError):
    """Raised when the BPS WebAPI returns an invalid or unsuccessful response."""


@dataclass(frozen=True)
class PageInfo:
    page: int
    pages: int
    per_page: int
    count: int
    total: int


Transport = Callable[[str, float], Mapping[str, Any]]


def http_get_json(url: str, timeout: float) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BPSApiError("BPS WebAPI returned a non-JSON response") from exc
    if not isinstance(payload, Mapping):
        raise BPSApiError("BPS WebAPI response root must be an object")
    return payload


def parse_list_response(payload: Mapping[str, Any]) -> tuple[PageInfo, list[Mapping[str, Any]]]:
    status = str(payload.get("status", ""))
    if status != "OK":
        raise BPSApiError(f"BPS WebAPI returned status={status or 'missing'}")

    availability = str(payload.get("data-availability", ""))
    if availability != "available":
        return PageInfo(page=1, pages=0, per_page=0, count=0, total=0), []

    data = payload.get("data")
    if not isinstance(data, list) or len(data) < 2:
        raise BPSApiError("BPS list response does not contain [page_info, rows]")

    metadata, rows = data[0], data[1]
    if not isinstance(metadata, Mapping) or not isinstance(rows, list):
        raise BPSApiError("BPS list response has an unexpected shape")

    try:
        page_info = PageInfo(
            page=int(metadata.get("page", 1)),
            pages=int(metadata.get("pages", 1)),
            per_page=int(metadata.get("per_page", len(rows))),
            count=int(metadata.get("count", len(rows))),
            total=int(metadata.get("total", len(rows))),
        )
    except (TypeError, ValueError) as exc:
        raise BPSApiError("BPS list pagination metadata is not numeric") from exc

    normalized: list[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise BPSApiError("BPS list row must be an object")
        normalized.append(row)
    return page_info, normalized


class BPSClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        transport: Transport | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")
        self._api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self._transport = transport or http_get_json

    def _url(self, path: str, params: Mapping[str, Any]) -> str:
        query = {key: value for key, value in params.items() if value is not None}
        query["key"] = self._api_key
        encoded = urllib.parse.urlencode(query, doseq=True)
        return f"{self.base_url}/{path.lstrip('/')}?{encoded}"

    def _request(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        url = self._url(path, params)
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                payload = self._transport(url, self.timeout)
                if not isinstance(payload, Mapping):
                    raise BPSApiError("BPS WebAPI transport returned a non-object payload")
                status = str(payload.get("status", ""))
                if status and status != "OK":
                    raise BPSApiError(f"BPS WebAPI returned status={status}")
                return payload
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in RETRYABLE_HTTP_STATUS or attempt >= self.retries:
                    raise BPSApiError(f"BPS WebAPI HTTP error {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise BPSApiError("BPS WebAPI request failed") from exc
            if self.retry_backoff_seconds:
                time.sleep(self.retry_backoff_seconds * (2**attempt))

        raise BPSApiError("BPS WebAPI request failed") from last_error

    def iter_list(
        self,
        model: str,
        *,
        domain: str,
        lang: str = "ind",
        max_pages: int | None = None,
        **filters: Any,
    ) -> Iterator[Mapping[str, Any]]:
        page = 1
        while True:
            payload = self._request(
                "api/list/",
                {
                    "model": model,
                    "domain": domain,
                    "lang": lang,
                    "page": page,
                    **filters,
                },
            )
            info, rows = parse_list_response(payload)
            yield from rows

            if info.pages <= page:
                break
            if max_pages is not None and page >= max_pages:
                break
            page += 1

    def list_subjects(
        self,
        *,
        domain: str,
        lang: str = "ind",
        subcat: int | None = None,
        max_pages: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return list(
            self.iter_list(
                "subject", domain=domain, lang=lang, subcat=subcat, max_pages=max_pages
            )
        )

    def list_publications(
        self,
        *,
        domain: str,
        lang: str = "ind",
        year: int | None = None,
        month: int | None = None,
        keyword: str | None = None,
        max_pages: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return list(
            self.iter_list(
                "publication",
                domain=domain,
                lang=lang,
                year=year,
                month=month,
                keyword=keyword,
                max_pages=max_pages,
            )
        )

    def list_static_tables(
        self,
        *,
        domain: str,
        lang: str = "ind",
        year: int | None = None,
        month: int | None = None,
        keyword: str | None = None,
        max_pages: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return list(
            self.iter_list(
                "statictable",
                domain=domain,
                lang=lang,
                year=year,
                month=month,
                keyword=keyword,
                max_pages=max_pages,
            )
        )

    def list_variables(
        self,
        *,
        domain: str,
        lang: str = "ind",
        subject: int | None = None,
        year: int | None = None,
        area: int | None = None,
        vervar: int | None = None,
        max_pages: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return list(
            self.iter_list(
                "var",
                domain=domain,
                lang=lang,
                subject=subject,
                year=year,
                area=area,
                vervar=vervar,
                max_pages=max_pages,
            )
        )

    def list_periods(
        self,
        *,
        domain: str,
        var: int | None = None,
        lang: str = "ind",
        max_pages: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return list(
            self.iter_list("th", domain=domain, lang=lang, var=var, max_pages=max_pages)
        )

    def list_derived_variables(
        self,
        *,
        domain: str,
        var: int | None = None,
        group: int | None = None,
        lang: str = "ind",
        max_pages: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return list(
            self.iter_list(
                "turvar",
                domain=domain,
                lang=lang,
                var=var,
                group=group,
                max_pages=max_pages,
            )
        )

    def list_derived_periods(
        self,
        *,
        domain: str,
        var: int | None = None,
        lang: str = "ind",
        max_pages: int | None = None,
    ) -> list[Mapping[str, Any]]:
        return list(
            self.iter_list("turth", domain=domain, lang=lang, var=var, max_pages=max_pages)
        )

    def get_dynamic_data(
        self,
        *,
        domain: str,
        var: int,
        th: int | str,
        lang: str = "ind",
        turvar: int | None = None,
        vervar: int | None = None,
        turth: int | str | None = None,
    ) -> Mapping[str, Any]:
        payload = self._request(
            "api/list",
            {
                "model": "data",
                "domain": domain,
                "lang": lang,
                "var": var,
                "turvar": turvar,
                "vervar": vervar,
                "th": th,
                "turth": turth,
            },
        )
        if str(payload.get("data-availability", "")) != "available":
            raise BPSApiError("BPS dynamic data is not available for the requested selection")
        return payload

    def get_publication(
        self, *, domain: str, publication_id: str, lang: str = "ind"
    ) -> Mapping[str, Any]:
        payload = self._request(
            "view",
            {
                "model": "publication",
                "domain": domain,
                "lang": lang,
                "id": publication_id,
            },
        )
        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise BPSApiError("BPS publication detail response is missing its data object")
        return data
