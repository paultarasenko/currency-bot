"""«Чистый чат»: в чате остаётся только актуальный экран.

Как это устроено
- `TrackingRequest` (подставляется в Bot) запоминает сообщения, которые бот отправил в чат автора
  текущего апдейта (методы send*; edit* не учитываются). Контекст апдейта — через ContextVar.
- `ScreenApplication` оборачивает обработку апдейта: handler отрабатывает и показывает новый экран,
  и только после этого удаляются старые экраны и (при «переходе») сообщение с названием кнопки.

Правила
- Переход — нажатие кнопки нижнего меню или команда из списка команд бота.
- Старые экраны удаляются, когда апдейт показал новый экран: это переход либо отправленное
  сообщение с inline-кнопками (так «живая» карточка, присланная в ответ на введённую сумму,
  не копится). Сообщения без inline-кнопок (подсказки об ошибке ввода) текущий экран не вытесняют.
- Текст, который человек ввёл руками (не кнопка меню и не команда из списка), запоминается и удаляется
  вместе со старыми экранами при СЛЕДУЮЩЕМ новом экране, а не сразу: рядом с ответом виден последний запрос.
- Не удаляются: сообщения, отправленные внутри `untracked()`; сообщения в другие чаты.
  Если хендлер упал или ничего не отправил — не удаляется ничего (введённый текст всё равно запоминается).
- Сообщение с нижней клавиатурой не удаляется, пока апдейт не прислал новое сообщение с клавиатурой.
- Любой сбой учёта или удаления только пишется в лог. Работает только в private-чатах.
- Id сообщений лежат в `user_data["screens"]` и сохраняются тем же PicklePersistence, что и остальное.

Предполагается, что хендлеры блокирующие (block=True, по умолчанию в PTB): очистка запускается
после `process_update`.
"""

import json
import logging
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from telegram import Message, ReplyKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import Application
from telegram.request import HTTPXRequest, RequestData

logger = logging.getLogger(__name__)

STORE_KEY = "screens"
# Telegram не даёт удалять сообщения старше 48 часов — помним чуть меньше.
SCREEN_TTL = 47 * 3600
MAX_TRACKED = 60


@dataclass(frozen=True)
class _Sent:
    message_id: int
    sent_at: float
    reply_keyboard: bool
    inline: bool = False  # только внутри апдейта, в хранилище не пишется


@dataclass
class _UpdateContext:
    chat_id: int
    user_id: int
    user_message_id: int | None  # сообщение с названием кнопки, если апдейт — «переход»
    sent: list[_Sent] = field(default_factory=list)
    untracked_depth: int = 0
    failed: bool = False
    typed_message_id: int | None = None  # введённый руками текст: удаляется со следующим новым экраном

    @property
    def transition(self) -> bool:
        return self.user_message_id is not None


_current: ContextVar[_UpdateContext | None] = ContextVar("screens_current_update", default=None)


@contextmanager
def untracked() -> Iterator[None]:
    """Отправки внутри блока не запоминаются и не удаляются.

    Нужен для сообщений, которые должны остаться в чате (уведомление, квитанция), если получатель
    совпадает с автором апдейта — для других чатов учёт и так не ведётся."""
    ctx = _current.get()
    if ctx is None:
        yield
        return
    ctx.untracked_depth += 1
    try:
        yield
    finally:
        ctx.untracked_depth -= 1


def reply_keyboard_texts(markup: ReplyKeyboardMarkup) -> frozenset[str]:
    """Тексты кнопок реальной reply-клавиатуры — единственный источник списка «переходов»."""
    return frozenset(button.text for row in markup.keyboard for button in row)


def _load(raw: Any, now: float) -> list[_Sent]:
    """Читает сохранённый список; терпим к мусору и отбрасывает записи старше SCREEN_TTL."""
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if (
            isinstance(item, (tuple, list))
            and len(item) == 3
            and isinstance(item[0], int)
            and not isinstance(item[0], bool)
            and isinstance(item[1], (int, float))
            and isinstance(item[2], bool)
            and now - item[1] < SCREEN_TTL
        ):
            result.append(_Sent(item[0], float(item[1]), item[2]))
    return result[-MAX_TRACKED:]


def _dump(entries: list[_Sent]) -> list[tuple[int, float, bool]]:
    return [(e.message_id, e.sent_at, e.reply_keyboard) for e in entries]


def _markup_kind(raw: Any) -> tuple[bool, bool]:
    """(есть нижняя клавиатура, есть inline-кнопки) по параметру reply_markup запроса."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return False, False
    if not isinstance(raw, dict):
        return False, False
    return "keyboard" in raw, "inline_keyboard" in raw


def _record(url: str, request_data: RequestData | None, payload: bytes) -> None:
    ctx = _current.get()
    if ctx is None or ctx.untracked_depth:
        return
    if not url.rsplit("/", 1)[-1].lower().startswith("send"):
        return
    body = json.loads(payload)
    if not isinstance(body, dict) or not body.get("ok"):
        return
    result = body.get("result")
    reply_keyboard, inline = _markup_kind(request_data.parameters.get("reply_markup") if request_data else None)
    now = time.time()
    for item in result if isinstance(result, list) else [result]:
        if not isinstance(item, dict):  # sendChatAction и т. п. возвращают True
            continue
        message_id, chat = item.get("message_id"), item.get("chat")
        if isinstance(message_id, int) and isinstance(chat, dict) and chat.get("id") == ctx.chat_id:
            ctx.sent.append(_Sent(message_id, now, reply_keyboard, inline))


class TrackingRequest(HTTPXRequest):
    """HTTP-слой Bot: запоминает отправленные в чат автора апдейта сообщения (см. модуль)."""

    async def do_request(
        self,
        url: str,
        method: str,
        request_data: RequestData | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[int, bytes]:
        code, payload = await super().do_request(url, method, request_data, *args, **kwargs)
        try:
            _record(url, request_data, payload)
        except Exception:
            # URL не логируем: в нём токен бота.
            logger.exception("Чистый чат: не удалось запомнить отправленное сообщение")
        return code, payload


class ScreenApplication(Application[Any, Any, Any, Any, Any, Any]):
    def __init__(
        self,
        *,
        transition_texts: Iterable[str],
        transition_commands: Iterable[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._transition_texts = frozenset(transition_texts)
        self._transition_commands = frozenset(command.lower() for command in transition_commands)

    async def process_update(self, update: object) -> None:
        ctx = self._open_context(update)
        if ctx is None:
            await super().process_update(update)
            return
        token = _current.set(ctx)
        try:
            await super().process_update(update)
        finally:
            _current.reset(token)
        # Новый экран уже показан хендлером — теперь можно убирать старые.
        await self._close_context(ctx)

    async def process_error(
        self,
        update: object | None,
        error: Exception,
        job: Any = None,
        coroutine: Any = None,
    ) -> bool:
        # process_update не пробрасывает исключения хендлеров, поэтому о падении узнаём здесь.
        ctx = _current.get()
        if ctx is not None:
            ctx.failed = True
        return await super().process_error(update, error, job, coroutine)

    def _open_context(self, update: object) -> _UpdateContext | None:
        try:
            if not isinstance(update, Update):
                return None
            chat, user = update.effective_chat, update.effective_user
            if chat is None or user is None or chat.type != ChatType.PRIVATE:
                return None
            message = update.message
            if message is None and update.callback_query is None:
                return None
            is_transition = message is not None and self._is_transition(message)
            is_typed = message is not None and bool(message.text) and not is_transition
            return _UpdateContext(
                chat_id=chat.id,
                user_id=user.id,
                user_message_id=message.message_id if message is not None and is_transition else None,
                typed_message_id=message.message_id if message is not None and is_typed else None,
            )
        except Exception:
            logger.exception("Чистый чат: не удалось разобрать апдейт")
            return None

    def _is_transition(self, message: Message) -> bool:
        text = message.text
        if not text:
            return False
        if text in self._transition_texts:
            return True
        if text.startswith("/"):
            command = text.split(maxsplit=1)[0][1:].split("@", 1)[0].lower()
            return command in self._transition_commands
        return False

    async def _close_context(self, ctx: _UpdateContext) -> None:
        try:
            stale = self._update_store(ctx)
            if stale:
                await self.bot.delete_messages(ctx.chat_id, stale)
        except Exception:
            logger.exception("Чистый чат: не удалось обновить или удалить сообщения")

    def _update_store(self, ctx: _UpdateContext) -> list[int]:
        """Синхронно (без await) обновляет сохранённый список; возвращает id к удалению."""
        data = self.user_data[ctx.user_id]
        raw = data.get(STORE_KEY)
        tracked = _load(raw, time.time())
        stale: list[int] = []

        shows_new_screen = ctx.transition or any(sent.inline for sent in ctx.sent)
        if ctx.sent and shows_new_screen and not ctx.failed:
            new_keyboard = any(sent.reply_keyboard for sent in ctx.sent)
            # Последнее сообщение с нижней клавиатурой остаётся, пока не придёт новое с клавиатурой;
            # более ранние такие сообщения уже вытеснены более поздним и удаляются как обычные.
            holders = [e for e in tracked if e.reply_keyboard]
            kept = [] if new_keyboard else holders[-1:]
            kept_ids = {e.message_id for e in kept}
            stale = [e.message_id for e in tracked if e.message_id not in kept_ids]
            if ctx.user_message_id is not None:
                stale.append(ctx.user_message_id)
            tracked = kept

        if ctx.typed_message_id is not None:
            # Запоминаем после очистки: свой ввод уберётся со следующим новым экраном, а не сейчас.
            tracked.append(_Sent(ctx.typed_message_id, time.time(), False))

        dumped = _dump((tracked + ctx.sent)[-MAX_TRACKED:])
        if dumped != raw:
            if dumped:
                data[STORE_KEY] = dumped
            else:
                data.pop(STORE_KEY, None)
        return stale
