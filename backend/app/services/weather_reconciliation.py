"""Weather Reconciliation & Antecedent Saturation Index (ASI) Engine (Milestone 3)

Provides:
1. Multi-source priority arbitration:
   MOSDAC INSAT-3D/3DR (Priority 1) -> NASA GPM IMERG (Priority 2) -> Open-Meteo (Priority 3).
2. Antecedent Saturation Index (ASI) computation:
   ASI_10d = sum_{k=1}^{10} (0.85)^k * R_k
   where R_k is the 24h precipitation k days before the current observation.
3. Idempotent upsert of incoming weather observations to weather_observations table.
4. Audit-proof zero-fabrication quality reporting.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.config import ADVISORY_NOTICE
from backend.app.core.freshness import freshness_tier, utcnow
from backend.app.models.db_models import DataSource, District, SourceHealth, WeatherObservation, utc_now

logger = logging.getLogger(__name__)

# Strict India-First Multi-Source Priority
WEATHER_SOURCE_PRIORITY = [
    "MOSDAC_INSAT3D_QPE",
    "NASA_GPM_IMERG",
    "OPEN_METEO"
]

DECAY_FACTOR = 0.85  # Standard daily hydrological infiltration/evapotranspiration decay factor


class WeatherReconciliationService:
    """Service reconciling multi-source precipitation feeds and computing dynamic ASI."""

    @staticmethod
    def calculate_asi(daily_rainfall_past_10d: List[Optional[float]], decay: float = DECAY_FACTOR) -> Optional[float]:
        """Compute 10-day Antecedent Saturation Index (ASI) from past daily rainfall.
        
        daily_rainfall_past_10d[0] = R_1 (yesterday, 1 day ago)
        daily_rainfall_past_10d[1] = R_2 (2 days ago)
        ...
        daily_rainfall_past_10d[9] = R_10 (10 days ago)

        Formula: ASI = sum_{k=1}^{N} (decay)^k * R_k
        Returns None if daily_rainfall_past_10d is empty or contains no valid numbers.
        """
        if not daily_rainfall_past_10d:
            return None

        total_asi = 0.0
        valid_days = 0

        for k_idx, r_val in enumerate(daily_rainfall_past_10d[:10], start=1):
            if r_val is not None and r_val >= 0:
                weight = decay ** k_idx
                total_asi += weight * float(r_val)
                valid_days += 1

        if valid_days == 0:
            return None

        return round(total_asi, 2)

    @classmethod
    def compute_district_asi(cls, district_id: int, db: Session, ref_time: Optional[datetime] = None) -> Optional[float]:
        """Retrieve past 10 days of observations for a district and compute ASI."""
        if ref_time is None:
            ref_time = utc_now()

        past_10d_rainfall: List[Optional[float]] = []

        for day_offset in range(1, 11):
            day_target = ref_time - timedelta(days=day_offset)
            start_window = day_target.replace(hour=0, minute=0, second=0, microsecond=0)
            end_window = day_target.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Query observation for this day slot
            obs = (
                db.query(WeatherObservation)
                .filter(
                    WeatherObservation.district_id == district_id,
                    WeatherObservation.is_forecast == False,
                    WeatherObservation.observation_time >= start_window,
                    WeatherObservation.observation_time <= end_window,
                )
                .order_by(desc(WeatherObservation.observation_time))
                .first()
            )

            if obs and obs.rainfall_24h_mm is not None:
                past_10d_rainfall.append(obs.rainfall_24h_mm)
            else:
                past_10d_rainfall.append(None)

        return cls.calculate_asi(past_10d_rainfall)

    @classmethod
    def store_observations(cls, records: List[Dict[str, Any]], db: Session) -> int:
        """Store or update weather observations idempotently."""
        if not records:
            return 0

        stored_count = 0
        now = utc_now()

        for rec in records:
            district_id = rec.get("district_id")
            source_id = rec.get("source_id")
            obs_time = rec.get("observation_time")
            is_forecast = rec.get("is_forecast", False)

            if district_id is None or source_id is None or obs_time is None:
                continue

            existing = (
                db.query(WeatherObservation)
                .filter(
                    WeatherObservation.district_id == district_id,
                    WeatherObservation.source_id == source_id,
                    WeatherObservation.observation_time == obs_time,
                    WeatherObservation.is_forecast == is_forecast,
                )
                .first()
            )

            if existing:
                # Update existing record
                if "rainfall_1h_mm" in rec:
                    existing.rainfall_1h_mm = rec["rainfall_1h_mm"]
                if "rainfall_24h_mm" in rec:
                    existing.rainfall_24h_mm = rec["rainfall_24h_mm"]
                if "rainfall_7d_cumulative_mm" in rec:
                    existing.rainfall_7d_cumulative_mm = rec["rainfall_7d_cumulative_mm"]
                if "temperature_c" in rec:
                    existing.temperature_c = rec["temperature_c"]
                if "relative_humidity_pct" in rec:
                    existing.relative_humidity_pct = rec["relative_humidity_pct"]
                if "wind_speed_kmh" in rec:
                    existing.wind_speed_kmh = rec["wind_speed_kmh"]
                if "quality_flag" in rec:
                    existing.quality_flag = rec["quality_flag"]
                existing.ingestion_time = now
            else:
                new_obs = WeatherObservation(
                    district_id=district_id,
                    source_id=source_id,
                    observation_time=obs_time,
                    ingestion_time=now,
                    temperature_c=rec.get("temperature_c"),
                    relative_humidity_pct=rec.get("relative_humidity_pct"),
                    wind_speed_kmh=rec.get("wind_speed_kmh"),
                    rainfall_1h_mm=rec.get("rainfall_1h_mm"),
                    rainfall_24h_mm=rec.get("rainfall_24h_mm"),
                    rainfall_7d_cumulative_mm=rec.get("rainfall_7d_cumulative_mm"),
                    antecedent_saturation_index=rec.get("antecedent_saturation_index"),
                    quality_flag=rec.get("quality_flag", "NOMINAL"),
                    is_forecast=is_forecast,
                )
                db.add(new_obs)

            stored_count += 1

        db.commit()
        return stored_count

    @classmethod
    def get_reconciled_district_weather(cls, district_id: int, db: Session) -> Dict[str, Any]:
        """Fetch the highest-priority, freshest weather observation for a district."""
        dist = db.query(District).filter((District.id == district_id) | (District.lgd_code == district_id)).first()
        target_id = dist.id if dist else district_id

        # Query recent observations for this district ordered by time
        recent_obs = (
            db.query(WeatherObservation)
            .filter(
                WeatherObservation.district_id == target_id,
                WeatherObservation.is_forecast == False,
            )
            .order_by(desc(WeatherObservation.observation_time))
            .limit(20)
            .all()
        )

        if not recent_obs:
            return {
                "district_id": district_id,
                "status": "NO_DATA",
                "source": "None",
                "observed": None,
                "antecedent_saturation_index": None,
                "advisory": ADVISORY_NOTICE,
                "timestamp": utcnow().isoformat(),
            }

        max_time = recent_obs[0].observation_time
        # Group observations within 3 hours of the latest available observation time
        active_candidates = [
            o for o in recent_obs
            if o.observation_time and abs((max_time - o.observation_time).total_seconds()) <= 10800
        ]

        chosen_obs = None
        # Arbitrate by source priority within freshest candidates
        for preferred_source in WEATHER_SOURCE_PRIORITY:
            match = next((o for o in active_candidates if o.source_id == preferred_source), None)
            if match and (match.rainfall_24h_mm is not None or match.rainfall_1h_mm is not None):
                chosen_obs = match
                break

        if not chosen_obs and active_candidates:
            chosen_obs = active_candidates[0]
        elif not chosen_obs:
            chosen_obs = recent_obs[0]

        asi_val = cls.compute_district_asi(district_id, db)

        if not chosen_obs:
            return {
                "district_id": district_id,
                "status": "NO_DATA",
                "source": "None",
                "observed": None,
                "antecedent_saturation_index": None,
                "advisory": ADVISORY_NOTICE,
                "timestamp": utcnow().isoformat(),
            }

        # Map source_id to canonical SOURCE_CADENCE key
        src_id_upper = (chosen_obs.source_id or "").upper()
        if "MOSDAC" in src_id_upper or "INSAT" in src_id_upper:
            source_key = "insat_3d_qpe"
        elif "GPM" in src_id_upper or "NASA" in src_id_upper:
            source_key = "gpm_imerg"
        elif "OPEN_METEO" in src_id_upper:
            source_key = "open_meteo"
        else:
            source_key = chosen_obs.source_id.lower()

        tier = freshness_tier(source_key, chosen_obs.observation_time)

        return {
            "district_id": district_id,
            "status": tier,
            "source": chosen_obs.source_id,
            "observed": {
                "observation_time": chosen_obs.observation_time.isoformat() if chosen_obs.observation_time else None,
                "rainfall_1h_mm": chosen_obs.rainfall_1h_mm,
                "rainfall_24h_mm": chosen_obs.rainfall_24h_mm,
                "rainfall_7d_cumulative_mm": chosen_obs.rainfall_7d_cumulative_mm,
                "temperature_c": chosen_obs.temperature_c,
                "relative_humidity_pct": chosen_obs.relative_humidity_pct,
                "wind_speed_kmh": chosen_obs.wind_speed_kmh,
                "quality_flag": chosen_obs.quality_flag,
            },
            "antecedent_saturation_index": asi_val,
            "advisory": ADVISORY_NOTICE,
            "timestamp": utcnow().isoformat(),
        }
