"""Экраны бота: функции «данные → (текст, клавиатура)». Без обращений к Telegram и сети.

Единственный побочный эффект — возврат сохранённых валют к значениям по умолчанию,
если их больше нет в курсах."""

import html
from decimal import Decimal
from typing import NamedTuple

from telegram import InlineKeyboardMarkup

from bot import currencies, keyboards, state
from bot.formatting import fmt_money, fmt_plain, fmt_rate, fmt_time
from bot.services.rates import RatesSnapshot

ATTRIBUTION = '<a href="https://www.exchangerate-api.com">Rates By Exchange Rate API</a>'
_SEPARATOR = "┈┈┈┈┈┈┈┈┈┈┈┈"


class Screen(NamedTuple):
    text: str
    markup: InlineKeyboardMarkup | None


def _stale_note(snapshot: RatesSnapshot) -> str:
    if not snapshot.stale:
        return ""
    return "\n⚠️ <i>Не удалось обновить курсы — показаны последние известные.</i>"


def _updated_line(snapshot: RatesSnapshot) -> str:
    return f"🕐 Курсы на {fmt_time(snapshot.updated_at)}"


def rates_unavailable(retry_target: str) -> Screen:
    return Screen(
        "😕 <b>Не удалось загрузить курсы</b>\n\n"
        "Сервис курсов сейчас не отвечает. Это временно — попробуйте через минуту.",
        keyboards.retry_kb(retry_target),
    )


def welcome(first_name: str | None) -> str:
    name = f", {html.escape(first_name)}" if first_name else ""
    return (
        f"👋 <b>Привет{name}!</b>\n"
        "Я быстро считаю валюты по актуальным курсам: 12 популярных — в один тап, "
        "а ещё 150+ — по коду.\n\n"
        "<b>Как начать</b>\n"
        "💱 Выберите валюты в карточке ниже\n"
        "✍️ Или просто напишите: <code>100 usd в byn</code>\n"
        "🔢 Дальше достаточно присылать одну сумму\n\n"
        "<i>Разделы — в меню внизу экрана 👇</i>"
    )


def help_screen() -> Screen:
    codes = ", ".join(c.code for c in currencies.CURRENCIES)
    text = (
        "ℹ️ <b>Как пользоваться</b>\n\n"
        "<b>Кнопками</b>\n"
        "💱 <b>Конвертер</b> — выберите «Из» и «В», сумму — быстрыми кнопками или числом\n"
        "📊 <b>Курсы</b> — все валюты к выбранной базе\n"
        "⭐ <b>Избранное</b> — ваши частые пары в один тап\n"
        "🕘 <b>История</b> — последние расчёты, можно повторить\n\n"
        "<b>Текстом</b> — можно писать как удобно\n"
        "<code>100 usd byn</code> · <code>250 EUR в RUB</code>\n"
        "<code>$50</code> · <code>5к евро в рубли</code>\n"
        "<code>1 500 pln</code> — «Из» PLN, «В» — как выбрано\n"
        "<code>300</code> — пересчитать в текущей паре\n\n"
        f"<b>В кнопках:</b> {codes}\n"
        "Любая другая валюта — по трёхбуквенному коду, например <code>100 usd sek</code>.\n\n"
        f"{ATTRIBUTION}"
    )
    return Screen(text, keyboards.help_kb())


def converter(ud: state.UserData, snapshot: RatesSnapshot) -> Screen:
    from_code, to_code = state.get_pair(ud)
    if not (snapshot.has(from_code) and snapshot.has(to_code)):
        # Сохранённая валюта пропала из API — возвращаемся к паре по умолчанию.
        from_code, to_code = state.DEFAULT_PAIR
        state.set_pair(ud, from_code, to_code)
    amount = state.get_amount(ud)

    rate = snapshot.rate(from_code, to_code)
    if rate is None:
        return rates_unavailable("conv")
    result = amount * rate
    inverse = Decimal(1) / rate

    src, dst = currencies.get(from_code), currencies.get(to_code)
    text = (
        "💱 <b>Конвертер валют</b>\n\n"
        f"<b>{fmt_plain(amount)} {from_code}</b>  →  <b>{fmt_money(result, to_code)} {to_code}</b>\n"
        f"<i>{src.flag} {src.name} → {dst.flag} {dst.name}</i>\n\n"
        f"📈 1 {from_code} = {fmt_rate(rate)} {to_code}\n"
        f"📉 1 {to_code} = {fmt_rate(inverse)} {from_code}\n"
        f"{_updated_line(snapshot)}"
        f"{_stale_note(snapshot)}\n\n"
        "<i>Отправьте число, чтобы пересчитать другую сумму</i>"
    )
    markup = keyboards.converter_kb(from_code, to_code, amount, state.is_favorite(ud, (from_code, to_code)))
    return Screen(text, markup)


def picker(ud: state.UserData, role: str) -> Screen:
    from_code, to_code = state.get_pair(ud)
    selected = from_code if role == "f" else to_code
    title = "Из какой валюты?" if role == "f" else "В какую валюту?"
    text = (
        f"💱 <b>{title}</b>\n\n"
        f"Сейчас: <b>{currencies.label(selected)}</b>\n\n"
        "<i>Нужной нет в списке? Напишите код, например: <code>100 usd sek</code></i>"
    )
    return Screen(text, keyboards.picker_kb(role, selected))


def all_currencies(ud: state.UserData, snapshot: RatesSnapshot) -> Screen:
    from_code, _ = state.get_pair(ud)
    amount = state.get_amount(ud)
    lines = []
    for currency in currencies.CURRENCIES:
        if currency.code == from_code or not snapshot.has(currency.code):
            continue
        rate = snapshot.rate(from_code, currency.code)
        if rate is None:
            continue
        lines.append(f"{currency.flag} <code>{currency.code}</code>  <b>{fmt_money(amount * rate, currency.code)}</b>")

    text = (
        f"📋 <b>{fmt_plain(amount)} {from_code}</b> во все валюты\n\n"
        + "\n".join(lines)
        + f"\n\n{_updated_line(snapshot)}{_stale_note(snapshot)}"
    )
    return Screen(text, keyboards.all_currencies_kb())


def _align_on_comma(number: str) -> str:
    """Выравнивает числа в моноширинном блоке по десятичной запятой."""
    whole, comma, fraction = number.partition(",")
    return f"{whole:>7}{comma or ' '}{fraction:<6}"


def rates(ud: state.UserData, snapshot: RatesSnapshot) -> Screen:
    base = state.get_base(ud)
    if not snapshot.has(base):
        base = state.DEFAULT_PAIR[0]
        state.set_base(ud, base)

    rows = []
    for currency in currencies.CURRENCIES:
        if currency.code == base or not snapshot.has(currency.code):
            continue
        rate = snapshot.rate(base, currency.code)
        if rate is None:
            continue
        rows.append(f"{currency.flag} <code>{currency.code}  {_align_on_comma(fmt_rate(rate))}</code>")

    text = (
        f"📊 <b>Курсы валют</b>\n"
        f"{_SEPARATOR}\n"
        f"За 1 {currencies.label(base)}\n\n"
        + "\n".join(rows)
        + f"\n\n{_updated_line(snapshot)}{_stale_note(snapshot)}\n"
        f"<i>Выберите другую базу кнопками ниже</i>\n"
        f"{ATTRIBUTION}"
    )
    return Screen(text, keyboards.rates_kb(base))


def favorites(ud: state.UserData) -> Screen:
    pairs = state.get_favorites(ud)
    if not pairs:
        text = (
            "⭐ <b>Избранное</b>\n\n"
            "Пока пусто. Откройте «Конвертер», выберите пару и нажмите «☆ В избранное» — "
            "она появится здесь, и её можно будет открыть одним тапом."
        )
    else:
        text = (
            "⭐ <b>Избранное</b>\n\n"
            "Нажмите на пару, чтобы открыть её в конвертере.\n"
            "<i>✖️ — убрать из избранного.</i>"
        )
    return Screen(text, keyboards.favorites_kb(pairs))


def history(ud: state.UserData) -> Screen:
    entries = state.get_history(ud)
    if not entries:
        text = (
            "🕘 <b>История</b>\n\n"
            "Здесь появятся ваши последние расчёты. Напишите, например, <code>100 usd в byn</code>."
        )
    else:
        text = (
            "🕘 <b>История</b>\n\n"
            "Последние расчёты — нажмите, чтобы повторить с актуальным курсом."
        )
    return Screen(text, keyboards.history_kb(entries))


def unknown_input() -> str:
    return (
        "🤔 <b>Не понял запрос</b>\n\n"
        "Напишите сумму и валюты, например:\n"
        "<code>100 usd в byn</code>\n"
        "<code>250 eur rub</code>\n"
        "<code>$50</code>\n"
        "Или просто число — пересчитаю в текущей паре.\n\n"
        "<i>Все возможности — в «ℹ️ Помощь».</i>"
    )


def unknown_currency(code: str) -> str:
    return (
        f"🤷 Не знаю валюту <b>{html.escape(code)}</b>.\n\n"
        "Используйте трёхбуквенный код (<code>USD</code>, <code>EUR</code>, <code>SEK</code>…) — "
        "или выберите валюту кнопками в «💱 Конвертере»."
    )


def invalid_amount(reason: str) -> str:
    return f"⚠️ {html.escape(reason)}\nПример: <code>150</code> или <code>3,5</code>"


def same_currency() -> str:
    return "⚠️ Выберите две <b>разные</b> валюты, например: <code>100 usd в byn</code>"

