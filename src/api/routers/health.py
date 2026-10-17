"""Health check router for RiskLens AI backend."""

from fastapi import APIRouter
from ..database import check_db_health
from ..schemas import HealthResponse

router = APIRouter(tags=["System Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System and Database Health Check",
    description="Inspects database connectivity, verified warehouse record counts, and schema integrity."
)
def get_health() -> HealthResponse:
    """Return application and database connectivity status."""
    info = check_db_health()
    return HealthResponse.model_validate(info)
