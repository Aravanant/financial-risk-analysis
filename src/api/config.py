"""Configuration settings for RiskLens AI FastAPI Backend.

Environment Variables:
- RISKLENS_DB_PATH: Path to SQLite database (default: data/processed/risklens_analytics.db)
- RISKLENS_CORS_ORIGINS: Comma-separated list of allowed CORS origins
- RISKLENS_API_PREFIX: API route prefix (default: /api/v1)
- RISKLENS_ENV: Environment name ('development', 'testing', 'production')
"""

import os
from typing import List


class Settings:
    """Application configuration settings."""

    ENV: str = os.getenv("RISKLENS_ENV", "development")
    
    # Base directory of the repository
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    # Path to verified SQLite analytics database
    DEFAULT_DB_PATH: str = os.path.join(BASE_DIR, "data", "processed", "risklens_analytics.db")
    DB_PATH: str = os.getenv("RISKLENS_DB_PATH", DEFAULT_DB_PATH)
    
    API_V1_PREFIX: str = os.getenv("RISKLENS_API_PREFIX", "/api/v1")
    
    # Application metadata
    APP_TITLE: str = "RiskLens AI Analytics API"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = (
        "Enterprise-grade Analytical SQL and REST API engine for RiskLens AI. "
        "Delivers validated portfolio KPIs, channel performance, loan purpose breakdown, "
        "aggregate haircut metrics, source-provided risk tiers, and data quality metrics."
    )
    SCHEMA_VERSION: str = "2.0.0"
    CURRENCY_UNIT: str = "CU"
    
    # CORS configuration: explicit origins, avoiding wildcard '*' in production
    @property
    def cors_origins(self) -> List[str]:
        raw_origins = os.getenv("RISKLENS_CORS_ORIGINS", "")
        if raw_origins.strip():
            return [o.strip() for o in raw_origins.split(",") if o.strip()]
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]


settings = Settings()
