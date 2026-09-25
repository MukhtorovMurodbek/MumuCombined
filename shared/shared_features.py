"""Small self-contained features used by this bot -- kept in one file for
convenience. It is copied byte-identically into every bot rather than
imported across folders, because each bot is its own repo and its own
deployment -- the same arrangement family_link.py uses. Nothing here
touches another bot's data: the cross-bot machinery all lives in
family_link.py. Things that live here:
  1. Sibling-bot cross-promotion text/buttons, for /start and /help --
     purely cosmetic (one env var), no database involved. Plus the one-tap
     language picker /start shows, which every bot renders the same way.
  2. A throttled, non-annoying donation reminder + a self-serve /donate
     command paid in Telegram Stars (no external payment processor needed).
  3. /privacy, /terms and /deletemydata: what this bot keeps on somebody,
     who else gets to see it, and the command that erases it again.
  4. The shared half of /cancel: the states this file can leave a user
     waiting in, the release of Telegram's client-side reply lock, and the
     one report format every bot's /cancel answers in.
  5. Logging setup, unhandled-exception tracking, active-user tracking, and
     hosting-environment detection, all in support of each bot's owner-only
     /status command.
  6. attach_maintenance()/flush_on_shutdown(): the jobs that keep a
     long-running process cheap -- writing buffered activity counts out in
     batches instead of a row per update, and dropping the cached per-user
     state of people who stopped using the bot months ago.
  7. attach_flood_gate(): a ceiling on what one person can make the bot do
     per minute, applied before any handler runs.
"""
import asyncio
import gc
import logging
import os
import re
import socket
import sys
import time
import traceback
import uuid
import zlib
from collections import OrderedDict, deque, namedtuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler

from telegram import (
    BotCommand, BotCommandScopeAllChatAdministrators, BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats, BotCommandScopeChat, ForceReply, InlineKeyboardButton,
    InlineKeyboardMarkup, LabeledPrice, LinkPreviewOptions, ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, NetworkError, RetryAfter
from telegram.ext import ApplicationHandlerStop, ConversationHandler, TypeHandler

import db
import family_link
import i18n
import lifecycle
import live_message
import problems

# ---------------------------------------------------------------------------
# Sibling-bot cross-promotion
# ---------------------------------------------------------------------------
# SIBLING_BOTS format (one env var, same value given to every bot in the
# family): "id:Display Name:username,id:Display Name:username"
#   e.g. "stickerbot:StickerBot:MyStickerBot,convertbot:ConvertBot:MyConvertBot"
# Each bot filters *itself* out of the list using its own BOT_NAME constant.
# This is cosmetic only -- purely a shared env var, not a shared database.

def _parse_sibling_bots() -> list[dict]:
    raw = os.environ.get("SIBLING_BOTS", "")
    bots = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) != 3:
            continue
        bot_id, name, username = parts
        bots.append({"id": bot_id, "name": name, "username": username})
    return bots


def _convert_bot_name() -> str:
    """ConvertBot as somebody can tap it -- its @username from SIBLING_BOTS --
    or just its name when this deployment does not list it."""
    for bot in _parse_sibling_bots():
        if bot["id"] == "convertbot":
            return "@" + bot["username"]
    return "ConvertBot"


def sibling_bots_blurb(this_bot_name: str, lang: str) -> str:
    """One short pointer line, not a repeat of the sibling list itself --
    sibling_bots_keyboard_row() below already renders that list as buttons,
    so spelling it out again in text too was just duplicate noise."""
    others = [b for b in _parse_sibling_bots() if b["id"] != this_bot_name]
    if not others:
        return ""
    return i18n.t(lang, "sibling_blurb")


def sibling_bots_keyboard_row(this_bot_name: str, only: str | None = None) -> list[InlineKeyboardButton]:
    others = [b for b in _parse_sibling_bots() if b["id"] != this_bot_name]
    if only:
        others = [b for b in others if b["id"] == only]
    return [InlineKeyboardButton(f"↗️ {b['name']}", url=f"https://t.me/{b['username']}") for b in others]


# ---------------------------------------------------------------------------
# The language picker
# ---------------------------------------------------------------------------
# The trilingual greeting used to end with "/en — English, /uz — O'zbekcha,
# /rus — Русский" and wait for the user to type one. Asking someone to type a
# command before they have been told what the bot does is the worst possible
# first impression, and on a phone it is three taps and a keyboard. One row of
# buttons is one tap, and the /en /uz /rus commands still work for anyone who
# has learned them.
#
# This is what a brand-new user's first /start shows, and what /language
# shows on demand at any point after that -- see start() and
# language_command() in each bot. Passing `current` ticks the language
# already in force, so a returning user can see at a glance which one they
# are on before deciding to change it.

def language_keyboard(current: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(("✅ " if code == current else "") + label,
                             callback_data=f"setlang:{code}")
        for code, label in i18n.LANGUAGE_LABELS.items()
    ]])


# ---------------------------------------------------------------------------
# Runtime tuning
# ---------------------------------------------------------------------------

WORKER_THREADS = int(os.environ.get("WORKER_THREADS", "4"))

# The garbage collector's generation-0 threshold. The default of 700 means a
# full young-generation sweep every 700 net allocations, which on a bot
# handling one message a minute is a sweep every few seconds, forever, over a
# heap that is almost entirely long-lived. Raising it trades a little peak
# memory for a lot of pointless scanning.
GC_THRESHOLD = int(os.environ.get("GC_GEN0_THRESHOLD", "5000"))


async def tune_runtime(application) -> None:
    """Call from each bot's post_init. Three settings, all of them about what
    an idle-most-of-the-day process costs to keep running.

    1. asyncio's default executor sizes itself to min(32, cpu_count + 4), and
       on a shared cloud host cpu_count is the *machine's* core count rather
       than this container's slice of it. That is up to 32 threads, each with
       its own stack, standing by for a workload whose peak is a couple of
       concurrent database calls and one ffmpeg. Four is plenty, and the
       difference is real resident memory on the smallest plan that fits.

    2. Everything imported at startup -- python-telegram-bot, psycopg, this
       bot's own modules -- is permanent by definition, and the garbage
       collector walks all of it on every full collection for the rest of the
       process's life. gc.freeze() moves it out of the collector's reach
       entirely. Called here, at the end of startup, because that is the last
       moment at which "allocated so far" and "will never be freed" mean the
       same thing.

    3. The collection threshold above.

    (The fourth knob is not settable from inside Python: glibc gives a
    threaded process up to 8 x cpu_count malloc arenas, each of which can
    hold on to tens of megabytes it will never hand back. MALLOC_ARENA_MAX
    caps that, and is set in nixpacks.toml where the runtime environment is.)
    """
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=WORKER_THREADS, thread_name_prefix="worker")
    )
    gc.collect()
    gc.freeze()
    gc.set_threshold(GC_THRESHOLD, 20, 20)



# ---------------------------------------------------------------------------
# What one person is allowed to cost
# ---------------------------------------------------------------------------
# Telegram rate-limits what a bot SENDS and nothing at all about what it
# receives, so until now one script could hold a container and a shared
# database busy for as long as it liked: /stats in a loop is a query each, a
# link pasted into DownloaderBot is a fetch and an encode, and an inbox link
# is meant to be posted somewhere public, which is where the traffic that
# does this comes from.
#
# The ceiling is per user and deliberately high -- a fast typist, an album,
# and a run of button taps all have to pass -- because what it is defending
# against is a loop, not a hurry.
#
# Two properties matter as much as the number:
#
#   It runs BEFORE any handler, so a refused update costs one dictionary
#   lookup rather than a database round trip. A limit checked inside the
#   handler has already paid for the thing it was meant to prevent.
#
#   It answers once and then goes quiet. A gate that replies to every
#   refused message turns an incoming flood into an outgoing one, which is
#   worse: the sender pays nothing and the bot pays Telegram's send budget
#   for every other user in the queue.
#
# In memory rather than in the database on purpose, for the same reason
# AnonBot's own limiter is: one container holds the polling lease, so there
# is exactly one counter, and paying a round trip to enforce a per-minute
# limit would cost more than the limit saves. A redeploy forgets it, and the
# worst that costs is one burst getting through after a restart.

FLOOD_UPDATES_PER_MINUTE = int(os.environ.get("FLOOD_UPDATES_PER_MINUTE", "40"))
FLOOD_REMIND_SECONDS = int(os.environ.get("FLOOD_REMIND_SECONDS", "60"))
_FLOOD_MAX_TRACKED = 4096

_flood_window: "OrderedDict[int, deque]" = OrderedDict()
_flood_told: "OrderedDict[int, float]" = OrderedDict()


def _flood_trim(store) -> None:
    while len(store) > _FLOOD_MAX_TRACKED:
        store.popitem(last=False)


def flood_wait_seconds(user_id: int) -> int:
    """0 if this person may be served now, otherwise the whole seconds until
    their oldest counted update falls out of the window."""
    if FLOOD_UPDATES_PER_MINUTE <= 0:
        return 0
    now = time.monotonic()
    window = _flood_window.setdefault(user_id, deque())
    _flood_window.move_to_end(user_id)
    _flood_trim(_flood_window)
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= FLOOD_UPDATES_PER_MINUTE:
        return max(1, int(60 - (now - window[0])) + 1)
    window.append(now)
    return 0


def _flood_should_tell(user_id: int) -> bool:
    now = time.monotonic()
    last = _flood_told.get(user_id)
    if last is not None and now - last < FLOOD_REMIND_SECONDS:
        return False
    _flood_told[user_id] = now
    _flood_told.move_to_end(user_id)
    _flood_trim(_flood_told)
    return True


def attach_flood_gate(app, admin_ids=(), group: int = -3, exempt=None) -> None:
    """Register in a group of its OWN, above every other group.

    Its own group because python-telegram-bot runs one handler per group and
    this one matches every update; above the others because a limit that
    runs after the work has not limited anything. The owner is exempt --
    /messageas and a sweep through /status are the bot's own operator using
    it, and being throttled out of your own bot during an incident is the
    wrong failure.

    `exempt`, if given, is asked about each update first, and True lets it
    through uncounted. AnonBot's /export uses it for the forwards it asked
    for, which arrive a hundred at a time.
    """
    admins = set(admin_ids)

    async def _gate(update, context) -> None:
        user = update.effective_user
        if user is None or user.id in admins:
            return
        if exempt is not None:
            try:
                if exempt(update):
                    return
            except Exception:
                logging.getLogger(__name__).debug("Flood exemption check failed", exc_info=True)
        wait = flood_wait_seconds(user.id)
        if not wait:
            return
        if _flood_should_tell(user.id):
            try:
                lang = await i18n.get_lang(user.id, context)
                if update.callback_query is not None:
                    await update.callback_query.answer(
                        i18n.t(lang, "flood_wait", seconds=wait), show_alert=True)
                elif update.effective_message is not None:
                    await update.effective_message.reply_text(
                        i18n.t(lang, "flood_wait", seconds=wait))
            except Exception:
                logging.getLogger(__name__).debug(
                    "Could not tell a flooding user to wait", exc_info=True)
        raise ApplicationHandlerStop

    app.add_handler(TypeHandler(Update, _gate), group=group)

# ---------------------------------------------------------------------------
# Donation reminder + /donate (Telegram Stars)
# ---------------------------------------------------------------------------
# Cadence: usage only, on a schedule that runs out.
#
# Each bot decides what counts as an "action" -- a finished pack, a completed
# conversion, a delivered download -- and calls maybe_donation_nudge() at
# that point. DONATION_STEPS is how many further actions are needed before
# each successive nudge: the first at 15, the second 60 after that, the third
# 200 after that, and then never again.
#
# What this replaced, and why (v1.2.3):
#
#   The old rule was "20 actions OR 14 days since the last nudge", floored at
#   3 days. The time half was the problem. It fired on people who were barely
#   using the bot -- the ones least likely to pay for it and most likely to
#   read a fortnightly reminder as spam -- and it never stopped, so a user of
#   three years who had already decided not to donate would be asked around
#   seventy times. An ask that repeats forever is not an ask, it is a tax on
#   being a regular.
#
#   Usage-only fixes the first half: the nudge now only ever arrives right
#   after the bot has just done something useful, which is the one moment it
#   has earned the right to ask. The schedule fixes the second: someone who
#   has been asked three times across 275 successful actions and has not
#   given has answered the question, and continuing to ask only costs
#   goodwill.
#
# The counters live in THIS bot's own schema -- the five bots share one
# database but never each other's tables -- so somebody active in two bots
# may be asked by each. That is an accepted tradeoff and it is bounded now,
# because each bot asks at most three times ever.
#
# Anyone with a paid row in star_transactions is never nudged again by that
# bot. Thanking somebody for donating by asking them to donate is the worst
# sentence this file could produce.

DONATION_STEPS = [15, 60, 200]
DONATION_COOLDOWN_FLOOR_DAYS = 3

# ---- pinning the nudge instead of repeating it (off by default) ----
# The owner proposed pinning the prompt in the chat so it stays visible
# without being re-sent. The instinct is right -- "ask once, remain visible"
# beats "ask again" -- and the implementation is here, but it is off, for
# three reasons worth reading before turning it on:
#
#   A pin is a permanent claim on the top of the user's chat window, for
#   something explicitly voluntary. The nudge's own text ends "no pressure
#   either way", and a pinned ask contradicts it.
#
#   Pinning posts a service message into the chat ("… pinned a message"),
#   so the thing meant to avoid a second notification creates one. Pinning
#   silently avoids the alert but not the service message.
#
#   It competes with the bot's real uses of the chat header. Nothing pins
#   today, but the first genuinely useful thing to pin -- a maintenance
#   notice, a sticker pack link -- would be arguing with a tip jar.
#
# With the schedule above capping the ask at three times ever, the problem
# pinning was meant to solve is mostly already solved. If you want it anyway:
# DONATION_PIN=on. It pins the nudge silently, unpins the previous one first,
# and unpins for good the moment that person donates.

DONATION_PIN = os.environ.get("DONATION_PIN", "off").lower() in ("on", "1", "true", "yes")

# Preset amounts shown as buttons on /donate. Four tiers: a tap that costs
# almost nothing and exists so that saying thank you is possible, two in the
# middle, and a high anchor -- which is there as much to make the middle
# look reasonable as to be chosen. Roughly $0.30 / $1 / $3 / $10 at what a
# user pays for Stars.
DONATE_STAR_OPTIONS = [15, 50, 150, 500]
# Loose sanity ceiling for /donate <amount> -- not Telegram's real per-invoice
# cap (which Telegram enforces itself; a rejected amount just surfaces
# Telegram's own error text back to the sender), just a guard against an
# obvious typo like an extra zero or two.
MAX_DONATION_STARS = 100_000

# ---------------------------------------------------------------------------
# Paying without paying, for TestBot
# ---------------------------------------------------------------------------
# With this on, a Stars top-up skips Telegram entirely: no invoice is sent,
# nothing is charged, and the credit lands in the balance exactly as a real
# payment would put it there. It exists because the alternative for testing
# the money path is spending real Stars on every run, and the part worth
# testing is what happens *after* the payment -- the rate, the first-payment
# bonus, the ledger row, the balance the user is shown.
#
# It is off unless the environment says otherwise, and the environment that
# says otherwise is testbot/token.env. Two things make it safe to have in the
# shared file rather than in a fork of it:
#
#   every message it produces says so, in the user's own language, so nobody
#   can believe they paid;
#   it logs a warning at import, so a production process that somehow had it
#   set would say so in the first line of its log rather than silently
#   handing out free credit.
#
# Fiat is deliberately not covered: a card payment has a provider behind it
# and a sandbox for it belongs to that provider, not here.
STARS_SANDBOX = os.environ.get("FAMILY_STARS_SANDBOX", "").strip().lower() in ("1", "true", "yes", "on")
if STARS_SANDBOX:
    logging.getLogger(__name__).warning(
        "FAMILY_STARS_SANDBOX is on: Stars top-ups will be credited WITHOUT charging anybody. "
        "This must never be set on a bot real people use.")

# ---- optional fiat alternative (USD) to Stars ----
# Cashing Stars out to real money goes through Fragment (Stars -> TON ->
# sell on an exchange) -- several hops for something as simple as "cover the
# hosting bill." A regular Telegram Payments provider skips that: connect
# one via @BotFather -> /mypayments (Stripe or another provider that
# supports your country), then set PAYMENT_PROVIDER_TOKEN_USD. Nothing below
# activates until that's set -- with it unset, /donate behaves exactly as it
# did before (Stars only).
#
# "exp"/min/max here are straight from Telegram's own reference table
# (https://core.telegram.org/bots/payments/currencies.json, checked
# 2026-08-24) -- invoice amounts must be in the currency's smallest unit
# (10**exp per whole unit), e.g. $5.00 -> 500. Don't add another currency
# here without checking that table for its real exp -- guessing it risks
# over/undercharging someone by a factor of 100. Its options list must stay
# the same length as DONATE_STAR_OPTIONS -- donate_command() zips them
# together into one Stars-column-then-fiat-column button grid per row.
FIAT_CURRENCIES = {
    "USD": {
        "symbol": "$", "label": "USD", "exp": 2,
        # Deliberately not a straight conversion of the Stars column. The
        # Stars tiers are priced for a tap; a card payment has a floor below
        # which the processor's own fee eats most of it, so the bottom tier
        # is $1 rather than $0.30.
        "options": [1, 3, 5, 10], "min_minor": 100, "max_minor": 1_000_000,
    },
}


# ---- the freeze ----
# Real-currency donations are FROZEN as of v1.3.0. The code below is
# complete and stays complete; what it does is nothing.
#
# Why frozen rather than deleted: connecting a provider is a decision about
# payouts and a country, not about this file, and the day it is made the work
# should already be done. Deleting it would mean rewriting the button grid,
# the amount validation, the invoice call, the ledger's currency column and
# three languages' worth of strings, all of which exist and all of which
# work.
#
# Why frozen rather than just left unconfigured: it already did nothing
# without PAYMENT_PROVIDER_TOKEN_USD, but "does nothing because a variable
# happens to be empty" is one accidental deploy-variable away from a half-
# enabled payment path -- an invoice offered on a rail that cannot take it,
# in front of a real user. One flag, checked at the single point every fiat
# path already goes through, so the freeze cannot be lifted by accident.
#
# To unfreeze: set FIAT_DONATIONS=on AND PAYMENT_PROVIDER_TOKEN_USD=<token>.
# Both, deliberately. Nothing else has to change.
FIAT_DONATIONS = os.environ.get("FIAT_DONATIONS", "off").lower() in ("on", "1", "true", "yes")


def _fiat_provider_token(currency: str) -> str | None:
    """The one chokepoint. Every fiat path in this file asks this first --
    the button grid via _available_fiat_currencies, `/donate 5 usd` before it
    validates anything, and _send_donation_invoice before it calls Telegram
    -- so returning None here is the whole freeze, and no other function
    needed a line changed to honour it."""
    if not FIAT_DONATIONS:
        return None
    return os.environ.get(f"PAYMENT_PROVIDER_TOKEN_{currency}") or None


def _available_fiat_currencies() -> list[str]:
    return [c for c in FIAT_CURRENCIES if _fiat_provider_token(c)]


def format_ledger_amount(amount: int, currency: str) -> str:
    """amount is in the currency's smallest unit (see FIAT_CURRENCIES) for
    fiat, or a plain Stars count for XTR."""
    if currency == "XTR":
        return f"{amount}⭐"
    cfg = FIAT_CURRENCIES.get(currency)
    if not cfg:
        return f"{amount} {currency}"
    return f"{amount / (10 ** cfg['exp']):g} {cfg['symbol']}"


def _donation_nudge_due(user_id: int) -> bool:
    """Blocking; the async wrapper below is what handlers call. One statement
    to bump-and-read, and a second one only in the rare case where the nudge
    actually fires."""
    count, last_shown, times_shown, donated = db.bump_donation_action(user_id)

    if donated:
        return False
    if times_shown >= len(DONATION_STEPS):
        return False  # asked three times across 275 actions; that is an answer

    if last_shown:
        days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_shown)).days
        if days_since < DONATION_COOLDOWN_FLOOR_DAYS:
            return False  # hard floor -- never twice in quick succession

    if count < DONATION_STEPS[times_shown]:
        return False

    db.reset_donation_prompt(user_id)
    return True


async def maybe_donation_nudge(user_id: int, lang: str, context=None, chat_id: int | None = None) -> str | None:
    """Await right after a successful action. Returns text to append to your
    reply, or None most of the time (send nothing).

    Async because it writes to the database, and this is called on the
    success path of the bot's main job -- doing it inline on the event loop
    stalls every other user's update for the round trip.

    `context` and `chat_id` are only used when DONATION_PIN is on, in which
    case the nudge is sent as its own message and pinned rather than handed
    back to be appended -- there is nothing to pin about a sentence glued to
    the end of somebody else's reply. That path returns None, so a caller
    that passes them and one that does not both do the right thing with the
    return value.
    """
    try:
        due = await asyncio.to_thread(_donation_nudge_due, user_id)
    except Exception:
        logging.getLogger(__name__).debug("Donation nudge check failed", exc_info=True)
        return None
    if not due:
        return None
    text = i18n.t(lang, "donation_nudge")
    if DONATION_PIN and context is not None and chat_id is not None:
        await _pin_donation_nudge(context, user_id, chat_id, text)
        return None
    return text


async def _pin_donation_nudge(context, user_id: int, chat_id: int, text: str) -> None:
    """Send the nudge on its own and pin it, replacing any earlier one.

    Every step is best-effort. A pin that fails must not cost the user the
    action they actually asked for, and pinning is the sort of thing
    Telegram refuses for reasons outside this bot's control -- a chat
    cleared, a message older than the pin limit, a client that unpinned it
    already. `disable_notification=True` because a nudge that pings someone's
    phone is worse than one that does not; it still leaves the "pinned a
    message" service line, which is one of the reasons this is off by
    default.
    """
    try:
        previous = await asyncio.to_thread(db.get_pinned_donation_message, user_id)
    except Exception:
        previous = None
    if previous:
        try:
            await context.bot.unpin_chat_message(chat_id=chat_id, message_id=previous)
        except Exception:
            logging.getLogger(__name__).debug("Could not unpin the previous nudge", exc_info=True)
    try:
        sent = await context.bot.send_message(chat_id=chat_id, text=text)
        await context.bot.pin_chat_message(
            chat_id=chat_id, message_id=sent.message_id, disable_notification=True)
    except Exception:
        logging.getLogger(__name__).debug("Could not pin the donation nudge", exc_info=True)
        return
    try:
        await asyncio.to_thread(db.set_pinned_donation_message, user_id, sent.message_id)
    except Exception:
        logging.getLogger(__name__).debug("Could not record the pinned nudge", exc_info=True)


async def unpin_donation_nudge(context, user_id: int, chat_id: int) -> None:
    """Called when somebody donates. Whatever the cadence says, the ask is
    over for this person -- and leaving it pinned would make a thank-you look
    like a repeat request."""
    try:
        previous = await asyncio.to_thread(db.get_pinned_donation_message, user_id)
    except Exception:
        return
    if not previous:
        return
    try:
        await context.bot.unpin_chat_message(chat_id=chat_id, message_id=previous)
    except Exception:
        logging.getLogger(__name__).debug("Could not unpin after a donation", exc_info=True)
    try:
        await asyncio.to_thread(db.set_pinned_donation_message, user_id, None)
    except Exception:
        pass


async def _credit_topup(update_or_chat, context, user, amount: int, lang: str,
                        payload: str, charge_id: str | None, sandbox: bool = False) -> str:
    """Turn a completed payment into credit, and say what it bought.

    The one place money becomes balance, so the real payment path and the
    sandbox path cannot drift apart -- which for a thing that hands out
    credit is the drift that matters.

    Returns the text to send. It always names three things: what was
    charged, what was credited, and what the credit can and cannot do. The
    last of those is not decoration -- credit is worth more than the Stars
    paid for it and cannot be paid back out, so a message that only said
    "thank you for 15 ⭐" would be describing a donation rather than the
    purchase this now is.
    """
    await asyncio.to_thread(db.update_star_transaction, payload, "paid", charge_id)
    result = await asyncio.to_thread(family_link.topup, user.id, amount,
                                     "sandbox top-up" if sandbox else "stars top-up")
    # `total` and `convert_bot` are for the bots that take donations: there the
    # thank-you says the credit arrived in ConvertBot, the one place it can be
    # spent. ConvertBot's own wording does not use them.
    text = i18n.t(lang, "topup_thanks", stars=result["stars"],
                  credited=result["credited"], balance=result["balance"],
                  total=result["credited"] + result["bonus"], convert_bot=_convert_bot_name())
    if result["bonus"]:
        text += "\n" + i18n.t(lang, "topup_thanks_bonus", bonus=result["bonus"],
                                  date=result["bonus_expires"].strftime("%d.%m.%Y")
                                  if result.get("bonus_expires") else "?")
    text += "\n\n" + i18n.t(lang, "credit_cannot_be_withdrawn")
    if sandbox:
        text = i18n.t(lang, "sandbox_notice") + "\n\n" + text
    # What was paid and what it bought, not who paid: the owner reads the
    # family log, and wants no user details in it. The ledger keeps the id,
    # which is where /balance <id> looks when somebody asks.
    emit_event(
        "info", "payment",
        ("SANDBOX top-up (nothing charged): " if sandbox else "Top-up: ")
        + f"{result['stars']} XTR -> {result['credited']} credit"
        + (f" +{result['bonus']} bonus" if result["bonus"] else ""),
    )
    return text


async def _send_donation_invoice(chat_id: int, user, context, amount: int, lang: str, currency: str = "XTR") -> str | None:
    """amount is in the currency's smallest unit for fiat (see
    FIAT_CURRENCIES), or a plain Stars count for XTR. Returns None on
    success, or an error message to show the sender if Telegram itself
    rejects the amount/currency (e.g. above Telegram's own per-invoice cap,
    or no provider connected for that currency)."""
    if currency != "XTR" and not _fiat_provider_token(currency):
        # Belt and braces. Nothing reaches here with a frozen currency today
        # -- every caller checks first -- and the cost of being wrong about
        # that is an invoice a user cannot pay, so it is checked again before
        # anything is written to the ledger.
        return i18n.t(lang, "donate_currency_not_configured", currency=currency)
    payload = f"donate:{uuid.uuid4().hex}"
    await asyncio.to_thread(
        db.record_star_invoice, user.id, user.username, amount, "donation", payload,
        "invoiced", currency,
    )
    if STARS_SANDBOX and currency == "XTR":
        # No invoice, no precheckout, no successful_payment update -- so this
        # credits the balance itself rather than waiting for a callback that
        # is never coming. The charge id records which path wrote the row, so
        # a sandbox top-up is distinguishable in the ledger forever rather
        # than looking like money that arrived.
        text = await _credit_topup(chat_id, context, user, amount, lang,
                                   payload, f"sandbox:{payload}", sandbox=True)
        await context.bot.send_message(chat_id=chat_id, text=text)
        return None

    provider_token = "" if currency == "XTR" else (_fiat_provider_token(currency) or "")
    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=i18n.t(lang, "donate_invoice_title"),
            # Fiat buys no credit (see donation_payment_received), so its
            # invoice must not say it does -- it used to render "adds 500 ⚡"
            # for a five-dollar donation, from the amount in cents.
            description=(i18n.t(lang, "donate_invoice_description",
                                credited=(await asyncio.to_thread(family_link.quote_topup, user.id, amount))["total"])
                         if currency == "XTR"
                         else i18n.t(lang, "donate_invoice_description_fiat")),
            payload=payload,
            provider_token=provider_token,  # empty string is required for Telegram Stars payments
            currency=currency,
            prices=[LabeledPrice(i18n.t(lang, "donate_invoice_label"), amount)],
        )
        return None
    except Exception as exc:
        await asyncio.to_thread(db.update_star_transaction, payload, "failed")
        return i18n.t(lang, "donate_invoice_error", error=exc)


def _validate_donation_amount(whole_amount: int, currency: str, lang: str) -> tuple[int | None, str | None]:
    """whole_amount is in whole units (a Stars count, or whole dollars for
    USD). Returns (amount in the invoice's own unit, None) on success, or
    (None, error message) if it's outside the currency's allowed range."""
    if currency == "XTR":
        if whole_amount > MAX_DONATION_STARS:
            return None, i18n.t(lang, "donate_too_many_stars", max=MAX_DONATION_STARS)
        return whole_amount, None
    cfg = FIAT_CURRENCIES[currency]
    amount = whole_amount * (10 ** cfg["exp"])
    if amount < cfg["min_minor"] or amount > cfg["max_minor"]:
        lo = cfg["min_minor"] / (10 ** cfg["exp"])
        hi = cfg["max_minor"] / (10 ** cfg["exp"])
        return None, i18n.t(lang, "donate_out_of_range", currency=currency, lo=f"{lo:g}", hi=f"{hi:g}", symbol=cfg["symbol"])
    return amount, None


async def donate_command(update, context) -> None:
    """/donate -- with no args, shows preset-amount buttons for Stars plus
    any fiat currency that has a payment provider connected (see
    FIAT_CURRENCIES above), with a Custom button per currency for anything
    else. /donate <amount> [currency] skips straight to an invoice --
    currency defaults to Stars, e.g. /donate 500 or /donate 5 usd."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if context.args:
        raw = context.args[0].replace(",", "")
        currency = "XTR"
        if len(context.args) > 1:
            requested = context.args[1].upper()
            if requested not in FIAT_CURRENCIES:
                await update.message.reply_text(i18n.t(lang, "donate_unknown_currency", currency=context.args[1]))
                return
            # Frozen or unconfigured both land here, and the sentence is the
            # same either way -- "not set up on this bot" is true of both and
            # is what the user needs to know. See FIAT_DONATIONS above.
            if not _fiat_provider_token(requested):
                await update.message.reply_text(i18n.t(lang, "donate_currency_not_configured", currency=requested))
                return
            currency = requested
        if not raw.lstrip("-").isdigit() or int(raw) <= 0:
            await update.message.reply_text(i18n.t(lang, "donate_invalid_amount"))
            return

        amount, validation_error = _validate_donation_amount(int(raw), currency, lang)
        if validation_error:
            await update.message.reply_text(validation_error)
            return

        error = await _send_donation_invoice(update.effective_chat.id, update.effective_user, context, amount, lang, currency)
        if error:
            await update.message.reply_text(error)
        return

    # One row per preset tier, Stars in the left column and each connected
    # fiat currency in its own column to the right -- e.g. with just USD
    # connected: [15⭐ 1$] / [50⭐ 5$] / [100⭐ 10$] -- plus a final row of
    # Custom buttons, one per column, for anything not on the list.
    fiat_options = _available_fiat_currencies()
    columns = [("XTR", DONATE_STAR_OPTIONS, "⭐")] + [
        (ccy, FIAT_CURRENCIES[ccy]["options"], FIAT_CURRENCIES[ccy]["symbol"]) for ccy in fiat_options
    ]
    kb_rows = [
        [
            InlineKeyboardButton(
                _donate_button_label(ccy, amount, symbol),
                callback_data=f"donate:{amount}" if ccy == "XTR" else f"donatefiat:{ccy}:{amount}",
            )
            for (ccy, _, symbol), amount in zip(columns, row)
        ]
        for row in zip(*(options for _, options, _ in columns))
    ]
    kb_rows.append([
        InlineKeyboardButton(i18n.t(lang, "donate_custom_button", symbol=symbol), callback_data=f"donatecustom:{ccy}")
        for ccy, _, symbol in columns
    ])
    kb = InlineKeyboardMarkup(kb_rows)

    # Said before the amount is chosen, not only in the thank-you: a Stars
    # payment becomes credit that cannot be taken back out, and nobody should
    # find that out after paying.
    # What THIS person's next Stars earn: the ladder counts every Star they
    # have ever paid, so the same button means a different amount of credit
    # for somebody new than for somebody who has paid a thousand.
    totals = await asyncio.to_thread(family_link.star_totals, update.effective_user.id)
    multiplier, left = family_link.ladder_position(totals["stars_paid"])
    base_rate = family_link.credit_for_stars(1)
    if left:
        credit_line = i18n.t(lang, "donate_prompt_credit", left=left, mult=f"{multiplier:g}",
                             each=f"{base_rate * multiplier:g}", rate=base_rate,
                             days=family_link.BONUS_EXPIRY_DAYS)
    else:
        credit_line = i18n.t(lang, "donate_prompt_credit_base", rate=base_rate)
    prompt = i18n.t(lang, "donate_prompt") + "\n\n" + credit_line
    await update.message.reply_text(prompt, reply_markup=kb)


def _donate_button_label(ccy: str, amount: int, symbol: str) -> str:
    """The amount and its currency. The bonus is no longer on the button: it
    depends on what this person has paid before, across all their payments,
    so the prompt above the buttons says what their next Stars earn."""
    return f"{amount} {symbol}"


# Callback data is not the button's. It is whatever the client sends back,
# and a modified client can send anything at all for a button that exists --
# so the three handlers below check what they are given against what this bot
# actually offered, exactly as the typed `/donate <amount>` path above always
# has. Taken on trust, `donate:abc` raised ValueError, `donatefiat:x` raised
# on the unpack and an unknown currency raised KeyError: three ways for
# anybody to fill the owner's crash channel from a phone, and a fourth to
# raise an invoice for an amount no tier offers, which is the one thing
# MAX_DONATION_STARS exists to prevent.

async def donate_amount_chosen(update, context) -> None:
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    _, _, tail = (query.data or "").partition(":")
    if not tail.isdigit() or int(tail) not in DONATE_STAR_OPTIONS:
        await query.answer(i18n.t(lang, "donate_invalid_amount"), show_alert=True)
        return
    await query.answer()
    error = await _send_donation_invoice(
        query.message.chat_id, update.effective_user, context, int(tail), lang
    )
    if error:
        await context.bot.send_message(chat_id=query.message.chat_id, text=error)


async def donate_fiat_amount_chosen(update, context) -> None:
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    parts = (query.data or "").split(":", 2)
    currency = parts[1] if len(parts) == 3 else ""
    whole_amount = parts[2] if len(parts) == 3 else ""
    cfg = FIAT_CURRENCIES.get(currency)
    # _available_fiat_currencies() and not FIAT_CURRENCIES: a currency that is
    # known but has no provider token, or is frozen, was never on a button.
    if (cfg is None or currency not in _available_fiat_currencies()
            or not whole_amount.isdigit() or int(whole_amount) not in cfg["options"]):
        await query.answer(i18n.t(lang, "donate_invalid_amount"), show_alert=True)
        return
    amount = int(whole_amount) * (10 ** cfg["exp"])
    await query.answer()
    error = await _send_donation_invoice(query.message.chat_id, update.effective_user, context, amount, lang, currency)
    if error:
        await context.bot.send_message(chat_id=query.message.chat_id, text=error)


async def donate_custom_button_chosen(update, context) -> None:
    """Tapping a 'Custom' button asks for an amount via ForceReply; the
    actual amount is picked up by donate_custom_amount_received below,
    matched via the donate_custom_currency flag this sets in user_data."""
    query = update.callback_query
    lang = await i18n.get_lang(update.effective_user.id, context)
    _, _, currency = (query.data or "").partition(":")
    if currency != "XTR" and currency not in _available_fiat_currencies():
        await query.answer(i18n.t(lang, "donate_invalid_amount"), show_alert=True)
        return
    await query.answer()
    context.user_data["donate_custom_currency"] = currency
    unit = i18n.t(lang, "stars_unit") if currency == "XTR" else FIAT_CURRENCIES[currency]["label"]
    prompt = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=i18n.t(lang, "donate_custom_ask", unit=unit),
        reply_markup=ForceReply(selective=True, input_field_placeholder="e.g. 500"),
    )
    remember_force_reply(context, prompt)


async def donate_custom_amount_received(update, context) -> None:
    """Register in a group before your bot's normal text handling (see
    track_activity for the same pattern) -- a no-op unless
    donate_custom_button_chosen just set the awaiting-amount flag, in which
    case it consumes the reply and stops it from also being treated as a
    normal message (ApplicationHandlerStop)."""
    currency = context.user_data.get("donate_custom_currency")
    if not currency:
        return
    context.user_data.pop("donate_custom_currency", None)
    context.user_data.pop(FORCE_REPLY_KEY, None)
    lang = await i18n.get_lang(update.effective_user.id, context)

    raw = (update.message.text or "").strip().replace(",", "")
    if not raw.lstrip("-").isdigit() or int(raw) <= 0:
        await update.message.reply_text(i18n.t(lang, "donate_invalid_amount_retry"))
        raise ApplicationHandlerStop

    amount, validation_error = _validate_donation_amount(int(raw), currency, lang)
    if validation_error:
        await update.message.reply_text(validation_error)
        raise ApplicationHandlerStop

    error = await _send_donation_invoice(update.effective_chat.id, update.effective_user, context, amount, lang, currency)
    if error:
        await update.message.reply_text(error)
    raise ApplicationHandlerStop


# ---- primitives for bots that ALSO have their own Stars flow (e.g. ConvertBot's
# /convert), which need to check the payload prefix themselves and only fall
# through to these for "donate:"-prefixed ones ----

async def donation_precheckout(query) -> None:
    """Caller has already confirmed query.invoice_payload starts with 'donate:'."""
    await query.answer(ok=True)


async def donation_payment_received(update, context) -> None:
    """Caller has already confirmed the payload starts with 'donate:'.

    A payment used to end in a thank-you and nothing else. Now it ends in
    credit, through the same _credit_topup the sandbox uses -- so what a
    tester sees and what a payer sees are produced by one function.

    Fiat still only gets the thank-you: the credit rate is defined against
    Stars, and inventing an exchange rate from a currency's minor units would
    be making up a number.
    """
    sp = update.message.successful_payment
    user = update.effective_user
    lang = await i18n.get_lang(update.effective_user.id, context)
    if sp.currency == "XTR":
        text = await _credit_topup(update, context, user, sp.total_amount, lang,
                                   sp.invoice_payload, sp.telegram_payment_charge_id)
        await update.message.reply_text(text)
    else:
        await asyncio.to_thread(
            db.update_star_transaction, sp.invoice_payload, "paid",
            sp.telegram_payment_charge_id
        )
        emit_event(
            "info", "payment",
            f"Donation received: {format_ledger_amount(sp.total_amount, sp.currency)}",
        )
        await update.message.reply_text(i18n.t(lang, "donate_thanks", amount=sp.total_amount))
    # The ask is over for this person -- _donation_nudge_due checks the same
    # paid row and will never fire again, and anything still pinned comes
    # down now rather than sitting above a thank-you.
    await unpin_donation_nudge(context, user.id, update.effective_chat.id)


# How a ledger reason reads in /balance. Reasons stay short English tokens (see
# below), but "refund" beside credit coming back reads as Stars coming back,
# and in what the bots say only Stars are ever refunded -- and they are not.
_LEDGER_LABELS = {"refund": "returned"}


async def balance_command(update, context) -> None:
    """/balance -- what this person is holding, and what it is for.

    Registered by every bot rather than only by the ones that charge, because
    the balance is one wallet for the whole family: somebody who topped up in
    StickerBot has to be able to ask StickerBot where it went.

    It always prints the rate and the no-withdrawal line, not only when the
    balance is zero. A number on its own invites exactly the wrong question
    later -- "can I have it back" -- and the answer costs nothing to give
    before it is asked.
    """
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)
    totals = await asyncio.to_thread(family_link.star_totals, user.id)
    rows = await asyncio.to_thread(family_link.star_ledger_for, user.id, 8)
    lines = [i18n.t(lang, "balance_header", balance=totals["balance"])]
    if totals["stars_paid"] > 0 or totals["spent"] > 0:
        lines.append(i18n.t(lang, "balance_totals", paid=totals["stars_paid"],
                            credited=totals["topped_up"], spent=totals["spent"]))
    lines.append("")
    if totals.get("bonus"):
        lines.append(i18n.t(lang, "balance_bonus_line", bonus=totals["bonus"],
                            soon=totals["bonus_next_amount"],
                            date=totals["bonus_next_expiry"].strftime("%d.%m.%Y")))
    multiplier, left = family_link.ladder_position(totals["stars_paid"])
    base_rate = family_link.credit_for_stars(1)
    if left:
        lines.append(i18n.t(lang, "balance_rate", left=left, mult=f"{multiplier:g}",
                            each=f"{base_rate * multiplier:g}"))
    else:
        lines.append(i18n.t(lang, "balance_rate_base", rate=base_rate))
    lines.append(i18n.t(lang, "credit_cannot_be_withdrawn"))
    if rows:
        lines.append("")
        lines.append(i18n.t(lang, "balance_recent"))
        for row in rows:
            when = row["occurred_at"].strftime("%d %b")
            sign = "+" if row["delta"] > 0 else ""
            # The reason is a short English token from LEDGER_REASONS rather
            # than a translated phrase, the same choice /mystars makes about
            # ledger data: one word that groups rows, not prose.
            lines.append(f"  {when}  {sign}{row['delta']} ⚡  "
                         f"{_LEDGER_LABELS.get(row['reason'], row['reason'])}")
    if not rows and totals["balance"] == 0:
        lines.append("")
        lines.append(i18n.t(lang, "balance_empty_hint"))
    await update.message.reply_text("\n".join(lines))


# ---- full standalone handlers, for bots (like StickerBot) whose ONLY Stars
# usage is donations -- register these two directly, no branching needed ----

async def donation_precheckout_callback(update, context) -> None:
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("donate:"):
        await query.answer(ok=False, error_message="Unknown order.")
        return
    await donation_precheckout(query)


async def donation_payment_callback(update, context) -> None:
    sp = update.message.successful_payment
    if not sp.invoice_payload.startswith("donate:"):
        return
    await donation_payment_received(update, context)


# ---------------------------------------------------------------------------
# The two screens somebody sees before they ever press Start
# ---------------------------------------------------------------------------
# A Telegram bot has three pieces of profile text and the family was setting
# one of them. set_my_commands fills the slash menu, which only helps once you
# are already in the chat. The other two are what a stranger meets first:
#
#   the short description -- one line, next to the bot in search results and
#   under its name on the profile card;
#   the description -- up to 512 characters, and the whole of what an empty
#   chat shows above the Start button, under "What can this bot do?".
#
# Both were blank, so an empty chat said nothing at all and search results
# showed a name and a username. Both take a language_code, so all three
# languages go up, and the English text goes up twice: once tagged "en" and
# once untagged, because the untagged one is what Telegram falls back to for
# somebody whose client is in German.
#
# Called from each bot's _post_init beside set_my_commands. It costs six API
# calls on a start that happens a few times a day, and it never raises: a rate
# limit on a cosmetic call is not a reason to fail a deploy.

async def publish_profile(application) -> None:
    logger = logging.getLogger(__name__)
    for language in (None,) + tuple(i18n.SUPPORTED_LANGUAGES):
        lang = language or "en"
        try:
            await application.bot.set_my_short_description(
                short_description=i18n.t(lang, "bot_short_description"),
                language_code=language,
            )
            await application.bot.set_my_description(
                description=i18n.t(lang, "bot_description"),
                language_code=language,
            )
        except Exception:
            logger.warning("Could not publish the %s profile text.",
                           language or "default", exc_info=True)


# ---------------------------------------------------------------------------
# The slash menu, twice
# ---------------------------------------------------------------------------
# Every bot in the family handles commands it never offers. The owner-only
# ones -- /status, /dbdump, /messageas and each bot's own -- were kept out of
# set_my_commands on the sound reasoning that there is no point advertising to
# a stranger a command they cannot run. The unsound part was that this also
# hid them from the one person who can: the owner types /status into their own
# bot from memory, or does not, and a command nobody remembers is a command
# that may as well not exist.
#
# Telegram already has the answer and the family was not using it. A command
# menu has a *scope*, and BotCommandScopeChat sets one for a single chat.
# So the menu goes up twice: the public list at the default scope, which is
# what everybody sees, and the public list plus the owner-only ones in each
# admin's own chat with the bot. Nobody else's menu changes, and the guards
# are untouched -- a scope decides what is offered, never what is allowed.
#
# Two things are worth knowing about scopes:
#
#   A scoped menu outlives the reason for it. Drop an id from *_ADMIN_ID and
#   that person keeps the longer menu until somebody calls delete_my_commands
#   for their chat. It is cosmetic -- every one of those commands still checks
#   _is_admin and still refuses them -- but it is why the menu is not a
#   permission.
#   set_my_commands for a chat Telegram has never seen fails. An admin who has
#   never opened their own bot is exactly that chat, so this never raises: a
#   cosmetic call is not a reason to fail a deploy, same as publish_profile.
#
# AND IN THREE LANGUAGES, SINCE v1.6.0
# The bots answer in English, Uzbek and Russian everywhere except the one list
# somebody reads before they have understood anything. A menu also takes a
# language_code -- the same way publish_profile() already sends the profile
# text three times -- and Telegram picks the list matching the client's own
# language, falling back to the untagged one.
#
# So English lives in each bot's BOT_COMMANDS, where the menu can be read by
# reading bot.py, and the other two live in i18n.COMMAND_MENU keyed by command
# name. A command with no translation keeps its English description rather
# than disappearing from that language's menu, which is the one failure mode
# worth designing against: a half-translated menu is missing commands, and a
# missing command looks like a bot that cannot do the thing.
#
# Four commands are deliberately NOT translated, and they are the four that
# look most like they should be. /en, /uz and /rus are each described in the
# language they switch *to*, and /language is described in all three at once.
# A per-language menu does not change that: somebody whose client is Russian
# but who wants Uzbek has to recognise "O'zbekchaga o'tish", and somebody who
# set the wrong language needs /language to be legible whatever the menu is
# currently in. They are the way back, so they are written for everyone.
#
# The owner's scoped menu stays untagged English. All admin output in this
# family is English by policy, and the owner is the one reader whose language
# is not in question.

def _menu_in(commands, language: str):
    """`commands` with each description swapped for its `language` one.

    Falls back per command, not per menu: an untranslated entry keeps its
    English text and the rest of the list is still translated.
    """
    table = getattr(i18n, "COMMAND_MENU", {}).get(language) or {}
    return [BotCommand(c.command, table.get(c.command) or c.description)
            for c in commands]


# ---------------------------------------------------------------------------
# A menu in the language somebody chose
# ---------------------------------------------------------------------------
# Telegram picks which of the per-language menus to show from the language
# the person's Telegram APP is set to, not from anything a bot knows. So /uz
# changed every message this bot sends and left the menu in English for
# anybody whose phone is in English or Russian -- which in Uzbekistan is most
# people who would choose Uzbek. A menu set for one chat (BotCommandScopeChat)
# outranks every language list, so choosing a language now sets one.
#
# The catch with a per-chat menu is that it is frozen when it is set: a
# command added in a later version would never reach it. Each person's
# user_data remembers a signature of the menu they were given, and
# track_activity compares it with what they would be given now, and sets it
# again when the two differ. One call per person per change, made the next
# time they use the bot rather than all at once at startup.

MENU_SIGNATURE_KEY = "_menu_sig"
_MENU: dict = {}


def _menu_for(user_id: int, lang: "str | None"):
    """The menu this person should have, or None before publish_commands has
    said what the menus are."""
    public = _MENU.get("public")
    if public is None:
        return None
    commands = list(public) if lang in (None, "en") else _menu_in(public, lang)
    if user_id in _MENU.get("admin_ids", ()):
        commands = list(commands) + list(_MENU.get("admin_only", ()))
    return commands


def _menu_signature(commands) -> str:
    text = "\n".join(f"{c.command}\t{c.description}" for c in commands)
    return format(zlib.crc32(text.encode("utf-8")), "08x")


async def refresh_chat_menu(context, user_id: int, lang: "str | None") -> None:
    """Give one person's chat the menu in their language. Never raises: a
    menu is cosmetic, and a failure here must not cost anybody the language
    change they asked for."""
    commands = _menu_for(user_id, lang)
    if not commands:
        return
    try:
        await context.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
    except Exception:
        logging.getLogger(__name__).debug("Could not set the chat menu for %s", user_id, exc_info=True)
        return
    context.user_data[MENU_SIGNATURE_KEY] = _menu_signature(commands)


# Scopes this code never writes. Telegram resolves a chat's menu by scope
# precedence -- a chat's own, then all-private-chats, then the default -- so
# a menu left in one of these by anything else outranks the default the code
# does write, and reading the default says everything is fine. That is what
# kept StickerBot's commands on TestBot's token long after it ran ConvertBot's
# code. They are cleared on every start, so the code is the only authority.
_UNOWNED_SCOPES = (
    BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators,
)


async def publish_commands(application, public, admin_only=(), admin_ids=()) -> None:
    """The default menu for everyone, in every language; the scopes the code
    does not own, cleared; and the owner's chat, in the owner's language."""
    logger = logging.getLogger(__name__)
    public = list(public)
    _MENU.update(public=public, admin_only=list(admin_only), admin_ids=set(admin_ids))

    # None first: the untagged list is what a client in a fourth language
    # gets, so it goes up even if every tagged one fails after it.
    for language in (None,) + tuple(i18n.SUPPORTED_LANGUAGES):
        try:
            await application.bot.set_my_commands(
                public if language in (None, "en") else _menu_in(public, language),
                language_code=language,
            )
        except Exception:
            logger.warning("Could not publish the %s command menu.",
                           language or "default", exc_info=True)

    for scope in _UNOWNED_SCOPES:
        for language in (None,) + tuple(i18n.SUPPORTED_LANGUAGES):
            try:
                await application.bot.delete_my_commands(scope=scope(), language_code=language)
            except Exception:
                logger.debug("Could not clear the %s menu (%s).", scope.__name__,
                             language or "untagged", exc_info=True)

    if not admin_only:
        return
    for admin_id in sorted(admin_ids):
        lang = None
        try:
            lang = await asyncio.to_thread(db.get_user_language, admin_id)
        except Exception:
            logger.debug("Could not read the language of admin %s", admin_id, exc_info=True)
        try:
            await application.bot.set_my_commands(
                _menu_for(admin_id, lang),
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception:
            logger.warning("Could not publish the owner's command menu to %s.",
                           admin_id, exc_info=True)

# ---------------------------------------------------------------------------
# How a long message is laid out
# ---------------------------------------------------------------------------
# Telegram gives a bot four things to design with: bold, a monospace run, an
# expandable blockquote, and blank lines. That is the whole palette, and it is
# enough -- what it is not is automatic, and until this existed every screen in
# the family was one undifferentiated column of sentences. /privacy was the
# worst of them at about two thousand characters, which on a phone is four
# thumb-flicks of unbroken grey.
#
# The rules, such as they are:
#
#   A title line, once, at the top: the subject in bold, with the emoji that
#   the string already carries. Telegram has no heading levels -- there is
#   bold and there is not-bold -- so the title and the section headings use
#   the same helper and are told apart by position.
#   Section headings in bold, with a blank line above and none below.
#   Anything longer than a short paragraph goes in an expandable blockquote,
#   so the shape of the message is visible without scrolling and the detail is
#   one tap away.
#   Commands in a monospace run, so /deletemydata reads as a thing to type
#   rather than as a word in a sentence.
#
# EVERYTHING INTERPOLATED IS ESCAPED. The text these wrap comes from i18n.py
# and is written by whoever translated it; a stray "<" in a Russian string
# would otherwise take the whole message down with "can't parse entities", and
# the failure lands on the user as silence rather than as a log line.

# A link in a notice should not drag a preview card in behind it: the card
# for a GitHub page is a screenful of nothing under a document that is already
# long. Same call downloader_bot/bot.py makes.
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


def esc(text: str) -> str:
    """The three characters Telegram's HTML parser cares about."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def heading(text: str) -> str:
    return f"<b>{esc(text)}</b>"


# Two touches that give a translated string structure without the translator
# having had to think about markup, and without this file having to know which
# language it is looking at.

_COMMAND_RE = re.compile(r"(?<![\w/])(/[a-z][a-z0-9_]{1,30})\b")


def body(text: str) -> str:
    """Escaped, with every /command in it set as a command.

    A slash-word is a thing to type, and it reads as one when it is in a
    monospace run and as an ordinary word when it is not -- which matters most
    in the sentence that offers /deletemydata, since that is the one somebody
    is scanning for.
    """
    return _COMMAND_RE.sub(r"<code>\1</code>", esc(text))


def lead_in(text: str, limit: int = 28) -> str:
    """`Money: it is voluntary` with the lead-in in bold.

    Several strings already open with a short label and a colon, in all three
    languages, because that is how somebody writes a paragraph that answers a
    question. Bolding it costs nothing and gives a wall of paragraphs the
    headings it already implies. A string with no such opening is returned as
    it is, which is most of them.
    """
    label, colon, rest = text.partition(":")
    if not colon or "\n" in label or len(label) > limit:
        return body(text)
    return f"<b>{esc(label)}:</b>{body(rest)}"


def collapsed(text: str) -> str:
    """A blockquote that shows a few lines and opens on a tap.

    Bot API 7.2 and later. An older client -- or an older self-hosted Bot API
    server -- renders it as an ordinary blockquote, which is a worse but
    perfectly readable version of the same thing, so there is nothing to
    detect and nothing to fall back to.
    """
    return f"<blockquote expandable>{body(text)}</blockquote>"


def quoted(text: str) -> str:
    """A blockquote that is always open. For a few lines, not for many."""
    return f"<blockquote>{body(text)}</blockquote>"


def joined(*blocks) -> str:
    """The blocks that are not empty, one blank line between each."""
    return "\n\n".join(block for block in blocks if block)


# The one thing that can still go wrong is a Bot API server too old to know
# what an expandable blockquote is, which answers 400 rather than degrading.
# That is a self-hosted-server setup (LOCAL_BOT_API_URL) and nobody's fault,
# but the user should not pay for it with silence: the same text goes out
# again with every tag removed. Worth the eight lines -- a bot that cannot
# answer /privacy is worse than a bot that answers it in plain text.

_TAG_RE = re.compile(r"<[^>]+>")


def _plain(text: str) -> str:
    return (_TAG_RE.sub("", text).replace("&lt;", "<")
            .replace("&gt;", ">").replace("&amp;", "&"))


async def reply_formatted(message, text: str, **kwargs):
    try:
        return await message.reply_text(
            text, parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW, **kwargs
        )
    except BadRequest as exc:
        if "parse" not in str(exc).lower() and "entit" not in str(exc).lower():
            raise
        logging.getLogger(__name__).warning(
            "This Telegram server would not parse the formatting (%s); sending plain.", exc
        )
        return await message.reply_text(
            _plain(text), link_preview_options=NO_PREVIEW, **kwargs
        )


# ---------------------------------------------------------------------------
# /privacy, /terms, /deletemydata -- what is held, and getting rid of it
# ---------------------------------------------------------------------------
# A Telegram bot has no cookie banner, no tracking pixel and no third-party
# embeds, so most of a website's compliance checklist does not apply to one.
# What does apply is the part underneath: a bot holds personal data from the
# first message, because a numeric Telegram user id is the only thing it can
# address a person by, and it cannot ask permission before receiving one.
#
# Telegram asks every bot for a privacy policy and gives BotFather a field to
# put the link in, so there has to be something to link to. Three commands
# rather than one document nobody opens:
#
#   /privacy       what this bot keeps, who else sees it, how long it stays
#   /terms         what the bot may be used for, and where the money stands
#   /deletemydata  the erase button that makes the other two mean something
#
# A policy is worth what it can be held to, which is why the third command
# exists. Without it the first two describe a filing cabinet nobody can open.
#
# The wording is per-bot on purpose. StickerBot keeps sticker packs, AnonBot
# keeps who is talking to whom, DownloaderBot hands a link to somebody else's
# server -- a policy describing "the bot" in the abstract describes none of
# them truthfully. So this file owns the shape and the handlers, and each
# bot's i18n.py owns two keys: "privacy_stored", the list of what it actually
# keeps, and "privacy_others", whoever outside the family it has to talk to.
# The long forms live in PRIVACY.md and TERMS.md in each bot's repository.

# Who is running this copy, and how to reach them. A privacy notice that
# cannot name someone to complain to is a notice about nobody. Left blank the
# commands still work and omit the line, which is the honest result for a
# local test instance -- better than printing an address that goes nowhere.
# The owner's contact, as the default rather than only an environment
# variable: an unset variable on one Railway service used to mean that bot's
# /privacy named nobody. A deployment run by somebody else sets its own.
OPERATOR_CONTACT = (os.environ.get("OPERATOR_CONTACT") or "mukhtorovmurodbek@gmail.com").strip()
# Where the long forms were published, if they were. publish.ps1 pushes
# PRIVACY.md and TERMS.md to each bot's public repository, which gives them a
# URL; this is where that URL goes, and it is also what BotFather wants.
PRIVACY_URL = os.environ.get("PRIVACY_URL", "").strip()
TERMS_URL = os.environ.get("TERMS_URL", "").strip()


def _policy_footer(lang: str, url: str) -> str:
    """The two optional trailing lines, each dropped when unconfigured.

    The URL is the one thing here that is not escaped and must not be: it goes
    inside an anchor so that it is tappable, and the label is the address
    itself, because a privacy notice is the wrong place to hide where a link
    goes behind a word."""
    lines = []
    if url:
        label = esc(url)
        lines.append(body(i18n.t(lang, "policy_full_text", url="\x00"))
                     .replace("\x00", f'<a href="{label}">{label}</a>'))
    if OPERATOR_CONTACT:
        lines.append(body(i18n.t(lang, "policy_contact", contact=OPERATOR_CONTACT)))
    return "\n".join(lines)


def privacy_text(lang: str) -> str:
    """The notice, laid out so its shape is visible without scrolling.

    The two long blocks -- the list of what is kept, and the retention
    paragraphs -- are the ones that go behind a tap. What stays on screen is
    every heading, who else sees it, and the line offering /deletemydata,
    which is what somebody opening /privacy is usually looking for.
    """
    return joined(
        heading(i18n.t(lang, "privacy_heading")),
        heading(i18n.t(lang, "privacy_kept_heading")) + "\n"
        + collapsed(i18n.t(lang, "privacy_stored")),
        heading(i18n.t(lang, "privacy_problems_heading")) + "\n"
        + collapsed(i18n.t(lang, "privacy_problems")),
        heading(i18n.t(lang, "privacy_seen_by_heading")) + "\n"
        + body(i18n.t(lang, "privacy_seen_by")) + "\n"
        + body(i18n.t(lang, "privacy_others")),
        heading(i18n.t(lang, "privacy_kept_for_heading")) + "\n"
        + collapsed(i18n.t(lang, "privacy_kept_for")),
        lead_in(i18n.t(lang, "privacy_your_choices")),
        _policy_footer(lang, PRIVACY_URL),
    )


def terms_text(lang: str) -> str:
    """Four paragraphs, three of which already open with their own label and a
    colon -- in all three languages, because that is how the sentences were
    written. lead_in() promotes those to headings; the one without is left as
    a paragraph, which is what it is."""
    return joined(
        heading(i18n.t(lang, "terms_heading")),
        body(i18n.t(lang, "terms_use")),
        lead_in(i18n.t(lang, "terms_specific")),
        lead_in(i18n.t(lang, "terms_money")),
        lead_in(i18n.t(lang, "terms_no_warranty")),
        _policy_footer(lang, TERMS_URL),
    )


async def privacy_command(update, context) -> None:
    lang = await i18n.get_lang(update.effective_user.id, context)
    await reply_formatted(update.message, privacy_text(lang))


async def terms_command(update, context) -> None:
    lang = await i18n.get_lang(update.effective_user.id, context)
    await reply_formatted(update.message, terms_text(lang))


# ---- erasure ----
# Two taps rather than one, because there is no undo and on a phone keyboard
# the command is a slip away from /donate. The confirmation spells out what
# goes and what does not, per bot: erasing a StickerBot user forgets their
# packs without deleting the packs themselves, which live on Telegram's
# servers and not here, and erasing an AnonBot inbox owner breaks every copy
# of their link that anybody has posted. Both are the right thing to do when
# asked and the wrong thing to find out about afterwards.

ERASE_PREFIX = "erasedata:"


def erase_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(i18n.t(lang, "delete_data_button_yes"), callback_data=ERASE_PREFIX + "yes"),
        InlineKeyboardButton(i18n.t(lang, "delete_data_button_no"), callback_data=ERASE_PREFIX + "no"),
    ]])


async def paysupport_command(update, context) -> None:
    """/paysupport -- required of every bot that takes Telegram Stars.

    Telegram's rules for digital goods say a bot must answer /paysupport and
    handle payment problems itself. The owner decided payments are final, so
    this says that first, and then how a payment that went wrong -- charged
    with no credit to show for it -- reaches somebody who can put it right,
    which here means with credit rather than with Stars."""
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)
    await update.message.reply_text(i18n.t(
        lang, "paysupport_text", contact=OPERATOR_CONTACT or "@BotFather", user_id=user.id))


async def delete_my_data_command(update, context):
    """Returns None on purpose. StickerBot registers this as one of its
    ConversationHandler's entry points -- same reasoning as the language
    switches there -- and an entry point returning None leaves the state
    machine exactly where it was, which is what asking a question should do.
    Only the answer below moves anything."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    # The consequences stay on screen rather than going behind a tap. This is
    # the one message in the family where the detail is the point: it is what
    # somebody needs to have read before they press a button that has no undo.
    await reply_formatted(
        update.message,
        joined(heading(i18n.t(lang, "delete_data_confirm")),
               body(i18n.t(lang, "delete_data_consequences"))),
        reply_markup=erase_keyboard(lang),
    )


async def delete_my_data_chosen(update, context):
    """Every edit goes through live_message.edit_in_place rather than
    query.edit_message_text, for the two reasons that helper exists. It never
    raises -- and this one really can be asked to write the same text twice,
    by somebody who taps a second, older confirmation after the first erase
    already reported nothing to erase -- and it moves the message down to the
    bottom if the person has said something since.

    Returns ConversationHandler.END after an erase, which StickerBot's entry
    points honour. Without it the state machine would sit in EDITING pointing
    at a pack this bot has just forgotten, and the next sticker would raise
    KeyError('owner_id') and page the owner about a crash that was really
    somebody exercising their right to be forgotten.
    """
    query = update.callback_query
    await query.answer()
    lang = await i18n.get_lang(update.effective_user.id, context)
    if query.data != ERASE_PREFIX + "yes":
        await live_message.edit_in_place(
            query.message, context.bot, body(i18n.t(lang, "delete_data_kept")), parse_mode=ParseMode.HTML
        )
        return None

    user_id = update.effective_user.id
    # The two erasures are reported on separately, and deliberately not in
    # one try. db.erase_user is a single transaction over this bot's own
    # tables: it either happened or it did not, and that is what the person
    # is being told about. lifecycle.forget_user clears a cache of work in
    # progress that expires by itself within the day, so failing it does not
    # make the answer above it untrue -- and saying "couldn't erase that"
    # after the data is already gone is the one answer this command must
    # never give.
    try:
        rows = await asyncio.to_thread(db.erase_user, user_id)
    except Exception:
        logging.getLogger(__name__).exception("Erasing user %s failed", user_id)
        await live_message.edit_in_place(
            query.message, context.bot, body(i18n.t(lang, "delete_data_failed")), parse_mode=ParseMode.HTML
        )
        return None
    try:
        rows += await asyncio.to_thread(lifecycle.forget_user, user_id)
    except Exception:
        logging.getLogger(__name__).exception(
            "Cleared %s's data but could not clear their saved state", user_id
        )
    # The family table, which is not this bot's own and so is not in
    # db.erase_user. Only the part that is about them: a problem they reported
    # still counts as a problem afterwards, it just no longer says who hit it.
    # Reported on separately for the same reason as the line above -- failing
    # it does not make "your data is gone" untrue of the tables that did.
    try:
        rows += await asyncio.to_thread(family_link.forget_problem_reporter, user_id)
    except Exception:
        logging.getLogger(__name__).exception(
            "Cleared %s's data but could not take them off their problem reports", user_id
        )

    # Rendered before the cache is dropped, because the chosen language is
    # part of what is being erased.
    done = body(i18n.t(lang, "delete_data_done", rows=rows))
    # Whatever the process still holds in memory, so the persistence flush a
    # minute later does not write a fresh row straight back out again.
    try:
        context.application.drop_user_data(user_id)
    except Exception:
        logging.getLogger(__name__).debug("Nothing cached for %s to drop", user_id)
    await live_message.edit_in_place(
        query.message, context.bot, done, parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /cancel -- getting out of whatever the bot is waiting for
# ---------------------------------------------------------------------------
# Every bot has at least one state where it has asked a question and is now
# sitting there waiting for the answer, and until this existed there was no
# single way out of them.
#
# /cancel asks before it does anything. A bot juggling a pack, a conversion
# and a donation prompt at once had one /cancel that stopped all three, and
# no way to say which one you meant -- so the command that exists to undo a
# mistake was itself the mistake, if what you wanted was to abandon the pack
# and keep the conversion. It now offers one button per waiting thing, plus
# "everything" when there is more than one and "keep going" always. Nothing
# is stopped until a button is tapped.
#
# The exception, and it is the common case, is having nothing to cancel:
# with no pending state there is nothing to ask about, so /cancel answers
# straight away exactly as it always did.
#
# Each bot builds its own /cancel out of the pieces below: cancel_items()
# for the states this file owns, cancel_question() and the *_choice helpers
# for the asking, release_force_reply() for Telegram's client-side reply
# lock, and build_cancel_text() so all of them report back in the same
# shape. Reporting *what* was stopped is the point, not decoration.

# Where the id of the last ForceReply prompt this bot sent is parked.
FORCE_REPLY_KEY = "force_reply_msg_id"


def remember_force_reply(context, message) -> None:
    """Call right after sending anything carrying a ForceReply, so /cancel
    can delete it again. Cheap, and the entry is dropped by the handler that
    consumes the reply or by release_force_reply(), whichever comes first."""
    context.user_data[FORCE_REPLY_KEY] = message.message_id


async def release_force_reply(update, context, stored_only: bool = False) -> bool:
    """Let go of a forced reply.

    ForceReply lives on the *client*, not on the server: once a bot sends a
    message carrying one, that user's reply box stays pinned to that message
    until they answer it or it stops existing. Nothing about restarting the
    bot, or even the database, releases it -- which is how a "how many Stars
    would you like to donate?" prompt can still be demanding an answer two
    days and several redeployments later. Deleting the prompt is the only
    lever a bot actually has.

    Two ways to find it, because the first stops working the moment the
    process restarts and takes user_data with it:
      1. the id remember_force_reply() stored when we sent it, and
      2. the message this /cancel is itself a reply to -- which is exactly
         what it will be, since a forced reply box is what the user was
         looking at when they typed it.

    stored_only turns (2) off, for the button path: there, the message being
    "replied to" is the bot's own "which one?" question, whose reply target
    is the user's /cancel. Deleting that would be deleting the wrong message
    entirely -- theirs. ask_cancel_choice stores the id under (1) before the
    question goes out, so nothing is lost by ignoring (2) here.

    Best-effort throughout. Telegram only lets a bot delete messages under
    48 hours old, so an old enough prompt cannot be removed at all; that is
    what the ReplyKeyboardRemove in build_cancel_text()'s caller is for, as
    it clears the reply lock client-side regardless of the prompt's age.
    """
    chat = update.effective_chat
    if chat is None:
        return False
    ids = []
    stored = context.user_data.pop(FORCE_REPLY_KEY, None)
    if stored:
        ids.append(stored)
    replied_to = None if stored_only else getattr(update.effective_message, "reply_to_message", None)
    if replied_to is not None and replied_to.message_id not in ids:
        ids.append(replied_to.message_id)
    released = False
    for message_id in ids:
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=message_id)
            released = True
        except Exception:
            # Already gone, too old to delete, or never ours. None of those
            # are worth failing a /cancel over.
            logging.getLogger(__name__).debug(
                "Could not delete force-reply prompt %s", message_id, exc_info=True
            )
    return released


def reset_user_state(context, keep: dict | None = None) -> None:
    """user_data.clear(), minus the one key /cancel is not finished with.

    A bot whose /cancel wipes user_data has to do it *before*
    release_force_reply() gets a chance to read the prompt id out of it,
    which quietly cost StickerBot the ability to take its own donation
    prompt back down. Keeping the key here rather than making every caller
    remember the ordering is the version that stays correct."""
    preserved = {k: context.user_data[k] for k in (FORCE_REPLY_KEY,) if k in context.user_data}
    context.user_data.clear()
    context.user_data.update(preserved)
    if keep:
        context.user_data.update(keep)


# What /cancel offers, one per thing the bot is waiting on:
#   key    -- goes in the button's callback_data, and comes back to the bot
#   label  -- how the "Cancelled:" report names it, a full phrase
#   button -- how the button names it, short enough to read on a phone
CancelItem = namedtuple("CancelItem", "key label button")

CANCEL_PICK_PREFIX = "cancelpick:"
CANCEL_PICK_ALL = "all"
CANCEL_PICK_NONE = "none"


def cancel_items(context, lang: str) -> list[CancelItem]:
    """The waiting-on-the-user states that live in this file, for the calling
    bot to offer alongside its own. Reads state; changes none of it -- that
    is cancel_shared_item's job, once the user has actually chosen."""
    items = []
    if context.user_data.get("donate_custom_currency"):
        items.append(CancelItem("donation",
                                i18n.t(lang, "cancel_item_donation"),
                                i18n.t(lang, "cancel_button_donation")))
    return items


def cancel_shared_item(context, lang: str, key: str) -> str | None:
    """Stop one of this file's states by key. Returns how to report it, or
    None if that key is not ours or was not pending after all."""
    if key == "donation" and context.user_data.pop("donate_custom_currency", None):
        return i18n.t(lang, "cancel_item_donation")
    return None


def cancel_question(lang: str, items: list[CancelItem]):
    """The "which one?" message: what is pending, and a button each.

    One button per row rather than a grid -- these are full phrases, not
    yes/no, and a two-column layout truncates them on a phone. "Everything"
    only appears when there is more than one thing it could mean, and "keep
    going" always does, because opening this menu must not be a one-way
    door: /cancel is what people reach for when they are already unsure.
    """
    text = i18n.t(lang, "cancel_ask") + "\n" + "\n".join(
        f"\u2022 {item.label}" for item in items
    )
    rows = [[InlineKeyboardButton(item.button, callback_data=CANCEL_PICK_PREFIX + item.key)]
            for item in items]
    if len(items) > 1:
        rows.append([InlineKeyboardButton(i18n.t(lang, "cancel_button_all"),
                                          callback_data=CANCEL_PICK_PREFIX + CANCEL_PICK_ALL)])
    rows.append([InlineKeyboardButton(i18n.t(lang, "cancel_button_none"),
                                      callback_data=CANCEL_PICK_PREFIX + CANCEL_PICK_NONE)])
    return text, InlineKeyboardMarkup(rows)


async def ask_cancel_choice(update, context, items: list[CancelItem], lang: str) -> bool:
    """Put the question on screen. False means there was nothing to ask
    about, and the caller should answer the old way -- see finish_cancel.

    Remembers what /cancel was a reply to, because the answer arrives as a
    button tap on a different message and release_force_reply would have no
    way to find the prompt otherwise.
    """
    if not items:
        return False
    replied_to = getattr(update.effective_message, "reply_to_message", None)
    if replied_to is not None and FORCE_REPLY_KEY not in context.user_data:
        context.user_data[FORCE_REPLY_KEY] = replied_to.message_id
    text, keyboard = cancel_question(lang, items)
    await update.effective_message.reply_text(text, reply_markup=keyboard)
    return True


def cancel_choice_key(update) -> str:
    """The key behind the tapped button -- an item's own, or "all"/"none"."""
    return update.callback_query.data.split(":", 1)[1]


def build_cancel_text(lang: str, stopped: list[str]) -> str:
    if not stopped:
        return i18n.t(lang, "cancel_nothing")
    return i18n.t(lang, "cancel_header") + "\n" + "\n".join(f"\u2022 {item}" for item in stopped)


async def finish_cancel(update, context, lang: str, stopped: list[str],
                        stored_only: bool = False) -> None:
    """The last two steps of every bot's /cancel: release the reply lock and
    say what was stopped. ReplyKeyboardRemove is what actually unpins the
    reply box on the client when the prompt itself was too old to delete.

    `stored_only` turns off release_force_reply's second route -- "delete
    whatever this /cancel is a reply to" -- for bots where that guess is
    expensive to get wrong. It is a good guess when every message a bot sends
    is a menu or a status line, and a bad one when its messages are the
    product: AnonBot's are somebody's conversation, and `/cancel` sent as a
    reply to one used to delete it and report a prompt that never existed.

    The default is unchanged for the three bots whose messages are menus.
    They are not entirely safe from it either -- a `/cancel` replying to a
    converted file or a finished download deletes that too -- but the fix
    there is a judgement about those bots, not a side effect of this one.
    """
    released = await release_force_reply(update, context, stored_only=stored_only)
    # A prompt we could still delete, but nothing in memory to go with it, is
    # the signature of one that outlived the process that sent it: user_data
    # does not survive a restart, but Telegram's reply lock does. Saying
    # "nothing to cancel" while visibly deleting the thing that was pestering
    # them is the one answer that would make no sense here.
    if released and not stopped:
        stopped = [i18n.t(lang, "cancel_item_stale_prompt")]
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        build_cancel_text(lang, stopped),
        reply_markup=ReplyKeyboardRemove(),
    )


async def finish_cancel_choice(update, context, lang: str, stopped: list[str]) -> None:
    """finish_cancel's twin for the button path.

    The question message becomes the report, which is both tidier than a
    reply underneath it and the only way to make sure a set of buttons that
    has already been acted on cannot be tapped a second time.

    An edit cannot carry ReplyKeyboardRemove, so the client-side reply lock
    gets its own one-line message -- but only in the case that actually
    needs it: a prompt we knew about and could not delete, which means it is
    over Telegram's 48-hour deletion limit and still pinning the reply box.
    A prompt old enough for that has almost always outlived the process that
    sent it, in which case nothing is pending, nothing was asked, and this
    path was never reached at all.
    """
    query = update.callback_query
    had_prompt = FORCE_REPLY_KEY in context.user_data
    released = await release_force_reply(update, context, stored_only=True)
    if released and not stopped:
        stopped = [i18n.t(lang, "cancel_item_stale_prompt")]
    text = build_cancel_text(lang, stopped)
    # Through live_message rather than edit_text: if the user has typed
    # anything since tapping, this report belongs at the bottom of the chat
    # with their message, not rewritten above it. It handles the send itself,
    # and never raises, so there is no fallback left to write here.
    await live_message.edit_in_place(query.message, context.bot, text)
    if had_prompt and not released:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=i18n.t(lang, "cancel_reply_box_freed"),
            reply_markup=ReplyKeyboardRemove(),
        )


async def keep_going(update, context, lang: str) -> None:
    """"Keep going" -- the way back out of the question, having changed
    nothing. The menu is replaced rather than left sitting there with live
    buttons under an answer that has already been given."""
    await live_message.edit_in_place(
        update.callback_query.message, context.bot, i18n.t(lang, "cancel_kept")
    )


# ---------------------------------------------------------------------------
# Logging, crash tracking, active-user tracking, hosting detection --
# all in support of each bot's owner-only /status command.
# ---------------------------------------------------------------------------
# Each bot's own process gets its own logs/ folder (next to its bot.py) --
# same "no shared files between bots" independence as everything else here.
# bot.log gets everything at INFO+; errors.log gets WARNING+ only, from any
# logger in the process (not just the PTB error handler below), so a stray
# warning logged deep in some helper module still ends up somewhere findable
# without needing to grep the full bot.log.

_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

# In-memory only -- resets on restart, which conveniently lines up with
# "since this deployment" rather than needing its own DB table. Capped at 10
# so a crash loop can't blow up memory; the running _error_count below still
# reflects the true total even once older entries fall off the deque.
_recent_errors: deque[tuple[str, str]] = deque(maxlen=10)
_error_count = 0

# Set by family_link.attach() to family_link.report_event_soon, so anything
# worth waking the owner up for also reaches ManagerBot. Left as None when a
# bot runs standalone (FAMILY_BUS=off, or no shared database reachable) --
# every call site below tolerates that, and none of them may ever raise:
# the most important caller is record_error(), i.e. the crash path itself.
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
    """Files on a laptop, stdout only in the cloud.

    On a host like Railway the container's filesystem is ephemeral and the
    platform's own log viewer already captures stdout, so the rotating files
    are three handlers' worth of formatting plus up to 12 MB of disk writes
    that nobody will ever read -- and disk writes are the slowest thing a
    small container does. LOG_TO_FILES=1 forces them back on anywhere;
    LOG_TO_FILES=0 forces them off locally."""
    override = os.environ.get("LOG_TO_FILES")
    if override is not None:
        return override.strip().lower() in ("1", "true", "yes", "on")
    return not (os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT"))


def setup_logging(bot_file: str) -> None:
    """Call once near the top of each bot's bot.py, passing __file__.

    Always logs to the console -- that is what `docker logs` and Railway's
    log viewer show. Adds rotating bot.log/errors.log files next to that
    file when running somewhere they will actually survive (see
    _log_to_files above)."""
    fmt = logging.Formatter(_LOG_FORMAT)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # These three are chatty at INFO -- httpx logs a line per HTTP request,
    # which for a long-polling bot means one every few seconds, forever, for
    # no information at all. Warnings and above still come through.
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


# ---------------------------------------------------------------------------
# Transient network conditions vs. actual faults
# ---------------------------------------------------------------------------
# A long poll losing its connection, a read timing out, Telegram asking us to
# slow down: PTB retries all of these itself and the bot keeps working, so
# waking the owner with a traceback for each one is noise that trains you to
# ignore the channel that also carries real crashes.
#
# The catch is PTB's class hierarchy: BadRequest *subclasses* NetworkError,
# and a BadRequest is a genuine fault -- a malformed API call, our bug -- so a
# plain `isinstance(exc, NetworkError)` would swallow exactly the errors most
# worth hearing about. It has to be excluded explicitly.

TRANSIENT_NETWORK_ERRORS = (NetworkError, RetryAfter)

# How many blips in a row before saying something. Reset by any update that
# arrives, since one arriving proves the connection is working again. Roughly
# a few minutes of a dead link at a 30-second poll.
NETWORK_ALERT_AFTER = int(os.environ.get("NETWORK_ALERT_AFTER", "20"))

_network_blips = 0        # consecutive, since the last update actually arrived
_network_blips_total = 0  # since this process started
_network_alerted = False


# PTB raises Telegram's HTTP 413 -- "Request Entity Too Large" -- as a plain
# NetworkError, so it matched the tuple above and was filed as a flaky
# connection. It is the opposite: permanent, and the same upload fails every
# time. That is how two successful ConvertBot conversions of a 200 MP photo
# vanished -- result converted, upload refused, error handler said "retried
# by PTB", user told nothing, credit kept. Anything whose text says the
# payload is too big is a real failure, whatever class it arrived as.
PERMANENT_NETWORK_MESSAGES = ("entity too large", "file is too big", "too big", "too large")


def is_transient_network_error(exc: BaseException) -> bool:
    if not isinstance(exc, TRANSIENT_NETWORK_ERRORS) or isinstance(exc, BadRequest):
        return False
    text = str(exc).lower()
    return not any(marker in text for marker in PERMANENT_NETWORK_MESSAGES)


def note_network_blip(exc: BaseException) -> None:
    """Counted and logged, never reported as a crash -- until there have been
    enough in a row to mean the connection is gone rather than flaky, which is
    worth exactly one message."""
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
    """An update arrived, so the connection works. Called from track_activity,
    which runs before every other handler."""
    global _network_blips, _network_alerted
    if _network_blips and _network_alerted:
        emit_event("info", "network", "Telegram is reachable again.")
    _network_blips = 0
    _network_alerted = False


def record_error(exc: BaseException) -> None:
    global _error_count
    _error_count += 1
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    _recent_errors.append((stamp, repr(exc)))
    emit_event(
        "error", "crash", f"Unhandled {type(exc).__name__}: {exc}",
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


# ---------------------------------------------------------------------------
# Problem codes, and the button that reports one
# ---------------------------------------------------------------------------
# The owner: "Give every possible exception that the user might trigger a code
# or a unique identifier. If user triggers something with such an error, they
# should get a button too, that says 'report the issue'." The codes and what
# they mean are in problems.py; i18n.t() ends every coded message with its
# code line.
#
# Both happen at the one place every message leaves through -- the bot's own
# send_message, edit_message_text and answer_callback_query -- rather than at a
# hundred call sites, each of which would be one more place to forget them.
# Every message that ends in a known code is logged with its time, code and a
# fresh incident id. The problems worth reporting also get a Report row beside
# whatever buttons they already had, carrying that same incident, so a report
# and its log line meet. The owner, about a Report button under "I don't
# recognize that command": "not every command needs a report button. But keep
# the report itself. Every exception should be logged inside the bot
# automatically with time and id, but this one is simple." Which problems are
# simple is problems.SIMPLE.
#
# **The problem is written down whether or not anybody taps anything.** The
# owner, in 1.7.0: "It should include the error without user pressing the
# report button, but should only store generic technical data with no user
# specific info, and that this issue is logged with no user data." So every
# coded message any bot sends puts a row in family.problem_reports holding the
# bot, the code, the incident, the time and the version -- and says so, on the
# message, above the button.
#
# That changes what the button is for. It used to be the only way a problem
# reached the owner at all, which made "Report the issue" a chore somebody did
# on the bot's behalf. Now the problem is already there, and tapping adds the
# one thing it cannot have without asking: who it happened to. The owner:
# "If the user wants to help, they can press the report button to include user
# specific data - type of data should be mentioned before actually sending the
# user details." The disclaimer names each field before anything is sent, and
# nothing is sent until Send is tapped.
#
# What goes to the owner's Telegram is still only that a report arrived, with
# the code and the incident. Who sent it is read with ManagerBot's /report
# <incident>, deliberately, rather than pushed at them unasked.

REPORTS_TO = int(os.environ.get("FAMILY_REPORTS_TO") or 8796896653)
REPORT_BUTTONS = (os.environ.get("FAMILY_REPORT_BUTTONS") or "on").strip().lower() not in ("0", "off", "no", "false")

# Recording every problem could not go on the sending path. A coded message is
# sent from inside a failure, often several at once -- FM-FLOOD is by
# definition many people at the same moment -- and a Postgres round trip there
# would add the database to the list of things that can go wrong while the bot
# is already going wrong, and add it to the *user's* wait.
#
# So occurrences collect here and go out as one pass on a timer, the same
# shape as the activity buffer further down for the same reason. A hard kill
# loses at most one window of them, and they are in this bot's own problems.log
# either way.
PROBLEM_FLUSH_SECONDS = int(os.environ.get("PROBLEM_FLUSH_SECONDS", "20"))
MAX_BUFFERED_PROBLEMS = 500

# ---------------------------------------------------------------------------
# Which problems interrupt the owner, and how often
# ---------------------------------------------------------------------------
# problems.level() says what a code is worth (1 urgent / 2 fault / 3 refused).
# Two rules turn that into messages:
#
#   An urgent problem is sent the moment it happens -- but at most once per
#   code per ALERT_COOLDOWN_SECONDS. A crash loop is one fault, not four
#   hundred, and four hundred messages is the fastest way to make somebody
#   stop reading the one that mattered. What the cooldown suppresses is
#   counted and carried into the next alert for that code.
#
#   A *fault* escalates to an urgent alert when the same code happens
#   BURST_COUNT times inside BURST_WINDOW_SECONDS. Fifty "all download routes
#   failed" in an hour is not fifty people having bad luck, it is a route that
#   has gone down -- which is a level-1 fact assembled out of level-2 parts,
#   and the only way to notice it on the day rather than in the nightly
#   report.
ALERT_COOLDOWN_SECONDS = int(os.environ.get("PROBLEM_ALERT_COOLDOWN_SECONDS", "900"))
BURST_COUNT = int(os.environ.get("PROBLEM_BURST_COUNT", "15"))
BURST_WINDOW_SECONDS = int(os.environ.get("PROBLEM_BURST_WINDOW_SECONDS", "3600"))

_problem_buffer: "OrderedDict[tuple, object]" = OrderedDict()
# code -> (monotonic time of the last alert, how many were suppressed since)
_alerted: "dict[str, list]" = {}
# code -> deque of monotonic times, for the burst rule
_recent_faults: "dict[str, deque]" = {}


def _should_alert(code: str, now: float) -> "tuple[bool, int]":
    """(send one now?, how many went unreported since the last one).

    The whole cooldown lives here rather than in the caller, so the counting
    and the decision cannot drift apart."""
    last, suppressed = _alerted.get(code, (None, 0))
    if last is not None and now - last < ALERT_COOLDOWN_SECONDS:
        _alerted[code] = [last, suppressed + 1]
        return False, 0
    _alerted[code] = [now, 0]
    return True, suppressed


def _is_burst(code: str, now: float) -> bool:
    """Whether this code has just crossed the burst threshold."""
    seen = _recent_faults.setdefault(code, deque())
    seen.append(now)
    while seen and now - seen[0] > BURST_WINDOW_SECONDS:
        seen.popleft()
    return len(seen) >= BURST_COUNT


def _alert_owner(code: str, incident: str, level: int, now: float) -> None:
    """Put an urgent problem on the family event bus, which is what ManagerBot
    forwards to the owner. Nothing here identifies anybody: the code, the
    incident and how many there were.

    An event, not a direct message: the bots do not hold the owner's chat and
    should not learn to. ManagerBot already decides what is worth a message
    (its ALERT_LEVELS) and already handles the owner never having started a
    bot, so this rides the rail that exists."""
    send, suppressed = _should_alert(code, now)
    if not send:
        return
    problem = problems.PROBLEMS.get(code)
    title = problem.title if problem else code
    burst = level != problems.level(code)
    message = f"{code} — {title}"
    if burst:
        message += (f" — {BURST_COUNT}+ of these in the last "
                    f"{BURST_WINDOW_SECONDS // 60} minutes, so this looks like it is down "
                    f"rather than unlucky")
    if suppressed:
        message += f" (+{suppressed} more since the last alert)"
    emit_event("critical" if not burst else "error", "problem",
               message, f"Incident {incident} · /report {incident} for anything a user added")


def note_occurrence(code: str, incident: str, occurred_at) -> None:
    """Remember that this problem was shown, to be written out on the next
    pass -- and interrupt the owner if it is the kind that cannot wait.

    Keyed by incident, so a message redrawn with the same problem still on it
    is one occurrence here as well as one line in the log."""
    key = (code, incident)
    if key in _problem_buffer:
        return
    _problem_buffer[key] = occurred_at
    level = problems.level(code)
    try:
        now = time.monotonic()
        if level == problems.URGENT:
            _alert_owner(code, incident, problems.URGENT, now)
        elif level == problems.FAULT and _is_burst(code, now):
            _alert_owner(code, incident, problems.URGENT, now)
    except Exception:
        # An alert that fails must never cost the record it was alerting
        # about -- the row below is the thing that has to survive.
        logging.getLogger(__name__).debug("Could not alert on %s", code, exc_info=True)
    # A ceiling rather than unbounded growth: if the database is unreachable
    # for an hour the buffer must not become the reason the container dies.
    # The oldest go, because the newest are the ones somebody might still be
    # looking at a Report button for.
    while len(_problem_buffer) > MAX_BUFFERED_PROBLEMS:
        _problem_buffer.popitem(last=False)


def _flush_problems_now() -> int:
    """Blocking; call through asyncio.to_thread. Takes the whole buffer in one
    swap so a problem arriving mid-flush lands in the next window rather than
    being lost."""
    global _problem_buffer
    if not _problem_buffer:
        return 0
    batch, _problem_buffer = _problem_buffer, OrderedDict()
    written = 0
    for (code, incident), occurred_at in batch.items():
        try:
            family_link.record_problem_occurrence(code, incident, occurred_at,
                                                  problems.level(code))
            written += 1
        except Exception:
            # Put back what is left, including this one, and stop: a database
            # that refused one row will refuse the next forty too.
            leftover = OrderedDict(list(batch.items())[written:])
            leftover.update(_problem_buffer)
            _problem_buffer = leftover
            raise
    return written


async def _flush_problems_job(context) -> None:
    try:
        await asyncio.to_thread(_flush_problems_now)
    except Exception:
        logging.getLogger(__name__).debug("Problem flush failed; will retry", exc_info=True)

_chat_langs: "OrderedDict[int, str]" = OrderedDict()


def remember_chat_lang(chat_id, lang) -> None:
    """The language a chat was last seen in, for labelling a report button on
    a message that is already on its way out."""
    if not chat_id or not lang:
        return
    _chat_langs[chat_id] = lang
    _chat_langs.move_to_end(chat_id)
    while len(_chat_langs) > 4096:
        _chat_langs.popitem(last=False)


def report_markup(lang: str, code: str, incident: str, markup=None):
    """`markup` with a Report row added, or a keyboard holding only that row.
    Left as it is for a problem too simple to need one (problems.SIMPLE), with
    the buttons switched off, and for a keyboard that already has one or is a
    reply keyboard."""
    if (not REPORT_BUTTONS or not problems.reportable(code) or _has_report(markup)
            or (markup is not None and not isinstance(markup, InlineKeyboardMarkup))):
        return markup
    rows = [list(row) for row in markup.inline_keyboard] if markup is not None else []
    rows.append([InlineKeyboardButton(i18n.t(lang, "report_button"),
                                      callback_data=f"rpt:{code}:{incident}")])
    return InlineKeyboardMarkup(rows)


def _with_logged_note(text: str, code: str, lang: str) -> str:
    """The same message, with one line saying it has already been written down
    and that nothing in what was written is about them.

    Above the code line, never below it: problems.find_code only recognises a
    code at the very end, and a note underneath it would make every one of
    these messages uncoded to everything that reads them afterwards -- the
    Report button included.

    Only on problems that offer a button, which is where somebody is being
    asked to decide something. "I don't recognize that command" explains
    itself and does not need a paragraph about logging under it.
    """
    note = i18n.t(lang, "problem_logged_note")
    body = problems.strip_code(text)
    if note in body:
        return text
    return f"{body}\n\n{note}{problems.code_line(code)}"


def _has_report(markup) -> bool:
    return any((getattr(button, "callback_data", None) or "").startswith("rpt")
               for row in getattr(markup, "inline_keyboard", None) or () for button in row)


def _button_incident(markup) -> "str | None":
    """The incident a Report button made elsewhere already carries -- a
    conversion's ending, or a crash notice, whose incident is also in the
    owner's alert or beside the traceback."""
    for row in getattr(markup, "inline_keyboard", None) or ():
        for button in row:
            data = getattr(button, "callback_data", None) or ""
            if data.startswith("rpt:"):
                return data.rsplit(":", 1)[-1]
    return None


# Every problem shown, one line each: when (the log line's own time), which
# code, which incident, and whether it offered a Report button. Nothing about
# who it happened to. Into bot.log with everything else, into problems.log of
# its own wherever the bot writes log files, and into the lines ManagerBot's
# /problemlog reads either way (family_link.keep_recent_log_lines).
problem_log = logging.getLogger("problems")

# One incident per occurrence. A message redrawn with the same problem still on
# it -- a status line refreshed, a menu re-rendered -- keeps the incident it was
# first shown with, so it is logged once and a Report button on it still
# matches.
_incidents: "OrderedDict[tuple, str]" = OrderedDict()


def _remember_incident(chat_id, message_id, code: str, incident: str) -> None:
    if chat_id is None or message_id is None:
        return
    key = (chat_id, message_id, code)
    _incidents[key] = incident
    _incidents.move_to_end(key)
    while len(_incidents) > 4096:
        _incidents.popitem(last=False)


async def note_problem(chat_id, message_id, text, kwargs: dict):
    """A message on its way out. If it ends in a problem code: log it, write it
    down for the owner, and give it a Report button if the problem deserves
    one. Returns (code, incident, text) -- the text possibly grown by a line
    saying the problem is already recorded -- or (None, None, text) for a
    message with no code."""
    code = problems.find_code(text) if isinstance(text, str) else None
    if not code:
        return None, None, text
    markup = kwargs.get("reply_markup")
    made = _button_incident(markup)
    known = _incidents.get((chat_id, message_id, code)) if message_id is not None else None
    incident = made or known or problems.new_incident()
    wants_button = (made is None and REPORT_BUTTONS and problems.reportable(code)
                    and (markup is None or isinstance(markup, InlineKeyboardMarkup)))
    if wants_button or problems.reportable(code):
        lang = _chat_langs.get(chat_id)
        if lang is None and isinstance(chat_id, int):
            try:
                lang = await asyncio.to_thread(db.get_user_language, chat_id)
            except Exception:
                lang = None
            remember_chat_lang(chat_id, lang)
        lang = lang or "en"
        if wants_button:
            try:
                kwargs["reply_markup"] = report_markup(lang, code, incident, markup)
            except Exception:
                logging.getLogger(__name__).debug("Could not add a report button", exc_info=True)
        try:
            text = _with_logged_note(text, code, lang)
        except Exception:
            logging.getLogger(__name__).debug("Could not add the logged note", exc_info=True)
    if incident != known:
        problem_log.info("%s incident %s, %s", code, incident,
                         "with a Report button" if _has_report(kwargs.get("reply_markup"))
                         else "no Report button")
        # Every problem, not only the ones somebody chooses to report, and not
        # only the ones that offer a button. Buffered -- see note_occurrence.
        note_occurrence(code, incident, datetime.now(timezone.utc))
    _remember_incident(chat_id, message_id, code, incident)
    return code, incident, text


def _log_problems_to_file() -> None:
    """problems.log beside bot.log, wherever setup_logging() writes files."""
    if any(isinstance(handler, RotatingFileHandler) for handler in problem_log.handlers):
        return
    for handler in logging.getLogger().handlers:
        if isinstance(handler, RotatingFileHandler):
            problem_file = RotatingFileHandler(
                os.path.join(os.path.dirname(handler.baseFilename), "problems.log"),
                maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            problem_file.setFormatter(handler.formatter)
            problem_log.addHandler(problem_file)
            return


def attach_problem_reports(application) -> None:
    """Log every problem this bot shows, and put a Report button under the ones
    that deserve it. Call once in main(), after the application is built.

    Done by giving the bot object a subclass of its own class whose send, edit
    and pop-up methods look at the text and hand over. python-telegram-bot
    objects refuse ordinary attribute assignment once built, so the class is
    swapped with object.__setattr__; if that is ever refused the codes still
    show, and the log says the logging and the buttons are off."""
    _log_problems_to_file()
    bot = getattr(application, "bot", None)
    base = type(bot)
    if bot is None or getattr(base, "_reports_problems", False) or not hasattr(base, "send_message"):
        return

    async def send_message(self, chat_id, text, *args, **kwargs):
        code, incident, text = await note_problem(chat_id, None, text, kwargs)
        sent = await base.send_message(self, chat_id, text, *args, **kwargs)
        if code:
            _remember_incident(chat_id, getattr(sent, "message_id", None), code, incident)
        return sent

    async def edit_message_text(self, text, *args, **kwargs):
        chat_id = kwargs.get("chat_id", args[0] if args else None)
        message_id = kwargs.get("message_id", args[1] if len(args) > 1 else None)
        _, _, text = await note_problem(chat_id, message_id, text, kwargs)
        return await base.edit_message_text(self, text, *args, **kwargs)

    async def answer_callback_query(self, callback_query_id, *args, **kwargs):
        # A pop-up cannot hold a button, but it is a problem shown all the
        # same -- so it is logged and recorded like any other, and only the
        # button is missing.
        text = kwargs.get("text", args[0] if args else None)
        code = problems.find_code(text) if isinstance(text, str) else None
        if code:
            incident = problems.new_incident()
            problem_log.info("%s incident %s, a pop-up", code, incident)
            note_occurrence(code, incident, datetime.now(timezone.utc))
        return await base.answer_callback_query(self, callback_query_id, *args, **kwargs)

    reporting = type(base.__name__, (base,), {
        "__slots__": (), "__module__": base.__module__, "_reports_problems": True,
        "send_message": send_message, "edit_message_text": edit_message_text,
        "answer_callback_query": answer_callback_query,
    })
    try:
        object.__setattr__(bot, "__class__", reporting)
    except Exception:
        logging.getLogger(__name__).warning(
            "Problem logging and Report buttons are off: this bot's send methods could not be wrapped",
            exc_info=True)


async def _send_report_to_owner(bot, code: str, incident: str, occurred_at) -> None:
    """Somebody attached their own details to a problem.

    **Urgent problems only.** The owner, in 1.7.0: "If user decides to report
    with additional details, highest level errors should get a new message,
    something like details provided for.., and for others it should be sent
    along with the daily report." A fault somebody bothered to sign is worth
    reading; it is not worth a notification at four in the morning, and the
    nightly report already lists it with a 🙋 beside it.

    It says that details were attached; it does not say what they are. The
    owner's standing rule is that nothing a bot pushes at them identifies a
    user, and somebody consenting to be identified does not repeal it -- what
    the consent bought is the owner being *able* to look. /report <incident>
    in ManagerBot is the looking.
    """
    if not problems.urgent(code):
        return
    label = os.environ.get("FAMILY_LABEL") or getattr(family_link, "_display_name", None) \
        or family_link._bot_id or "a bot"
    text = (f"🙋 Details provided for {incident} — {label}\n"
            f"Happened {occurred_at:%Y-%m-%d %H:%M} UTC · version {family_link.VERSION}\n\n"
            + problems.decode(code)
            + f"\n\nSomebody attached their own details to this one. "
              f"/report {incident} in ManagerBot to see them.")
    try:
        await bot.send_message(chat_id=REPORTS_TO, text=text)
        return
    except Exception:
        logging.getLogger(__name__).info("Could not message problem report %s directly", incident, exc_info=True)
    emit_event("warning", "report", text)


# One open "shall I send your details?" question per problem per chat. Two taps
# on the same Report button used to put two of them in the chat, and answering
# one left the other sitting there still offering to send -- which reads, a
# minute later, as the bot having sent the report on its own.
_open_dialogs: "OrderedDict[tuple, int]" = OrderedDict()


def _remember_dialog(chat_id, incident: str, message_id: int) -> None:
    _open_dialogs[(chat_id, incident)] = message_id
    _open_dialogs.move_to_end((chat_id, incident))
    while len(_open_dialogs) > 512:
        _open_dialogs.popitem(last=False)


async def _close_open_dialog(bot, chat_id, incident: str) -> None:
    message_id = _open_dialogs.pop((chat_id, incident), None)
    if message_id is None:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        logging.getLogger(__name__).debug("Could not take down an old report question", exc_info=True)


async def problem_report_callback(update, context) -> None:
    """Report -> what a report sends, with Send and Cancel -> sent, or not."""
    query = update.callback_query
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)
    parts = (query.data or "").split(":")
    action = parts[0]
    if action == "rptc":
        await query.answer()
        chat = getattr(query.message, "chat", None)
        for key, message_id in list(_open_dialogs.items()):
            if key[0] == (getattr(chat, "id", None) or user.id) \
                    and message_id == getattr(query.message, "message_id", None):
                _open_dialogs.pop(key, None)
        await live_message.edit_in_place(query.message, context.bot, i18n.t(lang, "report_cancelled"))
        return
    code = parts[1] if len(parts) > 1 else ""
    incident = parts[2] if len(parts) > 2 else ""
    if action not in ("rpt", "rpts") or not problems.is_code(code) or not problems.is_incident(incident):
        await query.answer(i18n.t(lang, "report_invalid"), show_alert=True)
        return
    await query.answer()
    chat = getattr(query.message, "chat", None)
    chat_id = getattr(chat, "id", None) or user.id
    if action == "rpt":
        # When the message with the problem was sent. A message too old for
        # Telegram to hand back has a date of 1970, which is no use to anyone.
        when = getattr(query.message, "date", None)
        if when is None or when.timestamp() <= 0:
            when = datetime.now(timezone.utc)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(i18n.t(lang, "report_send"),
                                 callback_data=f"rpts:{code}:{incident}:{int(when.timestamp())}"),
            InlineKeyboardButton(i18n.t(lang, "report_cancel"), callback_data="rptc"),
        ]])
        # A second tap replaces the first question rather than adding one --
        # see _open_dialogs. Into the chat the button was in, so it works in a
        # group as well as in private.
        await _close_open_dialog(context.bot, chat_id, incident)
        sent = await context.bot.send_message(
            chat_id=chat_id, reply_markup=keyboard,
            text=i18n.t(lang, "report_disclaimer", code=code, incident=incident))
        _remember_dialog(chat_id, incident, getattr(sent, "message_id", None))
        return
    stamp = parts[3] if len(parts) > 3 else ""
    occurred_at = (datetime.fromtimestamp(int(stamp), tz=timezone.utc) if stamp.isdigit()
                   else datetime.now(timezone.utc))
    _open_dialogs.pop((chat_id, incident), None)
    try:
        new = await asyncio.to_thread(
            family_link.attach_problem_reporter, code, incident, occurred_at,
            user.id, getattr(user, "username", None), lang,
            getattr(chat, "type", None), problems.level(code))
    except Exception:
        logging.getLogger(__name__).exception("Could not store problem report %s (%s)", incident, code)
        await live_message.edit_in_place(query.message, context.bot, i18n.t(lang, "report_failed"))
        return
    if new:
        await _send_report_to_owner(context.bot, code, incident, occurred_at)
    await live_message.edit_in_place(
        query.message, context.bot,
        i18n.t(lang, "report_sent" if new else "report_already", incident=incident))


async def _tell_about_crash(update, context, incident: str) -> None:
    """A crash used to leave the person with no answer at all. Now they are
    told it failed on the bot's side, with a code and a report button whose
    incident is the one logged beside the traceback."""
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    if chat is None or user is None or getattr(chat, "type", "") != "private":
        return
    try:
        lang = await i18n.get_lang(user.id, context)
    except Exception:
        lang = "en"
    try:
        await context.bot.send_message(chat_id=chat.id, text=i18n.t(lang, "crash_notice"),
                                       reply_markup=report_markup(lang, "FM-CRASH", incident))
    except Exception:
        logging.getLogger(__name__).debug("Could not tell anyone about crash %s", incident, exc_info=True)


async def error_handler(update, context) -> None:
    """Register with Application.add_error_handler in each bot's main() --
    this is PTB's global hook for exceptions that escape a handler callback
    uncaught (i.e. actual crashes, not the try/except'd, user-facing errors
    already handled inline elsewhere).

    A dropped long poll reaches here too, and is not a crash -- see
    is_transient_network_error above."""
    # Only a failure with no update behind it is the long poll. A network
    # error raised while handling somebody's message means that person asked
    # for something and did not get it, and that is not a blip however
    # transient its cause: it is counted, logged with its traceback, and
    # reported like any other failure.
    if update is None and is_transient_network_error(context.error):
        note_network_blip(context.error)
        return
    incident = problems.new_incident()
    logging.getLogger(__name__).error(
        "Unhandled exception while processing an update (incident %s)", incident, exc_info=context.error)
    record_error(context.error)
    await _tell_about_crash(update, context, incident)


# ---------------------------------------------------------------------------
# Active-user tracking, buffered
# ---------------------------------------------------------------------------
# This used to be one INSERT -- and, before the connection pool, one whole new
# Postgres connection -- on *every single update*, purely so /status could say
# how many people used the bot in the last hour.
#
# Nothing reads an individual row. Both queries are COUNT(DISTINCT user_id)
# over a window, so recording a user once per flush window is exactly as
# accurate as recording them forty times, and writes a fraction as much. Ids
# collect in a set here and go out as one multi-row INSERT per window.
ACTIVITY_FLUSH_SECONDS = int(os.environ.get("ACTIVITY_FLUSH_SECONDS", "60"))

_activity_buffer: set[int] = set()


def _flush_activity_now() -> int:
    """Blocking; call through asyncio.to_thread. Takes the whole buffer in one
    swap so an update arriving mid-flush lands in the next window rather than
    being lost."""
    global _activity_buffer
    if not _activity_buffer:
        return 0
    batch, _activity_buffer = _activity_buffer, set()
    try:
        db.record_activity_batch(batch)
    except Exception:
        # Put them back: a database blip should cost a delayed count, not a
        # wrong one. Union rather than assignment, so ids that arrived while
        # this was in flight survive too.
        _activity_buffer |= batch
        raise
    return len(batch)


async def _flush_activity_job(context) -> None:
    try:
        await asyncio.to_thread(_flush_activity_now)
    except Exception:
        logging.getLogger(__name__).debug("Activity flush failed; will retry", exc_info=True)


async def track_activity(update, context) -> None:
    """Register as a TypeHandler(Update, track_activity, ...) in a group of
    its OWN, above every other group, so /status can report active users
    hourly / since this process started.

    Its own group is not a style choice. python-telegram-bot runs at most one
    handler per group -- the first match wins and the rest of that group is
    skipped -- and this one matches every update there is. Anything sharing a
    group with it therefore never runs at all, silently, which is exactly
    what happened to the four bots' donate_custom_amount_received and to
    AnonBot's edited_message handler until v1.2.2R.

    Does no I/O at all now -- it adds an int to a set, and the job registered
    by attach_maintenance() writes the window out. It also stamps this user's
    per-user cache with the time, which is what lets that same job drop the
    caches of people who have not been seen in a long while."""
    note_network_ok()
    # Which message is newest in this chat, so a live message knows whether
    # it is still the last thing on screen. Before the user check on purpose:
    # it is a property of the chat, not of who sent it.
    live_message.note_update(update)
    user = update.effective_user
    if not user:
        return
    _activity_buffer.add(user.id)
    note_usage_update(user.id)
    context.user_data["_last_seen"] = time.time()
    remember_chat_lang(user.id, context.user_data.get("lang"))

    # A per-chat menu is frozen when it is set; see refresh_chat_menu. Only
    # people who have one are checked, and the signature is updated before the
    # call goes out, so a burst of updates schedules it once.
    have = context.user_data.get(MENU_SIGNATURE_KEY)
    if have:
        try:
            lang = context.user_data.get("lang")
            commands = _menu_for(user.id, lang)
            if commands:
                expected = _menu_signature(commands)
                if have != expected:
                    context.user_data[MENU_SIGNATURE_KEY] = expected
                    context.application.create_task(refresh_chat_menu(context, user.id, lang))
        except Exception:
            logging.getLogger(__name__).debug("Could not check the chat menu", exc_info=True)


# ---------------------------------------------------------------------------
# Not starting something an update is about to take away
# ---------------------------------------------------------------------------
# Two different reasons a bot should decline to begin slow work, and they want
# different sentences:
#
#   A stop signal has already arrived. The container is going in seconds and
#   there is nothing to arrange -- "send it again in a moment" is the whole
#   truth, and lifecycle.busy() covers anyone already inside a job.
#
#   The owner has announced an update from ManagerBot. That can last across
#   several deploys, so the honest answer carries an estimate and a promise:
#   the person is written down, and /finishupdates goes back to them when it
#   is over. Being told "try again in a moment" and finding it still shut
#   four times running is worse than being told to wait ten minutes once.
#
# Every handler that starts something slow calls this first and shows what it
# returns instead of starting.

async def refuse_new_work(lang: str, user_id: int, chat_id: int) -> str | None:
    """The sentence to answer with instead of starting slow work, or None
    when there is no reason not to start it.

    Writes the person down when -- and only when -- the owner has announced
    an update, because that is the only case where somebody is coming back to
    tell them it is finished.
    """
    if not lifecycle.is_paused():
        return None
    if not lifecycle.in_maintenance():
        return i18n.t(lang, "restarting_send_again")

    await asyncio.to_thread(lifecycle.hold_for_update, user_id, chat_id)
    minutes = lifecycle.maintenance_minutes_left()
    if minutes is None:
        return i18n.t(lang, "update_soon_try_later_soon")
    return i18n.t(lang, "update_soon_try_later", minutes=minutes)


# ---------------------------------------------------------------------------
# Bounding the process's own memory
# ---------------------------------------------------------------------------
# python-telegram-bot keeps a user_data dict per user id for the lifetime of
# the process and never evicts it. Each one is small (a cached language, a
# menu's worth of state) but the count only ever goes up, so on a bot that
# runs for months this is a genuine slow leak -- and on a container sized to
# the smallest plan that fits, a slow leak is an eventual OOM restart.
#
# Anyone idle for USER_DATA_TTL_HOURS gets theirs dropped. The only thing lost
# is a cache: their language is re-read from the database on their next
# message, and no bot in the family keeps anything in user_data that has to
# outlive a conversation.
USER_DATA_TTL_HOURS = int(os.environ.get("USER_DATA_TTL_HOURS", "12"))


def _prune_user_data(application) -> int:
    cutoff = time.time() - USER_DATA_TTL_HOURS * 3600
    stale = [
        user_id for user_id, data in application.user_data.items()
        if data.get("_last_seen", 0) < cutoff
    ]
    for user_id in stale:
        application.drop_user_data(user_id)
    return len(stale)


async def _maintenance_job(context) -> None:
    dropped = _prune_user_data(context.application)
    if dropped:
        logging.getLogger(__name__).info("Dropped cached state for %d idle user(s).", dropped)


def attach_maintenance(app) -> None:
    """One line in each bot's main(), next to family_link.attach().

    Flushes the activity buffer on a timer and again on shutdown, and keeps
    per-user memory from growing forever. Degrades to "no buffering, no
    pruning" rather than failing if the bot has no job queue."""
    if app.job_queue is None:
        logging.getLogger(__name__).warning(
            "No job queue -- activity counts and memory pruning are off. "
            'Install it with: pip install "python-telegram-bot[job-queue]"'
        )
        return
    app.job_queue.run_repeating(
        _flush_activity_job, interval=ACTIVITY_FLUSH_SECONDS, first=ACTIVITY_FLUSH_SECONDS
    )
    app.job_queue.run_repeating(
        _flush_problems_job, interval=PROBLEM_FLUSH_SECONDS, first=PROBLEM_FLUSH_SECONDS
    )
    app.job_queue.run_repeating(_maintenance_job, interval=3600, first=3600)
    # Offset by a minute so a redeploy does not have all five bots writing a
    # usage row into one second, and so the first window is a real window
    # rather than however long the process happened to have been up.
    app.job_queue.run_repeating(
        _usage_sample_job, interval=USAGE_SAMPLE_MINUTES * 60,
        first=USAGE_SAMPLE_MINUTES * 60 + 60,
    )


async def flush_on_shutdown(application) -> None:
    """Register as Application.post_stop. Writes out whatever the last window
    collected -- without this, a redeploy silently loses up to a minute of
    activity counts -- and lets the connection pool's worker threads go."""
    try:
        await asyncio.to_thread(_flush_activity_now)
    except Exception:
        logging.getLogger(__name__).debug("Final activity flush failed", exc_info=True)
    try:
        await asyncio.to_thread(_flush_problems_now)
    except Exception:
        logging.getLogger(__name__).debug("Final problem flush failed", exc_info=True)
    close = getattr(db, "close_pool", None)
    if close is not None:
        try:
            await asyncio.to_thread(close)
        except Exception:
            logging.getLogger(__name__).debug("Closing the connection pool failed", exc_info=True)


def detect_host_environment() -> str:
    """Best-effort guess at where this process is running. Railway sets a
    handful of its own env vars on every deploy, so their presence is a
    reliable cloud signal; anything else is assumed to be a local machine."""
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT")
    if railway_env:
        project = os.environ.get("RAILWAY_PROJECT_NAME", "?")
        service = os.environ.get("RAILWAY_SERVICE_NAME", "?")
        return f"☁️ Cloud (Railway -- project \"{project}\", service \"{service}\", env \"{railway_env}\")"
    return f"💻 Local ({socket.gethostname()})"


# ---------------------------------------------------------------------------
# What this process actually costs to run
# ---------------------------------------------------------------------------
# A usage-billed host charges for resident memory and CPU seconds, and until
# this was on /status there was no way to tell whether a change to either had
# helped, hurt, or done nothing. Every number here is read from the kernel,
# free, and only when someone asks.

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
    """What the container is allowed, rather than what the host has. cgroup
    v2 first (every current Linux container runtime), then v1."""
    for path, scale in (("/sys/fs/cgroup/memory.max", 1),
                        ("/sys/fs/cgroup/memory/memory.limit_in_bytes", 1)):
        value = _read_first_int(path)
        # An unset cgroup limit is reported as a number near 2^63, which is
        # "the whole machine" and worth nothing as a denominator.
        if value and value < (1 << 62):
            return value * scale
    return None


def footprint_numbers() -> dict:
    """The same four readings process_footprint() prints, as numbers.

    Separated out because a sentence is what a person wants and a number is
    what a threshold and a database row want, and building the sentence twice
    to parse it back would be the kind of thing that breaks silently in one
    language and not another.

    Any of them may be None: /proc is Linux, the cgroup file is a container,
    and `resource` is not on Windows. A missing number means "not measurable
    here", never zero -- zero would read as "free" to every caller.
    """
    resident = _read_first_int("/proc/self/status", "VmRSS:")
    peak = _read_first_int("/proc/self/status", "VmHWM:")
    ceiling = _memory_ceiling_bytes()
    cpu = None
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        cpu = usage.ru_utime + usage.ru_stime
        if resident is None:
            # ru_maxrss is kilobytes on Linux and bytes on macOS/BSD, and it
            # is a high-water mark rather than a live reading -- so it stands
            # in for the peak, and there is no live number to report.
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
    """One line: resident memory, its high-water mark, and CPU seconds burned
    since startup. Read /proc where it exists (Linux, which is what the
    deployed containers are) and fall back to getrusage elsewhere."""
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


# ---------------------------------------------------------------------------
# What it costs over time, and when that stops being normal
# ---------------------------------------------------------------------------
# /status answers "what is this process using right now", which on its own
# tells nobody whether right now is unusual. This keeps a rolling window --
# updates handled, distinct people, and the four kernel readings -- writes one
# row per window into family.usage_samples, and raises an event when a window
# is far enough from the others to be worth a message at 3am.
#
# Three things are worth being told about, and they are different questions:
#
#   memory headroom   the container is close to the limit it will be killed
#                     for crossing. The only one of the three that is an
#                     emergency.
#   an activity spike a window with far more updates than the recent norm.
#                     Could be a launch, could be one script. Either way the
#                     owner would rather hear it from the bot than from the
#                     bill.
#   monthly reach     how many distinct people used it in thirty days, which
#                     is the number that decides whether the plan it is on is
#                     still the right one. Slow-moving, so it is checked once
#                     a day and only ever mentioned when it crosses.
#
# Everything here is a count. No user ids, no chat ids, no text.

USAGE_SAMPLE_MINUTES = int(os.environ.get("USAGE_SAMPLE_MINUTES") or 15)
# How full the container has to be before it is worth saying so. 0.85 rather
# than 0.95: the point is to arrive before the OOM kill, not with it.
USAGE_MEMORY_WARN_RATIO = float(os.environ.get("USAGE_MEMORY_WARN_RATIO") or 0.85)
# A window counts as a spike when it is this many times the median of the
# recent ones AND clears the floor. The floor is what stops "2 updates, then
# 12" from being an incident on a quiet bot -- which, on a bot this quiet, is
# most of the time.
USAGE_SPIKE_FACTOR = float(os.environ.get("USAGE_SPIKE_FACTOR") or 6.0)
USAGE_SPIKE_FLOOR = int(os.environ.get("USAGE_SPIKE_FLOOR") or 60)
# Distinct people in thirty days, past which the owner is told once. Not a
# limit and nothing is refused; it is the number that means "the smallest
# plan that fits may no longer be the smallest plan that fits".
USAGE_MONTHLY_USERS_WARN = int(os.environ.get("USAGE_MONTHLY_USERS_WARN") or 400)
# How long a host waits for silence before it stops charging for a container.
# Railway sleeps a service after roughly five minutes with no *outbound*
# traffic, so a gap between updates is only worth anything from the five-minute
# mark onwards -- which is why this is subtracted from every gap rather than
# the gaps simply being added up. Nothing in the bots sleeps yet; this measures
# what sleeping *would* have saved, so the decision is made on this family's
# own traffic rather than on a guess.
SLEEP_AFTER_SECONDS = int(os.environ.get("SLEEP_AFTER_SECONDS") or 300)
# A window where more than this fraction of the jobs failed is worth being told
# about -- a job being a conversion, a download, a pack edit: whatever the bot
# is for. The floor is again what stops one failure out of one being an
# outage.
USAGE_FAILURE_WARN_RATIO = float(os.environ.get("USAGE_FAILURE_WARN_RATIO") or 0.5)
USAGE_FAILURE_FLOOR = int(os.environ.get("USAGE_FAILURE_FLOOR") or 4)
# How many recent windows the spike test compares against, and how long an
# alarm of one kind stays quiet after firing.
_USAGE_WINDOW_MEMORY = 24
_ALARM_QUIET_SECONDS = {"memory": 3600, "spike": 3600, "monthly_users": 86400,
                        "failures": 1800}

_usage_updates = 0
_usage_users: set[int] = set()
_usage_recent: "deque[int]" = deque(maxlen=_USAGE_WINDOW_MEMORY)
_usage_alarmed: dict[str, float] = {}
# The gap clock. monotonic() rather than time(): this measures a duration, and
# a clock that can be stepped by NTP would make one negative.
_usage_last_update = time.monotonic()
_usage_sleepable = 0.0
_usage_max_gap = 0.0
_usage_jobs_ok = 0
_usage_jobs_failed = 0


def note_usage_update(user_id: int | None) -> None:
    """One update happened. Called from track_activity, so it is on the path
    of every update there is -- it adds an int to a set and increments a
    couple of counters, and must never do anything more expensive than that."""
    global _usage_updates, _usage_last_update, _usage_sleepable, _usage_max_gap
    _usage_updates += 1
    now = time.monotonic()
    gap = now - _usage_last_update
    _usage_last_update = now
    _usage_max_gap = max(_usage_max_gap, gap)
    _usage_sleepable += max(0.0, gap - SLEEP_AFTER_SECONDS)
    if user_id is not None and len(_usage_users) < 10000:
        _usage_users.add(user_id)


def note_job(ok: bool) -> None:
    """One unit of the thing this bot is for finished -- a conversion, a
    download, a pack edit. Two counters and nothing else.

    What is deliberately NOT here: what was converted, which link, whose it
    was, or why it failed. The question this answers is "is the bot still
    working", and that needs a ratio, not a record. Per-route detail already
    lives where it belongs -- DownloaderBot's provider health, and every
    bot's error log."""
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
    """One line for /status: what the recent windows looked like, so the
    number above it has something to be compared with."""
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
    """One window: write the row, then decide whether to say anything.

    The counters are taken and reset first, so a slow database cannot make
    the next window count this one's updates twice."""
    global _usage_updates, _usage_users
    updates, users = _usage_updates, len(_usage_users)
    _usage_updates, _usage_users = 0, set()
    numbers = footprint_numbers()
    global _usage_sleepable, _usage_max_gap, _usage_jobs_ok, _usage_jobs_failed
    # The window ends with a gap in progress. Counting it now, and starting the
    # next window's clock from here, is what stops a bot that was quiet for six
    # hours reporting six hours of sleepable time in one window and none in the
    # twenty-three before it.
    global _usage_last_update
    now = time.monotonic()
    trailing = now - _usage_last_update
    sleepable = int(_usage_sleepable + max(0.0, trailing - SLEEP_AFTER_SECONDS))
    max_gap = int(max(_usage_max_gap, trailing))
    jobs_ok, jobs_failed = _usage_jobs_ok, _usage_jobs_failed
    _usage_sleepable, _usage_max_gap = 0.0, 0.0
    _usage_jobs_ok, _usage_jobs_failed = 0, 0
    _usage_last_update = now
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


def build_status_text(start_time: datetime, users_last_hour: int, users_since_start: int) -> str:
    now = datetime.now(timezone.utc)
    uptime = now - start_time
    days, rem = divmod(int(uptime.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    uptime_str = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"
    return "\n".join([
        "📊 Status",
        f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} ({uptime_str} ago)",
        f"Hosted: {detect_host_environment()}",
        f"Active users (last hour): {users_last_hour}",
        f"Active users (since this start): {users_since_start}",
        process_footprint(),
        "",
        error_summary(),
    ])
