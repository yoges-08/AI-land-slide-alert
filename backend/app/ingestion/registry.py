"""Ingestion Source Registry (Milestone 2)

Manages discovery and lifecycle registration of all data providers.
Enforces PENDING_VERIFICATION gating — unverified sources (e.g. NISAR S-SAR,
Resourcesat LISS) are strictly blocked from automated scheduling until their
APIs are verified with active credentials.
"""
import logging
from typing import Dict, List, Optional, Type

from backend.app.core.config import PENDING_VERIFICATION, SOURCE_CADENCE
from backend.app.ingestion.base import BaseSource

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Registry managing active and unverified data sources."""

    def __init__(self):
        self._sources: Dict[str, BaseSource] = {}

    def _normalize_key(self, source_id: str) -> str:
        return source_id.strip().lower()

    def register(self, source: BaseSource) -> None:
        """Register a source instance."""
        key = self._normalize_key(source.source_id)
        self._sources[key] = source
        logger.info("[Registry] Registered data source: %s (%s)", source.source_id, source.name)

    def get(self, source_id: str) -> Optional[BaseSource]:
        """Retrieve a registered source by ID (case-insensitive)."""
        key = self._normalize_key(source_id)
        return self._sources.get(key)

    def is_verified(self, source_id: str) -> bool:
        """Check if source is verified for automated scheduling.
        Unverified sources in PENDING_VERIFICATION will return False.
        """
        key = self._normalize_key(source_id)
        # Check against PENDING_VERIFICATION config
        for pending_key in PENDING_VERIFICATION:
            if self._normalize_key(pending_key) == key:
                return False
        # Also check SOURCE_CADENCE definition if present
        if key in SOURCE_CADENCE:
            return SOURCE_CADENCE[key].get("verified", True)
        return True

    def list_sources(self) -> List[BaseSource]:
        """Return all registered sources."""
        return list(self._sources.values())

    def list_active_sources(self) -> List[BaseSource]:
        """Return registered sources that are both active and verified."""
        return [
            src for src in self._sources.values()
            if src.is_active and self.is_verified(src.source_id)
        ]

    def get_unverified_sources(self) -> List[str]:
        """Return list of sources currently blocked by PENDING_VERIFICATION."""
        return list(PENDING_VERIFICATION)

    def clear(self) -> None:
        """Clear registry (useful for test resets)."""
        self._sources.clear()


# Global Registry Instance
source_registry = SourceRegistry()


def init_default_sources() -> None:
    """Register core operational sources into registry."""
    try:
        from backend.app.ingestion.sources.weather import (
            MosdacInsat3dSource, NasaGpmSource, OpenMeteoSource
        )
        from backend.app.ingestion.sources.seismic import UsgsEarthquakeSource

        if not source_registry.get("MOSDAC_INSAT3D_QPE"):
            source_registry.register(MosdacInsat3dSource())
        if not source_registry.get("NASA_GPM_IMERG"):
            source_registry.register(NasaGpmSource())
        if not source_registry.get("OPEN_METEO"):
            source_registry.register(OpenMeteoSource())
        if not source_registry.get("USGS_FDSN"):
            source_registry.register(UsgsEarthquakeSource())
    except Exception as exc:
        logger.debug("Source auto-registration deferred: %s", exc)


init_default_sources()


def register_source(source: BaseSource) -> None:
    source_registry.register(source)


def get_source(source_id: str) -> Optional[BaseSource]:
    return source_registry.get(source_id)


def list_registered_sources() -> List[BaseSource]:
    return source_registry.list_sources()
