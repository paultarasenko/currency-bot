"""«Чистый чат»: удаление сообщений от кнопок и неактуальных экранов (bot/screens.py)."""

import tempfile
import time
import unittest
from unittest import mock

from telegram.ext import CommandHandler, MessageHandler, filters

import main
from bot import keyboards, screens
from tests.fake_telegram import USER, Harness
from tests.test_flows import FlowTestCase


def deleted_ids(h: Harness) -> list[int]:
    """Все id, которые бот просил удалить, в порядке запросов."""
    return [i for params in h.transport.named("deleteMessages") for i in params["message_ids"]]


def call_names(h: Harness) -> list[str]:
    return [name for name, _ in h.transport.calls]


class ButtonMessageTests(FlowTestCase):
    async def test_menu_button_message_is_deleted(self):
        async with Harness() as h:
            button_message = await h.say(keyboards.BTN_RATES)
            self.assertIn(button_message, deleted_ids(h))

    async def test_every_menu_button_and_command_deletes_own_message(self):
        async with Harness() as h:
            triggers = list(keyboards.MENU_BUTTONS) + ["/start", "/convert", "/rates", "/favorites", "/history", "/help"]
            for trigger in triggers:
                with self.subTest(trigger=trigger):
                    message_id = await h.say(trigger)
                    self.assertIn(message_id, deleted_ids(h))

    async def test_command_with_bot_suffix_and_arguments_is_a_transition(self):
        async with Harness() as h:
            message_id = await h.say("/start@bot payload")
            self.assertIn(message_id, deleted_ids(h))

    async def test_unknown_command_is_not_a_transition(self):
        async with Harness() as h:
            message_id = await h.say("/cancel")
            self.assertNotIn(message_id, deleted_ids(h))

    async def test_transitions_come_from_real_keyboard(self):
        self.assertEqual(screens.reply_keyboard_texts(keyboards.main_menu()), frozenset(keyboards.MENU_BUTTONS))


class OldScreensTests(FlowTestCase):
    async def test_previous_screen_is_deleted_on_transition(self):
        async with Harness() as h:
            await h.say("/start")
            welcome, card = h.transport.sent_ids
            await h.say(keyboards.BTN_RATES)
            rates_card = h.transport.sent_ids[-1]
            self.assertIn(card, deleted_ids(h))
            self.assertNotIn(rates_card, deleted_ids(h))
            self.assertNotIn(welcome, deleted_ids(h))  # на нём висит нижняя клавиатура

    async def test_only_actual_screen_remains_after_several_transitions(self):
        async with Harness() as h:
            await h.say("/start")
            for button in (keyboards.BTN_RATES, keyboards.BTN_HISTORY, keyboards.BTN_FAVORITES, keyboards.BTN_CONVERT):
                await h.say(button)
            remaining = [i for i in h.transport.sent_ids if i not in deleted_ids(h)]
            self.assertEqual(remaining, [h.transport.sent_ids[0], h.transport.sent_ids[-1]])  # приветствие + экран

    async def test_typed_amount_replaces_previous_card(self):
        async with Harness() as h:
            typed = await h.say("100 usd eur")
            first = h.transport.sent_ids[-1]
            await h.say("250")
            self.assertEqual(deleted_ids(h), [typed, first])  # старая карточка и введённый к ней запрос

    async def test_typed_text_is_deleted_with_next_new_screen(self):
        async with Harness() as h:
            first = await h.say("100 usd eur")
            second = await h.say("250")
            self.assertIn(first, deleted_ids(h))  # второй ввод показал новую карточку
            self.assertNotIn(second, deleted_ids(h))  # последний запрос остаётся рядом с ответом

            await h.say(keyboards.BTN_RATES)
            self.assertIn(second, deleted_ids(h))

    async def test_error_hint_does_not_replace_current_screen(self):
        async with Harness() as h:
            await h.say(keyboards.BTN_RATES)
            card = h.transport.sent_ids[-1]
            await h.say("привет как дела")
            self.assertNotIn(card, deleted_ids(h))

    async def test_hint_is_cleaned_with_next_screen_that_brings_keyboard(self):
        async with Harness() as h:
            await h.say("привет как дела")
            hint = h.transport.sent_ids[-1]
            await h.say("/start")
            self.assertIn(hint, deleted_ids(h))

    async def test_callback_edit_does_not_delete_anything(self):
        async with Harness() as h:
            await h.say("100 usd eur")
            before = len(h.transport.named("deleteMessages"))
            await h.tap("cv:swap")
            self.assertEqual(len(h.transport.named("deleteMessages")), before)

    async def test_callback_fallback_to_new_message_replaces_old_screens(self):
        async with Harness() as h:
            typed = await h.say("100 usd eur")
            old = h.transport.sent_ids[-1]
            h.transport.fail_edit_with = "Bad Request: message can't be edited"
            await h.tap("cv:swap")
            self.assertEqual(deleted_ids(h), [typed, old])


class OrderTests(FlowTestCase):
    async def test_new_screen_is_sent_before_old_are_deleted(self):
        async with Harness() as h:
            await h.say("/start")
            start = len(h.transport.calls)
            await h.say(keyboards.BTN_RATES)
            names = call_names(h)[start:]
            self.assertLess(names.index("sendMessage"), names.index("deleteMessages"))

    async def test_all_old_screens_go_in_one_request_after_send(self):
        async with Harness() as h:
            await h.say(keyboards.BTN_RATES)
            await h.say(keyboards.BTN_HISTORY)
            self.assertEqual(call_names(h)[-2:], ["sendMessage", "deleteMessages"])


class NothingDeletedTests(FlowTestCase):
    async def test_failed_handler_deletes_nothing(self):
        async with Harness() as h:
            await h.say("/start")
            await h.say(keyboards.BTN_RATES)
            deletes_before = len(h.transport.named("deleteMessages"))
            with (
                mock.patch("bot.handlers.start.section_screen", side_effect=RuntimeError("boom")),
                self.assertLogs("bot.handlers.errors", level="ERROR"),
            ):
                await h.say(keyboards.BTN_HISTORY)
            self.assertEqual(len(h.transport.named("deleteMessages")), deletes_before)
            self.assertIn("Что-то пошло не так", h.transport.last_text())

    async def test_failed_handler_keeps_old_screens_tracked(self):
        async with Harness() as h:
            await h.say(keyboards.BTN_RATES)
            old = h.transport.sent_ids[-1]
            with (
                mock.patch("bot.handlers.start.section_screen", side_effect=RuntimeError("boom")),
                self.assertLogs("bot.handlers.errors", level="ERROR"),
            ):
                await h.say(keyboards.BTN_HISTORY)
            await h.say(keyboards.BTN_HELP)  # следующий успешный переход убирает и старый экран, и сообщение об ошибке
            self.assertIn(old, deleted_ids(h))
            self.assertIn(h.transport.sent_ids[-2], deleted_ids(h))

    async def test_handler_that_shows_nothing_deletes_nothing(self):
        async with Harness() as h:
            await h.say(keyboards.BTN_RATES)
            deletes_before = len(h.transport.named("deleteMessages"))
            with mock.patch("bot.handlers.start.show", mock.AsyncMock()):
                message_id = await h.say(keyboards.BTN_HISTORY)
            self.assertEqual(len(h.transport.named("deleteMessages")), deletes_before)
            self.assertNotIn(message_id, deleted_ids(h))

    async def test_garbage_callback_deletes_nothing(self):
        async with Harness() as h:
            await h.say(keyboards.BTN_RATES)
            deletes_before = len(h.transport.named("deleteMessages"))
            await h.tap("nav:nowhere")
            self.assertEqual(len(h.transport.named("deleteMessages")), deletes_before)

    async def test_non_private_chat_is_ignored(self):
        async with Harness() as h:
            group = {"id": -100, "type": "group", "title": "g"}
            await h._process(
                {
                    "message": {
                        "message_id": 7,
                        "date": 1_700_000_000,
                        "chat": group,
                        "from": USER,
                        "text": keyboards.BTN_RATES,
                    }
                }
            )
            self.assertEqual(h.transport.named("deleteMessages"), [])
            self.assertNotIn(screens.STORE_KEY, h.user_data)


class UntrackedTests(FlowTestCase):
    async def test_untracked_message_is_never_deleted(self):
        async def notify(update, context):
            with screens.untracked():
                await context.bot.send_message(update.effective_chat.id, "🔔 уведомление")

        async with Harness() as h:
            h.app.add_handler(MessageHandler(filters.Text([keyboards.BTN_HISTORY]), notify), group=1)
            await h.say("/start")
            await h.say(keyboards.BTN_HISTORY)
            notice = [params for params in h.transport.named("sendMessage") if params["text"] == "🔔 уведомление"]
            self.assertEqual(len(notice), 1)
            notice_id = h.transport.sent_ids[-1]  # группа 0 показала экран, группа 1 — уведомление следом
            await h.say(keyboards.BTN_RATES)
            await h.say(keyboards.BTN_HELP)
            self.assertNotIn(notice_id, deleted_ids(h))
            self.assertNotIn(notice_id, [entry[0] for entry in h.user_data[screens.STORE_KEY]])

    async def test_message_to_another_chat_is_not_tracked(self):
        async def broadcast(update, context):
            await context.bot.send_message(777, "для другого пользователя")

        async with Harness() as h:
            h.app.add_handler(CommandHandler("rates", broadcast), group=1)
            await h.say("/rates")
            other = h.transport.sent_ids[-1]  # основной хендлер (группа 0) отправил карточку, этот — следом
            tracked = [entry[0] for entry in h.user_data[screens.STORE_KEY]]
            self.assertNotIn(other, tracked)
            await h.say(keyboards.BTN_HELP)
            self.assertNotIn(other, deleted_ids(h))


class KeyboardSafetyTests(FlowTestCase):
    async def test_keyboard_message_survives_until_new_keyboard_is_sent(self):
        async with Harness() as h:
            await h.say("/start")
            first_welcome = h.transport.sent_ids[0]
            await h.say(keyboards.BTN_RATES)
            await h.say("250")
            self.assertNotIn(first_welcome, deleted_ids(h))

            await h.say("/start")  # новое приветствие с клавиатурой — старое можно убрать
            self.assertIn(first_welcome, deleted_ids(h))
            self.assertNotIn(h.transport.sent_ids[-2], deleted_ids(h))

    async def test_hint_does_not_take_over_keyboard_duty(self):
        async with Harness() as h:
            await h.say("/start")
            welcome = h.transport.sent_ids[0]
            deleted_before = deleted_ids(h)
            typed = await h.say("привет как дела")  # подсказка идёт без нижнего меню
            hint = h.transport.sent_ids[-1]
            self.assertEqual(deleted_ids(h), deleted_before)  # подсказка текущий экран не вытесняет

            await h.say(keyboards.BTN_RATES)
            self.assertIn(hint, deleted_ids(h))
            self.assertIn(typed, deleted_ids(h))
            self.assertNotIn(welcome, deleted_ids(h))  # нижнее меню по-прежнему держится на приветствии

    async def test_unknown_command_and_its_hint_are_deleted_with_next_screen(self):
        async with Harness() as h:
            await h.say("/start")
            typed = await h.say("/cancel")
            hint = h.transport.sent_ids[-1]
            self.assertNotIn("reply_markup", h.transport.named("sendMessage")[-1])
            await h.say(keyboards.BTN_RATES)
            self.assertIn(typed, deleted_ids(h))
            self.assertIn(hint, deleted_ids(h))


class FailureTolerance(FlowTestCase):
    async def test_delete_failure_is_logged_and_does_not_break_update(self):
        async with Harness() as h:
            await h.say(keyboards.BTN_RATES)
            h.transport.fail_delete_with = "Bad Request: message can't be deleted"
            with self.assertLogs("bot.screens", level="ERROR"):
                await h.say(keyboards.BTN_HISTORY)
            self.assertIn("История", h.transport.last_text())
            h.transport.fail_delete_with = None
            await h.say(keyboards.BTN_HELP)
            self.assertIn("Как пользоваться", h.transport.last_text())

    async def test_store_failure_is_logged_and_does_not_break_update(self):
        async with Harness() as h:
            with (
                mock.patch.object(screens.ScreenApplication, "_update_store", side_effect=RuntimeError("db")),
                self.assertLogs("bot.screens", level="ERROR"),
            ):
                await h.say(keyboards.BTN_RATES)
            self.assertIn("Курсы валют", h.transport.last_text())

    async def test_recording_failure_is_logged_and_does_not_break_update(self):
        async with Harness() as h:
            with (
                mock.patch.object(screens, "_record", side_effect=RuntimeError("bad")),
                self.assertLogs("bot.screens", level="ERROR"),
            ):
                await h.say(keyboards.BTN_RATES)
            self.assertIn("Курсы валют", h.transport.last_text())

    async def test_garbage_in_store_is_tolerated(self):
        for garbage in ("junk", 5, [None, "x", (1,), (1, 2, 3), ("a", 1.0, False), (True, 1.0, False)], {"a": 1}):
            with self.subTest(garbage=garbage):
                async with Harness() as h:
                    h.user_data[screens.STORE_KEY] = garbage
                    await h.say(keyboards.BTN_RATES)
                    self.assertIn("Курсы валют", h.transport.last_text())
                    self.assertEqual([e[0] for e in h.user_data[screens.STORE_KEY]], [h.transport.sent_ids[-1]])


class StorageLimitsTests(unittest.TestCase):
    def test_entries_older_than_ttl_are_dropped(self):
        now = 1_000_000.0
        raw = [
            (1, now - screens.SCREEN_TTL - 1, False),
            (2, now - screens.SCREEN_TTL + 60, False),
            (3, now, True),
        ]
        self.assertEqual([e.message_id for e in screens._load(raw, now)], [2, 3])

    def test_ttl_is_below_telegram_48h_limit(self):
        self.assertLess(screens.SCREEN_TTL, 48 * 3600)

    def test_only_newest_entries_are_kept_per_chat(self):
        now = time.time()
        raw = [(i, now, False) for i in range(screens.MAX_TRACKED + 10)]
        loaded = screens._load(raw, now)
        self.assertEqual(len(loaded), screens.MAX_TRACKED)
        self.assertEqual(loaded[-1].message_id, screens.MAX_TRACKED + 9)


class PersistenceTests(FlowTestCase):
    async def test_tracked_screens_survive_restart(self):
        data_dir = tempfile.mkdtemp(prefix="currency-bot-tests-")
        async with Harness(data_dir) as h:
            await h.say(keyboards.BTN_RATES)
            card = h.transport.sent_ids[-1]
        async with Harness(data_dir) as h2:
            await h2.say(keyboards.BTN_HISTORY)
            self.assertIn(card, deleted_ids(h2))


class WiringTests(unittest.TestCase):
    def test_application_uses_screen_tracking(self):
        with mock.patch.object(main, "DATA_DIR", tempfile.mkdtemp(prefix="currency-bot-tests-")):
            app = main.build_application()
        self.assertIsInstance(app, screens.ScreenApplication)
        self.assertIsInstance(app.bot.request, screens.TrackingRequest)


if __name__ == "__main__":
    unittest.main()
