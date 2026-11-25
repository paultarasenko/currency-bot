import logging
from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes

from bot import state, views
from bot.handlers.common import all_currencies_screen, converter_screen, is_code, show
from bot.parsing import parse, parse_callback_amount, validate_amount
from bot.services.rates import get_snapshot

logger = logging.getLogger(__name__)

_FAVORITE_TOASTS = {
    "added": "⭐ Добавлено в избранное",
    "removed": "Убрано из избранного",
    "full": f"В избранном максимум {state.MAX_FAVORITES} пар. Уберите ненужную в разделе «⭐ Избранное».",
}


async def convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Все inline-действия экрана конвертера (cv:*)."""
    query = update.callback_query
    ud = context.user_data
    parts = query.data.split(":")[1:]

    if parts == ["fav"]:
        outcome = state.toggle_favorite(ud, state.get_pair(ud))
        await query.answer(_FAVORITE_TOASTS[outcome], show_alert=outcome == "full")
    else:
        await query.answer()

    match parts:
        case ["pick", role] if role in ("f", "t"):
            screen = views.picker(ud, role)
        case ["set", role, code] if role in ("f", "t") and is_code(code):
            (state.set_from if role == "f" else state.set_to)(ud, code)
            screen = await converter_screen(ud)
        case ["swap"]:
            state.swap(ud)
            screen = await converter_screen(ud)
        case ["amt", value]:
            amount = parse_callback_amount(value)
            if amount is None:
                logger.warning("Некорректная сумма в callback_data: %r", query.data)
                return
            state.set_amount(ud, amount)
            screen = await converter_screen(ud)
        case ["pair", from_code, to_code] if is_code(from_code) and is_code(to_code) and from_code != to_code:
            state.set_pair(ud, from_code, to_code)
            screen = await converter_screen(ud)
        case ["all"]:
            screen = await all_currencies_screen(ud)
        case ["fav"]:
            screen = await converter_screen(ud)
        case _:
            logger.warning("Неизвестный callback_data: %r", query.data)
            return

    await show(update, context, screen)


async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Свободный ввод: «100 usd в byn», «$50», «250» (в текущей паре)."""
    message = update.message
    ud = context.user_data

    query = parse(message.text)
    if query is None:
        await message.reply_text(views.unknown_input())
        return

    amount = query.amount if query.amount is not None else Decimal(1)
    error = validate_amount(amount)
    if error:
        await message.reply_text(views.invalid_amount(error))
        return

    snapshot = await get_snapshot()
    if snapshot is None:
        await show(update, context, views.rates_unavailable("conv"))
        return

    for code in (query.from_code, query.to_code):
        if code and not snapshot.has(code):
            await message.reply_text(views.unknown_currency(code))
            return

    if query.from_code and query.to_code:
        if query.from_code == query.to_code:
            await message.reply_text(views.same_currency())
            return
        state.set_pair(ud, query.from_code, query.to_code)
    elif query.from_code:
        state.set_from(ud, query.from_code)

    state.set_amount(ud, amount)
    from_code, to_code = state.get_pair(ud)
    state.add_history(ud, from_code, to_code, amount)

    await show(update, context, views.converter(ud, snapshot))
