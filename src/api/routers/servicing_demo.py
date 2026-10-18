"""Demonstration-only simulated servicing router.

Strict Requirements:
1. Namespaced under /api/v1/demo/ to maintain strict separation from underwriting.
2. Queries demo_synthetic_repayment_snapshot exclusively.
3. Explicitly flags responses with demonstration_only: True.
4. Never feeds or mutates primary portfolio or haircut analytics.
"""

from typing import Any
from fastapi import APIRouter, Depends, Path, HTTPException, status
from ..database import get_db_connection
from ..services import fetch_servicing_demo_record
from ..schemas import ServicingDemoResponse, ErrorResponse

router = APIRouter(prefix="/demo/servicing-snapshot", tags=["Demonstration Servicing Snapshot"])


@router.get(
    "/{application_id}",
    response_model=ServicingDemoResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Synthetic servicing record not found"}
    },
    summary="Get Quarantined Synthetic Servicing Record",
    description=(
        "Returns the synthetic repayment snapshot record for demonstration/servicing purposes. "
        "Strictly quarantined from primary underwriting and portfolio analytics."
    )
)
def get_servicing_record(
    application_id: int = Path(..., ge=1, description="Application identifier"),
    conn: Any = Depends(get_db_connection)
) -> ServicingDemoResponse:
    """Fetch quarantined servicing demo record or return 404."""
    rec = fetch_servicing_demo_record(conn, application_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synthetic servicing record for application {application_id} not found"
        )
    return rec
