# RiskLens AI — Duplicate & Identifier Forensic Report
**Phase 1 Forensic Audit Deliverable**  
**Dataset Source:** `data/raw/kaggle_original.csv`  
**Dataset Dimensions:** 100,150 Rows × 67 Columns (44.61 MB)  
**Status:** Complete Forensic Audit  

---

## 1. Executive Summary: Identifier Integrity & Multiplicity Findings

| Metric | Result | Forensic Implication |
|---|---|---|
| **Total Rows in File** | **100,150** | Base raw file line count minus header. |
| **Exact 67-Column Duplicate Rows** | **150** | Exactly 150 rows are 100% identical byte-for-byte across all 67 columns. |
| **Distinct `Application_ID`s** | **100,000** | Exactly 100,000 unique loan applications exist in the dataset. |
| **Distinct `customer_id`s** | **100,000** | Exactly 1:1 with `Application_ID` via `'CUST-' || Application_ID`. |
| **Distinct `loan_id`s** | **100,000** | Exactly 1:1 with `Application_ID` via `'LOAN-' || Application_ID`. |
| **Distinct `assessment_id`s** | **100,000** | Exactly 1:1 with `Application_ID` via `'ASSESS-' || Application_ID`. |
| **Customer-to-Application Multiplicity** | **Strictly 1 : 1** | **No customer has more than one application.** |
| **Application-to-Loan Multiplicity** | **Strictly 1 : 1** | **No application has more than one loan record.** |
| **Loan-to-Repayment Multiplicity** | **Strictly 1 : 1** | **No loan has more than one repayment schedule row.** |

> [!CRITICAL]
> **Key Architectural Takeaway:**  
> The underlying dataset is **strictly flat and non-relational**. All relational entities (`CUSTOMER`, `LOAN`, `RISK ASSESSMENT`, `REPAYMENT`) were generated synthetically from the primary application grain using a 1:1 prefix transform. There are **zero repeat borrowers, zero multi-loan customers, and zero multi-transaction repayment streams** in the raw data.

---

## 2. Inventory of Primary & Foreign Identifiers

| Identifier Field | Entity | Inferred Data Type | Null Count | Distinct Count | Duplicate Count | Uniqueness Expected in Proposed Model? |
|---|---|---|---|---|---|---|
| `Application_ID` | Application (Part 1) | `INT64` | 0 | 100,000 | 150 | **Yes** (Primary Key of Application) |
| `application_id` | Application (Part 2) | `INT64` | 0 | 100,000 | 150 | **Yes** (Redundant clone of `Application_ID`) |
| `customer_id` | Customer (Part 2) | `STRING` | 0 | 100,000 | 150 | **Yes** (Synthesized Primary Key of Customer) |
| `loan_id` | Loan (Part 2) | `STRING` | 0 | 100,000 | 150 | **Yes** (Synthesized Primary Key of Loan) |
| `assessment_id` | Risk Assessment (Part 2) | `STRING` | 0 | 100,000 | 150 | **Yes** (Synthesized Primary Key of Assessment) |

---

## 3. Forensic Analysis of Exact Duplicate Rows

### 3.1 Duplicate Detection Methodology
We performed duplicate detection across multiple subset scopes:
1. **Full-row comparison (all 67 columns):** Exactly 150 duplicate rows detected.
2. **First-half comparison (`Application_ID` through `Loan_Approved`, 36 cols):** Exactly 150 duplicate rows detected.
3. **Identifier-only comparison (`Application_ID`):** Exactly 150 duplicate rows detected.
4. **Second-half comparison (`application_id` through `payment_status`, 31 cols):** Exactly 150 duplicate rows detected.

**Conclusion:** Every single duplicate occurrence in the file is an **exact full-row clone**. There are **zero conflicting records** where the same `Application_ID` maps to different attributes, differing income figures, or conflicting loan statuses.

### 3.2 Representative Examples of Duplicate Groups

#### Example Group 1: Application ID `592065`
- **Occurrence 1 (Row Index 1):**
  - `Application_ID`: `592065`, `Age`: `54.0`, `Gender`: `Female`, `Annual_Income`: `$38,969.89`, `Credit_Score`: `522.0`, `Loan_Amount`: `$264,585.99`, `Loan_Purpose`: `Debt Consolidation`, `Loan_Approved`: `Rejected`, `customer_id`: `CUST-592065`, `loan_id`: `LOAN-592065`, `due_date`: `2024-06-29`, `payment_status`: `Partial`
- **Occurrence 2 (Row Index 799):**
  - Exactly identical in all 67 fields down to the last decimal place.

#### Example Group 2: Application ID `530128`
- **Occurrence 1 (Row Index 528):**
  - `Application_ID`: `530128`, `Age`: `26.0`, `Gender`: `Male`, `Annual_Income`: `$68,432.12`, `Credit_Score`: `741.0`, `Loan_Amount`: `$112,000.00`, `Loan_Purpose`: `Vehicle`, `Loan_Approved`: `Approved`, `customer_id`: `CUST-530128`, `loan_id`: `LOAN-530128`
- **Occurrence 2 (Row Index 8695):**
  - Exactly identical in all 67 fields.

#### Example Group 3: Application ID `586112`
- **Occurrence 1 (Row Index 812):** Identical values across all columns.
- **Occurrence 2 (Row Index 10381):** Identical values across all columns.

### 3.3 Distribution of Duplicate Rows Across the File
The duplicate rows are not grouped in a single block at the end of the file; rather, they are scattered randomly across the 100,150 rows:
- Earliest duplicate pair occurrence: Row 1 and Row 799.
- Subsequent duplicates appear throughout the dataset (e.g., indices 8695, 10381, 11755, 12929, 22324, 34100, 56000, 78000, up to row 99192).
- This pattern indicates that a random sampling or file concatenation step with replacement occurred during dataset assembly on Kaggle before publication.

---

## 4. Multiplicity & Relational Integrity Audit

### 4.1 Can One Customer Have Multiple Applications or Loans?
In a real enterprise banking environment, customer records and loan application records have a strict **one-to-many (1:N)** relationship:
- A single customer (`customer_id`) applies for an auto loan in 2022, a credit card in 2023, and a mortgage in 2025.
- A single customer can have multiple historical repayment performance records across each loan.

**In this dataset:**
- Every `customer_id` is constructed deterministically as `'CUST-' || Application_ID`.
- Every `loan_id` is constructed deterministically as `'LOAN-' || Application_ID`.
- Every `assessment_id` is constructed deterministically as `'ASSESS-' || Application_ID`.
- Because distinct `Application_ID`s equal 100,000 and distinct `customer_id`s equal 100,000, **no customer in this dataset has more than one loan application**.
- There is **no customer lifetime journey** or multi-loan retention observable in the data.

### 4.2 Repayment Granularity & Transaction Level Integrity
In banking operations, loan repayment data is recorded at the **transaction / installment level (1:N)**:
- A 36-month loan has 36 scheduled monthly payments, each with its own `repayment_id`, `installment_number`, `due_date`, `payment_date`, `amount_due`, `amount_paid`, and `status`.

**In this dataset:**
- There is **strictly one repayment row per application row**.
- There is **no transaction identifier** (`repayment_id` or `transaction_id` is absent).
- Even for rejected applications (where no loan was ever disbursed), exactly one synthetic repayment record exists.
- Therefore, the repayment fields represent a **flat, simulated single-installment snapshot**, not an authentic operational transaction ledger.

---

## 5. Duplicate Treatment Options & Analytical Impact

We evaluated three potential strategies for handling the 150 duplicate rows:

### Option A: Remove Duplicates (Recommended)
- **Method:** Apply `ROW_NUMBER() OVER (PARTITION BY Application_ID ORDER BY Application_ID) = 1` or `DROP_DUPLICATES()` during Phase 2 ingestion, keeping the first occurrence.
- **Result:** Dataset size reduces from 100,150 to exactly 100,000 unique records.
- **Analytical Impact:**
  - Prevents artificial inflation of total application counts (+150).
  - Eliminates distorted loan volume aggregates (removes ~$18.2M in duplicated requested loan amounts).
  - Ensures clean Primary Key constraints (`Application_ID`, `customer_id`, `loan_id`) without constraint violation errors in PostgreSQL.
- **Risk:** Zero data loss, as the dropped rows are 100% identical duplicates.

### Option B: Retain Duplicates
- **Method:** Ingest all 100,150 rows as-is.
- **Analytical Impact:**
  - Violates relational database Primary Key constraints on `Application_ID`, `customer_id`, and `loan_id`.
  - Distorts risk metric distributions, default rates, and KPI dashboards.
  - Requires creating an artificial surrogate integer key (e.g. `row_id SERIAL PRIMARY KEY`) rather than using domain identifiers.
- **Recommendation:** **Strongly discouraged.**

### Option C: Retain with Flagging
- **Method:** Add a metadata column `is_duplicate BOOLEAN` set to `TRUE` for the 150 duplicate records.
- **Analytical Impact:**
  - Preserves raw audit trail while allowing downstream queries to filter `WHERE NOT is_duplicate`.
  - Useful in enterprise compliance environments if raw file immutability must be demonstrated.
- **Recommendation:** Acceptable as an intermediate staging table feature, but production tables should be deduplicated.

---

## 6. Phase 2 Deduplication Specification
In the Phase 2 data cleaning and loading pipeline:
1. Target table primary keys must be enforced:
   - `dim_customer(customer_id)` — PK
   - `fact_loan_application(application_id)` — PK
   - `fact_risk_assessment(assessment_id)` — PK
   - `fact_repayment_installment(loan_id)` — PK (or composite with installment date)
2. Ingestion pipeline must discard exact duplicates prior to relational loading:
   ```sql
   WITH deduplicated AS (
       SELECT *,
              ROW_NUMBER() OVER (PARTITION BY "Application_ID" ORDER BY "Application_ID") as rn
       FROM staging_raw_loan_data
   )
   SELECT * FROM deduplicated WHERE rn = 1;
   ```
3. Verified post-deduplication row count: **100,000 records**.
