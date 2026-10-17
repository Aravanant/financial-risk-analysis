"""RiskLens AI - Production ETL Pipeline (Milestone 1)

Orchestrates:
1. Pre-ingestion raw file hashing (SHA-256) and immutability verification.
2. Deterministic deduplication retaining the first physical occurrence (source_row_ordinal).
3. Conformed lookup dimension population (Location, Channel, Purpose).
4. Fact table transformation, cleaning, and quality flag assignment without ABS().
5. Quarantined synthetic repayment snapshot generation for eligible approved applications.
6. Atomic transactional loading into SQLite with rollback safety and atomic database replacement.
7. Post-load reconciliation and integrity validation.
"""

import os
import sys
import sqlite3
import logging
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

try:
    from .schema import DDL_STATEMENTS
    from .validators import (
        compute_file_sha256,
        validate_row_data,
        verify_duplicate_integrity,
        VALID_REGIONS,
        VALID_RESIDENTIAL_STATUSES,
        VALID_PROPERTY_OWNERSHIPS,
        VALID_CHANNELS,
        VALID_LOAN_PURPOSES
    )
except ImportError:
    # Fallback for direct script execution: python3 src/data/etl_pipeline.py
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from src.data.schema import DDL_STATEMENTS
    from src.data.validators import (
        compute_file_sha256,
        validate_row_data,
        verify_duplicate_integrity,
        VALID_REGIONS,
        VALID_RESIDENTIAL_STATUSES,
        VALID_PROPERTY_OWNERSHIPS,
        VALID_CHANNELS,
        VALID_LOAN_PURPOSES
    )


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("RiskLensETL")


class RiskLensETLPipeline:
    """Production ETL Pipeline for RiskLens AI SQLite Analytics Warehouse."""

    def __init__(
        self,
        raw_csv_path: str = "data/raw/kaggle_original.csv",
        target_db_path: str = "data/processed/risklens_analytics.db",
        seed: int = 42
    ):
        self.raw_csv_path = os.path.abspath(raw_csv_path)
        self.target_db_path = os.path.abspath(target_db_path)
        self.seed = seed
        self.pre_load_hash: Optional[str] = None
        self.post_load_hash: Optional[str] = None
        self.metrics: Dict[str, Any] = {}

    def verify_raw_file(self) -> str:
        """Verify existence and compute pre-load SHA-256 hash of raw CSV."""
        if not os.path.exists(self.raw_csv_path):
            raise FileNotFoundError(f"Raw source CSV not found at: {self.raw_csv_path}")
        
        file_size = os.path.getsize(self.raw_csv_path)
        logger.info(f"Inspecting raw file: {self.raw_csv_path} ({file_size:,} bytes)")
        self.pre_load_hash = compute_file_sha256(self.raw_csv_path)
        logger.info(f"Verified pre-load SHA-256: {self.pre_load_hash}")
        return self.pre_load_hash

    def load_and_deduplicate(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load CSV, assign source_row_ordinal, and perform deterministic deduplication.
        
        Returns:
            (df_dedup, df_duplicates)
        """
        logger.info("Reading raw CSV into staging...")
        df = pd.read_csv(self.raw_csv_path, low_memory=False)
        raw_rows, raw_cols = df.shape
        self.metrics["raw_row_count"] = raw_rows
        self.metrics["raw_col_count"] = raw_cols
        logger.info(f"Raw dataset loaded: {raw_rows:,} rows, {raw_cols} columns")
        
        if raw_rows != 100150 or raw_cols != 67:
            raise ValueError(
                f"Raw CSV dimension mismatch: Expected 100,150 rows x 67 cols, got {raw_rows} x {raw_cols}"
            )
        
        # Explicit duplicate integrity check: exact 67-column duplicates vs Application_ID duplicates
        dup_audit = verify_duplicate_integrity(df, id_col="Application_ID")
        self.metrics["exact_full_duplicates"] = dup_audit["exact_full_duplicates"]
        self.metrics["duplicate_application_ids"] = dup_audit["duplicate_id_count"]
        self.metrics["conflicting_duplicate_ids"] = dup_audit["conflicting_id_count"]
        
        if not dup_audit["is_exact_match"]:
            raise ValueError(
                f"Duplicate verification mismatch: Found {dup_audit['exact_full_duplicates']} full-row duplicates, "
                f"{dup_audit['duplicate_id_count']} duplicate Application_IDs, and "
                f"{dup_audit['conflicting_id_count']} conflicting records!"
            )
        logger.info(
            f"Duplicate verification passed: {dup_audit['exact_full_duplicates']} exact 67-column full-row duplicates, "
            f"{dup_audit['duplicate_id_count']} duplicate Application_IDs, 0 conflicting records."
        )

        # 1-indexed source row ordinal based on physical line order
        df["source_row_ordinal"] = np.arange(1, raw_rows + 1)
        
        # Deterministic deduplication: keep first occurrence by source_row_ordinal
        dup_mask = df.duplicated(subset=["Application_ID"], keep="first")
        df_duplicates = df[dup_mask].copy()
        df_dedup = df[~dup_mask].copy()
        
        n_dups = int(dup_mask.sum())
        n_clean = len(df_dedup)
        self.metrics["exact_duplicate_rows"] = n_dups
        self.metrics["deduplicated_row_count"] = n_clean
        logger.info(f"Deduplication complete: {n_dups} duplicate rows removed, {n_clean:,} clean rows retained")
        
        if n_dups != 150 or n_clean != 100000:
            raise ValueError(
                f"Deduplication mismatch: Expected 150 duplicates and 100,000 clean rows, got {n_dups} and {n_clean}"
            )
            
        return df_dedup, df_duplicates

    def create_schema(self, conn: sqlite3.Connection) -> None:
        """Execute approved DDL statements in SQLite database."""
        logger.info("Creating SQLite warehouse schema, constraints, and views...")
        cursor = conn.cursor()
        for ddl in DDL_STATEMENTS:
            cursor.execute(ddl)

    def populate_dimensions(
        self, conn: sqlite3.Connection, df: pd.DataFrame
    ) -> Tuple[Dict[Tuple[str, str, str], int], Dict[str, int], Dict[str, int]]:
        """
        Populate conformed lookup dimensions and return in-memory ID lookup maps.
        """
        logger.info("Populating conformed lookup dimensions...")
        cursor = conn.cursor()
        
        # 1. Location & Property Dimension
        # Distinct combinations of (Region, Residential_Status, Property_Ownership)
        loc_combos = df[["Region", "Residential_Status", "Property_Ownership"]].drop_duplicates().sort_values(
            by=["Region", "Residential_Status", "Property_Ownership"]
        )
        
        location_map = {}
        for _, row in loc_combos.iterrows():
            reg = str(row["Region"]).strip().title()
            res = str(row["Residential_Status"]).strip().title()
            prop = str(row["Property_Ownership"]).strip().title()
            if prop == "Family Owned":
                prop = "Family Owned"
            elif prop.upper() == "RENT":
                prop = "Rent"
            elif prop.upper() == "OWN":
                prop = "Own"
            elif prop.upper() == "MORTGAGE":
                prop = "Mortgage"
            elif prop.upper() == "OTHER":
                prop = "Other"
                
            cursor.execute(
                """
                INSERT OR IGNORE INTO dim_residence_property_location (region, residential_status, property_ownership)
                VALUES (?, ?, ?)
                """,
                (reg, res, prop)
            )
            cursor.execute(
                """
                SELECT location_property_id FROM dim_residence_property_location
                WHERE region = ? AND residential_status = ? AND property_ownership = ?
                """,
                (reg, res, prop)
            )
            loc_id = cursor.fetchone()[0]
            location_map[(reg, res, prop)] = loc_id
            
        cursor.execute("SELECT COUNT(*) FROM dim_residence_property_location")
        n_loc = cursor.fetchone()[0]
        self.metrics["dim_residence_property_location_count"] = n_loc
        logger.info(f"Loaded dim_residence_property_location: {n_loc} distinct combinations")
        if n_loc != 75:
            raise ValueError(f"Expected 75 location/property dimension rows, got {n_loc}")
            
        # 2. Channel Dimension
        channel_map = {}
        for ch in sorted(VALID_CHANNELS):
            cursor.execute("INSERT OR IGNORE INTO dim_channel (channel_name) VALUES (?)", (ch,))
            cursor.execute("SELECT channel_id FROM dim_channel WHERE channel_name = ?", (ch,))
            channel_map[ch] = cursor.fetchone()[0]
            
        cursor.execute("SELECT COUNT(*) FROM dim_channel")
        n_chan = cursor.fetchone()[0]
        self.metrics["dim_channel_count"] = n_chan
        logger.info(f"Loaded dim_channel: {n_chan} distinct channels")
        if n_chan != 4:
            raise ValueError(f"Expected 4 channel rows, got {n_chan}")
            
        # 3. Purpose Dimension
        purpose_map = {}
        for purp in sorted(VALID_LOAN_PURPOSES):
            cursor.execute("INSERT OR IGNORE INTO dim_loan_purpose (purpose_name) VALUES (?)", (purp,))
            cursor.execute("SELECT purpose_id FROM dim_loan_purpose WHERE purpose_name = ?", (purp,))
            purpose_map[purp] = cursor.fetchone()[0]
            
        cursor.execute("SELECT COUNT(*) FROM dim_loan_purpose")
        n_purp = cursor.fetchone()[0]
        self.metrics["dim_loan_purpose_count"] = n_purp
        logger.info(f"Loaded dim_loan_purpose: {n_purp} distinct purposes")
        if n_purp != len(VALID_LOAN_PURPOSES):
            raise ValueError(f"Expected {len(VALID_LOAN_PURPOSES)} purpose rows, got {n_purp}")
            
        return location_map, channel_map, purpose_map

    def populate_fact_table(
        self,
        conn: sqlite3.Connection,
        df: pd.DataFrame,
        location_map: Dict[Tuple[str, str, str], int],
        channel_map: Dict[str, int],
        purpose_map: Dict[str, int]
    ) -> None:
        """Transform, clean, and insert all 100,000 application fact records."""
        logger.info("Transforming and loading fct_loan_application records...")
        cursor = conn.cursor()
        
        insert_sql = """
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
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?
        );
        """
        
        batch = []
        batch_size = 5000
        
        for idx, row in df.iterrows():
            clean_row = validate_row_data(row)
            
            # Resolve Foreign Keys
            reg = str(row["Region"]).strip().title()
            res = str(row["Residential_Status"]).strip().title()
            raw_prop = str(row["Property_Ownership"]).strip().title()
            if raw_prop.upper() == "FAMILY OWNED":
                prop = "Family Owned"
            elif raw_prop.upper() == "RENT":
                prop = "Rent"
            elif raw_prop.upper() == "OWN":
                prop = "Own"
            elif raw_prop.upper() == "MORTGAGE":
                prop = "Mortgage"
            elif raw_prop.upper() == "OTHER":
                prop = "Other"
            else:
                prop = raw_prop
                
            loc_key = (reg, res, prop)
            loc_id = location_map.get(loc_key)
            if loc_id is None:
                raise ValueError(f"Unmapped location combination: {loc_key} on Application_ID {clean_row['application_id']}")
                
            chan_name = str(row["Application_Channel"]).strip()
            # Normalize channel case
            chan_match = None
            for ch in VALID_CHANNELS:
                if ch.upper() == chan_name.upper():
                    chan_match = ch
                    break
            if chan_match is None or chan_match not in channel_map:
                raise ValueError(f"Unmapped channel: '{chan_name}' on Application_ID {clean_row['application_id']}")
            chan_id = channel_map[chan_match]
            
            purp_name = str(row["Loan_Purpose"]).strip()
            purp_match = None
            for p in VALID_LOAN_PURPOSES:
                if p.upper() == purp_name.upper():
                    purp_match = p
                    break
            if purp_match is None or purp_match not in purpose_map:
                raise ValueError(f"Unmapped purpose: '{purp_name}' on Application_ID {clean_row['application_id']}")
            purp_id = purpose_map[purp_match]
            
            record_tuple = (
                clean_row['application_id'], clean_row['source_row_ordinal'], loc_id, chan_id, purp_id,
                clean_row['age'], clean_row['gender'], clean_row['marital_status'], clean_row['education_level'], clean_row['employment_status'],
                clean_row['job_experience_years'], clean_row['dependents'],
                clean_row['annual_income'], clean_row['monthly_income_reported'], clean_row['monthly_income_calculated'],
                clean_row['savings_balance'], clean_row['checking_balance'], clean_row['total_assets'], clean_row['total_liabilities'], clean_row['monthly_debt_payment'],
                clean_row['net_worth'], clean_row['bank_account_tenure_months'],
                clean_row['requested_loan_amount'], clean_row['requested_term_months'], clean_row['interest_rate'], clean_row['debt_to_income_ratio'],
                clean_row['co_applicant_flag'], clean_row['collateral_flag'],
                clean_row['bureau_credit_score'], clean_row['bureau_existing_loans'], clean_row['bureau_late_payments_2yr'],
                clean_row['bureau_credit_history_years'], clean_row['bureau_prior_loan_status'],
                clean_row['proprietary_risk_score'], clean_row['risk_tier'], clean_row['normalized_risk_score'],
                clean_row['underwriting_decision'], clean_row['sanctioned_approved_amount'], clean_row['is_approved'], clean_row['has_missing_sanctioned_amount'],
                clean_row['has_invalid_annual_income'], clean_row['has_invalid_loan_amount'], clean_row['has_invalid_savings_balance'],
                clean_row['has_invalid_age'], clean_row['has_invalid_financials']
            )
            batch.append(record_tuple)
            
            if len(batch) >= batch_size:
                cursor.executemany(insert_sql, batch)
                batch.clear()
                
        if batch:
            cursor.executemany(insert_sql, batch)
            batch.clear()
            
        cursor.execute("SELECT COUNT(*) FROM fct_loan_application")
        fact_count = cursor.fetchone()[0]
        self.metrics["fct_loan_application_count"] = fact_count
        logger.info(f"Loaded fct_loan_application: {fact_count:,} rows")
        if fact_count != 100000:
            raise ValueError(f"Expected exactly 100,000 fact rows, got {fact_count}")

    def populate_demo_servicing(self, conn: sqlite3.Connection, df: pd.DataFrame) -> None:
        """
        Populate isolated demo_synthetic_repayment_snapshot table.
        
        Applies strict population eligibility: Approved applications with positive sanctioned amount.
        Cleanses sentinel dates ('not_a_date', '31/31/2025' -> NULL).
        """
        logger.info("Populating demo_synthetic_repayment_snapshot (isolated servicing demonstration)...")
        cursor = conn.cursor()
        
        insert_sql = """
        INSERT INTO demo_synthetic_repayment_snapshot (
            application_id, simulated_due_date, simulated_payment_date,
            simulated_amount_due_cu, simulated_amount_paid_cu, simulated_days_late,
            simulated_payment_status, simulated_disbursement_amount_cu, simulated_outstanding_balance_cu
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        # Filter strictly for Approved applications with positive Approved_Amount
        app_status = df["Loan_Approved"].astype(str).str.strip().str.capitalize()
        eligible_mask = (app_status == "Approved") & (df["Approved_Amount"] > 0)
        eligible_df = df[eligible_mask].copy()
        
        eligible_count = len(eligible_df)
        self.metrics["demo_synthetic_eligible_count"] = eligible_count
        logger.info(f"Eligible approved applications with positive sanction: {eligible_count:,}")
        if eligible_count != 48596:
            raise ValueError(f"Expected 48,596 eligible demonstration snapshot rows, got {eligible_count}")
            
        batch = []
        for _, row in eligible_df.iterrows():
            aid = int(row["Application_ID"])
            
            # Clean sentinel dates
            due_d = str(row["due_date"]).strip() if not pd.isnull(row["due_date"]) else None
            if due_d in ('not_a_date', 'nan', 'None', ''):
                due_d = None
                
            pay_d = str(row["payment_date"]).strip() if not pd.isnull(row["payment_date"]) else None
            if pay_d in ('31/31/2025', 'not_a_date', 'nan', 'None', ''):
                pay_d = None
                
            amt_due = float(row["amount_due"]) if not pd.isnull(row["amount_due"]) else None
            amt_paid = float(row["amount_paid"]) if not pd.isnull(row["amount_paid"]) else None
            days_late = int(row["days_late"]) if not pd.isnull(row["days_late"]) else None
            status = str(row["payment_status"]).strip().title() if not pd.isnull(row["payment_status"]) else None
            disb_amt = float(row["disbursement_amount"]) if not pd.isnull(row["disbursement_amount"]) else None
            out_bal = float(row["outstanding_amount"]) if not pd.isnull(row["outstanding_amount"]) else None
            
            batch.append((
                aid, due_d, pay_d, amt_due, amt_paid, days_late, status, disb_amt, out_bal
            ))
            
        cursor.executemany(insert_sql, batch)
        cursor.execute("SELECT COUNT(*) FROM demo_synthetic_repayment_snapshot")
        demo_count = cursor.fetchone()[0]
        self.metrics["demo_synthetic_repayment_snapshot_count"] = demo_count
        logger.info(f"Loaded demo_synthetic_repayment_snapshot: {demo_count:,} rows")
        if demo_count != 48596:
            raise ValueError(f"Expected 48,596 demonstration servicing rows, got {demo_count}")

    def run_integrity_checks(self, conn: sqlite3.Connection) -> None:
        """Execute automated integrity, constraint, and KPI reconciliation assertions."""
        logger.info("Executing comprehensive post-load integrity checks...")
        cursor = conn.cursor()
        
        # 1. Foreign Key Integrity Check
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        if fk_violations:
            raise ValueError(f"Foreign key violations detected: {fk_violations}")
        logger.info("PASS: PRAGMA foreign_key_check returned 0 violations.")
        
        # 2. Decision Reconciliation Check
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN underwriting_decision = 'Approved' THEN 1 ELSE 0 END) AS app_count,
                SUM(CASE WHEN underwriting_decision = 'Rejected' THEN 1 ELSE 0 END) AS rej_count,
                SUM(is_approved) AS approved_flag_sum
            FROM fct_loan_application;
        """)
        app_c, rej_c, flag_sum = cursor.fetchone()
        self.metrics["approved_applications"] = app_c
        self.metrics["rejected_applications"] = rej_c
        if app_c != 49171 or rej_c != 50829 or app_c != flag_sum:
            raise ValueError(
                f"Decision reconciliation failed: Expected 49,171 Approved / 50,829 Rejected, got {app_c} / {rej_c} (flag sum: {flag_sum})"
            )
        logger.info(f"PASS: Decision reconciliation exact: {app_c:,} Approved, {rej_c:,} Rejected.")
        
        # 3. Quality Flags & Composite Invalid Financials Check
        cursor.execute("""
            SELECT 
                SUM(has_invalid_annual_income),
                SUM(has_invalid_loan_amount),
                SUM(has_invalid_savings_balance),
                SUM(has_invalid_age),
                SUM(has_invalid_financials)
            FROM fct_loan_application;
        """)
        neg_inc, neg_loan, neg_sav, inv_age, comp_fin = cursor.fetchone()
        self.metrics["has_invalid_annual_income"] = neg_inc
        self.metrics["has_invalid_loan_amount"] = neg_loan
        self.metrics["has_invalid_savings_balance"] = neg_sav
        self.metrics["has_invalid_age"] = inv_age
        self.metrics["has_invalid_financials"] = comp_fin
        
        if neg_inc != 35 or neg_loan != 35 or neg_sav != 35:
            raise ValueError(f"Individual financial negative count mismatch: Expected (35, 35, 35), got ({neg_inc}, {neg_loan}, {neg_sav})")
        if comp_fin != 104:
            raise ValueError(f"Composite invalid financials mismatch: Expected 104, got {comp_fin}")
        if inv_age != 25:
            raise ValueError(f"Invalid age flag count mismatch: Expected 25, got {inv_age}")
        logger.info(f"PASS: Quality flags verified: {comp_fin} composite invalid financials, {inv_age} invalid ages.")
        
        # 4. Missing Sanctioned Amount Check
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount = 0.0 THEN 1 ELSE 0 END),
                SUM(has_missing_sanctioned_amount)
            FROM fct_loan_application;
        """)
        app_null, rej_null, rej_zero, tot_missing = cursor.fetchone()
        self.metrics["approved_missing_sanction"] = app_null
        self.metrics["rejected_missing_sanction"] = rej_null
        self.metrics["rejected_genuine_zero"] = rej_zero
        self.metrics["total_missing_sanctions"] = tot_missing
        
        if app_null != 575 or rej_null != 631 or tot_missing != 1206:
            raise ValueError(
                f"Sanctioned amount missingness mismatch: Expected (575 App Null, 631 Rej Null, 1206 Tot), got ({app_null}, {rej_null}, {tot_missing})"
            )
        if rej_zero != 50198:
            raise ValueError(f"Rejected genuine zero mismatch: Expected 50,198, got {rej_zero}")
        logger.info(f"PASS: Sanction missingness verified: {app_null} Approved NULLs, {rej_null} Rejected NULLs, {rej_zero:,} Rejected Zeros.")
        
        # 5. Haircut KPI Population & Financial Aggregation Check
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
        self.metrics["haircut_eligible_count"] = el_count
        self.metrics["haircut_total_requested_cu"] = tot_req
        self.metrics["haircut_total_sanctioned_cu"] = tot_sanc
        self.metrics["haircut_total_haircut_cu"] = tot_hair
        self.metrics["haircut_aggregate_pct"] = hair_pct
        
        if el_count != 48022:
            raise ValueError(f"Haircut eligible population mismatch: Expected 48,022, got {el_count}")
        if abs(hair_pct - 20.3155) > 0.01:
            raise ValueError(f"Haircut percentage mismatch: Expected ~20.3155%, got {hair_pct:.4f}%")
        logger.info(
            f"PASS: Haircut KPI validated: {el_count:,} eligible applications, "
            f"Haircut = {tot_hair:,.2f} CU ({hair_pct:.4f}%)."
        )

    def run(self, atomic_swap: bool = True) -> Dict[str, Any]:
        """
        Execute the full ETL pipeline with atomic replacement and verification.
        
        Args:
            atomic_swap: If True, builds into temporary DB and atomically replaces target only on complete success.
        Returns:
            Dictionary of metrics and execution audit logs.
        """
        logger.info("=== STARTING RISKLENS AI ETL PIPELINE ===")
        
        # Step 1: Pre-load immutability check
        pre_hash = self.verify_raw_file()
        
        # Step 2: Read and deduplicate
        df_dedup, _ = self.load_and_deduplicate()
        
        # Step 3: Setup database path
        os.makedirs(os.path.dirname(self.target_db_path), exist_ok=True)
        build_db_path = f"{self.target_db_path}.tmp" if atomic_swap else self.target_db_path
        
        if os.path.exists(build_db_path):
            os.remove(build_db_path)
            
        logger.info(f"Target build database: {build_db_path}")
        conn = sqlite3.connect(build_db_path)
        
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("BEGIN TRANSACTION;")
            
            # Step 4: Schema creation
            self.create_schema(conn)
            
            # Step 5: Dimensions
            loc_map, chan_map, purp_map = self.populate_dimensions(conn, df_dedup)
            
            # Step 6: Fact table
            self.populate_fact_table(conn, df_dedup, loc_map, chan_map, purp_map)
            
            # Step 7: Demonstration Servicing Table
            self.populate_demo_servicing(conn, df_dedup)
            
            # Step 8: Post-load integrity checks
            self.run_integrity_checks(conn)
            
            # Commit transaction
            conn.commit()
            logger.info("Database transaction committed successfully.")
            
        except Exception as e:
            logger.error(f"ETL transaction failed: {e}. Initiating rollback...")
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
            if os.path.exists(build_db_path):
                os.remove(build_db_path)
            raise RuntimeError(f"ETL execution aborted: {e}") from e
            
        finally:
            if conn:
                conn.close()
                
        # Step 9: Post-load raw file hash verification
        self.post_load_hash = compute_file_sha256(self.raw_csv_path)
        if self.pre_load_hash != self.post_load_hash:
            raise RuntimeError(
                f"CRITICAL DATA INTEGRITY VIOLATION: Raw CSV hash altered! "
                f"Pre: {self.pre_load_hash} vs Post: {self.post_load_hash}"
            )
        logger.info(f"Raw CSV immutability confirmed: SHA-256 unchanged ({self.post_load_hash})")
        self.metrics["raw_csv_sha256"] = self.post_load_hash
        
        # Step 10: Atomic Replacement
        if atomic_swap:
            logger.info(f"Atomically replacing target database: {self.target_db_path}")
            os.replace(build_db_path, self.target_db_path)
            
        target_size = os.path.getsize(self.target_db_path)
        self.metrics["target_db_bytes"] = target_size
        logger.info(f"=== ETL PIPELINE COMPLETED SUCCESSFULLY: {self.target_db_path} ({target_size:,} bytes) ===")
        return self.metrics


if __name__ == "__main__":
    pipeline = RiskLensETLPipeline()
    results = pipeline.run(atomic_swap=True)
    print("\nETL Pipeline Execution Summary:")
    for k, v in results.items():
        print(f"  {k}: {v}")
