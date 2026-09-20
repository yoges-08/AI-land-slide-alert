"""Freshness tiers and data-status objects.

The single rule this module exists to enforce: when a source has no value for
us, we return a status, never a number. There is no code path here that can
invent, default or carry forward an observation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.core.config import FRESHNESS_MULTIPLIERS, SOURCE_CADENCE

FRESH, RECENT, AGING, STALE, OFFLINE = "FRESH", "RECENT", "AGING", "STALE", "OFFLINE"
NO_DATA = "NO_DATA"


def utcnow() -> datetime:
    """Timezone-aware UTC. Never datetime.utcnow()."""
    return datetime.now(timezone.utc)


def freshness_tier(source_key: str, observed_at: Optional[datetime],
                   now: Optional[datetime] = None) -> str:
    """Tier from the source's documented cadence.

    Pass-based sources (NISAR 12-day repeat, Sentinel-1/2, Resourcesat) use
    'latest available pass' semantics: the cadence IS the repeat cycle, so a
    scene is FRESH for a whole cycle rather than going stale by the clock.
    """
    if observed_at is None:
        return NO_DATA
    cfg = SOURCE_CADENCE.get(source_key)
    if cfg is None:
        return NO_DATA
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    age = ((now or utcnow()) - observed_at).total_seconds()
    cadence = cfg["cadence_s"]
    if age <= cadence * FRESHNESS_MULTIPLIERS["FRESH"]:
        return FRESH
    if age <= cadence * FRESHNESS_MULTIPLIERS["RECENT"]:
        return RECENT
    if age <= cadence * FRESHNESS_MULTIPLIERS["AGING"]:
        return AGING
    return STALE


def liveness(source_key: str) -> str:
    cfg = SOURCE_CADENCE.get(source_key)
    return cfg["liveness"] if cfg else "LATEST_AVAILABLE"


@dataclass
class Provenance:
    """Travels with the value, never assembled separately at render time."""
    source: str
    dataset_product_id: Optional[str] = None
    observed_at: Optional[str] = None
    received_at: Optional[str] = None
    processed_at: Optional[str] = None
    spatial_resolution: Optional[str] = None
    temporal_resolution: Optional[str] = None
    licence: Optional[str] = None
    quality_flag: str = "GOOD"          # GOOD | DEGRADED | SUSPECT | ESTIMATED


@dataclass
class DataStatus:
    """Attached to every payload that carries, or fails to carry, observations."""
    status: str                          # FRESH/RECENT/AGING/STALE/OFFLINE/NO_DATA
    source: str
    liveness: str = "LATEST_AVAILABLE"
    observed_at: Optional[str] = None
    last_success_at: Optional[str] = None
    reason: Optional[str] = None
    pending: Optional[str] = None
    provenance: Optional[dict] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def no_data(source: str, reason: str, last_success_at: Optional[str] = None,
            pending: Optional[str] = None, offline: bool = False) -> dict:
    """The canonical unavailable-source payload. No values, ever."""
    return DataStatus(
        status=OFFLINE if offline else NO_DATA,
        source=source,
        liveness=liveness(source),
        last_success_at=last_success_at,
        reason=reason,
        pending=pending,
    ).as_dict()
