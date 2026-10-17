"""Channel performance analytics router."""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends
from ..database import get_db_connection
from ..services import fetch_channel_performance
from ..schemas import ChannelPerformanceItem

router = APIRouter(prefix="/channels", tags=["Channel Performance"])


@router.get(
    "",
    response_model=List[ChannelPerformanceItem],
    summary="Channel-Level Origination Performance",
    description="Returns origination volume, approval rates, and financial totals for all 4 channels (Online, Branch, Mobile App, Agent)."
)
def get_channel_metrics(
    conn: sqlite3.Connection = Depends(get_db_connection)
) -> List[ChannelPerformanceItem]:
    """Fetch channel performance analytics."""
    return fetch_channel_performance(conn)
