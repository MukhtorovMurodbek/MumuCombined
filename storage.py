"""Each bot's own tables, in its own schema -- and ManagerBot's view across all of them.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("storage.py is loaded section by section by main.py -- run main.py")


# ─── module: sticker_bot.db ──────────────────────────────────────────────────
"""Postgres layer for StickerBot -- these tables are this bot's alone."""
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
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stickerbot"
)

DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

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

POOL_MIN = int(os.environ.get("DB_POOL_MIN", "1"))
POOL_MAX = int(os.environ.get("DB_POOL_MAX", "3"))
POOL_MAX_IDLE = float(os.environ.get("DB_POOL_MAX_IDLE", "120"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "15"))

POOL_CHECK_AFTER_IDLE = float(os.environ.get("DB_POOL_CHECK_AFTER_IDLE", "45"))

_pool: "ConnectionPool | None" = None

_last_known_good: "dict[int, float]" = {}

def _check_if_idle(conn) -> None:
    """The pool's checkout check, but only for connections that have actually been sitting there."""
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
    """Created on first use, never at import time -- init_db() has to be able to create the schema before anything connects into it."""
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

                "keepalives": 1, "keepalives_idle": 30,
                "keepalives_interval": 10, "keepalives_count": 5,
            },
            check=_check_if_idle,
            name=f"{DB_SCHEMA}",
            open=True,
        )
    return _pool

def pooled():
    """A connection from the pool, as a context manager."""
    return _get_pool().connection()

@contextmanager
def pooled_read():
    """A pooled connection in autocommit, for statements that only read."""
    with _get_pool().connection() as conn:
        conn.set_autocommit(True)
        try:
            yield conn
        finally:

            try:
                conn.set_autocommit(False)
            except Exception:
                logging.getLogger(__name__).debug("Could not restore transaction mode", exc_info=True)

def close_pool() -> None:
    """Shutdown hook -- lets the process exit without waiting on the pool's own worker threads."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None

def connect(dsn: str = DATABASE_URL):
    """A brand-new, unpooled connection to an arbitrary database."""
    return psycopg.connect(dsn, options=f"-c search_path={DB_SCHEMA},public")

def ensure_schema(dsn: str = DATABASE_URL) -> None:
    """Deliberately connects *without* the search_path option -- the schema it is about to create may not exist yet, and libpq would not complain but every later CREATE TABLE would land in public instead."""
    with closing(psycopg.connect(dsn)) as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        conn.commit()

def init_db(dsn: str = DATABASE_URL) -> None:
    for _problem in check_database_url(dsn):
        logging.getLogger(__name__).warning("%s", _problem)

    ensure_schema(dsn)
    with closing(connect(dsn)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS packs (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner_username TEXT,
                owner_name TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pack_editors (
                pack_name TEXT NOT NULL,
                user_id BIGINT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (pack_name, user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pack_share_tokens (
                pack_name TEXT PRIMARY KEY,
                token TEXT NOT NULL UNIQUE
            )
            """
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

        conn.execute("ALTER TABLE donation_prompts ADD COLUMN IF NOT EXISTS times_shown INTEGER NOT NULL DEFAULT 0")

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

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id BIGINT PRIMARY KEY,
                language TEXT
            )
            """
        )
        conn.commit()

def record_activity_batch(user_ids) -> None:
    """One row per user per flush window -- see shared_features.py's track_activity, which buffers them."""
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
    """Everyone with activity since `since`."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT DISTINCT user_id FROM activity_events WHERE occurred_at >= %s",
            (since,),
        )
        return [row[0] for row in cur.fetchall()]

def list_all_users() -> list[int]:
    """Everyone this bot could send an unprompted message to."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT user_id FROM user_settings "
            "UNION "
            "SELECT DISTINCT user_id FROM activity_events"
        )
        return [int(r[0]) for r in cur.fetchall()]

def get_user_language(user_id: int) -> str | None:
    """None means the user hasn't picked a language yet (no row, or a row with no language set)."""
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

def add_pack(
    user_id: int,
    name: str,
    title: str,
    owner_username: str | None = None,
    owner_name: str | None = None,
) -> None:
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO packs (user_id, name, title, created_at, owner_username, owner_name)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, name, title, datetime.now(timezone.utc).isoformat(), owner_username, owner_name),
        )
        conn.commit()

def get_user_packs(user_id: int) -> list[tuple[str, str]]:
    """Returns list of (name, title) for a user's own packs, newest first."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT name, title FROM packs WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )
        return cur.fetchall()

def get_pack_owner(name: str) -> int | None:
    with pooled_read() as conn:
        cur = conn.execute("SELECT user_id FROM packs WHERE name = %s", (name,))
        row = cur.fetchone()
        return row[0] if row else None

def get_pack_creator_info(name: str) -> dict | None:
    """Everything /whomade needs about a pack this bot created."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT user_id, title, created_at, owner_username, owner_name FROM packs WHERE name = %s",
            (name,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "owner_id": row[0],
            "title": row[1],
            "created_at": row[2],
            "owner_username": row[3],
            "owner_name": row[4],
        }

def get_pack_title(name: str) -> str | None:
    with pooled_read() as conn:
        cur = conn.execute("SELECT title FROM packs WHERE name = %s", (name,))
        row = cur.fetchone()
        return row[0] if row else None

def set_pack_title(name: str, title: str) -> None:
    with pooled() as conn:
        conn.execute("UPDATE packs SET title = %s WHERE name = %s", (title, name))
        conn.commit()

def add_editor(pack_name: str, user_id: int) -> None:
    """Records that user_id has been granted add-only access to pack_name (they opened a valid co-edit link)."""
    with pooled() as conn:
        conn.execute(
            "INSERT INTO pack_editors (pack_name, user_id, added_at) VALUES (%s, %s, %s) "
            "ON CONFLICT (pack_name, user_id) DO NOTHING",
            (pack_name, user_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

def get_coedit_view(pack_name: str) -> tuple[str, str | None, int]:
    """(share token, pack title, number of co-editors) -- everything the co-edit screen renders, on one connection."""
    with pooled() as conn:
        cur = conn.execute("SELECT token FROM pack_share_tokens WHERE pack_name = %s", (pack_name,))
        row = cur.fetchone()
        if row:
            token = row[0]
        else:
            token = uuid.uuid4().hex
            conn.execute(
                "INSERT INTO pack_share_tokens (pack_name, token) VALUES (%s, %s)",
                (pack_name, token),
            )
        cur = conn.execute(
            "SELECT (SELECT title FROM packs WHERE name = %s), "
            "(SELECT COUNT(*) FROM pack_editors WHERE pack_name = %s)",
            (pack_name, pack_name),
        )
        title, editor_count = cur.fetchone()
        conn.commit()
        return token, title, editor_count

def reset_share_token(pack_name: str) -> str:
    """Generates a fresh token for the pack, invalidating the old link."""
    token = uuid.uuid4().hex
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO pack_share_tokens (pack_name, token) VALUES (%s, %s)
            ON CONFLICT (pack_name) DO UPDATE SET token = excluded.token
            """,
            (pack_name, token),
        )
        conn.commit()
    return token

def get_pack_by_token(token: str) -> str | None:
    with pooled_read() as conn:
        cur = conn.execute("SELECT pack_name FROM pack_share_tokens WHERE token = %s", (token,))
        row = cur.fetchone()
        return row[0] if row else None

def delete_pack_records(name: str) -> None:
    """Wipes all local traces of a pack (owner record, co-editors, share token)."""
    with pooled() as conn:
        conn.execute("DELETE FROM packs WHERE name = %s", (name,))
        conn.execute("DELETE FROM pack_editors WHERE pack_name = %s", (name,))
        conn.execute("DELETE FROM pack_share_tokens WHERE pack_name = %s", (name,))
        conn.commit()

def record_star_invoice(
    user_id: int,
    username: str | None,
    amount_stars: int,
    item: str,
    payload: str,
    status: str = "invoiced",
    currency: str = "XTR",
) -> None:
    """amount_stars is in the currency's smallest unit for fiat currencies (see shared_features.py's FIAT_CURRENCIES), or a plain Stars count for the default currency="XTR"."""
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

def bump_donation_action(user_id: int) -> tuple[int, str | None, int, bool]:
    """Increments this user's action counter and returns everything the nudge decision needs: (actions since the last nudge, when it was last shown, how many times it has ever been shown, has this person ever donated)."""
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
    """Zeroes the action counter, stamps 'last_shown_at' and counts the showing -- call right after actually showing the nudge, not on every check."""
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

def erase_user(user_id: int) -> int:
    """Returns how many rows were removed. Blocking; call through asyncio.to_thread."""
    removed = 0
    with pooled() as conn:
        cur = conn.execute("SELECT name FROM packs WHERE user_id = %s", (user_id,))
        owned = [row[0] for row in cur.fetchall()]
        if owned:
            for table in ("pack_share_tokens", "pack_editors"):
                cur = conn.execute(f"DELETE FROM {table} WHERE pack_name = ANY(%s)", (owned,))
                removed += cur.rowcount or 0
            cur = conn.execute("DELETE FROM packs WHERE user_id = %s", (user_id,))
            removed += cur.rowcount or 0

        cur = conn.execute("DELETE FROM pack_editors WHERE user_id = %s", (user_id,))
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

def dump_database_csv_zip() -> bytes:
    """Exports every table in this bot's own schema to one CSV per table, zipped together -- this bot's data only, never a sibling's."""
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

# ─── module: convert_bot.db ──────────────────────────────────────────────────
"""Postgres layer for ConvertBot -- these tables are this bot's alone."""
import logging
import os
import time
from contextlib import closing, contextmanager
from datetime import datetime, timezone

from urllib.parse import urlsplit

import psycopg
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/convertbot"
)

DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

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

POOL_MIN = int(os.environ.get("DB_POOL_MIN", "1"))
POOL_MAX = int(os.environ.get("DB_POOL_MAX", "3"))
POOL_MAX_IDLE = float(os.environ.get("DB_POOL_MAX_IDLE", "120"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "15"))

POOL_CHECK_AFTER_IDLE = float(os.environ.get("DB_POOL_CHECK_AFTER_IDLE", "45"))

_pool: "ConnectionPool | None" = None

_last_known_good: "dict[int, float]" = {}

def _check_if_idle(conn) -> None:
    """The pool's checkout check, but only for connections that have actually been sitting there."""
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
    """Created on first use, never at import time -- init_db() has to be able to create the schema before anything connects into it."""
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

                "keepalives": 1, "keepalives_idle": 30,
                "keepalives_interval": 10, "keepalives_count": 5,
            },
            check=_check_if_idle,
            name=f"{DB_SCHEMA}",
            open=True,
        )
    return _pool

def pooled():
    """A connection from the pool, as a context manager."""
    return _get_pool().connection()

@contextmanager
def pooled_read():
    """A pooled connection in autocommit, for statements that only read."""
    with _get_pool().connection() as conn:
        conn.set_autocommit(True)
        try:
            yield conn
        finally:

            try:
                conn.set_autocommit(False)
            except Exception:
                logging.getLogger(__name__).debug("Could not restore transaction mode", exc_info=True)

def close_pool() -> None:
    """Shutdown hook -- lets the process exit without waiting on the pool's own worker threads."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None

def connect(dsn: str = DATABASE_URL):
    """A brand-new, unpooled connection to an arbitrary database."""
    return psycopg.connect(dsn, options=f"-c search_path={DB_SCHEMA},public")

def ensure_schema(dsn: str = DATABASE_URL) -> None:
    """Deliberately connects *without* the search_path option -- the schema it is about to create may not exist yet, and libpq would not complain but every later CREATE TABLE would land in public instead."""
    with closing(psycopg.connect(dsn)) as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        conn.commit()

def init_db(dsn: str = DATABASE_URL) -> None:
    for _problem in check_database_url(dsn):
        logging.getLogger(__name__).warning("%s", _problem)

    ensure_schema(dsn)
    with closing(connect(dsn)) as conn:

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

        conn.execute("ALTER TABLE donation_prompts ADD COLUMN IF NOT EXISTS times_shown INTEGER NOT NULL DEFAULT 0")

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

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversions_in_flight (
                job_id TEXT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                price INTEGER NOT NULL,
                lang TEXT,
                pair TEXT,
                owner TEXT NOT NULL,
                touched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                recovered BOOLEAN NOT NULL DEFAULT false
            )
            """
        )
        conn.commit()

def hold_conversion(job_id: str, user_id: int, chat_id: int, price: int, lang: str | None,
                    pair: str, owner: str) -> None:
    with pooled() as conn:
        conn.execute(
            "INSERT INTO conversions_in_flight (job_id, user_id, chat_id, price, lang, pair, owner) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (job_id) DO NOTHING",
            (job_id, user_id, chat_id, price, lang, pair, owner),
        )
        conn.commit()

def touch_conversions(owner: str) -> int:
    with pooled() as conn:
        cur = conn.execute(
            "UPDATE conversions_in_flight SET touched_at = now() WHERE owner = %s AND NOT recovered",
            (owner,),
        )
        conn.commit()
    return cur.rowcount or 0

def release_conversion(job_id: str) -> str:
    """The conversion ended here."""
    with pooled() as conn:
        row = conn.execute(
            "DELETE FROM conversions_in_flight WHERE job_id = %s RETURNING recovered", (job_id,),
        ).fetchone()
        conn.commit()
    if row is None:
        return "absent"
    return "recovered" if row[0] else "held"

def claim_orphaned_conversions(owner: str, stale_seconds: int) -> list[dict]:
    """Rows of processes that stopped stamping them, claimed for refunding."""
    with pooled() as conn:
        rows = conn.execute(
            "UPDATE conversions_in_flight SET recovered = true, touched_at = now() "
            "WHERE NOT recovered AND owner <> %s "
            "AND touched_at < now() - make_interval(secs => %s) "
            "RETURNING job_id, user_id, chat_id, price, lang, pair",
            (owner, stale_seconds),
        ).fetchall()
        conn.commit()
    return [dict(zip(("job_id", "user_id", "chat_id", "price", "lang", "pair"), row)) for row in rows]

def record_activity_batch(user_ids) -> None:
    """One row per user per flush window -- see shared_features.py's track_activity, which buffers them."""
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
    """Everyone with activity since `since`."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT DISTINCT user_id FROM activity_events WHERE occurred_at >= %s",
            (since,),
        )
        return [row[0] for row in cur.fetchall()]

def list_all_users() -> list[int]:
    """Everyone this bot could send an unprompted message to."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT user_id FROM user_settings "
            "UNION "
            "SELECT DISTINCT user_id FROM activity_events"
        )
        return [int(r[0]) for r in cur.fetchall()]

def get_user_language(user_id: int) -> str | None:
    """None means the user hasn't picked a language yet (no row)."""
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

def record_star_invoice(
    user_id: int,
    username: str | None,
    amount_stars: int,
    item: str,
    payload: str,
    status: str = "invoiced",
    currency: str = "XTR",
) -> None:
    """amount_stars is in the currency's smallest unit for fiat currencies (see shared_features.py's FIAT_CURRENCIES), or a plain Stars count for the default currency="XTR"."""
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

def get_star_transaction(payload: str) -> dict | None:
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT user_id, username, amount_stars, item, status, payload, charge_id, created_at "
            "FROM star_transactions WHERE payload = %s",
            (payload,),
        )
        row = cur.fetchone()
        if not row:
            return None
        keys = ["user_id", "username", "amount_stars", "item", "status", "payload", "charge_id", "created_at"]
        return dict(zip(keys, row))

def get_user_star_summary(user_id: int, limit: int = 20) -> tuple[int, list[dict]]:
    """(total Stars actually paid, most recent transactions) for /mystars."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(amount_stars), 0) FROM star_transactions "
            "WHERE user_id = %s AND status = 'paid' AND currency = 'XTR'",
            (user_id,),
        )
        total = cur.fetchone()[0]
        cur = conn.execute(
            """
            SELECT amount_stars, item, status, currency, created_at FROM star_transactions
            WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
            """,
            (user_id, limit),
        )
        history = [
            {"amount_stars": r[0], "item": r[1], "status": r[2], "currency": r[3], "created_at": r[4]}
            for r in cur.fetchall()
        ]
        return total, history

def get_star_ledger(limit: int = 20) -> tuple[dict, list[dict]]:
    """Everything the owner-only /stars command prints: global totals plus the most recent transactions."""
    with pooled_read() as conn:
        cur = conn.execute(
            """
            SELECT
                COALESCE(SUM(amount_stars) FILTER (WHERE status = 'paid'), 0),
                COUNT(*) FILTER (WHERE status = 'paid'),
                COALESCE(SUM(amount_stars) FILTER (WHERE status = 'refunded'), 0),
                COUNT(*) FILTER (WHERE status = 'refunded'),
                COUNT(*) FILTER (WHERE status = 'free'),
                COUNT(DISTINCT user_id) FILTER (WHERE status = 'paid')
            FROM star_transactions WHERE currency = 'XTR'
            """
        )
        paid_total, paid_count, refunded_total, refunded_count, free_count, paying_users = cur.fetchone()
        summary = {
            "paid_total": paid_total,
            "paid_count": paid_count,
            "refunded_total": refunded_total,
            "refunded_count": refunded_count,
            "free_count": free_count,
            "paying_users": paying_users,
        }
        cur = conn.execute(
            """
            SELECT user_id, username, amount_stars, item, status, currency, created_at
            FROM star_transactions ORDER BY created_at DESC LIMIT %s
            """,
            (limit,),
        )
        recent = [
            {
                "user_id": r[0], "username": r[1], "amount_stars": r[2],
                "item": r[3], "status": r[4], "currency": r[5], "created_at": r[6],
            }
            for r in cur.fetchall()
        ]
        return summary, recent

def bump_donation_action(user_id: int) -> tuple[int, str | None, int, bool]:
    """Increments this user's action counter and returns everything the nudge decision needs: (actions since the last nudge, when it was last shown, how many times it has ever been shown, has this person ever donated)."""
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
    """Zeroes the action counter, stamps 'last_shown_at' and counts the showing -- call right after actually showing the nudge, not on every check."""
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

ACTIVITY_RETENTION_DAYS = int(os.environ.get("ACTIVITY_RETENTION_DAYS", "90"))

def prune_old_data() -> int:
    """Returns how many rows were removed. Safe to run at any time."""
    with pooled() as conn:
        cur = conn.execute(
            "DELETE FROM activity_events WHERE occurred_at < now() - make_interval(days => %s)",
            (ACTIVITY_RETENTION_DAYS,),
        )
        removed = cur.rowcount
        cur = conn.execute(
            "DELETE FROM conversions_in_flight WHERE (recovered AND touched_at < now() - interval '1 day') "
            "OR touched_at < now() - interval '2 days'"
        )
        removed += cur.rowcount or 0
        conn.commit()
    return removed

def erase_user(user_id: int) -> int:
    """Returns how many rows were removed. Blocking; call through asyncio.to_thread."""
    removed = 0
    with pooled() as conn:
        for table in ("user_settings", "donation_prompts", "activity_events", "conversions_in_flight"):
            cur = conn.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
            removed += cur.rowcount or 0
        conn.execute(
            "UPDATE star_transactions SET username = NULL "
            "WHERE user_id = %s AND username IS NOT NULL",
            (user_id,),
        )
        conn.commit()
    return removed

def dump_database_csv_zip() -> bytes:
    """Exports every table in this bot's own schema to one CSV per table, zipped together -- this bot's data only, never a sibling's."""
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

# ─── module: downloader_bot.db ───────────────────────────────────────────────
"""Postgres layer for DownloaderBot -- these tables are this bot's alone."""
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

DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

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

POOL_MIN = int(os.environ.get("DB_POOL_MIN", "1"))
POOL_MAX = int(os.environ.get("DB_POOL_MAX", "3"))
POOL_MAX_IDLE = float(os.environ.get("DB_POOL_MAX_IDLE", "120"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "15"))

POOL_CHECK_AFTER_IDLE = float(os.environ.get("DB_POOL_CHECK_AFTER_IDLE", "45"))

_pool: "ConnectionPool | None" = None

_last_known_good: "dict[int, float]" = {}

def _check_if_idle(conn) -> None:
    """The pool's checkout check, but only for connections that have actually been sitting there."""
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
    """Created on first use, never at import time -- init_db() has to be able to create the schema before anything connects into it."""
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

                "keepalives": 1, "keepalives_idle": 30,
                "keepalives_interval": 10, "keepalives_count": 5,
            },
            check=_check_if_idle,
            name=f"{DB_SCHEMA}",
            open=True,
        )
    return _pool

def pooled():
    """A connection from the pool, as a context manager."""
    return _get_pool().connection()

@contextmanager
def pooled_read():
    """A pooled connection in autocommit, for statements that only read."""
    with _get_pool().connection() as conn:
        conn.set_autocommit(True)
        try:
            yield conn
        finally:

            try:
                conn.set_autocommit(False)
            except Exception:
                logging.getLogger(__name__).debug("Could not restore transaction mode", exc_info=True)

def close_pool() -> None:
    """Shutdown hook -- lets the process exit without waiting on the pool's own worker threads."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None

def connect(dsn: str = DATABASE_URL):
    """A brand-new, unpooled connection to an arbitrary database."""
    return psycopg.connect(dsn, options=f"-c search_path={DB_SCHEMA},public")

def ensure_schema(dsn: str = DATABASE_URL) -> None:
    """Deliberately connects *without* the search_path option -- the schema it is about to create may not exist yet, and libpq would not complain but every later CREATE TABLE would land in public instead."""
    with closing(psycopg.connect(dsn)) as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        conn.commit()

def init_db(dsn: str = DATABASE_URL) -> None:
    for _problem in check_database_url(dsn):
        logging.getLogger(__name__).warning("%s", _problem)

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

        conn.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS language TEXT")

        conn.execute(
            "ALTER TABLE settings ADD COLUMN IF NOT EXISTS "
            "lossless_enabled INTEGER NOT NULL DEFAULT 0"
        )

        conn.execute(
            "ALTER TABLE settings ADD COLUMN IF NOT EXISTS "
            "large_files_enabled INTEGER NOT NULL DEFAULT 0"
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

        conn.execute("ALTER TABLE donation_prompts ADD COLUMN IF NOT EXISTS times_shown INTEGER NOT NULL DEFAULT 0")

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

def record_activity_batch(user_ids) -> None:
    """One row per user per flush window -- see shared_features.py's track_activity, which buffers them."""
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
    """Everyone with activity since `since`."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT DISTINCT user_id FROM activity_events WHERE occurred_at >= %s",
            (since,),
        )
        return [row[0] for row in cur.fetchall()]

def list_all_users() -> list[int]:
    """Everyone this bot could send an unprompted message to."""
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
        return bool(row[0]) if row else True

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
    """Whether to send downloads as files rather than as photos/videos."""
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

def get_large_files_enabled(user_id: int) -> bool:
    """Whether this person has switched on downloads over the free ceiling, which cost credit."""
    with pooled_read() as conn:
        cur = conn.execute("SELECT large_files_enabled FROM settings WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else False

def set_large_files_enabled(user_id: int, enabled: bool) -> None:
    with pooled() as conn:
        conn.execute(
            """
            INSERT INTO settings (user_id, large_files_enabled) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET large_files_enabled = excluded.large_files_enabled
            """,
            (user_id, int(enabled)),
        )
        conn.commit()

def get_user_language(user_id: int) -> str | None:
    """None means the user hasn't picked a language yet (no row, or a row with caption prefs but no language set)."""
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

def record_star_invoice(
    user_id: int,
    username: str | None,
    amount_stars: int,
    item: str,
    payload: str,
    status: str = "invoiced",
    currency: str = "XTR",
) -> None:
    """amount_stars is in the currency's smallest unit for fiat currencies (see shared_features.py's FIAT_CURRENCIES), or a plain Stars count for the default currency="XTR"."""
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

def bump_donation_action(user_id: int) -> tuple[int, str | None, int, bool]:
    """Increments this user's action counter and returns everything the nudge decision needs: (actions since the last nudge, when it was last shown, how many times it has ever been shown, has this person ever donated)."""
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
    """Zeroes the action counter, stamps 'last_shown_at' and counts the showing -- call right after actually showing the nudge, not on every check."""
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

DOWNLOADS_PER_HOUR = int(os.environ.get("DBOT_DOWNLOADS_PER_HOUR", "12"))
DOWNLOADS_PER_DAY = int(os.environ.get("DBOT_DOWNLOADS_PER_DAY", "40"))
DONOR_MULTIPLIER = float(os.environ.get("DBOT_DONOR_MULTIPLIER", "4"))
DOWNLOAD_RETENTION_DAYS = int(os.environ.get("DBOT_DOWNLOAD_RETENTION_DAYS", "7"))

def download_allowance(user_id: int) -> dict:
    """What this person has left, and when the next one frees up."""
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

    if day_max and state["day"] >= day_max:
        state.update(allowed=False, scope="day",
                     wait_min=_minutes_until(oldest_day, 86400))
    elif hour_max and state["hour"] >= hour_max:
        state.update(allowed=False, scope="hour",
                     wait_min=_minutes_until(oldest_hour, 3600))
    return state

def record_download(user_id: int, platform: str | None = None) -> None:
    """Counted when a download is STARTED, not when it succeeds."""
    with pooled() as conn:
        conn.execute(
            "INSERT INTO download_events (user_id, platform) VALUES (%s, %s)",
            (user_id, platform),
        )
        conn.commit()

ACTIVITY_RETENTION_DAYS = int(os.environ.get("ACTIVITY_RETENTION_DAYS", "90"))

def load_provider_health() -> list[dict]:
    """Everything known at startup."""
    with pooled_read() as conn:
        rows = conn.execute(
            "SELECT provider, ok_count, fail_count, consecutive_fails, "
            "last_ok_at, last_fail_at, last_error FROM provider_health"
        ).fetchall()
    cols = ("provider", "ok_count", "fail_count", "consecutive_fails",
            "last_ok_at", "last_fail_at", "last_error")
    return [dict(zip(cols, row)) for row in rows]

def save_provider_health(rows: list[tuple]) -> None:
    """Upsert the counters that changed since the last flush."""
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

        cur = conn.execute(
            "DELETE FROM download_events WHERE occurred_at < now() - make_interval(days => %s)",
            (DOWNLOAD_RETENTION_DAYS,),
        )
        removed += cur.rowcount
        conn.commit()
    return removed

def erase_user(user_id: int) -> int:
    """Returns how many rows were removed. Blocking; call through asyncio.to_thread."""
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

def dump_database_csv_zip() -> bytes:
    """Exports every table in this bot's own schema to one CSV per table, zipped together -- this bot's data only, never a sibling's."""
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

# ─── module: anon_bot.db ─────────────────────────────────────────────────────
"""Postgres layer for AnonBot -- these tables are this bot's alone."""
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

DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

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

POOL_MIN = int(os.environ.get("DB_POOL_MIN", "1"))
POOL_MAX = int(os.environ.get("DB_POOL_MAX", "3"))
POOL_MAX_IDLE = float(os.environ.get("DB_POOL_MAX_IDLE", "120"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "15"))

POOL_CHECK_AFTER_IDLE = float(os.environ.get("DB_POOL_CHECK_AFTER_IDLE", "45"))

_pool: "ConnectionPool | None" = None

_last_known_good: "dict[int, float]" = {}

def _check_if_idle(conn) -> None:
    """The pool's checkout check, but only for connections that have actually been sitting there."""
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
    """Created on first use, never at import time -- init_db() has to be able to create the schema before anything connects into it."""
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

                "keepalives": 1, "keepalives_idle": 30,
                "keepalives_interval": 10, "keepalives_count": 5,
            },
            check=_check_if_idle,
            name=f"{DB_SCHEMA}",
            open=True,
        )
    return _pool

def pooled():
    """A connection from the pool, as a context manager."""
    return _get_pool().connection()

@contextmanager
def pooled_read():
    """A pooled connection in autocommit, for statements that only read."""
    with _get_pool().connection() as conn:
        conn.set_autocommit(True)
        try:
            yield conn
        finally:

            try:
                conn.set_autocommit(False)
            except Exception:
                logging.getLogger(__name__).debug("Could not restore transaction mode", exc_info=True)

def close_pool() -> None:
    """Shutdown hook -- lets the process exit without waiting on the pool's own worker threads."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None

def connect(dsn: str = DATABASE_URL):
    """A brand-new, unpooled connection to an arbitrary database."""
    return psycopg.connect(dsn, options=f"-c search_path={DB_SCHEMA},public")

def ensure_schema(dsn: str = DATABASE_URL) -> None:
    """Deliberately connects *without* the search_path option -- the schema it is about to create may not exist yet, and libpq would not complain but every later CREATE TABLE would land in public instead."""
    with closing(psycopg.connect(dsn)) as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        conn.commit()

def init_db(dsn: str = DATABASE_URL) -> None:
    for _problem in check_database_url(dsn):
        logging.getLogger(__name__).warning("%s", _problem)

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

        conn.execute("ALTER TABLE donation_prompts ADD COLUMN IF NOT EXISTS times_shown INTEGER NOT NULL DEFAULT 0")

        conn.execute("ALTER TABLE donation_prompts ADD COLUMN IF NOT EXISTS pinned_message_id BIGINT")

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

        conn.execute("ALTER TABLE anon_conversations ADD COLUMN IF NOT EXISTS follower_first_msg_at TEXT")

        conn.execute("ALTER TABLE anon_conversations DROP COLUMN IF EXISTS owner_replied_at")

        conn.execute("ALTER TABLE anon_conversations ADD COLUMN IF NOT EXISTS archived_at TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_anon_conversations_pair "
            "ON anon_conversations (owner_user_id, follower_user_id)"
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_anon_conversations_owner_activity "
            "ON anon_conversations (owner_user_id, last_activity_at DESC)"
        )

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

        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS is_prompt BOOLEAN NOT NULL DEFAULT FALSE")

        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS peer_message_id BIGINT")

        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ")
        conn.execute("ALTER TABLE anon_relay ADD COLUMN IF NOT EXISTS from_bot BOOLEAN")

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

def record_activity_batch(user_ids) -> None:
    """One row per user per flush window -- see shared_features.py's track_activity, which buffers them."""
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
    """Everyone with activity since `since`."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT DISTINCT user_id FROM activity_events WHERE occurred_at >= %s",
            (since,),
        )
        return [row[0] for row in cur.fetchall()]

def list_all_users() -> list[int]:
    """Everyone this bot could send an unprompted message to."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT user_id FROM user_settings "
            "UNION "
            "SELECT DISTINCT user_id FROM activity_events"
        )
        return [int(r[0]) for r in cur.fetchall()]

def get_user_language(user_id: int) -> str | None:
    """None means the user hasn't picked a language yet (no row, or a row with no language set)."""
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

def record_star_invoice(
    user_id: int,
    username: str | None,
    amount_stars: int,
    item: str,
    payload: str,
    status: str = "invoiced",
    currency: str = "XTR",
) -> None:
    """amount_stars is in the currency's smallest unit for fiat currencies (see shared_features.py's FIAT_CURRENCIES), or a plain Stars count for the default currency="XTR"."""
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

def bump_donation_action(user_id: int) -> tuple[int, str | None, int, bool]:
    """Increments this user's action counter and returns everything the nudge decision needs: (actions since the last nudge, when it was last shown, how many times it has ever been shown, has this person ever donated)."""
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
    """Zeroes the action counter, stamps 'last_shown_at' and counts the showing -- call right after actually showing the nudge, not on every check."""
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

def get_or_create_anon_link(owner_user_id: int) -> tuple[str, bool]:
    """(token, is_paused) for this owner, creating the row on first use."""
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
    """Fresh token -- invalidates the old link for NEW conversations."""
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
    """Everything the "someone tapped a link" path needs to decide what to do: (owner id or None, is the inbox paused, has this follower been blocked)."""
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
    """(is this follower blocked, does the inbox still exist, the owner's language)."""
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
    """Always creates a brand-new conversation row -- this is what makes tapping the link again 'the start of a new conversation' -- and points the follower's active-routing state at it, so their very next un-replied message lands here instead of wherever they left off before."""
    with pooled() as conn:

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
    """Where a follower's next un-prompted message should be routed -- 'active' meaning 'the conversation their most recent /start link tap pointed at', see start_new_anon_conversation()."""
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
    """Remembers 'these messages, in this chat, belong to this conversation' so a later reply can be traced back to the right thread even with many conversations interleaved in the same chat."""
    ids = list(message_ids)
    if not ids:
        return
    with pooled() as conn:
        conn.execute(

            "INSERT INTO anon_relay (chat_id, message_id, conversation_id, sent_at) "
            "SELECT %s, unnest(%s::bigint[]), %s, now() "
            "ON CONFLICT (chat_id, message_id) DO UPDATE SET "
            "conversation_id = excluded.conversation_id, sent_at = excluded.sent_at, "
            "from_bot = NULL",
            (chat_id, ids, conversation_id),
        )
        conn.commit()

def relay_rows_between(chat_id: int, since, until) -> list[dict]:
    """One chat's relay rows written between two times: which conversation, when, and whether the bot wrote the bubble."""
    with pooled_read() as conn:
        rows = conn.execute(
            "SELECT conversation_id, sent_at, from_bot FROM anon_relay "
            "WHERE chat_id = %s AND sent_at BETWEEN %s AND %s",
            (chat_id, since, until),
        ).fetchall()
    return [{"conversation_id": row[0], "sent_at": row[1], "from_bot": row[2]} for row in rows]

def forget_anon_relay(chat_id: int, message_id: int) -> None:
    """Drop one relay row, so nothing is left pointing at a message that no longer exists."""
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
    """Everything one relayed message leaves behind, in one statement."""
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
    """Records that the guest has now sent their opening message, which is what spends this conversation's one exemption from the reply rule."""
    with pooled() as conn:
        conn.execute(
            "UPDATE anon_conversations SET follower_first_msg_at = %s "
            "WHERE id = %s AND follower_first_msg_at IS NULL",
            (datetime.now(timezone.utc).isoformat(), conversation_id),
        )
        conn.commit()

def count_owner_conversations(owner_user_id: int) -> int:
    """How many conversations this user is the inbox owner of, counting only the ones something was actually said in."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT count(*) FROM anon_conversations WHERE owner_user_id = %s "
            "AND (follower_first_msg_at IS NOT NULL OR last_owner_msg_id IS NOT NULL)",
            (owner_user_id,),
        )
        return cur.fetchone()[0]

def get_routing_context(user_id: int, chat_id: int) -> dict:
    """Everything handle_message needs to route one un-replied message, in a single round trip."""
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

        newest_is_active = newest is None or newest == conversation_id
        return {"active": active, "owned": row[6] or 0,
                "newest_is_active": newest_is_active,
                "active_anchor": row[8]}

def get_relay_row(chat_id: int, message_id: int) -> "dict | None":
    """This message's relay row: which conversation it belongs to, and which message in the other chat it is the same message as."""
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
    """Which conversation this message in this chat belongs to, if any."""
    row = get_relay_row(chat_id, message_id)
    return row["conversation_id"] if row else None

def clear_follower_state(follower_user_id: int) -> bool:
    """Forgets where this follower's next un-replied message was going to be routed, which is what /cancel does to an open ask session."""
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
    """Blocked guests, each as (a conversation id to address them by, the conversation numbers they used)."""
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

CONVERSATIONS_PER_PAGE = 6

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
    """One page of the owner's threads, whichever tab they are looking at, newest activity first -- which is the order an inbox is read in."""
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
    """File a conversation away, or bring it back."""
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

def list_exportable_conversations(user_id: int, chat_id: int) -> list[dict]:
    """Every conversation this person is in, from either side, with how many of its messages are still on record in their own chat."""
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
    """(rows, how many were left out). One row per message of this conversation still in this chat, oldest first."""
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
    """The earliest message of this conversation still on record in this chat, which is what "go to the start" scrolls to."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT min(message_id) FROM anon_relay "
            "WHERE chat_id = %s AND conversation_id = %s",
            (chat_id, conversation_id),
        )
        row = cur.fetchone()
        return row[0] if row else None

def get_anon_stats(owner_user_id: int) -> dict:
    """Counts only conversations something was actually said in -- a link tap that never became a message is not a conversation anybody had."""
    with pooled_read() as conn:
        cur = conn.execute(
            "SELECT COUNT(DISTINCT follower_user_id), COUNT(*) FROM anon_conversations "
            "WHERE owner_user_id = %s "
            "AND (follower_first_msg_at IS NOT NULL OR last_owner_msg_id IS NOT NULL)",
            (owner_user_id,),
        )
        distinct_followers, conversations = cur.fetchone()
        return {"distinct_followers": distinct_followers or 0, "conversations": conversations or 0}

ACTIVITY_RETENTION_DAYS = int(os.environ.get("ACTIVITY_RETENTION_DAYS", "90"))
RELAY_RETENTION_DAYS = int(os.environ.get("RELAY_RETENTION_DAYS", "180"))

def prune_old_data() -> int:
    """Returns how many rows were removed. Safe to run at any time."""
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

def erase_user(user_id: int) -> int:
    """Returns how many rows were removed. Blocking; call through asyncio.to_thread."""
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

def dump_database_csv_zip() -> bytes:
    """Exports every table in this bot's own schema to one CSV per table, zipped together -- this bot's data only, never a sibling's."""
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

# ─── module: manager_bot.db ──────────────────────────────────────────────────
"""Postgres layer for ManagerBot."""
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

DB_SCHEMA = os.environ.get("DB_SCHEMA", "manager_bot")

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

POOL_MIN = int(os.environ.get("DB_POOL_MIN", "1"))
POOL_MAX = int(os.environ.get("DB_POOL_MAX", "3"))
POOL_MAX_IDLE = float(os.environ.get("DB_POOL_MAX_IDLE", "120"))
POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "15"))

POOL_CHECK_AFTER_IDLE = float(os.environ.get("DB_POOL_CHECK_AFTER_IDLE", "45"))

_pool: "ConnectionPool | None" = None

_last_known_good: "dict[int, float]" = {}

def _check_if_idle(conn) -> None:
    """The pool's checkout check, but only for connections that have actually been sitting there."""
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
    """Created on first use, never at import time -- init_db() has to be able to create the schema before anything connects into it."""
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

                "keepalives": 1, "keepalives_idle": 30,
                "keepalives_interval": 10, "keepalives_count": 5,
            },
            check=_check_if_idle,
            name=f"{DB_SCHEMA}",
            open=True,
        )
    return _pool

def pooled():
    """A connection from the pool, as a context manager."""
    return _get_pool().connection()

@contextmanager
def pooled_read():
    """A pooled connection in autocommit, for statements that only read."""
    with _get_pool().connection() as conn:
        conn.set_autocommit(True)
        try:
            yield conn
        finally:

            try:
                conn.set_autocommit(False)
            except Exception:
                logging.getLogger(__name__).debug("Could not restore transaction mode", exc_info=True)

def close_pool() -> None:
    """Shutdown hook -- lets the process exit without waiting on the pool's own worker threads."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None

def connect(dsn: str = DATABASE_URL):
    """A brand-new, unpooled connection to an arbitrary database."""
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

def record_activity_batch(user_ids) -> None:
    """One row per user per flush window -- see shared_features.py's track_activity, which buffers them."""
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

def active_user_ids_since(since) -> list[int]:
    """Everyone with activity since `since`."""
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
    """One bot's row, or None if it has never been seen."""
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

def take_unnotified_events(limit: int = 20) -> list[dict]:
    """Claims and returns them in one statement, so a ManagerBot that gets restarted mid-DM doesn't re-send the whole backlog."""
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
    """ManagerBot's own events go in already marked as notified -- it is the one doing the notifying, so forwarding them to itself would be a loop."""
    with pooled() as conn:
        conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.events (bot_id, level, kind, message, notified) "
            f"VALUES (%s, %s, %s, %s, TRUE)",
            (bot_id, level, kind, message[:4000]),
        )
        conn.commit()

def queue_command(target_bot: str, command: str, args: str, requested_by: int,
                  reply_chat_id: int) -> int:
    """Queue one command for a bot to pick up."""
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
    """A command aimed at a bot that is down never gets claimed."""
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

def _existing_tables(conn, schemas: list[str], table: str) -> set[str]:
    """Which of these schemas actually have this table yet -- one lookup for the whole family rather than one per bot."""
    cur = conn.execute(
        "SELECT table_schema FROM information_schema.tables "
        "WHERE table_schema = ANY(%s) AND table_name = %s",
        (schemas, table),
    )
    return {row[0] for row in cur.fetchall()}

def active_users_by_schema(schemas: list[str], since, include_known: bool = False) -> dict[str, tuple]:
    """{schema: (active since `since`, all-time known)} for every schema that has an activity_events table."""
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
    """{schema: [(currency, paid transactions, total amount), ...]}."""
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
    """Backs ManagerBot's /sql."""
    with pooled() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '10s'")
        cur = conn.execute(sql)
        cols = [d.name for d in cur.description] if cur.description else []
        rows = cur.fetchmany(limit) if cur.description else []
        conn.rollback()
        return cols, rows

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

def dump_database_csv_zip() -> bytes:
    """ManagerBot's own schema only -- same contract as every other bot's db.py, so family_link's `dbdump` command works here unchanged."""
    return _dump_schemas([DB_SCHEMA])

def dump_family_csv_zip(schemas: list[str]) -> bytes:
    """Every schema in the shared database, one folder per schema, one CSV per table."""
    return _dump_schemas(schemas)

def _csv_safe(row: tuple) -> list:
    """family.commands carries a BYTEA column (a finished /dbdump waiting to be delivered)."""
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
    """Everything ManagerBot's /status prints, on one connection: heartbeats, per-bot active users, the alerts toggle and the database's own size."""
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

# ─── module: manager_bot.family_db ───────────────────────────────────────────
#!/usr/bin/env python3
"""Download the whole family database, and upload it back."""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import psycopg

SYSTEM_SCHEMAS = (
    "information_schema",
    "auth", "storage", "realtime", "_realtime", "vault",
    "pgsodium", "pgsodium_masks", "extensions",
    "graphql", "graphql_public", "pgbouncer",
    "cron", "net", "_analytics", "_supabase",
)

COPY_OPTS = "FORMAT CSV, HEADER, NULL '\\N'"

def load_dotenv_if_present() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def resolve_dsn(alias_or_url: str) -> str:
    if alias_or_url.startswith(("postgres://", "postgresql://")):
        return alias_or_url
    alias = alias_or_url.lower()
    if alias == "local":
        dsn = os.environ.get("LOCAL_DATABASE_URL") or os.environ.get("DATABASE_URL")
    else:
        dsn = os.environ.get(f"{alias.upper()}_DATABASE_URL")
    if not dsn:
        sys.exit(
            f"Don't know a database called '{alias_or_url}'. Pass a full postgresql:// URL, "
            f"or set {alias.upper()}_DATABASE_URL in your environment or in manager_bot/.env."
        )
    return dsn

def list_tables(conn, schemas: list[str] | None = None) -> list[tuple[str, str]]:
    sql = (
        "SELECT table_schema, table_name FROM information_schema.tables "

        "WHERE table_type = 'BASE TABLE' AND table_schema NOT LIKE 'pg\\_%%' "
        "AND table_schema NOT LIKE 'supabase\\_%%' "
        "AND table_schema <> ALL(%s)"
    )
    params: list = [list(SYSTEM_SCHEMAS)]
    if schemas:
        sql += " AND table_schema = ANY(%s)"
        params.append(schemas)
    sql += " ORDER BY table_schema, table_name"
    cur = conn.execute(sql, params)
    return [(row[0], row[1]) for row in cur.fetchall()]

def columns_of(conn, schema: str, table: str) -> list[str]:
    cur = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s "

        "AND is_generated = 'NEVER' "
        "ORDER BY ordinal_position",
        (schema, table),
    )
    return [row[0] for row in cur.fetchall()]

def quoted(cols: list[str]) -> str:
    return ", ".join(f'"{c}"' for c in cols)

def backup(dsn: str, out_path: Path, schemas: list[str] | None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": "csv-copy-v1",
        "tables": [],
    }

    with closing(psycopg.connect(dsn)) as conn, zipfile.ZipFile(
        out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        tables = list_tables(conn, schemas)
        if not tables:
            sys.exit("That database has no family tables in it at all -- wrong DATABASE_URL?")
        for schema, table in tables:
            cols = columns_of(conn, schema, table)
            buf = io.BytesIO()
            with conn.cursor().copy(
                f'COPY "{schema}"."{table}" ({quoted(cols)}) TO STDOUT ({COPY_OPTS})'
            ) as copy:
                for block in copy:
                    buf.write(bytes(block))
            payload = buf.getvalue()
            zf.writestr(f"{schema}/{table}.csv", payload)
            rows = max(payload.count(b"\n") - 1, 0)
            manifest["tables"].append(
                {"schema": schema, "table": table, "columns": cols, "approx_rows": rows}
            )
            print(f"  {schema}.{table}: ~{rows} row(s)")
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))

    size = out_path.stat().st_size
    print(f"\nWrote {out_path} ({size/1024:.0f} KB, {len(manifest['tables'])} table(s)).")

def restore(dsn: str, archive: Path, mode: str, schemas: list[str] | None, dry_run: bool) -> None:
    with zipfile.ZipFile(archive) as zf:
        manifest = json.loads(zf.read("MANIFEST.json"))
        entries = [
            entry for entry in manifest["tables"]
            if not schemas or entry["schema"] in schemas
        ]
        if not entries:
            sys.exit("Nothing in that archive matches the schemas you asked for.")

        with closing(psycopg.connect(dsn)) as conn:
            present = {(s, t) for s, t in list_tables(conn)}
            missing = [e for e in entries if (e["schema"], e["table"]) not in present]
            if missing:
                names = ", ".join(f"{e['schema']}.{e['table']}" for e in missing[:8])
                print(
                    f"! {len(missing)} table(s) don't exist in the target and will be skipped: {names}\n"
                    "  Start each bot once against this database (they create their own tables),\n"
                    "  or run migrate_to_shared_db.py, then run this again.",
                    file=sys.stderr,
                )

            total = 0
            restored: list[dict] = []
            for entry in entries:
                schema, table, cols = entry["schema"], entry["table"], entry["columns"]
                if (schema, table) not in present:
                    continue
                data = zf.read(f"{schema}/{table}.csv")
                target_cols = columns_of(conn, schema, table)
                usable = [c for c in cols if c in target_cols]
                if not usable:
                    print(f"  {schema}.{table}: no matching columns, skipped")
                    continue
                if len(usable) != len(cols):
                    dropped = set(cols) - set(usable)
                    print(f"  {schema}.{table}: ignoring column(s) the target doesn't have: {sorted(dropped)}")

                before = _row_count(conn, schema, table)
                if mode == "replace":
                    conn.execute(f'TRUNCATE "{schema}"."{table}" RESTART IDENTITY CASCADE')
                    _copy_into(conn, f'"{schema}"."{table}"', cols, usable, data)
                else:
                    _merge_into(conn, schema, table, cols, usable, data)
                after = _row_count(conn, schema, table)

                restored.append({**entry, "columns": usable})
                total += max(after - before, 0)
                print(f"  {schema}.{table}: {before} -> {after} row(s)")

            _resync_sequences(conn, restored)

            if dry_run:
                conn.rollback()
                print(f"\nDRY RUN -- rolled back. It would have added about {total} row(s).")
            else:
                conn.commit()
                print(f"\nDone. About {total} row(s) added.")

def _row_count(conn, schema: str, table: str) -> int:
    return conn.execute(f'SELECT count(*) FROM "{schema}"."{table}"').fetchone()[0]

def _copy_into(conn, target: str, all_cols: list[str], usable: list[str], data: bytes) -> None:
    """COPY straight in."""
    if usable == all_cols:
        with conn.cursor().copy(f"COPY {target} ({quoted(all_cols)}) FROM STDIN ({COPY_OPTS})") as copy:
            copy.write(data)
        return
    conn.execute(f"CREATE TEMP TABLE _stage (LIKE {target} INCLUDING DEFAULTS) ON COMMIT DROP")
    with conn.cursor().copy(f"COPY _stage ({quoted(usable)}) FROM STDIN ({COPY_OPTS})") as copy:
        copy.write(_project_csv(data, all_cols, usable))
    conn.execute(f"INSERT INTO {target} ({quoted(usable)}) SELECT {quoted(usable)} FROM _stage")
    conn.execute("DROP TABLE _stage")

def _merge_into(conn, schema: str, table: str, all_cols: list[str], usable: list[str], data: bytes) -> None:
    """Additive: load into a staging copy of the table, then insert only the rows the target does not already have."""
    target = f'"{schema}"."{table}"'
    conn.execute(f"CREATE TEMP TABLE _stage (LIKE {target} INCLUDING DEFAULTS) ON COMMIT DROP")
    payload = data if usable == all_cols else _project_csv(data, all_cols, usable)
    with conn.cursor().copy(f"COPY _stage ({quoted(usable)}) FROM STDIN ({COPY_OPTS})") as copy:
        copy.write(payload)
    conn.execute(
        f"INSERT INTO {target} ({quoted(usable)}) "
        f"SELECT {quoted(usable)} FROM _stage ON CONFLICT DO NOTHING"
    )
    conn.execute("DROP TABLE _stage")

def _project_csv(data: bytes, all_cols: list[str], keep: list[str]) -> bytes:
    """Drops columns the target no longer has."""
    import csv

    text = data.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return b""
    idx = [header.index(c) for c in keep]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(keep)
    for row in reader:
        writer.writerow([row[i] for i in idx])
    return out.getvalue().encode("utf-8")

def _resync_sequences(conn, entries: list[dict]) -> None:
    """Every bot's tables use BIGSERIAL ids."""
    for entry in entries:
        schema, table = entry["schema"], entry["table"]
        for col in entry["columns"]:
            row = conn.execute(
                "SELECT pg_get_serial_sequence(%s, %s)", (f'"{schema}"."{table}"', col)
            ).fetchone()
            if not row or not row[0]:
                continue
            conn.execute(
                f'SELECT setval(%s, COALESCE((SELECT MAX("{col}") FROM "{schema}"."{table}"), 1), true)',
                (row[0],),
            )

def main() -> None:
    load_dotenv_if_present()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)

    common_schemas = dict(nargs="*", default=None, metavar="SCHEMA",
                          help="limit to these schemas (default: all of them)")

    p = sub.add_parser("backup", help="download a database into a zip")
    p.add_argument("--from", dest="src", default="cloud")
    p.add_argument("--out", default=None, help="default: backups/family_<timestamp>.zip")
    p.add_argument("--schemas", **common_schemas)

    p = sub.add_parser("restore", help="upload a zip back into a database")
    p.add_argument("--into", dest="dst", default="cloud")
    p.add_argument("--file", required=True)
    p.add_argument("--mode", choices=("merge", "replace"), default="merge")
    p.add_argument("--schemas", **common_schemas)
    p.add_argument("--dry-run", action="store_true", help="do it all, then roll back")
    p.add_argument("--yes", action="store_true", help="skip the confirmation for --mode replace")

    p = sub.add_parser("copy", help="backup and restore in one step")
    p.add_argument("--from", dest="src", default="cloud")
    p.add_argument("--into", dest="dst", default="local")
    p.add_argument("--mode", choices=("merge", "replace"), default="merge")
    p.add_argument("--schemas", **common_schemas)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("tables", help="list what's in a database")
    p.add_argument("--at", dest="src", default="cloud")

    args = parser.parse_args()

    if args.action == "tables":
        with closing(psycopg.connect(resolve_dsn(args.src))) as conn:
            for schema, table in list_tables(conn):
                print(f"{schema}.{table}: {_row_count(conn, schema, table)} row(s)")
        return

    if args.action == "backup":
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        out = Path(args.out) if args.out else Path("backups") / f"family_{stamp}.zip"
        print(f"Backing up '{args.src}' -> {out}")
        backup(resolve_dsn(args.src), out, args.schemas)
        return

    if args.action == "copy":
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        tmp = Path("backups") / f"_copy_{stamp}.zip"
        print(f"Backing up '{args.src}' -> {tmp}")
        backup(resolve_dsn(args.src), tmp, args.schemas)
        args.file = str(tmp)

    if args.mode == "replace" and not args.yes and not args.dry_run:
        answer = input(
            f"--mode replace EMPTIES every matching table in '{args.dst}' before loading. "
            f"Rows only present there will be lost. Continue? [y/N] "
        )
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled -- nothing was touched.")
            return

    print(f"Restoring {args.file} -> '{args.dst}' (mode: {args.mode})")
    restore(resolve_dsn(args.dst), Path(args.file), args.mode, args.schemas, args.dry_run)

if __name__ == "__main__":
    main()
