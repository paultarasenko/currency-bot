import asyncio
import time
import unittest
from decimal import Decimal
from unittest import mock

from bot.services import rates

D = Decimal

PAYLOAD = {
    "result": "success",
    "time_last_update_unix": 1_762_732_800,
    "rates": {"USD": 1, "EUR": 0.86, "BYN": 2.95, "JPY": 150.0, "BAD": 0, "NEG": -1, "STR": "x"},
}


def snapshot(fetched_at: float | None = None) -> rates.RatesSnapshot:
    snap = rates._parse_payload(PAYLOAD)
    return snap if fetched_at is None else rates.replace(snap, fetched_at=fetched_at)


class ParsePayloadTests(unittest.TestCase):
    def test_valid(self):
        snap = rates._parse_payload(PAYLOAD)
        self.assertEqual(snap.rates["EUR"], D("0.86"))
        self.assertEqual(snap.updated_at.year, 2025)
        self.assertFalse(snap.stale)

    def test_invalid_rates_are_dropped(self):
        snap = rates._parse_payload(PAYLOAD)
        for code in ("BAD", "NEG", "STR"):
            self.assertFalse(snap.has(code))

    def test_error_payloads(self):
        for payload in [{"result": "error", "error-type": "quota-reached"}, {"result": "success"}, [], None]:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    rates._parse_payload(payload)

    def test_cross_rate(self):
        snap = rates._parse_payload(PAYLOAD)
        self.assertEqual(snap.rate("EUR", "EUR"), D(1))
        self.assertAlmostEqual(float(snap.rate("EUR", "BYN")), 2.95 / 0.86, places=9)
        self.assertIsNone(snap.rate("EUR", "XXX"))


class CacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        rates._cache = None
        rates._retry_not_before = 0.0
        rates._lock = asyncio.Lock()

    async def test_cache_hit_does_not_refetch(self):
        with mock.patch.object(rates, "_fetch", mock.AsyncMock(return_value=snapshot(time.time()))) as fetch:
            first = await rates.get_snapshot()
            second = await rates.get_snapshot()
        self.assertIs(first, second)
        fetch.assert_awaited_once()

    async def test_concurrent_requests_share_one_fetch(self):
        async def slow_fetch():
            await asyncio.sleep(0.05)
            return snapshot(time.time())

        with mock.patch.object(rates, "_fetch", side_effect=slow_fetch) as fetch:
            results = await asyncio.gather(*(rates.get_snapshot() for _ in range(10)))
        self.assertEqual(fetch.await_count, 1)
        self.assertTrue(all(r is not None and not r.stale for r in results))

    async def test_no_data_at_all_returns_none(self):
        with mock.patch.object(rates, "_fetch", mock.AsyncMock(side_effect=OSError("down"))):
            self.assertIsNone(await rates.get_snapshot())

    async def test_expired_cache_and_failure_returns_stale(self):
        rates._cache = snapshot(time.time() - rates.CACHE_TTL - 1)
        with mock.patch.object(rates, "_fetch", mock.AsyncMock(side_effect=OSError("down"))):
            result = await rates.get_snapshot()
        self.assertTrue(result.stale)
        self.assertEqual(result.rates["EUR"], D("0.86"))

    async def test_backoff_after_failure(self):
        fetch = mock.AsyncMock(side_effect=OSError("down"))
        with mock.patch.object(rates, "_fetch", fetch):
            await rates.get_snapshot()
            await rates.get_snapshot()
        fetch.assert_awaited_once()

    async def test_rate_limit_uses_long_backoff(self):
        with mock.patch.object(rates, "_fetch", mock.AsyncMock(side_effect=rates._RateLimited())):
            await rates.get_snapshot()
        self.assertGreater(rates._retry_not_before - time.time(), rates.RETRY_DELAY)

    async def test_recovers_after_backoff(self):
        rates._retry_not_before = time.time() - 1
        with mock.patch.object(rates, "_fetch", mock.AsyncMock(return_value=snapshot(time.time()))):
            result = await rates.get_snapshot()
        self.assertFalse(result.stale)


if __name__ == "__main__":
    unittest.main()
