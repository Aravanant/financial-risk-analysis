# RiskLens AI — Business Questions & KPI Analytical Framework
**Phase 1 Forensic Audit Deliverable**  
**Dataset Source:** `data/raw/kaggle_original.csv`  
**Dataset Dimensions:** 100,150 Rows × 67 Columns (44.61 MB)  
**Status:** Complete Forensic Audit  

---

## 1. Analytical Scope & Ground Rules

Based on our forensic audit, this framework outlines the **high-value business intelligence, portfolio risk, and underwriting analytics** that can be legitimately supported by the dataset.

> [!IMPORTANT]
> **Strict Analytical Guardrails:**
> 1. **No True Loan Default Modeling:** Because no post-origination default event is tracked, analyses must focus on **Underwriting Approval/Rejection Dynamics**, **Bureau Risk Profiling**, and **Synthetic Delinquency Indicators**.
> 2. **Repayment Isolation:** Any repayment metrics (`amount_due`, `amount_paid`, `days_late`, `payment_status`) must be restricted strictly to **Approved and Disbursed Loans**.
> 3. **Macro-Regional Scope:** Geographic analytics must use the 4 authentic macro-regions (`Region`: West, Central, South, East) rather than the pseudo-attribute `city`.
> 4. **Deduplication Dependency:** All KPI calculations must execute on the deduplicated population of **100,000 distinct applications**.

---

## 2. Core Business Analysis Questions (Supported by Evidence)

### Question 1: Underwriting Approval Velocity & Rejection Funnel Analysis
- **Business Value:** Enables credit executives to evaluate lending expansion, policy stringency, and conversion efficiency across acquisition channels.
- **Required Columns:** `Application_ID`, `Loan_Approved`, `Application_Channel`, `Region`.
- **Metric Definitions:**
  - **Total Applications:** `COUNT(DISTINCT Application_ID)`
  - **Approval Rate (%):** `COUNT(CASE WHEN Loan_Approved = 'Approved' THEN 1 END) / COUNT(*) * 100`
  - **Rejection Rate (%):** `COUNT(CASE WHEN Loan_Approved = 'Rejected' THEN 1 END) / COUNT(*) * 100`
- **Analytical Method / SQL:**
  ```sql
  SELECT TRIM(INITCAP(Application_Channel)) AS channel,
         Region,
         COUNT(DISTINCT Application_ID) AS total_apps,
         ROUND(AVG(CASE WHEN TRIM(INITCAP(Loan_Approved)) = 'Approved' THEN 1.0 ELSE 0.0 END) * 100, 2) AS approval_rate_pct
  FROM fact_loan_application
  GROUP BY 1, 2
  ORDER BY total_apps DESC;
  ```
- **Data Quality Dependencies:** Requires canonicalization of `Application_Channel` and `Loan_Approved` strings (trimming whitespace and standardizing casing).
- **Known Limitations:** Origination dates for applications are not explicitly separated from repayment due dates.

---

### Question 2: Credit Policy "Haircut" Analysis (Requested vs. Approved Principal)
- **Business Value:** Quantifies credit rationing—the percentage of loan volume scaled back by underwriters to mitigate exposure on marginal borrowers.
- **Required Columns:** `Loan_Amount`, `Approved_Amount`, `Loan_Approved`, `Loan_Purpose`, `Default_Risk`.
- **Metric Definitions:**
  - **Total Requested Principal:** `SUM(Loan_Amount)`
  - **Total Sanctioned Principal:** `SUM(Approved_Amount)`
  - **Underwriter Haircut Ratio (%):** `(1.0 - (Approved_Amount / Loan_Amount)) * 100` (computed strictly for Approved loans)
- **Analytical Method / SQL:**
  ```sql
  SELECT TRIM(INITCAP(Loan_Purpose)) AS loan_purpose,
         TRIM(INITCAP(Default_Risk)) AS risk_tier,
         COUNT(*) AS approved_count,
         ROUND(AVG(Loan_Amount), 2) AS avg_requested,
         ROUND(AVG(Approved_Amount), 2) AS avg_approved,
         ROUND(AVG(1.0 - (Approved_Amount / Loan_Amount)) * 100, 2) AS avg_haircut_pct
  FROM fact_loan_application
  WHERE TRIM(INITCAP(Loan_Approved)) = 'Approved'
  GROUP BY 1, 2
  ORDER BY avg_haircut_pct DESC;
  ```
- **Data Quality Dependencies:** Requires excluding the 35 negative `Loan_Amount` values and deduplicating rows.
- **Known Limitations:** Rationale for specific haircuts (collateral shortfall vs income deficit) is unobserved.

---

### Question 3: Risk Score Tiering & Bureau Credit Score Alignment
- **Business Value:** Calibrates internal proprietary underwriting scorecards against external credit bureau ratings (FICO/Vantage) to detect policy misalignments.
- **Required Columns:** `Credit_Score`, `Risk_Score`, `Default_Risk`, `Loan_Approved`.
- **Metric Definitions:**
  - **Credit Score Buckets:** Standard bureau tiers (`Deep Subprime < 580`, `Subprime 580-669`, `Prime 670-739`, `Super Prime 740+`).
  - **Approval Conversion by Credit Tier:** Approval percentage within each score band.
  - **Internal vs External Score Correlation:** Pearson correlation between `Credit_Score` and `Risk_Score`.
- **Analytical Method / SQL:**
  ```sql
  SELECT CASE 
             WHEN Credit_Score < 580 THEN '1. Deep Subprime (<580)'
             WHEN Credit_Score BETWEEN 580 AND 669 THEN '2. Subprime (580-669)'
             WHEN Credit_Score BETWEEN 670 AND 739 THEN '3. Prime (670-739)'
             WHEN Credit_Score >= 740 THEN '4. Super Prime (740+)'
             ELSE '5. Unscored / Null'
         END AS credit_tier,
         COUNT(*) AS applicant_count,
         ROUND(AVG(Risk_Score), 2) AS avg_internal_risk_score,
         ROUND(AVG(CASE WHEN TRIM(INITCAP(Loan_Approved)) = 'Approved' THEN 1.0 ELSE 0.0 END) * 100, 2) AS approval_rate_pct
  FROM fact_loan_application
  GROUP BY 1
  ORDER BY 1;
  ```
- **Data Quality Dependencies:** Requires handling null credit scores (1,321 rows) and documenting scores outside 300-850.
- **Known Limitations:** Bureau credit score weighting methodology is black-box.

---

### Question 4: Employment Stability & Cash Flow Solvency Profiling
- **Business Value:** Determines whether self-employed and contract workers experience higher credit rejection rates compared to salaried employees.
- **Required Columns:** `Employment_Status`, `Job_Experience_Years`, `Annual_Income`, `Debt_To_Income_Ratio`, `Loan_Approved`.
- **Metric Definitions:**
  - **Median Income by Employment Segment:** 50th percentile income.
  - **High DTI Exposure Rate (%):** Percentage of applicants with `Debt_To_Income_Ratio > 43.0%`.
  - **Rejection Odds Ratio:** Relative rejection rate across employment categories.
- **Analytical Method / SQL:**
  ```sql
  SELECT TRIM(INITCAP(Employment_Status)) AS employment_type,
         COUNT(*) AS applicant_volume,
         ROUND(AVG(Annual_Income), 2) AS mean_income,
         ROUND(AVG(Debt_To_Income_Ratio), 2) AS mean_dti,
         ROUND(AVG(CASE WHEN TRIM(INITCAP(Loan_Approved)) = 'Approved' THEN 1.0 ELSE 0.0 END) * 100, 2) AS approval_rate_pct
  FROM fact_loan_application
  WHERE Annual_Income > 0
  GROUP BY 1
  ORDER BY approval_rate_pct DESC;
  ```
- **Data Quality Dependencies:** Must filter out 35 negative annual incomes.
- **Known Limitations:** Incomes are self-reported at application without tax return verification stamps.

---

### Question 5: Prior Delinquency Drag on Credit Underwriting
- **Business Value:** Measures how strongly historical bureau delinquencies (`Late_Payments_Last_2_Years`, `Previous_Loan_Status`) penalize approval odds and drive interest rate pricing premiums.
- **Required Columns:** `Late_Payments_Last_2_Years`, `Previous_Loan_Status`, `Loan_Approved`, `Interest_Rate`.
- **Metric Definitions:**
  - **Approval Rate by Delinquency Count:** Approval probability indexed by 0, 1, 2, 3+ late payments.
  - **Risk-Based Interest Rate Spread:** Mean interest rate sanctioned across prior default histories.
- **Analytical Method / SQL:**
  ```sql
  SELECT Late_Payments_Last_2_Years AS delinquencies_2yr,
         TRIM(INITCAP(Previous_Loan_Status)) AS bureau_prior_loan_status,
         COUNT(*) AS application_count,
         ROUND(AVG(CASE WHEN TRIM(INITCAP(Loan_Approved)) = 'Approved' THEN 1.0 ELSE 0.0 END) * 100, 2) AS approval_rate_pct,
         ROUND(AVG(CASE WHEN TRIM(INITCAP(Loan_Approved)) = 'Approved' THEN Interest_Rate END), 2) AS avg_approved_apr
  FROM fact_loan_application
  GROUP BY 1, 2
  ORDER BY 1, 2;
  ```
- **Data Quality Dependencies:** Canonicalization of `Previous_Loan_Status`.
- **Known Limitations:** Does not distinguish between minor 30-day late payments vs severe 90-day charge-offs.

---

### Question 6: Liquid Asset Coverage & Net Solvency Cushion
- **Business Value:** Identifies applicants with high income but low liquid reserves ("wealth-poor" borrowers) versus asset-backed applicants.
- **Required Columns:** `Savings_Balance`, `Checking_Balance`, `Total_Assets`, `Total_Liabilities`, `Loan_Amount`, `Loan_Approved`.
- **Metric Definitions:**
  - **Liquid Reserve Ratio:** `(Savings_Balance + Checking_Balance) / Loan_Amount`.
  - **Net Asset Cushion:** `Total_Assets - Total_Liabilities`.
- **Analytical Method / SQL:**
  ```sql
  SELECT CASE 
             WHEN (Total_Assets - Total_Liabilities) < 0 THEN '1. Negative Net Worth'
             WHEN (Total_Assets - Total_Liabilities) BETWEEN 0 AND 100000 THEN '2. $0 - $100k'
             WHEN (Total_Assets - Total_Liabilities) BETWEEN 100001 AND 500000 THEN '3. $100k - $500k'
             ELSE '4. > $500k High Net Worth'
         END AS net_worth_bracket,
         COUNT(*) AS applicant_count,
         ROUND(AVG(CASE WHEN TRIM(INITCAP(Loan_Approved)) = 'Approved' THEN 1.0 ELSE 0.0 END) * 100, 2) AS approval_rate_pct
  FROM fact_loan_application
  WHERE Savings_Balance >= 0
  GROUP BY 1
  ORDER BY 1;
  ```
- **Data Quality Dependencies:** Exclude 35 negative savings balance values.
- **Known Limitations:** Breakdown of total assets (real estate vs equity vs retirement) is not provided.

---

### Question 7: Synthetic Single-Installment Delinquency on Disbursed Loans
- **Business Value:** Evaluates initial collection performance and payment fulfillment strictly among borrowers who actually received loan funding.
- **Required Columns:** `Loan_Approved`, `disbursement_amount`, `days_late`, `payment_status`, `amount_due`, `amount_paid`.
- **Metric Definitions:**
  - **On-Time Settlement Rate (%):** `COUNT(CASE WHEN days_late = 0 THEN 1 END) / COUNT(*) * 100` (Approved loans only).
  - **Collection Efficiency (%):** `SUM(amount_paid) / SUM(amount_due) * 100` (Approved loans only).
- **Analytical Method / SQL:**
  ```sql
  SELECT TRIM(INITCAP(payment_status)) AS status,
         COUNT(*) AS installment_count,
         ROUND(AVG(days_late), 1) AS avg_days_late,
         ROUND(SUM(amount_due), 2) AS total_due,
         ROUND(SUM(amount_paid), 2) AS total_collected,
         ROUND(SUM(amount_paid) / SUM(amount_due) * 100, 2) AS collection_recovery_pct
  FROM fact_repayment_installment
  WHERE is_disbursed_loan = TRUE
  GROUP BY 1
  ORDER BY installment_count DESC;
  ```
- **Data Quality Dependencies:** **Crucial:** Must filter `WHERE is_disbursed_loan = TRUE` (excluding the 50,907 rejected loans with synthetic repayments).
- **Known Limitations:** Represents a flat single-month installment snapshot, not an ongoing multi-month amortization schedule.

---

## 3. Business Questions That CANNOT Be Answered (Out-of-Scope)

| Prohibited Business Question | Why It Cannot Be Answered with Evidence | Analytical Misrepresentation Risk |
|---|---|---|
| **"What is the portfolio 90+ day default rate?"** | **No true default flag exists.** Equating loan rejection or prior bureau history with current loan default is false. | Severe: Invalid portfolio loss modeling. |
| **"Which customers have the highest repeat lifetime value (LTV)?"** | Every record represents an isolated individual application (100,000 distinct customer IDs). **No multi-application customer history exists.** | Severe: Inventing artificial customer loyalty. |
| **"What is the optimal multi-year loss provision (CECL/IFRS 9)?"** | Data lacks multi-year macroeconomic cycles, write-offs, and charge-off vintage curves. | Severe: Falsifying regulatory accounting. |
| **"Which specific municipal cities have the highest credit risk?"** | The `city` column is merely `Region || '_City'` (only 4 macro regions exist). | Moderate: Presenting pseudo-cities as municipal data. |
| **"What is the monthly repayment trajectory over the 36-month loan term?"** | Repayment data contains only a single simulated due date and payment date per loan. | Moderate: Misrepresenting single snapshot as full schedule. |
