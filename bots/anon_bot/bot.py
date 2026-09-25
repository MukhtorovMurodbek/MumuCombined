"""
AnonBot -- one-sided anonymous inbox, 4th bot in the family (see
ARCHITECTURE.md). Anyone can grab a permanent personal link (/link) and
post it somewhere public; anyone who taps it can send them anonymous
messages here without the owner seeing who they are. The owner's identity
is never hidden -- it's their own bot chat -- only the person asking is.

The two things this bot is built around (both explicitly requested):
  1. Every message either side sends says which conversation it answers, by
     being a real Telegram reply to a real message in that conversation --
     so with a dozen different people messaging the owner in the same chat,
     there is never any doubt about where an answer is going. Exactly one
     message is exempt: a guest's opening one, which has nothing above it to
     answer. Every incoming message carries a "Reply" button, which explains
     the gesture; it is not a second way of sending, and there is no way to
     send a message that names nothing.
  2. When the owner replies, it's delivered as a genuine Telegram reply on
     the follower's end too (quoting their own earlier message) -- so it
     visibly looks like a real back-and-forth, not a wall of disconnected
     bot messages. See anon_logic.relay_content() for how.

Tapping the SAME link again always starts a brand-new conversation (a fresh
conv_number, a fresh reply-chain anchor) -- it does not continue whatever
was last open with that owner.

Commands:
  /start, /help     - greeting + how it works (also handles /start q_<token>,
                       i.e. someone tapping a link)
  /link             - get your own permanent inbox link
  /newlink          - reset your link (invalidates the old one)
  /pause / /resume  - stop/resume NEW conversations (open ones keep working)
  /conversations    - list your own threads, revisit one from its start,
                       archive the ones you're done with
  /which            - sent as a reply: which conversation is that message in
  /blocked          - review + undo who you've blocked
  /stats            - quick counts for your own inbox
  /donate           - support hosting costs (voluntary)
  /en, /uz, /rus    - switch language (English/Uzbek/Russian); also asked
                       once, trilingually, on first /start

Requires: python-telegram-bot[job-queue]>=21.3, python-dotenv>=1.0
Env vars: ABOT_TOKEN, ABOT_USERNAME (no @), ABOT_ADMIN_ID (optional,
          comma-separated, gates /messageas, /dbdump and /status),
          DATABASE_URL and DB_SCHEMA (the shared family database, and this
          bot's schema in it), SIBLING_BOTS (see shared_features.py)
"""
import asyncio
import html
import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

try:  # optional convenience: load env vars from a local .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import (
    BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
    LinkPreviewOptions, Update,
)

# The inbox link is sent as a plain, tappable link rather than as a code
# block, so it reads and shares like a link -- but Telegram turns the first
# link in a message into a preview card, and a preview of this bot's own
# start page under a two-line message with buttons is noise. Every message
# carrying an inbox link opts out.
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
    PreCheckoutQueryHandler,
    TypeHandler,
    filters,
)

import family_link
import i18n
import lifecycle
import live_message
import transcript
from live_message import LiveMessage, edit_in_place
from anon_logic import (
    message_allowed,
    new_conversation_allowed,
    relay_content,
)
from db import (
    CONVERSATIONS_PER_PAGE,
    RELAY_RETENTION_DAYS,
    clear_follower_state,
    count_owner_conversation_states,
    first_relay_message,
    get_active_conversation_for_follower,
    get_anon_link_state,
    get_anon_stats,
    get_conversation,
    get_conversation_for_relay,
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
    list_exportable_conversations,
    conversation_messages,
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
    donate_custom_amount_received,
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
BOT_USERNAME = os.environ.get("ABOT_USERNAME")  # no @
BOT_NAME = "anonbot"  # this bot's id within SIBLING_BOTS

# Owner-only admin tools (/messageas, /dbdump, /status) -- comma-separated
# Telegram user ids. Empty/unset means disabled for everyone.
ADMIN_IDS = {int(x) for x in os.environ.get("ABOT_ADMIN_ID", "").split(",") if x.strip()}

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



async def _reply(update: Update, text: str, **kwargs):
    """Works whether this came from a command or a button tap -- the first-run
    language picker means a brand-new user can reach any of these paths from
    a callback query, which has no message of its own to reply to.

    The button path evolves the tapped message in place, but only while it is
    still the last thing in the chat; once the user has typed anything since,
    a rewrite would land above their own message and out of sight, so a new
    message is sent instead. See live_message.py."""
    if update.message:
        return await LiveMessage.reply_to(update.message, text, **kwargs)
    return await edit_in_place(update.callback_query.message, update.get_bot(), text, **kwargs)


def build_help_text(lang: str) -> str:
    return i18n.t(lang, "help_text") + sibling_bots_blurb(BOT_NAME, lang)


# Public command menu (the "/" button in Telegram's chat UI) -- set on
# startup via set_my_commands() below instead of pasting into @BotFather by
# hand. The owner-only /dbdump is deliberately left off. Language-switch
# commands are described in the language they switch to (self-explanatory
# by script/language, since Telegram's command menu itself isn't per-user).
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
    # /newlink, /pause, /resume and /stats are gone from here and still work.
    # The /link screen has been showing New link and Pause/Resume as buttons
    # since v1.1, and now carries the counts /stats printed -- so four menu
    # entries pointed at things already on one screen. /pause and /resume were
    # the worst of them: the same two words mean "stop the bots for an update"
    # in ManagerBot, which is a different thing entirely.
    #
    # /archive is gone and still works. It files the conversation you are
    # replying to, and /conversations has an Archive button on every row.
    BotCommand("start", "What I do, and how to start"),
    BotCommand("language", "Choose your language / Tilni tanlash / Выбрать язык"),
    BotCommand("link", "Your inbox link, and its settings"),
    BotCommand("conversations", "Your conversations"),
    BotCommand("which", "Which conversation is this? — reply to a message"),
    BotCommand("blocked", "Who you have blocked"),
    BotCommand("export", "Get a conversation back"),
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
    """Under a message arriving in the GUEST's chat. Reply only -- blocking
    is the inbox owner's tool, and a guest who wants out just stops
    answering."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(i18n.t(lang, "reply_button"), callback_data=f"aq_reply:{conversation_id}")]]
    )


# ---------- /start (also handles someone tapping an inbox link: /start q_<token>) ----------

async def _continue_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, args):
    if args and args[0].startswith("q_"):
        return await start_follow_link(update, context, args[0][2:], lang)

    kb = sibling_bots_keyboard_row(BOT_NAME)
    await _reply(
        update,
        i18n.t(lang, "start_greeting") + build_help_text(lang),
        reply_markup=InlineKeyboardMarkup([kb]) if kb else None,
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

    A deep link (/start q_<token>, someone opening an inbox link) still goes
    straight to that inbox, and a brand-new user who arrives on one picks a
    language first and is carried there afterwards by pending_start_args.
    """
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


async def _apply_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """The single path every language change goes through -- /en, /uz, /rus
    and a tap on the picker alike -- so all four end the same way: with the
    instructions, printed in the language just chosen.

    Answering a language change with nothing but "Language set" (which is all
    /en, /uz and /rus used to do for anyone who was not brand new) leaves
    someone looking at a bot whose manual they have just made themselves
    unable to reach. pending_start_args carries a brand-new user who arrived
    on an inbox link through to that inbox once they have picked.
    """
    await asyncio.to_thread(set_user_language, update.effective_user.id, lang)
    context.user_data["lang"] = lang
    # The menu follows the choice too -- Telegram otherwise shows it in the
    # language of the phone.
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
    """A tap on the picker. Carries any pending /start q_<token> through, so
    someone whose very first action was opening a link lands in the
    conversation it points at rather than back at the greeting."""
    query = update.callback_query
    lang = query.data.split(":", 1)[1]
    await query.answer(i18n.t(lang, "language_set_confirmation"))
    await _apply_language(update, context, lang)


async def start_follow_link(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, lang: str):
    follower = update.effective_user
    # One query for "who owns this token, are they paused, and have they
    # blocked me" -- it used to be three, run one after the other.
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

    # Opening a conversation writes rows the owner is then notified about,
    # and it is one tap to do. A short cooldown is the difference between a
    # misfire and somebody filling an inbox with empty threads.
    wait = new_conversation_allowed(follower.id)
    if wait:
        await _reply(update, i18n.t(lang, "too_fast", seconds=wait))
        return

    # An update the owner has announced can span several deploys, and a
    # conversation opened into one starts a thread the database may be in the
    # middle of migrating underneath. Being told to come back in ten minutes,
    # once, beats finding out afterwards -- and refuse_new_work writes this
    # person down so /finishupdates goes back to them.
    refusal = await refuse_new_work(lang, follower.id, update.effective_chat.id)
    if refusal:
        await _reply(update, refusal)
        return

    conv = await asyncio.to_thread(start_new_anon_conversation, owner_id, follower.id)
    # Sent rather than edited in place, because this bubble is the
    # conversation's permanent anchor -- the thing every swipe in this thread
    # eventually points back at -- and a brand-new user who arrives on a deep
    # link reaches here from a button tap, where _reply would have rewritten
    # the language picker into it instead of leaving something of its own.
    #
    # It used to carry a ForceReply, so that the guest's first message was a
    # real reply to it without their having to know that. That made the
    # opening message arrive by the same route as every other message, with
    # the exemption below as a fallback. The ForceReply is gone -- see the
    # reply requirement further down -- so the exemption is now the ordinary
    # path for an opening message rather than the fallback for one, which is
    # why it is worth being exact about: see handle_message step 2.
    #
    # What has not changed, and is what keeps this recoverable, is the relay
    # row registered just below. Whatever else happens in this chat, this
    # bubble stays a valid thing to reply to, so a guest who loses the
    # exemption can always swipe it and open the conversation that way.
    opening = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        # No conv_number here either -- the string stopped using it in
        # v1.4.0 and the argument was left behind, which is how a number
        # that is not supposed to reach a guest stays one edit away from
        # doing so again.
        text=i18n.t(lang, "follow_link_started"),
    )
    live_message.bump(opening.chat_id, opening.message_id)
    # Registered as a relay target so the guest's *first* message has
    # something to reply to. Every later message in this chat is a real
    # message from the owner; this one stands in for them until then. Not
    # marked as a prompt: a prompt is scaffolding that is deleted once
    # answered, and this is the opposite -- it is what the thread hangs on.
    await asyncio.to_thread(
        record_anon_relays, follower.id, [opening.message_id], conv["id"]
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await i18n.get_lang(update.effective_user.id, context)
    await update.message.reply_text(build_help_text(lang))


# ---------- owner: inbox link management ----------

def _link_message(token: str, paused: bool, lang: str, note: str = "",
                  stats: "dict | None" = None) -> tuple[str, InlineKeyboardMarkup]:
    """Shared by /link and its Pause/Resume/New-link buttons, so tapping
    one edits the same message back into an up-to-date version of itself
    instead of you needing to type /pause, /resume, or /newlink by hand.

    Since 1.7.0 it also carries the two counts /stats printed. They are about
    this link -- how many people have used it, and how many threads came out
    of that -- so the page about the link is where somebody looks for them,
    and /stats was a menu entry for two numbers."""
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
    # A new link does not un-pause the inbox, and the screen has to keep
    # saying so -- the paused flag comes back from the same statement rather
    # than costing a second query.
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
    await asyncio.to_thread(get_or_create_anon_link, owner.id)  # idempotent
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
    """/dbdump -- exports every table in this bot's own database as one
    zip of CSVs. Owner-only: this is every user's data, not something to
    hand out on request."""
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


async def _blocked_list_text_and_kb(owner_id: int, lang: str):
    rows = await asyncio.to_thread(list_anon_blocks_with_conversations, owner_id)
    if not rows:
        return i18n.t(lang, "blocked_none"), None
    lines = [i18n.t(lang, "blocked_header")]
    kb = []
    for conversation_id, conv_numbers in rows:
        # Conversation numbers instead of a pseudonym: the owner has seen
        # these in their own chat, and unlike a stable hash they say nothing
        # about the guest beyond "we spoke, in this thread".
        #
        # The button is addressed by conversation id, never by the guest's
        # Telegram user id. Callback data travels to the client as part of
        # the keyboard, so a user id in it is a user id published -- see
        # list_anon_blocks_with_conversations.
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


# ---------- /conversations: the owner's own list of their own threads ----------
# One chat holds every conversation an inbox has, interleaved, and until now
# the only way to see what was in there was to scroll. Three questions this
# answers, in order of how often they are asked: how many am I actually in,
# where does this one start, and which of these am I done with.
#
# It is a list, a card and one action, in that order, editing a single
# message in place. The alternative -- every conversation drawn as a line of
# text with its own row of buttons underneath -- puts twenty-odd buttons in
# somebody's chat and still has nowhere to say anything about one thread.

CONVS_PREFIX = "aq_convs:"      # <archived 0|1>:<page>
CONV_CARD_PREFIX = "aq_conv:"   # <conversation id>:<archived 0|1>:<page>
CONV_ARCH_PREFIX = "aq_arch:"   # <conversation id>:<archive 0|1>:<archived 0|1>:<page>
CONV_JUMP_PREFIX = "aq_jump:"   # <conversation id>


def _ago(lang: str, when: str | None) -> str:
    """How long ago, in whole units, with no date and no clock time in it.

    Every timestamp in this schema is an ISO string in UTC and the bot has no
    idea which timezone the person reading is in, so a clock time would be
    wrong for nearly everybody and a date needs month names in three
    languages. "3 h ago" needs neither, and is the question being asked.
    """
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
    """The list message: what it says and what is under it.

    The conversations themselves are buttons rather than lines of text.
    Every one of them is something to tap, and printing each as a line and
    then repeating it as a button says the same thing twice in a chat that
    is mostly somebody else's words already.
    """
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
    """One conversation, and the two things that can be done to it from
    here. Blocking is deliberately not one of them: it is available under
    every message the guest has sent, and a list is the wrong place to put
    an action a mis-tap cannot take back."""
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
    """The conversation a card button names, if it is this user's to act on.

    Every button below is drawn only in the owner's own chat, so a tap
    naming somebody else's conversation is either a stale keyboard or a
    crafted one. Both get the same answer, which says nothing about whether
    the conversation exists.
    """
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
    """Page turns and the Open/Archived switch, both of which are just
    "draw the list again with different arguments"."""
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
    """Filing, and nothing more. Nothing is refused because a conversation
    is archived and the guest is never told -- an archived thread that
    somebody writes into comes straight back, which is what makes this safe
    to press on a thread that only looks finished."""
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


# /archive -- the same filing /conversations does, without the walk to it.
#
# Archiving already existed, but only as a button on a conversation's card
# inside /conversations: open the list, page to the thread, open its card,
# press Archive. Four steps to file the thread whose message is already on
# screen. Replying to that message and sending /archive is one, and the
# backend is the same call.
#
# It asks first. Every other action in this bot is reversible in place and
# this one is too -- an archived thread comes straight back the moment
# anything is relayed into it -- but a command typed under a message is much
# easier to aim at the wrong message than a button on a card that names the
# conversation, so the confirmation is where the naming happens.
ARCH_CMD_PREFIX = "aq_archcmd:"     # <conversation id>:<archive 0|1>


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
    # A guest has no list to file anything out of: conv_number is the owner's
    # index for their own inbox, and archiving is an operation on that index.
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
    """The answer to that question. Re-reads the conversation rather than
    trusting the button: it may have been on screen a while, and the thread
    could have been archived from /conversations in the meantime."""
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
    """A message pointing at an older one, and a relay row saying which
    conversation it belongs to.

    Tapping the quote is what scrolls to the older message: a private chat
    with a bot has no message links -- t.me/c/... is supergroups and
    channels -- so a reply-quote is the only way to point at something
    further up.

    Registering it as a relay row is deliberate, and it is not a hole in the
    reply rule. The rule is that a message has to say which conversation it
    answers by being a Telegram reply to a message in that conversation;
    this is a message in exactly one conversation, so replying to it says
    that. It is the same thing the line announcing a new conversation has
    always been. What it adds is a way into a thread without having to find
    a message from it first.

    If the anchor has since been deleted Telegram refuses the whole send, so
    this retries without it -- the same shape relay_content uses. A bookmark
    with no quote is worth less, but it still names the conversation and is
    still a valid thing to reply into.
    """
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
        # Everything from this conversation has been pruned, so there is
        # nothing left in the chat to point at -- and nothing left to reply
        # to either, which is why prune_old_data archives it at the same
        # time. Saying so beats pointing somewhere else.
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
    """/which, sent as a reply: which conversation is that message in?

    Every message this bot delivers already carries a "Conversation #N"
    header. What it cannot label is the rest of what is in the chat -- the
    owner's own outgoing bubbles, the second and third photo of an album,
    the later bubbles of a message too long for one -- and this answers for
    any of them, because it asks anon_relay rather than reading the screen.

    The owner is told the number. A guest is not: conv_number is the
    owner's index for their own inbox, so "#3" in a guest's chat means
    "this owner's third correspondent", which is meaningless to them and is
    a fact about somebody else. They are pointed at that conversation's own
    opening line instead, which identifies it without labelling it.
    """
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
        # `reply_stale` used to answer here, and it ends "your message was not
        # sent" -- which is a confusing thing to read after asking a question.
        # /which sends nothing and can fail for its own reason, so it says so
        # in its own words.
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


# ---------- the Reply / Block buttons under an incoming message ----------

def _callback_ints(query, count: int) -> "list[int] | None":
    """The `count` numeric fields after the prefix in a button's
    callback_data, or None if they are not all there and not all numbers.

    Every one of these buttons was drawn by this bot, so in ordinary use the
    tail is always numbers. Callback data is still client-supplied: a
    crafted client can send `aq_reply:notanumber` against any message it can
    see, and int() on that raised straight through the handler into the error
    handler -- which reports a crash to ManagerBot. That turns a malformed
    string anybody can send into a way to page the owner at will. Refusing
    it here answers the tap the same way an id for somebody else's
    conversation is answered, and stays out of the crash log.
    """
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
    """Works for whichever side tapped it. Both chats now carry relay rows,
    so a conversation has two legitimate participants and the only question
    is whether this user is one of them."""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = await i18n.get_lang(user_id, context)
    conversation_id = _conversation_arg(query)
    conv = (await asyncio.to_thread(get_conversation, conversation_id)
            if conversation_id is not None else None)
    if not conv or user_id not in (conv["owner_user_id"], conv["follower_user_id"]):
        await query.answer(i18n.t(lang, "not_your_conversation"), show_alert=True)
        return

    # This button used to send a prompt carrying a ForceReply, which aimed the
    # reply box at the right conversation for you. That was the second of the
    # two routes into a conversation, and the two of them together are what
    # made this bot's routing hard to be sure about -- so there is one route
    # now, and it is the one Telegram already gives everybody: reply to the
    # message.
    #
    # The button stays, and says how. It cannot aim the reply box itself --
    # nothing except ForceReply can, and ForceReply can only aim at a message
    # the bot is sending right now, never at an earlier one -- so what is left
    # for it to do is teach the gesture once to whoever has not met it. That
    # is worth a button: the alternative is a rule with no visible way to obey
    # it, which is the shape of every bot people give up on.
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
    # One tap, one answer. This used to fire the toast AND send a separate
    # "Conversation #N is blocked" message underneath -- two notifications
    # for one deliberate action, in a chat this bot already writes into more
    # than it needs to. The toast says it happened; the button now says it is
    # still true, which is the part the owner comes back and looks for.
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
    """The /blocked list's own Undo. Addressed by conversation, and the guest
    behind it is looked up here rather than carried in the button."""
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


# ---------- the reply requirement ----------
# Every message either side sends has to say which conversation it answers, by
# being a real Telegram reply to a real message in that conversation. One
# message is exempt and only one: a guest's opening message, which has nothing
# above it to answer.
#
# There used to be a way past it. A message that named nothing was HELD -- the
# whole message, text and all, parked in user_data -- and offered back with a
# "Send it anyway" button. It was written to spare somebody a swipe, and it
# cost more than it saved:
#
#   It stored what people wrote. user_data is persisted to Postgres by
#   lifecycle.PostgresPersistence, so the held message's text went into the
#   database and sat there until the button was tapped or the row expired.
#   Every version of this bot's privacy notice says message content is never
#   stored. That sentence was not true while this existed, and no amount of
#   "only briefly" makes a stored message unstored.
#
#   It was a second router. The button guessed a destination -- the one
#   conversation the message could unambiguously have had -- which is the
#   guess the reply requirement exists to prevent, made by a button instead
#   of by the router.
#
# So there is no way past it now. A message that names nothing is refused, and
# refused is all: nothing is sent, nothing is kept, and the person is told
# which message to reply to instead of being told merely that they must.
#
# Pointing at it is the whole difference between a rule and an obstacle, which
# is why the refusal is sent AS a reply to the message it is asking about --
# see active_anchor in db.get_routing_context.

async def _refuse_unaddressed(update, context, lang: str, routing: dict) -> None:
    """Say which message to reply to. Send nothing, keep nothing."""
    active, owned = routing["active"], routing["owned"]
    anchor = routing.get("active_anchor")

    if active and not owned:
        # One possible destination, so the refusal can name it and point at
        # it. Whether the conversation has been opened yet changes what the
        # person is being asked for: their first message, or an answer.
        # No conversation number in either: conv_number is the OWNER's index
        # for their own inbox, so a guest with two conversations open has two
        # of them both called #1. It is the right label for the owner and a
        # misleading one for a guest, who never needs to name a conversation
        # anyway -- they name it by replying to it.
        opening = active.get("follower_first_msg_at") is None
        text = i18n.t(lang, "must_reply_opening" if opening else "must_reply")
    else:
        # An inbox of their own, with or without a session of their own open:
        # several people could be on the other end, and naming one would be
        # the guess this rule exists to stop.
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
            # The message it wanted to point at has been deleted. Quoting the
            # person's own message still says which one did not go.
            pass
    await update.message.reply_text(text, do_quote=True)


# ---------- the actual message routing: owner replies vs. follower questions ----------

# An album is several updates, not one. Telegram sends each photo of a media
# group as its own message with a shared media_group_id, so a three-photo
# album used to arrive as three headed bubbles, three Reply/Block rows and
# three "Sent" confirmations. The first part of a group says all of that; the
# rest ride in quietly underneath it. Kept in memory and only for a moment,
# because that is exactly how long the parts take to arrive.
_ALBUM_WINDOW = 20  # seconds
# media_group_id -> (conversation_id, when the first part was seen)
_albums: "dict[str, tuple[int, float]]" = {}


def _album_group(message) -> str | None:
    return getattr(message, "media_group_id", None) or None


def _album_prune(now: float) -> None:
    for key, (_, seen) in list(_albums.items()):
        if now - seen > _ALBUM_WINDOW:
            del _albums[key]


def _album_route(message) -> int | None:
    """The conversation an earlier part of this album already went to.

    The map is not only about saying "Conversation #6" once. Which
    conversation an album belongs to is decided by its FIRST part and by that
    part alone, because the parts after it cannot be routed the ordinary way:

      * the guest's opening album spends the one-message exemption on part
        one, so parts two and three were held with "reply to something
        first" -- two photos of a three-photo message silently not delivered;
      * the owner's reply album anchors every part to the Reply prompt, and
        answering the prompt is what takes the prompt down, so parts two and
        three came back "that message is too old to reply to".

    Both are the same mistake: treating an album as several messages when a
    person sent one. Consulted before any other routing, which is what makes
    every part land where the first part did.
    """
    group = _album_group(message)
    if not group:
        return None
    _album_prune(datetime.now(timezone.utc).timestamp())
    known = _albums.get(group)
    return known[0] if known else None


def _album_remember(message, conversation_id: int) -> bool:
    """Note where this album is going. Returns True if an earlier part has
    already been announced, i.e. this one should arrive quietly."""
    group = _album_group(message)
    if not group:
        return False
    now = datetime.now(timezone.utc).timestamp()
    _album_prune(now)
    seen = group in _albums
    _albums[group] = (conversation_id, _albums[group][1] if seen else now)
    return seen


async def _refuse_if_updating(message, lang: str, user_id: int, chat_id: int) -> bool:
    """Whether an announced update means this message should not be relayed
    now. Says so and writes the person down when it does.

    A relay is quick, but it is still a write into a database an update may
    be in the middle of migrating -- and the point of the owner announcing an
    update in advance is that people hear about it before it lands rather
    than afterwards. AnonBot had none of these checks at all: /pause reached
    it, set the flag correctly, and nothing ever asked.
    """
    refusal = await refuse_new_work(lang, user_id, chat_id)
    if refusal:
        await message.reply_text(refusal)
        return True
    return False


def _anchor_for(peer_anchor: "int | None", conv: dict, newest_key: str) -> "int | None":
    """Which message in the receiving chat the delivered copy hangs under.

    The peer of whatever was replied to, when there is one. Otherwise the
    newest message of this conversation in that chat, which is what the
    whole family of these anchors used to be and is still the right answer
    when nothing more specific is known -- a first message, an album's
    later parts, a reply to a line that exists in one chat only.

    Both can be None, and that is a valid answer too: it means the copy goes
    in unanchored, which is what the very first message of a conversation
    has always done."""
    if peer_anchor is not None:
        return peer_anchor
    return conv.get(newest_key)


async def _deliver_follower_message(update: Update, context: ContextTypes.DEFAULT_TYPE, active: dict,
                                    message=None, peer_anchor: int | None = None):
    """`message` is normally the one that just arrived; the Send-it-anyway
    button passes the earlier, held one instead."""
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

    # "Is the sender blocked, does the inbox still exist, and what language
    # does the owner read?" -- one query, where it used to be three separate
    # round trips on the hot path of every anonymous message.
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

    # Both anchors move: the owner-side copy anchors the OWNER's next reply
    # chain, and the follower's own message anchors what the owner's reply
    # will quote on the way back (see _deliver_owner_reply below). The
    # guest's own message is written down on their side for the same reason
    # the owner's is on theirs -- so an edit to it can be answered, and so a
    # guest quoting themselves resolves rather than being refused.
    # When each side's bubble was written, and which side the bot wrote: what
    # /export places a forwarded message by. The guest's own message has
    # Telegram's date for it; the delivered copy is "now", read before the
    # round trip to the database rather than after it.
    delivered_at = datetime.now(timezone.utc)
    await asyncio.to_thread(
        record_relay_and_touch, active["id"],
        owner_id, [m.message_id for m in sent],
        message.chat_id, [message.message_id],
        sent[-1].message_id, message.message_id,
        owner_sent_at=delivered_at, follower_sent_at=getattr(message, "date", None),
        delivered_to="owner",
    )

    if active.get("follower_first_msg_at") is None:
        await asyncio.to_thread(mark_follower_opened, active["id"])

    # One confirmation per album, not one per photo.
    if not quiet:
        await message.reply_text(i18n.t(follower_lang, "sent_confirmation"))
    # No donation nudge on this side. A guest did not choose this bot -- they
    # tapped somebody's link -- and asking them to fund it is asking the
    # wrong person. The owner is nudged instead, once per conversation; see
    # _deliver_owner_reply.


async def _deliver_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, conversation_id: int,
                               peer_anchor: int | None = None):
    message = update.message
    owner = update.effective_user
    owner_lang = await i18n.get_lang(owner.id, context)
    conv = await asyncio.to_thread(get_conversation, conversation_id)
    if not conv or conv["owner_user_id"] != owner.id:
        # anon_relay rows for a chat are only ever written for that chat's
        # real owner, so this shouldn't normally trip -- but never guess and
        # risk sending a reply to the wrong chat.
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
            # No conversation number on this side. conv_number is the
            # OWNER's index for their own inbox, so this header was telling
            # every guest that they were somebody's forty-seventh
            # correspondent -- a fact about the owner, delivered to a
            # stranger, with no way for the owner to stop it. v1.4.0 took
            # the number out of the other guest-facing strings for the
            # weaker reason that it meant nothing to them; this one was
            # missed, and it is the one that leaked.
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

    # The owner's own sent message is a valid anchor too, so the NEXT
    # incoming message in this conversation threads off of it in the
    # owner's chat, keeping the back-and-forth visually connected there too.
    # And the delivered copies on the guest's side, without which a guest
    # who swipe-replies to the answer they just received is told their reply
    # matches no conversation. Both sides, one statement.
    delivered_at = datetime.now(timezone.utc)
    await asyncio.to_thread(
        record_relay_and_touch, conversation_id,
        owner.id, [message.message_id],
        follower_id, [m.message_id for m in sent],
        message.message_id, sent[-1].message_id,
        owner_sent_at=getattr(message, "date", None), follower_sent_at=delivered_at,
        delivered_to="follower",
    )

    if not quiet:
        await message.reply_text(i18n.t(owner_lang, "delivered_confirmation"))
    # Once per conversation, on the owner's first answer in it -- not once per
    # message. maybe_donation_nudge counts the times it is called, and in the
    # other bots one call is one whole conversion or download. Here it was one
    # chat message, so a pair holding an ordinary back-and-forth were shown a
    # donation pitch three messages in and then every few days.
    if conv.get("last_owner_msg_id") is None:
        nudge = await maybe_donation_nudge(
            owner.id, owner_lang, context, message.chat_id)
        if nudge:
            await message.reply_text(nudge)


# ---------------------------------------------------------------------------
# /export -- the conversation itself, either copied or written down
# ---------------------------------------------------------------------------
# The reasoning is in transcript.py. This is the Telegram half: choosing which
# conversation, choosing whether the bot reads it, and doing the one that was
# chosen.
#
# The owner, on what it was:
#
#   "The export button should be easier. User specifies which conversation to
#    export, or all, and all of them are either copied without accessing the
#    contents or with accessing and then deleted immediately after. ... This
#    should specify before exporting if it does or doesn't access the contents
#    of the messages."
#
# Nobody forwards anything any more. `anon_relay` already knows which message
# ids in this chat belonged to which conversation, so the bot can work from
# the index -- which is also why the access question has two real answers
# rather than one: naming an id to Telegram and reading what comes back are
# genuinely different things, and only one of them involves the bot seeing
# what was said.

# How long between edits of the progress line. Telegram rate-limits edits to
# about one a second per chat, and a line that updates on every message of a
# four-hundred-message export is the flood rather than the progress.
EXPORT_PROGRESS_SECONDS = 2.0


def _export_selection_keyboard(lang: str, conversations: list) -> InlineKeyboardMarkup:
    """One button per conversation, plus All when there is more than one."""
    rows = []
    buttons = []
    for conv in conversations:
        label = (i18n.t(lang, "export_pick_numbered", number=conv["conv_number"],
                        count=conv["messages"]) if conv["is_owner"]
                 else i18n.t(lang, "export_pick_yours", count=conv["messages"]))
        buttons.append(InlineKeyboardButton(label, callback_data=f"aq_export:pick:{conv['id']}"))
    rows += [buttons[index:index + 2] for index in range(0, len(buttons), 2)]
    if len(conversations) > 1:
        total = sum(conv["messages"] for conv in conversations)
        rows.append([InlineKeyboardButton(i18n.t(lang, "export_pick_all", count=total),
                                          callback_data="aq_export:pick:all")])
    rows.append([InlineKeyboardButton(i18n.t(lang, "export_button_cancel"),
                                      callback_data="aq_export:cancel")])
    return InlineKeyboardMarkup(rows)


def _export_mode_keyboard(lang: str, selection: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(i18n.t(lang, "export_button_copy"),
                              callback_data=f"aq_export:copy:{selection}")],
        [InlineKeyboardButton(i18n.t(lang, "export_button_doc"),
                              callback_data=f"aq_export:doc:{selection}")],
        [InlineKeyboardButton(i18n.t(lang, "export_button_cancel"),
                              callback_data="aq_export:cancel")],
    ])


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/export: which conversation, and then whether the bot may read it."""
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)
    chat_id = update.effective_chat.id
    conversations = await asyncio.to_thread(
        list_exportable_conversations, user.id, chat_id)
    if not conversations:
        await update.message.reply_text(i18n.t(lang, "export_nothing_to_export"))
        return
    await update.message.reply_text(
        i18n.t(lang, "export_pick_intro", count=len(conversations)),
        reply_markup=_export_selection_keyboard(lang, conversations))


async def _export_rows(user_id: int, chat_id: int, selection: str) -> tuple:
    """(conversations, {conversation id: rows}, how many were left out).

    Read here rather than in the handler so the whole export is one decision
    about how much to do, taken once, against the cap -- and so a selection of
    "all" cannot quietly become five separate caps.
    """
    conversations = await asyncio.to_thread(
        list_exportable_conversations, user_id, chat_id)
    if selection != "all":
        conversations = [c for c in conversations if str(c["id"]) == selection]
    # Oldest first: a conversation reads forwards, and so does a set of them.
    conversations = sorted(conversations, key=lambda c: str(c.get("started_at") or ""))
    rows, left_out, budget = {}, 0, transcript.MAX_MESSAGES
    for conv in conversations:
        got, skipped = await asyncio.to_thread(
            conversation_messages, chat_id, conv["id"], max(budget, 0))
        rows[conv["id"]] = got
        left_out += skipped
        budget -= len(got)
    return conversations, rows, left_out


async def export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pick a conversation, pick a mode, or cancel."""
    query = update.callback_query
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)
    parts = (query.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    selection = parts[2] if len(parts) > 2 else ""
    chat_id = query.message.chat_id

    if action == "cancel":
        await query.answer()
        await edit_in_place(query.message, context.bot, i18n.t(lang, "export_cancelled"))
        return

    if action == "pick":
        conversations, rows, left_out = await _export_rows(user.id, chat_id, selection)
        if not conversations:
            await query.answer(i18n.t(lang, "export_gone"), show_alert=True)
            return
        await query.answer()
        count = sum(len(got) for got in rows.values())
        what = (i18n.t(lang, "export_what_all", conversations=len(conversations))
                if selection == "all" or len(conversations) > 1
                else _export_one_name(lang, conversations[0]))
        text = i18n.t(lang, "export_modes", what=what, count=count)
        if left_out:
            text += "\n\n" + i18n.t(lang, "export_left_out", count=left_out)
        await edit_in_place(query.message, context.bot, text,
                            reply_markup=_export_mode_keyboard(lang, selection))
        return

    if action not in ("copy", "doc"):
        await query.answer()
        return

    # Refused before it starts rather than half-way through: an export is
    # hundreds of Telegram calls, and a container about to go is a container
    # that would stop somewhere in the middle of somebody's conversation.
    refusal = await refuse_new_work(lang, user.id, chat_id)
    if refusal:
        await query.answer(refusal, show_alert=True)
        return

    conversations, rows, left_out = await _export_rows(user.id, chat_id, selection)
    if not conversations or not any(rows.values()):
        await query.answer(i18n.t(lang, "export_gone"), show_alert=True)
        return
    await query.answer()
    if action == "copy":
        await _export_by_copying(context, query.message, lang, conversations, rows)
    else:
        await _export_as_document(context, query.message, lang, user, conversations, rows,
                                  left_out)


def _export_one_name(lang: str, conv: dict) -> str:
    # The number is the owner's own index for their inbox, so a guest is never
    # shown it -- the same rule as every other guest-facing string.
    return (i18n.t(lang, "export_what_numbered", number=conv["conv_number"]) if conv["is_owner"]
            else i18n.t(lang, "export_what_yours"))


class _Progress:
    """One line that keeps a count, rewritten at most every couple of
    seconds."""

    def __init__(self, bot, message, lang: str, total: int, key: str):
        self.bot, self.message, self.lang = bot, message, lang
        self.total, self.key, self.done, self.last = total, key, 0, 0.0

    async def step(self, by: int = 1) -> None:
        self.done += by
        now = asyncio.get_running_loop().time()
        if self.done < self.total and now - self.last < EXPORT_PROGRESS_SECONDS:
            return
        self.last = now
        try:
            await edit_in_place(self.message, self.bot,
                                i18n.t(self.lang, self.key, done=self.done, total=self.total))
        except Exception:
            logger.debug("Could not update the export progress", exc_info=True)


async def _export_by_copying(context, message, lang: str, conversations, rows) -> None:
    """Telegram copies each message into the chat. The bot names an id and
    never sees what is in it.

    Each conversation gets a line above it saying which it is -- the bot's own
    words, not anybody's -- so a copy of five threads is readable as five
    threads rather than as one long one.
    """
    chat_id = message.chat_id
    total = sum(len(got) for got in rows.values())
    progress = _Progress(context.bot, message, lang, total, "export_copy_progress")
    await progress.step(0)
    copied, missing = 0, 0
    for conv in conversations:
        if not rows.get(conv["id"]):
            continue
        try:
            await context.bot.send_message(
                chat_id=chat_id, disable_notification=True,
                text=i18n.t(lang, "export_copy_header", what=_export_one_name(lang, conv),
                            count=len(rows[conv["id"]])))
        except Exception:
            logger.debug("Could not write an export header", exc_info=True)
        for row in rows[conv["id"]]:
            try:
                await context.bot.copy_message(
                    chat_id=chat_id, from_chat_id=chat_id,
                    message_id=row["message_id"], disable_notification=True)
                copied += 1
            except Exception:
                # A message the person has since deleted, or one Telegram will
                # not copy. Counted and named at the end rather than failing
                # the whole export over one bubble.
                missing += 1
            await progress.step()
    done = i18n.t(lang, "export_copy_done", count=copied)
    if missing:
        done += "\n\n" + i18n.t(lang, "export_copy_missing", count=missing)
    await context.bot.send_message(chat_id=chat_id, text=done, disable_notification=True)
    await edit_in_place(message, context.bot, i18n.t(lang, "export_copy_finished", count=copied))


async def _read_one(context, chat_id: int, message_id: int):
    """Forward a message to its own chat, read what Telegram hands back, and
    take the copy down again.

    This is the whole of "accessing the contents", and it is the only way a
    bot can: there is no API for reading a message by id. The copy is deleted
    before the next one is made, so at most one extra message is on screen at
    any moment, and it is sent silently so nobody's phone lights up for it.
    """
    forwarded = await context.bot.forward_message(
        chat_id=chat_id, from_chat_id=chat_id, message_id=message_id,
        disable_notification=True)
    try:
        return forwarded
    finally:
        try:
            await context.bot.delete_message(
                chat_id=chat_id, message_id=forwarded.message_id)
        except Exception:
            logger.debug("Could not delete a read copy in %s", chat_id, exc_info=True)


async def _export_as_document(context, message, lang: str, user, conversations, rows,
                              left_out: int) -> None:
    """The transcript, read message by message and kept nowhere."""
    chat_id = message.chat_id
    total = sum(len(got) for got in rows.values())
    progress = _Progress(context.bot, message, lang, total, "export_doc_progress")
    await progress.step(0)

    def note(item) -> str:
        if item.kind == "text":
            return ""
        label = i18n.t(lang, f"export_kind_{item.kind}")
        return f"[{label}: {item.detail}]" if item.detail else f"[{label}]"

    owner_label = i18n.t(lang, "export_doc_owner")
    anon_label = i18n.t(lang, "export_doc_anon")
    sections, count, unreadable = [], 0, 0
    for conv in conversations:
        headers = _header_texts(conv)
        entries = []
        for row in rows.get(conv["id"], ()):
            try:
                forwarded = await _read_one(context, chat_id, row["message_id"])
            except Exception:
                unreadable += 1
                await progress.step()
                continue
            side = transcript.side_of(row["from_bot"], conv["is_owner"])
            item = transcript.item_for(forwarded, row["message_id"], side, row["sent_at"])
            text = item.text
            if row["from_bot"] and text:
                # The bot's header line above a delivered bubble is the bot
                # talking, not either side of the conversation.
                text = transcript.strip_header(text, headers)
                if text is None and item.kind == "text":
                    await progress.step()
                    continue
            entries.append({"label": owner_label if side == transcript.OWNER else anon_label,
                            "own": side == transcript.OWNER, "text": text or "",
                            "note": note(item), "when": item.sent_at})
            await progress.step()
        if not entries:
            continue
        count += len(entries)
        sections.append((_export_one_name(lang, conv),
                         i18n.t(lang, "export_doc_started",
                                date=str(conv.get("started_at") or "")[:10],
                                count=len(entries)), entries))

    if not sections:
        await edit_in_place(message, context.bot, i18n.t(lang, "export_failed"))
        return
    now = datetime.now(timezone.utc)
    page = transcript.render(
        title=i18n.t(lang, "export_doc_title"),
        generated=i18n.t(lang, "export_doc_generated", date=f"{now:%Y-%m-%d %H:%M}"),
        lang=lang, sections=sections, footer=i18n.t(lang, "export_doc_footer"))
    caption = i18n.t(lang, "export_caption", messages=count, conversations=len(sections))
    if unreadable:
        caption += "\n" + i18n.t(lang, "export_doc_unreadable", count=unreadable)
    if left_out:
        caption += "\n" + i18n.t(lang, "export_left_out", count=left_out)
    await context.bot.send_document(
        chat_id=chat_id, document=BytesIO(page), caption=caption,
        filename=f"anonbot_transcript_{now:%Y-%m-%d_%H%M}.html")
    await edit_in_place(message, context.bot, i18n.t(lang, "export_done"))


def _header_texts(conv: dict) -> list:
    """Every header the bot could have put above a delivered bubble of this
    conversation, in every language, so it comes off a forwarded one."""
    headers = []
    for language in i18n.SUPPORTED_LANGUAGES:
        headers.append(i18n.t(language, "incoming_header", conv_number=conv["conv_number"]))
        headers.append(i18n.t(language, "incoming_header_follower"))
    return headers


async def _cancel_items(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> list[CancelItem]:
    """Everything this bot could be waiting on.

    The open ask session -- what tapping someone's inbox link leaves behind
    -- is the one that matters most, because it lives in the database rather
    than in memory: every ordinary message you send keeps going to that
    person until something clears it. It is also the one most worth being
    asked about rather than swept up, since someone who typed /cancel to
    escape a Reply prompt did not mean to walk out of the conversation.
    """
    items = cancel_items(context, lang)
    if await asyncio.to_thread(get_active_conversation_for_follower, update.effective_user.id):
        items.append(CancelItem("anon_session",
                                i18n.t(lang, "cancel_item_anon_session"),
                                i18n.t(lang, "cancel_button_anon_session")))
    return items


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks which of the things it is waiting on to stop, then stops that
    one -- see _cancel_items for what they are."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    items = await _cancel_items(update, context, lang)
    if await ask_cancel_choice(update, context, items, lang):
        return
    # stored_only: every message this bot sends into a chat is part of a
    # conversation, so "delete whatever /cancel replies to" would delete
    # somebody's message and leave its relay row pointing at nothing.
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
    """Editing a message that has already been relayed changes nothing on the
    other side, and saying nothing let people believe it had.

    A bot cannot edit a message it copied into somebody else's chat back into
    a new shape -- copy_message makes an independent message, and the other
    person has very likely already read it. So the honest answer is to say
    what happened, once, and point at the thing that does work.

    Registered in group -1 and always ends by stopping the update, because
    asking Telegram for edits at all (allowed_updates) means every handler
    below this one starts seeing them: python-telegram-bot matches a
    MessageHandler -- and a CommandHandler -- on effective_message, which is
    the edited message, while update.message is None. Nothing downstream is
    written for that, and nothing downstream has any use for an edit.
    """
    edited = update.edited_message
    try:
        conversation_id = await asyncio.to_thread(
            get_conversation_for_relay, update.effective_chat.id, edited.message_id
        )
        if conversation_id is not None:
            lang = await i18n.get_lang(update.effective_user.id, context)
            await edited.reply_text(i18n.t(lang, "edit_not_relayed"))
    except Exception:
        # Logged, not swallowed. `raise` in a `finally` REPLACES whatever was
        # already propagating, so with only a finally here every failure in
        # this handler -- including a TypeError from a signature that had
        # changed underneath it -- became ApplicationHandlerStop and vanished.
        # The user got silence and the owner got no crash report; the suite
        # was the only thing that noticed.
        logger.exception("Could not answer an edited message")
    finally:
        raise ApplicationHandlerStop


async def _route_into(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      conversation_id: int, conv: dict | None = None,
                      peer_anchor: int | None = None) -> None:
    """Deliver this message into one named conversation, whichever side sent
    it. The sender's own id is what says the direction -- owner one way,
    guest the other -- and a sender who is neither is told the same thing a
    reply to something untracked is told, rather than being guessed at.

    `peer_anchor` is where the delivered copy should hang on the receiving
    side: the other chat's counterpart of the message this one replied to.
    None means there is nothing better to say, and the conversation's newest
    anchor is used -- which is the right answer for the two callers that
    pass nothing. An album's second and third parts arrive with no reply of
    their own and belong under the first part, and a message replying to the
    line that announced the conversation is replying to something that
    exists in one chat only."""
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

    # A forward while this person's export is open is for the transcript and
    # nothing else. It is never relayed, whatever it replies to and whichever
    # album it came in -- which is why it is asked before anything below.

    # 0. A later part of an album goes exactly where the first part went,
    #    before any other question is asked. See _album_route: the parts
    #    after the first cannot be routed on their own merits, because the
    #    first part is what spends the opening exemption and what takes the
    #    Reply prompt back down. Sending three photos is one message from
    #    where the person is sitting, and it has one destination.
    album = _album_route(message)
    if album is not None:
        return await _route_into(update, context, album)

    # 1. Is this a reply landing on a message we're tracking? That's an
    #    owner answering one specific conversation -- via the Reply button's
    #    forced reply, or an ordinary swipe-reply, both resolve identically.
    #    Checked FIRST and unconditionally, so it's correct even for someone
    #    who's simultaneously an owner (of their own link) and a follower
    #    (of someone else's) -- explicit reply intent always wins.
    #
    #    Crucially: a reply that DOESN'T match anything tracked stops right
    #    here instead of falling through to step 2 below. Using Telegram's
    #    reply feature is an explicit, deliberate signal -- "this is meant
    #    for the conversation I'm replying to" -- so if that conversation
    #    can't be found, the right answer is to say so, never to silently
    #    reinterpret the message as something else (e.g. a fresh anonymous
    #    message to whatever OTHER inbox this user happens to still have an
    #    open session with, which is exactly how a stray reply on old chat
    #    history could otherwise land somewhere unintended).
    if message.reply_to_message:
        anchor_id = message.reply_to_message.message_id
        relay = await asyncio.to_thread(get_relay_row, chat_id, anchor_id)
        conversation_id = relay["conversation_id"] if relay else None
        if conversation_id:
            # Both chats carry relay rows now, so a matched row says *which*
            # conversation, not which direction -- _route_into settles that
            # from the sender's own id.
            #
            # A guest replying used to be allowed only into the one
            # conversation anon_follower_state happened to point at -- which
            # every link tap overwrites, so tapping any inbox link silently
            # ended the guest's ability to answer everything they already
            # had. The Reply buttons under those older messages stayed on
            # screen and kept failing, and the message they got back blamed
            # the age of the message rather than the tap. The relay row is
            # the authority on which conversation a reply belongs to, it
            # resolved correctly the whole time, and the owner was never held
            # to this rule. Now neither side is: anon_follower_state says
            # where an UN-replied message goes, and nothing more.
            conv = await asyncio.to_thread(get_conversation, conversation_id)
            if conv and user.id in (conv["owner_user_id"], conv["follower_user_id"]):
                # The bubble on the other side that this one is the same
                # message as, so the delivered answer quotes what was
                # actually answered rather than whatever was said last.
                return await _route_into(update, context, conversation_id, conv,
                                         peer_anchor=relay["peer_message_id"])
        lang = await i18n.get_lang(user.id, context)
        await message.reply_text(i18n.t(lang, "reply_stale"))
        return

    # 2. A message that says nothing about where it is going.
    #
    #    Exactly one message in a conversation is allowed to: the guest's
    #    opening one, which has nothing above it to answer. Everything after
    #    it, from either side, has to name what it replies to -- an inbox
    #    link is posted somewhere public and one person ends up answering
    #    several, so "whichever thread was most recently touched" is not a
    #    guess worth making. It is also not a guess this bot got right: an
    #    owner answering a new arrival, while still holding an open session
    #    from a link they had tapped themselves, had their answer delivered
    #    to that other conversation entirely -- and told "Sent".
    routing = await asyncio.to_thread(get_routing_context, user.id, chat_id)
    active, owned = routing["active"], routing["owned"]

    # The exemption is spent on the conversation, and only while the
    # conversation that was just opened is still the newest thing in the
    # chat.
    #
    # It used to rest on follower_first_msg_at alone, which made it a
    # property of the newest conversation rather than of the chat -- so a
    # guest who was mid-conversation with one person, tapped a second link,
    # and then typed an answer to the first had it delivered to the second as
    # an opening message, and was told "Sent". Closing that with "is there
    # any other thread in this chat at all" was too blunt in the other
    # direction: it is a yes for every returning user, so from their second
    # inbox onwards the ordinary flow -- tap a link, type a message -- was
    # answered with "reply to the message you're answering", pointing at a
    # chat where the only thing to reply to was the line that had just told
    # them to write.
    #
    # Order is what tells the two apart, and the ordering is free: relay
    # message ids climb within a chat, so the newest relay row IS the last
    # thing the bot put on screen. If that is this conversation's own
    # opening line, nothing has happened since the tap and there is nothing
    # else the message could be answering. If something from another thread
    # arrived in between, there is, and the reply rule applies.
    if (active and active.get("follower_first_msg_at") is None
            and routing["newest_is_active"]):
        return await _deliver_follower_message(update, context, active)

    if active or owned:
        lang = await i18n.get_lang(user.id, context)
        return await _refuse_unaddressed(update, context, lang, routing)

    # 3. Neither -- generic nudge instead of silently swallowing the message.
    lang = await i18n.get_lang(user.id, context)
    await message.reply_text(i18n.t(lang, "generic_nudge"))


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
        raise SystemExit("Set ABOT_TOKEN and ABOT_USERNAME environment variables first.")

    init_db()
    builder = (
        ApplicationBuilder().token(BOT_TOKEN)
        .post_init(_post_init).post_stop(_post_stop)
    )
    # Open conversations kept in Postgres, so a redeploy is not the end of
    # somebody's half-written message. See lifecycle.py.
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
    # Answered here and stopped here -- see edited_message. Registered after
    # track_activity so an edit still counts as activity and still moves
    # live_message's watermark, and before everything else so no handler
    # written for update.message ever receives an update that has none.
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, edited_message), group=-2)
    # Runs after track_activity but before every other handler (including the
    # anonymous-relay handle_message below) -- a no-op unless a "Custom" donate
    # button was just tapped, in which case it consumes the reply and stops it
    # from also being relayed as an anonymous message (see
    # donate_custom_amount_received's docstring).
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, donate_custom_amount_received), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
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
    app.add_handler(CommandHandler("dbdump", dbdump_command))  # owner-only
    app.add_handler(CommandHandler("messageas", messageas_command))  # owner-only
    app.add_handler(CommandHandler("status", status_command))  # owner-only

    # ---- language: /en, /uz, /rus -- pick at first /start, change anytime ----
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

    app.add_handler(CallbackQueryHandler(language_chosen, pattern=r"^setlang:"))
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
    app.add_handler(CallbackQueryHandler(export_callback, pattern=r"^aq_export:"))

    # ---- donations (Telegram Stars) -- this bot's only Stars usage ----
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CallbackQueryHandler(donate_amount_chosen, pattern="^donate:"))
    app.add_handler(CallbackQueryHandler(donate_fiat_amount_chosen, pattern="^donatefiat:"))
    app.add_handler(CallbackQueryHandler(donate_custom_button_chosen, pattern="^donatecustom:"))
    app.add_handler(PreCheckoutQueryHandler(donation_precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, donation_payment_callback))

    # Everything else non-command in a private chat is either an owner's
    # reply or a follower's question -- handle_message() tells them apart.
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, handle_message))
    # Registered last so every real command above gets first shot -- only
    # reached by a slash-command this bot doesn't actually have.
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # ManagerBot's link: heartbeats, crash/donation events, and the queue it
    # uses to run this bot's owner-only commands remotely. Never raises --
    # with no shared database reachable the bot just runs on its own.
    family_link.attach(app, BOT_NAME, "AnonBot", START_TIME)
    attach_maintenance(app)

    logger.info("Bot starting (polling)...")
    # A 30-second long poll is the same latency as the default 10 -- Telegram
    # answers the moment an update exists -- for a third of the HTTP requests.
    # allowed_updates lists every kind this bot has a handler for, so Telegram
    # stops sending the rest rather than this process parsing and dropping it.
    app.run_polling(**lifecycle.polling_kwargs(
        timeout=POLL_TIMEOUT,
        allowed_updates=[
            Update.MESSAGE, Update.EDITED_MESSAGE,
            Update.CALLBACK_QUERY, Update.PRE_CHECKOUT_QUERY,
        ],
    ))


if __name__ == "__main__":
    main()
