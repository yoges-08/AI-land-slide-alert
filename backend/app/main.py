import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from backend.app.api.routes import router as api_router
from backend.app.core.config import ADVISORY_NOTICE, settings
from backend.app.core.mode import DEMO_LABEL, is_demo
from backend.app.ingestion.scheduler import ingestion_scheduler
from backend.app.services.ml_service import load_ml_assets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[LANDSAFE-NER] starting in %s mode", settings.LANDSAFE_MODE)
    if is_demo():
        logger.warning("[LANDSAFE-NER] DEMO MODE — every response carries %s", DEMO_LABEL)
    load_ml_assets()          # real infrastructure, kept (defect 6)
    logger.info("[LANDSAFE-NER] model and SHAP explainer loaded (UNCALIBRATED, synthetic training data)")
    if settings.SCHEDULER_AUTOSTART:
        ingestion_scheduler.start()
        logger.info("[LANDSAFE-NER] Ingestion scheduler started")
    yield
    if ingestion_scheduler.is_running:
        ingestion_scheduler.shutdown()
        logger.info("[LANDSAFE-NER] Ingestion scheduler stopped")
    logger.info("[LANDSAFE-NER] shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Advisory landslide and multi-hazard monitoring for Northeast India. "
        "Not an official warning system — IMD, NDMA and NCS are the sole authorities."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# M0, defect 7: the baseline used allow_origins=["*"] with allow_credentials=True.
# That combination is a real security gap and is additionally rejected outright
# by browsers, so it never worked as intended either. Origins now come from
# config/.env. Auth on write endpoints lands in M11.
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_advisory_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-LANDSAFE-Advisory"] = (
        "Advisory only. IMD, NDMA and NCS are the official authorities."
    )
    response.headers["X-LANDSAFE-Mode"] = settings.LANDSAFE_MODE
    if is_demo():
        response.headers["X-LANDSAFE-Data-Mode"] = DEMO_LABEL
    return response


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "system": settings.PROJECT_NAME,
        "description": "Advisory landslide and multi-hazard monitoring, Northeast India",
        "advisory_notice": ADVISORY_NOTICE,
        "academic_prototype_disclaimer": settings.PROTOTYPE_DISCLAIMER,
        "mode": settings.LANDSAFE_MODE,
        "api_docs": "/docs",
        "api_prefix": settings.API_V1_STR,
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "LANDSAFE-NER API",
        "mode": settings.LANDSAFE_MODE,
        "note": "Liveness only. Per-source health arrives in M2.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
