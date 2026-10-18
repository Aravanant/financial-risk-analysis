"""Risk tier summary analytics router."""

from typing import List, Any
from fastapi import APIRouter, Depends
from ..database import get_db_connection
from ..services import fetch_risk_tiers
from ..schemas import RiskTierItem

router = APIRouter(prefix="/risk-tiers", tags=["Risk Tiers"])


@router.get(
    "",
    response_model=List[RiskTierItem],
    summary="Source-Provided Risk Tier Distribution",
    description=(
        "Returns application volumes, approval rates, and score averages across source-provided Default_Risk tiers. "
        "Explicitly documents that proprietary risk score is an uncalibrated scorecard (0-100), not default probability."
    )
)
def get_risk_tier_metrics(
    conn: Any = Depends(get_db_connection)
) -> List[RiskTierItem]:
    """Fetch risk tier analytics."""
    return fetch_risk_tiers(conn)
