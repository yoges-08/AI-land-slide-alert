import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LANDSAFE-NER"
    API_V1_STR: str = "/api"
    LANDSAFE_MODE: str = os.getenv("LANDSAFE_MODE", "production")  # production | demo
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./landsafe.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Allowed CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # External API Base URLs & Keys
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    NASA_GIBS_WMTS_URL: str = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
    NASA_FIRMS_MAP_KEY: str = os.getenv("NASA_FIRMS_MAP_KEY", "")
    USGS_FDSN_URL: str = "https://earthquake.usgs.gov/fdsnws/event/1"
    MOSDAC_BASE_URL: str = "https://www.mosdac.gov.in"
    CDSE_BASE_URL: str = "https://catalogue.dataspace.copernicus.eu"
    
    # Advisory & Prototype Disclaimer (Required by Section 0)
    PROTOTYPE_DISCLAIMER: str = (
        "LANDSAFE-NER is an academic prototype and advisory service. "
        "It is NOT an official disaster-warning system. IMD, NDMA, and NCS are the official authorities in India. "
        "Do not use for real-world emergency decisions."
    )

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

settings = Settings()
