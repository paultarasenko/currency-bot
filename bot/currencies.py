"""Справочник валют, которые бот показывает кнопками.

Конвертировать можно любую валюту, которую отдаёт API (150+ кодов), но в кнопках
и списках курсов показываются только эти — самые востребованные.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    code: str
    flag: str
    name: str
    decimals: int = 2


CURRENCIES: tuple[Currency, ...] = (
    Currency("USD", "🇺🇸", "Доллар США"),
    Currency("EUR", "🇪🇺", "Евро"),
    Currency("BYN", "🇧🇾", "Белорусский рубль"),
    Currency("RUB", "🇷🇺", "Российский рубль"),
    Currency("PLN", "🇵🇱", "Польский злотый"),
    Currency("GBP", "🇬🇧", "Фунт стерлингов"),
    Currency("CNY", "🇨🇳", "Китайский юань"),
    Currency("JPY", "🇯🇵", "Японская иена", decimals=0),
    Currency("CHF", "🇨🇭", "Швейцарский франк"),
    Currency("UAH", "🇺🇦", "Украинская гривна"),
    Currency("KZT", "🇰🇿", "Казахстанский тенге"),
    Currency("AED", "🇦🇪", "Дирхам ОАЭ"),
)

_BY_CODE = {c.code: c for c in CURRENCIES}
_FALLBACK_FLAG = "🌐"


def get(code: str) -> Currency:
    """Метаданные валюты; для кода вне списка — нейтральная заглушка."""
    return _BY_CODE.get(code) or Currency(code, _FALLBACK_FLAG, code)


def label(code: str) -> str:
    """Короткая подпись для кнопок и текста: «🇺🇸 USD»."""
    return f"{get(code).flag} {code}"
