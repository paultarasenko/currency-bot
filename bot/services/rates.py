import time
import logging
import aiohttp

logger = logging.getLogger(__name__)

_rates_cache: dict = {}
_rates_cache_time: float = 0
CACHE_TTL = 300  # 5 минут


async def get_rates() -> dict:
    """
    Получает курсы валют через open.er-api.com.
    Кеш обновляется раз в 5 минут.
    """
    global _rates_cache, _rates_cache_time

    if _rates_cache and (time.time() - _rates_cache_time) < CACHE_TTL:
        return _rates_cache

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://open.er-api.com/v6/latest/USD",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                rates = data.get("rates", {})
                rates["USD"] = 1.0
                _rates_cache = rates
                _rates_cache_time = time.time()
                return rates
    except Exception as e:
        logger.error(f"Ошибка получения курсов: {e}")
        return _rates_cache if _rates_cache else {}


async def get_exchange_rate(from_currency: str, to_currency: str) -> float | None:
    """Конвертирует через USD как промежуточную валюту."""
    rates = await get_rates()
    if not rates:
        return None
    from_usd = rates.get(from_currency.upper())
    to_usd = rates.get(to_currency.upper())
    if from_usd and to_usd:
        return to_usd / from_usd
    return None