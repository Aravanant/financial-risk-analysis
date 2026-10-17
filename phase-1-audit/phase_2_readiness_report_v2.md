# RiskLens AI — Final Phase 2 Readiness Report (v2)

**Project:** RiskLens AI — Financial Risk Intelligence & Business Analytics Platform  
**Target Raw File:** `data/raw/kaggle_original.csv` (Verified Read-Only / Untouched: 46,779,106 bytes)  
**Database Engine Target:** **SQLite**  
**Canonical File Path:** `phase-1-audit/phase_2_readiness_report_v2.md`  
**Status:** Pre-ETL Blocker Resolution & Final Architecture Gate Complete — **Awaiting Explicit User Approval Before Milestone 1 Implementation**

---

## 1. Executive Summary & Master Blocker Resolution Ledger

This document serves as the authoritative architectural readiness specification and audit ledger for Phase 2 implementation of RiskLens AI. Every column mapping, cleaning policy, constraint definition, and KPI formulation has been reconciled against the physical raw CSV (`data/raw/kaggle_original.csv`) using executed Python profiling scripts.

### Master Ledger of Resolved Gate Items

| # | Gate Item | Previous Version Limitation | Final Resolved Specification | Empirical Evidence & Profiling Basis |
|---|---|---|---|---|
| **1** | **Preserve Sanctioned-Amount Missingness** | Declared `sanctioned_approved_amount NOT NULL DEFAULT 0.0`, silently replacing 575 missing values with 0.0. | **Resolved:** Schema allows `sanctioned_approved_amount REAL CHECK (sanctioned_approved_amount IS NULL OR sanctioned_approved_amount >= 0.0)` without default. Added `has_missing_sanctioned_amount` flag. For Rejected loans, genuine zero ($50,198$) is preserved; source nulls ($631$) remain `NULL`. For Approved loans, positive amounts ($48,596$) are preserved; source nulls ($575$) remain `NULL`. | Profiling confirmed: Approved has $48,596$ positive, $0$ zero, $575$ null. Rejected has $50,198$ zero, $0$ positive, $631$ null. |
| **2** | **Credit-Score Casting Justification** | Proposed casting `Credit_Score` to `INTEGER` without verifying whether fractional values exist. | **Resolved:** Executed profiling confirmed **exactly 0 fractional values** among all 98,680 non-null records. Casting to `INTEGER` preserves values losslessly. Valid range: $[0, 999]$. | 100% of non-null credit scores satisfy `val % 1 == 0`. 1,320 source nulls preserved as `NULL`. |
| **3** | **Strict Boolean Parsing** | Used `CASE WHEN TRIM(UPPER(col)) = 'YES' THEN 1 ELSE 0 END`, which silently converts nulls and unexpected strings to `0` (No). | **Resolved:** Replaced `ELSE 0` with explicit mapping: `'YES' -> 1`, `'NO' -> 0`, `NULL -> NULL`. Unrecognized values raise an immediate `ValueError` and roll back transaction prior to insertion. | Source contains only 8 case/whitespace variants of 'Yes' and 'No'; 0 nulls, 0 corrupted strings. |
| **4** | **Requested-Amount Zero Reconciliation** | Stated haircut population totals without providing empirical counts of zero requested amounts or executable assertions. | **Resolved:** Profiled `Loan_Amount`: **0 zero values** exist across all 100,000 records. Breakdown: Approved has $569$ null, $15$ negative, $0$ zero, $48,587$ positive. Rejected has $692$ null, $20$ negative, $0$ zero, $50,117$ positive. Reconciled 48,022 haircut population with passing executable assertion. | Executable assertion verified: $49,171 - 1,149 \text{ exclusions} = 48,022$ eligible approved applications. |
| **5** | **Evidence vs. Interpretation (`Default_Risk`)** | Asserted an undocumented credit committee process or multi-factor derivation as established fact. | **Resolved:** Documented `Default_Risk` strictly as a **source-provided categorical field** (`'Low'`, `'Medium'`, `'High'`, 0 nulls). Labeled multi-factor policy boundaries as an inferred hypothesis, not verified fact. Direct mapping rule confirmed; naive score cuts yield **3,252 mismatches**. | Overlaps verified: 958 records in $[34.0, 35.0]$; 3,413 records in $[65.0, 67.0]$. 1,216 records have missing scores but assigned tiers. |
| **6** | **Normalized Score Consistency** | Missing formal specification and null preservation rule for `normalized_risk_score`. | **Resolved:** Formally specified `normalized_risk_score = proprietary_risk_score / 100.0`. Validated across all 98,784 non-null scores: bounded in $[0.0, 1.0]$. When source score is `NULL`, normalized score is strictly `NULL`. | Executable assertion verified: 1,216 source nulls yield 1,216 normalized nulls; 0 drift. |
| **7** | **Enforce Decision Consistency** | Checked decision string only without enforcing database-level parity with boolean flag. | **Resolved:** Added SQLite constraint: `CHECK ((underwriting_decision = 'Approved' AND is_approved = 1) OR (underwriting_decision = 'Rejected' AND is_approved = 0))`. Verified 100% agreement between `Loan_Approved` and `loan_status` (0 mismatches). | Disallows inconsistent states; ETL raises explicit error on unexpected strings. |
| **8** | **Auditable Transformations & Safe Loading** | Broad constraints and `INSERT OR IGNORE` risked silent drops or concealed constraint violations. | **Resolved:** Strict `INSERT INTO` on fact table inside an atomic transaction with full rollback on error. Safe `INSERT OR IGNORE` strictly on dimension keys. Composite financial flag verified as row-level OR with **exactly 104 unique applications**. | Profiling confirmed App ID `530545` is the sole overlap between negative loan and negative savings. |
| **9** | **Clarify Synthetic Repayment Calculations** | Ambiguous principal basis (requested vs sanctioned) and population eligibility. | **Resolved:** Demonstrated empirically that raw CSV `amount_due` was derived from **requested principal** ($Loan\_Amount / Term$, $99.96\%$ match). Defined demonstration snapshot table for **48,596 eligible approved applications**, seed=42, and strict quarantine from underwriting KPIs. | Verified deduplicated approved population with positive sanction: $49,171 - 575 = 48,596$. |

---

## 2. Forensic Resolutions for Pre-ETL Gate Issues

### 2.1 Preserving Sanctioned-Amount Missingness & Recorded vs Real-World Zeros

#### Empirical Source Breakdown (Deduplicated Clean Population: N = 100,000)
Profiling executed against the raw source file reveals that `Approved_Amount` exhibits distinct patterns between approved and rejected applications:

```text
Approved Applications (N = 49,171):
  - Approved_Amount > 0.0:     48,596  (Recorded positive sanctioned principal in CU)
  - Approved_Amount == 0.0:         0  (Exactly zero approved applications have a recorded 0 amount)
  - Approved_Amount IS NULL:      575  (Missing sanctioned amount -> retained as NULL)

Rejected Applications (N = 50,829):
  - Approved_Amount == 0.0:    50,198  (Recorded zero sanctioned principal in CU)
  - Approved_Amount IS NULL:      631  (Missing decision amount -> retained as NULL)
  - Approved_Amount > 0.0:          0  (Exactly zero rejected applications have positive amount)

Combined Missingness Audit:
  - Total Source NULLs:         1,206  (575 Approved + 631 Rejected)
  - Total Recorded Zeros:      50,198  (All residing on Rejected applications)
  - Total Recorded Positives:  48,596  (All residing on Approved applications)
  - Total Reconciled Rows:    100,000  (48,596 + 50,198 + 1,206)
```

#### Distinguishing Recorded Values from Real-World Meaning
- **Recorded Zeros ($50,198$):** In the source dataset, 50,198 rejected applications have an explicit numeric entry of `0.0`. In a credit underwriting context, this records the real-world outcome that zero funds were sanctioned.
- **Recorded NULLs on Rejections ($631$):** 631 rejected applications contain `NULL` instead of `0.0`. While an analyst might assume rejected applicants receive zero funds in the real world, the source data did not record a zero; it recorded a missing field. To preserve forensic auditability, we retain these 631 rows as `NULL` and flag them, rather than overwriting source missingness with an imputed zero.
- **Recorded NULLs on Approvals ($575$):** 575 approved applications have missing sanctioned amounts. Replacing these with `0.0` (as the previous schema proposed via `DEFAULT 0.0`) would conflate approved borrowers with rejected applicants and corrupt average loan size metrics.

#### Revised Target Specification & SQL DDL
```sql
sanctioned_approved_amount REAL CHECK (sanctioned_approved_amount IS NULL OR sanctioned_approved_amount >= 0.0),
has_missing_sanctioned_amount INTEGER NOT NULL DEFAULT 0 CHECK (has_missing_sanctioned_amount IN (0, 1))
```

#### Ingestion & Transformation Rules
```python
# ETL Ingestion Logic for Sanctioned Amount
if pd.isnull(row['Approved_Amount']):
    sanctioned_approved_amount = None
    has_missing_sanctioned_amount = 1
elif row['Approved_Amount'] < 0:
    # Any negative amount is treated as corrupted data
    sanctioned_approved_amount = None
    has_missing_sanctioned_amount = 1
else:
    sanctioned_approved_amount = float(row['Approved_Amount'])
    has_missing_sanctioned_amount = 0
```

---

### 2.2 Credit-Score Profiling & INTEGER Casting Evidence

#### Empirical Source Profiling (`Credit_Score`, Col 10)
A proposed cast to `INTEGER` must be justified by evidence that no fractional information is destroyed. Profiling executed against `Credit_Score` across all 100,000 deduplicated records shows:

```python
cs = df_dedup['Credit_Score'].dropna()
fractionals = (cs % 1 != 0).sum()
# Output: fractionals == 0 (0.000%)
```

- **Total Deduplicated Records:** 100,000
- **Source NULLs:** **1,320 records** (1.32%)
- **Non-Null Records:** **98,680 records** (98.68%)
- **Fractional Values:** **EXACTLY 0**. 100% of non-null credit scores in the dataset are exact whole numbers (e.g. 696.0, 522.0, 822.0). The column appeared as a float solely because pandas represents numeric columns containing `NaN` as `float64`.
- **Value Distribution:**
  - Min Value: `0.0`
  - Max Value: `999.0`
  - Values $< 0$: **0**
  - Values in $[0, 299]$: **19**
  - Values in $[300, 850]$: **95,106**
  - Values in $[851, 999]$: **3,555**
  - Values $> 1000$: **0**

#### Casting Policy & Validation Rule
1. **Evidence-Based Cast:** Because 100% of non-null values have zero fractional remainder, casting to `INTEGER` preserves the source data with zero truncation error and aligns with credit bureau integer index standards.
2. **Defensive Ingestion Logic:**
   ```python
   if pd.isnull(row['Credit_Score']):
       bureau_credit_score = None
   else:
       score_val = float(row['Credit_Score'])
       if score_val % 1 != 0:
           # Log anomaly if future stream presents true fractionals
           bureau_credit_score = int(round(score_val))
       else:
           bureau_credit_score = int(score_val)
   ```
3. **Database Constraint:**
   ```sql
   bureau_credit_score INTEGER CHECK (bureau_credit_score IS NULL OR (bureau_credit_score >= 0 AND bureau_credit_score <= 1000))
   ```

---

### 2.3 Strict Boolean Parsing (Replacing `ELSE 0`)

#### Source Inventory (`Co_Applicant` and `Collateral`)
In the source CSV, both `Co_Applicant` and `Collateral` contain text representations of boolean flags with minor casing and leading/trailing whitespace variations:

- **`Co_Applicant` Unique Values (N = 100,000):**
  - `'No'`: 72,044 | `'Yes'`: 25,449 | `'NO'`: 635 | `'no'`: 628 | `' No '`: 616 | `' Yes '`: 218 | `'yes'`: 211 | `'YES'`: 199
  - Source Nulls: **0**
- **`Collateral` Unique Values (N = 100,000):**
  - `'No'`: 62,310 | `'Yes'`: 35,226 | `' No '`: 537 | `'NO'`: 517 | `'no'`: 511 | `'YES'`: 312 | `' Yes '`: 295 | `'yes'`: 292
  - Source Nulls: **0**

#### Elimination of Dangerous `ELSE 0` Logic
The earlier report proposed:
```sql
-- REJECTED: Dangerous fallback that masks unknown/missing data
CASE WHEN TRIM(UPPER(Co_Applicant)) = 'YES' THEN 1 ELSE 0 END
```
This expression is unacceptable because it silently converts `NULL`, `'MAYBE'`, `'UNKNOWN'`, or corrupted strings into `0` (`No`), masking data quality issues.

#### Revised Strict Boolean Parsing Policy
Category validation occurs **before dimension or fact insertion**. The pipeline requires explicit mapping with fail-fast exception handling:

```python
def parse_strict_boolean(val, col_name, app_id):
    if pd.isnull(val):
        return None
    cleaned = str(val).strip().upper()
    if cleaned == 'YES':
        return 1
    elif cleaned == 'NO':
        return 0
    else:
        raise ValueError(
            f"Strict boolean validation failed: Unexpected value '{val}' in column '{col_name}' "
            f"for Application_ID {app_id}. Ingestion aborted."
        )
```

Target DDL constraints enforce strict boolean integers:
```sql
co_applicant_flag INTEGER CHECK (co_applicant_flag IS NULL OR co_applicant_flag IN (0, 1)),
collateral_flag INTEGER CHECK (collateral_flag IS NULL OR collateral_flag IN (0, 1))
```

---

### 2.4 Requested-Amount Zero-Value Reconciliation & Executable Haircut Assertion

#### Empirical Breakdown of `Loan_Amount` (Col 14)
Profiling executed against the raw source file yields the following complete distribution across both underwriting outcomes:

| Application Subset | Total Rows | `Loan_Amount IS NULL` | `Loan_Amount < 0` (Negative) | `Loan_Amount == 0` (Zero) | `Loan_Amount > 0` (Positive) | Sum Reconciled |
|---|---|---|---|---|---|---|
| **Approved Applications** | 49,171 | 569 | 15 | **0** | 48,587 | 49,171 |
| **Rejected Applications** | 50,829 | 692 | 20 | **0** | 50,117 | 50,829 |
| **Total Deduplicated** | **100,000** | **1,261** | **35** | **0** | **98,704** | **100,000** |

#### Key Findings & Policy Alignment
1. **Zero Values:** Exactly **0 applications** requested an amount of `0.0 CU` in the physical dataset.
2. **Policy for Future Streams:** If a zero requested amount were encountered, a loan request of zero has no financial validity. The pipeline policy sets `requested_loan_amount = NULL` and flags `has_invalid_loan_amount = 1`.
3. **Compatibility with CHECK Constraint:** This policy is 100% compatible with the target constraint:
   ```sql
   requested_loan_amount REAL CHECK (requested_loan_amount IS NULL OR requested_loan_amount > 0)
   ```
   All 35 negative values are nullified during ingestion, ensuring zero constraint violations during database loading.

#### Executable Haircut Population Reconciliation ($N = 48,022$)
The eligible population for the underwriting policy haircut KPI is reconciled using the following executable logic:

```python
import pandas as pd
df = pd.read_csv('data/raw/kaggle_original.csv', low_memory=False)
df_dedup = df.drop_duplicates(subset=['Application_ID'], keep='first')

approved = df_dedup[df_dedup['Loan_Approved'].str.strip().str.capitalize() == 'Approved']
n_approved = len(approved)  # 49,171

# Exclusions on Approved Applications
req_null = approved['Loan_Amount'].isnull()              # 569
req_neg = approved['Loan_Amount'] <= 0                   # 15 (all 15 are < 0; 0 are == 0)
app_null = approved['Approved_Amount'].isnull()          # 575
app_zero = approved['Approved_Amount'] <= 0              # 0 (0 are <= 0)

# Overlap accounting
overlap_req_null_app_null = (req_null & app_null).sum()  # 9
overlap_req_neg_app_null = (req_neg & app_null).sum()    # 1
total_exclusions = (req_null | req_neg | app_null | app_zero).sum()  # 1,149

eligible_count = n_approved - total_exclusions

assert total_exclusions == 1149, f"Expected 1149, got {total_exclusions}"
assert eligible_count == 48022, f"Expected 48022, got {eligible_count}"
```

- **Approved Population:** $49,171$
- **Disqualified Approved Records ($1,149$):**
  - Missing requested amount: $569$
  - Negative requested amount: $15$
  - Missing sanctioned amount: $575$
  - Less intersections ($9$ null-null $+ 1$ negative-null): $-10$
- **Net Eligible Haircut Population:** $$49,171 - 1,149 = \mathbf{48,022 \text{ applications}}$$

---

### 2.5 Evidence versus Interpretation (`Default_Risk` and `Risk_Score`)

To maintain forensic integrity, we strictly separate **verified empirical observations** from **inferred business interpretations**:

#### Empirical Findings (Verified Against Source File)
1. **Source Attribute:** `Default_Risk` is an **original source column** (Column 34). It is populated for 100% of records (0 nulls) with three values: `'Low'` ($13,266$), `'Medium'` ($48,875$), and `'High'` ($37,859$).
2. **Score Completeness:** `Risk_Score` (Column 33) contains **1,216 source nulls** (59 in Low, 619 in Medium, 538 in High).
3. **Score Distributions by Tier:**
   - Low: range $[0.00, 35.00]$, mean $23.70$, non-null count $13,207$.
   - Medium: range $[34.00, 66.99]$, mean $52.13$, non-null count $48,256$.
   - High: range $[65.01, 100.00]$, mean $81.03$, non-null count $37,321$.
4. **Empirical Overlaps:**
   - Score band $[34.00, 35.00]$: **958 records** (489 Low, 469 Medium).
   - Score band $[65.00, 67.00]$: **3,413 records** (2,783 Medium, 630 High).
5. **Observed Mismatch on Naive Cut:** A mechanical score cutoff ($\le 35$ Low, $35\text{--}65$ Medium, $\ge 65$ High) produces **3,252 classification mismatches** against source `Default_Risk` and fails on the 1,216 missing scores.

#### Inferred Semantics & Working Assumptions (Explicitly Labeled)
> [!NOTE]  
> **Working Assumption:** We infer that `Default_Risk` was not generated via a simple univariate threshold on `Risk_Score`. It may reflect an independent scorecard, multi-attribute policy rules, fuzzy tier boundaries, or a synthetic generation process. Because the source repository provides no documentation or code defining how `Default_Risk` was created, **we do not assert an underwriting committee review or multi-factor policy as established fact**. We treat `Default_Risk` strictly as a source-provided categorical attribute.

#### Target Ingestion Specification
- Ingest `risk_tier` directly from source `Default_Risk`:
  ```sql
  risk_tier = TRIM(INITCAP(Default_Risk))
  ```
- Store `proprietary_risk_score` directly from source `Risk_Score`.
- Do **not** derive or overwrite `risk_tier` from `Risk_Score`.

---

### 2.6 Normalized Score Consistency & Null Preservation

#### Exact Mathematical Specification
```sql
normalized_risk_score = proprietary_risk_score / 100.0
```

#### Executable Validation on Deduplicated Source Data
Executing verification across all 100,000 records confirms:
```python
rs = df_dedup['Risk_Score']
norm_rs = rs / 100.0

# 1. Null preservation assertion
assert rs.isnull().sum() == 1216
assert norm_rs.isnull().sum() == 1216
assert (rs.isnull() == norm_rs.isnull()).all()

# 2. Boundary assertion on non-nulls
non_null_mask = rs.notnull()
assert norm_rs[non_null_mask].min() == 0.0
assert norm_rs[non_null_mask].max() == 1.0
assert ((norm_rs[non_null_mask] >= 0.0) & (norm_rs[non_null_mask] <= 1.0)).all()
```

- **Null Preservation:** In 100% of cases where `proprietary_risk_score IS NULL` ($1,216$ records), `normalized_risk_score` is set strictly to `NULL`.
- **Value Bounds:** For all 98,784 non-null records, `normalized_risk_score` falls strictly within $[0.0, 1.0]$.
- **Target DDL Constraint:**
  ```sql
  normalized_risk_score REAL CHECK (normalized_risk_score IS NULL OR (normalized_risk_score >= 0.0 AND normalized_risk_score <= 1.0))
  ```
- **Semantic Guardrail:** This column is documented strictly as a continuous score scaling ($0.0\text{--}1.0$). It is **never** presented as an empirical or calibrated Probability of Default (PD).

---

### 2.7 Enforcing Decision Consistency & Safe Transactional Loading

#### SQLite Schema CHECK Constraint
```sql
CONSTRAINT chk_decision_consistency CHECK (
    (underwriting_decision = 'Approved' AND is_approved = 1) OR
    (underwriting_decision = 'Rejected' AND is_approved = 0)
)
```

#### Inconsistent Record Handling Policy
1. **Source Status:** Profiling confirmed 100% agreement between `Loan_Approved` and `loan_status` (0 mismatches, 0 nulls, only `'Approved'` and `'Rejected'`).
2. **ETL Validation Rule:** Prior to database insertion, the string is canonicalized. If any record presents an unrecognized string (e.g. `'Pending'`, `'Under Review'`, `'Unknown'`, `NULL`), the pipeline raises an unhandled `ValueError` and rolls back the transaction. In optional quarantine mode, it is routed to `stg_quarantined_records`.

#### Safe Database Loading Strategy
1. **Lookup Dimensions:** Loaded using safe `INSERT OR IGNORE` on conformed unique keys (`region, residential_status, property_ownership`, `channel_name`, `purpose_name`). Legitimate duplicate dimension combinations are handled gracefully without data loss.
2. **Fact Table (`fct_loan_application`):** Loaded strictly with `INSERT INTO` inside an atomic transaction (`BEGIN TRANSACTION ... COMMIT`). `INSERT OR IGNORE` on the fact table is strictly prohibited; any constraint violation causes an immediate abort and complete rollback (`ROLLBACK`).

#### Composite Financial Quality Flag Formulation
- Formula:
  $$\text{has\_invalid\_financials} = \text{has\_invalid\_annual_income} \lor \text{has\_invalid\_loan\_amount} \lor \text{has\_invalid\_savings\_balance}$$
- Overlap Verification:
  - Applications with `Annual_Income < 0`: 35
  - Applications with `Loan_Amount < 0`: 35
  - Applications with `Savings_Balance < 0`: 35
  - Overlap between Negative Loan and Negative Savings: **Exactly 1 application** (Application ID `530545`, source row ordinal 91,694).
  - Overlap between Negative Income and Negative Loan: 0.
  - Overlap between Negative Income and Negative Savings: 0.
  - Net Unique Affected Applications: $$35 + 35 + 35 - 1 = \mathbf{104 \text{ unique applications}}$$

---

### 2.8 Synthetic Repayment Servicing & Principal Basis

#### Principal Basis Discrepancy
Profiling revealed that in `kaggle_original.csv`:
```python
diff_requested = abs(df['amount_due'] - (df['Loan_Amount'] / df['Loan_Term_Months']))
matches_requested = (diff_requested < 0.01).sum()  # 97,329 of 97,364 rows (99.96%)
```
In 99.96% of rows, the synthetic installment `amount_due` was derived from **requested principal**, not sanctioned principal. We document this generator flaw explicitly.

#### Eligible Demonstration Snapshot Population
- Servicing records are retained strictly for approved applications with known, positive sanctioned funds:
  $$\text{Deduplicated Approved (49,171)} - \text{Missing Sanctioned (575)} = \mathbf{48,596 \text{ applications}}$$
- Deterministic random seed: `numpy.random.default_rng(seed=42)`.
- Sentinel cleansing: `'not_a_date'` ($20$ rows) and `'31/31/2025'` ($20$ rows) set to `NULL`.
- Missing inputs: Missing loan amount or term nullifies all simulated servicing fields.
- Demonstration Isolation: Quarantined in `demo_synthetic_repayment_snapshot`, zero presence in core underwriting KPI views, persistent UI demonstration disclaimer.

---

## 3. Deduplication, Identifier Integrity & Row Reconciliation

### 3.1 Empirical Equivalence Verification
Using profiling scripts executed against `data/raw/kaggle_original.csv`, we verified that duplicate `Application_ID` records are 100% identical across all columns:

```python
import pandas as pd
df = pd.read_csv('data/raw/kaggle_original.csv', low_memory=False)

orig_36 = list(df.columns[:36])
dup_all = df.duplicated(keep='first')
dup_orig = df.duplicated(subset=orig_36, keep='first')
dup_id = df.duplicated(subset=['Application_ID'], keep='first')

assert dup_all.sum() == 150
assert dup_orig.sum() == 150
assert dup_id.sum() == 150
assert (dup_all == dup_orig).all() and (dup_orig == dup_id).all()
```

- **All 67 columns duplicate count:** Exactly **150**.
- **Original 36 columns duplicate count:** Exactly **150**.
- **`Application_ID` duplicate count:** Exactly **150**.
- **Conflicting records for any `Application_ID`:** Exactly **0**. Every duplicate row is an identical clone.

### 3.2 Deterministic Deduplication Rule
1. Assign a 1-indexed **`source_row_ordinal`** ($1$ to $100,150$) reflecting physical line order in the raw CSV.
2. Filter duplicates by preserving the earliest source line:
   ```sql
   WITH ranked_staging AS (
       SELECT *,
              ROW_NUMBER() OVER (
                  PARTITION BY Application_ID 
                  ORDER BY source_row_ordinal ASC
              ) AS deduplication_rank
       FROM stg_raw_loan_data
   )
   SELECT * FROM ranked_staging WHERE deduplication_rank = 1;
   ```

### 3.3 Verified Application Status Reconciliation

| Underwriting Decision | Raw CSV Rows (100,150) | In 150 Duplicate Rows | Deduplicated Analytical View (100,000) | Clean Portfolio Share (%) |
|---|---|---|---|---|
| **Approved** | **49,243** | **72** | **49,171** | **49.171%** |
| **Rejected** | **50,907** | **78** | **50,829** | **50.829%** |
| **Pending / In Review** | **0** | **0** | **0** | **0.000%** |
| **Unknown / Null** | **0** | **0** | **0** | **0.000%** |
| **Total Applications** | **100,150** | **150** | **100,000** | **100.000%** |

$$\text{Reconciliation: } 49,243 - 72 = 49,171 \text{ (Approved)} \quad\mid\quad 50,907 - 78 = 50,829 \text{ (Rejected)} \quad\mid\quad \text{Total: } 100,000$$

---

## 4. Complete Source-to-Target Lineage (All 36 Original Columns)

Every original column from Part 1 (Cols 1–36) has been evaluated, validated, and mapped:

| # | Source Column Name | Inferred Source Type | Target Table & Column | Cleaning Transformation & Mapping Rule | Null & Invalid Value Handling | Validation Rule / Range Check | Intended Analytical Purpose |
|---|---|---|---|---|---|---|---|
| **1** | `Application_ID` | `INT64` | `fct_loan_application.application_id` | Direct passthrough; deduplicated on first source occurrence. | 0 nulls in source. `NOT NULL`. | `application_id > 0` | Primary key of the analytical warehouse; unique application tracking. |
| **2** | `Age` | `FLOAT64` | `fct_loan_application.age` | Cast to `INTEGER` (profiling confirmed 0 fractional ages). | 1,201 source nulls preserved as `NULL`. 25 out-of-bounds ($<18$ or $>100$) set to `NULL` + flagged `has_invalid_age = 1`. | `CHECK (age IS NULL OR (age >= 18 AND age <= 100))` | Applicant demographic profiling; age-bracket underwriting analysis. |
| **3** | `Gender` | `STRING` | `fct_loan_application.gender` | String trimming: `TRIM(INITCAP(Gender))`. | 0 nulls in source. | `CHECK (gender IN ('Male', 'Female'))` | Demographic equity analysis; portfolio demographic distribution. |
| **4** | `Marital_Status` | `STRING` | `fct_loan_application.marital_status` | String canonicalization: `TRIM(INITCAP(Marital_Status))`. | 0 nulls in source. | `CHECK (marital_status IN ('Married', 'Single', 'Divorced', 'Widowed'))` | Household stability analysis; underwriting risk tiering. |
| **5** | `Education_Level` | `STRING` | `fct_loan_application.education_level` | String canonicalization: `TRIM(INITCAP(Education_Level))`. | 0 nulls in source. | `CHECK (education_level IN ('Bachelor', 'High School', 'Master', 'Phd'))` | Socio-economic underwriting segmentation. |
| **6** | `Employment_Status` | `STRING` | `fct_loan_application.employment_status` | String canonicalization: `TRIM(INITCAP(Employment_Status))`. | 0 nulls in source. | `CHECK (employment_status IN ('Salaried', 'Self-Employed', 'Contract', 'Freelancer'))` | Employment stability and borrower cash flow profiling. |
| **7** | `Job_Experience_Years` | `INT64` | `fct_loan_application.job_experience_years` | Direct integer passthrough (profiling confirmed 0 fractionals). | 0 nulls in source. | `CHECK (job_experience_years IS NULL OR job_experience_years >= 0)` | Career longevity and underwriting score stability indicator. |
| **8** | `Annual_Income` | `FLOAT64` | `fct_loan_application.annual_income` | Numeric passthrough in `CU`. | 1,292 source nulls preserved. 35 negative values set to `NULL` + flagged `has_invalid_annual_income = 1`. | `CHECK (annual_income IS NULL OR annual_income >= 0)` | Borrower earning capacity; DTI verification; income decile analysis. |
| **9** | `Monthly_Income` | `FLOAT64` | `fct_loan_application.monthly_income_reported` | Numeric passthrough in `CU`. | 1,299 source nulls preserved as `NULL`. | `CHECK (monthly_income_reported IS NULL OR monthly_income_reported >= 0)` | Cash flow audit; compared against calculated `annual_income / 12.0`. |
| **10** | `Credit_Score` | `FLOAT64` | `fct_loan_application.bureau_credit_score` | Cast to `INTEGER` (profiling confirmed 0 fractional credit scores). | 1,320 source nulls preserved as `NULL`. | `CHECK (bureau_credit_score IS NULL OR (bureau_credit_score >= 0 AND bureau_credit_score <= 1000))` | Primary external credit bureau score (0 to 999 continuous index). |
| **11** | `Credit_History_Years` | `FLOAT64` | `fct_loan_application.bureau_credit_history_years` | Numeric passthrough. | 0 nulls in source. | `CHECK (bureau_credit_history_years IS NULL OR bureau_credit_history_years >= 0)` | Credit file seasoning (thin-file vs seasoned bureau profile). |
| **12** | `Existing_Loans` | `INT64` | `fct_loan_application.bureau_existing_loans` | Integer passthrough. | 0 nulls in source. Discrete values 0–11. | `CHECK (bureau_existing_loans IS NULL OR bureau_existing_loans >= 0)` | Active credit facility count on bureau file. |
| **13** | `Late_Payments_Last_2_Years` | `INT64` | `fct_loan_application.bureau_late_payments_2yr` | Integer passthrough. | 0 nulls in source. Discrete values 0–10. | `CHECK (bureau_late_payments_2yr IS NULL OR bureau_late_payments_2yr >= 0)` | Historical bureau delinquencies (vital credit underwriting risk metric). |
| **14** | `Loan_Amount` | `FLOAT64` | `fct_loan_application.requested_loan_amount` | Numeric passthrough in `CU` (0 zero values in source). | 1,261 source nulls preserved. 35 negative values set to `NULL` + flagged `has_invalid_loan_amount = 1`. | `CHECK (requested_loan_amount IS NULL OR requested_loan_amount > 0)` | Requested loan principal in `CU`; denominator for haircut analysis. |
| **15** | `Loan_Term_Months` | `INT64` | `fct_loan_application.requested_term_months` | Integer passthrough. | 0 nulls in source. Values: 12, 24, 36, 48, 60, 72, 84, 120, 180, 360. | `CHECK (requested_term_months IS NULL OR requested_term_months > 0)` | Loan amortization duration. |
| **16** | `Loan_Purpose` | `STRING` | `dim_loan_purpose.purpose_name` -> `fct.purpose_id` | Normalized into conformed dimension: `Home`, `Education`, `Vehicle`, `Personal`, `Debt Consolidation`. | 0 nulls in source. | Conformed FK reference. | Portfolio product distribution; haircut analysis by loan category. |
| **17** | `Interest_Rate` | `FLOAT64` | `fct_loan_application.interest_rate` | Numeric passthrough as percentage (5.00 to 30.00). | 1,305 source nulls preserved as `NULL`. | `CHECK (interest_rate IS NULL OR (interest_rate >= 0 AND interest_rate <= 100))` | Loan pricing and APR spread analysis across risk tiers. |
| **18** | `Debt_To_Income_Ratio` | `FLOAT64` | `fct_loan_application.debt_to_income_ratio` | Numeric passthrough as percentage (0.0 to 95.0). | 1,259 source nulls preserved as `NULL`. 0 negatives. | `CHECK (debt_to_income_ratio IS NULL OR (debt_to_income_ratio >= 0 AND debt_to_income_ratio <= 100))` | Core solvency indicator; exploratory DTI bracket distribution. |
| **19** | `Savings_Balance` | `FLOAT64` | `fct_loan_application.savings_balance` | Numeric passthrough in `CU`. | 1,265 source nulls preserved. 35 negative values set to `NULL` + flagged `has_invalid_savings_balance = 1`. | `CHECK (savings_balance IS NULL OR savings_balance >= 0)` | Liquid reserve asset cushion analysis. |
| **20** | `Checking_Balance` | `FLOAT64` | `fct_loan_application.checking_balance` | Numeric passthrough in `CU`. | 1,192 source nulls preserved as `NULL`. | `CHECK (checking_balance IS NULL OR checking_balance >= 0)` | Operational liquidity reserve analysis. |
| **21** | `Total_Assets` | `FLOAT64` | `fct_loan_application.total_assets` | Numeric passthrough in `CU`. | 1,260 source nulls preserved as `NULL`. | `CHECK (total_assets IS NULL OR total_assets >= 0)` | Total applicant wealth / asset coverage. |
| **22** | `Total_Liabilities` | `FLOAT64` | `fct_loan_application.total_liabilities` | Numeric passthrough in `CU`. | 1,298 source nulls preserved as `NULL`. | `CHECK (total_liabilities IS NULL OR total_liabilities >= 0)` | Existing debt burden; balance sheet leverage analysis. |
| **23** | `Monthly_Debt_Payment` | `FLOAT64` | `fct_loan_application.monthly_debt_payment` | Numeric passthrough in `CU`. | 1,259 source nulls preserved as `NULL`. | `CHECK (monthly_debt_payment IS NULL OR monthly_debt_payment >= 0)` | Monthly debt servicing burden; cash flow solvency. |
| **24** | `Property_Ownership` | `STRING` | `dim_residence_property_location.property_ownership` | Normalized: `Rent`, `Own`, `Mortgage`, `Other`, `Family Owned`. | 0 nulls in source. | Conformed FK reference. | Collateral / real estate ownership analysis. |
| **25** | `Residential_Status` | `STRING` | `dim_residence_property_location.residential_status` | Normalized: `Urban`, `Suburban`, `Rural`. | 0 nulls in source. | Conformed FK reference. | Residential stability analysis. |
| **26** | `Dependents` | `INT64` | `fct_loan_application.dependents` | Integer passthrough. | 0 nulls in source. Discrete values 0–6. | `CHECK (dependents IS NULL OR dependents >= 0)` | Household expenditure load. |
| **27** | `Co_Applicant` | `STRING` | `fct_loan_application.co_applicant_flag` | Strict boolean parsing: `'YES' -> 1`, `'NO' -> 0`, `NULL -> NULL`. Pre-insertion validation rejects unexpected values. | 0 nulls in source. | `CHECK (co_applicant_flag IS NULL OR co_applicant_flag IN (0, 1))` | Guarantor / co-borrower credit support analysis. |
| **28** | `Collateral` | `STRING` | `fct_loan_application.collateral_flag` | Strict boolean parsing: `'YES' -> 1`, `'NO' -> 0`, `NULL -> NULL`. Pre-insertion validation rejects unexpected values. | 0 nulls in source. | `CHECK (collateral_flag IS NULL OR collateral_flag IN (0, 1))` | Secured vs unsecured underwriting sanction analysis. |
| **29** | `Application_Channel` | `STRING` | `dim_channel.channel_name` -> `fct.channel_id` | Normalized into conformed dimension: `Online`, `Branch`, `Mobile App`, `Agent`. | 0 nulls in source. | Conformed FK reference. | Channel volume and underwriting approval rate analysis. |
| **30** | `Region` | `STRING` | `dim_residence_property_location.region` | Normalized into 5 macro-regions: `East`, `South`, `Central`, `North`, `West`. | 0 nulls in source. | Conformed FK reference. | Primary geographic reporting dimension. |
| **31** | `Bank_Account_Age_Years` | `FLOAT64` | `fct_loan_application.bank_account_tenure_months` | Derived as `ROUND(Bank_Account_Age_Years * 12)`. | 0 nulls in source. | `CHECK (bank_account_tenure_months >= 0)` | Institutional relationship tenure in months. |
| **32** | `Previous_Loan_Status` | `STRING` | `fct_loan_application.bureau_prior_loan_status` | Clean to Title Case: `Paid Off`, `Active`, `No Previous Loan`, `Defaulted`. | 0 nulls in source. | `CHECK (bureau_prior_loan_status IN ('Paid Off', 'Active', 'No Previous Loan', 'Defaulted'))` | Credit bureau historical credit performance (external prior loans). |
| **33** | `Risk_Score` | `FLOAT64` | `fct_loan_application.proprietary_risk_score` | Continuous scorecard value (0.00 to 100.00). | 1,216 source nulls preserved as `NULL`. | `CHECK (proprietary_risk_score IS NULL OR (proprietary_risk_score >= 0 AND proprietary_risk_score <= 100))` | Internal scorecard continuous risk rating. |
| **34** | `Default_Risk` | `STRING` | `fct_loan_application.risk_tier` | Ingested directly from source; normalized to Title Case: `Low`, `Medium`, `High`. | 0 nulls in source. | `CHECK (risk_tier IN ('Low', 'Medium', 'High'))` | Source-provided categorical underwriting risk tier. |
| **35** | `Approved_Amount` | `FLOAT64` | `fct_loan_application.sanctioned_approved_amount` | Numeric amount in `CU`. Preserves genuine 0.0 for Rejected; preserves source NULLs; flagged with `has_missing_sanctioned_amount`. | 1,206 source nulls preserved as `NULL` (575 Approved, 631 Rejected). | `CHECK (sanctioned_approved_amount IS NULL OR sanctioned_approved_amount >= 0)` | Sanctioned loan principal; numerator for haircut analysis. |
| **36** | `Loan_Approved` | `STRING` | `fct_loan_application.underwriting_decision` & `is_approved` | Normalized string (`'Approved'` / `'Rejected'`) & integer flag (`1` / `0`). Strictly parity-checked. | 0 nulls in source. | `CHECK ((underwriting_decision = 'Approved' AND is_approved = 1) OR (underwriting_decision = 'Rejected' AND is_approved = 0))` | Primary underwriting sanction outcome (binary target of credit committee). |

---

## 5. Corrected SQLite Schema (DDL)

```sql
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. CONFORMED LOOKUP DIMENSIONS
-- ============================================================================

-- Combined housing, property, and macro-geography lookup (75 distinct clean combos)
CREATE TABLE IF NOT EXISTS dim_residence_property_location (
    location_property_id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT NOT NULL CHECK (region IN ('East', 'South', 'Central', 'North', 'West')),
    residential_status TEXT NOT NULL CHECK (residential_status IN ('Urban', 'Suburban', 'Rural')),
    property_ownership TEXT NOT NULL CHECK (property_ownership IN ('Rent', 'Own', 'Mortgage', 'Other', 'Family Owned')),
    UNIQUE(region, residential_status, property_ownership)
);

CREATE TABLE IF NOT EXISTS dim_channel (
    channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name TEXT NOT NULL UNIQUE CHECK (channel_name IN ('Online', 'Branch', 'Mobile App', 'Agent'))
);

CREATE TABLE IF NOT EXISTS dim_loan_purpose (
    purpose_id INTEGER PRIMARY KEY AUTOINCREMENT,
    purpose_name TEXT NOT NULL UNIQUE CHECK (purpose_name IN ('Home', 'Education', 'Vehicle', 'Personal', 'Debt Consolidation'))
);

-- ============================================================================
-- 2. PRIMARY APPLICATION FACT TABLE (Application Grain: 100,000 Rows)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fct_loan_application (
    application_id INTEGER PRIMARY KEY,
    source_row_ordinal INTEGER NOT NULL UNIQUE,
    location_property_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    purpose_id INTEGER NOT NULL,
    
    -- Applicant Demographics & Socio-Economics (Safe constraints allowing NULL)
    age INTEGER CHECK (age IS NULL OR (age >= 18 AND age <= 100)),
    gender TEXT CHECK (gender IS NULL OR gender IN ('Male', 'Female')),
    marital_status TEXT CHECK (marital_status IS NULL OR marital_status IN ('Married', 'Single', 'Divorced', 'Widowed')),
    education_level TEXT CHECK (education_level IS NULL OR education_level IN ('Bachelor', 'High School', 'Master', 'Phd')),
    employment_status TEXT CHECK (employment_status IS NULL OR employment_status IN ('Salaried', 'Self-Employed', 'Contract', 'Freelancer')),
    job_experience_years INTEGER CHECK (job_experience_years IS NULL OR job_experience_years >= 0),
    dependents INTEGER CHECK (dependents IS NULL OR dependents >= 0),
    
    -- Financial Balances (CU) (Nullified if negative)
    annual_income REAL CHECK (annual_income IS NULL OR annual_income >= 0),
    monthly_income_reported REAL CHECK (monthly_income_reported IS NULL OR monthly_income_reported >= 0),
    monthly_income_calculated REAL CHECK (monthly_income_calculated IS NULL OR monthly_income_calculated >= 0),
    savings_balance REAL CHECK (savings_balance IS NULL OR savings_balance >= 0),
    checking_balance REAL CHECK (checking_balance IS NULL OR checking_balance >= 0),
    total_assets REAL CHECK (total_assets IS NULL OR total_assets >= 0),
    total_liabilities REAL CHECK (total_liabilities IS NULL OR total_liabilities >= 0),
    monthly_debt_payment REAL CHECK (monthly_debt_payment IS NULL OR monthly_debt_payment >= 0),
    net_worth REAL,
    bank_account_tenure_months INTEGER CHECK (bank_account_tenure_months IS NULL OR bank_account_tenure_months >= 0),
    
    -- Loan Request & Underwriting Attributes
    requested_loan_amount REAL CHECK (requested_loan_amount IS NULL OR requested_loan_amount > 0),
    requested_term_months INTEGER CHECK (requested_term_months IS NULL OR requested_term_months > 0),
    interest_rate REAL CHECK (interest_rate IS NULL OR (interest_rate >= 0 AND interest_rate <= 100)),
    debt_to_income_ratio REAL CHECK (debt_to_income_ratio IS NULL OR (debt_to_income_ratio >= 0 AND debt_to_income_ratio <= 100)),
    co_applicant_flag INTEGER CHECK (co_applicant_flag IS NULL OR co_applicant_flag IN (0, 1)),
    collateral_flag INTEGER CHECK (collateral_flag IS NULL OR collateral_flag IN (0, 1)),
    
    -- Credit Bureau Attributes
    bureau_credit_score INTEGER CHECK (bureau_credit_score IS NULL OR (bureau_credit_score >= 0 AND bureau_credit_score <= 1000)),
    bureau_existing_loans INTEGER CHECK (bureau_existing_loans IS NULL OR bureau_existing_loans >= 0),
    bureau_late_payments_2yr INTEGER CHECK (bureau_late_payments_2yr IS NULL OR bureau_late_payments_2yr >= 0),
    bureau_credit_history_years REAL CHECK (bureau_credit_history_years IS NULL OR bureau_credit_history_years >= 0),
    bureau_prior_loan_status TEXT CHECK (bureau_prior_loan_status IS NULL OR bureau_prior_loan_status IN ('Paid Off', 'Active', 'No Previous Loan', 'Defaulted')),
    
    -- Proprietary Scorecard Attributes
    proprietary_risk_score REAL CHECK (proprietary_risk_score IS NULL OR (proprietary_risk_score >= 0 AND proprietary_risk_score <= 100)),
    risk_tier TEXT CHECK (risk_tier IS NULL OR risk_tier IN ('Low', 'Medium', 'High')),
    normalized_risk_score REAL CHECK (normalized_risk_score IS NULL OR (normalized_risk_score >= 0.0 AND normalized_risk_score <= 1.0)),
    
    -- Final Underwriting Sanction (Enforcing Strict Parity Between String and Boolean)
    underwriting_decision TEXT NOT NULL CHECK (underwriting_decision IN ('Approved', 'Rejected')),
    sanctioned_approved_amount REAL CHECK (sanctioned_approved_amount IS NULL OR sanctioned_approved_amount >= 0.0),
    is_approved INTEGER NOT NULL CHECK (is_approved IN (0, 1)),
    has_missing_sanctioned_amount INTEGER NOT NULL DEFAULT 0 CHECK (has_missing_sanctioned_amount IN (0, 1)),
    
    -- Decision Consistency Constraint
    CONSTRAINT chk_decision_consistency CHECK (
        (underwriting_decision = 'Approved' AND is_approved = 1) OR
        (underwriting_decision = 'Rejected' AND is_approved = 0)
    ),
    
    -- Data Quality Audit Flags (1 = Issue Present, 0 = Clean)
    has_invalid_annual_income INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_annual_income IN (0, 1)),
    has_invalid_loan_amount INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_loan_amount IN (0, 1)),
    has_invalid_savings_balance INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_savings_balance IN (0, 1)),
    has_invalid_age INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_age IN (0, 1)),
    has_invalid_financials INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_financials IN (0, 1)),
    
    FOREIGN KEY (location_property_id) REFERENCES dim_residence_property_location(location_property_id),
    FOREIGN KEY (channel_id) REFERENCES dim_channel(channel_id),
    FOREIGN KEY (purpose_id) REFERENCES dim_loan_purpose(purpose_id)
);

CREATE INDEX IF NOT EXISTS idx_fct_decision ON fct_loan_application(underwriting_decision);
CREATE INDEX IF NOT EXISTS idx_fct_location ON fct_loan_application(location_property_id);
CREATE INDEX IF NOT EXISTS idx_fct_channel ON fct_loan_application(channel_id);
CREATE INDEX IF NOT EXISTS idx_fct_purpose ON fct_loan_application(purpose_id);

-- ============================================================================
-- 3. QUARANTINED DEMONSTRATION TABLE (Synthetic Servicing Snapshot)
-- ============================================================================

CREATE TABLE IF NOT EXISTS demo_synthetic_repayment_snapshot (
    application_id INTEGER PRIMARY KEY,
    simulated_due_date TEXT,
    simulated_payment_date TEXT,
    simulated_amount_due_cu REAL,
    simulated_amount_paid_cu REAL,
    simulated_days_late INTEGER,
    simulated_payment_status TEXT,
    simulated_disbursement_amount_cu REAL,
    simulated_outstanding_balance_cu REAL,
    FOREIGN KEY (application_id) REFERENCES fct_loan_application(application_id)
);
```

### 5.1 Ingestion Transaction & Connection Protocol
The Python ETL pipeline (`src/data/etl_pipeline.py`) will adhere to this transactional execution protocol:
1. Initialize connection with `PRAGMA foreign_keys = ON;`.
2. Wrap all insertions inside a single transaction:
   ```python
   try:
       conn.execute("BEGIN TRANSACTION;")
       # 1. Pre-insertion validation of all categorical and boolean fields
       # 2. Insert lookup dimensions using INSERT OR IGNORE
       # 3. Insert clean fct_loan_application using strict INSERT INTO (100,000 rows)
       # 4. Insert demo_synthetic_repayment_snapshot (48,596 rows)
       # 5. Verify integrity
       cursor = conn.cursor()
       cursor.execute("PRAGMA foreign_key_check;")
       violations = cursor.fetchall()
       if violations:
           raise ValueError(f"Foreign key violations detected: {violations}")
       conn.commit()
   except Exception as e:
       conn.rollback()
       raise RuntimeError(f"ETL pipeline failed. Transaction rolled back completely: {e}")
   ```

---

## 6. Primary Underwriting KPIs & Analytical Formulations

### KPI 1: Portfolio Underwriting Approval Rate
- **Metric Formula:**  
  $$\text{Approval Rate (\%)} = \left( \frac{\sum \text{is\_approved}}{\text{Total Applications}} \right) \times 100.0$$
- **Numerator:** Count of applications where `underwriting_decision = 'Approved'` ($49,171$).
- **Denominator:** **Total unique applications ($100,000$)**.
- **Null Handling:** `underwriting_decision` contains 0 nulls.
- **SQL Implementation:**
  ```sql
  SELECT COUNT(*) AS total_applications,
         SUM(is_approved) AS approved_applications,
         ROUND(AVG(is_approved) * 100.0, 2) AS approval_rate_pct,
         ROUND((1.0 - AVG(is_approved)) * 100.0, 2) AS rejection_rate_pct
  FROM fct_loan_application;
  ```

### KPI 2: Channel Underwriting Approval Rate
- **Metric Formula:**  
  $$\text{Channel Approval Rate (\%)} = \left( \frac{\sum_{\text{channel}} \text{is\_approved}}{\text{Total Applications in Channel}} \right) \times 100.0$$
- **Numerator:** Approved applications within channel.
- **Denominator:** Total applications received through that channel.
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

### KPI 3: Underwriting Policy Haircut (Sanction Rationing)
- **Metric Formula:**  
  $$\text{Haircut (\%)} = \left( 1.0 - \frac{\sum \text{sanctioned\_approved\_amount}}{\sum \text{requested\_loan\_amount}} \right) \times 100.0$$
- **Consistent Population Definition (Numerator & Denominator):**
  - Strictly Approved applications ($is\_approved = 1$)
  - Valid positive requested amount ($\text{requested\_loan\_amount} > 0$)
  - Valid non-null sanctioned amount ($\text{sanctioned\_approved\_amount IS NOT NULL}$)
- **Excluded Records Breakdown ($1,149$ total approved exclusions):**
  - Missing requested amount: $569$
  - Negative requested amount: $15$
  - Missing sanctioned amount: $575$
  - Less intersections ($9$ null-null overlaps $+ 1$ negative-null overlap): $-10$
  - Net excluded: $569 + 15 + 575 - 10 = \mathbf{1,149 \text{ records}}$.
- **Net Eligible Population:** $$49,171 - 1,149 = \mathbf{48,022 \text{ applications}}$$
- **SQL Implementation:**
  ```sql
  SELECT p.purpose_name,
         COUNT(*) AS eligible_approved_count,
         ROUND(SUM(f.requested_loan_amount), 2) AS total_requested_cu,
         ROUND(SUM(f.sanctioned_approved_amount), 2) AS total_sanctioned_cu,
         ROUND(SUM(f.requested_loan_amount - f.sanctioned_approved_amount), 2) AS total_haircut_cu,
         ROUND((1.0 - (SUM(f.sanctioned_approved_amount) / SUM(f.requested_loan_amount))) * 100.0, 2) AS aggregate_haircut_pct
  FROM fct_loan_application f
  JOIN dim_loan_purpose p ON f.purpose_id = p.purpose_id
  WHERE f.is_approved = 1 
    AND f.requested_loan_amount IS NOT NULL 
    AND f.requested_loan_amount > 0
    AND f.sanctioned_approved_amount IS NOT NULL
  GROUP BY p.purpose_name
  HAVING SUM(f.requested_loan_amount) > 0
  ORDER BY aggregate_haircut_pct DESC;
  ```

### KPI 4: Debt-to-Income (DTI) Solvency Distribution
- **Metric Scale:** **Percentage (0.0% to 100.0%)**.
- **Numerator:** Application count within DTI bracket.
- **Denominator:** **Total applications where `debt_to_income_ratio IS NOT NULL` ($98,741$)**.
- **Null Handling:** Excludes 1,259 source-null records from bracket share; reports null count in a data-completeness indicator.
- **Exploratory Thresholds:** `0-20%` (Low), `21-35%` (Moderate), `36-43%` (Elevated), `>43%` (High).
- **SQL Implementation:**
  ```sql
  SELECT CASE 
             WHEN debt_to_income_ratio <= 20.0 THEN '1. Low Debt (0 - 20%)'
             WHEN debt_to_income_ratio <= 35.0 THEN '2. Moderate Debt (21 - 35%)'
             WHEN debt_to_income_ratio <= 43.0 THEN '3. Elevated Debt (36 - 43%)'
             ELSE '4. High Exposure (> 43%)'
         END AS dti_bracket,
         COUNT(*) AS application_count,
         ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fct_loan_application WHERE debt_to_income_ratio IS NOT NULL), 2) AS bracket_share_pct,
         ROUND(AVG(is_approved) * 100.0, 2) AS approval_rate_pct
  FROM fct_loan_application
  WHERE debt_to_income_ratio IS NOT NULL
  GROUP BY 1
  ORDER BY 1;
  ```

### KPI 5: Descriptive Scorecard Tier Segmentation
- **Metric Scope:** Descriptive comparison of source-provided risk tiers (`Low`, `Medium`, `High`) against external bureau scores.
- **Numerator:** Approved applications within risk tier.
- **Denominator:** Total applications within that tier where `risk_tier IS NOT NULL`.
- **SQL Implementation:**
  ```sql
  SELECT risk_tier,
         COUNT(*) AS tier_applications,
         ROUND(AVG(proprietary_risk_score), 2) AS avg_internal_score,
         ROUND(AVG(bureau_credit_score), 1) AS avg_bureau_score,
         SUM(is_approved) AS approved_count,
         ROUND(AVG(is_approved) * 100.0, 2) AS approval_rate_pct
  FROM fct_loan_application
  WHERE risk_tier IS NOT NULL
  GROUP BY risk_tier
  ORDER BY avg_internal_score ASC;
  ```

---

## 7. Verification Status: Executed Profiling Checks vs. Proposed Future Tests

To maintain complete audit integrity, all checks are strictly divided into empirical findings verified via executed Python scripts versus proposed automated tests to be executed during Milestone 1:

### 7.1 Executed Empirical Checks (Verified Against Physical CSV)

| Check ID | Verification Scope | Status | Execution Command / Script Logic | Verified Output & Findings |
|---|---|---|---|---|
| **EXEC-01** | Raw File Physical Profile | **EXECUTED** | `os.path.getsize()`, `csv.reader` | 46,779,106 bytes, 67 columns, 100,150 data rows, 0 corrupted lines. |
| **EXEC-02** | Duplicate Equivalence Check | **EXECUTED** | Pandas duplicate mask intersection | All 67 cols duplicate count (150) == Part 1 duplicate count (150) == Application_ID duplicate count (150). |
| **EXEC-03** | Conflicting Application_ID Records | **EXECUTED** | Groupby Application_ID equality check | 0 conflicting records. Every repeated ID is an exact row clone. |
| **EXEC-04** | Deduplicated Decision Split | **EXECUTED** | Raw status counts minus duplicate counts | 49,243 - 72 = 49,171 Approved; 50,907 - 78 = 50,829 Rejected. |
| **EXEC-05** | Approved_Amount Breakdown | **EXECUTED** | Filtering approved/rejected amounts | Approved: 48,596 positive, 0 zero, 575 null. Rejected: 50,198 zero, 0 positive, 631 null. Total nulls: 1,206. |
| **EXEC-06** | Financial Flag Overlap Analysis | **EXECUTED** | Set intersections on negative indicators | Negative income (35), negative loan (35), negative savings (35). Overlap loan & savings = 1 (App ID 530545). Net composite = **104**. |
| **EXEC-07** | Usable DTI Count | **EXECUTED** | `df_dedup['Debt_To_Income_Ratio'].notnull().sum()` | 98,741 usable non-null records ($100,000 - 1,259$). |
| **EXEC-08** | Haircut Exceedance Check | **EXECUTED** | `Approved_Amount > Loan_Amount` on positive loans | 0 positive loans exceeded. All 14 exceedances occurred on negative loan amounts. |
| **EXEC-09** | Haircut Eligible Population Assertion | **EXECUTED** | Multi-condition filter on approved apps | Excluded: 1,149 records. Net eligible population: **48,022 applications** verified via programmatic assertion. Aggregate haircut: **20.32%**. |
| **EXEC-10** | Synthetic Servicing Formula | **EXECUTED** | Check `amount_due` against Loan_Amount and Approved_Amount / Term | Matches `Loan_Amount / Term` in 99.96% of rows (97,329 of 97,364). Matches `Approved_Amount / Term` in only 9.25%. |
| **EXEC-11** | Fractional Age Check | **EXECUTED** | `(df_dedup['Age'].dropna() % 1 != 0).sum()` | 0 fractional ages. All non-null ages are whole integers. |
| **EXEC-12** | Risk-Tier Score Overlap Count | **EXECUTED** | Score filter in $[34.0, 35.0]$ and $[65.0, 67.0]$ | Exactly 958 records in Low/Med overlap; 3,413 records in Med/High overlap. Naive cuts yield **3,252 mismatches**. |
| **EXEC-13** | Credit-Score Fractional Check | **EXECUTED** | `(df_dedup['Credit_Score'].dropna() % 1 != 0).sum()` | **0 fractional values** among all 98,680 non-null credit scores. Min=0.0, Max=999.0, 1,320 nulls. |
| **EXEC-14** | Strict Boolean Inventory | **EXECUTED** | Unique values & value counts for `Co_Applicant` and `Collateral` | Exactly 8 case/whitespace variants of 'Yes' and 'No'; 0 nulls, 0 corrupted strings. |
| **EXEC-15** | Requested-Amount Zero Count | **EXECUTED** | `(df_dedup['Loan_Amount'] == 0).sum()` | **0 records** have `Loan_Amount == 0.0`. 1,261 nulls, 35 negatives, 98,704 positives. |
| **EXEC-16** | Normalized Risk Score Assertion | **EXECUTED** | Verify `rs / 100.0` matches non-null and preserves nulls | 1,216 source nulls $\to$ 1,216 normalized nulls. Non-nulls bounded in $[0.0, 1.0]$. Max difference: 0.0. |

### 7.2 Proposed Automated Reconciliation Tests (Milestone 1 Test Plan)

| Check ID | Test Scope | Status | Execution Command / Test Assertion | Target Output / Acceptance Criteria |
|---|---|---|---|---|
| **PROP-01** | Foreign Key Integrity | *PROPOSED* | `PRAGMA foreign_key_check;` in `tests/test_etl_reconciliation.py` | Must return 0 violations after SQLite database load. |
| **PROP-02** | Clean Table Row Count | *PROPOSED* | `SELECT COUNT(*) FROM fct_loan_application` | Must equal exactly 100,000. |
| **PROP-03** | Quality Flag Assertion | *PROPOSED* | `SELECT SUM(has_invalid_financials) FROM fct_loan_application` | Must equal exactly 104. |
| **PROP-04** | Missing Sanctioned Amount Assertion | *PROPOSED* | `SELECT SUM(has_missing_sanctioned_amount) FROM fct_loan_application` | Must equal exactly 1,206 (575 Approved + 631 Rejected). |
| **PROP-05** | Decision Consistency Constraint Test | *PROPOSED* | Insert invalid `('Approved', 0)` tuple | SQLite must reject insert with `CHECK constraint failed: chk_decision_consistency`. |
| **PROP-06** | Haircut Eligible Population Assertion | *PROPOSED* | Count records matching Haircut `WHERE` clause | Must equal exactly 48,022. |
| **PROP-07** | Synthetic Data Isolation | *PROPOSED* | Query primary analytical views for synthetic column names | Must return 0 references to `disbursement_amount` or `payment_status`. |
| **PROP-08** | Transactional Rollback Test | *PROPOSED* | Inject simulated failure during test load | Database must roll back completely without partial table writes. |

---

## 8. Summary of Remaining Blockers & Pre-Implementation Plan

- **Outstanding Technical Blockers:** **ZERO.** Every blocker and gate item identified by the user has been empirically profiled against physical CSV evidence, specified with exact SQL/Python rules, and documented in this canonical specification.
- **Data Integrity Assurance:** The raw CSV file (`data/raw/kaggle_original.csv`) remains strictly read-only and immutable (size: 46,779,106 bytes). Zero application code, database files, or dependencies have been created.

### Exact Checks Requiring Execution Against Physical Database (Milestone 1 Gate)
Upon user approval to begin Milestone 1, the following concrete checks will be executed against the created SQLite database:
1. `PRAGMA foreign_key_check;` returns empty set.
2. `SELECT COUNT(*) FROM fct_loan_application;` returns `100,000`.
3. `SELECT COUNT(*) FROM dim_residence_property_location;` returns `75`.
4. `SELECT COUNT(*) FROM dim_channel;` returns `4`.
5. `SELECT COUNT(*) FROM dim_loan_purpose;` returns `5`.
6. `SELECT COUNT(*) FROM demo_synthetic_repayment_snapshot;` returns `48,596`.
7. `SELECT SUM(has_invalid_financials) FROM fct_loan_application;` returns `104`.
8. `SELECT SUM(has_missing_sanctioned_amount) FROM fct_loan_application;` returns `1,206`.
9. `SELECT COUNT(*) FROM fct_loan_application WHERE is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL;` returns `48,022`.
10. Attempting an insert with mismatched `underwriting_decision` and `is_approved` raises SQLite `IntegrityError`.
11. Pre-insertion validation test asserts that unexpected categorical values or booleans (e.g. `'UNKNOWN'`) fail immediately and abort transaction.

---

## 9. Concise Change Log

1. **Section 1 & Master Ledger:** Expanded master ledger to 9 structured items, incorporating credit score casting justification, strict boolean parsing (replacing `ELSE 0`), requested-amount zero reconciliation, evidence vs. interpretation boundaries, and normalized score consistency.
2. **Section 2.1 (Sanctioned-Amount Missingness):** Formalized nullable schema column, separate handling for rejected ($50,198$ zero, $631$ null) vs approved ($48,596$ positive, $575$ null), and distinguished recorded zero from real-world meaning.
3. **Section 2.2 (Credit-Score Profiling & Casting):** Documented empirical proof of **0 fractional credit scores** across all 98,680 non-null values ($val \% 1 == 0$), justifying integer casting without loss of precision. Range validated: $[0, 999]$.
4. **Section 2.3 (Strict Boolean Parsing):** Eliminated `ELSE 0` logic; formalized strict mapping (`'YES' -> 1`, `'NO' -> 0`, `NULL -> NULL`) with pre-insertion validation that aborts transaction on unrecognized values.
5. **Section 2.4 (Requested-Amount Zero Reconciliation):** Profiled `Loan_Amount` across decisions: verified **0 zero values** in physical source file ($1,261$ nulls, $35$ negatives, $98,704$ positives). Confirmed compatibility with `requested_loan_amount > 0` constraint. Verified 48,022 haircut population with passing programmatic assertion.
6. **Section 2.5 (Evidence vs. Interpretation):** Clarified `Default_Risk` as a source-provided categorical attribute; explicitly labeled multi-factor policy boundaries as an inferred hypothesis rather than verified committee charter fact.
7. **Section 2.6 (Normalized Score Consistency):** Formally specified `normalized_risk_score = proprietary_risk_score / 100.0`. Validated exact null preservation (1,216 nulls) and range $[0.0, 1.0]$ across all 98,784 non-null records.
8. **Section 2.7 & 2.8 (Decision Consistency, Auditable Loading, Synthetic Servicing):** Re-confirmed DDL check constraints, safe dimension loading vs strict fact loading, 104 composite flag count, requested principal basis ($99.96\%$ match), and demonstration quarantine.
9. **Section 4 (Source-to-Target Lineage):** Updated rows for `Credit_Score`, `Loan_Amount`, `Co_Applicant`, `Collateral`, `Risk_Score`, and `Default_Risk` with revised policies.
10. **Section 7 (Verification Status):** Added executed profiling checks `EXEC-13` (Credit-Score fractional check), `EXEC-14` (Strict boolean inventory), `EXEC-15` (Loan_Amount zero count), and `EXEC-16` (Normalized risk score assertion).

---

**FINAL READINESS REPORT V2 COMPLETE. STOPPING HERE.**  
*Awaiting your explicit approval of this document before beginning Milestone 1 implementation.*
