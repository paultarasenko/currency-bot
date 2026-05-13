# 💱 Currency Converter Bot

Telegram-бот для конвертации валют в реальном времени.

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
