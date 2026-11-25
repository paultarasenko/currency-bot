import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import state
from bot.handlers.common import is_code, rates_screen, show

logger = logging.getLogger(__name__)


async def rates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Смена базовой валюты на экране курсов (rt:base:<CODE>)."""
    query = update.callback_query
    await query.answer()

    match query.data.split(":")[1:]:
        case ["base", code] if is_code(code):
            state.set_base(context.user_data, code)
        case _:
            logger.warning("Неизвестный callback_data: %r", query.data)
            return

    await show(update, context, await rates_screen(context.user_data))
