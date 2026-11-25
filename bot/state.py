"""Пользовательское состояние поверх `context.user_data` (сохраняется PicklePersistence).

Все функции терпимы к «мусору» в данных: после обновления бота или ручной правки файла
персистентности бот должен вернуться к значениям по умолчанию, а не падать.
"""

import re
from decimal import Decimal
from typing import Any, MutableMapping

from bot.parsing import MAX_AMOUNT

UserData = MutableMapping[str, Any]

DEFAULT_PAIR = ("USD", "BYN")
DEFAULT_AMOUNT = Decimal(100)
MAX_FAVORITES = 8
MAX_HISTORY = 10

_CODE = re.compile(r"^[A-Z]{3}$")


def _valid_pair(value: Any) -> bool:
    return (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and all(isinstance(c, str) and _CODE.match(c) for c in value)
        and value[0] != value[1]
    )


def get_pair(ud: UserData) -> tuple[str, str]:
    pair = ud.get("pair")
    return (pair[0], pair[1]) if _valid_pair(pair) else DEFAULT_PAIR


def get_amount(ud: UserData) -> Decimal:
    amount = ud.get("amount")
    if isinstance(amount, Decimal) and amount.is_finite() and 0 < amount <= MAX_AMOUNT:
        return amount
    return DEFAULT_AMOUNT


def set_amount(ud: UserData, amount: Decimal) -> None:
    ud["amount"] = amount


def set_pair(ud: UserData, from_code: str, to_code: str) -> None:
    if from_code == to_code:
        raise ValueError("Валюты в паре должны различаться")
    ud["pair"] = (from_code, to_code)


def set_from(ud: UserData, code: str) -> None:
    """Выбор «Из»; если выбрана текущая «В» — валюты меняются местами."""
    from_code, to_code = get_pair(ud)
    set_pair(ud, code, from_code if code == to_code else to_code)


def set_to(ud: UserData, code: str) -> None:
    """Выбор «В»; если выбрана текущая «Из» — валюты меняются местами."""
    from_code, to_code = get_pair(ud)
    set_pair(ud, to_code if code == from_code else from_code, code)


def swap(ud: UserData) -> None:
    from_code, to_code = get_pair(ud)
    set_pair(ud, to_code, from_code)


# --- избранное -------------------------------------------------------------------------


def get_favorites(ud: UserData) -> list[tuple[str, str]]:
    raw = ud.get("favorites")
    if not isinstance(raw, list):
        return []
    return [(p[0], p[1]) for p in raw if _valid_pair(p)][:MAX_FAVORITES]


def is_favorite(ud: UserData, pair: tuple[str, str]) -> bool:
    return pair in get_favorites(ud)


def toggle_favorite(ud: UserData, pair: tuple[str, str]) -> str:
    """Возвращает 'added', 'removed' или 'full' (достигнут лимит)."""
    favorites = get_favorites(ud)
    if pair in favorites:
        ud["favorites"] = [p for p in favorites if p != pair]
        return "removed"
    if len(favorites) >= MAX_FAVORITES:
        return "full"
    ud["favorites"] = favorites + [pair]
    return "added"


def remove_favorite(ud: UserData, pair: tuple[str, str]) -> None:
    ud["favorites"] = [p for p in get_favorites(ud) if p != pair]


# --- история ---------------------------------------------------------------------------


def get_history(ud: UserData) -> list[tuple[str, str, Decimal]]:
    raw = ud.get("history")
    if not isinstance(raw, list):
        return []
    result = []
    for entry in raw:
        if (
            isinstance(entry, (tuple, list))
            and len(entry) == 3
            and _valid_pair(entry[:2])
            and isinstance(entry[2], Decimal)
            and entry[2].is_finite()
            and 0 < entry[2] <= MAX_AMOUNT
        ):
            result.append((entry[0], entry[1], entry[2]))
    return result[:MAX_HISTORY]


def add_history(ud: UserData, from_code: str, to_code: str, amount: Decimal) -> None:
    """Новая запись всплывает наверх; повтор той же конвертации не дублируется."""
    entry = (from_code, to_code, amount)
    rest = [e for e in get_history(ud) if e != entry]
    ud["history"] = [entry] + rest[: MAX_HISTORY - 1]


def clear_history(ud: UserData) -> None:
    ud["history"] = []


# --- база для экрана курсов ------------------------------------------------------------


def get_base(ud: UserData) -> str:
    base = ud.get("base")
    return base if isinstance(base, str) and _CODE.match(base) else get_pair(ud)[0]


def set_base(ud: UserData, code: str) -> None:
    ud["base"] = code
