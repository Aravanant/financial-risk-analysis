"""Dual-backend database connection and health handling for RiskLens AI.

Enforces:
1. SQLite as default local-development and test backend when DATABASE_URL is unset.
2. PostgreSQL / Supabase connection support when DATABASE_URL is set, using SSL (sslmode=require).
3. Serverless-safe connection management: explicit per-request closure and autocommit mode.
4. Safe SQL parameter adaptation from '?' to '%s' preserving literals and comments.
5. Strict credential redaction in all error messages, health diagnostics, and logs.
6. Record count verification across fact, dimensions, and demo servicing tables.
"""

import os
import re
import sqlite3
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Generator, Dict, Any, Optional

try:
    import psycopg2
    import psycopg2.extensions
    import psycopg2.extras

    # Map PostgreSQL NUMERIC types to Python float so analytical schemas match SQLite baseline
    DEC2FLOAT = psycopg2.extensions.new_type(
        psycopg2.extensions.DECIMAL.values,
        'DEC2FLOAT',
        lambda value, curs: float(value) if value is not None else None
    )
    psycopg2.extensions.register_type(DEC2FLOAT)
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

from .config import settings


def sanitize_db_error(msg: str) -> str:
    """Strip credentials and passwords from database error messages to prevent leakage."""
    if not msg:
        return ""
    # Redact ://user:password@ format
    sanitized = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", msg)
    # Redact password=xxx format
    sanitized = re.sub(r"password=\S+", "password=***", sanitized)
    return sanitized


def enforce_sslmode(dsn: str) -> str:
    """
    Ensure the connection URI enforces SSL (sslmode=require).
    Safe for both postgresql:// and postgres:// formats.
    """
    if not dsn:
        return ""
    parsed = urlparse(dsn)
    qs = parse_qs(parsed.query)
    if "sslmode" not in qs:
        qs["sslmode"] = ["require"]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def adapt_sql_placeholders(sql: str) -> str:
    """
    Safely convert unquoted '?' query parameter placeholders to '%s' (PostgreSQL style).

    Guarantees:
    - Does NOT replace question marks inside single-quoted strings ('...')
    - Does NOT replace question marks inside double-quoted identifiers ("...")
    - Does NOT replace question marks inside line comments (-- ...)
    - Does NOT replace question marks inside block comments (/* ... */)
    """
    out = []
    i = 0
    n = len(sql)
    state = "NORMAL"  # NORMAL, S_QUOTE, D_QUOTE, LINE_COMMENT, BLOCK_COMMENT

    while i < n:
        ch = sql[i]
        next_ch = sql[i + 1] if i + 1 < n else ""

        if state == "NORMAL":
            if ch == "'":
                state = "S_QUOTE"
                out.append(ch)
            elif ch == '"':
                state = "D_QUOTE"
                out.append(ch)
            elif ch == "-" and next_ch == "-":
                state = "LINE_COMMENT"
                out.append(ch)
            elif ch == "/" and next_ch == "*":
                state = "BLOCK_COMMENT"
                out.append(ch)
            elif ch == "?":
                out.append("%s")
            else:
                out.append(ch)
        elif state == "S_QUOTE":
            out.append(ch)
            if ch == "'":
                if next_ch == "'":
                    out.append(next_ch)
                    i += 1
                else:
                    state = "NORMAL"
        elif state == "D_QUOTE":
            out.append(ch)
            if ch == '"':
                if next_ch == '"':
                    out.append(next_ch)
                    i += 1
                else:
                    state = "NORMAL"
        elif state == "LINE_COMMENT":
            out.append(ch)
            if ch == "\n":
                state = "NORMAL"
        elif state == "BLOCK_COMMENT":
            out.append(ch)
            if ch == "*" and next_ch == "/":
                out.append(next_ch)
                i += 1
                state = "NORMAL"
        i += 1

    return "".join(out)


class PostgresCursorWrapper:
    """
    Cursor wrapper that automatically adapts '?' placeholders to '%s'
    and delegates to a psycopg2 DictCursor.
    """
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query: str, params=None):
        adapted_query = adapt_sql_placeholders(query)
        if params is not None:
            return self._cursor.execute(adapted_query, params)
        return self._cursor.execute(adapted_query)

    def executemany(self, query: str, vars_list):
        adapted_query = adapt_sql_placeholders(query)
        return self._cursor.executemany(adapted_query, vars_list)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnectionWrapper:
    """
    Connection wrapper that provides PostgresCursorWrapper instances.
    """
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor())

    def close(self):
        self._conn.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_db_connection() -> Generator[Any, None, None]:
    """
    FastAPI dependency yielding a thread-safe database connection.

    Guarantees:
    - If DATABASE_URL is set: connects to Supabase/PostgreSQL via psycopg2 with SSL (sslmode=require),
      using autocommit mode (serverless / transaction pooler safe) and clean per-request closure.
    - If DATABASE_URL is unset: connects to local verified SQLite warehouse in read-only mode (mode=ro).
    - Connection is cleanly closed upon request completion even if exceptions occur.
    """
    if settings.is_postgres:
        if not HAS_PSYCOPG2:
            raise RuntimeError("psycopg2-binary is required for PostgreSQL support but is not installed.")
        dsn = enforce_sslmode(settings.DATABASE_URL)
        conn = psycopg2.connect(
            dsn,
            cursor_factory=psycopg2.extras.DictCursor,
            connect_timeout=10
        )
        conn.autocommit = True
        wrapped_conn = PostgresConnectionWrapper(conn)
        try:
            yield wrapped_conn
        finally:
            conn.close()
    else:
        if not os.path.exists(settings.DB_PATH):
            raise FileNotFoundError(f"Analytics database not found at: {settings.DB_PATH}")

        db_uri = f"file:{os.path.abspath(settings.DB_PATH)}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def check_db_health() -> Dict[str, Any]:
    """
    Inspect database connectivity, backend engine, schema version, and core table row counts.
    Never exposes passwords, tokens, or sensitive credentials in error messages.
    """
    if settings.is_postgres:
        if not HAS_PSYCOPG2:
            return {
                "status": "unhealthy",
                "connected": False,
                "database_backend": "postgresql",
                "error": "psycopg2-binary is not installed"
            }

        try:
            dsn = enforce_sslmode(settings.DATABASE_URL)
            conn = psycopg2.connect(
                dsn,
                cursor_factory=psycopg2.extras.DictCursor,
                connect_timeout=5
            )
            conn.autocommit = True
            cur = conn.cursor()

            # Verify query execution
            cur.execute("SELECT 1 AS ping;")
            ping = cur.fetchone()["ping"]

            # Query physical database size
            db_size_bytes: Optional[int] = None
            try:
                cur.execute("SELECT pg_database_size(current_database()) AS db_size;")
                db_size_bytes = cur.fetchone()["db_size"]
            except Exception:
                db_size_bytes = None

            # Verify core fact, dimension, and quarantined servicing counts
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM fct_loan_application) AS fct_count,
                    (SELECT COUNT(*) FROM dim_channel) AS channel_count,
                    (SELECT COUNT(*) FROM dim_loan_purpose) AS purpose_count,
                    (SELECT COUNT(*) FROM dim_residence_property_location) AS location_count,
                    (SELECT COUNT(*) FROM demo_synthetic_repayment_snapshot) AS demo_servicing_count;
            """)
            counts = dict(cur.fetchone())
            conn.close()

            is_healthy = (
                ping == 1 and
                counts["fct_count"] == 100000 and
                counts["channel_count"] == 4 and
                counts["purpose_count"] == 8 and
                counts["location_count"] == 75 and
                counts["demo_servicing_count"] == 48596
            )

            return {
                "status": "healthy" if is_healthy else "degraded",
                "connected": True,
                "database_backend": "postgresql",
                "database_size_bytes": db_size_bytes,
                "schema_version": settings.SCHEMA_VERSION,
                "record_counts": counts
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "connected": False,
                "database_backend": "postgresql",
                "error": sanitize_db_error(str(exc))
            }
    else:
        if not os.path.exists(settings.DB_PATH):
            return {
                "status": "unhealthy",
                "connected": False,
                "database_backend": "sqlite",
                "error": "Database file does not exist on disk"
            }

        db_size_bytes = os.path.getsize(settings.DB_PATH)
        db_uri = f"file:{os.path.abspath(settings.DB_PATH)}?mode=ro"

        try:
            conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Verify query execution
            cur.execute("SELECT 1 AS ping;")
            ping = cur.fetchone()["ping"]

            # Verify core fact and dimension counts
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM fct_loan_application) AS fct_count,
                    (SELECT COUNT(*) FROM dim_channel) AS channel_count,
                    (SELECT COUNT(*) FROM dim_loan_purpose) AS purpose_count,
                    (SELECT COUNT(*) FROM dim_residence_property_location) AS location_count,
                    (SELECT COUNT(*) FROM demo_synthetic_repayment_snapshot) AS demo_servicing_count;
            """)
            counts = dict(cur.fetchone())
            conn.close()

            is_healthy = (
                ping == 1 and
                counts["fct_count"] == 100000 and
                counts["channel_count"] == 4 and
                counts["purpose_count"] == 8 and
                counts["location_count"] == 75 and
                counts["demo_servicing_count"] == 48596
            )

            return {
                "status": "healthy" if is_healthy else "degraded",
                "connected": True,
                "database_backend": "sqlite",
                "database_size_bytes": db_size_bytes,
                "schema_version": settings.SCHEMA_VERSION,
                "record_counts": counts
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "connected": False,
                "database_backend": "sqlite",
                "error": sanitize_db_error(str(exc))
            }
