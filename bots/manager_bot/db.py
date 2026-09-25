"""Postgres layer for ManagerBot.

ManagerBot is the one process in the family that reads *across* schemas. It
owns `manager_bot.*` (just its own activity log, so the same /status
machinery as every other bot works here too), it reads and writes
`family.*` (heartbeats, events, the command queue -- created by
family_link.py, which every bot in the family carries), and it reads the
four public bots' schemas to answer "how many users has ConvertBot had this
week" without going anywhere near their processes.

Read-only across other bots' schemas, deliberately -- ManagerBot never
writes into a bot's own tables. When something needs changing inside a bot,
it goes through the family command queue so that bot does it itself, with
its own code and its own invariants.
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
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/botfamily"
)

# ManagerBot's own schema in the shared database -- same convention as every
# other bot (see family_link.py's layout diagram).
DB_SCHEMA = os.environ.get("DB_SCHEMA", "manager_bot")

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


FAMILY_SCHEMA = "family"


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
    with closing(psycopg.connect(dsn)) as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        conn.commit()


def init_db(dsn: str = DATABASE_URL) -> None:
    for _problem in check_database_url(dsn):
        logging.getLogger(__name__).warning("%s", _problem)

    """Only ManagerBot's own tables. The family.* tables are created by
    family_link.init_family_schema(), which runs in every bot including
    this one, so whichever process starts first sets them up."""
    # Deliberately on a plain connection rather than the pool: the offline
    # tools (db_merge.py, migrate_to_shared_db.py) call this against a
    # *different* database than the one this process serves, and the pool
    # is bound to DATABASE_URL. It runs once, so there is nothing to save.
    ensure_schema(dsn)
    with closing(connect(dsn)) as conn:
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


# ---------- this bot's own activity (mirrors every other bot's db.py) ----------

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
            "SELECT COUNT(DISTINCT user_id) FROM activity_events WHERE occurred_at >= %s", (since,)
        )
        return cur.fetchone()[0]


# ---------- family.heartbeats ----------


def active_user_ids_since(since) -> list[int]:
    """Everyone with activity since `since`. Used by the family bus for an
    aimed broadcast -- see BROADCAST_ACTIVE_DAYS in family_link.py."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT DISTINCT user_id FROM activity_events WHERE occurred_at >= %s",
            (since,),
        )
        return [row[0] for row in cur.fetchall()]

def all_heartbeats() -> list[dict]:
    with pooled_read() as conn:
        cur = conn.execute(
            f"""
            SELECT bot_id, display_name, host, version, pid, db_schema,
                   started_at, last_seen, error_count,
                   to_jsonb(h) ->> 'commands' AS commands,
                   EXTRACT(EPOCH FROM (now() - last_seen))::int AS seconds_ago
            FROM {FAMILY_SCHEMA}.heartbeats h ORDER BY bot_id
            """
        )
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def heartbeat_of(bot_id: str) -> dict | None:
    """One bot's row, or None if it has never been seen.

    Separate from all_heartbeats() because it is asked on the way into every
    /run: the version check in bot.py wants one bot, not five, and this runs
    in front of a command the owner is waiting on.
    """
    with pooled_read() as conn:
        cur = conn.execute(
            f"""
            SELECT bot_id, display_name, host, version, pid, db_schema,
                   started_at, last_seen, error_count,
                   to_jsonb(h) ->> 'commands' AS commands,
                   EXTRACT(EPOCH FROM (now() - last_seen))::int AS seconds_ago
            FROM {FAMILY_SCHEMA}.heartbeats h WHERE bot_id = %s
            """,
            (bot_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip([d.name for d in cur.description], row))


# ---------- family.bot_state (edge-triggered up/down alerting) ----------

def get_known_state() -> dict[str, bool]:
    with pooled_read() as conn:
        cur = conn.execute(f"SELECT bot_id, is_up FROM {FAMILY_SCHEMA}.bot_state")
        return {row[0]: row[1] for row in cur.fetchall()}


def set_known_state(bot_id: str, is_up: bool) -> None:
    with pooled() as conn:
        conn.execute(
            f"""
            INSERT INTO {FAMILY_SCHEMA}.bot_state (bot_id, is_up, changed_at)
            VALUES (%s, %s, now())
            ON CONFLICT (bot_id) DO UPDATE SET is_up = excluded.is_up, changed_at = now()
            """,
            (bot_id, is_up),
        )
        conn.commit()


# ---------- family.events ----------

def take_unnotified_events(limit: int = 20) -> list[dict]:
    """Claims and returns them in one statement, so a ManagerBot that gets
    restarted mid-DM doesn't re-send the whole backlog."""
    with pooled() as conn:
        cur = conn.execute(
            f"""
            UPDATE {FAMILY_SCHEMA}.events SET notified = TRUE
            WHERE id IN (
                SELECT id FROM {FAMILY_SCHEMA}.events WHERE notified = FALSE
                ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED
            )
            RETURNING id, bot_id, level, kind, message, details, occurred_at
            """,
            (limit,),
        )
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.commit()
        return rows


def recent_events(limit: int = 15, bot_id: str | None = None) -> list[dict]:
    sql = (
        f"SELECT bot_id, level, kind, message, occurred_at FROM {FAMILY_SCHEMA}.events "
        + ("WHERE bot_id = %s " if bot_id else "")
        + "ORDER BY id DESC LIMIT %s"
    )
    params = (bot_id, limit) if bot_id else (limit,)
    with pooled_read() as conn:
        cur = conn.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def log_event(bot_id: str, level: str, kind: str, message: str) -> None:
    """ManagerBot's own events go in already marked as notified -- it is the
    one doing the notifying, so forwarding them to itself would be a loop."""
    with pooled() as conn:
        conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.events (bot_id, level, kind, message, notified) "
            f"VALUES (%s, %s, %s, %s, TRUE)",
            (bot_id, level, kind, message[:4000]),
        )
        conn.commit()


# ---------- family.commands ----------

def queue_command(target_bot: str, command: str, args: str, requested_by: int,
                  reply_chat_id: int) -> int:
    """Queue one command for a bot to pick up.

    The target finds it on its next bus poll -- about a second if the bus is
    already busy, at most FAMILY_BUS_POLL_IDLE_SECONDS if it has been quiet
    (see family_link._bus_tick). The caller should call
    family_link.mark_bus_active() right after this so ManagerBot's own result
    pump goes to the fast cadence while the answer is on its way back.
    """
    with pooled() as conn:
        cur = conn.execute(
            f"""
            INSERT INTO {FAMILY_SCHEMA}.commands (target_bot, command, args, requested_by, reply_chat_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (target_bot, command, args, requested_by, reply_chat_id),
        )
        command_id = cur.fetchone()[0]
        conn.commit()
    # One choke point for every /ping, /run, /pause, ... so ManagerBot's result
    # pump goes to its fast cadence the instant a command is outstanding,
    # without each call site having to remember to say so. Imported here
    # rather than at module scope because family_link imports this module.
    try:
        import family_link
        family_link.mark_bus_active()
    except Exception:
        logging.getLogger(__name__).debug("Could not mark the family bus active", exc_info=True)
    return command_id


def take_finished_commands(limit: int = 5) -> list[dict]:
    with pooled() as conn:
        cur = conn.execute(
            f"""
            UPDATE {FAMILY_SCHEMA}.commands SET delivered = TRUE
            WHERE id IN (
                SELECT id FROM {FAMILY_SCHEMA}.commands
                WHERE delivered = FALSE AND status IN ('done', 'failed', 'timeout')
                ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED
            )
            RETURNING id, target_bot, command, args, reply_chat_id, status, ok, output,
                      file_name, file_bytes, created_at, claimed_at, finished_at,
                      clock_timestamp() AS taken_at
            """,
            (limit,),
        )
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.commit()
        return rows


def expire_stale_commands(after_seconds: int) -> list[dict]:
    """A command aimed at a bot that is down never gets claimed. Rather than
    leave it pending forever, mark it timed out so the owner gets told
    instead of silently waiting."""
    with pooled() as conn:
        cur = conn.execute(
            f"""
            UPDATE {FAMILY_SCHEMA}.commands
            SET status = 'timeout', ok = FALSE, finished_at = now(),
                output = 'No answer -- that bot did not pick the command up. It is probably down.'
            WHERE status IN ('pending', 'running')
              AND created_at < now() - make_interval(secs => %s)
            RETURNING id, target_bot, command
            """,
            (after_seconds,),
        )
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.commit()
        return rows


# ---------- family.settings (ManagerBot's own toggles) ----------

def get_setting(key: str, default: str | None = None) -> str | None:
    with pooled_read() as conn:
        cur = conn.execute(f"SELECT value FROM {FAMILY_SCHEMA}.settings WHERE key = %s", (key,))
        row = cur.fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str) -> None:
    with pooled() as conn:
        conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.settings (key, value) VALUES (%s, %s) "
            f"ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


# ---------- cross-schema reads (the whole point of one shared database) ----------


def _existing_tables(conn, schemas: list[str], table: str) -> set[str]:
    """Which of these schemas actually have this table yet -- one lookup for
    the whole family rather than one per bot."""
    cur = conn.execute(
        "SELECT table_schema FROM information_schema.tables "
        "WHERE table_schema = ANY(%s) AND table_name = %s",
        (schemas, table),
    )
    return {row[0] for row in cur.fetchall()}


def active_users_by_schema(schemas: list[str], since, include_known: bool = False) -> dict[str, tuple]:
    """{schema: (active since `since`, all-time known)} for every schema that
    has an activity_events table. A schema missing from the result has never
    been created -- worth showing differently from a real zero.

    One connection and one UNION ALL for the whole family. /status ran this
    query once per bot, each on its own connection; ManagerBot's own status
    screen was eight separate connections to the same database."""
    if not schemas:
        return {}
    with pooled_read() as conn:
        present = sorted(_existing_tables(conn, schemas, "activity_events"))
        if not present:
            return {}
        known_expr = "COUNT(DISTINCT user_id)" if include_known else "0"
        union = " UNION ALL ".join(
            f'''SELECT %s AS schema_name,
                       COUNT(DISTINCT user_id) FILTER (WHERE occurred_at >= %s) AS active,
                       {known_expr} AS known
                FROM "{schema}".activity_events'''
            for schema in present
        )
        params: list = []
        for schema in present:
            params += [schema, since]
        cur = conn.execute(union, params)
        return {row[0]: (row[1], row[2]) for row in cur.fetchall()}


def donations_by_schema(schemas: list[str]) -> dict[str, list[tuple[str, int, int]]]:
    """{schema: [(currency, paid transactions, total amount), ...]}. Amounts
    are in each currency's own unit -- Stars for XTR, minor units for fiat --
    exactly as star_transactions stores them. One trip for the whole family."""
    if not schemas:
        return {}
    with pooled_read() as conn:
        present = sorted(_existing_tables(conn, schemas, "star_transactions"))
        if not present:
            return {}
        union = " UNION ALL ".join(
            f'''SELECT %s AS schema_name, currency, COUNT(*), COALESCE(SUM(amount_stars), 0)
                FROM "{schema}".star_transactions WHERE status = 'paid'
                GROUP BY currency'''
            for schema in present
        )
        cur = conn.execute(union, list(present))
        out: dict[str, list[tuple[str, int, int]]] = {}
        for schema_name, currency, count, total in cur.fetchall():
            out.setdefault(schema_name, []).append((currency, count, total))
        for rows in out.values():
            rows.sort()
        return out


def run_readonly_query(sql: str, limit: int = 50):
    """Backs ManagerBot's /sql. The safety here is the connection being
    genuinely read-only at the transaction level -- Postgres itself rejects
    any write, so this does not depend on parsing the statement correctly.
    The keyword check in bot.py is only there to give a friendlier error.

    Both SETs are LOCAL, i.e. scoped to this transaction. The connection is
    pooled and gets handed to the next caller afterwards; a plain SET would
    leave a ten-second statement timeout stuck on it for the rest of the
    process's life."""
    with pooled() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '10s'")
        cur = conn.execute(sql)
        cols = [d.name for d in cur.description] if cur.description else []
        rows = cur.fetchmany(limit) if cur.description else []
        conn.rollback()
        return cols, rows


# ---------- housekeeping ----------
# activity_events is append-only and powers nothing older than the retention
# window below (/status counts the last hour and since-start, ManagerBot's
# /users the last N hours). Left alone it is the one table in this schema that
# grows without limit, which on a metered database is a bill that only ever
# goes up. family_link.py's housekeeping job calls this.
ACTIVITY_RETENTION_DAYS = int(os.environ.get("ACTIVITY_RETENTION_DAYS", "90"))


def prune_old_data() -> int:
    """Returns how many rows were removed. Safe to run at any time."""
    with pooled() as conn:
        cur = conn.execute(
            "DELETE FROM activity_events WHERE occurred_at < now() - make_interval(days => %s)",
            (ACTIVITY_RETENTION_DAYS,),
        )
        removed = cur.rowcount
        conn.commit()
    return removed

# ---------- exports ----------

def dump_database_csv_zip() -> bytes:
    """ManagerBot's own schema only -- same contract as every other bot's
    db.py, so family_link's `dbdump` command works here unchanged. For the
    whole family in one file, see dump_family_csv_zip below."""
    return _dump_schemas([DB_SCHEMA])


def dump_family_csv_zip(schemas: list[str]) -> bytes:
    """Every schema in the shared database, one folder per schema, one CSV
    per table. This is the "download the whole database" button: it needs
    nothing but the psycopg connection already in use here, so it works
    from anywhere without pg_dump being installed."""
    return _dump_schemas(schemas)


def _csv_safe(row: tuple) -> list:
    """family.commands carries a BYTEA column (a finished /dbdump waiting to
    be delivered). Writing raw bytes into a CSV would produce megabytes of
    unreadable escaping, so they are summarised instead -- the real payload
    was already sent to Telegram when the command finished."""
    return [f"<{len(v)} bytes>" if isinstance(v, (bytes, bytearray, memoryview)) else v for v in row]


def _dump_schemas(schemas: list[str]) -> bytes:
    import csv
    import io
    import zipfile

    buf = io.BytesIO()
    with pooled() as conn, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        stamp = datetime.now(timezone.utc).isoformat()
        manifest = [f"# botfamily database export, {stamp}", ""]
        for schema in schemas:
            cur = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
                (schema,),
            )
            tables = [row[0] for row in cur.fetchall()]
            if not tables:
                manifest.append(f"{schema}/ -- no tables")
                continue
            for table in tables:
                cur = conn.execute(f'SELECT * FROM "{schema}"."{table}"')
                columns = [d.name for d in cur.description]
                rows = cur.fetchall()
                out = io.StringIO()
                writer = csv.writer(out)
                writer.writerow(columns)
                writer.writerows(_csv_safe(row) for row in rows)
                zf.writestr(f"{schema}/{table}.csv", out.getvalue())
                manifest.append(f"{schema}/{table}.csv -- {len(rows)} row(s)")
        zf.writestr("MANIFEST.txt", "\n".join(manifest) + "\n")
    return buf.getvalue()


def status_snapshot(schemas: list[str], since) -> dict:
    """Everything ManagerBot's /status prints, on one connection: heartbeats,
    per-bot active users, the alerts toggle and the database's own size.

    Drawing that board used to mean eight connections -- one for the
    heartbeats, one per bot for its user count, one for the setting and one
    for the database size -- every time the owner typed four characters."""
    with pooled_read() as conn:
        cur = conn.execute(
            f"""
            SELECT bot_id, display_name, host, version, pid, db_schema,
                   started_at, last_seen, error_count, commands,
                   EXTRACT(EPOCH FROM (now() - last_seen))::int AS seconds_ago
            FROM {FAMILY_SCHEMA}.heartbeats ORDER BY bot_id
            """
        )
        cols = [d.name for d in cur.description]
        beats = [dict(zip(cols, row)) for row in cur.fetchall()]

        cur = conn.execute(f"SELECT value FROM {FAMILY_SCHEMA}.settings WHERE key = 'alerts'")
        row = cur.fetchone()
        alerts = row[0] if row else "on"

        cur = conn.execute(
            "SELECT current_database(), pg_size_pretty(pg_database_size(current_database())), "
            "split_part(version(), ' ', 2)"
        )
        name, size, version = cur.fetchone()

        present = sorted(_existing_tables(conn, schemas, "activity_events"))
        active: dict[str, int] = {}
        if present:
            union = " UNION ALL ".join(
                f'''SELECT %s, COUNT(DISTINCT user_id)
                    FROM "{schema}".activity_events WHERE occurred_at >= %s'''
                for schema in present
            )
            params: list = []
            for schema in present:
                params += [schema, since]
            cur = conn.execute(union, params)
            active = {r[0]: r[1] for r in cur.fetchall()}

    return {
        "beats": beats,
        "alerts": alerts,
        "active": active,
        "database": {"name": name, "size": size, "version": version},
    }
