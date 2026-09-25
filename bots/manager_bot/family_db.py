#!/usr/bin/env python3
"""Download the whole family database, and upload it back.

    python family_db.py backup  --from cloud --out backups/family.zip
    python family_db.py restore --into local --file backups/family.zip
    python family_db.py copy    --from cloud --into local
    python family_db.py tables  --at cloud

"local" and "cloud" are aliases read from DATABASE_URL (or
LOCAL_DATABASE_URL) and CLOUD_DATABASE_URL, out of the environment or the
.env next to this file. Any full postgresql:// URL works in their place.

WHY THIS EXISTS ALONGSIDE db_backup.ps1
    db_backup.ps1 wraps pg_dump/pg_restore and produces a true, complete
    backup -- indexes, constraints, sequences, ownership, the lot. Use it
    when you want a restorable snapshot. Its one weakness is that pg_dump
    refuses to talk to a server newer than itself, which bites the moment
    Railway upgrades its Postgres past whatever your laptop has installed.

    This script talks to the server through the same psycopg the bots use,
    so no local Postgres installation is involved and no version can
    mismatch. It moves *data*, not structure: the target's tables have to
    already exist, which they do as soon as each bot has started once
    against that database. That makes it the right tool for the everyday
    job -- "pull what the deployed bots have collected down to my laptop",
    and "push what I changed locally back up".

MODES for restore/copy
    merge (default)  Insert rows the target does not already have, matched
                     by that table's own primary key / unique constraints.
                     Nothing is deleted, nothing existing is overwritten.
                     Safe to run repeatedly.
    replace          Empty each table first, then load. The target ends up
                     an exact copy of the source. Asks for confirmation
                     unless --yes, because it does destroy rows.
"""
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

# Schemas that belong to Postgres itself, or to the Supabase platform,
# rather than to the family. The Supabase-managed ones are recreated per
# project, are never the family's own data, and several of them carry
# things this CSV-merge tool cannot round-trip -- generated columns
# (auth.identities.email) and views exposed as tables (vault.secrets).
# list_tables() also always skips pg_% and supabase_%.
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
        # %% rather than %: this statement carries parameters, so psycopg reads
        # a bare % as the start of a placeholder.
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
        # A generated column cannot appear in a COPY column list (either
        # direction), and a STORED one is recomputed on insert anyway, so
        # dropping it from both the backup and the restore is necessary and
        # lossless. Supabase's auth.identities.email is the one that bites.
        "AND is_generated = 'NEVER' "
        "ORDER BY ordinal_position",
        (schema, table),
    )
    return [row[0] for row in cur.fetchall()]


def quoted(cols: list[str]) -> str:
    return ", ".join(f'"{c}"' for c in cols)


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------

def backup(dsn: str, out_path: Path, schemas: list[str] | None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": "csv-copy-v1",
        "tables": [],
    }
    # Level 9: CSV is most of what a database is, it compresses several
    # times over, and the archive is made rarely and kept a long time --
    # including as a Telegram document, where every megabyte under the 50 MB
    # ceiling is a part fewer to join back together.
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
            rows = max(payload.count(b"\n") - 1, 0)  # minus the header
            manifest["tables"].append(
                {"schema": schema, "table": table, "columns": cols, "approx_rows": rows}
            )
            print(f"  {schema}.{table}: ~{rows} row(s)")
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))

    size = out_path.stat().st_size
    print(f"\nWrote {out_path} ({size/1024:.0f} KB, {len(manifest['tables'])} table(s)).")


# ---------------------------------------------------------------------------
# restore
# ---------------------------------------------------------------------------

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
                # Resync from the columns that actually landed, not the ones
                # the archive happened to carry. A column the target does not
                # have is not merely empty to pg_get_serial_sequence -- it
                # raises UndefinedColumn, which would abort the whole restore
                # transaction *after* every row had been copied into it.
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
    """COPY straight in. `usable` may be narrower than the archive's columns,
    in which case the CSV is re-read through a staging table instead."""
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
    """Additive: load into a staging copy of the table, then insert only the
    rows the target does not already have. ON CONFLICT DO NOTHING with no
    conflict target covers every unique constraint the table has at once,
    which is exactly the "never overwrite, never delete" policy the bots'
    own db_merge.py already follows."""
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
    """Drops columns the target no longer has. Rare -- it only happens when
    restoring an archive taken before a schema change -- so this goes
    through Python's csv module rather than complicating the COPY path."""
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
    """Every bot's tables use BIGSERIAL ids. Copying rows carries their id
    values across but not the sequence behind them, so without this the very
    next insert would collide with a restored row."""
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


# ---------------------------------------------------------------------------

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
