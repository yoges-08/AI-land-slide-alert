"""Weather Ingestion Package (Milestone 3)

Provides satellite and numerical model precipitation ingestors:
- MOSDAC_INSAT3D_QPE (ISRO MOSDAC INSAT-3D/3DR QPE & IMSRA - Priority 1)
- NASA_GPM_IMERG (NASA Global Precipitation Measurement - Priority 2)
- OPEN_METEO (Open-Meteo Ground Model - Priority 3)
"""
from backend.app.ingestion.sources.weather.mosdac_insat3d import MosdacInsat3dSource
from backend.app.ingestion.sources.weather.nasa_gpm import NasaGpmSource
from backend.app.ingestion.sources.weather.open_meteo import OpenMeteoSource

__all__ = ["MosdacInsat3dSource", "NasaGpmSource", "OpenMeteoSource"]
