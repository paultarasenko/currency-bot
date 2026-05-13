from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.keyboards import currency_keyboard
from bot.services.rates import get_exchange_rate

CHOOSE_FROM, CHOOSE_TO, ENTER_AMOUNT = range(3)


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
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: `150` или `3.50`)",
            parse_mode="Markdown",
        )
        return ENTER_AMOUNT

    from_c = context.user_data["from_currency"]
    to_c = context.user_data["to_currency"]

    await update.message.reply_text("⏳ Конвертирую...")
    rate = await get_exchange_rate(from_c, to_c)

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
        from_c, to_c = parts[0], parts[1]
        amount = 1.0
    else:
        return

    if not (2 <= len(from_c) <= 4 and 2 <= len(to_c) <= 4 and from_c.isalpha() and to_c.isalpha()):
        return

    rate = await get_exchange_rate(from_c, to_c)
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