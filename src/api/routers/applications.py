"""Loan applications query and detail router."""

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from ..database import get_db_connection
from ..services import fetch_applications_paginated, fetch_application_by_id
from ..schemas import PaginatedApplicationsResponse, ApplicationSummary, ErrorResponse

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=PaginatedApplicationsResponse,
    summary="Paginated Application Records",
    description="Returns filtered, sorted, and paginated loan applications with conformed dimension attributes."
)
def list_applications(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of records per page (1-100)"),
    decision: Optional[str] = Query(
        None,
        pattern="^(Approved|Rejected)$",
        description="Filter by underwriting decision ('Approved', 'Rejected')"
    ),
    channel: Optional[str] = Query(
        None,
        pattern="^(Online|Branch|Mobile App|Agent)$",
        description="Filter by channel ('Online', 'Branch', 'Mobile App', 'Agent')"
    ),
    loan_purpose: Optional[str] = Query(
        None,
        pattern="^(Business|Car|Debt Consolidation|Education|Home|Medical|Personal|Vehicle)$",
        description="Filter by verified loan purpose category"
    ),
    risk_tier: Optional[str] = Query(
        None,
        pattern="^(Low|Medium|High)$",
        description="Filter by source risk tier ('Low', 'Medium', 'High')"
    ),
    has_invalid_financials: Optional[int] = Query(
        None,
        ge=0,
        le=1,
        description="Filter by composite invalid financials audit flag (1=Corrupted, 0=Clean)"
    ),
    sort_by: Optional[str] = Query(
        "application_id",
        pattern="^(application_id|requested_loan_amount|sanctioned_approved_amount|bureau_credit_score|proprietary_risk_score|annual_income|age)$",
        description="Column to sort by"
    ),
    sort_order: Optional[str] = Query(
        "asc",
        pattern="^(asc|desc|ASC|DESC)$",
        description="Sort order ('asc', 'desc')"
    ),
    conn: sqlite3.Connection = Depends(get_db_connection)
) -> PaginatedApplicationsResponse:
    """Fetch paginated application records with validated optional filters."""
    return fetch_applications_paginated(
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


@router.get(
    "/{application_id}",
    response_model=ApplicationSummary,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Application ID not found"}
    },
    summary="Get Single Application by ID",
    description="Returns full application attributes and joined conformed dimensions for a specific application ID."
)
def get_application(
    application_id: int = Path(..., ge=1, description="Application identifier"),
    conn: sqlite3.Connection = Depends(get_db_connection)
) -> ApplicationSummary:
    """Fetch single application by ID or return 404."""
    app = fetch_application_by_id(conn, application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    return app
