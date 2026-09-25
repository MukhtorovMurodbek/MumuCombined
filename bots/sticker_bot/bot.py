"""
fstik-style sticker pack manager bot.

Part of a small bot family (see ARCHITECTURE.md): generic file conversion
(/convert, /mystars, /stars) lives in @ConvertBot, and Instagram/TikTok
downloading lives in @DownloaderBot. Each bot is its own process, its own
folder and its own deployment, with no shared files or file handoffs between
them -- so a clip that's too complex to compress into a video sticker just
dead-ends here with a pointer to @ConvertBot; the user re-sends it there.
The five do share one Postgres database, with a schema each; family_link.py
is the only code that touches anything outside this bot's own schema.

Commands:
  /start        - greeting + menu (also handles co-edit share links)
  /newpack      - create a new sticker set
  /addsticker   - add to an existing pack
  /mypacks      - list your packs; tap one for Add/Rename/Co-edit
  /import       - (while editing a pack) bulk-import from another Telegram
                  pack or a WhatsApp sticker pack .zip/.wastickers file
  /done         - finish the current pack-editing session
  /cancel       - stop whatever the bot is waiting on you for
  /whomade      - look up who created a pack (packs made through this bot)
  /donate       - support hosting costs (voluntary)
  /en, /uz, /rus - switch language (English/Uzbek/Russian); also asked
                    once, trilingually, on first /start

Once you're "editing" a pack (after /newpack, tapping Add on a pack, or
opening someone else's co-edit link), just send images, GIFs, videos, or
static/video stickers one after another -- each is added immediately with a
default 😭 emoji. Send emoji right after a sticker to retag it instead.
GIFs/videos are auto-converted (via ffmpeg) into Telegram's video-sticker
format; Lottie/.tgs animated stickers still aren't supported anywhere in
this bot family (needs a separate rendering pipeline neither bot has).

Requires: python-telegram-bot[job-queue]>=21.3, Pillow>=10.0, ffmpeg on PATH
Env vars: SBOT_TOKEN, SBOT_USERNAME (no @), DATABASE_URL and DB_SCHEMA
          (the shared family database, and this bot's schema in it),
          SIBLING_BOTS (see shared_features.py). Every performance/cost knob
          has a working default and is documented in .env.example.
"""
import asyncio
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from io import BytesIO

try:  # optional convenience: load BOT_TOKEN/BOT_USERNAME from a local .env file
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
)
from telegram.error import TimedOut
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

import family_link
import i18n
import problems
import lifecycle
import live_message
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
from video_sticker import to_video_sticker_webm, ConversionError
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
    donate_custom_amount_received,
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
BOT_USERNAME = os.environ.get("SBOT_USERNAME")  # no @

# Owner-only admin tools (/whois, /messageas, /dbdump, /status) -- comma-separated
# Telegram user ids, e.g. "111,222" for more than one of your own accounts.
# Empty/unset means those commands are disabled for everyone.
ADMIN_IDS = {int(x) for x in os.environ.get("SBOT_ADMIN_ID", "").split(",") if x.strip()}

# Optional: point at a self-hosted Bot API server (https://github.com/tdlib/telegram-bot-api)
# instead of Telegram's cloud one. This is what actually breaks the 20 MB download / 50 MB
# upload ceiling -- a local server raises those to (practically) unlimited download and
# ~1.9 GB upload. See https://github.com/tdlib/telegram-bot-api for setup.
LOCAL_BOT_API_URL = os.environ.get("LOCAL_BOT_API_URL")  # e.g. "http://localhost:8081"
LOCAL_BOT_API_MODE = os.environ.get("LOCAL_BOT_API_MODE", "true").lower() == "true"

# This bot's id within the family (matches a key in SIBLING_BOTS, see shared_features.py)
BOT_NAME = "stickerbot"

# Telegram's long-poll window. Higher means fewer requests for identical
# latency; 30s is comfortably inside every proxy's idle timeout.
POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "30"))

TITLE, EDITING, RENAME = range(3)


def build_help_text(lang: str) -> str:
    return i18n.t(lang, "help_text") + sibling_bots_blurb(BOT_NAME, lang)


def build_start_text(lang: str) -> str:
    return i18n.t(lang, "start_intro") + build_help_text(lang)


# Public command menu (the "/" button in Telegram's chat UI) -- set on
# startup via set_my_commands() below instead of pasting into @BotFather by
# hand. Owner-only admin commands (/whois, /messageas, /dbdump) are
# deliberately left off -- no reason to advertise them to every user.
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
    BotCommand("start", "What I do, and how to start"),
    BotCommand("language", "Choose your language / Tilni tanlash / Выбрать язык"),
    BotCommand("newpack", "Make a new sticker pack"),
    BotCommand("addsticker", "Add stickers to one of your packs"),
    BotCommand("mypacks", "Your packs"),
    BotCommand("import", "Copy stickers in from another pack"),
    BotCommand("done", "Finish the pack you are editing"),
    BotCommand("whomade", "Who made a pack — send me one of its stickers"),
    BotCommand("cancel", "Stop whatever I am waiting for"),
    BotCommand("help", "Everything I can do"),
    BotCommand("balance", "Your ⚡ credit"),
    BotCommand("donate", "Chip in for hosting costs"),
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
    BotCommand("whois", "🔒 whois <user_id> — a user, and their packs"),
    BotCommand("messageas", "🔒 messageas <user_id> <text> — DM as this bot"),
    BotCommand("dbdump", "🔒 This bot's tables as a zip of CSVs"),
    BotCommand("crashtest", "🔒 Raise on purpose, to check the alert arrives"),
]

# ---------- small helpers ----------

async def reply(update: Update, text: str, **kwargs) -> LiveMessage:
    """Works whether the update came from a command or a button tap. A
    button tap evolves the tapped message in place instead of sending a new
    one -- so menu navigation (start -> my packs -> a pack -> ...) reuses a
    single message, fstik/BotFather-style, rather than piling up a fresh one
    per tap. A command has no prior bot message to reuse, so it always sends
    fresh."""
    if update.message:
        return await LiveMessage.reply_to(update.message, text, **kwargs)
    return await edit_in_place(update.callback_query.message, update.get_bot(), text, **kwargs)


def slugify(text: str) -> str:
    """Telegram sticker-set names must start with a *letter* (not a digit or
    underscore) -- a title like "2007" would otherwise slugify to "2007",
    which Telegram rejects outright with 'Invalid sticker set name is
    specified'. Prefixing with a letter when needed avoids that.

    Stripping stray underscores happens both before *and* after truncating
    to 30 chars -- truncating mid-run of underscores (e.g. a long title
    with a space/symbol landing right at the cutoff) can otherwise leave a
    trailing "_" that collides with the "_" separator appended after this
    in bot.py, producing "__" in the final name, which Telegram also rejects.
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    slug = slug[:30].strip("_") or "pack"
    if not slug[0].isalpha():
        slug = ("p_" + slug)[:30].strip("_")
    return slug


def start_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(i18n.t(lang, "btn_new_pack"), callback_data="menu_newpack"),
            InlineKeyboardButton(i18n.t(lang, "btn_my_packs"), callback_data="menu_mypacks"),
        ],
        [InlineKeyboardButton(i18n.t(lang, "btn_help"), callback_data="menu_help")],
    ]
    sibling_row = sibling_bots_keyboard_row(BOT_NAME)
    if sibling_row:
        rows.append(sibling_row)
    return InlineKeyboardMarkup(rows)


def packs_keyboard(packs: list[tuple[str, str]], lang: str) -> InlineKeyboardMarkup:
    """One button per pack (tap opens its menu), fStik-style."""
    rows = [[InlineKeyboardButton(title, callback_data=f"packopen:{name}")] for name, title in packs]
    rows.append([InlineKeyboardButton(i18n.t(lang, "btn_new_pack"), callback_data="menu_newpack")])
    rows.append([InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data="menu_start")])
    return InlineKeyboardMarkup(rows)


def pack_detail_keyboard(pack_name: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(i18n.t(lang, "btn_open_pack"), url=f"https://t.me/addstickers/{pack_name}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_add_stickers"), callback_data=f"pack:{pack_name}")],
            [
                InlineKeyboardButton(i18n.t(lang, "btn_rename"), callback_data=f"packrename:{pack_name}"),
                InlineKeyboardButton(i18n.t(lang, "btn_coedit"), callback_data=f"packcoedit:{pack_name}"),
            ],
            [InlineKeyboardButton(i18n.t(lang, "btn_delete_pack"), callback_data=f"packdel:{pack_name}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data="menu_mypacks")],
        ]
    )


def _sticker_error_key(exc: Exception) -> tuple:
    """Which explanation a raw Telegram error from set-creation/add calls
    gets, as (i18n key, fields)."""
    if isinstance(exc, TimedOut):
        # Not a rejection -- Telegram (or a local Bot API server) just
        # didn't confirm in time, most often on a slow connection uploading
        # a converted video sticker. The upload may well have gone through
        # anyway, so don't call it "rejected" -- that's actively misleading.
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
    """Turns raw Telegram API errors from set-creation/add calls into
    something the user can actually act on, instead of a bare exception."""
    key, fields = _sticker_error_key(exc)
    return i18n.t(lang, key, **fields)


def _sticker_error_note(exc: Exception, lang: str) -> str:
    """The status note a failed sticker leaves: what went wrong, what to do
    next, and its problem code last, where the Report button looks for it."""
    key, _ = _sticker_error_key(exc)
    return (_explain_sticker_error(exc, lang) + "\n" + i18n.t(lang, "last_attempt_failed")
            + problems.code_line(problems.STICKER_ERRORS[key]))


def _status_text(context: ContextTypes.DEFAULT_TYPE, lang: str, note: str = "") -> str:
    title = context.user_data.get("title") or i18n.t(lang, "status_default_title")
    created = context.user_data.get("pack_created")
    count = context.user_data.get("sticker_count", 0)
    verb = i18n.t(lang, "status_verb_creating" if not created else "status_verb_editing")
    intro = context.user_data.get("status_intro", "")
    text = i18n.t(lang, "status_line", verb=verb, title=title, count=count)
    if intro:
        text = f"{intro}\n\n{text}"
    if note:
        text += f"\n{note}"
    return text


# The one message that tracks an editing session. It is the *only* thing
# this bot says while a pack is open: every "added ✅", every failure, every
# count is folded into it as the note line, rather than sent as a reply
# underneath. That is not tidiness for its own sake -- a message that keeps
# rewriting itself only works while it is the newest thing on screen, and a
# separate confirmation after each sticker would push it out of that place
# itself, every single time.
#
# When the user does speak over it -- another photo, a stray "ok" -- the
# handle notices and moves the whole status down to the bottom as a new
# message instead of rewriting one they have scrolled past. See
# live_message.py.
STATUS_KEY = "status"


def _has_status(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.get(STATUS_KEY))


async def _start_status(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, title: str, lang: str,
    intro: str = "", adopt: dict | None = None,
):
    """Sets up the session's status message.

    When `adopt` is a saved handle (typically the prompt that led here), that
    message becomes the status display instead of a new one being sent -- so
    "What should the pack title be?" turns into "📝 Creating "X" -- 0
    sticker(s)..." in place.
    """
    context.user_data["title"] = title
    context.user_data["sticker_count"] = 0
    context.user_data["status_intro"] = intro
    text = _status_text(context, lang)
    try:
        live = LiveMessage.restore(adopt)
        if live is None:
            live = await LiveMessage.send(context.bot, chat_id, text)
        else:
            await live.set(context.bot, text)
        context.user_data[STATUS_KEY] = live.save()
    except Exception:
        logger.exception("Couldn't set up the status message")


async def _refresh_status(context: ContextTypes.DEFAULT_TYPE, lang: str, note: str = ""):
    live = LiveMessage.restore(context.user_data.get(STATUS_KEY))
    if live is None:
        return
    await live.set(context.bot, _status_text(context, lang, note))
    # Saved back because set() may have moved it: a status the user talked
    # over is re-sent at the bottom, under a new message id.
    context.user_data[STATUS_KEY] = live.save()


async def _end_status(context: ContextTypes.DEFAULT_TYPE, final_note: str):
    live = LiveMessage.restore(context.user_data.get(STATUS_KEY))
    if live is not None:
        await live.finish(context.bot, final_note)
    for key in (STATUS_KEY, "sticker_count", "status_intro"):
        context.user_data.pop(key, None)


async def _owns_pack_or_deny(pack_name: str, user_id: int) -> bool:
    """True if user_id owns pack_name. Packs can only be managed (renamed,
    shared, or opened via the /mypacks menu) by their owner -- co-editors
    only ever get add access, and only through a valid share link.

    Async because it is a database round trip, and this runs on the first
    line of six different button handlers: doing it inline would stall every
    other user's update for the duration."""
    return await asyncio.to_thread(get_pack_owner, pack_name) == user_id


# ---------- /whomade ----------

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


# ---------- owner-only admin tools ----------

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



async def whois_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/whois <user_id> -- looks up a Telegram user's profile (name,
    username, bio) plus any packs of theirs on record, so a numeric id
    (e.g. from /whomade or the packs table) can be turned back into "which
    of my friends is this". Owner-only: this surfaces info about other
    people, not something every user should be able to query."""
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
    """/messageas <user_id> <text> -- sends a message to that user as this
    bot. Only works if the user has messaged the bot before (Telegram
    doesn't let bots cold-message anyone). Owner-only for obvious reasons."""
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
    """/dbdump -- exports every table in this bot's own database as one
    zip of CSVs. Owner-only: this is the whole user table, not something to
    hand out on request."""
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
    """/status -- uptime, hosting environment, any crashes since this
    process started, and active-user counts. Owner-only, same reasoning as
    /dbdump: this is operational info, not something every user should see."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    now = datetime.now(timezone.utc)
    users_hour = await asyncio.to_thread(count_active_users_since, now - timedelta(hours=1))
    users_since_start = await asyncio.to_thread(count_active_users_since, START_TIME)
    await update.message.reply_text(build_status_text(START_TIME, users_hour, users_since_start))


async def crashtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/crashtest -- owner-only, deliberately raises so you can confirm
    /status's error tracking + logs/errors.log actually catch something
    without needing a real bug. PTB's own dispatcher catches whatever this
    raises and routes it to error_handler (shared_features.py) -- polling
    keeps running either way. Safe to leave in permanently (gated same as
    every other admin command), or ask to have it removed once you're done
    testing."""
    if not _is_admin(update.effective_user.id):
        return await _deny(update, context)
    raise RuntimeError("Manual /crashtest trigger -- error tracking is working as intended.")


# ---------- /start and menu buttons ----------

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

    A deep link (/start s_<token>, a co-edit invite) still goes straight
    where it points, and a brand-new user who arrives on one picks a
    language first and is carried there afterwards by pending_start_args.
    """
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    if context.args:
        if lang is None:
            context.user_data["pending_start_args"] = context.args
            await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
            return ConversationHandler.END
        context.user_data["lang"] = lang
        return await _continue_start(update, context, lang, context.args)

    # A bare /start abandons any half-finished pack session, exactly as it
    # always has -- it is registered as a conversation fallback for that
    # reason -- so tear that session status message down with it rather than
    # leaving one dangling above a fresh greeting. Before the language gate
    # below, not after it: a user who never picked a language is served in
    # English (i18n.get_lang) rather than turned away, so they can be in the
    # middle of a pack when this arrives.
    if _has_status(context):
        await _end_status(context, i18n.t(lang or "en", "cancelled_status_note"))
    context.user_data.clear()

    if lang is None:
        await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard())
        return ConversationHandler.END

    context.user_data["lang"] = lang
    return await _continue_start(update, context, lang, None)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/language -- the picker on demand, which is what /start used to be.

    Same trilingual greeting and same three buttons, with a tick on the
    language in force so a returning user can see which one they are on
    before deciding to change it. The tap that follows runs through
    _apply_language like /en, /uz and /rus do, and so ends where they end:
    at the instructions, in the language just chosen.

    Deliberately *not* a conversation entry point. Asking to see the picker
    is not a reason to tear down a pack someone is halfway through editing;
    the tap that actually changes language is an entry point, because the
    instructions it prints have to leave the state machine at the top level.
    """
    lang = await asyncio.to_thread(get_user_language, update.effective_user.id)
    # Keep the cached language warm even though the picker itself is
    # trilingual -- the next handler this user hits would otherwise pay for
    # a database read that /language had already done.
    if lang:
        context.user_data["lang"] = lang
    await update.message.reply_text(i18n.LANGUAGE_PROMPT, reply_markup=language_keyboard(lang))


async def _continue_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, args):
    if args and args[0].startswith("s_"):
        return await start_coedit_link(update, context, args[0][2:], lang)

    await reply(update, build_start_text(lang), reply_markup=start_menu_keyboard(lang))
    return ConversationHandler.END


async def _apply_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """The single path every language change goes through -- /en, /uz, /rus
    and a tap on the picker alike. Two things all of them have to do, which
    is why they share this:

    1. Show the instructions. Answering a language change with nothing but
       "Language set" leaves someone looking at a bot whose manual they have
       just made themselves unable to reach; printing the full help in the
       language they picked is the point of having picked it.
    2. Leave the user at the top level. This used to strand people: change
       language halfway through /newpack and the pack-editing conversation
       stayed open behind the start menu that appeared, so /newpack got
       "I don't recognize that command" and the New pack button did nothing
       at all. Clearing user_data and returning END puts the state machine
       where the screen says it is.

    pending_start_args is read back before the clear so a brand-new user who
    arrived on a co-edit link still lands in that pack once they have picked
    a language.
    """
    await asyncio.to_thread(set_user_language, update.effective_user.id, lang)
    pending = context.user_data.get("pending_start_args") or []
    if _has_status(context):
        await _end_status(context, i18n.t(lang, "cancelled_status_note"))
    context.user_data.clear()
    context.user_data["lang"] = lang
    # The menu follows the choice too -- Telegram otherwise shows it in the
    # language of the phone. After the clear, so the signature survives it.
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
    """A tap on the picker. Registered as a conversation entry point as well
    as a plain handler, because the very first thing a brand-new user does
    can be opening someone's co-edit link -- and that has to be able to put
    them straight into an editing session. Being an entry point is also what
    lets the END _apply_language returns actually close a conversation the
    tap interrupted: a plain handler's return value is thrown away."""
    query = update.callback_query
    lang = query.data.split(":", 1)[1]
    await query.answer(i18n.t(lang, "language_set_confirmation"))
    return await _apply_language(update, context, lang)


async def menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'⬅️ Back' from deeper in the menu -- edits back to the start view
    instead of leaving a trail of old menu messages behind."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.callback_query.answer()
    await edit_in_place(update.callback_query.message, context.bot, build_start_text(lang), reply_markup=start_menu_keyboard(lang))


async def start_coedit_link(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, lang: str):
    """Handles /start s_<token> -- someone opening a co-edit share link.

    Replies through reply() rather than update.message, because a first-time
    user reaches this by tapping a language button, and a button tap has no
    message of its own to reply to."""
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

    context.user_data.clear()
    context.user_data["lang"] = lang
    context.user_data["mode"] = "add"
    context.user_data["pack_created"] = True
    context.user_data["target_pack"] = pack_name
    context.user_data["owner_id"] = owner_id

    intro = i18n.t(lang, "coedit_joined_intro", title=title)
    await _start_status(context, update.effective_chat.id, title, lang, intro=intro)
    return EDITING


async def menu_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data="menu_start")]])
    await edit_in_place(update.callback_query.message, context.bot, build_help_text(lang), reply_markup=kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data="menu_start")]])
    await update.message.reply_text(build_help_text(lang), reply_markup=kb)


async def menu_mypacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await show_packs(update, context)


async def mypacks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_packs(update, context)


async def show_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    user_id = update.effective_user.id
    packs = await asyncio.to_thread(get_user_packs, user_id)
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


# ---------- pack detail menu (Add / Rename / Co-edit) ----------

async def pack_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "not_your_pack"), show_alert=True)
        return
    await query.answer()

    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    await edit_in_place(query.message, context.bot, 
        i18n.t(lang, "pack_detail_title", title=title), reply_markup=pack_detail_keyboard(pack_name, lang)
    )


# ---------- co-editing menu ----------

async def _send_coedit_message(message, bot, pack_name: str, lang: str):
    # One trip to the database for all three values -- this used to be a
    # token read, a title read and an editor count, each with its own
    # round trip, to render a single message.
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
            [InlineKeyboardButton(i18n.t(lang, "btn_reset_link"), callback_data=f"cotoken_reset:{pack_name}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_back"), callback_data=f"packopen:{pack_name}")],
        ]
    )
    await edit_in_place(message, bot, text, reply_markup=kb)


async def coedit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_coedit"), show_alert=True)
        return
    await query.answer()
    await _send_coedit_message(query.message, context.bot, pack_name, lang)


async def coedit_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_coedit"), show_alert=True)
        return

    await asyncio.to_thread(reset_share_token, pack_name)
    await query.answer(i18n.t(lang, "link_reset_confirm"))
    await _send_coedit_message(query.message, context.bot, pack_name, lang)


# ---------- rename ----------

async def rename_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_rename"), show_alert=True)
        return ConversationHandler.END

    await query.answer()
    context.user_data.clear()
    context.user_data["lang"] = lang
    context.user_data["rename_pack"] = pack_name
    # The new title arrives as a plain text message, not a button tap --
    # stashing this prompt's handle lets receive_new_title turn it into the
    # result instead of sending a separate reply. By then the user's own
    # title message is underneath it, so the handle will (correctly) send a
    # new message rather than rewrite one they have already scrolled past.
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
    new_title = update.message.text.strip()[:64]  # Telegram title limit
    if not pack_name or prompt is None:
        await update.message.reply_text(i18n.t(lang, "rename_broken_state"))
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([[InlineKeyboardButton(i18n.t(lang, "btn_back_to_pack"), callback_data=f"packopen:{pack_name}")]])
    try:
        await context.bot.set_sticker_set_title(name=pack_name, title=new_title)
        await asyncio.to_thread(set_pack_title, pack_name, new_title)
        await prompt.finish(context.bot, i18n.t(lang, "renamed_success", title=new_title), reply_markup=kb)
    except Exception as exc:
        logger.exception("Rename failed")
        await prompt.finish(context.bot, i18n.t(lang, "renamed_failed", error=exc), reply_markup=kb)

    context.user_data.clear()
    return ConversationHandler.END


# ---------- delete pack (owner-only, two taps to confirm) ----------

async def delete_pack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """First tap of 'Delete pack' -- owner-only (co-editors never even see
    this button, since it only appears in the /mypacks detail menu, but the
    check is repeated here too since callback_data can be replayed)."""
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_delete"), show_alert=True)
        return
    await query.answer()

    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(i18n.t(lang, "btn_delete"), callback_data=f"packdelconfirm1:{pack_name}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_cancel_inline"), callback_data=f"packopen:{pack_name}")],
        ]
    )
    await edit_in_place(query.message, context.bot, 
        i18n.t(lang, "delete_confirm1", title=title),
        reply_markup=kb,
    )


async def delete_pack_confirm1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Second tap -- one more explicit confirmation before anything actually happens."""
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not await _owns_pack_or_deny(pack_name, user.id):
        await query.answer(i18n.t(lang, "only_owner_delete"), show_alert=True)
        return
    await query.answer()

    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(i18n.t(lang, "btn_delete_confirm"), callback_data=f"packdelconfirm2:{pack_name}")],
            [InlineKeyboardButton(i18n.t(lang, "btn_cancel_inline"), callback_data=f"packopen:{pack_name}")],
        ]
    )
    await edit_in_place(query.message, context.bot, 
        i18n.t(lang, "delete_confirm2", title=title),
        reply_markup=kb,
    )


async def delete_pack_confirm2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Third tap -- actually deletes the set from Telegram and wipes local records."""
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    if not _owns_pack_or_deny(pack_name, user.id):
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
        # Telegram already has no record of it (e.g. auto-deleted earlier
        # after its last sticker was removed) -- just clean up our side.

    await asyncio.to_thread(delete_pack_records, pack_name)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(i18n.t(lang, "btn_my_packs_back"), callback_data="menu_mypacks")]])
    await edit_in_place(query.message, context.bot, i18n.t(lang, "delete_success", title=title), reply_markup=kb)


# ---------- /newpack (and "New pack" button) ----------

async def newpack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    context.user_data.clear()
    context.user_data["lang"] = lang
    context.user_data["mode"] = "new"
    context.user_data["pack_created"] = False
    context.user_data["owner_id"] = update.effective_user.id
    if update.callback_query:
        await update.callback_query.answer()
    msg = await reply(update, i18n.t(lang, "newpack_title_prompt"))
    # So receive_title can turn THIS message into the status display below,
    # instead of sending a separate one once the title arrives -- assuming
    # it is still the last thing in the chat by then, which is exactly what
    # the handle is for.
    context.user_data["title_prompt"] = msg.save()
    return TITLE


async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text(i18n.t(lang, "title_empty"))
        return TITLE
    if len(title) > 64:  # Telegram's hard limit on set titles
        title = title[:64]
        await update.message.reply_text(i18n.t(lang, "title_truncated", title=title))

    intro = i18n.t(lang, "editing_intro_new")
    prompt = context.user_data.pop("title_prompt", None)
    await _start_status(
        context, update.effective_chat.id, title, lang, intro=intro, adopt=prompt,
    )
    return EDITING


# ---------- /addsticker (and per-pack "Add" button) ----------

async def addsticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    user_id = update.effective_user.id
    packs = await asyncio.to_thread(get_user_packs, user_id)
    if not packs:
        await update.message.reply_text(i18n.t(lang, "no_packs_for_add"))
        return
    await update.message.reply_text(
        i18n.t(lang, "pick_pack_prompt"), reply_markup=packs_keyboard(packs, lang)
    )


async def pack_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pack_name = query.data.split(":", 1)[1]
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)

    owner_id = await asyncio.to_thread(get_pack_owner, pack_name)
    if owner_id != user.id:
        await query.answer(i18n.t(lang, "not_your_pack"), show_alert=True)
        return ConversationHandler.END
    await query.answer()

    context.user_data.clear()
    context.user_data["lang"] = lang
    context.user_data["mode"] = "add"
    context.user_data["pack_created"] = True
    context.user_data["target_pack"] = pack_name
    context.user_data["owner_id"] = owner_id

    intro = i18n.t(lang, "editing_intro_add")
    title = await asyncio.to_thread(get_pack_title, pack_name) or pack_name
    await _start_status(
        context, query.message.chat_id, title, lang,
        intro=intro, adopt=LiveMessage.adopt(query.message).save(),
    )
    return EDITING


# ---------- the editing loop ----------

async def _add_input_sticker(
    context: ContextTypes.DEFAULT_TYPE, user, input_sticker: InputSticker,
    want_file_id: bool = True,
) -> str | None:
    """Creates the pack (first sticker of a /newpack session) or adds to the
    existing target pack. Returns the newly-added sticker's file_id.

    Always acts on Telegram's behalf of the pack's *owner* (owner_id), even
    if a co-editor is the one physically sending the sticker through the
    bot -- Telegram's API ties set ownership to that id, not the caller.

    That file_id costs an extra getStickerSet call -- the API has no way to
    return it from the add itself -- and it exists only so the next message
    can retag the sticker with different emoji. During a bulk import nobody
    is going to retag sticker #37 of 100, so want_file_id=False skips a
    hundred round trips and the whole set is read once at the end instead.
    """
    owner_id = context.user_data["owner_id"]

    if not context.user_data.get("pack_created"):
        title = context.user_data["title"]
        # A random suffix (not the owner's Telegram user id) keeps the pack
        # name -- and therefore the public https://t.me/addstickers/... link
        # everyone sees -- from doubling as a permanent, unrevokable pointer
        # to the creator's numeric user id. Ownership is still tracked
        # server-side via add_pack()/get_pack_owner(), so nothing else here
        # depends on what's actually in the name.
        pack_name = f"{slugify(title)}_{secrets.token_hex(5)}_by_{BOT_USERNAME}"
        # Uploading a sticker (especially a converted video one) can take
        # longer than PTB's default 5s read/write timeout, which was
        # showing up as a spurious "Timed out" failure even when the
        # upload was going through fine -- just slowly.
        await context.bot.create_new_sticker_set(
            user_id=owner_id,
            name=pack_name,
            title=title,
            stickers=[input_sticker],
            read_timeout=60,
            write_timeout=60,
        )
        await asyncio.to_thread(
            add_pack, owner_id, pack_name, title, user.username, user.full_name
        )
        context.user_data["target_pack"] = pack_name
        context.user_data["pack_created"] = True
    else:
        pack_name = context.user_data["target_pack"]
        await context.bot.add_sticker_to_set(
            user_id=owner_id,
            name=pack_name,
            sticker=input_sticker,
            read_timeout=60,
            write_timeout=60,
        )

    if not want_file_id:
        return None
    sticker_set = await context.bot.get_sticker_set(pack_name)
    return sticker_set.stickers[-1].file_id


async def _remember_last_sticker(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run once after a bulk import so "send emoji to retag" still points at
    the last sticker added -- one getStickerSet instead of one per sticker."""
    pack_name = context.user_data.get("target_pack")
    if not pack_name:
        return
    try:
        sticker_set = await context.bot.get_sticker_set(pack_name)
        context.user_data["last_sticker_id"] = sticker_set.stickers[-1].file_id
    except Exception:
        logger.debug("Couldn't re-read the pack after a bulk import", exc_info=True)


async def _is_own_pack_sticker(context: ContextTypes.DEFAULT_TYPE, sticker) -> bool:
    """True if an incoming sticker message is a sticker that's still
    actually in the pack currently being edited (as opposed to a fresh
    image, or a sticker from some *other* pack, which still gets added
    normally).

    `sticker.set_name` alone isn't enough to decide this: it reflects
    whatever set the message's *sender* last saw the sticker belong to, and
    a sender's sticker panel can lag behind a removal the bot itself just
    made in this same session (e.g. remove it, then immediately re-send the
    same sticker from their panel before Telegram's client has refreshed
    it). Trusting set_name alone in that case would try to delete an
    already-deleted sticker and fail with STICKERSET_NOT_MODIFIED instead of
    doing what the user clearly wants: re-add it. So once set_name points at
    our pack, confirm against the pack's actual current contents."""
    target_pack = context.user_data.get("target_pack")
    if not target_pack or not sticker.set_name or sticker.set_name != target_pack:
        return False
    try:
        sticker_set = await context.bot.get_sticker_set(target_pack)
    except Exception:
        return True  # can't verify right now -- fall back to trusting set_name
    return any(s.file_unique_id == sticker.file_unique_id for s in sticker_set.stickers)


async def _remove_own_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE, sticker) -> int:
    """Handles the 'sent a sticker that's already in this pack' case by
    removing it instead of trying (and failing) to re-add it -- Telegram
    rejects re-adding a sticker to the exact set it already belongs to with
    an unhelpful STICKERSET_INVALID error, so this sidesteps that entirely.

    If it's the *last* sticker in the pack, removing it would make Telegram
    auto-delete the whole set (packs can't be empty) -- so that case asks
    for confirmation first instead of silently nuking the pack.
    """
    lang = await i18n.get_lang(update.effective_user.id, context)
    try:
        sticker_set = await context.bot.get_sticker_set(sticker.set_name)
    except Exception:
        sticker_set = None

    if sticker_set and len(sticker_set.stickers) <= 1:
        context.user_data["pending_removal"] = sticker.file_id
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(i18n.t(lang, "btn_delete_pack_yes"), callback_data="confirmremove:yes"),
                    InlineKeyboardButton(i18n.t(lang, "btn_cancel"), callback_data="confirmremove:no"),
                ]
            ]
        )
        await update.message.reply_text(
            i18n.t(lang, "remove_last_confirm"),
            reply_markup=kb,
        )
        return EDITING

    try:
        await context.bot.delete_sticker_from_set(sticker=sticker.file_id)
    except Exception as exc:
        logger.exception("Failed to delete sticker from set")
        record_error(exc)
        await update.message.reply_text(i18n.t(lang, "remove_failed", error=exc))
        return EDITING
    context.user_data["sticker_count"] = max(0, context.user_data.get("sticker_count", 0) - 1)
    await _refresh_status(context, lang)
    await update.message.reply_text(i18n.t(lang, "remove_success"))
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
        await asyncio.to_thread(delete_pack_records, target_pack)  # Telegram auto-deleted the empty set
    await edit_in_place(query.message, context.bot, i18n.t(lang, "pack_deleted_empty"))
    await _end_status(context, i18n.t(lang, "pack_deleted_note"))
    context.user_data.clear()
    return ConversationHandler.END


async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Static images / static stickers -> PNG sticker."""
    msg = update.message
    lang = await i18n.get_lang(update.effective_user.id, context)
    if msg.sticker and await _is_own_pack_sticker(context, msg.sticker):
        return await _remove_own_sticker(update, context, msg.sticker)

    if msg.photo:
        file_id = msg.photo[-1].file_id
    elif msg.document:
        file_id = msg.document.file_id
    elif msg.sticker:
        file_id = msg.sticker.file_id
    else:
        return EDITING

    tg_file = await context.bot.get_file(file_id)
    raw = await tg_file.download_as_bytearray()

    try:
        # Pillow decodes and resamples in-process; a phone photo is tens of
        # milliseconds of pure CPU, which on the event loop is every other
        # user's update waiting behind it.
        png_bytes = (await asyncio.to_thread(to_sticker_png, bytes(raw))).getvalue()
    except Exception as exc:
        record_error(exc)
        await msg.reply_text(i18n.t(lang, "image_process_failed", error=exc))
        return EDITING

    input_sticker = InputSticker(sticker=png_bytes, emoji_list=[DEFAULT_EMOJI], format="static")

    try:
        last_id = await _add_input_sticker(context, update.effective_user, input_sticker)
        context.user_data["last_sticker_id"] = last_id
        context.user_data["sticker_count"] = context.user_data.get("sticker_count", 0) + 1
        # The confirmation goes *into* the status message rather than under
        # it. A separate "added ✅" reply would sit below the status and push
        # it out of last place on every single sticker, which is the one
        # thing an evolving message cannot survive.
        await _refresh_status(context, lang, i18n.t(lang, "added_default_emoji", emoji=DEFAULT_EMOJI))
    except Exception as exc:
        logger.exception("Sticker set operation failed")
        record_error(exc)
        await _refresh_status(
            context, lang,
            _sticker_error_note(exc, lang),
        )

    return EDITING


async def receive_video_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GIFs / videos / video stickers -> WEBM video sticker (via ffmpeg)."""
    msg = update.message
    lang = await i18n.get_lang(update.effective_user.id, context)
    if msg.sticker and await _is_own_pack_sticker(context, msg.sticker):
        return await _remove_own_sticker(update, context, msg.sticker)

    if msg.animation:
        file_id = msg.animation.file_id
    elif msg.video:
        file_id = msg.video.file_id
    elif msg.document:
        file_id = msg.document.file_id
    elif msg.sticker:
        file_id = msg.sticker.file_id
    else:
        return EDITING

    # An encode takes longer than the platform's shutdown grace period, so
    # starting one into a landing update would only end in silence. Saying so
    # costs the user a few seconds; not saying so costs them the file.
    refusal = await refuse_new_work(lang, update.effective_user.id, msg.chat_id)
    if refusal:
        await msg.reply_text(refusal)
        return EDITING

    tg_file = await context.bot.get_file(file_id)
    raw = await tg_file.download_as_bytearray()

    # The status message *is* the progress message: one bot message per
    # action, always at the bottom of the chat, always current.
    await _refresh_status(context, lang, i18n.t(lang, "converting_video"))
    try:
        async with lifecycle.busy(msg.chat_id, i18n.t(lang, "restarting_send_again")):
            webm_bytes = await asyncio.to_thread(to_video_sticker_webm, bytes(raw), lang)
    except ConversionError as exc:
        # Couldn't hit the 256 KB video-sticker target -- the raw clip itself is
        # still fine, so point at @ConvertBot for a plain (non-sticker)
        # conversion instead of just dead-ending here. No file handoff between
        # bots anymore (each bot is fully independent) -- the user re-sends
        # the file over there themselves.
        record_error(exc)
        kb = InlineKeyboardMarkup([sibling_bots_keyboard_row(BOT_NAME, only="convertbot")])
        # The buttons need a message of their own -- an inline keyboard on
        # the status line would still be sitting there, live, several
        # stickers later. bump() then tells the status handle that something
        # has been sent underneath it (the watermark only watches the *user*,
        # which is right everywhere except here), so the refresh moves the
        # status down to the bottom instead of rewriting it above the
        # buttons.
        sent = await msg.reply_text(
            i18n.t(lang, "video_convert_failed_redirect", error=exc), reply_markup=kb,
        )
        live_message.bump(sent.chat_id, sent.message_id)
        await _refresh_status(context, lang)
        return EDITING
    except Exception as exc:
        logger.exception("Video conversion failed")
        record_error(exc)
        await _refresh_status(context, lang, i18n.t(lang, "video_convert_generic_failed", error=exc))
        return EDITING

    input_sticker = InputSticker(sticker=webm_bytes, emoji_list=[DEFAULT_EMOJI], format="video")

    try:
        last_id = await _add_input_sticker(context, update.effective_user, input_sticker)
        context.user_data["last_sticker_id"] = last_id
        context.user_data["sticker_count"] = context.user_data.get("sticker_count", 0) + 1
        await _refresh_status(context, lang, i18n.t(lang, "added_video_default_emoji", emoji=DEFAULT_EMOJI))
    except Exception as exc:
        logger.exception("Sticker set operation failed")
        record_error(exc)
        await _refresh_status(
            context, lang,
            _sticker_error_note(exc, lang),
        )

    return EDITING


async def reject_unsupported_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "animated_not_supported"))
    return EDITING


# ---------- bulk import (Telegram pack or WhatsApp zip) ----------

async def import_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/import <link or name> -- copies stickers from another public
    Telegram pack into the pack currently being edited. Re-uses each source
    sticker's file_id directly, so quality and emoji tags carry over as-is."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if not context.args:
        await update.message.reply_text(i18n.t(lang, "import_usage"))
        return EDITING

    source = " ".join(context.args)
    pack_source = parse_telegram_pack_source(source)
    if not pack_source:
        await update.message.reply_text(i18n.t(lang, "import_invalid_source"))
        return EDITING

    # A bulk import is the longest thing this bot does -- dozens of stickers
    # added one at a time, paced to stay under Telegram's rate limit -- and it
    # was the one long path with no check that an update was coming. Starting
    # one into a landing deploy leaves a half-filled pack and no explanation.
    refusal = await refuse_new_work(lang, update.effective_user.id, update.effective_chat.id)
    if refusal:
        await update.message.reply_text(refusal)
        return EDITING

    # Progress and result both land in the session's status message -- see
    # _start_status. A bulk import is the longest thing this bot does, so it
    # is also the one most likely to have the user typing over it; the
    # handle moves the whole report down to the bottom when they do.
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
                await asyncio.sleep(0.3)  # be gentle with Telegram's API during bulk adds
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
    """Same idea for /done. Both commands sit in Telegram's command menu, so
    both are one tap away at any moment, including when there is no editing
    session for them to act on -- answering that with "I don't recognize that
    command" is the bot disowning something it is itself advertising."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "done_standalone_hint"))


async def receive_whatsapp_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A .zip/.wastickers file sent while editing -- treated as a WhatsApp
    sticker pack export and bulk-imported."""
    msg = update.message
    lang = await i18n.get_lang(update.effective_user.id, context)

    # Same reasoning as /import, which this is the other half of: a zip of
    # stickers added one by one outlasts a shutdown grace period easily.
    refusal = await refuse_new_work(lang, update.effective_user.id, msg.chat_id)
    if refusal:
        await msg.reply_text(refusal)
        return EDITING

    tg_file = await context.bot.get_file(msg.document.file_id)
    raw = await tg_file.download_as_bytearray()

    await _refresh_status(context, lang, i18n.t(lang, "whatsapp_reading"))
    try:
        items = await asyncio.to_thread(parse_whatsapp_zip, bytes(raw), lang)
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


async def maybe_emoji_override(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = await i18n.get_lang(update.effective_user.id, context)

    if not looks_like_emoji_message(text):
        await update.message.reply_text(i18n.t(lang, "not_emoji_message"))
        return EDITING

    last_sticker_id = context.user_data.get("last_sticker_id")
    if not last_sticker_id:
        await update.message.reply_text(i18n.t(lang, "no_sticker_to_tag"))
        return EDITING

    emojis = split_emoji(text)
    try:
        await context.bot.set_sticker_emoji_list(sticker=last_sticker_id, emoji_list=emojis)
        await update.message.reply_text(i18n.t(lang, "retagged_success", emojis=" ".join(emojis)))
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

    # Finishing a pack is a natural "successful action" checkpoint -- see
    # shared_features.py for the cadence this is throttled to (not shown every time).
    nudge = await maybe_donation_nudge(
        update.effective_user.id, lang, context, update.effective_chat.id)
    if nudge:
        await update.message.reply_text(nudge)

    context.user_data.clear()
    return ConversationHandler.END


async def convert_redirect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/convert lives in @ConvertBot now -- keep the command here as a
    friendly redirect for anyone still typing it out of habit."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    kb = InlineKeyboardMarkup([sibling_bots_keyboard_row(BOT_NAME, only="convertbot")])
    await update.message.reply_text(
        i18n.t(lang, "convert_redirect"),
        reply_markup=kb,
    )


# The three pack states, as opposed to the donation prompt: cancelling one
# of these is what closes the ConversationHandler, and cancelling anything
# else must not.
PACK_CANCEL_KEYS = ("rename", "editing", "newpack")


async def _cancel_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> list[CancelItem]:
    """Everything this bot could be waiting on, named well enough to choose
    between. The three pack states are mutually exclusive by construction --
    newpack_start and rename_start both clear user_data before setting their
    own keys -- so at most one of them is ever on offer, and the real choice
    this menu exists for is "the pack, or the donation prompt, or both".
    """
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
    """Stop the chosen things; report what they were and whether a pack went
    with them.

    That second answer is what decides whether the conversation ends, and it
    is the whole reason this is not one indiscriminate reset any more:
    cancelling a donation prompt has no business closing an editing session
    the user never mentioned. The reset that a pack cancellation does still
    need is given back anything not chosen -- in practice the donation
    prompt, the only other thing that can be live at the same time.
    """
    items = {item.key: item for item in await _cancel_items(update, context, lang)}
    stopped, pack_stopped = [], False
    for chosen in keys:
        item = items.get(chosen)
        if item is None:
            continue
        if chosen == "editing":
            # The editing session owns the status message -- close that out
            # before the reset clears the keys _end_status finds it by.
            await _end_status(context, i18n.t(lang, "cancelled_status_note"))
        if chosen in PACK_CANCEL_KEYS:
            pack_stopped = True
            stopped.append(item.label)
        elif cancel_shared_item(context, lang, chosen):
            stopped.append(item.label)

    if pack_stopped:
        keep = {"lang": lang}
        if "donate_custom_currency" in context.user_data:
            keep["donate_custom_currency"] = context.user_data["donate_custom_currency"]
        reset_user_state(context, keep)
    return stopped, pack_stopped


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks which of the things it is waiting on to stop, and stops nothing
    until the answer comes back.

    "Cancelled." on its own used to leave you guessing which of several
    half-finished things it had caught; v0.7.0 fixed that by naming them
    afterwards. This is the other half: being asked first, so that a pack
    you are three stickers into is not collateral damage of wanting out of a
    donation prompt.

    Returns None while the question is on screen -- the conversation is still
    open at that point, and it is the button tap that ends it, if the answer
    turns out to be a pack. With nothing pending there is nothing to ask, so
    this answers immediately, exactly as it always has.
    """
    lang = await i18n.get_lang(update.effective_user.id, context)
    items = await _cancel_items(update, context, lang)
    if await ask_cancel_choice(update, context, items, lang):
        return None
    await finish_cancel(update, context, lang, [])
    return ConversationHandler.END


async def cancel_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on one of /cancel's buttons.

    Registered as a conversation entry point as well as a plain handler, for
    the same reason language_chosen is: a plain handler's return value is
    thrown away, and this one has to be able to close the conversation the
    /cancel it answers was sent from.
    """
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
    await finish_cancel_choice(update, context, lang, stopped)
    return ConversationHandler.END if pack_stopped else None


async def unrecognized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Only ever reached with no active /newpack or pack-editing session --
    while one's active, the conversation's own state handlers (e.g.
    maybe_emoji_override) claim the update first. Registered last, so
    every real handler above gets first shot."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "unrecognized"))


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(i18n.t(lang, "unknown_command"))


async def _post_init(application):
    await tune_runtime(application)
    # Before a single getUpdates goes out: if the container this one is
    # replacing is still polling, two processes would be splitting this
    # bot's updates between them and getting 409 Conflict for their trouble.
    await lifecycle.on_start(BOT_NAME)
    await publish_commands(application, BOT_COMMANDS, ADMIN_COMMANDS, ADMIN_IDS)
    await publish_profile(application)


async def _post_stop(application):
    # Order matters: lifecycle writes the in-progress state out, and
    # flush_on_shutdown closes the connection pool it writes through.
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
    # Open conversations and half-finished packs, in Postgres, so a redeploy
    # is not the end of somebody's editing session. None when it is switched
    # off or the database will not have it -- see lifecycle.py.
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
    # Before the handlers, because ConversationHandler(persistent=...) below
    # asks lifecycle whether persistence actually came up.
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
    # Runs after track_activity but before every other handler (ConversationHandler
    # included) -- a no-op unless a "Custom" donate button was just tapped, in
    # which case it consumes the reply and stops it from also being treated as,
    # e.g., a pack title (see donate_custom_amount_received's docstring).
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, donate_custom_amount_received), group=-1)

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("newpack", newpack_start),
            CallbackQueryHandler(newpack_start, pattern="^menu_newpack$"),
            CallbackQueryHandler(pack_chosen, pattern="^pack:"),
            CallbackQueryHandler(rename_start, pattern="^packrename:"),
            # The three language switches are entry points purely so that the
            # END they return is honoured. A handler registered only outside
            # the conversation has its return value discarded, which is how a
            # language change used to leave the state machine sitting in
            # TITLE/EDITING behind a start menu.
            CallbackQueryHandler(language_chosen, pattern="^setlang:"),
            # Same reasoning: /cancel's buttons have to be able to close the
            # session the /cancel that raised them was sent from.
            CallbackQueryHandler(cancel_choice_callback, pattern="^cancelpick:"),
            CommandHandler("en", set_language_en),
            CommandHandler("uz", set_language_uz),
            CommandHandler("rus", set_language_rus),
            # And /deletemydata, for the same reason and one more. Its END has
            # to be honoured, or an erase leaves the state machine in EDITING
            # holding a pack this bot has just been told to forget -- the next
            # sticker then fails on state that is gone. The command itself
            # returns None and moves nothing; only the confirmation ends it.
            CommandHandler("deletemydata", delete_my_data_command),
            CallbackQueryHandler(delete_my_data_chosen, pattern="^" + ERASE_PREFIX),
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            RENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_title)],
            EDITING: [
                CallbackQueryHandler(confirm_remove_last_sticker, pattern="^confirmremove:"),
                MessageHandler(
                    filters.Document.FileExtension("zip") | filters.Document.FileExtension("wastickers"),
                    receive_whatsapp_import,
                ),
                MessageHandler(
                    filters.PHOTO | filters.Document.IMAGE | filters.Sticker.STATIC,
                    receive_media,
                ),
                MessageHandler(
                    filters.ANIMATION | filters.VIDEO | filters.Document.VIDEO | filters.Sticker.VIDEO,
                    receive_video_media,
                ),
                MessageHandler(
                    filters.Sticker.ANIMATED,
                    reject_unsupported_sticker,
                ),
                CommandHandler("import", import_command),
                CommandHandler("done", done),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    maybe_emoji_override,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start)],
        # Named and persisted, so someone who was three stickers into a pack
        # when the bot was redeployed sends the fourth and it just works.
        name="stickerbot_pack_editing",
        persistent=lifecycle.persistent(),
        # Without this, entry points are ignored for as long as a conversation
        # is open, and every one of them is a dead end mid-session: /newpack
        # fell through to unknown_command ("I don't recognize that command")
        # and the New pack / Add stickers / Rename buttons did nothing at all
        # when tapped, with no feedback to say why. Re-entry restarts the flow
        # the user actually asked for, which is what tapping any of them means.
        allow_reentry=True,
    )

    app.add_handler(conv)
    # ---- language: /language for the picker, /en, /uz, /rus to switch
    # directly -- offered at the first /start, available anytime after.
    # Standalone (not part of the ConversationHandler above) so they still
    # work mid pack-editing session -- conv's per-state handlers don't match
    # a bare "/en" etc, so the update falls through to these. ----
    app.add_handler(CallbackQueryHandler(language_chosen, pattern="^setlang:"))
    app.add_handler(CallbackQueryHandler(cancel_choice_callback, pattern="^cancelpick:"))
    app.add_handler(CommandHandler("language", language_command))
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
    app.add_handler(CommandHandler("mypacks", mypacks_command))
    app.add_handler(CommandHandler("addsticker", addsticker_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("whomade", whomade_command))
    app.add_handler(CommandHandler("whois", whois_command))  # owner-only
    app.add_handler(CommandHandler("messageas", messageas_command))  # owner-only
    app.add_handler(CommandHandler("dbdump", dbdump_command))  # owner-only
    app.add_handler(CommandHandler("status", status_command))  # owner-only
    app.add_handler(CommandHandler("crashtest", crashtest_command))  # owner-only, for testing /status
    # Both only fire outside an active editing session -- inside one, the
    # conversation's own EDITING handlers claim them first.
    app.add_handler(CommandHandler("import", import_standalone))
    app.add_handler(CommandHandler("done", done_standalone))
    app.add_handler(CommandHandler("cancel", cancel_command))  # standalone fallback
    app.add_handler(CallbackQueryHandler(menu_mypacks, pattern="^menu_mypacks$"))
    app.add_handler(CallbackQueryHandler(menu_help, pattern="^menu_help$"))
    app.add_handler(CallbackQueryHandler(menu_start, pattern="^menu_start$"))
    app.add_handler(CallbackQueryHandler(pack_detail, pattern="^packopen:"))
    app.add_handler(CallbackQueryHandler(coedit_menu, pattern="^packcoedit:"))
    app.add_handler(CallbackQueryHandler(coedit_reset, pattern="^cotoken_reset:"))
    app.add_handler(CallbackQueryHandler(delete_pack_start, pattern="^packdel:"))
    app.add_handler(CallbackQueryHandler(delete_pack_confirm1, pattern="^packdelconfirm1:"))
    app.add_handler(CallbackQueryHandler(delete_pack_confirm2, pattern="^packdelconfirm2:"))
    app.add_handler(CommandHandler("convert", convert_redirect_command))  # points to @ConvertBot now

    # ---- donations (Telegram Stars) -- this bot's only Stars usage, so these
    # register directly with no payload-prefix branching needed ----
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CallbackQueryHandler(donate_amount_chosen, pattern="^donate:"))
    app.add_handler(CallbackQueryHandler(donate_fiat_amount_chosen, pattern="^donatefiat:"))
    app.add_handler(CallbackQueryHandler(donate_custom_button_chosen, pattern="^donatecustom:"))
    app.add_handler(PreCheckoutQueryHandler(donation_precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, donation_payment_callback))

    # Both registered last, so every real handler (and the conversation's
    # own in-state handlers) above gets first shot.
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unrecognized_message))

    # ManagerBot's link: heartbeats, crash/donation events, and the queue it
    # uses to run this bot's owner-only commands remotely. Never raises --
    # with no shared database reachable the bot just runs on its own.
    family_link.attach(app, BOT_NAME, "StickerBot", START_TIME)
    attach_maintenance(app)

    logger.info("Bot starting (polling)...")
    # A 30-second long poll instead of the default 10 is the same latency --
    # Telegram answers the moment an update exists -- for a third of the HTTP
    # requests, which on an idle bot is most of what it does all day. The
    # allowed_updates list is every kind this bot has a handler for; anything
    # else (edited messages, channel posts, reactions, chat member changes)
    # Telegram now stops sending at all rather than this process downloading
    # and parsing it only to drop it.
    # polling_kwargs() is what lets this process hear SIGTERM before
    # python-telegram-bot shuts it down, so a redeploy can tell anyone
    # mid-conversion what happened instead of leaving them waiting.
    # drop_pending_updates stays off (its default): updates sent while the
    # container was being replaced are still on Telegram's side, and this is
    # the poll that collects them.
    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY, Update.PRE_CHECKOUT_QUERY],
    ))

if __name__ == "__main__":
    main()
