/**
 * RiskLens AI — TypeScript API Data Contracts
 * 
 * Synchronized with FastAPI Pydantic schemas in src/api/schemas.py.
 * Preserves source NULLs (null in TypeScript) and CU currency notation.
 */

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  connected: boolean;
  database_backend?: 'postgresql' | 'sqlite' | string | null;
  database_size_bytes?: number | null;
  schema_version: string;
  record_counts?: {
    fct_count: number;
    channel_count: number;
    purpose_count: number;
    location_count: number;
    demo_servicing_count: number;
  } | null;
  error?: string | null;
}

export interface PortfolioKPIs {
  total_applications: number;
  approved_applications: number;
  rejected_applications: number;
  approval_rate_pct: number;
  rejection_rate_pct: number;
  total_requested_cu: number;
  total_sanctioned_cu: number;
  invalid_financials_count: number;
  missing_sanctioned_count: number;
  currency_unit: string;
}

export interface ChannelPerformanceItem {
  channel_id: number;
  channel_name: 'Online' | 'Branch' | 'Mobile App' | 'Agent';
  total_applications: number;
  approved_applications: number;
  rejected_applications: number;
  approval_rate_pct: number;
  total_requested_cu: number;
  total_sanctioned_cu: number;
  currency_unit: string;
}

export interface LoanPurposeItem {
  purpose_id: number;
  purpose_name: string;
  total_applications: number;
  approved_applications: number;
  rejected_applications: number;
  approval_rate_pct: number;
  total_requested_cu: number;
  total_sanctioned_cu: number;
  haircut_eligible_count: number;
  haircut_eligible_requested_cu: number;
  haircut_eligible_sanctioned_cu: number;
  haircut_total_cu: number;
  aggregate_haircut_pct: number;
  haircut_excluded_count: number;
  currency_unit: string;
}

export interface HaircutExclusions {
  excluded_rejected_count: number;
  excluded_approved_missing_sanction_count: number;
  excluded_approved_missing_requested_count: number;
  total_excluded_count: number;
}

export interface PortfolioHaircutSummary {
  total_portfolio_applications: number;
  eligible_applications_count: number;
  total_eligible_requested_cu: number;
  total_eligible_sanctioned_cu: number;
  total_haircut_cu: number;
  aggregate_haircut_pct: number;
  currency_unit: string;
  exclusions: HaircutExclusions;
  calculation_notes: string;
}

export interface HaircutResponse {
  portfolio_summary: PortfolioHaircutSummary;
  by_purpose: LoanPurposeItem[];
}

export interface RiskTierItem {
  risk_tier: 'Low' | 'Medium' | 'High';
  total_applications: number;
  approved_count: number;
  rejected_count: number;
  tier_approval_rate_pct: number;
  avg_proprietary_risk_score: number;
  avg_bureau_credit_score: number;
  avg_normalized_risk_score: number;
  tier_notes: string;
}

export interface DataQualityAuditFlags {
  invalid_annual_income_flag_count: number;
  invalid_loan_amount_flag_count: number;
  invalid_savings_balance_flag_count: number;
  invalid_age_flag_count: number;
  composite_invalid_financials_count: number;
}

export interface DataQualityMissingValues {
  missing_sanctioned_amount_count: number;
  missing_sanctioned_approved_count: number;
  missing_sanctioned_rejected_count: number;
  genuine_zero_sanctioned_rejected_count: number;
  missing_bureau_credit_score_count: number;
  missing_age_count: number;
  missing_annual_income_count: number;
  missing_savings_balance_count: number;
  missing_requested_loan_amount_count: number;
  missing_interest_rate_count: number;
  missing_debt_to_income_ratio_count: number;
  missing_proprietary_risk_score_count: number;
}

export interface DataQualityResponse {
  total_applications: number;
  audit_flags: DataQualityAuditFlags;
  missing_values: DataQualityMissingValues;
  haircut_exclusions: HaircutExclusions;
}

export interface ApplicationSummary {
  application_id: number;
  source_row_ordinal: number;
  
  // Demographics
  age: number | null;
  gender: string | null;
  marital_status: string | null;
  education_level: string | null;
  employment_status: string | null;
  job_experience_years: number | null;
  dependents: number | null;
  
  // Financial Balances (CU)
  annual_income: number | null;
  monthly_income_reported: number | null;
  monthly_income_calculated: number | null;
  savings_balance: number | null;
  checking_balance: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  monthly_debt_payment: number | null;
  net_worth: number | null;
  bank_account_tenure_months: number | null;
  
  // Loan Request & Terms
  requested_loan_amount: number | null;
  requested_term_months: number | null;
  interest_rate: number | null;
  debt_to_income_ratio: number | null;
  co_applicant_flag: number | null;
  collateral_flag: number | null;
  
  // Credit Bureau
  bureau_credit_score: number | null;
  bureau_existing_loans: number | null;
  bureau_late_payments_2yr: number | null;
  bureau_credit_history_years: number | null;
  bureau_prior_loan_status: string | null;
  
  // Proprietary Scorecard
  proprietary_risk_score: number | null;
  risk_tier: 'Low' | 'Medium' | 'High' | null;
  normalized_risk_score: number | null;
  
  // Underwriting Outcome
  underwriting_decision: 'Approved' | 'Rejected';
  sanctioned_approved_amount: number | null;
  is_approved: number;
  has_missing_sanctioned_amount: number;
  
  // Conformed Dimension Details
  channel_name: string;
  purpose_name: string;
  region: string;
  residential_status: string;
  property_ownership: string;
  
  // Audit Flags
  has_invalid_annual_income: number;
  has_invalid_loan_amount: number;
  has_invalid_savings_balance: number;
  has_invalid_age: number;
  has_invalid_financials: number;
}

export interface PaginatedApplicationsResponse {
  total_items: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: ApplicationSummary[];
}

export interface ApplicationFilterParams {
  page?: number;
  page_size?: number;
  decision?: 'Approved' | 'Rejected';
  channel?: string;
  loan_purpose?: string;
  risk_tier?: string;
  has_invalid_financials?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ServicingDemoResponse {
  application_id: number;
  simulated_due_date: string | null;
  simulated_payment_date: string | null;
  simulated_amount_due_cu: number | null;
  simulated_amount_paid_cu: number | null;
  simulated_days_late: number | null;
  simulated_payment_status: string | null;
  simulated_disbursement_amount_cu: number | null;
  simulated_outstanding_balance_cu: number | null;
  demonstration_only: boolean;
  isolation_notice: string;
}

export interface ApiError {
  detail: string;
  error_code?: string;
}
