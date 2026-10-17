# RiskLens AI — Phase 1 Recommendation & Scope Boundary
**Phase 1 Forensic Audit Deliverable**  
**Dataset Source:** `data/raw/kaggle_original.csv`  
**Dataset Dimensions:** 100,150 Rows × 67 Columns (44.61 MB)  
**Status:** Complete Forensic Audit  

---

## 1. Executive Summary & Recommended MVP Scope

The Phase 1 forensic audit establishes that `kaggle_original.csv` contains a robust, highly detailed core underwriting dataset of **100,000 distinct loan applications** across 36 original features, accompanied by 31 synthetic or derived columns.

To build a credible, defensible, and impressive **Data Analyst / Business Analyst Portfolio Platform (RiskLens AI)** in Phase 2, we recommend anchoring the Minimum Viable Product (MVP) around **Credit Risk Underwriting Intelligence, Portfolio Sanctions Analytics, and Delinquency Risk Segmentation**.

---

## 2. Recommended Phase 2 MVP Architecture & Features

### Feature Set 1: Executive Portfolio & Underwriting Intelligence Dashboard
- **Volume & Conversion Funnel:** Total application volume (100,000), approval rate (~49.2%), rejection rate (~50.8%), segmented by acquisition channel (`Online`, `Branch`, `Mobile App`, `Agent`) and macro-region (`West`, `Central`, `South`, `East`).
- **Policy Haircut Analytics:** Comparison of requested loan principal ($18.5B+) versus sanctioned loan principal, calculating underwriter risk haircuts across loan purposes (`Home`, `Education`, `Vehicle`, `Personal`, `Debt Consolidation`).
- **Risk Score Tier Calibration:** Portfolio distribution across `Low`, `Medium`, and `High` risk tiers mapped against external credit bureau score bands (FICO tiers).

### Feature Set 2: Borrower Financial Health & Solvency Matrix
- **Debt-to-Income (DTI) & Cash Flow Pressure:** Scatter and distribution analysis of applicant gross annual income against monthly debt obligations and DTI percentages.
- **Liquid Reserve & Asset Cushion Analysis:** Analysis of borrower liquidity (`Savings_Balance` + `Checking_Balance`) versus total requested debt.
- **Employment Stability & Income Segmentation:** Underwriting conversion and average sanctioned loan amounts across employment categories (`Salaried`, `Self-Employed`, `Contract`, `Freelancer`).

### Feature Set 3: Funded Loan Repayment & Delinquency Snapshot
- **Disbursement & Outstanding Balances:** Tracking sanctioned versus disbursed capital on the 49,243 approved loans.
- **Single-Installment Collection Efficiency:** Recovery percentage (`amount_paid / amount_due`) and days past due distribution (`days_late`), strictly isolated to approved and disbursed loans.
- **Prior Bureau Delinquency Drag:** Evaluating how historical bureau delinquencies (`Late_Payments_Last_2_Years`, `Previous_Loan_Status`) influence current repayment delays.

---

## 3. Explicitly Unsupported Features (Out-of-Scope)

To preserve analytical integrity and professional credibility, the following features **MUST NOT** be included in Phase 2:

1. **True Loan Default Prediction Models:**
   - **Reason:** No post-origination default outcome variable exists in the dataset.
   - **Alternative:** Train an **Underwriting Decision Classifier** (`Loan_Approved == 'Approved'` vs `'Rejected'`) or an **Underwriter Risk Tier Classifier** (`Default_Risk`).
2. **Customer Lifetime Value (LTV) & Repeat Borrower Retention:**
   - **Reason:** Every row is an isolated individual application (100,000 distinct customer IDs). No multi-application history exists.
3. **Municipal / City-Level Geographic Dashboards:**
   - **Reason:** The `city` column is merely `Region || '_City'` (e.g. `West_City`). Real city-level granularity does not exist.
4. **Time-Series Vintage Default / Loss Curve Modeling:**
   - **Reason:** The dataset contains only a single payment snapshot per loan; multi-month repayment curves do not exist.

---

## 4. Key Engineering Assumptions for Phase 2

1. **Deduplication:** The 150 exact row duplicates will be dropped during Phase 2 ingestion, establishing a clean analytical population of **100,000 records**.
2. **Authoritative Field Selection:** Part 1 columns (`Annual_Income`, `Total_Liabilities`, `Bank_Account_Age_Years`, `Late_Payments_Last_2_Years`) will be treated as canonical ground truth over redundant Part 2 clones.
3. **Repayment Isolation:** Repayment fields will be set to `NULL` for all 50,907 Rejected applications to eliminate the fatal business contradiction present in the raw data.
4. **Negative Value Normalization:** The 105 negative values in `Annual_Income`, `Loan_Amount`, and `Savings_Balance` will be converted using absolute value `ABS()` or set to `NULL` with an audit flag.
5. **Sentinel Date Cleansing:** The 20 `'not_a_date'` values and 20 `'31/31/2025'` values will be converted to `NULL` prior to date casting.

---

## 5. Unresolved Questions for User Decision Gate

Before beginning Phase 2 (ETL pipeline and database setup), we require the user's explicit decision on the following **4 strategic questions**:

### Question 1: Negative Numeric Value Strategy
- **Context:** Exactly 35 records have negative `Annual_Income` (min -$211,679.11), 35 have negative `Loan_Amount` (min -$375,200.41), and 35 have negative `Savings_Balance` (min -$62,004.75).
- **Options:**
  - **Option A (Recommended):** Assume an accidental sign inversion during data generation and apply `ABS(value)`.
  - **Option B:** Set negative values to `NULL` to prevent potentially corrupt data from entering aggregations.
  - **Option C:** Filter out and permanently drop the 105 affected rows.

### Question 2: Scope of the Repayment Table in SQL
- **Context:** The raw file contains synthetic repayment records for all 100,150 rows, including 50,907 rejected loans.
- **Options:**
  - **Option A (Recommended):** Restrict `fact_repayment_installment` strictly to the 49,243 Approved/Disbursed loans. Rejected loans have no repayment rows.
  - **Option B:** Keep a flat table containing all rows, but force repayment columns to `NULL` whenever `Loan_Approved == 'Rejected'`.
  - **Option C:** Retain the raw synthetic values as-is (Not recommended; corrupts financial accounting).

### Question 3: Geographic Dimension Presentation
- **Context:** The `city` column is 100% synthetic (`West_City`, `Central_City`, `South_City`, `East_City`).
- **Options:**
  - **Option A (Recommended):** Present the geographic analytics purely at the `Region` level (West, Central, South, East) and transparently document `city` as a synthetic placeholder.
  - **Option B:** Display `city` as a UI display convenience while querying `Region` underneath.

### Question 4: Scope of Predictive Modeling in Future Phases
- **Context:** Without a true default flag, standard "Default Prediction" is methodologically invalid.
- **Options:**
  - **Option A (Recommended):** Frame the predictive AI model as an **"Underwriting Approval Optimization Model"** (predicting loan sanctioning probability and identifying borderline approvals).
  - **Option B:** Frame the predictive model as a **"Risk Score Regressor"** (predicting continuous proprietary `Risk_Score` from financial fundamentals).
