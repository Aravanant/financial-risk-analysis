"""Data access layer / repository functions for RiskLens AI.

Enforces:
1. Fully parameterized SQL queries, regex-validated filter constraints, and strict sort-column whitelisting.
2. Read-only queries against SQLite analytical views and fact/dimension tables.
3. Separation of quarantined simulated servicing from underwriting queries.
4. Strict column whitelisting for sorting and filtering.
"""

import sqlite3
from typing import Optional, List, Dict, Any, Tuple


# Safe column whitelist for application sorting
ALLOWED_SORT_COLUMNS = {
    "application_id": "f.application_id",
    "requested_loan_amount": "f.requested_loan_amount",
    "sanctioned_approved_amount": "f.sanctioned_approved_amount",
    "bureau_credit_score": "f.bureau_credit_score",
    "proprietary_risk_score": "f.proprietary_risk_score",
    "annual_income": "f.annual_income",
    "age": "f.age"
}


def get_portfolio_kpis(conn: Any) -> Dict[str, Any]:
    """Retrieve primary portfolio KPIs from vw_portfolio_kpis view."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM vw_portfolio_kpis;")
    row = cur.fetchone()
    if not row:
        raise RuntimeError("vw_portfolio_kpis returned no rows")
    return dict(row)


def get_channel_performance(conn: Any) -> List[Dict[str, Any]]:
    """Retrieve channel-level performance metrics from vw_channel_performance."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM vw_channel_performance ORDER BY channel_id;")
    return [dict(r) for r in cur.fetchall()]


def get_loan_purposes(conn: Any) -> List[Dict[str, Any]]:
    """Retrieve loan purpose volume and haircut metrics from vw_loan_purpose_analysis."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM vw_loan_purpose_analysis ORDER BY purpose_id;")
    return [dict(r) for r in cur.fetchall()]


def get_haircut_summary(conn: Any) -> Dict[str, Any]:
    """Retrieve portfolio-level aggregate haircut summary from vw_portfolio_haircut_summary."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM vw_portfolio_haircut_summary;")
    row = cur.fetchone()
    if not row:
        raise RuntimeError("vw_portfolio_haircut_summary returned no rows")
    return dict(row)


def get_risk_tiers(conn: Any) -> List[Dict[str, Any]]:
    """Retrieve source-provided risk tier statistics from vw_risk_tier_summary."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM vw_risk_tier_summary;")
    return [dict(r) for r in cur.fetchall()]


def get_data_quality_metrics(conn: Any) -> Dict[str, Any]:
    """Retrieve audit flag counts and missingness metrics from vw_data_quality_metrics."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM vw_data_quality_metrics;")
    row = cur.fetchone()
    if not row:
        raise RuntimeError("vw_data_quality_metrics returned no rows")
    return dict(row)


def get_applications_paginated(
    conn: Any,
    page: int = 1,
    page_size: int = 50,
    decision: Optional[str] = None,
    channel: Optional[str] = None,
    loan_purpose: Optional[str] = None,
    risk_tier: Optional[str] = None,
    has_invalid_financials: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc"
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Retrieve paginated application records with validated optional filters using parameterized SQL.
    
    Returns:
        (total_count: int, items: List[Dict[str, Any]])
    """
    where_clauses = ["1=1"]
    params: List[Any] = []
    
    if decision is not None:
        where_clauses.append("f.underwriting_decision = ?")
        params.append(decision)
        
    if channel is not None:
        where_clauses.append("c.channel_name = ?")
        params.append(channel)
        
    if loan_purpose is not None:
        where_clauses.append("p.purpose_name = ?")
        params.append(loan_purpose)
        
    if risk_tier is not None:
        where_clauses.append("f.risk_tier = ?")
        params.append(risk_tier)
        
    if has_invalid_financials is not None:
        where_clauses.append("f.has_invalid_financials = ?")
        params.append(has_invalid_financials)
        
    where_sql = " AND ".join(where_clauses)
    
    # 1. Total count query
    count_sql = f"""
        SELECT COUNT(*) 
        FROM fct_loan_application f
        JOIN dim_channel c ON f.channel_id = c.channel_id
        JOIN dim_loan_purpose p ON f.purpose_id = p.purpose_id
        JOIN dim_residence_property_location l ON f.location_property_id = l.location_property_id
        WHERE {where_sql};
    """
    cur = conn.cursor()
    cur.execute(count_sql, tuple(params))
    total_count = cur.fetchone()[0]
    
    # 2. Sorting clause (strictly whitelisted column names)
    order_col = ALLOWED_SORT_COLUMNS.get(sort_by, "f.application_id")
    direction = "DESC" if str(sort_order).strip().lower() == "desc" else "ASC"
    
    # 3. Pagination offset
    offset = (page - 1) * page_size
    
    # 4. Data query
    data_sql = f"""
        SELECT 
            f.application_id,
            f.source_row_ordinal,
            f.age,
            f.gender,
            f.marital_status,
            f.education_level,
            f.employment_status,
            f.job_experience_years,
            f.dependents,
            f.annual_income,
            f.monthly_income_reported,
            f.monthly_income_calculated,
            f.savings_balance,
            f.checking_balance,
            f.total_assets,
            f.total_liabilities,
            f.monthly_debt_payment,
            f.net_worth,
            f.bank_account_tenure_months,
            f.requested_loan_amount,
            f.requested_term_months,
            f.interest_rate,
            f.debt_to_income_ratio,
            f.co_applicant_flag,
            f.collateral_flag,
            f.bureau_credit_score,
            f.bureau_existing_loans,
            f.bureau_late_payments_2yr,
            f.bureau_credit_history_years,
            f.bureau_prior_loan_status,
            f.proprietary_risk_score,
            f.risk_tier,
            f.normalized_risk_score,
            f.underwriting_decision,
            f.sanctioned_approved_amount,
            f.is_approved,
            f.has_missing_sanctioned_amount,
            c.channel_name,
            p.purpose_name,
            l.region,
            l.residential_status,
            l.property_ownership,
            f.has_invalid_annual_income,
            f.has_invalid_loan_amount,
            f.has_invalid_savings_balance,
            f.has_invalid_age,
            f.has_invalid_financials
        FROM fct_loan_application f
        JOIN dim_channel c ON f.channel_id = c.channel_id
        JOIN dim_loan_purpose p ON f.purpose_id = p.purpose_id
        JOIN dim_residence_property_location l ON f.location_property_id = l.location_property_id
        WHERE {where_sql}
        ORDER BY {order_col} {direction}
        LIMIT ? OFFSET ?;
    """
    
    query_params = tuple(params) + (page_size, offset)
    cur.execute(data_sql, query_params)
    items = [dict(r) for r in cur.fetchall()]
    
    return total_count, items


def get_application_by_id(conn: Any, application_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single loan application by ID joined with conformed dimensions.
    
    Returns:
        Dict of application data or None if not found.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            f.application_id,
            f.source_row_ordinal,
            f.age,
            f.gender,
            f.marital_status,
            f.education_level,
            f.employment_status,
            f.job_experience_years,
            f.dependents,
            f.annual_income,
            f.monthly_income_reported,
            f.monthly_income_calculated,
            f.savings_balance,
            f.checking_balance,
            f.total_assets,
            f.total_liabilities,
            f.monthly_debt_payment,
            f.net_worth,
            f.bank_account_tenure_months,
            f.requested_loan_amount,
            f.requested_term_months,
            f.interest_rate,
            f.debt_to_income_ratio,
            f.co_applicant_flag,
            f.collateral_flag,
            f.bureau_credit_score,
            f.bureau_existing_loans,
            f.bureau_late_payments_2yr,
            f.bureau_credit_history_years,
            f.bureau_prior_loan_status,
            f.proprietary_risk_score,
            f.risk_tier,
            f.normalized_risk_score,
            f.underwriting_decision,
            f.sanctioned_approved_amount,
            f.is_approved,
            f.has_missing_sanctioned_amount,
            c.channel_name,
            p.purpose_name,
            l.region,
            l.residential_status,
            l.property_ownership,
            f.has_invalid_annual_income,
            f.has_invalid_loan_amount,
            f.has_invalid_savings_balance,
            f.has_invalid_age,
            f.has_invalid_financials
        FROM fct_loan_application f
        JOIN dim_channel c ON f.channel_id = c.channel_id
        JOIN dim_loan_purpose p ON f.purpose_id = p.purpose_id
        JOIN dim_residence_property_location l ON f.location_property_id = l.location_property_id
        WHERE f.application_id = ?;
    """, (application_id,))
    
    row = cur.fetchone()
    return dict(row) if row else None


def get_servicing_demo_record(conn: Any, application_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve quarantined synthetic servicing record for demonstration purposes.
    
    Isolated strictly to demo_synthetic_repayment_snapshot table.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            application_id,
            simulated_due_date,
            simulated_payment_date,
            simulated_amount_due_cu,
            simulated_amount_paid_cu,
            simulated_days_late,
            simulated_payment_status,
            simulated_disbursement_amount_cu,
            simulated_outstanding_balance_cu
        FROM demo_synthetic_repayment_snapshot
        WHERE application_id = ?;
    """, (application_id,))
    row = cur.fetchone()
    return dict(row) if row else None
