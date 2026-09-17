import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.api.routes import router as api_router
from backend.app.services.ml_service import load_ml_assets

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[LANDSAFE-NER] Initializing Backend Engine...")
    load_ml_assets()
    print("[LANDSAFE-NER] Machine Learning models and SHAP explainer ready.")
    yield
    print("[LANDSAFE-NER] Shutting down Backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Landslide & Multi-Hazard Risk Monitoring API for Northeast India (B.Tech AI & Data Science Prototype)",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_disclaimer_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Prototype-Disclaimer"] = (
        "LANDSAFE-NER is an academic prototype. Not an official disaster warning system."
    )
    return response

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "system": settings.PROJECT_NAME,
        "description": "Landslide Risk Monitoring System for Northeast India",
        "academic_prototype_disclaimer": settings.PROTOTYPE_DISCLAIMER,
        "api_docs": "/docs",
        "api_prefix": settings.API_V1_STR,
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "LANDSAFE-NER API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
