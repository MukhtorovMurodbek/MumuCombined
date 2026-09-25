"""A transcript of AnonBot conversations, and the page it becomes.

Until 1.7.0 this file was mostly a way of coping with a limitation: a bot
cannot read a chat's history, so a transcript had to be built from messages
the person forwarded back to the bot one selection at a time. It worked, and
it was a chore.

What it missed is that the bot already knows which message id in which chat
belonged to which conversation -- `anon_relay` has held exactly that since
v1.1, because a swipe-reply on an old message has to resolve to a thread. With
the ids in hand there are two honest ways to hand a conversation back, and
they differ in exactly one thing:

  * **Copy it.** `copyMessage` asks Telegram to place a copy of a message in
    a chat. The bot names an id and never sees what is in it, so a sticker, a
    voice message and a 40 MB video all arrive exactly as they were, and the
    bot has read nothing.
  * **Write it down.** To put words on a page the bot has to know the words,
    so each message is forwarded to the chat, read from what Telegram hands
    back, and deleted straight away -- one at a time, so at most one extra
    message is ever on screen.

The person is told which of those they are choosing, in those terms, before
either runs. `bot.py` has the Telegram half.

**The bot still keeps nothing anybody wrote.** A document is assembled in
memory, sent, and dropped; `tests/no_storage_scenarios.py` holds it to that.
And nothing here carries a name, a username or an id: the inbox holder is
"Owner" and the person writing to them is "Anon", whichever of the two is
doing the exporting.
"""
from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import datetime, timezone

# One export's ceiling, in messages. Generous for a conversation, bounded for
# a process: the document mode is two Telegram calls per message, and an
# unbounded export of a thread somebody has been using daily for a year would
# be a long time with the chat flickering.
MAX_MESSAGES = int(os.environ.get("EXPORT_MAX_MESSAGES", "500"))
MAX_CHARS = 2_000_000

# Who wrote a bubble, in the only two roles this bot has. Never a name, never
# an id -- the owner asked for exactly these two words: "the link owner should
# be addressed as owner and the anon messager should be addressed as anon".
OWNER, ANON = "owner", "anon"


def side_of(from_bot: bool, exporter_is_owner: bool) -> str:
    """Which side a relay row belongs to, from the one flag the row carries.

    `from_bot` is a property of the *chat the row is in*: true for a copy the
    bot delivered into it, false for what the person in that chat wrote. So
    the same flag means opposite people in the two chats, and who is asking
    decides which.
    """
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


# ---------------------------------------------------------------------------
# What a message is
# ---------------------------------------------------------------------------

# Checked in this order: Telegram also sets `document` on a GIF, and
# `location` on a venue.
_MEDIA = ("photo", "video", "animation", "video_note", "voice", "audio", "sticker",
          "document", "venue", "location", "contact", "poll", "dice")


def _duration(seconds) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""
    return f"{seconds // 60}:{seconds % 60:02d}"


def describe(message) -> tuple:
    """(kind, text, detail): the words a message carries, and what else it is.

    Nothing is downloaded -- a photo becomes the word for a photo. A shared
    contact or location is named and not copied out: a phone number or a
    place is exactly what a transcript should not quietly carry further than
    the chat it was sent in."""
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
    """One message of a conversation, as a line of the page.

    `describe` is what reads it, and what it reads is deliberately shallow:
    the words, the kind of thing it was, and a label. Nothing is downloaded,
    and a shared contact or location is named rather than copied out -- a
    phone number or a place is exactly what a transcript should not carry
    further than the chat it was sent in.
    """
    kind, text, detail = describe(message)
    return Item(message_id=message_id, side=side, sent_at=_utc(sent_at),
                kind=kind, text=text, detail=detail)


def strip_header(text: str, headers) -> "str | None":
    """A delivered bubble's words without the bot's header line above them,
    or None when the bubble was nothing but the header."""
    for header in headers:
        if not header:
            continue
        if text == header:
            return None
        if text.startswith(header + "\n\n"):
            return text[len(header) + 2:]
    return text


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

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
    """One self-contained HTML page: no script, nothing fetched from anywhere,
    readable offline in any browser and printable as it is.

    `sections` is [(heading, subheading, entries)]; an entry is
    {label, own, text, note, when}. Everything that came from a message is
    escaped, so nothing anybody wrote can become markup.

    `unplaced` is a section for messages that belong to no conversation. The
    export has none -- it works from the conversation index rather than from
    whatever somebody forwarded -- so it is left empty, and an empty one is
    not printed."""
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
