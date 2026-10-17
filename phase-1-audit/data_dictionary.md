# RiskLens AI — Data Dictionary & Column Specification
**Phase 1 Forensic Audit Deliverable**  
**Dataset Source:** `data/raw/kaggle_original.csv`  
**Dataset Dimensions:** 100,150 Rows × 67 Columns (44.61 MB)  
**Status:** Complete Forensic Audit  

---

## 1. Architectural Overview: The Two-Part Dataset Structure

Our forensic audit has confirmed that `kaggle_original.csv` is composed of **two distinct structural halves glued together horizontally**:

1. **Part 1 — Original Application & Credit Risk Inventory (Columns 1 to 36):**
   - Formatted in **Title_Case / PascalCase** (`Application_ID`, `Age`, `Annual_Income`, `Loan_Amount`, `Loan_Approved`, etc.).
   - Contains a comprehensive 36-feature loan underwriting dataset, including rich applicant demographics, assets, liabilities, bureau metrics, and underwriting decisions.
2. **Part 2 — Synthetic Relational & Repayment Extension (Columns 37 to 67):**
   - Formatted in **snake_case** (`application_id`, `customer_id`, `loan_id`, `age`, `city`, `disbursement_amount`, `due_date`, etc.).
   - Consists of cloned columns, derived mathematical scalings (`Risk_Score / 100`, `Region + '_City'`), and synthetically generated post-origination fields (`disbursement_amount`, `outstanding_amount`, `due_date`, `payment_date`, `amount_due`, `amount_paid`, `days_late`, `payment_status`).

---

## 2. Complete Column Inventory (Columns 1 – 67)

### Part 1: Primary Underwriting & Application Columns (Cols 1–36)

| # | Column Name | Inferred Type | Null Count (%) | Distinct Count | Domain / Valid Range | Business Definition | Role & Recommended Treatment |
|---|---|---|---|---|---|---|---|
| 1 | `Application_ID` | `INT64` | 0 (0.00%) | 100,000 | 500,001 – 600,000 | Unique application tracking number. | **Primary Key** for raw record. Deduplicate 150 rows. |
| 2 | `Age` | `FLOAT64` | 1,204 (1.20%) | 83 | 5.0 – 115.0 | Age of primary applicant in years. | **Customer Demographic**. 13 rows < 18 (min 5), 12 rows > 100. Filter or nullify minors. |
| 3 | `Gender` | `STRING` | 0 (0.00%) | 2 | `Male`, `Female` | Applicant self-reported gender. | **Customer Demographic**. 100% clean (Male: 58,284, Female: 41,866). |
| 4 | `Marital_Status` | `STRING` | 0 (0.00%) | 16 | `Single`, `Married`, `Divorced`, `Widowed` | Applicant legal marital status. | **Customer Demographic**. Casing and whitespace noise present (` Married`, `MARRIED`). Apply `TRIM() + INITCAP()`. |
| 5 | `Education_Level` | `STRING` | 0 (0.00%) | 16 | `High School`, `Bachelor`, `Master`, `PhD` | Highest educational attainment. | **Customer Demographic**. Casing and whitespace noise (` Bachelor`, `BACHELOR`). Apply `TRIM() + INITCAP()`. |
| 6 | `Employment_Status` | `STRING` | 0 (0.00%) | 4 | `Salaried`, `Self-Employed`, `Contract`, `Freelancer` | Nature of primary employment. | **Customer Attribute**. Canonical source for employment stability analysis. |
| 7 | `Job_Experience_Years` | `INT64` | 0 (0.00%) | 41 | 0 – 40 | Number of years in current/relevant employment. | **Customer Attribute**. 13 records violate `Job_Experience_Years <= Age - 18` due to minor age errors. |
| 8 | `Annual_Income` | `FLOAT64` | 1,295 (1.29%) | 98,822 | -$211,679.11 – $500,000.00 | Total gross annual income. | **Financial Measure**. 35 negative values (min -$211,679.11). Invert sign or set to NULL. |
| 9 | `Monthly_Income` | `FLOAT64` | 1,301 (1.30%) | 98,815 | $416.67 – $41,809.01 | Gross monthly income. | **Financial Measure**. 69.25% mismatch with `Annual_Income / 12` (max diff $35,433). Use `Annual_Income / 12` as authoritative. |
| 10 | `Credit_Score` | `FLOAT64` | 1,321 (1.32%) | 651 | 0.0 – 999.0 | Bureau credit score. | **Credit Measure**. 3,583 records outside standard US FICO range (300–850). Retain continuous score; document range. |
| 11 | `Credit_History_Years` | `FLOAT64` | 0 (0.00%) | 398 | 0.0 – 40.0 | Length of bureau credit file in years. | **Credit Measure**. 13 records exceed `Age - 18` due to minor age errors. |
| 12 | `Existing_Loans` | `INT64` | 0 (0.00%) | 12 | 0 – 11 | Count of active external loans. | **Credit Profile**. Discrete count. Median = 2, Mean = 2.01. |
| 13 | `Late_Payments_Last_2_Years` | `INT64` | 0 (0.00%) | 11 | 0 – 10 | Delinquency events in past 24 months. | **Credit Risk Measure**. Crucial underwriting feature. Discrete count (0: 41.9%, 1: 34.4%, 2: 15.9%). |
| 14 | `Loan_Amount` | `FLOAT64` | 1,265 (1.26%) | 98,851 | -$375,200.41 – $1,000,000.00 | Requested loan principal amount. | **Loan Measure**. 35 negative values (min -$375,200.41). Invert sign or set to NULL. |
| 15 | `Loan_Term_Months` | `INT64` | 0 (0.00%) | 10 | 12, 24, 36, 48, 60, 72, 84, 120, 180, 360 | Requested loan term in months. | **Loan Attribute**. Discrete standard banking amortization durations. |
| 16 | `Loan_Purpose` | `STRING` | 0 (0.00%) | 5 | `Home`, `Education`, `Vehicle`, `Personal`, `Debt Consolidation` | Intended use of loan proceeds. | **Loan Attribute**. Clean categorical distribution. Canonical source. |
| 17 | `Interest_Rate` | `FLOAT64` | 1,308 (1.31%) | 2,492 | 5.00% – 30.00% | Underwritten annual percentage rate (APR). | **Pricing Measure**. Mean = 15.02%, Median = 14.51%. Plausible commercial lending range. |
| 18 | `Debt_To_Income_Ratio` | `FLOAT64` | 1,260 (1.26%) | 8,970 | 0.00% – 95.00% | Back-end debt-to-income percentage (DTI). | **Underwriting Measure**. Mean = 24.96%. Mismatches direct monthly debt / monthly income formula on 65.5% of rows. |
| 19 | `Savings_Balance` | `FLOAT64` | 1,270 (1.27%) | 98,124 | -$62,004.75 – $872,935.06 | Liquid savings account balance. | **Asset Measure**. 35 negative values; 746 zeros. Savings cannot be negative. |
| 20 | `Checking_Balance` | `FLOAT64` | 1,194 (1.19%) | 98,284 | $0.00 – $345,655.69 | Transactional checking account balance. | **Asset Measure**. 655 zeros. Non-negative. |
| 21 | `Total_Assets` | `FLOAT64` | 1,262 (1.26%) | 98,854 | $3,619.24 – $5,000,000.00 | Net asset valuation of applicant. | **Wealth Measure**. Positively skewed wealth distribution. |
| 22 | `Total_Liabilities` | `FLOAT64` | 1,303 (1.30%) | 98,813 | $62.83 – $3,000,000.00 | Total external outstanding debts. | **Liability Measure**. Identical to `existing_debt`. |
| 23 | `Monthly_Debt_Payment` | `FLOAT64` | 1,262 (1.26%) | 96,878 | $0.00 – $17,865.16 | Total monthly debt service obligations. | **Cash Flow Measure**. 2,006 zeros. Used in DTI validation. |
| 24 | `Property_Ownership` | `STRING` | 0 (0.00%) | 17 | `Rent`, `Own`, `Mortgage`, `Other`, `Family Owned` | Collateral / Residential tenure. | **Underwriting Attribute**. Casing and leading space noise present. Apply `TRIM() + INITCAP()`. |
| 25 | `Residential_Status` | `STRING` | 0 (0.00%) | 12 | `Urban`, `Suburban`, `Rural` | Macro geographic classification. | **Geographic Dimension**. Casing/whitespace noise present. Apply `TRIM() + INITCAP()`. |
| 26 | `Dependents` | `INT64` | 0 (0.00%) | 7 | 0 – 6 | Number of financial dependents. | **Customer Demographic**. Discrete count (0: 26.1%, 1: 35.3%, 2: 23.5%, 3: 10.4%, 4+: 4.7%). |
| 27 | `Co_Applicant` | `STRING` | 0 (0.00%) | 8 | `Yes`, `No` | Flag indicating co-borrower presence. | **Underwriting Attribute**. Casing/whitespace noise (` Yes`, `YES`, `No`, `NO`). Clean to Boolean. |
| 28 | `Collateral` | `STRING` | 0 (0.00%) | 8 | `Yes`, `No` | Flag indicating pledged physical collateral. | **Underwriting Attribute**. Casing/whitespace noise. Clean to Boolean. |
| 29 | `Application_Channel` | `STRING` | 0 (0.00%) | 16 | `Online`, `Branch`, `Mobile App`, `Agent` | Origination touchpoint. | **Operational Dimension**. Casing/whitespace noise (` Online`, `ONLINE`). Clean to 4 standard channels. |
| 30 | `Region` | `STRING` | 0 (0.00%) | 4 | `West`, `Central`, `South`, `East` | Sales & underwriting operational region. | **Geographic Dimension**. Clean 4-level dimension. Genuine source for `city`. |
| 31 | `Bank_Account_Age_Years` | `FLOAT64` | 0 (0.00%) | 398 | 0.0 – 40.0 | Tenure of primary banking relationship. | **Relationship Measure**. 3,281 records exceed `Age - 18`. Authoritative source for `account_tenure_months`. |
| 32 | `Previous_Loan_Status` | `STRING` | 0 (0.00%) | 16 | `Paid Off`, `Active`, `No Previous Loan`, `Defaulted` | Performance on prior bureau credit facilities. | **Credit History Attribute**. Casing/whitespace noise. Note: Refers to *past* loans, NOT current application! |
| 33 | `Risk_Score` | `FLOAT64` | 1,221 (1.22%) | 7,651 | 0.00 – 100.00 | Internal credit scoring model (0=Safest, 100=Riskiest). | **Risk Measure**. Mean = 58.74, Median = 58.66. Ground truth for `default_probability`. |
| 34 | `Default_Risk` | `STRING` | 0 (0.00%) | 12 | `Low`, `Medium`, `High` | Underwriting risk tier segmentation. | **Risk Dimension**. Casing/whitespace noise. Aligns with `Risk_Score` (Low: 0-35, Med: 34-67, High: 65-100). |
| 35 | `Approved_Amount` | `FLOAT64` | 1,209 (1.21%) | 47,078 | $0.00 – $995,598.11 | Loan amount approved by underwriting. | **Loan Measure**. Exactly 0.0 for all non-null Rejected applications. <= `Loan_Amount` for Approved loans. |
| 36 | `Loan_Approved` | `STRING` | 0 (0.00%) | 8 | `Approved`, `Rejected` | Final underwriting credit origination decision. | **Loan Status Dimension**. Casing/whitespace noise (` Approved`, `REJECTED`). Clean to binary `Approved`/`Rejected`. |

---

### Part 2: Relational & Synthetic Extension Columns (Cols 37–67)

| # | Column Name | Inferred Type | Null Count (%) | Distinct Count | Generation Method / Formula | Forensic Findings & Limitations | Role in Proposed Model |
|---|---|---|---|---|---|---|---|
| 37 | `application_id` | `INT64` | 0 (0.00%) | 100,000 | `Application_ID` | 100% redundant exact clone of `Application_ID`. | Drop redundant duplicate. |
| 38 | `customer_id` | `STRING` | 0 (0.00%) | 100,000 | `'CUST-' || Application_ID` | Artificially synthesized 1:1 ID. No multi-application customers exist. | Surrogate Customer PK in SQL schema. |
| 39 | `loan_id` | `STRING` | 0 (0.00%) | 100,000 | `'LOAN-' || Application_ID` | Artificially synthesized 1:1 ID. Exactly one loan per application. | Surrogate Loan PK in SQL schema. |
| 40 | `age` | `FLOAT64` | 1,204 (1.20%) | 83 | `Age` | 100% redundant exact clone of `Age`. | Drop redundant duplicate. |
| 41 | `gender` | `STRING` | 0 (0.00%) | 2 | `Gender` | 100% redundant exact clone of `Gender`. | Drop redundant duplicate. |
| 42 | `income` | `FLOAT64` | 1,295 (1.29%) | 98,822 | `Annual_Income` | 100% redundant exact clone of `Annual_Income`. | Drop redundant duplicate. |
| 43 | `employee_type` | `STRING` | 0 (0.00%) | 4 | `Employment_Status` | 100% redundant exact clone of `Employment_Status`. | Drop redundant duplicate. |
| 44 | `city` | `STRING` | 0 (0.00%) | 4 | `Region || '_City'` | **Synthetic Pseudo-City**: 100% generated from `Region` (`West_City`, etc.). | Document as synthetic; use `Region` instead. |
| 45 | `credit_score` | `FLOAT64` | 1,321 (1.32%) | 651 | `Credit_Score` | 100% redundant exact clone of `Credit_Score`. | Drop redundant duplicate. |
| 46 | `existing_debt` | `FLOAT64` | 1,303 (1.30%) | 98,813 | `Total_Liabilities` | 100% redundant exact clone of `Total_Liabilities`. | Drop redundant duplicate. |
| 47 | `account_tenure_months` | `INT64` | 0 (0.00%) | 398 | `round(Bank_Account_Age_Years * 12)` | Direct mathematical conversion of account age to months. | Retain as integer months in Customer table. |
| 48 | `loan_amount` | `FLOAT64` | 1,265 (1.26%) | 98,851 | `Loan_Amount` | 100% redundant exact clone of `Loan_Amount`. | Drop redundant duplicate. |
| 49 | `loan_type` | `STRING` | 0 (0.00%) | 5 | `Loan_Purpose` | 100% redundant exact clone of `Loan_Purpose`. | Drop redundant duplicate. |
| 50 | `interest_rate` | `FLOAT64` | 1,308 (1.31%) | 2,492 | `Interest_Rate` | 100% redundant exact clone of `Interest_Rate`. | Drop redundant duplicate. |
| 51 | `loan_term` | `INT64` | 0 (0.00%) | 10 | `Loan_Term_Months` | 100% redundant exact clone of `Loan_Term_Months`. | Drop redundant duplicate. |
| 52 | `loan_status` | `STRING` | 0 (0.00%) | 8 | `Loan_Approved` | 100% redundant exact clone of `Loan_Approved`. | Drop redundant duplicate. |
| 53 | `approved_amount` | `FLOAT64` | 1,209 (1.21%) | 47,078 | `Approved_Amount` | 100% redundant exact clone of `Approved_Amount`. | Drop redundant duplicate. |
| 54 | `disbursement_amount` | `FLOAT64` | 577 (0.58%) | 47,622 | `approved_amount * Uniform(0.85, 1.00)` | Synthetic metric; 0 for Rejected; 10 decimal precision on Approved. | Round to `NUMERIC(15,2)` in Loan Disbursement. |
| 55 | `outstanding_amount` | `FLOAT64` | 0 (0.00%) | 47,622 | `disbursement_amount * Uniform(0.00, 1.00)` | Synthetic metric; 0 for Rejected; 10 decimal precision on Approved. | Round to `NUMERIC(15,2)` in Loan Disbursement. |
| 56 | `previous_defaults` | `INT64` | 0 (0.00%) | 11 | `Late_Payments_Last_2_Years` | 100% redundant exact clone of `Late_Payments_Last_2_Years`. | Drop redundant duplicate. |
| 57 | `payment_histories` | `STRING` | 0 (0.00%) | 16 | `Previous_Loan_Status` | 100% redundant exact clone of `Previous_Loan_Status`. | Drop redundant duplicate. |
| 58 | `risk_score` | `FLOAT64` | 1,221 (1.22%) | 7,651 | `Risk_Score` | 100% redundant exact clone of `Risk_Score`. | Drop redundant duplicate. |
| 59 | `risk_category` | `STRING` | 0 (0.00%) | 12 | `Default_Risk` | 100% redundant exact clone of `Default_Risk`. | Drop redundant duplicate. |
| 60 | `default_probability` | `FLOAT64` | 1,221 (1.22%) | 7,651 | `Risk_Score / 100` | **Trivial linear rescale**. Not a calibrated probability model. | Retain as normalized probability (0.0 to 1.0). |
| 61 | `assessment_id` | `STRING` | 0 (0.00%) | 100,000 | `'ASSESS-' || Application_ID` | Artificially synthesized 1:1 ID. | Primary Key for Risk Assessment table. |
| 62 | `due_date` | `STRING` | 0 (0.00%) | 1,489 | Random calendar dates (2022–2026) | **Contradiction**: Present for Rejected loans! 20 rows contain literal `'not_a_date'`. | Clean to DATE; set NULL for Rejected loans. |
| 63 | `payment_date` | `STRING` | 0 (0.00%) | 1,514 | Random dates >= `due_date` | **Contradiction**: Present for Rejected loans! 20 rows contain literal `'31/31/2025'`. | Clean to DATE; set NULL for Rejected loans. |
| 64 | `amount_due` | `FLOAT64` | 1,407 (1.40%) | 97,472 | `Loan_Amount / Loan_Term_Months` | **Contradiction**: Generated for 50,153 Rejected loans! Ignores interest rate. | Retain for Approved loans only; NULL for Rejected. |
| 65 | `amount_paid` | `FLOAT64` | 1,366 (1.36%) | 98,735 | `amount_due * random_multiplier` | **Contradiction**: Generated for 49,464 Rejected loans! Multiplier based on status. | Retain for Approved loans only; NULL for Rejected. |
| 66 | `days_late` | `FLOAT64` | 1,408 (1.41%) | 82 | `max(0, payment_date - due_date)` | **Contradiction**: Generated for Rejected loans! Exactly matches date difference. | Retain for Approved loans only; NULL for Rejected. |
| 67 | `payment_status` | `STRING` | 0 (0.00%) | 9 | `Partial` (85.1%), `Paid` (14.0%), `Missed` (2 rows) | **Contradiction**: Assigned to Rejected loans! Severe class imbalance (`Missed` has only 2 rows). | Retain for Approved loans only; NULL for Rejected. |

---

## 3. High-Value Underwriting Columns Omitted from User's Initial Entity List

The initial project specifications in Step 11 defined target fields for 5 entities, but omitted **17 highly valuable columns** that exist in Part 1. These columns must be retained in our data warehouse schema to ensure deep business intelligence capabilities:

1. `Marital_Status` — Essential for household stability and co-borrower credit modeling.
2. `Education_Level` — Key socio-economic predictor in credit scoring.
3. `Job_Experience_Years` — Core underwriting feature for employment longevity.
4. `Monthly_Income` — Cash flow metric used alongside annual gross income.
5. `Credit_History_Years` — Bureau file depth (thin-file vs seasoned credit profile).
6. `Existing_Loans` — Active debt load count.
7. `Debt_To_Income_Ratio` — Authoritative regulatory solvency metric (DTI).
8. `Savings_Balance` — Liquid cash reserve metric for emergency liquidity assessment.
9. `Checking_Balance` — Operating account liquidity metric.
10. `Total_Assets` — Net asset coverage / borrower net worth.
11. `Monthly_Debt_Payment` — Explicit monthly debt servicing burden.
12. `Property_Ownership` — Real estate collateral indicator (Rent, Own, Mortgage).
13. `Residential_Status` — Geographic area stability (Urban, Suburban, Rural).
14. `Dependents` — Household expenditure burden indicator.
15. `Co_Applicant` — Secondary credit guarantor flag.
16. `Collateral` — Secured vs unsecured loan classification.
17. `Application_Channel` — Sales performance and acquisition channel analytics (`Online`, `Branch`, `Mobile App`, `Agent`).
