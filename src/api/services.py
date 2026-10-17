"""Analytical service layer for RiskLens AI.

Orchestrates data access, formats compound analytics, enforces business domain rules,
and packages responses into validated Pydantic schemas.
"""

import math
import sqlite3
from typing import Optional, List, Dict, Any
from . import crud
from .schemas import (
    PortfolioKPIsResponse,
    ChannelPerformanceItem,
    LoanPurposeItem,
    HaircutResponse,
    PortfolioHaircutSummary,
    HaircutExclusions,
    RiskTierItem,
    DataQualityResponse,
    DataQualityAuditFlags,
    DataQualityMissingValues,
    PaginatedApplicationsResponse,
    ApplicationSummary,
    ServicingDemoResponse
)


def fetch_portfolio_kpis(conn: sqlite3.Connection) -> PortfolioKPIsResponse:
    """Fetch and package primary portfolio KPIs."""
    data = crud.get_portfolio_kpis(conn)
    return PortfolioKPIsResponse(
        total_applications=data["total_applications"],
        approved_applications=data["approved_applications"],
        rejected_applications=data["rejected_applications"],
        approval_rate_pct=data["approval_rate_pct"],
        rejection_rate_pct=data["rejection_rate_pct"],
        total_requested_cu=data["total_requested_cu"],
        total_sanctioned_cu=data["total_sanctioned_cu"],
        invalid_financials_count=data["invalid_financials_count"],
        missing_sanctioned_count=data["missing_sanctioned_count"],
        currency_unit="CU"
    )


def fetch_channel_performance(conn: sqlite3.Connection) -> List[ChannelPerformanceItem]:
    """Fetch channel-level performance breakdown."""
    rows = crud.get_channel_performance(conn)
    return [
        ChannelPerformanceItem(
            channel_id=r["channel_id"],
            channel_name=r["channel_name"],
            total_applications=r["total_applications"],
            approved_applications=r["approved_applications"],
            rejected_applications=r["rejected_applications"],
            approval_rate_pct=r["approval_rate_pct"],
            total_requested_cu=r["total_requested_cu"],
            total_sanctioned_cu=r["total_sanctioned_cu"],
            currency_unit="CU"
        )
        for r in rows
    ]


def fetch_loan_purposes(conn: sqlite3.Connection) -> List[LoanPurposeItem]:
    """Fetch purpose-level volume and haircut metrics across all 8 verified categories."""
    rows = crud.get_loan_purposes(conn)
    return [
        LoanPurposeItem(
            purpose_id=r["purpose_id"],
            purpose_name=r["purpose_name"],
            total_applications=r["total_applications"],
            approved_applications=r["approved_applications"],
            rejected_applications=r["rejected_applications"],
            approval_rate_pct=r["approval_rate_pct"],
            total_requested_cu=r["total_requested_cu"],
            total_sanctioned_cu=r["total_sanctioned_cu"],
            haircut_eligible_count=r["haircut_eligible_count"],
            haircut_eligible_requested_cu=r["haircut_eligible_requested_cu"],
            haircut_eligible_sanctioned_cu=r["haircut_eligible_sanctioned_cu"],
            haircut_total_cu=r["haircut_total_cu"],
            aggregate_haircut_pct=r["aggregate_haircut_pct"],
            haircut_excluded_count=r["haircut_excluded_count"],
            currency_unit="CU"
        )
        for r in rows
    ]


def fetch_haircut_analysis(conn: sqlite3.Connection) -> HaircutResponse:
    """
    Fetch comprehensive portfolio-level and purpose-level haircut metrics.
    
    Guarantees:
    - Aggregate portfolio haircut is calculated from aggregate sums:
      ROUND((1.0 - (SUM(sanctioned) / SUM(requested))) * 100.0, 4)
      and NOT by taking the arithmetic average of purpose-level percentages.
    """
    summary_data = crud.get_haircut_summary(conn)
    purpose_rows = crud.get_loan_purposes(conn)
    
    exclusions = HaircutExclusions(
        excluded_rejected_count=summary_data["excluded_rejected_count"],
        excluded_approved_missing_sanction_count=summary_data["excluded_approved_missing_sanction_count"],
        excluded_approved_missing_requested_count=summary_data["excluded_approved_missing_requested_count"],
        total_excluded_count=summary_data["total_excluded_count"]
    )
    
    portfolio_summary = PortfolioHaircutSummary(
        total_portfolio_applications=summary_data["total_portfolio_applications"],
        eligible_applications_count=summary_data["eligible_applications_count"],
        total_eligible_requested_cu=summary_data["total_eligible_requested_cu"],
        total_eligible_sanctioned_cu=summary_data["total_eligible_sanctioned_cu"],
        total_haircut_cu=summary_data["total_haircut_cu"],
        aggregate_haircut_pct=summary_data["aggregate_haircut_pct"],
        currency_unit="CU",
        exclusions=exclusions,
        calculation_notes=(
            "Portfolio aggregate haircut is computed from aggregate eligible principal sums: "
            "1.0 - (SUM(eligible_sanctioned_cu) / SUM(eligible_requested_cu)), "
            "preserving true financial weighting rather than averaging category percentages."
        )
    )
    
    purposes = [
        LoanPurposeItem(
            purpose_id=r["purpose_id"],
            purpose_name=r["purpose_name"],
            total_applications=r["total_applications"],
            approved_applications=r["approved_applications"],
            rejected_applications=r["rejected_applications"],
            approval_rate_pct=r["approval_rate_pct"],
            total_requested_cu=r["total_requested_cu"],
            total_sanctioned_cu=r["total_sanctioned_cu"],
            haircut_eligible_count=r["haircut_eligible_count"],
            haircut_eligible_requested_cu=r["haircut_eligible_requested_cu"],
            haircut_eligible_sanctioned_cu=r["haircut_eligible_sanctioned_cu"],
            haircut_total_cu=r["haircut_total_cu"],
            aggregate_haircut_pct=r["aggregate_haircut_pct"],
            haircut_excluded_count=r["haircut_excluded_count"],
            currency_unit="CU"
        )
        for r in purpose_rows
    ]
    
    return HaircutResponse(
        portfolio_summary=portfolio_summary,
        by_purpose=purposes
    )


def fetch_risk_tiers(conn: sqlite3.Connection) -> List[RiskTierItem]:
    """Fetch source-provided risk tier summaries."""
    rows = crud.get_risk_tiers(conn)
    return [
        RiskTierItem(
            risk_tier=r["risk_tier"],
            total_applications=r["total_applications"],
            approved_count=r["approved_count"],
            rejected_count=r["rejected_count"],
            tier_approval_rate_pct=r["tier_approval_rate_pct"],
            avg_proprietary_risk_score=r["avg_proprietary_risk_score"],
            avg_bureau_credit_score=r["avg_bureau_credit_score"],
            avg_normalized_risk_score=r["avg_normalized_risk_score"]
        )
        for r in rows
    ]


def fetch_data_quality_metrics(conn: sqlite3.Connection) -> DataQualityResponse:
    """Fetch comprehensive data quality audit flags, missingness counts, and exclusions."""
    data = crud.get_data_quality_metrics(conn)
    
    audit_flags = DataQualityAuditFlags(
        invalid_annual_income_flag_count=data["invalid_annual_income_flag_count"],
        invalid_loan_amount_flag_count=data["invalid_loan_amount_flag_count"],
        invalid_savings_balance_flag_count=data["invalid_savings_balance_flag_count"],
        invalid_age_flag_count=data["invalid_age_flag_count"],
        composite_invalid_financials_count=data["composite_invalid_financials_count"]
    )
    
    missing_values = DataQualityMissingValues(
        missing_sanctioned_amount_count=data["missing_sanctioned_amount_count"],
        missing_sanctioned_approved_count=data["missing_sanctioned_approved_count"],
        missing_sanctioned_rejected_count=data["missing_sanctioned_rejected_count"],
        genuine_zero_sanctioned_rejected_count=data["genuine_zero_sanctioned_rejected_count"],
        missing_bureau_credit_score_count=data["missing_bureau_credit_score_count"],
        missing_age_count=data["missing_age_count"],
        missing_annual_income_count=data["missing_annual_income_count"],
        missing_savings_balance_count=data["missing_savings_balance_count"],
        missing_requested_loan_amount_count=data["missing_requested_loan_amount_count"],
        missing_interest_rate_count=data["missing_interest_rate_count"],
        missing_debt_to_income_ratio_count=data["missing_debt_to_income_ratio_count"],
        missing_proprietary_risk_score_count=data["missing_proprietary_risk_score_count"]
    )
    
    haircut_exclusions = HaircutExclusions(
        excluded_rejected_count=data["haircut_excluded_rejected_count"],
        excluded_approved_missing_sanction_count=data["haircut_excluded_approved_missing_sanction_count"],
        excluded_approved_missing_requested_count=data["haircut_excluded_approved_missing_requested_count"],
        total_excluded_count=data["haircut_total_excluded_count"]
    )
    
    return DataQualityResponse(
        total_applications=data["total_applications"],
        audit_flags=audit_flags,
        missing_values=missing_values,
        haircut_exclusions=haircut_exclusions
    )


def fetch_applications_paginated(
    conn: sqlite3.Connection,
    page: int = 1,
    page_size: int = 50,
    decision: Optional[str] = None,
    channel: Optional[str] = None,
    loan_purpose: Optional[str] = None,
    risk_tier: Optional[str] = None,
    has_invalid_financials: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc"
) -> PaginatedApplicationsResponse:
    """Fetch paginated application summaries with total pages calculation."""
    total_count, rows = crud.get_applications_paginated(
        conn=conn,
        page=page,
        page_size=page_size,
        decision=decision,
        channel=channel,
        loan_purpose=loan_purpose,
        risk_tier=risk_tier,
        has_invalid_financials=has_invalid_financials,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
    items = [ApplicationSummary.model_validate(r) for r in rows]
    
    return PaginatedApplicationsResponse(
        total_items=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items
    )


def fetch_application_by_id(conn: sqlite3.Connection, application_id: int) -> Optional[ApplicationSummary]:
    """Fetch a single application record by ID."""
    row = crud.get_application_by_id(conn, application_id)
    if not row:
        return None
    return ApplicationSummary.model_validate(row)


def fetch_servicing_demo_record(conn: sqlite3.Connection, application_id: int) -> Optional[ServicingDemoResponse]:
    """Fetch demonstration-only synthetic servicing record."""
    row = crud.get_servicing_demo_record(conn, application_id)
    if not row:
        return None
    return ServicingDemoResponse.model_validate(row)
