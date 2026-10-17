"""Analytical SQL Layer Test Suite for RiskLens AI.

Verifies:
1. vw_portfolio_kpis against independently written reference SQL.
2. vw_channel_performance across all 4 channels without join fan-out.
3. vw_loan_purpose_analysis across all 8 verified categories with haircut metrics.
4. vw_portfolio_haircut_summary aggregate calculation (sum-based, not average of percentages) and exclusion arithmetic.
5. vw_risk_tier_summary using source-provided Default_Risk categories.
6. vw_data_quality_metrics auditing missingness, genuine zeros, and invalid flags.
7. Complete quarantine of demo_synthetic_repayment_snapshot from all primary analytical views.
"""

import os
import sys
import sqlite3
import unittest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = "data/processed/risklens_analytics.db"


class TestAnalyticalSQLViews(unittest.TestCase):
    """Test suite validating SQLite analytical views against independent reference queries."""

    @classmethod
    def setUpClass(cls):
        """Connect to the validated analytics database in read-only mode."""
        cls.db_path = os.path.abspath(DB_PATH)
        if not os.path.exists(cls.db_path):
            raise FileNotFoundError(f"Database file not found: {cls.db_path}")
        
        # Connect in URI read-only mode to prevent any accidental mutation
        cls.conn = sqlite3.connect(f"file:{cls.db_path}?mode=ro", uri=True)
        cls.conn.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        """Close read-only connection."""
        if cls.conn:
            cls.conn.close()

    def test_01_portfolio_kpis_reconciliation(self):
        """Verify vw_portfolio_kpis matches independent reference aggregation query."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vw_portfolio_kpis;")
        view_row = dict(cursor.fetchone())
        
        # Independent reference query directly on fct_loan_application
        cursor.execute("""
            SELECT 
                COUNT(*) AS ref_total,
                SUM(CASE WHEN underwriting_decision = 'Approved' THEN 1 ELSE 0 END) AS ref_app,
                SUM(CASE WHEN underwriting_decision = 'Rejected' THEN 1 ELSE 0 END) AS ref_rej,
                ROUND(AVG(is_approved) * 100.0, 3) AS ref_app_rate,
                ROUND((1.0 - AVG(is_approved)) * 100.0, 3) AS ref_rej_rate,
                ROUND(SUM(requested_loan_amount), 2) AS ref_req_cu,
                ROUND(SUM(sanctioned_approved_amount), 2) AS ref_sanc_cu,
                SUM(has_invalid_financials) AS ref_inv_fin,
                SUM(has_missing_sanctioned_amount) AS ref_miss_sanc
            FROM fct_loan_application;
        """)
        ref_row = dict(cursor.fetchone())
        
        self.assertEqual(view_row["total_applications"], 100000)
        self.assertEqual(view_row["approved_applications"], 49171)
        self.assertEqual(view_row["rejected_applications"], 50829)
        self.assertAlmostEqual(view_row["approval_rate_pct"], 49.171, places=3)
        self.assertAlmostEqual(view_row["rejection_rate_pct"], 50.829, places=3)
        self.assertAlmostEqual(view_row["total_requested_cu"], 14208864987.26, places=1)
        self.assertAlmostEqual(view_row["total_sanctioned_cu"], 5429935281.88, places=1)
        self.assertEqual(view_row["invalid_financials_count"], 104)
        self.assertEqual(view_row["missing_sanctioned_count"], 1206)
        
        # Reconciliation against independent reference
        self.assertEqual(view_row["total_applications"], ref_row["ref_total"])
        self.assertEqual(view_row["approved_applications"], ref_row["ref_app"])
        self.assertEqual(view_row["rejected_applications"], ref_row["ref_rej"])
        self.assertEqual(view_row["approval_rate_pct"], ref_row["ref_app_rate"])
        self.assertEqual(view_row["total_requested_cu"], ref_row["ref_req_cu"])
        self.assertEqual(view_row["total_sanctioned_cu"], ref_row["ref_sanc_cu"])

    def test_02_channel_performance_reconciliation(self):
        """Verify vw_channel_performance covers all 4 channels without join fan-out."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vw_channel_performance ORDER BY channel_id;")
        channels = [dict(r) for r in cursor.fetchall()]
        
        # Verify exactly 4 distinct channels
        self.assertEqual(len(channels), 4)
        channel_names = {c["channel_name"] for c in channels}
        self.assertEqual(channel_names, {'Agent', 'Branch', 'Mobile App', 'Online'})
        
        # Check conservation of portfolio totals across channels
        tot_apps = sum(c["total_applications"] for c in channels)
        tot_appr = sum(c["approved_applications"] for c in channels)
        tot_rejc = sum(c["rejected_applications"] for c in channels)
        tot_req = sum(c["total_requested_cu"] for c in channels)
        tot_sanc = sum(c["total_sanctioned_cu"] for c in channels)
        
        self.assertEqual(tot_apps, 100000)
        self.assertEqual(tot_appr, 49171)
        self.assertEqual(tot_rejc, 50829)
        self.assertAlmostEqual(tot_req, 14208864987.26, places=1)
        self.assertAlmostEqual(tot_sanc, 5429935281.88, places=1)
        
        # Verify specific channel numbers
        ch_map = {c["channel_name"]: c for c in channels}
        self.assertEqual(ch_map["Agent"]["total_applications"], 20422)
        self.assertEqual(ch_map["Branch"]["total_applications"], 25283)
        self.assertEqual(ch_map["Mobile App"]["total_applications"], 24256)
        self.assertEqual(ch_map["Online"]["total_applications"], 30039)

    def test_03_loan_purpose_analysis_all_eight_categories(self):
        """Verify vw_loan_purpose_analysis contains all 8 categories and accurate haircut metrics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vw_loan_purpose_analysis ORDER BY purpose_name;")
        purposes = [dict(r) for r in cursor.fetchall()]
        
        self.assertEqual(len(purposes), 8)
        expected_categories = {
            'Business', 'Car', 'Debt Consolidation', 'Education',
            'Home', 'Medical', 'Personal', 'Vehicle'
        }
        found_categories = {p["purpose_name"] for p in purposes}
        self.assertEqual(found_categories, expected_categories)

        # Authoritative verified metrics for each category (derived directly from deduplicated raw CSV)
        expected_metrics = {
            'Business': {
                'total_applications': 14269,
                'approved_applications': 7087,
                'rejected_applications': 7182,
                'approval_rate_pct': 49.67,
                'total_requested_cu': 2018127261.68,
                'total_sanctioned_cu': 782181290.77,
                'haircut_eligible_count': 6929,
                'haircut_eligible_requested_cu': 971603348.40,
                'haircut_eligible_sanctioned_cu': 773378055.87,
                'haircut_total_cu': 198225292.53,
                'aggregate_haircut_pct': 20.4019,
                'haircut_excluded_count': 7340,
            },
            'Car': {
                'total_applications': 4349,
                'approved_applications': 2677,
                'rejected_applications': 1672,
                'approval_rate_pct': 61.55,
                'total_requested_cu': 597847590.89,
                'total_sanctioned_cu': 257683128.58,
                'haircut_eligible_count': 2677,
                'haircut_eligible_requested_cu': 349597901.79,
                'haircut_eligible_sanctioned_cu': 257683128.58,
                'haircut_total_cu': 91914773.21,
                'aggregate_haircut_pct': 26.2916,
                'haircut_excluded_count': 1672,
            },
            'Debt Consolidation': {
                'total_applications': 14236,
                'approved_applications': 6910,
                'rejected_applications': 7326,
                'approval_rate_pct': 48.54,
                'total_requested_cu': 2010279716.67,
                'total_sanctioned_cu': 762489028.84,
                'haircut_eligible_count': 6760,
                'haircut_eligible_requested_cu': 946986677.96,
                'haircut_eligible_sanctioned_cu': 754029943.56,
                'haircut_total_cu': 192956734.40,
                'aggregate_haircut_pct': 20.3759,
                'haircut_excluded_count': 7476,
            },
            'Education': {
                'total_applications': 14289,
                'approved_applications': 6891,
                'rejected_applications': 7398,
                'approval_rate_pct': 48.23,
                'total_requested_cu': 2026642586.82,
                'total_sanctioned_cu': 750392291.06,
                'haircut_eligible_count': 6720,
                'haircut_eligible_requested_cu': 924612228.71,
                'haircut_eligible_sanctioned_cu': 739528475.06,
                'haircut_total_cu': 185083753.65,
                'aggregate_haircut_pct': 20.0174,
                'haircut_excluded_count': 7569,
            },
            'Home': {
                'total_applications': 14183,
                'approved_applications': 7189,
                'rejected_applications': 6994,
                'approval_rate_pct': 50.69,
                'total_requested_cu': 2000021248.92,
                'total_sanctioned_cu': 788125042.79,
                'haircut_eligible_count': 7015,
                'haircut_eligible_requested_cu': 978968509.30,
                'haircut_eligible_sanctioned_cu': 776764554.36,
                'haircut_total_cu': 202203954.94,
                'aggregate_haircut_pct': 20.6548,
                'haircut_excluded_count': 7168,
            },
            'Medical': {
                'total_applications': 14167,
                'approved_applications': 6860,
                'rejected_applications': 7307,
                'approval_rate_pct': 48.42,
                'total_requested_cu': 2019030030.13,
                'total_sanctioned_cu': 758069310.24,
                'haircut_eligible_count': 6705,
                'haircut_eligible_requested_cu': 938536418.11,
                'haircut_eligible_sanctioned_cu': 748432248.46,
                'haircut_total_cu': 190104169.65,
                'aggregate_haircut_pct': 20.2554,
                'haircut_excluded_count': 7462,
            },
            'Personal': {
                'total_applications': 14421,
                'approved_applications': 6964,
                'rejected_applications': 7457,
                'approval_rate_pct': 48.29,
                'total_requested_cu': 2051826588.70,
                'total_sanctioned_cu': 774945106.58,
                'haircut_eligible_count': 6783,
                'haircut_eligible_requested_cu': 955528709.21,
                'haircut_eligible_sanctioned_cu': 764459744.39,
                'haircut_total_cu': 191068964.82,
                'aggregate_haircut_pct': 19.9962,
                'haircut_excluded_count': 7638,
            },
            'Vehicle': {
                'total_applications': 10086,
                'approved_applications': 4593,
                'rejected_applications': 5493,
                'approval_rate_pct': 45.54,
                'total_requested_cu': 1485089963.45,
                'total_sanctioned_cu': 556050083.02,
                'haircut_eligible_count': 4433,
                'haircut_eligible_requested_cu': 661543126.30,
                'haircut_eligible_sanctioned_cu': 546398019.42,
                'haircut_total_cu': 115145106.88,
                'aggregate_haircut_pct': 17.4055,
                'haircut_excluded_count': 5653,
            },
        }

        # Assert each category individually
        for p in purposes:
            name = p["purpose_name"]
            exp = expected_metrics[name]
            self.assertEqual(p["total_applications"], exp["total_applications"], f"Mismatch for {name} total_applications")
            self.assertEqual(p["approved_applications"], exp["approved_applications"], f"Mismatch for {name} approved_applications")
            self.assertEqual(p["rejected_applications"], exp["rejected_applications"], f"Mismatch for {name} rejected_applications")
            self.assertAlmostEqual(p["approval_rate_pct"], exp["approval_rate_pct"], places=2, msg=f"Mismatch for {name} approval_rate_pct")
            self.assertAlmostEqual(p["total_requested_cu"], exp["total_requested_cu"], places=1, msg=f"Mismatch for {name} total_requested_cu")
            self.assertAlmostEqual(p["total_sanctioned_cu"], exp["total_sanctioned_cu"], places=1, msg=f"Mismatch for {name} total_sanctioned_cu")
            self.assertEqual(p["haircut_eligible_count"], exp["haircut_eligible_count"], f"Mismatch for {name} haircut_eligible_count")
            self.assertAlmostEqual(p["haircut_eligible_requested_cu"], exp["haircut_eligible_requested_cu"], places=1, msg=f"Mismatch for {name} eligible requested")
            self.assertAlmostEqual(p["haircut_eligible_sanctioned_cu"], exp["haircut_eligible_sanctioned_cu"], places=1, msg=f"Mismatch for {name} eligible sanctioned")
            self.assertAlmostEqual(p["haircut_total_cu"], exp["haircut_total_cu"], places=1, msg=f"Mismatch for {name} haircut_total_cu")
            self.assertAlmostEqual(p["aggregate_haircut_pct"], exp["aggregate_haircut_pct"], places=3, msg=f"Mismatch for {name} aggregate_haircut_pct")
            self.assertEqual(p["haircut_excluded_count"], exp["haircut_excluded_count"], f"Mismatch for {name} haircut_excluded_count")
        
        # Verify conservation of totals across loan purposes
        tot_apps = sum(p["total_applications"] for p in purposes)
        tot_appr = sum(p["approved_applications"] for p in purposes)
        tot_rejc = sum(p["rejected_applications"] for p in purposes)
        tot_req = sum(p["total_requested_cu"] for p in purposes)
        tot_sanc = sum(p["total_sanctioned_cu"] for p in purposes)
        tot_eligible_haircut = sum(p["haircut_eligible_count"] for p in purposes)
        tot_excluded_haircut = sum(p["haircut_excluded_count"] for p in purposes)
        
        self.assertEqual(tot_apps, 100000)
        self.assertEqual(tot_appr, 49171)
        self.assertEqual(tot_rejc, 50829)
        self.assertAlmostEqual(tot_req, 14208864987.26, places=1)
        self.assertAlmostEqual(tot_sanc, 5429935281.88, places=1)
        self.assertEqual(tot_eligible_haircut, 48022)
        self.assertEqual(tot_excluded_haircut, 51978)
        self.assertEqual(tot_eligible_haircut + tot_excluded_haircut, 100000)
        
        # Verify haircut amounts consistency for each purpose: requested - sanctioned = haircut
        for p in purposes:
            req = p["haircut_eligible_requested_cu"]
            sanc = p["haircut_eligible_sanctioned_cu"]
            haircut = p["haircut_total_cu"]
            self.assertAlmostEqual(req - sanc, haircut, places=1)
            expected_pct = round(((req - sanc) / req) * 100.0, 4)
            self.assertAlmostEqual(p["aggregate_haircut_pct"], expected_pct, places=3)

    def test_04_portfolio_haircut_summary_and_exclusion_arithmetic(self):
        """Verify portfolio-level haircut calculation and complete exclusion arithmetic."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vw_portfolio_haircut_summary;")
        row = dict(cursor.fetchone())
        
        self.assertEqual(row["total_portfolio_applications"], 100000)
        self.assertEqual(row["eligible_applications_count"], 48022)
        self.assertAlmostEqual(row["total_eligible_requested_cu"], 6727376919.78, places=1)
        self.assertAlmostEqual(row["total_eligible_sanctioned_cu"], 5360674169.70, places=1)
        self.assertAlmostEqual(row["total_haircut_cu"], 1366702750.08, places=1)
        self.assertAlmostEqual(row["aggregate_haircut_pct"], 20.3155, places=3)
        
        # Exclusions breakdown
        self.assertEqual(row["excluded_rejected_count"], 50829)
        self.assertEqual(row["excluded_approved_missing_sanction_count"], 575)
        self.assertEqual(row["excluded_approved_missing_requested_count"], 584)
        self.assertEqual(row["total_excluded_count"], 51978)
        
        # Verify mutually exclusive cohorts for the 1,149 unique approved exclusions
        cursor.execute("""
            SELECT
                SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL AND (requested_loan_amount IS NOT NULL AND requested_loan_amount > 0) THEN 1 ELSE 0 END) AS missing_sanction_only,
                SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NOT NULL AND (requested_loan_amount IS NULL OR requested_loan_amount <= 0) THEN 1 ELSE 0 END) AS invalid_requested_only,
                SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL AND (requested_loan_amount IS NULL OR requested_loan_amount <= 0) THEN 1 ELSE 0 END) AS both_conditions
            FROM fct_loan_application;
        """)
        mex_row = dict(cursor.fetchone())
        self.assertEqual(mex_row["missing_sanction_only"], 565)
        self.assertEqual(mex_row["invalid_requested_only"], 574)
        self.assertEqual(mex_row["both_conditions"], 10)
        
        # Check sum of mutually exclusive cohorts equals 1,149
        unique_approved_excluded = mex_row["missing_sanction_only"] + mex_row["invalid_requested_only"] + mex_row["both_conditions"]
        self.assertEqual(unique_approved_excluded, 1149)
        
        # 48,022 eligible + 51,978 excluded = 100,000 total
        self.assertEqual(row["eligible_applications_count"] + row["total_excluded_count"], 100000)
        
        # Verify portfolio aggregate haircut is NOT an average of category haircut percentages
        cursor.execute("SELECT AVG(aggregate_haircut_pct) FROM vw_loan_purpose_analysis;")
        avg_category_pct = cursor.fetchone()[0]
        self.assertNotEqual(round(row["aggregate_haircut_pct"], 2), round(avg_category_pct, 2))
        self.assertAlmostEqual(row["aggregate_haircut_pct"], 20.3155, places=3)

    def test_05_risk_tier_summary_and_score_bounds(self):
        """Verify vw_risk_tier_summary uses source-provided categories and proper score metrics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vw_risk_tier_summary;")
        tiers = [dict(r) for r in cursor.fetchall()]
        
        self.assertEqual(len(tiers), 3)
        tier_names = [t["risk_tier"] for t in tiers]
        self.assertEqual(tier_names, ['Low', 'Medium', 'High'])
        
        tier_map = {t["risk_tier"]: t for t in tiers}
        self.assertEqual(tier_map["Low"]["total_applications"], 13266)
        self.assertEqual(tier_map["Medium"]["total_applications"], 48875)
        self.assertEqual(tier_map["High"]["total_applications"], 37859)
        
        # Total across tiers
        self.assertEqual(sum(t["total_applications"] for t in tiers), 100000)
        self.assertEqual(sum(t["approved_count"] for t in tiers), 49171)
        self.assertEqual(sum(t["rejected_count"] for t in tiers), 50829)
        
        # Score bounds verification
        for t in tiers:
            self.assertGreaterEqual(t["avg_proprietary_risk_score"], 0.0)
            self.assertLessEqual(t["avg_proprietary_risk_score"], 100.0)
            self.assertGreaterEqual(t["avg_bureau_credit_score"], 300.0)
            self.assertLessEqual(t["avg_bureau_credit_score"], 900.0)
            self.assertGreaterEqual(t["avg_normalized_risk_score"], 0.0)
            self.assertLessEqual(t["avg_normalized_risk_score"], 1.0)

    def test_06_data_quality_metrics_reconciliation(self):
        """Verify vw_data_quality_metrics accurately reports missingness and invalid flags."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vw_data_quality_metrics;")
        dq = dict(cursor.fetchone())
        
        self.assertEqual(dq["total_applications"], 100000)
        self.assertEqual(dq["invalid_annual_income_flag_count"], 35)
        self.assertEqual(dq["invalid_loan_amount_flag_count"], 35)
        self.assertEqual(dq["invalid_savings_balance_flag_count"], 35)
        self.assertEqual(dq["invalid_age_flag_count"], 25)
        self.assertEqual(dq["composite_invalid_financials_count"], 104)
        
        # Sanction missingness vs genuine zero
        self.assertEqual(dq["missing_sanctioned_amount_count"], 1206)
        self.assertEqual(dq["missing_sanctioned_approved_count"], 575)
        self.assertEqual(dq["missing_sanctioned_rejected_count"], 631)
        self.assertEqual(dq["genuine_zero_sanctioned_rejected_count"], 50198)
        self.assertEqual(
            dq["missing_sanctioned_approved_count"] + dq["missing_sanctioned_rejected_count"],
            dq["missing_sanctioned_amount_count"]
        )
        
        # Key missing value counts
        self.assertEqual(dq["missing_bureau_credit_score_count"], 1320)
        self.assertEqual(dq["missing_age_count"], 1226)
        self.assertEqual(dq["missing_annual_income_count"], 1327)
        self.assertEqual(dq["missing_savings_balance_count"], 1300)
        self.assertEqual(dq["missing_requested_loan_amount_count"], 1296)
        self.assertEqual(dq["missing_interest_rate_count"], 1305)
        self.assertEqual(dq["missing_debt_to_income_ratio_count"], 1259)
        self.assertEqual(dq["missing_proprietary_risk_score_count"], 1216)
        
        # Haircut exclusions
        self.assertEqual(dq["haircut_eligible_count"], 48022)
        self.assertEqual(dq["haircut_total_excluded_count"], 51978)

    def test_07_synthetic_servicing_isolation_from_views(self):
        """Verify no analytical view references the synthetic servicing demonstration table."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type = 'view';")
        views = cursor.fetchall()
        
        for name, sql in views:
            self.assertNotIn(
                "demo_synthetic_repayment_snapshot",
                sql,
                f"View {name} references quarantined synthetic servicing table!"
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
