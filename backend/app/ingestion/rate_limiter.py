"""Per-source Rate Limiting and Call Budget Guards (Milestone 2)

Protects non-commercial free tiers (e.g. Open-Meteo <10,000 calls/day)
and prevents provider rate-limit bans via client-side burst and quota controls.
"""
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

class RateLimiter:
    def __init__(self, source_id: str, daily_budget: int = 10000, max_calls_per_second: float = 10.0):
        self.source_id = source_id
        self.daily_budget = daily_budget
        self.min_interval_s = 1.0 / max_calls_per_second if max_calls_per_second > 0 else 0.0
        
        self.calls_today = 0
        self.last_call_timestamp: float = 0.0
        self.reset_date = datetime.now(timezone.utc).date()

    def _check_day_rollover(self):
        current_date = datetime.now(timezone.utc).date()
        if current_date > self.reset_date:
            self.calls_today = 0
            self.reset_date = current_date

    def can_call(self, count: int = 1) -> bool:
        """Check if an outbound batch of size `count` is permitted under daily quota."""
        self._check_day_rollover()
        return (self.calls_today + count) <= self.daily_budget

    def acquire(self, count: int = 1) -> bool:
        """Synchronously acquire permission for `count` calls. Returns True if granted."""
        self._check_day_rollover()
        if not self.can_call(count):
            return False

        # Burst rate spacing
        now = time.time()
        elapsed = now - self.last_call_timestamp
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)

        self.calls_today += count
        self.last_call_timestamp = time.time()
        return True

    async def acquire_async(self, count: int = 1) -> bool:
        """Asynchronously acquire permission for `count` calls without blocking event loop."""
        self._check_day_rollover()
        if not self.can_call(count):
            return False

        now = time.time()
        elapsed = now - self.last_call_timestamp
        if elapsed < self.min_interval_s:
            await asyncio.sleep(self.min_interval_s - elapsed)

        self.calls_today += count
        self.last_call_timestamp = time.time()
        return True

    def reset_usage(self):
        """Reset call counter (useful for unit tests and manual maintenance)."""
        self.calls_today = 0
        self.last_call_timestamp = 0.0
        self.reset_date = datetime.now(timezone.utc).date()

    def get_status(self) -> Dict[str, Any]:
        """Returns current usage and quota status."""
        self._check_day_rollover()
        return {
            "source_id": self.source_id,
            "daily_budget": self.daily_budget,
            "calls_today": self.calls_today,
            "remaining_budget": max(0, self.daily_budget - self.calls_today),
            "quota_exceeded": self.calls_today >= self.daily_budget,
            "reset_date": str(self.reset_date)
        }

# Global registry of source rate limiters
_LIMITERS: Dict[str, RateLimiter] = {
    "open_meteo": RateLimiter("open_meteo", daily_budget=10000, max_calls_per_second=5.0),
    "usgs_fdsn": RateLimiter("usgs_fdsn", daily_budget=50000, max_calls_per_second=2.0),
    "gpm_imerg": RateLimiter("gpm_imerg", daily_budget=20000, max_calls_per_second=5.0),
    "firms": RateLimiter("firms", daily_budget=10000, max_calls_per_second=1.0),
    "mosdac_insat3d_qpe": RateLimiter("mosdac_insat3d_qpe", daily_budget=10000, max_calls_per_second=2.0),
    "copernicus_s1_sar": RateLimiter("copernicus_s1_sar", daily_budget=5000, max_calls_per_second=1.0),
    "copernicus_s2_optical": RateLimiter("copernicus_s2_optical", daily_budget=5000, max_calls_per_second=1.0),
    "nasa_coolr": RateLimiter("nasa_coolr", daily_budget=5000, max_calls_per_second=1.0)
}

def get_rate_limiter(source_id: str) -> RateLimiter:
    normalized_key = source_id.strip().lower()
    if normalized_key not in _LIMITERS:
        _LIMITERS[normalized_key] = RateLimiter(normalized_key, daily_budget=10000, max_calls_per_second=5.0)
    return _LIMITERS[normalized_key]
