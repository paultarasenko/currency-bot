"""
Telegram Currency Converter Bot
================================
Установка зависимостей:
    pip install python-telegram-bot requests

Запуск:
    python currency_bot.py

Получить токен бота: @BotFather в Telegram
Курсы берутся с API Национального банка Республики Беларусь (бесплатно, без ключа):
    https://www.nbrb.by/api/exrates
"""

import logging
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
import requests

#  НАСТРОЙКИ — замените на свои значения

import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

#  Состояния диалога

CHOOSE_FROM, CHOOSE_TO, ENTER_AMOUNT = range(3)

#  Валюты — приоритетный порядок кнопок
#  Базовая валюта НБРБ — белорусский рубль (BYN)

POPULAR_CURRENCIES = [
    ("🇺🇸 USD", "USD"),
    ("🇪🇺 EUR", "EUR"),
    ("🇧🇾 BYN", "BYN"),
    ("🇷🇺 RUB", "RUB"),
    ("🇵🇱 PLN", "PLN"),
    ("🇬🇧 GBP", "GBP"),
    ("🇨🇳 CNY", "CNY"),
    ("🇯🇵 JPY", "JPY"),
    ("🇨🇭 CHF", "CHF"),
    ("🇺🇦 UAH", "UAH"),
    ("🇰🇿 KZT", "KZT"),
    ("🇦🇪 AED", "AED"),
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

"""Получает курсы через open.er-api.com (бесплатно, без ключа)."""

def get_nbrb_rates() -> dict:
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = resp.json()
        rates = data.get("rates", {})
        rates["USD"] = 1.0
        return rates
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return {}


def get_exchange_rate(from_currency: str, to_currency: str) -> float | None:
    rates = get_nbrb_rates()
    if not rates:
        return None
    from_usd = rates.get(from_currency.upper())
    to_usd = rates.get(to_currency.upper())
    if from_usd and to_usd:
        return to_usd / from_usd
    return None

#  Клавиатура выбора валюты

def currency_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for label, code in POPULAR_CURRENCIES:
        row.append(InlineKeyboardButton(label, callback_data=f"{callback_prefix}:{code}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

#  Обработчики команд

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *Привет! Я бот-конвертер валют.*\n\n"
        "Доступные команды:\n"
        "💱 /convert — конвертировать валюту\n"
        "📊 /rates — курсы популярных валют к USD\n"
        "❓ /help — помощь\n\n"
        "Или просто напиши, например:\n`100 USD в RUB`",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *Как пользоваться ботом:*\n\n"
        "1️⃣ Команда /convert — пошаговый конвертер\n"
        "2️⃣ Быстрый ввод: `100 USD в EUR`\n"
        "   или `50 EUR RUB`\n\n"
        "3️⃣ /rates — текущие курсы к USD\n\n"
        "*Поддерживаемые валюты:*\n"
        "USD, EUR, RUB, GBP, CNY, JPY, KZT, CHF, UAH, TRY, BYN, AED и другие",
        parse_mode="Markdown",
    )


async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Загружаю курсы с сайта Нацбанка РБ...")
    rates = get_nbrb_rates()
    today = date.today().strftime("%d.%m.%Y")
    if not rates:
        await update.message.reply_text("❌ Не удалось получить курсы. Попробуйте позже.")
        return
    lines = [f"📊 *Курсы валют к BYN на {today}*\n*(источник: НБРБ)*\n"]
    for label, code in POPULAR_CURRENCIES:
        if code == "BYN":
            continue
        r = rates.get(code)
        if r:
            lines.append(f"{label}: `{r:.4f} BYN`")
        else:
            lines.append(f"{label}: недоступно")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

#  Конвертация через диалог /convert

async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "💱 *Конвертация валюты*\n\nВыберите исходную валюту:",
        parse_mode="Markdown",
        reply_markup=currency_keyboard("from"),
    )
    return CHOOSE_FROM


async def choose_from(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, code = query.data.split(":")
    context.user_data["from_currency"] = code
    await query.edit_message_text(
        f"✅ Из: *{code}*\n\nТеперь выберите целевую валюту:",
        parse_mode="Markdown",
        reply_markup=currency_keyboard("to"),
    )
    return CHOOSE_TO


async def choose_to(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, code = query.data.split(":")
    context.user_data["to_currency"] = code
    from_c = context.user_data["from_currency"]
    await query.edit_message_text(
        f"✅ Из: *{from_c}* → В: *{code}*\n\nВведите сумму:",
        parse_mode="Markdown",
    )
    return ENTER_AMOUNT


async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.replace(",", ".").strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Пожалуйста, введите корректное число (например: `150` или `3.50`)", parse_mode="Markdown")
        return ENTER_AMOUNT

    from_c = context.user_data["from_currency"]
    to_c = context.user_data["to_currency"]

    await update.message.reply_text("⏳ Конвертирую...")
    rate = get_exchange_rate(from_c, to_c)

    if rate is None:
        await update.message.reply_text("❌ Не удалось получить курс. Попробуйте позже.")
        return ConversationHandler.END

    result = amount * rate
    await update.message.reply_text(
        f"💰 *Результат конвертации:*\n\n"
        f"`{amount:,.2f} {from_c}` = `{result:,.2f} {to_c}`\n\n"
        f"📈 Курс: 1 {from_c} = {rate:.4f} {to_c}\n\n"
        f"Хотите ещё раз? /convert",
        parse_mode="Markdown",
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Конвертация отменена.")
    else:
        await update.message.reply_text("❌ Конвертация отменена.")
    return ConversationHandler.END

#  Быстрая конвертация из текста
#  Формат: "100 USD в RUB" или "100 USD RUB"

async def quick_convert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.upper().replace("В ", "").replace("TO ", "").replace("IN ", "")
    parts = text.split()

    if len(parts) >= 3:
        try:
            amount = float(parts[0].replace(",", "."))
            from_c = parts[1]
            to_c = parts[2]
        except (ValueError, IndexError):
            return
    elif len(parts) == 2:
        # Формат: "USD EUR" (без суммы — показываем курс)
        from_c, to_c = parts[0], parts[1]
        amount = 1.0
    else:
        return

    # Проверяем, что это похоже на коды валют
    if not (2 <= len(from_c) <= 4 and 2 <= len(to_c) <= 4 and from_c.isalpha() and to_c.isalpha()):
        return

    rate = get_exchange_rate(from_c, to_c)
    if rate is None:
        await update.message.reply_text(
            f"❌ Не удалось найти курс *{from_c}* → *{to_c}*.\nПроверьте правильность кодов валют.",
            parse_mode="Markdown",
        )
        return

    result = amount * rate
    await update.message.reply_text(
        f"💰 `{amount:,.2f} {from_c}` = `{result:,.2f} {to_c}`\n"
        f"📈 Курс: 1 {from_c} = {rate:.4f} {to_c}",
        parse_mode="Markdown",
    )

#  Запуск бота

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
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
