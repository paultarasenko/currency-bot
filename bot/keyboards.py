from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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