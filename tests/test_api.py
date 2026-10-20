"""Automated Test Suite for RiskLens AI FastAPI Backend.

Verifies:
1. Health endpoint connectivity and schema metadata.
2. Response schemas, types, and NULL preservation across all endpoints.
3. KPI reconciliation with underlying database views.
4. Channel performance conservation and loan-purpose coverage (all 8 verified categories).
5. Portfolio and category haircut calculations and exclusion arithmetic.
6. Risk-tier distribution and proprietary score bounds.
7. Data-quality flags, missingness counts, and genuine zero preservation.
8. Application pagination, multi-attribute filtering, and sorting.
9. Input validation errors (422) and non-existent resource handling (404).
10. SQL injection resistance on all query parameters.
11. Quarantine of simulated servicing demonstration data.
12. Consistency across repeated requests.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.main import app

client = TestClient(app)


class TestRiskLensAPI(unittest.TestCase):
    """Integration test suite executing real HTTP requests against the FastAPI backend."""

    def test_01_health_endpoints(self):
        """Verify /health and /api/v1/health return 200 and healthy status."""
        for path in ["/health", "/api/v1/health"]:
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertTrue(data["connected"])
            self.assertEqual(data["schema_version"], "2.0.0")
            self.assertGreater(data["database_size_bytes"], 0)
            self.assertEqual(data["record_counts"]["fct_count"], 100000)
            self.assertEqual(data["record_counts"]["channel_count"], 4)
            self.assertEqual(data["record_counts"]["purpose_count"], 8)
            self.assertEqual(data["record_counts"]["location_count"], 75)
            self.assertEqual(data["record_counts"]["demo_servicing_count"], 48596)

    def test_02_portfolio_overview_kpis(self):
        """Verify /api/v1/overview returns verified portfolio KPIs and CU currency notation."""
        response = client.get("/api/v1/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total_applications"], 100000)
        self.assertEqual(data["approved_applications"], 49171)
        self.assertEqual(data["rejected_applications"], 50829)
        self.assertAlmostEqual(data["approval_rate_pct"], 49.171, places=3)
        self.assertAlmostEqual(data["rejection_rate_pct"], 50.829, places=3)
        self.assertAlmostEqual(data["total_requested_cu"], 14208864987.26, places=1)
        self.assertAlmostEqual(data["total_sanctioned_cu"], 5429935281.88, places=1)
        self.assertEqual(data["invalid_financials_count"], 104)
        self.assertEqual(data["missing_sanctioned_count"], 1206)
        self.assertEqual(data["currency_unit"], "CU")

    def test_03_channels_performance(self):
        """Verify /api/v1/channels returns all 4 channels and totals sum to 100,000."""
        response = client.get("/api/v1/channels")
        self.assertEqual(response.status_code, 200)
        channels = response.json()
        
        self.assertEqual(len(channels), 4)
        channel_names = {c["channel_name"] for c in channels}
        self.assertEqual(channel_names, {"Agent", "Branch", "Mobile App", "Online"})
        
        total_apps = sum(c["total_applications"] for c in channels)
        total_appr = sum(c["approved_applications"] for c in channels)
        total_rejc = sum(c["rejected_applications"] for c in channels)
        self.assertEqual(total_apps, 100000)
        self.assertEqual(total_appr, 49171)
        self.assertEqual(total_rejc, 50829)

    def test_04_loan_purposes_breakdown(self):
        """Verify /api/v1/loan-purposes returns all 8 verified source categories with haircut metrics."""
        response = client.get("/api/v1/loan-purposes")
        self.assertEqual(response.status_code, 200)
        purposes = response.json()
        
        self.assertEqual(len(purposes), 8)
        expected_categories = {
            "Business", "Car", "Debt Consolidation", "Education",
            "Home", "Medical", "Personal", "Vehicle"
        }
        found_categories = {p["purpose_name"] for p in purposes}
        self.assertEqual(found_categories, expected_categories)
        
        # Exact authoritative per-category assertions
        expected_metrics = {
            "Business": {"total": 14269, "approved": 7087, "rejected": 7182, "req": 2018127261.68, "sanc": 782181290.77, "eligible": 6929, "haircut_pct": 20.4019},
            "Car": {"total": 4349, "approved": 2677, "rejected": 1672, "req": 597847590.89, "sanc": 257683128.58, "eligible": 2677, "haircut_pct": 26.2916},
            "Debt Consolidation": {"total": 14236, "approved": 6910, "rejected": 7326, "req": 2010279716.67, "sanc": 762489028.84, "eligible": 6760, "haircut_pct": 20.3759},
            "Education": {"total": 14289, "approved": 6891, "rejected": 7398, "req": 2026642586.82, "sanc": 750392291.06, "eligible": 6720, "haircut_pct": 20.0174},
            "Home": {"total": 14183, "approved": 7189, "rejected": 6994, "req": 2000021248.92, "sanc": 788125042.79, "eligible": 7015, "haircut_pct": 20.6548},
            "Medical": {"total": 14167, "approved": 6860, "rejected": 7307, "req": 2019030030.13, "sanc": 758069310.24, "eligible": 6705, "haircut_pct": 20.2554},
            "Personal": {"total": 14421, "approved": 6964, "rejected": 7457, "req": 2051826588.70, "sanc": 774945106.58, "eligible": 6783, "haircut_pct": 19.9962},
            "Vehicle": {"total": 10086, "approved": 4593, "rejected": 5493, "req": 1485089963.45, "sanc": 556050083.02, "eligible": 4433, "haircut_pct": 17.4055},
        }
        for p in purposes:
            name = p["purpose_name"]
            exp = expected_metrics[name]
            self.assertEqual(p["total_applications"], exp["total"], f"API mismatch for {name} total")
            self.assertEqual(p["approved_applications"], exp["approved"], f"API mismatch for {name} approved")
            self.assertEqual(p["rejected_applications"], exp["rejected"], f"API mismatch for {name} rejected")
            self.assertAlmostEqual(p["total_requested_cu"], exp["req"], places=1, msg=f"API mismatch for {name} total requested")
            self.assertAlmostEqual(p["total_sanctioned_cu"], exp["sanc"], places=1, msg=f"API mismatch for {name} total sanctioned")
            self.assertEqual(p["haircut_eligible_count"], exp["eligible"], f"API mismatch for {name} eligible")
            self.assertAlmostEqual(p["aggregate_haircut_pct"], exp["haircut_pct"], places=3, msg=f"API mismatch for {name} haircut %")
        
        # Verify conservation of totals
        total_apps = sum(p["total_applications"] for p in purposes)
        total_appr = sum(p["approved_applications"] for p in purposes)
        total_rejc = sum(p["rejected_applications"] for p in purposes)
        total_req = sum(p["total_requested_cu"] for p in purposes)
        total_sanc = sum(p["total_sanctioned_cu"] for p in purposes)
        total_haircut_eligible = sum(p["haircut_eligible_count"] for p in purposes)
        total_haircut_excluded = sum(p["haircut_excluded_count"] for p in purposes)
        
        self.assertEqual(total_apps, 100000)
        self.assertEqual(total_appr, 49171)
        self.assertEqual(total_rejc, 50829)
        self.assertAlmostEqual(total_req, 14208864987.26, places=1)
        self.assertAlmostEqual(total_sanc, 5429935281.88, places=1)
        self.assertEqual(total_haircut_eligible, 48022)
        self.assertEqual(total_haircut_excluded, 51978)
        self.assertEqual(total_haircut_eligible + total_haircut_excluded, 100000)

    def test_05_haircut_summary_and_exclusions(self):
        """Verify /api/v1/haircut returns aggregate haircut (20.3155%) and exclusion arithmetic."""
        response = client.get("/api/v1/haircut")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        summary = data["portfolio_summary"]
        self.assertEqual(summary["total_portfolio_applications"], 100000)
        self.assertEqual(summary["eligible_applications_count"], 48022)
        self.assertAlmostEqual(summary["total_eligible_requested_cu"], 6727376919.78, places=1)
        self.assertAlmostEqual(summary["total_eligible_sanctioned_cu"], 5360674169.70, places=1)
        self.assertAlmostEqual(summary["total_haircut_cu"], 1366702750.08, places=1)
        self.assertAlmostEqual(summary["aggregate_haircut_pct"], 20.3155, places=3)
        self.assertEqual(summary["currency_unit"], "CU")
        
        exclusions = summary["exclusions"]
        self.assertEqual(exclusions["excluded_rejected_count"], 50829)
        self.assertEqual(exclusions["excluded_approved_missing_sanction_count"], 575)
        self.assertEqual(exclusions["excluded_approved_missing_requested_count"], 584)
        self.assertEqual(exclusions["total_excluded_count"], 51978)
        self.assertEqual(summary["eligible_applications_count"] + exclusions["total_excluded_count"], 100000)
        
        # Verify derived mutually exclusive cohorts:
        # Overlap = gross missing sanction + gross invalid requested - unique approved exclusions
        unique_approved_excluded = exclusions["total_excluded_count"] - exclusions["excluded_rejected_count"]  # 1,149
        overlap = (exclusions["excluded_approved_missing_sanction_count"] + exclusions["excluded_approved_missing_requested_count"]) - unique_approved_excluded
        missing_sanction_only = exclusions["excluded_approved_missing_sanction_count"] - overlap
        invalid_requested_only = exclusions["excluded_approved_missing_requested_count"] - overlap
        
        self.assertEqual(unique_approved_excluded, 1149)
        self.assertEqual(overlap, 10)
        self.assertEqual(missing_sanction_only, 565)
        self.assertEqual(invalid_requested_only, 574)
        self.assertEqual(missing_sanction_only + invalid_requested_only + overlap, 1149)
        
        # Verify all 8 purposes are present in breakdown
        self.assertEqual(len(data["by_purpose"]), 8)

    def test_06_risk_tiers_distribution(self):
        """Verify /api/v1/risk-tiers returns source-provided categories (Low, Medium, High)."""
        response = client.get("/api/v1/risk-tiers")
        self.assertEqual(response.status_code, 200)
        tiers = response.json()
        
        self.assertEqual(len(tiers), 3)
        tier_names = [t["risk_tier"] for t in tiers]
        self.assertEqual(tier_names, ["Low", "Medium", "High"])
        
        tier_map = {t["risk_tier"]: t for t in tiers}
        self.assertEqual(tier_map["Low"]["total_applications"], 13266)
        self.assertEqual(tier_map["Medium"]["total_applications"], 48875)
        self.assertEqual(tier_map["High"]["total_applications"], 37859)
        
        # Verify score bounds and tier notes
        for t in tiers:
            self.assertGreaterEqual(t["avg_proprietary_risk_score"], 0.0)
            self.assertLessEqual(t["avg_proprietary_risk_score"], 100.0)
            self.assertIn("not a probability", t["tier_notes"].lower())

    def test_07_data_quality_metrics(self):
        """Verify /api/v1/data-quality returns complete audit flags, missingness, and zero counts."""
        response = client.get("/api/v1/data-quality")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total_applications"], 100000)
        flags = data["audit_flags"]
        self.assertEqual(flags["invalid_annual_income_flag_count"], 35)
        self.assertEqual(flags["invalid_loan_amount_flag_count"], 35)
        self.assertEqual(flags["invalid_savings_balance_flag_count"], 35)
        self.assertEqual(flags["invalid_age_flag_count"], 25)
        self.assertEqual(flags["composite_invalid_financials_count"], 104)
        
        missing = data["missing_values"]
        self.assertEqual(missing["missing_sanctioned_amount_count"], 1206)
        self.assertEqual(missing["missing_sanctioned_approved_count"], 575)
        self.assertEqual(missing["missing_sanctioned_rejected_count"], 631)
        self.assertEqual(missing["genuine_zero_sanctioned_rejected_count"], 50198)
        self.assertEqual(missing["missing_bureau_credit_score_count"], 1320)
        self.assertEqual(missing["missing_age_count"], 1226)

    def test_08_applications_pagination_and_sorting(self):
        """Verify /api/v1/applications pagination and sorting."""
        # Page 1 default
        response = client.get("/api/v1/applications?page=1&page_size=20")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_items"], 100000)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 20)
        self.assertEqual(data["total_pages"], 5000)
        self.assertEqual(len(data["items"]), 20)
        
        # Page 2
        response2 = client.get("/api/v1/applications?page=2&page_size=20")
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertEqual(data2["page"], 2)
        # Ensure page 1 and page 2 items are distinct
        p1_ids = [item["application_id"] for item in data["items"]]
        p2_ids = [item["application_id"] for item in data2["items"]]
        self.assertTrue(set(p1_ids).isdisjoint(set(p2_ids)))
        
        # Sorting by requested_loan_amount desc
        sort_resp = client.get("/api/v1/applications?page=1&page_size=10&sort_by=requested_loan_amount&sort_order=desc")
        self.assertEqual(sort_resp.status_code, 200)
        sort_items = sort_resp.json()["items"]
        amounts = [it["requested_loan_amount"] for it in sort_items if it["requested_loan_amount"] is not None]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_09_applications_filtering(self):
        """Verify filtering by decision, channel, loan_purpose, risk_tier, and invalid financials."""
        # Filter by decision: Approved
        res_app = client.get("/api/v1/applications?decision=Approved&page_size=10")
        self.assertEqual(res_app.status_code, 200)
        data_app = res_app.json()
        self.assertEqual(data_app["total_items"], 49171)
        for it in data_app["items"]:
            self.assertEqual(it["underwriting_decision"], "Approved")
            self.assertEqual(it["is_approved"], 1)
            
        # Filter by decision: Rejected
        res_rej = client.get("/api/v1/applications?decision=Rejected&page_size=10")
        self.assertEqual(res_rej.status_code, 200)
        data_rej = res_rej.json()
        self.assertEqual(data_rej["total_items"], 50829)
        for it in data_rej["items"]:
            self.assertEqual(it["underwriting_decision"], "Rejected")
            self.assertEqual(it["is_approved"], 0)
            
        # Filter by channel: Mobile App
        res_ch = client.get("/api/v1/applications?channel=Mobile%20App&page_size=10")
        self.assertEqual(res_ch.status_code, 200)
        data_ch = res_ch.json()
        self.assertEqual(data_ch["total_items"], 24256)
        for it in data_ch["items"]:
            self.assertEqual(it["channel_name"], "Mobile App")
            
        # Filter by loan_purpose: Medical
        res_purp = client.get("/api/v1/applications?loan_purpose=Medical&page_size=10")
        self.assertEqual(res_purp.status_code, 200)
        data_purp = res_purp.json()
        self.assertEqual(data_purp["total_items"], 14167)
        for it in data_purp["items"]:
            self.assertEqual(it["purpose_name"], "Medical")
            
        # Filter by risk_tier: High
        res_tier = client.get("/api/v1/applications?risk_tier=High&page_size=10")
        self.assertEqual(res_tier.status_code, 200)
        data_tier = res_tier.json()
        self.assertEqual(data_tier["total_items"], 37859)
        for it in data_tier["items"]:
            self.assertEqual(it["risk_tier"], "High")
            
        # Filter by has_invalid_financials: 1
        res_flags = client.get("/api/v1/applications?has_invalid_financials=1&page_size=20")
        self.assertEqual(res_flags.status_code, 200)
        data_flags = res_flags.json()
        self.assertEqual(data_flags["total_items"], 104)
        for it in data_flags["items"]:
            self.assertEqual(it["has_invalid_financials"], 1)

    def test_10_application_by_id_and_null_preservation(self):
        """Verify single application retrieval and preservation of NULL values."""
        # Application 500001 (Approved)
        res = client.get("/api/v1/applications/500001")
        self.assertEqual(res.status_code, 200)
        app_data = res.json()
        self.assertEqual(app_data["application_id"], 500001)
        self.assertEqual(app_data["underwriting_decision"], "Approved")
        self.assertEqual(app_data["is_approved"], 1)
        self.assertAlmostEqual(app_data["sanctioned_approved_amount"], 34868.81, places=2)
        self.assertIn("channel_name", app_data)
        self.assertIn("purpose_name", app_data)
        self.assertIn("region", app_data)
        
        # Application 530166 (Rejected with genuine zero and source NULLs)
        res_null = client.get("/api/v1/applications/530166")
        self.assertEqual(res_null.status_code, 200)
        null_data = res_null.json()
        self.assertEqual(null_data["application_id"], 530166)
        self.assertEqual(null_data["underwriting_decision"], "Rejected")
        self.assertEqual(null_data["is_approved"], 0)
        # Verify genuine recorded zero is NOT nullified
        self.assertEqual(null_data["sanctioned_approved_amount"], 0.0)
        # Verify genuine source NULLs are preserved as None in Python / null in JSON
        self.assertIsNone(null_data["bureau_credit_score"])
        self.assertIsNone(null_data["savings_balance"])
        
        # Test unknown application ID returns 404
        res_404 = client.get("/api/v1/applications/999999999")
        self.assertEqual(res_404.status_code, 404)
        self.assertIn("not found", res_404.json()["detail"].lower())

    def test_11_input_validation_errors(self):
        """Verify invalid query parameters return HTTP 422 Unprocessable Entity."""
        # Invalid page (page < 1)
        res1 = client.get("/api/v1/applications?page=0")
        self.assertEqual(res1.status_code, 422)
        
        # Invalid page size (page_size > 100)
        res2 = client.get("/api/v1/applications?page_size=101")
        self.assertEqual(res2.status_code, 422)
        
        # Invalid decision filter
        res3 = client.get("/api/v1/applications?decision=Pending")
        self.assertEqual(res3.status_code, 422)
        
        # Invalid channel filter
        res4 = client.get("/api/v1/applications?channel=InPerson")
        self.assertEqual(res4.status_code, 422)
        
        # Invalid loan purpose
        res5 = client.get("/api/v1/applications?loan_purpose=Vacation")
        self.assertEqual(res5.status_code, 422)
        
        # Invalid risk tier
        res6 = client.get("/api/v1/applications?risk_tier=Critical")
        self.assertEqual(res6.status_code, 422)
        
        # Invalid sort column
        res7 = client.get("/api/v1/applications?sort_by=secret_column")
        self.assertEqual(res7.status_code, 422)
        
        # Invalid sort order
        res8 = client.get("/api/v1/applications?sort_order=sideways")
        self.assertEqual(res8.status_code, 422)
        
        # Invalid application_id format
        res9 = client.get("/api/v1/applications/invalid_id")
        self.assertEqual(res9.status_code, 422)

    def test_12_sql_injection_resistance(self):
        """Verify SQL injection attempts in query parameters fail validation or are safely parameterized."""
        injection_payloads = [
            "' OR '1'='1",
            "1; DROP TABLE fct_loan_application; --",
            "Approved' OR 1=1 --",
            "1' UNION SELECT * FROM fct_loan_application --"
        ]
        for payload in injection_payloads:
            # When passed to validated parameter (decision), must return 422
            resp = client.get(f"/api/v1/applications?decision={payload}")
            self.assertEqual(resp.status_code, 422)
            
            # When passed as application_id path param, must return 422
            resp_path = client.get(f"/api/v1/applications/{payload}")
            self.assertEqual(resp_path.status_code, 422)

    def test_13_servicing_demo_quarantine(self):
        """Verify simulated servicing demo endpoint is namespaced and isolated from primary metrics."""
        # Application 500001 is an approved application present in the demo snapshot
        res = client.get("/api/v1/demo/servicing-snapshot/500001")
        self.assertEqual(res.status_code, 200)
        demo_data = res.json()
        self.assertEqual(demo_data["application_id"], 500001)
        self.assertTrue(demo_data["demonstration_only"])
        self.assertIn("isolated", demo_data["isolation_notice"].lower())
            
        # Application 512257 is a rejected application, quarantined and excluded from demo snapshot
        res_rej = client.get("/api/v1/demo/servicing-snapshot/512257")
        self.assertEqual(res_rej.status_code, 404)

        # Non-existent demo record returns 404
        res_404 = client.get("/api/v1/demo/servicing-snapshot/999999999")
        self.assertEqual(res_404.status_code, 404)

    def test_14_repeated_request_consistency(self):
        """Verify API produces consistent results across repeated invocations."""
        resp1 = client.get("/api/v1/overview")
        resp2 = client.get("/api/v1/overview")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp1.json(), resp2.json())

    def test_15_entrypoint_import_no_circular_dependency(self):
        """Verify src.api.main entrypoint can be imported in isolation without circular import errors."""
        import subprocess
        # Test 1: Clean subprocess import of src.api.main:app
        cmd1 = [sys.executable, "-c", "from src.api.main import app; assert app.title is not None"]
        proc1 = subprocess.run(cmd1, capture_output=True, text=True)
        self.assertEqual(proc1.returncode, 0, f"Importing src.api.main failed: {proc1.stderr}")

        # Test 2: Verify custom spec file loader (used by Vercel serverless Python runtime)
        code2 = (
            "import importlib.util, sys;"
            "spec = importlib.util.spec_from_file_location('src.api.main', 'src/api/main.py');"
            "module = importlib.util.module_from_spec(spec);"
            "sys.modules['src.api.main'] = module;"
            "spec.loader.exec_module(module);"
            "assert hasattr(module, 'app');"
            "assert module.app.title is not None"
        )
        cmd2 = [sys.executable, "-c", code2]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        self.assertEqual(proc2.returncode, 0, f"Spec loader execution failed: {proc2.stderr}")


if __name__ == '__main__':
    unittest.main(verbosity=2)

