from datetime import date
from telegram import Update
from telegram.ext import ContextTypes

from bot.services.rates import get_rates
from bot.keyboards import POPULAR_CURRENCIES


async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Загружаю курсы...")
    rates = await get_rates()
    today = date.today().strftime("%d.%m.%Y")

    if not rates:
        await update.message.reply_text("❌ Не удалось получить курсы. Попробуйте позже.")
        return

    lines = [f"📊 *Курсы валют к USD на {today}*\n*(источник: open.er-api.com)*\n"]
    for label, code in POPULAR_CURRENCIES:
        if code == "USD":
            continue
        r = rates.get(code)
        if r:
            lines.append(f"{label}: `{r:.4f}`")
        else:
            lines.append(f"{label}: недоступно")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")