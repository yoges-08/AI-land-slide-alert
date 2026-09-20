"""Ingestion Scheduler & Job Management (Milestone 2)

Uses APScheduler (AsyncIOScheduler) to coordinate background ingestion jobs
according to each provider's documented cadence. Unverified providers are blocked,
and job failures are isolated so one failing source cannot crash the scheduler.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.app.ingestion.base import BaseSource
from backend.app.ingestion.registry import source_registry

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """Manages APScheduler lifecycle for multi-source periodic ingestion."""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        return self._is_running and self._scheduler is not None and self._scheduler.running

    def _get_job_id(self, source_id: str) -> str:
        return f"ingest_{source_id.strip().lower()}"

    def start(self, autoconfigure_jobs: bool = True) -> None:
        """Start the background scheduler."""
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler(timezone=timezone.utc)

        if not self._scheduler.running:
            self._scheduler.start()
            self._is_running = True
            logger.info("[Scheduler] IngestionScheduler started successfully.")

            if autoconfigure_jobs:
                self.schedule_all_active()

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully stop the background scheduler."""
        if self._scheduler is not None and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            self._is_running = False
            logger.info("[Scheduler] IngestionScheduler stopped.")

    def schedule_all_active(self) -> int:
        """Schedule periodic ingestion jobs for all active and verified sources."""
        active_sources = source_registry.list_active_sources()
        count = 0
        for src in active_sources:
            try:
                self.add_source_job(src)
                count += 1
            except Exception as ex:
                logger.error("[Scheduler] Failed to schedule source %s: %s", src.source_id, ex)
        logger.info("[Scheduler] Scheduled %d active data sources.", count)
        return count

    def add_source_job(self, source: BaseSource) -> bool:
        """Register or update an interval job for a specific source."""
        if not source_registry.is_verified(source.source_id):
            logger.warning(
                "[Scheduler] Source %s is blocked (PENDING_VERIFICATION). Skipping scheduler registration.",
                source.source_id
            )
            return False

        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler(timezone=timezone.utc)

        job_id = self._get_job_id(source.source_id)
        # Cadence in minutes -> seconds
        interval_minutes = max(1, getattr(source, "cadence_minutes", 60))

        # Define wrapper job function
        async def _job_wrapper():
            logger.debug("[Scheduler] Firing scheduled ingestion for: %s", source.source_id)
            try:
                result = await source.run_cycle()
                logger.debug("[Scheduler] Ingestion cycle result for %s: %s", source.source_id, result.get("status"))
            except Exception as err:
                logger.error("[Scheduler] Unhandled error during scheduled ingestion for %s: %s", source.source_id, err, exc_info=True)

        self._scheduler.add_job(
            _job_wrapper,
            trigger=IntervalTrigger(minutes=interval_minutes, timezone=timezone.utc),
            id=job_id,
            name=f"Ingest {source.name}",
            replace_existing=True
        )
        logger.info("[Scheduler] Added job %s with interval %d minutes.", job_id, interval_minutes)
        return True

    def remove_source_job(self, source_id: str) -> bool:
        """Remove a scheduled ingestion job."""
        if self._scheduler is None:
            return False
        job_id = self._get_job_id(source_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info("[Scheduler] Removed job %s.", job_id)
            return True
        return False

    def pause_source(self, source_id: str) -> bool:
        """Pause a scheduled source job."""
        if self._scheduler is None:
            return False
        job_id = self._get_job_id(source_id)
        job = self._scheduler.get_job(job_id)
        if job:
            job.pause()
            logger.info("[Scheduler] Paused job %s.", job_id)
            return True
        return False

    def resume_source(self, source_id: str) -> bool:
        """Resume a paused source job."""
        if self._scheduler is None:
            return False
        job_id = self._get_job_id(source_id)
        job = self._scheduler.get_job(job_id)
        if job:
            job.resume()
            logger.info("[Scheduler] Resumed job %s.", job_id)
            return True
        return False

    async def trigger_now(self, source_id: str) -> Dict[str, Any]:
        """Immediately execute an ingestion cycle on-demand."""
        source = source_registry.get(source_id)
        if not source:
            raise ValueError(f"Source '{source_id}' is not registered in source registry")

        if not source_registry.is_verified(source_id):
            return {
                "source_id": source_id,
                "success": False,
                "status": "BLOCKED",
                "error": f"Source '{source_id}' is PENDING_VERIFICATION and cannot be triggered until credentials/API are verified."
            }

        logger.info("[Scheduler] Manual trigger requested for: %s", source_id)
        return await source.run_cycle()

    def get_jobs_status(self) -> List[Dict[str, Any]]:
        """List current state of all scheduled ingestion jobs."""
        if self._scheduler is None or not self._scheduler.running:
            return []

        jobs_info = []
        for job in self._scheduler.get_jobs():
            jobs_info.append({
                "job_id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "pending": job.pending
            })
        return jobs_info


# Global Scheduler Instance
ingestion_scheduler = IngestionScheduler()
