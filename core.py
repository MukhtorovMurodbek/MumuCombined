"""What every bot shares: the family bus and the wallet, surviving a redeploy, messages that
keep evolving, problem codes, the public bots' common commands, files past the Bot API's
limits, and prices.

Every section below, from its `# ─── module:` line to the next, is a module of its own: main.py
loads each one separately, for each bot that uses it, so a bot's `import db` is still that
bot's db. This file is never imported whole -- run main.py.
"""
raise ImportError("core.py is loaded section by section by main.py -- run main.py")


# ─── module: family_link ─────────────────────────────────────────────────────
"""The family bus: how one bot talks to ManagerBot, and how ManagerBot talks back."""
from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import socket
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import db
import lifecycle

logger = logging.getLogger(__name__)

FAMILY_SCHEMA = "family"

VERSION = os.environ.get("FAMILY_VERSION", "2.0.0")

_REPORTS_BECAME_AUTOMATIC = datetime(2026, 9, 13, tzinfo=timezone.utc)

HEARTBEAT_SECONDS = int(os.environ.get("FAMILY_HEARTBEAT_SECONDS", "30"))

BUS_POLL_ACTIVE_SECONDS = float(os.environ.get("FAMILY_BUS_POLL_ACTIVE_SECONDS", "1"))
BUS_POLL_IDLE_SECONDS = float(os.environ.get("FAMILY_BUS_POLL_IDLE_SECONDS", "10"))

BUS_ACTIVE_WINDOW_SECONDS = float(os.environ.get("FAMILY_BUS_ACTIVE_WINDOW_SECONDS", "20"))

RUN_LATE = {"misfire_grace_time": None}

_bot_id: str | None = None
_display_name: str | None = None
_start_time: datetime | None = None
_enabled = False

HOSTNAME = socket.gethostname()

COMMAND_RETENTION_HOURS = int(os.environ.get("FAMILY_COMMAND_RETENTION_HOURS", "24"))
EVENT_RETENTION_DAYS = int(os.environ.get("FAMILY_EVENT_RETENTION_DAYS", "30"))
HOUSEKEEPING_SECONDS = int(os.environ.get("FAMILY_HOUSEKEEPING_SECONDS", "21600"))

def _connect():
    return db.pooled()

def init_family_schema() -> None:
    """Idempotent; every bot calls it at startup, whoever gets there first wins."""
    with _connect() as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {FAMILY_SCHEMA}")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.heartbeats (
                bot_id TEXT PRIMARY KEY,
                display_name TEXT,
                host TEXT,
                version TEXT,
                pid INTEGER,
                db_schema TEXT,
                started_at TIMESTAMPTZ NOT NULL,
                last_seen TIMESTAMPTZ NOT NULL,
                error_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.heartbeats "
                     f"ADD COLUMN IF NOT EXISTS commands TEXT")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.events (
                id BIGSERIAL PRIMARY KEY,
                bot_id TEXT NOT NULL,
                level TEXT NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                notified BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_family_events_pending "
            f"ON {FAMILY_SCHEMA}.events (notified, id)"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.commands (
                id BIGSERIAL PRIMARY KEY,
                target_bot TEXT NOT NULL,
                command TEXT NOT NULL,
                args TEXT NOT NULL DEFAULT '',
                requested_by BIGINT,
                reply_chat_id BIGINT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                claimed_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                ok BOOLEAN,
                output TEXT,
                file_name TEXT,
                file_bytes BYTEA,
                delivered BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_family_commands_queue "
            f"ON {FAMILY_SCHEMA}.commands (target_bot, status, id)"
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.usage_samples (
                id BIGSERIAL PRIMARY KEY,
                bot_id TEXT NOT NULL,
                sampled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                window_minutes INTEGER NOT NULL,
                rss_mb INTEGER,
                peak_rss_mb INTEGER,
                ceiling_mb INTEGER,
                cpu_seconds INTEGER,
                updates INTEGER NOT NULL DEFAULT 0,
                users INTEGER NOT NULL DEFAULT 0,
                sleepable_seconds INTEGER NOT NULL DEFAULT 0,
                max_gap_seconds INTEGER NOT NULL DEFAULT 0,
                jobs_ok INTEGER NOT NULL DEFAULT 0,
                jobs_failed INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        for column in ("sleepable_seconds", "max_gap_seconds", "jobs_ok", "jobs_failed"):
            conn.execute(
                f"ALTER TABLE {FAMILY_SCHEMA}.usage_samples "
                f"ADD COLUMN IF NOT EXISTS {column} INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_family_usage_recent "
            f"ON {FAMILY_SCHEMA}.usage_samples (bot_id, sampled_at DESC)"
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.bot_state (
                bot_id TEXT PRIMARY KEY,
                is_up BOOLEAN NOT NULL,
                changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.star_balances (
                user_id BIGINT PRIMARY KEY,
                balance BIGINT NOT NULL DEFAULT 0,
                lifetime_topped_up BIGINT NOT NULL DEFAULT 0,
                lifetime_spent BIGINT NOT NULL DEFAULT 0,
                lifetime_stars_paid BIGINT NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.star_ledger (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                bot_id TEXT NOT NULL,
                delta BIGINT NOT NULL,
                reason TEXT NOT NULL,
                detail TEXT,
                stars_paid BIGINT NOT NULL DEFAULT 0,
                balance_after BIGINT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_family_star_ledger_user "
            f"ON {FAMILY_SCHEMA}.star_ledger (user_id, id DESC)"
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.star_bonus_lots (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount BIGINT NOT NULL,
                remaining BIGINT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_family_bonus_lots_user "
            f"ON {FAMILY_SCHEMA}.star_bonus_lots (user_id, expires_at)"
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FAMILY_SCHEMA}.problem_reports (
                id BIGSERIAL PRIMARY KEY,
                bot_id TEXT NOT NULL,
                code TEXT NOT NULL,
                incident TEXT NOT NULL,
                occurred_at TIMESTAMPTZ,
                reported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                version TEXT,
                UNIQUE (bot_id, incident)
            )
            """
        )

        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.problem_reports "
                     f"ADD COLUMN IF NOT EXISTS shared_at TIMESTAMPTZ")
        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.problem_reports "
                     f"ADD COLUMN IF NOT EXISTS user_id BIGINT")
        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.problem_reports "
                     f"ADD COLUMN IF NOT EXISTS username TEXT")
        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.problem_reports "
                     f"ADD COLUMN IF NOT EXISTS user_lang TEXT")
        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.problem_reports "
                     f"ADD COLUMN IF NOT EXISTS chat_kind TEXT")

        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.problem_reports "
                     f"ADD COLUMN IF NOT EXISTS seen INTEGER NOT NULL DEFAULT 1")

        conn.execute(f"ALTER TABLE {FAMILY_SCHEMA}.problem_reports "
                     f"ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 2")

        conn.execute(f"UPDATE {FAMILY_SCHEMA}.problem_reports "
                     f"SET shared_at = reported_at "
                     f"WHERE shared_at IS NULL AND reported_at < %s",
                     (_REPORTS_BECAME_AUTOMATIC,))

        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_family_problem_reports_recent "
            f"ON {FAMILY_SCHEMA}.problem_reports (reported_at DESC)"
        )
        conn.commit()

TOPUP_MULTIPLIER = float(os.environ.get("FAMILY_TOPUP_MULTIPLIER", "2"))

def _parse_ladder(spec: str) -> list:
    steps = []
    for part in (spec or "").split(","):
        stars, _, multiplier = part.strip().partition(":")
        try:
            steps.append((int(stars), float(multiplier)))
        except ValueError:
            continue
    return [(stars, multiplier) for stars, multiplier in steps if stars > 0 and multiplier >= 1]

TOPUP_LADDER = _parse_ladder(os.environ.get("FAMILY_TOPUP_LADDER", "500:3,500:2"))
BONUS_EXPIRY_DAYS = int(os.environ.get("FAMILY_BONUS_EXPIRY_DAYS", "90"))

LEDGER_REASONS = ("topup", "bonus", "grant", "spend", "refund", "adjustment", "expired")

def credit_for_stars(stars: int) -> int:
    """The ordinary credit `stars` buy, with no bonus -- the part that never expires."""
    return int(round(stars * TOPUP_MULTIPLIER, 6))

def _ladder_ranges():
    start = 0
    for size, multiplier in TOPUP_LADDER:
        yield start, start + size, multiplier
        start += size
    yield start, None, 1.0

def quote_credit(lifetime_paid: int, stars: int) -> dict:
    """What paying `stars` earns for somebody who has already paid `lifetime_paid` Stars, split into the ordinary part and the bonus."""
    low, high = max(0, lifetime_paid), max(0, lifetime_paid) + max(0, stars)
    total = 0.0
    for start, end, multiplier in _ladder_ranges():
        overlap_low = max(start, low)
        overlap_high = high if end is None else min(end, high)
        if overlap_high > overlap_low:
            total += (overlap_high - overlap_low) * TOPUP_MULTIPLIER * multiplier
    base = credit_for_stars(stars)
    total_credit = max(int(round(total, 6)), base)
    return {"stars": stars, "base": base, "bonus": total_credit - base, "total": total_credit}

def ladder_position(lifetime_paid: int) -> tuple:
    """(multiplier the next Star earns, Stars left at that multiplier). The second is None once past the ladder."""
    for start, end, multiplier in _ladder_ranges():
        if end is None or lifetime_paid < end:
            return multiplier, (None if end is None else end - max(lifetime_paid, start))
    return 1.0, None

def _ledger_bot() -> str:
    """Which bot a movement is recorded against."""
    return _bot_id or "unattached"

def _ledger_in(conn, user_id, delta, reason, detail, stars_paid, balance_after) -> None:
    conn.execute(
        f"INSERT INTO {FAMILY_SCHEMA}.star_ledger "
        f"(user_id, bot_id, delta, reason, detail, stars_paid, balance_after) "
        f"VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (user_id, _ledger_bot(), delta, reason, detail, stars_paid, balance_after),
    )

def _lock_wallet_in(conn, user_id) -> int:
    """Make sure the wallet exists and hold it for this transaction."""
    conn.execute(
        f"INSERT INTO {FAMILY_SCHEMA}.star_balances (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )
    return int(conn.execute(
        f"SELECT balance FROM {FAMILY_SCHEMA}.star_balances WHERE user_id = %s FOR UPDATE",
        (user_id,),
    ).fetchone()[0])

def _expire_in(conn, user_id) -> int:
    """Take away this person's bonus credit that has run out."""
    due = conn.execute(
        f"SELECT id, remaining FROM {FAMILY_SCHEMA}.star_bonus_lots "
        f"WHERE user_id = %s AND remaining > 0 AND expires_at <= now() FOR UPDATE",
        (user_id,),
    ).fetchall()
    total = sum(int(row[1]) for row in due)
    if not total:
        return 0
    conn.execute(
        f"UPDATE {FAMILY_SCHEMA}.star_bonus_lots SET remaining = 0 WHERE id = ANY(%s)",
        ([row[0] for row in due],),
    )
    after = conn.execute(
        f"UPDATE {FAMILY_SCHEMA}.star_balances SET balance = balance - %s, updated_at = now() "
        f"WHERE user_id = %s RETURNING balance",
        (total, user_id),
    ).fetchone()[0]
    _ledger_in(conn, user_id, -total, "expired", "bonus credit expired", 0, int(after))
    return total

def _take_bonus_in(conn, user_id, amount) -> None:
    """Reduce this person's unexpired bonus by `amount`, soonest to expire first."""
    if amount <= 0:
        return
    lots = conn.execute(
        f"SELECT id, remaining FROM {FAMILY_SCHEMA}.star_bonus_lots "
        f"WHERE user_id = %s AND remaining > 0 AND expires_at > now() "
        f"ORDER BY expires_at, id FOR UPDATE",
        (user_id,),
    ).fetchall()
    for lot_id, remaining in lots:
        if amount <= 0:
            break
        taken = min(int(remaining), amount)
        conn.execute(
            f"UPDATE {FAMILY_SCHEMA}.star_bonus_lots SET remaining = remaining - %s WHERE id = %s",
            (taken, lot_id),
        )
        amount -= taken

def _bonus_in(conn, user_id) -> int:
    return int(conn.execute(
        f"SELECT coalesce(sum(remaining), 0) FROM {FAMILY_SCHEMA}.star_bonus_lots "
        f"WHERE user_id = %s AND remaining > 0 AND expires_at > now()",
        (user_id,),
    ).fetchone()[0])

def _cap_bonus_in(conn, user_id, balance) -> None:
    """After a balance goes down for any reason but a spend, bonus cannot be more than what is left -- or its expiry would later take away credit that is not there."""
    excess = _bonus_in(conn, user_id) - max(balance, 0)
    _take_bonus_in(conn, user_id, excess)

def _move_in(conn, user_id, delta, reason, detail, stars_paid=0) -> int:
    earned = delta if reason in ("topup", "bonus", "grant") and delta > 0 else 0
    after = int(conn.execute(
        f"UPDATE {FAMILY_SCHEMA}.star_balances "
        f"SET balance = balance + %s, lifetime_topped_up = lifetime_topped_up + %s, "
        f"lifetime_stars_paid = lifetime_stars_paid + %s, updated_at = now() "
        f"WHERE user_id = %s RETURNING balance",
        (delta, earned, stars_paid, user_id),
    ).fetchone()[0])
    _ledger_in(conn, user_id, delta, reason, detail, stars_paid, after)
    return after

def star_balance(user_id: int) -> int:
    """What this person has, in credits, after any expired bonus is gone."""
    with _connect() as conn:
        exists = conn.execute(
            f"SELECT 1 FROM {FAMILY_SCHEMA}.star_balances WHERE user_id = %s", (user_id,)).fetchone()
        if not exists:
            return 0
        _lock_wallet_in(conn, user_id)
        _expire_in(conn, user_id)
        balance = int(conn.execute(
            f"SELECT balance FROM {FAMILY_SCHEMA}.star_balances WHERE user_id = %s", (user_id,)
        ).fetchone()[0])
        conn.commit()
    return balance

def star_totals(user_id: int) -> dict:
    """Balance, lifetime figures, and how much of the balance is bonus with when the next of it expires."""
    empty = {"balance": 0, "topped_up": 0, "spent": 0, "stars_paid": 0,
             "bonus": 0, "bonus_next_amount": 0, "bonus_next_expiry": None}
    with _connect() as conn:
        exists = conn.execute(
            f"SELECT 1 FROM {FAMILY_SCHEMA}.star_balances WHERE user_id = %s", (user_id,)).fetchone()
        if not exists:
            return empty
        _lock_wallet_in(conn, user_id)
        _expire_in(conn, user_id)
        row = conn.execute(
            f"SELECT balance, lifetime_topped_up, lifetime_spent, lifetime_stars_paid "
            f"FROM {FAMILY_SCHEMA}.star_balances WHERE user_id = %s", (user_id,)
        ).fetchone()
        nxt = conn.execute(
            f"SELECT expires_at, sum(remaining) FROM {FAMILY_SCHEMA}.star_bonus_lots "
            f"WHERE user_id = %s AND remaining > 0 AND expires_at > now() "
            f"GROUP BY expires_at ORDER BY expires_at LIMIT 1", (user_id,)
        ).fetchone()
        bonus = _bonus_in(conn, user_id)
        conn.commit()
    return {"balance": int(row[0]), "topped_up": int(row[1]), "spent": int(row[2]),
            "stars_paid": int(row[3]), "bonus": bonus,
            "bonus_next_amount": int(nxt[1]) if nxt else 0,
            "bonus_next_expiry": nxt[0] if nxt else None}

def quote_topup(user_id: int, stars: int) -> dict:
    """quote_credit for this person, from what they have paid so far."""
    with _connect() as conn:
        row = conn.execute(
            f"SELECT lifetime_stars_paid FROM {FAMILY_SCHEMA}.star_balances WHERE user_id = %s",
            (user_id,),
        ).fetchone()
    return quote_credit(int(row[0]) if row else 0, stars)

def move_stars(user_id: int, delta: int, reason: str, detail: str | None = None,
               stars_paid: int = 0) -> int:
    """Add `delta` credits to a balance and record why."""
    if reason not in LEDGER_REASONS:
        raise ValueError(f"unknown ledger reason {reason!r}; add it to LEDGER_REASONS")
    if delta == 0 and not stars_paid:
        return star_balance(user_id)
    with _connect() as conn:
        _lock_wallet_in(conn, user_id)
        _expire_in(conn, user_id)
        after = _move_in(conn, user_id, delta, reason, detail, stars_paid)
        if delta < 0:
            _cap_bonus_in(conn, user_id, after)
        conn.commit()
    return after

def spend_stars(user_id: int, amount: int, reason: str = "spend",
                detail: str | None = None) -> "int | None":
    """Take `amount` credits off a balance if it covers it."""
    if amount <= 0:
        return star_balance(user_id)
    with _connect() as conn:
        balance = _lock_wallet_in(conn, user_id)
        balance -= _expire_in(conn, user_id)
        if balance < amount:
            conn.commit()
            return None
        after = int(conn.execute(
            f"UPDATE {FAMILY_SCHEMA}.star_balances SET balance = balance - %s, "
            f"lifetime_spent = lifetime_spent + %s, updated_at = now() "
            f"WHERE user_id = %s RETURNING balance",
            (amount, amount, user_id),
        ).fetchone()[0])
        _ledger_in(conn, user_id, -amount, reason, detail, 0, after)
        _take_bonus_in(conn, user_id, amount)
        conn.commit()
    return after

def topup(user_id: int, stars_paid: int, detail: str | None = None) -> dict:
    """The whole of the money-in path."""
    with _connect() as conn:
        _lock_wallet_in(conn, user_id)
        _expire_in(conn, user_id)
        lifetime = int(conn.execute(
            f"SELECT lifetime_stars_paid FROM {FAMILY_SCHEMA}.star_balances WHERE user_id = %s",
            (user_id,),
        ).fetchone()[0])
        quote = quote_credit(lifetime, stars_paid)
        balance = _move_in(conn, user_id, quote["base"], "topup", detail, stars_paid)
        expires = None
        if quote["bonus"] > 0:
            balance = _move_in(conn, user_id, quote["bonus"], "bonus",
                               f"ladder bonus on {stars_paid} stars, expires in {BONUS_EXPIRY_DAYS} days")
            expires = conn.execute(
                f"INSERT INTO {FAMILY_SCHEMA}.star_bonus_lots (user_id, amount, remaining, expires_at) "
                f"VALUES (%s, %s, %s, now() + make_interval(days => %s)) RETURNING expires_at",
                (user_id, quote["bonus"], quote["bonus"], BONUS_EXPIRY_DAYS),
            ).fetchone()[0]
        conn.commit()
    return {"stars": stars_paid, "credited": quote["base"], "bonus": quote["bonus"],
            "balance": balance, "bonus_expires": expires, "lifetime_before": lifetime}

def set_star_balance(user_id: int, target: int, reason: str = "adjustment",
                     detail: str | None = None) -> int:
    """Put a balance at exactly `target` credits, recording the movement."""
    with _connect() as conn:
        before = _lock_wallet_in(conn, user_id)
        before -= _expire_in(conn, user_id)
        delta = target - before
        if delta:
            conn.execute(
                f"UPDATE {FAMILY_SCHEMA}.star_balances SET balance = %s, updated_at = now() WHERE user_id = %s",
                (target, user_id),
            )
            _ledger_in(conn, user_id, delta, reason, detail, 0, target)
            _cap_bonus_in(conn, user_id, target)
        conn.commit()
    return target

def grant_stars_once(user_id: int, amount: int, key: str, detail: str | None = None,
                     reason: str = "grant") -> "int | None":
    """Credit `amount` the first time this (key, user) is ever asked for, and never again."""
    claim = f"stars:granted:{key}:{user_id}"
    with _connect() as conn:
        won = conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.settings (key, value) VALUES (%s, %s) "
            f"ON CONFLICT (key) DO NOTHING RETURNING key",
            (claim, datetime.now(timezone.utc).isoformat()),
        ).fetchone()
        conn.commit()
    if not won:
        return None
    try:
        return move_stars(user_id, amount, reason, detail or key)
    except Exception:
        try:
            with _connect() as conn:
                conn.execute(f"DELETE FROM {FAMILY_SCHEMA}.settings WHERE key = %s", (claim,))
                conn.commit()
        except Exception:
            logger.exception("Could not release the grant claim %s", claim)
        raise

def expire_bonus_credit() -> int:
    """Housekeeping: expire every person's run-out bonus."""
    with _connect() as conn:
        users = [row[0] for row in conn.execute(
            f"SELECT DISTINCT user_id FROM {FAMILY_SCHEMA}.star_bonus_lots "
            f"WHERE remaining > 0 AND expires_at <= now()"
        ).fetchall()]
    total = 0
    for user_id in users:
        with _connect() as conn:
            _lock_wallet_in(conn, user_id)
            total += _expire_in(conn, user_id)
            conn.commit()
    return total

def star_ledger_for(user_id: int, limit: int = 10) -> list[dict]:
    """This person's movements, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT occurred_at, bot_id, delta, reason, detail, stars_paid, balance_after "
            f"FROM {FAMILY_SCHEMA}.star_ledger WHERE user_id = %s "
            f"ORDER BY id DESC LIMIT %s",
            (user_id, max(1, min(limit, 100))),
        ).fetchall()
    return [{"occurred_at": r[0], "bot_id": r[1], "delta": int(r[2]),
             "reason": r[3], "detail": r[4], "stars_paid": int(r[5] or 0),
             "balance_after": int(r[6])}
            for r in rows]

def star_balance_overview(limit: int = 20) -> tuple[dict, list[dict]]:
    """Family-wide totals, and the largest balances."""
    with _connect() as conn:
        totals = conn.execute(
            f"SELECT coalesce(sum(balance), 0), coalesce(sum(lifetime_topped_up), 0), "
            f"coalesce(sum(lifetime_spent), 0), coalesce(sum(lifetime_stars_paid), 0), "
            f"count(*) FROM {FAMILY_SCHEMA}.star_balances"
        ).fetchone()
        bonus = conn.execute(
            f"SELECT coalesce(sum(remaining), 0) FROM {FAMILY_SCHEMA}.star_bonus_lots "
            f"WHERE remaining > 0 AND expires_at > now()"
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT user_id, balance, lifetime_topped_up, lifetime_spent, lifetime_stars_paid "
            f"FROM {FAMILY_SCHEMA}.star_balances "
            f"WHERE balance <> 0 ORDER BY balance DESC LIMIT %s",
            (max(1, min(limit, 100)),),
        ).fetchall()
    return (
        {"outstanding": int(totals[0]), "topped_up": int(totals[1]),
         "spent": int(totals[2]), "stars_paid": int(totals[3]),
         "wallets": int(totals[4]), "bonus": int(bonus)},
        [{"user_id": int(r[0]), "balance": int(r[1]), "topped_up": int(r[2]),
          "spent": int(r[3]), "stars_paid": int(r[4])} for r in rows],
    )

def record_problem_occurrence(code: str, incident: str, occurred_at, level: int = 2) -> bool:
    """Write down that this problem was shown."""
    with _connect() as conn:
        row = conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.problem_reports "
            f"(bot_id, code, incident, occurred_at, version, level) "
            f"VALUES (%s, %s, %s, %s, %s, %s) "
            f"ON CONFLICT (bot_id, incident) DO UPDATE "
            f"SET seen = {FAMILY_SCHEMA}.problem_reports.seen + 1 "
            f"RETURNING (xmax = 0)",
            (_ledger_bot(), code, incident, occurred_at, VERSION, int(level)),
        ).fetchone()
        conn.commit()
    return bool(row and row[0])

def attach_problem_reporter(code: str, incident: str, occurred_at,
                            user_id: int, username: "str | None",
                            user_lang: "str | None", chat_kind: "str | None",
                            level: int = 2) -> bool:
    """Add the details somebody volunteered to their incident's row."""
    with _connect() as conn:
        row = conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.problem_reports "
            f"(bot_id, code, incident, occurred_at, version, level, shared_at, "
            f" user_id, username, user_lang, chat_kind) "
            f"VALUES (%s, %s, %s, %s, %s, %s, now(), %s, %s, %s, %s) "
            f"ON CONFLICT (bot_id, incident) DO UPDATE "
            f"SET shared_at = now(), user_id = excluded.user_id, "
            f"    username = excluded.username, user_lang = excluded.user_lang, "
            f"    chat_kind = excluded.chat_kind "
            f"WHERE {FAMILY_SCHEMA}.problem_reports.shared_at IS NULL "
            f"RETURNING id",
            (_ledger_bot(), code, incident, occurred_at, VERSION, int(level),
             user_id, username, user_lang, chat_kind),
        ).fetchone()
        conn.commit()
    return row is not None

def recent_problem_reports(limit: int = 15, shared_only: bool = False) -> list[dict]:
    """The latest problems, newest first."""
    where = " WHERE shared_at IS NOT NULL" if shared_only else ""
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT reported_at, bot_id, code, incident, occurred_at, version, "
            f"seen, shared_at, user_id, username, user_lang, chat_kind, level "
            f"FROM {FAMILY_SCHEMA}.problem_reports{where} ORDER BY id DESC LIMIT %s",
            (max(1, min(limit, 100)),),
        ).fetchall()
    return [_problem_row(r) for r in rows]

def problem_report_by_incident(incident: str) -> "dict | None":
    """One incident, whichever bot it came from."""
    with _connect() as conn:
        row = conn.execute(
            f"SELECT reported_at, bot_id, code, incident, occurred_at, version, "
            f"seen, shared_at, user_id, username, user_lang, chat_kind, level "
            f"FROM {FAMILY_SCHEMA}.problem_reports WHERE incident = %s "
            f"ORDER BY id DESC LIMIT 1",
            (incident,),
        ).fetchone()
    return _problem_row(row) if row is not None else None

def _problem_row(r) -> dict:
    return {"reported_at": r[0], "bot_id": r[1], "code": r[2], "incident": r[3],
            "occurred_at": r[4], "version": r[5], "seen": r[6], "shared_at": r[7],
            "user_id": r[8], "username": r[9], "user_lang": r[10], "chat_kind": r[11],
            "level": r[12]}

def recent_problem_reports_since(hours: int = 24, limit: int = 400) -> list:
    """Everything recorded in the last `hours`, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT reported_at, bot_id, code, incident, occurred_at, version, "
            f"seen, shared_at, user_id, username, user_lang, chat_kind, level "
            f"FROM {FAMILY_SCHEMA}.problem_reports "
            f"WHERE reported_at > now() - make_interval(hours => %s) "
            f"ORDER BY id DESC LIMIT %s",
            (max(1, min(hours, 168)), max(1, min(limit, 1000))),
        ).fetchall()
    return [_problem_row(r) for r in rows]

def problem_counts_since(hours: int = 24) -> dict:
    """{bot_id: {level: count}} for the last `hours`."""
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT bot_id, level, count(*), coalesce(sum(seen), 0) "
            f"FROM {FAMILY_SCHEMA}.problem_reports "
            f"WHERE reported_at > now() - make_interval(hours => %s) "
            f"GROUP BY bot_id, level",
            (max(1, min(hours, 168)),),
        ).fetchall()
    out: dict = {}
    for bot_id, level, incidents, seen in rows:
        out.setdefault(bot_id, {})[int(level)] = {"incidents": int(incidents), "seen": int(seen)}
    return out

PROBLEM_DETAIL_RETENTION_DAYS = int(os.environ.get("PROBLEM_DETAIL_RETENTION_DAYS", "30"))
PROBLEM_RETENTION_DAYS = int(os.environ.get("PROBLEM_RETENTION_DAYS", "180"))

def prune_problem_reports() -> int:
    """Clear old volunteered details, then drop old rows entirely. Returns how many rows were changed or removed."""
    with _connect() as conn:
        cleared = conn.execute(
            f"UPDATE {FAMILY_SCHEMA}.problem_reports "
            f"SET user_id = NULL, username = NULL, user_lang = NULL, chat_kind = NULL "
            f"WHERE shared_at IS NOT NULL AND user_id IS NOT NULL "
            f"AND shared_at < now() - make_interval(days => %s)",
            (PROBLEM_DETAIL_RETENTION_DAYS,),
        ).rowcount or 0
        removed = conn.execute(
            f"DELETE FROM {FAMILY_SCHEMA}.problem_reports "
            f"WHERE reported_at < now() - make_interval(days => %s)",
            (PROBLEM_RETENTION_DAYS,),
        ).rowcount or 0
        conn.commit()
    return cleared + removed

def forget_problem_reporter(user_id: int) -> int:
    """Take one person off every problem they ever volunteered for, now."""
    with _connect() as conn:
        changed = conn.execute(
            f"UPDATE {FAMILY_SCHEMA}.problem_reports "
            f"SET user_id = NULL, username = NULL, user_lang = NULL, chat_kind = NULL "
            f"WHERE user_id = %s",
            (user_id,),
        ).rowcount or 0
        conn.commit()
    return changed

_bus_active_until = 0.0

def mark_bus_active() -> None:
    """Poll at the fast cadence for the next BUS_ACTIVE_WINDOW_SECONDS."""
    global _bus_active_until
    _bus_active_until = time.monotonic() + BUS_ACTIVE_WINDOW_SECONDS

def bus_is_active() -> bool:
    return time.monotonic() < _bus_active_until

def _monitoring():
    """The module holding this bot's error counter / status text."""
    for name in ("monitoring", "shared_features"):
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
        except Exception:
            return None
    return None

def write_heartbeat() -> None:
    sf = _monitoring()
    errors = getattr(sf, "_error_count", 0) if sf else 0
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {FAMILY_SCHEMA}.heartbeats
                (bot_id, display_name, host, version, pid, db_schema, started_at, last_seen,
                 error_count, commands)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s, %s)
            ON CONFLICT (bot_id) DO UPDATE SET
                display_name = excluded.display_name,
                host = excluded.host,
                version = excluded.version,
                pid = excluded.pid,
                db_schema = excluded.db_schema,
                started_at = excluded.started_at,
                last_seen = excluded.last_seen,
                error_count = excluded.error_count,
                commands = excluded.commands
            """,
            (_bot_id, _display_name, HOSTNAME, VERSION, os.getpid(),
             getattr(db, "DB_SCHEMA", "public"), _start_time, errors,
             ",".join(sorted(COMMANDS))),
        )
        conn.commit()

USAGE_RETENTION_DAYS = int(os.environ.get("FAMILY_USAGE_RETENTION_DAYS") or 45)

def report_event(level: str, kind: str, message: str, details: str | None = None) -> None:
    """Blocking -- call it through asyncio.to_thread from async code, or just let report_event_soon() below do that for you."""
    if not _enabled:
        return
    with _connect() as conn:
        conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.events (bot_id, level, kind, message, details) "
            f"VALUES (%s, %s, %s, %s, %s)",
            (_bot_id, level, kind, message[:4000], (details or "")[:8000] or None),
        )
        conn.commit()

def record_usage(window_minutes: int, rss_mb, peak_rss_mb, ceiling_mb,
                 cpu_seconds, updates: int, users: int, sleepable_seconds: int = 0,
                 max_gap_seconds: int = 0, jobs_ok: int = 0, jobs_failed: int = 0) -> None:
    """One sampling window's worth of what this process cost. Blocking."""
    if not _enabled:
        return
    with _connect() as conn:
        conn.execute(
            f"INSERT INTO {FAMILY_SCHEMA}.usage_samples "
            f"(bot_id, window_minutes, rss_mb, peak_rss_mb, ceiling_mb, cpu_seconds, "
            f"updates, users, sleepable_seconds, max_gap_seconds, jobs_ok, jobs_failed) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (_bot_id, window_minutes, rss_mb, peak_rss_mb, ceiling_mb, cpu_seconds,
             updates, users, sleepable_seconds, max_gap_seconds, jobs_ok, jobs_failed),
        )
        conn.commit()

def usage_history(bot_id: str | None = None, hours: int = 24) -> list[dict]:
    """Recent samples, newest first. `bot_id=None` means every bot, which is what ManagerBot asks for."""
    if not _enabled:
        return []
    where = "sampled_at > now() - make_interval(hours => %s)"
    params: tuple = (hours,)
    if bot_id:
        where += " AND bot_id = %s"
        params += (bot_id,)
    with _connect() as conn:
        cur = conn.execute(
            f"SELECT bot_id, sampled_at, window_minutes, rss_mb, peak_rss_mb, "
            f"ceiling_mb, cpu_seconds, updates, users, sleepable_seconds, "
            f"max_gap_seconds, jobs_ok, jobs_failed "
            f"FROM {FAMILY_SCHEMA}.usage_samples WHERE {where} "
            f"ORDER BY sampled_at DESC LIMIT 5000",
            params,
        )
        names = [column.name for column in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]

def report_event_soon(level: str, kind: str, message: str, details: str | None = None) -> None:
    """Fire-and-forget version, safe to call from a running event loop or from plain sync code."""
    def _run():
        try:
            report_event(level, kind, message, details)
        except Exception:
            logger.debug("Could not report a family event", exc_info=True)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _run()
        return
    loop.run_in_executor(None, _run)

def _where_am_i() -> str:
    sf = _monitoring()
    detect = getattr(sf, "detect_host_environment", None) if sf else None
    if detect is not None:
        try:
            return detect()
        except Exception:
            pass
    return HOSTNAME

def ping_probe() -> dict:
    """Blocking -- call through asyncio.to_thread."""
    local_before = datetime.now(timezone.utc)
    started = time.perf_counter()

    with db.pooled_read() as conn:
        server_now = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    elapsed_ms = (time.perf_counter() - started) * 1000
    local_after = datetime.now(timezone.utc)

    midpoint = local_before + (local_after - local_before) / 2
    return {
        "db_ms": round(elapsed_ms, 2),
        "skew_ms": round((server_now - midpoint).total_seconds() * 1000, 1),
        "host": HOSTNAME,
        "where": _where_am_i(),
        "version": VERSION,
        "pid": os.getpid(),
    }

PROBE_USER_ID = 0

def user_path_probe() -> dict:
    """Blocking -- call through asyncio.to_thread. The database half of what a person actually waits for."""
    read = getattr(db, "get_user_language", None)
    started = time.perf_counter()
    if read is not None:
        read(PROBE_USER_ID)
        what = "user_settings"
    else:

        with db.pooled_read() as conn:
            conn.execute("SELECT 1").fetchone()
        what = "SELECT 1"
    return {"info_ms": round((time.perf_counter() - started) * 1000, 2), "info_query": what}

async def _telegram_round_trip(context) -> float | None:
    """One call to the Bot API and back, in milliseconds."""
    bot = getattr(context, "bot", None)
    if bot is None or not hasattr(bot, "get_webhook_info"):
        return None
    started = time.perf_counter()
    await bot.get_webhook_info()
    return round((time.perf_counter() - started) * 1000, 2)

async def _cmd_ping(context, args):
    """Plain `ping` answers a sentence."""
    up = datetime.now(timezone.utc) - _start_time
    if not args or args[0] != "trace":
        return f"pong -- up {_format_delta(up)}", None, None
    try:
        probe = await asyncio.to_thread(ping_probe)
    except Exception as exc:
        probe = {"error": f"{type(exc).__name__}: {exc}"}
    probe["up"] = _format_delta(up)

    user: dict = {}
    try:
        user.update(await asyncio.to_thread(user_path_probe))
    except Exception as exc:
        user["info_error"] = f"{type(exc).__name__}: {exc}"
    try:
        telegram_ms = await _telegram_round_trip(context)
        if telegram_ms is not None:
            user["telegram_ms"] = telegram_ms
    except Exception as exc:
        user["telegram_error"] = f"{type(exc).__name__}: {exc}"
    if "info_ms" in user and "telegram_ms" in user:

        user["total_ms"] = round(user["info_ms"] + user["telegram_ms"], 2)
    probe["user"] = user
    return json.dumps(probe, separators=(",", ":")), None, None

async def _cmd_status(context, args):
    sf = _monitoring()
    now = datetime.now(timezone.utc)
    hour = await _active_users_since(now - timedelta(hours=1))
    since_start = await _active_users_since(_start_time)
    if sf and hasattr(sf, "build_status_text"):
        return sf.build_status_text(_start_time, hour, since_start), None, None
    return (
        f"Started: {_start_time:%Y-%m-%d %H:%M:%S UTC}\n"
        f"Active users (last hour): {hour}\n"
        f"Active users (since start): {since_start}"
    ), None, None

async def _cmd_errors(context, args):
    sf = _monitoring()
    if sf and hasattr(sf, "error_summary"):
        return sf.error_summary(), None, None
    return "No error tracking in this bot.", None, None

async def _cmd_users(context, args):
    hours = int(args[0]) if args and args[0].isdigit() else 24
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return f"{await _active_users_since(since)} active user(s) in the last {hours}h.", None, None

async def _cmd_dbdump(context, args):
    dump = getattr(db, "dump_database_csv_zip", None)
    if dump is None:
        return "This bot has no database export.", None, None
    data = await asyncio.to_thread(dump)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    return f"{len(data)/1024:.0f} KB", f"{_bot_id}_db_{stamp}.zip", data

async def _cmd_whois(context, args):
    if not args or not args[0].lstrip("-").isdigit():
        return "Usage: whois <user_id>", None, None
    user_id = int(args[0])
    lines = [f"{user_id}"]
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
        lines.append(f"Couldn't fetch their profile from this bot: {exc}")
        lines.append("(They may have never messaged this bot, or blocked it.)")
    return "\n".join(lines), None, None

async def _cmd_message(context, args):
    """Sends as THIS bot -- that is the whole point of routing it here rather than having ManagerBot send it: the user only ever sees the bot they actually talked to."""
    if len(args) < 2 or not args[0].lstrip("-").isdigit():
        return "Usage: message <user_id> <text>", None, None
    await context.bot.send_message(chat_id=int(args[0]), text=" ".join(args[1:]))
    return "Sent.", None, None

class _RecentLines(logging.Handler):
    """The last lines one of the log files would hold, kept in memory."""

    def __init__(self, capacity: int, level: int, only: str | None = None):
        super().__init__(level)
        self.lines: deque = deque(maxlen=capacity)
        self.only = only

    def emit(self, record) -> None:
        if self.only and record.name != self.only:
            return
        try:
            self.lines.extend(self.format(record).splitlines())
        except Exception:
            pass

    def tail(self, wanted: int) -> list[str]:
        return list(self.lines)[-wanted:]

_RECENT_LOGS = {
    "bot.log": _RecentLines(1500, logging.INFO),
    "errors.log": _RecentLines(800, logging.WARNING),
    "problems.log": _RecentLines(500, logging.INFO, only="problems"),
}

def keep_recent_log_lines() -> None:
    """Keep the latest lines of each log in memory, for /logs on a host with no log files."""
    root = logging.getLogger()
    fmt = next((h.formatter for h in root.handlers if h.formatter is not None), None) \
        or logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    for handler in _RECENT_LOGS.values():
        if handler not in root.handlers:
            handler.setFormatter(fmt)
            root.addHandler(handler)

def _tail_lines(path: Path, wanted: int) -> list[str]:
    """Reads the last `wanted` lines by seeking backwards from the end of the file."""
    block = 8192
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        data = b""
        while end > 0 and data.count(b"\n") <= wanted:
            step = min(block, end)
            end -= step
            f.seek(end)
            data = f.read(step) + data
    return data.decode("utf-8", errors="replace").splitlines()[-wanted:]

async def _cmd_logs(context, args):
    lines_wanted = min(int(args[0]), 500) if args and args[0].isdigit() else 40
    which = "errors.log"
    if args and args[-1] in ("bot", "all"):
        which = "bot.log"
    elif args and args[-1] in ("problems", "problem"):
        which = "problems.log"
    path = Path(__file__).resolve().parent / "logs" / which
    if path.exists():
        tail = await asyncio.to_thread(_tail_lines, path, lines_wanted)
        where = which
    else:

        tail = _RECENT_LOGS[which].tail(lines_wanted)
        where = f"{which} (kept in memory since this process started; no log files on this host)"
    if not tail:
        return f"{where}: nothing yet.", None, None
    return f"--- {where}, last {len(tail)} line(s) ---\n" + "\n".join(tail), None, None

async def _cmd_restart(context, args):
    """Exits with a non-zero code so a supervisor restarts the process -- Railway's restart policy, Docker's restart: unless-stopped, and so on."""
    async def _bye():
        await asyncio.sleep(2)
        logger.warning("Restarting: asked to by ManagerBot.")
        os._exit(1)

    asyncio.create_task(_bye())
    return "Restarting now (a supervisor brings it back; a hand-started process just stops).", None, None

async def _cmd_crashtest(context, args):
    """Deliberately raise inside this bot, so the whole crash path can be checked end to end from ManagerBot without waiting for a real bug."""
    app = getattr(context, "application", None)
    if app is None:
        raise RuntimeError("Manual crashtest via ManagerBot -- error tracking works.")

    async def _boom():
        raise RuntimeError(
            f"Manual crashtest for {_bot_id} via ManagerBot -- error tracking works.")

    app.create_task(_boom())
    return ("Raised. The alert should arrive in a moment; if it does not, "
            "the crash reporting is what is broken."), None, None

def _i18n():
    """This bot's translations, or None."""
    try:
        return importlib.import_module("i18n")
    except ImportError:
        return None
    except Exception:
        return None

_PLAIN = {
    "update_soon_try_later": "\U0001f527 I'm about to be updated, so I can't start anything new right now. Please try again in about {minutes} minutes.",
    "update_soon_try_later_soon": "\U0001f527 I'm about to be updated, so I can't start anything new right now. Please try again shortly.",
    "update_will_reset": "\U0001f527 Heads up: I'm about to be updated, and what you have going right now will be reset. You'll be able to start it again in a moment.",
    "update_done_try_now": "✅ The update is done. You can go ahead and try again now.",
}

def phrase(key: str, lang: str | None = None, **kwargs) -> str:
    """One of the four sentences above, translated if this bot can."""
    i18n = _i18n()
    if i18n is not None:
        try:
            text = i18n.t(lang or "en", key, **kwargs)

            if text and text != key:
                return text
        except Exception:
            pass
    return _PLAIN.get(key, key).format(**kwargs)

def _language_of(user_id: int) -> str | None:
    fn = getattr(db, "get_user_language", None)
    if fn is None:
        return None
    try:
        return fn(user_id)
    except Exception:
        return None

BROADCAST_ACTIVE_DAYS = int(os.environ.get("FAMILY_BROADCAST_ACTIVE_DAYS", "7"))

def _everyone() -> list[int]:
    fn = getattr(db, "list_all_users", None)
    if fn is None:
        return []
    try:
        return fn()
    except Exception:
        logger.exception("Could not read this bot's user list")
        return []

def _recently_active(days: int) -> list[int] | None:
    """Everyone seen in the last `days`, or None if this bot cannot say."""
    fn = getattr(db, "active_user_ids_since", None)
    if fn is None:
        return None
    try:
        return fn(datetime.now(timezone.utc) - timedelta(days=days))
    except Exception:
        logger.exception("Could not read this bot's active users")
        return None

BROADCAST_PER_SECOND = float(os.environ.get("FAMILY_BROADCAST_PER_SECOND", "20"))

async def _send_to_each(context, targets, text_for) -> tuple[int, int]:
    """(delivered, skipped)."""
    delivered = skipped = 0
    delay = 1.0 / BROADCAST_PER_SECOND if BROADCAST_PER_SECOND > 0 else 0
    for user_id, chat_id in targets:
        text = text_for(user_id)
        if not text:
            skipped += 1
            continue
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            delivered += 1
        except Exception as exc:
            skipped += 1
            logger.debug("Broadcast skipped %s: %s", chat_id, exc)
        if delay:
            await asyncio.sleep(delay)
    return delivered, skipped

async def _cmd_broadcast(context, args):
    """Sends one message to everyone this bot knows, as this bot."""
    aimed = bool(args) and args[0] == "--active"
    if aimed:
        args = args[1:]
    text = " ".join(args).strip()
    if not text:
        return "Usage: broadcast [--active] <text>", None, None

    if aimed:
        users = await asyncio.to_thread(_recently_active, BROADCAST_ACTIVE_DAYS)
        if users is None:
            return ("This bot cannot tell who is active, so --active would have "
                    "reached nobody. Nothing was sent."), None, None
        who = f"active in the last {BROADCAST_ACTIVE_DAYS} day(s)"
    else:
        users = await asyncio.to_thread(_everyone)
        who = "everyone this bot knows"

    if not users:
        return f"Nobody to broadcast to ({who}).", None, None
    delivered, skipped = await _send_to_each(
        context, ((uid, uid) for uid in users), lambda _uid: text,
    )
    return (
        f"Broadcast to {delivered} of {len(users)} user(s), {who}"
        + (f"; {skipped} unreachable." if skipped else "."),
        None, None,
    )

async def _cmd_pause(context, args):
    """Stop starting work a redeploy would throw away, and say so."""
    minutes = int(args[0]) if args and args[0].isdigit() else lifecycle.DEFAULT_MAINTENANCE_MINUTES
    until = await asyncio.to_thread(lifecycle.begin_maintenance, _bot_id, minutes)
    return (
        f"Paused. New long work is declined until you say otherwise; "
        f"users are being told to come back in about {minutes} minute(s) "
        f"(around {until.strftime('%H:%M')} UTC).",
        None, None,
    )

async def _cmd_warnbusy(context, args):
    """Tell everyone mid-something that it is about to be lost."""
    waiting = lifecycle.in_flight()
    if not waiting:
        return "Nobody is mid-anything right now -- nothing to warn about.", None, None
    seen = set()
    targets = []
    for chat_id, _ in waiting:
        if chat_id not in seen:
            seen.add(chat_id)
            targets.append((chat_id, chat_id))
    delivered, skipped = await _send_to_each(
        context, targets,
        lambda uid: phrase("update_will_reset", _language_of(uid)),
    )
    return (
        f"Warned {delivered} user(s) with work in flight"
        + (f"; {skipped} unreachable." if skipped else "."),
        None, None,
    )

async def _cmd_resume(context, args):
    """The other half of pause: reopen, and go back to everyone who was turned away while it was closed."""
    await asyncio.to_thread(lifecycle.end_maintenance, _bot_id)
    held = await asyncio.to_thread(lifecycle.take_held, _bot_id)
    if not held:
        return "Open again. Nobody had been turned away.", None, None
    delivered, skipped = await _send_to_each(
        context, held,
        lambda uid: phrase("update_done_try_now", _language_of(uid)),
    )
    return (
        f"Open again. Told {delivered} of {len(held)} user(s) who had been "
        f"turned away" + (f"; {skipped} unreachable." if skipped else "."),
        None, None,
    )

COMMANDS = {
    "ping": _cmd_ping,
    "status": _cmd_status,
    "errors": _cmd_errors,
    "users": _cmd_users,
    "dbdump": _cmd_dbdump,
    "whois": _cmd_whois,
    "message": _cmd_message,
    "logs": _cmd_logs,
    "restart": _cmd_restart,
    "crashtest": _cmd_crashtest,
    "broadcast": _cmd_broadcast,
    "pause": _cmd_pause,
    "warnbusy": _cmd_warnbusy,
    "resume": _cmd_resume,
}

COMMAND_HELP = {
    "ping": "is it alive, and for how long",
    "status": "uptime, host, crash count, active users",
    "errors": "errors since that bot last started",
    "users": "active users -- users [hours], default 24",
    "dbdump": "that bot's own tables as a zip of CSVs",
    "whois": "whois <user_id> -- look a user up through that bot",
    "message": "message <user_id> <text> -- DM someone as that bot",
    "logs": "logs [n] [bot|problems] -- tail errors.log, bot.log with 'bot', problems.log with 'problems'",
    "restart": "restart that bot's process",
    "crashtest": "raise on purpose, to check the crash alert still works",
    "broadcast": "broadcast [--active] <text> -- one message as that bot; --active aims it at recent users only",
    "pause": "pause [minutes] -- decline new long work and say why",
    "warnbusy": "tell whoever is mid-something that it is about to be reset",
    "resume": "reopen, and tell everyone who was turned away",
}

async def _active_users_since(since) -> int:
    fn = getattr(db, "count_active_users_since", None)
    if fn is None:
        return 0
    try:
        return await asyncio.to_thread(fn, since)
    except Exception:
        return 0

def _format_delta(delta: timedelta) -> str:
    days, rem = divmod(int(delta.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def _claim_next_command() -> tuple[int, str, str] | None:
    """FOR UPDATE SKIP LOCKED so two copies of the same bot (a laptop one and a deployed one both pointed at the same database) can't run the same command twice."""
    with _connect() as conn:
        cur = conn.execute(
            f"""
            UPDATE {FAMILY_SCHEMA}.commands SET status = 'running', claimed_at = now()
            WHERE id = (
                SELECT id FROM {FAMILY_SCHEMA}.commands
                WHERE target_bot = %s AND status = 'pending'
                ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
            )
            RETURNING id, command, args
            """,
            (_bot_id,),
        )
        row = cur.fetchone()
        conn.commit()
        return row

def _finish_command(command_id: int, ok: bool, output: str, file_name, file_bytes) -> None:
    with _connect() as conn:
        conn.execute(
            f"""
            UPDATE {FAMILY_SCHEMA}.commands
            SET status = %s, ok = %s, output = %s, file_name = %s, file_bytes = %s, finished_at = now()
            WHERE id = %s
            """,
            ("done" if ok else "failed", ok, output[:60000], file_name, file_bytes, command_id),
        )
        conn.commit()

async def _run_one_command(context, row) -> None:
    command_id, command, raw_args = row
    handler = COMMANDS.get(command)
    logger.info("ManagerBot asked for: %s %s", command, raw_args)
    try:
        if handler is None:
            ok, output, name, data = False, f"Unknown command '{command}'.", None, None
        else:
            output, name, data = await handler(context, raw_args.split())
            ok = True
    except Exception as exc:
        logger.exception("Family command %r failed", command)
        ok, output, name, data = False, f"{type(exc).__name__}: {exc}", None, None

    try:
        await asyncio.to_thread(_finish_command, command_id, ok, output, name, data)
    except Exception:
        logger.exception("Could not write the result of family command %s back", command_id)

MAX_COMMANDS_PER_PASS = int(os.environ.get("FAMILY_MAX_COMMANDS_PER_PASS", "10"))

async def _poll_commands(context) -> None:
    ran = 0
    for _ in range(MAX_COMMANDS_PER_PASS):
        try:
            row = await asyncio.to_thread(_claim_next_command)
        except Exception:
            logger.debug("Family command poll failed (database unreachable?)", exc_info=True)
            break
        if not row:
            break
        await _run_one_command(context, row)
        ran += 1
    if ran:

        mark_bus_active()

_last_bus_poll_at = 0.0

async def _bus_tick(context) -> None:
    global _last_bus_poll_at
    due = BUS_POLL_ACTIVE_SECONDS if bus_is_active() else BUS_POLL_IDLE_SECONDS
    now = time.monotonic()
    if now - _last_bus_poll_at < due:
        return
    _last_bus_poll_at = now
    await _poll_commands(context)

async def _send_heartbeat(context) -> None:
    try:
        await asyncio.to_thread(write_heartbeat)
    except Exception:
        logger.debug("Heartbeat failed (database unreachable?)", exc_info=True)

def _prune_family_rows() -> tuple[int, int]:
    with _connect() as conn:
        cur = conn.execute(
            f"DELETE FROM {FAMILY_SCHEMA}.commands "
            f"WHERE target_bot = %s AND delivered = TRUE "
            f"AND finished_at < now() - make_interval(hours => %s)",
            (_bot_id, COMMAND_RETENTION_HOURS),
        )
        commands = cur.rowcount
        cur = conn.execute(
            f"DELETE FROM {FAMILY_SCHEMA}.events "
            f"WHERE bot_id = %s AND notified = TRUE "
            f"AND occurred_at < now() - make_interval(days => %s)",
            (_bot_id, EVENT_RETENTION_DAYS),
        )
        events = cur.rowcount
        cur = conn.execute(
            f"DELETE FROM {FAMILY_SCHEMA}.usage_samples "
            f"WHERE bot_id = %s AND sampled_at < now() - make_interval(days => %s)",
            (_bot_id, USAGE_RETENTION_DAYS),
        )
        samples = cur.rowcount
        conn.commit()
    return commands, events, samples

def _prune() -> str:
    commands, events, samples = _prune_family_rows()
    parts = [f"{commands} command(s)", f"{events} event(s)", f"{samples} usage sample(s)"]
    try:
        parts.append(f"{expire_bonus_credit()} expired bonus credit")
    except Exception:
        logger.debug("Could not expire bonus credit", exc_info=True)

    try:
        parts.append(f"{prune_problem_reports()} problem row(s)")
    except Exception:
        logger.debug("Could not prune problem reports", exc_info=True)
    own = getattr(db, "prune_old_data", None)
    if own is not None:
        parts.append(f"{own()} activity row(s)")
    return ", ".join(parts)

async def _housekeeping(context) -> None:
    try:
        removed = await asyncio.to_thread(_prune)
    except Exception:
        logger.debug("Housekeeping pass failed (database unreachable?)", exc_info=True)
        return
    logger.info("Housekeeping: pruned %s.", removed)

def attach(app, bot_id: str, display_name: str, start_time: datetime) -> None:
    """One line in each bot's main(), just before run_polling()."""
    global _bot_id, _display_name, _start_time, _enabled

    keep_recent_log_lines()

    if os.environ.get("FAMILY_BUS", "on").lower() in ("off", "0", "false", "no"):
        logger.info("Family bus disabled (FAMILY_BUS=off) -- running standalone.")
        return

    bot_id = os.environ.get("FAMILY_BOT_ID") or bot_id
    display_name = os.environ.get("FAMILY_LABEL") or display_name
    _bot_id, _display_name, _start_time = bot_id, display_name, start_time

    try:
        init_family_schema()
        write_heartbeat()
    except Exception as exc:
        logger.warning(
            "Family bus unavailable (%s) -- this bot runs fine without it, but "
            "ManagerBot will report it as down until the shared database is reachable.", exc,
        )
        return

    _enabled = True

    sf = _monitoring()
    if sf and hasattr(sf, "set_event_hook"):
        sf.set_event_hook(report_event_soon)

    report_event_soon("info", "startup", f"{display_name} started on {HOSTNAME}.")

    if app.job_queue is None:
        logger.warning("No job queue -- install python-telegram-bot[job-queue]. Family bus is off.")
        _enabled = False
        return

    app.job_queue.run_repeating(_send_heartbeat, interval=HEARTBEAT_SECONDS, first=HEARTBEAT_SECONDS)

    app.job_queue.run_repeating(
        _bus_tick, interval=BUS_POLL_ACTIVE_SECONDS, first=BUS_POLL_ACTIVE_SECONDS
    )

    mark_bus_active()

    app.job_queue.run_repeating(_housekeeping, interval=HOUSEKEEPING_SECONDS, first=60)
    logger.info(
        "Family bus on: heartbeat every %ss, commands polled (%ss busy / %ss idle), "
        "tidy-up every %ss.",
        HEARTBEAT_SECONDS, BUS_POLL_ACTIVE_SECONDS, BUS_POLL_IDLE_SECONDS, HOUSEKEEPING_SECONDS,
    )

# ─── module: lifecycle ───────────────────────────────────────────────────────
"""Surviving a redeploy without anybody noticing."""
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

ENABLED = os.environ.get("DEPLOY_SAFETY", "on").lower() not in ("off", "0", "false", "no")

LEASE_WAIT_SECONDS = float(os.environ.get("DEPLOY_LEASE_WAIT_SECONDS", "240"))

STATE_TTL_HOURS = int(os.environ.get("DEPLOY_STATE_TTL_HOURS", "12"))

PERSIST_SECONDS = float(os.environ.get("DEPLOY_PERSIST_SECONDS", "180"))

_app = None
_draining = False
_drain_started: float | None = None
_lease_conn = None
_bot_id: str | None = None

def _lease_key(bot_id: str) -> int:
    """A stable 64-bit key per bot. Signed, because that is what pg_advisory_lock takes."""
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
    """Block until this process is the only one polling for `bot_id`."""
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
    """`value` if it survives a JSON round trip unchanged, else None."""
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
    """Everything of one kind that is still young enough to mean something, deleting the rest on the way past -- the only pruning this table needs, and it happens once per process start."""
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
    """Delete everything this table holds for one person. Blocking; call through asyncio.to_thread."""
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
except ImportError:
    BasePersistence = object
    PersistenceInput = None

class PostgresPersistence(BasePersistence):
    """user_data and conversation states, in the bot's own Postgres schema."""

    def __init__(self):
        super().__init__(
            store_data=PersistenceInput(
                bot_data=False, chat_data=False, user_data=True, callback_data=False
            ),

            update_interval=max(PERSIST_SECONDS * 10, 600),
        )
        self._user_data: dict[int, dict] = {}
        self._dirty_users: set[int] = set()
        self._dropped_users: set[int] = set()
        self._conversations: dict[str, dict] = {}
        self._conversations_loaded = False

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

    async def flush(self) -> None:
        writes, deletes = [], [("user", str(u)) for u in self._dropped_users]
        for user_id in self._dirty_users:
            kept = _clean(self._user_data.get(user_id) or {})
            if kept:
                writes.append(("user", str(user_id), kept))
            else:

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

_in_flight: dict[int, tuple[int, str]] = {}
_next_ticket = 0

def is_draining() -> bool:
    """True once a stop signal has arrived."""
    return _draining

@asynccontextmanager
async def busy(chat_id: int, if_interrupted: str):
    """Mark a stretch of slow work, so a redeploy in the middle of it ends with an explanation rather than with silence."""
    global _next_ticket
    _next_ticket += 1
    ticket = _next_ticket
    _in_flight[ticket] = (chat_id, if_interrupted)
    try:
        yield
    finally:
        _in_flight.pop(ticket, None)

async def _tell_the_interrupted(bot) -> None:
    """One message each, to everyone who was mid-something."""
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

MAINTENANCE_KEY_PREFIX = "maintenance:"
WAITLIST_TABLE = "update_waitlist"

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

        return True, None

def refresh_maintenance(bot_id: str) -> bool:
    """Read the flag out of the shared database into this process. Blocking."""
    global _maintenance_on, _maintenance_until
    try:
        _maintenance_on, _maintenance_until = _read_maintenance(bot_id)
    except Exception:
        logger.debug("Could not read the maintenance flag", exc_info=True)
        return _maintenance_on
    return _maintenance_on

def begin_maintenance(bot_id: str, minutes: int) -> "datetime":
    """Blocking."""
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
    """Blocking."""
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
    """Whole minutes still promised, or None once the estimate has run out."""
    if not _maintenance_on or _maintenance_until is None:
        return None
    left = (_maintenance_until - datetime.now(timezone.utc)).total_seconds()
    if left <= 0:
        return None

    return max(1, -(-int(left) // 60))

def is_paused() -> bool:
    """True when nothing slow should be *started*: either a stop signal has already arrived, or the owner has announced an update."""
    return _draining or _maintenance_on

def hold_for_update(user_id: int, chat_id: int, bot_id: "str | None" = None) -> None:
    """Remember that this person was turned away, so /finishupdates can tell them it is over. Blocking; best-effort."""
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
    """Everyone waiting on this bot, as (user_id, chat_id), removed as they are handed over. Blocking."""
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
    """Who is mid-something right now, as (chat_id, the message they would get if it were interrupted) -- one entry per stretch of slow work."""
    return list(_in_flight.values())

def persistence():
    """Pass to ApplicationBuilder().persistence()."""
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
    """For ConversationHandler(persistent=..., name=...)."""
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

        logger.info("Stopped before startup finished; exiting.")
        os._exit(0)

def can_handle_signals() -> bool:
    return sys.platform != "win32" and hasattr(signal, "SIGTERM")

def polling_kwargs(**extra) -> dict:
    """Wrap each bot's run_polling() arguments."""
    if ENABLED and can_handle_signals():
        extra["stop_signals"] = ()
    return extra

async def _persist_job(context) -> None:
    """Collect what changed and write it out."""
    app = _app
    if app is None or app.persistence is None:
        return
    try:
        await app.update_persistence()
        await app.persistence.flush()
    except Exception:
        logger.debug("Periodic state save failed; the next pass retries", exc_info=True)

def install(app, bot_id: str) -> None:
    """One line in each bot's main(), next to family_link.attach()."""
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
    """Register as (part of) each bot's post_init, before it starts polling."""
    global _bot_id
    _bot_id = bot_id
    if not ENABLED:
        return
    await hold_the_lease(bot_id)

    try:
        await asyncio.to_thread(init_waitlist_table)
        if await asyncio.to_thread(refresh_maintenance, bot_id):
            logger.info("Still in maintenance -- not starting new long work yet.")
    except Exception:
        logger.debug("Could not read the maintenance flag at startup", exc_info=True)

    if not can_handle_signals():
        return

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
    """Register as the *first* thing in each bot's post_stop -- before flush_on_shutdown(), which closes the connection pool these writes go through."""
    if application.persistence is not None:
        try:
            await application.update_persistence()
            await application.persistence.flush()
            logger.info("In-progress state saved -- the next start picks it up.")
        except Exception:
            logger.warning("Could not save in-progress state on the way out.", exc_info=True)
    release_lease()

# ─── module: live_message ────────────────────────────────────────────────────
"""One bot message that keeps evolving -- for as long as it is still the last thing in the chat."""
from __future__ import annotations

import logging
from collections import OrderedDict

from telegram.error import BadRequest

logger = logging.getLogger(__name__)

MAX_TRACKED_CHATS = 2048

_last_incoming: "OrderedDict[int, int]" = OrderedDict()

_SEND_ONLY_KWARGS = frozenset({
    "do_quote", "reply_to_message_id", "allow_sending_without_reply",
    "reply_parameters", "disable_notification", "protect_content",
    "message_effect_id", "allow_paid_broadcast", "message_thread_id",
})

def note_incoming(chat_id: int, message_id: int) -> None:
    """Remember that the user has spoken in this chat."""
    current = _last_incoming.get(chat_id, 0)
    if message_id > current:
        _last_incoming[chat_id] = message_id
    _last_incoming.move_to_end(chat_id)
    while len(_last_incoming) > MAX_TRACKED_CHATS:
        _last_incoming.popitem(last=False)

def note_update(update) -> None:
    """Called for every update, from the same place each bot already counts active users (track_activity, group=-1, before any real handler)."""
    message = getattr(update, "message", None) or getattr(update, "edited_message", None)
    if message is not None:
        note_incoming(message.chat_id, message.message_id)

def bump(chat_id: int, message_id: int) -> None:
    """Same effect as the user having spoken: whatever live message this chat had is now buried and the next write to it starts fresh."""
    note_incoming(chat_id, message_id)

def _edit_kwargs(kwargs: dict) -> dict:
    return {k: v for k, v in kwargs.items() if k not in _SEND_ONLY_KWARGS}

class LiveMessage:
    """A handle on one evolving message."""

    __slots__ = ("chat_id", "message_id", "watermark")

    def __init__(self, chat_id: int, message_id: int, watermark: int | None = None):
        self.chat_id = chat_id
        self.message_id = message_id

        self.watermark = _last_incoming.get(chat_id, 0) if watermark is None else watermark

    def _still_last(self) -> bool:
        return self.message_id >= max(self.watermark, _last_incoming.get(self.chat_id, 0))

    @classmethod
    async def send(cls, bot, chat_id: int, text: str, **kwargs) -> "LiveMessage":
        message = await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return cls(chat_id, message.message_id)

    @classmethod
    async def reply_to(cls, message, text: str, **kwargs) -> "LiveMessage":
        """Start a live message as a reply to the one that triggered it -- the ordinary "user sent a video, bot says converting..." case."""
        sent = await message.reply_text(text, **kwargs)
        return cls(sent.chat_id, sent.message_id)

    @classmethod
    def adopt(cls, message) -> "LiveMessage":
        """Take over a message the bot already sent -- typically the one holding the button that was just tapped, so a menu keeps evolving in the same place instead of starting a new one below itself."""
        return cls(message.chat_id, message.message_id)

    def save(self) -> dict:
        """A plain dict for user_data."""
        return {"chat_id": self.chat_id, "message_id": self.message_id,
                "watermark": self.watermark}

    @classmethod
    def restore(cls, state) -> "LiveMessage | None":
        """The other half of save()."""
        if not isinstance(state, dict):
            return None
        try:
            chat_id = int(state["chat_id"])
            message_id = int(state["message_id"])
        except (KeyError, TypeError, ValueError):
            return None
        stored = state.get("watermark") or 0
        return cls(chat_id, message_id, max(int(stored), _last_incoming.get(chat_id, 0)))

    async def set(self, bot, text: str, **kwargs) -> "LiveMessage":
        """Show `text`, in place if this message is still the last one in the chat and as a new message otherwise."""
        if self._still_last():
            try:
                await bot.edit_message_text(
                    chat_id=self.chat_id, message_id=self.message_id, text=text,
                    **_edit_kwargs(kwargs),
                )
                self.watermark = _last_incoming.get(self.chat_id, 0)
                return self
            except BadRequest as exc:
                lowered = str(exc).lower()
                if "not modified" in lowered:

                    return self
                if "not found" not in lowered and "can't be edited" not in lowered:
                    logger.debug("Live message edit refused (%s); sending a new one", exc)
            except Exception:
                logger.debug("Live message edit failed; sending a new one", exc_info=True)

        try:
            sent = await bot.send_message(chat_id=self.chat_id, text=text, **kwargs)
        except Exception:
            logger.debug("Could not send a live message", exc_info=True)
            return self
        self.message_id = sent.message_id
        self.watermark = _last_incoming.get(self.chat_id, 0)
        return self

    async def finish(self, bot, text: str, **kwargs) -> None:
        """The last thing this message will ever say."""
        await self.set(bot, text, **kwargs)

    async def delete(self, bot) -> None:
        """Take it away entirely -- for a progress message whose result arrives as a file or a photo of its own, where leaving "Downloading ..." above the thing it was waiting for reads as a second, stuck request."""
        try:
            await bot.delete_message(chat_id=self.chat_id, message_id=self.message_id)
        except Exception:
            logger.debug("Could not delete a live message", exc_info=True)

async def edit_in_place(message, bot, text: str, **kwargs) -> "LiveMessage":
    """Rewrite one of the bot's own messages -- typically the one holding the button that was just tapped -- or send a new one if the user has said anything since."""
    return await LiveMessage.adopt(message).set(bot, text, **kwargs)

DEFAULT_KEY = "live_message"

async def show(context, chat_id: int, text: str, key: str = DEFAULT_KEY, **kwargs) -> "LiveMessage":
    """Write this user's live message, creating it on first call."""
    live = LiveMessage.restore(context.user_data.get(key))
    if live is None:
        live = await LiveMessage.send(context.bot, chat_id, text, **kwargs)
    else:
        await live.set(context.bot, text, **kwargs)
    context.user_data[key] = live.save()
    return live

def drop(context, key: str = DEFAULT_KEY) -> None:
    context.user_data.pop(key, None)

# ─── module: problems ────────────────────────────────────────────────────────
"""Every problem a person can run into in the family's bots, by code."""
from __future__ import annotations

import re
import secrets
from collections import namedtuple

Problem = namedtuple("Problem", "bot title meaning causes check")

MARK = "🆔 "
CODE_RE = re.compile(r"^[A-Z]{2}(?:-[A-Z0-9]+)+$")
INCIDENT_RE = re.compile(r"^[A-HJ-NP-Z2-9]{6}$")
_INCIDENT_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_AT_END = re.compile(r"\n\n🆔 ([A-Z]{2}(?:-[A-Z0-9]+)+)(?:</[a-z]+>)*\s*$")

EVERY_PUBLIC_BOT = "every public bot"

PROBLEMS = {

    "FM-CRASH": Problem(
        EVERY_PUBLIC_BOT, "The bot crashed while handling a message",
        "A handler raised an exception nothing caught. The request was not done; the person was told so "
        "and offered a report.",
        "A bug in that handler; the shared database unreachable or timing out; Telegram rejecting a call in "
        "a way the code does not expect (a changed API, editing a message that was deleted).",
        "Search the bot's log for the incident id: the traceback is logged beside it. /events and the crash "
        "alert name the exception type; /status shows whether errors are piling up."),
    "FM-FLOOD": Problem(
        EVERY_PUBLIC_BOT, "Too many updates from one person",
        "One person sent more than FLOOD_UPDATES_PER_MINUTE updates (40 by default) inside a minute; the rest "
        "were ignored until the window cleared.",
        "Tapping buttons very fast, a client resending, forwarding a big selection outside /export, or a script.",
        "Usually nothing. If ordinary use trips it, raise FLOOD_UPDATES_PER_MINUTE on that bot."),
    "FM-DONATE-CURRENCY": Problem(
        EVERY_PUBLIC_BOT, "Unknown currency in /donate or /recharge",
        "The command named a currency the bot does not offer.",
        "A typo, or a currency that was never configured.",
        "Nothing, unless people keep asking for a currency that should be added to FIAT_CURRENCIES."),
    "FM-DONATE-UNAVAILABLE": Problem(
        EVERY_PUBLIC_BOT, "Currency offered but not set up",
        "The currency is known, but its payment provider token is missing, so no invoice can be made.",
        "The provider token environment variable is not set on this bot.",
        "Set that currency's provider token, or stop offering it."),
    "FM-DONATE-AMOUNT": Problem(
        EVERY_PUBLIC_BOT, "Invalid payment amount",
        "The amount was not a positive whole number, or a button carried an amount the bot never offered.",
        "A typo in /donate or /recharge; an old or tampered button.",
        "Nothing, unless it happens with the bot's own buttons -- then the offered amounts and the handler "
        "disagree (DONATE_STAR_OPTIONS)."),
    "FM-DONATE-TOO-MANY": Problem(
        EVERY_PUBLIC_BOT, "Payment above the per-payment limit",
        "The Stars amount was above MAX_DONATION_STARS.",
        "A large custom amount.",
        "Raise MAX_DONATION_STARS if larger single payments are wanted."),
    "FM-DONATE-RANGE": Problem(
        EVERY_PUBLIC_BOT, "Card payment outside the allowed range",
        "A fiat amount was below that currency's minimum or above its maximum.",
        "An amount outside the provider's limits.",
        "Correct the currency's limits in FIAT_CURRENCIES if they are wrong."),
    "FM-INVOICE": Problem(
        EVERY_PUBLIC_BOT, "Telegram refused to create an invoice",
        "send_invoice failed. The payment row was marked failed and nothing was charged.",
        "An amount Telegram rejects, a provider token that stopped working, or Telegram having a problem.",
        "The error Telegram returned is in the message and in the log at that time; check the provider token "
        "and the amount."),
    "FM-ERASE": Problem(
        EVERY_PUBLIC_BOT, "/deletemydata failed",
        "Erasing the person's data raised an error, so nothing was erased and they were asked to try again.",
        "The database unreachable, or a table the erase does not expect.",
        "The traceback is in the log; tests/erase_scenarios.py reproduces erasing against a real database."),
    "FM-UPDATING": Problem(
        EVERY_PUBLIC_BOT, "The bot is paused for an update",
        "New work was refused because an update is about to be deployed (/pause in ManagerBot).",
        "An announced update window, or a pause that was never lifted.",
        "If no update is under way, lift it with /finishupdates in ManagerBot."),
    "FM-UNKNOWN-COMMAND": Problem(
        EVERY_PUBLIC_BOT, "Unknown command",
        "A slash command this bot does not have.",
        "A typo, a command from an older version, or one that belongs to another bot.",
        "Nothing, unless an old command should be kept working as an alias."),

    "CV-NO-EXTENSION": Problem(
        "ConvertBot", "File name without a usable extension",
        "The format could not be told from the file's name, so nothing was downloaded or charged.",
        "A file sent without an extension, or with one the bot does not recognise.",
        "Nothing, unless a common extension is missing from formats.ALIASES."),
    "CV-TG-LIMIT": Problem(
        "ConvertBot", "File larger than a bot may download",
        "Telegram declared the file over 20 MB, and nothing on this bot lifts the cloud Bot API's 20 MB download "
        "limit.",
        "A large file, on a bot without CBOT_API_ID and CBOT_API_HASH (or a local Bot API server).",
        "Set CBOT_API_ID and CBOT_API_HASH (my.telegram.org) so files over 20 MB come over MTProto -- "
        "big_files.py. The startup log line 'Largest upload' says which is in force."),
    "CV-GROUP-LIMIT": Problem(
        "ConvertBot", "Big file sent in a group",
        "A file over 20 MB was sent in a group. Files past the Bot API's limit come over MTProto, which this bot "
        "uses in private chats only, so the person was asked to send it privately.",
        "Using the bot in a group.",
        "Nothing; it is by design (big_files.usable)."),
    "CV-BIG-UNAVAILABLE": Problem(
        "ConvertBot", "The route for files over 20 MB is down",
        "A file over 20 MB was sent, and the MTProto connection that fetches those could not be made or used. "
        "Nothing was downloaded or charged. Files under 20 MB were unaffected.",
        "Telegram refusing the login (a wrong CBOT_API_ID or CBOT_API_HASH, a revoked token, a flood wait after "
        "too many logins), or the host's network. After a failure every big file is refused for five minutes "
        "rather than each waiting out a timeout.",
        "The bot's log: 'MTProto connection for big files failed' with Telegram's error beside it."),
    "CV-DOWNLOAD": Problem(
        "ConvertBot", "Downloading the file from Telegram failed",
        "get_file or the download raised, so nothing was converted and nothing charged.",
        "A network error, Telegram timing out, or the file no longer being available.",
        "The error text is in the message and the log; repeated failures point at the host's network."),
    "CV-UNSUPPORTED": Problem(
        "ConvertBot", "Format not converted",
        "The source format, or the target that was chosen, is not one this server can convert.",
        "An unsupported file; an old menu offering a format no longer available; a converter missing on this host.",
        "/formats on the bot; the startup log line 'Converters available' lists what was found."),
    "CV-TOO-BIG": Problem(
        "ConvertBot", "File over ConvertBot's size limit",
        "The file, or an album's files together, are larger than MAX_FILE_MB, so it was refused before "
        "anything was charged.",
        "A large file, or a large album.",
        "CONVERT_MAX_FILE_MB (100 by default when files over 20 MB can be fetched at all). Raise it only once "
        "the host has shown it converts that much inside CONVERT_TIME_LIMIT_SECONDS."),
    "CV-NO-TARGETS": Problem(
        "ConvertBot", "Nothing this file can become",
        "The format is readable, but no target format is available for it on this server.",
        "A converter library or an ffmpeg encoder missing on the host.",
        "The startup log line 'Converters available'; requirements.txt and nixpacks.toml."),
    "CV-NOTHING-SENDABLE": Problem(
        "ConvertBot", "Every result would be too big to send",
        "For a picture this large, every offered format would come out over what the bot may send back (50 MB, "
        "or more where results can go over MTProto), so nothing was offered or charged.",
        "A very high-resolution image, in a group or on a bot without CBOT_API_ID.",
        "Nothing; CBOT_API_ID and CBOT_API_HASH raise the send limit in private chats."),
    "CV-MEGAPIXELS": Problem(
        "ConvertBot", "Picture over the megapixel limit",
        "The image is larger than CONVERT_MAX_MEGAPIXELS, above which one decode needs more memory than the "
        "container has. Nothing was charged.",
        "A very high-resolution image.",
        "Raise CONVERT_MAX_MEGAPIXELS only together with the container's memory."),
    "CV-FORMAT-TOO-BIG": Problem(
        "ConvertBot", "That format would be too big to send",
        "A format was tapped whose result is estimated over the send limit, usually from an old menu.",
        "An old menu, or a size estimate that changed.",
        "jobs.unsendable_targets and LOSSLESS_BYTES_PER_PIXEL in jobs.py."),
    "CV-STORAGE-USER": Problem(
        "ConvertBot", "Person over their temporary storage share",
        "Files waiting, or kept for more formats, already use CONVERT_USER_STORAGE_MB for this person.",
        "Several large files kept at once.",
        "Nothing, unless the share is too small for real albums."),
    "CV-STORAGE-FULL": Problem(
        "ConvertBot", "Server short of temporary space",
        "Taking the file would leave less than CONVERT_MIN_FREE_MB free, or push everyone's files over "
        "CONVERT_STORAGE_MB.",
        "Many large conversions at once, or files left behind that the sweep has not removed yet.",
        "Disk use on the container; the sweep lines in the log ('Swept ... abandoned upload(s)')."),
    "CV-QUEUE-FULL": Problem(
        "ConvertBot", "Too many conversions waiting",
        "The person already has CONVERT_MAX_QUEUED_PER_USER conversions queued or running.",
        "Many formats chosen quickly.",
        "Nothing, unless the limit is too low for real use."),
    "CV-EXPIRED": Problem(
        "ConvertBot", "The file is no longer waiting",
        "A format was chosen for a file whose pending state is gone.",
        "More than CONVERT_PENDING_TTL_SECONDS since the file was sent, a restart, or the file already converted.",
        "Nothing, unless it happens within minutes of sending -- then pending state is being lost."),
    "CV-JOB-GONE": Problem(
        "ConvertBot", "That conversion has already finished",
        "Stop was tapped for a conversion that had already ended.",
        "Tapping Stop just as it finished.",
        "Nothing."),
    "CV-NO-CREDIT": Problem(
        "ConvertBot", "Balance did not cover the conversion when it started",
        "When the conversion reached the front of the queue the balance was below its price, so it did not run "
        "and nothing was charged.",
        "Credit spent on another conversion meanwhile, or bonus credit that expired while it waited.",
        "/balance <id> in ManagerBot shows the ledger if the person disputes it."),
    "CV-UNKNOWN-ORDER": Problem(
        "ConvertBot", "Payment for an order the bot does not know",
        "A pre-checkout query carried a payload that is neither a conversion nor a top-up; it was declined "
        "before anything was charged.",
        "A very old invoice, or an invoice made by another deployment of the bot.",
        "The payload is in the log; nothing was charged."),
    "CV-MIXED-BATCH": Problem(
        "ConvertBot", "Album of different formats",
        "Files sent together had different formats, which one conversion cannot take.",
        "A photo and a video in one album.",
        "Nothing."),
    "CV-UNRECOGNIZED": Problem(
        "ConvertBot", "Not something ConvertBot can use",
        "A message that is neither a file nor a format name.",
        "Text, a sticker or other media sent to ConvertBot.",
        "Nothing."),
    "CV-REFUSED": Problem(
        "ConvertBot", "The converter could not convert this file",
        "The worker raised ConversionError: the file could not be read or converted as asked. Its ⚡ went back "
        "to the balance.",
        "A damaged or unusual file, or something the converter does not support (an encrypted PDF, an unusual "
        "codec).",
        "The converter's own message is in the log beside the incident id."),
    "CV-TIMEOUT": Problem(
        "ConvertBot", "Conversion ran past its time limit",
        "The worker was still running at CONVERT_TIME_LIMIT_SECONDS (60 s for a free conversion) and was killed. "
        "Its ⚡ went back to the balance and the owner was alerted.",
        "A very large or complex file (a long video, many pages), a slow encoder such as AVIF, or a host short "
        "of CPU.",
        "The owner alert gives size, formats and run time; compare with /usage for CPU pressure at that time."),
    "CV-TOO-SLOW": Problem(
        "ConvertBot", "Stopped early: would not finish in time",
        "A conversion reported its progress for PROJECT_AFTER_S and was on course to take longer than its "
        "time limit (by more than PROJECT_MARGIN), so it was stopped then rather than at the limit. Its ⚡ went "
        "back to the balance, and the person was told roughly how long it would have taken.",
        "A long or high-resolution video (4K, 60 fps, HDR) on a small host, or a slow encoder such as AV1 or AVIF.",
        "Nothing, if it is rare. If it is common, the host is short of CPU for what people send: /usage, "
        "FFMPEG_THREADS, or CONVERT_TIME_LIMIT_SECONDS with the pricing test run again."),
    "CV-CRASH": Problem(
        "ConvertBot", "The conversion worker crashed",
        "The worker process died without a result -- most often killed for memory. Its ⚡ went back to the "
        "balance and the owner was alerted.",
        "An out-of-memory kill on a very large image, or a crash inside a native decoder.",
        "The log line beside the incident id has the exit code (-9 or 137 means killed); /usage shows memory."),
    "CV-OUTPUT-TOO-BIG": Problem(
        "ConvertBot", "The result was over its send limit",
        "The conversion finished, but the file is larger than this job may send back: 50 MB, or where results "
        "go over MTProto, twice what the job was priced on (jobs.send_limit_for). Its ⚡ went back to the "
        "balance and the owner was alerted.",
        "A lossless or high-resolution target (PNG, TIFF, GIF) for a large input.",
        "If one format keeps doing this, add it to the unsendable estimates in jobs.py."),
    "CV-SEND-FAILED": Problem(
        "ConvertBot", "Sending the result failed",
        "The file was converted but uploading it to the person failed. Its ⚡ went back to the balance and the "
        "owner was alerted.",
        "Telegram rejecting the upload, a network error or timeout, or the person having blocked the bot.",
        "The exception type and text are in the owner alert and the log."),
    "CV-RESTARTED": Problem(
        "ConvertBot", "The bot restarted during the conversion",
        "The process stopped while the conversion was running. Its ⚡ went back to the balance.",
        "A redeploy, a manual restart, or the container being killed.",
        "The deploy history at that time, and /events for the restart."),

    "DL-QUOTA-HOUR": Problem(
        "DownloaderBot", "Hourly download limit reached",
        "The person has used their downloads for the last hour.",
        "Heavy use.",
        "The hourly allowance settings; people who have donated get a higher one."),
    "DL-QUOTA-DAY": Problem(
        "DownloaderBot", "Daily download limit reached",
        "The person has used their downloads for the day.",
        "Heavy use.",
        "The daily allowance settings; people who have donated get a higher one."),
    "DL-QUEUE-FULL": Problem(
        "DownloaderBot", "Too many links waiting",
        "The person already has DBOT_MAX_PENDING_PER_USER links in progress.",
        "Many links sent at once.",
        "Nothing, unless the limit is too low."),
    "DL-NO-SPACE": Problem(
        "DownloaderBot", "Server short of temporary space",
        "Free disk was below DBOT_MIN_FREE_MB, so the download did not start.",
        "Several large downloads at once, or files left behind.",
        "Disk use on the container."),
    "DL-DELIVERY": Problem(
        "DownloaderBot", "Sending the downloaded file failed",
        "The media was fetched, but uploading it to Telegram failed.",
        "A file over Telegram's limit after all, a network error, or Telegram rejecting the media.",
        "The provider and exception are in the log ('Delivering ... failed')."),
    "DL-BLOCKED": Problem(
        "DownloaderBot", "The site refused every route",
        "Every provider was refused by the platform: blocked, rate limited, or asked to log in.",
        "The platform limiting the server's IP, expired cookies, or a change on the platform.",
        "/providers and /probe in ManagerBot show which routes are failing."),
    "DL-NOT-FOUND": Problem(
        "DownloaderBot", "Post not found",
        "The platform says the post does not exist or is not public.",
        "A deleted post, a private account, or a mistyped link.",
        "Nothing, unless public posts come back as missing -- then a resolver is misreading the page."),
    "DL-TOO-BIG": Problem(
        "DownloaderBot", "Media over what Telegram allows",
        "The media is larger than a bot may send.",
        "A long, high-quality video.",
        "Nothing on the cloud API."),
    "DL-LARGE-OFF": Problem(
        "DownloaderBot", "Over the free ceiling, large files off",
        "The media is over DBOT_MAX_DOWNLOAD_MB, and this person has not switched on large files, which cost "
        "credit. They were told the price and offered the switch; nothing past the ceiling was fetched.",
        "A long or high-quality video.",
        "Nothing; it is by design (large_files.py). Default off, on the owner's instruction."),
    "DL-LARGE-PRIVATE": Problem(
        "DownloaderBot", "A large file asked for in a group",
        "A file over the free ceiling was asked for in a group; large files go over MTProto, which this bot "
        "uses in private chats only, so the person was sent to a private chat.",
        "Using the bot in a group.",
        "Nothing; it is by design (big_files.usable)."),
    "DL-LARGE-NO-CREDIT": Problem(
        "DownloaderBot", "Large files on, no credit for one",
        "A file over the free ceiling, large files switched on, and a balance under the least one costs "
        "(large_files.first_price()). Nothing was fetched or charged.",
        "An empty balance.",
        "Nothing; the person was told to top up."),
    "DL-LARGE-TOO-BIG": Problem(
        "DownloaderBot", "Over even the large-file ceiling",
        "The media is over DBOT_LARGE_MAX_MB -- 2000 MB, Telegram's own limit for a bot, unless it was set "
        "lower. Nothing was charged.",
        "A very long, high-quality video.",
        "Nothing, unless DBOT_LARGE_MAX_MB was set below 2000."),
    "DL-LARGE-SHORT": Problem(
        "DownloaderBot", "A large file cost more than the balance",
        "The large file arrived, its price was worked out from its size, and the balance did not cover it. "
        "Nothing was charged and the file was deleted.",
        "A balance that covered the least a large file costs, but not this one.",
        "Nothing; the person was told the price and to top up."),
    "DL-LARGE-SEND": Problem(
        "DownloaderBot", "A large file was charged for and could not be sent",
        "A large file was fetched and charged for, and sending it over MTProto failed. The credit went back.",
        "The MTProto route failing mid-send (a flood wait, the connection dropping), or a file Telegram refused.",
        "The traceback in the log beside the incident id; big_files' own warning line if the route was down."),
    "DL-ALL-ROUTES": Problem(
        "DownloaderBot", "Every download route failed",
        "Every provider in the chain failed, for a reason other than blocked, missing or too big.",
        "Provider outages, a platform change that broke the resolvers, or network trouble.",
        "/providers for failure counts; the per-provider log lines; tests/test_resolvers.py."),
    "DL-REDDIT": Problem(
        "DownloaderBot", "Reddit post could not be fetched",
        "Reading the Reddit post's data failed.",
        "Reddit rate limiting, or a changed response.",
        "The error text in the message and the log."),
    "DL-TWITTER-CARD": Problem(
        "DownloaderBot", "X/Twitter post content unavailable",
        "The post's content could not be fetched, so only the link was sent back.",
        "X blocking the routes, or a changed page.",
        "/providers for the X routes."),
    "DL-UNRECOGNIZED": Problem(
        "DownloaderBot", "Not a supported link",
        "The message was not a link from a supported platform.",
        "Text, or a link from an unsupported platform.",
        "Nothing, unless a supported platform's link format changed (platforms.detect_platform)."),
    "DL-BUTTON-EXPIRED": Problem(
        "DownloaderBot", "Re-send button too old",
        "The compressed/uncompressed button refers to a download that is no longer remembered.",
        "An old message, or a restart.",
        "Nothing."),

    "ST-WHOMADE-UNKNOWN": Problem(
        "StickerBot", "Pack not made through this bot",
        "/whomade found no record of the pack.",
        "A pack made elsewhere, or a mistyped name or link.",
        "Nothing."),
    "ST-COEDIT-LINK": Problem(
        "StickerBot", "Co-editing link not valid",
        "The link's token matches no pack.",
        "The owner reset the link, or it was mistyped.",
        "Nothing."),
    "ST-COEDIT-GONE": Problem(
        "StickerBot", "Pack no longer exists",
        "The pack a co-editing link points at has no owner on record.",
        "The pack was deleted.",
        "Nothing."),
    "ST-NOT-YOURS": Problem(
        "StickerBot", "Not the person's pack",
        "A pack button was tapped by someone who does not own the pack.",
        "A forwarded menu, or an old button.",
        "Nothing."),
    "ST-OWNER-ONLY": Problem(
        "StickerBot", "Only the pack's owner can do that",
        "Renaming, co-editing settings and deleting belong to the pack's owner.",
        "A co-editor tapping an owner's button.",
        "Nothing."),
    "ST-RENAME-STATE": Problem(
        "StickerBot", "Rename lost track of the pack",
        "A new name arrived, but the pack it was meant for is no longer known.",
        "A restart, or a long gap between tapping Rename and sending the name.",
        "Nothing, unless it is frequent -- then state is being lost."),
    "ST-RENAME-FAILED": Problem(
        "StickerBot", "Telegram refused the rename",
        "set_sticker_set_title raised.",
        "A title Telegram rejects, the pack deleted meanwhile, or a network error.",
        "The error text is in the message and the log."),
    "ST-DELETE-FAILED": Problem(
        "StickerBot", "Telegram refused to delete the pack",
        "delete_sticker_set raised.",
        "The pack already deleted, or a network error.",
        "The error text is in the message and the log."),
    "ST-TITLE-EMPTY": Problem(
        "StickerBot", "Empty pack name",
        "The name sent was empty once trimmed.",
        "Whitespace, or an empty message.",
        "Nothing."),
    "ST-REMOVE-FAILED": Problem(
        "StickerBot", "Removing a sticker failed",
        "delete_sticker_from_set raised.",
        "The sticker already gone, or a network error.",
        "The error text is in the message and the log."),
    "ST-IMAGE": Problem(
        "StickerBot", "Picture could not be made into a sticker",
        "Processing the image raised.",
        "A damaged or unusual image file.",
        "The error text in the message and the log."),
    "ST-VIDEO-CONVERT": Problem(
        "StickerBot", "Video could not be made into a sticker",
        "The video could not be encoded into a sticker Telegram accepts.",
        "A clip too long or too detailed to fit 256 KB, an empty file, or ffmpeg missing on the host.",
        "The reason is the first line of the message; the startup log says whether ffmpeg was found."),
    "ST-VIDEO-FAILED": Problem(
        "StickerBot", "Video conversion crashed",
        "An unexpected error while converting a video.",
        "A bug, or an unusual file.",
        "The traceback in the log ('Video conversion failed')."),
    "ST-ANIMATED": Problem(
        "StickerBot", "Animated (Lottie) sticker not supported",
        "A .tgs animated sticker was sent, which the bot cannot copy.",
        "An animated sticker.",
        "Nothing."),
    "ST-IMPORT-SOURCE": Problem(
        "StickerBot", "Not a sticker pack name or link",
        "/import was given something that is neither a pack name nor a t.me/addstickers link.",
        "A typo.",
        "Nothing."),
    "ST-IMPORT": Problem(
        "StickerBot", "Import could not read the pack",
        "Importing failed: the Telegram pack was not found, or the WhatsApp archive was not a valid .zip or had "
        "no usable images.",
        "A private or mistyped pack name, or a damaged or unexpected archive.",
        "The message says which; nothing to do unless valid packs fail (import_utils.py)."),
    "ST-TG-TIMEOUT": Problem(
        "StickerBot", "Telegram did not confirm in time",
        "Adding a sticker timed out; it may have been added anyway.",
        "A slow upload, most often a video sticker.",
        "Nothing, unless constant -- then the host's network."),
    "ST-TG-BAD-NAME": Problem(
        "StickerBot", "Telegram rejected the pack's internal name",
        "The generated set name was invalid.",
        "A title starting with a digit or a symbol.",
        "Nothing; the message explains the workaround."),
    "ST-TG-NAME-TAKEN": Problem(
        "StickerBot", "Pack name already taken",
        "The generated set name collided with an existing pack.",
        "Chance.",
        "Nothing."),
    "ST-TG-PACK-FULL": Problem(
        "StickerBot", "Pack is full",
        "The pack reached Telegram's sticker limit (120).",
        "A full pack.",
        "Nothing."),
    "ST-TG-BAD-FORMAT": Problem(
        "StickerBot", "Telegram rejected the sticker file",
        "The prepared file was not accepted for this pack.",
        "A format mismatch, such as a video sticker into an older static pack.",
        "The Telegram error text in the log."),
    "ST-TG-REJECTED": Problem(
        "StickerBot", "Telegram rejected the sticker",
        "Adding a sticker failed with an error the bot has no specific explanation for.",
        "Any other Telegram API error.",
        "The Telegram error text is in the message and the log."),
    "ST-UNRECOGNIZED": Problem(
        "StickerBot", "Message not understood",
        "Something StickerBot has no use for outside a pack session.",
        "Text or media sent without starting a pack.",
        "Nothing."),
    "ST-NOTHING-ADDED": Problem(
        "StickerBot", "/done with nothing added",
        "/done was sent before any sticker was added.",
        "Finishing too early.",
        "Nothing."),
    "ST-NO-STICKER": Problem(
        "StickerBot", "Emoji with no sticker to tag",
        "An emoji arrived before any sticker was added in this session.",
        "Sending the emoji first.",
        "Nothing."),
    "ST-RETAG": Problem(
        "StickerBot", "Changing the emoji failed",
        "set_sticker_emoji_list raised.",
        "The sticker removed meanwhile, or a network error.",
        "The error text is in the message and the log."),

    "AN-LINK-INVALID": Problem(
        "AnonBot", "Inbox link not valid",
        "The link's token matches no inbox.",
        "The owner reset the link, or it was mistyped.",
        "Nothing."),
    "AN-LINK-BLOCKED": Problem(
        "AnonBot", "Blocked by the inbox owner",
        "The person who opened the link is on the owner's block list.",
        "The owner blocked them.",
        "Nothing."),
    "AN-LINK-PAUSED": Problem(
        "AnonBot", "Inbox paused",
        "The owner has paused new conversations.",
        "/pause by the owner.",
        "Nothing."),
    "AN-INBOX-GONE": Problem(
        "AnonBot", "Inbox no longer exists",
        "The owner's inbox is gone, usually through /deletemydata.",
        "The owner erased their data.",
        "Nothing."),
    "AN-SENDER-BLOCKED": Problem(
        "AnonBot", "Message not delivered: blocked",
        "The guest is blocked by the owner, so the message was not relayed.",
        "The owner blocked this guest.",
        "Nothing."),
    "AN-NOT-STARTED": Problem(
        "AnonBot", "Recipient has not started the bot",
        "Telegram refused the delivery (Forbidden).",
        "The recipient never started the bot, or has blocked it.",
        "Nothing."),
    "AN-DELIVERY": Problem(
        "AnonBot", "Relaying the message failed",
        "Telegram rejected the copy for another reason (BadRequest).",
        "An unsupported message type, an oversized caption, or a changed API.",
        "The error text is in the message and the log ('Failed relaying follower message')."),
    "AN-REPLY-NO-MATCH": Problem(
        "AnonBot", "Reply resolved to someone else's conversation",
        "A reply matched a conversation the sender does not own; it was not sent.",
        "Should not happen -- relay rows are written per chat.",
        "The anon_relay rows for that chat; tests/anon_scenarios.py group P checks the pairing."),
    "AN-NEEDS-REPLY": Problem(
        "AnonBot", "Message did not say which conversation",
        "A message that was not a reply arrived while conversations are open.",
        "Typing without swiping to reply.",
        "Nothing."),
    "AN-OPENING-NEEDS-REPLY": Problem(
        "AnonBot", "First message has to answer the opening line",
        "The conversation a link tap opened has not started, and something else arrived in between.",
        "A message from another conversation arriving after the tap.",
        "Nothing."),
    "AN-AMBIGUOUS": Problem(
        "AnonBot", "Several conversations open, none named",
        "A message without a reply while several conversations are open.",
        "Typing without replying.",
        "Nothing."),
    "AN-REPLY-BLOCKED": Problem(
        "AnonBot", "Reply not delivered: guest unavailable",
        "Telegram refused the owner's reply (Forbidden).",
        "The guest blocked the bot or deleted their account.",
        "Nothing."),
    "AN-REPLY-FAILED": Problem(
        "AnonBot", "Relaying the reply failed",
        "Telegram rejected the owner's reply for another reason.",
        "An unsupported message type or an oversized caption.",
        "The error text is in the message and the log ('Failed relaying owner reply')."),
    "AN-REPLY-STALE": Problem(
        "AnonBot", "Reply to a message with no record",
        "The replied-to message is in no tracked conversation.",
        "A reply to the person's own message, to a bot notice, or to a message older than RELAY_RETENTION_DAYS.",
        "Nothing."),
    "AN-TOO-FAST": Problem(
        "AnonBot", "Messages sent too fast",
        "More than ABOT_MSGS_PER_MINUTE messages inside a minute.",
        "Rapid sending, or a script.",
        "Raise ABOT_MSGS_PER_MINUTE if ordinary use trips it."),
    "AN-EDIT-NOT-RELAYED": Problem(
        "AnonBot", "Edits are not relayed",
        "An already relayed message was edited; the other side still has the original.",
        "Editing after sending.",
        "Nothing."),
    "AN-CONV-GONE": Problem(
        "AnonBot", "Conversation no longer on record",
        "A conversation button refers to a conversation that was not found or is not the person's.",
        "An old button, or /deletemydata.",
        "Nothing."),
    "AN-NOT-YOURS": Problem(
        "AnonBot", "Not the person's conversation",
        "A button was tapped for a conversation the tapper is not part of.",
        "A forwarded message with buttons.",
        "Nothing."),
    "AN-NO-ANCHOR": Problem(
        "AnonBot", "Conversation start no longer available",
        "Jumping to the start is impossible because the records of its messages were pruned.",
        "More than RELAY_RETENTION_DAYS of silence in the conversation.",
        "Nothing."),
    "AN-WHICH-UNKNOWN": Problem(
        "AnonBot", "Message belongs to no open conversation",
        "/which or /archive was used on a message with no conversation.",
        "The person's own old message, or an archived conversation.",
        "Nothing."),
    "AN-ARCHIVE-OWNER-ONLY": Problem(
        "AnonBot", "Only the inbox owner archives",
        "A guest tried to archive a conversation.",
        "A guest using the owner's command.",
        "Nothing."),
    "AN-EXPORT-FAILED": Problem(
        "AnonBot", "Building the document failed",
        "Reading the conversation or rendering the page failed; nothing was sent and nothing was kept.",
        "A bug, the database failing during the relay lookup, or Telegram refusing every forward.",
        "The traceback beside 'Could not build a transcript' in the log."),
    "AN-EXPORT-GONE": Problem(
        "AnonBot", "That conversation is no longer on record",
        "A conversation chosen for export had no relay rows left by the time the button was tapped.",
        "prune_old_data clearing a long-silent conversation, or /cancel removing it, between the "
        "menu being drawn and the button being tapped.",
        "Nothing. RELAY_RETENTION_DAYS is what decides how long a conversation stays exportable."),
    "AN-EXPORT-NOTHING": Problem(
        "AnonBot", "Nothing to export",
        "/export was sent by somebody with no conversation on record in this chat.",
        "Never having used an inbox link in either direction, or every conversation being older "
        "than RELAY_RETENTION_DAYS.",
        "Nothing."),
    "AN-UNADDRESSED": Problem(
        "AnonBot", "Message with nowhere to go",
        "A message from somebody with no inbox and no open conversation.",
        "Writing to the bot without having tapped a link.",
        "Nothing."),
}

KEYS = {
    "shared": {
        "crash_notice": "FM-CRASH",
        "flood_wait": "FM-FLOOD",
        "donate_unknown_currency": "FM-DONATE-CURRENCY",
        "donate_currency_not_configured": "FM-DONATE-UNAVAILABLE",
        "donate_invalid_amount": "FM-DONATE-AMOUNT",
        "donate_invalid_amount_retry": "FM-DONATE-AMOUNT",
        "donate_too_many_stars": "FM-DONATE-TOO-MANY",
        "donate_out_of_range": "FM-DONATE-RANGE",
        "donate_invoice_error": "FM-INVOICE",
        "delete_data_failed": "FM-ERASE",
        "update_soon_try_later": "FM-UPDATING",
        "update_soon_try_later_soon": "FM-UPDATING",
        "unknown_command": "FM-UNKNOWN-COMMAND",
    },
    "convert_bot": {
        "unknown_extension": "CV-NO-EXTENSION",
        "file_too_large_download": "CV-TG-LIMIT",
        "file_too_large_in_group": "CV-GROUP-LIMIT",
        "big_download_unavailable": "CV-BIG-UNAVAILABLE",
        "download_failed": "CV-DOWNLOAD",
        "unsupported_format": "CV-UNSUPPORTED",
        "file_too_large_convert": "CV-TOO-BIG",
        "no_target_formats": "CV-NO-TARGETS",
        "nothing_sendable": "CV-NOTHING-SENDABLE",
        "too_many_megapixels": "CV-MEGAPIXELS",
        "too_big_to_send_alert": "CV-FORMAT-TOO-BIG",
        "storage_full_user": "CV-STORAGE-USER",
        "storage_full_global": "CV-STORAGE-FULL",
        "queue_full": "CV-QUEUE-FULL",
        "conversion_expired": "CV-EXPIRED",
        "job_not_running": "CV-JOB-GONE",
        "job_no_credit": "CV-NO-CREDIT",
        "unknown_order": "CV-UNKNOWN-ORDER",
        "batch_mixed_formats": "CV-MIXED-BATCH",
        "unrecognized_message": "CV-UNRECOGNIZED",
    },
    "downloader_bot": {
        "download_queue_full": "DL-QUEUE-FULL",
        "download_short_on_space": "DL-NO-SPACE",
        "download_failed": "DL-DELIVERY",
        "download_blocked": "DL-BLOCKED",
        "download_missing": "DL-NOT-FOUND",
        "download_too_big": "DL-TOO-BIG",
        "download_all_routes_failed": "DL-ALL-ROUTES",
        "reddit_fetch_failed": "DL-REDDIT",
        "twitter_fetch_failed_link": "DL-TWITTER-CARD",
        "unrecognized_message": "DL-UNRECOGNIZED",
        "redeliver_expired": "DL-BUTTON-EXPIRED",
        "large_files_off": "DL-LARGE-OFF",
        "large_files_private_only": "DL-LARGE-PRIVATE",
        "large_files_no_credit": "DL-LARGE-NO-CREDIT",
        "large_files_too_big": "DL-LARGE-TOO-BIG",
        "large_files_short": "DL-LARGE-SHORT",
        "large_files_send_failed": "DL-LARGE-SEND",
    },
    "sticker_bot": {
        "whomade_not_found": "ST-WHOMADE-UNKNOWN",
        "coedit_link_invalid": "ST-COEDIT-LINK",
        "coedit_pack_gone": "ST-COEDIT-GONE",
        "not_your_pack": "ST-NOT-YOURS",
        "only_owner_coedit": "ST-OWNER-ONLY",
        "only_owner_rename": "ST-OWNER-ONLY",
        "only_owner_delete": "ST-OWNER-ONLY",
        "rename_broken_state": "ST-RENAME-STATE",
        "renamed_failed": "ST-RENAME-FAILED",
        "delete_failed": "ST-DELETE-FAILED",
        "title_empty": "ST-TITLE-EMPTY",
        "remove_failed": "ST-REMOVE-FAILED",
        "image_process_failed": "ST-IMAGE",
        "video_convert_failed_redirect": "ST-VIDEO-CONVERT",
        "video_convert_generic_failed": "ST-VIDEO-FAILED",
        "animated_not_supported": "ST-ANIMATED",
        "import_invalid_source": "ST-IMPORT-SOURCE",
        "unrecognized": "ST-UNRECOGNIZED",
        "nothing_added_yet": "ST-NOTHING-ADDED",
        "no_sticker_to_tag": "ST-NO-STICKER",
        "retag_failed": "ST-RETAG",
    },
    "anon_bot": {
        "follow_link_invalid": "AN-LINK-INVALID",
        "follow_link_blocked": "AN-LINK-BLOCKED",
        "follow_link_paused": "AN-LINK-PAUSED",
        "inbox_gone": "AN-INBOX-GONE",
        "delivery_blocked": "AN-SENDER-BLOCKED",
        "delivery_forbidden": "AN-NOT-STARTED",
        "delivery_failed": "AN-DELIVERY",
        "reply_no_match": "AN-REPLY-NO-MATCH",
        "must_reply": "AN-NEEDS-REPLY",
        "must_reply_opening": "AN-OPENING-NEEDS-REPLY",
        "must_reply_ambiguous": "AN-AMBIGUOUS",
        "reply_forbidden": "AN-REPLY-BLOCKED",
        "reply_failed": "AN-REPLY-FAILED",
        "reply_stale": "AN-REPLY-STALE",
        "too_fast": "AN-TOO-FAST",
        "edit_not_relayed": "AN-EDIT-NOT-RELAYED",
        "conv_gone": "AN-CONV-GONE",
        "not_your_conversation": "AN-NOT-YOURS",
        "jump_no_anchor": "AN-NO-ANCHOR",
        "which_unknown": "AN-WHICH-UNKNOWN",
        "archive_not_owner": "AN-ARCHIVE-OWNER-ONLY",
        "export_failed": "AN-EXPORT-FAILED",
        "export_gone": "AN-EXPORT-GONE",
        "export_nothing_to_export": "AN-EXPORT-NOTHING",
        "generic_nudge": "AN-UNADDRESSED",
    },
}

JOB_ENDINGS = {
    "refused": "CV-REFUSED", "timeout": "CV-TIMEOUT", "too_slow": "CV-TOO-SLOW", "crash": "CV-CRASH",
    "too_large": "CV-OUTPUT-TOO-BIG", "send_failed": "CV-SEND-FAILED", "interrupted": "CV-RESTARTED",
}
STICKER_ERRORS = {
    "err_timed_out": "ST-TG-TIMEOUT", "err_invalid_name": "ST-TG-BAD-NAME", "err_name_occupied": "ST-TG-NAME-TAKEN",
    "err_too_many_stickers": "ST-TG-PACK-FULL", "err_bad_format": "ST-TG-BAD-FORMAT", "err_generic": "ST-TG-REJECTED",
}
ASSEMBLED = set(JOB_ENDINGS.values()) | set(STICKER_ERRORS.values()) | {"ST-IMPORT", "DL-QUOTA-HOUR", "DL-QUOTA-DAY"}

ALERT_KEYS = {
    "shared": {"flood_wait", "donate_invalid_amount"},
    "convert_bot": {"unsupported_format", "conversion_expired", "too_big_to_send_alert", "queue_full",
                    "job_not_running", "unknown_order"},
    "downloader_bot": {"redeliver_expired"},
    "sticker_bot": {"not_your_pack", "only_owner_coedit", "only_owner_rename", "only_owner_delete"},
    "anon_bot": {"conv_gone", "not_your_conversation", "export_ended", "export_nothing_yet"},
}

SIMPLE = frozenset({
    "FM-FLOOD", "FM-DONATE-CURRENCY", "FM-DONATE-AMOUNT", "FM-DONATE-TOO-MANY", "FM-DONATE-RANGE",
    "FM-UPDATING", "FM-UNKNOWN-COMMAND",
    "CV-NO-EXTENSION", "CV-TG-LIMIT", "CV-GROUP-LIMIT", "CV-UNSUPPORTED", "CV-TOO-BIG", "CV-NOTHING-SENDABLE",
    "CV-MEGAPIXELS", "CV-FORMAT-TOO-BIG", "CV-STORAGE-USER", "CV-QUEUE-FULL", "CV-EXPIRED",
    "CV-JOB-GONE", "CV-NO-CREDIT", "CV-MIXED-BATCH", "CV-UNRECOGNIZED", "CV-TOO-SLOW",
    "DL-QUOTA-HOUR", "DL-QUOTA-DAY", "DL-QUEUE-FULL", "DL-TOO-BIG", "DL-UNRECOGNIZED",
    "DL-LARGE-OFF", "DL-LARGE-PRIVATE", "DL-LARGE-NO-CREDIT", "DL-LARGE-TOO-BIG", "DL-LARGE-SHORT",
    "DL-BUTTON-EXPIRED",
    "ST-WHOMADE-UNKNOWN", "ST-COEDIT-LINK", "ST-COEDIT-GONE", "ST-NOT-YOURS", "ST-OWNER-ONLY",
    "ST-TITLE-EMPTY", "ST-ANIMATED", "ST-IMPORT-SOURCE", "ST-TG-PACK-FULL", "ST-UNRECOGNIZED",
    "ST-NOTHING-ADDED", "ST-NO-STICKER",
    "AN-LINK-INVALID", "AN-LINK-BLOCKED", "AN-LINK-PAUSED", "AN-INBOX-GONE", "AN-SENDER-BLOCKED",
    "AN-NOT-STARTED", "AN-NEEDS-REPLY", "AN-OPENING-NEEDS-REPLY", "AN-AMBIGUOUS", "AN-REPLY-BLOCKED",
    "AN-REPLY-STALE", "AN-TOO-FAST", "AN-EDIT-NOT-RELAYED", "AN-CONV-GONE", "AN-NOT-YOURS",
    "AN-NO-ANCHOR", "AN-WHICH-UNKNOWN", "AN-ARCHIVE-OWNER-ONLY", "AN-EXPORT-GONE",
    "AN-EXPORT-NOTHING", "AN-UNADDRESSED",
})

URGENT, FAULT, REFUSED = 1, 2, 3

URGENT_CODES = frozenset({

    "FM-CRASH", "CV-CRASH",

    "FM-INVOICE",

    "FM-ERASE",

    "CV-STORAGE-FULL", "DL-NO-SPACE",

    "CV-RESTARTED",

    "AN-DELIVERY", "AN-REPLY-FAILED",
})

def level(code) -> int:
    """URGENT, FAULT or REFUSED for a code."""
    if code in URGENT_CODES:
        return URGENT
    if code in SIMPLE:
        return REFUSED
    return FAULT

LEVEL_NAMES = {URGENT: "urgent", FAULT: "fault", REFUSED: "refused"}
LEVEL_ICONS = {URGENT: "🚨", FAULT: "⚠️", REFUSED: "•"}

def urgent(code) -> bool:
    """Whether this one is worth interrupting the owner for."""
    return level(code) == URGENT

def reportable(code) -> bool:
    """Whether a message ending in this code offers a Report button."""
    return is_code(code) and code not in SIMPLE

def code_for(bot: str, key: str) -> "str | None":
    """The code a message key carries in this bot, or None."""
    return KEYS.get(bot, {}).get(key) or KEYS["shared"].get(key)

def code_line(code: "str | None") -> str:
    return f"\n\n{MARK}{code}" if code else ""

def find_code(text: "str | None") -> "str | None":
    """The code a message ends with, if it is a known one."""
    match = _AT_END.search(text or "")
    return match.group(1) if match and match.group(1) in PROBLEMS else None

def strip_code(text: str) -> str:
    """The message without its code line."""
    match = _AT_END.search(text or "")
    return text[:match.start()] if match else text

def new_incident() -> str:
    return "".join(secrets.choice(_INCIDENT_ALPHABET) for _ in range(6))

def is_code(value) -> bool:
    return isinstance(value, str) and value in PROBLEMS

def is_incident(value) -> bool:
    return isinstance(value, str) and bool(INCIDENT_RE.match(value))

def decode(code: str) -> str:
    """Plain-text explanation of a code, for the owner."""
    problem = PROBLEMS.get(code)
    if problem is None:
        return f"{code}: not a known code."
    return (f"{code} — {problem.title} ({problem.bot})\n\n"
            f"What happened: {problem.meaning}\n"
            f"Likely causes: {problem.causes}\n"
            f"What to check: {problem.check}\n"
            f"Report button: {'offered' if reportable(code) else 'not offered, the message explains itself'}")

# ─── module: shared_features ─────────────────────────────────────────────────
"""Small self-contained features used by this bot -- kept in one file for convenience."""
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
        bots.append({"id": bot_id, "name": name, "username": username.strip().lstrip("@")})
    return bots

def _convert_bot_name() -> str:
    """ConvertBot as somebody can tap it -- its @username from SIBLING_BOTS -- or just its name when this deployment does not list it."""
    for bot in _parse_sibling_bots():
        if bot["id"] == "convertbot":
            return "@" + bot["username"]
    return "ConvertBot"

def sibling_bots_blurb(this_bot_name: str, lang: str) -> str:
    """One short pointer line, not a repeat of the sibling list itself -- sibling_bots_keyboard_row() below already renders that list as buttons, so spelling it out again in text too was just duplicate noise."""
    others = [b for b in _parse_sibling_bots() if b["id"] != this_bot_name]
    if not others:
        return ""
    return i18n.t(lang, "sibling_blurb")

def sibling_bots_keyboard_row(this_bot_name: str, only: str | None = None) -> list[InlineKeyboardButton]:
    others = [b for b in _parse_sibling_bots() if b["id"] != this_bot_name]
    if only:
        others = [b for b in others if b["id"] == only]
    return [InlineKeyboardButton(f"↗️ {b['name']}", url=f"https://t.me/{b['username']}") for b in others]

def language_keyboard(current: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(("✅ " if code == current else "") + label,
                             callback_data=f"setlang:{code}")
        for code, label in i18n.LANGUAGE_LABELS.items()
    ]])

WORKER_THREADS = int(os.environ.get("WORKER_THREADS", "4"))

GC_THRESHOLD = int(os.environ.get("GC_GEN0_THRESHOLD", "5000"))

async def tune_runtime(application) -> None:
    """Call from each bot's post_init."""
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=WORKER_THREADS, thread_name_prefix="worker")
    )
    gc.collect()
    gc.freeze()
    gc.set_threshold(GC_THRESHOLD, 20, 20)

FLOOD_UPDATES_PER_MINUTE = int(os.environ.get("FLOOD_UPDATES_PER_MINUTE", "40"))
FLOOD_REMIND_SECONDS = int(os.environ.get("FLOOD_REMIND_SECONDS", "60"))
_FLOOD_MAX_TRACKED = 4096

_flood_window: "OrderedDict[int, deque]" = OrderedDict()
_flood_told: "OrderedDict[int, float]" = OrderedDict()

def _flood_trim(store) -> None:
    while len(store) > _FLOOD_MAX_TRACKED:
        store.popitem(last=False)

def flood_wait_seconds(user_id: int) -> int:
    """0 if this person may be served now, otherwise the whole seconds until their oldest counted update falls out of the window."""
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
    """Register in a group of its OWN, above every other group."""
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

DONATION_STEPS = [15, 60, 200]
DONATION_COOLDOWN_FLOOR_DAYS = 3

DONATION_PIN = os.environ.get("DONATION_PIN", "off").lower() in ("on", "1", "true", "yes")

DONATE_STAR_OPTIONS = [15, 50, 150, 500]

MAX_DONATION_STARS = 100_000

STARS_SANDBOX = os.environ.get("FAMILY_STARS_SANDBOX", "").strip().lower() in ("1", "true", "yes", "on")
if STARS_SANDBOX:
    logging.getLogger(__name__).warning(
        "FAMILY_STARS_SANDBOX is on: Stars top-ups will be credited WITHOUT charging anybody. "
        "This must never be set on a bot real people use.")

FIAT_CURRENCIES = {
    "USD": {
        "symbol": "$", "label": "USD", "exp": 2,

        "options": [1, 3, 5, 10], "min_minor": 100, "max_minor": 1_000_000,
    },
}

FIAT_DONATIONS = os.environ.get("FIAT_DONATIONS", "off").lower() in ("on", "1", "true", "yes")

def _fiat_provider_token(currency: str) -> str | None:
    """The one chokepoint."""
    if not FIAT_DONATIONS:
        return None
    return os.environ.get(f"PAYMENT_PROVIDER_TOKEN_{currency}") or None

def _available_fiat_currencies() -> list[str]:
    return [c for c in FIAT_CURRENCIES if _fiat_provider_token(c)]

def format_ledger_amount(amount: int, currency: str) -> str:
    """amount is in the currency's smallest unit (see FIAT_CURRENCIES) for fiat, or a plain Stars count for XTR."""
    if currency == "XTR":
        return f"{amount}⭐"
    cfg = FIAT_CURRENCIES.get(currency)
    if not cfg:
        return f"{amount} {currency}"
    return f"{amount / (10 ** cfg['exp']):g} {cfg['symbol']}"

def _donation_nudge_due(user_id: int) -> bool:
    """Blocking; the async wrapper below is what handlers call."""
    count, last_shown, times_shown, donated = db.bump_donation_action(user_id)

    if donated:
        return False
    if times_shown >= len(DONATION_STEPS):
        return False

    if last_shown:
        days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_shown)).days
        if days_since < DONATION_COOLDOWN_FLOOR_DAYS:
            return False

    if count < DONATION_STEPS[times_shown]:
        return False

    db.reset_donation_prompt(user_id)
    return True

async def maybe_donation_nudge(user_id: int, lang: str, context=None, chat_id: int | None = None) -> str | None:
    """Await right after a successful action."""
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
    """Send the nudge on its own and pin it, replacing any earlier one."""
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
    """Called when somebody donates."""
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
    """Turn a completed payment into credit, and say what it bought."""
    await asyncio.to_thread(db.update_star_transaction, payload, "paid", charge_id)
    result = await asyncio.to_thread(family_link.topup, user.id, amount,
                                     "sandbox top-up" if sandbox else "stars top-up")

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

    emit_event(
        "info", "payment",
        ("SANDBOX top-up (nothing charged): " if sandbox else "Top-up: ")
        + f"{result['stars']} XTR -> {result['credited']} credit"
        + (f" +{result['bonus']} bonus" if result["bonus"] else ""),
    )
    return text

async def _send_donation_invoice(chat_id: int, user, context, amount: int, lang: str, currency: str = "XTR") -> str | None:
    """amount is in the currency's smallest unit for fiat (see FIAT_CURRENCIES), or a plain Stars count for XTR."""
    if currency != "XTR" and not _fiat_provider_token(currency):

        return i18n.t(lang, "donate_currency_not_configured", currency=currency)
    payload = f"donate:{uuid.uuid4().hex}"
    await asyncio.to_thread(
        db.record_star_invoice, user.id, user.username, amount, "donation", payload,
        "invoiced", currency,
    )
    if STARS_SANDBOX and currency == "XTR":

        text = await _credit_topup(chat_id, context, user, amount, lang,
                                   payload, f"sandbox:{payload}", sandbox=True)
        await context.bot.send_message(chat_id=chat_id, text=text)
        return None

    provider_token = "" if currency == "XTR" else (_fiat_provider_token(currency) or "")
    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=i18n.t(lang, "donate_invoice_title"),

            description=(i18n.t(lang, "donate_invoice_description",
                                credited=(await asyncio.to_thread(family_link.quote_topup, user.id, amount))["total"])
                         if currency == "XTR"
                         else i18n.t(lang, "donate_invoice_description_fiat")),
            payload=payload,
            provider_token=provider_token,
            currency=currency,
            prices=[LabeledPrice(i18n.t(lang, "donate_invoice_label"), amount)],
        )
        return None
    except Exception as exc:
        await asyncio.to_thread(db.update_star_transaction, payload, "failed")
        return i18n.t(lang, "donate_invoice_error", error=exc)

def _validate_donation_amount(whole_amount: int, currency: str, lang: str) -> tuple[int | None, str | None]:
    """whole_amount is in whole units (a Stars count, or whole dollars for USD)."""
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
    """/donate -- with no args, shows preset-amount buttons for Stars plus any fiat currency that has a payment provider connected (see FIAT_CURRENCIES above), with a Custom button per currency for anything else."""
    lang = await i18n.get_lang(update.effective_user.id, context)
    if context.args:
        raw = context.args[0].replace(",", "")
        currency = "XTR"
        if len(context.args) > 1:
            requested = context.args[1].upper()
            if requested not in FIAT_CURRENCIES:
                await update.message.reply_text(i18n.t(lang, "donate_unknown_currency", currency=context.args[1]))
                return

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
    """The amount and its currency."""
    return f"{amount} {symbol}"

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
    """Tapping a 'Custom' button asks for an amount via ForceReply; the actual amount is picked up by donate_custom_amount_received below, matched via the donate_custom_currency flag this sets in user_data."""
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
    """Register in a group before your bot's normal text handling (see track_activity for the same pattern) -- a no-op unless donate_custom_button_chosen just set the awaiting-amount flag, in which case it consumes the reply and stops it from also being treated as a normal message (ApplicationHandlerStop)."""
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

async def donation_precheckout(query) -> None:
    """Caller has already confirmed query.invoice_payload starts with 'donate:'."""
    await query.answer(ok=True)

async def donation_payment_received(update, context) -> None:
    """Caller has already confirmed the payload starts with 'donate:'."""
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

    await unpin_donation_nudge(context, user.id, update.effective_chat.id)

_LEDGER_LABELS = {"refund": "returned"}

async def balance_command(update, context) -> None:
    """/balance -- what this person is holding, and what it is for."""
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

            lines.append(f"  {when}  {sign}{row['delta']} ⚡  "
                         f"{_LEDGER_LABELS.get(row['reason'], row['reason'])}")
    if not rows and totals["balance"] == 0:
        lines.append("")
        lines.append(i18n.t(lang, "balance_empty_hint"))
    await update.message.reply_text("\n".join(lines))

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

def _menu_in(commands, language: str):
    """`commands` with each description swapped for its `language` one."""
    table = getattr(i18n, "COMMAND_MENU", {}).get(language) or {}
    return [BotCommand(c.command, table.get(c.command) or c.description)
            for c in commands]

MENU_SIGNATURE_KEY = "_menu_sig"
_MENU: dict = {}

def _menu_for(user_id: int, lang: "str | None"):
    """The menu this person should have, or None before publish_commands has said what the menus are."""
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
    """Give one person's chat the menu in their language."""
    commands = _menu_for(user_id, lang)
    if not commands:
        return
    try:
        await context.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
    except Exception:
        logging.getLogger(__name__).debug("Could not set the chat menu for %s", user_id, exc_info=True)
        return
    context.user_data[MENU_SIGNATURE_KEY] = _menu_signature(commands)

_UNOWNED_SCOPES = (
    BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators,
)

async def publish_commands(application, public, admin_only=(), admin_ids=()) -> None:
    """The default menu for everyone, in every language; the scopes the code does not own, cleared; and the owner's chat, in the owner's language."""
    logger = logging.getLogger(__name__)
    public = list(public)
    _MENU.update(public=public, admin_only=list(admin_only), admin_ids=set(admin_ids))

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

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

def esc(text: str) -> str:
    """The three characters Telegram's HTML parser cares about."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def heading(text: str) -> str:
    return f"<b>{esc(text)}</b>"

_COMMAND_RE = re.compile(r"(?<![\w/])(/[a-z][a-z0-9_]{1,30})\b")

def body(text: str) -> str:
    """Escaped, with every /command in it set as a command."""
    return _COMMAND_RE.sub(r"<code>\1</code>", esc(text))

def lead_in(text: str, limit: int = 28) -> str:
    """`Money: it is voluntary` with the lead-in in bold."""
    label, colon, rest = text.partition(":")
    if not colon or "\n" in label or len(label) > limit:
        return body(text)
    return f"<b>{esc(label)}:</b>{body(rest)}"

def collapsed(text: str) -> str:
    """A blockquote that shows a few lines and opens on a tap."""
    return f"<blockquote expandable>{body(text)}</blockquote>"

def quoted(text: str) -> str:
    """A blockquote that is always open. For a few lines, not for many."""
    return f"<blockquote>{body(text)}</blockquote>"

def joined(*blocks) -> str:
    """The blocks that are not empty, one blank line between each."""
    return "\n\n".join(block for block in blocks if block)

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

OPERATOR_CONTACT = (os.environ.get("OPERATOR_CONTACT") or "mukhtorovmurodbek@gmail.com").strip()

PRIVACY_URL = os.environ.get("PRIVACY_URL", "").strip()
TERMS_URL = os.environ.get("TERMS_URL", "").strip()

def _policy_footer(lang: str, url: str) -> str:
    """The two optional trailing lines, each dropped when unconfigured."""
    lines = []
    if url:
        label = esc(url)
        lines.append(body(i18n.t(lang, "policy_full_text", url="\x00"))
                     .replace("\x00", f'<a href="{label}">{label}</a>'))
    if OPERATOR_CONTACT:
        lines.append(body(i18n.t(lang, "policy_contact", contact=OPERATOR_CONTACT)))
    return "\n".join(lines)

def privacy_text(lang: str) -> str:
    """The notice, laid out so its shape is visible without scrolling."""
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
    """Four paragraphs, three of which already open with their own label and a colon -- in all three languages, because that is how the sentences were written."""
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

ERASE_PREFIX = "erasedata:"

def erase_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(i18n.t(lang, "delete_data_button_yes"), callback_data=ERASE_PREFIX + "yes"),
        InlineKeyboardButton(i18n.t(lang, "delete_data_button_no"), callback_data=ERASE_PREFIX + "no"),
    ]])

async def paysupport_command(update, context) -> None:
    """/paysupport -- required of every bot that takes Telegram Stars."""
    user = update.effective_user
    lang = await i18n.get_lang(user.id, context)
    await update.message.reply_text(i18n.t(
        lang, "paysupport_text", contact=OPERATOR_CONTACT or "@BotFather", user_id=user.id))

async def delete_my_data_command(update, context):
    """Returns None on purpose."""
    lang = await i18n.get_lang(update.effective_user.id, context)

    await reply_formatted(
        update.message,
        joined(heading(i18n.t(lang, "delete_data_confirm")),
               body(i18n.t(lang, "delete_data_consequences"))),
        reply_markup=erase_keyboard(lang),
    )

async def delete_my_data_chosen(update, context):
    """Every edit goes through live_message.edit_in_place rather than query.edit_message_text, for the two reasons that helper exists."""
    query = update.callback_query
    await query.answer()
    lang = await i18n.get_lang(update.effective_user.id, context)
    if query.data != ERASE_PREFIX + "yes":
        await live_message.edit_in_place(
            query.message, context.bot, body(i18n.t(lang, "delete_data_kept")), parse_mode=ParseMode.HTML
        )
        return None

    user_id = update.effective_user.id

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

    try:
        rows += await asyncio.to_thread(family_link.forget_problem_reporter, user_id)
    except Exception:
        logging.getLogger(__name__).exception(
            "Cleared %s's data but could not take them off their problem reports", user_id
        )

    done = body(i18n.t(lang, "delete_data_done", rows=rows))

    try:
        context.application.drop_user_data(user_id)
    except Exception:
        logging.getLogger(__name__).debug("Nothing cached for %s to drop", user_id)
    await live_message.edit_in_place(
        query.message, context.bot, done, parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END

FORCE_REPLY_KEY = "force_reply_msg_id"

def remember_force_reply(context, message) -> None:
    """Call right after sending anything carrying a ForceReply, so /cancel can delete it again."""
    context.user_data[FORCE_REPLY_KEY] = message.message_id

async def release_force_reply(update, context, stored_only: bool = False) -> bool:
    """Let go of a forced reply."""
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

            logging.getLogger(__name__).debug(
                "Could not delete force-reply prompt %s", message_id, exc_info=True
            )
    return released

def reset_user_state(context, keep: dict | None = None) -> None:
    """user_data.clear(), minus the one key /cancel is not finished with."""
    preserved = {k: context.user_data[k] for k in (FORCE_REPLY_KEY,) if k in context.user_data}
    context.user_data.clear()
    context.user_data.update(preserved)
    if keep:
        context.user_data.update(keep)

CancelItem = namedtuple("CancelItem", "key label button")

CANCEL_PICK_PREFIX = "cancelpick:"
CANCEL_PICK_ALL = "all"
CANCEL_PICK_NONE = "none"

def cancel_items(context, lang: str) -> list[CancelItem]:
    """The waiting-on-the-user states that live in this file, for the calling bot to offer alongside its own."""
    items = []
    if context.user_data.get("donate_custom_currency"):
        items.append(CancelItem("donation",
                                i18n.t(lang, "cancel_item_donation"),
                                i18n.t(lang, "cancel_button_donation")))
    return items

def cancel_shared_item(context, lang: str, key: str) -> str | None:
    """Stop one of this file's states by key."""
    if key == "donation" and context.user_data.pop("donate_custom_currency", None):
        return i18n.t(lang, "cancel_item_donation")
    return None

def cancel_question(lang: str, items: list[CancelItem]):
    """The "which one?" message: what is pending, and a button each."""
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
    """Put the question on screen."""
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
    """The last two steps of every bot's /cancel: release the reply lock and say what was stopped."""
    released = await release_force_reply(update, context, stored_only=stored_only)

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
    """finish_cancel's twin for the button path."""
    query = update.callback_query
    had_prompt = FORCE_REPLY_KEY in context.user_data
    released = await release_force_reply(update, context, stored_only=True)
    if released and not stopped:
        stopped = [i18n.t(lang, "cancel_item_stale_prompt")]
    text = build_cancel_text(lang, stopped)

    await live_message.edit_in_place(query.message, context.bot, text)
    if had_prompt and not released:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=i18n.t(lang, "cancel_reply_box_freed"),
            reply_markup=ReplyKeyboardRemove(),
        )

async def keep_going(update, context, lang: str) -> None:
    """"Keep going" -- the way back out of the question, having changed nothing."""
    await live_message.edit_in_place(
        update.callback_query.message, context.bot, i18n.t(lang, "cancel_kept")
    )

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
    """Files on a laptop, stdout only in the cloud."""
    override = os.environ.get("LOG_TO_FILES")
    if override is not None:
        return override.strip().lower() in ("1", "true", "yes", "on")
    return not (os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get("RAILWAY_ENVIRONMENT"))

def setup_logging(bot_file: str) -> None:
    """Call once near the top of each bot's bot.py, passing __file__."""
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

REPORTS_TO = int(os.environ.get("FAMILY_REPORTS_TO") or 8796896653)
REPORT_BUTTONS = (os.environ.get("FAMILY_REPORT_BUTTONS") or "on").strip().lower() not in ("0", "off", "no", "false")

PROBLEM_FLUSH_SECONDS = int(os.environ.get("PROBLEM_FLUSH_SECONDS", "20"))
MAX_BUFFERED_PROBLEMS = 500

ALERT_COOLDOWN_SECONDS = int(os.environ.get("PROBLEM_ALERT_COOLDOWN_SECONDS", "900"))
BURST_COUNT = int(os.environ.get("PROBLEM_BURST_COUNT", "15"))
BURST_WINDOW_SECONDS = int(os.environ.get("PROBLEM_BURST_WINDOW_SECONDS", "3600"))

_problem_buffer: "OrderedDict[tuple, object]" = OrderedDict()

_alerted: "dict[str, list]" = {}

_recent_faults: "dict[str, deque]" = {}

def _should_alert(code: str, now: float) -> "tuple[bool, int]":
    """(send one now?, how many went unreported since the last one)."""
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
    """Put an urgent problem on the family event bus, which is what ManagerBot forwards to the owner."""
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
    """Remember that this problem was shown, to be written out on the next pass -- and interrupt the owner if it is the kind that cannot wait."""
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

        logging.getLogger(__name__).debug("Could not alert on %s", code, exc_info=True)

    while len(_problem_buffer) > MAX_BUFFERED_PROBLEMS:
        _problem_buffer.popitem(last=False)

def _flush_problems_now() -> int:
    """Blocking; call through asyncio.to_thread."""
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
    """The language a chat was last seen in, for labelling a report button on a message that is already on its way out."""
    if not chat_id or not lang:
        return
    _chat_langs[chat_id] = lang
    _chat_langs.move_to_end(chat_id)
    while len(_chat_langs) > 4096:
        _chat_langs.popitem(last=False)

def report_markup(lang: str, code: str, incident: str, markup=None):
    """`markup` with a Report row added, or a keyboard holding only that row."""
    if (not REPORT_BUTTONS or not problems.reportable(code) or _has_report(markup)
            or (markup is not None and not isinstance(markup, InlineKeyboardMarkup))):
        return markup
    rows = [list(row) for row in markup.inline_keyboard] if markup is not None else []
    rows.append([InlineKeyboardButton(i18n.t(lang, "report_button"),
                                      callback_data=f"rpt:{code}:{incident}")])
    return InlineKeyboardMarkup(rows)

def _with_logged_note(text: str, code: str, lang: str) -> str:
    """The same message, with one line saying it has already been written down and that nothing in what was written is about them."""
    note = i18n.t(lang, "problem_logged_note")
    body = problems.strip_code(text)
    if note in body:
        return text
    return f"{body}\n\n{note}{problems.code_line(code)}"

def _has_report(markup) -> bool:
    return any((getattr(button, "callback_data", None) or "").startswith("rpt")
               for row in getattr(markup, "inline_keyboard", None) or () for button in row)

def _button_incident(markup) -> "str | None":
    """The incident a Report button made elsewhere already carries -- a conversion's ending, or a crash notice, whose incident is also in the owner's alert or beside the traceback."""
    for row in getattr(markup, "inline_keyboard", None) or ():
        for button in row:
            data = getattr(button, "callback_data", None) or ""
            if data.startswith("rpt:"):
                return data.rsplit(":", 1)[-1]
    return None

problem_log = logging.getLogger("problems")

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
    """A message on its way out."""
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
    """Log every problem this bot shows, and put a Report button under the ones that deserve it."""
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
    """Somebody attached their own details to a problem."""
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

        when = getattr(query.message, "date", None)
        if when is None or when.timestamp() <= 0:
            when = datetime.now(timezone.utc)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(i18n.t(lang, "report_send"),
                                 callback_data=f"rpts:{code}:{incident}:{int(when.timestamp())}"),
            InlineKeyboardButton(i18n.t(lang, "report_cancel"), callback_data="rptc"),
        ]])

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
    """A crash used to leave the person with no answer at all."""
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
    """Register with Application.add_error_handler in each bot's main() -- this is PTB's global hook for exceptions that escape a handler callback uncaught (i.e."""

    if update is None and is_transient_network_error(context.error):
        note_network_blip(context.error)
        return
    incident = problems.new_incident()
    logging.getLogger(__name__).error(
        "Unhandled exception while processing an update (incident %s)", incident, exc_info=context.error)
    record_error(context.error)
    await _tell_about_crash(update, context, incident)

ACTIVITY_FLUSH_SECONDS = int(os.environ.get("ACTIVITY_FLUSH_SECONDS", "60"))

_activity_buffer: set[int] = set()

def _flush_activity_now() -> int:
    """Blocking; call through asyncio.to_thread."""
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
    """Register as a TypeHandler(Update, track_activity, ...) in a group of its OWN, above every other group, so /status can report active users hourly / since this process started."""
    note_network_ok()

    live_message.note_update(update)
    user = update.effective_user
    if not user:
        return
    _activity_buffer.add(user.id)
    note_usage_update(user.id)
    context.user_data["_last_seen"] = time.time()
    remember_chat_lang(user.id, context.user_data.get("lang"))

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

async def refuse_new_work(lang: str, user_id: int, chat_id: int) -> str | None:
    """The sentence to answer with instead of starting slow work, or None when there is no reason not to start it."""
    if not lifecycle.is_paused():
        return None
    if not lifecycle.in_maintenance():
        return i18n.t(lang, "restarting_send_again")

    await asyncio.to_thread(lifecycle.hold_for_update, user_id, chat_id)
    minutes = lifecycle.maintenance_minutes_left()
    if minutes is None:
        return i18n.t(lang, "update_soon_try_later_soon")
    return i18n.t(lang, "update_soon_try_later", minutes=minutes)

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
    """One line in each bot's main(), next to family_link.attach()."""
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
    """Best-effort guess at where this process is running."""
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

# ─── module: big_files ───────────────────────────────────────────────────────
"""Files over the Bot API's size limits, moved over MTProto instead."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_MB = 1024 * 1024

BOT_API_DOWNLOAD_BYTES = 20 * _MB
BOT_API_SEND_BYTES = 50 * _MB

MTPROTO_MAX_BYTES = 2000 * _MB

CONNECT_TIMEOUT_S = 20

REST_AFTER_FAILURE_S = 300

PART_BYTES = 512 * 1024
PARALLEL_PARTS = 4

STALL_S = float(os.environ.get("BIG_FILES_STALL_SECONDS") or 90)

TRANSFER_TIME_LIMIT_S = 600
MIN_RATE_BYTES_S = 256 * 1024

PROGRESS_EVERY_S = 0.5

def transfer_limit_s(size: int) -> int:
    """The longest a transfer of `size` bytes may take."""
    return int(max(TRANSFER_TIME_LIMIT_S, (size or 0) / MIN_RATE_BYTES_S))

PREFIX = ""
API_ID = ""
API_HASH = ""
BOT_TOKEN = ""

SCRIPT = Path(__spec__.origin if __spec__ else __file__).resolve()

SESSION_FILE = Path(tempfile.gettempdir()) / "unconfigured-mtproto.session"

class Unavailable(Exception):
    """The MTProto route could not be used."""

class Stalled(asyncio.TimeoutError):
    """The transfer stopped moving: nothing arrived or left for STALL_S."""

class NotThere(Exception):
    """The route works, but the message or its file is not what was asked for: deleted since, or a different file than the one announced."""

def _telethon_installed() -> bool:
    try:
        return importlib.util.find_spec("telethon") is not None
    except (ImportError, ValueError):
        return False

def _configured() -> bool:
    if not (API_ID.strip().isdigit() and API_HASH.strip() and BOT_TOKEN):
        return False
    if not _telethon_installed():
        logger.warning("%s_API_ID and %s_API_HASH are set but Telethon is not installed; "
                       "files over the Bot API's limits stay refused.", PREFIX, PREFIX)
        return False
    return True

CONFIGURED = False

VERIFIED = None
_on_disabled: list = []

_REFUSALS = ("ApiIdInvalid", "api_id/api_hash", "AccessTokenInvalid", "AccessTokenExpired")

def configure(prefix: str, name: str) -> bool:
    """Which bot this is: its settings' prefix ("CBOT") and its name ("convertbot"), for its token, its API id and its session file."""
    global PREFIX, API_ID, API_HASH, BOT_TOKEN, SESSION_FILE, CONFIGURED
    PREFIX = prefix
    API_ID = os.environ.get(f"{prefix}_API_ID") or os.environ.get("TELEGRAM_API_ID") or ""
    API_HASH = os.environ.get(f"{prefix}_API_HASH") or os.environ.get("TELEGRAM_API_HASH") or ""
    BOT_TOKEN = os.environ.get(f"{prefix}_TOKEN") or ""

    SESSION_FILE = Path(tempfile.gettempdir()) / (
        f"{name}-mtproto-" + hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:12] + ".session")
    CONFIGURED = _configured()
    return CONFIGURED

def usable(chat_id: int) -> bool:
    """Whether a big file in this chat can go over MTProto."""
    return CONFIGURED and chat_id > 0

def describe() -> str:
    """One line for the startup log."""
    if VERIFIED is False:
        return (f"files past the Bot API's limits are refused: Telegram refused the API id and hash "
                f"({PREFIX}_API_ID / {PREFIX}_API_HASH, or TELEGRAM_API_ID / TELEGRAM_API_HASH)")
    if CONFIGURED:
        return f"files past the Bot API's limits go over MTProto ({PREFIX}_API_ID or TELEGRAM_API_ID is set)"
    return (f"files past the Bot API's limits are refused (set {PREFIX}_API_ID and {PREFIX}_API_HASH, "
            f"or TELEGRAM_API_ID and TELEGRAM_API_HASH, to lift them)")

def on_disabled(hook) -> None:
    """Call `hook()` if verify() switches the route off -- for a module that worked out a limit from CONFIGURED when it was imported."""
    _on_disabled.append(hook)

async def verify() -> bool:
    """Log in once, as the bot starts, so that an API id and hash that are set but wrong switch the route off -- the bot then promises and takes exactly what the Bot API allows, as if they had never been set -- instead of failing the first person who sends a big file."""
    global CONFIGURED, VERIFIED
    if not CONFIGURED:
        return False
    try:
        await _run({"op": "check", "limit_s": CONNECT_TIMEOUT_S})
    except Unavailable as exc:
        if not any(word in str(exc) for word in _REFUSALS):
            logger.warning("Could not check the MTProto login for big files (%s); the route stays on.", exc)
            return True
        CONFIGURED, VERIFIED = False, False
        logger.warning("Telegram refused %s's API id and hash for big files (%s). Files past the Bot API's "
                       "limits are refused until they are fixed.", PREFIX, exc)
        for hook in _on_disabled:
            try:
                hook()
            except Exception:
                logger.exception("A module could not lower its limits after the big-file route went off")
        return False
    except Exception as exc:
        if not _closing:
            logger.warning("Could not check the MTProto login for big files (%s: %s); the route stays on.",
                           type(exc).__name__, exc)
        return True
    VERIFIED = True
    logger.info("MTProto login for big files checked: Telegram accepted it.")
    return True

_resting_until = 0.0
_children: set = set()
_closing = False

def _child_environment() -> dict:
    """What the child needs, handed over explicitly and under names of its own: in the one-process edition this module sees its bot's settings through a view of its own, the child inherits only the real environment, and the child has no way to know which bot started it."""
    env = {key: value for key, value in dict(os.environ).items() if isinstance(value, str)}
    env.update(BIG_FILES_API_ID=API_ID, BIG_FILES_API_HASH=API_HASH, BIG_FILES_TOKEN=BOT_TOKEN,
               BIG_FILES_SESSION=str(SESSION_FILE), PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    return env

async def _run(job: dict, progress=None) -> dict:
    """Run one transfer in a child and return its last line."""
    global _resting_until
    if not CONFIGURED:
        raise Unavailable(f"{PREFIX or 'the bot'}'s API id and hash are not set")
    if time.monotonic() < _resting_until:
        raise Unavailable("resting after a failed connection")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-u", str(SCRIPT.with_name("main.py")), "--module", "big_files", json.dumps(job),
        cwd=str(SCRIPT.parent), env=_child_environment(),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _children.add(proc)
    outcome = None
    errors = bytearray()

    async def keep_stderr_tail():

        while chunk := await proc.stderr.read(65536):
            errors.extend(chunk)
            del errors[:-2000]

    async def follow():
        nonlocal outcome
        drain = asyncio.ensure_future(keep_stderr_tail())
        while True:
            try:
                raw = await proc.stdout.readline()
            except ValueError:
                continue
            if not raw:
                break
            try:
                line = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if "progress" in line:
                if progress is not None:
                    result = progress(*line["progress"])
                    if asyncio.iscoroutine(result):
                        await result
            else:
                outcome = line
        await proc.wait()
        await drain

    try:
        await asyncio.wait_for(follow(), job["limit_s"] + 2 * CONNECT_TIMEOUT_S)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        raise
    finally:
        _children.discard(proc)

    if outcome is None:
        tail = bytes(errors).decode("utf-8", "replace").strip()[-300:]
        raise RuntimeError(f"the transfer process exited {proc.returncode} without a result. {tail}".strip())
    if outcome.get("ok"):
        return outcome
    kind, message = outcome.get("kind"), outcome.get("message") or ""
    if kind == "unavailable":
        _resting_until = time.monotonic() + REST_AFTER_FAILURE_S
        logger.warning("MTProto route for big files failed: %s", message)
        raise Unavailable(message)
    if kind == "not_there":
        raise NotThere(message)
    if kind == "stalled":
        raise Stalled(message)
    if kind == "timeout":
        raise asyncio.TimeoutError(message)
    raise RuntimeError(message)

async def download(chat_id: int, message_id: int, dest, expected_size: int = 0,
                   progress=None) -> int:
    """Write the file attached to message `message_id` in the private chat `chat_id` to `dest`."""
    if not usable(chat_id):
        raise Unavailable("big files are only fetched in private chats")
    outcome = await _run({"op": "download", "chat_id": chat_id, "message_id": message_id,
                          "dest": str(dest), "expected_size": expected_size,
                          "limit_s": transfer_limit_s(expected_size)}, progress)
    return int(outcome.get("bytes") or 0)

async def send_document(chat_id: int, path, filename: str, caption: str = "", progress=None) -> None:
    """Send `path` to the private chat `chat_id` as a document called `filename`, with a plain-text caption."""
    if not usable(chat_id):
        raise Unavailable("big files are only sent in private chats")
    await _run({"op": "send", "chat_id": chat_id, "path": str(path), "filename": filename, "caption": caption,
                "limit_s": transfer_limit_s(Path(path).stat().st_size)}, progress)

async def close() -> None:
    """Stop any transfer still running -- the bot is shutting down. Never raises."""
    global _closing
    _closing = True
    for proc in list(_children):
        try:
            if proc.returncode is None:
                proc.kill()
        except Exception:
            logger.debug("Could not stop a transfer process", exc_info=True)

def _emit(line: dict) -> None:
    sys.stdout.write(json.dumps(line) + "\n")
    sys.stdout.flush()

def _save_session(text: str) -> None:
    """Written whole and then renamed, so a reader never sees half a file."""
    partial = SESSION_FILE.with_suffix(".partial")
    partial.write_text(text, encoding="utf-8")
    try:
        os.chmod(partial, 0o600)
    except OSError:
        pass
    os.replace(partial, SESSION_FILE)

async def _connect():
    """A connected, logged-in client. Raises Unavailable."""
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    try:
        saved = SESSION_FILE.read_text(encoding="utf-8") if SESSION_FILE.is_file() else ""
    except OSError:
        saved = ""
    client = TelegramClient(StringSession(saved or None), int(API_ID), API_HASH.strip(),
                            receive_updates=False, connection_retries=1, request_retries=2,
                            timeout=CONNECT_TIMEOUT_S)
    try:
        await asyncio.wait_for(client.connect(), CONNECT_TIMEOUT_S)
        if not await client.is_user_authorized():
            await asyncio.wait_for(client.sign_in(bot_token=BOT_TOKEN), CONNECT_TIMEOUT_S)
            _save_session(client.session.save())
    except Exception as exc:
        try:
            await client.disconnect()
        except Exception:
            pass
        raise Unavailable(f"{type(exc).__name__}: {exc}") from exc
    return client

def _media_size(media) -> int:
    document = getattr(media, "document", None)
    return int(getattr(document, "size", 0) or 0)

class _Stalled(Exception):
    pass

class _Moving:
    """When the transfer last moved a byte."""

    def __init__(self):
        self.at = time.monotonic()

def _progress_emitter(moving: "_Moving | None" = None):
    last = [0.0]

    def progress(done, total):
        now = time.monotonic()
        if moving is not None:
            moving.at = now
        if now - last[0] >= PROGRESS_EVERY_S:
            last[0] = now
            _emit({"progress": [done, total]})
    return progress

async def _watched(coroutine, limit_s: float, moving: _Moving):
    """Run a transfer to its end, unless nothing moves for STALL_S or it runs past `limit_s`."""
    task = asyncio.ensure_future(coroutine)
    deadline = time.monotonic() + limit_s
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=min(5.0, STALL_S / 3))
            if done:
                return task.result()
            now = time.monotonic()
            if now - moving.at > STALL_S:
                raise _Stalled(f"nothing moved for {STALL_S:.0f}s")
            if now > deadline:
                raise asyncio.TimeoutError(f"still going after {limit_s / 60:.0f} minutes")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except BaseException:
                pass

async def _download_in_parallel(client, media, handle, size: int, progress) -> None:
    """PARALLEL_PARTS streams, each asking for every PARALLEL_PARTS-th part of PART_BYTES, written where it belongs as it arrives."""
    streams = max(1, min(PARALLEL_PARTS, -(-size // PART_BYTES)))
    done = 0

    async def stream(index: int) -> None:
        nonlocal done
        position = index * PART_BYTES
        async for chunk in client.iter_download(media, offset=position, stride=streams * PART_BYTES,
                                                request_size=PART_BYTES, file_size=size):
            handle.seek(position)
            handle.write(chunk)
            position += streams * PART_BYTES
            done += len(chunk)
            progress(done, size)
    await asyncio.gather(*(stream(index) for index in range(streams)))

async def _child_download(client, job: dict, progress) -> int:
    chat_id, dest, expected = job["chat_id"], job["dest"], job.get("expected_size") or 0
    try:

        message = await client.get_messages(None, ids=job["message_id"])
    except Exception as exc:
        raise Unavailable(f"{type(exc).__name__}: {exc}") from exc
    if message is None or getattr(message, "media", None) is None:
        raise NotThere("the message with the file is no longer in the chat")

    if getattr(message.peer_id, "user_id", None) != chat_id:
        raise NotThere("the message is not in this chat")
    size = _media_size(message.media)
    if expected and size and size != expected:
        raise NotThere(f"the message holds a {size}-byte file, not the {expected} bytes announced")
    with open(dest, "wb") as handle:
        if size:
            await _download_in_parallel(client, message.media, handle, size, progress)
        else:
            await client.download_media(message, file=handle, progress_callback=progress)
    written = Path(dest).stat().st_size
    if expected and written != expected:
        raise NotThere(f"only {written} of {expected} bytes arrived")
    return written

async def _child_send(client, job: dict, progress) -> None:
    from telethon import types

    uploaded = await client.upload_file(job["path"], part_size_kb=PART_BYTES // 1024,
                                        file_name=job["filename"], progress_callback=progress)
    await client.send_file(
        types.PeerUser(job["chat_id"]), file=uploaded, caption=job.get("caption") or None,
        force_document=True, parse_mode=None,
        attributes=[types.DocumentAttributeFilename(job["filename"])])

async def _child(job: dict) -> None:
    try:
        client = await _connect()
    except Unavailable as exc:
        _emit({"ok": False, "kind": "unavailable", "message": str(exc)})
        return
    moving = _Moving()
    progress = _progress_emitter(moving)
    limit_s = job.get("limit_s") or TRANSFER_TIME_LIMIT_S
    try:
        if job["op"] == "check":

            await asyncio.wait_for(client.get_me(), CONNECT_TIMEOUT_S)
            _emit({"ok": True})
        elif job["op"] == "download":
            written = await _watched(_child_download(client, job, progress), limit_s, moving)
            _emit({"ok": True, "bytes": written})
        else:
            await _watched(_child_send(client, job, progress), limit_s, moving)
            _emit({"ok": True})
    except _Stalled as exc:
        _emit({"ok": False, "kind": "stalled", "message": str(exc)})
    except asyncio.TimeoutError as exc:
        _emit({"ok": False, "kind": "timeout", "message": str(exc) or "ran out of time"})
    except Unavailable as exc:
        _emit({"ok": False, "kind": "unavailable", "message": str(exc)})
    except NotThere as exc:
        _emit({"ok": False, "kind": "not_there", "message": str(exc)})
    except Exception as exc:
        _emit({"ok": False, "kind": "error", "message": f"{type(exc).__name__}: {exc}"})
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

if __name__ == "__main__":

    API_ID = os.environ.get("BIG_FILES_API_ID", "")
    API_HASH = os.environ.get("BIG_FILES_API_HASH", "")
    BOT_TOKEN = os.environ.get("BIG_FILES_TOKEN", "")
    SESSION_FILE = Path(os.environ.get("BIG_FILES_SESSION") or SESSION_FILE)
    asyncio.run(_child(json.loads(sys.argv[1])))

# ─── module: pricing ─────────────────────────────────────────────────────────
"""What a job costs the machine it runs on, and what it is sold for."""
from __future__ import annotations

import math
import os

MONTH_SECONDS = 30 * 24 * 3600
USD_PER_VCPU_SECOND = 20 / MONTH_SECONDS
USD_PER_GB_SECOND = 10 / MONTH_SECONDS
USD_PER_GB_EGRESS = 0.05

USD_PER_STAR = float(os.environ.get("FAMILY_USD_PER_STAR") or 0.013)

JOB_CPUS = 2
JOB_MEMORY_GB = 1.5

OVERHEAD = float(os.environ.get("FAMILY_PRICE_OVERHEAD") or 0.5)

KNEE = float(os.environ.get("FAMILY_PRICE_KNEE") or 5)

POWER = float(os.environ.get("FAMILY_PRICE_POWER") or 0.8)

MINIMUM = int(os.environ.get("FAMILY_PRICE_MINIMUM") or 3)

GB = 1024 ** 3

def deepest_credits_per_star() -> float:
    """The most ⚡ one Star ever buys, from the family's own ladder."""
    import family_link
    ladder = [multiplier for _, multiplier in family_link.TOPUP_LADDER]
    return family_link.TOPUP_MULTIPLIER * max([1.0] + ladder)

def usd_per_credit() -> float:
    """What one ⚡ is worth at the least it may have brought in."""
    return USD_PER_STAR / deepest_credits_per_star()

def running_usd(seconds: float) -> float:
    """A job holding its two cores and 1.5 GB for `seconds`."""
    return seconds * (JOB_CPUS * USD_PER_VCPU_SECOND + JOB_MEMORY_GB * USD_PER_GB_SECOND)

def egress_usd(sent_bytes: float) -> float:
    return sent_bytes / GB * USD_PER_GB_EGRESS

def cost(seconds: float, sent_bytes: float) -> float:
    """The most a job allowed to run `seconds` and send `sent_bytes` costs, in ⚡, overhead included."""
    return OVERHEAD + (running_usd(seconds) + egress_usd(sent_bytes)) / usd_per_credit()

def markup(job_cost: float) -> float:
    if job_cost <= KNEE:
        return job_cost
    return KNEE * (job_cost / KNEE) ** POWER

def price(job_cost: float) -> int:
    """What a job of this cost is sold for, in whole ⚡."""
    return max(MINIMUM, math.ceil(job_cost + markup(job_cost) - 1e-9))

def affordable_seconds(sold_for: int, sent_bytes: float) -> float:
    """How long a job sold for `sold_for` ⚡ may run, sending `sent_bytes`, before it would cost more than it was sold for."""
    left = (sold_for - OVERHEAD) * usd_per_credit() - egress_usd(sent_bytes)
    return max(0.0, left / running_usd(1))
