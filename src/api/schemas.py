"""Pydantic v2 schemas for RiskLens AI analytical REST API responses and requests.

Enforces:
1. Exact type hints, field descriptions, and stability.
2. Preservation of source NULLs (Optional types with None defaults).
3. Standardized pagination metadata and error envelopes.
4. Currency unit labeled as 'CU' throughout.
5. Risk score clearly designated as proprietary scorecard (0-100), not default probability.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# Base schema configuration allowing attribute population and serialization
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --- 1. Health & Status Schemas ---

class HealthResponse(BaseSchema):
    status: str = Field(..., description="System health status ('healthy', 'degraded', 'unhealthy')")
    connected: bool = Field(..., description="SQLite database connectivity indicator")
    database_size_bytes: Optional[int] = Field(None, description="Physical database file size in bytes")
    schema_version: str = Field(..., description="Underwriting warehouse schema version")
    record_counts: Optional[Dict[str, int]] = Field(None, description="Row counts across key tables")
    error: Optional[str] = Field(None, description="Diagnostic error message if degraded")


# --- 2. Portfolio Overview Schemas ---

class PortfolioKPIsResponse(BaseSchema):
    total_applications: int = Field(..., description="Total deduplicated loan applications received")
    approved_applications: int = Field(..., description="Total sanctioned/approved applications")
    rejected_applications: int = Field(..., description="Total rejected applications")
    approval_rate_pct: float = Field(..., description="Portfolio approval rate percentage")
    rejection_rate_pct: float = Field(..., description="Portfolio rejection rate percentage")
    total_requested_cu: float = Field(..., description="Total requested principal volume in Currency Units (CU)")
    total_sanctioned_cu: float = Field(..., description="Total sanctioned approved principal volume in Currency Units (CU)")
    invalid_financials_count: int = Field(..., description="Applications flagged with negative financial balances")
    missing_sanctioned_count: int = Field(..., description="Applications with missing approved amounts (NULLs)")
    currency_unit: str = Field("CU", description="Standard currency unit notation")


# --- 3. Dimension Breakdown Schemas ---

class ChannelPerformanceItem(BaseSchema):
    channel_id: int = Field(..., description="Conformed channel identifier")
    channel_name: str = Field(..., description="Origination channel name ('Online', 'Branch', 'Mobile App', 'Agent')")
    total_applications: int = Field(..., description="Total applications originating via this channel")
    approved_applications: int = Field(..., description="Approved applications via this channel")
    rejected_applications: int = Field(..., description="Rejected applications via this channel")
    approval_rate_pct: float = Field(..., description="Channel-level approval rate percentage")
    total_requested_cu: float = Field(..., description="Total requested principal via channel in CU")
    total_sanctioned_cu: float = Field(..., description="Total sanctioned principal via channel in CU")
    currency_unit: str = Field("CU", description="Currency unit")


class LoanPurposeItem(BaseSchema):
    purpose_id: int = Field(..., description="Conformed loan purpose identifier")
    purpose_name: str = Field(..., description="Loan purpose category")
    total_applications: int = Field(..., description="Applications in this purpose category")
    approved_applications: int = Field(..., description="Approved applications in this category")
    rejected_applications: int = Field(..., description="Rejected applications in this category")
    approval_rate_pct: float = Field(..., description="Category approval rate percentage")
    total_requested_cu: float = Field(..., description="Total requested principal across all applications in CU")
    total_sanctioned_cu: float = Field(..., description="Total sanctioned principal across all applications in CU")
    haircut_eligible_count: int = Field(..., description="Approved applications eligible for haircut calculation")
    haircut_eligible_requested_cu: float = Field(..., description="Requested principal of eligible applications in CU")
    haircut_eligible_sanctioned_cu: float = Field(..., description="Sanctioned principal of eligible applications in CU")
    haircut_total_cu: float = Field(..., description="Haircut difference (requested - sanctioned) in CU")
    aggregate_haircut_pct: float = Field(..., description="Aggregate haircut percentage for this purpose")
    haircut_excluded_count: int = Field(..., description="Applications excluded from haircut calculation")
    currency_unit: str = Field("CU", description="Currency unit")


# --- 4. Haircut Metrics Schemas ---

class HaircutExclusions(BaseSchema):
    excluded_rejected_count: int = Field(..., description="Rejected applications excluded from haircut")
    excluded_approved_missing_sanction_count: int = Field(..., description="Approved applications with missing sanctioned amount")
    excluded_approved_missing_requested_count: int = Field(..., description="Approved applications with missing or non-positive requested amount")
    total_excluded_count: int = Field(..., description="Net unique applications excluded from haircut calculation")


class PortfolioHaircutSummary(BaseSchema):
    total_portfolio_applications: int = Field(..., description="Total applications across portfolio")
    eligible_applications_count: int = Field(..., description="Approved applications meeting all haircut criteria")
    total_eligible_requested_cu: float = Field(..., description="Sum of requested principal for eligible cohort in CU")
    total_eligible_sanctioned_cu: float = Field(..., description="Sum of sanctioned principal for eligible cohort in CU")
    total_haircut_cu: float = Field(..., description="Total underwriting haircut in CU")
    aggregate_haircut_pct: float = Field(..., description="Portfolio-level aggregate haircut percentage")
    currency_unit: str = Field("CU", description="Currency unit")
    exclusions: HaircutExclusions = Field(..., description="Breakdown of excluded applications")
    calculation_notes: str = Field(..., description="Methodology statement confirming aggregate sum calculation")


class HaircutResponse(BaseSchema):
    portfolio_summary: PortfolioHaircutSummary = Field(..., description="Portfolio-level haircut KPIs and exclusions")
    by_purpose: List[LoanPurposeItem] = Field(..., description="Haircut metrics segmented across all 8 verified loan purposes")


# --- 5. Risk Tier Schemas ---

class RiskTierItem(BaseSchema):
    risk_tier: str = Field(..., description="Source-provided Default_Risk category ('Low', 'Medium', 'High')")
    total_applications: int = Field(..., description="Applications assigned to this risk tier")
    approved_count: int = Field(..., description="Approved applications in this tier")
    rejected_count: int = Field(..., description="Rejected applications in this tier")
    tier_approval_rate_pct: float = Field(..., description="Approval rate percentage for this tier")
    avg_proprietary_risk_score: float = Field(..., description="Average source proprietary risk score (0-100 scale, NOT calibrated default probability)")
    avg_bureau_credit_score: float = Field(..., description="Average credit bureau score")
    avg_normalized_risk_score: float = Field(..., description="Average normalized risk score (0.0 - 1.0)")
    tier_notes: str = Field(
        "Source-provided Default_Risk. Proprietary risk score is an uncalibrated scorecard (0-100), not a probability.",
        description="Methodological clarification note"
    )


# --- 6. Data Quality Schemas ---

class DataQualityAuditFlags(BaseSchema):
    invalid_annual_income_flag_count: int = Field(..., description="Negative annual income entries nullified and flagged")
    invalid_loan_amount_flag_count: int = Field(..., description="Non-positive loan amount entries nullified and flagged")
    invalid_savings_balance_flag_count: int = Field(..., description="Negative savings balance entries nullified and flagged")
    invalid_age_flag_count: int = Field(..., description="Out-of-bounds applicant ages (<18 or >100) nullified and flagged")
    composite_invalid_financials_count: int = Field(..., description="Unique applications with at least one invalid financial entry")


class DataQualityMissingValues(BaseSchema):
    missing_sanctioned_amount_count: int = Field(..., description="Total missing sanctioned approved amounts (NULLs)")
    missing_sanctioned_approved_count: int = Field(..., description="Approved applications with missing sanctioned amount")
    missing_sanctioned_rejected_count: int = Field(..., description="Rejected applications with missing sanctioned amount")
    genuine_zero_sanctioned_rejected_count: int = Field(..., description="Rejected applications with genuine recorded 0.0 amount")
    missing_bureau_credit_score_count: int = Field(..., description="Missing credit bureau scores")
    missing_age_count: int = Field(..., description="Missing or nullified applicant ages")
    missing_annual_income_count: int = Field(..., description="Missing or nullified annual incomes")
    missing_savings_balance_count: int = Field(..., description="Missing or nullified savings balances")
    missing_requested_loan_amount_count: int = Field(..., description="Missing or nullified requested loan amounts")
    missing_interest_rate_count: int = Field(..., description="Missing interest rates")
    missing_debt_to_income_ratio_count: int = Field(..., description="Missing debt-to-income ratios")
    missing_proprietary_risk_score_count: int = Field(..., description="Missing proprietary risk scores")


class DataQualityResponse(BaseSchema):
    total_applications: int = Field(..., description="Total records evaluated in warehouse")
    audit_flags: DataQualityAuditFlags = Field(..., description="Audit flag counts for sanitized invalid entries")
    missing_values: DataQualityMissingValues = Field(..., description="Counts of source nulls and genuine recorded zeros")
    haircut_exclusions: HaircutExclusions = Field(..., description="Eligibility audit for haircut KPI")


# --- 7. Application Details & Pagination Schemas ---

class ApplicationSummary(BaseSchema):
    application_id: int = Field(..., description="Unique loan application identifier")
    source_row_ordinal: int = Field(..., description="1-indexed physical file order")
    
    # Demographics
    age: Optional[int] = Field(None, description="Applicant age (NULL if out of range [18, 100] or missing)")
    gender: Optional[str] = Field(None, description="Gender ('Male', 'Female', 'Other')")
    marital_status: Optional[str] = Field(None, description="Marital status")
    education_level: Optional[str] = Field(None, description="Highest education level")
    employment_status: Optional[str] = Field(None, description="Employment status")
    job_experience_years: Optional[int] = Field(None, description="Years of professional experience")
    dependents: Optional[int] = Field(None, description="Number of dependents")
    
    # Financial Balances (CU)
    annual_income: Optional[float] = Field(None, description="Annual income in CU (NULL if negative)")
    monthly_income_reported: Optional[float] = Field(None, description="Source reported monthly income in CU")
    monthly_income_calculated: Optional[float] = Field(None, description="Calculated monthly income (annual_income / 12) in CU")
    savings_balance: Optional[float] = Field(None, description="Savings account balance in CU (NULL if negative)")
    checking_balance: Optional[float] = Field(None, description="Checking account balance in CU")
    total_assets: Optional[float] = Field(None, description="Total balance sheet assets in CU")
    total_liabilities: Optional[float] = Field(None, description="Total balance sheet liabilities in CU")
    monthly_debt_payment: Optional[float] = Field(None, description="Monthly existing debt servicing payment in CU")
    net_worth: Optional[float] = Field(None, description="Calculated net worth (assets - liabilities) in CU")
    bank_account_tenure_months: Optional[int] = Field(None, description="Banking relationship tenure in months")
    
    # Loan Request & Terms
    requested_loan_amount: Optional[float] = Field(None, description="Requested principal amount in CU (NULL if <= 0)")
    requested_term_months: Optional[int] = Field(None, description="Requested tenure in months")
    interest_rate: Optional[float] = Field(None, description="Annual interest rate percentage")
    debt_to_income_ratio: Optional[float] = Field(None, description="Debt to income ratio percentage")
    co_applicant_flag: Optional[int] = Field(None, description="Co-applicant present flag (1=Yes, 0=No, NULL)")
    collateral_flag: Optional[int] = Field(None, description="Collateral pledged flag (1=Yes, 0=No, NULL)")
    
    # Credit Bureau
    bureau_credit_score: Optional[int] = Field(None, description="Credit bureau score [0, 999]")
    bureau_existing_loans: Optional[int] = Field(None, description="Number of active existing loans")
    bureau_late_payments_2yr: Optional[int] = Field(None, description="Late payment incidents in trailing 24 months")
    bureau_credit_history_years: Optional[float] = Field(None, description="Length of credit history in years")
    bureau_prior_loan_status: Optional[str] = Field(None, description="Status of prior loan account")
    
    # Proprietary Scorecard
    proprietary_risk_score: Optional[float] = Field(None, description="Proprietary risk scorecard rating [0, 100]")
    risk_tier: Optional[str] = Field(None, description="Source-provided default risk category ('Low', 'Medium', 'High')")
    normalized_risk_score: Optional[float] = Field(None, description="Normalized risk score [0.0, 1.0]")
    
    # Underwriting Outcome
    underwriting_decision: str = Field(..., description="Decision ('Approved', 'Rejected')")
    sanctioned_approved_amount: Optional[float] = Field(None, description="Sanctioned principal amount in CU (0.0 for rejected with recorded zero, NULL if missing)")
    is_approved: int = Field(..., description="Underwriting approval indicator (1=Approved, 0=Rejected)")
    has_missing_sanctioned_amount: int = Field(..., description="Flag indicating sanctioned amount was missing in source")
    
    # Conformed Dimension Details
    channel_name: str = Field(..., description="Origination channel name")
    purpose_name: str = Field(..., description="Loan purpose category")
    region: str = Field(..., description="Geographic region")
    residential_status: str = Field(..., description="Residential status ('Urban', 'Suburban', 'Rural')")
    property_ownership: str = Field(..., description="Property ownership status")
    
    # Audit Flags
    has_invalid_annual_income: int = Field(..., description="Flag: Corrupted negative annual income sanitized")
    has_invalid_loan_amount: int = Field(..., description="Flag: Non-positive loan amount sanitized")
    has_invalid_savings_balance: int = Field(..., description="Flag: Corrupted negative savings balance sanitized")
    has_invalid_age: int = Field(..., description="Flag: Out-of-bounds applicant age sanitized")
    has_invalid_financials: int = Field(..., description="Composite flag: Any financial balance was corrupted")


class PaginatedApplicationsResponse(BaseSchema):
    total_items: int = Field(..., description="Total matching application records")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of records per page")
    total_pages: int = Field(..., description="Total available pages")
    items: List[ApplicationSummary] = Field(..., description="Application records for the current page")


# --- 8. Demonstration-Only Synthetic Servicing Schemas ---

class ServicingDemoResponse(BaseSchema):
    application_id: int = Field(..., description="Application identifier")
    simulated_due_date: Optional[str] = Field(None, description="Simulated installment due date")
    simulated_payment_date: Optional[str] = Field(None, description="Simulated fulfillment payment date")
    simulated_amount_due_cu: Optional[float] = Field(None, description="Simulated installment amount due in CU")
    simulated_amount_paid_cu: Optional[float] = Field(None, description="Simulated actual payment received in CU")
    simulated_days_late: Optional[int] = Field(None, description="Simulated delinquency delay in days")
    simulated_payment_status: Optional[str] = Field(None, description="Simulated payment status ('Paid', 'Late', 'Defaulted')")
    simulated_disbursement_amount_cu: Optional[float] = Field(None, description="Simulated disbursed balance in CU")
    simulated_outstanding_balance_cu: Optional[float] = Field(None, description="Simulated remaining balance in CU")
    demonstration_only: bool = Field(True, description="Strict quarantine marker")
    isolation_notice: str = Field(
        "Demonstration-only simulated servicing snapshot. Strictly isolated and quarantined from primary portfolio analytics and underwriting KPIs.",
        description="Notice confirming isolation from primary underwriting"
    )


# --- 9. Standard Error Envelopes ---

class ErrorResponse(BaseSchema):
    detail: str = Field(..., description="Human-readable error description")
    error_code: Optional[str] = Field(None, description="Specific error classification code")
