import asyncio
import json
import logging
import tempfile
import time
import unittest
from decimal import Decimal
from unittest import mock

from bot import keyboards, state
from bot.services import rates
from tests.fake_telegram import Harness, button_texts, callback_data_of, main

D = Decimal

RATES = {
    "USD": 1, "EUR": 0.86, "BYN": 2.95, "RUB": 80, "PLN": 3.65, "GBP": 0.76,
    "CNY": 7.1, "JPY": 150, "CHF": 0.8, "UAH": 41, "KZT": 520, "AED": 3.67, "SEK": 9.5,
}
PAYLOAD = {"result": "success", "time_last_update_unix": 1_794_268_800, "rates": RATES}


def fresh_snapshot():
    return rates.replace(rates._parse_payload(PAYLOAD), fetched_at=time.time())


class FlowTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Ожидаемые предупреждения/ошибки в этих сценариях — не шум в выводе тестов.
        bot_logger = logging.getLogger("bot")
        previous_level = bot_logger.level
        bot_logger.setLevel(logging.CRITICAL)
        self.addCleanup(bot_logger.setLevel, previous_level)

        rates._cache = None
        rates._retry_not_before = 0.0
        rates._lock = asyncio.Lock()
        patcher = mock.patch.object(rates, "_fetch", mock.AsyncMock(side_effect=lambda: fresh_snapshot()))
        self.fetch = patcher.start()
        self.addCleanup(patcher.stop)


class StartAndMenuTests(FlowTestCase):
    async def test_start_shows_bottom_menu_and_live_converter(self):
        async with Harness() as h:
            await h.say("/start")
            sent = h.transport.named("sendMessage")
            self.assertEqual(len(sent), 2)

            welcome_markup = sent[0]["reply_markup"]
            welcome_markup = json.loads(welcome_markup) if isinstance(welcome_markup, str) else welcome_markup
            rows = [[b["text"] if isinstance(b, dict) else b for b in row] for row in welcome_markup["keyboard"]]
            self.assertEqual(rows, [[keyboards.BTN_CONVERT, keyboards.BTN_RATES],
                                    [keyboards.BTN_FAVORITES, keyboards.BTN_HISTORY],
                                    [keyboards.BTN_HELP]])
            self.assertIn("Аня", sent[0]["text"])
            self.assertIn("Конвертер валют", sent[1]["text"])
            self.assertEqual(sent[1]["parse_mode"], "HTML")

    async def test_every_menu_button_opens_its_section(self):
        expectations = {
            keyboards.BTN_CONVERT: "Конвертер валют",
            keyboards.BTN_RATES: "Курсы валют",
            keyboards.BTN_FAVORITES: "Избранное",
            keyboards.BTN_HISTORY: "История",
            keyboards.BTN_HELP: "Как пользоваться",
        }
        async with Harness() as h:
            for button, title in expectations.items():
                with self.subTest(button=button):
                    await h.say(button)
                    self.assertIn(title, h.transport.last_text())

    async def test_commands_match_menu(self):
        async with Harness() as h:
            for command, title in {"/convert": "Конвертер", "/rates": "Курсы", "/favorites": "Избранное",
                                   "/history": "История", "/help": "Как пользоваться"}.items():
                with self.subTest(command=command):
                    await h.say(command)
                    self.assertIn(title, h.transport.last_text())

    async def test_unknown_command_gets_hint(self):
        async with Harness() as h:
            await h.say("/cancel")
            self.assertIn("Не знаю такой команды", h.transport.last_text())

    async def test_commands_registered_on_startup(self):
        async with Harness() as h:
            await main.post_init(h.app)
            commands = h.transport.named("setMyCommands")[0]["commands"]
            self.assertEqual(len(commands), 6)


class TextInputTests(FlowTestCase):
    async def test_full_query(self):
        async with Harness() as h:
            await h.say("100 usd в eur")
            self.assertIn("100 USD", h.transport.last_text())
            self.assertIn("86,00 EUR", h.transport.last_text())
            self.assertEqual(state.get_pair(h.user_data), ("USD", "EUR"))

    async def test_number_only_uses_current_pair(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            await h.say("250")
            self.assertIn("250 USD", h.transport.last_text())
            self.assertIn("215,00 EUR", h.transport.last_text())

    async def test_single_currency_replaces_source_only(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            await h.say("1 000 pln")
            self.assertEqual(state.get_pair(h.user_data), ("PLN", "EUR"))

    async def test_currency_outside_buttons_is_supported(self):
        async with Harness() as h:
            await h.say("100 usd sek")
            self.assertIn("950,00 SEK", h.transport.last_text())
            self.assertIn("🌐", h.transport.last_text())

    async def test_unknown_currency(self):
        async with Harness() as h:
            await h.say("100 usd xyz")
            self.assertIn("Не знаю валюту", h.transport.last_text())
            self.assertIn("XYZ", h.transport.last_text())
            self.assertEqual(state.get_pair(h.user_data), state.DEFAULT_PAIR)

    async def test_same_currency(self):
        async with Harness() as h:
            await h.say("100 usd usd")
            self.assertIn("разные", h.transport.last_text())

    async def test_invalid_amounts(self):
        async with Harness() as h:
            for text in ["0", "0.0000001 usd", "9" * 30 + " usd"]:
                with self.subTest(text=text):
                    await h.say(text)
                    self.assertIn("⚠️", h.transport.last_text())
            self.assertEqual(state.get_history(h.user_data), [])

    async def test_gibberish_explains_without_resending_menu(self):
        async with Harness() as h:
            await h.say("привет как дела")
            self.assertIn("Не понял запрос", h.transport.last_text())
            # Подсказка без нижнего меню: иначе она «держит» клавиатуру и не удаляется (bot/screens.py).
            self.assertNotIn("reply_markup", h.transport.named("sendMessage")[-1])

    async def test_user_text_is_never_reflected_unescaped(self):
        async with Harness() as h:
            await h.say("<b>x</b> 5")
            self.assertNotIn("<b>x</b>", h.transport.last_text())


class ConverterButtonsTests(FlowTestCase):
    async def test_swap_edits_message_in_place(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            await h.tap("cv:swap")
            self.assertEqual(state.get_pair(h.user_data), ("EUR", "USD"))
            self.assertEqual(len(h.transport.named("editMessageText")), 1)
            self.assertIn("100 EUR", h.transport.last_text())

    async def test_quick_amount_buttons(self):
        async with Harness() as h:
            await h.tap("cv:amt:1000")
            self.assertEqual(state.get_amount(h.user_data), D(1000))
            self.assertIn("✓ 1 000", " ".join(button_texts(h.transport.last_markup())))

    async def test_picker_flow_and_swap_on_collision(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            await h.tap("cv:pick:f")
            self.assertIn("Из какой валюты?", h.transport.last_text())
            texts = button_texts(h.transport.last_markup())
            self.assertIn("✓ 🇺🇸 USD", texts)
            self.assertEqual(len(callback_data_of(h.transport.last_markup())), 13)  # 12 валют + «Назад»

            await h.tap("cv:set:f:EUR")  # EUR уже «В» → валюты меняются местами
            self.assertEqual(state.get_pair(h.user_data), ("EUR", "USD"))
            await h.tap("cv:pick:t")
            await h.tap("cv:set:t:PLN")
            self.assertEqual(state.get_pair(h.user_data), ("EUR", "PLN"))

    async def test_all_currencies_view(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            await h.tap("cv:all")
            text = h.transport.last_text()
            self.assertIn("во все валюты", text)
            self.assertIn("29", text)  # 100 USD = 295,00 BYN
            self.assertNotIn("<code>USD</code>", text)
            self.assertEqual(text.count("<code>"), 11)

    async def test_favorite_toggle_and_management(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            await h.tap("cv:fav")
            self.assertEqual(h.transport.named("answerCallbackQuery")[-1]["text"], "⭐ Добавлено в избранное")
            self.assertIn("★ В избранном", button_texts(h.transport.last_markup()))

            await h.say(keyboards.BTN_FAVORITES)
            self.assertIn("fv:o:USD:EUR", callback_data_of(h.transport.last_markup()))

            await h.tap("fv:o:USD:EUR")
            self.assertIn("Конвертер валют", h.transport.last_text())

            await h.tap("fv:d:USD:EUR")
            self.assertEqual(state.get_favorites(h.user_data), [])
            await h.tap("nav:favs")
            self.assertIn("Пока пусто", h.transport.last_text())

    async def test_favorites_limit_alerts(self):
        async with Harness() as h:
            for code in ["EUR", "BYN", "RUB", "PLN", "GBP", "CNY", "JPY", "CHF"]:
                state.toggle_favorite(h.user_data, ("USD", code))
            await h.say("100 usd uah")
            await h.tap("cv:fav")
            answer = h.transport.named("answerCallbackQuery")[-1]
            self.assertTrue(answer["show_alert"])
            self.assertIn("максимум", answer["text"])

    async def test_garbage_callbacks_do_not_crash(self):
        async with Harness() as h:
            for data in ["cv:bogus", "cv:set:x:USD", "cv:set:f:us", "cv:amt:abc", "cv:amt:-5", "cv:pair:USD:USD",
                         "rt:base:xx", "fv:o:USD", "hs:o:USD:EUR:NaN", "nav:nowhere", "cv"]:
                with self.subTest(data=data):
                    before = len(h.transport.named("editMessageText"))
                    await h.tap(data)
                    self.assertEqual(len(h.transport.named("editMessageText")), before)
            self.assertEqual(h.transport.named("sendMessage"), [])


class RatesAndHistoryTests(FlowTestCase):
    async def test_rates_screen_and_base_switch(self):
        async with Harness() as h:
            await h.say(keyboards.BTN_RATES)
            text = h.transport.last_text()
            self.assertIn("За 1 🇺🇸 USD", text)
            self.assertIn("Rates By Exchange Rate API", text)
            self.assertIn("10.11.2026, 00:00 UTC", text)
            self.assertNotIn("<code>USD ", text)

            await h.tap("rt:base:EUR")
            self.assertIn("За 1 🇪🇺 EUR", h.transport.last_text())
            self.assertIn("✓ 🇪🇺 EUR", button_texts(h.transport.last_markup()))
            self.assertEqual(state.get_pair(h.user_data), state.DEFAULT_PAIR)  # конвертер не затронут

    async def test_history_records_repeats_and_clears(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            await h.say("5k pln rub")
            await h.say(keyboards.BTN_HISTORY)
            callbacks = callback_data_of(h.transport.last_markup())
            self.assertEqual(callbacks[:2], ["hs:o:PLN:RUB:5000", "hs:o:USD:EUR:100"])

            await h.tap("hs:o:USD:EUR:100")
            self.assertEqual(state.get_pair(h.user_data), ("USD", "EUR"))
            self.assertIn("Конвертер валют", h.transport.last_text())

            await h.tap("hs:clear")
            self.assertIn("Здесь появятся", h.transport.last_text())

    async def test_buttons_work_without_prior_state(self):
        """Старое сообщение после перезапуска/потери данных: кнопка работает, значения по умолчанию."""
        async with Harness() as h:
            await h.tap("cv:swap")
            self.assertEqual(state.get_pair(h.user_data), ("BYN", "USD"))


class ResilienceTests(FlowTestCase):
    async def test_rates_unavailable_shows_retry_and_recovers(self):
        self.fetch.side_effect = OSError("network down")
        async with Harness() as h:
            await h.say(keyboards.BTN_CONVERT)
            self.assertIn("Не удалось загрузить курсы", h.transport.last_text())
            self.assertEqual(callback_data_of(h.transport.last_markup()), ["nav:conv"])

            self.fetch.side_effect = lambda: fresh_snapshot()
            rates._retry_not_before = 0.0
            await h.tap("nav:conv")
            self.assertIn("Конвертер валют", h.transport.last_text())

    async def test_stale_rates_are_flagged(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            rates._cache = rates.replace(rates._cache, fetched_at=time.time() - rates.CACHE_TTL - 1)
            self.fetch.side_effect = OSError("down")
            await h.tap("cv:swap")
            self.assertIn("Не удалось обновить курсы", h.transport.last_text())

    async def test_not_modified_is_ignored(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            h.transport.fail_edit_with = "Bad Request: message is not modified"
            await h.tap("nav:conv")
            self.assertEqual(h.transport.named("answerCallbackQuery")[-1].get("show_alert"), None)
            self.assertEqual(len(h.transport.named("sendMessage")), 1)  # новое сообщение не отправлялось

    async def test_uneditable_message_falls_back_to_new_message(self):
        async with Harness() as h:
            h.transport.fail_edit_with = "Bad Request: message can't be edited"
            await h.tap("cv:swap")
            self.assertEqual(len(h.transport.named("sendMessage")), 1)
            self.assertIn("Конвертер валют", h.transport.last_text())

    async def test_unexpected_exception_is_reported_to_user(self):
        async with Harness() as h:
            with mock.patch("bot.handlers.convert.get_snapshot", side_effect=RuntimeError("boom")):
                with self.assertLogs("bot.handlers.errors", level="ERROR"):
                    await h.say("100 usd eur")
            self.assertIn("Что-то пошло не так", h.transport.last_text())


class PersistenceTests(FlowTestCase):
    async def test_state_survives_restart(self):
        data_dir = tempfile.mkdtemp(prefix="currency-bot-tests-")
        async with Harness(data_dir) as h:
            await h.say("250 eur pln")
            await h.tap("cv:fav")
        async with Harness(data_dir) as h2:
            self.assertEqual(state.get_pair(h2.user_data), ("EUR", "PLN"))
            self.assertEqual(state.get_amount(h2.user_data), D(250))
            self.assertEqual(state.get_favorites(h2.user_data), [("EUR", "PLN")])
            self.assertEqual(state.get_history(h2.user_data), [("EUR", "PLN", D(250))])
            await h2.tap("cv:swap")  # кнопка со «старого» сообщения продолжает работать
            self.assertIn("250 PLN", h2.transport.last_text())


class CallbackDataLimitTests(unittest.TestCase):
    def test_all_callback_data_fit_telegram_limit(self):
        worst_amount = D("999999999999.999999")
        markups = [
            keyboards.converter_kb("USD", "EUR", worst_amount, True),
            keyboards.picker_kb("f", "USD"),
            keyboards.rates_kb("USD"),
            keyboards.favorites_kb([("USD", "EUR")] * 8),
            keyboards.history_kb([("USD", "EUR", worst_amount)] * 10),
            keyboards.help_kb(),
            keyboards.retry_kb("conv"),
        ]
        for markup in markups:
            for row in markup.inline_keyboard:
                for button in row:
                    self.assertLessEqual(len(button.callback_data.encode()), 64, button.callback_data)


if __name__ == "__main__":
    unittest.main()
