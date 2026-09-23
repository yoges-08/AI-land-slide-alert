"""Central configuration.

Every threshold, origin, source cadence and disclaimer string lives here or in
.env — never inline in a service. Source cadences drive the freshness tiers, so
they are stated with their documented provider cadence, not guessed.
"""
import os
from typing import Literal
from pydantic_settings import BaseSettings

# --- Advisory notice -------------------------------------------------------
# LANDSAFE-NER is advisory. IMD, NDMA and NCS are the sole official authorities.
# This string is rendered on every alert, report and page.
ADVISORY_NOTICE = (
    "ADVISORY ONLY. LANDSAFE-NER is an academic, non-commercial monitoring aid. "
    "It is not an official warning system and carries no authority. "
    "The India Meteorological Department (IMD), the National Disaster Management "
    "Authority (NDMA) and the National Center for Seismology (NCS) are the sole "
    "official sources for warnings and emergency instructions. "
    "Always follow IMD/NDMA/NCS guidance over anything shown here."
)


class Settings(BaseSettings):
    PROJECT_NAME: str = "LANDSAFE-NER"
    API_V1_STR: str = "/api"

    # production | demo. Default production. See backend/app/core/mode.py.
    LANDSAFE_MODE: Literal["production", "demo"] = "production"

    # M1 replaces SQLite with PostgreSQL+PostGIS. Left here so nothing breaks
    # before the migration lands; no code currently opens a connection.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./landsafe.db")

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://ai-land-slide-alert.vercel.app"

    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    OPEN_METEO_TIMEOUT_S: float = 15.0
    OPEN_METEO_RETRIES: int = 2
    # Free tier: <10,000 calls/day, non-commercial. Enforced client-side in M2.
    OPEN_METEO_DAILY_CALL_BUDGET: int = 10000

    NASA_GIBS_WMTS_URL: str = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

    SCHEDULER_AUTOSTART: bool = True

    EARTHDATA_USERNAME: str = ""
    EARTHDATA_PASSWORD: str = ""
    EARTHDATA_TOKEN: str = ""

    MOSDAC_USERNAME: str = ""
    MOSDAC_PASSWORD: str = ""
    MOSDAC_AUTH_TOKEN: str = ""

    NASA_FIRMS_MAP_KEY: str = ""
    CDSE_CLIENT_ID: str = ""
    CDSE_CLIENT_SECRET: str = ""

    # AI Weather & Hazard Assistant LLM configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # gemini | openai | fallback
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", "")))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    LLM_TEMPERATURE: float = 0.2

    PROTOTYPE_DISCLAIMER: str = ADVISORY_NOTICE

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()


# --- Freshness tiers -------------------------------------------------------
# Thresholds are multiples of each source's DOCUMENTED cadence, not guesses.
# FRESH <= 1x cadence, RECENT <= 2x, AGING <= 6x, STALE beyond, OFFLINE when the
# source itself is failing.
FRESHNESS_MULTIPLIERS = {"FRESH": 1, "RECENT": 2, "AGING": 6}

# cadence_s: provider's documented delivery interval.
# liveness: LIVE only where the provider documents real-time delivery.
# pass_based: True where staleness is a satellite repeat cycle, not a clock —
#   NISAR's 12-day repeat means "latest available pass", so simple time-based
#   staleness would mark a perfectly good scene STALE on day 3.
SOURCE_CADENCE = {
    "open_meteo": {
        "cadence_s": 3600, "liveness": "LATEST_AVAILABLE", "pass_based": False,
        "licence": "Open-Meteo free tier, non-commercial", "verified": True,
    },
    "insat_3d_qpe": {
        "cadence_s": 1800, "liveness": "NEAR_REAL_TIME", "pass_based": False,
        "licence": "MOSDAC research-only", "verified": True,
    },
    "gpm_imerg": {
        "cadence_s": 1800, "liveness": "NEAR_REAL_TIME", "pass_based": False,
        "licence": "NASA open data", "verified": True,
    },
    "firms": {
        "cadence_s": 10800, "liveness": "NEAR_REAL_TIME", "pass_based": False,
        "licence": "NASA FIRMS open data", "verified": True,
    },
    "usgs_fdsn": {
        "cadence_s": 300, "liveness": "NEAR_REAL_TIME", "pass_based": False,
        "licence": "USGS public domain", "verified": True,
    },
    "nisar_ssar": {
        "cadence_s": 12 * 86400, "liveness": "LATEST_AVAILABLE", "pass_based": True,
        "licence": "India Space Policy 2023 open data", "verified": False,
    },
    "sentinel1": {
        "cadence_s": 6 * 86400, "liveness": "LATEST_AVAILABLE", "pass_based": True,
        "licence": "Copernicus free and open", "verified": True,
    },
    "resourcesat_liss": {
        "cadence_s": 5 * 86400, "liveness": "LATEST_AVAILABLE", "pass_based": True,
        "licence": "Bhoonidhi free tier", "verified": False,
    },
    "sentinel2": {
        "cadence_s": 5 * 86400, "liveness": "LATEST_AVAILABLE", "pass_based": True,
        "licence": "Copernicus free and open", "verified": True,
    },
}

# Sources that exist in config but must not be scheduled or queried until their
# API has actually been exercised. Enforced by the ingestion registry in M2.
PENDING_VERIFICATION = [k for k, v in SOURCE_CADENCE.items() if not v["verified"]]
