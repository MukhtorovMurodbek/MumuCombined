"""Pure-ish logic for AnonBot -- StickerBot-family sibling #4 (see
ARCHITECTURE.md). Same split as image_utils.py / convert_utils.py / video.py
in the other bots: this file owns the parts that don't need to know about
ApplicationBuilder/handlers, and bot.py owns the Telegram wiring.

relay_content() delivers one message's content into another chat as a plain
(non-forwarded) message, optionally as a native reply-to and/or with a header
line, and optionally with buttons. It is the one piece that makes a reply
"look like they actually replied" on the receiving end -- and it is also what
lets either side's chat thread several simultaneous conversations via
Telegram's native reply-quote instead of one flat, confusing feed.

Everything a *person* wrote is relayed in italics; everything the bot says
for itself (headers, confirmations, prompts) stays upright. In a chat where
both arrive in the same bubble stream, that one difference is what tells you
at a glance which words are somebody else's.
"""
import html
import os
import time
from collections import OrderedDict, deque

from telegram.constants import ParseMode
from telegram.error import BadRequest

# Telegram's own ceilings, and a little room. The limits are on the *parsed*
# text, so measuring the escaped-and-tagged string over-counts -- which is the
# direction to be wrong in: an occasional early split costs a second bubble,
# and getting it wrong the other way costs the message entirely.
TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024
SAFETY = 24


def italicize(text: str) -> str:
    """Someone else's words, marked as theirs. Escaped first: a guest who
    types <b>hi</b> should see <b>hi</b> arrive, not bold text, and should
    certainly not be able to close the tag this wraps them in."""
    return f"<i>{html.escape(text)}</i>"


def split_to_fit(body: str, first_budget: int, later_budget: int) -> list[str]:
    """`body` cut into pieces that will each survive escaping, preferring to
    break at a newline and then at a space.

    A header costs characters the sender never sees, so a guest who filled
    their message box exactly to Telegram's limit used to have the whole
    thing rejected -- and be told "Couldn't deliver that message: Message is
    too long", which reads as their fault. Splitting says everything they
    wrote, in the order they wrote it.
    """
    pieces: list[str] = []
    rest = body
    budget = first_budget
    while rest:
        if len(html.escape(rest)) <= budget:
            pieces.append(rest)
            break
        # Walk back from the largest slice that could possibly fit until the
        # escaped form does, then back further to a sensible break.
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


# ---------------------------------------------------------------------------
# Flood control
# ---------------------------------------------------------------------------
# An inbox link is meant to be posted somewhere public, and until now nothing
# at all bounded how fast a stranger could write into it: Block was the only
# defence, and Block is per Telegram account. This is deliberately in memory
# rather than in the database -- one process holds the polling lease, so there
# is exactly one counter to keep, and paying a round trip to a database in
# another continent on every message to enforce a per-minute limit would cost
# more than the limit saves. A redeploy forgets it, which is the right way to
# fail: the worst case is one burst getting through after a restart.

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
    """0 if this person may open another conversation now, otherwise the
    whole seconds to wait. Tapping a link is cheap for the tapper and costs
    the owner a row and a notification each time."""
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


async def relay_content(
    bot, message, to_chat_id,
    reply_to_message_id=None, reply_markup=None, header=None, italic=True,
):
    """Delivers `message`'s content into `to_chat_id`, preserving whatever it
    is (text, photo, video, voice, sticker, document, ...) with no "Forwarded
    from" tag -- copy_message handles every content type Telegram lets a bot
    copy, so there is no need to branch on message.photo / message.video /
    etc. here, the way convert_bot's file handling does.

    Plain text gets its own path (send_message, not copy_message) purely so
    `header` can be prepended into the SAME bubble -- copy_message has no way
    to alter a text message's body. A captioned media message keeps one
    bubble too: copy_message *can* replace a caption, so the header and the
    italicised caption go together underneath it. Only media with no caption
    of its own needs the header as a separate line above.

    `reply_to_message_id` is what makes the delivered message show up as a
    genuine Telegram reply on the receiving end. If that anchor message was
    since deleted, Telegram rejects the whole send -- so this retries once
    without it rather than losing the message entirely.

    Returns the list of Message/MessageId objects actually sent, in send
    order (normally one; two for uncaptioned media with a header).
    """

    def _compose(body: str | None) -> str:
        """Bot's own header upright, the person's own words in italics."""
        parts = []
        if header:
            parts.append(html.escape(header))
        if body:
            parts.append(italicize(body) if italic else html.escape(body))
        return "\n\n".join(parts)

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
            # The header goes on the first bubble only, and the buttons on the
            # last, so a message split in three still reads as one thing with
            # one Reply button under the end of it.
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
        # Too long to ride along under the picture. The words go above it as
        # their own bubbles and the media follows, carrying the buttons --
        # which is the same shape uncaptioned media already uses, and beats
        # either truncating what somebody wrote or refusing the whole thing.
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
        reply_to_message_id = None  # already visually anchored by the header line right above

    sent.append(await _copy(reply_to_message_id, reply_markup))
    return sent
