# RiskLens AI — Phase 1 Forensic CSV Audit Summary
**Project:** RiskLens AI — Financial Risk Intelligence & Business Analytics Platform  
**Target File:** `data/raw/kaggle_original.csv`  
**Audit Status:** Complete & Verified (Forensic Analysis Only — Zero Application Code Generated)  
**Deliverable Output Directory:** `phase-1-audit/`  

---

## 1. Executive Summary & Verification of Source Dataset

Our forensic audit of `kaggle_original.csv` is complete. The dataset has been located, verified, and profiled using high-efficiency Python audit utilities without modifying or overwriting the original file.

### Dataset Dimensions & Physical Profile
- **File Location:** `data/raw/kaggle_original.csv`
- **File Size:** **46,779,106 bytes (44.61 MB)**
- **Character Encoding:** US-ASCII / UTF-8 compatible
- **Delimiter:** Standard comma (`,`)
- **Total Line Count:** 100,151 lines (1 header line + **100,150 data rows**)
- **Total Columns:** **67 columns**
- **Row Parsing Integrity:** Exactly 67 fields per line across all 100,150 rows (**0 corrupted lines, 0 truncated rows, 0 silently skipped records**).

---

## 2. Major Forensic Findings: Provenance & Dataset Anatomy

### Finding 1: The "Two-Part Glued Dataset" Discovery
The CSV contains two distinct halves glued together horizontally:
1. **Part 1 (Columns 1–36, PascalCase / Title_Case):** Represents an authentic, highly detailed loan origination and applicant credit dataset from Kaggle (`Application_ID`, `Age`, `Gender`, `Marital_Status`, `Annual_Income`, `Credit_Score`, `Total_Assets`, `Total_Liabilities`, `Loan_Approved`, etc.).
2. **Part 2 (Columns 37–67, snake_case):** Represents an artificial relational schema added to match target application entities (`application_id`, `customer_id`, `loan_id`, `city`, `disbursement_amount`, `due_date`, `payment_date`, `amount_due`, `payment_status`).
   - 17 columns in Part 2 are **100% redundant exact clones** of Part 1 columns.
   - `customer_id`, `loan_id`, and `assessment_id` are simply `'CUST-'`, `'LOAN-'`, and `'ASSESS-'` prepended to `Application_ID`.
   - `city` was 100% generated as `Region || '_City'` (e.g. `West` -> `West_City`).
   - `account_tenure_months` was 100% generated as `round(Bank_Account_Age_Years * 12)`.
   - `default_probability` was 100% generated as `Risk_Score / 100.0`.

### Finding 2: Exact Duplicate Records (150 Rows)
- Exactly **150 rows** are 100% identical byte-for-byte across all 67 columns.
- Distinct `Application_ID` count is **exactly 100,000**.
- Distinct `customer_id`, `loan_id`, and `assessment_id` counts are also **exactly 100,000**.
- There are **zero conflicting records** for any identifier. Every duplicate is an exact row clone.
- Post-deduplication analytical population: **100,000 unique records**.

### Finding 3: Strictly Flat 1:1 Cardinality (Zero Relational Multiplicity)
- **Zero repeat customers:** Exactly one loan application per customer.
- **Zero multi-installment repayment streams:** Exactly one payment snapshot per loan.
- The dataset is an application-grain flat ledger, not a transactional relational database.

### Finding 4: Fatal Business Contradiction — Repayments on Rejected Loans
- Exactly **50,907 loan applications were REJECTED** (`Loan_Approved == 'Rejected'`, `Approved_Amount == 0`, `disbursement_amount == 0`).
- Yet, **all 50,907 rejected loans have synthetic repayment records attached to them**:
  - 50,153 rejected applications have an `amount_due` (calculated as `Loan_Amount / Loan_Term_Months`).
  - 49,464 rejected applications have an `amount_paid > 0`!
  - 7,295 rejected applications are marked `payment_status == 'Paid'`!
  - 43,610 rejected applications are marked `payment_status == 'Partial'`!
- **Impact:** An applicant rejected for a loan was never issued money; having an active billing schedule and collections is financially impossible. Repayment data must be isolated strictly to approved and disbursed loans.

### Finding 5: Absence of a True Current Loan Default Flag
- No column records an actual post-origination loan charge-off or default event for the current loan.
- `Previous_Loan_Status == 'Defaulted'` indicates that the applicant defaulted on an *earlier* loan from another lender years ago, not the current loan.
- `payment_status == 'Missed'` contains only **2 records out of 100,150**.
- **Conclusion:** Standard "Default Prediction" cannot be legitimately trained on this dataset.

### Finding 6: Synthetic Data Traps Injected into the Data
- **Impossible Calendar Dates:** 20 rows in `payment_date` contain the literal string `"31/31/2025"`.
- **Malformed Date String:** 20 rows in `due_date` contain the literal string `"not_a_date"`.
- **Negative Financial Metrics:** Exactly 35 records have negative `Annual_Income` (min -$211,679.11), 35 have negative `Loan_Amount` (min -$375,200.41), and 35 have negative `Savings_Balance` (min -$62,004.75).
- **Impossible Demographics:** Exactly 13 records have `Age < 18` (e.g. 5-year-old child with 24 years job experience and 21.5 years credit history), and 12 records have `Age > 100`.
- **Categorical Noise:** Whitespace and casing inconsistencies injected across 14 categorical columns (e.g. `" Bachelor"`, `"BACHELOR"`, `"bachelor"`, `" Married"`, `"MARRIED"`).

---

## 3. Complete Phase 1 Deliverables Inventory

All 10 deliverables mandated by the project instructions have been generated and saved to the `phase-1-audit/` folder:

| # | Deliverable File | Type | Description |
|---|---|---|---|
| 1 | `audit_summary.md` | Markdown | Executive summary, dimensions, major findings, risks, and next steps. |
| 2 | `column_profile.csv` | CSV | 67 rows (one per column) with data types, nulls, distinct counts, descriptive statistics, and quality notes. |
| 3 | `data_dictionary.md` | Markdown | Proposed business definitions, domain ranges, limitations, and canonical sources for all 67 columns. |
| 4 | `data_quality_issues.csv` | CSV | 17 structured issues with Issue ID, severity, affected counts, examples, and recommended actions. |
| 5 | `schema_mapping.csv` | CSV | 35 fields mapped to project target entities (`CUSTOMER`, `LOAN`, `CREDIT`, `REPAYMENT`, `RISK ASSESSMENT`). |
| 6 | `duplicate_and_identifier_report.md` | Markdown | Forensic audit of duplicate rows, identifier relationships, and deduplication strategy. |
| 7 | `business_rules_report.md` | Markdown | 15 financial, temporal, and mathematical business rules audited with exact statistics. |
| 8 | `business_questions.md` | Markdown | Supported high-value analytical questions, KPI definitions, SQL queries, and prohibited questions. |
| 9 | `proposed_sql_model.md` | Markdown | Kimball star schema architecture, table grains, DDL specifications, and Mermaid diagram. |
| 10 | `phase_1_recommendation.md` | Markdown | MVP scope boundaries, engineering assumptions, and user decision gate questions. |

---

## 4. Key Risks & Recommended Next Steps

1. **Risk of Double-Counting:** Deduplication must be executed as Step 1 of Phase 2 ETL to drop the 150 exact row clones.
2. **Risk of Portfolio Contamination:** The 50,907 rejected loan repayment records must be nullified or segregated into an approved-only repayment table.
3. **Risk of Machine Learning Misrepresentation:** Do not attempt to train a default prediction model; reframe modeling around Underwriting Decision Classification or Risk Tier Segmentation.
4. **Next Phase (Phase 2):** Await user approval on decision points, then proceed to build the clean ETL pipeline, PostgreSQL database schema, FastAPI analytics backend, and interactive React intelligence dashboard.
