"""Surviving a redeploy without anybody noticing.

Pushing an update to a bot on a platform like Railway means the running
container is replaced. Four separate things go wrong in that gap, and only
one of them is the obvious one:

  1. **Two bots, one token.** If the new container starts polling before the
     old one has stopped, Telegram answers one of them with 409 Conflict and
     both flap. `hold_the_lease()` below settles it with a Postgres advisory
     lock: exactly one process at a time holds the right to poll, and the
     new one waits for the old one's grip to relax rather than fighting it.

  2. **Everything the bot was in the middle of is forgotten.** user_data and
     every ConversationHandler state live in that process's memory and go
     with it. Someone who was three stickers into a pack sends the fourth
     and gets "I don't recognize that" from a bot that, thirty seconds ago,
     knew exactly what they were doing. `PostgresPersistence` writes both
     into the bot's own schema, so the new process picks the conversation up
     mid-sentence.

  3. **Work in flight is killed.** An ffmpeg encode or a download that is
     running when the platform sends SIGTERM does not come back, and the
     user is left looking at "converting..." forever. `busy()` marks those
     stretches; when a stop signal arrives, everyone inside one is told, in
     their own chat, that an update interrupted them -- once, immediately,
     instead of never.

  4. **The owner gets paged for a deploy they did on purpose.** ManagerBot
     decides a bot is down from a stale heartbeat, and a redeploy makes
     every heartbeat stale. `mark_expected_restart()` leaves a note in the
     shared database saying this one was deliberate.

What is *not* a problem, and does not need solving: updates sent while the
bot is between containers. Telegram queues undelivered updates for 24 hours
and hands them over on the next getUpdates, so as long as nothing calls
run_polling(drop_pending_updates=True), the gap costs those users latency
and nothing else.

Copied byte-identically into every bot, like shared_features.py,
family_link.py and live_message.py.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import db

logger = logging.getLogger(__name__)

# Everything here is opt-out, one env var, and every piece of it degrades to
# "the way it worked before" rather than to a bot that will not start.
ENABLED = os.environ.get("DEPLOY_SAFETY", "on").lower() not in ("off", "0", "false", "no")

# How long a starting process waits for a previous one to let go of the poll
# lease before it starts anyway.
#
# Raised from 45s to 240s in v1.2.2R, when railway.json's overlapSeconds went
# from 0 to 30. Those two numbers are one decision, not two.
#
# overlapSeconds: 0 meant Railway stopped the old container before starting
# the new one, so the bot was away for the whole of the new container's build
# and boot -- a minute or three during which every message waited. Telegram
# holds those updates and hands them over afterwards, so nothing was ever
# lost; what it cost was a user typing into what looked like a dead bot.
#
# With this lease in place, the old container can keep serving while the new
# one builds and boots. The new one blocks HERE, in post_init -- before its
# first getUpdates, before its first heartbeat -- until Railway stops the old
# one and Postgres releases its session-level lock. The gap becomes the drain
# alone, which is seconds.
#
# The wait therefore has to outlast the whole handover: the overlap window
# (30s) plus a worst-case drain (drainingSeconds, 120s), with room to spare.
# If it does not, the new container gives up and starts polling while the old
# one is still going, and Telegram answers 409 Conflict and splits the
# updates between them -- which is the exact failure overlapSeconds: 0
# existed to prevent. Keep DEPLOY_LEASE_WAIT_SECONDS comfortably above
# overlapSeconds + drainingSeconds if either is ever changed.
LEASE_WAIT_SECONDS = float(os.environ.get("DEPLOY_LEASE_WAIT_SECONDS", "240"))

# State older than this is not loaded at startup, and is deleted when it is
# noticed. Matches shared_features' USER_DATA_TTL_HOURS, which drops the same
# state from memory for the same reason -- a conversation nobody has touched
# for half a day is over, whatever the state machine still thinks.
STATE_TTL_HOURS = int(os.environ.get("DEPLOY_STATE_TTL_HOURS", "12"))

# How often in-memory state is written out *besides* at shutdown. A clean
# redeploy flushes on the way out and needs none of these; this is purely
# insurance against the ways a process dies without warning (an OOM kill, a
# host failure), where the alternative is losing everything since startup.
# Every pass is one small upsert per user who has changed, so the cost of
# making it more frequent is real but modest.
PERSIST_SECONDS = float(os.environ.get("DEPLOY_PERSIST_SECONDS", "180"))

_app = None
_draining = False
_drain_started: float | None = None
_lease_conn = None
_bot_id: str | None = None


# ---------------------------------------------------------------------------
# 1. One poller at a time
# ---------------------------------------------------------------------------
# Telegram allows exactly one getUpdates consumer per token. Two is not a
# degraded mode, it is a coin flip per update: 409 Conflict to whichever
# asked second, and updates split unpredictably between the two.
#
# A Postgres *session*-level advisory lock is the right shape for this. It is
# free (no table, no rows, no cleanup), it is held by a connection rather
# than by a row anybody has to remember to delete, and -- the part that
# matters here -- the server drops it the moment that connection goes away,
# including when the process holding it was killed rather than asked. So a
# hard-killed old container releases it too, just less promptly.
#
# It needs its own connection, deliberately not one from db.py's pool: a
# pooled connection is handed back after every query, and a session lock
# released with it.

def _lease_key(bot_id: str) -> int:
    """A stable 64-bit key per bot. Signed, because that is what
    pg_advisory_lock takes."""
    digest = hashlib.blake2b(bot_id.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


def _try_lease(bot_id: str) -> bool:
    global _lease_conn
    import psycopg

    if _lease_conn is None or _lease_conn.closed:
        _lease_conn = psycopg.connect(db.DATABASE_URL, autocommit=True)
    cur = _lease_conn.execute("SELECT pg_try_advisory_lock(%s)", (_lease_key(bot_id),))
    return bool(cur.fetchone()[0])


async def hold_the_lease(bot_id: str) -> bool:
    """Block until this process is the only one polling for `bot_id`.

    Returns True when the lease is ours. Returns False -- and lets the bot
    start anyway -- if it could not be had: an unreachable database must not
    be able to stop a bot from serving its users, and a lease nobody can
    check is no worse than the no-lease-at-all this family ran with before.
    """
    if not ENABLED:
        return False
    deadline = time.monotonic() + LEASE_WAIT_SECONDS
    complained = False
    while True:
        try:
            if await asyncio.to_thread(_try_lease, bot_id):
                if complained:
                    logger.info("Poll lease acquired -- the previous instance has stopped.")
                return True
        except Exception as exc:
            logger.warning("Could not check the poll lease (%s) -- starting without it.", exc)
            return False
        if time.monotonic() >= deadline:
            logger.warning(
                "Another instance of %s still holds the poll lease after %.0fs. Starting "
                "anyway -- expect 409 Conflict from Telegram until it stops.",
                bot_id, LEASE_WAIT_SECONDS,
            )
            return False
        if not complained:
            logger.info("Waiting for the previous instance of %s to let go of the poll lease...", bot_id)
            complained = True
        await asyncio.sleep(1.0)


def release_lease() -> None:
    global _lease_conn
    if _lease_conn is None:
        return
    try:
        if not _lease_conn.closed:
            _lease_conn.execute("SELECT pg_advisory_unlock(%s)", (_lease_key(_bot_id or ""),))
    except Exception:
        logger.debug("Could not release the poll lease; closing the connection does it too", exc_info=True)
    try:
        _lease_conn.close()
    except Exception:
        pass
    _lease_conn = None


# ---------------------------------------------------------------------------
# 2. State that outlives the process
# ---------------------------------------------------------------------------
# One table in the bot's own schema (search_path is already pointed there by
# db.py, so this needs no qualification and cannot collide with a sibling's).
#
# JSONB rather than pickle, on purpose. It is readable from ManagerBot's /sql,
# it can be pruned by age with plain SQL, and it cannot execute anything on
# the way back in. The price is that values which are not JSON -- notably
# whole telegram.Message objects -- are dropped instead of stored; every
# caller in this family already treats those as in-memory-only, and the one
# place that keeps one (AnonBot's held message) has said "expired" when it is
# missing since the day it was written.

STATE_TABLE = "runtime_state"


def init_state_table() -> None:
    with db.pooled() as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {STATE_TABLE} (
                kind       TEXT NOT NULL,
                key        TEXT NOT NULL,
                value      JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (kind, key)
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{STATE_TABLE}_age "
            f"ON {STATE_TABLE} (updated_at)"
        )
        conn.commit()


def _json_safe(value):
    """`value` if it survives a JSON round trip unchanged, else None.

    Tuples are the one thing deliberately *not* accommodated: JSON has no
    tuple, so one would come back as a list and quietly change type under
    code that unpacked it. Nothing in this family keeps a tuple in user_data
    that has to survive a restart, so refusing them is safer than converting
    them.
    """
    import json

    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return None
    if json.loads(encoded) != value:
        return None
    return value


def _clean(data: dict) -> dict:
    out = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        kept = _json_safe(value)
        if kept is None and value is not None:
            logger.debug("Not persisting user_data[%r]: not JSON", key)
            continue
        out[key] = value
    return out


def _write_state(rows: list[tuple[str, str, dict]]) -> None:
    if not rows:
        return
    from psycopg.types.json import Jsonb

    with db.pooled() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                f"""
                INSERT INTO {STATE_TABLE} (kind, key, value, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (kind, key) DO UPDATE
                SET value = excluded.value, updated_at = excluded.updated_at
                """,
                [(kind, key, Jsonb(value)) for kind, key, value in rows],
            )
        conn.commit()


def _delete_state(rows: list[tuple[str, str]]) -> None:
    if not rows:
        return
    with db.pooled() as conn:
        with conn.cursor() as cur:
            cur.executemany(f"DELETE FROM {STATE_TABLE} WHERE kind = %s AND key = %s", rows)
        conn.commit()


def _read_state(kind: str) -> list[tuple[str, dict]]:
    """Everything of one kind that is still young enough to mean something,
    deleting the rest on the way past -- the only pruning this table needs,
    and it happens once per process start."""
    with db.pooled() as conn:
        conn.execute(
            f"DELETE FROM {STATE_TABLE} WHERE updated_at < now() - make_interval(hours => %s)",
            (STATE_TTL_HOURS,),
        )
        cur = conn.execute(f"SELECT key, value FROM {STATE_TABLE} WHERE kind = %s", (kind,))
        rows = cur.fetchall()
        conn.commit()
    return rows


def forget_user(user_id: int) -> int:
    """Delete everything this table holds for one person. Blocking; call
    through asyncio.to_thread.

    Reached from /deletemydata, which is the one place a user can ask for
    their data back. The bot's own tables are its db.py's business -- this
    is the half that db.py cannot clean up, because the table name and the
    shape of a conversation key are both known only here.

    Conversation rows are matched on the key's *last* component. A
    ConversationHandler key is (chat, user) by default and (user,) with
    per_chat=False, and the user id is the trailing part either way.

    Returns 0 when the table is not there at all, which is the normal state
    of a bot running with DEPLOY_SAFETY=off: nothing was persisted, so there
    is nothing to forget. Letting the DELETE raise instead meant
    /deletemydata reported "couldn't erase that" to somebody whose data had
    just been erased -- the bot's own tables are cleared before this is
    called -- which is the worst answer available for an action with no undo.
    """
    with db.pooled() as conn:
        if conn.execute("SELECT to_regclass(%s)", (STATE_TABLE,)).fetchone()[0] is None:
            return 0
        cur = conn.execute(
            f"DELETE FROM {STATE_TABLE} WHERE (kind = 'user' AND key = %s) "
            f"OR (kind = 'conversation' AND (key LIKE %s OR key LIKE %s))",
            (str(user_id), f"%:{user_id}", f"%|{user_id}"),
        )
        removed = cur.rowcount or 0
        conn.commit()
    return removed


try:
    from telegram.ext import BasePersistence, PersistenceInput
except ImportError:  # pragma: no cover -- only if PTB is missing entirely
    BasePersistence = object
    PersistenceInput = None


class PostgresPersistence(BasePersistence):
    """user_data and conversation states, in the bot's own Postgres schema.

    Written at shutdown (python-telegram-bot calls flush() there) and every
    PERSIST_SECONDS in between, not on every update: the point is to survive
    a restart, and a restart gives ample warning. Conversation states are the
    exception -- they are single small rows, they change rarely, and being
    one state behind is the difference between picking a conversation up and
    dropping it, so those are written as they happen.
    """

    def __init__(self):
        super().__init__(
            store_data=PersistenceInput(
                bot_data=False, chat_data=False, user_data=True, callback_data=False
            ),
            # python-telegram-bot's own timer only *collects* changes (it
            # calls update_user_data and stops there); the writing is driven
            # from install()'s job below, so PTB's pass is pushed far out
            # rather than doing the same deep copies twice a period.
            update_interval=max(PERSIST_SECONDS * 10, 600),
        )
        self._user_data: dict[int, dict] = {}
        self._dirty_users: set[int] = set()
        self._dropped_users: set[int] = set()
        self._conversations: dict[str, dict] = {}
        self._conversations_loaded = False

    # ---- loading, once, at startup ----

    async def get_user_data(self) -> dict[int, dict]:
        try:
            rows = await asyncio.to_thread(_read_state, "user")
        except Exception:
            logger.warning("Could not read saved user state; starting with none.", exc_info=True)
            return {}
        loaded = {}
        for key, value in rows:
            try:
                loaded[int(key)] = dict(value)
            except (TypeError, ValueError):
                continue
        self._user_data = loaded
        if loaded:
            logger.info("Restored in-progress state for %d user(s).", len(loaded))
        return loaded

    async def get_conversations(self, name: str) -> dict:
        if not self._conversations_loaded:
            self._conversations_loaded = True
            try:
                rows = await asyncio.to_thread(_read_state, "conversation")
            except Exception:
                logger.warning("Could not read saved conversations; starting with none.", exc_info=True)
                rows = []
            for key, value in rows:
                handler, _, pair = key.partition("|")
                try:
                    # Rebuilt with the same arity it was stored with: a
                    # ConversationHandler's key is (chat, user) by default but
                    # (user,) with per_chat=False, and handing back the wrong
                    # shape would silently match nothing.
                    conv_key = tuple(int(part) for part in pair.split(":"))
                except ValueError:
                    continue
                self._conversations.setdefault(handler, {})[conv_key] = value.get("state")
        restored = self._conversations.get(name, {})
        if restored:
            logger.info("Restored %d open %s conversation(s).", len(restored), name)
        return dict(restored)

    async def get_bot_data(self):
        return {}

    async def get_chat_data(self):
        return {}

    async def get_callback_data(self):
        return None

    # ---- collecting changes ----

    async def update_user_data(self, user_id: int, data: dict) -> None:
        self._user_data[user_id] = data
        self._dirty_users.add(user_id)
        self._dropped_users.discard(user_id)

    async def update_conversation(self, name: str, key: tuple, new_state) -> None:
        conversations = self._conversations.setdefault(name, {})
        if new_state is None:
            conversations.pop(key, None)
        else:
            conversations[key] = new_state
        row_key = f"{name}|" + ":".join(str(part) for part in key)
        try:
            if new_state is None:
                await asyncio.to_thread(_delete_state, [("conversation", row_key)])
            else:
                await asyncio.to_thread(_write_state, [("conversation", row_key, {"state": new_state})])
        except Exception:
            logger.debug("Could not persist a conversation state", exc_info=True)

    async def drop_user_data(self, user_id: int) -> None:
        self._user_data.pop(user_id, None)
        self._dirty_users.discard(user_id)
        self._dropped_users.add(user_id)

    async def update_bot_data(self, data) -> None:
        return None

    async def update_chat_data(self, chat_id: int, data) -> None:
        return None

    async def update_callback_data(self, data) -> None:
        return None

    async def drop_chat_data(self, chat_id: int) -> None:
        return None

    async def refresh_user_data(self, user_id: int, user_data: dict) -> None:
        return None

    async def refresh_chat_data(self, chat_id: int, chat_data) -> None:
        return None

    async def refresh_bot_data(self, bot_data) -> None:
        return None

    # ---- writing them out ----

    async def flush(self) -> None:
        writes, deletes = [], [("user", str(u)) for u in self._dropped_users]
        for user_id in self._dirty_users:
            kept = _clean(self._user_data.get(user_id) or {})
            if kept:
                writes.append(("user", str(user_id), kept))
            else:
                # Their state emptied out -- a /cancel, a /done, or nothing
                # worth keeping in the first place. Without this the row
                # would be restored as an empty dict forever.
                deletes.append(("user", str(user_id)))
        self._dirty_users.clear()
        self._dropped_users.clear()
        if not writes and not deletes:
            return
        try:
            await asyncio.to_thread(_write_state, writes)
            await asyncio.to_thread(_delete_state, deletes)
        except Exception:
            logger.warning("Could not save in-progress state.", exc_info=True)


# ---------------------------------------------------------------------------
# 3. Work that is in flight when the platform says stop
# ---------------------------------------------------------------------------
# python-telegram-bot already waits for running handlers before it shuts down,
# so short work finishes on its own. The problem is the long kind: a video
# encode or a download can outlast whatever grace period the platform allows
# before SIGKILL, and the user is left watching a "converting..." that will
# never change.
#
# There is no way to make that work survive. There is a way to make sure the
# user hears about it, which is all busy() does: it keeps a note of who is
# waiting on what, and the stop handler answers all of them at once.

# chat id -> the message to send there if this work does not survive. The
# message rather than a label, because this file is byte-identical in five
# bots and four of them are trilingual: the caller has the user's language in
# hand and this file has no business importing i18n to go and find it.
_in_flight: dict[int, tuple[int, str]] = {}
_next_ticket = 0


def is_draining() -> bool:
    """True once a stop signal has arrived. Check it before starting
    anything slow -- see the guard in each bot's media handlers."""
    return _draining


@asynccontextmanager
async def busy(chat_id: int, if_interrupted: str):
    """Mark a stretch of slow work, so a redeploy in the middle of it ends
    with an explanation rather than with silence.

        async with lifecycle.busy(chat_id, i18n.t(lang, "restarting_send_again")):
            ...

    `if_interrupted` is the finished, translated message to send if a stop
    signal arrives while this is running -- and nothing at all otherwise.
    """
    global _next_ticket
    _next_ticket += 1
    ticket = _next_ticket
    _in_flight[ticket] = (chat_id, if_interrupted)
    try:
        yield
    finally:
        _in_flight.pop(ticket, None)


async def _tell_the_interrupted(bot) -> None:
    """One message each, to everyone who was mid-something. Best-effort and
    strictly time-boxed: this runs inside the platform's shutdown grace
    period, and holding that up to retry a send helps nobody."""
    waiting = list(_in_flight.values())
    if not waiting:
        return
    logger.info("Telling %d user(s) that an update interrupted them.", len(waiting))
    for chat_id, message in waiting:
        try:
            await asyncio.wait_for(
                bot.send_message(chat_id=chat_id, text=message), timeout=5,
            )
        except Exception:
            logger.debug("Could not warn %s about the restart", chat_id, exc_info=True)


# ---------------------------------------------------------------------------
# 4. A deploy is not a crash
# ---------------------------------------------------------------------------
# ManagerBot calls a bot down when its heartbeat goes stale, which is exactly
# what a redeploy does to it. Leaving a note in the shared settings table
# lets the watchdog tell "I did this on purpose" from "something is wrong"
# -- see ManagerBot's watchdog.

RESTART_NOTE_PREFIX = "restarting:"


def mark_expected_restart(bot_id: str) -> None:
    try:
        import family_link

        with db.pooled() as conn:
            conn.execute(
                f"""
                INSERT INTO {family_link.FAMILY_SCHEMA}.settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = excluded.value
                """,
                (RESTART_NOTE_PREFIX + bot_id, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
    except Exception:
        logger.debug("Could not leave a redeploy note", exc_info=True)


# ---------------------------------------------------------------------------
# 5. An update the owner announces before it happens
# ---------------------------------------------------------------------------
# Sections 1-4 are about a redeploy nobody was warned about. This one is for
# the deploy you know is coming: the owner puts a bot into maintenance from
# ManagerBot, and until they say otherwise it declines to *start* anything a
# restart would throw away, says roughly how long it expects to be, and
# writes down who it turned away so they can be told when it is over.
#
# Three properties, none of which a module-level flag would have:
#
#   It has to survive the restart it is announcing. One update is often
#   several deploys, so the flag lives in family.settings and is read back at
#   startup rather than being held in the process that is about to end.
#
#   It has to be free to check. Every incoming message asks "are we paused?",
#   so the answer is a cached flag -- set at startup and whenever ManagerBot
#   says so -- and not a query per update.
#
#   The people turned away have to outlive the process too. That is what
#   family.update_waitlist is: one row per person told to come back, removed
#   when they are told they can.
#
# The announced time is an estimate and nothing more. Maintenance ends when
# the owner ends it, never on a timer -- because the reason they wanted a
# manual end is exactly that one update can take several deploys, and a timer
# would let the bot reopen between two of them. Once the estimate has passed
# the bots stop quoting a number rather than start quoting a wrong one.

MAINTENANCE_KEY_PREFIX = "maintenance:"
WAITLIST_TABLE = "update_waitlist"

# What ManagerBot's /pause promises when it is not told a number.
DEFAULT_MAINTENANCE_MINUTES = int(os.environ.get("DEPLOY_MAINTENANCE_MINUTES", "10"))

_maintenance_on = False
_maintenance_until: "datetime | None" = None


def _family_schema() -> str:
    import family_link

    return family_link.FAMILY_SCHEMA


def init_waitlist_table() -> None:
    schema = _family_schema()
    with db.pooled() as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {schema}.{WAITLIST_TABLE} (
                bot_id  TEXT   NOT NULL,
                user_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                held_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (bot_id, user_id)
            )
            """
        )
        conn.commit()


def _read_maintenance(bot_id: str) -> "tuple[bool, datetime | None]":
    """(is it on, what was promised). Blocking."""
    schema = _family_schema()
    with db.pooled() as conn:
        cur = conn.execute(
            f"SELECT value FROM {schema}.settings WHERE key = %s",
            (MAINTENANCE_KEY_PREFIX + bot_id,),
        )
        row = cur.fetchone()
    if row is None or not row[0]:
        return False, None
    try:
        return True, datetime.fromisoformat(row[0])
    except ValueError:
        # The row is the flag; a value that will not parse costs the estimate
        # and nothing else.
        return True, None


def refresh_maintenance(bot_id: str) -> bool:
    """Read the flag out of the shared database into this process. Blocking.

    Called at startup and after ManagerBot changes it -- the only two moments
    it can have changed, which is why nothing else has to ask.
    """
    global _maintenance_on, _maintenance_until
    try:
        _maintenance_on, _maintenance_until = _read_maintenance(bot_id)
    except Exception:
        logger.debug("Could not read the maintenance flag", exc_info=True)
        return _maintenance_on
    return _maintenance_on


def begin_maintenance(bot_id: str, minutes: int) -> "datetime":
    """Blocking. Returns the moment being promised, so the caller can say it
    back to the owner in the same words the users will get."""
    global _maintenance_on, _maintenance_until
    until = datetime.now(timezone.utc) + timedelta(minutes=max(1, minutes))
    schema = _family_schema()
    with db.pooled() as conn:
        conn.execute(
            f"""
            INSERT INTO {schema}.settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = excluded.value
            """,
            (MAINTENANCE_KEY_PREFIX + bot_id, until.isoformat()),
        )
        conn.commit()
    _maintenance_on, _maintenance_until = True, until
    return until


def end_maintenance(bot_id: str) -> None:
    """Blocking. Deletes the flag rather than blanking it, so "paused" is the
    presence of a row and there is no second way to spell "off"."""
    global _maintenance_on, _maintenance_until
    schema = _family_schema()
    with db.pooled() as conn:
        conn.execute(
            f"DELETE FROM {schema}.settings WHERE key = %s",
            (MAINTENANCE_KEY_PREFIX + bot_id,),
        )
        conn.commit()
    _maintenance_on, _maintenance_until = False, None


def in_maintenance() -> bool:
    return _maintenance_on


def maintenance_minutes_left() -> "int | None":
    """Whole minutes still promised, or None once the estimate has run out.

    None does not mean the pause is over -- only the owner ends that. It
    means there is no honest number to quote any more, and the bots say
    "shortly" instead of a figure they have already missed.
    """
    if not _maintenance_on or _maintenance_until is None:
        return None
    left = (_maintenance_until - datetime.now(timezone.utc)).total_seconds()
    if left <= 0:
        return None
    # Rounded up, so 90 seconds left is "2 minutes" rather than "1" -- but a
    # real ceiling, not seconds//60 + 1, which turns a flat ten minutes into
    # eleven the instant it is announced.
    return max(1, -(-int(left) // 60))


def is_paused() -> bool:
    """True when nothing slow should be *started*: either a stop signal has
    already arrived, or the owner has announced an update.

    The check every long handler makes. is_draining() is still the narrower
    question -- "is this process going away right now" -- and is what the
    shutdown path itself uses.
    """
    return _draining or _maintenance_on


def hold_for_update(user_id: int, chat_id: int, bot_id: "str | None" = None) -> None:
    """Remember that this person was turned away, so /finishupdates can tell
    them it is over. Blocking; best-effort.

    One row per person, not per attempt: someone who tries four times during
    an update is one person to apologise to, not four.
    """
    bot_id = bot_id or _bot_id
    if not bot_id:
        return
    schema = _family_schema()
    try:
        with db.pooled() as conn:
            conn.execute(
                f"""
                INSERT INTO {schema}.{WAITLIST_TABLE} (bot_id, user_id, chat_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (bot_id, user_id) DO NOTHING
                """,
                (bot_id, user_id, chat_id),
            )
            conn.commit()
    except Exception:
        logger.debug("Could not add %s to the update waitlist", user_id, exc_info=True)


def take_held(bot_id: str) -> "list[tuple[int, int]]":
    """Everyone waiting on this bot, as (user_id, chat_id), removed as they
    are handed over. Blocking.

    Deleted in the same statement that returns them, so a second
    /finishupdates -- or two of them racing -- cannot message anybody twice.
    """
    schema = _family_schema()
    with db.pooled() as conn:
        cur = conn.execute(
            f"DELETE FROM {schema}.{WAITLIST_TABLE} WHERE bot_id = %s "
            f"RETURNING user_id, chat_id",
            (bot_id,),
        )
        rows = cur.fetchall()
        conn.commit()
    return [(int(u), int(c)) for u, c in rows]


def in_flight() -> "list[tuple[int, str]]":
    """Who is mid-something right now, as (chat_id, the message they would
    get if it were interrupted) -- one entry per stretch of slow work.

    The same registry the shutdown path reads, exposed so the owner can warn
    these people *before* pressing deploy rather than as the door closes.
    """
    return list(_in_flight.values())


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------

def persistence():
    """Pass to ApplicationBuilder().persistence(). None when deploy safety is
    off, in which case every ConversationHandler must also drop
    persistent=True -- which is what persistent() below is for."""
    if not ENABLED:
        return None
    try:
        init_state_table()
    except Exception as exc:
        logger.warning(
            "No state table (%s) -- conversations will not survive a restart, "
            "which is how this bot behaved before.", exc,
        )
        return None
    return PostgresPersistence()


_persistence_on = False


def persistent() -> bool:
    """For ConversationHandler(persistent=..., name=...). Adding a persistent
    handler to an Application that has no persistence is an error, so the two
    have to agree."""
    return _persistence_on


def _on_stop_signal(sig: int) -> None:
    global _draining, _drain_started
    if _draining:
        return
    _draining = True
    _drain_started = time.monotonic()
    logger.info("Got %s -- draining. Finishing what's in flight, then stopping.",
                signal.Signals(sig).name if hasattr(signal, "Signals") else sig)
    app = _app
    if app is None:
        return
    asyncio.get_running_loop().create_task(_drain_and_stop(app))


async def _drain_and_stop(app) -> None:
    # Off the event loop: this is a database write, and the signal handler
    # that got us here runs *in* the loop -- blocking it would hold up the
    # very shutdown it is announcing.
    if _bot_id:
        try:
            await asyncio.to_thread(mark_expected_restart, _bot_id)
        except Exception:
            logger.debug("Could not leave a redeploy note", exc_info=True)
    try:
        await _tell_the_interrupted(app.bot)
    except Exception:
        logger.debug("Drain announcement failed", exc_info=True)
    try:
        app.stop_running()
    except RuntimeError:
        # A stop signal that arrived before run_polling() had finished
        # starting. Nothing is serving anyone yet, so there is nothing to
        # drain gracefully -- just go.
        logger.info("Stopped before startup finished; exiting.")
        os._exit(0)


def can_handle_signals() -> bool:
    return sys.platform != "win32" and hasattr(signal, "SIGTERM")


def polling_kwargs(**extra) -> dict:
    """Wrap each bot's run_polling() arguments.

    Where we can take the stop signals ourselves we do, because
    python-telegram-bot's own handler goes straight to shutdown and there is
    no way to get a word in before it -- and the word is the whole point:
    "an update interrupted you, send it again". Where we cannot (Windows has
    no loop.add_signal_handler), the key is simply left out and PTB's own
    default handling stands.
    """
    if ENABLED and can_handle_signals():
        extra["stop_signals"] = ()
    return extra


async def _persist_job(context) -> None:
    """Collect what changed and write it out. Both halves are needed: PTB's
    update_persistence() is what copies live user_data into the persistence
    object, and flush() is what puts it in Postgres."""
    app = _app
    if app is None or app.persistence is None:
        return
    try:
        await app.update_persistence()
        await app.persistence.flush()
    except Exception:
        logger.debug("Periodic state save failed; the next pass retries", exc_info=True)


def install(app, bot_id: str) -> None:
    """One line in each bot's main(), next to family_link.attach().

    Everything it wires is best-effort: a bot whose database is unreachable
    keeps running exactly as it did before any of this existed.
    """
    global _app, _bot_id, _persistence_on
    _app, _bot_id = app, bot_id
    _persistence_on = app.persistence is not None
    if not ENABLED:
        logger.info("Deploy safety off (DEPLOY_SAFETY=off).")
        return
    if not _persistence_on:
        logger.warning("Running without persistence -- open conversations will not survive a restart.")
    elif app.job_queue is not None:
        app.job_queue.run_repeating(_persist_job, interval=PERSIST_SECONDS, first=PERSIST_SECONDS)
    logger.info(
        "Deploy safety on: single-poller lease, state in %s, in-flight work announced on SIGTERM.",
        STATE_TABLE,
    )


async def on_start(bot_id: str) -> None:
    """Register as (part of) each bot's post_init, before it starts polling.

    Two jobs: make sure no previous container is still polling this token,
    and take the stop signals so a redeploy can say goodbye properly.
    """
    global _bot_id
    _bot_id = bot_id
    if not ENABLED:
        return
    await hold_the_lease(bot_id)

    # An update is usually several deploys, so a container that has just come
    # up has to find out whether it is still inside one before it starts
    # taking work it would only have to throw away again.
    try:
        await asyncio.to_thread(init_waitlist_table)
        if await asyncio.to_thread(refresh_maintenance, bot_id):
            logger.info("Still in maintenance -- not starting new long work yet.")
    except Exception:
        logger.debug("Could not read the maintenance flag at startup", exc_info=True)

    if not can_handle_signals():
        return

    # polling_kwargs() has already told python-telegram-bot not to install its
    # own handlers, so if none of these land the process would be deaf to
    # SIGTERM and the platform would go straight to SIGKILL. The plain
    # signal.signal() fallback exists for that case alone.
    loop = asyncio.get_running_loop()
    wanted = (signal.SIGTERM, signal.SIGINT)
    installed = 0
    for sig in wanted:
        try:
            loop.add_signal_handler(sig, _on_stop_signal, sig)
            installed += 1
        except (NotImplementedError, RuntimeError):
            logger.debug("Could not take signal %s through the loop.", sig)
    if installed:
        return
    for sig in wanted:
        try:
            signal.signal(sig, lambda number, frame: loop.call_soon_threadsafe(_on_stop_signal, number))
        except (ValueError, OSError):
            logger.warning("Nothing could take signal %s -- shutdown will not be graceful.", sig)


async def on_stop(application) -> None:
    """Register as the *first* thing in each bot's post_stop -- before
    flush_on_shutdown(), which closes the connection pool these writes go
    through.

    python-telegram-bot flushes persistence itself a moment later, during
    shutdown(). Doing it here as well is what makes the ordering explicit
    instead of load-bearing: by the time the pool closes, the state is
    already written.
    """
    if application.persistence is not None:
        try:
            await application.update_persistence()
            await application.persistence.flush()
            logger.info("In-progress state saved -- the next start picks it up.")
        except Exception:
            logger.warning("Could not save in-progress state on the way out.", exc_info=True)
    release_lease()
