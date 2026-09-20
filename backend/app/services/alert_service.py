"""Alert store and threshold evaluation.

M0, confirmed defect 4: this module held six hardcoded alerts with prose like
"Heavy 24h precipitation (142 mm)" and created_at strings like "2 hours ago" —
a literal that never aged. They are gone.

M0 keeps the store in-process (the DB arrives in M1) but makes it honest:
  - starts empty; no seeded alerts
  - created_at is a real timezone-aware ISO-8601 timestamp
  - every alert carries the advisory notice and its input provenance
  - an alert cannot be raised from data that is not an observation

M1 replaces this with the alerts table. M7 adds dedupe/cooldown/escalation/
expiry/grouping. M11 puts auth on the write path, which is why POST is disabled
rather than left open (see routes.py).
"""
from __future__ import annotations

import itertools
import threading
from typing import Any, Dict, List, Optional

from backend.app.core.config import ADVISORY_NOTICE
from backend.app.core.freshness import utcnow

_ALERTS: List[Dict[str, Any]] = []
_ID_SEQ = itertools.count(1)
_LOCK = threading.Lock()

WRITE_DISABLED_REASON = (
    "Alert creation is disabled until authentication lands in M11. The baseline "
    "accepted unauthenticated writes into a process-local list."
)


def get_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_ALERTS[:limit])


def create_alert(location_id: int, location_name: str, state: str,
                 hazard_type: str, severity: str, title: str, message: str,
                 inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Internal use only in M0 — the HTTP write path is closed."""
    now = utcnow()
    alert = {
        "id": next(_ID_SEQ),
        "location_id": location_id,
        "location_name": location_name,
        "state": state,
        "hazard_type": hazard_type,
        "severity": severity,
        "title": title,
        "message": message,
        "created_at": now.isoformat(),      # real timestamp, not "2 hours ago"
        "is_active": True,
        "is_read": False,
        "inputs": inputs or {},
        "advisory": ADVISORY_NOTICE,
    }
    with _LOCK:
        _ALERTS.insert(0, alert)
    return alert


def reset_alerts() -> None:
    """Test hook."""
    with _LOCK:
        _ALERTS.clear()


def evaluate_threshold_breach(location: dict, weather: dict,
                              risk_result: dict) -> Dict[str, Any]:
    """Evaluate documented thresholds against OBSERVED rainfall only.

    This is where the baseline did its worst damage: it consumed the hardcoded
    fallback 142 mm and emitted a Critical alert quoting that number as if it
    had been measured. An alert may now only be raised from a real observation.
    """
    observed = (weather or {}).get("observed") or {}
    rainfall_24h = observed.get("rainfall_24h")
    weather_status = (weather or {}).get("status")

    if rainfall_24h is None:
        return {
            "breach": False,
            "evaluated": False,
            "reason": "No observed 24 h rainfall available; thresholds not evaluated.",
            "weather_status": weather_status,
            "advisory": ADVISORY_NOTICE,
        }

    index = risk_result.get("hazard_index")
    if index is None:
        return {
            "breach": False,
            "evaluated": False,
            "reason": "No hazard index available for this location.",
            "weather_status": weather_status,
            "advisory": ADVISORY_NOTICE,
        }

    # Interim documented thresholds. M6 replaces these with cited
    # intensity-duration thresholds for Indian terrain; M7 owns the levels.
    breach, level = False, None
    if index >= 0.70 and rainfall_24h >= 100:
        breach, level = True, "WARNING"
    elif index >= 0.40 and rainfall_24h >= 60:
        breach, level = True, "ADVISORY"

    return {
        "breach": breach,
        "evaluated": True,
        "alert_level": level,
        "weather_status": weather_status,
        "inputs": {
            "observed_rainfall_24h_mm": rainfall_24h,
            "observed_at": observed.get("observed_at"),
            "rainfall_source": (weather or {}).get("source"),
            "hazard_index": index,
        },
        "message": (
            f"Observed 24 h rainfall {rainfall_24h} mm at {location.get('name')} "
            f"with hazard index {index}."
        ) if breach else None,
        "note": "Interim thresholds pending M6/M7. Not a calibrated warning.",
        "advisory": ADVISORY_NOTICE,
    }
