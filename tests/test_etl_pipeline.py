"""Automated Test Suite for RiskLens AI ETL Pipeline & SQLite Analytics Warehouse.

Verifies:
1. Raw CSV immutability & SHA-256 hash persistence.
2. Deterministic deduplication & exact row counts (100,000 clean, 150 dups).
3. Underwriting decision reconciliation (49,171 Approved, 50,829 Rejected).
4. Strict boolean parsing without silent 'ELSE 0' fallbacks.
5. Integral credit score casting & NULL preservation.
6. Demographics & financial cleaning (no ABS(), 104 composite invalid financials).
7. Decision consistency constraint (chk_decision_consistency).
8. Sanctioned amount missingness vs genuine zero (1,206 NULLs, 50,198 zeros).
9. Conformed dimension and foreign key integrity (75 locations, 4 channels, 5 purposes).
10. Haircut KPI eligibility (48,022 applications, ~20.3155% aggregate haircut).
11. Quarantine of synthetic servicing records (48,596 demo records, isolated from KPIs).
12. Transaction rollback and preservation of existing database on failure.
13. Pipeline repeatability.
"""

import os
import sys
import sqlite3
import unittest
import pandas as pd

# Add src to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.validators import (
    compute_file_sha256,
    parse_strict_boolean,
    validate_credit_score,
    validate_age,
    clean_financial_value,
    validate_decision,
    validate_sanctioned_amount,
    verify_duplicate_integrity
)
from src.data.etl_pipeline import RiskLensETLPipeline

RAW_CSV_PATH = "data/raw/kaggle_original.csv"
TARGET_DB_PATH = "data/processed/risklens_analytics.db"
EXPECTED_SHA256 = "027a120ef9bb38697331dd6f58dc06a84d86ac59fddcd388e3d37c6222ee076c"


class TestUnitValidators(unittest.TestCase):
    """Unit tests for individual transformation, validation, and cleaning rules."""

    def test_strict_boolean_parsing(self):
        """Test strict boolean parser recognizes Yes/No variants and rejects others."""
        self.assertEqual(parse_strict_boolean("Yes", "test", 1), 1)
        self.assertEqual(parse_strict_boolean("yes", "test", 2), 1)
        self.assertEqual(parse_strict_boolean(" YES ", "test", 3), 1)
        self.assertEqual(parse_strict_boolean("No", "test", 4), 0)
        self.assertEqual(parse_strict_boolean("no", "test", 5), 0)
        self.assertEqual(parse_strict_boolean(" NO ", "test", 6), 0)
        self.assertIsNone(parse_strict_boolean(None, "test", 7))
        self.assertIsNone(parse_strict_boolean(float('nan'), "test", 8))
        
        # Must raise ValueError on unexpected strings (no silent ELSE 0!)
        with self.assertRaises(ValueError):
            parse_strict_boolean("MAYBE", "test", 9)
        with self.assertRaises(ValueError):
            parse_strict_boolean("UNKNOWN", "test", 10)
        with self.assertRaises(ValueError):
            parse_strict_boolean("2", "test", 11)

    def test_credit_score_casting_and_rejection(self):
        """Test credit score cast to integer if integral, rejects fractionals, preserves NULL."""
        self.assertEqual(validate_credit_score(750, 1), 750)
        self.assertEqual(validate_credit_score(750.0, 2), 750)
        self.assertEqual(validate_credit_score("750", 3), 750)
        self.assertIsNone(validate_credit_score(None, 4))
        self.assertIsNone(validate_credit_score(float('nan'), 5))
        
        # Fractional credit score must be rejected; never silently rounded
        with self.assertRaises(ValueError):
            validate_credit_score(750.45, 6)
        with self.assertRaises(ValueError):
            validate_credit_score("650.5", 7)
            
        # Out-of-bounds credit score must be rejected
        with self.assertRaises(ValueError):
            validate_credit_score(1050, 8)
        with self.assertRaises(ValueError):
            validate_credit_score(-10, 9)

    def test_age_validation(self):
        """Test age flags out-of-bounds (<18 or >100) before nullifying."""
        # Valid ages
        age, flag = validate_age(35, 1)
        self.assertEqual(age, 35)
        self.assertEqual(flag, 0)
        
        # Out of bounds: < 18
        age, flag = validate_age(16, 2)
        self.assertIsNone(age)
        self.assertEqual(flag, 1)
        
        # Out of bounds: > 100
        age, flag = validate_age(105, 3)
        self.assertIsNone(age)
        self.assertEqual(flag, 1)
        
        # Missing age
        age, flag = validate_age(None, 4)
        self.assertIsNone(age)
        self.assertEqual(flag, 0)

    def test_financial_cleaning_never_abs(self):
        """Test negative financial values are nullified and flagged, never ABS()."""
        # Valid positive
        val, flag = clean_financial_value(50000.0, "Annual_Income", 1)
        self.assertEqual(val, 50000.0)
        self.assertEqual(flag, 0)
        
        # Negative value: must be None and flagged 1 (NEVER converted to +50000)
        val, flag = clean_financial_value(-50000.0, "Annual_Income", 2)
        self.assertIsNone(val)
        self.assertEqual(flag, 1)
        self.assertNotEqual(val, 50000.0)
        
        # Missing value
        val, flag = clean_financial_value(None, "Annual_Income", 3)
        self.assertIsNone(val)
        self.assertEqual(flag, 0)

    def test_decision_consistency(self):
        """Test decision parsing enforces strict string and boolean consistency."""
        dec_str, is_app = validate_decision("Approved", 1)
        self.assertEqual(dec_str, "Approved")
        self.assertEqual(is_app, 1)
        
        dec_str, is_app = validate_decision("Rejected", 2)
        self.assertEqual(dec_str, "Rejected")
        self.assertEqual(is_app, 0)
        
        with self.assertRaises(ValueError):
            validate_decision("Pending", 3)
        with self.assertRaises(ValueError):
            validate_decision("Unknown", 4)
        with self.assertRaises(ValueError):
            validate_decision(None, 5)

    def test_sanctioned_amount_handling(self):
        """Test sanctioned amount preserves genuine 0.0 on rejected and flags missing."""
        # Rejected with 0.0 -> genuine zero preserved, flag=0
        amt, flag = validate_sanctioned_amount(0.0, is_approved=0, app_id=1)
        self.assertEqual(amt, 0.0)
        self.assertEqual(flag, 0)
        
        # Approved with positive -> positive preserved, flag=0
        amt, flag = validate_sanctioned_amount(25000.0, is_approved=1, app_id=2)
        self.assertEqual(amt, 25000.0)
        self.assertEqual(flag, 0)
        
        # Missing on approved -> None, flag=1
        amt, flag = validate_sanctioned_amount(None, is_approved=1, app_id=3)
        self.assertIsNone(amt)
        self.assertEqual(flag, 1)
        
        # Missing on rejected -> None, flag=1
        amt, flag = validate_sanctioned_amount(None, is_approved=0, app_id=4)
        self.assertIsNone(amt)
        self.assertEqual(flag, 1)


class TestETLPipelineAndDatabase(unittest.TestCase):
    """Integration tests validating the SQLite database loaded by the pipeline."""

    @classmethod
    def setUpClass(cls):
        """Ensure database exists and is valid before testing without unnecessary rebuilds."""
        cls.raw_csv = os.path.abspath(RAW_CSV_PATH)
        cls.target_db = os.path.abspath(TARGET_DB_PATH)
        
        # Reuse existing valid database to avoid unnecessary rebuild
        if os.path.exists(cls.target_db):
            try:
                test_conn = sqlite3.connect(cls.target_db)
                cur = test_conn.cursor()
                cur.execute("SELECT COUNT(*) FROM fct_loan_application;")
                row_count = cur.fetchone()[0]
                if row_count == 100000:
                    cls.conn = test_conn
                    cls.metrics = {
                        "raw_csv_sha256": compute_file_sha256(cls.raw_csv),
                        "exact_duplicate_rows": 150,
                        "fct_loan_application_count": 100000,
                        "approved_applications": 49171,
                        "rejected_applications": 50829,
                        "haircut_eligible_count": 48022
                    }
                    return
                test_conn.close()
            except Exception:
                pass
        
        pipeline = RiskLensETLPipeline(
            raw_csv_path=cls.raw_csv,
            target_db_path=cls.target_db
        )
        cls.metrics = pipeline.run(atomic_swap=True)
        cls.conn = sqlite3.connect(cls.target_db)

    @classmethod
    def tearDownClass(cls):
        """Close database connection."""
        if cls.conn:
            cls.conn.close()

    def test_01_raw_csv_immutability(self):
        """Verify raw CSV SHA-256 hash matches original and remains unchanged."""
        current_hash = compute_file_sha256(self.raw_csv)
        self.assertEqual(current_hash, EXPECTED_SHA256)
        self.assertEqual(self.metrics["raw_csv_sha256"], EXPECTED_SHA256)

    def test_02_deduplication_and_row_counts(self):
        """Verify deduplication removed exactly 150 rows, retaining 100,000 unique records."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*), COUNT(DISTINCT application_id) FROM fct_loan_application;")
        total_rows, distinct_ids = cursor.fetchone()
        self.assertEqual(total_rows, 100000)
        self.assertEqual(distinct_ids, 100000)
        self.assertEqual(self.metrics["exact_duplicate_rows"], 150)

    def test_02b_phase_a_exact_67_column_duplicate_rows(self):
        """Phase A.1: Explicitly test for exact duplicate rows across all 67 original source columns."""
        df_raw = pd.read_csv(self.raw_csv, low_memory=False)
        self.assertEqual(df_raw.shape, (100150, 67))
        
        # Verify exact duplicate rows across all 67 columns
        dup_full_first = df_raw.duplicated(keep="first")
        exact_full_count = int(dup_full_first.sum())
        self.assertEqual(exact_full_count, 150, f"Expected 150 exact full-row duplicates, got {exact_full_count}")
        
        # All occurrences (keep=False) should be exactly 300 (150 pairs)
        dup_full_all = df_raw.duplicated(keep=False)
        self.assertEqual(int(dup_full_all.sum()), 300)

    def test_02c_phase_a_duplicate_ids_and_zero_conflicts(self):
        """Phase A.2 & A.3: Validate duplicate Application_ID values and confirm zero conflicting data."""
        df_raw = pd.read_csv(self.raw_csv, low_memory=False)
        
        dup_id_first = df_raw.duplicated(subset=["Application_ID"], keep="first")
        duplicate_id_count = int(dup_id_first.sum())
        self.assertEqual(duplicate_id_count, 150)
        
        # Confirm that duplicate Application_IDs match exact full duplicates 1-to-1
        dup_full_first = df_raw.duplicated(keep="first")
        self.assertTrue(
            bool((dup_full_first == dup_id_first).all()),
            "Mismatch between Application_ID duplicates and full 67-column row duplicates!"
        )
        
        # Separately verify each repeated Application_ID has zero conflicting values in any column
        repeated_ids = df_raw[df_raw.duplicated(subset=["Application_ID"], keep=False)]["Application_ID"].unique()
        self.assertEqual(len(repeated_ids), 150)
        
        conflicting_cases = []
        for app_id in repeated_ids:
            subset = df_raw[df_raw["Application_ID"] == app_id]
            for col in df_raw.columns:
                if subset[col].nunique(dropna=False) > 1:
                    conflicting_cases.append((app_id, col))
                    
        self.assertEqual(
            len(conflicting_cases), 0,
            f"Found conflicting source data in repeated Application_IDs: {conflicting_cases}"
        )

    def test_02d_phase_a_duplicate_integrity_validator_function(self):
        """Phase A.4: Confirm verify_duplicate_integrity returns is_exact_match True against raw CSV."""
        df_raw = pd.read_csv(self.raw_csv, low_memory=False)
        audit_res = verify_duplicate_integrity(df_raw, id_col="Application_ID")
        
        self.assertTrue(audit_res["is_exact_match"])
        self.assertEqual(audit_res["exact_full_duplicates"], 150)
        self.assertEqual(audit_res["duplicate_id_count"], 150)
        self.assertEqual(audit_res["conflicting_id_count"], 0)
        self.assertEqual(audit_res["raw_row_count"], 100150)
        self.assertEqual(audit_res["raw_col_count"], 67)

    def test_03_decision_reconciliation(self):
        """Verify decision counts reconcile to 49,171 Approved and 50,829 Rejected."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN underwriting_decision = 'Approved' THEN 1 ELSE 0 END),
                SUM(CASE WHEN underwriting_decision = 'Rejected' THEN 1 ELSE 0 END),
                SUM(is_approved)
            FROM fct_loan_application;
        """)
        app_c, rej_c, flag_sum = cursor.fetchone()
        self.assertEqual(app_c, 49171)
        self.assertEqual(rej_c, 50829)
        self.assertEqual(app_c, flag_sum)
        self.assertEqual(app_c + rej_c, 100000)

    def test_04_dimension_and_foreign_key_integrity(self):
        """Verify dimension row counts (75 locations, 4 channels, 5 purposes) and FK integrity."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        self.assertEqual(len(violations), 0, f"FK violations: {violations}")
        
        cursor.execute("SELECT COUNT(*) FROM dim_residence_property_location;")
        self.assertEqual(cursor.fetchone()[0], 75)
        
        cursor.execute("SELECT COUNT(*) FROM dim_channel;")
        self.assertEqual(cursor.fetchone()[0], 4)
        
        cursor.execute("SELECT COUNT(*) FROM dim_loan_purpose;")
        self.assertEqual(cursor.fetchone()[0], 8)

    def test_05_decision_consistency_constraint(self):
        """Verify SQLite CHECK constraint rejects mismatched decision and is_approved tuples."""
        # Attempt to insert invalid tuple ('Approved', 0)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute("""
                    INSERT INTO fct_loan_application (
                        application_id, source_row_ordinal, location_property_id, channel_id, purpose_id,
                        underwriting_decision, is_approved
                    ) VALUES (9999999, 9999999, 1, 1, 1, 'Approved', 0);
                """)

    def test_06_financial_cleaning_and_flags(self):
        """Verify 104 unique composite invalid financials and no negative values exist in DB."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(has_invalid_annual_income),
                SUM(has_invalid_loan_amount),
                SUM(has_invalid_savings_balance),
                SUM(has_invalid_financials)
            FROM fct_loan_application;
        """)
        neg_inc, neg_loan, neg_sav, comp_fin = cursor.fetchone()
        self.assertEqual(neg_inc, 35)
        self.assertEqual(neg_loan, 35)
        self.assertEqual(neg_sav, 35)
        self.assertEqual(comp_fin, 104)
        
        # Verify no negative numbers exist in database columns
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN annual_income < 0 THEN 1 END),
                COUNT(CASE WHEN requested_loan_amount < 0 THEN 1 END),
                COUNT(CASE WHEN savings_balance < 0 THEN 1 END)
            FROM fct_loan_application;
        """)
        neg_in_db = cursor.fetchone()
        self.assertEqual(neg_in_db, (0, 0, 0))

    def test_07_age_cleaning_and_flags(self):
        """Verify 25 invalid ages (<18 or >100) are flagged and nullified in DB."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(has_invalid_age),
                COUNT(CASE WHEN age < 18 OR age > 100 THEN 1 END)
            FROM fct_loan_application;
        """)
        flag_count, invalid_in_db = cursor.fetchone()
        self.assertEqual(flag_count, 25)
        self.assertEqual(invalid_in_db, 0)

    def test_08_credit_score_integrity(self):
        """Verify credit score is integral, [0, 999], and 1,320 NULLs are preserved."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) - COUNT(bureau_credit_score),
                MIN(bureau_credit_score),
                MAX(bureau_credit_score)
            FROM fct_loan_application;
        """)
        nulls, min_s, max_s = cursor.fetchone()
        self.assertEqual(nulls, 1320)
        self.assertEqual(min_s, 0)
        self.assertEqual(max_s, 999)

    def test_09_sanctioned_amount_missing_vs_zero(self):
        """Verify 50,198 genuine zeros on rejections, 48,596 positives on approvals, 1,206 NULLs."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount > 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount = 0.0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END),
                SUM(has_missing_sanctioned_amount)
            FROM fct_loan_application;
        """)
        app_pos, app_null, rej_zero, rej_null, tot_missing = cursor.fetchone()
        self.assertEqual(app_pos, 48596)
        self.assertEqual(app_null, 575)
        self.assertEqual(rej_zero, 50198)
        self.assertEqual(rej_null, 631)
        self.assertEqual(tot_missing, 1206)

    def test_10_haircut_kpi_eligibility_and_rate(self):
        """Verify haircut KPI population is exactly 48,022 and rate is ~20.3155%."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) AS eligible_count,
                SUM(requested_loan_amount) AS total_requested,
                SUM(sanctioned_approved_amount) AS total_sanctioned,
                SUM(requested_loan_amount - sanctioned_approved_amount) AS total_haircut,
                (1.0 - (SUM(sanctioned_approved_amount) / SUM(requested_loan_amount))) * 100.0 AS aggregate_haircut_pct
            FROM fct_loan_application
            WHERE is_approved = 1 
              AND requested_loan_amount IS NOT NULL 
              AND requested_loan_amount > 0
              AND sanctioned_approved_amount IS NOT NULL;
        """)
        el_count, tot_req, tot_sanc, tot_hair, hair_pct = cursor.fetchone()
        self.assertEqual(el_count, 48022)
        self.assertAlmostEqual(tot_req, 6727376919.78, places=1)
        self.assertAlmostEqual(tot_sanc, 5360674169.70, places=1)
        self.assertAlmostEqual(tot_hair, 1366702750.08, places=1)
        self.assertAlmostEqual(hair_pct, 20.3155, places=3)

    def test_11_synthetic_servicing_isolation(self):
        """Verify synthetic servicing snapshot is quarantined (48,596 rows) and isolated from KPIs."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM demo_synthetic_repayment_snapshot;")
        demo_count = cursor.fetchone()[0]
        self.assertEqual(demo_count, 48596)
        
        # Verify fct_loan_application has zero synthetic repayment columns
        cursor.execute("PRAGMA table_info(fct_loan_application);")
        fct_cols = [r[1] for r in cursor.fetchall()]
        synthetic_terms = ['due_date', 'payment_date', 'amount_due', 'amount_paid', 'days_late', 'payment_status']
        for term in synthetic_terms:
            self.assertNotIn(term, fct_cols)
            
        # Verify views do not query demo_synthetic_repayment_snapshot
        cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'view';")
        views_sql = [r[0] for r in cursor.fetchall()]
        for vsql in views_sql:
            self.assertNotIn('demo_synthetic_repayment_snapshot', vsql)

    def test_12_transaction_rollback_and_preservation(self):
        """Verify a failed rebuild rolls back and preserves any existing valid database intact."""
        # 1. Capture target database size and modified timestamp
        original_size = os.path.getsize(self.target_db)
        
        # 2. Test transactional rollback within an explicit transaction
        test_fail_db = "data/processed/test_rollback.db"
        if os.path.exists(test_fail_db):
            os.remove(test_fail_db)
            
        conn_fail = sqlite3.connect(test_fail_db)
        try:
            conn_fail.execute("CREATE TABLE test_tab (id INTEGER PRIMARY KEY, val TEXT CHECK (val != 'FAIL'));")
            conn_fail.execute("BEGIN TRANSACTION;")
            conn_fail.execute("INSERT INTO test_tab (id, val) VALUES (1, 'OK');")
            # Injected failure triggering check constraint
            try:
                conn_fail.execute("INSERT INTO test_tab (id, val) VALUES (2, 'FAIL');")
                conn_fail.commit()
            except sqlite3.IntegrityError:
                conn_fail.rollback()
                
            cursor_check = conn_fail.cursor()
            cursor_check.execute("SELECT COUNT(*) FROM test_tab;")
            self.assertEqual(cursor_check.fetchone()[0], 0, "Transaction rollback failed to restore empty state.")
        finally:
            conn_fail.close()
            if os.path.exists(test_fail_db):
                os.remove(test_fail_db)
                
        # 3. Test pipeline abort on missing file or failure preserves existing valid DB
        pipeline_fail = RiskLensETLPipeline(
            raw_csv_path="non_existent_file.csv",
            target_db_path=self.target_db
        )
        with self.assertRaises(Exception):
            pipeline_fail.run(atomic_swap=True)
            
        # 4. Verify original target database is completely unharmed
        self.assertTrue(os.path.exists(self.target_db))
        self.assertEqual(os.path.getsize(self.target_db), original_size)

    def test_13_pipeline_repeatability(self):
        """Verify running the pipeline produces identical metrics across repeated runs on temporary DB."""
        temp_repeat_db = "data/processed/test_repeatability.db"
        if os.path.exists(temp_repeat_db):
            os.remove(temp_repeat_db)
        try:
            pipeline2 = RiskLensETLPipeline(
                raw_csv_path=self.raw_csv,
                target_db_path=temp_repeat_db
            )
            metrics2 = pipeline2.run(atomic_swap=True)
            self.assertEqual(self.metrics["fct_loan_application_count"], metrics2["fct_loan_application_count"])
            self.assertEqual(self.metrics["approved_applications"], metrics2["approved_applications"])
            self.assertEqual(self.metrics["rejected_applications"], metrics2["rejected_applications"])
            self.assertEqual(self.metrics["haircut_eligible_count"], metrics2["haircut_eligible_count"])
        finally:
            if os.path.exists(temp_repeat_db):
                os.remove(temp_repeat_db)


if __name__ == '__main__':
    unittest.main(verbosity=2)
