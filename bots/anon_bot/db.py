"""Postgres layer for AnonBot -- these tables are this bot's
alone. The family shares one Postgres database now, but each bot gets its
own schema in it (DB_SCHEMA below), and no bot reads or writes another's
tables; the only shared tables are `family.*`, which family_link.py owns.

Owns the anonymous-inbox links, conversations,
and reply-routing (who owns which link, which conversation a follower's next
message belongs to, which owner-chat message maps to which conversation for
reply-swipes, and who's blocked whom), plus a Telegram Stars ledger +
donation-reminder cooldown for this bot's own /donate flow.

Postgres was chosen (over SQLite) so this survives an ephemeral cloud
container redeploy -- see DEPLOY.md.
"""
import logging
import os
import time
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone

from urllib.parse import urlsplit

import psycopg
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/anonbot"
)


# --- one shared database, one schema per bot ---------------------------------
# The whole family now lives in ONE Postgres database, with a schema per bot
# (family_link.py has the full layout). DB_SCHEMA is the one this bot owns.
# Nothing else in this file had to change: every statement below is still
# written against bare table names, and search_path resolves them into this
# bot's own schema, so the four bots' identically-named tables
# (user_settings, star_transactions, activity_events, ...) never collide.
# Leaving DB_SCHEMA unset keeps the old behaviour -- "public" in a database
# this bot has entirely to itself.
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

# ---------------------------------------------------------------------------
# Connection-string sanity check
# ---------------------------------------------------------------------------
# Two ways of pointing a bot at a cloud Postgres fail *quietly* rather than
# loudly, so both are worth catching at startup instead of in the data:
#
#   Transaction pooling -- Supabase/Supavisor on port 6543, or PgBouncer in
#   transaction mode -- multiplexes many clients over a few server
#   connections, so per-connection startup options do not survive from one
#   transaction to the next. The pool below passes search_path as exactly
#   such an option, which means the bot would read and write "public"
#   instead of its own schema, while still heartbeating perfectly. That
#   surfaces as wrong data rather than as a broken bot, which is the worst
#   way to find out. The session pooler (port 5432) keeps one server
#   connection per client and is the right one here.
#
#   An unencoded "@" or ":" in the password splits the URL in the wrong
#   place, so libpq ends up resolving a hostname that is really the tail of
#   the password -- a DNS error that says nothing about the real cause.
#
# These warn rather than refuse: an unusual setup is the owner's business,
# and a bot that will not start is worse than one that says why it might
# misbehave.
TRANSACTION_POOLER_PORTS = {6543}


def check_database_url(dsn: str = DATABASE_URL) -> list[str]:
    """Human-readable warnings about `dsn`; empty when it looks sane."""
    problems: list[str] = []
    try:
        parts = urlsplit(dsn)
    except ValueError as exc:
        return [f"DATABASE_URL could not be parsed ({exc})."]

    if parts.netloc.count("@") > 1:
        problems.append(
            "DATABASE_URL contains more than one '@'. If that is a literal "
            "'@' in the password, percent-encode it (@ -> %40, : -> %3A, "
            "/ -> %2F, # -> %23); otherwise the host is read from the wrong "
            "part of the string."
        )

    try:
        port = parts.port
    except ValueError:
        problems.append(
            "DATABASE_URL's port is not a number -- an unencoded ':' or '@' "
            "in the password is the usual reason."
        )
        port = None

    if port in TRANSACTION_POOLER_PORTS:
        problems.append(
            f"DATABASE_URL points at port {port}, which is a TRANSACTION "
            f"pooler. search_path is passed as a connection option and "
            f"transaction pooling discards it, so this bot would silently "
            f"use the 'public' schema instead of {DB_SCHEMA!r}. Use the "
            f"session pooler (port 5432)."
        )

    return problems



# ---------------------------------------------------------------------------
# One pooled connection per process
# ---------------------------------------------------------------------------
# Every function below used to open -- and immediately throw away -- its own
# Postgres connection. On a small shared cloud database that is by far the
# most expensive thing this bot does: a TCP round trip, a TLS handshake and a
# freshly forked backend process on the server, all to run one INSERT that
# takes microseconds. At one connection per Telegram update (plus one per
# heartbeat, per command poll, per donation check) it is also what decides
# how big the database instance has to be.
#
# A pool keeps a warm connection open instead and hands it out. Sized for
# cheap: one connection held, a couple more only while several things happen
# at once, and any extra handed back to the server after DB_POOL_MAX_IDLE
# seconds -- so an idle bot costs the database exactly one backend.
POOL_MIN = int(os.environ.get("DB_POOL_MIN", "1"))
POOL_MAX = int(os.environ.get("DB_POOL_MAX", "3"))
POOL_MAX_IDLE = float(os.environ.get("DB_POOL_MAX_IDLE", "120"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "15"))

# How long a pooled connection may sit unused before it is worth spending a
# round trip proving it is still alive. See _check_if_idle: the check was
# unconditional, and against a database on the other side of the world an
# unconditional check is the single most expensive thing about a small query.
POOL_CHECK_AFTER_IDLE = float(os.environ.get("DB_POOL_CHECK_AFTER_IDLE", "45"))

_pool: "ConnectionPool | None" = None
# id(connection) -> when it was last known good. Bounded by max_size. An id
# can be reused after a connection is closed, and the worst that costs is a
# skipped check on a connection that was only just opened -- which is alive
# by construction.
_last_known_good: "dict[int, float]" = {}


def _check_if_idle(conn) -> None:
    """The pool's checkout check, but only for connections that have actually
    been sitting there.

    A connection idle across a cloud provider's own network timeout comes back
    dead, and `ConnectionPool.check_connection` is the guard against handing
    one out. It is also a full round trip, and it was being paid on every
    checkout -- including the checkout half a second after the last one, on a
    connection that could not possibly have gone stale in between.

    That is most of them. It cost a quarter of a second each back when this
    bot's database was in ap-northeast-2 and the container in EU West -- a
    third of the cost of every read. Since v1.2.0 the database is in
    eu-central-1, beside the containers, which cuts the absolute cost by an
    order of magnitude but leaves the ratio alone: the check is still a whole
    extra round trip per read. A connection used within the last
    POOL_CHECK_AFTER_IDLE seconds is taken as alive, and everything quieter
    than that is still proved before use.
    """
    key = id(conn)
    now = time.monotonic()
    seen = _last_known_good.get(key)
    if seen is None or now - seen > POOL_CHECK_AFTER_IDLE:
        ConnectionPool.check_connection(conn)
    _last_known_good[key] = now
    if len(_last_known_good) > 4 * max(POOL_MAX, 1):
        for stale in [k for k, t in _last_known_good.items() if now - t > 3600]:
            _last_known_good.pop(stale, None)


def _get_pool() -> ConnectionPool:
    """Created on first use, never at import time -- init_db() has to be able
    to create the schema before anything connects into it."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            DATABASE_URL,
            min_size=POOL_MIN,
            max_size=POOL_MAX,
            max_idle=POOL_MAX_IDLE,
            timeout=POOL_TIMEOUT,
            kwargs={
                "options": f"-c search_path={DB_SCHEMA},public",
                # Keep an idle connection alive at the TCP level rather than
                # discovering it is dead on the next checkout. Cheaper than
                # the check it saves, and it happens while nobody is waiting.
                "keepalives": 1, "keepalives_idle": 30,
                "keepalives_interval": 10, "keepalives_count": 5,
            },
            check=_check_if_idle,
            name=f"{DB_SCHEMA}",
            open=True,
        )
    return _pool


def pooled():
    """A connection from the pool, as a context manager. The transaction is
    committed on a clean exit and rolled back on an exception; the connection
    itself goes back to the pool either way rather than being closed.

    For anything that writes. Reads should use pooled_read(), which is the
    same connection without the transaction around it."""
    return _get_pool().connection()


@contextmanager
def pooled_read():
    """A pooled connection in autocommit, for statements that only read.

    A read through pooled() costs three round trips to the database: the
    implicit BEGIN that psycopg opens with the first statement, the statement
    itself, and the COMMIT the context manager sends on the way out. Two of
    those exist to make a transaction nobody needed -- a single SELECT is
    atomic on its own.

    Measured against the family's actual database, one read: 28 ms through
    pooled(), 9 ms through this. The same shape holds wherever the database
    is; it is round trips, so it scales with the distance rather than washing
    out. Everything that writes -- and anything reading several statements
    that have to agree with each other -- still goes through pooled().
    """
    with _get_pool().connection() as conn:
        conn.set_autocommit(True)
        try:
            yield conn
        finally:
            # Back to the pool as it was found, so pooled() still gets a
            # connection that opens a transaction.
            try:
                conn.set_autocommit(False)
            except Exception:
                logging.getLogger(__name__).debug("Could not restore transaction mode", exc_info=True)


def close_pool() -> None:
    """Shutdown hook -- lets the process exit without waiting on the pool's
    own worker threads."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def connect(dsn: str = DATABASE_URL):
    """A brand-new, unpooled connection to an arbitrary database. Only the
    offline tools (db_merge.py) need this, because they hold two databases
    open at once and drive the transaction by hand. Everything in this module
    goes through pooled() instead."""
    return psycopg.connect(dsn, options=f"-c search_path={DB_SCHEMA},public")


def ensure_schema(dsn: str = DATABASE_URL) -> None:
    """Deliberately connects *without* the search_path option -- the schema
    it is about to create may not exist yet, and libpq would not complain
    but every later CREATE TABLE would land in public instead."""
    with closing(psycopg.connect(dsn)) as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        conn.commit()


def init_db(dsn: str = DATABASE_URL) -> None:
    for _problem in check_database_url(dsn):
        logging.getLogger(__name__).warning("%s", _problem)

    # Deliberately on a plain connection rather than the pool: the offline
    # tools (db_merge.py, migrate_to_shared_db.py) call this against a
    # *different* database than the one this process serves, and the pool
    # is bound to DATABASE_URL. It runs once, so there is nothing to save.
    ensure_schema(dsn)
    with closing(connect(dsn)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS star_transactions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username TEXT,
                amount_stars BIGINT NOT NULL,
                item TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL UNIQUE,
                charge_id TEXT,
                currency TEXT NOT NULL DEFAULT 'XTR',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Both safe to re-run on an existing table -- widens amount_stars
        # since some fiat currencies' minor-unit amounts can exceed a plain
        # INTEGER's range, and adds currency for bots migrating from
        # Stars-only donations (see shared_features.py's FIAT_CURRENCIES).
        conn.execute("ALTER TABLE star_transactions ALTER COLUMN amount_stars TYPE BIGINT")
        conn.execute("ALTER TABLE star_transactions ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'XTR'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS donation_prompts (
                user_id BIGINT PRIMARY KEY,
                action_count INTEGER NOT NULL DEFAULT 0,
                last_shown_at TEXT
            )
            """
        )
        # How many times this person has ever been shown the nudge. The
        # cadence is a schedule that runs out rather than a loop (see
        # DONATION_STEPS in shared_features.py), and this is the step counter
        # it reads. Safe to re-run on an existing table.
        conn.execute("ALTER TABLE donation_prompts ADD COLUMN IF NOT EXISTS times_shown INTEGER NOT NULL DEFAULT 0")
        # Set only when DONATION_PIN is on: the message this bot pinned, so
        # it can be unpinned again when they donate or when a newer nudge
        # replaces it.
        conn.execute("ALTER TABLE donation_prompts ADD COLUMN IF NOT EXISTS pinned_message_id BIGINT")
        # Nullable, no default -- NULL means "hasn't picked a language yet",
        # which is what gates the first-run picker in bot.py's /start.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id BIGINT PRIMARY KEY,
                language TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS anon_links (
                owner_user_id BIGINT PRIMARY KEY,
                token TEXT NOT NULL UNIQUE,
                is_paused INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS anon_conversations (
                id BIGSERIAL PRIMARY KEY,
                owner_user_id BIGINT NOT NULL,
                follower_user_id BIGINT NOT NULL,
                conv_number INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                last_activity_at TEXT NOT NULL,
                last_owner_msg_id BIGINT,
                last_follower_msg_id BIGINT
            )
            """
        )
        # Set when the guest sends their FIRST message in a conversation.
        # That one message is the only one either side may send without
        # saying what it answers -- it is the one that opens the thread, and
        # there is genuinely nothing above it. See handle_message.
        conn.execute("ALTER TABLE anon_conversations ADD COLUMN IF NOT EXISTS follower_first_msg_at TEXT")
        # Replaced by the column above. It asked "has the owner answered
        # yet?", which exempted every message a guest sent to an owner who
        # never answered -- so a guest's whole side of a one-way conversation
        # was still being routed by session state rather than by what it
        # replied to.
        conn.execute("ALTER TABLE anon_conversations DROP COLUMN IF EXISTS owner_replied_at")
        # Filed away, either by the owner from /conversations or by
        # prune_old_data once a conversation has been silent long enough for
        # its reply anchors to be removed. NULL means open.
        #
        # It is filing and nothing else: no message is ever refused because
        # of it, and the guest is never told. A conversation the owner has
        # archived un-archives itself the moment anything is relayed into it,
        # because a message arriving means it was not finished after all.
        conn.execute("ALTER TABLE anon_conversations ADD COLUMN IF NOT EXISTS archived_at TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_anon_conversations_pair "
            "ON anon_conversations (owner_user_id, follower_user_id)"
        )
        # What /conversations reads: one owner's threads, newest activity
        # first. Without it that is a sequential scan of every conversation
        # in the table on every page turn.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_anon_conversations_owner_activity "
            "ON anon_conversations (owner_user_id, last_activity_at DESC)"
        )
        # Natural key for a conversation -- also what scripts/db_merge.py
        # matches on when reconciling a local DB with a cloud one.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_anon_conversations_natural "
            "ON anon_conversations (owner_user_id, follower_user_id, conv_number)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS anon_follower_state (
                follower_user_id BIGINT PRIMARY KEY,
                owner_user_id BIGINT NOT NULL,
                conversation_id BIGINT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS anon_relay (
                chat_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                conversation_id BIGINT NOT NULL,
                PRIMARY KEY (chat_id, message_id)
            )
            """
        )
        # True for the Reply button's ForceReply prompt, and only for that.
        # The prompt is scaffolding: it exists to pin the reply box to one
        # conversation, and once the reply it asked for has arrived it has
        # nothing left to say. Knowing which rows are prompts is what lets
        # bot.py take them back down again -- and it has to be knowable from
        # the database rather than from user_data, because the tap and the
        # reply can land in different processes.
        # Vestigial since v1.4.0: it marked the Reply button's ForceReply
        # prompt, and there are no prompts. Kept, and kept being created, so
        # that a fresh database has the same shape as the live one -- nothing
        # reads it, nothing writes it, and its DEFAULT fills it in.
        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS is_prompt BOOLEAN NOT NULL DEFAULT FALSE")
        # The message in the OTHER chat that this one is the same message as
        # -- the copy that was delivered from it, or the original it was
        # copied from. A conversation exists twice, once in each chat, and
        # message ids are counted per chat, so nothing else in this schema
        # says which bubble here is which bubble there.
        #
        # It is what makes a reply to an OLDER message arrive on the right
        # bubble. Without it the only anchor available was the newest one in
        # the receiving chat, so answering the third message from the top
        # showed up on the other side as an answer to the most recent thing
        # said -- see record_relay_and_touch.
        #
        # Nullable, and NULL is not backfillable: the pairing is only
        # knowable at the moment of relaying, and the two chats hold
        # different numbers of bubbles for the same conversation (a header
        # line, an album, a message too long for one) so it cannot be
        # reconstructed by lining up what is already there. A row from before
        # this column falls back to the old behaviour rather than guessing.
        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS peer_message_id BIGINT")
        # When each bubble was written, and who wrote it: TRUE for a copy the
        # bot delivered, FALSE for the person's own message, NULL for the
        # bot's own words -- a header, a bookmark, a link's opening line.
        #
        # /export needs both. It builds a transcript from messages forwarded
        # back to the bot, and a forward carries its original date and who
        # wrote it, but not its message id -- so the time and the side are
        # the only way to say which conversation a forwarded message was in.
        # Times, not words: this is still nothing anybody wrote.
        #
        # NULL for every row from before these columns. They cannot be
        # backfilled, for the reason peer_message_id cannot, and a forward of
        # such a message is listed in the transcript as unmatched.
        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ")
        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS from_bot BOOLEAN")
        # "The first / newest message of THIS conversation in THIS chat" --
        # asked by get_routing_context on every un-replied message, and by
        # the bookmark /conversations and /which send. The primary key is
        # (chat_id, message_id), which answers neither without walking every
        # row the chat has.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_anon_relay_conversation "
            "ON anon_relay (chat_id, conversation_id, message_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS anon_blocks (
                owner_user_id BIGINT NOT NULL,
                follower_user_id BIGINT NOT NULL,
                blocked_at TEXT NOT NULL,
                PRIMARY KEY (owner_user_id, follower_user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_events (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_events_occurred_at ON activity_events (occurred_at)"
        )
        conn.commit()


# ---------- /status active-user tracking ----------

def record_activity_batch(user_ids) -> None:
    """One row per user per flush window -- see shared_features.py's
    track_activity, which buffers them. Sent as a single statement whatever
    the batch size: both readers of this table are COUNT(DISTINCT user_id)
    over a time window, so nothing depends on a row per update."""
    ids = list(user_ids)
    if not ids:
        return
    with pooled() as conn:
        conn.execute(
            "INSERT INTO activity_events (user_id, occurred_at) "
            "SELECT unnest(%s::bigint[]), now()",
            (ids,),
        )
        conn.commit()


def count_active_users_since(since) -> int:
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM activity_events WHERE occurred_at >= %s",
            (since,),
        )
        return cur.fetchone()[0]



def active_user_ids_since(since) -> list[int]:
    """Everyone with activity since `since`. Used by the family bus for an
    aimed broadcast -- see BROADCAST_ACTIVE_DAYS in family_link.py."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT DISTINCT user_id FROM activity_events WHERE occurred_at >= %s",
            (since,),
        )
        return [row[0] for row in cur.fetchall()]

def list_all_users() -> list[int]:
    """Everyone this bot could send an unprompted message to.

    The union of two tables because neither is the whole answer on its own:
    user_settings has a row per person who has ever picked a setting and is never
    pruned, while activity_events reaches people who only ever used the bot
    without changing anything -- but is pruned at ACTIVITY_RETENTION_DAYS.
    Together they are "everyone we still know about", which is the honest
    scope of a broadcast.
    """
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT user_id FROM user_settings "
            "UNION "
            "SELECT DISTINCT user_id FROM activity_events"
        )
        return [int(r[0]) for r in cur.fetchall()]


def get_user_language(user_id: int) -> str | None:
    """None means the user hasn't picked a language yet (no row, or a row
    with no language set)."""
    with pooled_read() as conn:
        cur = conn.execute("SELECT language FROM user_settings WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None


def set_user_language(user_id: int, language: str) -> None:
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, language) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET language = excluded.language
            """,
            (user_id, language),
        )
        conn.commit()


# ---------- Telegram Stars ledger (this bot's /donate only) ----------

def record_star_invoice(
    user_id: int,
    username: str | None,
    amount_stars: int,
    item: str,
    payload: str,
    status: str = "invoiced",
    currency: str = "XTR",
) -> None:
    """amount_stars is in the currency's smallest unit for fiat currencies
    (see shared_features.py's FIAT_CURRENCIES), or a plain Stars count for
    the default currency="XTR"."""
    now = datetime.now(timezone.utc).isoformat()
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO star_transactions
                (user_id, username, amount_stars, item, status, payload, currency, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, username, amount_stars, item, status, payload, currency, now, now),
        )
        conn.commit()


def update_star_transaction(payload: str, status: str, charge_id: str | None = None) -> None:
    with pooled() as conn:
        conn.execute(
            "UPDATE star_transactions SET status = %s, charge_id = COALESCE(%s, charge_id), updated_at = %s WHERE payload = %s",
            (status, charge_id, datetime.now(timezone.utc).isoformat(), payload),
        )
        conn.commit()


# ---------- donation-reminder cooldown ----------

def bump_donation_action(user_id: int) -> tuple[int, str | None, int, bool]:
    """Increments this user's action counter and returns everything the nudge
    decision needs: (actions since the last nudge, when it was last shown,
    how many times it has ever been shown, has this person ever donated).

    One statement. This runs on the success path of every completed action --
    every finished pack, every conversion, every download -- so it is one of
    the hottest writes in the family, and the database is on another
    continent. The donation check used to be two round trips and the "have
    they already given" question would have made it three.

    `times_shown` is what turns the cadence from "every N actions forever"
    into a schedule that runs out: see DONATION_STEPS in shared_features.py.
    The paid check is what stops the bot thanking somebody by asking them
    again.
    """
    with pooled() as conn:
        cur = conn.execute(
            """
            WITH bumped AS (
                INSERT INTO donation_prompts (user_id, action_count, last_shown_at)
                VALUES (%(uid)s, 1, NULL)
                ON CONFLICT (user_id) DO UPDATE
                   SET action_count = donation_prompts.action_count + 1
                RETURNING action_count, last_shown_at, times_shown
            )
            SELECT b.action_count, b.last_shown_at, b.times_shown,
                   EXISTS (SELECT 1 FROM star_transactions t
                            WHERE t.user_id = %(uid)s AND t.status = 'paid')
            FROM bumped b
            """,
            {"uid": user_id},
        )
        row = cur.fetchone()
        conn.commit()
        return row[0], row[1], row[2] or 0, bool(row[3])


def reset_donation_prompt(user_id: int) -> None:
    """Zeroes the action counter, stamps 'last_shown_at' and counts the
    showing -- call right after actually showing the nudge, not on every
    check."""
    now = datetime.now(timezone.utc).isoformat()
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO donation_prompts (user_id, action_count, last_shown_at, times_shown)
            VALUES (%s, 0, %s, 1)
            ON CONFLICT (user_id) DO UPDATE SET
                action_count = 0,
                last_shown_at = excluded.last_shown_at,
                times_shown = donation_prompts.times_shown + 1
            """,
            (user_id, now),
        )
        conn.commit()


def get_pinned_donation_message(user_id: int) -> int | None:
    """The id of the nudge this bot pinned in that person's chat, if any."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT pinned_message_id FROM donation_prompts WHERE user_id = %s", (user_id,)
        )
        row = cur.fetchone()
        return row[0] if row else None


def set_pinned_donation_message(user_id: int, message_id: int | None) -> None:
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO donation_prompts (user_id, action_count, pinned_message_id)
            VALUES (%s, 0, %s)
            ON CONFLICT (user_id) DO UPDATE SET pinned_message_id = excluded.pinned_message_id
            """,
            (user_id, message_id),
        )
        conn.commit()


# ---------- AnonBot: anonymous-inbox links, conversations, reply routing, blocks ----------

def get_or_create_anon_link(owner_user_id: int) -> tuple[str, bool]:
    """(token, is_paused) for this owner, creating the row on first use. The
    token never changes on its own -- only regenerate_anon_link() rolls it.

    One statement: an upsert that does nothing on conflict still RETURNINGs
    nothing, so the read comes first and the insert only runs for a genuinely
    new owner. /link used to call this and then get_anon_link_state, which
    was two round trips for two columns of the same row."""
    with pooled() as conn:
        cur = conn.execute(
            "SELECT token, is_paused FROM anon_links WHERE owner_user_id = %s", (owner_user_id,)
        )
        row = cur.fetchone()
        if row:
            return row[0], bool(row[1])
        token = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO anon_links (owner_user_id, token, is_paused, created_at) "
            "VALUES (%s, %s, 0, %s) ON CONFLICT (owner_user_id) DO NOTHING",
            (owner_user_id, token, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return token, False


def regenerate_anon_link(owner_user_id: int) -> tuple[str, bool]:
    """Fresh token -- invalidates the old link for NEW conversations.
    Conversations already in progress keep working since they're routed by
    conversation_id, not by the token.

    Returns (token, is_paused). The paused flag is deliberately left alone --
    a new link on a paused inbox is still paused -- and returned so the
    caller can redraw the screen without a second query for it."""
    token = uuid.uuid4().hex
    with pooled() as conn:
        cur = conn.execute(
            """
            INSERT INTO anon_links (owner_user_id, token, is_paused, created_at) VALUES (%s, %s, 0, %s)
            ON CONFLICT (owner_user_id) DO UPDATE SET token = excluded.token
            RETURNING token, is_paused
            """,
            (owner_user_id, token, datetime.now(timezone.utc).isoformat()),
        )
        row = cur.fetchone()
        conn.commit()
    return row[0], bool(row[1])


def get_link_view(token: str, follower_user_id: int) -> tuple[int | None, bool, bool]:
    """Everything the "someone tapped a link" path needs to decide what to
    do: (owner id or None, is the inbox paused, has this follower been
    blocked). One query where there used to be three, on a path that runs
    every time anyone opens anyone's inbox link."""
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT l.owner_user_id, l.is_paused,
                   EXISTS (SELECT 1 FROM anon_blocks b
                           WHERE b.owner_user_id = l.owner_user_id
                             AND b.follower_user_id = %s)
            FROM anon_links l WHERE l.token = %s
            """,
            (follower_user_id, token),
        )
        row = cur.fetchone()
        if not row:
            return None, False, False
        return row[0], bool(row[1]), bool(row[2])


def get_delivery_context(owner_user_id: int, follower_user_id: int) -> tuple[bool, bool, str | None]:
    """(is this follower blocked, does the inbox still exist, the owner's
    language). One query on the hot path of every anonymous message -- it was
    three, and the third of them was a whole extra connection just to look up
    which language to write the header in."""
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT EXISTS (SELECT 1 FROM anon_blocks
                           WHERE owner_user_id = %s AND follower_user_id = %s),
                   EXISTS (SELECT 1 FROM anon_links WHERE owner_user_id = %s),
                   (SELECT language FROM user_settings WHERE user_id = %s)
            """,
            (owner_user_id, follower_user_id, owner_user_id, owner_user_id),
        )
        blocked, inbox_exists, language = cur.fetchone()
        return bool(blocked), bool(inbox_exists), language



def set_anon_link_paused(owner_user_id: int, paused: bool) -> None:
    with pooled() as conn:
        conn.execute(
            "UPDATE anon_links SET is_paused = %s WHERE owner_user_id = %s", (int(paused), owner_user_id)
        )
        conn.commit()


def get_anon_link_state(owner_user_id: int) -> dict | None:
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT token, is_paused, created_at FROM anon_links WHERE owner_user_id = %s", (owner_user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {"token": row[0], "is_paused": bool(row[1]), "created_at": row[2]}


def start_new_anon_conversation(owner_user_id: int, follower_user_id: int) -> dict:
    """Always creates a brand-new conversation row -- this is what makes
    tapping the link again 'the start of a new conversation' -- and points
    the follower's active-routing state at it, so their very next un-replied
    message lands here instead of wherever they left off before."""
    with pooled() as conn:
        # Numbered per OWNER, not per (owner, follower) pair. The number is
        # the only thing either side is ever told about a thread, and per-pair
        # numbering restarted it at 1 for every new person -- so three
        # different strangers all arrived in the owner's chat as
        # "Conversation #1", and /blocked listed two separate guests both
        # described as "#1". Existing rows are left exactly as they are: the
        # owner has already read those numbers in their own chat and
        # renumbering would rewrite what they saw. Because this takes the
        # owner's highest number rather than the pair's, every number issued
        # from here on is above all of them, so no NEW collision can appear.
        cur = conn.execute(
            "SELECT COALESCE(MAX(conv_number), 0) FROM anon_conversations "
            "WHERE owner_user_id = %s",
            (owner_user_id,),
        )
        conv_number = cur.fetchone()[0] + 1
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            INSERT INTO anon_conversations
                (owner_user_id, follower_user_id, conv_number, started_at, last_activity_at,
                 last_owner_msg_id, last_follower_msg_id)
            VALUES (%s, %s, %s, %s, %s, NULL, NULL)
            RETURNING id
            """,
            (owner_user_id, follower_user_id, conv_number, now, now),
        )
        conversation_id = cur.fetchone()[0]
        conn.execute(
            """
            INSERT INTO anon_follower_state (follower_user_id, owner_user_id, conversation_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (follower_user_id) DO UPDATE SET
                owner_user_id = excluded.owner_user_id, conversation_id = excluded.conversation_id
            """,
            (follower_user_id, owner_user_id, conversation_id),
        )
        conn.commit()
        return {
            "id": conversation_id, "conv_number": conv_number,
            "owner_user_id": owner_user_id, "follower_user_id": follower_user_id,
            "last_owner_msg_id": None, "last_follower_msg_id": None,
        }


def get_active_conversation_for_follower(follower_user_id: int) -> dict | None:
    """Where a follower's next un-prompted message should be routed --
    'active' meaning 'the conversation their most recent /start link tap
    pointed at', see start_new_anon_conversation()."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT owner_user_id, conversation_id FROM anon_follower_state WHERE follower_user_id = %s",
            (follower_user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        owner_user_id, conversation_id = row
        cur = conn.execute(
            "SELECT conv_number, last_owner_msg_id, last_follower_msg_id, follower_first_msg_at "
            "FROM anon_conversations WHERE id = %s",
            (conversation_id,),
        )
        conv_row = cur.fetchone()
        if not conv_row:
            return None
        return {
            "id": conversation_id, "owner_user_id": owner_user_id, "follower_user_id": follower_user_id,
            "conv_number": conv_row[0], "last_owner_msg_id": conv_row[1], "last_follower_msg_id": conv_row[2], "follower_first_msg_at": conv_row[3],
        }


def get_conversation(conversation_id: int) -> dict | None:
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT owner_user_id, follower_user_id, conv_number, last_owner_msg_id,
                   last_follower_msg_id, follower_first_msg_at, started_at,
                   last_activity_at, archived_at
            FROM anon_conversations WHERE id = %s
            """,
            (conversation_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": conversation_id, "owner_user_id": row[0], "follower_user_id": row[1],
            "conv_number": row[2], "last_owner_msg_id": row[3], "last_follower_msg_id": row[4],
            "follower_first_msg_at": row[5], "started_at": row[6],
            "last_activity_at": row[7], "archived_at": row[8],
        }



def record_anon_relays(chat_id: int, message_ids, conversation_id: int) -> None:
    """Remembers 'these messages, in this chat, belong to this conversation'
    so a later reply can be traced back to the right thread even with many
    conversations interleaved in the same chat.

    Takes a list because a media message with a header goes out as two, and
    both are valid reply anchors; one statement covers however many.

    There used to be an `is_prompt` flag here, marking the Reply button's
    ForceReply prompt as the one kind of row meant to be deleted again once
    answered. There are no prompts, so nothing passed it and nothing read the
    column. The column itself stays where it is: dropping one from a live
    table to reclaim a bit per row is not a trade worth making, and it keeps
    every deployment's schema identical."""
    ids = list(message_ids)
    if not ids:
        return
    with pooled() as conn:
        conn.execute(
            # The bot's own words, so from_bot stays NULL: /export leaves a
            # forwarded header or bookmark out of a transcript rather than
            # attributing it to anybody in the conversation.
            "INSERT INTO anon_relay (chat_id, message_id, conversation_id, sent_at) "
            "SELECT %s, unnest(%s::bigint[]), %s, now() "
            "ON CONFLICT (chat_id, message_id) DO UPDATE SET "
            "conversation_id = excluded.conversation_id, sent_at = excluded.sent_at, "
            "from_bot = NULL",
            (chat_id, ids, conversation_id),
        )
        conn.commit()


def relay_rows_between(chat_id: int, since, until) -> list[dict]:
    """One chat's relay rows written between two times: which conversation,
    when, and whether the bot wrote the bubble. What /export places a
    forwarded message by -- rows only, since there is no content here to
    return."""
    with pooled_read() as conn:
        rows = conn.execute(
            "SELECT conversation_id, sent_at, from_bot FROM anon_relay "
            "WHERE chat_id = %s AND sent_at BETWEEN %s AND %s",
            (chat_id, since, until),
        ).fetchall()
    return [{"conversation_id": row[0], "sent_at": row[1], "from_bot": row[2]} for row in rows]


def forget_anon_relay(chat_id: int, message_id: int) -> None:
    """Drop one relay row, so nothing is left pointing at a message that no
    longer exists."""
    with pooled() as conn:
        conn.execute(
            "DELETE FROM anon_relay WHERE chat_id = %s AND message_id = %s",
            (chat_id, message_id),
        )
        conn.commit()


def record_relay_and_touch(
    conversation_id: int,
    owner_chat_id: int, owner_message_ids,
    follower_chat_id: int, follower_message_ids,
    last_owner_msg_id: int, last_follower_msg_id: int,
    owner_sent_at=None, follower_sent_at=None, delivered_to: "str | None" = None,
) -> None:
    """Everything one relayed message leaves behind, in one statement.

    `delivered_to` is "owner" or "follower": the side whose bubbles the bot
    wrote, as copies of the other side's message. With the two times, it is
    what /export places a forwarded message by (see transcript.place).

    Both chats get rows, and they get them together. Which conversation a
    reply belongs to is read out of anon_relay, so a message with no row is
    a message neither side can answer -- and the anchors are what make that
    reply quote the right bubble. A data-modifying CTE puts the insert and
    the anchor update in a single round trip, which matters here rather than
    generally: the database is on another continent from the container, so
    each extra statement on the hot path of every message is a real fraction
    of a second added to how long "Sent" takes to appear.

    Either id list may be empty; the arrays simply contribute no rows.

    The guest's own messages are in here too, which they were not before.
    Without them the guest's side of the chat was only half-tracked: editing
    something they had written got no answer at all, while the owner editing
    a reply was told the edit had not travelled, and a guest quoting their
    own earlier message was told it matched no conversation.

    Every row also records its counterpart in the other chat, and the two
    anchor arguments are already exactly that: `last_follower_msg_id` is the
    delivered end of this relay on the follower's side, so it is what each
    owner-side row of the same relay corresponds to, and the other way
    round. One relay can be several bubbles on one side and one on the
    other -- a header line above an uncaptioned sticker, a message too long
    for one bubble, an album -- and every bubble of it points at the single
    bubble the other side would quote, which is the last one sent there.
    That is the same id the `last_*` anchors carry, so the two agree by
    construction rather than by being kept in step.

    What it buys is a reply to an OLDER message landing on the right bubble.
    The anchors alone can only say "the newest thing in that chat", so
    answering the third message from the top arrived on the other side as an
    answer to the most recent one -- confusing, and confusing in the one
    direction that matters, since a conversation held out of order is
    exactly what a threaded inbox is for.

    Clearing `archived_at` here is the whole of un-archiving. Filing a
    conversation away says "I am done with this one", and a message landing
    in it says otherwise -- from either side, and without either of them
    having to know the flag exists.
    """
    with pooled() as conn:
        conn.execute(
            """
            WITH written AS (
                INSERT INTO anon_relay (chat_id, message_id, conversation_id, peer_message_id,
                                        sent_at, from_bot)
                SELECT chat_id, message_id, %(conv)s, peer, sent_at, from_bot FROM (
                    SELECT %(ochat)s::bigint AS chat_id, unnest(%(oids)s::bigint[]) AS message_id,
                           %(fmsg)s::bigint AS peer, %(osent)s::timestamptz AS sent_at,
                           %(obot)s::boolean AS from_bot
                    UNION ALL
                    SELECT %(fchat)s::bigint, unnest(%(fids)s::bigint[]), %(omsg)s::bigint,
                           %(fsent)s::timestamptz, %(fbot)s::boolean
                ) s
                ON CONFLICT (chat_id, message_id) DO UPDATE
                   SET conversation_id = excluded.conversation_id,
                       peer_message_id = excluded.peer_message_id,
                       sent_at = excluded.sent_at,
                       from_bot = excluded.from_bot
            )
            UPDATE anon_conversations
               SET last_owner_msg_id = %(omsg)s, last_follower_msg_id = %(fmsg)s,
                   last_activity_at = %(now)s, archived_at = NULL
             WHERE id = %(conv)s
            """,
            {
                "conv": conversation_id,
                "ochat": owner_chat_id, "oids": list(owner_message_ids),
                "fchat": follower_chat_id, "fids": list(follower_message_ids),
                "omsg": last_owner_msg_id, "fmsg": last_follower_msg_id,
                "osent": owner_sent_at, "fsent": follower_sent_at,
                "obot": {"owner": True, "follower": False}.get(delivered_to),
                "fbot": {"owner": False, "follower": True}.get(delivered_to),
                "now": datetime.now(timezone.utc).isoformat(),
            },
        )
        conn.commit()


def mark_follower_opened(conversation_id: int) -> None:
    """Records that the guest has now sent their opening message, which is
    what spends this conversation's one exemption from the reply rule."""
    with pooled() as conn:
        conn.execute(
            "UPDATE anon_conversations SET follower_first_msg_at = %s "
            "WHERE id = %s AND follower_first_msg_at IS NULL",
            (datetime.now(timezone.utc).isoformat(), conversation_id),
        )
        conn.commit()


def count_owner_conversations(owner_user_id: int) -> int:
    """How many conversations this user is the inbox owner of, counting only
    the ones something was actually said in. A bare message from someone with
    any at all is ambiguous -- it could be meant for any of them -- which is
    exactly what the reply rule exists to resolve.

    A link tap creates a row whether or not the guest ever writes, so counting
    rows counted people who opened the link and left. That pushed an owner
    into the ambiguous branch on the strength of conversations that had never
    contained a word."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT count(*) FROM anon_conversations WHERE owner_user_id = %s "
            "AND (follower_first_msg_at IS NOT NULL OR last_owner_msg_id IS NOT NULL)",
            (owner_user_id,),
        )
        return cur.fetchone()[0]


def get_routing_context(user_id: int, chat_id: int) -> dict:
    """Everything handle_message needs to route one un-replied message, in a
    single round trip.

    This used to be two queries and, once the opening-message exemption had to
    start checking for other live threads, would have been three. The database
    is a long way from the containers -- a bare SELECT 1 measures about a
    second -- so three sequential round trips on the hot path of every message
    is the most expensive thing this bot does. All three answers come from
    different tables and none depends on another, so one statement does.

    Returns:
      active           -- the conversation an un-replied message would go to, or None
      owned            -- how many live conversations this user owns an inbox for
      newest_is_active -- whether the last thing this bot put in this chat
                          belongs to `active`, i.e. nothing from another
                          thread has arrived since it was opened
      active_anchor    -- the newest message id in this chat belonging to
                          `active`, so a refusal can be sent as a reply to the
                          very message it is asking the person to reply to

    `newest_is_active` used to be `other_threads` -- "does this chat hold any
    conversation at all besides the active one" -- which is true for every
    returning guest and so refused the opening message of every inbox after
    their first. Relay message ids climb within a chat, so ORDER BY
    message_id DESC LIMIT 1 is the newest bot message in it, and asking
    whether *that* belongs to the active conversation is the same safety
    check made against what actually happened rather than against what has
    ever happened.
    """
    with pooled_read() as conn:
        cur = conn.execute(
            """
            WITH state AS (
                SELECT owner_user_id, conversation_id
                FROM anon_follower_state WHERE follower_user_id = %(uid)s
            )
            SELECT
              s.owner_user_id, s.conversation_id,
              c.conv_number, c.last_owner_msg_id, c.last_follower_msg_id, c.follower_first_msg_at,
              (SELECT count(*) FROM anon_conversations o
                WHERE o.owner_user_id = %(uid)s
                  AND (o.follower_first_msg_at IS NOT NULL OR o.last_owner_msg_id IS NOT NULL)),
              (SELECT r.conversation_id FROM anon_relay r
                WHERE r.chat_id = %(chat)s
                ORDER BY r.message_id DESC LIMIT 1),
              -- The newest thing this bot put in this chat for the ACTIVE
              -- conversation, which is the message a refusal points at. A
              -- refusal that says "reply to the message you are answering"
              -- without saying which one is the frustrating half of this
              -- rule; sending it as a reply to this id makes it visible.
              (SELECT r.message_id FROM anon_relay r
                WHERE r.chat_id = %(chat)s AND r.conversation_id = s.conversation_id
                ORDER BY r.message_id DESC LIMIT 1)
            FROM (SELECT 1) AS one
            LEFT JOIN state s ON TRUE
            LEFT JOIN anon_conversations c ON c.id = s.conversation_id
            """,
            {"uid": user_id, "chat": chat_id},
        )
        row = cur.fetchone()
        owner_id, conversation_id = row[0], row[1]
        active = None
        if conversation_id is not None and row[2] is not None:
            active = {
                "id": conversation_id, "owner_user_id": owner_id, "follower_user_id": user_id,
                "conv_number": row[2], "last_owner_msg_id": row[3],
                "last_follower_msg_id": row[4], "follower_first_msg_at": row[5],
            }
        newest = row[7]
        # No relay rows at all means nothing has been said in this chat, so
        # there is nothing the message could be answering either.
        newest_is_active = newest is None or newest == conversation_id
        return {"active": active, "owned": row[6] or 0,
                "newest_is_active": newest_is_active,
                "active_anchor": row[8]}


def get_relay_row(chat_id: int, message_id: int) -> "dict | None":
    """This message's relay row: which conversation it belongs to, and which
    message in the other chat it is the same message as.

    Both in one read because the caller that needs the peer is
    handle_message, on the hot path of every reply, and the peer is a column
    on the row it was already fetching.

    `peer_message_id` is None for a row that has no counterpart -- the line
    announcing a new conversation, a /conversations bookmark -- and for
    anything relayed before the column existed. Neither is an error: the
    caller falls back to the conversation's newest anchor, which is what it
    used before there was anything better.

    The `is_prompt` column stays where it is. Nothing writes True to it now,
    so it is uniformly False, and dropping a column from a live table to
    reclaim one bit per row is not a trade worth making."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT conversation_id, peer_message_id FROM anon_relay "
            "WHERE chat_id = %s AND message_id = %s",
            (chat_id, message_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {"conversation_id": row[0], "peer_message_id": row[1]}


def get_conversation_for_relay(chat_id: int, message_id: int) -> "int | None":
    """Which conversation this message in this chat belongs to, if any.

    For the callers that have no use for the peer -- /which, /archive, and
    the answer to an edit -- all of which ask one question about one message
    and then do something that has nothing to do with delivering anything."""
    row = get_relay_row(chat_id, message_id)
    return row["conversation_id"] if row else None



def clear_follower_state(follower_user_id: int) -> bool:
    """Forgets where this follower's next un-replied message was going to be
    routed, which is what /cancel does to an open ask session. The
    conversation row itself is left alone -- it is a record of messages that
    really were sent, and both sides can still reply into it by replying to
    a message from it. Returns whether there was anything to forget.

    Tapping the inbox link again starts a fresh conversation, exactly as it
    did before; see start_new_anon_conversation."""
    with pooled() as conn:
        cur = conn.execute(
            "DELETE FROM anon_follower_state WHERE follower_user_id = %s",
            (follower_user_id,),
        )
        conn.commit()
        return cur.rowcount > 0


def set_anon_blocked(owner_user_id: int, follower_user_id: int, blocked: bool) -> None:
    with pooled() as conn:
        if blocked:
            conn.execute(
                "INSERT INTO anon_blocks (owner_user_id, follower_user_id, blocked_at) VALUES (%s, %s, %s) "
                "ON CONFLICT (owner_user_id, follower_user_id) DO NOTHING",
                (owner_user_id, follower_user_id, datetime.now(timezone.utc).isoformat()),
            )
        else:
            conn.execute(
                "DELETE FROM anon_blocks WHERE owner_user_id = %s AND follower_user_id = %s",
                (owner_user_id, follower_user_id),
            )
        conn.commit()


def list_anon_blocks_with_conversations(owner_user_id: int) -> list[tuple[int | None, list[int]]]:
    """Blocked guests, each as (a conversation id to address them by, the
    conversation numbers they used).

    /blocked used to identify people by a hashed pseudonym. Conversation
    numbers do the same job with something the owner has actually seen in
    their chat -- and unlike the pseudonym they carry no identity at all,
    stable or otherwise. One query rather than one per blocked guest.

    The first element used to be the guest's Telegram user id, which bot.py
    then put in the unblock button's callback_data. Callback data is part of
    the keyboard Telegram hands to the client, so anything able to read a
    message's markup could read it -- and in a bot whose whole premise is
    that the owner never learns who is writing, that is the one field that
    must not leave the server. A conversation id says the same thing to the
    bot and nothing at all about the person.
    """
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT MIN(c.id),
                   COALESCE(ARRAY_AGG(c.conv_number ORDER BY c.conv_number)
                            FILTER (WHERE c.conv_number IS NOT NULL), '{}')
            FROM anon_blocks b
            LEFT JOIN anon_conversations c
                   ON c.owner_user_id = b.owner_user_id
                  AND c.follower_user_id = b.follower_user_id
            WHERE b.owner_user_id = %s
            GROUP BY b.follower_user_id, b.blocked_at
            ORDER BY b.blocked_at DESC
            """,
            (owner_user_id,),
        )
        return [(row[0], list(row[1])) for row in cur.fetchall()]


# ---------- the owner's own view of their inbox (/conversations) ----------
# Three states, and they do not overlap: open, archived, blocked. The header
# of /conversations counts all three; the list itself has a tab for the first
# two, and blocked threads belong to /blocked, which already lists them with
# an Undo button under each.
#
# "Open" means reachable, not "ever existed". A link tap nobody wrote into is
# not a conversation anybody had, and a thread whose reply anchors
# prune_old_data has removed has been archived by then -- so the number is
# one the owner can act on. /stats keeps the lifetime total.

CONVERSATIONS_PER_PAGE = 6

# A conversation only counts once somebody has said something in it, and a
# blocked guest's thread is neither open nor archived. Both conditions are
# needed by every query below, so they are written once.
_LIVE_CONVERSATIONS = """
    FROM anon_conversations c
    LEFT JOIN anon_blocks b
           ON b.owner_user_id = c.owner_user_id
          AND b.follower_user_id = c.follower_user_id
   WHERE c.owner_user_id = %(owner)s
     AND (c.follower_first_msg_at IS NOT NULL OR c.last_owner_msg_id IS NOT NULL)
"""


def count_owner_conversation_states(owner_user_id: int) -> dict:
    """How many of this owner's threads are open, archived and blocked."""
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT
              count(*) FILTER (WHERE b.follower_user_id IS NULL AND c.archived_at IS NULL),
              count(*) FILTER (WHERE b.follower_user_id IS NULL AND c.archived_at IS NOT NULL),
              count(*) FILTER (WHERE b.follower_user_id IS NOT NULL)
            """
            + _LIVE_CONVERSATIONS,
            {"owner": owner_user_id},
        )
        row = cur.fetchone()
        return {"open": row[0] or 0, "archived": row[1] or 0, "blocked": row[2] or 0}


def list_owner_conversations(owner_user_id: int, archived: bool = False,
                             offset: int = 0, limit: int = CONVERSATIONS_PER_PAGE) -> list[dict]:
    """One page of the owner's threads, whichever tab they are looking at,
    newest activity first -- which is the order an inbox is read in.

    `archived` is a bound parameter compared against the column rather than
    two branches of SQL text, so there is still exactly one statement here
    and nothing is built by concatenation."""
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT c.id, c.conv_number, c.started_at, c.last_activity_at, c.archived_at
            """
            + _LIVE_CONVERSATIONS
            + """
     AND b.follower_user_id IS NULL
     AND (c.archived_at IS NOT NULL) = %(archived)s
   ORDER BY c.last_activity_at DESC, c.conv_number DESC
   LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"owner": owner_user_id, "archived": archived,
             "limit": limit, "offset": max(0, offset)},
        )
        return [
            {"id": r[0], "conv_number": r[1], "started_at": r[2],
             "last_activity_at": r[3], "archived_at": r[4]}
            for r in cur.fetchall()
        ]


def set_conversation_archived(conversation_id: int, owner_user_id: int, archived: bool) -> bool:
    """File a conversation away, or bring it back. Returns whether there was
    such a conversation and it was this owner's to file.

    The owner id is in the WHERE clause as well as in the handler's check.
    The handler is the real gate; this is the one that still holds if a
    future caller forgets to write one."""
    with pooled() as conn:
        cur = conn.execute(
            "UPDATE anon_conversations SET archived_at = %s "
            "WHERE id = %s AND owner_user_id = %s",
            (datetime.now(timezone.utc).isoformat() if archived else None,
             conversation_id, owner_user_id),
        )
        changed = cur.rowcount > 0
        conn.commit()
        return changed


# ---------- /export ----------
# The bot already knows which message id in which chat belonged to which
# conversation: anon_relay has held exactly that since v1.1, because a
# swipe-reply on an old message has to resolve to a thread. Until 1.7.0
# /export ignored it and asked people to forward their own chat back at
# itself, which is a strange thing to ask when the index is right here.
#
# Neither of these functions reads a word anybody wrote. They answer "which
# messages, in which order" and nothing else -- which is all anon_relay has
# ever held.


def list_exportable_conversations(user_id: int, chat_id: int) -> list[dict]:
    """Every conversation this person is in, from either side, with how many
    of its messages are still on record in their own chat.

    `from_bot IS NOT NULL` is the filter that matters. NULL means one of two
    things -- a line the bot wrote in its own voice (a header, a bookmark), or
    a row from before v1.6.0, when the column did not exist -- and neither is
    a message in the conversation that can be attributed to a side.
    """
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT c.id, c.conv_number, c.started_at, c.last_activity_at,
                   (c.owner_user_id = %(me)s) AS is_owner,
                   count(r.message_id) FILTER (WHERE r.from_bot IS NOT NULL) AS messages
              FROM anon_conversations c
              LEFT JOIN anon_relay r
                     ON r.conversation_id = c.id AND r.chat_id = %(chat)s
             WHERE c.owner_user_id = %(me)s OR c.follower_user_id = %(me)s
             GROUP BY c.id, c.conv_number, c.started_at, c.last_activity_at, c.owner_user_id
            HAVING count(r.message_id) FILTER (WHERE r.from_bot IS NOT NULL) > 0
             ORDER BY c.last_activity_at DESC
            """,
            {"me": user_id, "chat": chat_id},
        )
        return [{"id": r[0], "conv_number": r[1], "started_at": r[2],
                 "last_activity_at": r[3], "is_owner": bool(r[4]), "messages": int(r[5])}
                for r in cur.fetchall()]


def conversation_messages(chat_id: int, conversation_id: int, limit: int) -> tuple:
    """(rows, how many were left out). One row per message of this
    conversation still in this chat, oldest first.

    Message ids climb within a chat, so id order is time order and does not
    depend on `sent_at`, which older rows do not have.

    The chat id is the whole of the access check. A relay row belongs to one
    chat, and a private chat's id is the person in it -- so asking for another
    person's conversation with this person's chat id returns nothing rather
    than returning theirs.
    """
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT message_id, from_bot, sent_at FROM anon_relay
             WHERE chat_id = %s AND conversation_id = %s AND from_bot IS NOT NULL
             ORDER BY message_id LIMIT %s
            """,
            (chat_id, conversation_id, max(1, limit) + 1),
        )
        rows = [{"message_id": r[0], "from_bot": bool(r[1]), "sent_at": r[2]}
                for r in cur.fetchall()]
        left_out = conn.execute(
            "SELECT count(*) FROM anon_relay WHERE chat_id = %s AND conversation_id = %s "
            "AND from_bot IS NULL AND peer_message_id IS NOT NULL",
            (chat_id, conversation_id),
        ).fetchone()[0]
    over = max(0, len(rows) - limit)
    return rows[:limit], int(left_out) + over


def first_relay_message(chat_id: int, conversation_id: int) -> int | None:
    """The earliest message of this conversation still on record in this
    chat, which is what "go to the start" scrolls to.

    Message ids climb within a chat, so the smallest is the first. It is the
    first *still on record*, which is not always the first there ever was:
    prune_old_data removes a long-silent conversation's rows, and /cancel can
    remove one. None means there is nothing left to point at, and the caller
    says so rather than pointing somewhere else."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT min(message_id) FROM anon_relay "
            "WHERE chat_id = %s AND conversation_id = %s",
            (chat_id, conversation_id),
        )
        row = cur.fetchone()
        return row[0] if row else None


def get_anon_stats(owner_user_id: int) -> dict:
    """Counts only conversations something was actually said in -- a link tap
    that never became a message is not a conversation anybody had."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT COUNT(DISTINCT follower_user_id), COUNT(*) FROM anon_conversations "
            "WHERE owner_user_id = %s "
            "AND (follower_first_msg_at IS NOT NULL OR last_owner_msg_id IS NOT NULL)",
            (owner_user_id,),
        )
        distinct_followers, conversations = cur.fetchone()
        return {"distinct_followers": distinct_followers or 0, "conversations": conversations or 0}


# ---------- housekeeping ----------
# Two tables here grow without limit if nobody prunes them: activity_events
# (one row per active user per flush window) and anon_relay (one row per
# relayed message, forever). anon_relay is what lets a swipe-reply on an old
# message still resolve, so it is pruned on conversation activity rather than
# on the row's own age -- a long-running conversation keeps all of its
# anchors, a conversation nobody has touched in months keeps none.
ACTIVITY_RETENTION_DAYS = int(os.environ.get("ACTIVITY_RETENTION_DAYS", "90"))
RELAY_RETENTION_DAYS = int(os.environ.get("RELAY_RETENTION_DAYS", "180"))


def prune_old_data() -> int:
    """Returns how many rows were removed. Safe to run at any time.

    It also archives the conversations it has just taken the last reply
    anchor from -- see the comment on that statement. Archiving is not a
    removal, so it is not in the count."""
    with pooled() as conn:
        cur = conn.execute(
            "DELETE FROM activity_events WHERE occurred_at < now() - make_interval(days => %s)",
            (ACTIVITY_RETENTION_DAYS,),
        )
        removed = cur.rowcount
        cur = conn.execute(
            """
            DELETE FROM anon_relay WHERE conversation_id IN (
                SELECT id FROM anon_conversations
                WHERE last_activity_at < to_char(
                    now() - make_interval(days => %s), 'YYYY-MM-DD"T"HH24:MI:SS'
                )
            )
            """,
            (RELAY_RETENTION_DAYS,),
        )
        removed += cur.rowcount
        # ...and the conversations those rows belonged to are archived, in
        # the same pass and by the same rule.
        #
        # This is not tidiness. Every route into a conversation goes through
        # a reply to a message that has a relay row, so a conversation with
        # none left cannot be written into by either side -- it is closed,
        # as a fact rather than as a decision. Leaving it counted as open
        # would make "4 open" a lifetime total wearing the word "open",
        # which is the number /conversations exists to stop being.
        #
        # Deliberately does not touch already-archived rows: archived_at is
        # when the owner filed it, and overwriting that with the night the
        # pruner happened to run loses the only thing it says.
        cur = conn.execute(
            """
            UPDATE anon_conversations SET archived_at = %s
             WHERE archived_at IS NULL
               AND last_activity_at < to_char(
                   now() - make_interval(days => %s), 'YYYY-MM-DD"T"HH24:MI:SS'
               )
            """,
            (datetime.now(timezone.utc).isoformat(), RELAY_RETENTION_DAYS),
        )
        archived = cur.rowcount
        conn.commit()
    if archived:
        logging.getLogger(__name__).info(
            "Archived %s conversation(s) with no reply anchors left", archived)
    return removed

# ---------- erasing one person, on request ----------
# What /deletemydata reaches -- see shared_features.py, which owns the
# command and the confirmation. Everything in this schema that is about one
# person goes, in a single transaction, with one deliberate exception.
#
# The Stars ledger keeps its rows. A donation is a payment, and a payment
# record has to outlive the payer asking to be forgotten: it is what a refund
# is issued against and what the totals are counted from. The username is
# cleared, since it is the one free-text identifier on the row; the numeric
# id stays, because without it a refund cannot be sent to anybody. The
# privacy notice says so rather than implying the erase is total.

def erase_user(user_id: int) -> int:
    """Returns how many rows were removed. Blocking; call through
    asyncio.to_thread.

    A conversation row is jointly held: it exists only to say that these two
    people are talking, so it cannot be erased for one side and kept for the
    other. Whichever side asks, the thread stops being routable and both
    sides get a fresh conversation number if they ever meet again. What was
    actually said is unaffected either way -- it was never stored here, it is
    in the two Telegram chats, and each person can delete their own copy.

    For an inbox owner this also invalidates their link. Every copy anyone
    has posted stops working, which is the point of asking rather than the
    cost of it, but it is not something to find out afterwards -- the
    confirmation says so before the button is tapped.
    """
    removed = 0
    with pooled() as conn:
        cur = conn.execute(
            "SELECT id FROM anon_conversations WHERE owner_user_id = %s OR follower_user_id = %s",
            (user_id, user_id),
        )
        conversations = [row[0] for row in cur.fetchall()]
        if conversations:
            cur = conn.execute(
                "DELETE FROM anon_relay WHERE conversation_id = ANY(%s)", (conversations,)
            )
            removed += cur.rowcount or 0
            cur = conn.execute("DELETE FROM anon_conversations WHERE id = ANY(%s)", (conversations,))
            removed += cur.rowcount or 0
        # Written out rather than looped, so that no part of a statement here
        # is assembled at runtime. There are three of them; a loop that built
        # the WHERE clause saved two lines and cost the guarantee that every
        # SQL string in this file is visible in this file.
        for statement, params in (
            ("DELETE FROM anon_follower_state WHERE follower_user_id = %s OR owner_user_id = %s",
             (user_id, user_id)),
            ("DELETE FROM anon_blocks WHERE owner_user_id = %s OR follower_user_id = %s",
             (user_id, user_id)),
            ("DELETE FROM anon_links WHERE owner_user_id = %s", (user_id,)),
        ):
            cur = conn.execute(statement, params)
            removed += cur.rowcount or 0
        for table in ("user_settings", "donation_prompts", "activity_events"):
            cur = conn.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
            removed += cur.rowcount or 0
        conn.execute(
            "UPDATE star_transactions SET username = NULL "
            "WHERE user_id = %s AND username IS NOT NULL",
            (user_id,),
        )
        conn.commit()
    return removed


# ---------- admin: full database export ----------

def dump_database_csv_zip() -> bytes:
    """Exports every table in this bot's own schema to one CSV per table,
    zipped together -- this bot's data only, never a sibling's. Deliberately not pg_dump-based -- that binary
    isn't guaranteed to exist wherever this bot ends up hosted, while this
    only needs the psycopg connection already used everywhere else here."""
    import csv
    import io
    import zipfile

    buf = io.BytesIO()
    with pooled() as conn, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        cur = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
            (DB_SCHEMA,),
        )
        tables = [row[0] for row in cur.fetchall()]
        for table in tables:
            cur = conn.execute(f'SELECT * FROM "{table}"')
            columns = [desc.name for desc in cur.description]
            rows = cur.fetchall()
            csv_buf = io.StringIO()
            writer = csv.writer(csv_buf)
            writer.writerow(columns)
            writer.writerows(rows)
            zf.writestr(f"{table}.csv", csv_buf.getvalue())
    return buf.getvalue()
