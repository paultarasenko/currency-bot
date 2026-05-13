"""
Telegram Currency Converter Bot
================================
Exchange rates are fetched from:
https://open.er-api.com/

Запуск:
    python main.py
"""

import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
)

from bot.config import BOT_TOKEN
from bot.handlers.start import start, help_command
from bot.handlers.rates import rates_command
from bot.handlers.convert import (
    convert_start,
    choose_from,
    choose_to,
    enter_amount,
    cancel,
    quick_convert,
    CHOOSE_FROM,
    CHOOSE_TO,
    ENTER_AMOUNT,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("convert", convert_start)],
        allow_reentry=True,
        states={
            CHOOSE_FROM: [CallbackQueryHandler(choose_from, pattern=r"^from:")],
            CHOOSE_TO: [CallbackQueryHandler(choose_to, pattern=r"^to:")],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rates", rates_command))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d'),
        quick_convert
    ))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()