from __future__ import annotations

import unittest

from rasterio.errors import RasterioIOError

from scripts.run_chirps_rainfall_production_resilient import RetryingRasterDataset


class FakeDataset:
    def __init__(self, read_failures: int = 0) -> None:
        self.read_failures = read_failures
        self.closed = False

    def read(self, *args, **kwargs):
        if self.read_failures > 0:
            self.read_failures -= 1
            raise RasterioIOError("transient read")
        return "ok"

    def close(self) -> None:
        self.closed = True

    @property
    def count(self) -> int:
        return 1


class ChirpsRasterRetryTests(unittest.TestCase):
    def test_open_retries_transient_rasterio_errors_then_succeeds(self) -> None:
        attempts = []
        sleeps = []
        dataset = FakeDataset()

        def opener(path, *args, **kwargs):
            attempts.append(path)
            if len(attempts) < 3:
                raise RasterioIOError("transient open")
            return dataset

        proxy = RetryingRasterDataset(
            "https://example.invalid/chirps.cog",
            opener=opener,
            max_attempts=4,
            base_delay_seconds=1.0,
            sleep_fn=sleeps.append,
        )
        with proxy as opened:
            self.assertEqual(opened.count, 1)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleeps, [1.0, 2.0])
        self.assertTrue(dataset.closed)

    def test_open_fails_after_bounded_attempts(self) -> None:
        attempts = []
        sleeps = []

        def opener(path, *args, **kwargs):
            attempts.append(path)
            raise RasterioIOError("persistent open failure")

        proxy = RetryingRasterDataset(
            "https://example.invalid/chirps.cog",
            opener=opener,
            max_attempts=3,
            base_delay_seconds=0.5,
            sleep_fn=sleeps.append,
        )
        with self.assertRaises(RasterioIOError):
            with proxy:
                pass
        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_read_reopens_after_transient_error(self) -> None:
        datasets = [FakeDataset(read_failures=1), FakeDataset()]
        sleeps = []
        open_count = 0

        def opener(path, *args, **kwargs):
            nonlocal open_count
            dataset = datasets[open_count]
            open_count += 1
            return dataset

        proxy = RetryingRasterDataset(
            "https://example.invalid/chirps.cog",
            opener=opener,
            max_attempts=3,
            base_delay_seconds=1.0,
            sleep_fn=sleeps.append,
        )
        with proxy as opened:
            result = opened.read(1)
            self.assertEqual(result, "ok")
            self.assertEqual(opened.read_retry_count, 1)
        self.assertEqual(open_count, 2)
        self.assertEqual(sleeps, [1.0])
        self.assertTrue(datasets[0].closed)
        self.assertTrue(datasets[1].closed)

    def test_non_rasterio_errors_are_not_retried(self) -> None:
        attempts = []

        def opener(path, *args, **kwargs):
            attempts.append(path)
            raise ValueError("semantic/programming error")

        proxy = RetryingRasterDataset(
            "https://example.invalid/chirps.cog",
            opener=opener,
            max_attempts=4,
            base_delay_seconds=0.0,
            sleep_fn=lambda _: None,
        )
        with self.assertRaises(ValueError):
            with proxy:
                pass
        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
