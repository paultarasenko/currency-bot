import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import state, views
from bot.handlers.common import converter_screen, is_code, show

logger = logging.getLogger(__name__)


async def favorites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Открыть (fv:o:<FROM>:<TO>) или удалить (fv:d:<FROM>:<TO>) пару из избранного."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    match query.data.split(":")[1:]:
        case ["o", from_code, to_code] if is_code(from_code) and is_code(to_code) and from_code != to_code:
            state.set_pair(ud, from_code, to_code)
            screen = await converter_screen(ud)
        case ["d", from_code, to_code] if is_code(from_code) and is_code(to_code):
            state.remove_favorite(ud, (from_code, to_code))
            screen = views.favorites(ud)
        case _:
            logger.warning("Неизвестный callback_data: %r", query.data)
            return

    await show(update, context, screen)
