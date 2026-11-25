"""Поддельный транспорт Telegram Bot API: реальный Application PTB без сети."""

import itertools
import json
import os
import tempfile
from typing import Any
from unittest import mock

os.environ.setdefault("BOT_TOKEN", "123:test-token")

import main  # noqa: E402  (нужен BOT_TOKEN/DATA_DIR в окружении до импорта)
from telegram import Update  # noqa: E402
from telegram.error import BadRequest  # noqa: E402
from telegram.request import HTTPXRequest  # noqa: E402

USER = {"id": 1, "is_bot": False, "first_name": "Аня"}
CHAT = {"id": 1, "type": "private", "first_name": "Аня"}


class Transport:
    """Запоминает все вызовы Bot API и отвечает заглушками."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_edit_with: str | None = None
        self.fail_delete_with: str | None = None
        self.sent_ids: list[int] = []  # id всех сообщений, которые «отправил» бот, по порядку
        self._ids = itertools.count(100)

    async def do_request(self, _request, url, method, request_data=None, **_kwargs):
        name = url.rsplit("/", 1)[-1]
        params = dict(request_data.parameters) if request_data else {}
        self.calls.append((name, params))

        if name == "getMe":
            result: Any = {"id": 99, "is_bot": True, "first_name": "Bot", "username": "bot"}
        elif name in ("sendMessage", "editMessageText"):
            if name == "editMessageText" and self.fail_edit_with:
                body = {"ok": False, "error_code": 400, "description": self.fail_edit_with}
                return 400, json.dumps(body).encode()
            result = {
                "message_id": params.get("message_id") or next(self._ids),
                "date": 1_700_000_000,
                "chat": {**CHAT, "id": int(params.get("chat_id", CHAT["id"]))},
                "text": params.get("text", ""),
            }
            if name == "sendMessage":
                self.sent_ids.append(result["message_id"])
        elif name == "deleteMessages" and self.fail_delete_with:
            body = {"ok": False, "error_code": 400, "description": self.fail_delete_with}
            return 400, json.dumps(body).encode()
        else:
            result = True
        return 200, json.dumps({"ok": True, "result": result}).encode()

    def named(self, name: str) -> list[dict[str, Any]]:
        return [params for call, params in self.calls if call == name]

    def last_text(self) -> str:
        texts = [p["text"] for n, p in self.calls if n in ("sendMessage", "editMessageText")]
        return texts[-1]

    def last_markup(self) -> dict[str, Any]:
        markups = [
            p["reply_markup"] for n, p in self.calls if n in ("sendMessage", "editMessageText") and "reply_markup" in p
        ]
        markup = markups[-1]
        return json.loads(markup) if isinstance(markup, str) else markup


def callback_data_of(markup: dict[str, Any]) -> list[str]:
    return [b["callback_data"] for row in markup["inline_keyboard"] for b in row]


def button_texts(markup: dict[str, Any]) -> list[str]:
    return [b["text"] for row in markup["inline_keyboard"] for b in row]


class Harness:
    """Запускает приложение main.build_application() и скармливает ему апдейты."""

    def __init__(self, data_dir: str | None = None) -> None:
        """data_dir — каталог персистентности; по умолчанию новый временный (изоляция тестов)."""
        self.transport = Transport()
        self._data_dir = data_dir or tempfile.mkdtemp(prefix="currency-bot-tests-")
        self._patches = [
            mock.patch.object(
                HTTPXRequest, "do_request", lambda req, *a, **kw: self.transport.do_request(req, *a, **kw)
            ),
            mock.patch.object(main, "DATA_DIR", self._data_dir),
        ]
        self._ids = itertools.count(1)
        self.app = None

    async def __aenter__(self) -> "Harness":
        for patch in self._patches:
            patch.start()
        self.app = main.build_application()
        await self.app.initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.app.shutdown()
        for patch in self._patches:
            patch.stop()

    async def _process(self, payload: dict[str, Any]) -> None:
        update = Update.de_json({"update_id": next(self._ids), **payload}, self.app.bot)
        await self.app.process_update(update)

    async def say(self, text: str) -> int:
        """Отправляет текст от пользователя; возвращает message_id этого сообщения."""
        message: dict[str, Any] = {
            "message_id": next(self._ids) + 1000,
            "date": 1_700_000_000,
            "chat": CHAT,
            "from": USER,
            "text": text,
        }
        if text.startswith("/"):
            message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
        await self._process({"message": message})
        return message["message_id"]

    async def tap(self, data: str) -> None:
        await self._process(
            {
                "callback_query": {
                    "id": str(next(self._ids)),
                    "from": USER,
                    "chat_instance": "ci",
                    "message": {"message_id": 500, "date": 1_700_000_000, "chat": CHAT, "text": "old"},
                    "data": data,
                }
            }
        )

    @property
    def user_data(self) -> dict[str, Any]:
        return self.app.user_data[USER["id"]]


def raise_bad_request(message: str):
    raise BadRequest(message)
