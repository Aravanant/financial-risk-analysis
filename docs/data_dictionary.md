# RiskLens AI — Data Dictionary & Analytical Methodology

This document provides a comprehensive reference for all attributes, semantic cleaning rules, audit flags, and financial metric definitions utilized throughout RiskLens AI.

---

## 1. Source to Target Column Mapping

| Source Raw Column | Cleaned Warehouse Column | Target Table | Type | Cleaning & Mapping Rule | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Application_ID` | `application_id` | `fct_loan_application` | `INTEGER PRIMARY KEY` | Unchanged; strictly validated unique identifier. | Primary loan application key. |
| *(File row ordinal)* | `source_row_ordinal` | `fct_loan_application` | `INTEGER` | 1-indexed row position in raw source CSV. | Physical file order tracking. |
| `Age` | `age` | `fct_loan_application` | `INTEGER` | Nullified if `< 18` or `> 100`. Flagged via `has_invalid_age`. | Borrower chronological age. |
| `Gender` | `gender` | `fct_loan_application` | `TEXT` | Trimmed, capitalized (`Male`, `Female`, `Other`). | Self-reported gender. |
| `Marital_Status` | `marital_status` | `fct_loan_application` | `TEXT` | Trimmed, standardized title case. | Marital status. |
| `Education_Level` | `education_level` | `fct_loan_application` | `TEXT` | Validated against educational hierarchy. | Highest educational attainment. |
| `Employment_Status` | `employment_status` | `fct_loan_application` | `TEXT` | Trimmed, validated against known categories. | Employment status category. |
| `Annual_Income` | `annual_income` | `fct_loan_application` | `REAL` | Nullified if `< 0`. Flagged via `has_invalid_annual_income`. | Pre-tax annual income in CU. |
| `Savings_Account_Balance` | `savings_balance` | `fct_loan_application` | `REAL` | Nullified if `< 0`. Flagged via `has_invalid_savings_balance`. | Verified liquid savings in CU. |
| `Loan_Amount` | `requested_loan_amount` | `fct_loan_application` | `REAL` | Nullified if `Loan_Amount <= 0`. Flagged via `has_invalid_loan_amount`. | Principal requested by applicant in CU. |
| `Approved_Amount` | `sanctioned_approved_amount`| `fct_loan_application` | `REAL` | Preserved as `0.0` for rejected loans. Preserved as `NULL` if missing. | Principal sanctioned by credit committee in CU. |
| `Loan_Approved` | `underwriting_decision` | `fct_loan_application` | `TEXT` | Standardized to `'Approved'` or `'Rejected'`. | Final credit decision. |
| `Loan_Approved` | `is_approved` | `fct_loan_application` | `INTEGER` | Derived: `1` for Approved, `0` for Rejected. Checked by constraint. | Boolean credit decision indicator. |
| `Loan_Purpose` | `purpose_id` | `fct_loan_application` | `INTEGER` | Trimmed, title-cased, mapped to conformed `dim_loan_purpose`. | Foreign key to loan purpose dimension. |
| `Loan_Channel` | `channel_id` | `fct_loan_application` | `INTEGER` | Standardized, mapped to conformed `dim_channel`. | Foreign key to origination channel. |
| `Credit_Score` | `bureau_credit_score` | `fct_loan_application` | `INTEGER` | Validated integer in range `[0, 999]`. Preserved `NULL` if missing. | External bureau credit score. |
| `Risk_Score` | `proprietary_risk_score`| `fct_loan_application` | `REAL` | Numeric score in `[0.0, 100.0]`. Preserved `NULL` if missing. | Internal underwriting scorecard (0–100). |
| `Risk_Score` | `normalized_risk_score` | `fct_loan_application` | `REAL` | Derived: `proprietary_risk_score / 100.0`. | Rescaled score in `[0.0, 1.0]`. |
| `Default_Risk` | `risk_tier` | `fct_loan_application` | `TEXT` | Standardized to `'Low'`, `'Medium'`, or `'High'`. | Source-assigned categorical risk bucket. |

---

## 2. NULL Semantics vs. Recorded Zero (`0.0`)

Credit risk analytics requires distinguishing between missing data and genuine zero balances:

1. **Rejected Application Sanctions (`0.00 CU`):**
   - **50,198** rejected applications have recorded `0.00` in the source data.
   - A recorded zero is an observed credit outcome: the application was rejected, and zero funds were disbursed. These zeros are preserved.
2. **Missing Sanction Amounts (`NULL`):**
   - **575** approved applications have missing sanction amounts in source.
   - **631** rejected applications have blank/missing sanction fields.
   - These **1,206 records** are preserved strictly as `NULL`. Imputing zeros onto approved applications would distort credit metrics and skew risk scorecards.
3. **Missing Requested Amounts (`NULL`):**
   - **1,301** applications lack a valid requested loan amount (1,299 blank/null in source + 2 non-positive entries nullified during cleaning).

---

## 3. Data Cleaning Rules & Audit Flags

| Audit Flag Column | Target Condition in Source Data | Action Taken | Flagged Rows |
| :--- | :--- | :--- | :---: |
| `has_invalid_annual_income` | `Annual_Income < 0` | Replaced with `NULL` | 27 |
| `has_invalid_loan_amount` | `Loan_Amount <= 0` | Replaced with `NULL` | 2 |
| `has_invalid_savings_balance` | `Savings_Account_Balance < 0` | Replaced with `NULL` | 76 |
| `has_invalid_age` | `Age < 18 OR Age > 100` | Replaced with `NULL` | 25 |
| `has_invalid_financials` | Row-level `OR` across income, loan, and savings flags | Flagged as composite invalid | **104** |

*Overlap Note:* Application `530545` triggered both `has_invalid_loan_amount` and `has_invalid_savings_balance`. Therefore:
$$27 + 2 + 76 - 1 = \mathbf{104\text{ unique applications with invalid financial records}}$$

Negative financial balances are never converted with `ABS()` because a negative savings or loan amount indicates a recording anomaly or software glitch. Silent absolute-value conversions risk distorting portfolio leverage calculations.

---

## 4. Underwriting Haircut Methodology

### 4.1 Definition & Objective
In credit origination, a **haircut** represents the conservative reduction applied by underwriters between the principal an applicant requested and the principal sanctioned for disbursement:

$$\text{Haircut Amount (CU)} = \text{Eligible Requested Amount} - \text{Eligible Sanctioned Amount}$$
$$\text{Aggregate Haircut Rate (\%)} = \left( 1 - \frac{\sum \text{Eligible Sanctioned Amount}}{\sum \text{Eligible Requested Amount}} \right) \times 100$$

### 4.2 Haircut Eligibility Criteria
An application is haircut-eligible if and only if it meets all three conditions:
1. `is_approved = 1` (application was approved by credit committee)
2. `requested_loan_amount > 0` (applicant requested a positive, verified principal amount)
3. `sanctioned_approved_amount IS NOT NULL` (underwriters recorded a sanctioned credit facility)

**Eligible Cohort Size:** Exactly **48,022 applications**.

### 4.3 Exclusion Ledger & Mutually Exclusive Cohorts

A total of **51,978 applications** are excluded from haircut calculations. Every application is classified into exactly one mutually exclusive cohort:

| Mutually Exclusive Exclusion Cohort | Application Count | Percentage | Accounting Rationale |
| :--- | :---: | :---: | :--- |
| **1. Rejected Applications** | 50,829 | 50.83% | Applications denied credit. No sanction haircut applies. |
| **2. Approved — Missing Sanction Only** | 565 | 0.57% | Approved with valid requested loan, but sanction amount is `NULL`. |
| **3. Approved — Invalid/Missing Request Only** | 574 | 0.57% | Approved with valid recorded sanction, but requested loan is `NULL` or $\le 0$. |
| **4. Approved — Both Conditions (Dual Exclusion)** | 10 | 0.01% | Approved with both requested and sanctioned amounts missing/invalid. |
| **Total Excluded Applications** | **51,978** | **51.98%** | $50,829 + 565 + 574 + 10 = 51,978$ |
| **Haircut-Eligible Approved Population** | **48,022** | **48.02%** | Approved loans meeting all 3 eligibility criteria |
| **Total Portfolio Evaluated** | **100,000** | **100.00%** | $48,022 + 51,978 = 100,000$ (Zero duplication) |

*Gross Condition Counts (with overlap):*
- Gross Approved Missing Sanction: $565 + 10 = \mathbf{575}$
- Gross Approved Missing/Invalid Request: $574 + 10 = \mathbf{584}$
- Unique Approved Exclusions: $575 + 584 - 10 = \mathbf{1,149}$

### 4.4 Methodological Distinction: Sum of Amounts vs. Average of Rates
The aggregate portfolio haircut rate (**20.3155%**, displayed as **20.32%**) is calculated from the aggregate financial sums:
$$\text{Aggregate Rate} = \frac{1,366,702,750.08\text{ CU}}{6,727,376,919.78\text{ CU}} \times 100 = 20.315494\%$$
Naively averaging the 8 purpose-level haircut percentages produces **20.68%**. Averaging rates across categories is mathematically invalid in financial reporting because it treats small volume categories (such as Car, 349.6M CU) with equal weight to large volume categories (such as Education, 924.6M CU).

---

## 5. Currency Unit Notation (CU)
Throughout RiskLens AI, currency figures are explicitly labeled with the suffix **CU (Currency Units)**. 

Because the source dataset does not specify an authoritative sovereign currency and contains synthetic modeling attributes, converting or labeling amounts as USD, EUR, or INR would be an unverified assumption.

---

## 6. Scorecard & Modeling Disclosures
- **Proprietary Risk Score:** The `proprietary_risk_score` (and raw `Risk_Score`) is an **uncalibrated scorecard (0–100 scale)**. It is **not** a calibrated Probability of Default (PD).
- **Default_Risk Tiers:** The `Low`, `Medium`, and `High` buckets represent categorical risk bands provided in the source dataset.
- **Causality:** High-approval channels (such as Online at 49.3%) versus lower-approval channels (such as Agent at 49.0%) represent descriptive portfolio distributions, not causal evidence of channel bias.
