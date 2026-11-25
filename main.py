"""
Telegram Currency Converter Bot
================================
Exchange rates are fetched from:
https://open.er-api.com/

Запуск:
    python main.py
"""

import logging
import os

from telegram import BotCommand, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    Defaults,
    MessageHandler,
    PersistenceInput,
    PicklePersistence,
    filters,
)

from bot.config import BOT_TOKEN, DATA_DIR
from bot.handlers.convert import convert_callback, text_input
from bot.handlers.errors import on_error
from bot.handlers.favorites import favorites_callback
from bot.handlers.history import history_callback
from bot.handlers.rates import rates_callback
from bot.handlers.start import (
    help_command,
    navigate,
    open_converter,
    open_favorites,
    open_history,
    open_rates,
    start,
    unknown_command,
)
from bot.keyboards import (
    BTN_CONVERT,
    BTN_FAVORITES,
    BTN_HELP,
    BTN_HISTORY,
    BTN_RATES,
    main_menu,
)
from bot.screens import ScreenApplication, TrackingRequest, reply_keyboard_texts

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# httpx на уровне INFO пишет в лог полный URL запроса, а в нём — токен бота.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start", "Начало работы"),
    BotCommand("convert", "Конвертер валют"),
    BotCommand("rates", "Курсы валют"),
    BotCommand("favorites", "Избранные пары"),
    BotCommand("history", "История расчётов"),
    BotCommand("help", "Как пользоваться"),
]

# Кнопки нижнего меню → обработчики (то же, что и одноимённые команды).
MENU_ROUTES = (
    (BTN_CONVERT, open_converter),
    (BTN_RATES, open_rates),
    (BTN_FAVORITES, open_favorites),
    (BTN_HISTORY, open_history),
    (BTN_HELP, help_command),
)


async def post_init(app: Application) -> None:
    try:
        await app.bot.set_my_commands(BOT_COMMANDS)
    except TelegramError as e:
        logger.warning("Не удалось установить список команд: %s", e)


def build_application() -> Application:
    os.makedirs(DATA_DIR, exist_ok=True)
    # Храним только user_data: избранное, историю и выбранную пару.
    persistence = PicklePersistence(
        filepath=os.path.join(DATA_DIR, "bot_data.pickle"),
        store_data=PersistenceInput(bot_data=False, chat_data=False, callback_data=False),
    )
    defaults = Defaults(
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        # «Чистый чат»: учёт отправленных сообщений и удаление старых экранов (bot/screens.py).
        # connection_pool_size=256 — значение по умолчанию, которое PTB использует для запросов.
        .request(TrackingRequest(connection_pool_size=256))
        .application_class(
            ScreenApplication,
            kwargs={
                "transition_texts": reply_keyboard_texts(main_menu()),
                "transition_commands": [command.command for command in BOT_COMMANDS],
            },
        )
        .defaults(defaults)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("convert", open_converter))
    app.add_handler(CommandHandler("rates", open_rates))
    app.add_handler(CommandHandler("favorites", open_favorites))
    app.add_handler(CommandHandler("history", open_history))

    for text, handler in MENU_ROUTES:
        app.add_handler(MessageHandler(filters.Text([text]), handler))

    app.add_handler(CallbackQueryHandler(navigate, pattern=r"^nav:"))
    app.add_handler(CallbackQueryHandler(convert_callback, pattern=r"^cv:"))
    app.add_handler(CallbackQueryHandler(rates_callback, pattern=r"^rt:"))
    app.add_handler(CallbackQueryHandler(favorites_callback, pattern=r"^fv:"))
    app.add_handler(CallbackQueryHandler(history_callback, pattern=r"^hs:"))

    # Порядок важен: неизвестные команды и свободный текст — после всех остальных.
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))

    app.add_error_handler(on_error)
    return app


def main() -> None:
    app = build_application()
    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
