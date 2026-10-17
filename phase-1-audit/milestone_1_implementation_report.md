# RiskLens AI — Milestone 1 Implementation Report

**Project:** RiskLens AI — Financial Risk Intelligence & Business Analytics Platform  
**Target Milestone:** **Milestone 1: Data Pipeline Implementation**  
**Raw Source File:** `data/raw/kaggle_original.csv`  
**Processed Target Database:** `data/processed/risklens_analytics.db` (41,078,784 bytes)  
**Execution Timestamp:** 2026-10-16  
**Status:** **COMPLETE — 100% Tests Passing — Awaiting Milestone 2 Approval**

---

## 1. Executive Summary & Verification Ledger

The Milestone 1 ETL data pipeline and SQLite analytical database have been implemented, executed, and validated against the physical source file (`data/raw/kaggle_original.csv`). All 19 automated tests in `tests/test_etl_pipeline.py` passed with zero errors.

### Master Verification Ledger

| Metric / Requirement | Reported Baseline | Actual Reproduced Value | Verification Status | Source & Method |
|---|---|---|---|---|
| **Raw File Immutability (SHA-256)** | `027a120ef...076c` | `027a120ef9bb38697331dd6f58dc06a84d86ac59fddcd388e3d37c6222ee076c` | **MATCH (100%)** | Verified before and after ETL via `hashlib.sha256` |
| **Raw Row & Column Dimensions** | 100,150 rows, 67 cols | 100,150 rows, 67 cols | **MATCH (100%)** | `pd.read_csv`, physical file shape |
| **Exact Duplicate Rows** | 150 rows | 150 rows | **MATCH (100%)** | Programmatic mask `df.duplicated(subset=['Application_ID'])` |
| **Deduplicated Analytical Grain** | 100,000 unique apps | 100,000 unique apps | **MATCH (100%)** | `SELECT COUNT(DISTINCT application_id) FROM fct_loan_application` |
| **Underwriting Decision: Approved** | 49,171 rows | 49,171 rows (49.171%) | **MATCH (100%)** | `SELECT SUM(is_approved) FROM fct_loan_application` |
| **Underwriting Decision: Rejected** | 50,829 rows | 50,829 rows (50.829%) | **MATCH (100%)** | `SELECT COUNT(*) - SUM(is_approved) FROM fct_loan_application` |
| **Location / Housing Dimension** | 75 combinations | 75 combinations | **MATCH (100%)** | `SELECT COUNT(*) FROM dim_residence_property_location` |
| **Channel Dimension** | 4 channels | 4 channels | **MATCH (100%)** | `SELECT COUNT(*) FROM dim_channel` (`Online`, `Branch`, `Mobile App`, `Agent`) |
| **Loan Purpose Dimension** | 5 (Reported Baseline) | **8 categories (Actual Source)** | **DISCREPANCY DOCUMENTED** | `SELECT COUNT(*) FROM dim_loan_purpose` (Discrepancy explained below) |
| **Invalid Negative Financials** | 104 unique applications | 104 unique applications | **MATCH (100%)** | `SELECT SUM(has_invalid_financials) FROM fct_loan_application` |
| **Invalid Demographics (Age)** | 25 applications | 25 applications | **MATCH (100%)** | `SELECT SUM(has_invalid_age) FROM fct_loan_application` |
| **Sanctioned Amount Missingness** | 1,206 missing | 1,206 missing (575 App / 631 Rej) | **MATCH (100%)** | `SELECT SUM(has_missing_sanctioned_amount) FROM fct_loan_application` |
| **Recorded Sanctioned Zeros** | 50,198 zeros | 50,198 zeros (all on Rejections) | **MATCH (100%)** | `SELECT COUNT(*) FROM fct_loan_application WHERE sanctioned_approved_amount = 0.0` |
| **Haircut Eligible Population** | 48,022 applications | 48,022 applications | **MATCH (100%)** | Verified via programmatic assertion & SQL query |
| **Aggregate Haircut Percentage** | ~20.3155% | **20.3155%** | **MATCH (100%)** | 1.366B CU haircut on 6.727B CU requested |
| **Synthetic Servicing Snapshot** | 48,596 applications | 48,596 applications | **MATCH (100%)** | `SELECT COUNT(*) FROM demo_synthetic_repayment_snapshot` |
| **Foreign Key Violations** | 0 violations | 0 violations | **MATCH (100%)** | `PRAGMA foreign_key_check;` returned empty set |

---

## 2. Discrepancy Analysis: Loan Purpose Dimension

- **Reported Baseline:** 5 loan purposes (`Home`, `Education`, `Vehicle`, `Personal`, `Debt Consolidation`).
- **Empirical Source Discovery:** Upon profiling all 100,000 deduplicated records in `data/raw/kaggle_original.csv`, `Loan_Purpose` contains **8 distinct categories**:
  1. `Personal`: 14,421 applications
  2. `Education`: 14,289 applications
  3. `Business`: 14,269 applications
  4. `Debt Consolidation`: 14,236 applications
  5. `Home`: 14,183 applications
  6. `Medical`: 14,167 applications
  7. `Vehicle`: 10,086 applications
  8. `Car`: 4,349 applications
- **Resolution:** As instructed by the core project principles ("Use the existing `data/raw/kaggle_original.csv` as the source of truth; do not invent data or silently change rules"), `dim_loan_purpose` was populated with all 8 verified source categories without dropping rows or forcing lossy consolidation.

---

## 3. Files Created and Modified

1. **`src/data/schema.py`** (Created):
   - SQLite DDL statements for lookup dimensions, primary fact table `fct_loan_application`, demonstration snapshot `demo_synthetic_repayment_snapshot`, performance indices, and analytical views.
   - Enforces `chk_decision_consistency`, non-negative constraints allowing `NULL`, and foreign key relations.
2. **`src/data/validators.py`** (Created):
   - Data validation and sanitization functions: `compute_file_sha256`, `parse_strict_boolean`, `validate_credit_score`, `validate_age`, `clean_financial_value`, `validate_decision`, and `validate_row_data`.
   - Never applies `ABS()` to negatives; flags and nullifies corrupted values.
   - Enforces integral credit score validation, rejecting unexpected fractionals.
3. **`src/data/etl_pipeline.py`** (Created):
   - Production ETL pipeline with atomic replacement (`.tmp` swap), transactional execution, pre/post SHA-256 hash validation, and automated post-load integrity checks.
4. **`tests/test_etl_pipeline.py`** (Created):
   - Comprehensive test suite covering 19 distinct unit and integration assertions.
5. **`data/processed/risklens_analytics.db`** (Generated):
   - SQLite analytics database (41,078,784 bytes) containing 100,000 fact rows, conformed dimensions, and 48,596 demonstration servicing records.

---

## 4. Exact Execution Commands & Results

### Command 1: ETL Pipeline Execution
```bash
python3 src/data/etl_pipeline.py
```
**Execution Output:**
```text
2026-10-16 16:56:35,409 [INFO] RiskLensETL: === STARTING RISKLENS AI ETL PIPELINE ===
2026-10-16 16:56:35,409 [INFO] RiskLensETL: Inspecting raw file: data/raw/kaggle_original.csv (46,779,106 bytes)
2026-10-16 16:56:35,525 [INFO] RiskLensETL: Verified pre-load SHA-256: 027a120ef9bb38697331dd6f58dc06a84d86ac59fddcd388e3d37c6222ee076c
2026-10-16 16:56:35,525 [INFO] RiskLensETL: Reading raw CSV into staging...
2026-10-16 16:56:37,021 [INFO] RiskLensETL: Raw dataset loaded: 100,150 rows, 67 columns
2026-10-16 16:56:37,125 [INFO] RiskLensETL: Deduplication complete: 150 duplicate rows removed, 100,000 clean rows retained
2026-10-16 16:56:37,131 [INFO] RiskLensETL: Target build database: data/processed/risklens_analytics.db.tmp
2026-10-16 16:56:37,131 [INFO] RiskLensETL: Creating SQLite warehouse schema, constraints, and views...
2026-10-16 16:56:37,133 [INFO] RiskLensETL: Populating conformed lookup dimensions...
2026-10-16 16:56:37,261 [INFO] RiskLensETL: Loaded dim_residence_property_location: 75 distinct combinations
2026-10-16 16:56:37,261 [INFO] RiskLensETL: Loaded dim_channel: 4 distinct channels
2026-10-16 16:56:37,261 [INFO] RiskLensETL: Loaded dim_loan_purpose: 8 distinct purposes
2026-10-16 16:56:37,261 [INFO] RiskLensETL: Transforming and loading fct_loan_application records...
2026-10-16 16:57:04,766 [INFO] RiskLensETL: Loaded fct_loan_application: 100,000 rows
2026-10-16 16:57:04,768 [INFO] RiskLensETL: Populating demo_synthetic_repayment_snapshot (isolated servicing demonstration)...
2026-10-16 16:57:04,841 [INFO] RiskLensETL: Eligible approved applications with positive sanction: 48,596
2026-10-16 16:57:08,883 [INFO] RiskLensETL: Loaded demo_synthetic_repayment_snapshot: 48,596 rows
2026-10-16 16:57:08,896 [INFO] RiskLensETL: Executing comprehensive post-load integrity checks...
2026-10-16 16:57:08,948 [INFO] RiskLensETL: PASS: PRAGMA foreign_key_check returned 0 violations.
2026-10-16 16:57:08,984 [INFO] RiskLensETL: PASS: Decision reconciliation exact: 49,171 Approved, 50,829 Rejected.
2026-10-16 16:57:09,026 [INFO] RiskLensETL: PASS: Quality flags verified: 104 composite invalid financials, 25 invalid ages.
2026-10-16 16:57:09,068 [INFO] RiskLensETL: PASS: Sanction missingness verified: 575 Approved NULLs, 631 Rejected NULLs, 50,198 Rejected Zeros.
2026-10-16 16:57:09,079 [INFO] RiskLensETL: PASS: Haircut KPI validated: 48,022 eligible applications, Haircut = 1,366,702,750.08 CU (20.3155%).
2026-10-16 16:57:09,127 [INFO] RiskLensETL: Database transaction committed successfully.
2026-10-16 16:57:09,248 [INFO] RiskLensETL: Raw CSV immutability confirmed: SHA-256 unchanged (027a120ef9bb38697331dd6f58dc06a84d86ac59fddcd388e3d37c6222ee076c)
2026-10-16 16:57:09,248 [INFO] RiskLensETL: Atomically replacing target database: data/processed/risklens_analytics.db
2026-10-16 16:57:09,248 [INFO] RiskLensETL: === ETL PIPELINE COMPLETED SUCCESSFULLY: data/processed/risklens_analytics.db (41,078,784 bytes) ===
```

### Command 2: Automated Test Suite Execution
```bash
python3 tests/test_etl_pipeline.py
```
**Test Results:**
```text
test_01_raw_csv_immutability ... ok
test_02_deduplication_and_row_counts ... ok
test_03_decision_reconciliation ... ok
test_04_dimension_and_foreign_key_integrity ... ok
test_05_decision_consistency_constraint ... ok
test_06_financial_cleaning_and_flags ... ok
test_07_age_cleaning_and_flags ... ok
test_08_credit_score_integrity ... ok
test_09_sanctioned_amount_missing_vs_zero ... ok
test_10_haircut_kpi_eligibility_and_rate ... ok
test_11_synthetic_servicing_isolation ... ok
test_12_transaction_rollback_and_preservation ... ok
test_13_pipeline_repeatability ... ok
test_age_validation ... ok
test_credit_score_casting_and_rejection ... ok
test_decision_consistency ... ok
test_financial_cleaning_never_abs ... ok
test_sanctioned_amount_handling ... ok
test_strict_boolean_parsing ... ok

----------------------------------------------------------------------
Ran 19 tests in 69.988s

OK
```

---

## 5. Analytical Views & Aggregates in Loaded Database

### View 1: `vw_portfolio_kpis`
- Total Applications: **100,000**
- Approved Applications: **49,171** (49.171%)
- Rejected Applications: **50,829** (50.829%)
- Composite Invalid Financials: **104**
- Missing Sanctioned Amounts: **1,206**

### View 2: `vw_channel_performance`
| Channel Name | Total Received | Total Approved | Total Rejected | Approval Rate (%) |
|---|---|---|---|---|
| **Online** | 30,039 | 15,164 | 14,875 | 50.48% |
| **Branch** | 25,283 | 12,489 | 12,794 | 49.40% |
| **Mobile App** | 24,256 | 11,842 | 12,414 | 48.82% |
| **Agent** | 20,422 | 9,676 | 10,746 | 47.38% |

### View 3: `vw_underwriting_haircut` (by Loan Purpose)
| Purpose Name | Eligible Approved Count | Total Requested (CU) | Total Sanctioned (CU) | Total Haircut (CU) | Haircut Rate (%) |
|---|---|---|---|---|---|
| **Car** | 2,677 | 349,597,901.79 | 257,683,128.58 | 91,914,773.21 | 26.2916% |
| **Home** | 7,015 | 978,968,509.30 | 776,764,554.36 | 202,203,954.94 | 20.6548% |
| **Business** | 6,929 | 971,603,348.40 | 773,378,055.87 | 198,225,292.53 | 20.4019% |
| **Debt Consolidation** | 6,760 | 946,986,677.96 | 754,029,943.56 | 192,956,734.40 | 20.3759% |
| **Medical** | 6,705 | 938,536,418.11 | 748,432,248.46 | 190,104,169.65 | 20.2554% |
| **Education** | 6,720 | 924,612,228.71 | 739,528,475.06 | 185,083,753.65 | 20.0174% |
| **Personal** | 6,783 | 955,528,709.21 | 764,459,744.39 | 191,068,964.82 | 19.9962% |
| **Vehicle** | 4,433 | 661,543,126.30 | 546,398,019.42 | 115,145,106.88 | 17.4055% |
| **Portfolio Total** | **48,022** | **6,727,376,919.78** | **5,360,674,169.70** | **1,366,702,750.08** | **20.3155%** |

### View 4: `vw_risk_tier_summary`
| Risk Tier | Total Applications | Approved Count | Approval Rate (%) | Mean Internal Score | Mean Bureau Score |
|---|---|---|---|---|---|
| **Low** | 13,266 | 12,922 | 97.41% | 23.70 | 768.0 |
| **Medium** | 48,875 | 35,335 | 72.30% | 52.13 | 712.0 |
| **High** | 37,859 | 914 | 2.41% | 81.03 | 605.8 |

---

## 6. Remaining Blockers & Next Milestone

- **Remaining Technical Blockers for Milestone 1:** **ZERO.**
- **Next Milestone:** **Milestone 2 (Analytical SQL Views, Backend Data Access Layer & FastAPI Endpoints)**.

---

**MILESTONE 1 COMPLETE. STOPPING HERE.**  
*Awaiting your explicit authorization before proceeding to Milestone 2.*
