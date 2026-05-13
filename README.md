Telegram-бот для конвертации валют в реальном времени.

# 💱 <img width="1200" height="833" alt="currency_converter_bot" src="https://github.com/user-attachments/assets/5d2c9925-8007-465b-a0e8-e82d9e7e8e46" />

## Возможности
- /convert — пошаговый конвертер с кнопками
- /rates — курсы популярных валют
- Быстрый ввод: `100 USD в RUB`
- 12 валют: USD, EUR, BYN, RUB, PLN, GBP, CNY, JPY, CHF, UAH, KZT, AED

## Технологии
- Python 3.14
- python-telegram-bot
- aiohttp (асинхронные запросы)
- Курсы валют: open.er-api.com
- Деплой: Railway

## Запуск локально
1. Клонируй репозиторий
2. Установи зависимости: `pip install -r requirements.txt`
3. Создай `.env` файл по примеру `.env.example`
4. Запусти: `python main.py`

## Структура проекта
\```
bot/
  handlers/   — обработчики команд
  services/   — API и кеш курсов
  keyboards.py — кнопки валют
  config.py   — конфигурация
main.py       — точка входа
\```

---<img width="1200" height="833" alt="Screenshot_20260513_145027_Telegram" src="https://github.com/user-attachments/assets/209c04be-67c3-4285-bfc7-34725f72aff5" />


# 💱 Currency Converter Bot

Telegram bot for real-time currency conversion.

## Features
- /convert — step-by-step converter with inline buttons
- /rates — current exchange rates for popular currencies
- Quick input: `100 USD to RUB`
- 12 currencies: USD, EUR, BYN, RUB, PLN, GBP, CNY, JPY, CHF, UAH, KZT, AED

## Tech Stack
- Python 3.14
- python-telegram-bot
- aiohttp (async requests)
- Exchange rates: open.er-api.com
- Hosting: Railway

## Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file based on `.env.example`
4. Run: `python main.py`

## Project Structure
```
bot/
  handlers/    — command handlers
  services/    — API & rates cache
  keyboards.py — currency buttons
  config.py    — configuration
main.py        — entry point
```
