"""Each bot's handlers: what it does with a message, a button, a payment.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("bots.py is loaded section by section by main.py -- run main.py")


# ─── module: sticker_bot.bot ─────────────────────────────────────────────────
"""fstik-style sticker pack manager bot."""
import asyncio
import hashlib
import logging
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from io import BytesIO

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputSticker,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyParameters,
)
from telegram.error import BadRequest, NetworkError, RetryAfter, TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ConversationHandler,
    ContextTypes,
    TypeHandler,
    filters,
)

import emoji_utils
import family_link
import i18n
import import_utils
import problems
import lifecycle
import live_message
import video_sticker
from live_message import LiveMessage, edit_in_place
from db import (
    init_db,
    add_pack,
    get_user_packs,
    get_pack_owner,
    get_pack_title,
    set_pack_title,
    get_pack_creator_info,
    add_editor,
    get_coedit_view,
    reset_share_token,
    get_pack_by_token,
    delete_pack_records,
    dump_database_csv_zip,
    count_active_users_since,
    get_user_language,
    set_user_language,
)
from image_utils import to_sticker_png
from video_sticker import to_video_sticker_webm, ConversionError, TooBig
from emoji_utils import DEFAULT_EMOJI, looks_like_emoji_message, split_emoji
from import_utils import (
    parse_telegram_pack_source,
    fetch_importable_stickers,
    sticker_to_input_sticker,
    parse_whatsapp_zip,
    ImportError_ as PackImportError,
    MAX_IMPORT_PER_RUN,
)
from shared_features import (
    note_stat,
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
    problem_report_callback,
    attach_flood_gate,
    attach_maintenance,
    refuse_new_work,
    CANCEL_PICK_ALL,
    CANCEL_PICK_NONE,
    CancelItem,
    ask_cancel_choice,
    cancel_choice_key,
    cancel_items,
    cancel_shared_item,
    finish_cancel_choice,
    keep_going,
    reset_user_state,
    finish_cancel,
    flush_on_shutdown,
    language_keyboard,
    tune_runtime,
    sibling_bots_blurb,
    sibling_bots_keyboard_row,
    maybe_donation_nudge,
    balance_command,
    donate_command,
    donate_amount_chosen,
    donate_fiat_amount_chosen,
    donate_custom_button_chosen,
    awaited_text_received,
    feedback_command,
    HELP_PAGE_PATTERN,
    HELP_TOGGLE_PATTERN,
    NO_PREVIEW,
    full_help_command,
    help_keyboard,
    help_page_button,
    help_page_name,
    help_page_text,
    help_toggle,
    wants_full_help,
    donation_precheckout_callback,
    donation_payment_callback,
    setup_logging,
    error_handler,
    record_error,
    track_activity,
    build_status_text,
)

setup_logging(__file__)
logger = logging.getLogger(__name__)

START_TIME = datetime.now(timezone.utc)

BOT_TOKEN = os.environ.get("SBOT_TOKEN")

BOT_USERNAME = (os.environ.get("SBOT_USERNAME") or "").strip().lstrip("@") or None

ADMIN_IDS = {int(x) for x in os.environ.get("SBOT_ADMIN_ID", "").split(",") if x.strip()}

LOCAL_BOT_API_URL = os.environ.get("LOCAL_BOT_API_URL")
LOCAL_BOT_API_MODE = os.environ.get("LOCAL_BOT_API_MODE", "true").lower() == "true"

BOT_NAME = "stickerbot"

POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "30"))

TITLE, EDITING, RENAME = range(3)

PACK_TITLE_MAX = 64

def build_help_text(lang: str, full: bool = False) -> str:
    """The short version unless asked for the long one -- the family's help template (shared_features, "/help in two lengths")."""
    if not full:
        text = i18n.t(lang, "help_brief").rstrip("\n")
    else:
        text = i18n.t(lang, "help_text").rstrip("\n")
    blurb = sibling_bots_blurb(BOT_NAME, lang)
    return text + "\n\n" + blurb if blurb else text

def _help_page_newpack(lang: str) -> str:
    return i18n.t(lang, "helppage_newpack",
                  title_max=PACK_TITLE_MAX, emoji=emoji_utils.DEFAULT_EMOJI,
                  emoji_max=emoji_utils.MAX_EMOJI_PER_STICKER, side=video_sticker.STICKER_SIDE,
                  seconds=video_sticker.MAX_DURATION_S, fps=video_sticker.MAX_FPS,
                  kb=video_sticker.MAX_BYTES // 1024)

def _help_page_addsticker(lang: str) -> str:
    return i18n.t(lang, "helppage_addsticker", emoji=emoji_utils.DEFAULT_EMOJI)

def _help_page_import(lang: str) -> str:
    return i18n.t(lang, "helppage_import", max=import_utils.MAX_IMPORT_PER_RUN)

HELP_PAGES = {"newpack": _help_page_newpack, "addsticker": _help_page_addsticker, "import": _help_page_import}
HELP_ALIASES = {}

def build_start_text(lang: str) -> str:
    return i18n.t(lang, "start_intro") + build_help_text(lang)

BOT_COMMANDS = [

    BotCommand("start", "What I do, and how to start"),
    BotCommand("language", "Choose your language / Tilni tanlash / Выбрать язык"),
    BotCommand("newpack", "Make a new sticker pack"),
    BotCommand("addsticker", "Add stickers to one of your packs"),
    BotCommand("mypacks", "Your packs"),
    BotCommand("import", "Copy stickers in from another pack"),
    BotCommand("whomade", "Who made a pack — send me one of its stickers"),
    BotCommand("cancel", "Stop whatever I am waiting for"),
    BotCommand("help", "Everything I can do"),
    BotCommand("feedback", "Suggest something, or report a problem"),
    BotCommand("balance", "Your ⚡ credit"),
    BotCommand("donate", "Chip in for hosting costs"),
    BotCommand("paysupport", "Trouble with a payment"),
    BotCommand("privacy", "What I keep about you"),
    BotCommand("terms", "What I may be used for"),
    BotCommand("deletemydata", "Delete everything I hold on you"),
]

ADMIN_COMMANDS = [
    BotCommand("status", "🔒 Uptime, host, errors, active users"),
    BotCommand("whois", "🔒 whois <user_id> — a user, and their packs"),
    BotCommand("messageas", "🔒 messageas <user_id> <text> — DM as this bot"),
    BotCommand("dbdump", "🔒 This bot's tables as a zip of CSVs"),
    BotCommand("crashtest", "🔒 Raise on purpose, to check the alert arrives"),
]

async def reply(update: Update, text: str, **kwargs) -> LiveMessage:
    """Works whether the update came from a command or a button tap."""
    if update.message:
        return await LiveMessage.reply_to(update.message, text, **kwargs)
    return await edit_in_place(update.callback_query.message, update.get_bot(), text, **kwargs)

def slugify(text: str) -> str:
    """Telegram sticker-set names must start with a *letter* (not a digit or underscore) -- a title like "2007" would otherwise slugify to "2007", which Telegram rejects outright with 'Invalid sticker set name is specified'."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    slug = slug[:30].strip("_") or "pack"
    if not slug[0].isalpha():
        slug = ("p_" + slug)[:30].strip("_")
    return slug

def help_rows(lang: str) -> list:
    """New pack and My packs: under /help, and under /start with the sibling bots after them."""
    return [[
        InlineKeyboardButton(i18n.t(lang, "btn_new_pack"), callback_data="menu_newpack"),
        InlineKeyboardButton(i18n.t(lang, "btn_my_packs"), callback_data="menu_mypacks"),
    ]]

def start_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return help_keyboard(lang, False, help_rows(lang) + [sibling_bots_keyboard_row(BOT_NAME)], HELP_PAGES)

def packs_keyboard(packs: list[tuple[str, str]], lang: str) -> InlineKeyboardMarkup:
    """One button per pack (tap opens its menu), fStik-style."""
    rows = [[InlineKeyboardButton(title, callback_data=f"packopen:{pack_ref(name)}")] for name, title in packs]
    rows.append([InlineKeyboardButton(i18n.t(lang, "btn_new_pack"), callback_data="menu_newpack")])
    rows.append([InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data="menu_start")])
    return InlineKeyboardMarkup(rows)

def pack_detail_keyboard(pack_name: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(i18n.t(lang, "btn_open_pack"), url=f"https://t.me/addstickers/{pack_name}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_add_stickers"), callback_data=f"pack:{pack_ref(pack_name)}")],
            [
                InlineKeyboardButton(i18n.t(lang, "btn_rename"), callback_data=f"packrename:{pack_ref(pack_name)}"),
                InlineKeyboardButton(i18n.t(lang, "btn_coedit"), callback_data=f"packcoedit:{pack_ref(pack_name)}"),
            ],
            [InlineKeyboardButton(i18n.t(lang, "btn_delete_pack"), callback_data=f"packdel:{pack_ref(pack_name)}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data="menu_mypacks")],
        ]
    )

def _sticker_error_key(exc: Exception) -> tuple:
    """Which explanation a raw Telegram error from set-creation/add calls gets, as (i18n key, fields)."""
    if isinstance(exc, TimedOut):

        return "err_timed_out", {}
    msg = str(exc)
    lower = msg.lower()
    if "invalid sticker set name" in lower or "sticker_set_name_invalid" in lower:
        return "err_invalid_name", {}
    if "name is already occupied" in lower or "sticker_set_name_occupied" in lower:
        return "err_name_occupied", {}
    if "stickers_too_much" in lower:
        return "err_too_many_stickers", {}
    if "png" in lower and "type" in lower or "webp" in lower and "type" in lower:
        return "err_bad_format", {}
    return "err_generic", {"msg": msg}

def _explain_sticker_error(exc: Exception, lang: str) -> str:
    """Turns raw Telegram API errors from set-creation/add calls into something the user can actually act on, instead of a bare exception."""
    key, fields = _sticker_error_key(exc)
    return i18n.t(lang, key, **fields)

def _sticker_error_note(exc: Exception, lang: str) -> str:
    """The status note a failed sticker leaves: what went wrong, what to do next, and its problem code last, where the Report button looks for it."""
    key, _ = _sticker_error_key(exc)
    return (_explain_sticker_error(exc, lang) + "\n" + i18n.t(lang, "last_attempt_failed")
            + problems.code_line(problems.STICKER_ERRORS[key]))

# Several pictures at once. python-telegram-bot takes one update at a time from its queue here
# (this bot does not set concurrent_updates), so while one picture becomes a sticker, the rest of an
# album wait in that queue. The status message counts them -- "⏳ 5/7" while they are being added,
# "✅ 7/7" when the last one is done -- so nobody thinks the bot saw only the first few. Pictures sent
# meanwhile join the same count.
BATCH_MEDIA = (filters.PHOTO | filters.Document.IMAGE | filters.Sticker.STATIC | filters.ANIMATION
               | filters.VIDEO | filters.Document.VIDEO | filters.Sticker.VIDEO)
BATCH_KEYS = ("batch_open", "batch_seen", "batch_failed", "batch_chat", "batch_removed", "batch_waiting",
              "status_note")

def _queued_items(context: ContextTypes.DEFAULT_TYPE, chat_id) -> int:
    """How many pictures, videos and stickers from this chat wait in the update queue behind the one being made (0 when the queue cannot be read)."""
    try:
        waiting = list(context.application.update_queue._queue)
    except Exception:
        return 0
    count = 0
    for item in waiting:
        try:
            if (isinstance(item, Update) and item.effective_chat is not None
                    and item.effective_chat.id == chat_id and BATCH_MEDIA.check_update(item)):
                count += 1
        except Exception:
            continue
    return count

def _batch_line(context: ContextTypes.DEFAULT_TYPE) -> str:
    """The count while a run of several items is being added ("⏳ 5/7"); nothing for a single one."""
    data = context.user_data
    if not data.get("batch_open"):
        return ""
    seen = data.get("batch_seen", 0)
    total = seen + _queued_items(context, data.get("batch_chat"))
    return f"⏳ {seen}/{total}" if total > 1 else ""

async def _batch_item(update: Update, context: ContextTypes.DEFAULT_TYPE, handler):
    """One item's handler, inside the count: the first item of a run opens it; the last one (nothing of this chat left waiting) closes it with "✅ 7/7", or with how many were not added."""
    data = context.user_data
    chat_id = update.effective_chat.id
    if not data.get("batch_open") or data.get("batch_chat") != chat_id:
        data.update(batch_open=True, batch_seen=0, batch_failed=0, batch_chat=chat_id)
    data["batch_seen"] = data.get("batch_seen", 0) + 1
    data["batch_removed"] = False
    data["batch_waiting"] = False
    before = data.get("sticker_count", 0)
    handled = False
    try:
        result = await handler(update, context)
        handled = (data.get("sticker_count", 0) > before or bool(data.get("batch_removed"))
                   or bool(data.get("batch_waiting")))
        return result
    finally:
        if not handled:
            data["batch_failed"] = data.get("batch_failed", 0) + 1
        if data.get("batch_open") and not _queued_items(context, chat_id):
            seen, failed = data.get("batch_seen", 0), data.get("batch_failed", 0)
            data["batch_open"] = False
            if seen > 1 and _has_status(context):
                try:
                    lang = await i18n.get_lang(update.effective_user.id, context)
                    line = (f"✅ {seen}/{seen}" if not failed
                            else i18n.t(lang, "batch_not_added", done=seen, total=seen, failed=failed))
                    # The count alone: every item has its own answer now, so a note left over
                    # from earlier (an import's error, say) would only be said again (review).
                    await _refresh_status(context, lang, "", batch_line=line)
                except Exception:
                    logger.debug("Couldn't show the run's last count", exc_info=True)

def _status_text(context: ContextTypes.DEFAULT_TYPE, lang: str, note: str = "",
                 batch_line: "str | None" = None) -> str:
    title = context.user_data.get("title") or i18n.t(lang, "status_default_title")
    created = context.user_data.get("pack_created")
    count = context.user_data.get("sticker_count", 0)
    verb = i18n.t(lang, "status_verb_creating" if not created else "status_verb_editing")
    intro = context.user_data.get("status_intro", "")
    text = i18n.t(lang, "status_line", verb=verb, title=title, count=count)
    if intro:
        text = f"{text}\n{intro}"
    line = _batch_line(context) if batch_line is None else batch_line
    if line:
        text += f"\n{line}"
    if note:
        text += f"\n{note}"
    return text

STATUS_KEY = "status"

def _has_status(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.get(STATUS_KEY))

async def _start_status(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, title: str, lang: str,
    intro: str = "", adopt: dict | None = None, **send_kwargs,
):
    """Sets up the session's status message ("✏️ Editing “Memes”"). `send_kwargs` go with a new one -- the pack buttons, say."""
    context.user_data["title"] = title
    context.user_data["sticker_count"] = 0
    context.user_data["status_intro"] = intro
    text = _status_text(context, lang)
    for attempt in (1, 2):
        try:
            live = LiveMessage.restore(adopt)
            if live is None:
                live = await LiveMessage.send(context.bot, chat_id, text, **send_kwargs)
            else:
                await live.set(context.bot, text)
            context.user_data[STATUS_KEY] = live.save()
            return
        except NetworkError as exc:
            # No connection was made (TestBot, 2026-11-13: "httpx.ConnectError" at the TLS
            # handshake), so nothing was sent and sending again cannot double it. Once.
            if attempt == 1 and "ConnectError" in str(exc):
                logger.info("No connection for the status message; trying once more")
                await asyncio.sleep(1.5)
                continue
            raise
    # Anything else goes up to error_handler, which tells the person (FM-CRASH): a pack that opened
    # without a word is what the owner hit on TestBot, 2026-11-13 ("It has left me on seen").

async def _refresh_status(context: ContextTypes.DEFAULT_TYPE, lang: str, note: str = "",
                          batch_line: "str | None" = None):
    live = LiveMessage.restore(context.user_data.get(STATUS_KEY))
    if live is None:
        # No status message to put it in (it could not be sent, or the session's state is
        # gone): a note still reaches the person, as a message of its own.
        # Only a failure (a note ending in a problem code) -- progress lines would be noise.
        chat_id = getattr(context, "_chat_id", None)
        if note and chat_id is not None and problems.find_code(note):
            await context.bot.send_message(chat_id, note)
        return
    context.user_data["status_note"] = note
    await live.set(context.bot, _status_text(context, lang, note, batch_line))

    context.user_data[STATUS_KEY] = live.save()

async def _end_status(context: ContextTypes.DEFAULT_TYPE, final_note: str):
    live = LiveMessage.restore(context.user_data.get(STATUS_KEY))
    if live is not None:
        await live.finish(context.bot, final_note)
    for key in (STATUS_KEY, "sticker_count", "status_intro", *BATCH_KEYS):
        context.user_data.pop(key, None)

async def _owns_pack_or_deny(pack_name: str, user_id: int) -> bool:
    """True if user_id owns pack_name."""
    return await asyncio.to_thread(get_pack_owner, pack_name) == user_id

async def whomade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    if not context.args:
        await update.message.reply_text(i18n.t(lang, "whomade_usage"))
        return

    source = " ".join(context.args)
    pack_name = parse_telegram_pack_source(source) or source
    info = await asyncio.to_thread(get_pack_creator_info, pack_name)
    if not info:
        await update.message.reply_text(i18n.t(lang, "whomade_not_found"))
        return

    if info["owner_username"]:
        creator = f"@{info['owner_username']}"
    elif info["owner_name"]:
        creator = info["owner_name"]
    else:
        creator = f"user {info['owner_id']}"

    created_date = (info["created_at"] or "")[:10]
    await update.message.reply_text(
        i18n.t(lang, "whomade_result", title=info["title"], creator=creator, date=created_date)
    )

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
async def _deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """How an owner-only command answers everybody else: exactly the way a misspelling does."""
    await unknown_command(update, context)

async def whois_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/whois <user_id> -- looks up a Telegram user's profile (name, username, bio) plus any packs of theirs on record, so a numeric id (e.g."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)

    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /whois <user_id>")
        return

    user_id = int(context.args[0])
    lines = [f"🆔 {user_id}"]
    try:
        chat = await context.bot.get_chat(user_id)
        name = " ".join(p for p in (chat.first_name, chat.last_name) if p)
        if name:
            lines.append(f"Name: {name}")
        if chat.username:
            lines.append(f"Username: @{chat.username}")
        if chat.bio:
            lines.append(f"Bio: {chat.bio}")
    except Exception as exc:
        lines.append(f"⚠️ Couldn't fetch their Telegram profile: {exc}")
        lines.append("(They may have never messaged this bot, or blocked it.)")

    packs = await asyncio.to_thread(get_user_packs, user_id)
    if packs:
        lines.append(f"\n📦 Packs ({len(packs)}):")
        lines.extend(f"  • {title}" for _, title in packs)
    else:
        lines.append("\n📦 No packs on record for this id.")

    await update.message.reply_text("\n".join(lines))

async def messageas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/messageas <user_id> <text> -- sends a message to that user as this bot."""
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

async def dbdump_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dbdump -- exports every table in this bot's own database as one zip of CSVs."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    status = await update.message.reply_text("Exporting the database...")
    try:
        data = await asyncio.to_thread(dump_database_csv_zip)
    except Exception as exc:
        await edit_in_place(status, context.bot, f"⚠️ Export failed: {exc}")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    await update.message.reply_document(
        document=BytesIO(data), filename=f"stickerbot_db_{stamp}.zip",
    )
    await status.delete()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status -- uptime, hosting environment, any crashes since this process started, and active-user counts."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    now = datetime.now(timezone.utc)
    users_hour = await asyncio.to_thread(count_active_users_since, now - timedelta(hours=1))
    users_since_start = await asyncio.to_thread(count_active_users_since, START_TIME)
    await update.message.reply_text(build_status_text(START_TIME, users_hour, users_since_start))

async def crashtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/crashtest -- owner-only, deliberately raises so you can confirm /status's error tracking + logs/errors.log actually catch something without needing a real bug."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    raise RuntimeError("Manual /crashtest trigger -- error tracking is working as intended.")

# A pack's name is its title's slug, a random part and "_by_<bot username>" -- up to 61 characters
# with mumu_sticker_bot, and more with a longer username. A button carries at most 64 bytes, so
# "packdelconfirm1:<name>" could not be sent at all, and the message carrying it was lost without a
# word (TestBot, 2026-11-14: Co-edit and Delete did nothing). Buttons carry pack_ref instead.
def pack_ref(pack_name: str) -> str:
    return hashlib.sha256(pack_name.encode()).hexdigest()[:10]

async def _pack_of(user_id: int, ref: str) -> "str | None":
    """The person's own pack a button means: by its reference, or by its full name on a button drawn before 2.1.6. None when it is not one of theirs (any more)."""
    for name, _ in await asyncio.to_thread(get_user_packs, user_id):
        if ref == name or ref == pack_ref(name):
            return name
    return None

# ─── Pack buttons: a keyboard under the message box, one button per pack ────────────────────────
# Tapping "📦 Memes" opens that pack ("✏️ Editing “Memes”") and the next picture goes straight in.
# The buttons are worked out again from the person's packs on every tap, so they need no state:
# the same titles in the same order give the same labels (a repeated title gets " · 2", counted
# oldest first, so a new pack does not renumber the old ones).
PACK_BUTTON = "📦 "
PACK_BUTTONS_MAX = int(os.environ.get("SBOT_PACK_BUTTONS", "12"))
PACK_LABEL_MAX = 40
KB_TITLES = "kb_titles"
# _last_seen too: cleared, the person looked gone -- to the soft stop's count until their next
# message, and to the hourly prune, which dropped a session opened a minute before it ran.
KEEP_ACROSS_SESSIONS = ("lang", "_last_seen", "held", "held_offer", "tags", "keyboard_stale", KB_TITLES)

def _fresh_session(context) -> None:
    """user_data cleared for a new session -- but held items, the retag map and the language stay."""
    keep = {key: context.user_data[key] for key in KEEP_ACROSS_SESSIONS if key in context.user_data}
    context.user_data.clear()
    context.user_data.update(keep)

def _pack_labels(packs) -> "list[tuple[str, str]]":
    """(button label, pack name) for each pack, in the order given (newest first)."""
    seen: dict = {}
    numbered = {}
    for name, title in reversed(list(packs)):
        base = (title or name)[:PACK_LABEL_MAX]
        seen[base] = seen.get(base, 0) + 1
        numbered[name] = base if seen[base] == 1 else f"{base} · {seen[base]}"
    return [(numbered[name], name) for name, _ in packs]

def pack_reply_keyboard(packs, lang: str) -> ReplyKeyboardMarkup:
    """Two buttons a pack -- "✏️ Edit Memes" opens it for adding, "👁 View Memes" shows it -- and "➕ New pack"."""
    rows = [[KeyboardButton(i18n.t(lang, "btn_kb_edit", title=label)),
             KeyboardButton(i18n.t(lang, "btn_kb_view", title=label))]
            for label, _ in _pack_labels(packs)[:PACK_BUTTONS_MAX]]
    rows.append([KeyboardButton(i18n.t(lang, "btn_new_pack"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)

_VARIATION_SELECTORS = dict.fromkeys(map(ord, "\ufe0f\ufe0e"), None)

def _plain(text: str) -> str:
    """Text with emoji variation selectors dropped: "✏️" and "✏" compare equal, whichever a client sends."""
    return (text or "").translate(_VARIATION_SELECTORS).strip()

def _pack_button_action(text: str, packs, remembered: "dict | None" = None) -> "tuple[str, str] | None":
    """("edit" | "view", pack name) for a pack button's text, in any language -- the buttons stay
    readable when the person changes language before the keyboard is redrawn."""
    text = _plain(text)
    owned = dict(packs)
    labels = list(_pack_labels(packs))
    # the labels on the keyboard last sent, for a pack renamed since (still one of theirs)
    labels += [(label, name) for name, label in (remembered or {}).items() if name in owned]
    for label, name in labels:
        for lang in ("en", "uz", "ru"):
            if text == _plain(i18n.t(lang, "btn_kb_edit", title=label)):
                return "edit", name
            if text == _plain(i18n.t(lang, "btn_kb_view", title=label)):
                return "view", name
    return None

_BUTTON_PREFIXES: "list[str]" = []

class _LooksLikePackButton(filters.MessageFilter):
    """Text shaped like a pack button -- "✏️ Edit …" / "👁 View …" in any language -- and nothing
    else. A bare "^(✏|👁)" took emoji such as "👁" or "✏️" (and a pack title starting with one) for
    a button: no retag, no title, "I can't find that pack" (review of 2026-11-14)."""

    def filter(self, message) -> bool:
        if not _BUTTON_PREFIXES:
            for lang in ("en", "uz", "ru"):
                for key in ("btn_kb_edit", "btn_kb_view"):
                    head = i18n.t(lang, key, title="\0").split("\0")[0]
                    _BUTTON_PREFIXES.append(head.translate(_VARIATION_SELECTORS))
        text = (message.text or "").translate(_VARIATION_SELECTORS)
        return any(text.startswith(head) and len(text) > len(head) for head in _BUTTON_PREFIXES)

PACK_BUTTON_TEXT = _LooksLikePackButton()

# A pack can be renamed in Telegram's own sticker settings, which the bot is never told about
# (TestBot, 2026-11-13: "testpack1" renamed "TestNameChange", and the bot kept the old name). So the
# title is read back from Telegram wherever packs are listed or opened, and after every sticker
# added, and the bot's own record follows it.
async def _sync_title(context, pack_name: str, known: "str | None") -> str:
    try:
        sticker_set = await _telegram(context.bot.get_sticker_set, pack_name, read=True)
    except Exception:
        return known or pack_name
    title = getattr(sticker_set, "title", None) or known or pack_name
    if title != known:
        try:
            await asyncio.to_thread(set_pack_title, pack_name, title)
        except Exception:
            logger.debug("Couldn't save a pack's new title", exc_info=True)
        if context.user_data.get("target_pack") == pack_name:
            context.user_data["title"] = title
    return title

async def _sync_titles(context, packs) -> "list[tuple[str, str]]":
    """The titles of the packs that get buttons (PACK_BUTTONS_MAX), read from Telegram all at once."""
    packs = list(packs)
    shown = packs[:PACK_BUTTONS_MAX]
    titles = await asyncio.gather(*(_sync_title(context, name, title) for name, title in shown))
    return [(name, title) for (name, _), title in zip(shown, titles)] + packs[PACK_BUTTONS_MAX:]

async def _pack_keyboard_for(context, user_id: int, lang: str, sync: bool = False) -> ReplyKeyboardMarkup:
    """The pack buttons as they are now (`sync`: titles read from Telegram first). The labels sent are kept (KB_TITLES), so a button still works after its pack is renamed."""
    packs = await asyncio.to_thread(get_user_packs, user_id)
    if sync:
        packs = await _sync_titles(context, packs)
    context.user_data[KB_TITLES] = {name: label for label, name in _pack_labels(packs)[:PACK_BUTTONS_MAX]}
    return pack_reply_keyboard(packs, lang)

async def _with_buttons(context, chat, user_id, lang: str) -> dict:
    """reply_markup for a plain answer in a private chat: the pack buttons. They ride along on nearly
    every answer, so they come back by themselves if anything took them away (/cancel did, on
    TestBot 2026-11-13: "the button menu disappeared"). Never on a message that is edited later --
    an edit cannot carry them."""
    if chat is None or getattr(chat, "type", None) != "private" or not user_id:
        return {}
    try:
        return {"reply_markup": await _pack_keyboard_for(context, user_id, lang)}
    except Exception:
        logger.debug("Pack buttons not attached", exc_info=True)
        return {}

def _new_pack_labels() -> "list[str]":
    return sorted({i18n.t(lang, "btn_new_pack") for lang in ("en", "uz", "ru")})

async def _send_pack_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    if update.effective_chat is None or update.effective_chat.type != "private":
        return
    try:
        await context.bot.send_message(update.effective_chat.id, i18n.t(lang, "packs_keyboard_note"),
                                       reply_markup=await _pack_keyboard_for(
                                           context, update.effective_user.id, lang, sync=True))
    except Exception:
        logger.debug("Couldn't send the pack buttons", exc_info=True)

async def _open_pack(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, pack_name: str,
                     owner_id: int, title: str, adopt: "dict | None" = None, intro_key: str = "editing_intro_add"):
    """The pack is open for adding: "✏️ Editing “Memes”", and anything held goes in."""
    # Opening the pack that is already open keeps its last sticker, so plain emoji still retag it
    # (TestBot, 2026-11-13: the button tapped mid-session, then emoji -> "Add a sticker first").
    same = context.user_data.get("target_pack") == pack_name
    last_sticker = context.user_data.get("last_sticker_id") if same else None
    title = await _sync_title(context, pack_name, title)
    _fresh_session(context)
    context.user_data.update(lang=lang, mode="add", pack_created=True, target_pack=pack_name, owner_id=owner_id)
    if last_sticker:
        context.user_data["last_sticker_id"] = last_sticker
    send_kwargs = {}
    if adopt is None and update.effective_chat.type == "private":
        context.user_data.pop("keyboard_stale", None)
        send_kwargs["reply_markup"] = await _pack_keyboard_for(context, update.effective_user.id, lang, sync=True)
    await _start_status(context, update.effective_chat.id, title, lang, intro=i18n.t(lang, intro_key),
                        adopt=adopt, **send_kwargs)
    await _add_held(update, context, lang)
    return EDITING

async def pack_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on "✏️ Edit Memes" or "👁 View Memes" under the message box."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    packs = await asyncio.to_thread(get_user_packs, update.effective_user.id)
    found = _pack_button_action(update.message.text.strip(), packs, context.user_data.get(KB_TITLES))
    if found is None:
        await update.message.reply_text(
            i18n.t(lang, "pack_button_gone"),
            reply_markup=await _pack_keyboard_for(context, update.effective_user.id, lang, sync=True))
        return None
    action, pack_name = found
    title = dict(packs).get(pack_name) or pack_name
    if action == "view":
        title = await _sync_title(context, pack_name, title)
        # One tap on the link opens the pack itself; whatever session is open stays open.
        await update.message.reply_text(
            i18n.t(lang, "pack_view", title=title),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                i18n.t(lang, "btn_open_pack"), url=f"https://t.me/addstickers/{pack_name}")]]))
        return None
    return await _open_pack(update, context, lang, pack_name, update.effective_user.id, title)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start prints the instructions -- except the very first one, which asks for a language first."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    if context.args:
        if lang is None:
            context.user_data["pending_start_args"] = context.args
            await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
            return ConversationHandler.END
        context.user_data["lang"] = lang
        return await _continue_start(update, context, lang, context.args)

    if _has_status(context):
        await _end_status(context, i18n.t(lang or "en", "cancelled_status_note"))
    _fresh_session(context)

    if lang is None:
        await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
        return ConversationHandler.END

    context.user_data["lang"] = lang
    result = await _continue_start(update, context, lang, None)
    await _send_pack_keyboard(update, context, lang)
    return result

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/language -- the picker on demand, which is what /start used to be."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)

    if lang:
        context.user_data["lang"] = lang
    await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard(lang))

async def _continue_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, args):
    if args and args[0].startswith("s_"):
        return await start_coedit_link(update, context, args[0][2:], lang)

    await reply(update, build_start_text(lang), reply_markup=start_menu_keyboard(lang))
    return ConversationHandler.END

async def _apply_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """The single path every language change goes through -- /en, /uz, /rus and a tap on the picker alike."""
    await asyncio.to_thread(set_user_language, update.effective_user.id, lang)
    pending = context.user_data.get("pending_start_args") or []
    if _has_status(context):
        await _end_status(context, i18n.t(lang, "cancelled_status_note"))
    _fresh_session(context)
    context.user_data["lang"] = lang

    await refresh_chat_menu(context, update.effective_user.id, lang)
    return await _continue_start(update, context, lang, pending)

async def _set_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    await update.message.reply_text(i18n.t(lang, "language_set_confirmation"))
    return await _apply_language(update, context, lang)

async def set_language_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _set_language(update, context, "en")

async def set_language_uz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _set_language(update, context, "uz")

async def set_language_rus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _set_language(update, context, "ru")

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on the picker."""
    query = update.callback_query
    lang = query.data.split(":", 1)[1]
    await query.answer(i18n.t(lang, "language_set_confirmation"))
    return await _apply_language(update, context, lang)

async def menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'⬅️ Back' from deeper in the menu -- edits back to the start view instead of leaving a trail of old menu messages behind."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.callback_query.answer()
    await edit_in_place(update.callback_query.message, context.bot, build_start_text(lang), reply_markup=start_menu_keyboard(lang))

async def start_coedit_link(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, lang: str):
    """Handles /start s_<token> -- someone opening a co-edit share link."""
    pack_name = await asyncio.to_thread(get_pack_by_token, token)
    if not pack_name:
        await reply(update, i18n.t(lang, "coedit_link_invalid"))
        return ConversationHandler.END

    owner_id = await asyncio.to_thread(get_pack_owner, pack_name)
    user = update.effective_user
    if owner_id is None:
        await reply(update, i18n.t(lang, "coedit_pack_gone"))
        return ConversationHandler.END
    if owner_id == user.id:
        await reply(update, i18n.t(lang, "coedit_own_pack"))
        return ConversationHandler.END

    await asyncio.to_thread(add_editor, pack_name, user.id)
    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name

    _fresh_session(context)
    context.user_data["lang"] = lang
    context.user_data["mode"] = "add"
    context.user_data["pack_created"] = True
    context.user_data["target_pack"] = pack_name
    context.user_data["owner_id"] = owner_id

    intro = i18n.t(lang, "coedit_joined_intro", title=title)
    await _start_status(context, update.effective_chat.id, title, lang, intro=intro)
    return EDITING

async def menu_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The Help button on a start menu sent before 2.1.0: the full guide."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.callback_query.answer()
    await edit_in_place(update.callback_query.message, context.bot, build_help_text(lang, full=True),
                        reply_markup=help_keyboard(lang, True, help_rows(lang), HELP_PAGES))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help is the short version; /help full is the long one."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    page = help_page_name(context, HELP_PAGES, HELP_ALIASES)
    if page:
        await update.message.reply_text(help_page_text(lang, HELP_PAGES, page),
                                        link_preview_options=NO_PREVIEW)
        return
    full = wants_full_help(context)
    await update.message.reply_text(build_help_text(lang, full=full),
                                    reply_markup=help_keyboard(lang, full, help_rows(lang), HELP_PAGES))

async def menu_mypacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await show_packs(update, context)

async def mypacks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_packs(update, context)

async def show_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    user_id = update.effective_user.id
    packs = await _sync_titles(context, await asyncio.to_thread(get_user_packs, user_id))
    if not packs:
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(i18n.t(lang, "btn_new_pack"), callback_data="menu_newpack")],
                [InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data="menu_start")],
            ]
        )
        await reply(update, i18n.t(lang, "no_packs_yet"), reply_markup=kb)
        return
    await reply(update, i18n.t(lang, "your_packs"), reply_markup=packs_keyboard(packs, lang))

async def pack_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "not_your_pack"), show_alert=True)
        return
    await query.answer()

    title = await _sync_title(context, pack_name, await asyncio.to_thread(get_pack_title, pack_name))
    await edit_in_place(query.message, context.bot,
        i18n.t(lang, "pack_detail_title", title=title), reply_markup=pack_detail_keyboard(pack_name, lang)
    )

async def _send_coedit_message(message, bot, pack_name: str, lang: str):

    token, title, editor_count = await asyncio.to_thread(get_coedit_view, pack_name)
    title = title or pack_name
    link = f"https://t.me/{BOT_USERNAME}?start=s_{token}"
    editors_line = (
        i18n.t(lang, "coedit_count_some", count=editor_count) if editor_count
        else i18n.t(lang, "coedit_count_none")
    )

    text = i18n.t(lang, "coedit_message", title=title, link=link, editors_line=editors_line)
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(i18n.t(lang, "btn_reset_link"), callback_data=f"cotoken_reset:{pack_ref(pack_name)}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data=f"packopen:{pack_ref(pack_name)}")],
        ]
    )
    await edit_in_place(message, bot, text, reply_markup=kb)

async def coedit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_coedit"), show_alert=True)
        return
    await query.answer()
    await _send_coedit_message(query.message, context.bot, pack_name, lang)

async def coedit_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_coedit"), show_alert=True)
        return

    await asyncio.to_thread(reset_share_token, pack_name)
    await query.answer(i18n.t(lang, "link_reset_confirm"))
    await _send_coedit_message(query.message, context.bot, pack_name, lang)

async def rename_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_rename"), show_alert=True)
        return ConversationHandler.END

    await query.answer()
    _fresh_session(context)
    context.user_data["lang"] = lang
    context.user_data["rename_pack"] = pack_name

    prompt = await edit_in_place(
        query.message, context.bot,
        i18n.t(lang, "rename_prompt",
               title=await asyncio.to_thread(get_pack_title, pack_name) or pack_name),
    )
    context.user_data["rename_prompt"] = prompt.save()
    return RENAME

async def receive_new_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    pack_name = context.user_data.get("rename_pack")
    prompt = LiveMessage.restore(context.user_data.get("rename_prompt"))
    new_title = update.message.text.strip()[:PACK_TITLE_MAX]
    if not pack_name or prompt is None:
        await update.message.reply_text(i18n.t(lang, "rename_broken_state"))
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([[InlineKeyboardButton(i18n.t(lang, "btn_back_to_pack"), callback_data=f"packopen:{pack_ref(pack_name)}")]])
    try:
        await context.bot.set_sticker_set_title(name=pack_name, title=new_title)
        await asyncio.to_thread(set_pack_title, pack_name, new_title)
        context.user_data["keyboard_stale"] = True
        await prompt.finish(context.bot, i18n.t(lang, "renamed_success", title=new_title), reply_markup=kb)
    except Exception as exc:
        logger.exception("Rename failed")
        await prompt.finish(context.bot, i18n.t(lang, "renamed_failed", error=exc), reply_markup=kb)

    _fresh_session(context)
    return ConversationHandler.END

async def delete_pack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """First tap of 'Delete pack' -- owner-only (co-editors never even see this button, since it only appears in the /mypacks detail menu, but the check is repeated here too since callback_data can be replayed)."""
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_delete"), show_alert=True)
        return
    await query.answer()

    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(i18n.t(lang, "btn_delete"), callback_data=f"packdelconfirm1:{pack_ref(pack_name)}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_cancel_inline"), callback_data=f"packopen:{pack_ref(pack_name)}")],
        ]
    )
    await edit_in_place(query.message, context.bot,
        i18n.t(lang, "delete_confirm1", title=title),
        reply_markup=kb,
    )

async def delete_pack_confirm1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Second tap -- one more explicit confirmation before anything actually happens."""
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_delete"), show_alert=True)
        return
    await query.answer()

    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(i18n.t(lang, "btn_delete_confirm"), callback_data=f"packdelconfirm2:{pack_ref(pack_name)}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_cancel_inline"), callback_data=f"packopen:{pack_ref(pack_name)}")],
        ]
    )
    await edit_in_place(query.message, context.bot,
        i18n.t(lang, "delete_confirm2", title=title),
        reply_markup=kb,
    )

async def delete_pack_confirm2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Third tap -- actually deletes the set from Telegram and wipes local records."""
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_delete"), show_alert=True)
        return
    await query.answer()

    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    try:
        await context.bot.delete_sticker_set(name=pack_name)
    except Exception as exc:
        lower = str(exc).lower()
        if "invalid" not in lower and "not found" not in lower:
            logger.exception("Failed to delete sticker set")
            await edit_in_place(query.message, context.bot, i18n.t(lang, "delete_failed", error=exc))
            return

    await asyncio.to_thread(delete_pack_records, pack_name)
    context.user_data["keyboard_stale"] = True
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(i18n.t(lang, "btn_my_packs_back"), callback_data="menu_mypacks")]])
    await edit_in_place(query.message, context.bot, i18n.t(lang, "delete_success", title=title), reply_markup=kb)

async def newpack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    _fresh_session(context)
    context.user_data["lang"] = lang
    context.user_data["mode"] = "new"
    context.user_data["pack_created"] = False
    context.user_data["owner_id"] = update.effective_user.id
    if update.callback_query:
        await update.callback_query.answer()
    msg = await reply(update, i18n.t(lang, "newpack_title_prompt"))

    context.user_data["title_prompt"] = msg.save()
    return TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text(i18n.t(lang, "title_empty"))
        return TITLE
    if len(title) > PACK_TITLE_MAX:
        title = title[:PACK_TITLE_MAX]
        await update.message.reply_text(i18n.t(lang, "title_truncated", title=title))

    intro = i18n.t(lang, "editing_intro_new")
    prompt = context.user_data.pop("title_prompt", None)
    await _start_status(
        context, update.effective_chat.id, title, lang, intro=intro, adopt=prompt,
    )
    await _add_held(update, context, lang)
    return EDITING

async def addsticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    user_id = update.effective_user.id
    packs = await _sync_titles(context, await asyncio.to_thread(get_user_packs, user_id))
    if not packs:
        await update.message.reply_text(i18n.t(lang, "no_packs_for_add"))
        return
    await update.message.reply_text(
        i18n.t(lang, "pick_pack_prompt"), reply_markup=packs_keyboard(packs, lang)
    )

async def pack_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    owner_id = await asyncio.to_thread(get_pack_owner, pack_name)
    if owner_id != user.id:
        await query.answer(i18n.t(lang, "not_your_pack"), show_alert=True)
        return ConversationHandler.END
    await query.answer()
    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    return await _open_pack(update, context, lang, pack_name, owner_id, title,
                            adopt=LiveMessage.adopt(query.message).save())

# Telegram limits how quickly stickers go into a pack. A run of pictures (an album) meets that
# limit as "Flood control exceeded. Retry in 10 seconds" (production, 2026-10-30), and that
# picture was lost. A request answered that way was not carried out, so it is sent again after the
# wait: at most TELEGRAM_TRIES times, and only for waits of up to FLOOD_WAIT_MAX seconds -- a
# longer one fails that picture with the usual note. Reads (fetching the picture, reading the pack
# back) are also tried again after a timeout or a dropped connection: on 2026-11-04 a picture's
# download timed out and the person got the crash reply. Creating a pack or adding a sticker is
# never repeated after a timeout, since it may have gone through.
TELEGRAM_TRIES = 3
FLOOD_WAIT_MAX = 30
# "Shortname_occupy_failed" (production, 2026-10-29): Telegram could not take a new pack's name.
# Another random name is tried, up to NAME_TRIES names in all.
NAME_TRIES = 3

def _retry_after_seconds(exc: RetryAfter) -> float:
    value = getattr(exc, "retry_after", None)
    if isinstance(value, timedelta):
        return value.total_seconds()
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(FLOOD_WAIT_MAX + 1)

async def _telegram(call, *args, read: bool = False, **kwargs):
    """`call(*args, **kwargs)`, sent again when Telegram asks to wait, and with read=True also after a timeout or a dropped connection."""
    for attempt in range(1, TELEGRAM_TRIES + 1):
        try:
            return await call(*args, **kwargs)
        except RetryAfter as exc:
            wait = _retry_after_seconds(exc)
            if attempt == TELEGRAM_TRIES or wait > FLOOD_WAIT_MAX:
                raise
            logger.info("Telegram asked to wait %.0f s before %s; waiting", wait,
                        getattr(call, "__name__", "the next call"))
            await asyncio.sleep(wait + 0.5)
        except NetworkError as exc:
            # BadRequest is a NetworkError in python-telegram-bot: a refusal, never sent again.
            if not read or isinstance(exc, BadRequest) or attempt == TELEGRAM_TRIES:
                raise
            await asyncio.sleep(2 * attempt)

async def _download_media(bot, file_id: str) -> bytes:
    tg_file = await _telegram(bot.get_file, file_id, read=True)
    return bytes(await _telegram(tg_file.download_as_bytearray, read=True))

def _name_refused(exc: BadRequest) -> bool:
    lower = str(exc).lower()
    return ("shortname_occupy_failed" in lower or "name is already occupied" in lower
            or "sticker_set_name_occupied" in lower)

async def _add_input_sticker(
    context: ContextTypes.DEFAULT_TYPE, user, input_sticker: InputSticker,
    want_file_id: bool = True,
) -> str | None:
    """Creates the pack (first sticker of a /newpack session) or adds to the existing target pack."""
    owner_id = context.user_data["owner_id"]

    if not context.user_data.get("pack_created"):
        title = context.user_data["title"]

        for attempt in range(1, NAME_TRIES + 1):
            pack_name = f"{slugify(title)}_{secrets.token_hex(5)}_by_{BOT_USERNAME}"
            try:
                await _telegram(
                    context.bot.create_new_sticker_set,
                    user_id=owner_id,
                    name=pack_name,
                    title=title,
                    stickers=[input_sticker],
                    read_timeout=60,
                    write_timeout=60,
                )
                break
            except BadRequest as exc:
                if attempt == NAME_TRIES or not _name_refused(exc):
                    raise
                logger.info("Telegram did not take a new pack's name (%s); trying another", exc)
        await asyncio.to_thread(
            add_pack, owner_id, pack_name, title, user.username, user.full_name
        )
        context.user_data["target_pack"] = pack_name
        context.user_data["pack_created"] = True
        context.user_data["keyboard_stale"] = True
        note_stat("sticker_pack", "created")
    else:
        pack_name = context.user_data["target_pack"]
        await _telegram(
            context.bot.add_sticker_to_set,
            user_id=owner_id,
            name=pack_name,
            sticker=input_sticker,
            read_timeout=60,
            write_timeout=60,
        )

    if not want_file_id:
        return None
    try:
        sticker_set = await _telegram(context.bot.get_sticker_set, pack_name, read=True)
    except Exception:
        # The sticker is in the pack; only its id for retagging is missing.
        logger.warning("Couldn't read the pack back after adding a sticker", exc_info=True)
        return None
    title = getattr(sticker_set, "title", None)
    if title and title != context.user_data.get("title"):
        context.user_data["title"] = title
        try:
            await asyncio.to_thread(set_pack_title, pack_name, title)
        except Exception:
            logger.debug("Couldn't save a pack's new title", exc_info=True)
    return sticker_set.stickers[-1].file_id

async def _remember_last_sticker(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run once after a bulk import so "send emoji to retag" still points at the last sticker added -- one getStickerSet instead of one per sticker."""
    pack_name = context.user_data.get("target_pack")
    if not pack_name:
        return
    try:
        sticker_set = await context.bot.get_sticker_set(pack_name)
        context.user_data["last_sticker_id"] = sticker_set.stickers[-1].file_id
    except Exception:
        logger.debug("Couldn't re-read the pack after a bulk import", exc_info=True)

# ─── Items: one picture, clip or sticker the person sent ────────────────────────────────────────
# Every item is answered in place, as a reply to it: "✅ Added to “Memes” with 😭. Reply to this
# message with emoji to change it." The reply's message id is remembered beside the sticker it made
# (TAGS_KEY), so emoji sent as a reply to it retag that sticker -- any of them, not only the last.
# An item is a plain dict (it waits in user_data while held, so it has to be JSON):
# chat, msg (its message id), kind ("static" | "video"), file_id, set and uid (a sticker's own
# pack and unique id, to notice one that is already in the pack), at (when it came).
TAGS_KEY = "tags"
TAGS_KEEP = 400  # two per sticker: its ✅ answer and the message it was made from

def _item_of(msg) -> "dict | None":
    """The item a message carries, or None for anything that is not a picture, clip or sticker."""
    sticker = msg.sticker
    if sticker is not None:
        if sticker.is_animated:
            return None
        kind, file_id = ("video" if sticker.is_video else "static"), sticker.file_id
    elif msg.photo:
        kind, file_id = "static", msg.photo[-1].file_id
    elif msg.animation:
        kind, file_id = "video", msg.animation.file_id
    elif msg.video:
        kind, file_id = "video", msg.video.file_id
    elif msg.document and (msg.document.mime_type or "").startswith("image/"):
        kind, file_id = "static", msg.document.file_id
    elif msg.document and (msg.document.mime_type or "").startswith("video/"):
        kind, file_id = "video", msg.document.file_id
    else:
        return None
    return {"chat": msg.chat_id, "msg": msg.message_id, "kind": kind, "file_id": file_id,
            "set": getattr(sticker, "set_name", None), "uid": getattr(sticker, "file_unique_id", None),
            "at": time.time()}

async def _reply_to_item(context, item: dict, text: str, reply_markup=None, buttons: bool = True):
    """A new message answering `item`, as a reply to it. In a private chat the pack buttons ride along (_with_buttons) -- unless `buttons` is False: an answer that is edited later ("Converting…") cannot keep them."""
    # Never on an answer that carries a problem code: note_problem adds "Send more details" only
    # beside an inline keyboard or none, and the pack buttons would keep it off (review).
    if reply_markup is None and buttons and item["chat"] > 0 and not problems.find_code(text):
        try:
            reply_markup = await _pack_keyboard_for(context, item["chat"], context.user_data.get("lang") or "en")
            context.user_data.pop("keyboard_stale", None)
        except Exception:
            logger.debug("Pack buttons not attached; the answer goes without them", exc_info=True)
    sent = await context.bot.send_message(
        item["chat"], text, reply_markup=reply_markup,
        reply_parameters=ReplyParameters(message_id=item["msg"], allow_sending_without_reply=True))
    live_message.bump(sent.chat_id, sent.message_id)
    return sent

async def _edit_reply(context, sent, text: str, reply_markup=None, item: "dict | None" = None):
    """Rewrite one of the item replies in place -- never moved to the bottom, so it stays beside its item. Returns the message that now says it: `sent`, or, when the person deleted it, a new answer to `item`."""
    try:
        await context.bot.edit_message_text(chat_id=sent.chat_id, message_id=sent.message_id, text=text,
                                            reply_markup=reply_markup)
    except BadRequest as exc:
        lowered = str(exc).lower()
        if "not modified" in lowered:
            return sent
        if item is not None and ("not found" in lowered or "can't be edited" in lowered):
            return await _reply_to_item(context, item, text, reply_markup=reply_markup, buttons=False)
        raise
    return sent

def _tag_key(chat_id, message_id) -> str:
    """Message ids are per chat: the same id in a group and in the private chat is two messages."""
    return f"{chat_id}:{message_id}"

def _remember_tag(context, chat_id, message_id: int, sticker_id: "str | None") -> None:
    if not sticker_id or message_id is None:
        return
    tags = context.user_data.setdefault(TAGS_KEY, {})
    tags[_tag_key(chat_id, message_id)] = sticker_id
    for old in list(tags)[:-TAGS_KEEP]:
        tags.pop(old, None)

def _pack_title(context) -> str:
    return context.user_data.get("title") or context.user_data.get("target_pack") or ""

async def _is_own_pack_sticker(context: ContextTypes.DEFAULT_TYPE, item: dict) -> bool:
    """True if the item is a sticker still in the pack being edited (as opposed to a fresh image, or a sticker from some *other* pack, which still gets added normally)."""
    target_pack = context.user_data.get("target_pack")
    if not target_pack or not item.get("set") or item["set"] != target_pack:
        return False
    try:
        sticker_set = await context.bot.get_sticker_set(target_pack)
    except Exception:
        return True
    return any(s.file_unique_id == item.get("uid") for s in sticker_set.stickers)

async def _remove_own_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE, item: dict) -> int:
    """Handles the 'sent a sticker that's already in this pack' case by removing it instead of trying (and failing) to re-add it -- Telegram rejects re-adding a sticker to the exact set it already belongs to with an unhelpful STICKERSET_INVALID error, so this sidesteps that entirely."""
    context.user_data["batch_removed"] = True  # the item did what it was sent for: not a failure in the count
    lang = await i18n.get_lang(update.effective_user.id, context)
    try:
        sticker_set = await context.bot.get_sticker_set(item["set"])
    except Exception:
        sticker_set = None

    if sticker_set and len(sticker_set.stickers) <= 1:
        context.user_data["pending_removal"] = item["file_id"]
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(i18n.t(lang, "btn_delete_pack_yes"), callback_data="confirmremove:yes"),
                    InlineKeyboardButton(i18n.t(lang, "btn_cancel"), callback_data="confirmremove:no"),
                ]
            ]
        )
        await _reply_to_item(context, item, i18n.t(lang, "remove_last_confirm"), reply_markup=kb)
        return EDITING

    try:
        await _telegram(context.bot.delete_sticker_from_set, sticker=item["file_id"])
    except Exception as exc:
        logger.exception("Failed to delete sticker from set")
        record_error(exc)
        await _reply_to_item(context, item, i18n.t(lang, "remove_failed", error=exc))
        return EDITING
    context.user_data["sticker_count"] = max(0, context.user_data.get("sticker_count", 0) - 1)
    await _reply_to_item(context, item, i18n.t(lang, "remove_success"))
    return EDITING

async def confirm_remove_last_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    await query.answer()
    choice = query.data.split(":", 1)[1]
    file_id = context.user_data.pop("pending_removal", None)

    if choice == "no" or not file_id:
        await edit_in_place(query.message, context.bot, i18n.t(lang, "keep_pack"))
        return EDITING

    target_pack = context.user_data.get("target_pack")
    try:
        await context.bot.delete_sticker_from_set(sticker=file_id)
    except Exception as exc:
        logger.exception("Failed to delete the last sticker / pack")
        record_error(exc)
        await edit_in_place(query.message, context.bot, i18n.t(lang, "remove_failed", error=exc))
        return EDITING

    if target_pack:
        await asyncio.to_thread(delete_pack_records, target_pack)
    await edit_in_place(query.message, context.bot, i18n.t(lang, "pack_deleted_empty"))
    await _end_status(context, i18n.t(lang, "pack_deleted_note"))
    _fresh_session(context)
    context.user_data["keyboard_stale"] = True
    return ConversationHandler.END

async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Static images / static stickers -> PNG sticker, counted when several come at once (_batch_item)."""
    return await _batch_item(update, context, _receive_media)

async def _receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    item = _item_of(update.message)
    if item is None:
        return EDITING
    item["kind"] = "static"
    return await _add_item(update, context, lang, item)

async def receive_video_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GIFs / videos / video stickers -> WEBM video sticker, counted when several come at once (_batch_item)."""
    return await _batch_item(update, context, _receive_video_media)

async def _receive_video_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    item = _item_of(update.message)
    if item is None:
        return EDITING
    item["kind"] = "video"
    return await _add_item(update, context, lang, item)

async def _add_item(update, context, lang: str, item: dict, held: bool = False) -> int:
    """One item into the pack being edited, answered as a reply to it."""
    if item.get("set") and await _is_own_pack_sticker(context, item):
        if held:
            # Sent with no pack open, then this pack picked for it: that is no request to take
            # it out (the review found the held sticker deleted from the pack picked for it).
            await _reply_to_item(context, item, i18n.t(lang, "held_already_in_pack", title=_pack_title(context)))
            return EDITING
        return await _remove_own_sticker(update, context, item)
    if item["kind"] == "video":
        await _add_video_item(update, context, lang, item)
    else:
        await _add_static_item(update, context, lang, item)
    return EDITING

async def _add_static_item(update, context, lang: str, item: dict) -> None:
    """Static images / static stickers -> PNG sticker."""
    try:
        raw = await _download_media(context.bot, item["file_id"])
        png_bytes = (await asyncio.to_thread(to_sticker_png, raw)).getvalue()
    except Exception as exc:
        record_error(exc)
        await _reply_to_item(context, item, i18n.t(lang, "image_process_failed", error=exc))
        return

    input_sticker = InputSticker(sticker=png_bytes, emoji_list=[DEFAULT_EMOJI], format="static")
    try:
        last_id = await _add_input_sticker(context, update.effective_user, input_sticker)
    except Exception as exc:
        logger.exception("Sticker set operation failed")
        record_error(exc)
        await _reply_to_item(context, item, _sticker_error_note(exc, lang))
        return
    context.user_data["last_sticker_id"] = last_id
    context.user_data["sticker_count"] = context.user_data.get("sticker_count", 0) + 1
    note_stat("sticker", "picture")
    sent = await _reply_to_item(context, item, i18n.t(lang, "item_added", title=_pack_title(context),
                                                      emoji=DEFAULT_EMOJI))
    _remember_tag(context, item["chat"], sent.message_id, last_id)
    _remember_tag(context, item["chat"], item["msg"], last_id)

async def _add_video_item(update, context, lang: str, item: dict) -> None:
    """GIFs / videos / video stickers -> WEBM video sticker (via ffmpeg)."""
    refusal = await refuse_new_work(lang, update.effective_user.id, item["chat"])
    if refusal:
        await _reply_to_item(context, item, refusal)
        return
    try:
        raw = await _download_media(context.bot, item["file_id"])
    except Exception as exc:
        logger.warning("Couldn't fetch a clip to make a sticker of", exc_info=True)
        record_error(exc)
        await _reply_to_item(context, item, i18n.t(lang, "video_convert_generic_failed", error=exc))
        return

    duration = await asyncio.to_thread(video_sticker.clip_duration, bytes(raw))
    if video_sticker.is_too_long(duration):
        # Not cut short any more: the person picks a speed, or trims it themselves. Waiting on a
        # choice is not a failure in the run's count; refused (no speed fits) it is.
        if await _offer_video_fit(context, lang, item, None, {}, "long", duration):
            context.user_data["batch_waiting"] = True
        return
    await _make_video_sticker(update, context, lang, raw, item, {}, None)

def _needs_session(handler):
    """A handler of an open pack session. The session's state can be gone while the conversation is still open -- dropped after USER_DATA_TTL_HOURS idle, or lost in a restart. A picture or clip is then held and the person asked which pack it is for (_hold_item); anything else is told the session closed. Either way the conversation ends instead of failing on a missing key."""
    async def guarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if "owner_id" in context.user_data:
            return await handler(update, context)
        lang = await i18n.get_lang(update.effective_user.id, context)
        if update.callback_query:
            await update.callback_query.answer()
        item = _item_of(update.message) if update.message else None
        if item is not None and update.effective_chat.type == "private":
            await _hold_item(context, lang, item)
            return ConversationHandler.END
        await reply(update, i18n.t(lang, "session_lost"))
        return ConversationHandler.END
    guarded.__name__ = handler.__name__
    guarded.__doc__ = handler.__doc__
    return guarded

# ─── Held items: sent with no pack open ──────────────────────────────────────────────────────────
# Someone who thinks a pack is still open sends pictures; the bot has no pack for them (none was
# picked, or the session was dropped). They are held for HOLD_SECONDS and the person is asked which
# pack they go to -- one question for a whole album, its count kept up to date.
HELD_KEY = "held"
HELD_OFFER_KEY = "held_offer"
HOLD_SECONDS = int(os.environ.get("SBOT_HOLD_SECONDS", "600"))
HOLD_MAX = 30

def _held_now(context) -> list:
    now = time.time()
    return [item for item in context.user_data.get(HELD_KEY) or () if now - item.get("at", 0) < HOLD_SECONDS]

async def _hold_item(context, lang: str, item: dict) -> None:
    waiting = _held_now(context)
    if len(waiting) >= HOLD_MAX:
        # Never dropped without a word (the review found the oldest silently lost past 30).
        await _reply_to_item(context, item, i18n.t(lang, "held_full", n=HOLD_MAX))
        return
    held = waiting + [item]
    context.user_data[HELD_KEY] = held
    packs = await asyncio.to_thread(get_user_packs, item["chat"])
    if not waiting:
        packs = await _sync_titles(context, packs)          # a new question: names as Telegram has them
    rows = [[InlineKeyboardButton(PACK_BUTTON + label, callback_data=f"hp:{pack_ref(name)}")]
            for label, name in _pack_labels(packs)[:PACK_BUTTONS_MAX]]
    rows.append([InlineKeyboardButton(i18n.t(lang, "btn_new_pack"), callback_data="hp+"),
                 InlineKeyboardButton(i18n.t(lang, "btn_held_discard"), callback_data="hp-")])
    text = i18n.t(lang, "held_offer", n=len(held), minutes=HOLD_SECONDS // 60)
    offer = LiveMessage.restore(context.user_data.get(HELD_OFFER_KEY)) if waiting else None
    if offer is not None:
        try:
            await context.bot.edit_message_text(chat_id=offer.chat_id, message_id=offer.message_id, text=text,
                                                reply_markup=InlineKeyboardMarkup(rows))
            return
        except BadRequest as exc:
            if "not modified" in str(exc).lower():
                return
            logger.debug("Couldn't update the held-items question; asking again", exc_info=True)
        except Exception:
            logger.debug("Couldn't update the held-items question; asking again", exc_info=True)
    sent = await _reply_to_item(context, item, text, reply_markup=InlineKeyboardMarkup(rows))
    context.user_data[HELD_OFFER_KEY] = LiveMessage.adopt(sent).save()

async def media_without_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A picture, clip or sticker in a private chat with no pack open: held, and the person asked which pack."""
    item = _item_of(update.message)
    if item is None:
        return
    lang = await i18n.get_lang(update.effective_user.id, context)
    await _hold_item(context, lang, item)

async def held_pack_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A pack tapped under the held-items question: that pack opens, and what was held goes in."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    pack_name = await _pack_of(update.effective_user.id, query.data.split(":", 1)[1])
    owner_id = await asyncio.to_thread(get_pack_owner, pack_name)
    if owner_id != update.effective_user.id:
        await query.answer(i18n.t(lang, "not_your_pack"), show_alert=True)
        return None
    await query.answer()
    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    return await _open_pack(update, context, lang, pack_name, owner_id, title,
                            adopt=LiveMessage.adopt(query.message).save())

async def held_new_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"➕ New pack" under the held-items question: the usual title prompt; what was held goes in once it is named."""
    return await newpack_start(update, context)

async def held_discard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    await query.answer()
    context.user_data.pop(HELD_KEY, None)
    context.user_data.pop(HELD_OFFER_KEY, None)
    await edit_in_place(query.message, context.bot, i18n.t(lang, "held_discarded"))

async def _add_held(update, context, lang: str) -> None:
    """Whatever was held, into the pack that was just opened, each answered beside itself."""
    held = context.user_data.pop(HELD_KEY, None) or []
    context.user_data.pop(HELD_OFFER_KEY, None)
    now = time.time()
    fresh = [i for i in held if now - i.get("at", 0) < HOLD_SECONDS]
    for item in held:
        if item not in fresh:
            await _reply_to_item(context, item, i18n.t(lang, "held_expired"))
    for item in fresh:
        try:
            await _add_item(update, context, lang, item, held=True)
        except Exception as exc:
            # One item failing must not stop the rest -- and is never left without an answer.
            logger.exception("A held item could not be added")
            record_error(exc)
            try:
                await _reply_to_item(context, item, _sticker_error_note(exc, lang))
            except Exception:
                logger.debug("Couldn't tell about a held item that failed", exc_info=True)

# A clip that does not fit a video sticker. Too long (over MAX_DURATION_S): speeds that fit it.
# Too heavy (every attempt over MAX_BYTES): lower resolution (recommended) or a lower frame rate.
# Trimming is the person's to do, for now. The choice waits in user_data under a short token,
# since callback_data holds 64 bytes; the newest VIDEO_FIT_KEEP are kept.
VIDEO_FIT_KEY = "video_fit"
VIDEO_FIT_KEEP = 10

async def _offer_video_fit(context, lang: str, item: dict, edit, fit: dict,
                           why: str, duration: "float | None") -> None:
    """Says why the clip does not fit and offers what would make it fit -- as a reply to the clip, or in place of the earlier answer to it (`edit`)."""
    token = secrets.token_hex(4)
    rows = []
    note_stat("video_fit_offered", why)
    offered = False
    if why == "long":
        speeds = video_sticker.speed_choices(duration)
        seconds = f"{duration:.1f}"
        if speeds:
            text = i18n.t(lang, "video_too_long", seconds=seconds, limit=video_sticker.MAX_DURATION_S)
            for i, speed in enumerate(speeds):
                key = "btn_speed_fit" if i == 0 else "btn_speed"
                rows.append([InlineKeyboardButton(i18n.t(lang, key, speed=f"{speed:g}"),
                                                  callback_data=f"vfit:{token}:s{speed:g}")])
        else:
            text = i18n.t(lang, "video_too_long_no_speed", seconds=seconds,
                          limit=video_sticker.MAX_DURATION_S, speed=f"{video_sticker.MAX_SPEED:g}",
                          longest=f"{video_sticker.MAX_DURATION_S * video_sticker.MAX_SPEED:g}")
    else:
        if fit.get("res") and fit.get("fps"):
            text = i18n.t(lang, "video_too_heavy_last", kb=video_sticker.MAX_BYTES // 1024)
        else:
            text = i18n.t(lang, "video_too_heavy", kb=video_sticker.MAX_BYTES // 1024)
            if not fit.get("res"):
                rows.append([InlineKeyboardButton(i18n.t(lang, "btn_lower_res"),
                                                  callback_data=f"vfit:{token}:res")])
            if not fit.get("fps"):
                rows.append([InlineKeyboardButton(i18n.t(lang, "btn_lower_fps", fps=video_sticker.LOW_FPS),
                                                  callback_data=f"vfit:{token}:fps")])
    if rows:
        offered = True
        rows.append([InlineKeyboardButton(i18n.t(lang, "btn_skip_clip"), callback_data=f"vfit:{token}:x")])
        waiting = context.user_data.setdefault(VIDEO_FIT_KEY, {})
        waiting[token] = {"item": dict(item), "fit": dict(fit), "duration": duration}
        for old in list(waiting)[:-VIDEO_FIT_KEEP]:
            waiting.pop(old, None)
    markup = InlineKeyboardMarkup(rows) if rows else None
    if edit is not None:
        await _edit_reply(context, edit, text, reply_markup=markup, item=item)
    else:
        await _reply_to_item(context, item, text, reply_markup=markup)
    return offered

async def video_fit_stale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A fit button tapped once its pack session is over (/done, /cancel, a lost session)."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.callback_query.answer(i18n.t(lang, "video_fit_expired"), show_alert=True)

async def video_fit_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of _offer_video_fit's buttons."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    _, token, choice = query.data.split(":", 2)
    entry = context.user_data.get(VIDEO_FIT_KEY, {}).pop(token, None)
    if entry is None or not isinstance(entry.get("item"), dict):
        await query.answer(i18n.t(lang, "video_fit_expired"), show_alert=True)
        return EDITING
    await query.answer()
    if choice == "x":
        note_stat("video_fit", "skipped")
        await _edit_reply(context, query.message, i18n.t(lang, "video_fit_skipped"))
        return EDITING
    fit = dict(entry.get("fit") or {})
    if choice.startswith("s"):
        try:
            fit["speed"] = float(choice[1:])
        except ValueError:
            return EDITING
    elif choice == "res":
        fit["res"] = True
    elif choice == "fps":
        fit["fps"] = True

    item = entry["item"]
    refusal = await refuse_new_work(lang, update.effective_user.id, item["chat"])
    if refusal:
        await _edit_reply(context, query.message, refusal)
        return EDITING
    await _edit_reply(context, query.message, i18n.t(lang, "converting_video"))
    try:
        raw = await _download_media(context.bot, item["file_id"])
    except Exception as exc:
        logger.warning("Couldn't fetch a clip again to make a sticker of", exc_info=True)
        record_error(exc)
        await _edit_reply(context, query.message, i18n.t(lang, "video_convert_generic_failed", error=exc))
        return EDITING
    await _make_video_sticker(update, context, lang, raw, item, fit, query.message)
    return EDITING

def _fit_label(fit: dict, lang: str) -> str:
    """What was done to make it fit, for the line that says it was added: "2.2×, lower resolution"."""
    parts = []
    if fit.get("speed"):
        parts.append(f"{fit['speed']:g}×")
    if fit.get("res"):
        parts.append(i18n.t(lang, "fit_lower_res"))
    if fit.get("fps"):
        parts.append(i18n.t(lang, "fit_lower_fps", fps=video_sticker.LOW_FPS))
    return ", ".join(parts)

async def _make_video_sticker(update, context, lang: str, raw, item: dict, fit: dict, answer) -> None:
    """Encodes the clip with the person's choices (`fit`) and adds it. Its answer -- "Converting…", then the result -- is one reply beside the clip: `answer` when there already is one (the message that held the last choices), a new one otherwise. A clip still too heavy gets the size choices there."""
    if answer is None:
        answer = await _reply_to_item(context, item, i18n.t(lang, "converting_video"), buttons=False)
    try:
        async with lifecycle.busy(item["chat"], i18n.t(lang, "restarting_send_again")):
            webm_bytes = await asyncio.to_thread(
                to_video_sticker_webm, bytes(raw), lang, fit.get("speed") or 1.0,
                bool(fit.get("res")), bool(fit.get("fps")))
    except TooBig:
        if await _offer_video_fit(context, lang, item, answer, fit, "heavy", None):
            context.user_data["batch_waiting"] = True
        return
    except ConversionError as exc:

        record_error(exc)
        kb = InlineKeyboardMarkup([sibling_bots_keyboard_row(BOT_NAME, only="convertbot")])
        await _edit_reply(context, answer, i18n.t(lang, "video_convert_failed_redirect", error=exc),
                          reply_markup=kb, item=item)
        return
    except Exception as exc:
        logger.exception("Video conversion failed")
        record_error(exc)
        await _edit_reply(context, answer, i18n.t(lang, "video_convert_generic_failed", error=exc), item=item)
        return

    input_sticker = InputSticker(sticker=webm_bytes, emoji_list=[DEFAULT_EMOJI], format="video")

    try:
        last_id = await _add_input_sticker(context, update.effective_user, input_sticker)
    except Exception as exc:
        logger.exception("Sticker set operation failed")
        record_error(exc)
        await _edit_reply(context, answer, _sticker_error_note(exc, lang), item=item)
        return
    context.user_data["last_sticker_id"] = last_id
    context.user_data["sticker_count"] = context.user_data.get("sticker_count", 0) + 1
    note_stat("sticker", "video")
    for choice in ("speed", "res", "fps"):
        if fit.get(choice):
            note_stat("video_fit", choice)
    how = _fit_label(fit, lang)
    text = (i18n.t(lang, "item_added_fit", title=_pack_title(context), emoji=DEFAULT_EMOJI, how=how) if how
            else i18n.t(lang, "item_added_video", title=_pack_title(context), emoji=DEFAULT_EMOJI))
    shown = await _edit_reply(context, answer, text, item=item)
    _remember_tag(context, item["chat"], shown.message_id, last_id)
    _remember_tag(context, item["chat"], item["msg"], last_id)

async def reject_unsupported_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "animated_not_supported"))
    return EDITING

async def import_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/import <link or name> -- copies stickers from another public Telegram pack into the pack currently being edited."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if not context.args:
        await update.message.reply_text(i18n.t(lang, "import_usage"))
        return EDITING

    source = " ".join(context.args)
    pack_source = parse_telegram_pack_source(source)
    if not pack_source:
        await update.message.reply_text(i18n.t(lang, "import_invalid_source"))
        return EDITING

    refusal = await refuse_new_work(lang, update.effective_user.id, update.effective_chat.id)
    if refusal:
        await update.message.reply_text(refusal)
        return EDITING

    await _refresh_status(context, lang, i18n.t(lang, "import_fetching", source=pack_source))
    try:
        stickers = await fetch_importable_stickers(context.bot, pack_source, lang)
    except PackImportError as exc:
        await _refresh_status(context, lang, str(exc) + problems.code_line("ST-IMPORT"))
        return EDITING

    added, skipped, failed = 0, 0, 0
    async with lifecycle.busy(update.effective_chat.id, i18n.t(lang, "restarting_send_again")):
        for sticker in stickers[:MAX_IMPORT_PER_RUN]:
            input_sticker = sticker_to_input_sticker(sticker)
            if input_sticker is None:
                skipped += 1
                continue
            try:
                await _add_input_sticker(context, update.effective_user, input_sticker, want_file_id=False)
                context.user_data["sticker_count"] = context.user_data.get("sticker_count", 0) + 1
                added += 1
                await asyncio.sleep(0.3)
            except Exception:
                logger.exception("Import: failed to add one sticker")
                failed += 1

    await _remember_last_sticker(context)
    summary = i18n.t(lang, "import_summary_head", added=added, source=pack_source)
    if skipped:
        summary += i18n.t(lang, "import_summary_skipped", skipped=skipped)
    if failed:
        summary += i18n.t(lang, "import_summary_failed", failed=failed)
    summary += i18n.t(lang, "import_summary_tail")
    await _refresh_status(context, lang, summary)
    return EDITING

async def import_standalone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Top-level /import fallback for when the user isn't currently editing a pack."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "import_standalone_hint"))

async def done_standalone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Same idea for /done."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "done_standalone_hint"),
                                    **await _with_buttons(context, update.effective_chat, update.effective_user.id, lang))

async def receive_whatsapp_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A .zip/.wastickers file sent while editing -- treated as a WhatsApp sticker pack export and bulk-imported."""
    msg = update.message
    lang = await i18n.get_lang(update.effective_user.id, context)

    refusal = await refuse_new_work(lang, update.effective_user.id, msg.chat_id)
    if refusal:
        await msg.reply_text(refusal)
        return EDITING

    try:
        raw = await _download_media(context.bot, msg.document.file_id)
    except Exception as exc:
        logger.warning("Couldn't fetch a WhatsApp sticker pack", exc_info=True)
        record_error(exc)
        await _refresh_status(context, lang, i18n.t(lang, "video_convert_generic_failed", error=exc))
        return EDITING

    await _refresh_status(context, lang, i18n.t(lang, "whatsapp_reading"))
    try:
        items = await asyncio.to_thread(parse_whatsapp_zip, raw, lang)
    except PackImportError as exc:
        await _refresh_status(context, lang, str(exc) + problems.code_line("ST-IMPORT"))
        return EDITING

    added, failed = 0, 0
    async with lifecycle.busy(msg.chat_id, i18n.t(lang, "restarting_send_again")):
        for png_bytes, emojis in items:
            input_sticker = InputSticker(sticker=png_bytes, emoji_list=emojis[:20], format="static")
            try:
                await _add_input_sticker(context, update.effective_user, input_sticker, want_file_id=False)
                context.user_data["sticker_count"] = context.user_data.get("sticker_count", 0) + 1
                added += 1
                await asyncio.sleep(0.3)
            except Exception:
                logger.exception("WhatsApp import: failed to add one sticker")
                failed += 1

    await _remember_last_sticker(context)
    summary = i18n.t(lang, "whatsapp_summary_head", added=added)
    if failed:
        summary += i18n.t(lang, "import_summary_failed", failed=failed)
    summary += i18n.t(lang, "import_summary_tail")
    await _refresh_status(context, lang, summary)
    return EDITING

def _retag_target(update: Update, context) -> "str | None | bool":
    """The sticker an emoji message is for: the one made from the message it replies to -- the ✅ answer, or the picture or sticker the person sent (TAGS_KEY). None when it replies to nothing; False when it replies to a message that made no sticker this bot remembers (never "the last one" then: that would retag the wrong sticker)."""
    replied = update.message.reply_to_message
    if replied is None:
        return None
    key = _tag_key(update.effective_chat.id, replied.message_id)
    return (context.user_data.get(TAGS_KEY) or {}).get(key) or False

async def retag_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Emoji sent as a reply to one of the ✅ answers, with no pack open: that sticker is retagged all the same."""
    text = update.message.text or ""
    if not looks_like_emoji_message(text):
        return await unrecognized_message(update, context)
    lang = await i18n.get_lang(update.effective_user.id, context)
    target = _retag_target(update, context)
    buttons = await _with_buttons(context, update.effective_chat, update.effective_user.id, lang)
    if not target:
        # An emoji reply to a message that made no sticker this bot remembers: say so, rather
        # than "Not sure what that's for".
        await update.message.reply_text(i18n.t(lang, "retag_unknown"), **buttons)
        return
    emojis = split_emoji(text)
    try:
        await context.bot.set_sticker_emoji_list(sticker=target, emoji_list=emojis)
        await update.message.reply_text(i18n.t(lang, "retagged_success", emojis=" ".join(emojis)), **buttons)
    except Exception as exc:
        await update.message.reply_text(i18n.t(lang, "retag_failed", error=exc))

async def maybe_emoji_override(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = await i18n.get_lang(update.effective_user.id, context)

    buttons = await _with_buttons(context, update.effective_chat, update.effective_user.id, lang)
    if not looks_like_emoji_message(text):
        await update.message.reply_text(i18n.t(lang, "not_emoji_message"), **buttons)
        return EDITING

    target = _retag_target(update, context)
    if target is False:
        await update.message.reply_text(i18n.t(lang, "retag_unknown"), **buttons)
        return EDITING
    last_sticker_id = target or context.user_data.get("last_sticker_id")
    if not last_sticker_id:
        await update.message.reply_text(i18n.t(lang, "no_sticker_to_tag"), **buttons)
        return EDITING

    emojis = split_emoji(text)
    try:
        await context.bot.set_sticker_emoji_list(sticker=last_sticker_id, emoji_list=emojis)
        await update.message.reply_text(i18n.t(lang, "retagged_success", emojis=" ".join(emojis)), **buttons)
    except Exception as exc:
        await update.message.reply_text(i18n.t(lang, "retag_failed", error=exc))

    return EDITING

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    pack_name = context.user_data.get("target_pack")
    if not pack_name:
        await update.message.reply_text(i18n.t(lang, "nothing_added_yet"))
        return EDITING
    count = context.user_data.get("sticker_count", 0)
    title = context.user_data.get("title") or pack_name
    await _end_status(
        context,
        i18n.t(lang, "done_success", title=title, count=count, pack_name=pack_name),
    )

    nudge = await maybe_donation_nudge(
        update.effective_user.id, lang, context, update.effective_chat.id)
    if nudge:
        await update.message.reply_text(nudge)

    _fresh_session(context)
    return ConversationHandler.END

async def convert_redirect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/convert lives in @ConvertBot now -- keep the command here as a friendly redirect for anyone still typing it out of habit."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    kb = InlineKeyboardMarkup([sibling_bots_keyboard_row(BOT_NAME, only="convertbot")])
    await update.message.reply_text(
        i18n.t(lang, "convert_redirect"),
        reply_markup=kb,
    )

PACK_CANCEL_KEYS = ("rename", "editing", "newpack")

async def _cancel_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> list[CancelItem]:
    """Everything this bot could be waiting on, named well enough to choose between."""
    items = cancel_items(context, lang)
    if context.user_data.get("rename_pack"):
        pack = context.user_data["rename_pack"]
        title = await asyncio.to_thread(get_pack_title, pack) or pack
        items.append(CancelItem("rename",
                                i18n.t(lang, "cancel_item_rename", title=title),
                                i18n.t(lang, "cancel_button_rename")))
    elif _has_status(context):
        title = context.user_data.get("title") or i18n.t(lang, "status_default_title")
        items.append(CancelItem("editing",
                                i18n.t(lang, "cancel_item_editing", title=title),
                                i18n.t(lang, "cancel_button_editing")))
    elif context.user_data.get("mode"):
        items.append(CancelItem("newpack",
                                i18n.t(lang, "cancel_item_new_pack"),
                                i18n.t(lang, "cancel_button_new_pack")))
    return items

async def _apply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, keys):
    """Stop the chosen things; report what they were and whether a pack went with them."""
    items = {item.key: item for item in await _cancel_items(update, context, lang)}
    stopped, pack_stopped = [], False
    for chosen in keys:
        item = items.get(chosen)
        if item is None:
            continue
        if chosen == "editing":
            # finish_cancel says what stopped; a second "❌ Cancelled." under it was noise.
            for key in (STATUS_KEY, "sticker_count", "status_intro", *BATCH_KEYS):
                context.user_data.pop(key, None)
        if chosen in PACK_CANCEL_KEYS:
            pack_stopped = True
            stopped.append(item.label)
        elif cancel_shared_item(context, lang, chosen):
            stopped.append(item.label)

    if pack_stopped:
        keep = {key: context.user_data[key] for key in KEEP_ACROSS_SESSIONS if key in context.user_data}
        keep["lang"] = lang
        if "donate_custom_currency" in context.user_data:
            keep["donate_custom_currency"] = context.user_data["donate_custom_currency"]
        reset_user_state(context, keep)
    return stopped, pack_stopped

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks which of the things it is waiting on to stop, and stops nothing until the answer comes back."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    items = await _cancel_items(update, context, lang)
    if await ask_cancel_choice(update, context, items, lang):
        return None
    buttons = await _with_buttons(context, update.effective_chat, update.effective_user.id, lang)
    await finish_cancel(update, context, lang, [], keyboard=buttons.get("reply_markup"))
    return ConversationHandler.END

async def cancel_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of /cancel's buttons."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    key = cancel_choice_key(update)
    await query.answer()
    if key == CANCEL_PICK_NONE:
        await keep_going(update, context, lang)
        return None

    if key == CANCEL_PICK_ALL:
        keys = [item.key for item in await _cancel_items(update, context, lang)]
    else:
        keys = [key]
    stopped, pack_stopped = await _apply_cancel(update, context, lang, keys)
    buttons = await _with_buttons(context, update.effective_chat, update.effective_user.id, lang)
    await finish_cancel_choice(update, context, lang, stopped, keyboard=buttons.get("reply_markup"))
    return ConversationHandler.END if pack_stopped else None

async def unrecognized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Only ever reached with no active /newpack or pack-editing session -- while one's active, the conversation's own state handlers (e.g."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    buttons = await _with_buttons(context, update.effective_chat, update.effective_user.id, lang)
    if looks_like_emoji_message(update.message.text or ""):
        await update.message.reply_text(i18n.t(lang, "no_sticker_to_tag"), **buttons)
        return
    await update.message.reply_text(i18n.t(lang, "unrecognized"), **buttons)

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "unknown_command"))

async def _post_init(application):
    await tune_runtime(application)

    await lifecycle.on_start(BOT_NAME)
    await publish_commands(application, BOT_COMMANDS, ADMIN_COMMANDS, ADMIN_IDS)
    await publish_profile(application)

async def _post_stop(application):

    await lifecycle.on_stop(application)
    await flush_on_shutdown(application)

def main():
    if not BOT_TOKEN or not BOT_USERNAME:
        raise SystemExit("Set SBOT_TOKEN and SBOT_USERNAME environment variables first.")

    init_db()

    builder = (
        ApplicationBuilder().token(BOT_TOKEN)
        .post_init(_post_init).post_stop(_post_stop)
    )

    state = lifecycle.persistence()
    if state is not None:
        builder = builder.persistence(state)
    if LOCAL_BOT_API_URL:
        base = LOCAL_BOT_API_URL.rstrip("/")
        builder = (
            builder
            .base_url(f"{base}/bot")
            .base_file_url(f"{base}/file/bot")
            .local_mode(LOCAL_BOT_API_MODE)
        )
        logger.info(
            "Using local Bot API server at %s (local_mode=%s) -- 20 MB download / 50 MB "
            "upload ceilings are lifted.", base, LOCAL_BOT_API_MODE,
        )
    app = builder.build()

    lifecycle.install(app, BOT_NAME, ADMIN_IDS)
    app.add_error_handler(error_handler)
    attach_problem_reports(app)

    app.add_handler(TypeHandler(Update, track_activity), group=-4)

    attach_flood_gate(app, ADMIN_IDS)

    app.add_handler(MessageHandler((filters.TEXT | filters.REPLY) & ~filters.COMMAND,
                                   awaited_text_received), group=-1)

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("newpack", newpack_start),
            MessageHandler(filters.ChatType.PRIVATE & PACK_BUTTON_TEXT, pack_button),
            MessageHandler(filters.ChatType.PRIVATE & filters.Text(_new_pack_labels()), newpack_start),
            CallbackQueryHandler(held_pack_chosen, pattern="^hp:"),
            CallbackQueryHandler(held_new_pack, pattern=r"^hp\+$"),
            CallbackQueryHandler(newpack_start, pattern="^menu_newpack$"),
            CallbackQueryHandler(pack_chosen, pattern="^pack:"),
            CallbackQueryHandler(rename_start, pattern="^packrename:"),

            CallbackQueryHandler(language_chosen, pattern="^setlang:"),

            CallbackQueryHandler(cancel_choice_callback, pattern="^cancelpick:"),
            CommandHandler("en", set_language_en),
            CommandHandler("uz", set_language_uz),
            CommandHandler("rus", set_language_rus),

            CommandHandler("deletemydata", delete_my_data_command),
            CallbackQueryHandler(delete_my_data_chosen, pattern="^" + ERASE_PREFIX),
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _needs_session(receive_title))],
            RENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_title)],
            EDITING: [
                CallbackQueryHandler(_needs_session(confirm_remove_last_sticker), pattern="^confirmremove:"),
                CallbackQueryHandler(_needs_session(video_fit_chosen), pattern="^vfit:"),
                MessageHandler(
                    filters.Document.FileExtension("zip") | filters.Document.FileExtension("wastickers"),
                    _needs_session(receive_whatsapp_import),
                ),
                MessageHandler(
                    filters.PHOTO | filters.Document.IMAGE | filters.Sticker.STATIC,
                    _needs_session(receive_media),
                ),
                MessageHandler(
                    filters.ANIMATION | filters.VIDEO | filters.Document.VIDEO | filters.Sticker.VIDEO,
                    _needs_session(receive_video_media),
                ),
                MessageHandler(
                    filters.Sticker.ANIMATED,
                    _needs_session(reject_unsupported_sticker),
                ),
                CommandHandler("import", _needs_session(import_command)),
                CommandHandler("done", _needs_session(done)),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    _needs_session(maybe_emoji_override),
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start)],

        name="stickerbot_pack_editing",
        persistent=lifecycle.persistent(),

        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(video_fit_stale, pattern="^vfit:"))
    app.add_handler(CallbackQueryHandler(held_discard, pattern="^hp-$"))

    app.add_handler(CallbackQueryHandler(language_chosen, pattern="^setlang:"))
    app.add_handler(CallbackQueryHandler(cancel_choice_callback, pattern="^cancelpick:"))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("en", set_language_en))
    app.add_handler(CommandHandler("uz", set_language_uz))
    app.add_handler(CommandHandler("rus", set_language_rus))

    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler("paysupport", paysupport_command))
    app.add_handler(CallbackQueryHandler(problem_report_callback, pattern=r"^rpt"))
    app.add_handler(CommandHandler("deletemydata", delete_my_data_command))
    app.add_handler(CallbackQueryHandler(delete_my_data_chosen, pattern="^" + ERASE_PREFIX))
    app.add_handler(CommandHandler("mypacks", mypacks_command))
    app.add_handler(CommandHandler("addsticker", addsticker_command))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CommandHandler("fullhelp", full_help_command(build_help_text, help_rows, HELP_PAGES)))
    app.add_handler(CallbackQueryHandler(help_toggle(build_help_text, help_rows, HELP_PAGES),
                                         pattern=HELP_TOGGLE_PATTERN))

    app.add_handler(CallbackQueryHandler(help_page_button(HELP_PAGES), pattern=HELP_PAGE_PATTERN))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("whomade", whomade_command))
    app.add_handler(CommandHandler("whois", whois_command))
    app.add_handler(CommandHandler("messageas", messageas_command))
    app.add_handler(CommandHandler("dbdump", dbdump_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("crashtest", crashtest_command))

    app.add_handler(CommandHandler("import", import_standalone))
    app.add_handler(CommandHandler("done", done_standalone))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CallbackQueryHandler(menu_mypacks, pattern="^menu_mypacks$"))
    app.add_handler(CallbackQueryHandler(menu_help, pattern="^menu_help$"))
    app.add_handler(CallbackQueryHandler(menu_start, pattern="^menu_start$"))
    app.add_handler(CallbackQueryHandler(pack_detail, pattern="^packopen:"))
    app.add_handler(CallbackQueryHandler(coedit_menu, pattern="^packcoedit:"))
    app.add_handler(CallbackQueryHandler(coedit_reset, pattern="^cotoken_reset:"))
    app.add_handler(CallbackQueryHandler(delete_pack_start, pattern="^packdel:"))
    app.add_handler(CallbackQueryHandler(delete_pack_confirm1, pattern="^packdelconfirm1:"))
    app.add_handler(CallbackQueryHandler(delete_pack_confirm2, pattern="^packdelconfirm2:"))
    app.add_handler(CommandHandler("convert", convert_redirect_command))

    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CallbackQueryHandler(donate_amount_chosen, pattern="^donate:"))
    app.add_handler(CallbackQueryHandler(donate_fiat_amount_chosen, pattern="^donatefiat:"))
    app.add_handler(CallbackQueryHandler(donate_custom_button_chosen, pattern="^donatecustom:"))
    app.add_handler(PreCheckoutQueryHandler(donation_precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, donation_payment_callback))

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & BATCH_MEDIA, media_without_pack))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND, retag_reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unrecognized_message))

    family_link.attach(app, BOT_NAME, "StickerBot", START_TIME)
    attach_maintenance(app)

    logger.info("Bot starting (polling)...")

    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY, Update.PRE_CHECKOUT_QUERY],
    ))

if __name__ == "__main__":
    main()

# ─── module: convert_bot.bot ─────────────────────────────────────────────────
"""Standalone file converter bot -- images/video/audio, priced in Telegram Stars."""
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

try:
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
import shared_features
from live_message import LiveMessage, edit_in_place
from db import (
    init_db,
    record_star_invoice,
    update_star_transaction,
    get_star_ledger,
    dump_database_csv_zip,
    count_active_users_since,
    get_user_language,
    set_user_language,
)
import big_files
import convert_utils
import raw_convert
import ocr_convert
import formats
import jobs
from convert_runner import ConvertRunner, download_card
from convert_utils import (
    BOT_API_MAX_MB,
    FREE_UNDER_MB,
    gif_is_animated,
    max_file_mb_in,
    price_for_size,
    price_for_job,
    document_pages,
    price_tiers_text,
    ConversionError as ConvertError,
)
from shared_features import (
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
    problem_report_callback,
    refuse_new_work,
    attach_flood_gate,
    attach_promo_claim,
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
    balance_command,
    STARS_SANDBOX,
    donate_command,
    donate_amount_chosen,
    donate_fiat_amount_chosen,
    donate_custom_button_chosen,
    awaited_text_received,
    feedback_command,
    HELP_PAGE_PATTERN,
    HELP_TOGGLE_PATTERN,
    NO_PREVIEW,
    full_help_command,
    help_keyboard,
    help_page_button,
    help_page_name,
    help_page_text,
    help_toggle,
    wants_full_help,
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

BOT_USERNAME = (os.environ.get("CBOT_USERNAME") or "").strip().lstrip("@") or None

ADMIN_IDS = {int(x) for x in os.environ.get("CBOT_ADMIN_ID", "").split(",") if x.strip()}

LOCAL_BOT_API_URL = os.environ.get("LOCAL_BOT_API_URL")
LOCAL_BOT_API_MODE = os.environ.get("LOCAL_BOT_API_MODE", "true").lower() == "true"

BOT_NAME = "convertbot"

POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "30"))

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
async def _deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """How an owner-only command answers everybody else: exactly the way a misspelling does."""
    await unknown_command(update, context)

UPLOAD_DIR = Path(os.environ.get("CONVERT_UPLOAD_DIR") or (Path(tempfile.gettempdir()) / "convertbot"))
PENDING_TTL_SECONDS = int(os.environ.get("CONVERT_PENDING_TTL_SECONDS", "900"))

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
    """Clears the conversion state and deletes whatever it was holding."""
    state = context.user_data.pop("convert", None)

    busy = jobs.active_paths()
    for path in (state or {}).get("paths", []):
        if str(path) not in busy:
            _unlink(path)

def _sweep_uploads(max_age_seconds: float = PENDING_TTL_SECONDS, keep=(), busy_stems=()) -> int:
    """Anything older than the TTL is gone: either the user never chose a format, or the process that was handling it died."""
    if not UPLOAD_DIR.is_dir():
        return 0

    sweep_all = max_age_seconds <= 0
    cutoff = time.time() - max_age_seconds

    job_cutoff = time.time() - max(max_age_seconds, jobs.TIME_LIMIT_S + 300)
    removed = 0
    for path in UPLOAD_DIR.iterdir():
        try:
            if str(path) in keep:

                continue
            if any(path.name == stem or path.name.startswith((stem + "-", stem + "."))
                   for stem in busy_stems):
                continue
            made_by_a_job = path.is_dir() or "-source." in path.name
            if path.is_file() and (sweep_all or path.stat().st_mtime < (job_cutoff if made_by_a_job else cutoff)):
                path.unlink()
                removed += 1
            elif (path.is_dir() and not path.is_symlink() and path.name.endswith("-contents")
                  and (sweep_all or path.stat().st_mtime < job_cutoff)):

                convert_utils.remove_tree(path)
                if not path.exists():
                    removed += 1
        except OSError:
            continue
    return removed

async def _sweep_uploads_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    removed = await asyncio.to_thread(
        _sweep_uploads, max_age_seconds=PENDING_TTL_SECONDS, keep=jobs.active_paths(),
        busy_stems=jobs.active_stems())
    if removed:
        logger.info("Swept %d abandoned upload(s).", removed)

async def _conversions_in_flight_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Keeps this process's paid conversions stamped, and refunds those of a process killed before it could -- see jobs.HOLD_STALE_S."""
    try:
        refunded = await _runner(context.application).keep_alive_and_recover()
    except Exception:
        logger.debug("Could not check conversions in flight", exc_info=True)
        return
    if refunded:
        logger.warning("Refunded %d conversion(s) lost to a restart.", refunded)

def build_help_text(lang: str, full: bool = False) -> str:
    """The short version unless asked for the long one -- the family's help template (shared_features, "/help in two lengths")."""
    if not full:
        text = i18n.t(lang, "help_brief").rstrip("\n")
    else:
        text = i18n.t(lang, "help_text", pricing=price_tiers_text(lang)).rstrip("\n")
    blurb = sibling_bots_blurb(BOT_NAME, lang)
    return text + "\n\n" + blurb if blurb else text

def _help_page_convert(lang: str) -> str:
    return i18n.t(lang, "helppage_convert",
                  max_mb=convert_utils.MAX_FILE_MB, pricing=price_tiers_text(lang),
                  free_mb=convert_utils.FREE_UNDER_MB, batch=formats.MAX_BATCH,
                  ocr_pages=ocr_convert.OCR_MAX_PAGES, ocr_free_pages=ocr_convert.OCR_FREE_PAGES,
                  minutes=max(1, PENDING_TTL_SECONDS // 60), least=convert_utils.least_paid_price())

def _help_topup_ladder(lang: str) -> tuple[str, str]:
    """(the ladder as lines, the sentence about the bonus) -- walked the way family_link.quote_credit prices a payment, from family_link.TOPUP_LADDER as it is now."""

    per_star = family_link.TOPUP_MULTIPLIER
    rate = f"{per_star:g}"
    if not family_link.TOPUP_LADDER:
        return i18n.t(lang, "helppage_recharge_flat", rate=rate), ""
    lines = []
    for number, (stars, multiplier) in enumerate(family_link.TOPUP_LADDER):
        extra = per_star * multiplier - per_star
        split = i18n.t(lang, "helppage_recharge_bonus_part", rate=rate, bonus=f"{extra:g}") if extra > 0 else ""
        lines.append(i18n.t(lang, "helppage_recharge_step_next" if number else "helppage_recharge_step_first",
                            stars=stars, each=f"{per_star * multiplier:g}", split=split))
    lines.append(i18n.t(lang, "helppage_recharge_step_after", rate=rate))
    return "\n".join(lines), i18n.t(lang, "helppage_recharge_bonus_rule", rate=rate,
                                    days=family_link.BONUS_EXPIRY_DAYS)

def _help_page_recharge(lang: str) -> str:
    ladder, bonus_rule = _help_topup_ladder(lang)
    quote = family_link.quote_credit(0, shared_features.DONATE_STAR_OPTIONS[0])
    if quote["bonus"] > 0:
        example = i18n.t(lang, "helppage_recharge_example", stars=quote["stars"], total=quote["total"],
                         base=quote["base"], bonus=quote["bonus"])
    else:
        example = i18n.t(lang, "helppage_recharge_example_flat", stars=quote["stars"], total=quote["total"])
    text = i18n.t(lang, "helppage_recharge", options=" · ".join(str(n) for n in shared_features.DONATE_STAR_OPTIONS),
                  ladder=ladder, bonus_rule=bonus_rule, example=example)

    return text if bonus_rule else text.replace(ladder + "\n\n", ladder + "\n", 1)

def _help_page_balance(lang: str) -> str:
    quote = family_link.quote_credit(0, shared_features.DONATE_STAR_OPTIONS[0])
    if quote["bonus"] > 0:
        example = i18n.t(lang, "helppage_balance_example", stars=quote["stars"], base=quote["base"],
                         bonus=quote["bonus"])
    else:
        example = i18n.t(lang, "helppage_balance_example_one", stars=quote["stars"], total=quote["total"])
    return i18n.t(lang, "helppage_balance", rows=shared_features.BALANCE_RECENT_ROWS,
                  days=family_link.BONUS_EXPIRY_DAYS, example=example)

HELP_PAGES = {"convert": _help_page_convert, "recharge": _help_page_recharge, "balance": _help_page_balance}
HELP_ALIASES = {"donate": "recharge", "mystars": "balance"}

BOT_COMMANDS = [

    BotCommand("start", "What I do, and how to start"),
    BotCommand("language", "Choose your language / Tilni tanlash / Выбрать язык"),
    BotCommand("convert", "Convert a file — or just send me one"),
    BotCommand("formats", "Every format I read and write"),
    BotCommand("cancel", "Stop whatever I am waiting for"),
    BotCommand("help", "Everything I can do"),
    BotCommand("feedback", "Suggest something, or report a problem"),
    BotCommand("balance", "Your ⚡ credit, and where it went"),
    BotCommand("recharge", "Top up your ⚡ credit"),
    BotCommand("paysupport", "Trouble with a payment"),
    BotCommand("privacy", "What I keep about you"),
    BotCommand("terms", "What I may be used for"),
    BotCommand("deletemydata", "Delete everything I hold on you"),
]

ADMIN_COMMANDS = [
    BotCommand("status", "🔒 Uptime, host, errors, active users"),
    BotCommand("stars", "🔒 The Stars ledger: paid, free and refunded"),
    BotCommand("messageas", "🔒 messageas <user_id> <text> — DM as this bot"),
    BotCommand("dbdump", "🔒 This bot's tables as a zip of CSVs"),
]

def help_rows(lang: str) -> list:
    """What sits under /start and /help besides the full-guide button."""
    return [sibling_bots_keyboard_row(BOT_NAME)]

async def _reply(update: Update, text: str, **kwargs):
    """Works whether the update came from a command or a button tap."""
    if update.message:
        return await LiveMessage.reply_to(update.message, text, **kwargs)
    return await edit_in_place(update.callback_query.message, update.get_bot(), text, **kwargs)

async def _continue_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    await _reply(
        update,
        i18n.t(lang, "start_greeting") + build_help_text(lang),
        reply_markup=help_keyboard(lang, False, help_rows(lang), HELP_PAGES),
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start prints the instructions -- except the very first one, which asks for a language first."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    if lang is None:
        await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
        return
    context.user_data["lang"] = lang
    await _continue_start(update, context, lang)

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/language -- the picker on demand, which is what /start used to be."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)

    if lang:
        context.user_data["lang"] = lang
    await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard(lang))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The instructions on their own."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    page = help_page_name(context, HELP_PAGES, HELP_ALIASES)
    if page:
        await update.message.reply_text(help_page_text(lang, HELP_PAGES, page),
                                        link_preview_options=NO_PREVIEW)
        return
    full = wants_full_help(context)
    await update.message.reply_text(build_help_text(lang, full=full),
                                    reply_markup=help_keyboard(lang, full, help_rows(lang), HELP_PAGES))

async def _apply_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """The single path every language change goes through -- /en, /uz, /rus and a tap on the picker alike -- so all four end the same way: with the instructions, printed in the language just chosen."""
    await asyncio.to_thread(set_user_language, update.effective_user.id, lang)
    context.user_data["lang"] = lang

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

def _ext_of(filename: str | None, fallback: str) -> str:
    """The part after the last dot, normalised, or `fallback`."""
    compound = formats.compound_extension(filename)
    if compound:
        return compound
    if filename and "." in filename:
        return formats.normalise(_safe_ext(filename.rsplit(".", 1)[-1])) or fallback
    return fallback

def _ext_of_file(file_obj, fallback: str) -> str:
    """`_ext_of` on the file's name; a file sent with no name (a GIF from Telegram's own picker, say) falls back to its MIME type, then to `fallback`."""
    ext = _ext_of(getattr(file_obj, "file_name", None), "")
    if ext:
        return ext
    import mimetypes
    guessed = mimetypes.guess_extension(getattr(file_obj, "mime_type", None) or "")
    guessed = formats.normalise(guessed) if guessed else ""
    if guessed and formats.is_supported_source(guessed):
        return guessed
    return fallback

async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(
        i18n.t(lang, "convert_start_prompt", max_mb=convert_utils.MAX_FILE_MB, pricing=price_tiers_text(lang)),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(i18n.t(lang, "btn_what_formats"), callback_data="fmtall"),
        ]]),
    )

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
    writes = ", ".join(i18n.target_label(lang, ext) for ext in formats.supported_targets(category))
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
    """What one named format becomes, or None if that was not a format."""
    ext = formats.find_format(word)
    if not ext:
        return None
    targets = formats.targets_for(ext)
    if not targets:
        return i18n.t(lang, "formats_lookup_none", ext=ext)
    return i18n.t(
        lang, "formats_lookup", ext=ext,
        category=i18n.t(lang, f"category_{formats.category_of(ext)}"),
        targets=", ".join(i18n.target_label(lang, target) for target in targets),
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

async def _cancel_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> list[CancelItem]:
    """Everything this bot could be waiting on: an uploaded file still waiting for you to pick a format, and the shared donation prompt."""
    items = cancel_items(context, lang)

    for job in jobs.jobs_for(update.effective_user.id):
        items.append(CancelItem(
            f"job_{job.id}",
            i18n.t(lang, "cancel_item_job_running" if job.state == "running" else "cancel_item_job_queued",
                   target=i18n.target_label(lang, job.target_ext), src=job.src_ext.upper(),
                   size=f"{job.size / 1024 / 1024:.1f}"),
            i18n.t(lang, "cancel_button_job", target=i18n.target_label(lang, job.target_ext)),
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
    """Asks which of the things it is waiting on to stop, then stops that one."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if await ask_cancel_choice(update, context, await _cancel_items(update, context, lang), lang):
        return
    await finish_cancel(update, context, lang, [])

async def cancel_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of /cancel's buttons."""
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
    """The Cancel button under the format list -- the same thing /cancel does, without making anyone type it."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    _discard_pending(context)
    await query.answer()
    await edit_in_place(query.message, context.bot, i18n.t(lang, "cancelled"))

BATCH_WAIT_SECONDS = float(os.environ.get("CONVERT_BATCH_WAIT_SECONDS") or 2.0)

def _batch_job_name(chat_id: int, group_id: str) -> str:
    return f"batch:{chat_id}:{group_id}"

def _too_large_text(lang: str, size: int, limit_mb: int) -> str:
    """Why a file this size is refused here, which depends on whose limit it is: Telegram's (the Bot API's 20 MB, when nothing lifts it), this chat's (over MTProto big files come in private chats only), or this bot's own."""
    if limit_mb < convert_utils.MAX_FILE_MB:
        return i18n.t(lang, "file_too_large_in_group", limit=limit_mb, max_mb=convert_utils.MAX_FILE_MB)
    if limit_mb <= BOT_API_MAX_MB and not LOCAL_BOT_API_URL:
        return i18n.t(lang, "file_too_large_download", max_mb=limit_mb)
    return i18n.t(lang, "file_too_large_convert", size=f"{size / 1024 / 1024:.1f}", max_mb=limit_mb)

_PROGRESS_EVERY_S = 3.0

_CARD_FROM_BYTES = 2 * 1024 * 1024

def _download_progress(context, status, lang: str):
    """A progress(done, total) that redraws the download card, at most every _PROGRESS_EVERY_S."""
    began = time.monotonic()
    last = {"at": 0.0, "text": ""}

    async def progress(done: int, total: int) -> None:
        if status is None or not total:
            return
        now = time.monotonic()
        if now - last["at"] < _PROGRESS_EVERY_S:
            return
        text = download_card(lang, done, total, now - began)
        if text != last["text"]:
            last.update(at=now, text=text)
            await status.set(context.bot, text)
    return progress

# Most likely cause of the "Timed out" a first try used to end in, where the second try worked:
# getFile on a file the Bot API server has not seen yet makes that server fetch the whole file
# from Telegram's storage before it answers, which can take longer than the library's 5 s default.
# The report kept no traceback, so the log now says which step failed (see _download_bot_api).
GET_FILE_READ_S = float(os.environ.get("CONVERT_GET_FILE_READ_S") or 90)
DOWNLOAD_TRIES = 3

class _Interrupted(Exception):
    """A streamed download that broke off; worth another try."""

def _worth_another_try(exc: BaseException) -> bool:
    """A timeout or a dropped connection, not a refusal: the next try usually just works."""
    from telegram.error import BadRequest, NetworkError, RetryAfter
    if isinstance(exc, BadRequest):
        return False
    return isinstance(exc, (NetworkError, RetryAfter, _Interrupted, asyncio.TimeoutError))

async def _download_bot_api(context, file_obj, path, declared_size: int, status, lang: str) -> None:
    """A file within the Bot API's 20 MB, with up to DOWNLOAD_TRIES tries when the network is what failed."""
    for attempt in range(1, DOWNLOAD_TRIES + 1):
        try:
            await _download_bot_api_once(context, file_obj, path, declared_size, status, lang)
            return
        except Exception as exc:
            if attempt == DOWNLOAD_TRIES or not _worth_another_try(exc):
                logger.warning("Download gave up after %d try(s) at %s: %s", attempt,
                               getattr(exc, "mumu_step", "getFile"), type(exc).__name__)
                if isinstance(exc, _Interrupted):
                    raise ConvertError(str(exc)) from None
                raise
            wait = 2.0 * attempt
            retry_after = getattr(exc, "retry_after", None)
            if retry_after is not None:
                seconds = retry_after.total_seconds() if isinstance(retry_after, timedelta) else float(retry_after)
                wait = min(max(wait, seconds + 0.5), 30.0)
            logger.info("Download try %d of %d failed (%s); trying again in %.0f s",
                        attempt, DOWNLOAD_TRIES, type(exc).__name__, wait)
            await asyncio.sleep(wait)

async def _download_bot_api_once(context, file_obj, path, declared_size: int, status, lang: str) -> None:
    """One try: getFile, then the file itself, streamed when it is big enough for the card to move."""
    tg_file = await context.bot.get_file(file_obj.file_id, read_timeout=GET_FILE_READ_S)
    try:
        await _fetch_file(tg_file, path, declared_size, status, context, lang)
    except Exception as exc:
        try:
            exc.mumu_step = "the download"
        except Exception:
            pass
        raise

async def _fetch_file(tg_file, path, declared_size: int, status, context, lang: str) -> None:
    url = getattr(tg_file, "file_path", None) or ""
    # About 100 KB/s at worst, and never under a minute.
    read_s = max(60.0, declared_size / 100_000)
    if (status is None or LOCAL_BOT_API_URL or not url.startswith("https://")
            or declared_size < _CARD_FROM_BYTES):
        await tg_file.download_to_drive(custom_path=path, read_timeout=read_s, write_timeout=60,
                                        connect_timeout=30)
        return
    import httpx
    progress = _download_progress(context, status, lang)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=60.0)) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length") or declared_size or 0)
                done = 0
                with open(path, "wb") as handle:
                    async for chunk in response.aiter_bytes(256 * 1024):
                        handle.write(chunk)
                        done += len(chunk)
                        await progress(done, total)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:
            raise _Interrupted(f"Telegram's file server answered {exc.response.status_code}") from None
        raise ConvertError(f"Telegram's file server answered {exc.response.status_code}") from None
    except httpx.HTTPError as exc:
        raise _Interrupted(f"the download was interrupted ({type(exc).__name__})") from None

async def _download_big(context, msg, path, declared_size: int, status, lang: str) -> None:
    """A file over the Bot API's 20 MB, fetched over MTProto -- big_files.py. Raises what big_files.download raises."""
    progress = _download_progress(context, status, lang)
    try:
        await big_files.download(msg.chat_id, msg.message_id, path, declared_size, progress)
    except big_files.Stalled:
        raise ConvertError(i18n.t(lang, "download_stalled", seconds=round(big_files.STALL_S))) from None
    except asyncio.TimeoutError:
        raise ConvertError(i18n.t(lang, "download_too_slow",
                                  minutes=big_files.transfer_limit_s(declared_size) // 60)) from None

async def convert_receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    msg = update.message
    # An animation comes with `document` set too (Bot API backward compatibility), so it is
    # looked at first: a Telegram GIF is an MP4 with no sound and often has no file name.
    if msg.animation:
        file_obj = msg.animation
        ext = _ext_of_file(file_obj, "mp4")
    elif msg.document:
        file_obj = msg.document
        ext = _ext_of_file(file_obj, "")
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
    else:
        return

    if not ext:
        await msg.reply_text(
            i18n.t(lang, "unknown_extension"), reply_markup=_what_formats_keyboard(lang),
        )
        return
    if not formats.is_supported_source(ext):
        # Said before the download, not after it: nothing is fetched that can't be converted.
        await msg.reply_text(
            i18n.t(lang, "unsupported_format", ext=formats.normalise(ext)),
            reply_markup=_what_formats_keyboard(lang),
        )
        return

    declared_size = file_obj.file_size or 0
    limit_mb = max_file_mb_in(msg.chat_id)
    if declared_size and declared_size > limit_mb * 1024 * 1024:
        await msg.reply_text(_too_large_text(lang, declared_size, limit_mb))
        return

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

        _discard_pending(context)
    elif formats.normalise(state["src_ext"]) != ext:

        await msg.reply_text(i18n.t(lang, "batch_mixed_formats"))
        return
    elif len(state["paths"]) >= formats.MAX_BATCH:
        return
    elif state.get("over"):

        state["declared"] = state.get("declared", state["size"]) + declared_size
        _schedule_batch(context, msg, update.effective_user, group_id)
        return
    elif state.get("declared", state["size"]) + declared_size > convert_utils.MAX_FILE_MB * 1024 * 1024:

        state["declared"] = state.get("declared", state["size"]) + declared_size
        state["over"] = True
        _schedule_batch(context, msg, update.effective_user, group_id)
        return

    status = None
    if not joining:
        status = await LiveMessage.reply_to(msg, download_card(lang, 0, 0, 0))
    path = _new_upload_path(update.effective_user.id, ext)
    try:
        # A file on its way in is work in progress: a soft stop waits for it (lifecycle.usage_here).
        async with lifecycle.busy(msg.chat_id, i18n.t(lang, "restarting_send_again")):
            if declared_size > big_files.BOT_API_DOWNLOAD_BYTES and not LOCAL_BOT_API_URL:
                await _download_big(context, msg, path, declared_size, status, lang)
            else:

                await _download_bot_api(context, file_obj, path, declared_size, status, lang)
    except big_files.Unavailable as exc:

        _unlink(path)
        logger.warning("Big file not fetched, MTProto unavailable: %s", exc)
        text = i18n.t(lang, "big_download_unavailable", limit=BOT_API_MAX_MB)
        if status is not None:
            await status.set(context.bot, text)
        else:
            await msg.reply_text(text)
        return
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
        _join_album(state, path)
        _schedule_batch(context, msg, update.effective_user, group_id)
        return

    if group_id and context.job_queue is not None:

        context.user_data["convert"] = {
            "state": "awaiting_format",
            "paths": [str(path)],
            "src_ext": ext,
            "size": path.stat().st_size,
            "declared": declared_size or path.stat().st_size,
            "group_id": group_id,
        }
        _schedule_batch(context, msg, update.effective_user, group_id)
        return

    await _present_conversion_options(msg, context, update.effective_user, [path], ext)

def _join_album(state: dict, path: Path) -> None:
    """A file joins the pending conversion of its album."""
    state["paths"].append(str(path))
    state["size"] += path.stat().st_size
    state["ocr_pages"] = 0
    state["pages"] = None

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

    context.user_data.pop("convert", None)
    if state.get("over"):

        for path in paths:
            _unlink(path)
        lang = await i18n.get_lang(data["user"].id, context)
        await data["message"].reply_text(i18n.t(
            lang, "file_too_large_convert",
            size=f"{state.get('declared', state['size']) / 1024 / 1024:.1f}", max_mb=convert_utils.MAX_FILE_MB))
        return
    await _present_conversion_options(
        data["message"], context, data["user"], paths, state["src_ext"],
        group_id=data["group_id"],
    )

def _what_formats_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(i18n.t(lang, "btn_what_formats"), callback_data="fmtall"),
    ]])

def _format_rows(lang: str, targets: list[str], expanded: bool, total: int,
                 keep: bool | None = None, ocr: str | None = None) -> list[list]:
    """Three formats to a row, then whatever navigation the list needs."""
    buttons = [InlineKeyboardButton(i18n.target_label(lang, target), callback_data=f"convfmt:{target}")
               for target in targets]
    rows = [buttons[index:index + 3] for index in range(0, len(buttons), 3)]
    if total > len(targets):
        rows.append([InlineKeyboardButton(i18n.t(lang, "btn_more_formats"), callback_data="convmore")])
    elif expanded:
        rows.append([InlineKeyboardButton(i18n.t(lang, "btn_fewer_formats"), callback_data="convless")])
    if ocr is not None:
        rows.append([InlineKeyboardButton(
            i18n.t(lang, "ocr_lang_toggle", name=i18n.t(lang, f"ocr_lang_{ocr}")), callback_data="convocr")])
    if keep is not None:

        rows.append([InlineKeyboardButton(
            i18n.t(lang, "keep_toggle_on" if keep else "keep_toggle_off"), callback_data="convkeep")])
    rows.append([InlineKeyboardButton(i18n.t(lang, "btn_cancel_conversion"), callback_data="convcancel")])
    return rows

def human_size(size_bytes: float) -> str:
    """A size somebody can read. "12288 KB" is a number to work out; "12 MB" is a size."""
    if size_bytes >= 1024 * 1024:
        megabytes = size_bytes / 1024 / 1024
        return f"{megabytes:.1f} MB" if megabytes < 10 else f"{megabytes:.0f} MB"
    return f"{max(1, round(size_bytes / 1024))} KB"

def _options_text(lang: str, paths, src_ext: str, size: int,
                  animated: bool | None = None, notes=()) -> str:
    """The format menu. It does not quote a price, because until a format is chosen there is no price to quote."""
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
                out_bytes: int, price: int, balance: int | None,
                send_limit: int = jobs.SEND_LIMIT_BYTES) -> str:
    """What this conversion will cost, and what it is costing for."""
    lines = [f"{src_ext.upper()} → {i18n.target_label(lang, target_ext)}",
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

    lines.append("")
    lines.append(i18n.t(lang, "credit_policy_note"))

    lines.append("")
    lines.append(i18n.t(lang, "send_limit_note", mb=send_limit // (1024 * 1024)))
    return "\n".join(lines)

def _quote_keyboard(lang: str, price: int) -> InlineKeyboardMarkup:
    label = (i18n.t(lang, "btn_quote_free") if price == 0
             else i18n.t(lang, "btn_quote_go", price=price))
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="convgo")],
        [InlineKeyboardButton(i18n.t(lang, "btn_quote_back"), callback_data="convback")],
        [InlineKeyboardButton(i18n.t(lang, "btn_cancel_conversion"), callback_data="convcancel")],
    ])

def _ocr_withheld(state: dict) -> set[str]:
    """The targets that read text which THIS file must not be offered, though the host can write them (formats.targets_for says only that it can)."""
    if len(state["paths"]) > 1:
        if formats.category_of(state["src_ext"], state.get("animated")) == formats.IMAGE:
            return {"txt", "ocrpdf"}
        return {"ocrpdf"}
    if state["src_ext"] != "pdf":
        return set()
    pages = state.get("ocr_pages") or 0
    return set() if 0 < pages <= ocr_convert.OCR_MAX_PAGES else {"ocrpdf"}

def _offered_targets(state: dict) -> list[str]:
    """What the menu offers for a pending conversion, computed one way for every redraw: the menu, More/Less, the keep toggle and the text language."""
    targets = formats.targets_for(state["src_ext"], state.get("animated"))
    if len(state["paths"]) > 1:
        targets = [target for target in targets if target != state["src_ext"]]
    blocked = set(state.get("blocked") or ()) | _ocr_withheld(state)
    return [target for target in targets if target not in blocked]

def _ocr_choice(context: ContextTypes.DEFAULT_TYPE, lang: str) -> str:
    """The language text is read in: the person's choice, remembered for their next file, or until they make one, the language they use the bot in."""
    choice = context.user_data.get("ocr_lang")
    return choice if choice in ocr_convert.CHOICES else ocr_convert.default_choice(lang)

def _ocr_row(context: ContextTypes.DEFAULT_TYPE, lang: str, state: dict, shown) -> str | None:
    """The text language for the menu's toggle row -- None unless one of the buttons on the screen being drawn reads text: the row changes how those are read, so it is not on a screen that has none (a picture's TXT and searchable PDF are under More formats, so its first screen has no row)."""
    pages = state.get("ocr_pages") or 0
    if any(convert_utils.ocr_job_pages(state["src_ext"], target, pages, len(state["paths"])) for target in shown):
        return _ocr_choice(context, lang)
    return None

async def _present_conversion_options(
    message, context: ContextTypes.DEFAULT_TYPE, user, paths, src_ext: str,
    group_id: str | None = None,
):
    lang = await i18n.get_lang(user.id, context)
    src_ext = formats.normalise(src_ext)

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

    price = price_for_size(size)
    if price is None:
        for path in paths:
            _unlink(path)
        await message.reply_text(
            i18n.t(lang, "file_too_large_convert", size=f"{size / 1024 / 1024:.1f}",
                   max_mb=convert_utils.MAX_FILE_MB)
        )
        return

    megapixels = None
    raw_info = None
    if len(paths) == 1 and src_ext in formats.RAW_FORMATS:

        raw_info = await jobs.describe_raw(paths[0], src_ext)
        if raw_info is not None:
            megapixels = raw_info.out_megapixels
            if raw_info.megapixels > raw_convert.MAX_MP:
                for path in paths:
                    _unlink(path)
                await message.reply_text(i18n.t(lang, "raw_too_big", mp=f"{raw_info.megapixels:.0f}",
                                                max=f"{raw_convert.MAX_MP:.0f}"))
                return
    elif len(paths) == 1 and formats.category_of(src_ext, animated) == formats.IMAGE:

        megapixels = await jobs.describe_image(paths[0])
        if megapixels is not None and megapixels > jobs.MAX_MEGAPIXELS:
            for path in paths:
                _unlink(path)
            await message.reply_text(i18n.t(lang, "too_many_megapixels",
                                            mp=f"{megapixels:.0f}", max=jobs.MAX_MEGAPIXELS))
            return

    pages = None

    ocr_pages = 0
    if len(paths) == 1 and src_ext == "pdf" and formats.category_of(src_ext, animated) == formats.DOCUMENT:
        counted = await jobs.describe_pdf(paths[0])
        if counted is not None:
            pages = counted["pages"]

            if formats.met("ocr") and counted["scanned"] is not None:
                ocr_pages = counted["scanned"]
    elif len(paths) == 1 and formats.category_of(src_ext, animated) == formats.DOCUMENT:
        pages = await asyncio.to_thread(document_pages, paths[0], src_ext)
    elif (len(paths) == 1 and formats.category_of(src_ext, animated) == formats.IMAGE
          and src_ext not in formats.RAW_FORMATS and src_ext != "svg" and formats.met("ocr")):
        ocr_pages = 1

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
        "ocr_pages": ocr_pages,
    }
    every_target = _offered_targets(state)
    blocked = jobs.unsendable_targets(megapixels, every_target, size, message.chat_id,
                                      raw=raw_info is not None)
    state["blocked"] = blocked
    notes = []
    if blocked:
        notes.append(i18n.t(lang, "too_big_to_send_note",
                            formats=", ".join(target.upper() for target in blocked),
                            mp=f"{megapixels:.0f}", limit=jobs.send_ceiling_mb(message.chat_id)))
    if raw_info is not None and raw_info.half:
        notes.append(i18n.t(lang, "raw_half_note", mp=f"{raw_info.megapixels:.0f}",
                            out=f"{raw_info.out_megapixels:.0f}"))

    if len(paths) == 1 and formats.category_of(src_ext, animated) == formats.VIDEO:
        fit = await asyncio.to_thread(convert_utils.video_fit_note, paths[0])
        if fit is not None:
            which, width, height, fit_w, fit_h = fit
            notes.append(i18n.t(lang, f"video_fit_{which}_note", w=width, h=height,
                                fw=fit_w, fh=fit_h))
    if ocr_pages > ocr_convert.OCR_MAX_PAGES:
        notes.append(i18n.t(lang, "ocr_too_many_pages_note", max=ocr_convert.OCR_MAX_PAGES))
    state["notes"] = notes

    targets = _offered_targets(state)
    if not targets:
        for path in paths:
            _unlink(path)
        key = "nothing_sendable" if blocked else "no_target_formats"
        await message.reply_text(i18n.t(lang, key, limit=jobs.send_ceiling_mb(message.chat_id)))
        return

    context.user_data["convert"] = state
    keep = bool(context.user_data.get("keep_files"))
    shown = formats.popular_targets(src_ext, animated)
    shown = [target for target in shown if target in targets] or targets
    await message.reply_text(
        _options_text(lang, paths, src_ext, size, animated, notes),
        reply_markup=InlineKeyboardMarkup(_format_rows(lang, shown, False, len(targets), keep=keep,
                                                       ocr=_ocr_row(context, lang, state, shown))),
    )

async def convert_keep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The keep-file toggle under the format menu."""
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
    state["expanded"] = False
    await edit_in_place(
        query.message, context.bot,
        _options_text(lang, state["paths"], state["src_ext"], state["size"],
                      state.get("animated"), state.get("notes") or ()),
        reply_markup=InlineKeyboardMarkup(_format_rows(lang, shown, False, len(targets), keep=keep,
                                                       ocr=_ocr_row(context, lang, state, shown))),
    )

async def convert_ocr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The text-language toggle under the format menu: English, Russian, Uzbek, and round again."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    state = context.user_data.get("convert")
    if not state or state.get("state") != "awaiting_format":
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return
    choices = ocr_convert.CHOICES
    chosen = choices[(choices.index(_ocr_choice(context, lang)) + 1) % len(choices)]
    context.user_data["ocr_lang"] = chosen
    await query.answer(i18n.t(lang, "ocr_lang_set", name=i18n.t(lang, f"ocr_lang_{chosen}")))
    targets = _offered_targets(state)
    expanded = bool(state.get("expanded"))
    shown = targets if expanded else [
        target for target in formats.popular_targets(state["src_ext"], state.get("animated"))
        if target in targets] or targets
    await edit_in_place(
        query.message, context.bot,
        _options_text(lang, state["paths"], state["src_ext"], state["size"],
                      state.get("animated"), state.get("notes") or ()),
        reply_markup=InlineKeyboardMarkup(_format_rows(
            lang, shown, expanded, len(targets), keep=bool(context.user_data.get("keep_files")),
            ocr=_ocr_row(context, lang, state, shown))),
    )

async def convert_show_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The same message, redrawn with every target on it -- or back to the short list."""
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
    state["expanded"] = expanded
    shown = targets if expanded else [
        target for target in formats.popular_targets(src_ext, animated) if target in targets
    ] or targets
    await edit_in_place(
        query.message, context.bot,
        _options_text(lang, state["paths"], src_ext, state["size"], animated,
                      state.get("notes") or ()),
        reply_markup=InlineKeyboardMarkup(_format_rows(
            lang, shown, expanded, len(targets), keep=bool(context.user_data.get("keep_files")),
            ocr=_ocr_row(context, lang, state, shown))),
    )

def _result_caption(lang: str, result, src_ext: str, target_ext: str, stars_paid: int) -> str:
    """Say what actually came back."""
    if result.zipped and target_ext != "zip":
        key = "converted_file_caption_pages" \
            if formats.category_of(src_ext) in (formats.DOCUMENT, formats.PRESENTATION) \
            else "converted_file_caption_zip"
        caption = i18n.t(lang, key, items=result.items)
    elif result.items > 1 and target_ext == "pdf":
        caption = i18n.t(lang, "converted_file_caption_pdf", items=result.items)
    else:
        caption = i18n.t(lang, "converted_file_caption" if stars_paid else "converted_file_caption_free")
    # LibreOffice lays a Word document out by Word's own rules; only without it is the page re-laid.
    relaid = ("md", "html", "txt") if formats.met("office") else ("docx", "md", "html", "txt")
    if src_ext in relaid and target_ext == "pdf":
        caption += "\n\n" + i18n.t(lang, "converted_layout_note")
    # The note is about a PDF's text made editable; a Word file from LibreOffice is a copy, not a rebuild.
    if target_ext == "docx" and src_ext not in ("doc", "odt", "rtf"):

        caption += "\n\n" + i18n.t(lang, "converted_docx_note")
    return caption

_RUNNER = None

def _runner(application) -> ConvertRunner:
    """One runner per application. Built lazily because the application does not exist when this module is imported."""
    global _RUNNER
    if _RUNNER is None or _RUNNER.application is not application:
        _RUNNER = ConvertRunner(application, ADMIN_IDS, UPLOAD_DIR, _result_caption)
    return _RUNNER

def _touch(paths) -> None:
    """Restart a kept file's 15 minutes: the sweeper goes by modification time, and a file somebody is still converting is not abandoned."""
    now = time.time()
    for path in paths:
        try:
            os.utime(path, (now, now))
        except OSError:
            pass

async def _enqueue(context: ContextTypes.DEFAULT_TYPE, message, user, lang: str,
                   conv_state: dict, target_ext: str, edit_menu: bool = True) -> None:
    """Hand a chosen conversion to the queue and return straight away."""
    keep = bool(context.user_data.get("keep_files"))
    paths = list(conv_state["paths"])

    reading = convert_utils.ocr_job_pages(conv_state["src_ext"], target_ext, conv_state.get("ocr_pages") or 0,
                                          len(paths))
    if reading:
        time_limit = convert_utils.ocr_limit(conv_state["src_ext"], target_ext, conv_state["size"],
                                             conv_state.get("est_out") or 0, reading,
                                             paid=conv_state["price"] > 0, pages=conv_state.get("pages"))
    else:
        time_limit = jobs.time_limit_for(
            convert_utils.billable_bytes(conv_state["size"], conv_state.get("est_out") or 0),
            convert_utils.work_factor(conv_state["src_ext"], target_ext),
            paid=conv_state["price"] > 0)
    job = jobs.Job(
        user_id=user.id, chat_id=message.chat_id, paths=paths,
        src_ext=conv_state["src_ext"], target_ext=target_ext,
        size=conv_state["size"], price=conv_state["price"], lang=lang,
        username=user.username, keep_file=keep,
        send_limit=jobs.send_limit_for(conv_state["size"], conv_state.get("est_out"),
                                       message.chat_id),
        time_limit=time_limit,
        ocr_lang=_ocr_choice(context, lang) if reading else "", ocr_pages=reading,
    )
    ahead = sum(1 for other in jobs._jobs.values() if other.state in ("queued", "running"))
    if ahead:
        text = i18n.t(lang, "job_queued", src=job.src_ext.upper(), target=i18n.target_label(lang, target_ext),
                      ahead=ahead, price=job.price)
    else:
        text = i18n.t(lang, "job_starting", src=job.src_ext.upper(), target=i18n.target_label(lang, target_ext))
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
    """The Stop button under a conversion's status."""
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

    if target_ext not in formats.targets_for(conv_state["src_ext"], conv_state.get("animated")):
        await query.answer(i18n.t(lang, "unsupported_format", ext=target_ext), show_alert=True)
        return
    if target_ext in (conv_state.get("blocked") or ()):
        await query.answer(i18n.t(lang, "too_big_to_send_alert",
                                  limit=jobs.send_ceiling_mb(query.message.chat_id)),
                           show_alert=True)
        return
    if target_ext not in _offered_targets(conv_state):

        await query.answer(i18n.t(lang, "not_for_this_file"), show_alert=True)
        return

    in_paths = conv_state["paths"]
    src_ext = conv_state["src_ext"]
    user = update.effective_user

    if not all(os.path.exists(path) for path in in_paths):
        _discard_pending(context)
        await query.answer(i18n.t(lang, "conversion_expired"), show_alert=True)
        return

    price, est_out = price_for_job(src_ext, target_ext, conv_state["size"],
                                   conv_state.get("pages"), conv_state.get("ocr_pages") or 0,
                                   len(in_paths))
    conv_state["price"] = price
    conv_state["est_out"] = est_out
    conv_state["target_ext"] = target_ext

    if price == 0:
        await query.answer()
        await _start_chosen(update, context, conv_state, target_ext, lang)
        return

    balance = await asyncio.to_thread(family_link.star_balance, user.id)
    await query.answer()
    await edit_in_place(
        query.message, context.bot,
        _quote_text(lang, src_ext, target_ext, conv_state["size"], est_out, price, balance,
                    jobs.send_limit_for(conv_state["size"], est_out, query.message.chat_id)),
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
    state["expanded"] = False
    await edit_in_place(
        query.message, context.bot,
        _options_text(lang, state["paths"], state["src_ext"], state["size"],
                      state.get("animated"), state.get("notes") or ()),
        reply_markup=InlineKeyboardMarkup(_format_rows(
            lang, shown, False, len(targets), keep=bool(context.user_data.get("keep_files")),
            ocr=_ocr_row(context, lang, state, shown))),
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
    """Everything between "yes, that one, at that price" and the job being on the queue: the refusals, the balance, the invoice if there is not enough."""
    query = update.callback_query
    price = conv_state["price"]
    src_ext = conv_state["src_ext"]
    user = update.effective_user

    refusal = await refuse_new_work(lang, user.id, query.message.chat_id)
    if refusal:
        await query.answer(refusal, show_alert=True)
        return

    if len(jobs.jobs_for(user.id)) >= jobs.MAX_QUEUED_PER_USER:
        await query.answer(i18n.t(lang, "queue_full", count=jobs.MAX_QUEUED_PER_USER),
                           show_alert=True)
        return

    needed = price + jobs.uncharged_total(user.id)
    balance = await asyncio.to_thread(family_link.star_balance, user.id) if needed else 0
    if needed and balance < needed:
        shortfall = needed - max(balance, 0)
        stars = math.ceil(shortfall / max(family_link.TOPUP_MULTIPLIER, 0.01))
        credited = (await asyncio.to_thread(family_link.quote_topup, user.id, stars))["total"]
        if STARS_SANDBOX:

            await asyncio.to_thread(family_link.topup, user.id, stars,
                                    "sandbox top-up for a conversion")
        else:
            payload = f"convert:{uuid.uuid4().hex}"
            conv_state["target_ext"] = target_ext
            conv_state["payload"] = payload
            conv_state["state"] = "awaiting_payment"
            await asyncio.to_thread(
                record_star_invoice, user.id, user.username, stars,
                f"top-up for a {src_ext}->{'searchable-pdf' if target_ext == 'ocrpdf' else target_ext} conversion",
                payload)
            await context.bot.send_invoice(
                chat_id=query.message.chat_id,
                title=i18n.t(lang, "convert_invoice_title", src=src_ext.upper(),
                             target=i18n.target_label(lang, target_ext)),
                description=i18n.t(lang, "convert_invoice_description", size_kb=f"{conv_state['size'] / 1024:.0f}"),
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(i18n.t(lang, "convert_invoice_label", src=src_ext,
                                           target=target_ext if target_ext != "ocrpdf" else i18n.target_label(lang, target_ext)),
                                     stars)],
            )
            await edit_in_place(query.message, context.bot,
                                i18n.t(lang, "topup_needed", price=needed, balance=max(balance, 0),
                                       stars=stars, credited=credited))
            return

    await _enqueue(context, query.message, user, lang, conv_state, target_ext)

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

    result = await asyncio.to_thread(
        family_link.topup, user.id, sp.total_amount, "top-up for a conversion", charge_id)
    if result is None:

        family_link.report_event_soon("warning", "payment", "A Stars payment was delivered twice and credited once.")
        return
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
    """/mystars, kept working for everybody who learned it."""
    await balance_command(update, context)

async def stars_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    await update.message.reply_text(await _stars_text())

async def _bus_stars(context, args):
    """The Stars ledger, asked for from ManagerBot (`/stars convert`)."""
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
    """/dbdump -- exports every table in this bot's own database as one zip of CSVs."""
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
    """/messageas <user_id> <text> -- sends a message to that user as this bot."""
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
    """/status -- uptime, hosting environment, any crashes since this process started, and active-user counts."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    now = datetime.now(timezone.utc)
    users_hour = await asyncio.to_thread(count_active_users_since, now - timedelta(hours=1))
    users_since_start = await asyncio.to_thread(count_active_users_since, START_TIME)
    await update.message.reply_text(build_status_text(START_TIME, users_hour, users_since_start))

async def unrecognized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches anything that isn't a file and isn't a known command -- registered last, so it only fires when nothing else already handled the update."""
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

async def _check_big_files() -> None:
    """In the background, as the bot starts: an API id and hash that are set but wrong turn the big-file route off here -- 20 MB, as if they were not set -- instead of failing the first person who sends a big file."""
    if await big_files.verify() or big_files.VERIFIED is not False:
        return
    logger.warning("Largest upload now %d MB: %s.", convert_utils.MAX_FILE_MB, big_files.describe())
    family_link.report_event_soon("warning", "big_files", f"ConvertBot: {big_files.describe()}.")

_background: set = set()

async def _post_init(application):
    await tune_runtime(application)

    await lifecycle.on_start(BOT_NAME)
    await publish_commands(application, BOT_COMMANDS, ADMIN_COMMANDS, ADMIN_IDS)
    await publish_profile(application)
    if big_files.CONFIGURED:
        task = asyncio.get_running_loop().create_task(_check_big_files())
        _background.add(task)
        task.add_done_callback(_background.discard)

async def _post_stop(application):

    await lifecycle.on_stop(application)
    await big_files.close()
    await flush_on_shutdown(application)

def main():
    if not BOT_TOKEN or not BOT_USERNAME:
        raise SystemExit("Set CBOT_TOKEN and CBOT_USERNAME environment variables first.")

    init_db()

    formats.probe()

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
    else:
        logger.info("Largest upload %d MB: %s.", convert_utils.MAX_FILE_MB, big_files.describe())
    state = lifecycle.persistence()
    if state is not None:
        builder = builder.persistence(state)
    app = builder.build()
    lifecycle.install(app, BOT_NAME, ADMIN_IDS)
    lifecycle.add_work_source("conversion(s)", lambda: len(jobs._jobs))
    app.add_error_handler(error_handler)
    attach_problem_reports(app)

    app.add_handler(TypeHandler(Update, track_activity), group=-4)

    attach_flood_gate(app, ADMIN_IDS)

    attach_promo_claim(app)

    app.add_handler(MessageHandler((filters.TEXT | filters.REPLY) & ~filters.COMMAND,
                                   awaited_text_received), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("fullhelp", full_help_command(build_help_text, help_rows, HELP_PAGES)))
    app.add_handler(CallbackQueryHandler(help_toggle(build_help_text, help_rows, HELP_PAGES),
                                         pattern=HELP_TOGGLE_PATTERN))
    app.add_handler(CallbackQueryHandler(help_page_button(HELP_PAGES), pattern=HELP_PAGE_PATTERN))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("convert", convert_start))
    app.add_handler(CommandHandler("formats", formats_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("mystars", mystars_command))
    app.add_handler(CommandHandler("stars", stars_admin_command))
    app.add_handler(CommandHandler("dbdump", dbdump_command))
    app.add_handler(CommandHandler("messageas", messageas_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(convert_format_chosen, pattern="^convfmt:"))
    app.add_handler(CallbackQueryHandler(convert_show_more, pattern="^conv(more|less)$"))
    app.add_handler(CallbackQueryHandler(convert_quote_go, pattern="^convgo$"))
    app.add_handler(CallbackQueryHandler(convert_quote_back, pattern="^convback$"))
    app.add_handler(CallbackQueryHandler(formats_overview_callback, pattern="^fmtall$"))
    app.add_handler(CallbackQueryHandler(formats_category_callback, pattern="^fmtcat:"))
    app.add_handler(CallbackQueryHandler(cancel_conversion_callback, pattern="^convcancel$"))
    app.add_handler(CallbackQueryHandler(convert_stop_callback, pattern="^convstop:"))
    app.add_handler(CallbackQueryHandler(convert_keep_callback, pattern="^convkeep$"))
    app.add_handler(CallbackQueryHandler(convert_ocr_callback, pattern="^convocr$"))
    app.add_handler(CallbackQueryHandler(cancel_choice_callback, pattern="^cancelpick:"))
    app.add_handler(CallbackQueryHandler(language_chosen, pattern="^setlang:"))
    app.add_handler(CommandHandler("language", language_command))

    app.add_handler(CommandHandler("en", set_language_en))
    app.add_handler(CommandHandler("uz", set_language_uz))
    app.add_handler(CommandHandler("rus", set_language_rus))

    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler("paysupport", paysupport_command))
    app.add_handler(CallbackQueryHandler(problem_report_callback, pattern=r"^rpt"))
    app.add_handler(CommandHandler("deletemydata", delete_my_data_command))
    app.add_handler(CallbackQueryHandler(delete_my_data_chosen, pattern="^" + ERASE_PREFIX))

    app.add_handler(CommandHandler("balance", balance_command))

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

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unrecognized_message))

    family_link.attach(app, BOT_NAME, "ConvertBot", START_TIME)

    family_link.COMMANDS["stars"] = _bus_stars
    family_link.COMMAND_HELP["stars"] = "the Stars ledger: paid, free and refunded"
    attach_maintenance(app)
    if app.job_queue is not None:
        app.job_queue.run_repeating(_sweep_uploads_job, interval=300, first=300)
        app.job_queue.run_repeating(_conversions_in_flight_job, interval=jobs.HOLD_TOUCH_S, first=10)

    logger.info("Bot starting (polling)...")

    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY, Update.PRE_CHECKOUT_QUERY],
    ))

if __name__ == "__main__":
    main()

# ─── module: downloader_bot.bot ──────────────────────────────────────────────
"""Media downloader bot -- 4th bot in the family (see ARCHITECTURE.md)."""
import asyncio
import hashlib
import logging
import os
import shutil
import uuid
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import (
    BotCommand, InputMediaDocument, InputMediaPhoto, InputMediaVideo,
    LinkPreviewOptions, Update, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.error import BadRequest

NO_PREVIEW = {"link_preview_options": LinkPreviewOptions(is_disabled=True)}
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

import cards
import db
import delivery_cache
import family_link
import i18n
import problems
import lifecycle
import net
import platforms
import resolvers
import routewatch
import sent_files
import shared_features
import big_files
import large_files
import merge
import video
from live_message import LiveMessage, edit_in_place
from db import (
    init_db,
    get_caption_enabled,
    set_caption_enabled,
    get_lossless_enabled,
    set_lossless_enabled,
    get_large_files_enabled,
    set_large_files_enabled,
    get_user_language,
    set_user_language,
    dump_database_csv_zip,
    count_active_users_since,
    load_provider_health,
    save_provider_health,
    download_allowance,
    record_download,
    sent_files_get,
    sent_files_put,
    sent_files_confirmed,
    sent_files_used,
    sent_files_drop,
)
from shared_features import (
    note_job,
    note_stat,
    note_tap,
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
    problem_report_callback,
    refuse_new_work,
    attach_flood_gate,
    attach_promo_claim,
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
    donate_command,
    donate_amount_chosen,
    donate_fiat_amount_chosen,
    donate_custom_button_chosen,
    awaited_text_received,
    feedback_command,
    HELP_PAGE_PATTERN,
    HELP_TOGGLE_PATTERN,
    full_help_command,
    help_keyboard,
    help_page_button,
    help_page_name,
    help_page_text,
    help_toggle,
    wants_full_help,
    donation_precheckout_callback,
    donation_payment_callback,
    setup_logging,
    error_handler,
    track_activity,
    build_status_text,
)

setup_logging(__file__)
logger = logging.getLogger(__name__)

START_TIME = datetime.now(timezone.utc)

BOT_TOKEN = os.environ.get("DBOT_TOKEN")

BOT_USERNAME = (os.environ.get("DBOT_USERNAME") or "").strip().lstrip("@") or None

BOT_NAME = "downloaderbot"

sent_files.configure(BOT_TOKEN)

ADMIN_IDS = {int(x) for x in os.environ.get("DBOT_ADMIN_ID", "").split(",") if x.strip()}

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def _deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """How an owner-only command answers everybody else: exactly the way a misspelling does."""
    await unknown_command(update, context)

POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "30"))

MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("DBOT_MAX_CONCURRENT_DOWNLOADS", "3"))

_download_slots: asyncio.Semaphore | None = None

def _slots() -> asyncio.Semaphore:
    global _download_slots
    if _download_slots is None:
        _download_slots = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    return _download_slots

MAX_CONCURRENT_LOOKUPS = 2

_lookup_slots: asyncio.Semaphore | None = None

def _lookups() -> asyncio.Semaphore:
    global _lookup_slots
    if _lookup_slots is None:
        _lookup_slots = asyncio.Semaphore(MAX_CONCURRENT_LOOKUPS)
    return _lookup_slots

MAX_PER_USER = max(1, int(os.environ.get("DBOT_MAX_PER_USER") or 2))

MAX_PENDING_PER_USER = max(1, int(os.environ.get("DBOT_MAX_PENDING_PER_USER") or 5))

MIN_FREE_MB = int(os.environ.get("DBOT_MIN_FREE_MB") or 300)

delivery_cache.configure(resolvers._WORK_DIR)

def _cache_floor_mb() -> int:
    return MIN_FREE_MB + MAX_CONCURRENT_DOWNLOADS * video.MAX_DOWNLOAD_MB

def _make_room(mb: int) -> None:
    """A download is about to take up to `mb` MB: kept files go first, until the disk has that and MIN_FREE_MB more, or none are left."""
    delivery_cache.make_room(mb, MIN_FREE_MB)

MERGE_MAX_ITEMS = int(os.environ.get("DBOT_MERGE_MAX_ITEMS") or 20)
MERGE_MAX_MB = int(os.environ.get("DBOT_MERGE_MAX_MB") or 48)

_user_slots: "dict[int, asyncio.Semaphore]" = {}
_user_pending: "dict[int, int]" = {}

_in_flight: "dict[tuple[int, int, str, str], float]" = {}
IN_FLIGHT_MAX_SECONDS = 3600

def _already_in_flight(key) -> bool:
    marked = _in_flight.get(key)
    return marked is not None and time.monotonic() - marked < IN_FLIGHT_MAX_SECONDS

def _clear_in_flight(key, stamp) -> None:
    """Take a link's mark down, only if it is still the one this job made: a job that ran past IN_FLIGHT_MAX_SECONDS may find its mark replaced by a newer copy of the link, and that mark is the newer job's to clear."""
    if _in_flight.get(key) == stamp:
        _in_flight.pop(key, None)

async def _answer_duplicate(update: Update) -> None:
    """The one answer to a link that is already being fetched: a 👌 on the copy."""
    try:
        await update.effective_message.set_reaction("👌")
    except Exception as exc:
        logger.debug("Couldn't react to a repeated link (%s)", type(exc).__name__)

@asynccontextmanager
async def _user_slot(user_id: int):
    slot = _user_slots.get(user_id)
    if slot is None:
        slot = _user_slots[user_id] = asyncio.Semaphore(MAX_PER_USER)
    try:
        async with slot:
            yield
    finally:

        if slot._value >= MAX_PER_USER and not slot._waiters:
            _user_slots.pop(user_id, None)

def _user_slots_full(user_id: int) -> bool:
    slot = _user_slots.get(user_id)
    return slot is not None and slot.locked()

def _free_mb() -> "int | None":
    try:
        return shutil.disk_usage(resolvers._WORK_DIR).free // (1024 * 1024)
    except OSError:
        return None

def _spawn_download(context, update, work, in_flight=None) -> None:
    """Run one link's whole download in a task of its own."""
    user_id = update.effective_user.id
    _user_pending[user_id] = _user_pending.get(user_id, 0) + 1
    stamp = _in_flight.get(in_flight) if in_flight is not None else None

    async def run():
        try:
            await work()
        finally:
            left = _user_pending.get(user_id, 1) - 1
            if left > 0:
                _user_pending[user_id] = left
            else:
                _user_pending.pop(user_id, None)
            if in_flight is not None:
                _clear_in_flight(in_flight, stamp)

    context.application.create_task(run(), update=update)

def build_help_text(lang: str, full: bool = False) -> str:
    """The short version unless asked for the long one -- the family's help template (shared_features, "/help in two lengths")."""
    if not full:
        text = i18n.t(lang, "help_brief").rstrip("\n")
    else:
        text = i18n.t(lang, "help_text", username=BOT_USERNAME or "this_bot").rstrip("\n")
    blurb = sibling_bots_blurb(BOT_NAME, lang)
    return text + "\n\n" + blurb if blurb else text

def _help_large_prices(lang: str, key: str) -> str:
    return i18n.t(lang, key, free_mb=large_files.FREE_MAX_MB, max=large_files.LARGE_MAX_MB,
                  first=large_files.first_price(), top=large_files.top_price())

def _help_page_download(lang: str) -> str:

    if db.DOWNLOADS_PER_DAY > 0 and db.DOWNLOADS_PER_HOUR > 0:

        quota = i18n.t(lang, "helppage_download_quota",
                       per_day=db.DOWNLOADS_PER_DAY, per_hour=db.DOWNLOADS_PER_HOUR,
                       donor_day=int(db.DOWNLOADS_PER_DAY * db.DONOR_MULTIPLIER),
                       donor_hour=int(db.DOWNLOADS_PER_HOUR * db.DONOR_MULTIPLIER))
    else:
        quota = i18n.t(lang, "helppage_download_quota_off")
    if large_files.CONFIGURED:
        large = i18n.t(lang, "helppage_download_large", max=large_files.LARGE_MAX_MB,
                       first=large_files.first_price(), top=large_files.top_price())
    else:
        large = i18n.t(lang, "helppage_download_large_off")
    return i18n.t(lang, "helppage_download", quota=quota, at_once=MAX_PER_USER, waiting=MAX_PENDING_PER_USER,
                  free_mb=large_files.FREE_MAX_MB, large=large,
                  merge_items=MERGE_MAX_ITEMS, merge_mb=MERGE_MAX_MB)

def _help_page_settings(lang: str) -> str:
    large = _help_large_prices(lang, "helppage_settings_large") + "\n" if large_files.CONFIGURED else ""
    return i18n.t(lang, "helppage_settings", username=BOT_USERNAME or "this_bot", large=large)

HELP_PAGES = {"download": _help_page_download, "settings": _help_page_settings}
HELP_ALIASES = {}

HELP_LABELS = {"download": "help_btn_download"}

BOT_COMMANDS = [

    BotCommand("start", "What I do, and how to start"),
    BotCommand("language", "Choose your language / Tilni tanlash / Выбрать язык"),
    BotCommand("settings", "Captions and file quality"),
    BotCommand("cancel", "Stop whatever I am waiting for"),
    BotCommand("help", "Everything I can do"),
    BotCommand("feedback", "Suggest something, or report a problem"),
    BotCommand("balance", "Your ⚡ credit"),
    BotCommand("donate", "Chip in for hosting costs"),
    BotCommand("paysupport", "Trouble with a payment"),
    BotCommand("privacy", "What I keep about you"),
    BotCommand("terms", "What I may be used for"),
    BotCommand("deletemydata", "Delete everything I hold on you"),
]

ADMIN_COMMANDS = [
    BotCommand("status", "🔒 Uptime, host, errors, active users"),
    BotCommand("providers", "🔒 Which download route works, which is resting"),
    BotCommand("messageas", "🔒 messageas <user_id> <text> — DM as this bot"),
    BotCommand("dbdump", "🔒 This bot's tables as a zip of CSVs"),
]

async def _reply(update: Update, text: str, **kwargs):
    """Works whether the update came from a command or a button tap."""
    if update.message:
        return await LiveMessage.reply_to(update.message, text, **kwargs)
    return await edit_in_place(update.callback_query.message, update.get_bot(), text, **kwargs)

async def _continue_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    await _reply(
        update,
        i18n.t(lang, "start_greeting") + build_help_text(lang),
        reply_markup=help_keyboard(lang, False, [sibling_bots_keyboard_row(BOT_NAME)], HELP_PAGES, HELP_LABELS),
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start prints the instructions -- except the very first one, which asks for a language first."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    if lang is None:
        await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
        return
    context.user_data["lang"] = lang
    await _continue_start(update, context, lang)

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/language -- the picker on demand, which is what /start used to be."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)

    if lang:
        context.user_data["lang"] = lang
    await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard(lang))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    page = help_page_name(context, HELP_PAGES, HELP_ALIASES)
    if page:
        await update.message.reply_text(help_page_text(lang, HELP_PAGES, page),
                                        link_preview_options=shared_features.NO_PREVIEW)
        return
    full = wants_full_help(context)
    await update.message.reply_text(build_help_text(lang, full=full),
                                    reply_markup=help_keyboard(lang, full, (), HELP_PAGES, HELP_LABELS))

async def _cancel_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> list[CancelItem]:
    """Everything this bot could be waiting on -- which is only ever the shared donation prompt."""
    return cancel_items(context, lang)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This bot asks the fewest questions in the family -- a link needs no follow-up, and /caption and /lossless answer themselves with buttons -- so the only thing /cancel usually has to catch is a donation amount it asked for."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if await ask_cancel_choice(update, context, await _cancel_items(update, context, lang), lang):
        return
    await finish_cancel(update, context, lang, [])

async def cancel_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of /cancel's buttons."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    key = cancel_choice_key(update)
    await query.answer()
    if key == CANCEL_PICK_NONE:
        await keep_going(update, context, lang)
        return
    if key == CANCEL_PICK_ALL:
        keys = [item.key for item in await _cancel_items(update, context, lang)]
    else:
        keys = [key]
    stopped = [label for label in (cancel_shared_item(context, lang, k) for k in keys) if label]
    await finish_cancel_choice(update, context, lang, stopped)

async def _apply_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """The single path every language change goes through -- /en, /uz, /rus and a tap on the picker alike -- so all four end the same way: with the instructions, printed in the language just chosen."""
    await asyncio.to_thread(set_user_language, update.effective_user.id, lang)
    context.user_data["lang"] = lang

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

def _caption_keyboard(lang: str, enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(("✅ " if enabled else "") + i18n.t(lang, "caption_state_on"), callback_data="caption:on"),
                InlineKeyboardButton(("✅ " if not enabled else "") + i18n.t(lang, "caption_state_off"), callback_data="caption:off"),
            ]
        ]
    )

async def caption_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    lang = await i18n.get_lang(update.effective_user.id, context)
    if not context.args or context.args[0].lower() not in ("on", "off"):
        current = await asyncio.to_thread(get_caption_enabled, update.effective_user.id)
        state = i18n.t(lang, "caption_state_on" if current else "caption_state_off")
        await update.message.reply_text(
            i18n.t(lang, "caption_status", state=state),
            reply_markup=_caption_keyboard(lang, current),
        )
        return
    enabled = context.args[0].lower() == "on"
    await asyncio.to_thread(set_caption_enabled, update.effective_user.id, enabled)
    state = i18n.t(lang, "caption_state_on" if enabled else "caption_state_off")
    await update.message.reply_text(i18n.t(lang, "caption_turned", state=state))

async def caption_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    enabled = query.data.split(":", 1)[1] == "on"
    await asyncio.to_thread(set_caption_enabled, update.effective_user.id, enabled)
    state = i18n.t(lang, "caption_state_on" if enabled else "caption_state_off")
    await query.answer(i18n.t(lang, "caption_toggle_answer", state=state))
    await edit_in_place(query.message, context.bot,
        i18n.t(lang, "caption_status", state=state),
        reply_markup=_caption_keyboard(lang, enabled),
    )

def _lossless_keyboard(lang: str, enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(("✅ " if enabled else "") + i18n.t(lang, "lossless_state_on"), callback_data="lossless:on"),
                InlineKeyboardButton(("✅ " if not enabled else "") + i18n.t(lang, "lossless_state_off"), callback_data="lossless:off"),
            ]
        ]
    )

async def lossless_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/lossless [on|off] -- send downloads as files instead of as media."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if not context.args or context.args[0].lower() not in ("on", "off"):
        current = await asyncio.to_thread(get_lossless_enabled, update.effective_user.id)
        state = i18n.t(lang, "lossless_state_on" if current else "lossless_state_off")
        await update.message.reply_text(
            i18n.t(lang, "lossless_status", state=state),
            reply_markup=_lossless_keyboard(lang, current),
        )
        return
    enabled = context.args[0].lower() == "on"
    await asyncio.to_thread(set_lossless_enabled, update.effective_user.id, enabled)
    state = i18n.t(lang, "lossless_state_on" if enabled else "lossless_state_off")
    await update.message.reply_text(i18n.t(lang, "lossless_turned", state=state))

async def lossless_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    enabled = query.data.split(":", 1)[1] == "on"
    await asyncio.to_thread(set_lossless_enabled, update.effective_user.id, enabled)
    state = i18n.t(lang, "lossless_state_on" if enabled else "lossless_state_off")
    await query.answer(i18n.t(lang, "lossless_toggle_answer", state=state))
    await edit_in_place(query.message, context.bot,
        i18n.t(lang, "lossless_status", state=state),
        reply_markup=_lossless_keyboard(lang, enabled),
    )

def _large_keyboard(lang: str, enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(("✅ " if enabled else "") + i18n.t(lang, "large_state_on"), callback_data="large:on"),
                InlineKeyboardButton(("✅ " if not enabled else "") + i18n.t(lang, "large_state_off"), callback_data="large:off"),
            ]
        ]
    )

def _large_status(lang: str, enabled: bool) -> str:
    state = i18n.t(lang, "large_state_on" if enabled else "large_state_off")
    return i18n.t(lang, "large_status", state=state, free=large_files.FREE_MAX_MB, per=large_files.first_price(),
                  top=large_files.top_price(),
                  max=large_files.LARGE_MAX_MB)

async def large_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The large-files switch, from /settings, or from the button under a refusal for a file over the free ceiling (`large:offer`)."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    choice = query.data.split(":", 1)[1]
    enabled = choice in ("on", "offer")
    await asyncio.to_thread(set_large_files_enabled, update.effective_user.id, enabled)
    state = i18n.t(lang, "large_state_on" if enabled else "large_state_off")
    await query.answer(i18n.t(lang, "large_toggle_answer", state=state))
    if choice == "offer":
        await edit_in_place(query.message, context.bot,
                            i18n.t(lang, "large_files_turned_on", per=large_files.first_price()))
        return
    await edit_in_place(query.message, context.bot, _large_status(lang, enabled),
                        reply_markup=_large_keyboard(lang, enabled))

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Both switches this bot has, on one screen, with their state on them."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    caption_on = await asyncio.to_thread(get_caption_enabled, update.effective_user.id)
    lossless_on = await asyncio.to_thread(get_lossless_enabled, update.effective_user.id)
    caption_state = i18n.t(lang, "caption_state_on" if caption_on else "caption_state_off")
    lossless_state = i18n.t(lang, "lossless_state_on" if lossless_on else "lossless_state_off")
    text = (i18n.t(lang, "settings_heading") + "\n\n"
            + i18n.t(lang, "caption_status", state=caption_state) + "\n\n"
            + i18n.t(lang, "lossless_status", state=lossless_state))
    rows = (_caption_keyboard(lang, caption_on).inline_keyboard
            + _lossless_keyboard(lang, lossless_on).inline_keyboard)

    if large_files.CONFIGURED:
        large_on = await asyncio.to_thread(get_large_files_enabled, update.effective_user.id)
        text += "\n\n" + _large_status(lang, large_on)
        rows += _large_keyboard(lang, large_on).inline_keyboard
    keyboard = InlineKeyboardMarkup(rows)
    await update.message.reply_text(text, reply_markup=keyboard)

async def dbdump_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dbdump -- exports every table in this bot's own database as one zip of CSVs. Owner-only."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    status = await LiveMessage.reply_to(update.message, "Exporting the database...")
    try:
        data = await asyncio.to_thread(dump_database_csv_zip)
    except Exception as exc:
        await status.set(context.bot, f"⚠️ Export failed: {exc}")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    await update.message.reply_document(document=BytesIO(data), filename=f"downloaderbot_db_{stamp}.zip")
    await status.delete(context.bot)

async def messageas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/messageas <user_id> <text> -- sends a message to that user as this bot."""
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
    """/status -- uptime, hosting environment, any crashes since this process started, and active-user counts."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    now = datetime.now(timezone.utc)
    users_hour = await asyncio.to_thread(count_active_users_since, now - timedelta(hours=1))
    users_since_start = await asyncio.to_thread(count_active_users_since, START_TIME)
    await update.message.reply_text(
        build_status_text(START_TIME, users_hour, users_since_start) + "\n" + _cache_status_line()
        + "\n" + _sent_files_status_line())

def _cache_status_line() -> str:
    """One line for the owner: counts only, never whose or what."""
    stats = delivery_cache.stats()
    if not stats["enabled"]:
        return "Delivery cache: off"
    return (f"Delivery cache: {stats['entries']} kept ({stats['bytes'] / (1024 * 1024):.1f} MB), "
            f"{stats['hits']} hits / {stats['misses']} misses since start")

def _sent_files_status_line() -> str:
    """The file-id store (sent_files.py), for the owner: counts since the bot started, never whose or what."""
    stats = sent_files.stats()
    if not stats["enabled"]:
        return "Sent-file store: off"
    return (f"Sent-file store: rows read {stats['hit']} fresh / {stats['stale']} stale / {stats['miss']} none; "
            f"lookups {stats['present']} present / {stats['missing']} missing / {stats['unknown']} unknown; "
            f"{stats['invalid']} invalid ids, {stats['stored']} stored since start")

PROVIDER_HEALTH_FLUSH_SECONDS = int(
    os.environ.get("DBOT_PROVIDER_FLUSH_SECONDS", "60"))

async def _flush_provider_health(_context=None) -> None:
    dirty = resolvers.take_dirty()
    if not dirty:
        return
    rows = [(name, h.ok, h.failed, h.streak, h.last_ok, h.last_fail, h.last_error)
            for name, h in dirty.items()]
    try:
        await asyncio.to_thread(save_provider_health, rows)
    except Exception:

        logger.warning("couldn't save provider health", exc_info=True)

PROBE_TIMEOUT_S = float(os.environ.get("DBOT_PROBE_TIMEOUT", "12"))

async def _bus_probe(context, args):
    """`probe [url|platform ...]` over the family bus."""
    fetch = True
    urls: dict[str, str] = {}
    for arg in args:
        if arg in ("--nofetch", "nofetch"):
            fetch = False
            continue
        if arg in resolvers.SAMPLES:
            urls[arg] = resolvers.SAMPLES[arg]
            continue
        detected = platforms.detect_platform(arg)
        if detected:
            urls[detected[0]] = detected[1]
    results = await resolvers.probe_all(urls or None, fetch=fetch,
                                        timeout=PROBE_TIMEOUT_S)
    header = ("Download routes, asked from inside this container "
              f"({os.environ.get('RAILWAY_ENVIRONMENT') or 'local'}). "
              "Scores untouched.\n")
    return header + resolvers.format_probe(results), None, None

async def _bus_routewatch(context, args):
    """`routewatch` over the family bus: the daily check, now."""
    return await routewatch.run(force=True, reply_within=routewatch.REPLY_WITHIN_S), None, None

async def providers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/providers -- which download route is working and which is not."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    await update.message.reply_text(_providers_text(), **NO_PREVIEW)

async def _bus_providers(context, args):
    """The same report, asked for from ManagerBot (`/providers downloader`)."""
    return _providers_text(), None, None

def _providers_text() -> str:
    now = time.time()
    lines = []
    for platform, chain in resolvers.PROVIDERS.items():
        lines.append(f"\n{platform}:")
        for name, _fn in chain:
            h = resolvers.health(name)
            if h.ok == 0 and h.failed == 0:
                lines.append(f"  \u2022 {name} -- not tried yet")
                continue
            if h.streak == 0 and h.ok:
                mark, note = "\u2705", f"last ok {_ago(now - (h.last_ok or now))} ago"
            elif h.cooling_until > now:
                mark = "\u274c"
                note = (f"{h.streak} in a row, resting "
                        f"{_ago(h.cooling_until - now)}: "
                        f"{resolvers.tidy_error(h.last_error)}")
            else:
                mark = "\u26a0\ufe0f"
                note = f"{h.streak} in a row: {resolvers.tidy_error(h.last_error)}"
            lines.append(f"  {mark} {name} -- {h.ok} ok / {h.failed} failed, {note}")
    return "Download routes, best first per platform:" + "\n".join(lines)

def _ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 90:
        return f"{seconds}s"
    if seconds < 5400:
        return f"{seconds // 60}m"
    if seconds < 172800:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"

REDELIVER_PREFIX = "redo:"
REDELIVER_MEMORY = 5

MERGE_PREFIX = "merge:"

def _remember_delivery(context, platform: str, url: str, lossless: bool) -> str:
    memory = context.user_data.setdefault("redeliver", {})
    while len(memory) >= REDELIVER_MEMORY:
        memory.pop(next(iter(memory)))
    token = uuid.uuid4().hex[:10]

    memory[token] = {"platform": platform, "url": url, "lossless": lossless, "at": time.time()}
    return token

REDO_DELAY_BUCKETS = (
    (60, "lt1m"), (120, "1-2m"), (300, "2-5m"), (900, "5-15m"), (3600, "15-60m"),
)

def _redo_delay_key(remembered: dict) -> str:
    at = remembered.get("at")
    if isinstance(at, bool) or not isinstance(at, (int, float)):
        return "redo.after.unknown"
    seconds = time.time() - at
    for limit, name in REDO_DELAY_BUCKETS:
        if seconds < limit:
            return f"redo.after.{name}"
    return "redo.after.gt60m"

def _spend_action(remembered: dict, action: str) -> bool:
    """True the first time `action` ("redo", "pdf" or "zip") is taken from this delivery, False every time after."""
    spent = remembered.setdefault("spent", [])
    if not isinstance(spent, list):

        spent = remembered["spent"] = ["redo"]
    if action in spent:
        return False
    spent.append(action)
    return True

def _unspend_action(remembered: dict, action: str) -> None:
    """Give `action` back: the tap that spent it came to nothing (the person was out of downloads), so the button is theirs to tap again."""
    spent = remembered.get("spent", [])
    if isinstance(spent, list) and action in spent:
        spent.remove(action)

def _remembered_kb(lang: str, token: str, remembered: dict):
    """The keyboard of a delivered album as it stands now: the same buttons it was first sent with (the counts are kept in `remembered` by _send_media), less every action already taken."""
    return _nudge_kb(lang, token, remembered.get("lossless", False),
                     photos=remembered.get("photos", 0), items=remembered.get("items", 0),
                     spent=remembered.get("spent") if isinstance(remembered.get("spent"), (list, tuple))
                     else ("redo",) if remembered.get("spent") else ())

def _nudge_kb(lang: str | None = None, token: str | None = None,
              lossless: bool = False, photos: int = 0,
              items: int = 0, spent=()) -> InlineKeyboardMarkup | None:

    rows = []
    if lang is not None and token is not None:

        if "redo" not in spent:
            rows.append([InlineKeyboardButton(
                i18n.t(lang, "redeliver_as_compressed" if lossless else "redeliver_as_file"),
                callback_data=f"{REDELIVER_PREFIX}{token}")])

        merge_row = []
        if photos >= merge.MIN_PDF_PHOTOS and "pdf" not in spent:
            merge_row.append(InlineKeyboardButton("📄 PDF", callback_data=f"{MERGE_PREFIX}pdf:{token}"))
        if items >= merge.MIN_ZIP_ITEMS and "zip" not in spent:
            merge_row.append(InlineKeyboardButton("🗜 ZIP", callback_data=f"{MERGE_PREFIX}zip:{token}"))
        if merge_row:
            rows.append(merge_row)
    kb_row = sibling_bots_keyboard_row(BOT_NAME, only="convertbot")
    if kb_row:
        rows.append(kb_row)
    return InlineKeyboardMarkup(rows) if rows else None

async def _take_button_off(query, lang: str, token: str, remembered: dict) -> None:
    """Put the delivery's keyboard under the message as it now stands (see _remembered_kb): the buttons of the actions spent are gone, the rest stay."""
    try:
        await query.edit_message_reply_markup(reply_markup=_remembered_kb(lang, token, remembered))
    except Exception:
        logger.debug("Couldn't change the delivery's buttons", exc_info=True)

async def redeliver_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The button under a finished download."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    token = query.data[len(REDELIVER_PREFIX):]
    remembered = context.user_data.get("redeliver", {}).get(token)
    if not remembered or not _spend_action(remembered, "redo"):

        note_tap("redo.spent" if remembered else "redo.expired")
        await query.answer(i18n.t(lang, "redeliver_expired"), show_alert=True)
        return
    await query.answer()

    note_tap("redo.to_compressed" if remembered.get("lossless") else "redo.to_file")
    note_tap(_redo_delay_key(remembered))

    delivery_cache.note_link(update.effective_user.id, remembered["platform"], remembered["url"])

    await _take_button_off(query, lang, token, remembered)

    allowance = await asyncio.to_thread(download_allowance, update.effective_user.id)
    if not allowance["allowed"]:

        _unspend_action(remembered, "redo")
        await _take_button_off(query, lang, token, remembered)
        await query.message.reply_text(_allowance_message(lang, allowance))
        return
    await asyncio.to_thread(record_download, update.effective_user.id, remembered["platform"])

    async def work():
        platform, url = remembered["platform"], remembered["url"]
        if platform in ("reddit", "twitter") and not delivery_cache.has(update.effective_user.id, platform, url):
            handler = _handle_reddit if platform == "reddit" else _handle_twitter
            await handler(update, context, url, lossless=not remembered["lossless"])
            return
        await _resolve_and_send(
            update, context, platform, url,
            lossless_override=not remembered["lossless"], from_redo=True,
        )

    _spawn_download(context, update, work)

class _MergeStop(Exception):
    """The merge ends here, with this message (an i18n key) to the person."""

    def __init__(self, key: str):
        super().__init__(key)
        self.key = key

def _merge_text(lang: str, key: str) -> str:

    return i18n.t(lang, key, items=MERGE_MAX_ITEMS, mb=MERGE_MAX_MB, mp=merge.MAX_MEGAPIXELS)

def _file_digest(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def _without_duplicates(items: list, paths: list) -> "tuple[list, list]":
    """The downloaded files without exact copies (some routes give the same picture twice); the copies are deleted."""
    seen: set = set()
    kept_items, kept_paths = [], []
    for item, path in zip(items, paths):
        digest = _file_digest(path)
        if digest in seen:
            _remove_files([path])
            continue
        seen.add(digest)
        kept_items.append(item)
        kept_paths.append(path)
    if len(kept_paths) < len(paths):
        logger.info("dropped %d file(s) that came twice", len(paths) - len(kept_paths))
    return kept_items, kept_paths

def _remove_files(paths) -> None:
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            logger.warning("couldn't remove %s", path)

async def merge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The 📄 PDF and 🗜 ZIP buttons under a delivered album."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    kind, _, token = query.data[len(MERGE_PREFIX):].partition(":")

    remembered = context.user_data.get("redeliver", {}).get(token) if kind in ("pdf", "zip") else None
    if not remembered or not _spend_action(remembered, kind):
        if not remembered:
            note_tap("merge.expired")
        await query.answer(i18n.t(lang, "redeliver_expired"), show_alert=True)
        return
    await query.answer()

    await _take_button_off(query, lang, token, remembered)

    allowance = await asyncio.to_thread(download_allowance, update.effective_user.id)
    if not allowance["allowed"]:

        _unspend_action(remembered, kind)
        await _take_button_off(query, lang, token, remembered)
        await query.message.reply_text(_allowance_message(lang, allowance))
        return

    await asyncio.to_thread(record_download, update.effective_user.id, remembered["platform"])

    async def work():
        await _merge_and_send(update, context, kind, remembered["platform"], remembered["url"])

    _spawn_download(context, update, work)

async def _merge_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          kind: str, platform: str, url: str) -> bool:
    """Fetch the post again, build one PDF (its photos) or one ZIP (all of it), send it as a document, delete everything."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    user_id, chat_id = update.effective_user.id, update.effective_chat.id
    message = update.effective_message
    refusal = await refuse_new_work(lang, user_id, chat_id)
    if refusal:
        await message.reply_text(refusal)
        return False

    status = await LiveMessage.reply_to(message, i18n.t(lang, "fetching"))
    if _slots().locked() or _user_slots_full(user_id):
        await status.set(context.bot, i18n.t(lang, "queued"))

    paths: list[str] = []
    resolved = None

    out_path = os.path.join(resolvers._WORK_DIR, f"{uuid.uuid4().hex}.{kind}")
    async with _user_slot(user_id), _slots(), lifecycle.busy(
            chat_id, i18n.t(lang, "restarting_send_again")):

        _make_room(MERGE_MAX_MB * 2)
        free = _free_mb()
        if free is not None and free < MIN_FREE_MB:
            await status.set(context.bot, i18n.t(lang, "download_short_on_space"))
            return False
        try:
            try:
                resolved = await resolvers.resolve(platform, url)
            except resolvers.NothingWorked as exc:
                logger.info("no route worked for %s (merge): %s", platform, exc)
                if exc.kind not in ("missing", "too_big"):
                    note_job(False)
                raise _MergeStop({
                    "missing": "download_missing",
                    "blocked": "download_blocked",
                    "too_big": "merge_too_big",
                }.get(exc.kind, "download_all_routes_failed"))

            wanted = [item for item in resolved.items if item.kind == "photo"] \
                if kind == "pdf" else list(resolved.items)
            if kind == "pdf" and len(wanted) < merge.MIN_PDF_PHOTOS:
                raise _MergeStop("merge_no_photos")
            if len(wanted) > MERGE_MAX_ITEMS:
                raise _MergeStop("merge_too_big")

            await status.set(context.bot, i18n.t(lang, "downloading"))
            total = 0
            for item in wanted:
                paths.append(await resolvers.download(item))
                total += os.path.getsize(paths[-1])
                if total > MERGE_MAX_MB * 1024 * 1024:
                    raise _MergeStop("merge_too_big")
            wanted, paths[:] = await asyncio.to_thread(_without_duplicates, wanted, list(paths))

            if kind == "pdf":

                try:
                    await merge.build_pdf_queued(paths, out_path)
                except (merge.NothingToMerge, merge.NotAPhoto):

                    raise _MergeStop("merge_no_photos")
            else:
                await asyncio.to_thread(merge.build_zip, paths, out_path)
            if os.path.getsize(out_path) > large_files.BOT_API_SEND_BYTES:

                raise _MergeStop("merge_too_big")

            caption = None
            if await asyncio.to_thread(get_caption_enabled, user_id):
                caption = i18n.t(lang, "download_credit_caption", username=BOT_USERNAME)
            with open(out_path, "rb") as handle:

                await message.reply_document(
                    handle, filename=merge.output_name(platform, kind),
                    caption=caption, read_timeout=120, write_timeout=120,
                    disable_content_type_detection=True,
                )
            await status.delete(context.bot)
            note_job(True)
            note_stat("link_extra", f"album_{kind}")
        except _MergeStop as stop:
            await status.set(context.bot, _merge_text(lang, stop.key), **NO_PREVIEW)
            return False
        except net.TooLarge:
            await status.set(context.bot, _merge_text(lang, "merge_too_big"), **NO_PREVIEW)
            return False
        except merge.PictureTooLarge as exc:
            logger.info("merge refused a picture: %s", exc)
            await status.set(context.bot, _merge_text(lang, "merge_picture_too_big"), **NO_PREVIEW)
            return False
        except net.FetchError as exc:
            note_job(False)
            await status.set(context.bot, str(exc), **NO_PREVIEW)
            return False
        except Exception:
            note_job(False)
            logger.exception("Merging %s (%s) failed", platform, kind)
            await status.set(context.bot, _merge_text(lang, "merge_failed"), **NO_PREVIEW)
            return False
        finally:

            _remove_files(paths + [item.path for item in (resolved.items if resolved else [])]
                          + [out_path])

    await _after_send(update, context, lang)
    return True

async def _after_send(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    nudge = await maybe_donation_nudge(
        update.effective_user.id, lang, context, update.effective_chat.id)
    if nudge:
        await update.effective_message.reply_text(nudge)

def _image_extension(data: bytes) -> str:
    """Name a file after what it actually is."""
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"GIF8"):
        return "gif"
    if data[:2] == b"\xff\xd8":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "bin"

async def _reply_image_with_button(update, context, data: bytes, stem: str, lang: str,
                                   platform: str, url: str,
                                   lossless: bool | None = None):
    """An image, with the same "the other way round" button the media path puts under a video."""
    if lossless is None:
        lossless = await asyncio.to_thread(get_lossless_enabled, update.effective_user.id)
    token = _remember_delivery(context, platform, url, lossless)
    return await _reply_image(update, data, stem,
                              reply_markup=_nudge_kb(lang, token, lossless),
                              lossless=lossless)

async def _reply_image(update: Update, data: bytes, stem: str, reply_markup=None,
                       lossless: bool | None = None):
    """One image back, compressed as a photo or verbatim as a file -- see lossless_toggle for which and why."""
    if lossless is None:
        lossless = await asyncio.to_thread(get_lossless_enabled, update.effective_user.id)

    if lossless:
        return await update.effective_message.reply_document(
            document=BytesIO(data),
            filename=f"{stem}.{_image_extension(data)}",
            reply_markup=reply_markup,
            disable_content_type_detection=True,
        )
    return await update.effective_message.reply_photo(
        BytesIO(data), reply_markup=reply_markup)

@contextmanager
def _media_source(item, path):
    """What goes to Telegram for one file: its stored file id (sent_files.StoredFile), or the file on disk, opened to be streamed."""
    stored = getattr(item, "file_id", None)
    if stored:
        yield stored
    else:
        with open(path, "rb") as handle:
            yield handle

def _file_id_of(sent, kind: str, lossless: bool) -> "str | None":
    """The file id Telegram gave the message `sent`, or None when it does not carry the kind of file the form expects: a clip with no sound that Telegram turned into an animation, say."""
    try:
        if lossless:
            attached = sent.document
        elif kind == "video":
            attached = sent.video
        else:
            photos = sent.photo
            attached = photos[-1] if photos else None
        file_id = attached.file_id if attached is not None else None
    except (AttributeError, IndexError, TypeError):
        return None
    return file_id if isinstance(file_id, str) and file_id else None

async def _send_media(update, context, items_with_paths, lang,
                      lossless: bool | None = None, redeliver_token: str | None = None,
                      probing: "video.ProbeRun | None" = None) -> "list[tuple[str, str]] | None":
    """Put what was resolved into the chat."""
    caption = None
    if await asyncio.to_thread(get_caption_enabled, update.effective_user.id):
        caption = i18n.t(lang, "download_credit_caption", username=BOT_USERNAME)
    if lossless is None:
        lossless = await asyncio.to_thread(get_lossless_enabled, update.effective_user.id)
    if probing is None:
        probing = video.ProbeRun()

    async def shape_of(path: str) -> dict:
        """The keyword arguments that give a video its shape; none when it could not be measured."""
        if probing.exhausted:
            return {}
        shape = await video.probe(path, probing)
        if shape is None:
            return {}
        fields = {"width": shape.width, "height": shape.height}
        if shape.duration is not None:
            fields["duration"] = shape.duration
        return fields

    photos = sum(1 for item, _ in items_with_paths if item.kind == "photo")

    remembered = context.user_data.get("redeliver", {}).get(redeliver_token)
    if remembered is not None:
        remembered["photos"], remembered["items"] = photos, len(items_with_paths)
    keyboard = _nudge_kb(lang, redeliver_token, lossless, photos=photos, items=len(items_with_paths))

    message = update.effective_message

    if len(items_with_paths) == 1:
        item, path = items_with_paths[0]
        shape = (await shape_of(path) if item.kind == "video" and not lossless
                 and not getattr(item, "file_id", None) else {})

        with _media_source(item, path) as f:
            if lossless:
                sent = await message.reply_document(
                    f, filename=os.path.basename(item.filename or path),
                    caption=caption, reply_markup=keyboard,
                    read_timeout=120, write_timeout=120,
                    disable_content_type_detection=True,
                )
            elif item.kind == "video":
                sent = await message.reply_video(
                    f, caption=caption, reply_markup=keyboard,
                    read_timeout=120, write_timeout=120,
                    **shape,
                )
            else:
                sent = await message.reply_photo(
                    f, caption=caption, reply_markup=keyboard,
                    read_timeout=120, write_timeout=120,
                )
        file_id = _file_id_of(sent, item.kind, lossless)
        return [(item.kind, file_id)] if file_id else None

    sent_ids: "list[tuple[str, str]] | None" = []
    for chunk_start in range(0, len(items_with_paths), 10):
        chunk = items_with_paths[chunk_start:chunk_start + 10]
        shapes = [await shape_of(path) if item.kind == "video" and not lossless
                  and not getattr(item, "file_id", None) else {}
                  for item, path in chunk]
        handles = [getattr(item, "file_id", None) or open(path, "rb") for item, path in chunk]
        try:
            group = []
            for n, ((item, path), handle) in enumerate(zip(chunk, handles)):
                cap = caption if (chunk_start == 0 and n == 0) else None
                if lossless:
                    group.append(InputMediaDocument(
                        handle, filename=os.path.basename(item.filename or path),
                        caption=cap, disable_content_type_detection=True))
                elif item.kind == "video":
                    group.append(InputMediaVideo(handle, caption=cap, **shapes[n]))
                else:
                    group.append(InputMediaPhoto(handle, caption=cap))
            sent_group = await message.reply_media_group(
                group, read_timeout=120, write_timeout=120)
        finally:
            for handle in handles:
                if not isinstance(handle, str):
                    handle.close()
        try:
            sent_group = list(sent_group)
        except TypeError:
            sent_group = []
        file_ids = [_file_id_of(sent, item.kind, lossless) for (item, _), sent in zip(chunk, sent_group)]
        if sent_ids is not None and len(sent_group) == len(chunk) and all(file_ids):
            sent_ids += [(item.kind, file_id) for (item, _), file_id in zip(chunk, file_ids)]
        else:
            sent_ids = None

    if keyboard is not None:
        await message.reply_text(
            i18n.t(lang, "album_delivered", count=len(items_with_paths)),
            reply_markup=keyboard)
    return sent_ids

async def _store_sent_files(user_id: int, platform: str, url: str, lossless: bool, sent) -> None:
    """After a delivery from bytes: keep the file ids Telegram gave (sent_files.py), so the next person who sends this post gets it without a download."""
    if not sent_files.usable(user_id) or not sent:
        return
    try:
        text = sent_files.encode_items(sent)
        if text is None:
            return
        await asyncio.to_thread(sent_files_put, sent_files.post_key(platform, url, lossless), text)
        sent_files.note("stored")
    except Exception as exc:
        logger.warning("The sent-file store could not be written (%s)", type(exc).__name__)

async def _forget_sent_files(key: str) -> None:
    try:
        await asyncio.to_thread(sent_files_drop, key)
    except Exception as exc:
        logger.warning("The sent-file store could not drop a row (%s)", type(exc).__name__)

async def _resend_by_file_id(update, context, lang, status, platform: str, url: str,
                             lossless_override: "bool | None") -> "bool | None":
    """Send this post again from the file ids stored when it was last delivered (sent_files.py), if there are any and the post is known to be public still."""
    user_id = update.effective_user.id
    if not sent_files.usable(user_id):
        return None
    try:
        if lossless_override is None:
            lossless = await asyncio.to_thread(get_lossless_enabled, user_id)
        else:
            lossless = lossless_override
        key = sent_files.post_key(platform, url, lossless)
        row = await asyncio.to_thread(sent_files_get, key)
    except Exception as exc:

        logger.warning("The sent-file store could not be read (%s)", type(exc).__name__)
        sent_files.note("miss")
        return None
    pairs = sent_files.decode_items(row[0]) if row else None
    if pairs is None:
        sent_files.note("miss")
        return None
    fresh = sent_files.is_fresh(row[1])
    sent_files.note("hit" if fresh else "stale")

    async with lifecycle.busy(update.effective_chat.id, i18n.t(lang, "restarting_send_again")):
        if not fresh:
            try:
                async with _lookups():
                    verdict = await resolvers.lookup(platform, url)
            except Exception as exc:
                logger.warning("The post could not be looked up (%s)", type(exc).__name__)
                verdict = "unknown"
            sent_files.note(verdict if verdict in ("present", "missing") else "unknown")
            if verdict == "missing":
                await _forget_sent_files(key)
                return None
            if verdict != "present":
                return None
        token = _remember_delivery(context, platform, url, lossless)
        try:
            await _send_media(update, context, [(file, None) for file in sent_files.stored_files(pairs)], lang,
                              lossless=lossless, redeliver_token=token)
            await status.delete(context.bot)
            note_job(True)
            note_stat("link_site", platform)
        except Exception as exc:
            if isinstance(exc, BadRequest):

                await _forget_sent_files(key)
            if sent_files.is_invalid_file_id(exc):

                sent_files.note("invalid")
                logger.info("A stored file id was refused (%s)", type(exc).__name__)
                context.user_data.get("redeliver", {}).pop(token, None)
                return None
            note_job(False)

            logger.warning("Delivering %s from the stored file ids failed (%s)", platform,
                           type(exc).__name__)
            await status.set(context.bot,
                             i18n.t(lang, "download_failed", error=type(exc).__name__),
                             **NO_PREVIEW)
            return False
    try:

        await asyncio.to_thread(sent_files_used if fresh else sent_files_confirmed, key)
    except Exception as exc:
        logger.warning("The sent-file store could not be updated (%s)", type(exc).__name__)
    return True

async def _resolve_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            platform: str, url: str, status=None,
                            quiet_if_missing: bool = False,
                            lossless_override: bool | None = None,
                            from_redo: bool = False) -> bool:
    """The whole download path: pick a route that is working, fetch, send."""
    lang = await i18n.get_lang(update.effective_user.id, context)

    refusal = await refuse_new_work(
        lang, update.effective_user.id, update.effective_chat.id
    )
    if refusal:
        if status is None:
            await update.effective_message.reply_text(refusal)
        else:
            await status.set(context.bot, refusal)
        return False

    if status is None:
        status = await LiveMessage.reply_to(
            update.effective_message, i18n.t(lang, "fetching"))
    else:
        await status.set(context.bot, i18n.t(lang, "fetching"))

    resent = await _resend_by_file_id(update, context, lang, status, platform, url, lossless_override)
    if resent is not None:
        if resent:
            await _after_send(update, context, lang)
        return resent

    if _slots().locked() or _user_slots_full(update.effective_user.id):
        await status.set(context.bot, i18n.t(lang, "queued"))

    paths: list[str] = []
    async with _user_slot(update.effective_user.id), _slots(), lifecycle.busy(
            update.effective_chat.id, i18n.t(lang, "restarting_send_again")):

        cached = delivery_cache.take(update.effective_user.id, platform, url)
        if from_redo and delivery_cache.usable(update.effective_user.id):
            note_tap("redo.cache.hit" if cached is not None else "redo.cache.miss")
        if cached is not None:
            try:
                if lossless_override is None:
                    delivered_lossless = await asyncio.to_thread(
                        get_lossless_enabled, update.effective_user.id)
                else:
                    delivered_lossless = lossless_override
                token = _remember_delivery(context, platform, url, delivered_lossless)

                await _send_media(update, context, list(cached.items), lang,
                                  lossless=delivered_lossless, redeliver_token=token)
                await status.delete(context.bot)
                note_job(True)
                note_stat("link_site", platform)
            except Exception as exc:
                note_job(False)

                logger.warning("Delivering %s from the kept files failed (%s)", platform,
                               type(exc).__name__)
                await status.set(context.bot,
                                 i18n.t(lang, "download_failed", error=type(exc).__name__),
                                 **NO_PREVIEW)
                return False
            finally:
                delivery_cache.release(cached)
        else:
            free = _free_mb()
            if free is not None and free < MIN_FREE_MB:
                await status.set(context.bot, i18n.t(lang, "download_short_on_space"))
                return False
            try:
                resolved = await resolvers.resolve(platform, url)
            except resolvers.NothingWorked as exc:
                logger.info("no route worked for %s: %s", platform, exc)
                if exc.kind == "missing" and quiet_if_missing:
                    return False

                if exc.kind == "too_big" and large_files.CONFIGURED:
                    return await _large_download(update, context, status, lang, platform, url)
                if exc.kind not in ("missing", "too_big"):
                    note_job(False)
                key = {
                    "missing": "download_missing",
                    "blocked": "download_blocked",
                    "too_big": "download_too_big",
                }.get(exc.kind, "download_all_routes_failed")

                await status.set(context.bot, i18n.t(lang, key), **NO_PREVIEW)
                return False

            try:
                await status.set(context.bot, i18n.t(lang, "downloading"))
                items = resolved.items
                for item in items:
                    paths.append(await resolvers.download(item))
                if len(paths) > 1:
                    items, paths[:] = await asyncio.to_thread(_without_duplicates, items, list(paths))
                if lossless_override is None:
                    delivered_lossless = await asyncio.to_thread(
                        get_lossless_enabled, update.effective_user.id)
                else:
                    delivered_lossless = lossless_override
                token = _remember_delivery(context, platform, url, delivered_lossless)
                sent = await _send_media(update, context, list(zip(items, paths)), lang,
                                         lossless=delivered_lossless, redeliver_token=token)
                await status.delete(context.bot)
                note_job(True)
                note_stat("link_site", platform)
                for item in items:
                    note_stat("link_media", f"{platform}:{getattr(item, 'kind', None) or 'other'}")

                kept = delivery_cache.keep(update.effective_user.id, platform, url,
                                           list(zip(items, paths)), _cache_floor_mb())
                if delivery_cache.usable(update.effective_user.id):
                    note_tap("cache.kept" if kept else "cache.not_kept")
                if kept:
                    paths.clear()
                await _store_sent_files(update.effective_user.id, platform, url, delivered_lossless, sent)
            except net.TooLarge as exc:
                if not large_files.CONFIGURED:
                    await status.set(context.bot, str(exc), **NO_PREVIEW)
                    return False
                for path in paths:
                    if path and os.path.exists(path):
                        os.remove(path)
                paths.clear()
                return await _large_download(update, context, status, lang, platform, url)
            except net.FetchError as exc:
                note_job(False)
                await status.set(context.bot, str(exc), **NO_PREVIEW)
                return False
            except Exception as exc:
                note_job(False)
                logger.exception("Delivering %s via %s failed", platform, resolved.provider)
                await status.set(context.bot, i18n.t(lang, "download_failed", error=exc),
                                 **NO_PREVIEW)
                return False
            finally:
                for path in paths:
                    try:
                        if path and os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        logger.warning("couldn't remove %s", path)

    await _after_send(update, context, lang)
    return True

async def _large_download(update, context, status, lang, platform: str, url: str) -> bool:
    """A file over the free ceiling (large_files.py): refused with its price and the switch, or -- for somebody who has switched large files on -- fetched, charged once it is here, and sent."""
    chat_id, user_id = update.effective_chat.id, update.effective_user.id
    free, per = large_files.FREE_MAX_MB, large_files.first_price()
    if not large_files.available(chat_id):
        await status.set(context.bot, i18n.t(lang, "large_files_private_only", free=free))
        return False
    if not await asyncio.to_thread(get_large_files_enabled, user_id):
        offer = InlineKeyboardMarkup([[InlineKeyboardButton(
            i18n.t(lang, "large_files_turn_on_button"), callback_data="large:offer")]])
        await status.set(context.bot, i18n.t(lang, "large_files_off", free=free, per=per), reply_markup=offer)
        return False
    balance = await asyncio.to_thread(family_link.star_balance, user_id)
    if balance < per:
        await status.set(context.bot, i18n.t(lang, "large_files_no_credit", free=free, per=per, balance=balance))
        return False

    _make_room(large_files.LARGE_MAX_MB)
    await status.set(context.bot, i18n.t(lang, "large_files_fetching", free=free, per=per))
    paths: list[str] = []
    try:
        try:
            resolved = await resolvers.resolve(platform, url, max_mb=large_files.LARGE_MAX_MB)
            for item in resolved.items:
                paths.append(await resolvers.download(item, max_mb=large_files.LARGE_MAX_MB))
        except (resolvers.NothingWorked, net.TooLarge) as exc:
            too_big = isinstance(exc, net.TooLarge) or exc.kind == "too_big"
            if not too_big:
                note_job(False)
            await status.set(context.bot, i18n.t(lang, "large_files_too_big", max=large_files.LARGE_MAX_MB)
                             if too_big else i18n.t(lang, "download_all_routes_failed"), **NO_PREVIEW)
            return False
        except net.FetchError as exc:
            note_job(False)
            await status.set(context.bot, str(exc), **NO_PREVIEW)
            return False

        size = sum(os.path.getsize(path) for path in paths)
        mb = max(1, round(size / large_files.MB))
        price = large_files.price_for(size)
        after = await asyncio.to_thread(family_link.spend_stars, user_id, price, "spend",
                                        f"large download, {mb} MB")
        if after is None:
            balance = await asyncio.to_thread(family_link.star_balance, user_id)
            await status.set(context.bot, i18n.t(lang, "large_files_short", mb=mb, price=price, balance=balance))
            return False
        try:
            await status.set(context.bot, i18n.t(lang, "large_files_sending", mb=mb))
            await _send_large(update, context, list(zip(resolved.items, paths)), lang)
        except Exception:
            logger.exception("A large download of %s MB could not be sent", mb)
            note_job(False)
            back = await asyncio.to_thread(family_link.move_stars, user_id, price, "refund",
                                           "large download not delivered")
            await status.set(context.bot, i18n.t(lang, "large_files_send_failed", price=price, balance=back))
            return False
        note_job(True)
        note_stat("link_site", platform)
        note_stat("link_extra", "large_file")
        await status.set(context.bot, i18n.t(lang, "large_files_charged", mb=mb, price=price, balance=after))
        return True
    finally:
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError:
                logger.warning("couldn't remove %s", path)

async def _send_large(update, context, items_with_paths, lang) -> None:
    """What a large download fetched: anything over the Bot API's 50 MB goes over MTProto as a file, the rest as usual, one by one."""
    caption = None
    if await asyncio.to_thread(get_caption_enabled, update.effective_user.id):
        caption = i18n.t(lang, "download_credit_caption", username=BOT_USERNAME)
    probing = video.ProbeRun()
    for item, path in items_with_paths:
        if os.path.getsize(path) > large_files.BOT_API_SEND_BYTES:
            await big_files.send_document(update.effective_chat.id, path,
                                          os.path.basename(item.filename or path), caption or "")
        else:
            await _send_media(update, context, [(item, path)], lang, probing=probing)

async def _handle_reddit(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str,
                         lossless: bool | None = None):
    """Reddit is the one platform where the *text* is often the point, so the post is read first and only media posts go near the download path."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    status = await LiveMessage.reply_to(update.effective_message, i18n.t(lang, "fetching"))
    try:
        post = await platforms.fetch_reddit_post(url)
    except Exception as exc:
        await status.set(context.bot, i18n.t(lang, "reddit_fetch_failed", error=exc))
        return

    if platforms.reddit_is_media(post):
        direct_img = platforms.reddit_direct_image_url(post)
        if direct_img:
            try:
                image = await net.fetch_bytes(direct_img)
                await _reply_image_with_button(
                    update, context, image, "reddit", lang, "reddit", url, lossless)
                await status.delete(context.bot)
                await _after_send(update, context, lang)
                return
            except Exception:
                logger.exception("Reddit direct image fetch failed -- falling back")
        await _resolve_and_send(update, context, "reddit", url, status=status, lossless_override=lossless)
        return

    title = post.get("title", "")
    selftext = post.get("selftext", "")
    body = title if not selftext else title + "\n\n" + selftext
    subreddit = "r/" + post.get("subreddit", "?")
    author = "u/" + post.get("author", "?")
    score = post.get("score")
    meta = f"{score:,} upvotes" if isinstance(score, int) else ""

    png = await asyncio.to_thread(cards.render_card, "reddit", subreddit, author, body, meta)

    await _reply_image_with_button(
        update, context, png, "reddit_post", lang, "reddit", url, lossless)
    await status.delete(context.bot)
    await _after_send(update, context, lang)

async def _handle_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str,
                          lossless: bool | None = None):
    """Media first, card second."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    status = await LiveMessage.reply_to(update.effective_message, i18n.t(lang, "fetching"))
    if await _resolve_and_send(update, context, "twitter", url, status=status,
                               quiet_if_missing=True, lossless_override=lossless):
        return

    tweet = await platforms.fetch_tweet_syndication(url)
    if tweet:

        user = tweet.get("user") or {}
        handle = user.get("screen_name")
        source = f"@{handle}" if handle else "Twitter/X"
        author = user.get("name", "")
        likes = tweet.get("favorite_count")
        meta = f"{likes:,} likes" if isinstance(likes, int) else ""
        png = await asyncio.to_thread(
            cards.render_card, "twitter", source, author, tweet.get("text", ""), meta)
        await _reply_image_with_button(
            update, context, png, "tweet", lang, "twitter", url, lossless)
        await status.delete(context.bot)
        await _after_send(update, context, lang)
        return

    await status.set(context.bot, i18n.t(lang, "twitter_fetch_failed_link", url=url))

def _allowance_message(lang: str, allowance: dict) -> str:
    """What somebody who has run out is told."""
    key = ("quota_hour" if allowance["scope"] == "hour" else "quota_day")
    text = i18n.t(lang, key, used=allowance[allowance["scope"]],
                  limit=allowance[f"{allowance['scope']}_max"],
                  minutes=allowance["wait_min"])
    if not allowance["donor"]:
        text += "\n\n" + i18n.t(lang, "quota_donor_hint")
    return text + problems.code_line("DL-QUOTA-HOUR" if allowance["scope"] == "hour" else "DL-QUOTA-DAY")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    detected = platforms.detect_platform(update.message.text)
    if not detected:
        return
    platform, url = detected

    found = delivery_cache.note_link(update.effective_user.id, platform, url)
    if found == delivery_cache.NOTED_AGAIN_CACHED:
        note_tap("link.again.cached")
    elif found == delivery_cache.NOTED_AGAIN_NOT_CACHED:
        note_tap("link.again.not_cached")

    key = (update.effective_chat.id, update.effective_user.id, platform, url)
    if _already_in_flight(key):
        await _answer_duplicate(update)
        return
    stamp = _in_flight[key] = time.monotonic()
    spawned = False
    try:

        lang = await i18n.get_lang(update.effective_user.id, context)
        refusal = await refuse_new_work(lang, update.effective_user.id, update.effective_chat.id)
        if refusal:
            await update.message.reply_text(refusal)
            return

        if _user_pending.get(update.effective_user.id, 0) >= MAX_PENDING_PER_USER:
            await update.message.reply_text(
                i18n.t(lang, "download_queue_full", count=MAX_PENDING_PER_USER))
            return
        allowance = await asyncio.to_thread(download_allowance, update.effective_user.id)
        if not allowance["allowed"]:
            await update.message.reply_text(_allowance_message(lang, allowance))
            return
        await asyncio.to_thread(record_download, update.effective_user.id, platform)

        async def work():
            if platform == "reddit":
                await _handle_reddit(update, context, url)
            elif platform == "twitter":
                await _handle_twitter(update, context, url)
            else:
                await _resolve_and_send(update, context, platform, url)

        _spawn_download(context, update, work, in_flight=key)
        spawned = True
    finally:

        if not spawned:
            _clear_in_flight(key, stamp)

async def unrecognized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches anything that isn't a recognized link and isn't a known command -- registered last, so it only fires when nothing else already handled the update."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "unrecognized_message"))

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "unknown_command"))

async def _delete_my_data_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The shared erase button, and what only this bot holds on top of what it erases: the person's kept delivery (delivery_cache.py), and the memory the redo buttons read their links from."""
    query = update.callback_query
    if query is not None and query.data == ERASE_PREFIX + "yes":
        delivery_cache.forget_user(update.effective_user.id)
        context.user_data.pop("redeliver", None)
    return await delete_my_data_chosen(update, context)

async def _post_init(application):
    await tune_runtime(application)

    try:
        resolvers.load(await asyncio.to_thread(load_provider_health))
    except Exception:
        logger.warning("couldn't load provider health -- starting from scratch",
                       exc_info=True)
    if application.job_queue is not None:
        application.job_queue.run_repeating(
            _flush_provider_health,
            interval=PROVIDER_HEALTH_FLUSH_SECONDS,
            first=PROVIDER_HEALTH_FLUSH_SECONDS,
        )

    routewatch.schedule(application)

    await lifecycle.on_start(BOT_NAME)

    delivery_cache.wipe()
    if application.job_queue is not None:
        application.job_queue.run_repeating(
            _sweep_delivery_cache, interval=DELIVERY_CACHE_SWEEP_SECONDS,
            first=DELIVERY_CACHE_SWEEP_SECONDS)
    await publish_commands(application, BOT_COMMANDS, ADMIN_COMMANDS, ADMIN_IDS)
    await publish_profile(application)
    if big_files.CONFIGURED:
        task = asyncio.get_running_loop().create_task(_check_big_files())
        _background.add(task)
        task.add_done_callback(_background.discard)

DELIVERY_CACHE_SWEEP_SECONDS = 15

async def _sweep_delivery_cache(_context=None) -> None:
    try:
        delivery_cache.sweep()
    except Exception as exc:
        logger.warning("The delivery cache sweep failed (%s)", type(exc).__name__)

async def _check_big_files() -> None:
    """In the background, as the bot starts: an API id and hash that are set but wrong turn large files off here -- no switch, 48 MB, as if they were not set -- instead of failing the first person who asks for one."""
    if await big_files.verify() or big_files.VERIFIED is not False:
        return
    logger.warning("Large files are off: %s.", big_files.describe())
    family_link.report_event_soon("warning", "big_files", f"DownloaderBot: {big_files.describe()}.")

_background: set = set()

async def _post_stop(application):

    await _flush_provider_health()
    await net.close_client()
    await big_files.close()

    await lifecycle.on_stop(application)
    await flush_on_shutdown(application)

def main():
    if not BOT_TOKEN or not BOT_USERNAME:
        raise SystemExit("Set DBOT_TOKEN and DBOT_USERNAME environment variables first.")

    init_db()
    builder = (
        ApplicationBuilder().token(BOT_TOKEN)
        .post_init(_post_init).post_stop(_post_stop)
    )

    state = lifecycle.persistence()
    if state is not None:
        builder = builder.persistence(state)
    app = builder.build()
    lifecycle.install(app, BOT_NAME, ADMIN_IDS)
    app.add_error_handler(error_handler)
    attach_problem_reports(app)

    app.add_handler(TypeHandler(Update, track_activity), group=-4)

    attach_flood_gate(app, ADMIN_IDS)

    attach_promo_claim(app)

    app.add_handler(MessageHandler((filters.TEXT | filters.REPLY) & ~filters.COMMAND,
                                   awaited_text_received), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("fullhelp", full_help_command(build_help_text, None, HELP_PAGES, HELP_LABELS)))
    app.add_handler(CallbackQueryHandler(help_toggle(build_help_text, None, HELP_PAGES, HELP_LABELS),
                                         pattern=HELP_TOGGLE_PATTERN))
    app.add_handler(CallbackQueryHandler(help_page_button(HELP_PAGES), pattern=HELP_PAGE_PATTERN))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("caption", caption_toggle))
    app.add_handler(CommandHandler("lossless", lossless_toggle))
    app.add_handler(CommandHandler("dbdump", dbdump_command))
    app.add_handler(CommandHandler("messageas", messageas_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("providers", providers_command))
    app.add_handler(CallbackQueryHandler(caption_toggle_callback, pattern="^caption:"))
    app.add_handler(CallbackQueryHandler(lossless_toggle_callback, pattern="^lossless:"))
    app.add_handler(CallbackQueryHandler(large_toggle_callback, pattern="^large:"))
    app.add_handler(CallbackQueryHandler(redeliver_callback, pattern="^redo:"))
    app.add_handler(CallbackQueryHandler(merge_callback, pattern="^merge:"))
    app.add_handler(CallbackQueryHandler(cancel_choice_callback, pattern="^cancelpick:"))
    app.add_handler(CallbackQueryHandler(language_chosen, pattern="^setlang:"))
    app.add_handler(CommandHandler("language", language_command))

    app.add_handler(CommandHandler("en", set_language_en))
    app.add_handler(CommandHandler("uz", set_language_uz))
    app.add_handler(CommandHandler("rus", set_language_rus))

    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler("paysupport", paysupport_command))
    app.add_handler(CallbackQueryHandler(problem_report_callback, pattern=r"^rpt"))
    app.add_handler(CommandHandler("deletemydata", delete_my_data_command))
    app.add_handler(CallbackQueryHandler(_delete_my_data_chosen, pattern="^" + ERASE_PREFIX))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(platforms.ANY_LINK_RE), handle_link))

    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CallbackQueryHandler(donate_amount_chosen, pattern="^donate:"))
    app.add_handler(CallbackQueryHandler(donate_fiat_amount_chosen, pattern="^donatefiat:"))
    app.add_handler(CallbackQueryHandler(donate_custom_button_chosen, pattern="^donatecustom:"))
    app.add_handler(PreCheckoutQueryHandler(donation_precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, donation_payment_callback))

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unrecognized_message))

    family_link.attach(app, BOT_NAME, "DownloaderBot", START_TIME)

    family_link.COMMANDS["probe"] = _bus_probe
    family_link.COMMAND_HELP["probe"] = (
        "probe [platform|url ...] -- try every download route from in here")
    family_link.COMMANDS["routewatch"] = _bus_routewatch
    family_link.COMMAND_HELP["routewatch"] = (
        "the daily route check, now: which platforms have a way in, and is yt-dlp current")
    family_link.COMMANDS["providers"] = _bus_providers
    family_link.COMMAND_HELP["providers"] = (
        "which download route is working and which is resting")
    attach_maintenance(app)

    logger.info("Bot starting (polling)...")

    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY, Update.PRE_CHECKOUT_QUERY],
    ))

if __name__ == "__main__":
    main()

# ─── module: anon_bot.bot ────────────────────────────────────────────────────
"""AnonBot -- one-sided anonymous inbox, 4th bot in the family (see ARCHITECTURE.md)."""
import asyncio
import html
import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import (
    BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
    LinkPreviewOptions, Update,
)

NO_PREVIEW = {"link_preview_options": LinkPreviewOptions(is_disabled=True)}
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    ApplicationBuilder,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    MessageReactionHandler,
    PreCheckoutQueryHandler,
    TypeHandler,
    filters,
)

import family_link
import i18n
import lifecycle
import live_message
import shared_features
from live_message import LiveMessage, edit_in_place
from anon_logic import (
    REACTION_NOTE_SECONDS,
    RELAYABLE_REACTIONS,
    message_allowed,
    new_conversation_allowed,
    pick_reaction,
    reaction_note_allowed,
    relay_content,
)
from db import (
    CONVERSATIONS_PER_PAGE,
    RELAY_RETENTION_DAYS,
    claim_promo_seen,
    claim_reactions_note,
    clear_follower_state,
    count_owner_conversation_states,
    first_relay_message,
    get_active_conversation_for_follower,
    get_anon_link_state,
    get_anon_stats,
    get_conversation,
    get_conversation_for_relay,
    get_reaction_route,
    get_relay_row,
    get_routing_context,
    list_owner_conversations,
    set_conversation_archived,
    list_anon_blocks_with_conversations,
    get_delivery_context,
    get_link_view,
    get_or_create_anon_link,
    get_user_language,
    set_user_language,
    init_db,
    record_relay_and_touch,
    record_anon_relays,
    mark_follower_opened,
    regenerate_anon_link,
    set_anon_blocked,
    set_anon_link_paused,
    start_new_anon_conversation,
    dump_database_csv_zip,
    count_active_users_since,
)
from shared_features import (
    note_stat,
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
    problem_report_callback,
    attach_flood_gate,
    attach_maintenance,
    awaited_text_received,
    feedback_command,
    FORCE_REPLY_KEY,
    HELP_PAGE_PATTERN,
    HELP_TOGGLE_PATTERN,
    full_help_command,
    help_page_button,
    help_page_name,
    help_page_text,
    help_keyboard,
    help_toggle,
    wants_full_help,
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
    donate_amount_chosen,
    donate_fiat_amount_chosen,
    donate_custom_button_chosen,
    balance_command,
    donate_command,
    donation_payment_callback,
    donation_precheckout_callback,
    maybe_donation_nudge,
    refuse_new_work,
    sibling_bots_blurb,
    sibling_bots_keyboard_row,
    setup_logging,
    error_handler,
    track_activity,
    build_status_text,
)

setup_logging(__file__)
logger = logging.getLogger(__name__)

START_TIME = datetime.now(timezone.utc)

BOT_TOKEN = os.environ.get("ABOT_TOKEN")

BOT_USERNAME = (os.environ.get("ABOT_USERNAME") or "").strip().lstrip("@") or None
BOT_NAME = "anonbot"

ADMIN_IDS = {int(x) for x in os.environ.get("ABOT_ADMIN_ID", "").split(",") if x.strip()}

POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "30"))

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
async def _deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """How an owner-only command answers everybody else: exactly the way a misspelling does."""
    await unknown_command(update, context)

async def _reply(update: Update, text: str, **kwargs):
    """Works whether this came from a command or a button tap -- the first-run language picker means a brand-new user can reach any of these paths from a callback query, which has no message of its own to reply to."""
    if update.message:
        return await LiveMessage.reply_to(update.message, text, **kwargs)
    return await edit_in_place(update.callback_query.message, update.get_bot(), text, **kwargs)

def build_help_text(lang: str, full: bool = False) -> str:
    """The short version unless asked for the long one -- the family's help template (shared_features, "/help in two lengths")."""
    if not full:
        text = i18n.t(lang, "help_brief").rstrip("\n")
    else:
        text = i18n.t(lang, "help_text", reactions=" ".join(RELAYABLE_REACTIONS)).rstrip("\n")
    blurb = sibling_bots_blurb(BOT_NAME, lang)
    return text + "\n\n" + blurb if blurb else text

def _help_page_link(lang: str) -> str:
    return i18n.t(lang, "helppage_link")

def _help_page_which(lang: str) -> str:

    return i18n.t(lang, "helppage_which", example=i18n.t(lang, "which_owner", conv_number=4))

HELP_PAGES = {"link": _help_page_link, "which": _help_page_which}
HELP_ALIASES = {}

BOT_COMMANDS = [

    BotCommand("start", "What I do, and how to start"),
    BotCommand("language", "Choose your language / Tilni tanlash / Выбрать язык"),
    BotCommand("link", "Your inbox link, and its settings"),
    BotCommand("conversations", "Your conversations"),
    BotCommand("which", "Which conversation is this? — reply to a message"),
    BotCommand("blocked", "Who you have blocked"),
    BotCommand("cancel", "Stop whatever I am waiting for"),
    BotCommand("help", "Everything I can do"),
    BotCommand("feedback", "Suggest something, or report a problem"),
    BotCommand("balance", "Your ⚡ credit"),
    BotCommand("donate", "Chip in for hosting costs"),
    BotCommand("paysupport", "Trouble with a payment"),
    BotCommand("privacy", "What I keep about you"),
    BotCommand("terms", "What I may be used for"),
    BotCommand("deletemydata", "Delete everything I hold on you"),
]

ADMIN_COMMANDS = [
    BotCommand("status", "🔒 Uptime, host, errors, active users"),
    BotCommand("messageas", "🔒 messageas <user_id> <text> — DM as this bot"),
    BotCommand("dbdump", "🔒 This bot's tables as a zip of CSVs"),
]

def _link_url(token: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start=q_{token}"

def _incoming_keyboard(conversation_id: int, lang: str) -> InlineKeyboardMarkup:
    """Under a message arriving in the OWNER's chat."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(i18n.t(lang, "reply_button"), callback_data=f"aq_reply:{conversation_id}"),
                InlineKeyboardButton(i18n.t(lang, "block_button"), callback_data=f"aq_block:{conversation_id}"),
            ]
        ]
    )

def _follower_keyboard(conversation_id: int, lang: str) -> InlineKeyboardMarkup:
    """Under a message arriving in the GUEST's chat."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(i18n.t(lang, "reply_button"), callback_data=f"aq_reply:{conversation_id}")]]
    )

async def _continue_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, args):
    if args and args[0].startswith("q_"):
        return await start_follow_link(update, context, args[0][2:], lang)

    await _reply(
        update,
        i18n.t(lang, "start_greeting") + build_help_text(lang),
        reply_markup=help_keyboard(lang, False, [sibling_bots_keyboard_row(BOT_NAME)], HELP_PAGES),
    )

    await _knows_reactions(context, update.effective_user.id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start prints the instructions -- except the very first one, which asks for a language first."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    if lang is None:
        context.user_data["pending_start_args"] = context.args
        await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
        return

    context.user_data["lang"] = lang
    if context.args:
        await _continue_start(update, context, lang, context.args)
        return

    context.user_data.pop("pending_start_args", None)
    await _continue_start(update, context, lang, None)

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/language -- the picker on demand, which is what /start used to be."""
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)

    if lang:
        context.user_data["lang"] = lang
    await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard(lang))

async def _apply_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """The single path every language change goes through -- /en, /uz, /rus and a tap on the picker alike -- so all four end the same way: with the instructions, printed in the language just chosen."""
    await asyncio.to_thread(set_user_language, update.effective_user.id, lang)
    context.user_data["lang"] = lang

    await refresh_chat_menu(context, update.effective_user.id, lang)
    pending = context.user_data.pop("pending_start_args", None) or []
    await _continue_start(update, context, lang, pending)

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
    """A tap on the picker."""
    query = update.callback_query
    lang = query.data.split(":", 1)[1]
    await query.answer(i18n.t(lang, "language_set_confirmation"))
    await _apply_language(update, context, lang)

async def start_follow_link(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, lang: str):
    follower = update.effective_user

    owner_id, is_paused, blocked = await asyncio.to_thread(
        get_link_view, token, follower.id
    )
    if owner_id is None:
        await _reply(update, i18n.t(lang, "follow_link_invalid"))
        return

    if owner_id == follower.id:
        await _reply(update, i18n.t(lang, "follow_link_own"))
        return

    if blocked:
        await _reply(update, i18n.t(lang, "follow_link_blocked"))
        return

    if is_paused:
        await _reply(update, i18n.t(lang, "follow_link_paused"))
        return

    wait = new_conversation_allowed(follower.id)
    if wait:
        await _reply(update, i18n.t(lang, "too_fast", seconds=wait))
        return

    refusal = await refuse_new_work(lang, follower.id, update.effective_chat.id)
    if refusal:
        await _reply(update, refusal)
        return

    conv = await asyncio.to_thread(start_new_anon_conversation, owner_id, follower.id)

    opening = await context.bot.send_message(
        chat_id=update.effective_chat.id,

        text=i18n.t(lang, "follow_link_started"),
    )
    live_message.bump(opening.chat_id, opening.message_id)

    await asyncio.to_thread(
        record_anon_relays, follower.id, [opening.message_id], conv["id"]
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help is the short version; /help full is the long one."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    page = help_page_name(context, HELP_PAGES, HELP_ALIASES)
    if page:

        await update.message.reply_text(help_page_text(lang, HELP_PAGES, page),
                                        link_preview_options=shared_features.NO_PREVIEW)
        return
    full = wants_full_help(context)
    await update.message.reply_text(build_help_text(lang, full=full),
                                    reply_markup=help_keyboard(lang, full, (), HELP_PAGES))
    await _knows_reactions(context, update.effective_user.id)

_full_help = full_help_command(build_help_text, None, HELP_PAGES)

async def fullhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/fullhelp: what /help full gives -- which lists every reaction, so whoever reads it has been told about reactions too."""
    await _full_help(update, context)
    await _knows_reactions(context, update.effective_user.id)

def _link_message(token: str, paused: bool, lang: str, note: str = "",
                  stats: "dict | None" = None) -> tuple[str, InlineKeyboardMarkup]:
    """Shared by /link and its Pause/Resume/New-link buttons, so tapping one edits the same message back into an up-to-date version of itself instead of you needing to type /pause, /resume, or /newlink by hand."""
    status = i18n.t(lang, "link_status_paused" if paused else "link_status_active")
    text = i18n.t(lang, "link_message", status=status, url=html.escape(_link_url(token)))
    if stats:
        text += "\n\n" + i18n.t(lang, "stats_message",
                                 followers=stats["distinct_followers"],
                                 conversations=stats["conversations"])
    if note:
        text = f"{note}\n\n{text}"
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    i18n.t(lang, "link_button_resume" if paused else "link_button_pause"),
                    callback_data="anonlink:toggle",
                ),
                InlineKeyboardButton(i18n.t(lang, "link_button_newlink"), callback_data="anonlink:newlink"),
            ]
        ]
    )
    return text, kb

async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = update.effective_user
    lang = await i18n.get_lang(owner.id, context)
    token, is_paused = await asyncio.to_thread(get_or_create_anon_link, owner.id)
    stats = await asyncio.to_thread(get_anon_stats, owner.id)
    text, kb = _link_message(token, is_paused, lang, stats=stats)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb, **NO_PREVIEW)

async def anonlink_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    owner_id = update.effective_user.id
    lang = await i18n.get_lang(owner_id, context)
    state = await asyncio.to_thread(get_anon_link_state, owner_id)
    if not state:
        await query.answer(i18n.t(lang, "anonlink_no_link_yet"), show_alert=True)
        return
    new_paused = not state["is_paused"]
    await asyncio.to_thread(set_anon_link_paused, owner_id, new_paused)
    await query.answer(i18n.t(lang, "anonlink_paused_answer" if new_paused else "anonlink_resumed_answer"))
    stats = await asyncio.to_thread(get_anon_stats, owner_id)
    text, kb = _link_message(state["token"], new_paused, lang, stats=stats)
    await edit_in_place(query.message, context.bot, text, parse_mode=ParseMode.HTML,
                        reply_markup=kb, **NO_PREVIEW)

async def anonlink_newlink_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    owner_id = update.effective_user.id
    lang = await i18n.get_lang(owner_id, context)

    token, is_paused = await asyncio.to_thread(regenerate_anon_link, owner_id)
    await query.answer(i18n.t(lang, "anonlink_newlink_answer"))
    stats = await asyncio.to_thread(get_anon_stats, owner_id)
    text, kb = _link_message(token, is_paused, lang, stats=stats)
    await edit_in_place(query.message, context.bot, text, parse_mode=ParseMode.HTML,
                        reply_markup=kb, **NO_PREVIEW)

async def newlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = update.effective_user
    lang = await i18n.get_lang(owner.id, context)
    token, _ = await asyncio.to_thread(regenerate_anon_link, owner.id)
    await update.message.reply_text(
        i18n.t(lang, "newlink_message", url=html.escape(_link_url(token))),
        parse_mode=ParseMode.HTML,
        **NO_PREVIEW,
    )

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = update.effective_user
    lang = await i18n.get_lang(owner.id, context)
    await asyncio.to_thread(get_or_create_anon_link, owner.id)
    await asyncio.to_thread(set_anon_link_paused, owner.id, True)
    await update.message.reply_text(i18n.t(lang, "pause_message"))

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await asyncio.to_thread(set_anon_link_paused, update.effective_user.id, False)
    await update.message.reply_text(i18n.t(lang, "resume_message"))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    stats = await asyncio.to_thread(get_anon_stats, update.effective_user.id)
    await update.message.reply_text(
        i18n.t(lang, "stats_message", followers=stats["distinct_followers"], conversations=stats["conversations"])
    )

async def dbdump_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dbdump -- exports every table in this bot's own database as one zip of CSVs."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    status = await LiveMessage.reply_to(update.message, "Exporting the database...")
    try:
        data = await asyncio.to_thread(dump_database_csv_zip)
    except Exception as exc:
        await status.set(context.bot, f"⚠️ Export failed: {exc}")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    await update.message.reply_document(document=BytesIO(data), filename=f"anonbot_db_{stamp}.zip")
    await status.delete(context.bot)

async def messageas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/messageas <user_id> <text> -- sends a message to that user as this bot."""
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
    """/status -- uptime, hosting environment, any crashes since this process started, and active-user counts."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    now = datetime.now(timezone.utc)
    users_hour = await asyncio.to_thread(count_active_users_since, now - timedelta(hours=1))
    users_since_start = await asyncio.to_thread(count_active_users_since, START_TIME)
    await update.message.reply_text(build_status_text(START_TIME, users_hour, users_since_start))

async def _blocked_list_text_and_kb(owner_id: int, lang: str):
    rows = await asyncio.to_thread(list_anon_blocks_with_conversations, owner_id)
    if not rows:
        return i18n.t(lang, "blocked_none"), None
    lines = [i18n.t(lang, "blocked_header")]
    kb = []
    for conversation_id, conv_numbers in rows:

        if conv_numbers:
            joined = ", ".join(f"#{n}" for n in conv_numbers)
            line = i18n.t(lang, "blocked_guest_line", conversations=joined)
            button = i18n.t(lang, "blocked_unblock_button", conversations=joined)
        else:
            line = i18n.t(lang, "blocked_guest_line_unknown")
            button = i18n.t(lang, "blocked_unblock_button_unknown")
        lines.append(line)
        if conversation_id is not None:
            kb.append([InlineKeyboardButton(button, callback_data=f"aq_unblockg:{conversation_id}")])
    return "\n".join(lines), InlineKeyboardMarkup(kb) if kb else None

async def blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    text, kb = await _blocked_list_text_and_kb(update.effective_user.id, lang)
    await update.message.reply_text(text, reply_markup=kb)

CONVS_PREFIX = "aq_convs:"
CONV_CARD_PREFIX = "aq_conv:"
CONV_ARCH_PREFIX = "aq_arch:"
CONV_JUMP_PREFIX = "aq_jump:"

def _ago(lang: str, when: str | None) -> str:
    """How long ago, in whole units, with no date and no clock time in it."""
    if not when:
        return i18n.t(lang, "rel_now")
    try:
        seen = datetime.fromisoformat(when)
    except (TypeError, ValueError):
        return i18n.t(lang, "rel_now")
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now(timezone.utc) - seen).total_seconds()))
    if seconds < 90:
        return i18n.t(lang, "rel_now")
    if seconds < 3600:
        return i18n.t(lang, "rel_minutes", n=seconds // 60)
    if seconds < 86400:
        return i18n.t(lang, "rel_hours", n=seconds // 3600)
    return i18n.t(lang, "rel_days", n=seconds // 86400)

async def _conversations_view(owner_id: int, lang: str, archived: bool, page: int):
    """The list message: what it says and what is under it."""
    counts = await asyncio.to_thread(count_owner_conversation_states, owner_id)
    total = counts["archived"] if archived else counts["open"]
    pages = max(1, -(-total // CONVERSATIONS_PER_PAGE))
    page = max(0, min(page, pages - 1))
    rows = await asyncio.to_thread(
        list_owner_conversations, owner_id, archived,
        page * CONVERSATIONS_PER_PAGE, CONVERSATIONS_PER_PAGE,
    )

    text = (i18n.t(lang, "convs_title_archived" if archived else "convs_title") + "\n"
            + i18n.t(lang, "convs_summary_blocked" if counts["blocked"] else "convs_summary",
                     **counts))
    if not rows:
        text += "\n\n" + i18n.t(lang, "convs_empty_archived" if archived else "convs_empty_open")

    here = f"{1 if archived else 0}:{page}"
    kb = [
        [InlineKeyboardButton(
            i18n.t(lang, "convs_row_button", conv_number=row["conv_number"],
                   when=_ago(lang, row["last_activity_at"])),
            callback_data=f"{CONV_CARD_PREFIX}{row['id']}:{here}")]
        for row in rows
    ]
    if pages > 1:
        flag = 1 if archived else 0
        kb.append([
            InlineKeyboardButton(i18n.t(lang, "convs_prev"),
                                 callback_data=f"{CONVS_PREFIX}{flag}:{max(0, page - 1)}"),
            InlineKeyboardButton(i18n.t(lang, "convs_page", page=page + 1, pages=pages),
                                 callback_data=f"{CONVS_PREFIX}{flag}:{page}"),
            InlineKeyboardButton(i18n.t(lang, "convs_next"),
                                 callback_data=f"{CONVS_PREFIX}{flag}:{min(pages - 1, page + 1)}"),
        ])
    kb.append([InlineKeyboardButton(
        i18n.t(lang, "convs_show_open" if archived else "convs_show_archived"),
        callback_data=f"{CONVS_PREFIX}{0 if archived else 1}:0")])
    return text, InlineKeyboardMarkup(kb)

def _conversation_card(conv: dict, lang: str, archived: bool, page: int):
    """One conversation, and the two things that can be done to it from here."""
    is_archived = conv.get("archived_at") is not None
    text = i18n.t(lang, "conv_card", conv_number=conv["conv_number"],
                  started=_ago(lang, conv.get("started_at")),
                  when=_ago(lang, conv.get("last_activity_at")))
    if is_archived:
        text += "\n" + i18n.t(lang, "conv_card_archived",
                              archived=_ago(lang, conv.get("archived_at")))
    back = f"{1 if archived else 0}:{page}"
    kb = [
        [InlineKeyboardButton(i18n.t(lang, "conv_jump_button"),
                              callback_data=f"{CONV_JUMP_PREFIX}{conv['id']}")],
        [
            InlineKeyboardButton(
                i18n.t(lang, "conv_unarchive_button" if is_archived else "conv_archive_button"),
                callback_data=f"{CONV_ARCH_PREFIX}{conv['id']}:{0 if is_archived else 1}:{back}"),
            InlineKeyboardButton(i18n.t(lang, "conv_back_button"),
                                 callback_data=f"{CONVS_PREFIX}{back}"),
        ],
    ]
    return text, InlineKeyboardMarkup(kb)

async def _owned_conversation(update, context, args, lang: str):
    """The conversation a card button names, if it is this user's to act on."""
    conv = (await asyncio.to_thread(get_conversation, args[0])) if args else None
    if not conv or conv["owner_user_id"] != update.effective_user.id:
        await update.callback_query.answer(i18n.t(lang, "conv_gone"), show_alert=True)
        return None
    return conv

async def conversations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    text, kb = await _conversations_view(update.effective_user.id, lang, False, 0)
    await update.message.reply_text(text, reply_markup=kb)

async def conversations_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Page turns and the Open/Archived switch, both of which are just "draw the list again with different arguments"."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    args = _callback_ints(query, 2)
    await query.answer()
    if args is None:
        return
    text, kb = await _conversations_view(
        update.effective_user.id, lang, bool(args[0]), args[1])
    await edit_in_place(query.message, context.bot, text, reply_markup=kb)

async def conversation_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    args = _callback_ints(query, 3)
    conv = await _owned_conversation(update, context, args, lang)
    if conv is None:
        return
    await query.answer()
    text, kb = _conversation_card(conv, lang, bool(args[1]), args[2])
    await edit_in_place(query.message, context.bot, text, reply_markup=kb)

async def conversation_archive_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filing, and nothing more."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    args = _callback_ints(query, 4)
    conv = await _owned_conversation(update, context, args, lang)
    if conv is None:
        return
    archive = bool(args[1])
    await asyncio.to_thread(set_conversation_archived, conv["id"],
                            update.effective_user.id, archive)
    await query.answer(i18n.t(lang, "conv_archived_answer" if archive
                              else "conv_unarchived_answer"))
    conv["archived_at"] = datetime.now(timezone.utc).isoformat() if archive else None
    text, kb = _conversation_card(conv, lang, bool(args[2]), args[3])
    await edit_in_place(query.message, context.bot, text, reply_markup=kb)

ARCH_CMD_PREFIX = "aq_archcmd:"

async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = update.effective_user.id
    lang = await i18n.get_lang(user_id, context)
    target = message.reply_to_message
    if target is None:
        await message.reply_text(i18n.t(lang, "archive_needs_reply"))
        return

    conversation_id = await asyncio.to_thread(
        get_conversation_for_relay, message.chat_id, target.message_id)
    conv = (await asyncio.to_thread(get_conversation, conversation_id)
            if conversation_id else None)
    if not conv or user_id not in (conv["owner_user_id"], conv["follower_user_id"]):
        await message.reply_text(i18n.t(lang, "which_unknown"))
        return

    if conv["owner_user_id"] != user_id:
        await message.reply_text(i18n.t(lang, "archive_not_owner"))
        return
    if conv.get("archived_at"):
        await message.reply_text(
            i18n.t(lang, "archive_already", conv_number=conv["conv_number"]))
        return

    await message.reply_text(
        i18n.t(lang, "archive_confirm", conv_number=conv["conv_number"]),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                i18n.t(lang, "archive_button_yes", conv_number=conv["conv_number"]),
                callback_data=f"{ARCH_CMD_PREFIX}{conv['id']}:1"),
            InlineKeyboardButton(i18n.t(lang, "archive_button_no"),
                                 callback_data=f"{ARCH_CMD_PREFIX}{conv['id']}:0"),
        ]]),
    )

async def archive_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The answer to that question."""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = await i18n.get_lang(user_id, context)
    try:
        conv_id, archive = (int(part) for part in query.data.split(":")[1:3])
    except (ValueError, IndexError):
        await query.answer()
        return
    await query.answer()
    if not archive:
        await edit_in_place(query.message, context.bot, i18n.t(lang, "archive_kept"))
        return

    conv = await asyncio.to_thread(get_conversation, conv_id)
    if not conv or conv["owner_user_id"] != user_id:
        await edit_in_place(query.message, context.bot, i18n.t(lang, "conv_gone"))
        return
    if conv.get("archived_at"):
        await edit_in_place(query.message, context.bot,
                            i18n.t(lang, "archive_already", conv_number=conv["conv_number"]))
        return
    await asyncio.to_thread(set_conversation_archived, conv["id"], user_id, True)
    await edit_in_place(query.message, context.bot,
                        i18n.t(lang, "archive_done", conv_number=conv["conv_number"]))

async def _send_bookmark(bot, chat_id: int, conversation_id: int, text: str, anchor: int):
    """A message pointing at an older one, and a relay row saying which conversation it belongs to."""
    try:
        sent = await bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=anchor)
    except BadRequest:
        sent = await bot.send_message(chat_id=chat_id, text=text)
    live_message.bump(sent.chat_id, sent.message_id)
    await asyncio.to_thread(record_anon_relays, chat_id, [sent.message_id], conversation_id)
    return sent

async def conversation_jump_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    args = _callback_ints(query, 1)
    conv = await _owned_conversation(update, context, args, lang)
    if conv is None:
        return
    await query.answer()
    chat_id = query.message.chat_id
    anchor = await asyncio.to_thread(first_relay_message, chat_id, conv["id"])
    if anchor is None:

        await context.bot.send_message(
            chat_id=chat_id,
            text=i18n.t(lang, "jump_no_anchor", conv_number=conv["conv_number"],
                        days=RELAY_RETENTION_DAYS),
        )
        return
    await _send_bookmark(context.bot, chat_id, conv["id"],
                         i18n.t(lang, "jump_bookmark", conv_number=conv["conv_number"]),
                         anchor)

async def which_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/which, sent as a reply: which conversation is that message in?"""
    message = update.message
    user_id = update.effective_user.id
    lang = await i18n.get_lang(user_id, context)
    target = message.reply_to_message
    if target is None:
        await message.reply_text(i18n.t(lang, "which_needs_reply"))
        return

    conversation_id = await asyncio.to_thread(
        get_conversation_for_relay, message.chat_id, target.message_id)
    conv = (await asyncio.to_thread(get_conversation, conversation_id)
            if conversation_id else None)
    if not conv or user_id not in (conv["owner_user_id"], conv["follower_user_id"]):

        await message.reply_text(i18n.t(lang, "which_unknown"))
        return

    if conv["owner_user_id"] == user_id:
        await message.reply_text(
            i18n.t(lang, "which_owner", conv_number=conv["conv_number"]), do_quote=True)
        return

    anchor = await asyncio.to_thread(first_relay_message, message.chat_id, conv["id"])
    if anchor is None:
        await message.reply_text(
            i18n.t(lang, "which_follower_no_anchor",
                   started=_ago(lang, conv.get("started_at"))), do_quote=True)
        return
    await _send_bookmark(context.bot, message.chat_id, conv["id"],
                         i18n.t(lang, "which_follower"), anchor)

def _callback_ints(query, count: int) -> "list[int] | None":
    """The `count` numeric fields after the prefix in a button's callback_data, or None if they are not all there and not all numbers."""
    _, _, tail = (query.data or "").partition(":")
    parts = tail.split(":")
    if len(parts) != count:
        return None
    try:
        return [int(part) for part in parts]
    except ValueError:
        return None

def _conversation_arg(query) -> int | None:
    """The conversation id out of a single-field button, or None."""
    args = _callback_ints(query, 1)
    return args[0] if args else None

async def reply_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Works for whichever side tapped it."""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = await i18n.get_lang(user_id, context)
    conversation_id = _conversation_arg(query)
    conv = (await asyncio.to_thread(get_conversation, conversation_id)
            if conversation_id is not None else None)
    if not conv or user_id not in (conv["owner_user_id"], conv["follower_user_id"]):
        await query.answer(i18n.t(lang, "not_your_conversation"), show_alert=True)
        return

    await query.answer(i18n.t(lang, "reply_button_hint"), show_alert=True)

async def block_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    conversation_id = _conversation_arg(query)
    conv = (await asyncio.to_thread(get_conversation, conversation_id)
            if conversation_id is not None else None)
    if not conv or conv["owner_user_id"] != update.effective_user.id:
        await query.answer(i18n.t(lang, "not_your_conversation"), show_alert=True)
        return

    await asyncio.to_thread(set_anon_blocked, conv["owner_user_id"], conv["follower_user_id"], True)

    await query.answer(i18n.t(lang, "blocked_answer"), show_alert=False)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            i18n.t(lang, "unblock_button_labelled", conv_number=conv["conv_number"]),
            callback_data=f"aq_unblockc:{conversation_id}",
        )]]
    )
    try:
        await query.edit_message_reply_markup(reply_markup=kb)
    except BadRequest:
        pass

async def unblock_from_conversation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    conversation_id = _conversation_arg(query)
    conv = (await asyncio.to_thread(get_conversation, conversation_id)
            if conversation_id is not None else None)
    if not conv or conv["owner_user_id"] != update.effective_user.id:
        await query.answer(i18n.t(lang, "not_your_conversation"), show_alert=True)
        return

    await asyncio.to_thread(set_anon_blocked, conv["owner_user_id"], conv["follower_user_id"], False)
    await query.answer(i18n.t(lang, "unblocked_answer"))
    try:
        await query.edit_message_reply_markup(reply_markup=_incoming_keyboard(conversation_id, lang))
    except BadRequest:
        pass

async def unblock_from_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The /blocked list's own Undo."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    conversation_id = _conversation_arg(query)
    owner_id = update.effective_user.id
    conv = (await asyncio.to_thread(get_conversation, conversation_id)
            if conversation_id is not None else None)
    if not conv or conv["owner_user_id"] != owner_id:
        await query.answer(i18n.t(lang, "not_your_conversation"), show_alert=True)
        return
    await asyncio.to_thread(set_anon_blocked, owner_id, conv["follower_user_id"], False)
    await query.answer(i18n.t(lang, "unblocked_answer"))
    text, kb = await _blocked_list_text_and_kb(owner_id, lang)
    await edit_in_place(query.message, context.bot, text, reply_markup=kb)

async def _refuse_unaddressed(update, context, lang: str, routing: dict) -> None:
    """Say which message to reply to. Send nothing, keep nothing."""
    active, owned = routing["active"], routing["owned"]
    anchor = routing.get("active_anchor")

    if active and not owned:

        opening = active.get("follower_first_msg_at") is None
        text = i18n.t(lang, "must_reply_opening" if opening else "must_reply")
    else:

        text = i18n.t(lang, "must_reply_ambiguous")
        anchor = None

    if anchor is not None:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=text,
                reply_to_message_id=anchor,
            )
            return
        except BadRequest:

            pass
    await update.message.reply_text(text, do_quote=True)

_ALBUM_WINDOW = 20

_albums: "dict[str, tuple[int, float]]" = {}

def _album_group(message) -> str | None:
    return getattr(message, "media_group_id", None) or None

def _album_prune(now: float) -> None:
    for key, (_, seen) in list(_albums.items()):
        if now - seen > _ALBUM_WINDOW:
            del _albums[key]

def _album_route(message) -> int | None:
    """The conversation an earlier part of this album already went to."""
    group = _album_group(message)
    if not group:
        return None
    _album_prune(datetime.now(timezone.utc).timestamp())
    known = _albums.get(group)
    return known[0] if known else None

def _album_remember(message, conversation_id: int) -> bool:
    """Note where this album is going."""
    group = _album_group(message)
    if not group:
        return False
    now = datetime.now(timezone.utc).timestamp()
    _album_prune(now)
    seen = group in _albums
    _albums[group] = (conversation_id, _albums[group][1] if seen else now)
    return seen

async def _refuse_if_updating(message, lang: str, user_id: int, chat_id: int) -> bool:
    """Whether an announced update means this message should not be relayed now."""
    refusal = await refuse_new_work(lang, user_id, chat_id)
    if refusal:
        await message.reply_text(refusal)
        return True
    return False

def _anchor_for(peer_anchor: "int | None", conv: dict, newest_key: str) -> "int | None":
    """Which message in the receiving chat the delivered copy hangs under."""
    if peer_anchor is not None:
        return peer_anchor
    return conv.get(newest_key)

async def _deliver_follower_message(update: Update, context: ContextTypes.DEFAULT_TYPE, active: dict,
                                    message=None, peer_anchor: int | None = None):
    """`message` is normally the one that just arrived; the Send-it-anyway button passes the earlier, held one instead."""
    message = message or update.message
    follower = update.effective_user
    owner_id = active["owner_user_id"]
    follower_lang = await i18n.get_lang(follower.id, context)
    quiet = _album_remember(message, active["id"])

    if not quiet:
        wait = message_allowed(follower.id)
        if wait:
            await message.reply_text(i18n.t(follower_lang, "too_fast", seconds=wait))
            return
        if await _refuse_if_updating(message, follower_lang, follower.id, message.chat_id):
            return

    blocked, inbox_exists, owner_lang = await asyncio.to_thread(
        get_delivery_context, owner_id, follower.id
    )
    if blocked:
        await message.reply_text(i18n.t(follower_lang, "delivery_blocked"))
        return
    if not inbox_exists:
        await message.reply_text(i18n.t(follower_lang, "inbox_gone"))
        return

    owner_lang = owner_lang or "en"
    header = None if quiet else i18n.t(owner_lang, "incoming_header", conv_number=active["conv_number"])
    kb = None if quiet else _incoming_keyboard(active["id"], owner_lang)

    try:
        sent = await relay_content(
            context.bot, message, owner_id,
            reply_to_message_id=_anchor_for(peer_anchor, active, "last_owner_msg_id"),
            reply_markup=kb, header=header,
        )
    except Forbidden:
        await message.reply_text(i18n.t(follower_lang, "delivery_forbidden"))
        return
    except BadRequest as exc:
        logger.exception("Failed relaying follower message")
        await message.reply_text(i18n.t(follower_lang, "delivery_failed", error=exc))
        return

    note_stat("anon_relay", "to_inbox")
    await asyncio.to_thread(
        record_relay_and_touch, active["id"],
        owner_id, [m.message_id for m in sent],
        message.chat_id, [message.message_id],
        sent[-1].message_id, message.message_id,
    )

    if active.get("follower_first_msg_at") is None:
        await asyncio.to_thread(mark_follower_opened, active["id"])

    if not quiet:
        await message.reply_text(i18n.t(follower_lang, "sent_confirmation"))

async def _deliver_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, conversation_id: int,
                               peer_anchor: int | None = None):
    message = update.message
    owner = update.effective_user
    owner_lang = await i18n.get_lang(owner.id, context)
    conv = await asyncio.to_thread(get_conversation, conversation_id)
    if not conv or conv["owner_user_id"] != owner.id:

        await message.reply_text(i18n.t(owner_lang, "reply_no_match"))
        return

    quiet = _album_remember(message, conversation_id)
    if not quiet:
        wait = message_allowed(owner.id)
        if wait:
            await message.reply_text(i18n.t(owner_lang, "too_fast", seconds=wait))
            return
        if await _refuse_if_updating(message, owner_lang, owner.id, message.chat_id):
            return

    follower_id = conv["follower_user_id"]
    follower_lang = await asyncio.to_thread(get_user_language, follower_id) or "en"
    try:
        sent = await relay_content(
            context.bot, message, follower_id,
            reply_to_message_id=_anchor_for(peer_anchor, conv, "last_follower_msg_id"),

            header=None if quiet else i18n.t(follower_lang, "incoming_header_follower"),
            reply_markup=None if quiet else _follower_keyboard(conversation_id, follower_lang),
        )
    except Forbidden:
        await message.reply_text(i18n.t(owner_lang, "reply_forbidden"))
        return
    except BadRequest as exc:
        logger.exception("Failed relaying owner reply")
        await message.reply_text(i18n.t(owner_lang, "reply_failed", error=exc))
        return

    note_stat("anon_relay", "reply")
    await asyncio.to_thread(
        record_relay_and_touch, conversation_id,
        owner.id, [message.message_id],
        follower_id, [m.message_id for m in sent],
        message.message_id, sent[-1].message_id,
    )

    if not quiet:
        await message.reply_text(i18n.t(owner_lang, "delivered_confirmation"))

    if conv.get("last_owner_msg_id") is None:
        nudge = await maybe_donation_nudge(
            owner.id, owner_lang, context, message.chat_id)
        if nudge:
            await message.reply_text(nudge)

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "export_removed"))

async def _cancel_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> list[CancelItem]:
    """Everything this bot could be waiting on."""
    items = cancel_items(context, lang)
    if await asyncio.to_thread(get_active_conversation_for_follower, update.effective_user.id):
        items.append(CancelItem("anon_session",
                                i18n.t(lang, "cancel_item_anon_session"),
                                i18n.t(lang, "cancel_button_anon_session")))
    return items

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks which of the things it is waiting on to stop, then stops that one -- see _cancel_items for what they are."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    items = await _cancel_items(update, context, lang)
    if await ask_cancel_choice(update, context, items, lang):
        return

    await finish_cancel(update, context, lang, [], stored_only=True)

async def cancel_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of /cancel's buttons."""
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
        if chosen == "anon_session":
            await asyncio.to_thread(clear_follower_state, update.effective_user.id)
            stopped.append(item.label)
        elif cancel_shared_item(context, lang, chosen):
            stopped.append(item.label)
    await finish_cancel_choice(update, context, lang, stopped)

async def edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Editing a message that has already been relayed changes nothing on the other side, and saying nothing let people believe it had."""
    edited = update.edited_message
    try:
        conversation_id = await asyncio.to_thread(
            get_conversation_for_relay, update.effective_chat.id, edited.message_id
        )
        if conversation_id is not None:
            lang = await i18n.get_lang(update.effective_user.id, context)
            await edited.reply_text(i18n.t(lang, "edit_not_relayed"))
    except Exception:

        logger.exception("Could not answer an edited message")
    finally:
        raise ApplicationHandlerStop

async def relay_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Somebody reacted to a bubble of a conversation: the bot puts the same reaction on its twin in the other chat, where it shows beside the bot's picture rather than theirs."""
    change = update.message_reaction
    if change is None or change.user is None or change.chat.type != "private":
        return
    reactor = change.user.id
    route = await asyncio.to_thread(get_reaction_route, change.chat.id, change.message_id)
    if route is None or reactor not in (route["owner_user_id"], route["follower_user_id"]):
        return

    await _knows_reactions(context, reactor)
    if route["blocked"]:
        return
    other = (route["follower_user_id"] if reactor == route["owner_user_id"]
             else route["owner_user_id"])
    chosen, note = pick_reaction(change.old_reaction, change.new_reaction)
    try:
        await context.bot.set_message_reaction(
            chat_id=other, message_id=route["peer_message_id"], reaction=chosen)
    except Forbidden:
        return
    except BadRequest as exc:
        if "REACTION_INVALID" in str(exc).upper():

            note = "reaction_not_passed"
        else:

            logger.debug("Could not pass a reaction on: %s", exc)
            return
    if note and reaction_note_allowed(reactor):
        lang = await i18n.get_lang(reactor, context)
        await _show_briefly(context, change.chat.id, i18n.t(lang, note))

_taking_down: set = set()

async def _show_briefly(context, chat_id: int, text: str) -> None:
    """A silent message that deletes itself after REACTION_NOTE_SECONDS."""
    try:
        sent = await context.bot.send_message(chat_id=chat_id, text=text,
                                              disable_notification=True)
    except Exception:
        logger.debug("Could not show a reaction note", exc_info=True)
        return

    async def take_down():
        await asyncio.sleep(REACTION_NOTE_SECONDS)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=sent.message_id)
        except Exception:
            logger.debug("Could not take a reaction note down", exc_info=True)

    task = asyncio.get_running_loop().create_task(take_down())
    _taking_down.add(task)
    task.add_done_callback(_taking_down.discard)

KNOWS_REACTIONS_KEY = "knows_reactions"

async def _knows_reactions(context, user_id: int) -> bool:
    """Mark this person as told, without telling them."""
    if context.user_data.get(KNOWS_REACTIONS_KEY):
        return False
    try:
        owed = await asyncio.to_thread(claim_reactions_note, user_id)
    except Exception:
        logger.debug("Could not read whether a user knows about reactions", exc_info=True)
        return False
    context.user_data[KNOWS_REACTIONS_KEY] = True
    return owed

async def reactions_update_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """After whatever somebody came to do: if they were here before reactions travelled, tell them once."""
    user, chat = update.effective_user, update.effective_chat
    if user is None or chat is None or chat.type != "private":
        return
    if update.message is None and update.callback_query is None:
        return
    if context.user_data.get(KNOWS_REACTIONS_KEY) or FORCE_REPLY_KEY in context.user_data:
        return
    if not await _knows_reactions(context, user.id):
        return
    lang = await i18n.get_lang(user.id, context)
    try:
        await context.bot.send_message(chat_id=chat.id, text=i18n.t(lang, "reactions_update_note"))
    except Exception:
        logger.debug("Could not send the reactions note", exc_info=True)
        return

    context.user_data[NOTE_UPDATE_KEY] = update.update_id

PROMO_AD_KEY = "_promo_ad"

NOTE_UPDATE_KEY = "_note_update"

_NO_AD_COMMANDS = {"/deletemydata", "/privacy", "/terms"}

def _no_ad_after(message) -> bool:
    """Is this one of the commands the gift's ad never follows?"""
    words = (message.text or "").split(None, 1)
    return bool(words) and words[0].split("@", 1)[0].lower() in _NO_AD_COMMANDS

async def promo_ad_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """After whatever somebody came to do, and after the reactions note: if the gift is open and they have not had it nor been shown this ad, show it once."""
    message, user, chat = update.message, update.effective_user, update.effective_chat
    if message is None or user is None or chat is None or chat.type != "private":
        return
    if getattr(user, "is_bot", False):
        return

    words = (message.text or "").split(None, 1)
    if len(words) == 2 and words[0].split("@", 1)[0].lower() == "/start":
        return

    if _no_ad_after(message):
        return
    if FORCE_REPLY_KEY in context.user_data:
        return
    if context.user_data.get(NOTE_UPDATE_KEY) == update.update_id:
        return
    if context.user_data.get(PROMO_AD_KEY) == family_link.PROMO_KEY:
        return
    try:
        window = await asyncio.to_thread(family_link.promo_window)

        if window is None or not window[0] <= datetime.now(timezone.utc) < window[1]:
            return

        row = (sibling_bots_keyboard_row(BOT_NAME, only="downloaderbot")
               + sibling_bots_keyboard_row(BOT_NAME, only="convertbot"))
        if not row:
            return

        lang = await asyncio.to_thread(get_user_language, user.id)
        if not lang:
            return
        if await asyncio.to_thread(family_link.promo_given_to, user.id):
            context.user_data[PROMO_AD_KEY] = family_link.PROMO_KEY
            return
        shown_now = await asyncio.to_thread(claim_promo_seen, user.id, family_link.PROMO_KEY)
        context.user_data[PROMO_AD_KEY] = family_link.PROMO_KEY
        if not shown_now:
            return
        await context.bot.send_message(
            chat_id=chat.id, text=family_link.promo_ad(lang, window[1]),
            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([row]), **NO_PREVIEW,
        )
    except Exception as exc:

        logger.debug("The gift ad was not shown (%s)", type(exc).__name__)

async def _route_into(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      conversation_id: int, conv: dict | None = None,
                      peer_anchor: int | None = None) -> None:
    """Deliver this message into one named conversation, whichever side sent it."""
    user = update.effective_user
    if conv is None:
        conv = await asyncio.to_thread(get_conversation, conversation_id)
    if not conv or user.id not in (conv["owner_user_id"], conv["follower_user_id"]):
        lang = await i18n.get_lang(user.id, context)
        await update.message.reply_text(i18n.t(lang, "reply_stale"))
        return
    if conv["owner_user_id"] == user.id:
        return await _deliver_owner_reply(update, context, conversation_id,
                                          peer_anchor=peer_anchor)
    return await _deliver_follower_message(update, context, conv,
                                           peer_anchor=peer_anchor)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    chat_id = message.chat_id

    album = _album_route(message)
    if album is not None:
        return await _route_into(update, context, album)

    if message.reply_to_message:
        anchor_id = message.reply_to_message.message_id
        relay = await asyncio.to_thread(get_relay_row, chat_id, anchor_id)
        conversation_id = relay["conversation_id"] if relay else None
        if conversation_id:

            conv = await asyncio.to_thread(get_conversation, conversation_id)
            if conv and user.id in (conv["owner_user_id"], conv["follower_user_id"]):

                return await _route_into(update, context, conversation_id, conv,
                                         peer_anchor=relay["peer_message_id"])
        lang = await i18n.get_lang(user.id, context)
        await message.reply_text(i18n.t(lang, "reply_stale"))
        return

    routing = await asyncio.to_thread(get_routing_context, user.id, chat_id)
    active, owned = routing["active"], routing["owned"]

    if (active and active.get("follower_first_msg_at") is None
            and routing["newest_is_active"]):
        return await _deliver_follower_message(update, context, active)

    if active or owned:
        lang = await i18n.get_lang(user.id, context)
        return await _refuse_unaddressed(update, context, lang, routing)

    lang = await i18n.get_lang(user.id, context)
    await message.reply_text(i18n.t(lang, "generic_nudge"))

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "unknown_command"))

async def _post_init(application):
    await tune_runtime(application)

    await lifecycle.on_start(BOT_NAME)
    await publish_commands(application, BOT_COMMANDS, ADMIN_COMMANDS, ADMIN_IDS)
    await publish_profile(application)

async def _post_stop(application):

    await lifecycle.on_stop(application)
    await flush_on_shutdown(application)

def main():
    if not BOT_TOKEN or not BOT_USERNAME:
        raise SystemExit("Set ABOT_TOKEN and ABOT_USERNAME environment variables first.")

    init_db()
    builder = (
        ApplicationBuilder().token(BOT_TOKEN)
        .post_init(_post_init).post_stop(_post_stop)
    )

    state = lifecycle.persistence()
    if state is not None:
        builder = builder.persistence(state)
    app = builder.build()
    lifecycle.install(app, BOT_NAME, ADMIN_IDS)
    app.add_error_handler(error_handler)
    attach_problem_reports(app)

    app.add_handler(TypeHandler(Update, track_activity), group=-4)

    attach_flood_gate(app, ADMIN_IDS)

    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, edited_message), group=-2)

    app.add_handler(MessageHandler((filters.TEXT | filters.REPLY) & ~filters.COMMAND,
                                   awaited_text_received), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("fullhelp", fullhelp_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("newlink", newlink_command))
    app.add_handler(CommandHandler("pause", pause_command))
    app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(CommandHandler("conversations", conversations_command))
    app.add_handler(CommandHandler("which", which_command))
    app.add_handler(CommandHandler("archive", archive_command))
    app.add_handler(CommandHandler("blocked", blocked_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("dbdump", dbdump_command))
    app.add_handler(CommandHandler("messageas", messageas_command))
    app.add_handler(CommandHandler("status", status_command))

    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("en", set_language_en))
    app.add_handler(CommandHandler("uz", set_language_uz))
    app.add_handler(CommandHandler("rus", set_language_rus))

    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler("paysupport", paysupport_command))
    app.add_handler(CallbackQueryHandler(problem_report_callback, pattern=r"^rpt"))
    app.add_handler(CommandHandler("deletemydata", delete_my_data_command))
    app.add_handler(CallbackQueryHandler(delete_my_data_chosen, pattern="^" + ERASE_PREFIX))

    app.add_handler(CallbackQueryHandler(language_chosen, pattern=r"^setlang:"))
    app.add_handler(CallbackQueryHandler(help_toggle(build_help_text, None, HELP_PAGES), pattern=HELP_TOGGLE_PATTERN))
    app.add_handler(CallbackQueryHandler(help_page_button(HELP_PAGES), pattern=HELP_PAGE_PATTERN))
    app.add_handler(CallbackQueryHandler(cancel_choice_callback, pattern=r"^cancelpick:"))
    app.add_handler(CallbackQueryHandler(anonlink_toggle_callback, pattern=r"^anonlink:toggle$"))
    app.add_handler(CallbackQueryHandler(anonlink_newlink_callback, pattern=r"^anonlink:newlink$"))
    app.add_handler(CallbackQueryHandler(conversations_page_callback, pattern=r"^aq_convs:"))
    app.add_handler(CallbackQueryHandler(conversation_card_callback, pattern=r"^aq_conv:"))
    app.add_handler(CallbackQueryHandler(conversation_archive_callback, pattern=r"^aq_arch:"))
    app.add_handler(CallbackQueryHandler(archive_command_callback, pattern=r"^aq_archcmd:"))
    app.add_handler(CallbackQueryHandler(conversation_jump_callback, pattern=r"^aq_jump:"))
    app.add_handler(CallbackQueryHandler(reply_button_callback, pattern=r"^aq_reply:"))
    app.add_handler(CallbackQueryHandler(block_callback, pattern=r"^aq_block:"))
    app.add_handler(CallbackQueryHandler(unblock_from_conversation_callback, pattern=r"^aq_unblockc:"))
    app.add_handler(CallbackQueryHandler(unblock_from_list_callback, pattern=r"^aq_unblockg:"))

    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CallbackQueryHandler(donate_amount_chosen, pattern="^donate:"))
    app.add_handler(CallbackQueryHandler(donate_fiat_amount_chosen, pattern="^donatefiat:"))
    app.add_handler(CallbackQueryHandler(donate_custom_button_chosen, pattern="^donatecustom:"))
    app.add_handler(PreCheckoutQueryHandler(donation_precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, donation_payment_callback))

    app.add_handler(MessageReactionHandler(
        relay_reaction, message_reaction_types=MessageReactionHandler.MESSAGE_REACTION_UPDATED))

    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, handle_message))

    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    app.add_handler(TypeHandler(Update, reactions_update_note), group=1)

    app.add_handler(TypeHandler(Update, promo_ad_note), group=2)

    family_link.attach(app, BOT_NAME, "AnonBot", START_TIME)
    attach_maintenance(app)

    logger.info("Bot starting (polling)...")

    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[
            Update.MESSAGE, Update.EDITED_MESSAGE,
            Update.CALLBACK_QUERY, Update.PRE_CHECKOUT_QUERY,
            Update.MESSAGE_REACTION,
        ],
    ))

if __name__ == "__main__":
    main()

# ─── module: manager_bot.bot ─────────────────────────────────────────────────
"""ManagerBot -- the private one, for the owner only."""
import asyncio
import functools
import hashlib
import html
import json
import logging
import os
import re
import secrets
import tempfile
import time as time_module
import zipfile
from collections import OrderedDict, deque
from itertools import takewhile
from datetime import datetime, time, timedelta, timezone
from io import BytesIO
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import (
    BotCommand, BotCommandScopeChat, InlineKeyboardButton,
    InlineKeyboardMarkup, LinkPreviewOptions, Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

import db
import family_link
import lifecycle
import problems
from live_message import LiveMessage, edit_in_place
from db import init_db
import monitoring
from monitoring import (
    attach_maintenance,
    build_status_text,
    error_handler,
    flush_on_shutdown,
    setup_logging,
    track_activity,
    tune_runtime,
)

setup_logging(__file__)
logger = logging.getLogger(__name__)

START_TIME = datetime.now(timezone.utc)

BOT_TOKEN = os.environ.get("MBOT_TOKEN")

BOT_USERNAME = (os.environ.get("MBOT_USERNAME") or "").strip().lstrip("@") or None
BOT_NAME = "managerbot"
DISPLAY_NAME = "ManagerBot"

ADMIN_IDS = {int(x) for x in os.environ.get("MBOT_ADMIN_ID", "").split(",") if x.strip()}

DOWN_AFTER_SECONDS = int(os.environ.get("MBOT_DOWN_AFTER_SECONDS", "120"))

COMMAND_TIMEOUT_SECONDS = int(os.environ.get("MBOT_COMMAND_TIMEOUT_SECONDS", "90"))

RESULT_POLL_SECONDS = int(os.environ.get("MBOT_RESULT_POLL_SECONDS", "20"))
EVENT_POLL_SECONDS = int(os.environ.get("MBOT_EVENT_POLL_SECONDS", "30"))
RESULT_POLL_FAST_SECONDS = int(os.environ.get("MBOT_RESULT_POLL_FAST_SECONDS", "1"))
EVENT_POLL_FAST_SECONDS = int(os.environ.get("MBOT_EVENT_POLL_FAST_SECONDS", "2"))

PUMP_TICK_SECONDS = int(os.environ.get("MBOT_PUMP_TICK_SECONDS", "1"))

REDEPLOY_GRACE_SECONDS = int(os.environ.get("MBOT_REDEPLOY_GRACE_SECONDS", "300"))

STARTUP_ROLLCALL_SECONDS = int(os.environ.get("MBOT_ROLLCALL_SECONDS", "5"))

ROLLCALL_FRESH_SECONDS = int(os.environ.get("MBOT_ROLLCALL_FRESH_SECONDS", "120"))

ALERT_LEVELS = {"warning", "error", "critical"}

DIGEST_AT_UTC = os.environ.get("MBOT_DIGEST_UTC", "").strip()

NIGHTLY_REPORT_AT_UTC = os.environ.get("MBOT_NIGHTLY_UTC", "13:00").strip()
NIGHTLY_REPORT_HOURS = int(os.environ.get("MBOT_NIGHTLY_HOURS", "24"))

TELEGRAM_MAX_CHARS = 3900

POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "30"))

DEFAULT_REGISTRY = (
    "stickerbot:StickerBot:sticker_bot,"
    "convertbot:ConvertBot:convert_bot,"
    "downloaderbot:DownloaderBot:downloader_bot,"
    "anonbot:AnonBot:anon_bot"
)

def _parse_registry() -> list[dict]:
    raw = os.environ.get("FAMILY_REGISTRY", DEFAULT_REGISTRY)
    bots = []
    for entry in raw.split(","):
        parts = [p.strip() for p in entry.strip().split(":")]
        if len(parts) == 3 and all(parts):
            bots.append({"id": parts[0], "name": parts[1], "schema": parts[2]})
    return bots

CHILDREN = _parse_registry()
ALL_BOTS = CHILDREN + [{"id": BOT_NAME, "name": DISPLAY_NAME, "schema": db.DB_SCHEMA}]

USERNAME_ALIASES = {
    "stickerbot": ["mumu_sticker_bot"],
    "convertbot": ["mumu_convert_bot"],
    "downloaderbot": ["mumu_downloader_bot"],
    "anonbot": ["mumu_chat_bot", "chat", "chatbot"],
    "managerbot": ["mumu_manager_bot", "manager", "parent", "parentbot"],
}

def _names_of(bot: dict) -> list[str]:
    return [bot["id"], bot["name"].lower(), bot["schema"], *USERNAME_ALIASES.get(bot["id"], [])]

def resolve_bot(token: str) -> dict | None:
    """Accepts "sticker", "stickerbot", "StickerBot", "sticker_bot", "@mumu_sticker_bot" -- any unambiguous prefix of the id, the display name, the schema, or the Telegram username."""
    token = token.strip().lower().lstrip("@")
    if not token:
        return None
    for bot in ALL_BOTS:
        if token in _names_of(bot):
            return bot
    matches = [b for b in ALL_BOTS if any(n.startswith(token) for n in _names_of(b))]
    return matches[0] if len(matches) == 1 else None

def bot_list_hint() -> str:
    return ", ".join(b["id"] for b in ALL_BOTS)

_reported_strangers: set[int] = set()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """True if this update may proceed."""
    user = update.effective_user
    if user and is_admin(user.id):
        return True
    if user and user.id not in _reported_strangers:
        _reported_strangers.add(user.id)

        await notify_owner(context, "👀 A stranger found ManagerBot, and was turned away.")
        await asyncio.to_thread(
            db.log_event, BOT_NAME, "warning", "stranger",
            "An unknown user messaged ManagerBot.",
        )
    if update.message:
        await update.message.reply_text("This is a private bot.")
    return False

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """Never raises."""
    delivered = False
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text, parse_mode=ParseMode.HTML)
            delivered = True
        except Exception:
            logger.exception("Couldn't deliver an alert to %s", admin_id)
    return delivered

async def send_long(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, filename: str = "output.txt") -> None:
    """Anything past Telegram's message ceiling goes as a file instead of being silently cut in half -- a truncated log tail is worse than useless when you are trying to work out what broke."""
    if len(text) <= TELEGRAM_MAX_CHARS:
        await context.bot.send_message(chat_id=chat_id, text=text)
        return
    await context.bot.send_message(chat_id=chat_id, text=f"{text[:TELEGRAM_MAX_CHARS]}\n\n[…full text attached]")
    await context.bot.send_document(
        chat_id=chat_id, document=BytesIO(text.encode("utf-8")), filename=filename
    )

def format_delta(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{secs}s"

def _build_board(sweep_line: str = "") -> str:
    """Runs entirely in a worker thread (it is all blocking SQL), so the caller wraps it in asyncio.to_thread."""
    now = datetime.now(timezone.utc)
    snapshot = db.status_snapshot([b["schema"] for b in ALL_BOTS], now - timedelta(hours=1))
    beats = {row["bot_id"]: row for row in snapshot["beats"]}
    active_by_schema = snapshot["active"]

    up_count = 0
    lines = []
    for bot in ALL_BOTS:
        beat = beats.get(bot["id"])
        me = " (me)" if bot["id"] == BOT_NAME else ""
        if beat is None:
            lines.append(f"❔ <b>{bot['name']}</b>{me} — never seen. Has it ever been started?")
            continue

        is_up = beat["seconds_ago"] <= DOWN_AFTER_SECONDS
        up_count += is_up
        if not is_up:
            lines.append(
                f"❌ <b>{bot['name']}</b>{me} — DOWN, last heartbeat "
                f"{format_delta(beat['seconds_ago'])} ago (was up "
                f"{format_delta((beat['last_seen'] - beat['started_at']).total_seconds())})"
            )
            continue

        active = active_by_schema.get(bot["schema"])
        uptime = format_delta((now - beat["started_at"]).total_seconds())
        errors = f" · ⚠️ {beat['error_count']}" if beat["error_count"] else ""
        users = "" if active is None else f" · {active} user(s)/h"
        lines.append(
            f"✅ <b>{bot['name']}</b>{me} — up {uptime} · {html.escape(beat['host'] or '?')} "
            f"· v{beat['version']}{errors}{users}"
        )

    info = snapshot["database"]
    db_line = f"🗄 Database: {info['name']} · Postgres {info['version']} · {info['size']}"
    header = f"👪 <b>Bot family</b> — {up_count}/{len(ALL_BOTS)} up"
    alerts = "on" if snapshot["alerts"] == "on" else "OFF"
    stamp = now.strftime("%H:%M:%S UTC")
    return "\n".join([header, "", *lines, "", db_line,
                      *([sweep_line] if sweep_line else []),
                      f"🔔 Alerts: {alerts} · 🕐 {stamp}"])

def _board_keyboard() -> InlineKeyboardMarkup:
    """A refresh button, because /status is the command anyone watching a deploy types over and over -- and a mute toggle right where you notice you want it."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Refresh", callback_data="board:refresh"),
        InlineKeyboardButton("🔔 Alerts", callback_data="board:alerts"),
        InlineKeyboardButton("📡 Ping all", callback_data="board:ping"),
    ]])

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    try:
        board = await asyncio.to_thread(_build_board, _sweep_line())
    except Exception as exc:
        await update.message.reply_text(
            f"⚠️ Couldn't read the family database: {exc}\n\n"
            "Every bot may well be fine -- this is ManagerBot's own connection failing."
        )
        return
    await update.message.reply_text(board, parse_mode=ParseMode.HTML, reply_markup=_board_keyboard())

MEMORY_USD_PER_MB_MONTH = float(os.environ.get("MEMORY_USD_PER_MB_MONTH") or 0.01)
USAGE_REPORT_HOURS = int(os.environ.get("USAGE_REPORT_HOURS") or 24)

def _usage_report(hours: int) -> str:
    samples = family_link.usage_history(None, hours)
    if not samples:
        return (f"No usage samples in the last {hours}h.\n\n"
                "Each bot writes one every USAGE_SAMPLE_MINUTES (15 by default), so this "
                "is empty until they have been up that long on a version that has it.")

    per_bot: dict[str, list[dict]] = {}
    for sample in samples:
        per_bot.setdefault(sample["bot_id"], []).append(sample)

    lines = [f"<b>Usage, last {hours}h</b>"]
    total_cost = 0.0
    for bot_id in sorted(per_bot):
        rows = per_bot[bot_id]
        resident = [row["rss_mb"] for row in rows if row["rss_mb"]]
        peaks = [row["peak_rss_mb"] for row in rows if row["peak_rss_mb"]]
        ceilings = [row["ceiling_mb"] for row in rows if row["ceiling_mb"]]
        updates = sum(row["updates"] or 0 for row in rows)
        people = max((row["users"] or 0) for row in rows)
        average = sum(resident) / len(resident) if resident else 0
        cost = average * MEMORY_USD_PER_MB_MONTH
        total_cost += cost
        line = f"\n<b>{html.escape(bot_id)}</b>"
        if resident:
            line += f"\n  {average:.0f} MB average, {max(peaks or resident)} MB peak"
            if ceilings:
                headroom = max(peaks or resident) / max(ceilings)
                line += f" of {max(ceilings)} MB ({headroom:.0%})"
            line += f"\n  \u2248 ${cost:.2f}/month in memory"
        else:
            line += "\n  no memory readings (not a Linux container?)"
        line += f"\n  {updates} update(s), busiest window {people} person(s)"
        lines.append(line)

    lines.append(f"\n<b>All five \u2248 ${total_cost:.2f}/month in memory</b> "
                 f"at ${MEMORY_USD_PER_MB_MONTH:.3f} per MB-month.")
    lines.append("\nMemory is the bill: a container is paid for every minute it holds "
                 "what it holds, busy or not.")
    return "\n".join(lines)

COLD_START_SECONDS = int(os.environ.get("COLD_START_SECONDS") or 6)

def _idle_report(hours: int) -> str:
    samples = family_link.usage_history(None, hours)
    if not samples:
        return (f"No usage samples in the last {hours}h -- nothing to judge yet.\n\n"
                "Each bot writes one every 15 minutes, so a day of running gives about "
                "96 per bot, which is enough to see a daily shape.")

    per_bot: dict[str, list[dict]] = {}
    for sample in samples:
        per_bot.setdefault(sample["bot_id"], []).append(sample)

    lines = [f"<b>Idle time, last {hours}h</b>",
             f"<i>Sleeping starts after {monitoring.SLEEP_AFTER_SECONDS // 60} min of quiet. "
             f"Nothing sleeps yet.</i>"]
    for bot_id in sorted(per_bot):
        rows = per_bot[bot_id]
        covered = sum((row["window_minutes"] or 0) for row in rows) * 60
        if not covered:
            continue
        sleepable = sum((row["sleepable_seconds"] or 0) for row in rows)
        longest = max((row["max_gap_seconds"] or 0) for row in rows)
        updates = sum((row["updates"] or 0) for row in rows)
        resident = [row["rss_mb"] for row in rows if row["rss_mb"]]
        average = sum(resident) / len(resident) if resident else 0
        share = sleepable / covered

        wakes = min(updates, int(sleepable / max(monitoring.SLEEP_AFTER_SECONDS, 1)) + 1)
        saving = average * MEMORY_USD_PER_MB_MONTH * share
        verdict = ("worth sleeping" if share >= 0.6 and average
                   else "not worth it yet" if share >= 0.2
                   else "busy enough to leave alone")
        lines.append(
            f"\n<b>{html.escape(bot_id)}</b> — {share:.0%} of the time asleep"
            f"\n  longest quiet stretch {longest // 3600}h {(longest % 3600) // 60}m"
            f"\n  {updates} update(s), about {wakes} wake(s) — "
            f"{wakes * COLD_START_SECONDS}s of cold start in total"
            f"\n  would save \u2248 ${saving:.2f}/month · <i>{verdict}</i>"
        )
    lines.append("\nA wake costs the person who caused it a few seconds before their "
                 "first reply. That is the whole trade.")
    return "\n".join(lines)

async def idle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    hours = USAGE_REPORT_HOURS
    if context.args:
        try:
            hours = max(1, min(24 * 45, int(context.args[0])))
        except ValueError:
            pass
    try:
        report = await asyncio.to_thread(_idle_report, hours)
    except Exception as exc:
        await update.message.reply_text(f"\u26a0\ufe0f Couldn't read the usage table: {exc}")
        return
    await update.message.reply_text(report, parse_mode=ParseMode.HTML)

async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    hours = USAGE_REPORT_HOURS
    if context.args:
        try:
            hours = max(1, min(24 * 45, int(context.args[0])))
        except ValueError:
            pass
    try:
        report = await asyncio.to_thread(_usage_report, hours)
    except Exception as exc:
        await update.message.reply_text(f"\u26a0\ufe0f Couldn't read the usage table: {exc}")
        return
    await update.message.reply_text(report, parse_mode=ParseMode.HTML)

BUTTONS_DEFAULT_DAYS = 7
BUTTONS_MAX_DAYS = 90
BUTTONS_MAX_LINES = 25
BUTTONS_USAGE = f"Usage: /buttons [days] -- from 1 to {BUTTONS_MAX_DAYS} days, {BUTTONS_DEFAULT_DAYS} if not said."

_REDO_KEYS = ("redo.to_file", "redo.to_compressed", "redo.expired", "redo.spent")
_REDO_AFTER = (("lt1m", "<1m"), ("1-2m", "1-2m"), ("2-5m", "2-5m"), ("5-15m", "5-15m"),
               ("15-60m", "15-60m"), ("gt60m", ">60m"), ("unknown", "unknown"))
_DOWNLOADER_BLOCK = (set(_REDO_KEYS) | {f"redo.after.{name}" for name, _ in _REDO_AFTER}
                     | {"redo.cache.hit", "redo.cache.miss", "cache.kept", "cache.not_kept",
                        "link.again.cached", "link.again.not_cached"})

def _downloader_block(counts: dict) -> list[str]:
    n = lambda key: counts.get(key, 0)
    return [
        f"  Redo taps: {n('redo.to_file') + n('redo.to_compressed')} (to file {n('redo.to_file')}, "
        f"to compressed {n('redo.to_compressed')}); expired {n('redo.expired')}, double {n('redo.spent')}",
        "  Tap after: " + " \u00b7 ".join(f"{label} {n('redo.after.' + name)}" for name, label in _REDO_AFTER),
        f"  Redo from cache: hit {n('redo.cache.hit')} \u00b7 miss {n('redo.cache.miss')}; "
        f"deliveries kept {n('cache.kept')} \u00b7 not kept {n('cache.not_kept')}",
        f"  Same link again: cached {n('link.again.cached')} \u00b7 not cached {n('link.again.not_cached')}",
    ]

def _buttons_report(days: int) -> str:
    rows = family_link.button_taps_history(days)
    if not rows:
        return "No button taps recorded yet."
    per_bot: dict[str, dict[str, int]] = {}
    for row in rows:
        per_bot.setdefault(row["bot_id"], {})[row["button"]] = int(row["taps"])
    names = {child["id"]: child["name"] for child in CHILDREN}
    order = [child["id"] for child in CHILDREN if child["id"] in per_bot]
    order += sorted(bot_id for bot_id in per_bot if bot_id not in names)
    lines = [f"Button taps, last {days} days (counts only, nothing about who)"]
    for bot_id in order:
        counts = per_bot[bot_id]
        lines += ["", names.get(bot_id, bot_id)]
        if bot_id == "downloaderbot":
            lines += _downloader_block(counts)
            counts = {key: taps for key, taps in counts.items() if key not in _DOWNLOADER_BLOCK}
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        lines += [f"  {key}: {taps}" for key, taps in ranked[:BUTTONS_MAX_LINES]]
        if len(ranked) > BUTTONS_MAX_LINES:
            lines.append(f"  +{len(ranked) - BUTTONS_MAX_LINES} more")
    return "\n".join(lines)

async def buttons_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    days = BUTTONS_DEFAULT_DAYS
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            days = 0
        if len(context.args) > 1 or not 1 <= days <= BUTTONS_MAX_DAYS:
            await update.message.reply_text(BUTTONS_USAGE)
            return
    try:
        report = await asyncio.to_thread(_buttons_report, days)
    except Exception as exc:
        await update.message.reply_text(f"\u26a0\ufe0f Couldn't read the button taps: {exc}")
        return
    await send_long(context, update.effective_chat.id, report, "buttons.txt")

STATS_DEFAULT_DAYS = 30
STATS_MAX_DAYS = 400
STATS_MAX_LINES = 12
STATS_USAGE = f"Usage: /stats [days] -- from 1 to {STATS_MAX_DAYS} days, {STATS_DEFAULT_DAYS} if not said."
STATS_LABELS = {
    "link_site": "Links delivered, by site",
    "link_media": "Media delivered, site:kind",
    "link_extra": "Extras",
    "conversion": "Conversions, from>to",
    "sticker": "Stickers added",
    "sticker_pack": "Packs",
    "video_fit_offered": "Clips that didn't fit",
    "video_fit": "What was done about them",
    "anon_relay": "Messages relayed",
}

def _stats_report(days: int) -> str:
    rows = family_link.stats_history(days)
    if not rows:
        return "No statistics recorded yet."
    per_bot: dict[str, dict[str, list]] = {}
    for row in rows:
        per_bot.setdefault(row["bot_id"], {}).setdefault(row["metric"], []).append((row["key"], int(row["n"])))
    names = {child["id"]: child["name"] for child in CHILDREN}
    order = [child["id"] for child in CHILDREN if child["id"] in per_bot]
    order += sorted(bot_id for bot_id in per_bot if bot_id not in names)
    lines = [f"Statistics, last {days} days (anonymous daily counts, nothing about who)"]
    for bot_id in order:
        lines += ["", names.get(bot_id, bot_id)]
        for metric, items in per_bot[bot_id].items():
            total = sum(n for _, n in items)
            lines.append(f"  {STATS_LABELS.get(metric, metric)} — {total}")
            for key, n in items[:STATS_MAX_LINES]:
                lines.append(f"    {key}: {n} ({n * 100 // total}%)")
            if len(items) > STATS_MAX_LINES:
                lines.append(f"    +{len(items) - STATS_MAX_LINES} more")
    return "\n".join(lines)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    days = STATS_DEFAULT_DAYS
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            days = 0
        if len(context.args) > 1 or not 1 <= days <= STATS_MAX_DAYS:
            await update.message.reply_text(STATS_USAGE)
            return
    try:
        report = await asyncio.to_thread(_stats_report, days)
    except Exception as exc:
        await update.message.reply_text(f"\u26a0\ufe0f Couldn't read the statistics: {exc}")
        return
    await send_long(context, update.effective_chat.id, report, "stats.txt")

async def board_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The three buttons under the /status board."""
    if not await guard(update, context):
        return
    query = update.callback_query
    action = query.data.split(":", 1)[1]

    if action == "alerts":
        current = await asyncio.to_thread(db.get_setting, "alerts", "on")
        new = "off" if current == "on" else "on"
        await asyncio.to_thread(db.set_setting, "alerts", new)
        await query.answer(f"Alerts {new}.")
    elif action == "ping":
        for child in CHILDREN:
            await asyncio.to_thread(
                db.queue_command, child["id"], "ping", "",
                update.effective_user.id, update.effective_chat.id,
            )
        await query.answer(f"Pinged all {len(CHILDREN)}.")
        return
    else:
        await query.answer()

    try:
        board = await asyncio.to_thread(_build_board, _sweep_line())
    except Exception as exc:

        await query.message.reply_text(
            f"⚠️ Couldn't read the family database: {exc}\n\n"
            "Every bot may well be fine -- this is ManagerBot's own connection failing."
        )
        return

    await edit_in_place(query.message, context.bot, board,
                        parse_mode=ParseMode.HTML, reply_markup=_board_keyboard())

async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ManagerBot's own /status, in the same shape every other bot uses."""
    if not await guard(update, context):
        return
    now = datetime.now(timezone.utc)
    hour = await asyncio.to_thread(db.count_active_users_since, now - timedelta(hours=1))
    since_start = await asyncio.to_thread(db.count_active_users_since, START_TIME)
    await update.message.reply_text(build_status_text(START_TIME, hour, since_start))

COMMAND_SINCE = {
    "probe": "1.2.1",
    "routewatch": "2.1.0",
    "versions": "2.1.0",
    "providers": "1.2.3",
    "stars": "1.2.3",
    "crashtest": "1.2.3",
    "gift": "2.1.1",
    "softstop": "2.1.6",
    "softstopbot": "2.1.6",
}

def _version_key(version: str | None):
    """A sortable form of a family version, or None if it cannot be read."""
    if not version:
        return None
    parts = []
    for chunk in str(version).strip().split("."):
        digits = "".join(takewhile(str.isdigit, chunk))
        if not digits:
            return None

        parts.append((int(digits), chunk[len(digits):]))
    return tuple(parts)

FLAG_SINCE = {("broadcast", "--active"): "1.3.0", ("logs", "problems"): "1.6.0"}

def _too_old_for(bot_version: str | None, command: str, args: list[str] | None = None) -> str | None:
    """The sentence to show instead of queueing, or None to go ahead."""
    needed = COMMAND_SINCE.get(command)
    for (cmd, flag), since in FLAG_SINCE.items():
        if cmd == command and args and flag in args:
            needed = since
            command = f"{command} {flag}"
            break
    if not needed:
        return None
    have, want = _version_key(bot_version), _version_key(needed)
    if have is None or want is None or have >= want:
        return None
    return (f"That bot is on <b>{html.escape(str(bot_version))}</b> and "
            f"<code>{html.escape(command)}</code> arrived in <b>{needed}</b>, so it has "
            f"never heard of it — nothing is broken, it just has not been deployed "
            f"since. It will have it after the next release.")

def _accepted_commands(beat: "dict | None") -> set:
    """Which bus commands a bot answers, from the list it publishes in its own heartbeat."""
    listed = (beat or {}).get("commands")
    if not listed:
        return set(family_link.COMMANDS)
    return {name.strip() for name in listed.split(",") if name.strip()}

async def _dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    bot: dict, command: str, args: list[str]) -> None:
    if bot["id"] == BOT_NAME:
        await update.effective_message.reply_text(
            "That one is me. Use /status, /me, /events or /backup directly."
        )
        return

    beat = await asyncio.to_thread(db.heartbeat_of, bot["id"])

    accepted = _accepted_commands(beat)
    if command not in accepted:
        known = ", ".join(sorted(accepted))
        await update.effective_message.reply_text(
            f"{bot['name']} has no '{command}'. It answers: {known}")
        return
    stale = _too_old_for((beat or {}).get("version"), command, args)
    if stale:
        await update.effective_message.reply_text(
            f"⏳ <b>{html.escape(bot['name'])}</b> · {html.escape(command)}\n\n"
            + stale,
            parse_mode=ParseMode.HTML,
        )
        return

    if command in ("softstop", "softstopbot", "restart"):
        args = [arg for arg in args if not arg.replace(".", "", 1).isdigit()] + [str(int(time_module.time()))]
    command_id = await asyncio.to_thread(
        db.queue_command, bot["id"], command, " ".join(args),
        update.effective_user.id, update.effective_chat.id,
    )

    await update.effective_message.reply_text(f"→ {bot['name']} · {command} — queued as #{command_id}")

SERVICE_ASK_SECONDS = 120
_SERVICE_ASKS: "OrderedDict[str, dict]" = OrderedDict()

async def _service_of(update: Update, bot_word: str):
    """(bot, the ids of every bot in its service) -- or None, having said why not."""
    bot = resolve_bot(bot_word)
    if bot is None or bot["id"] == BOT_NAME:
        await update.message.reply_text(
            "That one is me -- stop or restart me from the host." if bot else
            f"No such bot: {bot_word}. Known: {bot_list_hint()}")
        return None
    try:
        beats = {row["bot_id"]: row for row in await asyncio.to_thread(db.all_heartbeats)}
    except Exception as exc:
        await update.message.reply_text(f"Could not read the heartbeats, so nothing was asked: {exc}")
        return None
    beat = beats.get(bot["id"])
    if beat is None or beat["seconds_ago"] > DOWN_AFTER_SECONDS:
        await update.message.reply_text(f"{bot['name']} is not running, so there is nothing to do.")
        return None
    host = beat.get("host")
    together = sorted(row["bot_id"] for row in beats.values()
                      if host and row.get("host") == host and row["seconds_ago"] <= DOWN_AFTER_SECONDS)
    together = together or [bot["id"]]
    mine = beats.get(BOT_NAME) or {}
    if BOT_NAME in together or (host and mine.get("host") == host):
        await update.message.reply_text(
            f"{bot['name']} runs in the same service as me, so this would take me down too. "
            "Do it from the host.")
        return None
    return bot, together

def _names(bot_ids) -> str:
    return ", ".join((resolve_bot(bot_id) or {}).get("name", bot_id) for bot_id in bot_ids)

def _ask_service(kind: str, bot: dict, together: list, force: bool = False) -> str:
    nonce = secrets.token_hex(4)
    _SERVICE_ASKS[nonce] = {"kind": kind, "bot": bot["id"], "together": together, "force": force,
                            "at": time_module.monotonic()}
    while len(_SERVICE_ASKS) > 32:
        _SERVICE_ASKS.popitem(last=False)
    return nonce

async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shutdown <bot> -- stop that bot, or the whole service it runs in, after asking which; only if nobody is using it."""
    if not await guard(update, context):
        return
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /shutdown <bot>\n"
            "Asks first: that bot alone, or the whole service it runs in. Either way it stops only if "
            "nobody is using it; otherwise you get the reasons and nothing stops. A stopped bot stays "
            f"down until its service next starts.\nKnown: {bot_list_hint()}")
        return
    found = await _service_of(update, context.args[0])
    if found is None:
        return
    bot, together = found
    nonce = _ask_service("shutdown", bot, together)
    others = [bot_id for bot_id in together if bot_id != bot["id"]]
    if others:
        text = (f"⏹ <b>{html.escape(bot['name'])}</b> shares one service with "
                f"{html.escape(_names(others))}.\n\n"
                f"<b>Only {html.escape(bot['name'])}</b>: the others carry on; it comes back when the "
                f"service next starts.\n<b>All {len(together)}</b>: the whole service stops and stays down "
                "until it is deployed or redeployed.\n\n"
                "Either way it happens only if nobody is using them.")
        rows = [[InlineKeyboardButton(f"Stop only {bot['name']}", callback_data=f"svc:{nonce}:one")],
                [InlineKeyboardButton(f"Stop all {len(together)}", callback_data=f"svc:{nonce}:all")],
                [InlineKeyboardButton("Cancel", callback_data=f"svc:{nonce}:no")]]
    else:
        text = (f"⏹ Stop <b>{html.escape(bot['name'])}</b>? It is alone in its service, which stops and "
                "stays down until it is deployed or redeployed -- only if nobody is using it.")
        rows = [[InlineKeyboardButton(f"Stop {bot['name']}", callback_data=f"svc:{nonce}:all"),
                 InlineKeyboardButton("Cancel", callback_data=f"svc:{nonce}:no")]]
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/restart <bot> [force] -- restart the service that bot runs in, after asking; force skips the check of who is using it."""
    if not await guard(update, context):
        return
    args = [arg.lower() for arg in context.args]
    force = "force" in args
    words = [arg for arg in context.args if arg.lower() != "force"]
    if len(words) != 1:
        await update.message.reply_text(
            "Usage: /restart <bot> [force]\nRestarts the service that bot runs in -- every bot in it -- "
            "once nobody is using it; force restarts at once, whatever is running (for a stuck service).\n"
            f"Known: {bot_list_hint()}")
        return
    found = await _service_of(update, words[0])
    if found is None:
        return
    bot, together = found
    nonce = _ask_service("restart", bot, together, force)
    how = ("<b>at once</b>, whatever is running -- anybody mid-something loses it" if force
           else "once nobody is using it; otherwise you get the reasons and nothing restarts")
    text = (f"🔄 Restart the service of <b>{html.escape(bot['name'])}</b>? Every bot in it restarts: "
            f"{html.escape(_names(together))}.\nIt restarts {how}.")
    label = f"Restart all {len(together)}" + (" now" if force else "")
    rows = [[InlineKeyboardButton(label, callback_data=f"svc:{nonce}:all"),
             InlineKeyboardButton("Cancel", callback_data=f"svc:{nonce}:no")]]
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))

async def service_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap under /shutdown or /restart: queue what was chosen, once."""
    if not await guard(update, context):
        return
    query = update.callback_query
    _, nonce, choice = (query.data.split(":") + ["", ""])[:3]
    ask = _SERVICE_ASKS.pop(nonce, None)
    await query.answer()
    if ask is None or time_module.monotonic() - ask["at"] > SERVICE_ASK_SECONDS:
        await edit_in_place(query.message, context.bot, "That question has expired -- nothing was asked. "
                                                        "Send the command again.")
        return
    if choice not in ("one", "all"):
        await edit_in_place(query.message, context.bot, "Cancelled -- nothing was asked.")
        return
    bot = resolve_bot(ask["bot"])
    if ask["kind"] == "restart":
        command, args, chosen = "restart", (["force"] if ask["force"] else []), f"restart {_names(ask['together'])}"
    elif choice == "one":
        command, args, chosen = "softstopbot", [], f"stop only {bot['name']}"
    else:
        command, args, chosen = "softstop", [], f"stop {_names(ask['together'])}"
    await edit_in_place(query.message, context.bot, f"Asked: {chosen}. The answer follows.")
    await _dispatch(update, context, bot, command, args)

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/run <bot> <command> [args] -- the general form."""
    if not await guard(update, context):
        return
    if len(context.args) < 2:
        lines = ["Usage: /run &lt;bot&gt; &lt;command&gt; [args]", "", "<b>Bots:</b> " + bot_list_hint(), "", "<b>Commands:</b>"]
        lines += [f"  <code>{name}</code> — {desc}" for name, desc in family_link.COMMAND_HELP.items()]

        try:
            beats = await asyncio.to_thread(db.all_heartbeats)
        except Exception:
            beats = []
        extra: dict = {}
        for beat in beats:
            for name in _accepted_commands(beat) - set(family_link.COMMANDS):
                extra.setdefault(name, []).append(
                    (resolve_bot(beat["bot_id"]) or {}).get("name", beat["bot_id"]))
        for name, owners in sorted(extra.items()):
            lines.append(f"  <code>{html.escape(name)}</code> — only on "
                         f"{html.escape(', '.join(sorted(owners)))}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return

    bot = resolve_bot(context.args[0])
    if not bot:
        await update.message.reply_text(f"No such bot: {context.args[0]}. Known: {bot_list_hint()}")
        return
    await _dispatch(update, context, bot, context.args[1].lower(), context.args[2:])

def _shortcut(command: str, min_args: int, usage: str, default_bot: str | None = None):
    """Builds /whois, /say, /logs and friends -- each is /run with the command fixed and the first argument still naming the target bot."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await guard(update, context):
            return
        args = list(context.args)
        bot = resolve_bot(args[0]) if args else None
        if bot is not None:
            args = args[1:]
        elif default_bot:
            bot = resolve_bot(default_bot)
        if bot is None:
            if len(args) < min_args or not args:
                await update.message.reply_text(usage or f"Which bot? Known: {bot_list_hint()}")
            else:
                await update.message.reply_text(
                    f"No such bot: {args[0]}. Known: {bot_list_hint()}")
            return
        if len(args) < max(0, min_args - 1):
            await update.message.reply_text(usage)
            return
        await _dispatch(update, context, bot, command, args)
    return handler

_FANOUTS: "OrderedDict[int, dict]" = OrderedDict()
MAX_FANOUTS = 64

def _remember_fanout(command_id: int, group: dict) -> None:
    _FANOUTS[command_id] = group
    while len(_FANOUTS) > MAX_FANOUTS:
        _FANOUTS.popitem(last=False)

async def _fanout(update: Update, context: ContextTypes.DEFAULT_TYPE,
                  command: str, args: list, title: str, footer: str = "") -> None:
    """Ask every child bot the same thing and gather the answers into one message."""
    targets = list(CHILDREN)
    live = await LiveMessage.reply_to(update.effective_message,
                                      f"{title} — asking all {len(targets)}…",
                                      parse_mode=ParseMode.HTML)
    group = {"live": live, "title": title, "command": command, "footer": footer,
             "answers": {}, "queued": set()}

    for child in targets:
        beat = await asyncio.to_thread(db.heartbeat_of, child["id"])
        stale = _too_old_for((beat or {}).get("version"), command, args)
        if stale:
            group["answers"][child["id"]] = (
                "⏳", f"on {(beat or {}).get('version') or 'an unknown version'} — "
                     f"too old for this command; it will have it after the next release.")
            continue
        group["queued"].add(child["id"])
        command_id = await asyncio.to_thread(
            db.queue_command, child["id"], command, " ".join(args),
            update.effective_user.id, update.effective_chat.id,
        )
        _remember_fanout(command_id, group)
    if not group["queued"]:
        await _render_fanout(context, group)

def _fanout_text(group: dict) -> str:
    """One section per bot, in the order the family is declared in -- which is the order every other list in this bot uses, and the order the owner reads them in."""
    parts = []
    for child in CHILDREN:
        answer = group["answers"].get(child["id"])
        if answer is None:
            continue
        mark, body = answer
        parts.append(f"{mark} <b>{html.escape(child['name'])}</b>\n"
                     f"{html.escape(body.strip() or '(no output)')}")
    waiting = len(group["queued"] - set(group["answers"]))
    head = f"{group['title']}"
    if waiting > 0:
        head += f" — waiting on {waiting} more"
    text = head + "\n\n" + "\n\n".join(parts)

    if not waiting and group.get("footer"):
        text += "\n\n" + group["footer"]
    return text

async def _render_fanout(context: ContextTypes.DEFAULT_TYPE, group: dict) -> None:
    text = _fanout_text(group)
    if len(text) <= TELEGRAM_MAX_CHARS:
        await group["live"].set(context.bot, text, parse_mode=ParseMode.HTML)
        return

    await group["live"].set(context.bot, f"{group['title']} — the answers are attached.")
    await context.bot.send_document(
        chat_id=group["live"].chat_id,
        document=BytesIO(re.sub(r"<[^>]+>", "", text).encode("utf-8")),
        filename=f"{group['command']}.txt")

async def _deliver_fanout(context: ContextTypes.DEFAULT_TYPE, group: dict, result: dict) -> None:
    target = resolve_bot(result["target_bot"])
    key = target["id"] if target else result["target_bot"]
    if result["status"] == "timeout":
        group["answers"][key] = ("⏳", f"no answer in {COMMAND_TIMEOUT_SECONDS}s — that bot looks down.")
    else:
        group["answers"][key] = ("✅" if result["ok"] else "⚠️", result["output"] or "(no output)")
    await _render_fanout(context, group)

def _recorded_line(counts: dict, hours: int) -> str:
    """One line summarising what the shared table holds for the same window the live counts cover -- which is what makes the difference between the two commands visible without explaining it every time."""
    if not counts:
        return (f"Nothing recorded in the last {hours}h either.\n"
                f"<i>Above: since each process started, lost on a redeploy. "
                f"This line: the shared record, which is not.</i>")
    totals: dict = {}
    for per_level in counts.values():
        for level, numbers in per_level.items():
            totals[level] = totals.get(level, 0) + numbers["incidents"]
    parts = [f"{problems.LEVEL_ICONS.get(level, '•')} {count} "
             f"{problems.LEVEL_NAMES.get(level, '?')}"
             for level, count in sorted(totals.items())]
    return (f"<b>Recorded, last {hours}h:</b> " + " · ".join(parts)
            + "\n<i>Above: since each process started, lost on a redeploy. "
              "This line: the shared record, which is not. "
              "<code>/nightly</code> breaks it down, <code>/reports</code> goes back further.</i>")

async def errors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/errors <bot> is that bot's errors since it started."""
    if not await guard(update, context):
        return
    args = list(context.args)
    if args:
        bot = resolve_bot(args[0])
        if bot is None:
            await update.message.reply_text(f"No such bot: {args[0]}. Known: {bot_list_hint()}")
            return
        await _dispatch(update, context, bot, "errors", args[1:])
        return
    try:
        counts = await asyncio.to_thread(family_link.problem_counts_since,
                                         NIGHTLY_REPORT_HOURS)
        footer = _recorded_line(counts, NIGHTLY_REPORT_HOURS)
    except Exception:

        logger.debug("Could not read the recorded problem counts", exc_info=True)
        footer = ""
    await _fanout(update, context, "errors", [],
                  "⚠️ <b>Errors since each bot started</b>", footer=footer)

LOG_FILES = {"errorlog": "errors", "botlog": "bot", "problemlog": "problems"}
LOG_TITLES = {"errorlog": "errors.log", "botlog": "bot.log", "problemlog": "problems.log"}

def _log_picker(kind: str, lines: str = "") -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(b["name"], callback_data=f"logpick:{kind}:{b['id']}:{lines}")
               for b in ALL_BOTS if b["id"] != BOT_NAME]
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])

def _log_shortcut(kind: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await guard(update, context):
            return
        args = list(context.args)
        named = [a for a in args if not a.isdigit()]
        lines = next((a for a in args if a.isdigit()), "")
        target = resolve_bot(named[0]) if named else None
        if named and target is None:
            await update.message.reply_text(f"No such bot: {named[0]}. Known: {bot_list_hint()}")
            return
        if target is None:
            await update.message.reply_text(f"Whose {LOG_TITLES[kind]}?",
                                            reply_markup=_log_picker(kind, lines))
            return
        await _dispatch(update, context, target, "logs", ([lines] if lines else []) + [LOG_FILES[kind]])
    return handler

async def log_pick_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A bot tapped under /errorlog, /botlog or /problemlog. The buttons stay, so another bot's log is one more tap."""
    query = update.callback_query
    if not await guard(update, context):
        await query.answer()
        return
    parts = (query.data or "").split(":")
    kind = parts[1] if len(parts) > 1 else ""
    target = resolve_bot(parts[2]) if len(parts) > 2 else None
    lines = parts[3] if len(parts) > 3 and parts[3].isdigit() else ""
    if kind not in LOG_FILES or target is None:
        await query.answer("That button no longer works.", show_alert=True)
        return
    await query.answer()
    await _dispatch(update, context, target, "logs", ([lines] if lines else []) + [LOG_FILES[kind]])

_PING_TRACES: "OrderedDict[int, dict]" = OrderedDict()
MAX_PING_TRACES = 64

def _remember_trace(command_id: int, trace: dict) -> None:
    _PING_TRACES[command_id] = trace
    while len(_PING_TRACES) > MAX_PING_TRACES:
        _PING_TRACES.popitem(last=False)

def _ms(delta) -> str:
    """A duration, in whichever unit makes it readable."""
    if delta is None:
        return "     ?"
    ms = delta.total_seconds() * 1000 if hasattr(delta, "total_seconds") else float(delta)
    if ms >= 1000:
        return f"{ms / 1000:6.2f} s"
    return f"{ms:6.0f} ms"

def _row(label: str, value: str) -> str:
    return f"{label:<30}{value}"

def _describe_end(name: str, where: str, probe: dict) -> str:
    if not probe or "error" in probe:
        return _row(name, (probe or {}).get("error", "not reported"))
    skew = probe.get("skew_ms", 0)
    bits = [f"Supabase {_ms(probe.get('db_ms', 0)).strip()} per query",
            f"clock {skew:+.0f} ms"]
    return f"{name}\n  {where}\n  " + " · ".join(bits)

def _render_ping(trace: dict, result: dict) -> str:
    """The report."""
    name = trace["bot"]["name"]
    created, claimed = result.get("created_at"), result.get("claimed_at")
    finished, taken = result.get("finished_at"), result.get("taken_at")

    if result["status"] == "timeout" or claimed is None:
        return (f"🏓 <b>{html.escape(name)}</b> — no answer in {COMMAND_TIMEOUT_SECONDS}s.\n"
                f"It never picked the ping up, which means its process is not running.")

    there = {}
    try:
        there = json.loads(result.get("output") or "{}")
    except ValueError:
        pass

    lines = [
        _row("you → Telegram → ManagerBot", _ms(trace["to_manager"]) + "   ±1 s"),
        _row("ManagerBot → Telegram (ack)", _ms(trace["ack_ms"])),
        _row("ManagerBot → Supabase (queue)", _ms(trace["queue_ms"])),
        _row(f"queued → {name} claimed it", _ms(claimed - created)),
        _row(f"{name} answering", _ms(finished - claimed)),
        _row("answer → ManagerBot collected it", _ms(taken - finished)),
        "─" * 40,
        _row("bus round trip", _ms(taken - created)),
    ]

    head = (f"🏓 <b>{html.escape(name)}</b> — {_ms(taken - created).strip()} "
            f"round trip on the admin bus")
    ends = "\n\n".join([
        _describe_end("ManagerBot", trace["here"].get("where", "?"), trace["here"]),
        _describe_end(name, there.get("where", "?"), there),
    ])
    up = there.get("up")
    tail = f"\nUp {up}." if up else ""
    return (f"{head}\n\n<pre>{html.escape(chr(10).join(lines))}</pre>\n"
            f"{_render_user_wait(name, there.get('user') or {})}"
            f"<b>Each end</b>\n{html.escape(ends)}{html.escape(tail)}")

def _user_wait_ms(result: dict) -> "float | None":
    """The number the summary sorts on and shows first: what a person waits for this bot's own work on an info command."""
    try:
        there = json.loads(result.get("output") or "{}")
    except ValueError:
        return None
    value = (there.get("user") or {}).get("total_ms")
    return float(value) if isinstance(value, (int, float)) else None

def _render_user_wait(name: str, user: dict) -> str:
    """The other half of the report, and the half anybody outside this chat would recognise."""
    if not user:
        return ""
    if "total_ms" not in user:
        trouble = user.get("info_error") or user.get("telegram_error")
        if not trouble:
            return ""
        return f"<b>What a user waits for</b>\n{html.escape(trouble)}\n\n"
    lines = [
        _row("reading their row (info)", _ms(user["info_ms"])),
        _row("handing the reply to Telegram", _ms(user["telegram_ms"])),
        "-" * 40,
        _row("an info command, here", _ms(user["total_ms"])),
    ]
    note = (f"A /start in {name}: the database read plus the send. Their own trip "
            f"to Telegram is on top of this, and cannot be measured from either end.")
    return (f"<b>What a user waits for</b>\n"
            f"<pre>{html.escape(chr(10).join(lines))}</pre>{html.escape(note)}\n\n")

async def _ping_one(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: dict) -> None:
    started = time_module.perf_counter()
    now = datetime.now(timezone.utc)
    live = await LiveMessage.reply_to(update.message, f"🏓 {bot['name']} — timing the round trip…")
    ack_ms = (time_module.perf_counter() - started) * 1000

    try:
        here = await asyncio.to_thread(family_link.ping_probe)
    except Exception as exc:
        here = {"error": f"{type(exc).__name__}: {exc}"}

    queue_started = time_module.perf_counter()
    command_id = await asyncio.to_thread(
        db.queue_command, bot["id"], "ping", "trace",
        update.effective_user.id, update.effective_chat.id,
    )
    queue_ms = (time_module.perf_counter() - queue_started) * 1000

    _remember_trace(command_id, {
        "bot": bot, "live": live, "here": here,
        "to_manager": now - update.message.date,
        "ack_ms": ack_ms, "queue_ms": queue_ms,
    })

async def broadcast_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ping <bot> reports the round trip leg by leg."""
    if not await guard(update, context):
        return
    if context.args:
        bot = resolve_bot(context.args[0])
        if not bot:
            await update.message.reply_text(f"No such bot: {context.args[0]}. Known: {bot_list_hint()}")
            return
        await _ping_one(update, context, bot)
        return

    started = time_module.perf_counter()
    now = datetime.now(timezone.utc)
    live = await LiveMessage.reply_to(update.message, f"🏓 Pinging all {len(CHILDREN)}…")
    ack_ms = (time_module.perf_counter() - started) * 1000
    try:
        here = await asyncio.to_thread(family_link.ping_probe)
    except Exception as exc:
        here = {"error": f"{type(exc).__name__}: {exc}"}

    group = {"live": live, "rows": {}, "expected": len(CHILDREN), "details": {}}
    for child in CHILDREN:
        queue_started = time_module.perf_counter()
        command_id = await asyncio.to_thread(
            db.queue_command, child["id"], "ping", "trace",
            update.effective_user.id, update.effective_chat.id,
        )
        _remember_trace(command_id, {
            "bot": child, "group": group, "here": here,
            "to_manager": now - update.message.date, "ack_ms": ack_ms,
            "queue_ms": (time_module.perf_counter() - queue_started) * 1000,
        })

_PING_GROUPS: "OrderedDict[tuple[int, int], dict]" = OrderedDict()
MAX_PING_GROUPS = 16

def _remember_group(group: dict) -> None:
    live = group["live"]
    _PING_GROUPS[(live.chat_id, live.message_id)] = group
    while len(_PING_GROUPS) > MAX_PING_GROUPS:
        _PING_GROUPS.popitem(last=False)

def _ping_keyboard(group: dict) -> InlineKeyboardMarkup:
    live = group["live"]
    key = f"{live.chat_id}:{live.message_id}"
    buttons = [
        InlineKeyboardButton(child["name"], callback_data=f"pingdet:{key}:{child['id']}")
        for child in CHILDREN if child["id"] in group["details"]
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("📋 All details", callback_data=f"pingdet:{key}:*")])
    return InlineKeyboardMarkup(rows)

async def ping_detail_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of those buttons."""
    if not await guard(update, context):
        return
    query = update.callback_query
    _, chat_id, message_id, which = query.data.split(":", 3)
    group = _PING_GROUPS.get((int(chat_id), int(message_id)))
    if group is None:

        await query.answer("That ping is no longer in memory — run /ping again.",
                           show_alert=True)
        return

    wanted = [c for c in CHILDREN
              if (which == "*" or which == c["id"]) and c["id"] in group["details"]]
    if not wanted:
        await query.answer("Nothing was recorded for that one.", show_alert=True)
        return
    await query.answer()

    body = "\n\n".join(_render_ping(*group["details"][c["id"]]) for c in wanted)
    if len(body) <= TELEGRAM_MAX_CHARS:
        await context.bot.send_message(chat_id=query.message.chat_id, text=body,
                                       parse_mode=ParseMode.HTML)
        return

    await send_long(context, query.message.chat_id,
                    re.sub(r"<[^>]+>", "", body), filename="ping.txt")

def _summary_lines(rows: dict) -> list:
    """The family ping's table: one bot a line, fastest first."""
    def key(item):
        row = item[1]
        if row.get("user") is not None:
            return (0, row["user"])
        if row.get("bus") is not None:
            return (1, row["bus"])
        return (2, 0.0)

    lines = []
    for name, row in sorted(rows.items(), key=key):
        if row.get("note"):
            lines.append(f"{name:<14}{row['note']}")
            continue
        user = _ms(row["user"]) if row.get("user") is not None else "     ?"
        lines.append(f"{name:<14}{user} user   {_ms(row['bus'])} bus")
    return lines

async def _deliver_ping(context: ContextTypes.DEFAULT_TYPE, trace: dict, result: dict) -> None:
    """A ping's answer replaces the message that announced it, rather than arriving underneath -- and moves to the bottom of the chat by itself if anything was said in the meantime (see live_message.py)."""
    group = trace.get("group")
    if group is None:
        await trace["live"].set(context.bot, _render_ping(trace, result), parse_mode=ParseMode.HTML)
        return

    name = trace["bot"]["name"]
    if result["status"] == "timeout" or not result.get("claimed_at"):
        group["rows"][name] = {"user": None, "bus": None, "note": "no answer — down"}
    else:
        group["rows"][name] = {
            "user": _user_wait_ms(result),
            "bus": (result["taken_at"] - result["created_at"]).total_seconds() * 1000,
            "note": "",
        }

    group["details"][trace["bot"]["id"]] = (trace, result)
    lines = _summary_lines(group["rows"])
    missing = group["expected"] - len(group["rows"])
    text = f"🏓 <b>Family ping</b>\n<pre>{html.escape(chr(10).join(lines))}</pre>"
    keyboard = None
    if missing > 0:
        text += f"\nWaiting on {missing} more (down after {COMMAND_TIMEOUT_SECONDS}s)."
    else:
        text += ("\n<b>user</b> is an info command answered on the spot — one database "
                 "read and the send — which is the path everybody except this chat "
                 "takes. <b>bus</b> is the admin round trip through Postgres, which "
                 "nobody using a bot ever takes. Fastest first; tap a bot for its "
                 "breakdown.")
        _remember_group(group)
        keyboard = _ping_keyboard(group)
    await group["live"].set(context.bot, text, parse_mode=ParseMode.HTML,
                            reply_markup=keyboard)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """No command queue involved -- this is read straight out of the shared database, so it answers for bots that are currently down too."""
    if not await guard(update, context):
        return
    hours = int(context.args[0]) if context.args and context.args[0].isdigit() else 24
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    by_schema = await asyncio.to_thread(
        db.active_users_by_schema, [b["schema"] for b in ALL_BOTS], since, True
    )
    lines = [f"👥 Active users, last {hours}h (all-time known in brackets)", ""]
    for bot in ALL_BOTS:
        counts = by_schema.get(bot["schema"])
        if counts is None:
            lines.append(f"  {bot['name']}: — (no tables yet)")
        else:
            lines.append(f"  {bot['name']}: {counts[0]}  [{counts[1]}]")

    try:
        people = await asyncio.to_thread(db.unique_people, [b["schema"] for b in CHILDREN])
        lines.append(f"👤 Unique people across all bots: {people} (the gift's mark is {family_link.PROMO_USERS})")
    except Exception as exc:
        lines.append(f"👤 Unique people across all bots: could not count ({type(exc).__name__})")
    await update.message.reply_text("\n".join(lines))

async def donations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return

    by_schema = await asyncio.to_thread(
        db.donations_by_schema, [b["schema"] for b in ALL_BOTS]
    )
    lines = ["💝 Paid donations, per bot", ""]
    any_paid = False
    for bot in ALL_BOTS:
        per_currency = by_schema.get(bot["schema"])
        if not per_currency:
            continue
        name = bot["name"]
        for currency, count, total in per_currency:
            any_paid = True
            unit = "⭐" if currency == "XTR" else f" {currency} (minor units)"
            lines.append(f"  {name}: {total}{unit} over {count} payment(s)")
    if not any_paid:
        lines.append("  Nothing paid yet, anywhere.")
    await update.message.reply_text("\n".join(lines))

def _parse_balance_change(arg: str):
    """`+100`, `-50` or `=0` -> ("add"/"set", amount). None if it is not one."""
    if len(arg) < 2 or arg[0] not in "+-=":
        return None
    try:
        amount = int(arg[1:])
    except ValueError:
        return None
    if arg[0] == "=":
        return ("set", amount)
    return ("add", amount if arg[0] == "+" else -amount)

def _ledger_lines(rows) -> list:
    out = []
    for row in rows:
        when = row["occurred_at"].strftime("%Y-%m-%d %H:%M")
        sign = "+" if row["delta"] > 0 else ""
        paid = f", {row['stars_paid']} ⭐ paid" if row["stars_paid"] else ""
        detail = f" — {html.escape(str(row['detail']))}" if row["detail"] else ""
        out.append(f"  {when}  {sign}{row['delta']} ⚡ → {row['balance_after']} ⚡"
                   f"  [{row['reason']} via {row['bot_id']}{paid}]{detail}")
    return out

BALANCE_OVERVIEW_ROWS = 20
BALANCE_HISTORY_ROWS = 12

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/balance                -- the family-wide picture /balance <user_id>      -- one person, with their last movements /balance <user_id> +100 -- give them 100 credits /balance <user_id> -100 -- take 100 away (may go negative) /balance <user_id> =0   -- set it to exactly 0"""
    if not await guard(update, context):
        return
    args = context.args or []

    if not args:
        totals, rows = await asyncio.to_thread(family_link.star_balance_overview, BALANCE_OVERVIEW_ROWS)
        lines = [
            "⚡ Credit balances, whole family",
            "",
            f"  Outstanding: {totals['outstanding']} ⚡ across {totals['wallets']} wallet(s)",
            f"  Ever credited: {totals['topped_up']} ⚡   ever spent: {totals['spent']} ⚡",
            f"  Real money behind it: {totals['stars_paid']} ⭐",
            f"  Bonus credit still unspent (expires if unused): {totals['bonus']} ⚡",
            f"  Rate: 1 ⭐ = {family_link.credit_for_stars(1)} ⚡ · ladder: "
            + (", ".join(f"next {size} ⭐ at {mult:g}x" for size, mult in family_link.TOPUP_LADDER) or "off")
            + f" · bonus expires after {family_link.BONUS_EXPIRY_DAYS} days",
        ]
        if rows:
            lines += ["", "Largest balances:"]
            for row in rows:
                lines.append(f"  <code>{row['user_id']}</code>  {row['balance']} ⚡"
                             f"  (in {row['topped_up']}, out {row['spent']},"
                             f" paid {row['stars_paid']} ⭐)")
        else:
            lines += ["", "  Nobody holds any credit yet."]
        lines += ["", "One person: /balance &lt;user_id&gt; · "
                      "change it: /balance &lt;user_id&gt; +100"]
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return

    if not args[0].lstrip("-").isdigit():
        await update.message.reply_text(
            "Usage: /balance [user_id] [+100 | -100 | =0]\n"
            "A numeric Telegram user id — /whois &lt;bot&gt; &lt;id&gt; if you need "
            "to check who it is.",
            parse_mode=ParseMode.HTML)
        return
    user_id = int(args[0])

    if len(args) > 1:
        change = _parse_balance_change(args[1])
        if change is None:
            await update.message.reply_text(
                f"Didn't understand <code>{html.escape(args[1])}</code>. Use +100 to add, "
                "-100 to take away, or =100 to set it exactly.",
                parse_mode=ParseMode.HTML)
            return
        kind, amount = change
        who = update.effective_user
        detail = f"by admin {who.id}" + (f" (@{who.username})" if who.username else "")
        if kind == "set":
            after = await asyncio.to_thread(
                family_link.set_star_balance, user_id, amount, "adjustment", detail)
            what = f"set to {after} ⚡"
        else:
            after = await asyncio.to_thread(
                family_link.move_stars, user_id, amount, "adjustment", detail)
            what = f"{'+' if amount > 0 else ''}{amount} ⚡ → {after} ⚡"

        await asyncio.to_thread(
            family_link.report_event, "info", "payment",
            f"Balance of {user_id} {what} by admin {who.id}")
        await update.message.reply_text(
            f"⚡ <code>{user_id}</code>: {what}", parse_mode=ParseMode.HTML)

    totals = await asyncio.to_thread(family_link.star_totals, user_id)
    rows = await asyncio.to_thread(family_link.star_ledger_for, user_id, BALANCE_HISTORY_ROWS)
    lines = [
        f"⚡ <code>{user_id}</code>",
        "",
        f"  Balance: {totals['balance']} ⚡",
        f"  Credited over time: {totals['topped_up']} ⚡   spent: {totals['spent']} ⚡",
        f"  Actually paid: {totals['stars_paid']} ⭐",
        f"  Bonus credit: {totals['bonus']} ⚡"
        + (f", next {totals['bonus_next_amount']} ⚡ expires {totals['bonus_next_expiry']:%Y-%m-%d}"
           if totals["bonus"] else ""),
    ]
    if rows:
        lines += ["", "Last movements:"] + _ledger_lines(rows)
    else:
        lines += ["", "  No movements recorded."]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def addcredit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/addcredit <user_id> <amount> -- put ⚡ into anybody's balance by id."""
    if not await guard(update, context):
        return
    args = context.args or []
    amount_text = args[1].lstrip("+") if len(args) == 2 else ""
    if len(args) != 2 or not args[0].isdigit() or not amount_text.isdigit() or int(amount_text) <= 0:
        await update.message.reply_text(
            "Usage: /addcredit &lt;user_id&gt; &lt;amount&gt;\n"
            "Adds that many ⚡ to the account. It does not expire. "
            "To take credit away or set an exact number, use /balance.",
            parse_mode=ParseMode.HTML)
        return
    user_id, amount = int(args[0]), int(amount_text)
    who = update.effective_user
    detail = f"added by admin {who.id}" + (f" (@{who.username})" if who.username else "")
    after = await asyncio.to_thread(family_link.move_stars, user_id, amount, "grant", detail)
    await asyncio.to_thread(
        family_link.report_event, "info", "payment",
        f"+{amount} credit added to {user_id} by admin {who.id}, balance {after}")
    await update.message.reply_text(
        f"⚡ +{amount} added to <code>{user_id}</code>. Balance now {after} ⚡.",
        parse_mode=ParseMode.HTML)

EVENTS_DEFAULT = 15
EVENTS_MAX = 60

async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    limit = EVENTS_DEFAULT
    bot_id = None
    for arg in context.args:
        if arg.isdigit():
            limit = min(int(arg), EVENTS_MAX)
        else:
            match = resolve_bot(arg)
            if match:
                bot_id = match["id"]
    rows = await asyncio.to_thread(db.recent_events, limit, bot_id)
    if not rows:
        await update.message.reply_text("Nothing recorded yet.")
        return
    icons = {"info": "·", "warning": "⚠️", "error": "🔥", "critical": "🚨"}
    lines = [f"🗒 Last {len(rows)} event(s)" + (f" from {bot_id}" if bot_id else ""), ""]
    for row in rows:
        stamp = row["occurred_at"].strftime("%m-%d %H:%M")
        lines.append(f"{icons.get(row['level'], '·')} {stamp} [{row['bot_id']}] {row['message']}")
    await send_long(context, update.effective_chat.id, "\n".join(lines), "events.txt")

async def sql_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sql SELECT ..."""
    if not await guard(update, context):
        return
    query = update.message.text.partition(" ")[2].strip()
    if not query:
        await update.message.reply_text(
            'Usage: /sql SELECT ...\n\ne.g. /sql SELECT count(*) FROM sticker_bot.packs'
        )
        return
    if query.lower().split()[0] not in ("select", "with", "table", "explain", "show"):
        await update.message.reply_text("Read-only: start with SELECT, WITH, TABLE, EXPLAIN or SHOW.")
        return
    try:
        cols, rows = await asyncio.to_thread(db.run_readonly_query, query)
    except Exception as exc:
        await update.message.reply_text(f"⚠️ {type(exc).__name__}: {exc}")
        return
    if not rows:
        await update.message.reply_text("No rows.")
        return
    body = [" | ".join(cols), "-" * 40]
    body += [" | ".join("NULL" if v is None else str(v) for v in row) for row in rows]
    body.append(f"\n({len(rows)} row(s), capped at {db.SQL_MAX_ROWS})")
    await send_long(context, update.effective_chat.id, "\n".join(body), "query.txt")

BACKUP_PART_BYTES = int(os.environ.get("MBOT_BACKUP_PART_MB") or 49) * 1024 * 1024

def _backup_parts(size: int, limit: "int | None" = None) -> list:
    """(start, end) byte ranges of at most `limit` bytes, covering `size`."""
    limit = limit or BACKUP_PART_BYTES
    if size <= limit:
        return [(0, size)]
    return [(start, min(start + limit, size)) for start in range(0, size, limit)]

def _build_backup(out_path: Path) -> dict:
    """family_db.backup into `out_path`, and what the caption says about it."""
    import family_db
    try:
        family_db.backup(db.DATABASE_URL, out_path, None)
    except SystemExit as exc:

        raise RuntimeError(str(exc) or "nothing to back up") from None
    with zipfile.ZipFile(out_path) as archive:
        manifest = json.loads(archive.read("MANIFEST.json"))
    digest = hashlib.sha256()
    with open(out_path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    tables = manifest.get("tables") or []
    return {"tables": len(tables), "rows": sum(t.get("approx_rows", 0) for t in tables),
            "size": out_path.stat().st_size, "sha256": digest.hexdigest()}

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The whole shared database, every schema, as the archive family_db.py restores from -- sent here, and pinned."""
    if not await guard(update, context):
        return
    chat_id = update.effective_chat.id
    note = await update.message.reply_text("Backing up the whole database…")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    name = f"botfamily_{stamp}.zip"
    with tempfile.TemporaryDirectory(prefix="mbot-backup-") as folder:
        path = Path(folder) / name
        try:
            info = await asyncio.to_thread(_build_backup, path)
        except Exception as exc:
            logger.exception("Backup failed")
            await edit_in_place(note, context.bot, f"⚠️ Backup failed: {type(exc).__name__}: {exc}")
            return

        parts = _backup_parts(info["size"])
        summary = (f"{info['size'] / (1024 * 1024):.1f} MB · {info['tables']} tables · "
                   f"~{info['rows']} rows\nsha256 {info['sha256']}")
        pinned = 0
        for index, (start, end) in enumerate(parts, 1):
            with open(path, "rb") as handle:
                handle.seek(start)
                chunk = handle.read(end - start)
            if len(parts) == 1:
                filename = name
                caption = "🗄 Database backup — lossless, restorable\n" + summary
            else:
                filename = f"{name}.{index:03d}"
                caption = (f"🗄 Database backup — part {index} of {len(parts)}\n"
                           + summary + "\n(the checksum is of the joined file)")
            try:
                sent = await context.bot.send_document(
                    chat_id=chat_id, document=BytesIO(chunk), filename=filename,
                    caption=caption, read_timeout=300, write_timeout=300)
            except Exception as exc:
                logger.exception("Could not send backup part %s", index)
                await edit_in_place(note, context.bot,
                                    f"⚠️ The backup was made but part {index} of {len(parts)} "
                                    f"could not be sent: {type(exc).__name__}: {exc}")
                return
            try:
                await context.bot.pin_chat_message(
                    chat_id=chat_id, message_id=sent.message_id, disable_notification=True)
                pinned += 1
            except Exception:
                logger.warning("Could not pin backup part %s", index, exc_info=True)

    lines = [f"✅ Backed up and pinned ({pinned} of {len(parts)} pinned)." if pinned < len(parts)
             else ("✅ Backed up and pinned." if len(parts) == 1
                   else f"✅ Backed up in {len(parts)} parts, all pinned.")]
    if len(parts) > 1:
        lines.append(f"Join them first: <code>copy /b {name}.001+{name}.002 {name}</code> "
                     f"on Windows, or <code>cat {name}.0* &gt; {name}</code>.")
    lines.append("To restore: start each bot once against the new database, then "
                 "<code>python manager_bot/family_db.py restore --into &lt;url&gt; "
                 f"--file {name} --mode replace</code>. DEPLOY.md has the details.")
    await edit_in_place(note, context.bot, "\n".join(lines), parse_mode=ParseMode.HTML)

async def reports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reports [n] [mine] -- every problem the public bots have shown anybody, newest first."""
    if not await guard(update, context):
        return
    args = [a.lower() for a in context.args]
    shared_only = any(a in ("mine", "shared", "sent") for a in args)
    limit = next((int(a) for a in args if a.isdigit()), 15)
    rows = await asyncio.to_thread(family_link.recent_problem_reports,
                                   max(1, min(limit, 50)), shared_only)
    if not rows:
        await update.message.reply_text(
            "Nobody has attached their details to a problem yet." if shared_only
            else "No problems recorded yet.")
        return
    lines = ["🐞 " + ("Problems somebody put their name to" if shared_only
                      else "Latest problems, whether reported or not"), ""]
    for row in rows:
        problem = problems.PROBLEMS.get(row["code"])
        seen = f" ×{row['seen']}" if (row.get("seen") or 1) > 1 else ""
        mark = "🙋" if row.get("shared_at") else "  "
        lines.append(f"{mark}{_row_icon(row)} {row['reported_at']:%m-%d %H:%M} · {row['bot_id']} · "
                     f"{row['code']}{seen} ({row['incident']}) — "
                     f"{problem.title if problem else 'unknown code'}")
    kinds = " · ".join(f"{icon} {heading.lower()}"
                       for icon, heading, _ in (problems.KIND_LABELS[k] for k in problems.KIND_ORDER))
    lines += ["", "🚨 urgent (messaged when it happened) · ⚠️ fault",
              f"and where the bot was right and said why: {kinds}",
              "🙋 somebody attached their own details — /report <incident>",
              "What a code means: /decode <code>",
              f"The last {NIGHTLY_REPORT_HOURS}h, laid out: /nightly"]
    await send_long(context, update.effective_chat.id, "\n".join(lines), "reports.txt")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/report <incident> -- one problem in full, including whoever volunteered to be named on it."""
    if not await guard(update, context):
        return
    if not context.args:
        await update.message.reply_text("Usage: /report <incident> — the six-character "
                                        "code beside a problem, e.g. /report JNKS4N")
        return
    incident = context.args[0].strip().upper()
    row = await asyncio.to_thread(family_link.problem_report_by_incident, incident)
    if row is None:
        await update.message.reply_text(
            f"No problem recorded as {incident}. /reports lists the recent ones.")
        return
    lines = [f"🐞 <b>{html.escape(row['incident'])}</b> · {html.escape(row['bot_id'])} · "
             f"{html.escape(row['code'])}", ""]
    if row.get("occurred_at"):
        lines.append(f"Happened: {row['occurred_at']:%Y-%m-%d %H:%M} UTC")
    lines.append(f"Recorded: {row['reported_at']:%Y-%m-%d %H:%M} UTC")
    lines.append(f"Version: {html.escape(str(row.get('version') or '?'))}")
    level = int(row.get("level") or problems.level(row["code"]))
    lines.append(f"Level: {_row_icon(row)} {_row_level_name(row)}"
                 + (" — the owner was messaged when it happened" if level == problems.URGENT
                    else " — in the nightly report"))
    if (row.get("seen") or 1) > 1:
        lines.append(f"Shown {row['seen']} times")
    lines.append("")
    if row.get("shared_at"):
        who = f"id {row['user_id']}"
        if row.get("username"):
            who += f" (@{html.escape(str(row['username']))})"
        lines += [f"🙋 <b>Sent by</b> {who}",
                  f"Language {html.escape(str(row.get('user_lang') or '?'))} · "
                  f"{html.escape(str(row.get('chat_kind') or '?'))} chat · "
                  f"attached {row['shared_at']:%Y-%m-%d %H:%M} UTC", ""]
    else:
        lines += ["Nobody attached their details to this one — it was recorded "
                  "automatically, and holds nothing about who hit it.", ""]
    lines.append(html.escape(problems.decode(row["code"])))
    text = "\n".join(lines)
    if len(text) > TELEGRAM_MAX_CHARS:
        await send_long(context, update.effective_chat.id,
                        re.sub(r"<[^>]+>", "", text), f"{incident}.txt")
        return
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

MAX_INCIDENTS_LISTED = 4

MAX_CODES_PER_KIND = 6

def _row_icon(row) -> str:
    """🚨 / ⚠️ for the first two levels; for the third, its kind's own."""
    level = int(row.get("level") or problems.level(row["code"]))
    kind = problems.kind(row["code"]) if level == problems.REFUSED else None
    return problems.KIND_LABELS[kind][0] if kind else problems.LEVEL_ICONS.get(level, "•")

def _row_level_name(row) -> str:
    level = int(row.get("level") or problems.level(row["code"]))
    kind = problems.kind(row["code"]) if level == problems.REFUSED else None
    return problems.KIND_LABELS[kind][1].lower() if kind else problems.LEVEL_NAMES.get(level, "?")

def _group_problems(rows: list) -> dict:
    """{level: {(bot, code): [rows]}}, newest first within each group."""
    grouped: dict = {}
    for row in rows:
        level = int(row.get("level") or problems.level(row["code"]))
        grouped.setdefault(level, {}).setdefault((row["bot_id"], row["code"]), []).append(row)
    return grouped

def _bot_name(bot_id: str) -> str:
    found = resolve_bot(bot_id)
    return found["name"] if found else bot_id

ROUTES_PREFIX = "routewatch:"
ROUTES_ORDER = ("instagram", "tiktok", "twitter", "pinterest", "youtube")
ROUTES_NAMES = {"instagram": "Instagram", "tiktok": "TikTok", "twitter": "X",
                "pinterest": "Pinterest", "youtube": "YouTube"}
ROUTES_LOOK = {"up": "✅", "last_resort": "⚠️ last route only", "down": "❌ down",
               "sample_gone": "❔ sample post gone"}

ROUTES_STALE_S = 2 * 86400

def _ago(seconds: float) -> str:
    hours = seconds / 3600
    return f"{hours:.0f}h" if hours < 48 else f"{hours / 24:.0f}d"

def routes_section(settings: dict, now: float) -> "list[str]":
    """The report's download-routes lines, from the route check's settings. Pure."""
    try:
        last = float(settings.get(ROUTES_PREFIX + "last_run") or "")
    except ValueError:
        last = None
    if last is None:
        return ["\n🛣 <b>Download routes</b> — not checked yet "
                "(<code>/run downloaderbot routewatch</code>)"]
    states = {}
    for key, value in settings.items():
        if not key.startswith(ROUTES_PREFIX + "state:"):
            continue
        parts = (value or "").split("|")
        try:
            states[key[len(ROUTES_PREFIX + "state:"):]] = (parts[0], float(parts[1]))
        except (IndexError, ValueError):
            continue
    head = f"\n🛣 <b>Download routes</b> · checked {_ago(now - last)} ago"
    if now - last > ROUTES_STALE_S:
        head += " — ⚠️ the daily check has stopped running"
    order = [p for p in ROUTES_ORDER if p in states] + sorted(p for p in states if p not in ROUTES_ORDER)
    shown = []
    for platform in order:
        state, since = states[platform]
        look = ROUTES_LOOK.get(state, html.escape(state))
        if state != "up" and now - since >= 86400:
            look += f" for {_ago(now - since)}"
        shown.append(f"{html.escape(ROUTES_NAMES.get(platform, platform))} {look}")
    return [head, "  " + " · ".join(shown)] if shown else [head]

def _brief_line(code: str) -> str:
    """The code's own plain-words line, under it: what the person ran into."""
    text = problems.brief(code)
    return f"\n      <i>{html.escape(text)}</i>" if text else ""

def build_problem_report(rows: list, hours: int, feedback: "list | None" = None,
                         feedback_note: "str | None" = None, routes: "dict | None" = None,
                         now: "float | None" = None, people: "list | None" = None) -> str:
    """The message."""
    grouped = _group_problems(rows)
    signed = [row for row in rows if row.get("shared_at")]
    lines = [f"🌙 <b>Nightly report, last {hours}h</b>"]
    if people:
        lines += people

    urgent = grouped.get(problems.URGENT, {})
    if urgent:
        total = sum(len(group) for group in urgent.values())
        lines.append(f"\n🚨 <b>Urgent — {total}</b>")
        for (bot_id, code), group in sorted(urgent.items()):
            problem = problems.PROBLEMS.get(code)
            for row in group:
                mark = " 🙋" if row.get("shared_at") else ""
                lines.append(
                    f"  {html.escape(_bot_name(bot_id))} · <code>{html.escape(code)}</code> "
                    f"({html.escape(row['incident'])}) {row['reported_at']:%H:%M} — "
                    f"{html.escape(problem.title if problem else 'unknown code')}{mark}")

    faults = grouped.get(problems.FAULT, {})
    if faults:
        total = sum(len(group) for group in faults.values())
        bots = len({bot_id for bot_id, _ in faults})
        lines.append(f"\n⚠️ <b>Faults — {total} across {bots} bot(s)</b>")
        for (bot_id, code), group in sorted(faults.items(), key=lambda item: -len(item[1])):
            problem = problems.PROBLEMS.get(code)
            shown = [row["incident"] for row in group[:MAX_INCIDENTS_LISTED]]
            more = len(group) - len(shown)
            incidents = ", ".join(html.escape(incident) for incident in shown)
            if more:
                incidents += f", +{more}"
            mark = " 🙋" if any(row.get("shared_at") for row in group) else ""
            lines.append(
                f"  {html.escape(_bot_name(bot_id))} · <code>{html.escape(code)}</code> "
                f"×{len(group)} — {html.escape(problem.title if problem else 'unknown code')}"
                f"{mark}{_brief_line(code)}\n      {incidents}")

    by_kind: dict = {}
    for (bot_id, code), group in grouped.get(problems.REFUSED, {}).items():
        by_kind.setdefault(problems.kind(code) or problems.GUIDED, []).append((bot_id, code, group))
    for kind in problems.KIND_ORDER:
        entries = sorted(by_kind.get(kind, ()), key=lambda e: (-len(e[2]), e[0], e[1]))
        if not entries:
            continue
        icon, heading, _ = problems.KIND_LABELS[kind]
        total = sum(len(group) for _, _, group in entries)
        lines.append(f"\n{icon} <b>{html.escape(heading)} — {total}</b>")
        for bot_id, code, group in entries[:MAX_CODES_PER_KIND]:
            problem = problems.PROBLEMS.get(code)
            count = f" ×{len(group)}" if len(group) > 1 else ""
            lines.append(
                f"  {html.escape(_bot_name(bot_id))} · <code>{html.escape(code)}</code>{count} — "
                f"{html.escape(problem.title if problem else 'unknown code')}{_brief_line(code)}")
        rest = entries[MAX_CODES_PER_KIND:]
        if rest:
            lines.append(f"  +{sum(len(group) for _, _, group in rest)} more, under "
                         f"{len(rest)} other code(s) — <code>/reports</code>")

    if not rows:
        lines.append("\nNothing at all — no bot showed anybody a problem today.")

    if routes is not None:
        lines += routes_section(routes, time_module.time() if now is None else now)

    if feedback:
        lines.append(f"\n💬 <b>Feedback — {len(feedback)}</b> · read only")
        lines += [_feedback_block(item) for item in feedback]
    elif feedback_note:
        lines.append(f"\n💬 {html.escape(feedback_note)}")

    if signed:
        incidents = ", ".join(f"<code>{html.escape(row['incident'])}</code>" for row in signed[:8])
        lines.append(f"\n🙋 <b>{len(signed)} attached their own details</b>: {incidents}"
                     f"\n  <code>/report &lt;incident&gt;</code> to see what they sent.")

    lines.append("\n<code>/reports</code> for the longer history, "
                 "<code>/errors</code> for what is happening right now.")
    return "\n".join(lines)

PEOPLE_AT_LAST_REPORT = "nightly:people"

def people_section(total: "int | None", last_day: "int | None", complete: bool,
                   before: "tuple | None") -> "list[str]":
    """The report's people lines; `before` is (total, last 24h) at the last scheduled report, or None before the first one."""
    def change(now, then):
        if now is None or then is None:
            return ""
        return f" ({now - then:+d} since the last report)"
    total_text = "could not count" if total is None else str(total)
    day_text = "could not count" if last_day is None else str(last_day)
    if last_day is not None and not complete:
        day_text += " (AnonBot left out: the data key does not open)"
    return ["\n👥 <b>Unique users</b>",
            f"  All bots, all time: {total_text}{change(total, before[0] if before else None)}",
            f"  Last 24h: {day_text}{change(last_day, before[1] if before else None)}"]

async def _people_report(remember: bool) -> "list[str]":
    """people_section for now; `remember` (the scheduled report only) keeps tonight's numbers for tomorrow's change, /nightly on demand only reads them."""
    schemas = [b["schema"] for b in CHILDREN]
    total = last_day = None
    complete = True
    try:
        total = await asyncio.to_thread(db.unique_people, schemas)
    except Exception:
        logger.warning("Couldn't count the people for the nightly report", exc_info=True)
    try:
        last_day, complete = await asyncio.to_thread(
            db.people_since, schemas, datetime.now(timezone.utc) - timedelta(hours=24))
    except Exception:
        logger.warning("Couldn't count the last day's people for the nightly report", exc_info=True)
    before = None
    try:
        saved = await asyncio.to_thread(db.get_setting, PEOPLE_AT_LAST_REPORT)
        if saved:
            first, second = saved.split("|")[:2]
            before = (int(first) if first else None, int(second) if second else None)
    except Exception:
        logger.debug("Couldn't read the last report's people counts", exc_info=True)
    if remember and total is not None and last_day is not None and complete:
        try:
            await asyncio.to_thread(db.set_setting, PEOPLE_AT_LAST_REPORT, f"{total}|{last_day}")
        except Exception:
            logger.warning("Couldn't keep tonight's people counts", exc_info=True)
    return people_section(total, last_day, complete, before)

async def nightly_problem_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        rows = await asyncio.to_thread(
            family_link.recent_problem_reports_since, NIGHTLY_REPORT_HOURS)
    except Exception as exc:
        await notify_owner(context, f"🌙 Nightly report failed: {html.escape(str(exc))}")
        return

    feedback, note = [], None
    try:
        feedback = await asyncio.to_thread(family_link.take_undelivered_feedback, 200)
        if not feedback and await _feedback_mode() == family_link.FEEDBACK_INSTANT:
            count = await asyncio.to_thread(family_link.feedback_count_since, NIGHTLY_REPORT_HOURS)
            if count:
                note = (f"{count} feedback message(s) in the last {NIGHTLY_REPORT_HOURS}h, each "
                        f"sent to you as it came — /feedback to read them again.")
    except Exception:
        logger.warning("Couldn't collect feedback for the nightly report", exc_info=True)
    routes = await asyncio.to_thread(family_link.settings_with_prefix, ROUTES_PREFIX)
    people = await _people_report(remember=True)
    text = build_problem_report(rows, NIGHTLY_REPORT_HOURS, feedback, note, routes=routes, people=people)
    if feedback and len(text) > TELEGRAM_MAX_CHARS:

        text = build_problem_report(rows, NIGHTLY_REPORT_HOURS, routes=routes, people=people)
        await _send_feedback(context, f"💬 <b>Feedback — {len(feedback)}</b> · read only, with "
                                      f"tonight's report", feedback)
    if len(text) <= TELEGRAM_MAX_CHARS:
        await notify_owner(context, text)
        return

    await notify_owner(context, text[:TELEGRAM_MAX_CHARS])
    plain = re.sub(r"<[^>]+>", "", text)
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_document(
                chat_id=admin_id, document=BytesIO(plain.encode("utf-8")),
                filename="problems.txt")
        except Exception:
            logger.exception("Couldn't deliver the nightly report file to %s", admin_id)

FEEDBACK_READ_ONLY = "read only: it names nobody, so there is nobody to answer"

FEEDBACK_SHOWN_CHARS = 3000

FEEDBACK_LIST_ROWS = 10
FEEDBACK_SEARCH_ROWS = 50
_feedback_mode_cache = {"value": None, "read_at": 0.0}

async def _feedback_mode() -> str:
    """"instant" or "nightly", read at most once a minute -- the event pump asks on every sweep, and the answer changes when the owner taps a button here, which updates this as well."""
    now = time_module.monotonic()
    if _feedback_mode_cache["value"] is None or now - _feedback_mode_cache["read_at"] > 60:
        try:
            value = await asyncio.to_thread(db.get_setting, family_link.FEEDBACK_DELIVERY_KEY,
                                            family_link.FEEDBACK_INSTANT)
        except Exception:
            value = _feedback_mode_cache["value"] or family_link.FEEDBACK_INSTANT
        _feedback_mode_cache.update(value=value, read_at=now)
    return _feedback_mode_cache["value"]

def _feedback_block(item: dict, shown: int = FEEDBACK_SHOWN_CHARS) -> str:
    """One piece of feedback as HTML: where from, when, then the words."""
    body = item["body"]
    cut = len(body) > shown
    text = html.escape(body[:shown]) + (f"… <code>/feedback {item['id']}</code> for the rest"
                                        if cut else "")
    when = item["created_at"].strftime("%m-%d %H:%M") if item.get("created_at") else "?"
    return (f"  {html.escape(_bot_name(item['bot_id']))} · {html.escape(item.get('lang') or '?')} · "
            f"{when} UTC · #{item['id']}\n  <i>{text}</i>")

async def _send_feedback(context, header: str, items: list) -> None:
    """Items packed into as few messages as fit, never split inside one."""
    chunk = [header]
    for block in (_feedback_block(item) for item in items):
        if len("\n\n".join(chunk + [block])) > TELEGRAM_MAX_CHARS:
            await notify_owner(context, "\n\n".join(chunk))
            chunk = []
        chunk.append(block)
    if chunk:
        await notify_owner(context, "\n\n".join(chunk))

async def _deliver_feedback(context) -> None:
    """Each new piece as it arrives, in "instant" mode."""
    if await _feedback_mode() != family_link.FEEDBACK_INSTANT:
        return
    try:
        items = await asyncio.to_thread(family_link.take_undelivered_feedback, 10)
    except Exception:
        return
    for item in items:
        await notify_owner(context, "💬 <b>Feedback</b> · read only\n" + _feedback_block(item))

def _feedback_keyboard(mode: str) -> InlineKeyboardMarkup:
    tick = {mode: "✓ "}
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"{tick.get(family_link.FEEDBACK_INSTANT, '')}🔔 As it arrives",
                             callback_data="fbmode:instant"),
        InlineKeyboardButton(f"{tick.get(family_link.FEEDBACK_NIGHTLY, '')}🌙 With the 22:00 report",
                             callback_data="fbmode:nightly"),
    ]])

def _feedback_mode_line(mode: str) -> str:
    return ("🔔 Each piece reaches you as it arrives." if mode == family_link.FEEDBACK_INSTANT
            else "🌙 It reaches you with the 22:00 report.")

async def _feedback_overview(mode: str) -> str:
    items = await asyncio.to_thread(family_link.recent_feedback, FEEDBACK_LIST_ROWS)
    lines = ["💬 <b>Feedback</b>", f"<i>{FEEDBACK_READ_ONLY}.</i>", _feedback_mode_line(mode), ""]
    if not items:
        lines.append("Nobody has sent any yet.")
    else:
        lines.append(f"The latest {len(items)}, newest first:")
        lines += [_feedback_block(item, shown=280) for item in items]
    lines += ["", f"Kept {family_link.FEEDBACK_RETENTION_DAYS} days, then deleted. "
                  "<code>/feedback &lt;id&gt;</code> shows one in full."]
    return "\n".join(lines)

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/feedback -- the latest, and the switch."""
    if not await guard(update, context):
        return
    args = [a.lower() for a in context.args]
    if args and args[0] in (family_link.FEEDBACK_INSTANT, family_link.FEEDBACK_NIGHTLY):
        await asyncio.to_thread(db.set_setting, family_link.FEEDBACK_DELIVERY_KEY, args[0])
        _feedback_mode_cache.update(value=args[0], read_at=time_module.monotonic())
        await update.message.reply_text(_feedback_mode_line(args[0]), parse_mode=ParseMode.HTML)
        return
    if args and args[0].lstrip("#").isdigit():
        wanted = int(args[0].lstrip("#"))
        items = await asyncio.to_thread(family_link.recent_feedback, FEEDBACK_SEARCH_ROWS)
        item = next((i for i in items if i["id"] == wanted), None)
        if item is None:
            await update.message.reply_text(
                f"No feedback #{wanted} among the latest {FEEDBACK_SEARCH_ROWS}.")
            return
        await _send_feedback_one(context, update.effective_chat.id, item)
        return
    mode = await _feedback_mode()
    await update.message.reply_text(await _feedback_overview(mode), parse_mode=ParseMode.HTML,
                                    reply_markup=_feedback_keyboard(mode))

async def _send_feedback_one(context, chat_id: int, item: dict) -> None:
    head = (f"💬 #{item['id']} · {_bot_name(item['bot_id'])} · {item.get('lang') or '?'} · "
            f"{item['created_at']:%Y-%m-%d %H:%M} UTC\n\n")
    await send_long(context, chat_id, head + item["body"], f"feedback-{item['id']}.txt")

async def feedback_mode_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The switch under /feedback."""
    query = update.callback_query
    if not await guard(update, context):
        await query.answer()
        return
    mode = query.data.split(":", 1)[1]
    if mode not in (family_link.FEEDBACK_INSTANT, family_link.FEEDBACK_NIGHTLY):
        await query.answer()
        return
    await asyncio.to_thread(db.set_setting, family_link.FEEDBACK_DELIVERY_KEY, mode)
    _feedback_mode_cache.update(value=mode, read_at=time_module.monotonic())
    await query.answer("As it arrives" if mode == family_link.FEEDBACK_INSTANT
                       else "With the 22:00 report")
    await edit_in_place(query.message, context.bot, await _feedback_overview(mode),
                        parse_mode=ParseMode.HTML, reply_markup=_feedback_keyboard(mode))

PROBLEMS_MAX_HOURS = 168

async def nightly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/nightly [hours] -- the report the owner gets at 22:00, on demand."""
    if not await guard(update, context):
        return
    hours = int(context.args[0]) if context.args and context.args[0].isdigit() \
        else NIGHTLY_REPORT_HOURS
    hours = max(1, min(hours, PROBLEMS_MAX_HOURS))
    rows = await asyncio.to_thread(family_link.recent_problem_reports_since, hours)

    note = None
    try:
        count = await asyncio.to_thread(family_link.feedback_count_since, hours)
        if count:
            note = f"{count} feedback message(s) in the last {hours}h — /feedback to read them."
    except Exception:
        logger.debug("Couldn't count feedback for /nightly", exc_info=True)
    routes = await asyncio.to_thread(family_link.settings_with_prefix, ROUTES_PREFIX)
    people = await _people_report(remember=False)
    text = build_problem_report(rows, hours, feedback_note=note, routes=routes, people=people)
    if len(text) > TELEGRAM_MAX_CHARS:
        await send_long(context, update.effective_chat.id,
                        re.sub(r"<[^>]+>", "", text), "problems.txt")
        return
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def decode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/decode <code> -- what an error code means, from problems.py, the same registry the public bots code their messages from."""
    if not await guard(update, context):
        return
    wanted = " ".join(context.args or []).replace("🆔", "").strip().upper()
    if not wanted:
        await update.message.reply_text("Usage: /decode <code> — for example /decode CV-TIMEOUT")
        return
    matches = [wanted] if wanted in problems.PROBLEMS else [c for c in problems.PROBLEMS if wanted in c]
    if len(matches) == 1:
        await update.message.reply_text(problems.decode(matches[0]))
    elif matches:
        await update.message.reply_text("More than one code matches: " + ", ".join(matches[:40]))
    else:
        await update.message.reply_text(f"No code matches {wanted}.")

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    if context.args and context.args[0].lower() in ("on", "off"):
        value = context.args[0].lower()
        await asyncio.to_thread(db.set_setting, "alerts", value)
        await update.message.reply_text(
            f"🔔 Alerts {value}."
            + ("" if value == "on" else "\nDown/up and crash alerts are muted. /status still works.")
        )
        return
    current = await asyncio.to_thread(db.get_setting, "alerts", "on")
    await update.message.reply_text(f"🔔 Alerts are {current}. Use /alerts on or /alerts off.")

async def _alerts_on() -> bool:
    try:
        return await asyncio.to_thread(db.get_setting, "alerts", "on") == "on"
    except Exception:
        return True

async def startup_rollcall(context: ContextTypes.DEFAULT_TYPE) -> None:
    """One message, once, a few seconds after ManagerBot starts: who is up."""
    if not await _alerts_on():
        return
    try:
        beats = {row["bot_id"]: row for row in await asyncio.to_thread(db.all_heartbeats)}
    except Exception as exc:
        logger.warning("Startup roll-call couldn't reach the database: %s", exc)
        await notify_owner(
            context,
            "\U0001f44b <b>ManagerBot is up</b>, but it cannot reach the family "
            "database, so it has no idea who else is.\n"
            f"<code>{html.escape(str(exc))}</code>",
        )
        return

    now = datetime.now(timezone.utc)
    lines, up_count = [], 0
    for bot in CHILDREN:
        beat = beats.get(bot["id"])
        if beat is None:
            lines.append(f"\u2754 <b>{bot['name']}</b> -- never seen. Has it ever been started?")
            continue
        if beat["seconds_ago"] > DOWN_AFTER_SECONDS:
            lines.append(
                f"\u274c <b>{bot['name']}</b> -- not up. Last heartbeat "
                f"{format_delta(beat['seconds_ago'])} ago."
            )
            continue

        up_count += 1
        uptime = (now - beat["started_at"]).total_seconds()
        host = html.escape(beat["host"] or "?")
        if uptime <= ROLLCALL_FRESH_SECONDS:
            lines.append(
                f"\U0001f7e2 <b>{bot['name']}</b> -- just started on {host} "
                f"\u00b7 v{beat['version']}"
            )
        else:
            lines.append(
                f"\u2705 <b>{bot['name']}</b> -- already up ({format_delta(uptime)}) "
                f"on {host} \u00b7 v{beat['version']}"
            )

    header = (
        f"\U0001f44b <b>ManagerBot is up</b> on {html.escape(family_link.HOSTNAME)} -- "
        f"{up_count}/{len(CHILDREN)} of the family with it"
    )
    await notify_owner(context, "\n".join([header, "", *lines]))

    for bot in CHILDREN:
        beat = beats.get(bot["id"])
        is_up = beat is not None and beat["seconds_ago"] <= DOWN_AFTER_SECONDS
        try:
            await asyncio.to_thread(db.set_known_state, bot["id"], is_up)
        except Exception:
            logger.debug("Couldn't seed bot_state for %s", bot["id"], exc_info=True)

_db_failures = 0
_db_alerted = False

async def _is_redeploying(bot_id: str) -> bool:
    """True while a bot's own goodbye note is still fresh."""
    key = lifecycle.RESTART_NOTE_PREFIX + bot_id
    try:
        raw = await asyncio.to_thread(db.get_setting, key)
        if not raw:
            return False
        stamped = datetime.fromisoformat(raw)
    except Exception:
        return False
    age = (datetime.now(timezone.utc) - stamped).total_seconds()
    return 0 <= age <= REDEPLOY_GRACE_SECONDS

async def _stopped_on_purpose(bot_id: str) -> bool:
    """True when the bot's last words were a soft shutdown (its note is cleared when it starts again)."""
    try:
        return bool(await asyncio.to_thread(db.get_setting, lifecycle.STOPPED_NOTE_PREFIX + bot_id))
    except Exception:
        return False

async def _clear_redeploy_note(bot_id: str) -> None:
    try:
        await asyncio.to_thread(db.set_setting, lifecycle.RESTART_NOTE_PREFIX + bot_id, "")
    except Exception:
        logger.debug("Could not clear the redeploy note for %s", bot_id, exc_info=True)

async def watchdog(context: ContextTypes.DEFAULT_TYPE) -> None:
    global _db_failures, _db_alerted
    try:
        await asyncio.to_thread(db.expire_stale_commands, COMMAND_TIMEOUT_SECONDS)
        beats = {row["bot_id"]: row for row in await asyncio.to_thread(db.all_heartbeats)}
        known = await asyncio.to_thread(db.get_known_state)
    except Exception as exc:
        _db_failures += 1
        logger.warning("Watchdog couldn't reach the database (%s in a row): %s", _db_failures, exc)
        if _db_failures >= 3 and not _db_alerted:
            _db_alerted = True
            await notify_owner(
                context,
                "🚨 <b>ManagerBot cannot reach the family database.</b>\n"
                f"<code>{html.escape(str(exc))}</code>\n\n"
                "Until it comes back I cannot see any bot's state, so treat "
                "silence from me as unknown, not as healthy.",
            )
        return

    if _db_alerted:
        _db_alerted = False
        await notify_owner(context, "✅ Family database is reachable again.")
    _db_failures = 0

    if not await _alerts_on():
        return

    for bot in CHILDREN:
        beat = beats.get(bot["id"])
        is_up = beat is not None and beat["seconds_ago"] <= DOWN_AFTER_SECONDS
        was_up = known.get(bot["id"])

        if was_up is None:

            await asyncio.to_thread(db.set_known_state, bot["id"], is_up)
            if not is_up and beat is not None:
                await notify_owner(context, f"❌ <b>{bot['name']}</b> is down (first check since I started).")
            continue

        if is_up == was_up:
            continue

        if is_up:
            await asyncio.to_thread(db.set_known_state, bot["id"], True)
            await _clear_redeploy_note(bot["id"])
            uptime = format_delta((datetime.now(timezone.utc) - beat["started_at"]).total_seconds())
            await notify_owner(
                context,
                f"✅ <b>{bot['name']}</b> is back up (started {uptime} ago, "
                f"on {html.escape(beat['host'] or '?')})."
            )
        elif await _stopped_on_purpose(bot["id"]):
            await asyncio.to_thread(db.set_known_state, bot["id"], False)
            await notify_owner(context, f"⏹ <b>{bot['name']}</b> stopped as asked (soft shutdown). "
                                        "It stays down until it is deployed again.")
        elif await _is_redeploying(bot["id"]):

            logger.info("%s is stale but was shut down on purpose -- redeploying.", bot["id"])
            continue
        else:
            await asyncio.to_thread(db.set_known_state, bot["id"], False)
            last = format_delta(beat["seconds_ago"]) if beat else "?"
            await notify_owner(
                context,
                f"❌ <b>{bot['name']}</b> has gone down — no heartbeat for {last}.\n"
                f"Its last host was {html.escape((beat or {}).get('host') or '?')}."
            )

async def event_pump(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forwards what the bots themselves flagged."""
    if not await _alerts_on():

        return
    try:
        events = await asyncio.to_thread(db.take_unnotified_events, 20)
    except Exception:
        return

    if events:

        family_link.mark_bus_active()

    icons = {"warning": "⚠️", "error": "🔥", "critical": "🚨", "info": "ℹ️"}
    for event in events:
        if event["level"] not in ALERT_LEVELS and event["kind"] != "payment":
            continue
        icon = icons.get(event["level"], "•")
        text = (
            f"{icon} <b>{html.escape(event['bot_id'])}</b> — {html.escape(event['kind'])}\n"
            f"{html.escape(event['message'])}"
        )
        if event["details"]:
            tail = event["details"].strip().splitlines()[-6:]
            text += "\n\n<pre>" + html.escape("\n".join(tail)) + "</pre>"
        await notify_owner(context, text[:4000])

    await _deliver_feedback(context)

_last_pumped = {"result": 0.0, "event": 0.0}

_pump_tasks: dict[str, "asyncio.Task"] = {}
_pump_started: dict[str, float] = {}
_pump_stall_logged: set[str] = set()
PUMP_STALL_WARN_SECONDS = int(os.environ.get("MBOT_PUMP_STALL_WARN_SECONDS", "60"))

SWEEP_WINDOW_SECONDS = 900
_sweep_recent: dict[str, "deque[tuple[float, float]]"] = {}
_sweep_slowest: dict[str, float] = {}

def _note_sweep(key: str, started: float, task=None) -> None:
    """Done callback of a sweep task: it ended, however it ended (finished, raised or was cancelled), so it is counted."""
    try:
        now = time_module.monotonic()
        seconds = max(0.0, now - started)
        recent = _sweep_recent.setdefault(key, deque())
        recent.append((now, seconds))
        while recent and now - recent[0][0] > SWEEP_WINDOW_SECONDS:
            recent.popleft()
        _sweep_slowest[key] = max(_sweep_slowest.get(key, 0.0), seconds)
    except Exception as exc:
        logger.debug("Could not note how long the %s sweep took (%s).", key, type(exc).__name__)

def _sweep_line(key: str = "event") -> str:
    """The /status line about how long the sweeps take."""
    now = time_module.monotonic()
    name = key.capitalize()
    if key not in _sweep_slowest:
        return f"⏱ {name} sweep: none finished yet since start"
    since_start = f"{_sweep_slowest[key]:.2f} s"
    window = f"{SWEEP_WINDOW_SECONDS // 60} min"
    recent = [seconds for finished, seconds in _sweep_recent.get(key, ())
              if now - finished <= SWEEP_WINDOW_SECONDS]
    if not recent:
        return f"⏱ {name} sweep: none in the last {window} · slowest since start {since_start}"
    return (f"⏱ {name} sweep: slowest {max(recent):.2f} s in the last {window} "
            f"({len(recent)} sweep{'' if len(recent) == 1 else 's'}) · {since_start} since start")

async def _pump_if_due(context, key: str, pump, fast: int, idle: int) -> None:
    now = time_module.monotonic()
    task = _pump_tasks.get(key)
    if task is not None and not task.done():

        if (now - _pump_started[key] > PUMP_STALL_WARN_SECONDS
                and key not in _pump_stall_logged):
            _pump_stall_logged.add(key)
            logger.warning("The %s sweep has been running for %d s.", key, now - _pump_started[key])
        return
    _pump_stall_logged.discard(key)
    due = fast if family_link.bus_is_active() else idle
    if now - _last_pumped[key] < due:
        return
    _last_pumped[key] = now
    _pump_started[key] = now

    _pump_tasks[key] = context.application.create_task(pump(context), name=f"{key}-sweep")
    _pump_tasks[key].add_done_callback(functools.partial(_note_sweep, key, now))

async def _result_backstop(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _pump_if_due(context, "result", result_pump,
                       RESULT_POLL_FAST_SECONDS, RESULT_POLL_SECONDS)

async def _event_backstop(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _pump_if_due(context, "event", event_pump,
                       EVENT_POLL_FAST_SECONDS, EVENT_POLL_SECONDS)

async def result_pump(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delivers whatever the child bots wrote back, and gives up on commands nobody claimed."""
    try:
        results = await asyncio.to_thread(db.take_finished_commands, 5)
    except Exception:
        return

    if results:

        family_link.mark_bus_active()

    for result in results:

        trace = _PING_TRACES.pop(result["id"], None)
        if trace is not None:
            await _deliver_ping(context, trace, result)
            continue

        group = _FANOUTS.pop(result["id"], None)
        if group is not None:
            await _deliver_fanout(context, group, result)
            continue

        chat_id = result["reply_chat_id"]
        if not chat_id:
            continue

        target = resolve_bot(result["target_bot"])
        head = f"{target['name'] if target else result['target_bot']} · {result['command']}"
        if result["status"] == "timeout":
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏳ {head} (queued as #{result['id']}) — no answer in {COMMAND_TIMEOUT_SECONDS}s. That bot looks down.",
            )
            continue

        mark = "✅" if result["ok"] else "⚠️"
        body = result["output"] or "(no output)"

        if not result["ok"] and body.startswith("Unknown command"):
            beat = await asyncio.to_thread(db.heartbeat_of, result["target_bot"])
            theirs = (beat or {}).get("version")
            if theirs and theirs != family_link.VERSION:
                body += (f"\n\nThat bot is on {theirs}; ManagerBot is on "
                         f"{family_link.VERSION}. Most likely it has not been "
                         f"published since the command was written.")
        if result["file_bytes"]:
            await context.bot.send_document(
                chat_id=chat_id,
                document=BytesIO(bytes(result["file_bytes"])),
                filename=result["file_name"] or f"{result['target_bot']}.bin",
                caption=f"{mark} {head} — {body}"[:1000],
            )
        else:
            await send_long(context, chat_id, f"{mark} {head}\n\n{body}", f"{result['target_bot']}.txt")

async def daily_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        board = await asyncio.to_thread(_build_board, _sweep_line())
    except Exception as exc:
        await notify_owner(context, f"🚨 Daily check failed: {html.escape(str(exc))}")
        return
    await notify_owner(context, "🌅 <b>Daily check</b>\n\n" + board)

HELP = f"""👪 <b>ManagerBot</b> — the family's manager.

<b>Is everything alright</b>
/status — every bot: up/down, uptime, host, errors, users (with Refresh /
    Alerts / Ping buttons under it)
/nightly [hours] — the 22:00 nightly report, on demand: unique users,
    then what the bots showed people, laid out: urgent listed, faults
    grouped, the rest by what kind of thing it was
/reports [n] [mine] — the latest problems, newest first, each with its
    incident code; mine: only those somebody attached their details to
/report &lt;incident&gt; — one problem in full, with whoever volunteered to be named
/errors — what each bot has hit since it started (live; a redeploy clears it)
/events [bot] [n] — recent crashes, startups, payments
/ping [bot] — no bot named pings all of them, fastest first
/logs &lt;bot&gt; [n] [bot|problems] — tail a log: errors by default, "bot" or
    "problems" for the other two
/usage [bot] — memory, peaks, and what they cost
/idle [bot] — how quiet each bot is, and whether sleeping would pay
/buttons [days] — how often each button is tapped, per bot (counts only)
/providers — which of DownloaderBot's download routes work, which rest
/probe — test every download route, from DownloaderBot's container
/alerts on|off — mute or unmute unprompted alerts

<b>Doing something to a bot</b>
/run &lt;bot&gt; &lt;command&gt; [args] — the general form; run it bare for the list,
    which now includes the commands each bot registers for itself
/shutdown &lt;bot&gt; — asks: that bot alone, or the whole service it runs in;
    stops only when nobody is using it (refused, with the reasons, while
    anybody is). A stopped service stays down until a deploy or a Redeploy
/restart &lt;bot&gt; [force] — asks, then restarts its whole service once nobody is
    using it; force restarts at once whatever is running (for a stuck service)
/pause [bot|all] [minutes] — stop them taking work an update would lose;
    whoever asks is told to come back, and written down
/warn [bot|all] — tell whoever is mid-something that it is about to reset
/resume [bot|all] — reopen, and tell everyone who was turned away
    (yours to say, so one update can be as many deploys as it needs)

<b>Talking to people</b>
/say &lt;bot&gt; &lt;user_id&gt; &lt;text&gt; — DM someone <i>as</i> that bot
/broadcast &lt;bot|all&gt; [--active] &lt;text&gt; — one message to everyone, <i>as</i> that bot
/whois &lt;bot&gt; &lt;user_id&gt; — look someone up through that bot
/users [hours] — active users per bot, default 24h
/feedback [instant|nightly] — what people sent with /feedback (read only: it
    names nobody, so there is nobody to answer), and whether each one reaches
    you as it arrives or with the 22:00 report

<b>Money</b>
/balance [id] [±n|=n] — see or change a credit balance
/addcredit &lt;id&gt; &lt;amount&gt; — put ⚡ into an account
/gift &lt;bot|all&gt; &lt;key&gt; &lt;credits&gt; &lt;last day&gt; — bonus ⚡ for everyone,
    once each: each bot counts first, and nothing is given until you say so
/promo [stop] — the {family_link.PROMO_CREDITS} ⚡ gift: start it (once), see how it
    goes, end it early
/donations — paid donations per bot
/stars — ConvertBot's Stars: paid, refunded, recent

<b>The database</b>
/backup — the whole database, lossless and restorable, sent here and pinned
/dbdump &lt;bot&gt; — that bot's own tables as CSVs
/sql &lt;SELECT …&gt; — read-only query on the shared database
/decode &lt;code&gt; — what an error code means

<b>Still works, not in the menu</b>
Renamed in 1.7.0, with the old names kept so a habit does not break:
/problems → /nightly (its name from 1.7.0 to 2.1.2) · /finishupdates → /resume ·
/errorlog, /botlog and /problemlog → /logs · /me → /status
/crashtest &lt;bot&gt; makes a bot raise on purpose, to check the alert arrives
    (no bot named crashes ManagerBot itself)

Bots: <code>{{bots}}</code>
Any unambiguous prefix works — <code>/logs stick</code> is fine."""

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

def _help_page_pause() -> str:
    minutes = lifecycle.DEFAULT_MAINTENANCE_MINUTES
    timeout = COMMAND_TIMEOUT_SECONDS
    return f"""⏸ Updating the bots: /pause, /warn, /resume

In this order:
1. /pause — the bots stop starting new long work, the kind an update would cut off. Whoever asks for some is told to come back in about {minutes} minutes, and written down. Work already running carries on.
2. /warn — only the people in the middle of something right now are told it is about to be reset. It changes nothing, and you can send it again.
3. Deploy, as many times as it takes. The pause survives restarts and redeploys, and it never ends by itself: the minutes are only what people are told.
4. /resume — the bots take work again, and everyone who was turned away is told they can try again (each person once).

Forms:
/pause — all four bots, people told {minutes} minutes
/pause 30 — all four, 30 minutes
/pause convert — one bot (any unambiguous start of its name)
/pause convert 30 — one bot, 30 minutes
/warn [bot|all] and /resume [bot|all] — the same choice of bots
/finishupdates is the old name of /resume.

Each bot answers for itself: how many people it warned, or that it is open again and how many it told. A bot that is down gets nothing: after {timeout} seconds without an answer you are told it looks down; send the command again once it is up. ManagerBot itself is never paused.

Example: /pause 20, then /warn, deploy, check /status, then /resume.
"""

def _help_page_gift() -> str:
    key_rule = family_link.GIFT_KEY_RULE
    max_credit = family_link.GIFT_MAX_CREDIT
    days = family_link.GIFT_MAX_DAYS
    return f"""🎁 /gift — bonus ⚡ for everyone a bot knows, once each

/gift <bot|all> <key> <credits> <last day>
• bot|all — one bot (any unambiguous start of its name) or all four. Somebody who uses two bots still gets it once.
• key — names this gift. {key_rule} A key is given at most once per person, across the whole family, for ever: sending the same /gift twice is safe, and a new gift needs a new key.
• credits — a whole number from 1 to {max_credit}.
• last day — YYYY-MM-DD, from tomorrow up to {days} days ahead. The credit is bonus: spent before ordinary credit, and whatever is left disappears at the end of that day, UTC.

What happens:
1. Each bot first only counts, and says so in a message of its own: how many people it knows, how many would get it, how much ⚡ in all, and the notice they will read. Nothing is given.
2. A card names the amount, the last day and the key, with "Give it" and "Cancel". Nothing is given until you press Give it, and that cannot be taken back. Only the newest /gift can be given; an older card's buttons give nothing.
3. Each bot goes through its people and reports how many it gave it to. Each person is told, in their own language. If a bot fails partway, send the same /gift again: those who already have it are skipped.

/run <bot> gift … --go gives at once, with no count and no card.

Example: /gift all welcome-200 200 2027-01-15
"""

def _help_page_promo() -> str:
    amount = family_link.PROMO_CREDITS
    users = family_link.PROMO_USERS
    claim_days = family_link.PROMO_CLAIM_DAYS
    spend_days = family_link.PROMO_SPEND_DAYS
    minutes = PROMO_COUNT_SECONDS // 60
    return f"""🎉 /promo — the {amount} ⚡ gift for everyone who writes to ConvertBot or DownloaderBot

/promo
/promo stop

The count and the notice:
• Every {minutes} minutes ManagerBot counts the unique people across all the bots, each person once however many bots they use. The first time the count reaches {users} it messages you, once. /users shows the count too.

What /promo shows depends on where the gift stands:
• Not started, under {users} people: the count so far. Nothing to do; you will be told when it is reached.
• Not started, {users} reached: a card with the ad people will see and two buttons, Start the gift and Cancel. Starting can be done once, ever, and it cannot be undone. Only the newest card works.
• Started: when it started, when claiming closes, how many people claimed it, and how many people AnonBot showed the ad to.

Once started:
• Claiming stays open for {claim_days} days: until midnight UTC at the end of the {claim_days}th day after the start.
• The first message a person sends to ConvertBot or DownloaderBot in that time gives them {amount} ⚡ of bonus credit, once in all, not once per bot. They are told in their own language.
• Each gift can be spent for {spend_days} days from the day it was claimed. What is left then disappears at the end of that day, UTC.
• AnonBot shows the ad once to each person who writes to it and does not have the gift yet: not on the first /start of an inbox link, not in the middle of a question, and not again after a restart.

/promo stop ends the claiming at once. Credit already given stays and can be spent until it runs out. Before the start, or after the end, there is nothing to stop.

/gift is the separate, general tool for any gift under its own key. /promo is this one gift only.

Example: /promo stop
"""

def _help_page_broadcast() -> str:
    active_days = family_link.BROADCAST_ACTIVE_DAYS
    per_second = f"{family_link.BROADCAST_PER_SECOND:g}"
    return f"""📢 /broadcast — one message to everyone a bot knows, as that bot

/broadcast <bot|all> <text>
/broadcast <bot|all> --active <text>
• The first word must be a bot (any unambiguous start of its name) or all: "/broadcast hello there" is refused, because "hello" is not a bot.
• --active, right after the bot: only people who used that bot in the last {active_days} days. A bot that cannot tell who is active sends nothing, and says so.
• The text goes as plain text, with no formatting. Line breaks and double spaces are not kept: it arrives as one paragraph.
• First you get a card with the text and "Send it" / "Cancel". Nothing is sent before Send it, and nothing can be taken back after. A newer /broadcast replaces the one waiting.
• Each bot sends at most {per_second} messages a second, skips people who blocked it, and reports how many it reached.

/run <bot> broadcast … sends at once, with no card.

Example: /broadcast all --active The bots stop for an update at 22:00 UTC, for about 10 minutes.
"""

def _help_page_balance() -> str:
    top = BALANCE_OVERVIEW_ROWS
    rows = BALANCE_HISTORY_ROWS
    return f"""⚡ /balance — see or change one person's credit

/balance — the family's overview, with the {top} largest balances.
/balance <id> — that person's balance, what they paid and spent, their bonus and when it runs out, and their last {rows} movements.
/balance <id> +100 — add 100 ⚡
/balance <id> -100 — take 100 ⚡ away (the balance may go below zero)
/balance <id> =0 — set it to exactly 0
• id is the person's numeric Telegram id. Not sure who it is? /whois <bot> <id>.
• A bare number ("/balance 123 500") is refused on purpose: say +, - or =.
• A change happens at once, with no confirmation. The person's /balance shows it as "adjustment", and it is in /events.
• It is one wallet for the whole family: the same balance in every bot.
• /addcredit is the short way to add credit that never expires; /gift is for everyone at once.

Example: /balance 123456789 +50
"""

def _help_page_addcredit() -> str:
    return """➕ /addcredit — put ⚡ into one account

/addcredit <id> <amount>
• id: the person's numeric Telegram id. amount: a whole number above 0.
• It is ordinary credit: it never expires. The person's /balance shows it as "grant".
• It happens at once, with no confirmation, and nothing checks that the id is somebody a bot knows: check with /whois <bot> <id> first.
• To take credit away or set an exact amount: /balance <id> -n or =n.

Example: /addcredit 123456789 100
"""

def _help_page_run() -> str:
    timeout = COMMAND_TIMEOUT_SECONDS
    return f"""🛠 /run — any command, inside one bot

/run <bot> <command> [args]
• /run on its own lists the bots and every command, with the ones only one bot has.
• bot: any unambiguous start of its name. ManagerBot itself is refused; use its own commands.
• The bot must know the command: one its version doesn't have is refused before anything is sent.
• You see "queued as #n" at once; the bot's answer comes as a second message. No answer in {timeout} seconds means the bot looks down.
• No confirmation: /run <bot> broadcast … sends at once, and /run <bot> gift … --go gives at once. /broadcast and /gift are the ones that ask first.
• Shortcuts for the usual ones: /logs, /say, /stars, /probe, /providers.

Example: /run convert status
"""

def _help_page_logs() -> str:
    default = family_link.LOG_TAIL_DEFAULT
    most = family_link.LOG_TAIL_MAX
    return f"""📜 /logs — the end of one bot's log

/logs <bot> [lines] [bot|problems]
• bot: any unambiguous start of its name. One bot at a time.
• lines: how many from the end, {default} if not said, at most {most}. It must come straight after the bot's name.
• The last word picks the log: nothing (or anything else) — errors.log, its errors; "bot" or "all" — bot.log, everything it logged; "problems" — problems.log, what it showed people. ("all" means all of bot.log, not all bots.)
• If the bot's host keeps no log files, you get its in-memory copy since it started, and it says so.
• /errorlog, /botlog and /problemlog ask which bot with buttons.

Example: /logs convert 100 problems
"""

REPORTS_LINE = ("/reports [n] lists the latest problems, newest first, each with its "
                "incident code; /reports mine only the ones somebody attached their "
                "details to.")

def _help_page_nightly() -> str:
    default = NIGHTLY_REPORT_HOURS
    most = PROBLEMS_MAX_HOURS

    daily = (f"The same report arrives by itself every day at {NIGHTLY_REPORT_AT_UTC} UTC."
             if NIGHTLY_REPORT_AT_UTC else "The daily report is off (MBOT_NIGHTLY_UTC is blank).")
    reports_line = REPORTS_LINE
    return f"""🌙 /nightly — the 22:00 nightly report, on demand

/nightly [hours]
• hours: how far back, {default} if not said, from 1 to {most}.
• First the unique users: all bots, all time, and the last 24 hours, each with its change since the last scheduled report.
• Then what the bots showed people in that time, laid out: urgent ones listed, faults grouped, the rest by what kind of thing it was. A note says how many /feedback messages came in.
• Too long for one message: the start comes here, and the whole of it as problems.txt.
• {daily} /problems is the same command.
• One problem in full: /report <incident>. {reports_line}

Example: /nightly 72
"""

def _help_page_events() -> str:
    default = EVENTS_DEFAULT
    most = EVENTS_MAX
    return f"""🗒 /events — crashes, startups and payments, as they happened

/events [bot] [n]
• n: how many, {default} if not said, at most {most}. bot: only that bot's events (any unambiguous start of its name). Either order.
• A word that is not a bot is ignored, so a typo shows every bot's events: check that the heading says "from" the bot you meant.
• Each line: date and time, the bot, what happened, with an icon for how serious it was.
• Too long for one message: the start comes here, and the whole of it as events.txt.

Example: /events convert 30
"""

def _help_page_feedback() -> str:
    latest = FEEDBACK_LIST_ROWS
    search = FEEDBACK_SEARCH_ROWS
    days = family_link.FEEDBACK_RETENTION_DAYS
    return f"""💬 /feedback — what people sent with /feedback

/feedback — the latest {latest}, newest first, with two buttons: 🔔 As it arrives / 🌙 With the 22:00 report (✓ on the one in force).
/feedback instant — each one reaches you the moment it is sent.
/feedback nightly — they wait for the 22:00 report.
/feedback <n> or #<n> — one in full (among the latest {search}).
• Read only. A message carries the bot it came from and the language, never who sent it, so there is nobody to answer.
• Each is kept {days} days, then deleted.

Example: /feedback nightly
"""

def _help_page_sql() -> str:
    timeout = db.SQL_TIMEOUT_SECONDS
    rows = db.SQL_MAX_ROWS
    return f"""🔎 /sql — a read-only query on the shared database

/sql SELECT …
• It must start with SELECT, WITH, TABLE, EXPLAIN or SHOW, and be one statement.
• The database itself keeps it read-only, and stops it after {timeout} seconds.
• At most {rows} rows come back, as text with | between the columns. Longer than a message: the start comes here, and all of it as query.txt.
• Every bot's tables are there, each bot in its own schema.
• An error comes back as ⚠️ and the database's own message.

Example: /sql SELECT count(*) FROM sticker_bot.packs
"""

def _help_page_say() -> str:
    return """✉️ /say — a message to one person, as one of the bots

/say <bot> <user_id> <text>
• One bot (any unambiguous start of its name), never all, and the person's numeric Telegram id.
• Plain text, no formatting; line breaks and double spaces are not kept.
• It goes at once: no confirmation, and it cannot be taken back. It arrives from that bot, as if the bot wrote it.
• "Sent." means Telegram took it. If the person blocked the bot or never started it, you get Telegram's refusal instead.

Example: /say convert 123456789 The fix is live — try your file again.
"""

HELP_PAGES = {
    "pause": _help_page_pause,
    "gift": _help_page_gift,
    "promo": _help_page_promo,
    "broadcast": _help_page_broadcast,
    "balance": _help_page_balance,
    "addcredit": _help_page_addcredit,
    "run": _help_page_run,
    "logs": _help_page_logs,
    "nightly": _help_page_nightly,
    "events": _help_page_events,
    "feedback": _help_page_feedback,
    "sql": _help_page_sql,
    "say": _help_page_say,
}
HELP_ALIASES = {"warn": "pause", "resume": "pause", "finishupdates": "pause", "problems": "nightly"}

def help_page_name(context) -> "str | None":
    """The page `/help <word>` asks for, or None."""
    if not context.args:
        return None
    word = context.args[0].lower().lstrip("/").split("@", 1)[0].removeprefix("help_")
    word = HELP_ALIASES.get(word, word)
    return word if word in HELP_PAGES else None

def help_page_text(name: str) -> str:
    """One page, then the way back to /help."""
    return HELP_PAGES[name]().rstrip() + "\n\nEverything: /help"

def _help_keyboard() -> InlineKeyboardMarkup:
    """One button per page, two to a row, under /help and /start -- the way /ping has one per bot."""
    buttons = [InlineKeyboardButton("/" + name, callback_data=f"helpdet:{name}") for name in HELP_PAGES]
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])

async def help_page_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of those buttons: the page arrives as a new message, so the help above it stays to be tapped again."""
    if not await guard(update, context):
        return
    query = update.callback_query
    name = query.data.split(":", 1)[1]
    if name not in HELP_PAGES:

        await query.answer("That help page no longer exists. Send /help.", show_alert=True)
        return
    await query.answer()
    await context.bot.send_message(chat_id=query.message.chat_id, text=help_page_text(name),
                                   link_preview_options=NO_PREVIEW)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    page = help_page_name(context)
    if page:
        await update.message.reply_text(help_page_text(page), link_preview_options=NO_PREVIEW)
        return
    await update.message.reply_text(
        HELP.format(bots=bot_list_hint()), parse_mode=ParseMode.HTML, reply_markup=_help_keyboard())

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    await update.message.reply_text("Not a command I have. /help lists them.")

async def plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update, context):
        return
    await update.message.reply_text("I only take commands here. /help lists them.")

async def crashtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proves the crash path, the errors.log and the family alert all really fire -- for ManagerBot itself, or for any child bot by name."""
    if not await guard(update, context):
        return
    if context.args:
        bot = resolve_bot(context.args[0])
        if not bot:
            await update.message.reply_text(
                f"No such bot: {context.args[0]}. Known: {bot_list_hint()}")
            return
        await _dispatch(update, context, bot, "crashtest", [])
        return
    raise RuntimeError("Manual /crashtest trigger -- ManagerBot's error tracking works.")

def _targets(token: str | None) -> list[dict] | None:
    """The bots a command applies to."""
    if not token or token.lower() == "all":
        return list(CHILDREN)
    bot = resolve_bot(token)
    if not bot or bot["id"] == BOT_NAME:
        return None
    return [bot]

async def _fan_out(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   targets: list[dict], command: str, args: str, headline: str) -> None:
    """Queue one family command to several bots and say so once."""
    for bot in targets:
        await asyncio.to_thread(
            db.queue_command, bot["id"], command, args,
            update.effective_user.id, update.effective_chat.id,
        )
    names = ", ".join(b["name"] for b in targets)
    await update.message.reply_text(f"{headline}\n→ {names}")

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pause [bot|all] [minutes] — stop taking new long work, and say why."""
    if not await guard(update, context):
        return
    args = list(context.args)
    minutes = None
    if args and args[-1].isdigit():
        minutes = args.pop()
    targets = _targets(args[0] if args else None)
    if targets is None:
        await update.message.reply_text(
            f"Usage: /pause [bot|all] [minutes]. Known: {bot_list_hint()}"
        )
        return
    promised = minutes or str(lifecycle.DEFAULT_MAINTENANCE_MINUTES)
    await _fan_out(
        update, context, targets, "pause", minutes or "",
        f"⏸ Paused — telling users to come back in about {promised} minute(s).\n"
        f"They stay paused until /resume, however many deploys that takes.",
    )

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/warn [bot|all] — tell whoever is mid-something that it will be reset."""
    if not await guard(update, context):
        return
    targets = _targets(context.args[0] if context.args else None)
    if targets is None:
        await update.message.reply_text(f"Usage: /warn [bot|all]. Known: {bot_list_hint()}")
        return
    await _fan_out(
        update, context, targets, "warnbusy", "",
        "📣 Warning everyone with work in flight that it is about to be reset.",
    )

async def finish_updates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/finishupdates [bot|all] — reopen, and go back to everyone turned away."""
    if not await guard(update, context):
        return
    targets = _targets(context.args[0] if context.args else None)
    if targets is None:
        await update.message.reply_text(
            f"Usage: /resume [bot|all]. Known: {bot_list_hint()}"
        )
        return
    await _fan_out(
        update, context, targets, "resume", "",
        "✅ Reopening — everyone who was turned away is being told they can try again.",
    )

BROADCAST_PENDING = "broadcast_pending"
BROADCAST_PREVIEW = 3000

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast <bot|all> <text> — one message to everyone, as that bot."""
    if not await guard(update, context):
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            f"Usage: /broadcast &lt;bot|all&gt; [--active] &lt;text&gt;\nKnown: {bot_list_hint()}",
            parse_mode=ParseMode.HTML,
        )
        return
    targets = _targets(context.args[0])
    if targets is None:
        await update.message.reply_text(
            f"No such bot: {context.args[0]}. Known: {bot_list_hint()}"
        )
        return
    text = " ".join(context.args[1:]).strip()

    aimed = text.split(" ", 1)[0] == "--active"
    shown = text.partition(" ")[2].strip() if aimed else text
    if not shown:
        await update.message.reply_text("Nothing to say — give it some text.")
        return

    context.user_data[BROADCAST_PENDING] = {
        "bots": [b["id"] for b in targets],
        "text": text,
    }
    names = ", ".join(b["name"] for b in targets)
    audience = (f"active in the last {family_link.BROADCAST_ACTIVE_DAYS} day(s)"
                if aimed else "they know")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Send it", callback_data="upd:send"),
        InlineKeyboardButton("Cancel", callback_data="upd:cancel"),
    ]])
    await update.message.reply_text(
        f"📢 <b>Send as {html.escape(names)}, to everyone {audience}?</b>\n\n"
        f"<pre>{html.escape(shown[:BROADCAST_PREVIEW])}</pre>\n"
        f"This cannot be taken back.",
        parse_mode=ParseMode.HTML, reply_markup=kb,
    )

async def broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await guard(update, context):
        return
    pending = context.user_data.pop(BROADCAST_PENDING, None)
    if query.data == "upd:cancel" or not pending:
        await query.answer()
        await edit_in_place(
            query.message, context.bot,
            "Cancelled — nothing was sent." if pending else
            "That broadcast is no longer waiting. Send /broadcast again.",
        )
        return

    await query.answer()
    sent_to = []
    for bot_id in pending["bots"]:
        await asyncio.to_thread(
            db.queue_command, bot_id, "broadcast", pending["text"],
            update.effective_user.id, update.effective_chat.id,
        )
        sent_to.append(bot_id)
    await edit_in_place(
        query.message, context.bot,
        f"📢 Queued to {', '.join(sent_to)}. Each one reports back when it has "
        f"finished going through its list.",
    )

GIFT_PENDING = "gift_pending"
GIFT_DONE = "gift_done"

async def gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gift <bot|all> <key> <credits> <last day YYYY-MM-DD>"""
    if not await guard(update, context):
        return
    if len(context.args) != 4:
        await update.message.reply_text(
            "Usage: /gift &lt;bot|all&gt; &lt;key&gt; &lt;credits&gt; &lt;last day YYYY-MM-DD&gt;\n"
            "e.g. <code>/gift all gift-100-users 100 2027-01-15</code>\n"
            f"Known: {bot_list_hint()}",
            parse_mode=ParseMode.HTML,
        )
        return
    targets = _targets(context.args[0])
    if targets is None:
        await update.message.reply_text(
            f"No such bot: {context.args[0]}. Known: {bot_list_hint()}"
        )
        return
    parsed = family_link._gift_args(context.args[1:])
    if isinstance(parsed, str):
        await update.message.reply_text(parsed)
        return
    key, amount, _expires, raw_day = parsed
    args = f"{key} {amount} {raw_day}"
    for bot in targets:
        await asyncio.to_thread(
            db.queue_command, bot["id"], "gift", args,
            update.effective_user.id, update.effective_chat.id,
        )
    nonce = secrets.token_hex(4)
    context.user_data[GIFT_PENDING] = {"bots": [b["id"] for b in targets], "args": args,
                                       "nonce": nonce}
    names = ", ".join(b["name"] for b in targets)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Give it", callback_data=f"gift:go:{nonce}"),
        InlineKeyboardButton("Cancel", callback_data=f"gift:cancel:{nonce}"),
    ]])
    await update.message.reply_text(
        f"🎁 <b>{amount} ⚡ of bonus credit, good until {html.escape(raw_day)}</b>, "
        f"to everyone {html.escape(names)} know(s), once per person "
        f"(key <code>{html.escape(key)}</code>).\n\n"
        f"Each bot is counting now and will report how many people it would give "
        f"it to, with the notice they would read. Nothing is given until you press "
        f"<b>Give it</b>, and that cannot be taken back.",
        parse_mode=ParseMode.HTML, reply_markup=kb,
    )

async def gift_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await guard(update, context):
        return
    await query.answer()

    action, _, nonce = query.data.removeprefix("gift:").partition(":")
    if nonce and nonce == context.user_data.get(GIFT_DONE):

        return
    pending = context.user_data.get(GIFT_PENDING)
    if not pending:
        await edit_in_place(query.message, context.bot,
                            "That gift is no longer waiting. Send /gift again.")
        return
    if not nonce or nonce != pending.get("nonce"):
        await edit_in_place(
            query.message, context.bot,
            "That card is not the one waiting (a newer /gift replaced it, or the "
            "card is from before an update). Nothing was given. Use the newest "
            "card, or send /gift again.",
        )
        return
    context.user_data.pop(GIFT_PENDING, None)
    context.user_data[GIFT_DONE] = nonce
    key, amount = pending["args"].split()[:2]
    if action != "go":
        await edit_in_place(query.message, context.bot,
                            f"Cancelled — nothing was given ({amount} ⚡, key {key}).")
        return
    queued, failed = [], []
    for bot_id in pending["bots"]:
        try:
            await asyncio.to_thread(
                db.queue_command, bot_id, "gift", pending["args"] + " --go",
                update.effective_user.id, update.effective_chat.id,
            )
            queued.append(bot_id)
        except Exception as exc:
            failed.append(bot_id)
            logger.warning("Gift %s: could not be queued for %s (%s)", key, bot_id, type(exc).__name__)
    if queued:
        text = (f"🎁 Giving {amount} ⚡ (key {key}), through {', '.join(queued)}. "
                f"Each bot reports back how many people it gave it to when it has been "
                f"through its list.")
    else:
        text = f"🎁 Nothing was given ({amount} ⚡, key {key}): no bot could be asked."
    if failed:

        text += (f"\n\n⚠️ Could not ask {', '.join(failed)} (a database error, see "
                 f"the log). Send the same /gift again and press Give it: nobody "
                 f"gets it twice.")
    await edit_in_place(query.message, context.bot, text)

PROMO_COUNT_SECONDS = 15 * 60
PROMO_COUNT_FIRST_SECONDS = 60
PROMO_PENDING = "promo_pending"
PROMO_DONE = "promo_done"
PROMO_BUTTON_PATTERN = r"^promo:(go|cancel):[0-9a-f]{8}$"

_promo_count: dict = {"count": None, "at": None}

def _promo_schemas() -> list[str]:
    return [child["schema"] for child in CHILDREN]

def _promo_moment(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def _promo_last_day(closes: datetime) -> str:
    """The last day somebody can claim, from the midnight claiming closes at."""
    return (closes - timedelta(days=1)).strftime("%d.%m.%Y")

def _promo_db_error(exc: Exception) -> str:
    return f"Could not read the gift's state ({type(exc).__name__}). Nothing was changed."

async def count_unique_people(context: ContextTypes.DEFAULT_TYPE):
    """The 15-minute job: count the people across all the bots, and the first time the count reaches the mark, tell the owner once."""
    try:
        count = await asyncio.to_thread(db.unique_people, _promo_schemas())
        _promo_count.update(count=count, at=datetime.now(timezone.utc))
        if count < family_link.PROMO_USERS:
            return
        if await asyncio.to_thread(family_link.promo_milestone_at) is not None:
            return

        started = await asyncio.to_thread(family_link.promo_window, True)
        if started is not None:
            await asyncio.to_thread(family_link.note_promo_milestone)
            return
        delivered = await notify_owner(
            context,
            f"🎉 Mumu bots have reached {count} unique users (everyone who has used any of the bots, "
            f"counted once). That's the mark for the {family_link.PROMO_CREDITS} ⚡ gift: start it with /promo.",
        )
        if delivered is False:
            logger.warning("The gift's milestone notice could not be delivered; trying again at the next count")
            return
        await asyncio.to_thread(family_link.note_promo_milestone)
    except Exception as exc:
        logger.warning("The unique-people count did not finish (%s); trying again at the next one",
                       type(exc).__name__)

def _promo_status_text(started: datetime, closes: datetime, claims: int, seen: "int | None") -> str:
    now = datetime.now(timezone.utc)
    is_open = now < closes
    stopped_early = closes < family_link.promo_closes_for(started)
    text = (f"The {family_link.PROMO_CREDITS} ⚡ gift started {_promo_moment(started)}.\n"
            f"Claims {'are open until' if is_open else 'closed at'} {_promo_moment(closes)}"
            f"{' -- stopped early' if stopped_early else ''}.\n"
            f"Claimed by {claims} people. AnonBot showed the ad to {'?' if seen is None else seen} people.")
    if is_open:
        text += "\nTo end the claiming now: /promo stop"
    return text

def _promo_card_text(count: int) -> str:
    """The card, in HTML."""
    closes = family_link.promo_closes_for(datetime.now(timezone.utc))
    claim_by = html.escape(_promo_last_day(closes))
    amount, spend_days = family_link.PROMO_CREDITS, family_link.PROMO_SPEND_DAYS
    return (
        f"Start the {amount} ⚡ gift? This can be done once.\n"
        f"• Anyone who writes to ConvertBot or DownloaderBot until {claim_by} (the end of that day, UTC) "
        f"gets {amount} ⚡ of bonus credit, once, automatically, and a notice.\n"
        f"• Each gift can be spent for {spend_days} days from the day it is claimed.\n"
        f"• AnonBot shows this ad once to each person who writes to it, until then:\n\n"
        f"{family_link.promo_ad('en', closes)}\n\n"
        f"Unique users now: {count}."
    )

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/promo -- where the 220 ⚡ gift stands, and once the mark is reached a card to start it; /promo stop -- end the claiming early."""
    if not await guard(update, context):
        return
    args = [arg.lower() for arg in context.args]
    if args == ["stop"]:
        await _promo_stop(update)
        return
    if args:
        await update.message.reply_text("Usage: /promo, or /promo stop.")
        return
    try:
        window = await asyncio.to_thread(family_link.promo_window, True)
        if window is not None:
            claims = await asyncio.to_thread(family_link.promo_claim_count)
            anon = next((child for child in CHILDREN if child["id"] == "anonbot"), None)
            seen = (await asyncio.to_thread(db.promo_seen_count, anon["schema"], family_link.PROMO_KEY)
                    if anon else None)
            await update.message.reply_text(_promo_status_text(window[0], window[1], claims, seen))
            return
        count = await asyncio.to_thread(db.unique_people, _promo_schemas())
        milestone = await asyncio.to_thread(family_link.promo_milestone_at)
    except Exception as exc:
        await update.message.reply_text(_promo_db_error(exc))
        return
    if count < family_link.PROMO_USERS and milestone is None:
        await update.message.reply_text(
            f"The {family_link.PROMO_CREDITS} ⚡ gift can start once the bots have {family_link.PROMO_USERS} "
            f"unique users. Now: {count}. I'll message you when it happens.")
        return
    nonce = secrets.token_hex(4)
    context.user_data[PROMO_PENDING] = nonce
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("▶️ Start the gift", callback_data=f"promo:go:{nonce}"),
        InlineKeyboardButton("Cancel", callback_data=f"promo:cancel:{nonce}"),
    ]])
    await update.message.reply_text(_promo_card_text(count), parse_mode=ParseMode.HTML, reply_markup=kb)

async def _promo_stop(update: Update):
    try:
        stopped = await asyncio.to_thread(family_link.stop_promo)
    except Exception as exc:
        await update.message.reply_text(_promo_db_error(exc))
        return
    if not stopped:
        await update.message.reply_text("The gift is not open (not started yet, or already over). Nothing to stop.")
        return
    try:
        claims = await asyncio.to_thread(family_link.promo_claim_count)
    except Exception:
        claims = "?"
    await update.message.reply_text(
        f"Stopped. Nobody can claim the gift any more; the {claims} people who have it keep it until it runs out.")

async def promo_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on the card."""
    query = update.callback_query
    if not await guard(update, context):
        return
    await query.answer()
    action, _, nonce = query.data.removeprefix("promo:").partition(":")
    if nonce and nonce == context.user_data.get(PROMO_DONE):

        return
    if not nonce or nonce != context.user_data.get(PROMO_PENDING):
        await edit_in_place(
            query.message, context.bot,
            "That card is not the one waiting (a newer /promo replaced it, or it is from before an "
            "update). Nothing was started. Send /promo again.",
        )
        return
    context.user_data.pop(PROMO_PENDING, None)
    context.user_data[PROMO_DONE] = nonce
    if action != "go":
        await edit_in_place(query.message, context.bot, "Cancelled. Nothing was started.")
        return

    try:
        window = await asyncio.to_thread(family_link.promo_window, True)
        if window is not None:
            text = f"It had already started {_promo_moment(window[0])}. Nothing changed."
        else:
            count = await asyncio.to_thread(db.unique_people, _promo_schemas())
            reached = count >= family_link.PROMO_USERS or (
                await asyncio.to_thread(family_link.promo_milestone_at)) is not None
            if not reached:
                text = (f"Not yet: {count} unique users of {family_link.PROMO_USERS}. "
                        f"Nothing was started.")
            else:
                started, won = await asyncio.to_thread(family_link.start_promo)
                if won:
                    text = (f"Started {_promo_moment(started)}. Claims close "
                            f"{_promo_last_day(family_link.promo_closes_for(started))} "
                            f"(the end of that day, UTC). /promo shows how it goes.")
                else:
                    text = f"It had already started {_promo_moment(started)}. Nothing changed."
    except Exception as exc:
        text = f"Could not start it ({type(exc).__name__}). Nothing was started; send /promo again."
    await edit_in_place(query.message, context.bot, text)

BOT_COMMANDS = [

    BotCommand("status", "Every bot: up, version, errors, users"),
    BotCommand("nightly", "The 22:00 nightly report, on demand"),
    BotCommand("feedback", "What people sent with /feedback"),
    BotCommand("reports", "Latest problems, each with its incident code"),
    BotCommand("report", "One problem in full, by its incident code"),
    BotCommand("errors", "What each bot has hit since it started"),
    BotCommand("events", "Crashes, restarts and payments as they happened"),
    BotCommand("ping", "How fast each bot is, for a user and on the bus"),
    BotCommand("providers", "Which download routes work, which rest"),
    BotCommand("probe", "Test every download route, from its container"),
    BotCommand("logs", "Tail a bot's log"),
    BotCommand("usage", "Memory, peaks, and what they cost"),
    BotCommand("idle", "How quiet each bot is; would sleeping pay?"),
    BotCommand("buttons", "Button taps per bot, counts only"),
    BotCommand("stats", "Anonymous daily statistics, for infographics"),
    BotCommand("run", "Run a command inside another bot"),
    BotCommand("restart", "Restart a bot's service once nobody is using it"),
    BotCommand("shutdown", "Stop a bot's service once nobody is using it"),
    BotCommand("pause", "Stop the bots taking work an update would lose"),
    BotCommand("warn", "Tell whoever is mid-something that it will reset"),
    BotCommand("resume", "Reopen, and tell everyone who was waiting"),
    BotCommand("say", "Message one person, as one of the bots"),
    BotCommand("broadcast", "Message everyone, as one of the bots"),
    BotCommand("whois", "Look a user up through a bot"),
    BotCommand("users", "Active users per bot"),
    BotCommand("balance", "See or change a credit balance"),
    BotCommand("addcredit", "Add ⚡ credit to an account by Telegram id"),
    BotCommand("gift", "Bonus ⚡ for everyone; counts, then asks"),
    BotCommand("promo", "The 220 ⚡ gift: start, status, stop"),
    BotCommand("donations", "Paid donations per bot"),
    BotCommand("stars", "ConvertBot's Stars: paid, refunded, recent"),
    BotCommand("backup", "Whole database, restorable, pinned here"),
    BotCommand("dbdump", "One bot's tables as CSVs"),
    BotCommand("sql", "Read-only query on the shared database"),
    BotCommand("decode", "What an error code means"),
    BotCommand("alerts", "Mute or unmute alerts"),
    BotCommand("help", "What all of this does"),
]

STRANGER_COMMANDS = [
    BotCommand("start", "what this bot is"),
]

async def _publish_commands(application):
    """The full menu in each owner's chat, and one line for everybody else."""
    try:
        await application.bot.set_my_commands(STRANGER_COMMANDS)
    except Exception:
        logger.warning("Couldn't publish the public command menu.", exc_info=True)
    for admin_id in sorted(ADMIN_IDS):
        try:
            await application.bot.set_my_commands(
                BOT_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception:
            logger.warning("Couldn't publish the owner's command menu to %s.",
                           admin_id, exc_info=True)

    from telegram import (BotCommandScopeAllChatAdministrators, BotCommandScopeAllGroupChats,
                          BotCommandScopeAllPrivateChats)
    for scope in (BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats,
                  BotCommandScopeAllChatAdministrators):
        try:
            await application.bot.delete_my_commands(scope=scope())
        except Exception:
            logger.debug("Couldn't clear the %s menu.", scope.__name__, exc_info=True)

SHORT_DESCRIPTION = "A private bot. It looks after one person's other bots."

def _description() -> str:
    """Read off USERNAME_ALIASES rather than typed out again, so a bot that gets renamed is renamed here too."""
    siblings = ", ".join(
        "@" + USERNAME_ALIASES[bot["id"]][0]
        for bot in CHILDREN if USERNAME_ALIASES.get(bot["id"])
    )
    return (
        "This bot is not for general use and it will not answer you. It "
        "watches the public bots in this family — whether they are up, what "
        "they are doing, and when one of them breaks — and takes commands "
        "from their owner only.\n\n"
        f"The bots it looks after: {siblings}."
    )

async def _publish_profile(application):
    """Never raises, same reasoning as the menu above."""
    try:
        await application.bot.set_my_short_description(SHORT_DESCRIPTION)
        await application.bot.set_my_description(_description())
    except Exception:
        logger.warning("Couldn't publish ManagerBot's profile text.", exc_info=True)

async def _post_init(application):
    await tune_runtime(application)
    await lifecycle.on_start(BOT_NAME)
    await _publish_commands(application)
    await _publish_profile(application)

async def _post_stop(application):
    await lifecycle.on_stop(application)
    await flush_on_shutdown(application)

def main():
    if not BOT_TOKEN or not BOT_USERNAME:
        raise SystemExit("Set MBOT_TOKEN and MBOT_USERNAME environment variables first.")
    if not ADMIN_IDS:

        raise SystemExit(
            "MBOT_ADMIN_ID is empty. ManagerBot is owner-only by definition and "
            "refuses to start without knowing who the owner is -- put your numeric "
            "Telegram id there (get it from @userinfobot)."
        )

    init_db()

    builder = (
        ApplicationBuilder().token(BOT_TOKEN)
        .post_init(_post_init).post_stop(_post_stop)
    )
    state = lifecycle.persistence()
    if state is not None:
        builder = builder.persistence(state)
    app = builder.build()
    lifecycle.install(app, BOT_NAME, ADMIN_IDS)
    app.add_error_handler(error_handler)

    app.add_handler(TypeHandler(Update, track_activity), group=-3)

    app.add_handler(CommandHandler(["start", "help"], start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("usage", usage_command))
    app.add_handler(CommandHandler("idle", idle_command))
    app.add_handler(CommandHandler("buttons", buttons_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("ping", broadcast_ping))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("donations", donations_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("addcredit", addcredit_command))
    app.add_handler(CommandHandler("events", events_command))
    app.add_handler(CommandHandler("sql", sql_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(CommandHandler("reports", reports_command))
    app.add_handler(CommandHandler("report", report_command))

    app.add_handler(CommandHandler(["nightly", "problems"], nightly_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("decode", decode_command))
    app.add_handler(CommandHandler("alerts", alerts_command))
    app.add_handler(CommandHandler("crashtest", crashtest_command))

    app.add_handler(CommandHandler("errors", errors_command))
    app.add_handler(CommandHandler("errorlog", _log_shortcut("errorlog")))
    app.add_handler(CommandHandler("botlog", _log_shortcut("botlog")))
    app.add_handler(CommandHandler("problemlog", _log_shortcut("problemlog")))
    app.add_handler(CommandHandler("logs", _shortcut("logs", 1, "Usage: /logs <bot> [lines] [bot|problems]")))
    app.add_handler(CommandHandler("dbdump", _shortcut("dbdump", 1, "Usage: /dbdump <bot> — or /backup for everything")))
    app.add_handler(CommandHandler("restart", restart_command))
    app.add_handler(CommandHandler("shutdown", shutdown_command))
    app.add_handler(CommandHandler("whois", _shortcut("whois", 2, "Usage: /whois <bot> <user_id>")))
    app.add_handler(CommandHandler("say", _shortcut("message", 3, "Usage: /say <bot> <user_id> <text>")))

    app.add_handler(CommandHandler("providers", _shortcut("providers", 0, "", default_bot="downloaderbot")))
    app.add_handler(CommandHandler("probe", _shortcut("probe", 0, "", default_bot="downloaderbot")))
    app.add_handler(CommandHandler("stars", _shortcut("stars", 0, "", default_bot="convertbot")))

    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("gift", gift_command))
    app.add_handler(CommandHandler("promo", promo_command))
    app.add_handler(CommandHandler("pause", pause_command))
    app.add_handler(CommandHandler("warn", warn_command))

    app.add_handler(CommandHandler(["resume", "finishupdates"], finish_updates_command))

    app.add_handler(CallbackQueryHandler(board_button, pattern=r"^board:"))
    app.add_handler(CallbackQueryHandler(ping_detail_button, pattern=r"^pingdet:"))
    app.add_handler(CallbackQueryHandler(help_page_button, pattern=r"^helpdet:[a-z]{1,20}$"))
    app.add_handler(CallbackQueryHandler(broadcast_button, pattern=r"^upd:"))
    app.add_handler(CallbackQueryHandler(service_button, pattern=r"^svc:"))
    app.add_handler(CallbackQueryHandler(gift_button, pattern=r"^gift:"))
    app.add_handler(CallbackQueryHandler(promo_button, pattern=PROMO_BUTTON_PATTERN))
    app.add_handler(CallbackQueryHandler(log_pick_button, pattern=r"^logpick:"))
    app.add_handler(CallbackQueryHandler(feedback_mode_button, pattern=r"^fbmode:"))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text))

    if app.job_queue is None:

        raise SystemExit(
            "No JobQueue available, which means no watchdog, no alerts and no /run "
            'results -- ManagerBot would be a shell. Install it with:\n'
            '    pip install "python-telegram-bot[job-queue]"'
        )

    app.job_queue.run_once(startup_rollcall, when=STARTUP_ROLLCALL_SECONDS)
    app.job_queue.run_repeating(watchdog, interval=60, first=20)

    app.job_queue.run_repeating(count_unique_people, interval=PROMO_COUNT_SECONDS,
                                first=PROMO_COUNT_FIRST_SECONDS)

    app.job_queue.run_repeating(_event_backstop, interval=PUMP_TICK_SECONDS, first=10)
    app.job_queue.run_repeating(_result_backstop, interval=PUMP_TICK_SECONDS, first=5)

    app.job_queue.run_once(result_pump, when=0, job_kwargs=family_link.RUN_LATE)
    app.job_queue.run_once(event_pump, when=0, job_kwargs=family_link.RUN_LATE)
    if DIGEST_AT_UTC:
        hour, _, minute = DIGEST_AT_UTC.partition(":")
        app.job_queue.run_daily(
            daily_digest, time(int(hour), int(minute or 0), tzinfo=timezone.utc)
        )
        logger.info("Daily digest scheduled for %s UTC.", DIGEST_AT_UTC)
    if NIGHTLY_REPORT_AT_UTC:
        hour, _, minute = NIGHTLY_REPORT_AT_UTC.partition(":")
        app.job_queue.run_daily(
            nightly_problem_report, time(int(hour), int(minute or 0), tzinfo=timezone.utc)
        )
        logger.info("Nightly problem report scheduled for %s UTC (22:00 in Seoul at the default).",
                    NIGHTLY_REPORT_AT_UTC)

    family_link.attach(app, BOT_NAME, DISPLAY_NAME, START_TIME)
    attach_maintenance(app)

    logger.info("ManagerBot starting (polling). Watching: %s", bot_list_hint())

    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
    ))

if __name__ == "__main__":
    main()

# ─── module: manager_bot.monitoring ──────────────────────────────────────────
"""ManagerBot's own logging / crash tracking / activity tracking."""
import asyncio
import gc
import logging
import os
import socket
import sys
import time
import traceback
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler

from telegram.error import BadRequest, Conflict, NetworkError, RetryAfter

import db
import family_link
import live_message

_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

_recent_errors: deque[tuple[str, str]] = deque(maxlen=10)
_error_count = 0

_event_hook = None

def set_event_hook(fn) -> None:
    global _event_hook
    _event_hook = fn

def emit_event(level: str, kind: str, message: str, details: str | None = None) -> None:
    if _event_hook is None:
        return
    try:
        _event_hook(level, kind, message, details)
    except Exception:
        logging.getLogger(__name__).debug("Family event hook failed", exc_info=True)

def _log_to_files() -> bool:
    """Files on a laptop, stdout only in the cloud -- see the identical reasoning in the other four bots' shared_features.py."""
    override = os.environ.get("LOG_TO_FILES")
    if override is not None:
        return override.strip().lower() in ("1", "true", "yes", "on")
    return not (os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT"))

def setup_logging(bot_file: str) -> None:
    fmt = logging.Formatter(_LOG_FORMAT)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    for noisy in ("httpx", "httpcore", "telegram.ext.Updater", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not _log_to_files():
        return

    log_dir = os.path.join(os.path.dirname(os.path.abspath(bot_file)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    info_file = RotatingFileHandler(
        os.path.join(log_dir, "bot.log"), maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    info_file.setFormatter(fmt)
    root.addHandler(info_file)

    error_file = RotatingFileHandler(
        os.path.join(log_dir, "errors.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    error_file.setLevel(logging.WARNING)
    error_file.setFormatter(fmt)
    root.addHandler(error_file)

TRANSIENT_NETWORK_ERRORS = (NetworkError, RetryAfter)

NETWORK_ALERT_AFTER = int(os.environ.get("NETWORK_ALERT_AFTER", "20"))

_network_blips = 0
_network_blips_total = 0
_network_alerted = False

PERMANENT_NETWORK_MESSAGES = ("entity too large", "file is too big", "too big", "too large")

def is_transient_network_error(exc: BaseException) -> bool:
    if not isinstance(exc, TRANSIENT_NETWORK_ERRORS) or isinstance(exc, BadRequest):
        return False
    text = str(exc).lower()
    return not any(marker in text for marker in PERMANENT_NETWORK_MESSAGES)

def note_network_blip(exc: BaseException) -> None:
    """Counted and logged, never reported as a crash -- until there have been enough in a row to mean the connection is gone rather than flaky, which is worth exactly one message."""
    global _network_blips, _network_blips_total, _network_alerted
    _network_blips += 1
    _network_blips_total += 1
    logging.getLogger(__name__).warning(
        "Transient network error (%s): %s -- retried by PTB, %s in a row",
        type(exc).__name__, exc, _network_blips,
    )
    if _network_blips >= NETWORK_ALERT_AFTER and not _network_alerted:
        _network_alerted = True
        emit_event(
            "warning", "network",
            f"{_network_blips} network errors in a row -- this bot may not be "
            f"reaching Telegram. Latest: {type(exc).__name__}: {exc}",
        )

def note_network_ok() -> None:
    """An update arrived, so the connection works. Called from track_activity, which runs before every other handler."""
    global _network_blips, _network_alerted
    if _network_blips and _network_alerted:
        emit_event("info", "network", "Telegram is reachable again.")
    _network_blips = 0
    _network_alerted = False

CONFLICT_ALERT_COUNT = 3
CONFLICT_ALERT_WINDOW_S = 120
CONFLICT_QUIET_RESET_S = 600

_conflict_times: "deque[float]" = deque(maxlen=CONFLICT_ALERT_COUNT)
_conflict_last: "float | None" = None
_conflict_alerted = False

def note_conflict(exc: BaseException) -> None:
    """A Conflict from the long poll (no update behind it)."""
    global _conflict_last, _conflict_alerted
    now = time.monotonic()
    if _conflict_last is not None and now - _conflict_last >= CONFLICT_QUIET_RESET_S:
        _conflict_times.clear()
        _conflict_alerted = False
    _conflict_last = now
    _conflict_times.append(now)
    in_window = sum(1 for seen in _conflict_times if now - seen <= CONFLICT_ALERT_WINDOW_S)
    logging.getLogger(__name__).warning(
        "Conflict on getUpdates: %s within the last %s s (a report needs %s)",
        in_window, CONFLICT_ALERT_WINDOW_S, CONFLICT_ALERT_COUNT,
    )
    if in_window >= CONFLICT_ALERT_COUNT and not _conflict_alerted:
        _conflict_alerted = True
        message = (
            "Another copy of this bot seems to be polling with the same token: "
            f"{in_window} conflicts within {CONFLICT_ALERT_WINDOW_S} seconds"
        )
        logging.getLogger(__name__).error(message)
        report = Conflict(message)
        report.__cause__ = exc
        record_error(report)

def record_error(exc: BaseException) -> None:
    global _error_count
    _error_count += 1
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    _recent_errors.append((stamp, repr(exc)))
    emit_event(
        "error", "crash", f"ManagerBot itself hit an unhandled {type(exc).__name__}: {exc}",
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )

def error_summary() -> str:
    blips = (
        f"\n\U0001f310 {_network_blips_total} transient network error(s) -- retried, not crashes."
        if _network_blips_total else ""
    )
    if _error_count == 0:
        return "✅ No errors since this instance started." + blips
    lines = [f"⚠️ {_error_count} error(s) since start:"]
    lines.extend(f"  {stamp} — {msg}" for stamp, msg in _recent_errors)
    if _error_count > len(_recent_errors):
        lines.append(f"  (+{_error_count - len(_recent_errors)} earlier, see logs/errors.log)")
    return "\n".join(lines) + blips

async def error_handler(update, context) -> None:
    """Register with Application.add_error_handler in each bot's main() -- this is PTB's global hook for exceptions that escape a handler callback uncaught (i.e."""

    if update is None and is_transient_network_error(context.error):
        note_network_blip(context.error)
        return

    if update is None and isinstance(context.error, Conflict):
        note_conflict(context.error)
        return
    logging.getLogger(__name__).error("Unhandled exception while processing an update", exc_info=context.error)
    record_error(context.error)

ACTIVITY_FLUSH_SECONDS = int(os.environ.get("ACTIVITY_FLUSH_SECONDS", "60"))

_activity_buffer: set[int] = set()

def _flush_activity_now() -> int:
    global _activity_buffer
    if not _activity_buffer:
        return 0
    batch, _activity_buffer = _activity_buffer, set()
    try:
        db.record_activity_batch(batch)
    except Exception:
        _activity_buffer |= batch
        raise
    return len(batch)

async def _flush_activity_job(context) -> None:
    try:
        await asyncio.to_thread(_flush_activity_now)
    except Exception:
        logging.getLogger(__name__).debug("Activity flush failed; will retry", exc_info=True)

async def track_activity(update, context) -> None:
    note_network_ok()

    live_message.note_update(update)
    user = update.effective_user
    if not user:
        return
    _activity_buffer.add(user.id)
    note_usage_update(user.id)

WORKER_THREADS = int(os.environ.get("WORKER_THREADS", "4"))
GC_THRESHOLD = int(os.environ.get("GC_GEN0_THRESHOLD", "5000"))

async def tune_runtime(application) -> None:
    """Call from post_init -- see shared_features.py for why the default executor is worth capping, why everything imported at startup is worth freezing out of the garbage collector's reach, and why an idle process should not be sweeping its heap every few seconds."""
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=WORKER_THREADS, thread_name_prefix="worker")
    )
    gc.collect()
    gc.freeze()
    gc.set_threshold(GC_THRESHOLD, 20, 20)

def attach_maintenance(app) -> None:
    """One line in ManagerBot's main()."""
    app.job_queue.run_repeating(
        _flush_activity_job, interval=ACTIVITY_FLUSH_SECONDS, first=ACTIVITY_FLUSH_SECONDS
    )
    app.job_queue.run_repeating(
        _usage_sample_job, interval=USAGE_SAMPLE_MINUTES * 60,
        first=USAGE_SAMPLE_MINUTES * 60 + 60,
    )

async def flush_on_shutdown(application) -> None:
    """Register as Application.post_stop."""
    try:
        await asyncio.to_thread(_flush_activity_now)
    except Exception:
        logging.getLogger(__name__).debug("Final activity flush failed", exc_info=True)
    try:
        await asyncio.to_thread(db.close_pool)
    except Exception:
        logging.getLogger(__name__).debug("Closing the connection pool failed", exc_info=True)

def detect_host_environment() -> str:
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT")
    if railway_env:
        project = os.environ.get("RAILWAY_PROJECT_NAME", "?")
        service = os.environ.get("RAILWAY_SERVICE_NAME", "?")
        return f"☁️ Cloud (Railway -- project \"{project}\", service \"{service}\", env \"{railway_env}\")"
    return f"💻 Local ({socket.gethostname()})"

def _read_first_int(path: str, key: str | None = None) -> int | None:
    try:
        with open(path) as handle:
            if key is None:
                text = handle.read().strip()
                return int(text) if text.isdigit() else None
            for line in handle:
                if line.startswith(key):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None

def _memory_ceiling_bytes() -> int | None:
    """What the container is allowed, rather than what the host has."""
    for path, scale in (("/sys/fs/cgroup/memory.max", 1),
                        ("/sys/fs/cgroup/memory/memory.limit_in_bytes", 1)):
        value = _read_first_int(path)

        if value and value < (1 << 62):
            return value * scale
    return None

def footprint_numbers() -> dict:
    """The same four readings process_footprint() prints, as numbers."""
    resident = _read_first_int("/proc/self/status", "VmRSS:")
    peak = _read_first_int("/proc/self/status", "VmHWM:")
    ceiling = _memory_ceiling_bytes()
    cpu = None
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        cpu = usage.ru_utime + usage.ru_stime
        if resident is None:

            scale = 1 if sys.platform == "darwin" else 1024
            peak = usage.ru_maxrss * scale // 1024
    except Exception:
        pass
    return {
        "rss_mb": None if resident is None else resident // 1024,
        "peak_rss_mb": None if peak is None else peak // 1024,
        "ceiling_mb": None if ceiling is None else ceiling // (1024 * 1024),
        "cpu_seconds": None if cpu is None else int(cpu),
    }

def process_footprint() -> str:
    """One line: resident memory, its high-water mark, and CPU seconds burned since startup."""
    numbers = footprint_numbers()
    parts = []
    if numbers["rss_mb"] is not None:
        line = f"Memory: {numbers['rss_mb']} MB resident"
        if numbers["peak_rss_mb"]:
            line += f" (peak {numbers['peak_rss_mb']} MB)"
        if numbers["ceiling_mb"]:
            line += f" of {numbers['ceiling_mb']} MB allowed"
        parts.append(line)
    elif numbers["peak_rss_mb"] is not None:
        parts.append(f"Memory: peak {numbers['peak_rss_mb']} MB")
    if numbers["cpu_seconds"] is not None:
        parts.append(f"CPU: {numbers['cpu_seconds']}s used since start")
    trend = usage_trend_line()
    if trend:
        parts.append(trend)
    return " · ".join(parts) or "Footprint: not readable on this host"

SLEEP_AFTER_SECONDS = int(os.environ.get("SLEEP_AFTER_SECONDS") or 300)

USAGE_SAMPLE_MINUTES = int(os.environ.get("USAGE_SAMPLE_MINUTES") or 15)

USAGE_MEMORY_WARN_RATIO = float(os.environ.get("USAGE_MEMORY_WARN_RATIO") or 0.85)

USAGE_SPIKE_FACTOR = float(os.environ.get("USAGE_SPIKE_FACTOR") or 6.0)
USAGE_SPIKE_FLOOR = int(os.environ.get("USAGE_SPIKE_FLOOR") or 60)

USAGE_MONTHLY_USERS_WARN = int(os.environ.get("USAGE_MONTHLY_USERS_WARN") or 400)

SLEEP_AFTER_SECONDS = int(os.environ.get("SLEEP_AFTER_SECONDS") or 300)

USAGE_FAILURE_WARN_RATIO = float(os.environ.get("USAGE_FAILURE_WARN_RATIO") or 0.5)
USAGE_FAILURE_FLOOR = int(os.environ.get("USAGE_FAILURE_FLOOR") or 4)

_USAGE_WINDOW_MEMORY = 24
_ALARM_QUIET_SECONDS = {"memory": 3600, "spike": 3600, "monthly_users": 86400,
                        "failures": 1800}

_usage_updates = 0
_usage_users: set[int] = set()
_usage_recent: "deque[int]" = deque(maxlen=_USAGE_WINDOW_MEMORY)
_usage_alarmed: dict[str, float] = {}

_usage_last_update = time.monotonic()
_usage_window_start = _usage_last_update
_usage_sleepable = 0.0
_usage_max_gap = 0.0
_usage_jobs_ok = 0
_usage_jobs_failed = 0

def _asleep_in_window(now: float) -> float:
    """How much of this window, up to `now`, the host would have been asleep for: the quiet since the last update, from SLEEP_AFTER_SECONDS into it, and only the part of that inside this window."""
    return max(0.0, now - max(_usage_last_update + SLEEP_AFTER_SECONDS, _usage_window_start))

def note_usage_update(user_id: int | None) -> None:
    """One update happened."""
    global _usage_updates, _usage_last_update, _usage_sleepable, _usage_max_gap
    _usage_updates += 1
    now = time.monotonic()
    gap = now - _usage_last_update
    _usage_sleepable += _asleep_in_window(now)
    _usage_last_update = now
    _usage_max_gap = max(_usage_max_gap, gap)
    if user_id is not None and len(_usage_users) < 10000:
        _usage_users.add(user_id)

def note_job(ok: bool) -> None:
    """One unit of the thing this bot is for finished -- a conversion, a download, a pack edit."""
    global _usage_jobs_ok, _usage_jobs_failed
    if ok:
        _usage_jobs_ok += 1
    else:
        _usage_jobs_failed += 1

def _alarm_due(kind: str) -> bool:
    now = time.time()
    if now - _usage_alarmed.get(kind, 0) < _ALARM_QUIET_SECONDS.get(kind, 3600):
        return False
    _usage_alarmed[kind] = now
    return True

def _median(values) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2

def usage_trend_line() -> str:
    """One line for /status: what the recent windows looked like, so the number above it has something to be compared with."""
    if not _usage_recent:
        return ""
    quiet = int(time.monotonic() - _usage_last_update)
    return (f"Recent: {sum(_usage_recent)} update(s) over the last "
            f"{len(_usage_recent)} window(s) of {USAGE_SAMPLE_MINUTES} min · "
            f"quiet for {quiet // 60}m {quiet % 60}s")

def _monthly_users() -> int | None:
    """Distinct people in the last thirty days, if this bot's db can say."""
    counter = getattr(db, "count_active_users_since", None)
    if counter is None:
        return None
    try:
        return counter(datetime.now(timezone.utc) - timedelta(days=30))
    except Exception:
        return None

def _check_usage_alarms(numbers: dict, updates: int, users: int,
                        jobs_ok: int = 0, jobs_failed: int = 0) -> None:
    """Blocking; runs in the same thread as the sample write."""
    jobs = jobs_ok + jobs_failed
    if (jobs >= USAGE_FAILURE_FLOOR
            and jobs_failed / jobs >= USAGE_FAILURE_WARN_RATIO
            and _alarm_due("failures")):
        family_link.report_event(
            "warning" if jobs_ok else "error", "job_failures",
            f"{jobs_failed} of {jobs} job(s) failed in the last "
            f"{USAGE_SAMPLE_MINUTES} min"
            + ("." if jobs_ok else " -- none succeeded."),
            "A job is whatever this bot is for: a conversion, a download, a pack "
            "edit. All of them failing usually means something outside the bot "
            "stopped answering rather than something inside it breaking.",
        )
    ceiling = numbers.get("ceiling_mb")
    peak = numbers.get("peak_rss_mb")
    if ceiling and peak and peak >= ceiling * USAGE_MEMORY_WARN_RATIO and _alarm_due("memory"):
        family_link.report_event(
            "warning", "memory_headroom",
            f"Memory peaked at {peak} MB of {ceiling} MB allowed "
            f"({peak / ceiling:.0%} of the limit).",
            "Crossing the limit is an out-of-memory kill rather than a slow reply. "
            "Either something is holding more than it should, or this service has "
            "outgrown its plan.",
        )

    baseline = _median(_usage_recent)
    if (updates >= USAGE_SPIKE_FLOOR and baseline > 0
            and updates >= baseline * USAGE_SPIKE_FACTOR and _alarm_due("spike")):
        family_link.report_event(
            "warning", "activity_spike",
            f"{updates} updates from {users} person(s) in {USAGE_SAMPLE_MINUTES} min, "
            f"against a recent median of {baseline:.0f}.",
            "Could be a launch and could be one script. /status and the usage table "
            "have the shape of it.",
        )

    monthly = _monthly_users()
    if monthly is not None and monthly >= USAGE_MONTHLY_USERS_WARN and _alarm_due("monthly_users"):
        family_link.report_event(
            "warning", "monthly_users",
            f"{monthly} distinct people used this bot in the last 30 days, "
            f"past the {USAGE_MONTHLY_USERS_WARN} mark.",
            "Nothing is refused and nothing is broken. It is the number that decides "
            "whether the plan this runs on is still the right one.",
        )

def _sample_usage_now() -> None:
    """One window: write the row, then decide whether to say anything."""
    global _usage_updates, _usage_users
    updates, users = _usage_updates, len(_usage_users)
    _usage_updates, _usage_users = 0, set()
    numbers = footprint_numbers()
    global _usage_sleepable, _usage_max_gap, _usage_jobs_ok, _usage_jobs_failed

    global _usage_window_start
    now = time.monotonic()
    trailing = now - _usage_last_update
    sleepable = int(_usage_sleepable + _asleep_in_window(now))
    max_gap = int(max(_usage_max_gap, trailing))
    jobs_ok, jobs_failed = _usage_jobs_ok, _usage_jobs_failed
    _usage_sleepable, _usage_max_gap = 0.0, 0.0
    _usage_jobs_ok, _usage_jobs_failed = 0, 0
    _usage_window_start = now
    try:
        family_link.record_usage(
            USAGE_SAMPLE_MINUTES, numbers["rss_mb"], numbers["peak_rss_mb"],
            numbers["ceiling_mb"], numbers["cpu_seconds"], updates, users,
            sleepable, max_gap, jobs_ok, jobs_failed,
        )
    except Exception:
        logging.getLogger(__name__).debug("Usage sample not written", exc_info=True)
    try:
        _check_usage_alarms(numbers, updates, users, jobs_ok, jobs_failed)
    except Exception:
        logging.getLogger(__name__).debug("Usage alarm check failed", exc_info=True)
    _usage_recent.append(updates)

async def _usage_sample_job(context) -> None:
    await asyncio.to_thread(_sample_usage_now)
_BUILD = (os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "")[:7]

def build_status_text(start_time: datetime, users_last_hour: int, users_since_start: int) -> str:
    now = datetime.now(timezone.utc)
    uptime = now - start_time
    days, rem = divmod(int(uptime.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    uptime_str = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"
    return "\n".join([
        "📊 Status",
        f"Version: {family_link.VERSION}" + (f" ({_BUILD})" if _BUILD else ""),
        f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} ({uptime_str} ago)",
        f"Hosted: {detect_host_environment()}",
        f"Active users (last hour): {users_last_hour}",
        f"Active users (since this start): {users_since_start}",
        process_footprint(),
        "",
        error_summary(),
    ])
