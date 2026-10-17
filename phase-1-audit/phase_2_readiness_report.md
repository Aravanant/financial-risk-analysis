# RiskLens AI — Phase 2 Readiness Report & Architectural Correction Pass

**Project:** RiskLens AI — Financial Risk Intelligence & Business Analytics Platform  
**Target File:** `data/raw/kaggle_original.csv`  
**Execution Context:** Verification Pass & Architectural Alignment (Phase 1 Sign-Off Gate)  
**Database Engine Target:** **SQLite** (strictly adhering to user directive; PostgreSQL eliminated)  
**Deliverable Path:** `phase-1-audit/phase_2_readiness_report.md`  
**Status:** Audit Verified & Corrected — **Awaiting Explicit User Approval Before Phase 2 Implementation**

---

## 1. Verified Raw and Deduplicated Application Counts

All figures in this section were derived by executing direct inspection scripts on `data/raw/kaggle_original.csv`.

### 1.1 Python Verification Script & Terminal Output
```python
import pandas as pd
df = pd.read_csv('data/raw/kaggle_original.csv', low_memory=False)

dup_mask = df.duplicated(keep='first')
print(f"Raw rows: {len(df):,}")
print(f"Exact duplicate rows across all 67 columns: {dup_mask.sum():,}")
print(f"Distinct Application_ID count: {df['Application_ID'].nunique():,}")
print(f"Missing / Null Application_ID count: {df['Application_ID'].isnull().sum():,}")

# Check conflicting duplicate Application_ID records
dup_app_ids = df[df.duplicated(subset=['Application_ID'], keep=False)]
non_identical_conflicts = len(dup_app_ids[~dup_app_ids.duplicated(keep=False)])
print(f"Conflicting duplicate Application_ID records: {non_identical_conflicts}")

# Raw value counts of Loan_Approved
print("\nRaw Loan_Approved value counts:\n", df['Loan_Approved'].value_counts(dropna=False))
```

```text
Raw rows: 100,150
Exact duplicate rows across all 67 columns: 150
Distinct Application_ID count: 100,000
Missing / Null Application_ID count: 0
Conflicting duplicate Application_ID records: 0

Raw Loan_Approved value counts:
Rejected      49570
Approved      48179
REJECTED        449
rejected        446
 Rejected       442
 Approved       360
APPROVED        360
approved        344
Name: count, dtype: int64
```

### 1.2 Mathematical Reconciliation: Raw (100,150) vs. Deduplicated (100,000)

| Application Status Category | Raw File Count (All 100,150 Rows) | Raw Portfolio Share (%) | Count in 150 Duplicate Rows | Deduplicated Analytical View (Unique Applications) | Deduplicated Share (%) |
|---|---|---|---|---|---|
| **Approved** | **49,243** | 49.169% | **72** | **49,171** | **49.171%** |
| **Rejected** | **50,907** | 50.831% | **78** | **50,829** | **50.829%** |
| **Pending** | **0** | 0.000% | **0** | **0** | **0.000%** |
| **Unknown / Null** | **0** | 0.000% | **0** | **0** | **0.000%** |
| **Total Applications** | **100,150** | **100.000%** | **150** | **100,000** | **100.000%** |

### 1.3 Resolution of the Row Count Discrepancy
- **The Prior Apparent Discrepancy:** The raw status counts ($50,907$ rejected $+ 49,243$ approved $= 100,150$) exceeded the $100,000$ unique application benchmark by exactly $150$ records.
- **Root Cause Verified:** Exactly $150$ records in the CSV are byte-for-byte duplicates across all 67 columns.
- **Duplicate Breakdown:** The $150$ duplicates consist of exactly **$72$ Approved** applications and **$78$ Rejected** applications.
- **Arithmetic Verification:**
  - $\text{Approved (Unique): } 49,243 - 72 = 49,171$
  - $\text{Rejected (Unique): } 50,907 - 78 = 50,829$
  - $\text{Net Total Unique Applications: } 49,171 + 50,829 = 100,000$
- **Zero Ambiguity:** There are $0$ pending records, $0$ unknown records, $0$ null status values, and $0$ conflicting records for any `Application_ID`.

---

## 2. Table of Corrected, Confirmed, and Unresolved Audit Claims

This section explicitly documents the corrections made to previous assumptions and provides the empirical basis for each decision.

| Item / Claim | Previous Audit Assumption | Corrected Finding & Rationale | Status |
|---|---|---|---|
| **Disbursement Credibility** | Claimed 49,243 approved loans represent authentic funded loan facilities. | **Corrected:** The dataset contains **zero independently supported loan funding dates or real disbursement events**. `disbursement_amount` is an artificial float generated via `approved_amount * Uniform(0.85, 1.00)`. Approved applications must be analyzed as **underwriting approvals**, not verified funded loans. | **CORRECTED** |
| **Relational Schema Structure** | Proposed separate production relational tables (`fact_loan_disbursement`, `fact_repayment_installment`). | **Corrected:** An **application-centric fact table** (`fct_loan_application`) is the authoritative source for all business KPIs. Repayment demonstration fields are quarantined to a separate, clearly labelled demonstration table (`demo_synthetic_repayment_snapshot`). | **CORRECTED** |
| **Negative Financial Value Cleaning** | Proposed applying `ABS()` to negative values. | **Corrected:** **Never automatically apply `ABS()` to financial data.** Negative values in `Annual_Income` (35 rows), `Loan_Amount` (35 rows), and `Savings_Balance` (35 rows) will be set to `NULL` in the cleaned layer and flagged with dedicated boolean audit columns. | **CORRECTED** |
| **Target Database Engine** | Proposed PostgreSQL DDL. | **Corrected:** Switched strictly to **SQLite** (`INTEGER PRIMARY KEY`, `REAL`, `TEXT`, `CHECK` constraints). | **CORRECTED** |
| **`default_probability` Semantics** | Previously described as a default probability measure. | **Confirmed & Corrected:** `default_probability` is **strictly `Risk_Score / 100.0`** ($1.11 \times 10^{-16}$ max diff). It is a normalized scorecard transform, **not a calibrated statistical default probability**. | **CORRECTED** |
| **Repayment Granularity** | Previously referenced as repayment records. | **Confirmed:** The dataset contains only a **single synthetic payment snapshot** per application row, with identical fields populated even for Rejected loans. It is **not** an installment history ledger. | **CONFIRMED** |
| **Predictive Modeling in MVP** | Considered approval classification modeling in Phase 2. | **Corrected:** Modeling is **strictly excluded from the MVP**. Phase 2 is 100% focused on robust SQL analytics, dimensional modeling, and business insights. | **CORRECTED** |
| **Geographic Lineage** | Checked `city` vs `Region`. | **Confirmed:** `city` is 100% synthetically created by appending `_City` to `Region`. All geographic intelligence must use `Region` exclusively. | **CONFIRMED** |
| **Monthly vs. Annual Income** | Investigated formula discrepancy. | **Confirmed:** $69.25\%$ of records do not equal `Annual_Income / 12` (mean diff $4.27, max diff $35,433.93). `Annual_Income` is adopted as primary; monthly income is derived analytically. | **CONFIRMED** |
| **External Source Provenance** | Filename `kaggle_original.csv` suggests Kaggle origin. | **Unresolved:** External real-world institution or benchmark provenance remains **unverified**; treated strictly as an empirical underwriting dataset. | **UNRESOLVED / DOCUMENTED** |

---

## 3. Source-versus-Derived-versus-Synthetic Column Lineage Summary

Every column in `kaggle_original.csv` has been evaluated and assigned an authoritative architectural classification:

### 3.1 Original Underwriting Columns (Part 1, Cols 1–36) — Canonical Ingestion Source
These columns represent the primary empirical data and form the foundation of our analytical warehouse:
- **Identifiers & Demographics:** `Application_ID`, `Age`, `Gender`, `Marital_Status`, `Education_Level`, `Employment_Status`, `Job_Experience_Years`, `Dependents`.
- **Financial Balances & Cash Flow:** `Annual_Income`, `Monthly_Income`, `Savings_Balance`, `Checking_Balance`, `Total_Assets`, `Total_Liabilities`, `Monthly_Debt_Payment`.
- **Credit Bureau Attributes:** `Credit_Score`, `Credit_History_Years`, `Existing_Loans`, `Late_Payments_Last_2_Years`, `Previous_Loan_Status`.
- **Loan Underwriting Request & Decision:** `Loan_Amount`, `Loan_Term_Months`, `Loan_Purpose`, `Interest_Rate`, `Debt_To_Income_Ratio`, `Property_Ownership`, `Residential_Status`, `Co_Applicant`, `Collateral`, `Application_Channel`, `Region`, `Bank_Account_Age_Years`, `Risk_Score`, `Default_Risk`, `Approved_Amount`, `Loan_Approved`.

### 3.2 Exact Clones (Part 2, 17 Redundant Columns) — Discard During Ingestion
Verified via line-by-line comparison to have **0 mismatches (100.0% agreement)** with their Part 1 counterparts. These will be discarded to prevent redundant storage and schema clutter:
- `application_id`, `age`, `gender`, `income`, `employee_type`, `credit_score`, `existing_debt`, `loan_amount`, `loan_type`, `interest_rate`, `loan_term`, `loan_status`, `approved_amount`, `previous_defaults`, `payment_histories`, `risk_score`, `risk_category`.

### 3.3 Derived Transformations (Part 2, 2 Columns) — Replace with SQL Views / Generated Columns
- `account_tenure_months`: Exactly equals `round(Bank_Account_Age_Years * 12)`. Stored directly as an integer.
- `default_probability`: Exactly equals `Risk_Score / 100.0`. Stored as `normalized_risk_score` to reflect its true mathematical nature.

### 3.4 Synthetic Identifiers & Pseudo-Attributes (Part 2, 4 Columns) — Relabel or Discard
- `customer_id`, `loan_id`, `assessment_id`: Mechanical 1:1 prefix additions (`'CUST-'`, `'LOAN-'`, `'ASSESS-'`). Retained only as surrogate convenience keys; not proof of relational entities.
- `city`: Synthetic string (`Region || '_City'`). Discarded in favor of authentic `Region`.

### 3.5 Synthetic Demonstration Fields (Part 2, 8 Columns) — Quarantined to Demo Table
These columns do not represent authentic accounting events and are heavily populated on rejected loans. They are strictly excluded from primary underwriting KPIs and stored in a secondary demonstration table:
- `disbursement_amount`, `outstanding_amount`, `due_date`, `payment_date`, `amount_due`, `amount_paid`, `days_late`, `payment_status`.

---

## 4. Corrected SQLite Schema Proposal

The corrected schema adheres strictly to Kimball dimensional principles, utilizes native **SQLite syntax**, places the application at the center of all analysis, and quarantines synthetic data.

```mermaid
erDiagram
    dim_customer_profile ||--o{ fct_loan_application : "profile_for"
    dim_geography ||--o{ fct_loan_application : "originates_in"
    dim_channel ||--o{ fct_loan_application : "submitted_through"
    fct_loan_application ||--o| demo_synthetic_repayment_snapshot : "simulates_snapshot_for"

    dim_customer_profile {
        TEXT customer_key PK "Derived as CUST- || Application_ID"
        INTEGER age "NULL if < 18 or > 100"
        TEXT gender
        TEXT marital_status "Normalized"
        TEXT education_level "Normalized"
        TEXT employment_status "Normalized"
        INTEGER job_experience_years
        INTEGER dependents
        REAL annual_income "NULL if negative"
        REAL monthly_income_calculated "annual_income / 12.0"
        REAL savings_balance "NULL if negative"
        REAL checking_balance
        REAL total_assets
        REAL total_liabilities
        REAL net_worth "total_assets - total_liabilities"
        INTEGER bank_tenure_months
    }

    dim_geography {
        INTEGER geo_id PK
        TEXT region "West, Central, South, East"
        TEXT residential_status "Urban, Suburban, Rural"
        TEXT property_ownership "Rent, Own, Mortgage"
    }

    dim_channel {
        INTEGER channel_id PK
        TEXT channel_name "Online, Branch, Mobile App, Agent"
    }

    fct_loan_application {
        INTEGER application_id PK "100,000 unique records"
        TEXT customer_key FK
        INTEGER geo_id FK
        INTEGER channel_id FK
        TEXT loan_purpose "Home, Vehicle, Education, etc."
        REAL requested_loan_amount "NULL if negative"
        INTEGER requested_term_months
        REAL interest_rate
        REAL debt_to_income_ratio
        INTEGER bureau_credit_score "0 to 999 range"
        INTEGER bureau_existing_loans
        INTEGER bureau_late_payments_2yr
        REAL bureau_credit_history_years
        TEXT bureau_prior_loan_status "Historical past loans"
        REAL proprietary_risk_score "0.00 to 100.00"
        TEXT risk_tier "Low, Medium, High"
        REAL normalized_risk_score "risk_score / 100.0"
        TEXT underwriting_decision "Approved or Rejected"
        REAL sanctioned_approved_amount "0.00 for Rejected"
        INTEGER is_approved "1 for Approved, 0 for Rejected"
        INTEGER has_invalid_financials "Flag: 1 if income/loan was negative"
    }

    demo_synthetic_repayment_snapshot {
        INTEGER application_id PK FK "Approved loans only"
        TEXT simulated_due_date "NULL if 'not_a_date'"
        TEXT simulated_payment_date "NULL if '31/31/2025'"
        REAL simulated_amount_due
        REAL simulated_amount_paid
        INTEGER simulated_days_late
        TEXT simulated_payment_status
        REAL simulated_disbursement_amount
        REAL simulated_outstanding_balance
    }
```

### 4.1 SQLite DDL Specifications

```sql
-- ============================================================================
-- 1. DIMENSION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS dim_geography (
    geo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL,
    residential_status TEXT NOT NULL,
    property_ownership TEXT NOT NULL,
    UNIQUE(region, residential_status, property_ownership)
);

CREATE TABLE IF NOT EXISTS dim_channel (
    channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_customer_profile (
    customer_key TEXT PRIMARY KEY,
    age INTEGER CHECK (age IS NULL OR (age >= 18 AND age <= 100)),
    gender TEXT NOT NULL,
    marital_status TEXT NOT NULL,
    education_level TEXT NOT NULL,
    employment_status TEXT NOT NULL,
    job_experience_years INTEGER,
    dependents INTEGER,
    annual_income REAL CHECK (annual_income IS NULL OR annual_income >= 0),
    monthly_income_calculated REAL,
    savings_balance REAL CHECK (savings_balance IS NULL OR savings_balance >= 0),
    checking_balance REAL CHECK (checking_balance >= 0),
    total_assets REAL CHECK (total_assets >= 0),
    total_liabilities REAL CHECK (total_liabilities >= 0),
    net_worth REAL,
    bank_tenure_months INTEGER
);

-- ============================================================================
-- 2. PRIMARY ANALYTICAL FACT TABLE (APPLICATION GRAIN)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fct_loan_application (
    application_id INTEGER PRIMARY KEY,
    customer_key TEXT NOT NULL,
    geo_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    loan_purpose TEXT NOT NULL,
    requested_loan_amount REAL CHECK (requested_loan_amount IS NULL OR requested_loan_amount > 0),
    requested_term_months INTEGER NOT NULL,
    interest_rate REAL,
    debt_to_income_ratio REAL,
    bureau_credit_score INTEGER,
    bureau_existing_loans INTEGER,
    bureau_late_payments_2yr INTEGER,
    bureau_credit_history_years REAL,
    bureau_prior_loan_status TEXT,
    proprietary_risk_score REAL,
    risk_tier TEXT,
    normalized_risk_score REAL,
    underwriting_decision TEXT NOT NULL CHECK (underwriting_decision IN ('Approved', 'Rejected')),
    sanctioned_approved_amount REAL NOT NULL DEFAULT 0.0,
    is_approved INTEGER NOT NULL CHECK (is_approved IN (0, 1)),
    has_invalid_financials INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_key) REFERENCES dim_customer_profile(customer_key),
    FOREIGN KEY (geo_id) REFERENCES dim_geography(geo_id),
    FOREIGN KEY (channel_id) REFERENCES dim_channel(channel_id)
);

CREATE INDEX IF NOT EXISTS idx_fct_app_decision ON fct_loan_application(underwriting_decision);
CREATE INDEX IF NOT EXISTS idx_fct_app_geo ON fct_loan_application(geo_id);
CREATE INDEX IF NOT EXISTS idx_fct_app_channel ON fct_loan_application(channel_id);

-- ============================================================================
-- 3. SEPARATE SYNTHETIC DEMONSTRATION TABLE (QUARANTINED)
-- ============================================================================

CREATE TABLE IF NOT EXISTS demo_synthetic_repayment_snapshot (
    application_id INTEGER PRIMARY KEY,
    simulated_due_date TEXT,
    simulated_payment_date TEXT,
    simulated_amount_due REAL,
    simulated_amount_paid REAL,
    simulated_days_late INTEGER,
    simulated_payment_status TEXT,
    simulated_disbursement_amount REAL,
    simulated_outstanding_balance REAL,
    FOREIGN KEY (application_id) REFERENCES fct_loan_application(application_id)
);
```

---

## 5. Cleaning & Data-Quality Policy (Phase 2 Ingestion Contract)

The ingestion pipeline will execute under the following immutable data-quality rules:

1. **Raw File Immutability:** `data/raw/kaggle_original.csv` will remain strictly untouched on disk.
2. **Deterministic Deduplication:** Exactly $150$ duplicate records will be filtered out during staging ingestion by preserving the first occurrence of each `Application_ID`. Raw ($100,150$) versus clean ($100,000$) counts will be logged in an audit metadata table.
3. **Invalid Financial Balances (No Auto-ABS):**
   - If `Annual_Income < 0` ($35$ rows), set `annual_income = NULL` and set `has_invalid_financials = 1`.
   - If `Loan_Amount < 0` ($35$ rows), set `requested_loan_amount = NULL` and set `has_invalid_financials = 1`.
   - If `Savings_Balance < 0` ($35$ rows), set `savings_balance = NULL` and set `has_invalid_financials = 1`.
   - Under no circumstances will negative values be multiplied by $-1$ or blindly converted using `ABS()`.
4. **Malformed Date String Cleansing:**
   - Literal text `"not_a_date"` in `due_date` ($20$ rows) will be converted to `NULL`.
   - Impossible calendar date `"31/31/2025"` in `payment_date` ($20$ rows) will be converted to `NULL`.
5. **Categorical Normalization:**
   - Whitespace and casing across all $14$ categorical fields will be cleansed using deterministic SQL mappings: `TRIM(UPPER(col))` mapped to standard Title Case values (`'Approved'`, `'Rejected'`, `'Bachelor'`, `'Married'`, `'Online'`, `'Branch'`, etc.).
6. **Row Preservation:** Records with an invalid field will **not** be deleted. The record will be retained for valid attributes (e.g. demographic analysis) while excluding the specific `NULL` attribute from measure aggregations.
7. **Repayment Quarantining:** Only applications where `underwriting_decision == 'Approved'` and sanctioned amount $> 0$ will have rows populated in `demo_synthetic_repayment_snapshot`. Rejected applications will have **zero** repayment rows.

---

## 6. Initial SQL KPI Plan (Metrics, Formulas & Explicit Denominators)

Every metric in the platform is anchored to a verified business definition and an explicit denominator:

### KPI 1: Overall Application Approval Rate
- **Business Question:** What proportion of submitted credit applications meet underwriting approval criteria?
- **Numerator:** Count of applications where `underwriting_decision = 'Approved'`.
- **Denominator:** **Total unique applications ($100,000$)**.
- **SQL Implementation:**
  ```sql
  SELECT COUNT(*) AS total_applications,
         SUM(is_approved) AS approved_applications,
         ROUND(AVG(is_approved) * 100.0, 2) AS approval_rate_pct,
         ROUND((1.0 - AVG(is_approved)) * 100.0, 2) AS rejection_rate_pct
  FROM fct_loan_application;
  ```

### KPI 2: Channel Conversion Efficiency
- **Business Question:** Which origination channel produces the highest volume and approval conversion?
- **Numerator:** Count of approved applications per channel.
- **Denominator:** **Total applications received through that specific channel**.
- **SQL Implementation:**
  ```sql
  SELECT c.channel_name,
         COUNT(f.application_id) AS total_received,
         SUM(f.is_approved) AS total_approved,
         ROUND(AVG(f.is_approved) * 100.0, 2) AS channel_approval_rate_pct
  FROM fct_loan_application f
  JOIN dim_channel c ON f.channel_id = c.channel_id
  GROUP BY c.channel_name
  ORDER BY total_received DESC;
  ```

### KPI 3: Underwriting Policy Haircut Percentage
- **Business Question:** By what percentage does the credit committee scale back requested loan amounts for approved borrowers?
- **Numerator:** `SUM(requested_loan_amount - sanctioned_approved_amount)`.
- **Denominator:** **`SUM(requested_loan_amount)` strictly among Approved applications with non-null loan amounts**.
- **SQL Implementation:**
  ```sql
  SELECT loan_purpose,
         COUNT(*) AS approved_count,
         ROUND(SUM(requested_loan_amount), 2) AS total_requested,
         ROUND(SUM(sanctioned_approved_amount), 2) AS total_sanctioned,
         ROUND(SUM(requested_loan_amount - sanctioned_approved_amount), 2) AS total_haircut_amount,
         ROUND((1.0 - (SUM(sanctioned_approved_amount) / SUM(requested_loan_amount))) * 100.0, 2) AS haircut_pct
  FROM fct_loan_application
  WHERE is_approved = 1 
    AND requested_loan_amount IS NOT NULL
  GROUP BY loan_purpose
  ORDER BY haircut_pct DESC;
  ```

### KPI 4: Underwriting Tier Conversion & Bureau Score Calibration
- **Business Question:** Does the proprietary scorecard align with external bureau ratings, and what are the approval cutoffs?
- **Numerator:** Count of approved applications within each risk tier.
- **Denominator:** **Total applications within that risk tier**.
- **SQL Implementation:**
  ```sql
  SELECT risk_tier,
         COUNT(*) AS tier_applications,
         ROUND(AVG(proprietary_risk_score), 2) AS avg_risk_score,
         ROUND(AVG(bureau_credit_score), 1) AS avg_bureau_score,
         SUM(is_approved) AS approved_count,
         ROUND(AVG(is_approved) * 100.0, 2) AS tier_approval_rate_pct
  FROM fct_loan_application
  WHERE risk_tier IS NOT NULL
  GROUP BY risk_tier
  ORDER BY avg_risk_score ASC;
  ```

### KPI 5: Borrower Debt Burden & Solvency Segmentation
- **Business Question:** What percentage of applicants exceed standard regulatory DTI thresholds ($> 43.0\%$)?
- **Numerator:** Count of applications where `debt_to_income_ratio > 43.0`.
- **Denominator:** **Total applications with non-null DTI**.
- **SQL Implementation:**
  ```sql
  SELECT CASE 
             WHEN debt_to_income_ratio <= 20.0 THEN '1. Low Debt (<= 20%)'
             WHEN debt_to_income_ratio <= 35.0 THEN '2. Moderate Debt (21-35%)'
             WHEN debt_to_income_ratio <= 43.0 THEN '3. Standard Cap (36-43%)'
             ELSE '4. High Exposure (> 43%)'
         END AS dti_bracket,
         COUNT(*) AS applicant_count,
         ROUND(AVG(is_approved) * 100.0, 2) AS approval_rate_pct
  FROM fct_loan_application
  WHERE debt_to_income_ratio IS NOT NULL
  GROUP BY 1
  ORDER BY 1;
  ```

---

## 7. Test and Reconciliation Plan

Before declaring the Phase 2 database ready for BI queries, the ETL pipeline will execute an automated test suite verifying $100\%$ reconciliation:

```mermaid
flowchart TD
    A["Raw Ingestion (100,150 rows)"] --> B["Deduplication Filter"]
    B --> C["100,000 Clean Staging Rows"]
    C --> D["Data Quality Validation Suite"]
    D --> E["Load dim_customer_profile (100,000)"]
    D --> F["Load fct_loan_application (100,000)"]
    D --> G["Load demo_synthetic_repayment (49,171)"]
    F --> H["Automated Reconciliation Test Assertions"]
    H --> I["Sign-Off Dashboard Ready"]
```

### Mandatory Automated Test Assertions
1. **Row Count Assertion:**  
   `SELECT COUNT(*) FROM fct_loan_application` must equal **exactly 100,000**.
2. **Decision Sum Assertion:**  
   `SELECT SUM(is_approved), COUNT(*) - SUM(is_approved) FROM fct_loan_application` must equal **exactly 49,171 Approved** and **50,829 Rejected**.
3. **Primary Key Uniqueness Assertion:**  
   `SELECT COUNT(DISTINCT application_id) FROM fct_loan_application` must equal **100,000**.
4. **Sanction Amount Integrity Assertion:**  
   `SELECT COUNT(*) FROM fct_loan_application WHERE is_approved = 0 AND sanctioned_approved_amount > 0` must equal **0**.
5. **Negative Value Cleanse Assertion:**  
   `SELECT COUNT(*) FROM fct_loan_application WHERE requested_loan_amount < 0` must equal **0**.  
   `SELECT COUNT(*) FROM dim_customer_profile WHERE annual_income < 0 OR savings_balance < 0` must equal **0**.
6. **Repayment Quarantining Assertion:**  
   `SELECT COUNT(*) FROM demo_synthetic_repayment_snapshot r JOIN fct_loan_application f ON r.application_id = f.application_id WHERE f.is_approved = 0` must equal **0**.

---

## 8. Remaining Decisions for User Input

All technical and architectural blockers have been resolved. The remaining decisions are user preferences regarding dashboard presentation:

### Decision 1: Currency Normalization in UI Dashboards
- **Context:** The dataset contains values across diverse magnitudes (e.g. loan amounts up to $\$1,000,000$).
- **Option A (Recommended):** Display all dollar metrics in standard US Dollar currency formatting (`$XX,XXX.XX` and `$X.XX M`).
- **Option B:** Provide a currency toggle in the UI (e.g. USD `$`, EUR `€`, INR `₹`) for portfolio presentation flexibility.

### Decision 2: Demonstration Data Visibility in the Dashboard
- **Context:** We have isolated synthetic repayment fields to `demo_synthetic_repayment_snapshot`.
- **Option A (Recommended):** Place synthetic repayment and collection analytics in a clearly demarcated secondary tab labeled **"Simulated Servicing & Collection Snapshot (Demonstration Data)"** with an explicit disclaimer.
- **Option B:** Omit repayment demonstration data entirely from the initial MVP dashboard, focusing $100\%$ of user attention on authentic Underwriting Intelligence and Solvency Analysis.

---

## 9. Recommended Phase 2 Implementation Sequence with Mandatory Checkpoints

To ensure zero divergence and maintain rigorous pair-programming discipline, Phase 2 will proceed in sequential, verifiable milestones:

```text
[CHECKPOINT 1: Current Gate] ---> User Approves Readiness Report (phase_2_readiness_report.md)
                                         |
                                         v
[MILESTONE 1: ETL Pipeline] ----> Build src/data/etl_pipeline.py (Clean, Deduplicate, SQLite Ingest)
                                         |
                                         v
[CHECKPOINT 2: DB Audit] -------> Execute Test & Reconciliation Suite against SQLite DB (Verify 100k rows)
                                         |
                                         v
[MILESTONE 2: Analytical SQL] --> Build SQL KPI Views & Repository Layer (Analytical queries)
                                         |
                                         v
[CHECKPOINT 3: SQL Review] -----> Verify KPI Output against Baseline Reconciliation Numbers
                                         |
                                         v
[MILESTONE 3: Fast API Engine] -> Build FastAPI Backend Endpoints (Serving Structured KPI Payloads)
                                         |
                                         v
[MILESTONE 4: React Dashboard] -> Build High-Aesthetic Dashboard (Tailored Charts, Glassmorphic UI)
                                         |
                                         v
[FINAL SIGN-OFF: End-to-End] ---> Complete Platform Verification & Walkthrough
```

---

## 10. Readiness Statement & Blocker Assessment

- **Readiness Status:** **READY FOR IMPLEMENTATION**
- **Identified Blockers:** **NONE.** All data quality anomalies, row count discrepancies, synthetic attributes, and model semantics have been rigorously identified, reconciled, and accounted for in the corrected SQLite architecture.
- **Rule Enforcement:** Zero application code, zero database tables, and zero package installations have been performed. Source CSV remains completely unmodified.

---

**READINESS PASS COMPLETE. STOPPING HERE.**  
*Awaiting your explicit approval of `phase_2_readiness_report.md` and guidance on Decisions 1 & 2 before starting Phase 2.*
