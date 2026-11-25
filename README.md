# 💱 Конвертер валют: Telegram-бот

<img width="1200" height="833" alt="currency_converter_bot" src="https://github.com/user-attachments/assets/5d2c9925-8007-465b-a0e8-e82d9e7e8e46" />

Бот переводит одну валюту в другую по актуальному курсу. Работает прямо в Telegram: можно нажимать кнопки, а можно просто написать сумму.

## Что умеет
- Нижнее меню: 💱 Конвертер, 📊 Курсы, ⭐ Избранное, 🕘 История, ℹ️ Помощь. Те же разделы открываются командами `/convert`, `/rates`, `/favorites`, `/history`, `/help`.
- Конвертер - это одна «живая» карточка: выбор валют, обмен местами ⇄, быстрые суммы, пересчёт сразу во все валюты и избранные пары.
- Можно писать текстом: `100 usd в byn`, `$50`, `5к евро в рубли`, `1 500 pln`. Если отправить просто число, оно пересчитается в текущей паре.
- 12 валют вынесены на кнопки, остальные (больше 150) вводятся трёхбуквенным кодом, например `100 usd sek`.
- Курсы можно смотреть относительно любой валюты. Бот показывает время обновления и пишет «курсы устарели», если API не ответил.
- Избранное и история сохраняются между перезапусками (папка `DATA_DIR`, по умолчанию `data/`).
- Чат остаётся чистым: сообщения с названиями кнопок, введённый вручную текст, подсказки об ошибках и старые экраны удаляются. Остаётся только актуальный экран, а последний введённый запрос виден рядом с ответом до следующего экрана.

## Технологии
- Python 3.14
- python-telegram-bot
- aiohttp для асинхронных запросов
- Курсы валют: open.er-api.com (ключ не нужен)
- Деплой: Railway

## Запуск
1. Склонируй репозиторий.
2. Установи зависимости: `pip install -r requirements.txt`.
3. Создай файл `.env` по образцу `.env.example` и впиши токен бота в `BOT_TOKEN` (его выдаёт @BotFather).
4. Запусти: `python main.py`.

Курсы кэшируются на час, так что лишних запросов к API бот не делает.

## Тесты
Запуск (для тестов подойдёт любой токен):

    BOT_TOKEN=test python -m unittest discover -s tests -t .

Перед публикацией всё проверено: тесты проходят, бот запущен, и в Telegram все разделы работают как надо.

## Структура проекта

    bot/
      handlers/      обработчики команд, кнопок и текстового ввода
      services/      запросы к API и кэш курсов
      views.py       экраны: тексты и клавиатуры
      keyboards.py   нижнее меню и inline-кнопки
      parsing.py     разбор текстового ввода
      state.py       избранное, история, выбранная пара
      screens.py     «чистый чат»: учёт отправленных сообщений и удаление старых экранов
      currencies.py, formatting.py, config.py
    tests/           тесты
    main.py          точка входа

---

# 💱 Currency Converter Bot

<img width="1200" height="833" alt="Screenshot_20260513_145027_Telegram" src="https://github.com/user-attachments/assets/209c04be-67c3-4285-bfc7-34725f72aff5" />

A Telegram bot that converts currencies at the current rate. Tap the buttons or just type an amount.

## Features
- Bottom menu: 💱 Converter, 📊 Rates, ⭐ Favorites, 🕘 History, ℹ️ Help. The same sections open with `/convert`, `/rates`, `/favorites`, `/history`, `/help`.
- The converter is a single live card: currency pickers, swap ⇄, quick amounts, conversion to all currencies at once, and favorite pairs.
- Free text works too: `100 usd to byn`, `$50`, `5k eur to rub`, `1 500 pln`. A bare number is converted in the current pair.
- 12 currencies are on buttons, 150+ more are available by three-letter code, for example `100 usd sek`.
- Rates can be viewed against any base currency. The bot shows the last update time and a "rates may be outdated" notice when the API does not respond.
- Favorites and history persist across restarts (`DATA_DIR`, defaults to `data/`).
- The chat stays clean: button-label messages, text typed by hand, error hints and outdated screens are deleted. Only the current screen stays, and the latest typed request remains next to its reply until the next screen.

## Tech Stack
- Python 3.14
- python-telegram-bot
- aiohttp for async requests
- Exchange rates: open.er-api.com (no API key needed)
- Hosting: Railway

## Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Create a `.env` file based on `.env.example` and put your bot token into `BOT_TOKEN` (you get it from @BotFather).
4. Run: `python main.py`.

Rates are cached for an hour, so the bot does not send extra requests to the API.

## Tests
Run (any token will do for tests):

    BOT_TOKEN=test python -m unittest discover -s tests -t .

Everything was checked before publishing: the tests pass, the bot is running, and every section works as intended in Telegram.

## Project Structure

    bot/
      handlers/      command, button and text-input handlers
      services/      API requests and rates cache
      views.py       screens: texts and keyboards
      keyboards.py   bottom menu and inline buttons
      parsing.py     free-text input parser
      state.py       favorites, history, selected pair
      screens.py     clean chat: tracking of sent messages and removal of old screens
      currencies.py, formatting.py, config.py
    tests/           tests
    main.py          entry point
