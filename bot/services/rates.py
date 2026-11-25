import asyncio
import logging
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping

import aiohttp

logger = logging.getLogger(__name__)

API_URL = "https://open.er-api.com/v6/latest/USD"

# Провайдер обновляет курсы раз в сутки, а при превышении лимита блокирует IP на 20 минут,
# поэтому кеш живёт час, а после сбоя мы какое-то время не ходим в API повторно.
CACHE_TTL = 3600
RETRY_DELAY = 60
RATE_LIMIT_DELAY = 1200


@dataclass(frozen=True)
class RatesSnapshot:
    """Курсы всех валют к USD на момент `updated_at` (UTC)."""

    rates: Mapping[str, Decimal]
    updated_at: datetime
    fetched_at: float
    stale: bool = False  # True — обновить не удалось, показываем последние известные данные

    def has(self, code: str) -> bool:
        return code in self.rates

    def rate(self, from_code: str, to_code: str) -> Decimal | None:
        """Сколько единиц to_code в одной единице from_code."""
        from_usd = self.rates.get(from_code)
        to_usd = self.rates.get(to_code)
        if from_usd is None or to_usd is None:
            return None
        return to_usd / from_usd


_cache: RatesSnapshot | None = None
_retry_not_before: float = 0.0
_lock = asyncio.Lock()


def _parse_payload(data: object) -> RatesSnapshot:
    if not isinstance(data, dict) or data.get("result") != "success":
        detail = data.get("error-type") if isinstance(data, dict) else data
        raise ValueError(f"API вернул ошибку: {detail}")

    raw_rates = data.get("rates")
    if not isinstance(raw_rates, dict):
        raise ValueError("В ответе API нет поля rates")

    rates: dict[str, Decimal] = {}
    for code, value in raw_rates.items():
        try:
            rate = Decimal(str(value))
        except InvalidOperation:
            continue
        if rate.is_finite() and rate > 0:
            rates[str(code).upper()] = rate
    rates["USD"] = Decimal(1)

    updated_unix = data.get("time_last_update_unix")
    if isinstance(updated_unix, (int, float)):
        updated_at = datetime.fromtimestamp(updated_unix, tz=timezone.utc)
    else:
        updated_at = datetime.now(timezone.utc)

    return RatesSnapshot(rates=rates, updated_at=updated_at, fetched_at=time.time())


class _RateLimited(Exception):
    pass


async def _fetch() -> RatesSnapshot:
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 429:
                raise _RateLimited()
            resp.raise_for_status()
            return _parse_payload(await resp.json())


async def get_snapshot() -> RatesSnapshot | None:
    """Актуальные курсы из кеша или API. None — данных нет вообще (нет сети и пустой кеш)."""
    global _cache, _retry_not_before

    now = time.time()
    if _cache and now - _cache.fetched_at < CACHE_TTL:
        return _cache

    async with _lock:
        # Пока мы ждали блокировку, соседний запрос мог уже обновить кеш.
        now = time.time()
        if _cache and now - _cache.fetched_at < CACHE_TTL:
            return _cache

        if now >= _retry_not_before:
            try:
                _cache = await _fetch()
                return _cache
            except _RateLimited:
                logger.warning("API курсов вернул 429, пауза %s с", RATE_LIMIT_DELAY)
                _retry_not_before = now + RATE_LIMIT_DELAY
            except Exception as e:
                logger.error("Ошибка получения курсов: %s", e)
                _retry_not_before = now + RETRY_DELAY

        return replace(_cache, stale=True) if _cache else None
