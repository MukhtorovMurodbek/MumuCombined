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

async def relay_content(
    bot, message, to_chat_id,
    reply_to_message_id=None, reply_markup=None, header=None, italic=True,
):
    """Delivers `message`'s content into `to_chat_id`, preserving whatever it is (text, photo, video, voice, sticker, document, ...) with no "Forwarded from" tag -- copy_message handles every content type Telegram lets a bot copy, so there is no need to branch on message.photo / message.video / etc."""

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

# ─── module: anon_bot.transcript ─────────────────────────────────────────────
"""A transcript of AnonBot conversations, and the page it becomes."""
from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import datetime, timezone

MAX_MESSAGES = int(os.environ.get("EXPORT_MAX_MESSAGES", "500"))
MAX_CHARS = 2_000_000

OWNER, ANON = "owner", "anon"

def side_of(from_bot: bool, exporter_is_owner: bool) -> str:
    """Which side a relay row belongs to, from the one flag the row carries."""
    if exporter_is_owner:
        return ANON if from_bot else OWNER
    return OWNER if from_bot else ANON

@dataclass
class Item:
    message_id: int
    side: str
    sent_at: "datetime | None"
    kind: str
    text: str = ""
    detail: str = ""

_MEDIA = ("photo", "video", "animation", "video_note", "voice", "audio", "sticker",
          "document", "venue", "location", "contact", "poll", "dice")

def _duration(seconds) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""
    return f"{seconds // 60}:{seconds % 60:02d}"

def describe(message) -> tuple:
    """(kind, text, detail): the words a message carries, and what else it is."""
    text = getattr(message, "text", None)
    if text is not None:
        return "text", text, ""
    kind, media = "other", None
    for name in _MEDIA:
        media = getattr(message, name, None)
        if media:
            kind = name
            break
    if kind == "venue":
        kind = "location"
    detail = ""
    if kind in ("video", "animation", "video_note", "voice", "audio"):
        detail = _duration(getattr(media, "duration", None))
    if kind == "audio":
        named = " – ".join(part for part in (getattr(media, "performer", None),
                                             getattr(media, "title", None)) if part)
        detail = ", ".join(part for part in (named, detail) if part)
    elif kind == "document":
        detail = getattr(media, "file_name", None) or ""
    elif kind == "sticker":
        detail = getattr(media, "emoji", None) or ""
    elif kind == "poll":
        detail = getattr(media, "question", None) or ""
    elif kind == "dice":
        detail = f"{getattr(media, 'emoji', '') or ''} {getattr(media, 'value', '') or ''}".strip()
    return kind, getattr(message, "caption", None) or "", detail

def _utc(when):
    if when is None:
        return None
    if when.tzinfo is None:
        return when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc)

def item_for(message, message_id: int, side: str, sent_at) -> Item:
    """One message of a conversation, as a line of the page."""
    kind, text, detail = describe(message)
    return Item(message_id=message_id, side=side, sent_at=_utc(sent_at),
                kind=kind, text=text, detail=detail)

def strip_header(text: str, headers) -> "str | None":
    """A delivered bubble's words without the bot's header line above them, or None when the bubble was nothing but the header."""
    for header in headers:
        if not header:
            continue
        if text == header:
            return None
        if text.startswith(header + "\n\n"):
            return text[len(header) + 2:]
    return text

_STYLE = """
:root { color-scheme: light dark; --bg: #fbfaf7; --fg: #1d1d1f; --muted: #6b6b70;
        --own: #dcebfc; --them: #efeee9; --line: #e2e0da; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161618; --fg: #ececef; --muted: #9a9aa2; --own: #1f3350; --them: #29292d; --line: #333338; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
       font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 28px 16px 48px; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 0; }
.meta { color: var(--muted); font-size: 13px; margin: 0 0 24px; }
h2 + .meta { margin: 2px 0 12px; }
section { margin: 0 0 36px; }
.day { color: var(--muted); font-size: 12px; text-align: center; margin: 18px 0 6px; }
.msg { display: flex; flex-direction: column; align-items: flex-start; margin: 6px 0; }
.msg.own { align-items: flex-end; }
.who { font-size: 12px; color: var(--muted); margin: 0 8px 2px; }
.bubble { max-width: 88%; background: var(--them); border-radius: 14px; padding: 8px 12px;
          white-space: pre-wrap; overflow-wrap: anywhere; }
.own .bubble { background: var(--own); }
.note { color: var(--muted); font-style: italic; }
footer { border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; padding-top: 12px; }
@media print { :root { --bg: #fff; --fg: #000; --own: #fff; --them: #fff; }
               .bubble { border: 1px solid #bbb; } }
"""

def _entry(entry) -> list:
    esc = html.escape
    when = entry.get("when")
    who = esc(entry["label"]) + (f" · {when:%H:%M}" if when else "")
    body = []
    if entry.get("note"):
        body.append(f'<span class="note">{esc(entry["note"])}</span>')
    if entry.get("text"):
        body.append(esc(entry["text"]))
    own = " own" if entry.get("own") else ""
    return [f'<div class="msg{own}"><div class="who">{who}</div>'
            f'<div class="bubble">{chr(10).join(body)}</div></div>']

def _entries(entries) -> list:
    out, day = [], None
    for entry in entries:
        when = entry.get("when")
        if when is not None and when.date() != day:
            day = when.date()
            out.append(f'<div class="day">{day:%Y-%m-%d}</div>')
        out += _entry(entry)
    return out

def render(*, title: str, generated: str, lang: str, sections, footer: str,
           unplaced_heading: str = "", unplaced_note: str = "", unplaced=()) -> bytes:
    """One self-contained HTML page: no script, nothing fetched from anywhere, readable offline in any browser and printable as it is."""
    esc = html.escape
    out = ["<!doctype html>", f'<html lang="{esc(lang)}">', "<head>", '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f"<title>{esc(title)}</title>", f"<style>{_STYLE}</style>", "</head>", "<body><main>",
           f"<h1>{esc(title)}</h1>", f'<p class="meta">{esc(generated)}</p>']
    for heading, subheading, entries in sections:
        out += ["<section>", f"<h2>{esc(heading)}</h2>", f'<p class="meta">{esc(subheading)}</p>']
        out += _entries(entries)
        out.append("</section>")
    if unplaced:
        out += ["<section>", f"<h2>{esc(unplaced_heading)}</h2>", f'<p class="meta">{esc(unplaced_note)}</p>']
        out += _entries(unplaced)
        out.append("</section>")
    out += [f"<footer>{esc(footer)}</footer>", "</main></body></html>"]
    return "\n".join(out).encode("utf-8")
