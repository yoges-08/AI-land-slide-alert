import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LANDSAFE-NER"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./landsafe.db")
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    NASA_GIBS_WMTS_URL: str = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
    
    PROTOTYPE_DISCLAIMER: str = (
        "LANDSAFE-NER is a B.Tech AI & Data Science academic prototype. "
        "It is NOT an official government disaster-warning system. "
        "Risk levels are based on prototype thresholds for demonstration purposes only. "
        "Do not use for real-world emergency decisions."
    )

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
