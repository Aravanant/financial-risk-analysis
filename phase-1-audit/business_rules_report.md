# RiskLens AI — Business Rules & Financial Consistency Report
**Phase 1 Forensic Audit Deliverable**  
**Dataset Source:** `data/raw/kaggle_original.csv`  
**Dataset Dimensions:** 100,150 Rows × 67 Columns (44.61 MB)  
**Status:** Complete Forensic Audit  

---

## 1. Executive Summary & Verification Matrix

We systematically tested **15 fundamental financial, operational, and mathematical business rules** across the entire 100,150-record dataset. Each rule was classified as either a **Hard Validation Failure** (breaking relational or financial integrity) or an **Analytical Warning** (indicating noise, synthetic generation, or uncalibrated modeling).

| Rule ID | Business Rule Tested | Target Scope | Violation Count | Violation % | Severity | Classification |
|---|---|---|---|---|---|---|
| **BR-01** | `Monthly_Income == Annual_Income / 12` | Financial Cash Flow | 67,573 / 97,575 | **69.25%** | MEDIUM | Warning |
| **BR-02** | `Approved_Amount == 0` for Rejected Loans | Underwriting Logic | 0 / 49,698 non-null | **0.00%** | CRITICAL | **Confirmed Valid** |
| **BR-03** | `Approved_Amount <= Loan_Amount` for Approved Loans | Underwriting Sanction | 0 / 47,077 non-null | **0.00%** | CRITICAL | **Confirmed Valid** |
| **BR-04** | `disbursement_amount == 0` for Rejected Loans | Fund Disbursement | 0 / 50,330 non-null | **0.00%** | CRITICAL | **Confirmed Valid** |
| **BR-05** | `outstanding_amount == 0` for Rejected Loans | Loan Accounting | 0 / 50,907 | **0.00%** | CRITICAL | **Confirmed Valid** |
| **BR-06** | **Repayment Fields Must Be NULL for Rejected Loans** | Portfolio Accounting | 50,907 / 50,907 | **100.00%** | CRITICAL | **Hard Failure** |
| **BR-07** | `days_late == max(0, payment_date - due_date)` | Calendar Accounting | 40 / 98,742 | **0.04%** | MEDIUM | **Confirmed Valid** |
| **BR-08** | `payment_date >= due_date` (Chronological Order) | Temporal Integrity | 0 / 98,742 valid dates | **0.00%** | HIGH | **Confirmed Valid** |
| **BR-09** | Valid Calendar Dates in `due_date` and `payment_date` | Temporal Integrity | 40 / 100,150 | **0.04%** | HIGH | **Hard Failure** |
| **BR-10** | `account_tenure_months == round(Bank_Account_Age_Years * 12)` | Data Transformation | 0 / 100,150 | **0.00%** | LOW | **Confirmed Valid** |
| **BR-11** | `default_probability == Risk_Score / 100` | Risk Modeling | 0 / 98,929 non-null | **0.00%** | MEDIUM | **Confirmed Valid** |
| **BR-12** | `Credit_History_Years <= Age - 18` | Legal Demographics | 13 / 98,946 | **0.01%** | HIGH | **Hard Failure** |
| **BR-13** | `Job_Experience_Years <= Age - 18` | Legal Demographics | 13 / 98,946 | **0.01%** | HIGH | **Hard Failure** |
| **BR-14** | `Bank_Account_Age_Years <= Age - 18` | Demographic Logic | 3,281 / 98,946 | **3.32%** | MEDIUM | Warning |
| **BR-15** | Non-Negative Balances & Principals (`Income`, `Loan`, `Savings`) | Financial Baseline | 105 / 100,150 | **0.10%** | CRITICAL | **Hard Failure** |

---

## 2. In-Depth Business Rule Audit

### BR-01: Monthly Income vs Annual Income Divided by 12
- **Business Rule:** An applicant's reported monthly gross cash flow should equal annual income divided by 12 (within standard rounding tolerances of ±$0.01).
- **Audit Findings:**
  - Valid comparisons evaluated: 97,575 records where both fields were non-null.
  - Exactly matching records (diff < $0.01): **30,002 (30.75%)**.
  - Mismatched records: **67,573 (69.25%)**.
  - Maximum observed discrepancy: **$35,433.93**. Mean discrepancy: **$48.35**.
- **Representative Examples:**
  - Row 1: `Annual_Income` = $38,969.89, `Monthly_Income` = $3,214.61 (Calculated: $3,247.49, Diff: -$32.88).
  - Row 2: `Annual_Income` = $93,739.02, `Monthly_Income` = $7,908.86 (Calculated: $7,811.59, Diff: +$97.27).
- **Explanation:** In synthetic or survey data, monthly income is frequently gathered as a distinct self-reported estimate or perturbed with a random noise factor (e.g. including irregular bonuses or overtime).
- **Recommendation:** Adopt `Annual_Income` as the authoritative underwriting ground truth, and calculate standardized monthly income as `Annual_Income / 12.0` in the database.

---

### BR-02 & BR-03: Underwriting Sanction Limits (Approved Amount vs Loan Amount)
- **Business Rule:**
  1. A rejected loan must never receive an approved amount (`Approved_Amount == 0`).
  2. An approved loan must never be sanctioned for more than the requested amount (`Approved_Amount <= Loan_Amount`).
- **Audit Findings:**
  - **Rejected Loans:** 49,698 non-null records inspected. **100.0% had `Approved_Amount == 0.0`**. (1,209 records were NULL).
  - **Approved Loans:** 47,077 non-null records inspected.
    - `Approved_Amount == Loan_Amount`: **12,455 records (26.5%)** (100% full approval).
    - `Approved_Amount < Loan_Amount`: **34,622 records (73.5%)** (Haircut / partial approval). Mean approval ratio: **82.4%** (range: 20% to 100%).
    - `Approved_Amount > Loan_Amount`: **0 records (0.00%)**.
- **Conclusion:** **Confirmed Valid**. Underwriting sanction logic strictly follows banking rules.

---

### BR-04 & BR-05: Loan Disbursement & Outstanding Balances
- **Business Rule:**
  1. Unapproved loans must have zero disbursement and zero outstanding balance.
  2. Disbursed loans must have an outstanding balance less than or equal to the disbursed amount.
- **Audit Findings:**
  - **Rejected Loans:** 100% had `disbursement_amount == 0` and `outstanding_amount == 0`.
  - **Approved Loans:**
    - `disbursement_amount / approved_amount`: Ranges strictly from **0.8500 to 0.9999** (Mean: 0.9247, Std: 0.0434). This reveals a textbook `Uniform(0.85, 1.00)` random generation function.
    - Precision: Both fields are stored with **10 to 14 decimal places** (e.g., `$36,114.3516959484`), a mathematical artifact of floating-point generation.
- **Recommendation:** In Phase 2 database loading, round all financial balance fields to standard two-decimal banking currency: `ROUND(disbursement_amount, 2)::NUMERIC(15,2)`.

---

### BR-06: Repayment Fields on Rejected Loans (CRITICAL ANOMALY)
- **Business Rule:** An applicant whose loan application was **Rejected** was never issued funds; therefore, they cannot have an amortization schedule, a monthly due date, an amount due, an amount paid, or a repayment status.
- **Audit Findings:**
  - Total Rejected Applications: **50,907**.
  - Rejected applications with non-null `due_date`: **50,907 (100.0%)**.
  - Rejected applications with non-null `payment_date`: **50,907 (100.0%)**.
  - Rejected applications with non-null `amount_due`: **50,153 (98.5%)**.
  - Rejected applications with non-null `amount_paid`: **50,166 (98.5%)**.
  - Rejected applications with `amount_paid > 0`: **49,464 (97.2%)**!
  - Rejected applications classified as `payment_status == 'Paid'`: **7,295**!
  - Rejected applications classified as `payment_status == 'Partial'`: **43,610**!
- **Representative Example (Row 0 / App ID 512257):**
  - Application Status: `Loan_Approved = 'Rejected'`
  - Sanction Amounts: `Approved_Amount = 0`, `disbursement_amount = 0`, `outstanding_amount = 0`
  - Repayment Data: `due_date = '2022-07-01'`, `payment_date = '2022-07-01'`, `amount_due = $4,386.98`, `amount_paid = $2,173.64`, `payment_status = 'Partial'`
- **Forensic Diagnosis:**
  The creator of the dataset generated repayment columns across the entire CSV table unconditionally, calculating `amount_due = Loan_Amount / Loan_Term_Months` for every single row, completely ignoring the `Loan_Approved` flag!
- **Business Impact:**
  If an analyst includes rejected loans in repayment or collection analysis, portfolio collection rates and loss metrics will be completely corrupted.
- **Actionable Remediation for Phase 2:**
  In the SQL transformation layer, **strictly set all repayment fields to NULL for any application where `loan_status == 'Rejected'`**, or model repayments strictly in a separate `fact_repayment_installment` table containing only approved and disbursed loans (49,243 rows).

---

### BR-07 & BR-08: Temporal Consistency (Dates & Days Late)
- **Business Rule:**
  1. `payment_date` must occur on or after `due_date` (no negative days late).
  2. `days_late` must equal the exact calendar day difference `payment_date - due_date`.
- **Audit Findings:**
  - Valid parseable dates: 98,742 records.
  - Records where `payment_date < due_date`: **0 records (0.00%)**. Payments are never made early in this dataset.
  - Records where `days_late == (payment_date - due_date).days`: **98,702 / 98,742 (99.96%)**.
  - Discrepancies: 40 records (caused by the 20 `'not_a_date'` and 20 `'31/31/2025'` sentinel strings).
- **Conclusion:** **Confirmed Valid** across all parseable records. The `days_late` column was directly derived as `payment_date - due_date`.

---

### BR-09: Malformed Date Strings (Sentinel Injections)
- **Business Rule:** All temporal fields must conform to standard ISO-8601 calendar date formats (`YYYY-MM-DD`).
- **Audit Findings:**
  1. `due_date`: Exactly **20 records** contain the literal text string `"not_a_date"`.
  2. `payment_date`: Exactly **20 records** contain the impossible calendar date `"31/31/2025"` (Month 31, Day 31).
  3. Overlap: The 20 bad due dates and 20 bad payment dates occur in 40 completely separate rows.
- **Forensic Diagnosis:**
  These values represent intentional data quality traps injected into the dataset to test whether data engineering pipelines apply robust validation.
- **Actionable Remediation:**
  Convert both `"not_a_date"` and `"31/31/2025"` to `NULL` before casting to `DATE` data types in PostgreSQL.

---

### BR-10 & BR-11: Cloned & Scaled Columns
- **BR-10 (`account_tenure_months` vs `Bank_Account_Age_Years`):**
  - Formula: `round(Bank_Account_Age_Years * 12)`.
  - Result: **100.0% exact match** across all 100,150 rows.
- **BR-11 (`default_probability` vs `Risk_Score`):**
  - Formula: `Risk_Score / 100.0`.
  - Result: **100.0% exact match** across all 98,929 non-null rows.
- **Conclusion:** `default_probability` is not a machine-learning score; it is a linear rescale of `Risk_Score`.

---

### BR-12, BR-13, BR-14: Demographic Plausibility vs Age
- **Business Rule:** Legal contracting age in lending requires `Age >= 18`. Consequently, credit history duration, job experience, and bank tenure cannot exceed `Age - 18`.
- **Audit Findings:**
  - **Minors in Dataset (`Age < 18`):** Exactly **13 records** have ages between 5.0 and 12.0 years.
    - Example: App ID 537401 — Age 5.0, Job Experience 24 years, Credit History 21.5 years, Annual Income $60,768, Requested Loan $273,907!
  - **Centenarians in Dataset (`Age > 100`):** Exactly **12 records** have ages between 101.0 and 115.0 years.
  - **Account Tenure vs Age:** Exactly **3,281 records** have `Bank_Account_Age_Years > Age - 18`.
- **Remediation:** Minors (< 18) must be flagged and filtered from production demographic dashboards.

---

### BR-15: Negative Balances & Principal Values
- **Business Rule:** Loan amount requests, annual gross income, and savings account balances cannot be negative.
- **Audit Findings:**
  - Negative `Annual_Income`: **35 records** (min -$211,679.11).
  - Negative `Loan_Amount`: **35 records** (min -$375,200.41).
  - Negative `Savings_Balance`: **35 records** (min -$62,004.75).
  - Intersection: The 35 rows for each column are mutually exclusive (total of 105 distinct affected rows).
- **Remediation:** Check whether signs were accidentally inverted; if so, apply `ABS()`, or set to `NULL` with an invalidity flag.

---

## 3. Repayment Credibility & True Default Outcome Forensic Audit

### 3.1 Does a True Historical Default Outcome Exist?
In credit risk modeling, a genuine default flag represents a confirmed post-origination loss event (e.g. 90+ days past due, charge-off, or bankruptcy).

We audited all potential default indicators in the dataset:
1. `Loan_Approved`: Measures **pre-origination underwriting rejection**, NOT post-origination default.
2. `Default_Risk` / `risk_category`: Represents **pre-application risk tiering** (Low, Medium, High) based on credit bureau score, not an observed default event.
3. `Previous_Loan_Status` / `payment_histories`: Refers to **prior completed credit facilities** from the applicant's credit bureau file (`Paid Off`, `Active`, `No Previous Loan`, `Defaulted`). `Defaulted` (8,940 records) indicates that the borrower defaulted on an *earlier* loan with another lender in the past, not on the current loan!
4. `previous_defaults`: 100% duplicate of `Late_Payments_Last_2_Years` (count of past delinquencies).
5. `payment_status`: Only contains `Paid` (14.0%), `Partial` (85.1%), and `Missed` (**exactly 2 records out of 100,150!**).

### 3.2 Formal Risk & Repayment Classification Matrix

| Concept | Actual Dataset Column | Confirmed Finding | Credibility Classification |
|---|---|---|---|
| **Loan Underwriting Decision** | `Loan_Approved` | Authentic origination binary flag (Approved vs Rejected). | **Confirmed** |
| **Applicant Risk Score** | `Risk_Score` | Proprietary underwriter scoring index (0–100). | **Confirmed** |
| **Bureau Past Default History** | `Previous_Loan_Status` | Applicant's past credit history; NOT current loan performance. | **Confirmed** |
| **Current Loan Repayment** | `payment_status`, `amount_due` | Flat, synthetically generated single-installment record. | **Plausible (Synthetic)** |
| **True Current Loan Default** | **None** | **No confirmed post-origination default flag exists.** | **UNKNOWN / ABSENT** |

> [!WARNING]
> **Definitive Portfolio Modeling Boundary:**  
> It is analytically invalid to train a "Loan Default Prediction Model" on this dataset because **no observed loan default target variable exists**. Any machine learning model developed must be framed strictly as an **Underwriting Approval / Rejection Classifier** or a **Risk Tier Segmentation Model**.
