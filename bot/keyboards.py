"""Все клавиатуры бота.

Нижнее меню (ReplyKeyboard) — постоянная навигация по разделам.
Inline-кнопки — действия внутри экрана; все они «stateless»: callback_data содержит всё нужное
для действия, поэтому кнопки старых сообщений продолжают работать после перезапуска бота.

Формат callback_data (≤ 64 байт):
    nav:<conv|rates|favs|hist|help>      переход на экран
    cv:pick:<f|t>                        открыть выбор валюты «Из» / «В»
    cv:set:<f|t>:<CODE>                  выбрать валюту
    cv:swap | cv:all | cv:fav            поменять местами / во все валюты / избранное
    cv:amt:<сумма>                       быстрая сумма
    cv:pair:<FROM>:<TO>                  открыть конвертер с парой
    rt:base:<CODE>                       сменить базу экрана курсов
    fv:o:<FROM>:<TO> | fv:d:<FROM>:<TO>  открыть / удалить пару из избранного
    hs:o:<FROM>:<TO>:<сумма> | hs:clear  повторить запись истории / очистить историю
"""

from decimal import Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot import currencies
from bot.formatting import fmt_plain

BTN_CONVERT = "💱 Конвертер"
BTN_RATES = "📊 Курсы"
BTN_FAVORITES = "⭐ Избранное"
BTN_HISTORY = "🕘 История"
BTN_HELP = "ℹ️ Помощь"

MENU_BUTTONS = (BTN_CONVERT, BTN_RATES, BTN_FAVORITES, BTN_HISTORY, BTN_HELP)

QUICK_AMOUNTS = (10, 100, 1000, 10000)

_GRID_COLUMNS = 3


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data)


def amount_to_callback(amount: Decimal) -> str:
    return format(amount.normalize(), "f")


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_CONVERT, BTN_RATES], [BTN_FAVORITES, BTN_HISTORY], [BTN_HELP]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Сумма или запрос: 100 usd в byn",
    )


def converter_kb(from_code: str, to_code: str, amount: Decimal, is_favorite: bool) -> InlineKeyboardMarkup:
    presets = [
        _btn(("✓ " if Decimal(value) == amount else "") + fmt_plain(Decimal(value)), f"cv:amt:{value}")
        for value in QUICK_AMOUNTS
    ]
    return InlineKeyboardMarkup(
        [
            [
                _btn(currencies.label(from_code), "cv:pick:f"),
                _btn("⇄", "cv:swap"),
                _btn(currencies.label(to_code), "cv:pick:t"),
            ],
            presets,
            [
                _btn("📋 Во все валюты", "cv:all"),
                _btn("★ В избранном" if is_favorite else "☆ В избранное", "cv:fav"),
            ],
        ]
    )


def picker_kb(role: str, selected: str) -> InlineKeyboardMarkup:
    """Сетка валют; role — 'f' («Из») или 't' («В»)."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for currency in currencies.CURRENCIES:
        mark = "✓ " if currency.code == selected else ""
        row.append(_btn(f"{mark}{currency.flag} {currency.code}", f"cv:set:{role}:{currency.code}"))
        if len(row) == _GRID_COLUMNS:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_btn("⬅️ Назад", "nav:conv")])
    return InlineKeyboardMarkup(rows)


def all_currencies_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_btn("⬅️ К конвертеру", "nav:conv")]])


def rates_kb(base: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for currency in currencies.CURRENCIES:
        mark = "✓ " if currency.code == base else ""
        row.append(_btn(f"{mark}{currency.flag} {currency.code}", f"rt:base:{currency.code}"))
        if len(row) == _GRID_COLUMNS:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_btn("💱 Конвертер", "nav:conv"), _btn("⭐ Избранное", "nav:favs")])
    return InlineKeyboardMarkup(rows)


def favorites_kb(pairs: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            _btn(f"{currencies.label(f)} → {currencies.label(t)}", f"fv:o:{f}:{t}"),
            _btn("✖️", f"fv:d:{f}:{t}"),
        ]
        for f, t in pairs
    ]
    rows.append([_btn("💱 Конвертер", "nav:conv")])
    return InlineKeyboardMarkup(rows)


def history_kb(entries: list[tuple[str, str, Decimal]]) -> InlineKeyboardMarkup:
    rows = [
        [_btn(f"{fmt_plain(amount)} {f} → {t}", f"hs:o:{f}:{t}:{amount_to_callback(amount)}")]
        for f, t, amount in entries
    ]
    if entries:
        rows.append([_btn("🧹 Очистить", "hs:clear"), _btn("💱 Конвертер", "nav:conv")])
    else:
        rows.append([_btn("💱 Конвертер", "nav:conv")])
    return InlineKeyboardMarkup(rows)


def help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[_btn("💱 Конвертер", "nav:conv"), _btn("📊 Курсы", "nav:rates")]]
    )


def retry_kb(target: str) -> InlineKeyboardMarkup:
    """Кнопка повтора после ошибки загрузки курсов; target — раздел из nav:*."""
    return InlineKeyboardMarkup([[_btn("🔄 Повторить", f"nav:{target}")]])
