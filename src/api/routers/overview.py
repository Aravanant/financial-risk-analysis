"""Portfolio overview and high-level KPI endpoints."""

from typing import Any
from fastapi import APIRouter, Depends
from ..database import get_db_connection
from ..services import fetch_portfolio_kpis
from ..schemas import PortfolioKPIsResponse

router = APIRouter(prefix="/overview", tags=["Portfolio KPIs"])


@router.get(
    "",
    response_model=PortfolioKPIsResponse,
    summary="Portfolio KPI Summary",
    description="Returns aggregate portfolio-level underwriting metrics: totals, approval rate, sanctioned amounts, and quality issues."
)
def get_portfolio_overview(
    conn: Any = Depends(get_db_connection)
) -> PortfolioKPIsResponse:
    """Fetch primary portfolio KPI summary from analytical SQL view."""
    return fetch_portfolio_kpis(conn)
