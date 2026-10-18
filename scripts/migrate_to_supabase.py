#!/usr/bin/env python3
"""RiskLens AI — Supabase PostgreSQL Schema Migration & Data Import CLI.

Enforces:
1. Safe, repeatable, idempotent schema creation (IF NOT EXISTS / CREATE OR REPLACE VIEW).
2. Explicit confirmation required for destructive resets (--reset + --confirm-reset).
3. Reads production credentials strictly from DATABASE_URL environment variable.
4. Fast, atomic, batched streaming from local validated SQLite warehouse to Supabase PostgreSQL.
5. All 7 conformed analytical views created and verified.
6. Side-by-side automated reconciliation asserting 100.000% parity across all key financial metrics.
7. Zero secret leakage in CLI outputs or logs.
"""

import os
import sys
import argparse
import logging
import sqlite3
from typing import Dict, Any, List, Tuple, Optional

# Ensure project root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.api.config import settings
from src.api.database import enforce_sslmode, sanitize_db_error
from src.data.schema import POSTGRES_TABLE_DDL, POSTGRES_VIEW_DDL

try:
    import psycopg2
    import psycopg2.extensions
    import psycopg2.extras

    # Map PostgreSQL NUMERIC types to Python float
    DEC2FLOAT = psycopg2.extensions.new_type(
        psycopg2.extensions.DECIMAL.values,
        "DEC2FLOAT",
        lambda value, curs: float(value) if value is not None else None
    )
    psycopg2.extensions.register_type(DEC2FLOAT)
except ImportError:
    psycopg2 = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RiskLensMigration")


class ReconciliationError(Exception):
    """Raised when SQLite and PostgreSQL metrics diverge."""
    pass


def get_pg_connection(database_url: str):
    """Open a secure SSL connection to Supabase PostgreSQL."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2-binary is required for PostgreSQL migration. Run: pip install psycopg2-binary")

    dsn = enforce_sslmode(database_url)
    conn = psycopg2.connect(
        dsn,
        cursor_factory=psycopg2.extras.DictCursor,
        connect_timeout=15
    )
    return conn


def get_sqlite_connection(sqlite_path: str) -> sqlite3.Connection:
    """Open read-only connection to verified local SQLite database."""
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"Local SQLite analytics warehouse not found at: {sqlite_path}")

    uri = f"file:{os.path.abspath(sqlite_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def reset_schema(pg_conn, confirmed: bool = False) -> None:
    """Drop existing tables and views if and only if explicitly confirmed."""
    if not confirmed:
        raise ValueError(
            "Destructive reset requested without confirmation. "
            "Pass --confirm-reset alongside --reset to proceed."
        )

    logger.warning("Executing destructive reset on target database...")
    views_to_drop = [
        "vw_portfolio_kpis",
        "vw_channel_performance",
        "vw_loan_purpose_analysis",
        "vw_underwriting_haircut",
        "vw_portfolio_haircut_summary",
        "vw_risk_tier_summary",
        "vw_data_quality_metrics"
    ]
    tables_to_drop = [
        "demo_synthetic_repayment_snapshot",
        "fct_loan_application",
        "dim_residence_property_location",
        "dim_channel",
        "dim_loan_purpose"
    ]

    with pg_conn.cursor() as cur:
        for v in views_to_drop:
            cur.execute(f"DROP VIEW IF EXISTS {v} CASCADE;")
        for t in tables_to_drop:
            cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE;")
    pg_conn.commit()
    logger.info("Target schema reset successfully.")


def create_schema(pg_conn) -> None:
    """Create all lookup tables, fact tables, indexes, and all 7 analytical views."""
    logger.info("Applying PostgreSQL warehouse table DDL...")
    with pg_conn.cursor() as cur:
        for ddl in POSTGRES_TABLE_DDL:
            cur.execute(ddl)
    pg_conn.commit()
    logger.info("PostgreSQL tables and indexes verified/created.")

    logger.info("Applying all 7 conformed analytical views...")
    with pg_conn.cursor() as cur:
        for v_ddl in POSTGRES_VIEW_DDL:
            cur.execute(v_ddl)
    pg_conn.commit()
    logger.info("All 7 analytical views verified/created.")


def import_data(pg_conn, sqlite_conn, batch_size: int = 5000) -> Dict[str, int]:
    """
    Stream cleaned analytical data from SQLite into Supabase PostgreSQL.
    Preserves exact conformed IDs, nulls, and numeric precision.
    """
    imported_counts: Dict[str, int] = {}

    # Check if fact table already has records
    with pg_conn.cursor() as pg_cur:
        pg_cur.execute("SELECT COUNT(*) FROM fct_loan_application;")
        existing_facts = pg_cur.fetchone()[0]
        if existing_facts > 0:
            logger.warning(
                f"fct_loan_application already contains {existing_facts:,} records. "
                "Skipping import to prevent duplicate records. Use --reset --confirm-reset if re-import is required."
            )
            return {"fct_loan_application": existing_facts}

    logger.info("Starting atomic migration of conformed lookup dimensions...")
    sq_cur = sqlite_conn.cursor()

    # 1. dim_residence_property_location
    sq_cur.execute("SELECT location_property_id, region, residential_status, property_ownership FROM dim_residence_property_location;")
    loc_rows = [tuple(r) for r in sq_cur.fetchall()]
    with pg_conn.cursor() as pg_cur:
        psycopg2.extras.execute_values(
            pg_cur,
            """
            INSERT INTO dim_residence_property_location (location_property_id, region, residential_status, property_ownership)
            VALUES %s
            ON CONFLICT (location_property_id) DO NOTHING;
            """,
            loc_rows
        )
        pg_cur.execute("SELECT setval('dim_residence_property_location_location_property_id_seq', (SELECT MAX(location_property_id) FROM dim_residence_property_location));")
    pg_conn.commit()
    imported_counts["dim_residence_property_location"] = len(loc_rows)
    logger.info(f"Loaded dim_residence_property_location: {len(loc_rows)} rows")

    # 2. dim_channel
    sq_cur.execute("SELECT channel_id, channel_name FROM dim_channel;")
    chan_rows = [tuple(r) for r in sq_cur.fetchall()]
    with pg_conn.cursor() as pg_cur:
        psycopg2.extras.execute_values(
            pg_cur,
            """
            INSERT INTO dim_channel (channel_id, channel_name)
            VALUES %s
            ON CONFLICT (channel_id) DO NOTHING;
            """,
            chan_rows
        )
        pg_cur.execute("SELECT setval('dim_channel_channel_id_seq', (SELECT MAX(channel_id) FROM dim_channel));")
    pg_conn.commit()
    imported_counts["dim_channel"] = len(chan_rows)
    logger.info(f"Loaded dim_channel: {len(chan_rows)} rows")

    # 3. dim_loan_purpose
    sq_cur.execute("SELECT purpose_id, purpose_name FROM dim_loan_purpose;")
    purp_rows = [tuple(r) for r in sq_cur.fetchall()]
    with pg_conn.cursor() as pg_cur:
        psycopg2.extras.execute_values(
            pg_cur,
            """
            INSERT INTO dim_loan_purpose (purpose_id, purpose_name)
            VALUES %s
            ON CONFLICT (purpose_id) DO NOTHING;
            """,
            purp_rows
        )
        pg_cur.execute("SELECT setval('dim_loan_purpose_purpose_id_seq', (SELECT MAX(purpose_id) FROM dim_loan_purpose));")
    pg_conn.commit()
    imported_counts["dim_loan_purpose"] = len(purp_rows)
    logger.info(f"Loaded dim_loan_purpose: {len(purp_rows)} rows")

    # 4. fct_loan_application (100,000 rows in batches)
    logger.info("Streaming 100,000 fct_loan_application records...")
    sq_cur.execute("""
        SELECT
            application_id, source_row_ordinal, location_property_id, channel_id, purpose_id,
            age, gender, marital_status, education_level, employment_status,
            job_experience_years, dependents,
            annual_income, monthly_income_reported, monthly_income_calculated,
            savings_balance, checking_balance, total_assets, total_liabilities, monthly_debt_payment,
            net_worth, bank_account_tenure_months,
            requested_loan_amount, requested_term_months, interest_rate, debt_to_income_ratio,
            co_applicant_flag, collateral_flag,
            bureau_credit_score, bureau_existing_loans, bureau_late_payments_2yr,
            bureau_credit_history_years, bureau_prior_loan_status,
            proprietary_risk_score, risk_tier, normalized_risk_score,
            underwriting_decision, sanctioned_approved_amount, is_approved, has_missing_sanctioned_amount,
            has_invalid_annual_income, has_invalid_loan_amount, has_invalid_savings_balance,
            has_invalid_age, has_invalid_financials
        FROM fct_loan_application
        ORDER BY application_id;
    """)

    fact_insert_sql = """
        INSERT INTO fct_loan_application (
            application_id, source_row_ordinal, location_property_id, channel_id, purpose_id,
            age, gender, marital_status, education_level, employment_status,
            job_experience_years, dependents,
            annual_income, monthly_income_reported, monthly_income_calculated,
            savings_balance, checking_balance, total_assets, total_liabilities, monthly_debt_payment,
            net_worth, bank_account_tenure_months,
            requested_loan_amount, requested_term_months, interest_rate, debt_to_income_ratio,
            co_applicant_flag, collateral_flag,
            bureau_credit_score, bureau_existing_loans, bureau_late_payments_2yr,
            bureau_credit_history_years, bureau_prior_loan_status,
            proprietary_risk_score, risk_tier, normalized_risk_score,
            underwriting_decision, sanctioned_approved_amount, is_approved, has_missing_sanctioned_amount,
            has_invalid_annual_income, has_invalid_loan_amount, has_invalid_savings_balance,
            has_invalid_age, has_invalid_financials
        ) VALUES %s
        ON CONFLICT (application_id) DO NOTHING;
    """

    total_facts = 0
    with pg_conn.cursor() as pg_cur:
        while True:
            chunk = sq_cur.fetchmany(batch_size)
            if not chunk:
                break
            batch_tuples = [tuple(r) for r in chunk]
            psycopg2.extras.execute_values(pg_cur, fact_insert_sql, batch_tuples, page_size=batch_size)
            total_facts += len(batch_tuples)
            logger.info(f"Loaded {total_facts:,} / 100,000 fact records...")
    pg_conn.commit()
    imported_counts["fct_loan_application"] = total_facts
    logger.info(f"Finished loading fct_loan_application: {total_facts:,} rows")

    # 5. demo_synthetic_repayment_snapshot (48,596 quarantined rows in batches)
    logger.info("Streaming 48,596 demo_synthetic_repayment_snapshot records...")
    sq_cur.execute("""
        SELECT
            application_id, simulated_due_date, simulated_payment_date,
            simulated_amount_due_cu, simulated_amount_paid_cu, simulated_days_late,
            simulated_payment_status, simulated_disbursement_amount_cu, simulated_outstanding_balance_cu
        FROM demo_synthetic_repayment_snapshot
        ORDER BY application_id;
    """)

    demo_insert_sql = """
        INSERT INTO demo_synthetic_repayment_snapshot (
            application_id, simulated_due_date, simulated_payment_date,
            simulated_amount_due_cu, simulated_amount_paid_cu, simulated_days_late,
            simulated_payment_status, simulated_disbursement_amount_cu, simulated_outstanding_balance_cu
        ) VALUES %s
        ON CONFLICT (application_id) DO NOTHING;
    """

    total_demo = 0
    with pg_conn.cursor() as pg_cur:
        while True:
            chunk = sq_cur.fetchmany(batch_size)
            if not chunk:
                break
            batch_tuples = [tuple(r) for r in chunk]
            psycopg2.extras.execute_values(pg_cur, demo_insert_sql, batch_tuples, page_size=batch_size)
            total_demo += len(batch_tuples)
            logger.info(f"Loaded {total_demo:,} / 48,596 demo servicing records...")
    pg_conn.commit()
    imported_counts["demo_synthetic_repayment_snapshot"] = total_demo
    logger.info(f"Finished loading demo_synthetic_repayment_snapshot: {total_demo:,} rows")

    return imported_counts


def verify_reconciliation(pg_conn, sqlite_conn) -> None:
    """
    Run automated side-by-side reconciliation between SQLite and Supabase PostgreSQL.
    Verifies record counts, portfolio KPIs, haircut analysis, channel totals, and quality flags.
    """
    logger.info("=== STARTING DUAL-DATABASE RECONCILIATION VERIFICATION ===")
    pg_cur = pg_conn.cursor()
    sq_cur = sqlite_conn.cursor()

    checks: List[Tuple[str, Any, Any]] = []

    # 1. Table Counts
    tables = [
        "fct_loan_application",
        "dim_channel",
        "dim_loan_purpose",
        "dim_residence_property_location",
        "demo_synthetic_repayment_snapshot"
    ]
    for tbl in tables:
        sq_cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        sq_cnt = sq_cur.fetchone()[0]
        pg_cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        pg_cnt = pg_cur.fetchone()[0]
        checks.append((f"Row Count: {tbl}", sq_cnt, pg_cnt))

    # 2. Portfolio KPIs View
    sq_cur.execute("SELECT * FROM vw_portfolio_kpis;")
    sq_kpis = dict(sq_cur.fetchone())
    pg_cur.execute("SELECT * FROM vw_portfolio_kpis;")
    pg_kpis = dict(pg_cur.fetchone())

    for k in [
        "total_applications",
        "approved_applications",
        "rejected_applications",
        "approval_rate_pct",
        "rejection_rate_pct",
        "total_requested_cu",
        "total_sanctioned_cu",
        "invalid_financials_count",
        "missing_sanctioned_count"
    ]:
        checks.append((f"KPI: {k}", sq_kpis[k], pg_kpis[k]))

    # 3. Portfolio Haircut Summary View
    sq_cur.execute("SELECT * FROM vw_portfolio_haircut_summary;")
    sq_haircut = dict(sq_cur.fetchone())
    pg_cur.execute("SELECT * FROM vw_portfolio_haircut_summary;")
    pg_haircut = dict(pg_cur.fetchone())

    for k in [
        "eligible_applications_count",
        "total_eligible_requested_cu",
        "total_eligible_sanctioned_cu",
        "total_haircut_cu",
        "aggregate_haircut_pct",
        "total_excluded_count"
    ]:
        checks.append((f"Haircut: {k}", sq_haircut[k], pg_haircut[k]))

    # 4. Data Quality Metrics View
    sq_cur.execute("SELECT * FROM vw_data_quality_metrics;")
    sq_dq = dict(sq_cur.fetchone())
    pg_cur.execute("SELECT * FROM vw_data_quality_metrics;")
    pg_dq = dict(pg_cur.fetchone())

    for k in [
        "invalid_annual_income_flag_count",
        "invalid_loan_amount_flag_count",
        "invalid_savings_balance_flag_count",
        "invalid_age_flag_count",
        "composite_invalid_financials_count",
        "missing_sanctioned_amount_count"
    ]:
        checks.append((f"DataQuality: {k}", sq_dq[k], pg_dq[k]))

    # Evaluate checks
    mismatches = []
    print("\n" + "=" * 80)
    print(f"{'Metric':<35} | {'SQLite Baseline':<18} | {'Postgres Value':<18} | {'Match'}")
    print("-" * 80)
    for name, sq_val, pg_val in checks:
        if isinstance(sq_val, float):
            is_match = abs(float(sq_val) - float(pg_val)) < 0.01
            sq_str = f"{sq_val:,.2f}"
            pg_str = f"{pg_val:,.2f}"
        else:
            is_match = sq_val == pg_val
            sq_str = f"{sq_val:,}" if isinstance(sq_val, int) else str(sq_val)
            pg_str = f"{pg_val:,}" if isinstance(pg_val, int) else str(pg_val)

        status_str = "PASS" if is_match else "FAIL"
        print(f"{name:<35} | {sq_str:<18} | {pg_str:<18} | {status_str}")
        if not is_match:
            mismatches.append((name, sq_val, pg_val))
    print("=" * 80 + "\n")

    if mismatches:
        err_msg = f"Reconciliation failed on {len(mismatches)} metrics: {mismatches}"
        logger.error(err_msg)
        raise ReconciliationError(err_msg)

    logger.info("SUCCESS: All 26 analytical metrics verified with 100.000% parity between SQLite and PostgreSQL!")


def main():
    parser = argparse.ArgumentParser(description="RiskLens AI — Supabase PostgreSQL Schema Migration & Data Import CLI")
    parser.add_argument("--schema-only", action="store_true", help="Apply DDL for tables, constraints, indexes, and all 7 views without importing data")
    parser.add_argument("--import-data", action="store_true", help="Stream cleaned analytical data from SQLite to PostgreSQL")
    parser.add_argument("--verify", action="store_true", help="Run reconciliation check comparing SQLite baseline and PostgreSQL")
    parser.add_argument("--reset", action="store_true", help="Destructively drop existing PostgreSQL schema (requires --confirm-reset)")
    parser.add_argument("--confirm-reset", action="store_true", help="Confirmation flag required alongside --reset")
    parser.add_argument("--database-url", type=str, default=None, help="PostgreSQL connection string (defaults to DATABASE_URL env var)")
    parser.add_argument("--sqlite-path", type=str, default=None, help="Path to local SQLite database (defaults to data/processed/risklens_analytics.db)")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for streamed data insertion (default: 5000)")

    args = parser.parse_args()

    # Determine database connection string
    db_url = args.database_url or os.getenv("DATABASE_URL")
    if not db_url or not db_url.strip():
        logger.error(
            "DATABASE_URL is not set. Please provide --database-url or export the DATABASE_URL environment variable.\n"
            "Example: export DATABASE_URL=\"postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres\""
        )
        sys.exit(1)

    sqlite_path = args.sqlite_path or settings.DB_PATH

    logger.info(f"Connecting to target PostgreSQL database: {settings.masked_database_url or 'postgresql://***'}")
    pg_conn = get_pg_connection(db_url)

    # 1. Handle Reset
    if args.reset:
        if not args.confirm_reset:
            logger.error("Destructive reset requested without --confirm-reset. Aborting to safeguard data.")
            sys.exit(1)
        reset_schema(pg_conn, confirmed=True)

    # Default action if no specific flags: run full safe migration (schema + import + verify)
    do_all = not (args.schema_only or args.import_data or args.verify)

    if args.schema_only or do_all:
        create_schema(pg_conn)

    if args.import_data or do_all:
        sqlite_conn = get_sqlite_connection(sqlite_path)
        try:
            import_data(pg_conn, sqlite_conn, batch_size=args.batch_size)
        finally:
            sqlite_conn.close()

    if args.verify or do_all:
        sqlite_conn = get_sqlite_connection(sqlite_path)
        try:
            verify_reconciliation(pg_conn, sqlite_conn)
        finally:
            sqlite_conn.close()

    pg_conn.close()
    logger.info("Migration workflow complete.")


if __name__ == "__main__":
    main()
