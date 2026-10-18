"""Loan purpose breakdown and financial analytics router."""

from typing import List, Any
from fastapi import APIRouter, Depends
from ..database import get_db_connection
from ..services import fetch_loan_purposes
from ..schemas import LoanPurposeItem

router = APIRouter(prefix="/loan-purposes", tags=["Loan Purpose Analysis"])


@router.get(
    "",
    response_model=List[LoanPurposeItem],
    summary="Loan Purpose Financial Breakdown",
    description="Returns volume, approval rates, requested/sanctioned volumes, and haircut metrics across all 8 verified loan purposes."
)
def get_loan_purpose_metrics(
    conn: Any = Depends(get_db_connection)
) -> List[LoanPurposeItem]:
    """Fetch loan purpose analytics."""
    return fetch_loan_purposes(conn)
