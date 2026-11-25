import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import views
from bot.handlers.common import converter_screen, section_screen, show
from bot.keyboards import main_menu

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие с нижним меню и сразу «живая» карточка конвертера — без лишних шагов."""
    user = update.effective_user
    await update.message.reply_text(
        views.welcome(user.first_name if user else None),
        reply_markup=main_menu(),
    )
    await show(update, context, await converter_screen(context.user_data))


def _open_section(section: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        screen = await section_screen(section, context.user_data)
        await show(update, context, screen)

    handler.__name__ = f"open_{section}"
    return handler


open_converter = _open_section("conv")
open_rates = _open_section("rates")
open_favorites = _open_section("favs")
open_history = _open_section("hist")
help_command = _open_section("help")


async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline-кнопки nav:* — переход на раздел в том же сообщении."""
    query = update.callback_query
    await query.answer()
    screen = await section_screen(query.data.removeprefix("nav:"), context.user_data)
    if screen is None:
        logger.warning("Неизвестный раздел в callback_data: %r", query.data)
        return
    await show(update, context, screen)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤔 Не знаю такой команды. Воспользуйтесь меню внизу или отправьте сумму, "
        "например: <code>100 usd в byn</code>",
    )
