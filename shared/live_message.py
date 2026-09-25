"""One bot message that keeps evolving -- for as long as it is still the
last thing in the chat.

Editing a message in place is the right shape for anything that changes:
a menu the user is walking through, a "converting..." that becomes
"added", a pack status line that counts up. It is how fstik and BotFather
read, and it beats a fresh message per step.

It has one failure mode, and it is invisible from the bot's side. The edit
lands wherever that message already is. If the user has typed anything
since -- another photo, "ok", a stray sticker -- the message being edited
is no longer at the bottom of the chat, so the user is looking at their own
message while the bot silently rewrites something above it. On a phone that
is off-screen. The bot answered; nobody saw it.

So every evolving message here carries a watermark: the id of the newest
message the *user* had sent in that chat at the moment the bot last wrote
it. Before each edit that watermark is compared with what has arrived
since:

  nothing new        -> edit in place, exactly as before
  the user spoke     -> send a new message, and evolve that one from now on

Only the user's own messages count. A button tap does not (the message they
tapped *is* the live one), and neither does the bot's own chatter -- except
where a bot deliberately sends something underneath a live message, which
is what bump() is for.

The watermark lives in this module, keyed by chat, in a bounded dict. It is
deliberately not persisted: a process that has just started has no idea what
the chat looks like, and the safe assumption there is "something happened
while I was away", which is what an empty watermark already means -- the
first write after a restart sends a new message instead of editing a message
the user may have scrolled far past. save()/restore() carry the *handle*
across a restart (see lifecycle.py), not the watermark.

This file is copied byte-identically into every bot, like shared_features.py
and family_link.py -- each bot is its own repo and its own deployment, so
nothing is imported across folders.
"""
from __future__ import annotations

import logging
from collections import OrderedDict

from telegram.error import BadRequest

logger = logging.getLogger(__name__)

# Watermarks are per chat and tiny (two ints), but a bot that has met a lot
# of people would still grow one entry per chat forever. The oldest are
# dropped once there are more than this many; losing one costs a single
# unnecessary new message, which is the safe direction to fail in.
MAX_TRACKED_CHATS = 2048

_last_incoming: "OrderedDict[int, int]" = OrderedDict()

# Message-only kwargs that edit_message_text has no equivalent for. Passing
# one to an edit is a TypeError, so they are dropped there rather than made
# every caller's problem -- a caller that sets do_quote is describing the
# first send, and there is nothing sensible for an in-place edit to do with
# it anyway.
_SEND_ONLY_KWARGS = frozenset({
    "do_quote", "reply_to_message_id", "allow_sending_without_reply",
    "reply_parameters", "disable_notification", "protect_content",
    "message_effect_id", "allow_paid_broadcast", "message_thread_id",
})


# ---------------------------------------------------------------------------
# The watermark
# ---------------------------------------------------------------------------

def note_incoming(chat_id: int, message_id: int) -> None:
    """Remember that the user has spoken in this chat. Telegram's message
    ids climb within a chat, so the largest one seen is the newest."""
    current = _last_incoming.get(chat_id, 0)
    if message_id > current:
        _last_incoming[chat_id] = message_id
    _last_incoming.move_to_end(chat_id)
    while len(_last_incoming) > MAX_TRACKED_CHATS:
        _last_incoming.popitem(last=False)


def note_update(update) -> None:
    """Called for every update, from the same place each bot already counts
    active users (track_activity, group=-1, before any real handler).

    Deliberately only update.message: a callback query carries the *bot's*
    own message -- the one holding the button that was tapped -- and counting
    that would mean every tap immediately declared the menu stale and
    replaced it with a fresh copy of itself below the old one."""
    message = getattr(update, "message", None) or getattr(update, "edited_message", None)
    if message is not None:
        note_incoming(message.chat_id, message.message_id)


def bump(chat_id: int, message_id: int) -> None:
    """Same effect as the user having spoken: whatever live message this
    chat had is now buried and the next write to it starts fresh.

    For the case the watermark cannot see -- the bot itself sending
    something *underneath* a live message. Most bots here have no such
    place (the live message is the only thing they send), which is why this
    is an explicit call rather than a wrapper around every send."""
    note_incoming(chat_id, message_id)


def _edit_kwargs(kwargs: dict) -> dict:
    return {k: v for k, v in kwargs.items() if k not in _SEND_ONLY_KWARGS}


# ---------------------------------------------------------------------------
# The handle
# ---------------------------------------------------------------------------

class LiveMessage:
    """A handle on one evolving message.

    Hold it for as long as the thing it is reporting on lasts -- a local
    variable for a single conversion, or user_data via save()/restore() for
    something that spans several messages, like a pack-editing session.
    """

    __slots__ = ("chat_id", "message_id", "watermark")

    def __init__(self, chat_id: int, message_id: int, watermark: int | None = None):
        self.chat_id = chat_id
        self.message_id = message_id
        # Where the chat stood when this message was written. Normally this
        # is redundant -- it never exceeds what note_incoming() has already
        # recorded -- and it earns its place in exactly one case: a handle
        # restored into a process whose watermark table is empty, where it
        # is the only evidence left of how far the chat had got.
        self.watermark = _last_incoming.get(chat_id, 0) if watermark is None else watermark

    def _still_last(self) -> bool:
        return self.message_id >= max(self.watermark, _last_incoming.get(self.chat_id, 0))

    # ---- making one ----

    @classmethod
    async def send(cls, bot, chat_id: int, text: str, **kwargs) -> "LiveMessage":
        message = await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return cls(chat_id, message.message_id)

    @classmethod
    async def reply_to(cls, message, text: str, **kwargs) -> "LiveMessage":
        """Start a live message as a reply to the one that triggered it --
        the ordinary "user sent a video, bot says converting..." case."""
        sent = await message.reply_text(text, **kwargs)
        return cls(sent.chat_id, sent.message_id)

    @classmethod
    def adopt(cls, message) -> "LiveMessage":
        """Take over a message the bot already sent -- typically the one
        holding the button that was just tapped, so a menu keeps evolving in
        the same place instead of starting a new one below itself."""
        return cls(message.chat_id, message.message_id)

    # ---- carrying one across handlers, and across restarts ----

    def save(self) -> dict:
        """A plain dict for user_data. JSON-safe on purpose: this is what
        lets an editing session survive a redeploy (see lifecycle.py)."""
        return {"chat_id": self.chat_id, "message_id": self.message_id,
                "watermark": self.watermark}

    @classmethod
    def restore(cls, state) -> "LiveMessage | None":
        """The other half of save(). None for anything that isn't one, so a
        caller can hand it whatever user_data.get() returned.

        The stored watermark and the live one are combined with max(), so a
        handle carried across a restart is judged against the later of "how
        far the chat had got when this was written" and "how far it has got
        since this process started"."""
        if not isinstance(state, dict):
            return None
        try:
            chat_id = int(state["chat_id"])
            message_id = int(state["message_id"])
        except (KeyError, TypeError, ValueError):
            return None
        stored = state.get("watermark") or 0
        return cls(chat_id, message_id, max(int(stored), _last_incoming.get(chat_id, 0)))

    # A note on restarts, since it looks like a gap and is not one: a process
    # that has just come up has an empty watermark table, so on the face of
    # it a restored handle could edit a message the user has since scrolled
    # far past. It cannot, because Telegram holds undelivered updates for 24
    # hours and hands them over on the first getUpdates -- so anything said
    # during the downtime is recorded by note_update() before any handler
    # that might write to this message runs.

    # ---- evolving it ----

    async def set(self, bot, text: str, **kwargs) -> "LiveMessage":
        """Show `text`, in place if this message is still the last one in the
        chat and as a new message otherwise. Returns self, re-pointed at
        whichever message now carries the text, so callers can chain or just
        ignore the result.

        Never raises: a live message is a progress report, and failing the
        operation it is reporting on because its own edit did not land would
        be the wrong trade every time.
        """
        if self._still_last():
            try:
                await bot.edit_message_text(
                    chat_id=self.chat_id, message_id=self.message_id, text=text,
                    **_edit_kwargs(kwargs),
                )
                self.watermark = _last_incoming.get(self.chat_id, 0)
                return self
            except BadRequest as exc:
                lowered = str(exc).lower()
                if "not modified" in lowered:
                    # Same text and same markup as last time. Nothing to do,
                    # and nothing wrong.
                    return self
                if "not found" not in lowered and "can't be edited" not in lowered:
                    logger.debug("Live message edit refused (%s); sending a new one", exc)
            except Exception:
                logger.debug("Live message edit failed; sending a new one", exc_info=True)

        try:
            sent = await bot.send_message(chat_id=self.chat_id, text=text, **kwargs)
        except Exception:
            logger.debug("Could not send a live message", exc_info=True)
            return self
        self.message_id = sent.message_id
        self.watermark = _last_incoming.get(self.chat_id, 0)
        return self

    async def finish(self, bot, text: str, **kwargs) -> None:
        """The last thing this message will ever say."""
        await self.set(bot, text, **kwargs)

    async def delete(self, bot) -> None:
        """Take it away entirely -- for a progress message whose result
        arrives as a file or a photo of its own, where leaving "Downloading
        ..." above the thing it was waiting for reads as a second, stuck
        request."""
        try:
            await bot.delete_message(chat_id=self.chat_id, message_id=self.message_id)
        except Exception:
            logger.debug("Could not delete a live message", exc_info=True)


# ---------------------------------------------------------------------------
# The one-liner
# ---------------------------------------------------------------------------

async def edit_in_place(message, bot, text: str, **kwargs) -> "LiveMessage":
    """Rewrite one of the bot's own messages -- typically the one holding the
    button that was just tapped -- or send a new one if the user has said
    anything since. The single most common use of this file, and the drop-in
    replacement for `await message.edit_text(...)`.

    Returns the handle, which anything that keeps evolving the same message
    should hold on to; anything that is finished with it can ignore the
    result. Never raises: a menu that could not be redrawn is not a reason to
    fail whatever the tap was actually asking for.
    """
    return await LiveMessage.adopt(message).set(bot, text, **kwargs)


# ---------------------------------------------------------------------------
# The user_data form
# ---------------------------------------------------------------------------
# Most bots keep exactly one live message per user (the status line of
# whatever they are in the middle of), so the two calls below are the whole
# API for that case: show() writes it, drop() forgets it.

DEFAULT_KEY = "live_message"


async def show(context, chat_id: int, text: str, key: str = DEFAULT_KEY, **kwargs) -> "LiveMessage":
    """Write this user's live message, creating it on first call."""
    live = LiveMessage.restore(context.user_data.get(key))
    if live is None:
        live = await LiveMessage.send(context.bot, chat_id, text, **kwargs)
    else:
        await live.set(context.bot, text, **kwargs)
    context.user_data[key] = live.save()
    return live


def drop(context, key: str = DEFAULT_KEY) -> None:
    context.user_data.pop(key, None)
