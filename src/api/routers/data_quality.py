"""Data quality metrics and audit flags router."""

import sqlite3
from fastapi import APIRouter, Depends
from ..database import get_db_connection
from ..services import fetch_data_quality_metrics
from ..schemas import DataQualityResponse

router = APIRouter(prefix="/data-quality", tags=["Data Quality & Audit"])


@router.get(
    "",
    response_model=DataQualityResponse,
    summary="Data Quality Audit and Missingness Ledger",
    description="Returns audit flag counts for sanitized negative values/ages, missingness breakdowns, genuine zeros, and haircut exclusions."
)
def get_data_quality_report(
    conn: sqlite3.Connection = Depends(get_db_connection)
) -> DataQualityResponse:
    """Fetch data quality metrics."""
    return fetch_data_quality_metrics(conn)
