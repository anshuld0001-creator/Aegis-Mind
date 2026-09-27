"""
AEGIS MIND - API entrypoint.

"AI-assisted preventive personnel welfare and early intervention."

This service never diagnoses mental illness, never detects deception, and
never issues disciplinary action. Every meaningful welfare decision passes
through a human welfare officer (see /api/cases).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 - ensures models are registered before create_all
from app.routers import auth, checkin, risk, cases, analytics, mitra
from app.ml.risk_engine import risk_engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_TAGLINE,
    version="1.0.0-prototype",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(checkin.router)
app.include_router(risk.router)
app.include_router(cases.router)
app.include_router(analytics.router)
app.include_router(mitra.router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "tagline": settings.APP_TAGLINE,
        "status": "ok",
        "models_loaded": risk_engine.is_ready(),
        "docs": "/docs",
        "note": "Prototype for SIH 2026 (PS ID 26186). Uses 100% synthetic demo data.",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "models_loaded": risk_engine.is_ready()}
