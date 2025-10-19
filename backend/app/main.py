"""Entry point for the CognitoForge Labs FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.settings import get_settings
from backend.app.routers import operations, ai
from backend.app.integrations import init_snowflake

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CognitoForge Labs",
    version="0.1.0",
    description="Hackathon backend for AI-driven DevSecOps red team simulations.",
)

# Basic CORS support so the hackathon frontend can call these endpoints without hassle.
allowed_origins = {
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
}
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
app.include_router(ai.router)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise optional integrations once the application boots."""

    try:
        client = init_snowflake()
        if client is not None:
            logger.info("Snowflake integration initialised")
        else:
            logger.debug("Snowflake integration skipped (configuration missing or connector absent)")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Snowflake integration initialisation failed", extra={"error": str(exc)})


@app.get("/health")
async def healthcheck() -> dict[str, bool]:
    """Simple health endpoint for uptime monitoring."""

    return {"ok": True}
