"""Entry point for the CognitoForge Labs FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.routers import operations

settings = get_settings()

app = FastAPI(
    title="CognitoForge Labs",
    version="0.1.0",
    description="Hackathon backend for AI-driven DevSecOps red team simulations.",
)

# Basic CORS support so the hackathon frontend can call these endpoints without hassle.
allowed_origins = {"http://localhost:3000", "http://127.0.0.1:3000"}
if settings.auth0_domain:
    allowed_origins.add(settings.auth0_domain.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(operations.router)


@app.get("/health")
async def healthcheck() -> dict[str, bool]:
    """Simple health endpoint for uptime monitoring."""

    return {"ok": True}
