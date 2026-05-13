from telegram import Update
from telegram.ext import ContextTypes


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
        "USD, EUR, BYN, RUB, PLN, GBP, CNY, JPY, CHF, UAH, KZT, AED и другие",
        parse_mode="Markdown",
    )