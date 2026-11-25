import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import state, views
from bot.handlers.common import converter_screen, is_code, show
from bot.parsing import parse_callback_amount

logger = logging.getLogger(__name__)


async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Повторить расчёт (hs:o:<FROM>:<TO>:<сумма>) или очистить историю (hs:clear)."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    match query.data.split(":")[1:]:
        case ["o", from_code, to_code, raw_amount] if is_code(from_code) and is_code(to_code) and from_code != to_code:
            amount = parse_callback_amount(raw_amount)
            if amount is None:
                logger.warning("Некорректная сумма в callback_data: %r", query.data)
                return
            state.set_pair(ud, from_code, to_code)
            state.set_amount(ud, amount)
            screen = await converter_screen(ud)
        case ["clear"]:
            state.clear_history(ud)
            screen = views.history(ud)
        case _:
            logger.warning("Неизвестный callback_data: %r", query.data)
            return

    await show(update, context, screen)
