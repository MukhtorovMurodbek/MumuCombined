"""Postgres layer for DownloaderBot -- these tables are this bot's
alone. The family shares one Postgres database now, but each bot gets its
own schema in it (DB_SCHEMA below), and no bot reads or writes another's
tables; the only shared tables are `family.*`, which family_link.py owns.

Owns:
- per-user setting: whether downloaded videos get a credit caption
- a Telegram Stars ledger + donation-reminder cooldown, for this bot's own
  /donate flow (see shared_features.py)

Postgres was chosen (over SQLite) so this survives an ephemeral cloud
container redeploy -- see DEPLOY.md.
"""
import logging
import os
import time
from contextlib import closing, contextmanager
from datetime import datetime, timezone

from urllib.parse import urlsplit

import psycopg
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/downloaderbot"
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
            CREATE TABLE IF NOT EXISTS settings (
                user_id BIGINT PRIMARY KEY,
                caption_enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        # Nullable, no default -- NULL means "hasn't picked a language yet",
        # which is what gates the first-run picker in bot.py's /start.
        conn.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS language TEXT")
        # Default 0: compressed is what Telegram does to everyone by default
        # and what almost everyone wants, since it is the form that plays
        # inline. Lossless is opt-in, per user, and remembered.
        conn.execute(
            "ALTER TABLE settings ADD COLUMN IF NOT EXISTS "
            "lossless_enabled INTEGER NOT NULL DEFAULT 0"
        )
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
        # One row per download this bot actually started for somebody.
        #
        # In the database rather than in memory, which is the opposite choice
        # to the per-minute update ceiling in shared_features.py, and for the
        # opposite reason: that one is defending the process against a burst,
        # so forgetting it on a redeploy costs nothing. This one is a share
        # of a day, and a limit that resets every time the owner ships is not
        # a limit -- it would hand the heaviest user a fresh allowance on
        # every deploy, which is several a day when anything is being worked
        # on.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS download_events (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                platform TEXT,
                occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_download_events_user_time "
            "ON download_events (user_id, occurred_at DESC)"
        )
        # Which download provider is currently working, and which is not.
        #
        # Kept in the database rather than in memory alone so a redeploy does
        # not go back to hammering a service that has been dead for a week --
        # a container that restarts every time the owner ships would otherwise
        # re-learn the same lesson from scratch, at a user's expense, several
        # times a day. See resolvers.py.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_health (
                provider TEXT PRIMARY KEY,
                ok_count BIGINT NOT NULL DEFAULT 0,
                fail_count BIGINT NOT NULL DEFAULT 0,
                consecutive_fails INTEGER NOT NULL DEFAULT 0,
                last_ok_at DOUBLE PRECISION,
                last_fail_at DOUBLE PRECISION,
                last_error TEXT
            )
            """
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
    settings has a row per person who has ever picked a setting and is never
    pruned, while activity_events reaches people who only ever used the bot
    without changing anything -- but is pruned at ACTIVITY_RETENTION_DAYS.
    Together they are "everyone we still know about", which is the honest
    scope of a broadcast.
    """
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT user_id FROM settings "
            "UNION "
            "SELECT DISTINCT user_id FROM activity_events"
        )
        return [int(r[0]) for r in cur.fetchall()]


def get_caption_enabled(user_id: int) -> bool:
    with pooled_read() as conn:
        cur = conn.execute("SELECT caption_enabled FROM settings WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else True  # default: caption ON


def set_caption_enabled(user_id: int, enabled: bool) -> None:
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO settings (user_id, caption_enabled) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET caption_enabled = excluded.caption_enabled
            """,
            (user_id, int(enabled)),
        )
        conn.commit()


def get_lossless_enabled(user_id: int) -> bool:
    """Whether to send downloads as files rather than as photos/videos.

    Defaults to False for everyone who has never said otherwise: a
    compressed video plays in the chat, and a file has to be downloaded
    first, so the quality is only worth having if you asked for it."""
    with pooled_read() as conn:
        cur = conn.execute("SELECT lossless_enabled FROM settings WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else False


def set_lossless_enabled(user_id: int, enabled: bool) -> None:
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO settings (user_id, lossless_enabled) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET lossless_enabled = excluded.lossless_enabled
            """,
            (user_id, int(enabled)),
        )
        conn.commit()


def get_user_language(user_id: int) -> str | None:
    """None means the user hasn't picked a language yet (no row, or a row
    with caption prefs but no language set)."""
    with pooled_read() as conn:
        cur = conn.execute("SELECT language FROM settings WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None


def set_user_language(user_id: int, language: str) -> None:
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO settings (user_id, language) VALUES (%s, %s)
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



# ---------- how much of the day one person may have ----------
# This is the one bot in the family whose work costs real money and real
# time: a fetch out to a site that would rather not be fetched from, an
# ffmpeg mux, and an upload back through Telegram. MAX_CONCURRENT_DOWNLOADS
# caps how many run at once, which protects the container -- but two slots
# shared by everybody is not the same thing as a fair share of them, and one
# person pasting a playlist of links holds both for as long as they keep
# pasting. Everyone else waits behind them, and the bot looks broken to
# people who did nothing wrong.
#
# So: a rolling hour and a rolling day, per person, counted in the database.
# The numbers are set where somebody using the bot the way it is meant to be
# used never meets them -- the ceiling is for the loop, not for the
# enthusiast -- and they are rolling windows rather than a reset at midnight,
# because a reset at midnight is an invitation to queue up against it.
#
# Donors get a larger share. Not a different bot and not a queue-jump: the
# same bot with the ceiling moved, which is the honest version of paying for
# something whose cost is a fetch and an encode. A single donation of any
# size counts, forever -- billing anybody monthly for this would cost more to
# run than it collects.

DOWNLOADS_PER_HOUR = int(os.environ.get("DBOT_DOWNLOADS_PER_HOUR", "12"))
DOWNLOADS_PER_DAY = int(os.environ.get("DBOT_DOWNLOADS_PER_DAY", "40"))
DONOR_MULTIPLIER = float(os.environ.get("DBOT_DONOR_MULTIPLIER", "4"))
DOWNLOAD_RETENTION_DAYS = int(os.environ.get("DBOT_DOWNLOAD_RETENTION_DAYS", "7"))


def download_allowance(user_id: int) -> dict:
    """What this person has left, and when the next one frees up.

    One query for all of it: how many downloads in the last hour, how many in
    the last day, when the oldest of each window falls out, and whether this
    person has ever donated. Called once per link, on a database that is a
    long way from the container, so it is one round trip rather than four.

    Returns a dict with:
      allowed    -- may they start one now
      scope      -- "hour" or "day", which ceiling stopped them
      wait_min   -- whole minutes until the next one frees up
      hour/day   -- how many they have used
      hour_max/day_max -- their ceilings, donor multiplier already applied
      donor      -- whether the larger ceiling is in force
    """
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT
              count(*) FILTER (WHERE occurred_at > now() - interval '1 hour'),
              count(*) FILTER (WHERE occurred_at > now() - interval '1 day'),
              min(occurred_at) FILTER (WHERE occurred_at > now() - interval '1 hour'),
              min(occurred_at) FILTER (WHERE occurred_at > now() - interval '1 day'),
              EXISTS (SELECT 1 FROM star_transactions t
                       WHERE t.user_id = %(uid)s AND t.status = 'paid')
            FROM download_events WHERE user_id = %(uid)s
            """,
            {"uid": user_id},
        )
        used_hour, used_day, oldest_hour, oldest_day, donor = cur.fetchone()

    factor = DONOR_MULTIPLIER if donor else 1
    hour_max = int(DOWNLOADS_PER_HOUR * factor) if DOWNLOADS_PER_HOUR > 0 else 0
    day_max = int(DOWNLOADS_PER_DAY * factor) if DOWNLOADS_PER_DAY > 0 else 0
    state = {
        "hour": used_hour or 0, "day": used_day or 0,
        "hour_max": hour_max, "day_max": day_max,
        "donor": bool(donor), "allowed": True, "scope": None, "wait_min": 0,
    }

    def _minutes_until(oldest, seconds: int) -> int:
        if oldest is None:
            return 1
        gone = (datetime.now(timezone.utc) - oldest).total_seconds()
        return max(1, int((seconds - gone) // 60) + 1)

    # The day is checked first: being told "about 40 minutes" when the real
    # answer is nine hours is worse than not being told at all.
    if day_max and state["day"] >= day_max:
        state.update(allowed=False, scope="day",
                     wait_min=_minutes_until(oldest_day, 86400))
    elif hour_max and state["hour"] >= hour_max:
        state.update(allowed=False, scope="hour",
                     wait_min=_minutes_until(oldest_hour, 3600))
    return state


def record_download(user_id: int, platform: str | None = None) -> None:
    """Counted when a download is STARTED, not when it succeeds. A fetch that
    fails still cost the fetch, and counting only successes would make a
    string of failures free -- which is the cheapest way to keep the bot
    busy."""
    with pooled() as conn:
        conn.execute(
            "INSERT INTO download_events (user_id, platform) VALUES (%s, %s)",
            (user_id, platform),
        )
        conn.commit()

# ---------- housekeeping ----------
# activity_events is append-only and powers nothing older than the retention
# window below (/status counts the last hour and since-start, ManagerBot's
# /users the last N hours). Left alone it is the one table in this schema that
# grows without limit, which on a metered database is a bill that only ever
# goes up. family_link.py's housekeeping job calls this.
ACTIVITY_RETENTION_DAYS = int(os.environ.get("ACTIVITY_RETENTION_DAYS", "90"))


# ---------- download provider health (resolvers.py) ----------

def load_provider_health() -> list[dict]:
    """Everything known at startup. Returns plain dicts so resolvers.py does
    not have to know what a psycopg row looks like."""
    with pooled_read() as conn:
        rows = conn.execute(
            "SELECT provider, ok_count, fail_count, consecutive_fails, "
            "last_ok_at, last_fail_at, last_error FROM provider_health"
        ).fetchall()
    cols = ("provider", "ok_count", "fail_count", "consecutive_fails",
            "last_ok_at", "last_fail_at", "last_error")
    return [dict(zip(cols, row)) for row in rows]


def save_provider_health(rows: list[tuple]) -> None:
    """Upsert the counters that changed since the last flush.

    One statement for the whole batch, on a timer, rather than a write per
    download -- the same bargain activity_events makes, and for the same
    reason: this is advice about which provider to try first, not user data,
    and it is not worth a round trip each time somebody pastes a link.
    """
    if not rows:
        return
    with pooled() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO provider_health (provider, ok_count, fail_count,
                        consecutive_fails, last_ok_at, last_fail_at, last_error)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (provider) DO UPDATE SET
                    ok_count = EXCLUDED.ok_count,
                    fail_count = EXCLUDED.fail_count,
                    consecutive_fails = EXCLUDED.consecutive_fails,
                    last_ok_at = EXCLUDED.last_ok_at,
                    last_fail_at = EXCLUDED.last_fail_at,
                    last_error = EXCLUDED.last_error
                """,
                rows,
            )
        conn.commit()


def prune_old_data() -> int:
    """Returns how many rows were removed. Safe to run at any time."""
    with pooled() as conn:
        cur = conn.execute(
            "DELETE FROM activity_events WHERE occurred_at < now() - make_interval(days => %s)",
            (ACTIVITY_RETENTION_DAYS,),
        )
        removed = cur.rowcount
        # The quota only ever looks back a day; anything older is history
        # nobody reads. Kept a week so the owner can still answer "was that
        # person really hammering it on Tuesday".
        cur = conn.execute(
            "DELETE FROM download_events WHERE occurred_at < now() - make_interval(days => %s)",
            (DOWNLOAD_RETENTION_DAYS,),
        )
        removed += cur.rowcount
        conn.commit()
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

    download_events goes with the rest. It is the daily allowance's memory,
    so erasing it hands this person a fresh allowance -- which is the right
    trade: a per-user counter that survives the user asking to be forgotten
    is a record of their behaviour, and the allowance exists to stop one
    person costing the bot a fortune in a day, not to punish anybody across
    weeks.
    """
    removed = 0
    with pooled() as conn:
        for table in ("settings", "donation_prompts", "activity_events", "download_events"):
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
