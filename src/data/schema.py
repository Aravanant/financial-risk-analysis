"""SQLite schema DDL, indexing, and view definitions for RiskLens AI.

Enforces:
1. Strict foreign key relationships between fct_loan_application and conformed dimensions.
2. CHECK constraints allowing NULL while forbidding out-of-range or corrupted values.
3. Strict underwriting decision consistency (chk_decision_consistency).
4. Physical separation of synthetic servicing data in demo_synthetic_repayment_snapshot.
"""

SCHEMA_VERSION = "2.0.0"

DDL_STATEMENTS = [
    # 1. Conformed Lookup Dimensions
    """
    CREATE TABLE IF NOT EXISTS dim_residence_property_location (
        location_property_id INTEGER PRIMARY KEY AUTOINCREMENT,
        region TEXT NOT NULL CHECK (region IN ('East', 'South', 'Central', 'North', 'West')),
        residential_status TEXT NOT NULL CHECK (residential_status IN ('Urban', 'Suburban', 'Rural')),
        property_ownership TEXT NOT NULL CHECK (property_ownership IN ('Rent', 'Own', 'Mortgage', 'Other', 'Family Owned')),
        UNIQUE(region, residential_status, property_ownership)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_channel (
        channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_name TEXT NOT NULL UNIQUE CHECK (channel_name IN ('Online', 'Branch', 'Mobile App', 'Agent'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_loan_purpose (
        purpose_id INTEGER PRIMARY KEY AUTOINCREMENT,
        purpose_name TEXT NOT NULL UNIQUE
    );
    """,
    # 2. Primary Application Fact Table
    """
    CREATE TABLE IF NOT EXISTS fct_loan_application (
        application_id INTEGER PRIMARY KEY,
        source_row_ordinal INTEGER NOT NULL UNIQUE,
        location_property_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        purpose_id INTEGER NOT NULL,

        -- Applicant Demographics & Socio-Economics (Safe constraints allowing NULL)
        age INTEGER CHECK (age IS NULL OR (age >= 18 AND age <= 100)),
        gender TEXT CHECK (gender IS NULL OR gender IN ('Male', 'Female', 'Other')),
        marital_status TEXT CHECK (marital_status IS NULL OR marital_status IN ('Married', 'Single', 'Divorced', 'Widowed')),
        education_level TEXT CHECK (education_level IS NULL OR education_level IN ('Bachelor', 'High School', 'Master', 'PhD', 'Phd')),
        employment_status TEXT CHECK (employment_status IS NULL OR employment_status IN ('Salaried', 'Self-Employed', 'Contract', 'Business Owner', 'Unemployed')),
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

        -- Final Underwriting Sanction (Strict Parity Between String and Boolean)
        underwriting_decision TEXT NOT NULL CHECK (underwriting_decision IN ('Approved', 'Rejected')),
        sanctioned_approved_amount REAL CHECK (sanctioned_approved_amount IS NULL OR sanctioned_approved_amount >= 0.0),
        is_approved INTEGER NOT NULL CHECK (is_approved IN (0, 1)),
        has_missing_sanctioned_amount INTEGER NOT NULL DEFAULT 0 CHECK (has_missing_sanctioned_amount IN (0, 1)),

        -- Data Quality Audit Flags (1 = Issue Present, 0 = Clean)
        has_invalid_annual_income INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_annual_income IN (0, 1)),
        has_invalid_loan_amount INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_loan_amount IN (0, 1)),
        has_invalid_savings_balance INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_savings_balance IN (0, 1)),
        has_invalid_age INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_age IN (0, 1)),
        has_invalid_financials INTEGER NOT NULL DEFAULT 0 CHECK (has_invalid_financials IN (0, 1)),

        -- Table Constraints
        CONSTRAINT chk_decision_consistency CHECK (
            (underwriting_decision = 'Approved' AND is_approved = 1) OR
            (underwriting_decision = 'Rejected' AND is_approved = 0)
        ),
        FOREIGN KEY (location_property_id) REFERENCES dim_residence_property_location(location_property_id),
        FOREIGN KEY (channel_id) REFERENCES dim_channel(channel_id),
        FOREIGN KEY (purpose_id) REFERENCES dim_loan_purpose(purpose_id)
    );
    """,
    # 3. Indices on Fact Table
    """
    CREATE INDEX IF NOT EXISTS idx_fct_decision ON fct_loan_application(underwriting_decision);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_location ON fct_loan_application(location_property_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_channel ON fct_loan_application(channel_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_purpose ON fct_loan_application(purpose_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_haircut ON fct_loan_application(is_approved, requested_loan_amount, sanctioned_approved_amount);
    """,
    # 4. Quarantined Synthetic Servicing Snapshot
    """
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
    """,
    # 5. Core Analytical Views (Strictly free from synthetic servicing fields)
    """
    CREATE VIEW IF NOT EXISTS vw_portfolio_kpis AS
    SELECT
        COUNT(*) AS total_applications,
        SUM(is_approved) AS approved_applications,
        COUNT(*) - SUM(is_approved) AS rejected_applications,
        ROUND(AVG(is_approved) * 100.0, 3) AS approval_rate_pct,
        ROUND((1.0 - AVG(is_approved)) * 100.0, 3) AS rejection_rate_pct,
        ROUND(SUM(requested_loan_amount), 2) AS total_requested_cu,
        ROUND(SUM(sanctioned_approved_amount), 2) AS total_sanctioned_cu,
        SUM(has_invalid_financials) AS invalid_financials_count,
        SUM(has_missing_sanctioned_amount) AS missing_sanctioned_count
    FROM fct_loan_application;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_channel_performance AS
    SELECT
        c.channel_id,
        c.channel_name,
        COUNT(f.application_id) AS total_applications,
        SUM(f.is_approved) AS approved_applications,
        COUNT(f.application_id) - SUM(f.is_approved) AS rejected_applications,
        ROUND(AVG(f.is_approved) * 100.0, 2) AS approval_rate_pct,
        ROUND(SUM(f.requested_loan_amount), 2) AS total_requested_cu,
        ROUND(SUM(f.sanctioned_approved_amount), 2) AS total_sanctioned_cu
    FROM dim_channel c
    LEFT JOIN fct_loan_application f ON c.channel_id = f.channel_id
    GROUP BY c.channel_id, c.channel_name
    ORDER BY c.channel_id;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_loan_purpose_analysis AS
    SELECT
        p.purpose_id,
        p.purpose_name,
        COUNT(f.application_id) AS total_applications,
        SUM(f.is_approved) AS approved_applications,
        COUNT(f.application_id) - SUM(f.is_approved) AS rejected_applications,
        ROUND(AVG(f.is_approved) * 100.0, 2) AS approval_rate_pct,
        ROUND(SUM(f.requested_loan_amount), 2) AS total_requested_cu,
        ROUND(SUM(f.sanctioned_approved_amount), 2) AS total_sanctioned_cu,
        SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END) AS haircut_eligible_count,
        ROUND(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.requested_loan_amount ELSE 0.0 END), 2) AS haircut_eligible_requested_cu,
        ROUND(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.sanctioned_approved_amount ELSE 0.0 END), 2) AS haircut_eligible_sanctioned_cu,
        ROUND(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN (f.requested_loan_amount - f.sanctioned_approved_amount) ELSE 0.0 END), 2) AS haircut_total_cu,
        ROUND((1.0 - (
            SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.sanctioned_approved_amount ELSE 0.0 END) /
            NULLIF(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.requested_loan_amount ELSE 0.0 END), 0.0)
        )) * 100.0, 4) AS aggregate_haircut_pct,
        COUNT(f.application_id) - SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END) AS haircut_excluded_count
    FROM dim_loan_purpose p
    LEFT JOIN fct_loan_application f ON p.purpose_id = f.purpose_id
    GROUP BY p.purpose_id, p.purpose_name
    ORDER BY p.purpose_id;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_underwriting_haircut AS
    SELECT
        p.purpose_name,
        COUNT(*) AS eligible_approved_count,
        ROUND(SUM(f.requested_loan_amount), 2) AS total_requested_cu,
        ROUND(SUM(f.sanctioned_approved_amount), 2) AS total_sanctioned_cu,
        ROUND(SUM(f.requested_loan_amount - f.sanctioned_approved_amount), 2) AS total_haircut_cu,
        ROUND((1.0 - (SUM(f.sanctioned_approved_amount) / SUM(f.requested_loan_amount))) * 100.0, 4) AS aggregate_haircut_pct
    FROM fct_loan_application f
    JOIN dim_loan_purpose p ON f.purpose_id = p.purpose_id
    WHERE f.is_approved = 1
      AND f.requested_loan_amount IS NOT NULL
      AND f.requested_loan_amount > 0
      AND f.sanctioned_approved_amount IS NOT NULL
    GROUP BY p.purpose_name
    HAVING SUM(f.requested_loan_amount) > 0;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_portfolio_haircut_summary AS
    SELECT
        COUNT(*) AS total_portfolio_applications,
        SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END) AS eligible_applications_count,
        ROUND(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN requested_loan_amount ELSE 0.0 END), 2) AS total_eligible_requested_cu,
        ROUND(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN sanctioned_approved_amount ELSE 0.0 END), 2) AS total_eligible_sanctioned_cu,
        ROUND(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN (requested_loan_amount - sanctioned_approved_amount) ELSE 0.0 END), 2) AS total_haircut_cu,
        ROUND((1.0 - (
            SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN sanctioned_approved_amount ELSE 0.0 END) /
            NULLIF(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN requested_loan_amount ELSE 0.0 END), 0.0)
        )) * 100.0, 4) AS aggregate_haircut_pct,
        SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) AS excluded_rejected_count,
        SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END) AS excluded_approved_missing_sanction_count,
        SUM(CASE WHEN is_approved = 1 AND (requested_loan_amount IS NULL OR requested_loan_amount <= 0) THEN 1 ELSE 0 END) AS excluded_approved_missing_requested_count,
        COUNT(*) - SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END) AS total_excluded_count
    FROM fct_loan_application;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_risk_tier_summary AS
    SELECT
        risk_tier,
        COUNT(*) AS total_applications,
        SUM(is_approved) AS approved_count,
        COUNT(*) - SUM(is_approved) AS rejected_count,
        ROUND(AVG(is_approved) * 100.0, 2) AS tier_approval_rate_pct,
        ROUND(AVG(proprietary_risk_score), 2) AS avg_proprietary_risk_score,
        ROUND(AVG(bureau_credit_score), 1) AS avg_bureau_credit_score,
        ROUND(AVG(normalized_risk_score), 4) AS avg_normalized_risk_score
    FROM fct_loan_application
    WHERE risk_tier IS NOT NULL
    GROUP BY risk_tier
    ORDER BY
        CASE risk_tier
            WHEN 'Low' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'High' THEN 3
            ELSE 4
        END;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_data_quality_metrics AS
    SELECT
        COUNT(*) AS total_applications,
        -- Data Quality Flags
        SUM(has_invalid_annual_income) AS invalid_annual_income_flag_count,
        SUM(has_invalid_loan_amount) AS invalid_loan_amount_flag_count,
        SUM(has_invalid_savings_balance) AS invalid_savings_balance_flag_count,
        SUM(has_invalid_age) AS invalid_age_flag_count,
        SUM(has_invalid_financials) AS composite_invalid_financials_count,

        -- Missing Value Null Counts
        SUM(has_missing_sanctioned_amount) AS missing_sanctioned_amount_count,
        SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END) AS missing_sanctioned_approved_count,
        SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END) AS missing_sanctioned_rejected_count,
        SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount = 0.0 THEN 1 ELSE 0 END) AS genuine_zero_sanctioned_rejected_count,
        SUM(CASE WHEN bureau_credit_score IS NULL THEN 1 ELSE 0 END) AS missing_bureau_credit_score_count,
        SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END) AS missing_age_count,
        SUM(CASE WHEN annual_income IS NULL THEN 1 ELSE 0 END) AS missing_annual_income_count,
        SUM(CASE WHEN savings_balance IS NULL THEN 1 ELSE 0 END) AS missing_savings_balance_count,
        SUM(CASE WHEN requested_loan_amount IS NULL THEN 1 ELSE 0 END) AS missing_requested_loan_amount_count,
        SUM(CASE WHEN interest_rate IS NULL THEN 1 ELSE 0 END) AS missing_interest_rate_count,
        SUM(CASE WHEN debt_to_income_ratio IS NULL THEN 1 ELSE 0 END) AS missing_debt_to_income_ratio_count,
        SUM(CASE WHEN proprietary_risk_score IS NULL THEN 1 ELSE 0 END) AS missing_proprietary_risk_score_count,

        -- Haircut Eligibility & Exclusions
        SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END) AS haircut_eligible_count,
        SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) AS haircut_excluded_rejected_count,
        SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END) AS haircut_excluded_approved_missing_sanction_count,
        SUM(CASE WHEN is_approved = 1 AND (requested_loan_amount IS NULL OR requested_loan_amount <= 0) THEN 1 ELSE 0 END) AS haircut_excluded_approved_missing_requested_count,
        COUNT(*) - SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END) AS haircut_total_excluded_count
    FROM fct_loan_application;
    """
]


# ==============================================================================
# 6. PostgreSQL / Supabase Schema DDL and Analytical Views
# ==============================================================================

POSTGRES_TABLE_DDL = [
    # 1. Conformed Lookup Dimensions
    """
    CREATE TABLE IF NOT EXISTS dim_residence_property_location (
        location_property_id SERIAL PRIMARY KEY,
        region VARCHAR(20) NOT NULL CHECK (region IN ('East', 'South', 'Central', 'North', 'West')),
        residential_status VARCHAR(20) NOT NULL CHECK (residential_status IN ('Urban', 'Suburban', 'Rural')),
        property_ownership VARCHAR(30) NOT NULL CHECK (property_ownership IN ('Rent', 'Own', 'Mortgage', 'Other', 'Family Owned')),
        UNIQUE(region, residential_status, property_ownership)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_channel (
        channel_id SERIAL PRIMARY KEY,
        channel_name VARCHAR(50) NOT NULL UNIQUE CHECK (channel_name IN ('Online', 'Branch', 'Mobile App', 'Agent'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_loan_purpose (
        purpose_id SERIAL PRIMARY KEY,
        purpose_name VARCHAR(50) NOT NULL UNIQUE
    );
    """,
    # 2. Primary Application Fact Table
    """
    CREATE TABLE IF NOT EXISTS fct_loan_application (
        application_id BIGINT PRIMARY KEY,
        source_row_ordinal INTEGER NOT NULL UNIQUE,
        location_property_id INTEGER NOT NULL REFERENCES dim_residence_property_location(location_property_id),
        channel_id INTEGER NOT NULL REFERENCES dim_channel(channel_id),
        purpose_id INTEGER NOT NULL REFERENCES dim_loan_purpose(purpose_id),

        -- Applicant Demographics & Socio-Economics
        age INTEGER CHECK (age IS NULL OR (age >= 18 AND age <= 100)),
        gender VARCHAR(20) CHECK (gender IS NULL OR gender IN ('Male', 'Female', 'Other')),
        marital_status VARCHAR(20) CHECK (marital_status IS NULL OR marital_status IN ('Married', 'Single', 'Divorced', 'Widowed')),
        education_level VARCHAR(30) CHECK (education_level IS NULL OR education_level IN ('Bachelor', 'High School', 'Master', 'PhD', 'Phd')),
        employment_status VARCHAR(30) CHECK (employment_status IS NULL OR employment_status IN ('Salaried', 'Self-Employed', 'Contract', 'Business Owner', 'Unemployed')),
        job_experience_years INTEGER CHECK (job_experience_years IS NULL OR job_experience_years >= 0),
        dependents INTEGER CHECK (dependents IS NULL OR dependents >= 0),

        -- Financial Balances (CU)
        annual_income NUMERIC(16, 2) CHECK (annual_income IS NULL OR annual_income >= 0),
        monthly_income_reported NUMERIC(16, 2) CHECK (monthly_income_reported IS NULL OR monthly_income_reported >= 0),
        monthly_income_calculated NUMERIC(16, 2) CHECK (monthly_income_calculated IS NULL OR monthly_income_calculated >= 0),
        savings_balance NUMERIC(16, 2) CHECK (savings_balance IS NULL OR savings_balance >= 0),
        checking_balance NUMERIC(16, 2) CHECK (checking_balance IS NULL OR checking_balance >= 0),
        total_assets NUMERIC(16, 2) CHECK (total_assets IS NULL OR total_assets >= 0),
        total_liabilities NUMERIC(16, 2) CHECK (total_liabilities IS NULL OR total_liabilities >= 0),
        monthly_debt_payment NUMERIC(16, 2) CHECK (monthly_debt_payment IS NULL OR monthly_debt_payment >= 0),
        net_worth NUMERIC(16, 2),
        bank_account_tenure_months INTEGER CHECK (bank_account_tenure_months IS NULL OR bank_account_tenure_months >= 0),

        -- Loan Request & Underwriting Attributes
        requested_loan_amount NUMERIC(16, 2) CHECK (requested_loan_amount IS NULL OR requested_loan_amount > 0),
        requested_term_months INTEGER CHECK (requested_term_months IS NULL OR requested_term_months > 0),
        interest_rate NUMERIC(6, 2) CHECK (interest_rate IS NULL OR (interest_rate >= 0 AND interest_rate <= 100)),
        debt_to_income_ratio NUMERIC(6, 2) CHECK (debt_to_income_ratio IS NULL OR (debt_to_income_ratio >= 0 AND debt_to_income_ratio <= 100)),
        co_applicant_flag SMALLINT CHECK (co_applicant_flag IS NULL OR co_applicant_flag IN (0, 1)),
        collateral_flag SMALLINT CHECK (collateral_flag IS NULL OR collateral_flag IN (0, 1)),

        -- Credit Bureau Attributes
        bureau_credit_score INTEGER CHECK (bureau_credit_score IS NULL OR (bureau_credit_score >= 0 AND bureau_credit_score <= 1000)),
        bureau_existing_loans INTEGER CHECK (bureau_existing_loans IS NULL OR bureau_existing_loans >= 0),
        bureau_late_payments_2yr INTEGER CHECK (bureau_late_payments_2yr IS NULL OR bureau_late_payments_2yr >= 0),
        bureau_credit_history_years NUMERIC(6, 2) CHECK (bureau_credit_history_years IS NULL OR bureau_credit_history_years >= 0),
        bureau_prior_loan_status VARCHAR(30) CHECK (bureau_prior_loan_status IS NULL OR bureau_prior_loan_status IN ('Paid Off', 'Active', 'No Previous Loan', 'Defaulted')),

        -- Proprietary Scorecard Attributes
        proprietary_risk_score NUMERIC(6, 2) CHECK (proprietary_risk_score IS NULL OR (proprietary_risk_score >= 0 AND proprietary_risk_score <= 100)),
        risk_tier VARCHAR(20) CHECK (risk_tier IS NULL OR risk_tier IN ('Low', 'Medium', 'High')),
        normalized_risk_score NUMERIC(8, 4) CHECK (normalized_risk_score IS NULL OR (normalized_risk_score >= 0.0 AND normalized_risk_score <= 1.0)),

        -- Final Underwriting Sanction
        underwriting_decision VARCHAR(20) NOT NULL CHECK (underwriting_decision IN ('Approved', 'Rejected')),
        sanctioned_approved_amount NUMERIC(16, 2) CHECK (sanctioned_approved_amount IS NULL OR sanctioned_approved_amount >= 0.0),
        is_approved SMALLINT NOT NULL CHECK (is_approved IN (0, 1)),
        has_missing_sanctioned_amount SMALLINT NOT NULL DEFAULT 0 CHECK (has_missing_sanctioned_amount IN (0, 1)),

        -- Data Quality Audit Flags (1 = Issue Present, 0 = Clean)
        has_invalid_annual_income SMALLINT NOT NULL DEFAULT 0 CHECK (has_invalid_annual_income IN (0, 1)),
        has_invalid_loan_amount SMALLINT NOT NULL DEFAULT 0 CHECK (has_invalid_loan_amount IN (0, 1)),
        has_invalid_savings_balance SMALLINT NOT NULL DEFAULT 0 CHECK (has_invalid_savings_balance IN (0, 1)),
        has_invalid_age SMALLINT NOT NULL DEFAULT 0 CHECK (has_invalid_age IN (0, 1)),
        has_invalid_financials SMALLINT NOT NULL DEFAULT 0 CHECK (has_invalid_financials IN (0, 1)),

        -- Table Constraints
        CONSTRAINT chk_decision_consistency CHECK (
            (underwriting_decision = 'Approved' AND is_approved = 1) OR
            (underwriting_decision = 'Rejected' AND is_approved = 0)
        )
    );
    """,
    # 3. Indices on Fact Table
    """
    CREATE INDEX IF NOT EXISTS idx_fct_decision ON fct_loan_application(underwriting_decision);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_location ON fct_loan_application(location_property_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_channel ON fct_loan_application(channel_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_purpose ON fct_loan_application(purpose_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_haircut ON fct_loan_application(is_approved, requested_loan_amount, sanctioned_approved_amount);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fct_risk_tier ON fct_loan_application(risk_tier);
    """,
    # 4. Quarantined Synthetic Servicing Snapshot
    """
    CREATE TABLE IF NOT EXISTS demo_synthetic_repayment_snapshot (
        application_id BIGINT PRIMARY KEY REFERENCES fct_loan_application(application_id),
        simulated_due_date VARCHAR(32),
        simulated_payment_date VARCHAR(32),
        simulated_amount_due_cu NUMERIC(16, 2),
        simulated_amount_paid_cu NUMERIC(16, 2),
        simulated_days_late INTEGER,
        simulated_payment_status VARCHAR(20),
        simulated_disbursement_amount_cu NUMERIC(16, 2),
        simulated_outstanding_balance_cu NUMERIC(16, 2)
    );
    """
]

# The 7 Conformed Analytical Views (PostgreSQL Dialect)
POSTGRES_VIEW_DDL = [
    # View 1: Primary Portfolio KPIs
    """
    CREATE OR REPLACE VIEW vw_portfolio_kpis AS
    SELECT
        COUNT(*)::bigint AS total_applications,
        SUM(is_approved)::bigint AS approved_applications,
        (COUNT(*) - SUM(is_approved))::bigint AS rejected_applications,
        ROUND((AVG(is_approved) * 100.0)::numeric, 3)::double precision AS approval_rate_pct,
        ROUND(((1.0 - AVG(is_approved)) * 100.0)::numeric, 3)::double precision AS rejection_rate_pct,
        ROUND(SUM(requested_loan_amount)::numeric, 2)::double precision AS total_requested_cu,
        ROUND(SUM(sanctioned_approved_amount)::numeric, 2)::double precision AS total_sanctioned_cu,
        SUM(has_invalid_financials)::bigint AS invalid_financials_count,
        SUM(has_missing_sanctioned_amount)::bigint AS missing_sanctioned_count
    FROM fct_loan_application;
    """,
    # View 2: Channel Performance Breakdown
    """
    CREATE OR REPLACE VIEW vw_channel_performance AS
    SELECT
        c.channel_id,
        c.channel_name,
        COUNT(f.application_id)::bigint AS total_applications,
        COALESCE(SUM(f.is_approved), 0)::bigint AS approved_applications,
        (COUNT(f.application_id) - COALESCE(SUM(f.is_approved), 0))::bigint AS rejected_applications,
        ROUND((COALESCE(AVG(f.is_approved), 0) * 100.0)::numeric, 2)::double precision AS approval_rate_pct,
        ROUND(COALESCE(SUM(f.requested_loan_amount), 0)::numeric, 2)::double precision AS total_requested_cu,
        ROUND(COALESCE(SUM(f.sanctioned_approved_amount), 0)::numeric, 2)::double precision AS total_sanctioned_cu
    FROM dim_channel c
    LEFT JOIN fct_loan_application f ON c.channel_id = f.channel_id
    GROUP BY c.channel_id, c.channel_name
    ORDER BY c.channel_id;
    """,
    # View 3: Loan Purpose Analysis & Haircut Metrics
    """
    CREATE OR REPLACE VIEW vw_loan_purpose_analysis AS
    SELECT
        p.purpose_id,
        p.purpose_name,
        COUNT(f.application_id)::bigint AS total_applications,
        COALESCE(SUM(f.is_approved), 0)::bigint AS approved_applications,
        (COUNT(f.application_id) - COALESCE(SUM(f.is_approved), 0))::bigint AS rejected_applications,
        ROUND((COALESCE(AVG(f.is_approved), 0) * 100.0)::numeric, 2)::double precision AS approval_rate_pct,
        ROUND(COALESCE(SUM(f.requested_loan_amount), 0)::numeric, 2)::double precision AS total_requested_cu,
        ROUND(COALESCE(SUM(f.sanctioned_approved_amount), 0)::numeric, 2)::double precision AS total_sanctioned_cu,
        COALESCE(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END), 0)::bigint AS haircut_eligible_count,
        ROUND(COALESCE(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.requested_loan_amount ELSE 0.0 END), 0)::numeric, 2)::double precision AS haircut_eligible_requested_cu,
        ROUND(COALESCE(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.sanctioned_approved_amount ELSE 0.0 END), 0)::numeric, 2)::double precision AS haircut_eligible_sanctioned_cu,
        ROUND(COALESCE(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN (f.requested_loan_amount - f.sanctioned_approved_amount) ELSE 0.0 END), 0)::numeric, 2)::double precision AS haircut_total_cu,
        ROUND((1.0 - (
            COALESCE(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.sanctioned_approved_amount ELSE 0.0 END), 0) /
            NULLIF(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN f.requested_loan_amount ELSE 0.0 END), 0.0)
        )) * 100.0, 4)::double precision AS aggregate_haircut_pct,
        (COUNT(f.application_id) - COALESCE(SUM(CASE WHEN f.is_approved = 1 AND f.requested_loan_amount IS NOT NULL AND f.requested_loan_amount > 0 AND f.sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END), 0))::bigint AS haircut_excluded_count
    FROM dim_loan_purpose p
    LEFT JOIN fct_loan_application f ON p.purpose_id = f.purpose_id
    GROUP BY p.purpose_id, p.purpose_name
    ORDER BY p.purpose_id;
    """,
    # View 4: Underwriting Haircut Breakdown
    """
    CREATE OR REPLACE VIEW vw_underwriting_haircut AS
    SELECT
        p.purpose_name,
        COUNT(*)::bigint AS eligible_approved_count,
        ROUND(SUM(f.requested_loan_amount)::numeric, 2)::double precision AS total_requested_cu,
        ROUND(SUM(f.sanctioned_approved_amount)::numeric, 2)::double precision AS total_sanctioned_cu,
        ROUND(SUM(f.requested_loan_amount - f.sanctioned_approved_amount)::numeric, 2)::double precision AS total_haircut_cu,
        ROUND((1.0 - (SUM(f.sanctioned_approved_amount) / SUM(f.requested_loan_amount))) * 100.0, 4)::double precision AS aggregate_haircut_pct
    FROM fct_loan_application f
    JOIN dim_loan_purpose p ON f.purpose_id = p.purpose_id
    WHERE f.is_approved = 1
      AND f.requested_loan_amount IS NOT NULL
      AND f.requested_loan_amount > 0
      AND f.sanctioned_approved_amount IS NOT NULL
    GROUP BY p.purpose_name
    HAVING SUM(f.requested_loan_amount) > 0;
    """,
    # View 5: Portfolio-Level Haircut Summary & Exclusion Arithmetic
    """
    CREATE OR REPLACE VIEW vw_portfolio_haircut_summary AS
    SELECT
        COUNT(*)::bigint AS total_portfolio_applications,
        SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END)::bigint AS eligible_applications_count,
        ROUND(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN requested_loan_amount ELSE 0.0 END)::numeric, 2)::double precision AS total_eligible_requested_cu,
        ROUND(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN sanctioned_approved_amount ELSE 0.0 END)::numeric, 2)::double precision AS total_eligible_sanctioned_cu,
        ROUND(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN (requested_loan_amount - sanctioned_approved_amount) ELSE 0.0 END)::numeric, 2)::double precision AS total_haircut_cu,
        ROUND((1.0 - (
            SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN sanctioned_approved_amount ELSE 0.0 END) /
            NULLIF(SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN requested_loan_amount ELSE 0.0 END), 0.0)
        )) * 100.0, 4)::double precision AS aggregate_haircut_pct,
        SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END)::bigint AS excluded_rejected_count,
        SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END)::bigint AS excluded_approved_missing_sanction_count,
        SUM(CASE WHEN is_approved = 1 AND (requested_loan_amount IS NULL OR requested_loan_amount <= 0) THEN 1 ELSE 0 END)::bigint AS excluded_approved_missing_requested_count,
        (COUNT(*) - SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END))::bigint AS total_excluded_count
    FROM fct_loan_application;
    """,
    # View 6: Risk Tier Summary
    """
    CREATE OR REPLACE VIEW vw_risk_tier_summary AS
    SELECT
        risk_tier,
        COUNT(*)::bigint AS total_applications,
        SUM(is_approved)::bigint AS approved_count,
        (COUNT(*) - SUM(is_approved))::bigint AS rejected_count,
        ROUND((AVG(is_approved) * 100.0)::numeric, 2)::double precision AS tier_approval_rate_pct,
        ROUND(AVG(proprietary_risk_score)::numeric, 2)::double precision AS avg_proprietary_risk_score,
        ROUND(AVG(bureau_credit_score)::numeric, 1)::double precision AS avg_bureau_credit_score,
        ROUND(AVG(normalized_risk_score)::numeric, 4)::double precision AS avg_normalized_risk_score
    FROM fct_loan_application
    WHERE risk_tier IS NOT NULL
    GROUP BY risk_tier
    ORDER BY
        CASE risk_tier
            WHEN 'Low' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'High' THEN 3
            ELSE 4
        END;
    """,
    # View 7: Data Quality & Missingness Metrics
    """
    CREATE OR REPLACE VIEW vw_data_quality_metrics AS
    SELECT
        COUNT(*)::bigint AS total_applications,
        -- Data Quality Flags
        SUM(has_invalid_annual_income)::bigint AS invalid_annual_income_flag_count,
        SUM(has_invalid_loan_amount)::bigint AS invalid_loan_amount_flag_count,
        SUM(has_invalid_savings_balance)::bigint AS invalid_savings_balance_flag_count,
        SUM(has_invalid_age)::bigint AS invalid_age_flag_count,
        SUM(has_invalid_financials)::bigint AS composite_invalid_financials_count,

        -- Missing Value Null Counts
        SUM(has_missing_sanctioned_amount)::bigint AS missing_sanctioned_amount_count,
        SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END)::bigint AS missing_sanctioned_approved_count,
        SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END)::bigint AS missing_sanctioned_rejected_count,
        SUM(CASE WHEN is_approved = 0 AND sanctioned_approved_amount = 0.0 THEN 1 ELSE 0 END)::bigint AS genuine_zero_sanctioned_rejected_count,
        SUM(CASE WHEN bureau_credit_score IS NULL THEN 1 ELSE 0 END)::bigint AS missing_bureau_credit_score_count,
        SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END)::bigint AS missing_age_count,
        SUM(CASE WHEN annual_income IS NULL THEN 1 ELSE 0 END)::bigint AS missing_annual_income_count,
        SUM(CASE WHEN savings_balance IS NULL THEN 1 ELSE 0 END)::bigint AS missing_savings_balance_count,
        SUM(CASE WHEN requested_loan_amount IS NULL THEN 1 ELSE 0 END)::bigint AS missing_requested_loan_amount_count,
        SUM(CASE WHEN interest_rate IS NULL THEN 1 ELSE 0 END)::bigint AS missing_interest_rate_count,
        SUM(CASE WHEN debt_to_income_ratio IS NULL THEN 1 ELSE 0 END)::bigint AS missing_debt_to_income_ratio_count,
        SUM(CASE WHEN proprietary_risk_score IS NULL THEN 1 ELSE 0 END)::bigint AS missing_proprietary_risk_score_count,

        -- Haircut Eligibility & Exclusions
        SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END)::bigint AS haircut_eligible_count,
        SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END)::bigint AS haircut_excluded_rejected_count,
        SUM(CASE WHEN is_approved = 1 AND sanctioned_approved_amount IS NULL THEN 1 ELSE 0 END)::bigint AS haircut_excluded_approved_missing_sanction_count,
        SUM(CASE WHEN is_approved = 1 AND (requested_loan_amount IS NULL OR requested_loan_amount <= 0) THEN 1 ELSE 0 END)::bigint AS haircut_excluded_approved_missing_requested_count,
        (COUNT(*) - SUM(CASE WHEN is_approved = 1 AND requested_loan_amount > 0 AND sanctioned_approved_amount IS NOT NULL THEN 1 ELSE 0 END))::bigint AS haircut_total_excluded_count
    FROM fct_loan_application;
    """
]

POSTGRES_DDL_STATEMENTS = POSTGRES_TABLE_DDL + POSTGRES_VIEW_DDL
