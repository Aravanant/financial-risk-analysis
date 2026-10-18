"""Underwriting haircut metrics router."""

from typing import Any
from fastapi import APIRouter, Depends
from ..database import get_db_connection
from ..services import fetch_haircut_analysis
from ..schemas import HaircutResponse

router = APIRouter(prefix="/haircut", tags=["Underwriting Haircut"])


@router.get(
    "",
    response_model=HaircutResponse,
    summary="Portfolio and Purpose Underwriting Haircut Analysis",
    description=(
        "Returns overall and category-level haircut metrics (requested vs sanctioned difference). "
        "Includes full eligibility counts (48,022 approved) and audit exclusion reasons (51,978 excluded)."
    )
)
def get_haircut_metrics(
    conn: Any = Depends(get_db_connection)
) -> HaircutResponse:
    """Fetch underwriting haircut metrics and eligibility audit."""
    return fetch_haircut_analysis(conn)
