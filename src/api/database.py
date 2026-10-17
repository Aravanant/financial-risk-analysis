"""Thread-safe SQLite connection handling for RiskLens AI.

Enforces:
1. Strict read-only mode via SQLite URI (?mode=ro) to prevent mutation through API.
2. Context manager and FastAPI dependency injection pattern for per-request isolation.
3. Row factory configured to sqlite3.Row for dict-like column access.
4. Database health inspection and table record counts.
"""

import os
import sqlite3
from typing import Generator, Dict, Any
from .config import settings


def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency yielding a thread-safe, read-only SQLite database connection.
    
    Guarantees:
    - Connection is opened in read-only mode (mode=ro).
    - Connection is cleanly closed upon request completion even if exceptions occur.
    """
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
    """Inspect database connectivity, schema version, and core table row counts."""
    if not os.path.exists(settings.DB_PATH):
        return {
            "status": "unhealthy",
            "connected": False,
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
            counts["location_count"] == 75
        )
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "connected": True,
            "database_size_bytes": db_size_bytes,
            "schema_version": settings.SCHEMA_VERSION,
            "record_counts": counts
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(exc)
        }
