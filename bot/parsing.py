"""Разбор свободного текста пользователя: «100 usd в byn», «$50», «5к евро рубли», «250».

Модуль не знает, какие коды реально есть в курсах: он только извлекает сумму и коды.
Проверка существования валюты — на стороне вызывающего кода.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

MAX_AMOUNT = Decimal("1000000000000")  # 10^12
MAX_TEXT_LENGTH = 100
_AMOUNT_STEP = Decimal("0.000001")

# Символы валют → код. «¥» намеренно нет: он неоднозначен (JPY/CNY).
_SYMBOLS = {"$": "usd", "€": "eur", "£": "gbp", "₽": "rub", "₴": "uah", "₸": "kzt", "zł": "pln"}

# Русские названия по началу слова (падежи и числа покрываются префиксом).
_ALIAS_PREFIXES = (
    ("доллар", "USD"),
    ("бакс", "USD"),
    ("евро", "EUR"),
    ("руб", "RUB"),
    ("белорус", "BYN"),
    ("злот", "PLN"),
    ("фунт", "GBP"),
    ("юан", "CNY"),
    ("иен", "JPY"),
    ("йен", "JPY"),
    ("франк", "CHF"),
    ("грив", "UAH"),
    ("тенг", "KZT"),
    ("дирхам", "AED"),
)

# «$50» → «50 usd»: символ перед суммой переносится за неё.
_PREFIX_SYMBOL = re.compile(r"([$€£₽₴₸])\s*(\d[\d \u00a0]*(?:[.,]\d+)?)")

_CONNECTORS = {"в", "во", "to", "in", "into"}

# «белорусский рубль», «бел. руб.» — это BYN, а не пара BYN + RUB.
_BYN_PHRASE = re.compile(r"(?:белорусск\w*|бел\.?)\s+руб\w*\.?")

_AMOUNT = re.compile(
    r"^(?P<num>\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?:(?P<k>[kк])(?![^\W\d_]))?"
)
_WORD = re.compile(r"[^\W\d_]+")


@dataclass(frozen=True)
class Query:
    amount: Decimal | None
    from_code: str | None
    to_code: str | None


def _resolve_word(word: str) -> str | None:
    for prefix, code in _ALIAS_PREFIXES:
        if word.startswith(prefix):
            return code
    if len(word) == 3 and word.isascii():
        return word.upper()
    return None


def parse(text: str) -> Query | None:
    """Возвращает Query или None, если текст не похож на запрос конвертации.

    Допустимо: только сумма («250»), сумма + валюта («100 usd»), сумма + пара
    («100 usd в byn»), пара без суммы («usd byn», сумма тогда 1 — решает вызывающий код).
    """
    if not text or len(text) > MAX_TEXT_LENGTH:
        return None

    s = text.strip().lower()
    s = _PREFIX_SYMBOL.sub(lambda m: f"{m.group(2)} {_SYMBOLS[m.group(1)]} ", s)
    for symbol, code in _SYMBOLS.items():
        s = s.replace(symbol, f" {code} ")
    s = _BYN_PHRASE.sub(" byn ", s).strip()

    amount: Decimal | None = None
    match = _AMOUNT.match(s)
    if match:
        raw = re.sub(r"[  ]", "", match.group("num")).replace(",", ".")
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            return None
        if match.group("k"):
            amount *= 1000
        if amount <= MAX_AMOUNT:
            # Сумма попадает в callback_data (лимит 64 байта), поэтому длина дроби ограничена.
            amount = amount.quantize(_AMOUNT_STEP)
        s = s[match.end():]

    codes: list[str] = []
    for word in _WORD.findall(s):
        if word in _CONNECTORS:
            continue
        code = _resolve_word(word)
        if code is None:
            return None
        codes.append(code)

    # Лишний «мусор» (цифры, знаки) допустим только как разделители: если после суммы
    # остались цифры, это не запрос конвертации.
    if re.search(r"\d", s):
        return None

    if len(codes) > 2:
        return None
    if amount is None and len(codes) < 2:
        return None

    return Query(
        amount=amount,
        from_code=codes[0] if codes else None,
        to_code=codes[1] if len(codes) > 1 else None,
    )


def validate_amount(amount: Decimal) -> str | None:
    """Текст ошибки для недопустимой суммы или None, если сумма корректна."""
    if amount <= 0:
        return "Сумма должна быть больше нуля."
    if amount > MAX_AMOUNT:
        return "Слишком большая сумма — максимум 1 000 000 000 000."
    return None


def parse_callback_amount(value: str) -> Decimal | None:
    """Сумма из callback_data; None — значение повреждено или недопустимо."""
    try:
        amount = Decimal(value)
    except InvalidOperation:
        return None
    return amount if amount.is_finite() and validate_amount(amount) is None else None
