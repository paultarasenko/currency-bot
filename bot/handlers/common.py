"""Общие помощники хендлеров: показ экрана и сборка экранов, требующих курсов."""

import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot import state, views
from bot.services.rates import get_snapshot
from bot.views import Screen

logger = logging.getLogger(__name__)

CODE_LENGTH = 3


def is_code(value: str) -> bool:
    return len(value) == CODE_LENGTH and value.isascii() and value.isalpha() and value.isupper()


async def converter_screen(ud: state.UserData) -> Screen:
    snapshot = await get_snapshot()
    return views.converter(ud, snapshot) if snapshot else views.rates_unavailable("conv")


async def rates_screen(ud: state.UserData) -> Screen:
    snapshot = await get_snapshot()
    return views.rates(ud, snapshot) if snapshot else views.rates_unavailable("rates")


async def all_currencies_screen(ud: state.UserData) -> Screen:
    snapshot = await get_snapshot()
    return views.all_currencies(ud, snapshot) if snapshot else views.rates_unavailable("conv")


async def section_screen(section: str, ud: state.UserData) -> Screen | None:
    """Экран раздела по имени из nav:*; None — неизвестный раздел."""
    match section:
        case "conv":
            return await converter_screen(ud)
        case "rates":
            return await rates_screen(ud)
        case "favs":
            return views.favorites(ud)
        case "hist":
            return views.history(ud)
        case "help":
            return views.help_screen()
    return None


async def show(update: Update, context: ContextTypes.DEFAULT_TYPE, screen: Screen) -> None:
    """Из inline-кнопки правит текущее сообщение, из текста/меню — отправляет новое."""
    query = update.callback_query
    if query is None:
        await update.effective_message.reply_text(screen.text, reply_markup=screen.markup)
        return

    try:
        await query.edit_message_text(screen.text, reply_markup=screen.markup)
    except BadRequest as e:
        if "message is not modified" in str(e).lower():
            return
        # Сообщение слишком старое или удалено — отправляем экран заново, а не теряем действие.
        logger.info("Не удалось отредактировать сообщение (%s), отправляю новое", e)
        await context.bot.send_message(update.effective_chat.id, screen.text, reply_markup=screen.markup)
