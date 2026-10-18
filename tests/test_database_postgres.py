"""Unit Test Suite for PostgreSQL / Supabase Integration Layer (Mocked).

IMPORTANT:
These are pure unit and mock tests validating PostgreSQL driver configuration,
SQL placeholder lexing, credential redaction, SSL enforcement, and schema DDL integrity.
They DO NOT require or claim to test against a live Supabase database instance.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.config import Settings
from src.api.database import (
    adapt_sql_placeholders,
    sanitize_db_error,
    enforce_sslmode,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
    check_db_health,
    get_db_connection
)
from src.data.schema import POSTGRES_TABLE_DDL, POSTGRES_VIEW_DDL, POSTGRES_DDL_STATEMENTS


class TestPostgresUnitConfiguration(unittest.TestCase):
    """Unit tests for configuration helpers, SSL enforcement, and credential redaction."""

    def test_01_sql_placeholder_adaptation_standard(self):
        """Verify standard '?' parameter placeholders are converted to '%s'."""
        sql = "SELECT * FROM fct_loan_application WHERE application_id = ?;"
        adapted = adapt_sql_placeholders(sql)
        self.assertEqual(adapted, "SELECT * FROM fct_loan_application WHERE application_id = %s;")

    def test_02_sql_placeholder_multiple_and_pagination(self):
        """Verify multiple filters and LIMIT/OFFSET placeholders are converted."""
        sql = """
            SELECT * FROM fct_loan_application f
            WHERE f.underwriting_decision = ? AND f.risk_tier = ?
            LIMIT ? OFFSET ?;
        """
        adapted = adapt_sql_placeholders(sql)
        self.assertEqual(adapted.count("%s"), 4)
        self.assertNotIn("?", adapted)

    def test_03_sql_placeholder_preserves_single_quoted_literals(self):
        """Verify question marks inside single-quoted strings are NOT replaced."""
        sql = "SELECT 'Is this a question?' AS title, ? AS id FROM tbl WHERE name = 'who?';"
        adapted = adapt_sql_placeholders(sql)
        self.assertIn("'Is this a question?'", adapted)
        self.assertIn("'who?'", adapted)
        self.assertIn("%s AS id", adapted)
        self.assertEqual(adapted.count("%s"), 1)

    def test_04_sql_placeholder_preserves_escaped_quotes(self):
        """Verify escaped single quotes ('') in strings are handled properly."""
        sql = "SELECT 'It''s a question?' FROM tbl WHERE id = ?;"
        adapted = adapt_sql_placeholders(sql)
        self.assertIn("'It''s a question?'", adapted)
        self.assertIn("id = %s", adapted)
        self.assertEqual(adapted.count("%s"), 1)

    def test_05_sql_placeholder_preserves_double_quoted_identifiers(self):
        """Verify question marks inside double-quoted identifiers are preserved."""
        sql = 'SELECT "col?name", f.id FROM tbl WHERE id = ?;'
        adapted = adapt_sql_placeholders(sql)
        self.assertIn('"col?name"', adapted)
        self.assertIn("id = %s", adapted)
        self.assertEqual(adapted.count("%s"), 1)

    def test_06_sql_placeholder_preserves_comments(self):
        """Verify question marks inside line comments and block comments are preserved."""
        sql = """
            -- Is this a comment with ? question mark
            SELECT * FROM tbl /* block comment with ? */ WHERE id = ?;
        """
        adapted = adapt_sql_placeholders(sql)
        self.assertIn("-- Is this a comment with ? question mark", adapted)
        self.assertIn("/* block comment with ? */", adapted)
        self.assertIn("WHERE id = %s;", adapted)
        self.assertEqual(adapted.count("%s"), 1)

    def test_07_credential_sanitization_uri(self):
        """Verify sanitize_db_error redacts passwords in standard connection strings."""
        raw_error = "FATAL: password authentication failed for user 'postgres' at postgresql://postgres:SecretPassword123@db.supabase.co:5432/postgres"
        cleaned = sanitize_db_error(raw_error)
        self.assertNotIn("SecretPassword123", cleaned)
        self.assertIn("postgresql://postgres:***@db.supabase.co:5432/postgres", cleaned)

    def test_08_credential_sanitization_key_value(self):
        """Verify sanitize_db_error redacts key-value password formats."""
        raw_error = "Connection failed: host=db.supabase.co port=5432 password=SuperSecretToken dbname=postgres"
        cleaned = sanitize_db_error(raw_error)
        self.assertNotIn("SuperSecretToken", cleaned)
        self.assertIn("password=***", cleaned)

    def test_09_masked_database_url_property(self):
        """Verify Settings.masked_database_url masks credentials properly."""
        s = Settings()
        s.DATABASE_URL = "postgresql://postgres:topsecretpassword@db.projectref.supabase.co:5432/postgres"
        self.assertNotIn("topsecretpassword", s.masked_database_url)
        self.assertEqual(s.masked_database_url, "postgresql://postgres:***@db.projectref.supabase.co:5432/postgres")

        # Unset DATABASE_URL
        s.DATABASE_URL = None
        self.assertIsNone(s.masked_database_url)

    def test_10_ssl_mode_enforcement(self):
        """Verify enforce_sslmode enforces sslmode=require without duplicate params."""
        # Without sslmode
        url = "postgresql://user:pass@db.supabase.co:5432/postgres"
        enforced = enforce_sslmode(url)
        self.assertIn("sslmode=require", enforced)

        # With existing sslmode
        url_with_ssl = "postgresql://user:pass@db.supabase.co:5432/postgres?sslmode=require"
        enforced_same = enforce_sslmode(url_with_ssl)
        self.assertEqual(enforced_same.count("sslmode=require"), 1)

        # With postgres:// prefix
        url_postgres = "postgres://user:pass@db.supabase.co:6543/postgres"
        enforced_pg = enforce_sslmode(url_postgres)
        self.assertIn("sslmode=require", enforced_pg)

    def test_11_schema_ddl_completeness(self):
        """Verify POSTGRES_DDL_STATEMENTS contains all required tables, indexes, and all 7 views."""
        # Verify 4 tables + 6 indexes
        self.assertGreaterEqual(len(POSTGRES_TABLE_DDL), 7)
        table_ddl_text = " ".join(POSTGRES_TABLE_DDL)
        self.assertIn("dim_residence_property_location", table_ddl_text)
        self.assertIn("dim_channel", table_ddl_text)
        self.assertIn("dim_loan_purpose", table_ddl_text)
        self.assertIn("fct_loan_application", table_ddl_text)
        self.assertIn("demo_synthetic_repayment_snapshot", table_ddl_text)
        self.assertIn("chk_decision_consistency", table_ddl_text)

        # Verify EXACTLY 7 conformed analytical views
        self.assertEqual(len(POSTGRES_VIEW_DDL), 7)
        expected_views = [
            "vw_portfolio_kpis",
            "vw_channel_performance",
            "vw_loan_purpose_analysis",
            "vw_underwriting_haircut",
            "vw_portfolio_haircut_summary",
            "vw_risk_tier_summary",
            "vw_data_quality_metrics"
        ]
        for v in expected_views:
            view_found = any(f"CREATE OR REPLACE VIEW {v}" in ddl for ddl in POSTGRES_VIEW_DDL)
            self.assertTrue(view_found, f"Expected view {v} not found in POSTGRES_VIEW_DDL")

        self.assertEqual(len(POSTGRES_DDL_STATEMENTS), len(POSTGRES_TABLE_DDL) + len(POSTGRES_VIEW_DDL))


class TestPostgresMockedConnectionAndHealth(unittest.TestCase):
    """Mocked unit tests for connection handling, wrappers, and health inspection."""

    def test_12_cursor_wrapper_adapts_query(self):
        """Verify PostgresCursorWrapper translates '?' and delegates to underlying cursor."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"total": 100}

        wrapper = PostgresCursorWrapper(mock_cursor)
        wrapper.execute("SELECT * FROM tbl WHERE id = ?;", (42,))

        # Verify underlying call used %s
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM tbl WHERE id = %s;",
            (42,)
        )
        result = wrapper.fetchone()
        self.assertEqual(result["total"], 100)

    def test_13_connection_wrapper_provides_wrapped_cursor(self):
        """Verify PostgresConnectionWrapper produces PostgresCursorWrapper."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        conn_wrapper = PostgresConnectionWrapper(mock_conn)
        cur = conn_wrapper.cursor()
        self.assertIsInstance(cur, PostgresCursorWrapper)

    @patch("src.api.database.settings")
    @patch("src.api.database.psycopg2.connect")
    def test_14_mocked_health_check_healthy(self, mock_connect, mock_settings):
        """Verify check_db_health returns healthy when PostgreSQL returns verified baseline counts."""
        mock_settings.is_postgres = True
        mock_settings.DATABASE_URL = "postgresql://user:pass@host:5432/db"
        mock_settings.SCHEMA_VERSION = "2.0.0"

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur

        # Ping
        mock_cur.fetchone.side_effect = [
            {"ping": 1},
            {"db_size": 42000000},
            {
                "fct_count": 100000,
                "channel_count": 4,
                "purpose_count": 8,
                "location_count": 75,
                "demo_servicing_count": 48596
            }
        ]

        health = check_db_health()
        self.assertEqual(health["status"], "healthy")
        self.assertTrue(health["connected"])
        self.assertEqual(health["database_backend"], "postgresql")
        self.assertEqual(health["record_counts"]["fct_count"], 100000)

    @patch("src.api.database.settings")
    @patch("src.api.database.psycopg2.connect")
    def test_15_mocked_health_check_connection_failure_masks_secret(self, mock_connect, mock_settings):
        """Verify check_db_health catches connection error and masks credentials in output."""
        mock_settings.is_postgres = True
        mock_settings.DATABASE_URL = "postgresql://postgres:secret123@db.supabase.co:5432/postgres"

        mock_connect.side_effect = Exception("Failed connecting to postgresql://postgres:secret123@db.supabase.co:5432/postgres")

        health = check_db_health()
        self.assertEqual(health["status"], "unhealthy")
        self.assertFalse(health["connected"])
        self.assertEqual(health["database_backend"], "postgresql")
        self.assertNotIn("secret123", health["error"])
        self.assertIn("postgresql://postgres:***@", health["error"])


if __name__ == "__main__":
    unittest.main()
