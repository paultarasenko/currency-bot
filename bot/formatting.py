"""Единое форматирование чисел и дат: «1 234,56» (узкий неразрывный пробел, запятая)."""

from datetime import datetime
from decimal import Decimal

from bot import currencies

NBSP = " "


def _group(text: str) -> str:
    # Сначала тысячи, потом десятичный разделитель — иначе запятые перепутаются.
    return text.replace(",", NBSP).replace(".", ",")


def fmt_plain(value: Decimal) -> str:
    """Число как ввёл пользователь: без лишних нулей (100, 1 500, 2,5)."""
    text = f"{value:,.6f}".rstrip("0").rstrip(".")
    return _group(text)


def fmt_money(value: Decimal, code: str) -> str:
    """Сумма в валюте: 2 знака (0 для иены), для долей единицы — минимум 4."""
    decimals = currencies.get(code).decimals
    if value != 0 and abs(value) < 1:
        decimals = max(decimals, 4)
    return _group(f"{value:,.{decimals}f}")


def fmt_rate(rate: Decimal) -> str:
    """Курс: чем он меньше, тем больше знаков, чтобы не терять точность."""
    if rate >= 100:
        decimals = 2
    elif rate >= 1:
        decimals = 4
    else:
        decimals = 6
    return _group(f"{rate:,.{decimals}f}")


def fmt_time(moment: datetime) -> str:
    return moment.strftime("%d.%m.%Y, %H:%M UTC")
