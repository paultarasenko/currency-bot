import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует необработанное исключение и даёт пользователю понятный ответ вместо тишины."""
    logger.error("Необработанная ошибка при обработке апдейта", exc_info=context.error)

    if not isinstance(update, Update):
        return
    try:
        if update.callback_query:
            await update.callback_query.answer("Что-то пошло не так. Попробуйте ещё раз.", show_alert=True)
        elif update.effective_message:
            await update.effective_message.reply_text("⚠️ Что-то пошло не так. Попробуйте ещё раз чуть позже.")
    except TelegramError:
        logger.debug("Не удалось сообщить пользователю об ошибке", exc_info=True)
