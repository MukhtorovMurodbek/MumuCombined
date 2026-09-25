"""
Standalone file converter bot -- images/video/audio, priced in Telegram Stars.

Split out of the original combined sticker+convert bot (see
ARCHITECTURE.md). This bot is its own process, its own folder and its own
deployment, with no file handoffs from its siblings -- so someone coming from
@StickerBot's "convert this" pointer just re-sends the file here directly
rather than it arriving pre-loaded. The five bots do share one Postgres
database, with a schema each; family_link.py is the only code that touches
anything outside this bot's own schema. What's new here past the original
combined bot is a shared /donate flow (Telegram Stars), merged into this
bot's existing precheckout/payment handlers alongside the "convert:" ones,
plus full English/Uzbek/Russian translation of every end-user-facing string.

Commands:
  /start           - greeting + menu
  /convert         - convert a file to another format
  /formats         - every format this bot reads and writes
  /mystars         - your own Stars spending history
  /stars           - (admin only) global Stars ledger
  /recharge        - top up ⚡ credit for conversions (/donate still works)
  /en, /uz, /rus   - switch language (English/Uzbek/Russian); also asked
                     once, trilingually, on first /start

Requires: python-telegram-bot[job-queue]>=21.3, Pillow>=10.0, ffmpeg on PATH.
          Everything past images and ffmpeg -- PDFs, e-books, Word documents,
          spreadsheets, HEIC -- is an optional dependency in requirements.txt,
          and formats.py stops offering a format whose library is missing
          rather than failing when somebody picks it.
Env vars: CBOT_TOKEN, CBOT_USERNAME (no @), CBOT_ADMIN_ID (optional,
          comma-separated, gates /stars, /dbdump, /messageas and /status),
          DATABASE_URL and DB_SCHEMA
          (the shared family database, and this bot's schema in it),
          SIBLING_BOTS (see shared_features.py), LOCAL_BOT_API_URL /
          LOCAL_BOT_API_MODE / CONVERT_MAX_FILE_MB (see convert_utils.py).
          Every performance/cost knob has a working default and is documented
          in .env.example.
"""
import asyncio
import logging
import math
import os
import re
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

try:  # optional convenience: load env vars from a local .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    TypeHandler,
    filters,
)

import family_link
import i18n
import lifecycle
from live_message import LiveMessage, edit_in_place
from db import (
    init_db,
    record_star_invoice,
    update_star_transaction,
    get_star_transaction,
    get_user_star_summary,
    get_star_ledger,
    dump_database_csv_zip,
    count_active_users_since,
    get_user_language,
    set_user_language,
)
import formats
import jobs
from convert_runner import ConvertRunner
from convert_utils import (
    convert,
    FREE_UNDER_MB,
    gif_is_animated,
    MAX_FILE_MB,
    price_for_size,
    price_for_job,
    document_pages,
    price_tiers_text,
    ConversionError as ConvertError,
)
from shared_features import (
    note_job,
    body,
    collapsed,
    heading,
    joined,
    lead_in,
    reply_formatted,
    publish_profile,
    publish_commands,
    refresh_chat_menu,
    ERASE_PREFIX,
    delete_my_data_chosen,
    delete_my_data_command,
    privacy_command,
    terms_command,
    paysupport_command,
    attach_problem_reports,
    add_problem_report_handlers,
    refuse_new_work,
    attach_flood_gate,
    attach_maintenance,
    CANCEL_PICK_ALL,
    CANCEL_PICK_NONE,
    CancelItem,
    ask_cancel_choice,
    cancel_choice_key,
    cancel_items,
    cancel_shared_item,
    finish_cancel_choice,
    keep_going,
    finish_cancel,
    flush_on_shutdown,
    language_keyboard,
    tune_runtime,
    sibling_bots_blurb,
    sibling_bots_keyboard_row,
    maybe_donation_nudge,
    balance_command,
    STARS_SANDBOX,
    donate_command,
    donate_amount_chosen,
    donate_fiat_amount_chosen,
    donate_custom_button_chosen,
    donate_custom_amount_received,
    donation_precheckout,
    donation_payment_received,
    setup_logging,
    error_handler,
    track_activity,
    build_status_text,
    format_ledger_amount,
)

setup_logging(__file__)
logger = logging.getLogger(__name__)

START_TIME = datetime.now(timezone.utc)

BOT_TOKEN = os.environ.get("CBOT_TOKEN")
BOT_USERNAME = os.environ.get("CBOT_USERNAME")  # no @
# Owner-only admin tools (/stars, /dbdump, /messageas, /status) -- comma-separated
# Telegram user ids. Empty/unset means disabled for everyone.
ADMIN_IDS = {int(x) for x in os.environ.get("CBOT_ADMIN_ID", "").split(",") if x.strip()}

LOCAL_BOT_API_URL = os.environ.get("LOCAL_BOT_API_URL")
LOCAL_BOT_API_MODE = os.environ.get("LOCAL_BOT_API_MODE", "true").lower() == "true"

BOT_NAME = "convertbot"  # this bot's id within SIBLING_BOTS

# Telegram's long-poll window -- see the note in main().
POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "30"))


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
async def _deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """How an owner-only command answers everybody else: exactly the way a
    misspelling does.

    The intent was always to avoid confirming the command exists, and a bare
    `return` looked like the way to do that. It is not: a bot that answers
    every command it has and ignores precisely one has just pointed at the
    interesting one, and to the person who typed it the bot simply looks
    broken. Giving back the same sentence a typo gets makes the owner-only
    commands indistinguishable from commands that were never there.
    """
    await unknown_command(update, context)



# ---------------------------------------------------------------------------
# Where an upload waits between "here is my file" and "convert it to X"
# ---------------------------------------------------------------------------
# It used to wait in context.user_data, i.e. in this process's memory, as a
# bytes object of up to MAX_FILE_MB. python-telegram-bot keeps user_data for
# the lifetime of the process, so anyone who uploaded a file and never picked
# a format left their whole file resident forever. With a local Bot API
# server raising the ceiling to 250 MB, a handful of abandoned uploads was
# the entire container.
#
# Now the upload goes to disk -- which on any host is both cheaper and more
# plentiful than RAM -- and user_data keeps only the path. A sweeper removes
# anything nobody came back for, including files orphaned by a restart.
UPLOAD_DIR = Path(os.environ.get("CONVERT_UPLOAD_DIR") or (Path(tempfile.gettempdir()) / "convertbot"))
PENDING_TTL_SECONDS = int(os.environ.get("CONVERT_PENDING_TTL_SECONDS", "900"))  # 15 min


# An extension reduced to something that is certainly one path component.
#
# Both extensions this file builds a path out of come from the other side of
# the wire: the upload's comes from `document.file_name`, which the sending
# client chooses, and the output's from callback data, which a modified
# client can put anything in. Neither is Telegram's to sanitise on our
# behalf, and `UPLOAD_DIR / f"...{ext}"` treats a "/" in `ext` as a directory
# separator and a ".." as a level up -- so a file_name of `a.b/../../../x`
# would have written the upload wherever the process could reach.
#
# Eight characters of ASCII alphanumerics covers every real extension
# ("jpeg", "webm", "tar" -- and this only ever sees the part after the last
# dot). Everything else becomes "", which the callers turn into a refusal or
# into "bin".
_EXT_RE = re.compile(r"[^a-z0-9]")


def _safe_ext(ext: str | None, limit: int = 8) -> str:
    return _EXT_RE.sub("", (ext or "").lower())[:limit]


def _new_upload_path(user_id: int, ext: str) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR / f"{user_id}-{uuid.uuid4().hex}.{_safe_ext(ext) or 'bin'}"


def _unlink(path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        logger.debug("Could not remove %s", path, exc_info=True)


def _discard_pending(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the conversion state and deletes whatever it was holding.

    A list rather than one path since v1.5.0: an album of pictures on its way
    to becoming a single PDF is one pending conversion holding several files,
    and abandoning it has to take all of them.
    """
    state = context.user_data.pop("convert", None)
    # A new upload abandons the pending menu, not the queue: with "keep file"
    # on, the same file can be waiting on the menu AND in a queued conversion,
    # and deleting it here would fail that conversion when it reached the
    # front.
    busy = jobs.active_paths()
    for path in (state or {}).get("paths", []):
        if str(path) not in busy:
            _unlink(path)


def _sweep_uploads(max_age_seconds: float = PENDING_TTL_SECONDS, keep=()) -> int:
    """Anything older than the TTL is gone: either the user never chose a
    format, or the process that was handling it died. Blocking (it stats a
    directory), so it runs through asyncio.to_thread.

    At startup it is called with max_age_seconds=0 to clear the directory
    outright: whatever is in there was staged by a process that no longer
    exists, and the user_data pointing at it went with that process."""
    if not UPLOAD_DIR.is_dir():
        return 0
    # A cutoff of "now" is not the same as "everything": a file written
    # milliseconds ago can carry an mtime at or past it, since filesystem
    # timestamp granularity is coarser than time.time(). Zero means all.
    sweep_all = max_age_seconds <= 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for path in UPLOAD_DIR.iterdir():
        try:
            if str(path) in keep:
                # A queued or running conversion's input. Its mtime is when it
                # was uploaded, which says nothing about whether it is still
                # needed -- a job at the back of a queue can be older than the
                # TTL and still be about to start.
                continue
            if path.is_file() and (sweep_all or path.stat().st_mtime < cutoff):
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


async def _sweep_uploads_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    removed = await asyncio.to_thread(
        _sweep_uploads, max_age_seconds=PENDING_TTL_SECONDS, keep=jobs.active_paths())
    if removed:
        logger.info("Swept %d abandoned upload(s).", removed)


def build_help_text(lang: str) -> str:
    return i18n.t(lang, "help_text", pricing=price_tiers_text(lang)) + sibling_bots_blurb(BOT_NAME, lang)


# Public command menu (the "/" button in Telegram's chat UI) -- set on
# startup via set_my_commands() below instead of pasting into @BotFather by
# hand. Owner-only admin commands (/stars, /dbdump, /status) are left off.
# Language-switch commands are described in the language they switch to
# (self-explanatory by script/language, since Telegram's command menu itself
# isn't per-user).
BOT_COMMANDS = [
    # Order is deliberate: what this is, how to change language, what the bot
    # does, how to stop it, help, money, then the policies. /language sits
    # second on the owner's instruction -- somebody reading a menu in the
    # wrong language needs the way out before anything else.
    #
    # /en, /uz and /rus are NOT here and still work. They are the way back for
    # somebody who cannot read the menu at all, so they must never stop
    # working -- but three lines for what /language already does is three
    # lines of noise for everybody who can read it.
    #
    # /mystars is gone from here and still works. It listed Stars paid for
    # conversions, which are not paid in Stars any more -- it has called
    # /balance since credit arrived, and one command showing the whole history
    # beats two showing halves of it.
    BotCommand("start", "What I do, and how to start"),
    BotCommand("language", "Choose your language / Tilni tanlash / Выбрать язык"),
    BotCommand("convert", "Convert a file — or just send me one"),
    BotCommand("formats", "Every format I read and write"),
    BotCommand("cancel", "Stop whatever I am waiting for"),
    BotCommand("help", "Everything I can do"),
    BotCommand("balance", "Your ⚡ credit, and where it went"),
    BotCommand("recharge", "Top up your ⚡ credit"),
    BotCommand("paysupport", "Trouble with a payment"),
    BotCommand("privacy", "What I keep about you"),
    BotCommand("terms", "What I may be used for"),
    BotCommand("deletemydata", "Delete everything I hold on you"),
]

# The same menu, in the owner's own chat, with the commands only they can
# run. Kept out of BOT_COMMANDS on purpose -- a stranger should not be offered
# /dbdump -- but hidden from the owner too, which was the accident. See
# publish_commands() in shared_features.py. English, like the rest of the
# admin output: the only person who sees this list wrote the bot.
ADMIN_COMMANDS = [
    BotCommand("status", "🔒 Uptime, host, errors, active users"),
    BotCommand("stars", "🔒 The Stars ledger: paid, free and refunded"),
    BotCommand("messageas", "🔒 messageas <user_id> <text> — DM as this bot"),
    BotCommand("dbdump", "🔒 This bot's tables as a zip of CSVs"),
]


def start_menu_keyboard() -> InlineKeyboardMarkup | None:
    rows = []
    sibling_row = sibling_bots_keyboard_row(BOT_NAME)
    if sibling_row:
        rows.append(sibling_row)
    return InlineKeyboardMarkup(rows) if rows else None


# ---------- /start ----------

async def _reply(update: Update, text: str, **kwargs):
    """Works whether the update came from a command or a button tap. A tap
    evolves the tapped message in place -- so choosing a language turns the
    picker itself into the instructions rather than leaving a stale picker
    sitting above them -- while a command has no earlier bot message to reuse
    and so always sends fresh.

    "In place" only while that message is still the last thing in the chat:
    once the user has said anything since, the answer is sent fresh rather
    than written above what they are looking at. See live_message.py."""
    if update.message:
        return await LiveMessage.reply_to(update.message, text, **kwargs)
    return await edit_in_place(update.callback_query.message, update.get_bot(), text, **kwargs)


async def _continue_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    await _reply(
        update,
        i18n.t(lang, "start_greeting") + build_help_text(lang),
        reply_markup=start_menu_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start prints the instructions -- except the very first one, which
    asks for a language first.

    v0.7.0 made every /start the language picker, which put a three-button
    detour in front of the one command every Telegram user types by reflex,
    for the sake of a choice that is made once. The 0.6.0 shape is back, and
    the picker has moved to a command of its own:

      * No language on record -- a brand-new user -- and /start does exactly
        what /language does: greet in all three languages and ask. Picking
        one prints the instructions (see _apply_language), so the first
        /start still ends where every later one begins. This is the only
        time /start asks.
      * A language on record, and /start prints the instructions in it.
        Anyone who wants the picker back asks for it by name: /language.
    """
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    if lang is None:
        await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
        return
    context.user_data["lang"] = lang
    await _continue_start(update, context, lang)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/language -- the picker on demand, which is what /start used to be.

    Same trilingual greeting and same three buttons, with a tick on the
    language in force so a returning user can see which one they are on
    before deciding to change it. The tap that follows runs through
    _apply_language exactly as /en, /uz and /rus do, so it ends where they
    end: at the instructions, in the language just chosen.
    """
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    # Keep the cached language warm even though the picker itself is
    # trilingual -- the next handler this user hits would otherwise pay for
    # a database read that /language had already done.
    if lang:
        context.user_data["lang"] = lang
    await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard(lang))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The instructions on their own. Every other bot in the family has had
    a /help since the beginning; this one only ever printed its help as part
    of /start, which stopped being a way to reach them once /start became
    the language picker."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(build_help_text(lang), reply_markup=start_menu_keyboard())


async def _apply_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """The single path every language change goes through -- /en, /uz, /rus
    and a tap on the picker alike -- so all four end the same way: with the
    instructions, printed in the language just chosen.

    A conversion already waiting on a format choice is deliberately left
    alone. Changing language is not cancelling anything, and the format
    buttons on that earlier message keep working."""
    await asyncio.to_thread(set_user_language, update.effective_user.id, lang)
    context.user_data["lang"] = lang
    # The menu follows the choice too -- Telegram otherwise shows it in the
    # language of the phone.
    await refresh_chat_menu(context, update.effective_user.id, lang)
    await _continue_start(update, context, lang)


async def _set_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    await update.message.reply_text(i18n.t(lang, "language_set_confirmation"))
    await _apply_language(update, context, lang)


async def set_language_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_language(update, context, "en")


async def set_language_uz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_language(update, context, "uz")


async def set_language_rus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_language(update, context, "ru")


async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on the picker -- same effect as /en, /uz or /rus."""
    query = update.callback_query
    lang = query.data.split(":", 1)[1]
    await query.answer(i18n.t(lang, "language_set_confirmation"))
    await _apply_language(update, context, lang)


# ---------- file converter (Telegram Stars) ----------

def _ext_of(filename: str | None, fallback: str) -> str:
    """The part after the last dot, normalised, or `fallback`.

    Sanitised, not trusted: see _safe_ext. A file_name whose tail is not a
    plausible extension is treated as having none at all, which is the
    honest answer -- the bot cannot tell what it was sent."""
    if filename and "." in filename:
        return formats.normalise(_safe_ext(filename.rsplit(".", 1)[-1])) or fallback
    return fallback


async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(
        i18n.t(lang, "convert_start_prompt", max_mb=MAX_FILE_MB, pricing=price_tiers_text(lang)),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(i18n.t(lang, "btn_what_formats"), callback_data="fmtall"),
        ]]),
    )


# ---------------------------------------------------------------------------
# /formats -- the answer to "what can this thing actually do"
# ---------------------------------------------------------------------------
# Where it is offered, and why there:
#
#   as a command       in the menu and in /help, for somebody deciding
#                      whether this bot is worth keeping.
#   as a button        under the refusal when a file's format is not one we
#                      take, and under /convert. That refusal is the single
#                      most valuable place for it: it is the one moment the
#                      user has demonstrated they want something converted
#                      and has just been told no.
#   as a bare word     "heic" typed into the chat is answered with what a
#                      HEIC becomes, rather than with a form letter. It costs
#                      one lookup in the catch-all handler that was already
#                      running.
#
# What it does NOT do is print eighty formats in one message. The first screen
# is six categories and six examples; a category is one tap.

def _formats_overview(lang: str) -> tuple[str, InlineKeyboardMarkup]:
    sources, targets, pairs = formats.counts()
    text = joined(
        heading(i18n.t(lang, "formats_title")),
        body(i18n.t(lang, "formats_intro", sources=sources, targets=targets, pairs=pairs)),
        collapsed(i18n.t(lang, "formats_highlights")),
    )
    available = [category for category in formats.CATEGORIES if formats.supported_sources(category)]
    buttons = [
        InlineKeyboardButton(i18n.t(lang, f"category_{category}").title(),
                             callback_data=f"fmtcat:{category}")
        for category in available
    ]
    rows = [buttons[index:index + 3] for index in range(0, len(buttons), 3)]
    return text, InlineKeyboardMarkup(rows)


def _formats_category(lang: str, category: str) -> tuple[str, InlineKeyboardMarkup]:
    label = i18n.t(lang, f"category_{category}")
    reads = ", ".join(ext.upper() for ext in formats.supported_sources(category))
    writes = ", ".join(ext.upper() for ext in formats.supported_targets(category))
    text = joined(
        heading(i18n.t(lang, "formats_category_title", category=label.title())),
        lead_in(f"{i18n.t(lang, 'formats_reads')}: {reads}"),
        lead_in(f"{i18n.t(lang, 'formats_writes')}: {writes}"),
    )
    back = InlineKeyboardMarkup([[
        InlineKeyboardButton(i18n.t(lang, "btn_formats_back"), callback_data="fmtall"),
    ]])
    return text, back


def _format_lookup(lang: str, word: str) -> str | None:
    """What one named format becomes, or None if that was not a format.

    None rather than a refusal, so the catch-all handler can fall through to
    its own answer for text that was never about a format at all.
    """
    ext = formats.find_format(word)
    if not ext:
        return None
    targets = formats.targets_for(ext)
    if not targets:
        return i18n.t(lang, "formats_lookup_none", ext=ext)
    return i18n.t(
        lang, "formats_lookup", ext=ext,
        category=i18n.t(lang, f"category_{formats.category_of(ext)}"),
        targets=", ".join(target.upper() for target in targets),
    )


async def formats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    if context.args:
        answer = _format_lookup(lang, " ".join(context.args))
        await reply_formatted(
            update.message,
            body(answer or i18n.t(lang, "formats_lookup_unknown",
                                  ext=_safe_ext(context.args[0].lstrip(".")) or "?")),
        )
        return
    text, keyboard = _formats_overview(lang)
    await reply_formatted(update.message, text, reply_markup=keyboard)


async def formats_overview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    await query.answer()
    text, keyboard = _formats_overview(lang)
    await edit_in_place(query.message, context.bot, text,
                        parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def formats_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    category = query.data.split(":", 1)[1]
    if category not in formats.CATEGORIES:
        await query.answer()
        return
    await query.answer()
    text, keyboard = _formats_category(lang, category)
    await edit_in_place(query.message, context.bot, text,
                        parse_mode=ParseMode.HTML, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------

async def _cancel_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> list[CancelItem]:
    """Everything this bot could be waiting on: an uploaded file still
    waiting for you to pick a format, and the shared donation prompt. Reads
    state only -- nothing is stopped until a button says which."""
    items = cancel_items(context, lang)
    # Each conversion in the queue is its own item, labelled with what
    # stopping it costs: nothing if it has not started, and the credit if it
    # has. The label is the warning.
    for job in jobs.jobs_for(update.effective_user.id):
        items.append(CancelItem(
            f"job_{job.id}",
            i18n.t(lang, "cancel_item_job_running" if job.state == "running" else "cancel_item_job_queued",
                   target=job.target_ext.upper(), src=job.src_ext.upper(),
                   size=f"{job.size / 1024 / 1024:.1f}"),
            i18n.t(lang, "cancel_button_job", target=job.target_ext.upper()),
        ))
    state = context.user_data.get("convert")
    if state:
        items.append(CancelItem(
            "conversion",
            i18n.t(lang, "cancel_item_conversion", ext=state.get("src_ext", "?")),
            i18n.t(lang, "cancel_button_conversion"),
        ))
    return items


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks which of the things it is waiting on to stop, then stops that
    one. The Cancel button under the format list stays as it is: there is
    only one thing it can possibly mean, so asking there would be noise."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if await ask_cancel_choice(update, context, await _cancel_items(update, context, lang), lang):
        return
    await finish_cancel(update, context, lang, [])


async def cancel_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of /cancel's buttons. Re-reads what is pending rather
    than trusting the menu: it may have been sitting on screen a while, and
    the file it offers to discard has a TTL."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    key = cancel_choice_key(update)
    await query.answer()
    if key == CANCEL_PICK_NONE:
        await keep_going(update, context, lang)
        return

    items = {item.key: item for item in await _cancel_items(update, context, lang)}
    keys = list(items) if key == CANCEL_PICK_ALL else [key]
    stopped = []
    for chosen in keys:
        item = items.get(chosen)
        if item is None:
            continue
        if chosen == "conversion":
            _discard_pending(context)
            stopped.append(item.label)
        elif chosen.startswith("job_"):
            if jobs.cancel(chosen[len("job_"):], user_id=update.effective_user.id):
                stopped.append(item.label)
        elif cancel_shared_item(context, lang, chosen):
            stopped.append(item.label)
    await finish_cancel_choice(update, context, lang, stopped)


async def cancel_conversion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The Cancel button under the format list -- the same thing /cancel does,
    without making anyone type it."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    _discard_pending(context)
    await query.answer()
    await edit_in_place(query.message, context.bot, i18n.t(lang, "cancelled"))


# ---------------------------------------------------------------------------
# a file arrives
# ---------------------------------------------------------------------------
# Telegram sends an album as N separate messages that share a media_group_id,
# a fraction of a second apart. Before v1.5.0 each one was handled on its own,
# so five photos produced five format menus of which only the last still had a
# file behind it -- every earlier one had been discarded by the next arrival.
#
# They are now collected instead. The first file of a group schedules a job
# BATCH_WAIT_SECONDS out; every further file of the same group cancels and
# re-schedules it, so the menu is drawn once, after the last one lands. That
# also makes "these pictures, one PDF" expressible, which is the conversion
# most people mean by "image to PDF" and which no amount of per-file handling
# can offer.
BATCH_WAIT_SECONDS = float(os.environ.get("CONVERT_BATCH_WAIT_SECONDS") or 2.0)


def _batch_job_name(chat_id: int, group_id: str) -> str:
    return f"batch:{chat_id}:{group_id}"


async def convert_receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    msg = update.message
    if msg.document:
        file_obj = msg.document
        ext = _ext_of(file_obj.file_name, "")
    elif msg.photo:
        file_obj = msg.photo[-1]
        ext = "jpg"
    elif msg.video:
        file_obj = msg.video
        ext = _ext_of(getattr(file_obj, "file_name", None), "mp4")
    elif msg.audio:
        file_obj = msg.audio
        ext = _ext_of(getattr(file_obj, "file_name", None), "mp3")
    elif msg.voice:
        file_obj = msg.voice
        ext = "ogg"
    elif msg.animation:
        file_obj = msg.animation
        ext = _ext_of(getattr(file_obj, "file_name", None), "gif")
    else:
        return

    if not ext:
        await msg.reply_text(
            i18n.t(lang, "unknown_extension"), reply_markup=_what_formats_keyboard(lang),
        )
        return

    declared_size = file_obj.file_size or 0
    if declared_size and declared_size > MAX_FILE_MB * 1024 * 1024:
        await msg.reply_text(i18n.t(lang, "file_too_large_download", max_mb=MAX_FILE_MB))
        return

    # Room on disk, checked against the size Telegram declares, before a byte
    # is written. With files kept for more conversions and several queued at
    # once, "the disk filled up half-way through a download" stopped being
    # hypothetical.
    problem = await asyncio.to_thread(
        jobs.storage_problem, update.effective_user.id, declared_size, UPLOAD_DIR)
    if problem is not None:
        which, used, limit = problem
        key = "storage_full_user" if which == "user" else "storage_full_global"
        await msg.reply_text(i18n.t(lang, key, used=used, limit=limit))
        return

    group_id = msg.media_group_id
    state = context.user_data.get("convert")
    joining = bool(
        group_id and state and state.get("group_id") == group_id
        and state.get("state") == "awaiting_format"
    )
    if not joining:
        # Whatever was waiting from a previous upload is dead the moment a new
        # file arrives -- delete it now rather than leaving it for the sweeper.
        _discard_pending(context)
    elif formats.normalise(state["src_ext"]) != ext:
        # An album of a photo and a video is two conversions, not one.
        await msg.reply_text(i18n.t(lang, "batch_mixed_formats"))
        return
    elif len(state["paths"]) >= formats.MAX_BATCH:
        return

    status = None
    if not joining:
        status = await LiveMessage.reply_to(msg, i18n.t(lang, "downloading"))
    path = _new_upload_path(update.effective_user.id, ext)
    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        # download_to_drive streams to the file; download_as_bytearray built
        # the whole thing in memory first.
        await tg_file.download_to_drive(custom_path=path)
    except Exception as exc:
        _unlink(path)
        if status is not None:
            await status.set(context.bot, i18n.t(lang, "download_failed", error=exc))
        else:
            await msg.reply_text(i18n.t(lang, "download_failed", error=exc))
        return
    if status is not None:
        await status.delete(context.bot)

    if joining:
        state["paths"].append(str(path))
        state["size"] += path.stat().st_size
        _schedule_batch(context, msg, update.effective_user, group_id)
        return

    if group_id and context.job_queue is not None:
        # Stage it, then wait: the rest of the album is milliseconds behind.
        context.user_data["convert"] = {
            "state": "awaiting_format",
            "paths": [str(path)],
            "src_ext": ext,
            "size": path.stat().st_size,
            "group_id": group_id,
        }
        _schedule_batch(context, msg, update.effective_user, group_id)
        return

    await _present_conversion_options(msg, context, update.effective_user, [path], ext)


def _schedule_batch(context: ContextTypes.DEFAULT_TYPE, message, user, group_id: str) -> None:
    """(Re)arm the job that draws the menu once the album has stopped arriving."""
    if context.job_queue is None:
        return
    name = _batch_job_name(message.chat_id, group_id)
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    context.job_queue.run_once(
        _present_batch_job, BATCH_WAIT_SECONDS, name=name,
        chat_id=message.chat_id, user_id=user.id,
        data={"message": message, "user": user, "group_id": group_id},
    )


async def _present_batch_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """The album stopped arriving; draw one menu for all of it."""
    data = context.job.data
    state = context.user_data.get("convert")
    if not state or state.get("group_id") != data["group_id"]:
        return
    paths = [Path(path) for path in state["paths"]]
    # user_data is rebuilt by _present_conversion_options, which is the one
    # place that decides what a pending conversion looks like.
    context.user_data.pop("convert", None)
    await _present_conversion_options(
        data["message"], context, data["user"], paths, state["src_ext"],
        group_id=data["group_id"],
    )


def _what_formats_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(i18n.t(lang, "btn_what_formats"), callback_data="fmtall"),
    ]])


def _format_rows(lang: str, targets: list[str], expanded: bool, total: int,
                 keep: bool | None = None) -> list[list]:
    """Three formats to a row, then whatever navigation the list needs.

    A long list is cut to POPULAR_COUNT with a "More formats" button under it
    rather than shown whole: an image now has fourteen targets, and fourteen
    buttons is a menu somebody has to read instead of a menu somebody can use.
    """
    buttons = [InlineKeyboardButton(target.upper(), callback_data=f"convfmt:{target}")
               for target in targets]
    rows = [buttons[index:index + 3] for index in range(0, len(buttons), 3)]
    if total > len(targets):
        rows.append([InlineKeyboardButton(i18n.t(lang, "btn_more_formats"), callback_data="convmore")])
    elif expanded:
        rows.append([InlineKeyboardButton(i18n.t(lang, "btn_fewer_formats"), callback_data="convless")])
    if keep is not None:
        # The consent to hold a file past its first conversion, asked where
        # it matters and remembered. Off unless somebody turns it on: the
        # default is the promise PRIVACY.md makes, that a file is deleted as
        # soon as it has been converted.
        rows.append([InlineKeyboardButton(
            i18n.t(lang, "keep_toggle_on" if keep else "keep_toggle_off"), callback_data="convkeep")])
    rows.append([InlineKeyboardButton(i18n.t(lang, "btn_cancel_conversion"), callback_data="convcancel")])
    return rows


def human_size(size_bytes: float) -> str:
    """A size somebody can read. "12288 KB" is a number to work out; "12 MB"
    is a size."""
    if size_bytes >= 1024 * 1024:
        megabytes = size_bytes / 1024 / 1024
        return f"{megabytes:.1f} MB" if megabytes < 10 else f"{megabytes:.0f} MB"
    return f"{max(1, round(size_bytes / 1024))} KB"


def _options_text(lang: str, paths, src_ext: str, size: int,
                  animated: bool | None = None, notes=()) -> str:
    """The format menu. It does not quote a price, because until a format is
    chosen there is no price to quote.

    It used to open with one, taken from the size of the upload, and that
    number was wrong in both directions for the same file: a 78 KB .docx
    became a 1.6 MB PDF and was billed as 78 KB, while a 12 MB video billed
    at 12 MB whether it was being turned into a 1 MB MP3 or a 70 MB GIF. The
    quote now happens where the answer exists -- see _quote_text.
    """
    if len(paths) > 1:
        text = i18n.t(lang, "convert_options_prompt_batch", count=len(paths),
                      size=human_size(size), price_line=i18n.t(lang, "price_after_format"))
    else:
        text = i18n.t(lang, "convert_options_prompt", size=human_size(size),
                      category=i18n.t(lang, f"category_{formats.category_of(src_ext, animated)}"),
                      price_line=i18n.t(lang, "price_after_format"))
    for note in notes:
        text += "\n\n" + note
    return text


def _quote_text(lang: str, src_ext: str, target_ext: str, in_bytes: int,
                out_bytes: int, price: int, balance: int | None) -> str:
    """What this conversion will cost, and what it is costing for.

    Both sizes are on it because both are in the price, and the estimate is
    called an estimate. The line that matters most is the one after it: the
    number quoted is the number charged. An estimate somebody is asked to
    agree to, which can then be revised upwards once they have agreed, is not
    a quote -- it is a deposit, and nobody signed up for one.
    """
    lines = [f"{src_ext.upper()} → {target_ext.upper()}",
             i18n.t(lang, "quote_line_sizes", in_size=human_size(in_bytes),
                    out_size=human_size(out_bytes))]
    if price == 0:
        lines.append(i18n.t(lang, "quote_free", mb=FREE_UNDER_MB))
        return "\n".join(lines)
    lines.append(i18n.t(lang, "quote_cost", price=price))
    lines.append("")
    lines.append(i18n.t(lang, "quote_fixed"))
    if balance is not None:
        lines.append(i18n.t(lang, "quote_balance", balance=max(balance, 0)))
    # Said where the money decision is made, which since 1.7.0 is here rather
    # than on the format menu: taken when the conversion starts, kept if you
    # stop it, returned if the bot fails, and never turned back into Stars.
    lines.append("")
    lines.append(i18n.t(lang, "credit_policy_note"))
    # A converted file can come out over what a bot may send, and whoever is
    # paying should know before they pay that the ⚡ comes back if it does.
    lines.append("")
    lines.append(i18n.t(lang, "send_limit_note", mb=jobs.SEND_LIMIT_MB))
    return "\n".join(lines)


def _quote_keyboard(lang: str, price: int) -> InlineKeyboardMarkup:
    label = (i18n.t(lang, "btn_quote_free") if price == 0
             else i18n.t(lang, "btn_quote_go", price=price))
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="convgo")],
        [InlineKeyboardButton(i18n.t(lang, "btn_quote_back"), callback_data="convback")],
        [InlineKeyboardButton(i18n.t(lang, "btn_cancel_conversion"), callback_data="convcancel")],
    ])


def _offered_targets(state: dict) -> list[str]:
    """What the menu offers for a pending conversion, computed one way for
    every redraw: the menu, More/Less, and the keep toggle."""
    targets = formats.targets_for(state["src_ext"], state.get("animated"))
    if len(state["paths"]) > 1:
        targets = [target for target in targets if target != state["src_ext"]]
    blocked = set(state.get("blocked") or ())
    return [target for target in targets if target not in blocked]


async def _present_conversion_options(
    message, context: ContextTypes.DEFAULT_TYPE, user, paths, src_ext: str,
    group_id: str | None = None,
):
    lang = await i18n.get_lang(user.id, context)
    src_ext = formats.normalise(src_ext)
    # A one-frame GIF is a picture and should be offered PDF and ICO; an
    # animated WEBP is a video and must not be offered a target that would
    # throw its frames away. The extension cannot tell them apart, so the
    # file is asked, once, and the answer travels with the pending conversion.
    animated = gif_is_animated(paths[0]) if src_ext in formats.ANIMATED_CAPABLE else None
    if not formats.is_supported_source(src_ext):
        for path in paths:
            _unlink(path)
        await message.reply_text(
            i18n.t(lang, "unsupported_format", ext=src_ext),
            reply_markup=_what_formats_keyboard(lang),
        )
        return

    size = sum(Path(path).stat().st_size for path in paths)
    # Still the upload's own size that decides whether the file is takeable at
    # all: that ceiling is Telegram's, and belongs to what arrived rather than
    # to an estimate of what would come out.
    price = price_for_size(size)
    if price is None:
        for path in paths:
            _unlink(path)
        await message.reply_text(
            i18n.t(lang, "file_too_large_convert", size=f"{size / 1024 / 1024:.1f}", max_mb=MAX_FILE_MB)
        )
        return

    # A picture's pixel count decides two things before anybody pays: whether
    # it can be converted at all, and which formats would come out too big
    # for a bot to send back. Read from the header, not decoded.
    megapixels = None
    if len(paths) == 1 and formats.category_of(src_ext, animated) == formats.IMAGE:
        megapixels = await asyncio.to_thread(jobs.image_megapixels, paths[0])
        if megapixels is not None and megapixels > jobs.MAX_MEGAPIXELS:
            for path in paths:
                _unlink(path)
            await message.reply_text(i18n.t(lang, "too_many_megapixels",
                                            mp=f"{megapixels:.0f}", max=jobs.MAX_MEGAPIXELS))
            return

    # How many pages a document has, read from its index rather than by
    # rendering it. It is what stops a 900 KB PDF of four hundred pages being
    # quoted as though four hundred PNGs would weigh 900 KB.
    pages = None
    if len(paths) == 1 and formats.category_of(src_ext, animated) == formats.DOCUMENT:
        pages = await asyncio.to_thread(document_pages, paths[0], src_ext)

    state = {
        "state": "awaiting_format",
        "paths": [str(path) for path in paths],
        "src_ext": src_ext,
        "size": size,
        "price": 0,
        "group_id": group_id,
        "animated": animated,
        "megapixels": megapixels,
        "pages": pages,
    }
    every_target = _offered_targets(state)
    blocked = jobs.unsendable_targets(megapixels, every_target)
    state["blocked"] = blocked
    notes = []
    if blocked:
        notes.append(i18n.t(lang, "too_big_to_send_note",
                            formats=", ".join(target.upper() for target in blocked),
                            mp=f"{megapixels:.0f}", limit=jobs.SEND_LIMIT_MB))
    state["notes"] = notes

    targets = _offered_targets(state)
    if not targets:
        for path in paths:
            _unlink(path)
        key = "nothing_sendable" if blocked else "no_target_formats"
        await message.reply_text(i18n.t(lang, key, limit=jobs.SEND_LIMIT_MB))
        return

    context.user_data["convert"] = state
    keep = bool(context.user_data.get("keep_files"))
    shown = formats.popular_targets(src_ext, animated)
    shown = [target for target in shown if target in targets] or targets
    await message.reply_text(
        _options_text(lang, paths, src_ext, size, animated, notes),
        reply_markup=InlineKeyboardMarkup(_format_rows(lang, shown, False, len(targets), keep=keep)),
    )


async def convert_keep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The keep-file toggle under the format menu.

    Asks permission rather than assuming it. Converting one file to several
    formats means holding the file between conversions, and the privacy
    notice promises a file is deleted once it has been converted -- so
    holding it longer is something a person turns on, for themselves, and
    can see is on. The choice is remembered for their next file too."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    keep = not bool(context.user_data.get("keep_files"))
    context.user_data["keep_files"] = keep
    await query.answer(i18n.t(lang, "keep_explained_on" if keep else "keep_explained_off",
                              minutes=max(1, PENDING_TTL_SECONDS // 60)), show_alert=keep)
    state = context.user_data.get("convert")
    if not state or state.get("state") != "awaiting_format":
        return
    if keep:
        _touch(state["paths"])
    targets = _offered_targets(state)
    shown = [target for target in formats.popular_targets(state["src_ext"], state.get("animated"))
             if target in targets] or targets
    await edit_in_place(
        query.message, context.bot,
        _options_text(lang, state["paths"], state["src_ext"], state["size"],
                      state.get("animated"), state.get("notes") or ()),
        reply_markup=InlineKeyboardMarkup(_format_rows(lang, shown, False, len(targets), keep=keep)),
    )


async def convert_show_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The same message, redrawn with every target on it -- or back to the
    short list. The menu is one message that changes, not a second one."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    state = context.user_data.get("convert")
    if not state or state.get("state") != "awaiting_format":
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return
    await query.answer()
    src_ext = state["src_ext"]
    animated = state.get("animated")
    targets = _offered_targets(state)
    expanded = query.data == "convmore"
    shown = targets if expanded else [
        target for target in formats.popular_targets(src_ext, animated) if target in targets
    ] or targets
    await edit_in_place(
        query.message, context.bot,
        _options_text(lang, state["paths"], src_ext, state["size"], animated,
                      state.get("notes") or ()),
        reply_markup=InlineKeyboardMarkup(_format_rows(
            lang, shown, expanded, len(targets), keep=bool(context.user_data.get("keep_files")))),
    )


def _result_caption(lang: str, result, src_ext: str, target_ext: str, stars_paid: int) -> str:
    """Say what actually came back.

    Three of these are new in v1.5.0 and all three exist because the button
    said one thing and the file is another: a zip instead of forty PNGs, a
    PDF holding six pictures, a Word document whose layout was rebuilt rather
    than copied. A caption that ignored any of them would be a small lie in
    the one message the user actually keeps.
    """
    if result.zipped and target_ext != "zip":
        key = "converted_file_caption_pages" if formats.category_of(src_ext) == formats.DOCUMENT \
            else "converted_file_caption_zip"
        caption = i18n.t(lang, key, items=result.items)
    elif result.items > 1 and target_ext == "pdf":
        caption = i18n.t(lang, "converted_file_caption_pdf", items=result.items)
    else:
        caption = i18n.t(lang, "converted_file_caption" if stars_paid else "converted_file_caption_free")
    if src_ext in ("docx", "md", "html", "txt") and target_ext == "pdf":
        caption += "\n\n" + i18n.t(lang, "converted_layout_note")
    if target_ext == "docx":
        # What a PDF is made of is marks on a page, so the thing that comes
        # back is the document's words rather than its pages. Said here, on
        # the file itself, because that is the message somebody keeps.
        caption += "\n\n" + i18n.t(lang, "converted_docx_note")
    return caption


_RUNNER = None


def _runner(application) -> ConvertRunner:
    """One runner per application. Built lazily because the application does
    not exist when this module is imported."""
    global _RUNNER
    if _RUNNER is None or _RUNNER.application is not application:
        _RUNNER = ConvertRunner(application, ADMIN_IDS, UPLOAD_DIR, _result_caption)
    return _RUNNER


def _touch(paths) -> None:
    """Restart a kept file's 15 minutes: the sweeper goes by modification
    time, and a file somebody is still converting is not abandoned."""
    now = time.time()
    for path in paths:
        try:
            os.utime(path, (now, now))
        except OSError:
            pass


async def _enqueue(context: ContextTypes.DEFAULT_TYPE, message, user, lang: str,
                   conv_state: dict, target_ext: str, edit_menu: bool = True) -> None:
    """Hand a chosen conversion to the queue and return straight away.

    The handler that calls this used to run the whole conversion before it
    returned, and every bot here handles updates one at a time -- so one
    large conversion froze the bot for everybody. Now the button is answered
    in milliseconds and the work happens in jobs.py.

    With "keep file" on, the menu message stays exactly as it is, so the
    same file can be sent to another format with one more tap, and the
    status goes in a message of its own. With it off, the menu becomes the
    status and the file belongs to the job from here on.
    """
    keep = bool(context.user_data.get("keep_files"))
    paths = list(conv_state["paths"])
    job = jobs.Job(
        user_id=user.id, chat_id=message.chat_id, paths=paths,
        src_ext=conv_state["src_ext"], target_ext=target_ext,
        size=conv_state["size"], price=conv_state["price"], lang=lang,
        username=user.username, keep_file=keep,
    )
    ahead = sum(1 for other in jobs._jobs.values() if other.state in ("queued", "running"))
    if ahead:
        text = i18n.t(lang, "job_queued", src=job.src_ext.upper(), target=target_ext.upper(),
                      ahead=ahead, price=job.price)
    else:
        text = i18n.t(lang, "job_starting", src=job.src_ext.upper(), target=target_ext.upper())
    runner = _runner(context.application)

    if keep:
        conv_state["state"] = "awaiting_format"
        conv_state.pop("payload", None)
        conv_state.pop("target_ext", None)
        _touch(paths)
        status = await message.reply_text(text, reply_markup=runner.stop_keyboard(job))
    else:
        context.user_data.pop("convert", None)
        if edit_menu:
            await edit_in_place(message, context.bot, text, reply_markup=runner.stop_keyboard(job))
            status = message
        else:
            status = await message.reply_text(text, reply_markup=runner.stop_keyboard(job))
    job.extra["status_message"] = status
    jobs.submit(context.application, job, runner)


async def convert_stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The Stop button under a conversion's status.

    A running conversion stopped this way is not refunded -- the button says
    so on its face, and the status the person was watching said so when it
    started. A queued one costs nothing, because credit is only taken when a
    conversion starts. Either way the runner writes the ending into the
    status, so this only has to ask."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    job_id = query.data.split(":", 1)[1] if ":" in (query.data or "") else ""
    job = jobs.cancel(job_id, user_id=update.effective_user.id)
    if job is None:
        await query.answer(i18n.t(lang, "job_not_running"))
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not take a stale Stop button down", exc_info=True)
        return
    await query.answer()


async def convert_format_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_ext = _safe_ext(query.data.split(":", 1)[1])
    lang = await i18n.get_lang(update.effective_user.id, context)
    conv_state = context.user_data.get("convert")
    if not conv_state or conv_state.get("state") != "awaiting_format":
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return

    # Callback data is whatever the client sends back, not necessarily what
    # was put on a button -- so the format is checked against the same list
    # the buttons were built from rather than taken on trust. Without this,
    # a format nobody was offered reached _new_upload_path and ffmpeg.
    # targets_for() rather than the declared table: a format this host cannot
    # actually produce must be refused here too, not only left off the menu.
    if target_ext not in formats.targets_for(conv_state["src_ext"], conv_state.get("animated")):
        await query.answer(i18n.t(lang, "unsupported_format", ext=target_ext), show_alert=True)
        return
    if target_ext in (conv_state.get("blocked") or ()):
        await query.answer(i18n.t(lang, "too_big_to_send_alert", limit=jobs.SEND_LIMIT_MB),
                           show_alert=True)
        return

    in_paths = conv_state["paths"]
    src_ext = conv_state["src_ext"]
    user = update.effective_user

    if not all(os.path.exists(path) for path in in_paths):
        _discard_pending(context)
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return

    # The price, at last: both sizes and how hard the pair is to run.
    price, est_out = price_for_job(src_ext, target_ext, conv_state["size"],
                                   conv_state.get("pages"))
    conv_state["price"] = price
    conv_state["est_out"] = est_out
    conv_state["target_ext"] = target_ext

    # A free conversion is not a decision anybody needs to confirm -- there is
    # nothing to agree to -- so it starts on the tap that chose the format,
    # exactly as it did before. A paid one stops here and asks.
    if price == 0:
        await query.answer()
        await _start_chosen(update, context, conv_state, target_ext, lang)
        return

    balance = await asyncio.to_thread(family_link.star_balance, user.id)
    await query.answer()
    await edit_in_place(
        query.message, context.bot,
        _quote_text(lang, src_ext, target_ext, conv_state["size"], est_out, price, balance),
        reply_markup=_quote_keyboard(lang, price))


async def convert_quote_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Another format" on a quote: back to the menu, nothing charged."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    state = context.user_data.get("convert")
    if not state or state.get("state") != "awaiting_format":
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return
    await query.answer()
    state.pop("target_ext", None)
    targets = _offered_targets(state)
    shown = [target for target in formats.popular_targets(state["src_ext"], state.get("animated"))
             if target in targets] or targets
    await edit_in_place(
        query.message, context.bot,
        _options_text(lang, state["paths"], state["src_ext"], state["size"],
                      state.get("animated"), state.get("notes") or ()),
        reply_markup=InlineKeyboardMarkup(_format_rows(
            lang, shown, False, len(targets), keep=bool(context.user_data.get("keep_files")))),
    )


async def convert_quote_go(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The tap that agrees to the quoted price."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    state = context.user_data.get("convert")
    target_ext = (state or {}).get("target_ext")
    if not state or state.get("state") != "awaiting_format" or not target_ext:
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return
    if not all(os.path.exists(path) for path in state["paths"]):
        _discard_pending(context)
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return
    await query.answer()
    await _start_chosen(update, context, state, target_ext, lang)


async def _start_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        conv_state: dict, target_ext: str, lang: str) -> None:
    """Everything between "yes, that one, at that price" and the job being on
    the queue: the refusals, the balance, the invoice if there is not enough.

    Reached from two places -- a free conversion, where choosing the format is
    the whole decision, and the Convert button on a quote."""
    query = update.callback_query
    price = conv_state["price"]
    src_ext = conv_state["src_ext"]
    user = update.effective_user

    # Refused before anything is queued or charged: an announced update is
    # the owner asking for quiet, and a job queued now would be interrupted.
    refusal = await refuse_new_work(lang, user.id, query.message.chat_id)
    if refusal:
        await query.answer(refusal, show_alert=True)
        return

    if len(jobs.jobs_for(user.id)) >= jobs.MAX_QUEUED_PER_USER:
        await query.answer(i18n.t(lang, "queue_full", count=jobs.MAX_QUEUED_PER_USER),
                           show_alert=True)
        return

    # Credit is taken when each conversion STARTS, so what matters now is
    # whether the balance covers this one and everything already queued
    # ahead of it -- otherwise the last job in a queue would reach the front
    # and find nothing to pay with.
    needed = price + jobs.uncharged_total(user.id)
    balance = await asyncio.to_thread(family_link.star_balance, user.id) if needed else 0
    if needed and balance < needed:
        shortfall = needed - max(balance, 0)
        stars = math.ceil(shortfall / max(family_link.TOPUP_MULTIPLIER, 0.01))
        credited = (await asyncio.to_thread(family_link.quote_topup, user.id, stars))["total"]
        if STARS_SANDBOX:
            # Nothing is charged, and the ordinary queue then runs for real.
            await asyncio.to_thread(family_link.topup, user.id, stars,
                                    "sandbox top-up for a conversion")
        else:
            payload = f"convert:{uuid.uuid4().hex}"
            conv_state["target_ext"] = target_ext
            conv_state["payload"] = payload
            conv_state["state"] = "awaiting_payment"
            await asyncio.to_thread(
                record_star_invoice, user.id, user.username, stars,
                f"top-up for a {src_ext}->{target_ext} conversion", payload)
            await context.bot.send_invoice(
                chat_id=query.message.chat_id,
                title=i18n.t(lang, "convert_invoice_title", src=src_ext.upper(), target=target_ext.upper()),
                description=i18n.t(lang, "convert_invoice_description", size_kb=f"{conv_state['size'] / 1024:.0f}"),
                payload=payload,
                provider_token="",  # empty string is required for Telegram Stars payments
                currency="XTR",
                prices=[LabeledPrice(i18n.t(lang, "convert_invoice_label", src=src_ext, target=target_ext), stars)],
            )
            await edit_in_place(query.message, context.bot,
                                i18n.t(lang, "topup_needed", price=needed, balance=max(balance, 0),
                                       stars=stars, credited=credited))
            return

    await _enqueue(context, query.message, user, lang, conv_state, target_ext)


# ---------- Stars payment plumbing -- handles BOTH "convert:" and "donate:" ----------
# Only one PreCheckoutQueryHandler / SUCCESSFUL_PAYMENT handler should be
# registered per bot (see shared_features.py's big comment on this), so this
# bot's versions branch on the payload prefix instead of stacking handlers.

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("convert:"):
        await query.answer(ok=True)
        return
    if query.invoice_payload.startswith("donate:"):
        await donation_precheckout(query)
        return
    lang = await i18n.get_lang(update.effective_user.id, context)
    await query.answer(ok=False, error_message=i18n.t(lang, "unknown_order"))


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sp = update.message.successful_payment
    payload = sp.invoice_payload

    if payload.startswith("donate:"):
        await donation_payment_received(update, context)
        return

    lang = await i18n.get_lang(update.effective_user.id, context)
    charge_id = sp.telegram_payment_charge_id
    user = update.effective_user
    conv_state = context.user_data.get("convert") or {}

    await asyncio.to_thread(update_star_transaction, payload, "paid", charge_id)
    # The Stars are credit whatever happens next. This branch used to refund a
    # payment whose staged file had gone -- and looked for that file under
    # conv_state["path"], a key that became "paths" when albums arrived in
    # v1.5.0. It could never find it, so every invoice-paid conversion since
    # then was refunded and never converted. Keeping the payment as credit is
    # both the fix and the better answer: nothing is lost and nobody waits on
    # a refund.
    result = await asyncio.to_thread(
        family_link.topup, user.id, sp.total_amount, "top-up for a conversion")
    paths = conv_state.get("paths") or []
    if (conv_state.get("payload") != payload or not paths
            or not all(os.path.exists(path) for path in paths)):
        await update.message.reply_text(i18n.t(
            lang, "payment_kept_as_credit",
            credited=result["credited"] + result["bonus"], balance=result["balance"]))
        return
    await _enqueue(context, update.message, user, lang, conv_state,
                   conv_state.get("target_ext"), edit_menu=False)


async def mystars_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mystars, kept working for everybody who learned it.

    It listed the Telegram Stars paid for conversions, and a conversion is not
    paid in Stars any more: it is paid in credit, and every movement of that
    credit is in the family ledger that /balance reads. Two commands showing
    two halves of one history would be worse than one showing all of it."""
    await balance_command(update, context)


# ---------- admin-only (English only, not part of this i18n rollout) ----------

async def stars_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    await update.message.reply_text(await _stars_text())


async def _bus_stars(context, args):
    """The Stars ledger, asked for from ManagerBot (`/stars convert`).

    ManagerBot's own `/donations` reads every bot's `star_transactions` out of
    the shared database and totals them. This is the other half of that
    picture: ConvertBot is the only bot in the family that charges for
    anything, so it is the only one whose ledger holds paid, free and
    refunded *conversions* rather than donations alone, and this is the view
    that shows them.
    """
    return await _stars_text(), None, None


async def _stars_text() -> str:
    summary, recent = await asyncio.to_thread(get_star_ledger, 15)
    lines = [
        f"Paid: {summary['paid_total']} ⭐ across {summary['paid_count']} order(s) from {summary['paying_users']} user(s) (Stars only)",
        f"Refunded: {summary['refunded_total']} ⭐ across {summary['refunded_count']} order(s) (Stars only)",
        f"Free conversions: {summary['free_count']}",
        "",
        "Recent transactions (any currency):",
    ]
    for t in recent:
        who = f"@{t['username']}" if t["username"] else str(t["user_id"])
        amount = format_ledger_amount(t["amount_stars"], t["currency"])
        lines.append(f"  {t['created_at'][:16]} {who} {amount} {t['item']} [{t['status']}]")
    return "\n".join(lines)


async def dbdump_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dbdump -- exports every table in this bot's own database as one
    zip of CSVs. Owner-only (reuses the same ADMIN_IDS as /stars)."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    status = await LiveMessage.reply_to(update.message, "Exporting the database...")
    try:
        data = await asyncio.to_thread(dump_database_csv_zip)
    except Exception as exc:
        await status.set(context.bot, f"⚠️ Export failed: {exc}")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    await update.message.reply_document(document=BytesIO(data), filename=f"convertbot_db_{stamp}.zip")
    await status.delete(context.bot)


async def messageas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/messageas <user_id> <text> -- sends a message to that user as this
    bot. Only works if the user has messaged the bot before (Telegram
    doesn't let bots cold-message anyone). Owner-only (reuses the same
    ADMIN_IDS as /stars, /dbdump, and /status)."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)

    if len(context.args) < 2 or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /messageas <user_id> <message text>")
        return

    user_id = int(context.args[0])
    text = " ".join(context.args[1:])
    try:
        await context.bot.send_message(chat_id=user_id, text=text)
        await update.message.reply_text("✅ Sent.")
    except Exception as exc:
        await update.message.reply_text(f"⚠️ Couldn't send it: {exc}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status -- uptime, hosting environment, any crashes since this
    process started, and active-user counts. Owner-only (reuses the same
    ADMIN_IDS as /stars and /dbdump)."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    now = datetime.now(timezone.utc)
    users_hour = await asyncio.to_thread(count_active_users_since, now - timedelta(hours=1))
    users_since_start = await asyncio.to_thread(count_active_users_since, START_TIME)
    await update.message.reply_text(build_status_text(START_TIME, users_hour, users_since_start))


async def unrecognized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches anything that isn't a file and isn't a known command --
    registered last, so it only fires when nothing else already handled the
    update. Silence here would just look like the bot ignored them.

    One word typed at a converter is usually a format ("heic", ".epub",
    "webm?"), and answering it costs a dictionary lookup. Anything else gets
    the same answer as before, with a button to the full list.
    """
    lang = await i18n.get_lang(update.effective_user.id, context)
    answer = _format_lookup(lang, update.message.text or "")
    if answer:
        await update.message.reply_text(answer)
        return
    await update.message.reply_text(
        i18n.t(lang, "unrecognized_message"), reply_markup=_what_formats_keyboard(lang),
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "unknown_command"))


async def _post_init(application):
    await tune_runtime(application)
    # Before the first getUpdates -- see lifecycle.py: two containers polling
    # one token is 409 Conflict and split updates, not a graceful overlap.
    await lifecycle.on_start(BOT_NAME)
    await publish_commands(application, BOT_COMMANDS, ADMIN_COMMANDS, ADMIN_IDS)
    await publish_profile(application)


async def _post_stop(application):
    # Before flush_on_shutdown, which closes the pool lifecycle writes through.
    await lifecycle.on_stop(application)
    await flush_on_shutdown(application)


def main():
    if not BOT_TOKEN or not BOT_USERNAME:
        raise SystemExit("Set CBOT_TOKEN and CBOT_USERNAME environment variables first.")

    init_db()
    # Which backends this host actually has. Once, before the first menu is
    # ever built, so nothing is offered that cannot run -- see formats.py.
    formats.probe()

    # Anything left in the staging directory belongs to a process that is no
    # longer running -- clear it before this one starts adding to it.
    _sweep_uploads(max_age_seconds=0)

    builder = (
        ApplicationBuilder().token(BOT_TOKEN)
        .post_init(_post_init).post_stop(_post_stop)
    )
    if LOCAL_BOT_API_URL:
        base = LOCAL_BOT_API_URL.rstrip("/")
        builder = (
            builder
            .base_url(f"{base}/bot")
            .base_file_url(f"{base}/file/bot")
            .local_mode(LOCAL_BOT_API_MODE)
        )
        logger.info("Using local Bot API server at %s (local_mode=%s)", base, LOCAL_BOT_API_MODE)
    state = lifecycle.persistence()
    if state is not None:
        builder = builder.persistence(state)
    app = builder.build()
    lifecycle.install(app, BOT_NAME)
    app.add_error_handler(error_handler)
    attach_problem_reports(app)
    # ---- the handlers that run before everything else ----
    # ONE GROUP EACH, and that is the whole point. python-telegram-bot runs
    # at most ONE handler per group: the first whose filter matches wins and
    # the rest of that group is skipped. track_activity is a TypeHandler on
    # Update, so it matches every update there is -- which meant that for as
    # long as these shared a group, it won every time and nothing else here
    # ever ran. Separate groups, in the order they have to happen in.
    app.add_handler(TypeHandler(Update, track_activity), group=-4)
    # Counted first, then throttled: somebody who floods is still somebody
    # who was here, and /status is supposed to say so.
    attach_flood_gate(app, ADMIN_IDS)
    # Runs after track_activity but before every other handler -- a no-op
    # unless a "Custom" donate button was just tapped, in which case it
    # consumes the reply and stops it from also being treated as a normal
    # message (see donate_custom_amount_received's docstring).
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, donate_custom_amount_received), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("convert", convert_start))
    app.add_handler(CommandHandler("formats", formats_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("mystars", mystars_command))
    app.add_handler(CommandHandler("stars", stars_admin_command))
    app.add_handler(CommandHandler("dbdump", dbdump_command))  # owner-only
    app.add_handler(CommandHandler("messageas", messageas_command))  # owner-only
    app.add_handler(CommandHandler("status", status_command))  # owner-only
    app.add_handler(CallbackQueryHandler(convert_format_chosen, pattern="^convfmt:"))
    app.add_handler(CallbackQueryHandler(convert_show_more, pattern="^conv(more|less)$"))
    app.add_handler(CallbackQueryHandler(convert_quote_go, pattern="^convgo$"))
    app.add_handler(CallbackQueryHandler(convert_quote_back, pattern="^convback$"))
    app.add_handler(CallbackQueryHandler(formats_overview_callback, pattern="^fmtall$"))
    app.add_handler(CallbackQueryHandler(formats_category_callback, pattern="^fmtcat:"))
    app.add_handler(CallbackQueryHandler(cancel_conversion_callback, pattern="^convcancel$"))
    app.add_handler(CallbackQueryHandler(convert_stop_callback, pattern="^convstop:"))
    app.add_handler(CallbackQueryHandler(convert_keep_callback, pattern="^convkeep$"))
    app.add_handler(CallbackQueryHandler(cancel_choice_callback, pattern="^cancelpick:"))
    app.add_handler(CallbackQueryHandler(language_chosen, pattern="^setlang:"))
    app.add_handler(CommandHandler("language", language_command))

    # ---- language: /en, /uz, /rus -- pick at first /start, change anytime ----
    app.add_handler(CommandHandler("en", set_language_en))
    app.add_handler(CommandHandler("uz", set_language_uz))
    app.add_handler(CommandHandler("rus", set_language_rus))
    # ---- what the bot keeps, what it may be used for, and the erase button.
    # Standalone for the same reason the language switches are: somebody who
    # wants to know what is held on them, or wants it gone, should not have to
    # finish whatever they were doing first. ----
    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler("paysupport", paysupport_command))
    add_problem_report_handlers(app)
    app.add_handler(CommandHandler("deletemydata", delete_my_data_command))
    app.add_handler(CallbackQueryHandler(delete_my_data_chosen, pattern="^" + ERASE_PREFIX))

    app.add_handler(CommandHandler("balance", balance_command))
    # ConvertBot sells credit, so here it is "recharge"; the bots that only
    # take support say "donate". /donate keeps working for anyone who learned
    # it, and stays out of the menu -- see UNADVERTISED in tests/test_menu.py.
    app.add_handler(CommandHandler("recharge", donate_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CallbackQueryHandler(donate_amount_chosen, pattern="^donate:"))
    app.add_handler(CallbackQueryHandler(donate_fiat_amount_chosen, pattern="^donatefiat:"))
    app.add_handler(CallbackQueryHandler(donate_custom_button_chosen, pattern="^donatecustom:"))

    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO
            | filters.VOICE | filters.ANIMATION,
            convert_receive_file,
        )
    )

    # Both registered last, so every real handler above gets first shot.
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unrecognized_message))

    # ManagerBot's link: heartbeats, crash/donation events, and the queue it
    # uses to run this bot's owner-only commands remotely. Never raises --
    # with no shared database reachable the bot just runs on its own.
    family_link.attach(app, BOT_NAME, "ConvertBot", START_TIME)
    # One extra bus command, registered here rather than in family_link.py:
    # only this bot sells anything, and family_link.py has to stay
    # byte-identical across all five. Same pattern DownloaderBot uses for
    # probe/providers -- the dispatcher looks COMMANDS up per command, so
    # adding to it after import is enough.
    family_link.COMMANDS["stars"] = _bus_stars
    family_link.COMMAND_HELP["stars"] = "the Stars ledger: paid, free and refunded"
    attach_maintenance(app)
    if app.job_queue is not None:
        app.job_queue.run_repeating(_sweep_uploads_job, interval=300, first=300)

    logger.info("Bot starting (polling)...")
    # A 30-second long poll is the same latency as the default 10 -- Telegram
    # answers the moment an update exists -- for a third of the HTTP requests.
    # allowed_updates lists every kind this bot has a handler for, so Telegram
    # stops sending the rest rather than this process parsing and dropping it.
    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY, Update.PRE_CHECKOUT_QUERY],
    ))


if __name__ == "__main__":
    main()
