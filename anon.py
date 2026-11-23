"""AnonBot's conversations and transcripts.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("anon.py is loaded section by section by main.py -- run main.py")


# ─── module: anon_bot.anon_logic ─────────────────────────────────────────────
"""Pure-ish logic for AnonBot -- StickerBot-family sibling #4 (see ARCHITECTURE.md)."""
import html
import os
import time
from collections import OrderedDict, deque

from telegram import (InputMediaAnimation, InputMediaAudio, InputMediaDocument, InputMediaPhoto,
                      InputMediaVideo)
from telegram.constants import ParseMode
from telegram.error import BadRequest

TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024
SAFETY = 24

def italicize(text: str) -> str:
    """Someone else's words, marked as theirs."""
    return f"<i>{html.escape(text)}</i>"

def split_to_fit(body: str, first_budget: int, later_budget: int) -> list[str]:
    """`body` cut into pieces that will each survive escaping, preferring to break at a newline and then at a space."""
    pieces: list[str] = []
    rest = body
    budget = first_budget
    while rest:
        if len(html.escape(rest)) <= budget:
            pieces.append(rest)
            break

        cut = budget
        while cut > 1 and len(html.escape(rest[:cut])) > budget:
            cut -= max(1, (len(html.escape(rest[:cut])) - budget) // 4 + 1)
        window = rest[:cut]
        at = max(window.rfind("\n"), window.rfind(" "))
        if at > cut // 2:
            cut = at + 1
        pieces.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
        budget = later_budget
    return [p for p in pieces if p] or [body]

MSGS_PER_MINUTE = int(os.environ.get("ABOT_MSGS_PER_MINUTE", "20"))
NEW_CONV_COOLDOWN = int(os.environ.get("ABOT_NEW_CONV_COOLDOWN_SEC", "30"))
_MAX_TRACKED = 4096

_recent_messages: "OrderedDict[int, deque]" = OrderedDict()
_recent_opens: "OrderedDict[int, float]" = OrderedDict()

def _trim(store) -> None:
    while len(store) > _MAX_TRACKED:
        store.popitem(last=False)

def message_allowed(user_id: int) -> int:
    """0 if this person may send now, otherwise the whole seconds to wait."""
    if MSGS_PER_MINUTE <= 0:
        return 0
    now = time.monotonic()
    window = _recent_messages.setdefault(user_id, deque())
    _recent_messages.move_to_end(user_id)
    _trim(_recent_messages)
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= MSGS_PER_MINUTE:
        return max(1, int(60 - (now - window[0])) + 1)
    window.append(now)
    return 0

def new_conversation_allowed(user_id: int) -> int:
    """0 if this person may open another conversation now, otherwise the whole seconds to wait."""
    if NEW_CONV_COOLDOWN <= 0:
        return 0
    now = time.monotonic()
    last = _recent_opens.get(user_id)
    if last is not None and now - last < NEW_CONV_COOLDOWN:
        return max(1, int(NEW_CONV_COOLDOWN - (now - last)) + 1)
    _recent_opens[user_id] = now
    _recent_opens.move_to_end(user_id)
    _trim(_recent_opens)
    return 0

RELAYABLE_REACTIONS = (
    "❤", "👍", "👎", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "❤‍🔥", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆",
    "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄",
    "😘", "💊", "🙊", "😎", "👾", "🤷‍♂", "🤷", "🤷‍♀", "😡",
)

REACTION_NOTE_SECONDS = float(os.environ.get("ABOT_REACTION_NOTE_SECONDS", "8"))

REACTION_NOTE_EVERY_SECONDS = int(os.environ.get("ABOT_REACTION_NOTE_EVERY_SECONDS", "30"))
_reaction_notes: "OrderedDict[int, float]" = OrderedDict()

def _reaction_id(reaction) -> "tuple[str, str]":
    kind = getattr(reaction, "type", None) or "emoji"
    if kind == "emoji":
        return kind, getattr(reaction, "emoji", "") or ""
    if kind == "custom_emoji":
        return kind, getattr(reaction, "custom_emoji_id", "") or ""
    return kind, ""

def pick_reaction(old, new) -> "tuple[list[str], str | None]":
    """What to put on the twin, and which note the reactor needs, if any."""
    before = {_reaction_id(r) for r in old or ()}
    after = [_reaction_id(r) for r in new or ()]
    standard = [value for kind, value in after if kind == "emoji" and value]
    added = [(kind, value) for kind, value in after if (kind, value) not in before]
    added_standard = [value for kind, value in added if kind == "emoji" and value]
    if added_standard:
        chosen = [added_standard[-1]]
    else:
        chosen = standard[:1]
    note = None
    if any(kind != "emoji" for kind, _ in added):
        note = "reaction_not_passed"
    elif added_standard and len(standard) > 1:
        note = "reaction_one_only"
    return chosen, note

def reaction_note_allowed(user_id: int) -> bool:
    """True at most once per REACTION_NOTE_EVERY_SECONDS for one person."""
    now = time.monotonic()
    last = _reaction_notes.get(user_id)
    if last is not None and now - last < REACTION_NOTE_EVERY_SECONDS:
        return False
    _reaction_notes[user_id] = now
    _reaction_notes.move_to_end(user_id)
    _trim(_reaction_notes)
    return True

def compose(header: "str | None", body: "str | None", italic: bool = True) -> str:
    """Bot's own header upright, the person's own words in italics."""
    parts = []
    if header:
        parts.append(html.escape(header))
    if body:
        parts.append(italicize(body) if italic else html.escape(body))
    return "\n\n".join(parts)

class EditTooLong(ValueError):
    """The edited message no longer fits in one message, so its twin cannot take it."""

def _edited_media(message, caption: "str | None"):
    """The edited message's file, as what replaces the twin's, or None for a kind that cannot be swapped."""
    common = {"caption": caption, "parse_mode": ParseMode.HTML}
    if message.photo:
        return InputMediaPhoto(message.photo[-1].file_id, **common)
    if message.animation is not None:
        return InputMediaAnimation(message.animation.file_id, **common)
    if message.video is not None:
        return InputMediaVideo(message.video.file_id, **common)
    if message.audio is not None:
        return InputMediaAudio(message.audio.file_id, **common)
    if message.document is not None:
        return InputMediaDocument(message.document.file_id, **common)
    return None

async def edit_relayed(bot, message, to_chat_id, twin_id, header=None, reply_markup=None, italic=True) -> None:
    """Carry an edit of `message` onto its one twin in `to_chat_id`, with the same header and buttons it was
    sent with. Raises EditTooLong when it no longer fits, BadRequest when Telegram refuses."""
    if message.text is not None:
        text = compose(header, message.text, italic)
        if len(text) > TEXT_LIMIT:
            raise EditTooLong()
        await bot.edit_message_text(chat_id=to_chat_id, message_id=twin_id, text=text,
                                    parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return
    caption = compose(header, message.caption, italic) or None
    if caption is not None and len(caption) > CAPTION_LIMIT:
        raise EditTooLong()
    media = _edited_media(message, caption)
    if media is not None:
        await bot.edit_message_media(chat_id=to_chat_id, message_id=twin_id, media=media,
                                     reply_markup=reply_markup)
        return
    await bot.edit_message_caption(chat_id=to_chat_id, message_id=twin_id, caption=caption,
                                   parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def relay_content(
    bot, message, to_chat_id,
    reply_to_message_id=None, reply_markup=None, header=None, italic=True,
):
    """Delivers `message`'s content into `to_chat_id`, preserving whatever it is (text, photo, video, voice, sticker, document, ...) with no "Forwarded from" tag -- copy_message handles every content type Telegram lets a bot copy, so there is no need to branch on message.photo / message.video / etc."""

    def _compose(body: str | None) -> str:
        return compose(header, body, italic)

    async def _send_text(text, reply_to, markup):
        try:
            return await bot.send_message(
                chat_id=to_chat_id, text=text, reply_to_message_id=reply_to,
                reply_markup=markup, parse_mode=ParseMode.HTML,
            )
        except BadRequest as exc:
            if reply_to and "repl" in str(exc).lower():
                return await bot.send_message(
                    chat_id=to_chat_id, text=text, reply_markup=markup,
                    parse_mode=ParseMode.HTML,
                )
            raise

    async def _copy(reply_to, markup, caption=None):
        kwargs = {}
        if caption is not None:
            kwargs = {"caption": caption, "parse_mode": ParseMode.HTML}
        try:
            return await bot.copy_message(
                chat_id=to_chat_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id,
                reply_to_message_id=reply_to,
                reply_markup=markup,
                **kwargs,
            )
        except BadRequest as exc:
            if reply_to and "repl" in str(exc).lower():
                return await bot.copy_message(
                    chat_id=to_chat_id, from_chat_id=message.chat_id,
                    message_id=message.message_id, reply_markup=markup, **kwargs,
                )
            raise

    header_cost = len(html.escape(header)) + 2 if header else 0

    def _pieces(body: str, limit: int) -> list[str]:
        return split_to_fit(body, limit - header_cost - SAFETY, limit - SAFETY)

    if message.text is not None:
        parts = _pieces(message.text, TEXT_LIMIT)
        sent = []
        for n, part in enumerate(parts):

            text = _compose(part) if n == 0 else italicize(part)
            sent.append(await _send_text(
                text,
                reply_to_message_id if n == 0 else None,
                reply_markup if n == len(parts) - 1 else None,
            ))
        return sent

    if message.caption is not None:
        composed = _compose(message.caption)
        if len(composed) <= CAPTION_LIMIT:
            return [await _copy(reply_to_message_id, reply_markup, caption=composed)]

        parts = _pieces(message.caption, TEXT_LIMIT)
        sent = []
        for n, part in enumerate(parts):
            sent.append(await _send_text(
                _compose(part) if n == 0 else italicize(part),
                reply_to_message_id if n == 0 else None,
                None,
            ))
        sent.append(await _copy(None, reply_markup))
        return sent

    sent = []
    if header:
        sent.append(await _send_text(_compose(None), reply_to_message_id, None))
        reply_to_message_id = None

    sent.append(await _copy(reply_to_message_id, reply_markup))
    return sent
