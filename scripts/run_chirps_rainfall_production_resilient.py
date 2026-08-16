from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

import rasterio
from rasterio.errors import RasterioIOError

from scripts import build_chirps_rainfall_production as production

_ORIGINAL_RASTERIO_OPEN = rasterio.open
DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_BASE_DELAY_SECONDS = 1.0


class RetryingRasterDataset:
    """Context-manager proxy that retries transient GDAL /vsicurl/ open/read failures.

    This adapter deliberately retries only RasterioIOError. Semantic validation in the
    production pipeline (CRS, resolution, coverage, row counts, evidence class) remains
    fail-closed and is not retried or weakened.
    """

    def __init__(
        self,
        path: str,
        *args: Any,
        opener: Callable[..., Any] = _ORIGINAL_RASTERIO_OPEN,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
        **kwargs: Any,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative")
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.opener = opener
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.sleep_fn = sleep_fn
        self._dataset: Any | None = None
        self.open_attempts = 0
        self.read_retry_count = 0

    def _delay(self, attempt: int) -> None:
        delay = self.base_delay_seconds * (2 ** max(0, attempt - 1))
        if delay > 0:
            self.sleep_fn(delay)

    def _open_with_retry(self) -> Any:
        last_error: RasterioIOError | None = None
        for attempt in range(1, self.max_attempts + 1):
            self.open_attempts += 1
            try:
                return self.opener(self.path, *self.args, **self.kwargs)
            except RasterioIOError as exc:
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                print(
                    f"warning: transient raster open failure for {self.path}; "
                    f"attempt {attempt}/{self.max_attempts}; retrying",
                    file=sys.stderr,
                )
                self._delay(attempt)
        assert last_error is not None
        raise last_error

    def __enter__(self) -> "RetryingRasterDataset":
        self._dataset = self._open_with_retry()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None

    def __getattr__(self, name: str) -> Any:
        dataset = object.__getattribute__(self, "_dataset")
        if dataset is None:
            raise AttributeError(name)
        return getattr(dataset, name)

    def read(self, *args: Any, **kwargs: Any) -> Any:
        if self._dataset is None:
            raise RuntimeError("dataset must be entered before read")
        last_error: RasterioIOError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._dataset.read(*args, **kwargs)
            except RasterioIOError as exc:
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                self.read_retry_count += 1
                print(
                    f"warning: transient raster read failure for {self.path}; "
                    f"attempt {attempt}/{self.max_attempts}; reopening and retrying",
                    file=sys.stderr,
                )
                self._dataset.close()
                self._dataset = None
                self._delay(attempt)
                self._dataset = self._open_with_retry()
        assert last_error is not None
        raise last_error


def retrying_rasterio_open(path: str, *args: Any, **kwargs: Any) -> RetryingRasterDataset:
    return RetryingRasterDataset(path, *args, **kwargs)


def run(output_dir: Path) -> dict[str, Any]:
    original = production.rasterio.open
    production.rasterio.open = retrying_rasterio_open
    try:
        return production.run_production(output_dir)
    finally:
        production.rasterio.open = original


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run full CHIRPS rainfall production with bounded retry for transient raster I/O"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/chirps-rainfall-production"),
    )
    args = parser.parse_args()
    manifest = run(args.output_dir)
    summary = {
        "runtime_seconds": manifest["runtime_seconds"],
        "scope": manifest["scope"],
        "coverage": manifest["diagnostics"]["coverage"],
        "gates": manifest["gates"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
