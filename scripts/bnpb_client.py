from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping

DEFAULT_BASE_URL = "https://data.bnpb.go.id/api/3/action"
RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 527}


class BNPBApiError(RuntimeError):
    """Raised when the BNPB CKAN API returns an invalid or unsuccessful response."""


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
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BNPBApiError("BNPB CKAN returned a non-JSON response") from exc
    if not isinstance(payload, Mapping):
        raise BNPBApiError("BNPB CKAN response root must be an object")
    return payload


class BNPBClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        retries: int = 3,
        retry_backoff_seconds: float = 0.5,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self._transport = transport or http_get_json

    def _url(self, action: str, params: Mapping[str, Any]) -> str:
        query = {key: value for key, value in params.items() if value is not None}
        return f"{self.base_url}/{action}?{urllib.parse.urlencode(query, doseq=True)}"

    def _request(self, action: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        url = self._url(action, params)
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                payload = self._transport(url, self.timeout)
                if not isinstance(payload, Mapping):
                    raise BNPBApiError("BNPB transport returned a non-object payload")
                if payload.get("success") is not True:
                    error = payload.get("error")
                    raise BNPBApiError(f"BNPB CKAN returned success=false: {error!r}")
                result = payload.get("result")
                if not isinstance(result, Mapping):
                    raise BNPBApiError("BNPB CKAN response does not contain an object result")
                return result
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in RETRYABLE_HTTP_STATUS or attempt >= self.retries:
                    raise BNPBApiError(f"BNPB CKAN HTTP error {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise BNPBApiError("BNPB CKAN request failed") from exc
            if self.retry_backoff_seconds:
                time.sleep(self.retry_backoff_seconds * (2**attempt))
        raise BNPBApiError("BNPB CKAN request failed") from last_error

    def package_show(self, dataset_id: str) -> Mapping[str, Any]:
        if not dataset_id.strip():
            raise ValueError("dataset_id is required")
        return self._request("package_show", {"id": dataset_id.strip()})

    def datastore_search_page(
        self,
        resource_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Mapping[str, Any]:
        if not resource_id.strip():
            raise ValueError("resource_id is required")
        if limit <= 0:
            raise ValueError("limit must be positive")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        result = self._request(
            "datastore_search",
            {"resource_id": resource_id.strip(), "limit": limit, "offset": offset},
        )
        records = result.get("records")
        fields = result.get("fields")
        if not isinstance(records, list) or not isinstance(fields, list):
            raise BNPBApiError("BNPB DataStore result must contain records and fields lists")
        for record in records:
            if not isinstance(record, Mapping):
                raise BNPBApiError("BNPB DataStore record must be an object")
        return result

    def datastore_search_all(
        self,
        resource_id: str,
        *,
        page_size: int = 100,
        max_records: int | None = None,
    ) -> Mapping[str, Any]:
        offset = 0
        all_records: list[Mapping[str, Any]] = []
        fields: list[Any] | None = None
        total: int | None = None

        while True:
            remaining = None if max_records is None else max_records - len(all_records)
            if remaining is not None and remaining <= 0:
                break
            limit = page_size if remaining is None else min(page_size, remaining)
            page = self.datastore_search_page(resource_id, limit=limit, offset=offset)
            page_records = page["records"]
            if fields is None:
                fields = list(page["fields"])
            try:
                total = int(page.get("total", len(page_records)))
            except (TypeError, ValueError) as exc:
                raise BNPBApiError("BNPB DataStore total is not numeric") from exc
            all_records.extend(page_records)
            if not page_records:
                break
            offset += len(page_records)
            if offset >= total:
                break

        return {
            "resource_id": resource_id,
            "total": total if total is not None else len(all_records),
            "returned": len(all_records),
            "fields": fields or [],
            "records": all_records,
        }
